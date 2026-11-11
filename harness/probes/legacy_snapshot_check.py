"""Harness checks for Legacy Artifact Snapshots (ROUNDS-00A-L04): creation
(PR 2) and server PDF on snapshot ids (PR 3), on the real PocketBase, both
runner replicas, nginx, the materializer, and the PDF renderer built from
this commit. Every account is generated for the run; between phases the
probe keeps only account emails, record ids, and correlation ids
(``/state/snapshot.json``, which never goes up with the receipts), and
signs back in with a password it derives from the run's test runner key.

Phases, in the order harness/run.sh runs them:

- ``snapshot-create``, gate on, materializer up: each RD-02 input, stored
  as an account's own resume, gets its declared outcome through nginx,
  and an ineligible one writes nothing; a created snapshot's markup
  hashes to its checksum, passes the output checks, and records its
  source; a replayed key returns the first answer and new key on the same
  inputs is ``reused``; a variant matching its parent's markup gets its
  own snapshot; a stale ``expected_updated`` is a conflict that writes
  nothing; another account's source answers exactly like a missing one,
  and nobody but the owner reads a snapshot or its file; a variant whose
  parent belongs to another account and the demo account get no
  snapshot.
- ``snapshot-render``, the renderer up: the owner gets a PDF of each of
  its snapshots through nginx; another account's snapshot answers exactly
  like a missing one, and so does a snapshot whose source was deleted; a
  checksum the snapshot doesn't hold, the request shape from before
  snapshots, and an anonymous caller are refused; a completed render's
  key doesn't run again, and another account's key on its own request is
  its own command. The isolation check writes its receipts for the case
  table (``RENDER_CASE``).
- ``snapshot-render-audit``, over the runners' decision lines run.sh
  saved: each refused render ended at its refusal before a slot ran, and
  the replicas answered exactly as many renders as the owner made, so no
  render ran without an owner-readable snapshot.
- ``snapshot-render-down``, the renderer stopped: a render is the typed
  503 with the renderer sentence and none of its text.
- ``snapshot-create-down``, the materializer stopped: creation answers
  503 ``materializer_unavailable`` and writes nothing, and a snapshot that
  exists still renders.
- ``snapshot-create-retry``, the materializer back: the same key runs
  again and makes exactly one snapshot.
- ``snapshot-scan``, over the reports run.sh saved: the scan is complete,
  its checksum holds, it counts every resume and variant, it names the
  materializer build the snapshots record, the signed copy carries the
  scan's signature, and a rescan with the gate off gives the same report.
- ``snapshot-create-off``, gate off: creation answers 503
  ``route_disabled``, and every snapshot still reads back and renders,
  owner only, with its checksum.
- ``snapshot-create-again``, gate on again: every snapshot's source gives
  ``reused`` with the same checksum; no resume, variant, or version row
  changed through any of it; deleting an account deletes its snapshots.
- ``snapshot-recovery``, after run.sh restored a ``pb_data`` backup taken
  with PocketBase stopped, its ``storage/`` included: every snapshot still
  renders for its owner with its checksum, and another account gets the
  404.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import factory
from admission_check import Checks, admin_token, call, uuid7
from pbclient import PBClient
from receipts import Receipt

POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://frontend").rstrip("/")
RUNNER_KEY = os.environ.get("ROUNDS_ADMISSION_SECRET", "")
RUN_ID = os.environ.get("RUN_ID", "local")
RD02_DIR = Path(os.environ.get("RD02_DIR", "/rd02"))
OUT = Path(os.environ.get("SNAPSHOT_OUT", "/out"))
STATE = Path(os.environ.get("SNAPSHOT_STATE_PATH", "/state/snapshot.json"))
# The runners' decision lines for the render route, saved by run.sh.
DECISIONS = Path(os.environ.get("SNAPSHOT_DECISIONS_PATH", "/state/render-decisions.jsonl"))
RECEIPTS_PATH = os.environ.get("RECEIPTS_PATH", "/out/receipts.jsonl")
ROUTE = "/api/pdf/snapshots"
RENDER = "/api/pdf/render"
SNAPSHOTS = "legacy_artifact_snapshots"
STALE = "2000-01-01 00:00:00.000Z"
MISSING_ID = "zzzzzzzzzzzzzz9"
SCAN_SCHEMA = "legacy-snapshot-scan/v1"
SCAN_LABEL = "rounds/legacy-snapshot-scan/v1"
# The case table's row this phase proves (docs/security/account-scope.v1.json).
RENDER_CASE = "isolation.render.snapshot.uniform-not-found"
# The runner's fixed sentences (backend/routers/pdf.py, backend/app/errors.py).
RENDERER_FAILED = "The PDF renderer couldn't finish this document. Try again shortly."
OUT_OF_DATE = "This page is out of date. Reload it to continue."
ENVELOPE = {"detail", "code", "correlation_id"}
RENDERER_TEXT = ("pdf-renderer", "Errno", "Traceback", "urlopen", "Connection refused", "puppeteer", "Chromium")


# ---- accounts ---------------------------------------------------------------

def password_for(tag: str) -> str:
    """The run's password for an account: derived, so no phase stores one."""
    digest = hmac.new(RUNNER_KEY.encode(), f"{RUN_ID}:{tag}".encode(), hashlib.sha256).hexdigest()
    return "Hx" + digest[:32] + "!9"


def new_account(pb: PBClient, tag: str) -> factory.Account:
    acct = factory.make_account(f"snap-{tag}")
    acct.password = password_for(tag)
    factory.register(pb, acct)
    return acct


def new_demo_account(pb: PBClient, admin: str) -> factory.Account:
    acct = factory.make_account("snap-demo")
    acct.password = password_for("demo")
    made = pb.create("users", admin, {"email": acct.email, "password": acct.password,
                                      "passwordConfirm": acct.password, "is_demo": True})
    if made.status != 200:
        raise RuntimeError(f"demo account create failed: status={made.status}")
    acct.user_id = made.body["id"]
    acct.token = pb.auth_password(acct.email, acct.password).body["token"]
    return acct


def sign_in(pb: PBClient, tag: str, email: str) -> str:
    auth = pb.auth_password(email, password_for(tag))
    if auth.status != 200:
        raise RuntimeError(f"sign-in {tag} failed: status={auth.status}")
    return auth.body["token"]


# ---- calls --------------------------------------------------------------------

def create(token: str, kind: str, source_id: str, updated: str, key: str | None = None) -> tuple[int, Any]:
    status, body, _ = call(FRONTEND_URL, "POST", ROUTE, token,
                           {"source_kind": kind, "source_id": source_id, "expected_updated": updated},
                           {"Idempotency-Key": key or uuid7()}, timeout=60)
    return status, body


def render_body(snapshot_id: str, checksum: str, key: str) -> dict[str, Any]:
    return {"snapshot_id": snapshot_id, "expected_checksum": checksum, "idempotency_id": key, "format": "pdf",
            "locale": "en", "page_size": "A4", "margin_mm": 0}


class Rendered:
    """One answer from the render route through nginx."""

    def __init__(self, status: int, raw: bytes, headers: dict[str, str]) -> None:
        self.status = status
        self.raw = raw
        self.headers = headers
        try:
            self.body: Any = json.loads(raw) if raw[:1] == b"{" else None
        except ValueError:
            self.body = None

    @property
    def pdf(self) -> bool:
        return (self.status == 200 and self.raw.startswith(b"%PDF-")
                and self.headers.get("content-type", "").startswith("application/pdf"))

    @property
    def code(self) -> str | None:
        return code_of(self.body)

    @property
    def correlation_id(self) -> str:
        return self.headers.get("x-correlation-id", "")

    def refusal(self) -> tuple[int, Any, Any]:
        return refusal(self.status, self.body)

    def typed(self) -> bool:
        """The typed envelope with nothing of the renderer's in it."""
        text = self.raw.decode("utf-8", "replace")
        return (isinstance(self.body, dict) and set(self.body) == ENVELOPE
                and not any(t in text for t in RENDERER_TEXT))


def render(token: str | None, snapshot_id: str, checksum: str, key: str | None = None,
           body: Any = None) -> Rendered:
    """POST /api/pdf/render through nginx; ``key`` goes as the
    Idempotency-Key and, unless ``body`` is given, as idempotency_id."""
    key = key or uuid7()
    payload = render_body(snapshot_id, checksum, key) if body is None else body
    headers = {"Content-Type": "application/json", "Idempotency-Key": key}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(FRONTEND_URL + RENDER, data=json.dumps(payload).encode(), method="POST",
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return Rendered(resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()})
    except urllib.error.HTTPError as err:
        return Rendered(err.code, err.read(), {k.lower(): v for k, v in (err.headers or {}).items()})


def record_render(state: dict, kind: str, answer: Rendered, expected_status: int, expected_code: str | None) -> None:
    """Notes a render's correlation id for snapshot-render-audit."""
    state.setdefault("renders", []).append({"kind": kind, "cid": answer.correlation_id,
                                            "status": expected_status, "code": expected_code})


def case_receipt(passed: bool, observed: int, detail: str) -> None:
    """One receipt for the case table's render row: no id, token, or body."""
    import run  # the probe runner's writer, with the run's context and redactor

    run.new_writer(RECEIPTS_PATH, "snapshot-render").write(
        Receipt(RENDER_CASE, "runner:render", "render", "authenticated-other", 404, observed, passed, 0,
                "" if passed else detail))


def code_of(body: Any) -> str | None:
    return body.get("code") if isinstance(body, dict) else None


def refusal(status: int, body: Any) -> tuple[int, Any, Any]:
    """What a refusal says, without its correlation id."""
    if not isinstance(body, dict):
        return status, None, None
    return status, body.get("code"), body.get("detail")


def rows(pb: PBClient, token: str, collection: str, flt: str = "") -> list[dict]:
    resp = pb.listing(collection, token, {"filter": flt} if flt else None)
    return list((resp.body or {}).get("items", [])) if resp.status == 200 else []


def snapshots_of(pb: PBClient, admin: str, user: str, source_id: str | None = None) -> list[dict]:
    flt = f"user = '{user}'" + (f" && source_id = '{source_id}'" if source_id else "")
    return rows(pb, admin, SNAPSHOTS, flt)


def recorded_rows(state: dict) -> int:
    """Every snapshot row the run made for account a: the ones it reads back
    and renders, and the ones kept after their source was deleted."""
    return len(state["snapshots"]) + len(state.get("kept_without_source", []))


def file_bytes(record: dict, token: str | None) -> tuple[int, bytes]:
    """The snapshot's markup file, read with a file token for `token`'s account."""
    query = ""
    if token:
        status, body, _ = call(POCKETBASE_URL, "POST", "/api/files/token", token, {})
        if status != 200 or not isinstance(body, dict):
            return status, b""
        query = "?token=" + urllib.parse.quote(body.get("token", ""))
    url = f"{POCKETBASE_URL}/api/files/{SNAPSHOTS}/{record.get('id', '')}/{urllib.parse.quote(record.get('markup', ''))}"
    try:
        with urllib.request.urlopen(url + query, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, b""


def sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def fingerprint(pb: PBClient, token: str) -> dict[str, str]:
    """Every resume, variant, and version row the account reads, by id, as
    a hash of the row; creation must never change one."""
    out: dict[str, str] = {}
    for collection in ("resumes", "resume_variants", "resume_versions"):
        for row in rows(pb, token, collection):
            out[f"{collection}/{row['id']}"] = hashlib.sha256(
                json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return out


def wait_frontend() -> None:
    """Until nginx answers, and the runner behind it: right after a restart,
    nginx and PocketBase can be up a moment before the runner is, and nginx
    answers the runner's routes 502 until then."""
    for _ in range(60):
        try:
            if call(FRONTEND_URL, "GET", "/api/health", timeout=3)[0] == 200 \
                    and call(FRONTEND_URL, "GET", ROUTE, timeout=3)[0] not in (502, 504):
                return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    raise RuntimeError("the frontend never answered /api/health and the runner's route")


def load_state() -> dict:
    return json.loads(STATE.read_text())


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def fixtures() -> list[dict]:
    found = []
    for path in sorted(RD02_DIR.glob("*.json")):
        doc = json.loads(path.read_text())
        found.append({"name": path.stem, "input": doc["input"], "expect": doc["expected"]})
    return found


def resume_from(pb: PBClient, acct: factory.Account, slug: str, given: dict) -> dict:
    made = pb.create("resumes", acct.token, {
        "user": acct.user_id, "name": slug, "slug": slug,
        "template_id": given.get("template_id") or "", "design": given.get("design"), "data": given.get("data"),
    })
    if made.status != 200 or not isinstance(made.body, dict):
        raise RuntimeError(f"resume {slug} create failed: status={made.status}")
    return made.body


# ---- phases -----------------------------------------------------------------------

def run_create(c: Checks) -> None:
    pb = PBClient(POCKETBASE_URL, timeout=30)
    admin = admin_token(pb)
    wait_frontend()
    a, b, gone = new_account(pb, "a"), new_account(pb, "b"), new_account(pb, "gone")
    demo = new_demo_account(pb, admin)
    state: dict[str, Any] = {"accounts": {"a": a.email, "b": b.email, "gone": gone.email, "demo": demo.email},
                             "ids": {"a": a.user_id, "b": b.user_id, "gone": gone.user_id, "demo": demo.user_id},
                             "snapshots": {}, "expected_ineligible": {}}

    # Each RD-02 input as the account's own resume.
    base = None
    for n, fx in enumerate(fixtures()):
        src = resume_from(pb, a, f"rd02-{n}", fx["input"])
        status, body = create(a.token, "resume", src["id"], src["updated"])
        want = fx["expect"]
        made = snapshots_of(pb, admin, a.user_id, src["id"])
        if want["status"] == "ineligible":
            c.check(f"snapshot.rd02.{fx['name']}.ineligible-and-nothing-written",
                    status == 200 and isinstance(body, dict) and body.get("status") == "ineligible"
                    and body.get("reason") == want["reason"] and body.get("snapshot_id") is None and not made,
                    f"status={status} reason={(body or {}).get('reason') if isinstance(body, dict) else None} "
                    f"rows={len(made)}")
            state["expected_ineligible"][want["reason"]] = state["expected_ineligible"].get(want["reason"], 0) + 1
            continue
        record = made[0] if len(made) == 1 else {}
        got, raw = file_bytes(record, a.token)
        text = raw.decode("utf-8", "replace")
        stored = json.dumps(record.get("data"))
        c.check(f"snapshot.rd02.{fx['name']}.created-with-its-declared-output",
                status == 201 and isinstance(body, dict) and body.get("status") == "created"
                and body.get("snapshot_id") == record.get("id") and got == 200
                and sha256(raw) == body.get("content_checksum") == record.get("content_checksum")
                and record.get("template_id") == want["template_id"]
                and record.get("template_fallback") is want["template_fallback"]
                and not any(s in text for s in want.get("markup_excludes", []))
                and not any(s in stored for s in want.get("data_excludes", [])),
                f"status={status} rows={len(made)} file={got}")
        if record:
            state["snapshots"][record["id"]] = {"tag": "a", "kind": "resume", "source": src["id"],
                                                "checksum": record.get("content_checksum")}
        if base is None and fx["input"].get("template_id") == "modern" and not want.get("template_fallback"):
            base = (src, body if isinstance(body, dict) else {})

    if base is None:
        c.check("snapshot.base-fixture", False, "no eligible modern fixture")
        return
    src, first = base
    rec = (snapshots_of(pb, admin, a.user_id, src["id"]) or [{}])[0]

    # The record carries its source; the owner reads it, nobody else does.
    c.check("snapshot.record.carries-its-source",
            rec.get("user") == a.user_id and rec.get("source_kind") == "resume" and rec.get("source_id") == src["id"]
            and rec.get("source_updated") == src["updated"] and rec.get("parent_id") == ""
            and str(rec.get("materializer_digest", "")).startswith("sha256:"), f"fields={sorted(rec)}")
    state["materializer_digest"] = rec.get("materializer_digest")
    other_view = pb.view(SNAPSHOTS, rec.get("id", MISSING_ID), b.token)
    other_list = [r["id"] for r in rows(pb, b.token, SNAPSHOTS)]
    anon_view = pb.view(SNAPSHOTS, rec.get("id", MISSING_ID), None)
    anon_list = rows(pb, "", SNAPSHOTS)
    other_file = file_bytes(rec, b.token)[0]
    anon_file = file_bytes(rec, None)[0]
    c.check("snapshot.read.only-the-owner",
            pb.view(SNAPSHOTS, rec.get("id", MISSING_ID), a.token).status == 200
            and other_view.status == 404 and rec.get("id") not in other_list
            and anon_view.status == 404 and not anon_list and other_file != 200 and anon_file != 200,
            f"other={other_view.status}/{other_file} anonymous={anon_view.status}/{anon_file}")

    # Replay, then the same inputs under a new key.
    key = uuid7()
    first_status, first_body = create(a.token, "resume", src["id"], src["updated"], key)
    again_status, again_body = create(a.token, "resume", src["id"], src["updated"], key)
    c.check("snapshot.replay.returns-the-first-answer",
            first_status == again_status == 200 and first_body == again_body
            and isinstance(first_body, dict) and first_body.get("status") == "reused",
            f"statuses={first_status}/{again_status}")
    c.check("snapshot.reuse.same-inputs-same-snapshot-and-checksum",
            isinstance(first_body, dict) and first_body.get("snapshot_id") == first.get("snapshot_id")
            and first_body.get("content_checksum") == first.get("content_checksum")
            and len(snapshots_of(pb, admin, a.user_id, src["id"])) == 1, f"body={first_body!r}"[:200])

    # A variant with its parent's data gets its own snapshot, same markup.
    variant = pb.create("resume_variants", a.token, {"user": a.user_id, "resume": src["id"], "name": "variant",
                                                    "data": src.get("data")})
    vbody: dict = {}
    if variant.status == 200:
        v_status, vbody = create(a.token, "variant", variant.body["id"], variant.body["updated"])
        vrec = (snapshots_of(pb, admin, a.user_id, variant.body["id"]) or [{}])[0]
        c.check("snapshot.variant.own-snapshot-with-its-parent",
                v_status == 201 and isinstance(vbody, dict) and vbody.get("snapshot_id") not in (None, rec.get("id"))
                and vbody.get("content_checksum") == rec.get("content_checksum")
                and vrec.get("source_kind") == "variant" and vrec.get("parent_id") == src["id"]
                and vrec.get("parent_updated") == src["updated"], f"status={v_status}")
        if vrec:
            state["snapshots"][vrec["id"]] = {"tag": "a", "kind": "variant", "source": variant.body["id"],
                                              "checksum": vrec.get("content_checksum")}
    else:
        c.check("snapshot.variant.own-snapshot-with-its-parent", False, f"variant create status={variant.status}")

    # A stale expected_updated is a conflict and writes nothing.
    before = len(snapshots_of(pb, admin, a.user_id))
    stale_status, stale_body = create(a.token, "resume", src["id"], STALE)
    c.check("snapshot.conflict.stale-updated-writes-nothing",
            stale_status == 409 and code_of(stale_body) == "snapshot_conflict"
            and len(snapshots_of(pb, admin, a.user_id)) == before, f"status={stale_status}")

    # Another account's source answers exactly like a missing one.
    foreign = create(b.token, "resume", src["id"], src["updated"])
    missing = create(b.token, "resume", MISSING_ID, src["updated"])
    c.check("snapshot.create.another-accounts-source-is-indistinguishable-from-missing",
            refusal(*foreign) == refusal(*missing) and foreign[0] == 404 and code_of(foreign[1]) == "not_found"
            and not snapshots_of(pb, admin, b.user_id), f"foreign={refusal(*foreign)} missing={refusal(*missing)}")

    # A variant whose parent is another account's gets no snapshot.
    crossed = pb.create("resume_variants", admin, {"user": b.user_id, "resume": src["id"], "name": "crossed",
                                                  "data": src.get("data")})
    if crossed.status == 200:
        x_status, x_body = create(b.token, "variant", crossed.body["id"], crossed.body["updated"])
        c.check("snapshot.variant.foreign-parent-gets-no-snapshot",
                x_status == 200 and isinstance(x_body, dict) and x_body.get("status") == "ineligible"
                and x_body.get("reason") == "parent_invalid" and not snapshots_of(pb, admin, b.user_id),
                f"status={x_status}")
        # The cross-owner row goes again, so the later relation scans see
        # only their own fixtures.
        pb.delete("resume_variants", crossed.body["id"], admin)
    else:
        c.check("snapshot.variant.foreign-parent-gets-no-snapshot", crossed.status in (400, 403, 404),
                f"the store refused the variant with status={crossed.status}")

    # The demo account gets no snapshot.
    demo_src = resume_from(pb, demo, "demo-resume", {"template_id": "modern", "design": {}, "data": src.get("data")})
    d_status, d_body = create(demo.token, "resume", demo_src["id"], demo_src["updated"])
    c.check("snapshot.demo-account.no-snapshot",
            d_status == 200 and isinstance(d_body, dict) and d_body.get("reason") == "demo_account"
            and not snapshots_of(pb, admin, demo.user_id), f"status={d_status}")
    state["expected_ineligible"]["demo_account"] = state["expected_ineligible"].get("demo_account", 0) + 1

    # A source with no snapshot yet, for the outage phases.
    pending = resume_from(pb, a, "pending", {"template_id": "classic", "design": {}, "data": src.get("data")})
    state["pending"] = {"source": pending["id"], "updated": pending["updated"], "key": uuid7()}

    # An account whose deletion the last phase checks.
    gone_src = resume_from(pb, gone, "gone-resume", {"template_id": "modern", "design": {}, "data": src.get("data")})
    g_status, _ = create(gone.token, "resume", gone_src["id"], gone_src["updated"])
    c.check("snapshot.second-account.creates-its-own", g_status == 201 and len(snapshots_of(pb, admin, gone.user_id)) == 1,
            f"status={g_status}")

    # Reconciliation: every stored snapshot hashes to its checksum and
    # matches its source's owner and updated.
    mismatched = []
    for row in snapshots_of(pb, admin, a.user_id):
        collection = "resumes" if row.get("source_kind") == "resume" else "resume_variants"
        source = pb.view(collection, row.get("source_id", ""), a.token).body or {}
        raw = file_bytes(row, a.token)[1]
        parent_ok = (row.get("parent_id") == "" or
                     (pb.view("resumes", row["parent_id"], a.token).body or {}).get("updated") == row.get("parent_updated"))
        if not (sha256(raw) == row.get("content_checksum") and source.get("user") == row.get("user") == a.user_id
                and source.get("updated") == row.get("source_updated") and parent_ok):
            mismatched.append(row.get("id"))
    c.check("snapshot.reconcile.checksums-owners-and-sources", not mismatched and bool(state["snapshots"]),
            f"mismatched={len(mismatched)}")

    state["fingerprints"] = {tag: fingerprint(pb, acct.token) for tag, acct in
                             (("a", a), ("b", b), ("demo", demo))}
    state["sources"] = {"resumes": count(pb, admin, "resumes"),
                        "variants": count(pb, admin, "resume_variants")}
    save_state(state)


def renders_for_owner(state: dict, token: str, other: str | None = None) -> tuple[list[str], list[str]]:
    """Every recorded snapshot rendered by its owner, and by ``other`` when
    given: the ids that didn't give the owner a PDF, and the ids another
    account got anything but the 404 from."""
    failed, leaked = [], []
    for snap_id, want in state["snapshots"].items():
        mine = render(token, snap_id, want["checksum"])
        if mine.pdf:
            record_render(state, "owner", mine, 200, None)
        else:
            failed.append(snap_id)
        if other is not None:
            theirs = render(other, snap_id, want["checksum"])
            record_render(state, "foreign", theirs, 404, "not_found")
            if (theirs.status, theirs.code) != (404, "not_found"):
                leaked.append(snap_id)
    return failed, leaked


def run_render(c: Checks) -> None:
    pb = PBClient(POCKETBASE_URL, timeout=30)
    admin = admin_token(pb)
    wait_frontend()
    state = load_state()
    state["renders"] = []
    tokens = {tag: sign_in(pb, tag, state["accounts"][tag]) for tag in ("a", "b")}
    a, b = tokens["a"], tokens["b"]

    # The owner gets a PDF of each of its snapshots, the variant's included.
    failed, _ = renders_for_owner(state, a)
    c.check("render.owner.pdf-of-each-snapshot", not failed and bool(state["snapshots"]), f"failed={len(failed)}")

    # Another account's snapshot, named with its own checksum, answers
    # exactly like a missing one, and neither renders.
    snap_id, want = next(iter(state["snapshots"].items()))
    foreign = render(b, snap_id, want["checksum"])
    missing = render(b, MISSING_ID, want["checksum"])
    record_render(state, "foreign", foreign, 404, "not_found")
    record_render(state, "missing", missing, 404, "not_found")
    same = foreign.refusal() == missing.refusal() and (foreign.status, foreign.code) == (404, "not_found")
    c.check("render.another-accounts-snapshot-is-indistinguishable-from-missing",
            same and not foreign.pdf and not missing.pdf, f"foreign={foreign.refusal()} missing={missing.refusal()}")
    case_receipt(same and not foreign.pdf, foreign.status, f"foreign={foreign.status}/{foreign.code}")

    # A checksum the snapshot doesn't hold is refused before any render.
    wrong = render(a, snap_id, "sha256:" + "0" * 64)
    record_render(state, "checksum", wrong, 409, "checksum_mismatch")
    c.check("render.another-checksum-is-refused", (wrong.status, wrong.code) == (409, "checksum_mismatch")
            and wrong.typed(), f"status={wrong.status} code={wrong.code}")

    # The request shape from before snapshots asks the page to reload, and
    # nothing renders.
    for name, old in (("markup", {"html": "<p>harness</p>"}), ("markup-and-margin", {"html": "<p>x</p>", "margin_mm": 5})):
        stale = render(a, snap_id, want["checksum"], body=old)
        record_render(state, "legacy", stale, 422, "legacy_request_rejected")
        c.check(f"render.older-request-shape.{name}.reload",
                (stale.status, stale.code) == (422, "legacy_request_rejected") and stale.typed()
                and isinstance(stale.body, dict) and stale.body.get("detail") == OUT_OF_DATE,
                f"status={stale.status} code={stale.code}")

    # Anonymous: refused before anything is read.
    anonymous = render(None, snap_id, want["checksum"])
    c.check("render.anonymous.unauthenticated", (anonymous.status, anonymous.code) == (401, "unauthenticated"),
            f"status={anonymous.status}")

    # A completed render's key doesn't render again; another account's
    # key on its own request is that account's own command.
    key = uuid7()
    first = render(a, snap_id, want["checksum"], key=key)
    again = render(a, snap_id, want["checksum"], key=key)
    reused = render(b, snap_id, want["checksum"], key=key)
    if first.pdf:
        record_render(state, "owner", first, 200, None)
    record_render(state, "replay", again, 409, "already_completed")
    record_render(state, "foreign", reused, 404, "not_found")
    c.check("render.replay.completed-render-runs-once",
            first.pdf and (again.status, again.code) == (409, "already_completed"), f"statuses={first.status}/{again.status}")
    c.check("render.replay.another-accounts-key-is-its-own-command",
            (reused.status, reused.code) == (404, "not_found") and not reused.pdf, f"status={reused.status}")

    # A snapshot whose source was deleted answers the same 404.
    acct_id = state["ids"]["a"]
    content = {"personalInfo": {"fullName": "Render check"}, "experience": [], "education": [], "skills": [],
               "projects": [], "publications": [], "profiles": []}
    gone = resume_from(pb, factory.Account(tag="a", email=state["accounts"]["a"], password="", user_id=acct_id,
                                           token=a),
                       "render-gone", {"template_id": "modern", "design": {}, "data": content})
    status, body = create(a, "resume", gone["id"], gone["updated"])
    if status == 201 and isinstance(body, dict):
        # Its row stays after the source goes, as the spec keeps such rows,
        # so the later row counts include it.
        state.setdefault("kept_without_source", []).append(body["snapshot_id"])
        deleted = pb.delete("resumes", gone["id"], a)
        after = render(a, body["snapshot_id"], body["content_checksum"])
        record_render(state, "source-gone", after, 404, "not_found")
        c.check("render.source-deleted.not-found", deleted.status == 204 and (after.status, after.code) == (404, "not_found")
                and snapshots_of(pb, admin, acct_id, gone["id"]) != [], f"delete={deleted.status} render={after.status}")
    else:
        c.check("render.source-deleted.not-found", False, f"snapshot create status={status}")
    save_state(state)


def run_render_audit(c: Checks) -> None:
    """The decision lines both replicas wrote for the render route since
    they started: each refusal ended there, before a slot ran, and only the
    owner's renders answered 200."""
    state = load_state()
    lines = []
    for raw in DECISIONS.read_text().splitlines() if DECISIONS.exists() else []:
        try:
            line = json.loads(raw)
        except ValueError:
            continue
        if line.get("event") == "decision" and line.get("route") == RENDER:
            lines.append(line)
    by_cid = {line.get("correlation_id"): line for line in lines}
    missing, wrong = [], []
    for made in state.get("renders", []):
        line = by_cid.get(made["cid"])
        if line is None:
            missing.append(made["kind"])
            continue
        if made["status"] == 200:
            ok = line.get("status") == 200
        else:
            # Refused at step 5 (no charge) or step 8 (refunded): never a slot.
            ok = (line.get("status"), line.get("code")) == (made["status"], made["code"]) and \
                line.get("quota") in ("skipped", "refunded")
        if not ok:
            wrong.append(made["kind"])
    c.check("render.audit.every-refusal-ended-before-a-slot", bool(lines) and not missing and not wrong,
            f"lines={len(lines)} missing={missing} wrong={wrong}")
    owner = sum(1 for made in state.get("renders", []) if made["status"] == 200)
    rendered = sum(1 for line in lines if line.get("status") == 200)
    c.check("render.audit.no-render-without-an-owner-readable-snapshot", owner > 0 and rendered == owner,
            f"owner_renders={owner} answered_200={rendered}")


def run_render_down(c: Checks) -> None:
    pb = PBClient(POCKETBASE_URL, timeout=30)
    wait_frontend()
    state = load_state()
    token = sign_in(pb, "a", state["accounts"]["a"])
    snap_id, want = next(iter(state["snapshots"].items()))
    down = render(token, snap_id, want["checksum"])
    c.check("render.renderer-down.typed-503-without-its-text",
            (down.status, down.code) == (503, "worker_unavailable") and down.typed()
            and isinstance(down.body, dict) and down.body.get("detail") == RENDERER_FAILED,
            f"status={down.status} code={down.code}")


def count(pb: PBClient, admin: str, collection: str) -> int:
    resp = pb.listing(collection, admin, {"perPage": 1})
    return int((resp.body or {}).get("totalItems", -1)) if resp.status == 200 else -1


def run_down(c: Checks) -> None:
    pb = PBClient(POCKETBASE_URL, timeout=30)
    admin = admin_token(pb)
    state = load_state()
    token = sign_in(pb, "a", state["accounts"]["a"])
    p = state["pending"]
    status, body = create(token, "resume", p["source"], p["updated"], p["key"])
    c.check("snapshot.outage.materializer-down-is-typed-and-writes-nothing",
            status == 503 and code_of(body) == "materializer_unavailable"
            and not snapshots_of(pb, admin, state["ids"]["a"], p["source"]), f"status={status} code={code_of(body)}")
    # A snapshot that exists renders without the materializer.
    snap_id, want = next(iter(state["snapshots"].items()))
    c.check("render.outage.materializer-down-still-renders", render(token, snap_id, want["checksum"]).pdf,
            "no PDF")


def run_retry(c: Checks) -> None:
    pb = PBClient(POCKETBASE_URL, timeout=30)
    admin = admin_token(pb)
    state = load_state()
    token = sign_in(pb, "a", state["accounts"]["a"])
    p = state["pending"]
    status, body = create(token, "resume", p["source"], p["updated"], p["key"])
    replay = create(token, "resume", p["source"], p["updated"], p["key"])
    made = snapshots_of(pb, admin, state["ids"]["a"], p["source"])
    c.check("snapshot.outage.same-key-retry-makes-one-snapshot",
            status == 201 and isinstance(body, dict) and body.get("status") == "created" and len(made) == 1
            and replay == (status, body), f"status={status} rows={len(made)}")
    if made:
        state["snapshots"][made[0]["id"]] = {"tag": "a", "kind": "resume", "source": p["source"],
                                             "checksum": made[0].get("content_checksum")}
        save_state(state)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def run_scan(c: Checks) -> None:
    state = load_state()
    reports = {}
    for name in ("scan-1", "scan-1.signed", "scan-2"):
        try:
            reports[name] = json.loads((OUT / f"{name}.json").read_text())
        except (OSError, ValueError):
            reports[name] = {}
    first, signed, second = reports["scan-1"], reports["scan-1.signed"], reports["scan-2"]
    body = {k: v for k, v in first.items() if k != "checksum"}
    c.check("snapshot.scan.report-is-complete-and-its-checksum-holds",
            first.get("schema") == SCAN_SCHEMA and first.get("complete") is True
            and first.get("checksum") == "sha256:" + hashlib.sha256(canonical(body)).hexdigest(),
            f"schema={first.get('schema')} complete={first.get('complete')}")
    totals = first.get("totals") or {}
    by_reason = first.get("by_reason") or {}
    c.check("snapshot.scan.counts-every-source-and-each-ineligible-fixture",
            totals.get("resumes") == state["sources"]["resumes"] and totals.get("variants") == state["sources"]["variants"]
            and totals.get("sources") == totals.get("resumes", 0) + totals.get("variants", 0)
            and totals.get("unavailable") == 0
            and all(by_reason.get(reason, 0) >= n for reason, n in state["expected_ineligible"].items()),
            f"totals={totals}")
    c.check("snapshot.scan.names-the-build-the-snapshots-record",
            first.get("materializer_digest") == state.get("materializer_digest"), "digest differs")
    leaked = [v for v in list(state["ids"].values()) + list(state["accounts"].values()) if v in json.dumps(first)]
    c.check("snapshot.scan.report-holds-no-id-or-email", bool(first) and not leaked, f"leaked={len(leaked)}")
    sig = signed.get("signature") or {}
    c.check("snapshot.scan.signed-under-the-scan-label",
            {k: v for k, v in signed.items() if k != "signature"} == first
            and sig.get("alg") == "HMAC-SHA256" and sig.get("key") == SCAN_LABEL
            and isinstance(sig.get("value"), str) and len(sig["value"]) == 64, f"signature={sorted(sig)}")
    c.check("snapshot.scan.rescan-gives-the-same-report", bool(second) and second == first,
            f"checksums={first.get('checksum')}/{second.get('checksum')}")


def run_off(c: Checks) -> None:
    pb = PBClient(POCKETBASE_URL, timeout=30)
    admin = admin_token(pb)
    wait_frontend()
    state = load_state()
    tokens = {tag: sign_in(pb, tag, state["accounts"][tag]) for tag in ("a", "b")}
    any_id = next(iter(state["snapshots"].values()))
    collection = "resumes" if any_id["kind"] == "resume" else "resume_variants"
    source = pb.view(collection, any_id["source"], tokens["a"]).body or {}
    status, body = create(tokens["a"], any_id["kind"], any_id["source"], source.get("updated", STALE))
    c.check("snapshot.gate-off.route-disabled", status == 503 and code_of(body) == "route_disabled",
            f"status={status} code={code_of(body)}")
    unreadable = []
    for snap_id, want in state["snapshots"].items():
        own = pb.view(SNAPSHOTS, snap_id, tokens["a"])
        raw = file_bytes(own.body or {}, tokens["a"])[1] if own.status == 200 else b""
        if own.status != 200 or sha256(raw) != want["checksum"] or pb.view(SNAPSHOTS, snap_id, tokens["b"]).status != 404:
            unreadable.append(snap_id)
    c.check("snapshot.gate-off.snapshots-still-read-back-owner-only", not unreadable, f"failed={len(unreadable)}")
    # Creation off doesn't stop server PDF for snapshots that exist: each
    # still renders for its owner, and only for its owner.
    failed, leaked = renders_for_owner(state, tokens["a"], tokens["b"])
    c.check("render.gate-off.snapshots-still-render-owner-only", not failed and not leaked,
            f"failed={len(failed)} leaked={len(leaked)}")
    c.check("snapshot.gate-off.no-source-row-changed",
            fingerprint(pb, tokens["a"]) == state["fingerprints"]["a"]
            and fingerprint(pb, tokens["b"]) == state["fingerprints"]["b"], "a source row changed")
    c.check("snapshot.gate-off.nothing-written",
            len(snapshots_of(pb, admin, state["ids"]["a"])) == recorded_rows(state), "row count changed")


def run_again(c: Checks) -> None:
    pb = PBClient(POCKETBASE_URL, timeout=30)
    admin = admin_token(pb)
    wait_frontend()
    state = load_state()
    token = sign_in(pb, "a", state["accounts"]["a"])
    differed = []
    # Each differing answer's status and kind or code, never an id.
    answers: dict[str, int] = {}
    for snap_id, want in state["snapshots"].items():
        collection = "resumes" if want["kind"] == "resume" else "resume_variants"
        source = pb.view(collection, want["source"], token).body or {}
        status, body = create(token, want["kind"], want["source"], source.get("updated", STALE))
        if not (status == 200 and isinstance(body, dict) and body.get("status") == "reused"
                and body.get("snapshot_id") == snap_id and body.get("content_checksum") == want["checksum"]):
            differed.append(snap_id)
            kind = (body.get("status") or code_of(body)) if isinstance(body, dict) else None
            same = isinstance(body, dict) and body.get("snapshot_id") == snap_id
            label = f"{status}:{kind}:{'same-id' if same else 'other-id'}"
            answers[label] = answers.get(label, 0) + 1
    c.check("snapshot.forward-again.every-snapshot-reused-with-its-checksum",
            not differed and bool(state["snapshots"]),
            f"differed={len(differed)} answers={','.join(f'{k}x{v}' for k, v in sorted(answers.items()))}")
    c.check("snapshot.forward-again.no-source-row-changed",
            fingerprint(pb, token) == state["fingerprints"]["a"], "a source row changed")
    gone = state["ids"]["gone"]
    deleted = pb.delete("users", gone, admin)
    c.check("snapshot.account-deletion.removes-its-snapshots",
            deleted.status == 204 and not snapshots_of(pb, admin, gone), f"status={deleted.status}")


def run_recovery(c: Checks) -> None:
    """After run.sh restored the backup it took with PocketBase stopped:
    every snapshot reads back and renders for its owner with the checksum
    it had, its file hashes to it, and another account gets the 404."""
    pb = PBClient(POCKETBASE_URL, timeout=30)
    wait_frontend()
    state = load_state()
    tokens = {tag: sign_in(pb, tag, state["accounts"][tag]) for tag in ("a", "b")}
    changed = []
    for snap_id, want in state["snapshots"].items():
        own = pb.view(SNAPSHOTS, snap_id, tokens["a"])
        raw = file_bytes(own.body or {}, tokens["a"])[1] if own.status == 200 else b""
        if own.status != 200 or (own.body or {}).get("content_checksum") != want["checksum"] or sha256(raw) != want["checksum"]:
            changed.append(snap_id)
    c.check("recovery.snapshots-restored-with-their-checksums", not changed and bool(state["snapshots"]),
            f"changed={len(changed)}")
    failed, leaked = renders_for_owner(state, tokens["a"], tokens["b"])
    c.check("recovery.snapshots-render-for-their-owner-only", not failed and not leaked,
            f"failed={len(failed)} leaked={len(leaked)}")


PHASES = {
    "snapshot-create": run_create,
    "snapshot-render": run_render,
    "snapshot-render-audit": run_render_audit,
    "snapshot-render-down": run_render_down,
    "snapshot-create-down": run_down,
    "snapshot-create-retry": run_retry,
    "snapshot-scan": run_scan,
    "snapshot-create-off": run_off,
    "snapshot-create-again": run_again,
    "snapshot-recovery": run_recovery,
}


def main(phase: str) -> int:
    c = Checks()
    if len(RUNNER_KEY) < 32:
        c.check("snapshot.runner-key-configured", False, "the harness passes its test runner key")
        return 1
    try:
        PHASES[phase](c)
    except Exception as err:  # noqa: BLE001 - a crash is one failed check, with its type only
        c.check(f"{phase}.ran", False, type(err).__name__)
    print(f"{phase}: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
