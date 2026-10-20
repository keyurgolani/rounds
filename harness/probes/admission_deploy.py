"""Deployment checks for the admission chain and gates (ROUNDS-00A-L01 stage 4).

Built on #9's harness and #1 stage 3's admission phase (admission_check.py,
which already proves idempotency, shared counts, and in-flight limits across
the two replicas). These phases add what stage 4's Deployment item asks for:

  admission-deploy   both replicas up on the one PocketBase, enforcing:
                     on each replica, the admitted routes refuse an anonymous
                     caller in the typed envelope, the runner's own byte cap
                     comes before the account, the request's fields come
                     before its idempotency key and the key before any lookup,
                     a refusal repeats none of the request, the replica admits
                     through the admission store in admission/v1 and only the
                     admitted request counts, and stage 2's closures hold in
                     the built image (a candidate's minimal environment, its
                     unprivileged uid and private scratch, an event loop a
                     running execution doesn't hold up, a status-only
                     renderer health check, and a typed render failure).
  emergency-disable  both replicas restarted with ROUNDS_GATE_RUN=disabled:
                     the route answers 503 route_disabled through nginx and
                     at each replica for every caller and charges nothing,
                     each replica's gates line says so, and the other routes
                     still refuse an anonymous caller 401 and admit a
                     signed-in one.
  emergency-enable   the gate cleared and both replicas restarted: every
                     route refuses an anonymous caller 401 again, runs are
                     admitted through nginx and at each replica, and each
                     gates line says so.

Each check writes one receipt, named by the guarantee it holds; the verdict
requires a passing receipt for every id in CHECKS and in
verify_deployment.ADMISSION_CHECKS. Accounts are generated per run, a
candidate run reports only names and numbers, never a value from its
environment, and no receipt carries a token.
"""
from __future__ import annotations

import json
import os
import secrets
import time
import urllib.error
import urllib.request
from typing import Any, Callable

import admission_check as ac
import factory
import verify_deployment as vd
from pbclient import PBClient
from receipts import Receipt, ReceiptWriter

POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://frontend").rstrip("/")

CHECKS: dict[str, str] = {
    "admission.policy.fields-before-idempotency":
        "a request with a field it doesn't take is refused 422 before its idempotency key is asked for",
    "admission.policy.idempotency-before-lookup":
        "a request without an idempotency key is refused 400 before anything is looked up",
    "admission.policy.version":
        "an enforcing replica admits through the admission store in admission/v1, and only the admitted request counts",
    "admission.error-shape.no-echo":
        "a refusal of a request with content is the typed envelope and repeats none of that content",
    "admission.closure.child-env.minimal":
        "a candidate process sees only the minimal environment, none of the runner's settings",
    "admission.closure.candidate.unprivileged":
        "a candidate process runs as a candidate uid that can't write the runner's code",
    "admission.closure.scratch.private":
        "a candidate process's home and temp directory are its own 0700 scratch",
    "admission.closure.event-loop.free":
        "a running execution doesn't hold up the replica's other requests",
    "admission.closure.pdf-health.status-only":
        "the renderer health check answers only its status",
    "admission.closure.render-failure.typed":
        "a render the renderer can't finish is the typed 503, without the renderer's text",
    "admission.emergency.disabled.signed-in-denied":
        "with its gate off, a signed-in request is refused 503 route_disabled and charged nothing",
    "admission.emergency.disabled.others-unaffected":
        "turning one route off leaves the other routes admitting",
    "admission.emergency.enabled.restored":
        "clearing the gate and restarting admits the route again",
}

# What a candidate process's environment may hold (backend/app/sandbox.py
# candidate_env), plus what Python itself may set.
ALLOWED_ENV = frozenset({
    "PATH", "HOME", "TMPDIR", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE", "PYTHONDONTWRITEBYTECODE",
})
# The candidate uids the image creates, one per in-flight slot.
CANDIDATE_UIDS = range(10001, 10005)
# How long a replica may take to answer /health while a run is in flight.
FREE_LOOP_S = 1.0
SLOW_S = 3
RENDERER_TEXT = ("pdf-renderer", "Errno", "Traceback", "urlopen", "Connection refused")
# The contract the runner and its admission store speak (backend/app/admission_state.py).
ADMISSION_VERSION = "admission/v1"

# Reports the facts the closures promise, as names and numbers only.
CLOSURE_CODE = '''import os


def {name}(*args, **kwargs):
    home = os.environ.get("HOME", "")
    try:
        st = os.stat(home)
        mode, owner = st.st_mode & 0o777, st.st_uid
    except OSError:
        mode, owner = None, None
    return {{
        "env": sorted(os.environ),
        "uid": os.getuid(),
        "app_writable": os.access("/app", os.W_OK) or os.access("/app/main.py", os.W_OK),
        "home_mode": mode,
        "home_owned": owner == os.getuid(),
        "tmpdir_is_home": os.environ.get("TMPDIR") == home,
    }}
'''


def receipt(check_id: str, target: str, actor: str, expected: int, observed: int, ok: bool,
            elapsed_ms: int = 0, detail: str = "") -> Receipt:
    return Receipt(check_id, target, "admission", actor, expected, observed, ok, elapsed_ms, "" if ok else detail)


def verifier_receipts(writer: ReceiptWriter, results, where: str = "") -> None:
    """verify_deployment results as receipts. ``where`` names the hop when
    it isn't the public URL, so a replica's result reads apart from nginx's."""
    for r in results:
        target = f"{where} {r.target}".strip()
        writer.write(Receipt(r.check_id, target, r.operation, r.actor, r.expected_status, r.observed_status,
                             r.passed and not r.inconclusive, r.elapsed_ms, r.detail))


# The compose services behind RUNNER_URLS, in order, as the launcher names
# their saved gates lines.
REPLICA_SERVICES = ("runner", "runner-b")


def gates_log(phase: str, service: str = "runner") -> str:
    """A replica's gates line the launcher saved for this phase."""
    name = f"gates-{phase}.log" if service == "runner" else f"gates-{phase}-{service}.log"
    path = os.path.join(os.path.dirname(os.environ.get("RECEIPTS_PATH", "/out/receipts.jsonl")), name)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _keyed() -> dict[str, str]:
    return {"Idempotency-Key": ac.uuid7()}


def _code(body: Any) -> Any:
    return body.get("code") if isinstance(body, dict) else None


def _code_raw(raw: bytes) -> Any:
    try:
        return _code(json.loads(raw)) if raw else None
    except ValueError:
        return None


def _timed(fn: Callable[[], Any]) -> tuple[Any, int]:
    start = time.monotonic()
    out = fn()
    return out, int((time.monotonic() - start) * 1000)


# --------------------------------------------------------------------------
# admission-deploy
# --------------------------------------------------------------------------


def check_order(writer: ReceiptWriter, replica: str, acct: factory.Account, slug: str, name: str) -> None:
    # 5 before 6: fields the route doesn't take (client-supplied cases, and
    # one named by a marker made for this run), and no key. The refusal is
    # the typed envelope and repeats none of the request.
    marker = "s4echo" + secrets.token_hex(6)
    sent = {**ac.run_body(slug, name), "test_cases": [], marker: marker}
    sent["code"] = f"# {marker}\n" + sent["code"]
    (status, raw, headers), ms = _timed(lambda: _raw_call(replica, "/api/run", acct.token, sent, keyed=False))
    code = _code_raw(raw)
    target = f"{replica} /api/run"
    writer.write(receipt("admission.policy.fields-before-idempotency", target, "standard", 422, status,
                         status == 422 and code == "invalid_request", ms, f"status={status} code={code!r}"))
    problem = vd.envelope_problem(status, raw, headers)
    echoed = sum(1 for t in (marker, "test_cases") if t in raw.decode("utf-8", "replace"))
    writer.write(receipt("admission.error-shape.no-echo", target, "standard", 422, status,
                         status == 422 and not problem and not echoed, ms,
                         f"status={status} {problem} echoed={echoed}".strip()))
    # 6 before 8: no key, for a question that doesn't exist.
    missing = {**ac.run_body(slug, name), "question_slug": "harness-no-such-question"}
    (status, body, _), ms = _timed(lambda: ac.call(replica, "POST", "/api/run", acct.token, missing))
    ok = status == 400 and _code(body) == "idempotency_key_required"
    writer.write(receipt("admission.policy.idempotency-before-lookup", f"{replica} /api/run", "standard",
                         400, status, ok, ms, f"status={status} code={_code(body)!r}"))


def check_closures(writer: ReceiptWriter, replica: str, acct: factory.Account, slug: str, name: str) -> None:
    body = {"question_slug": slug, "language": "python", "code": CLOSURE_CODE.format(name=name), "input": {}}
    (status, out, _), ms = _timed(lambda: ac.call(replica, "POST", "/api/run", acct.token, body, _keyed()))
    facts = (out or {}).get("return_value") if status == 200 and isinstance(out, dict) else None
    target = f"{replica} /api/run"
    if not isinstance(facts, dict):
        why = f"status={status} error={(out or {}).get('error')!r}" if isinstance(out, dict) else f"status={status}"
        for check_id in ("admission.closure.child-env.minimal", "admission.closure.candidate.unprivileged",
                         "admission.closure.scratch.private"):
            writer.write(receipt(check_id, target, "standard", 200, status, False, ms, f"no report: {why}"))
        return
    extra = sorted(set(facts.get("env") or []) - ALLOWED_ENV)
    writer.write(receipt("admission.closure.child-env.minimal", target, "standard", 200, status, not extra, ms,
                         "unexpected variables: " + ", ".join(extra)))
    uid = facts.get("uid")
    ok = isinstance(uid, int) and uid in CANDIDATE_UIDS and facts.get("app_writable") is False
    writer.write(receipt("admission.closure.candidate.unprivileged", target, "standard", 200, status, ok, ms,
                         f"uid={uid} app_writable={facts.get('app_writable')}"))
    ok = facts.get("home_mode") == 0o700 and facts.get("home_owned") is True and facts.get("tmpdir_is_home") is True
    writer.write(receipt("admission.closure.scratch.private", target, "standard", 200, status, ok, ms,
                         f"home_mode={facts.get('home_mode')!r} owned={facts.get('home_owned')} "
                         f"tmpdir_is_home={facts.get('tmpdir_is_home')}"))


def check_store_contract(writer: ReceiptWriter, replica: str, acct: factory.Account, before: dict) -> None:
    """After check_order's refusals and check_closures' one admitted run:
    the store answers the account in admission/v1 and counts that run
    alone. A UTC hour turning between the two reads may move the count to
    the next hour, so then either count passes."""
    after = ac.usage(acct.token)
    same_hour = after.get("hour") == before.get("hour")
    counted = after.get("requests")
    ok = after.get("v") == ADMISSION_VERSION and (counted == 1 if same_hour else counted in (0, 1))
    writer.write(receipt("admission.policy.version", f"{replica} /api/run", "standard", 200, 200, ok, 0,
                         f"v={after.get('v')!r} requests={counted} same_hour={same_hour}"))


def check_event_loop(writer: ReceiptWriter, replica: str, acct: factory.Account, slug: str, name: str) -> None:
    slow = ac.in_background(lambda: ac.call(replica, "POST", "/api/run", acct.token,
                                            ac.run_body(slug, name, SLOW_S), _keyed()))
    busy = ac.wait_in_flight(acct.token, 1)
    worst, status = 0, 0
    for _ in range(3):
        (status, _body, _), ms = _timed(lambda: ac.call(replica, "GET", "/health", timeout=10))
        worst = max(worst, ms)
        if status != 200:
            break
    slow[0].join(timeout=60)
    finished = slow[1].get("result", (0,))[0]
    ok = busy and status == 200 and worst <= FREE_LOOP_S * 1000 and finished == 200
    writer.write(receipt("admission.closure.event-loop.free", f"{replica} /health", "standard", 200, status, ok,
                         worst, f"busy={busy} health_ms={worst} run_status={finished}"))


def check_renderer(writer: ReceiptWriter, replica: str, acct: factory.Account) -> None:
    (status, body, _), ms = _timed(lambda: ac.call(replica, "GET", "/api/pdf/health", acct.token))
    ok = status in (200, 503) and isinstance(body, dict) and set(body) == {"status"} and isinstance(body["status"], str)
    writer.write(receipt("admission.closure.pdf-health.status-only", f"{replica} /api/pdf/health", "standard",
                         200, status, ok, ms, f"status={status} keys={sorted(body) if isinstance(body, dict) else None}"))
    # The harness runs no renderer, so the runner can't reach one.
    raw_status, raw, headers = _raw_call(replica, "/api/pdf/render", acct.token, {"html": "<p>harness</p>"})
    text = raw.decode("utf-8", "replace")
    problem = vd.envelope_problem(raw_status, raw, headers)
    leaked = [t for t in RENDERER_TEXT if t in text]
    code = _code_raw(raw)
    ok = raw_status == 503 and code == "worker_unavailable" and not problem and not leaked
    writer.write(receipt("admission.closure.render-failure.typed", f"{replica} /api/pdf/render", "standard", 503,
                         raw_status, ok, 0, f"status={raw_status} code={code!r} {problem} leaked={leaked}".strip()))


def _raw_call(base: str, path: str, token: str, body: dict, keyed: bool = True) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + token, **(_keyed() if keyed else {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as err:
        return err.code, err.read(), {k.lower(): v for k, v in (err.headers or {}).items()}


def run_admission_deploy(writer: ReceiptWriter) -> None:
    replicas = ac.RUNNERS
    if len(replicas) != 2 or not all(ac.wait_up(r) for r in replicas):
        raise RuntimeError("admission-deploy needs both runner replicas up (RUNNER_URLS)")
    pb = PBClient(POCKETBASE_URL)
    pb.wait_healthy()
    admin = ac.admin_token(pb)
    slug, name, _charge = ac.a_question(pb, admin)
    for replica in replicas:
        verifier_receipts(writer, vd.check_admitted_routes(replica), where=replica)
        verifier_receipts(writer, vd.check_admission_body_caps(replica, at_runner=True), where=replica)
        acct = ac.account(pb, "s4")
        before = ac.usage(acct.token)
        check_order(writer, replica, acct, slug, name)
        check_closures(writer, replica, acct, slug, name)
        check_store_contract(writer, replica, acct, before)
        check_event_loop(writer, replica, acct, slug, name)
        check_renderer(writer, replica, acct)


# --------------------------------------------------------------------------
# emergency disable and re-enable
# --------------------------------------------------------------------------


def _wait_routed() -> list[str]:
    """Both replicas up and nginx routing to the runner; the replicas'
    URLs, in REPLICA_SERVICES order."""
    replicas = ac.RUNNERS
    if len(replicas) != len(REPLICA_SERVICES) or not all(ac.wait_up(r) for r in replicas):
        raise RuntimeError("the emergency phases need both runner replicas up (RUNNER_URLS)")
    frontend = PBClient(FRONTEND_URL)
    frontend.wait_healthy()
    frontend.wait_for("/api/ai/providers", lambda r: r.status == 401 and isinstance(r.body, dict) and "detail" in r.body)
    return replicas


def _gates_receipts(writer: ReceiptWriter, phase: str, expected: dict[str, str], what: str) -> None:
    for service in REPLICA_SERVICES:
        verifier_receipts(writer, vd.check_gates_log(gates_log(phase, service), expected,
                                                     source=f"{service} log {what}"))


ENFORCING = {"ENFORCE_IDEMPOTENCY": "enforce", "ENFORCE_QUOTA": "enforce"}


def run_emergency_disable(writer: ReceiptWriter) -> None:
    replicas = _wait_routed()
    _gates_receipts(writer, "emergency-disable", {"RUN": "disabled", **ENFORCING}, "after disabling RUN")
    verifier_receipts(writer, vd.check_disabled_routes(FRONTEND_URL, ["/api/run"]))
    for replica in replicas:
        verifier_receipts(writer, vd.check_disabled_routes(replica, ["/api/run"]), where=replica)
    # Only the route turned off answers 503; the rest still refuse 401.
    verifier_receipts(writer, vd.check_admitted_routes(FRONTEND_URL, disabled=["/api/run"]), where="with RUN off")

    pb = PBClient(POCKETBASE_URL)
    admin = ac.admin_token(pb)
    slug, name, _charge = ac.a_question(pb, admin)
    acct = ac.account(pb, "s4-off")
    for base in (FRONTEND_URL, *replicas):
        (status, body, _), ms = _timed(lambda: ac.call(base, "POST", "/api/run", acct.token,
                                                       ac.run_body(slug, name), _keyed()))
        charged = ac.usage(acct.token)["requests"]
        ok = status == 503 and _code(body) == "route_disabled" and charged == 0
        writer.write(receipt("admission.emergency.disabled.signed-in-denied", f"{base} /api/run", "standard", 503,
                             status, ok, ms, f"status={status} code={_code(body)!r} charged={charged}"))
    evaluate = {k: v for k, v in ac.run_body(slug, name).items() if k != "input"}
    (status, body, _), ms = _timed(lambda: ac.call(FRONTEND_URL, "POST", "/api/evaluate", acct.token, evaluate,
                                                   _keyed(), timeout=420))
    writer.write(receipt("admission.emergency.disabled.others-unaffected", "/api/evaluate", "standard", 200,
                         status, status == 200, ms, f"status={status} code={_code(body)!r}"))


def run_emergency_enable(writer: ReceiptWriter) -> None:
    replicas = _wait_routed()
    _gates_receipts(writer, "emergency-enable", {"RUN": "enabled", **ENFORCING}, "after re-enabling RUN")
    # Every route refuses an anonymous caller 401 again, none 503.
    verifier_receipts(writer, vd.check_admitted_routes(FRONTEND_URL), where="after RUN re-enabled")
    pb = PBClient(POCKETBASE_URL)
    admin = ac.admin_token(pb)
    slug, name, _charge = ac.a_question(pb, admin)
    acct = ac.account(pb, "s4-on")
    for base in (FRONTEND_URL, *replicas):
        anonymous = ac.call(base, "POST", "/api/run", None, ac.run_body(slug, name))
        (status, body, _), ms = _timed(lambda: ac.call(base, "POST", "/api/run", acct.token,
                                                       ac.run_body(slug, name), _keyed()))
        ok = status == 200 and anonymous[0] == 401 and _code(anonymous[1]) == "unauthenticated"
        writer.write(receipt("admission.emergency.enabled.restored", f"{base} /api/run", "standard", 200, status,
                             ok, ms, f"signed_in={status} anonymous={anonymous[0]} code={_code(anonymous[1])!r}"))
