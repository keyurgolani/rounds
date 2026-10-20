"""Harness check for admission state across two runner replicas
(ROUNDS-00A-L01 stage 3).

Two runner replicas built from this commit share one PocketBase, with
``ROUNDS_GATE_ENFORCE_IDEMPOTENCY`` and ``ROUNDS_GATE_ENFORCE_QUOTA`` at
``enforce``. Every account here is generated for the run.

1. A command completed on one replica replays on the other; a key reused
   for another request, or a missing key, is refused.
2. Requests on both replicas land in one hourly count, and an account's
   in-flight limit holds across them, as does the shared demo tier's.
3. A step 8 denial leaves its command retryable, with no live lease, on
   either replica.
4. No client sets or clears ``is_demo``, the admission collections are
   superuser-only, and the admission routes need a bearer.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import factory
from pbclient import PBClient

POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
RUNNERS = [u.strip().rstrip("/") for u in os.environ.get("RUNNER_URLS", "").split(",") if u.strip()]
COLLECTIONS = ("admission_commands", "admission_counters", "admission_leases")
# A run's own work: the second one sleeps long enough for others to queue.
SLOW_S = 2


class Checks:
    def __init__(self) -> None:
        self.failed = 0
        self.passed = 0

    def check(self, name: str, ok: bool, why: str = "") -> bool:
        if ok:
            self.passed += 1
            print(f"PASS {name}")
        else:
            self.failed += 1
            print(f"FAIL {name}: {why}")
        return ok


def uuid7() -> str:
    raw = bytearray(secrets.token_bytes(16))
    raw[0:6] = int(time.time() * 1000).to_bytes(6, "big")
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    h = raw.hex()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def call(base: str, method: str, path: str, token: str | None = None, body: Any = None,
         headers: dict[str, str] | None = None, timeout: float = 30) -> tuple[int, Any, dict[str, str]]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    sent = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        sent["Content-Type"] = "application/json"
    if token:
        sent["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + path, data=data, headers=sent, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw, status, got = resp.read(), resp.status, dict(resp.headers)
    except urllib.error.HTTPError as err:
        raw, status, got = err.read(), err.code, dict(err.headers)
    try:
        parsed = json.loads(raw) if raw else None
    except ValueError:
        parsed = None
    return status, parsed, {k.lower(): v for k, v in got.items()}


def wait_up(base: str, attempts: int = 90) -> bool:
    for _ in range(attempts):
        try:
            if call(base, "GET", "/health", timeout=3)[0] == 200:
                return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    return False


def admin_token(pb: PBClient) -> str:
    resp = pb.admin_auth(os.environ.get("PB_ADMIN_EMAIL", ""), os.environ.get("PB_ADMIN_PASSWORD", ""))
    if resp.status != 200 or not isinstance(resp.body, dict):
        raise RuntimeError(f"admin auth failed: status={resp.status}")
    return resp.body["token"]


def account(pb: PBClient, tag: str) -> factory.Account:
    acct = factory.make_account(tag)
    factory.register(pb, acct)
    return acct


def demo_account(pb: PBClient, admin: str) -> factory.Account:
    """A demo-tier account. Only a superuser can set is_demo."""
    acct = factory.make_account("demo")
    created = pb.create("users", admin, {
        "email": acct.email, "password": acct.password, "passwordConfirm": acct.password, "is_demo": True,
    })
    if created.status != 200:
        raise RuntimeError(f"demo account create failed: status={created.status}")
    acct.user_id = created.body["id"]
    auth = pb.auth_password(acct.email, acct.password)
    acct.token = auth.body["token"]
    return acct


def a_question(pb: PBClient, admin: str) -> tuple[str, str, int]:
    """A seeded question with a plain function entry and test cases: its
    slug, its function name, and the wall seconds its cases charge."""
    resp = pb.listing("coding_questions", admin, {"perPage": 200, "fields": "slug,entry,test_cases"})
    for item in (resp.body or {}).get("items", []):
        entry = item.get("entry") or {}
        cases = [tc for tc in (item.get("test_cases") or []) if isinstance(tc, dict)]
        if entry.get("kind") == "function" and isinstance(entry.get("name"), str) and 0 < len(cases) <= 32:
            charge = sum(10 if "large" in (tc.get("tags") or []) else 3 for tc in cases)
            return item["slug"], entry["name"], charge
    raise RuntimeError("no seeded coding question with a function entry")


def run_body(slug: str, name: str, sleep_s: float = 0, marker: int = 1, printed: int = 0) -> dict:
    code = (
        f"import time\ndef {name}(*args, **kwargs):\n    print('x' * {printed})\n"
        f"    time.sleep({sleep_s})\n    return {marker}\n"
    )
    return {"question_slug": slug, "language": "python", "code": code, "input": {}}


def usage(token: str) -> dict:
    status, body, _ = call(POCKETBASE_URL, "GET", "/api/rounds/admission/usage", token)
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"usage failed: status={status}")
    return body


def wait_in_flight(token: str, count: int, timeout_s: float = 10) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if usage(token)["in_flight"] >= count:
            return True
        time.sleep(0.05)
    return False


def in_background(fn) -> tuple[threading.Thread, dict]:
    out: dict = {}

    def target() -> None:
        out["result"] = fn()

    thread = threading.Thread(target=target)
    thread.start()
    return thread, out


def main() -> int:
    c = Checks()
    if len(RUNNERS) != 2:
        c.check("admission.replicas.two-configured", False, f"RUNNER_URLS has {len(RUNNERS)} entries")
        return 1
    pb = PBClient(POCKETBASE_URL)
    pb.wait_healthy()
    c.check("admission.replicas.both-up", all(wait_up(r) for r in RUNNERS), "a runner never answered /health")
    admin = admin_token(pb)
    slug, name, evaluate_charge = a_question(pb, admin)
    one, two = RUNNERS

    # 1. Idempotency across replicas.
    a = account(pb, "adm-a")
    key = uuid7()
    first = call(one, "POST", "/api/run", a.token, run_body(slug, name), {"Idempotency-Key": key})
    c.check("admission.idempotency.first-run-admitted", first[0] == 200, f"status={first[0]}")
    again = call(two, "POST", "/api/run", a.token, run_body(slug, name), {"Idempotency-Key": key})
    c.check("admission.idempotency.replays-on-the-other-replica",
            again[0] == 200 and again[2].get("idempotent-replayed") == "true" and again[1] == first[1],
            f"status={again[0]} replayed={again[2].get('idempotent-replayed')}")
    changed = call(two, "POST", "/api/run", a.token, run_body(slug, name, marker=2), {"Idempotency-Key": key})
    c.check("admission.idempotency.reused-key-refused",
            changed[0] == 409 and (changed[1] or {}).get("code") == "idempotency_mismatch", f"status={changed[0]}")
    keyless = call(one, "POST", "/api/run", a.token, run_body(slug, name))
    c.check("admission.idempotency.key-required",
            keyless[0] == 400 and (keyless[1] or {}).get("code") == "idempotency_key_required", f"status={keyless[0]}")
    # A result near the runner's 64 KiB output cap is kept and replayed whole.
    big = uuid7()
    loud = call(two, "POST", "/api/run", a.token, run_body(slug, name, printed=60_000), {"Idempotency-Key": big})
    echoed = call(one, "POST", "/api/run", a.token, run_body(slug, name, printed=60_000), {"Idempotency-Key": big})
    c.check("admission.idempotency.large-result-replays",
            loud[0] == 200 and len((loud[1] or {}).get("stdout", "")) >= 60_000
            and echoed[2].get("idempotent-replayed") == "true" and echoed[1] == loud[1],
            f"status={loud[0]}/{echoed[0]}")

    # 2. One count across replicas.
    for i in range(4):
        status = call(RUNNERS[i % 2], "POST", "/api/run", a.token, run_body(slug, name), {"Idempotency-Key": uuid7()})[0]
        if status != 200:
            c.check("admission.quota.runs-admitted", False, f"run {i} status={status}")
    # Two charged runs above, a replay and refusals that weren't, and four more.
    used = usage(a.token)
    c.check("admission.quota.one-count-across-replicas", used["requests"] == 6 and used["in_flight"] == 0,
            f"requests={used['requests']} in_flight={used['in_flight']}")
    rows = pb.listing("admission_counters", admin, {"filter": f"bucket = 'account' && account = '{a.user_id}'"})
    c.check("admission.quota.one-counter-row", rows.status == 200 and len(rows.body["items"]) == 1
            and rows.body["items"][0]["requests"] == 6, f"status={rows.status}")

    e = account(pb, "adm-e")
    evaluate = {k: v for k, v in run_body(slug, name).items() if k != "input"}
    evaluated = call(two, "POST", "/api/evaluate", e.token, evaluate, {"Idempotency-Key": uuid7()})
    used = usage(e.token)
    c.check("admission.quota.evaluate-settles-on-its-cases",
            evaluated[0] == 200 and used["requests"] == 1 and used["wall_seconds"] == evaluate_charge,
            f"status={evaluated[0]} wall={used['wall_seconds']} expected={evaluate_charge}")

    b = account(pb, "adm-b")
    slow = [in_background(lambda r=r: call(r, "POST", "/api/run", b.token, run_body(slug, name, SLOW_S),
                                           {"Idempotency-Key": uuid7()})) for r in RUNNERS]
    busy = wait_in_flight(b.token, 2)
    third = call(one, "POST", "/api/run", b.token, run_body(slug, name), {"Idempotency-Key": uuid7()})
    c.check("admission.quota.in-flight-limit-across-replicas",
            busy and third[0] == 429 and (third[1] or {}).get("code") == "quota_exceeded" and "retry-after" in third[2],
            f"busy={busy} status={third[0]}")
    for thread, _out in slow:
        thread.join(timeout=30)
    c.check("admission.quota.slow-runs-finished", all(out.get("result", (0,))[0] == 200 for _t, out in slow),
            f"statuses={[out.get('result', (0,))[0] for _t, out in slow]}")
    after = call(two, "POST", "/api/run", b.token, run_body(slug, name), {"Idempotency-Key": uuid7()})
    c.check("admission.quota.leases-released", after[0] == 200 and usage(b.token)["in_flight"] == 0, f"status={after[0]}")

    d = demo_account(pb, admin)
    other_demo = demo_account(pb, admin)
    held = in_background(lambda: call(one, "POST", "/api/run", d.token, run_body(slug, name, SLOW_S),
                                      {"Idempotency-Key": uuid7()}))
    busy = wait_in_flight(d.token, 1)
    shared = call(two, "POST", "/api/run", other_demo.token, run_body(slug, name), {"Idempotency-Key": uuid7()})
    c.check("admission.demo.shared-in-flight-limit-across-replicas",
            busy and shared[0] == 429 and (shared[1] or {}).get("code") == "demo_limit_reached",
            f"busy={busy} status={shared[0]}")
    held[0].join(timeout=30)
    c.check("admission.demo.tier-from-the-record", usage(d.token)["tier"] == "demo" and usage(a.token)["tier"] == "standard",
            "tiers differ from is_demo")

    # 3. A step 8 denial stays retryable on either replica.
    missing_key = uuid7()
    missing = {**run_body(slug, name), "question_slug": "harness-missing-question"}
    denied = [call(r, "POST", "/api/run", a.token, missing, {"Idempotency-Key": missing_key})[0] for r in RUNNERS]
    rows = pb.listing("admission_commands", admin, {"filter": f"command_id = '{missing_key}'"})
    items = (rows.body or {}).get("items", [])
    leases = pb.listing("admission_leases", admin, {"filter": f"command = '{items[0]['id']}'"}) if items else None
    c.check("admission.step8.retryable-on-either-replica",
            denied == [404, 404] and len(items) == 1 and items[0]["state"] == "retryable"
            and leases is not None and leases.body["items"] == [],
            f"statuses={denied} rows={len(items)}")

    # 4. The demo tier and the store stay server-side.
    for who, target, value in ((a, a.user_id, True), (d, d.user_id, False)):
        forged = pb.update("users", target, {"is_demo": value}, who.token)
        stored = pb.view("users", target, admin)
        c.check(f"admission.demo.tier-locked-{who.tag}",
                forged.status == 400 and stored.body.get("is_demo") is (not value), f"status={forged.status}")
    email = f"harness-forged-{secrets.token_hex(6)}@harness.invalid"
    password = "Hx" + secrets.token_hex(16) + "!9"
    forged_signup = pb._request("POST", "/api/collections/users/records", json_body={
        "email": email, "password": password, "passwordConfirm": password, "is_demo": True})
    c.check("admission.demo.no-demo-signup", forged_signup.status == 400, f"status={forged_signup.status}")
    for name_ in COLLECTIONS:
        listed = pb.listing(name_, a.token)
        anonymous = pb.listing(name_)
        c.check(f"admission.store.{name_}-superuser-only", listed.status == 403 and anonymous.status == 403,
                f"account={listed.status} anonymous={anonymous.status}")
    bare = call(POCKETBASE_URL, "POST", "/api/rounds/admission/admit", None, {"operation": "run", "wall_seconds": 3})
    c.check("admission.store.routes-need-a-bearer", bare[0] == 401, f"status={bare[0]}")

    print(f"admission check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
