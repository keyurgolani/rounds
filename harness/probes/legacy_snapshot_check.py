"""Harness checks for Legacy Artifact Snapshot creation (ROUNDS-00A-L04
PR 2), on the real PocketBase, both runner replicas, nginx, and the
materializer built from this commit. Every account is generated for the
run; between phases the probe keeps only account emails and record ids
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
- ``snapshot-create-down``, the materializer stopped: creation answers
  503 ``materializer_unavailable`` and writes nothing.
- ``snapshot-create-retry``, the materializer back: the same key runs
  again and makes exactly one snapshot.
- ``snapshot-scan``, over the reports run.sh saved: the scan is complete,
  its checksum holds, it counts every resume and variant, it names the
  materializer build the snapshots record, the signed copy carries the
  scan's signature, and a rescan with the gate off gives the same report.
- ``snapshot-create-off``, gate off: creation answers 503
  ``route_disabled``, and every snapshot still reads back, owner only,
  with its checksum.
- ``snapshot-create-again``, gate on again: every snapshot's source gives
  ``reused`` with the same checksum; no resume, variant, or version row
  changed through any of it; deleting an account deletes its snapshots.

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

POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://frontend").rstrip("/")
RUNNER_KEY = os.environ.get("ROUNDS_ADMISSION_SECRET", "")
RUN_ID = os.environ.get("RUN_ID", "local")
RD02_DIR = Path(os.environ.get("RD02_DIR", "/rd02"))
OUT = Path(os.environ.get("SNAPSHOT_OUT", "/out"))
STATE = Path(os.environ.get("SNAPSHOT_STATE_PATH", "/state/snapshot.json"))
ROUTE = "/api/pdf/snapshots"
SNAPSHOTS = "legacy_artifact_snapshots"
STALE = "2000-01-01 00:00:00.000Z"
MISSING_ID = "zzzzzzzzzzzzzz9"
SCAN_SCHEMA = "legacy-snapshot-scan/v1"
SCAN_LABEL = "rounds/legacy-snapshot-scan/v1"


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
    for _ in range(60):
        try:
            if call(FRONTEND_URL, "GET", "/api/health", timeout=3)[0] == 200:
                return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    raise RuntimeError("the frontend never answered /api/health")


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
    c.check("snapshot.gate-off.no-source-row-changed",
            fingerprint(pb, tokens["a"]) == state["fingerprints"]["a"]
            and fingerprint(pb, tokens["b"]) == state["fingerprints"]["b"], "a source row changed")
    c.check("snapshot.gate-off.nothing-written",
            len(snapshots_of(pb, admin, state["ids"]["a"])) == len(state["snapshots"]), "row count changed")


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


PHASES = {
    "snapshot-create": run_create,
    "snapshot-create-down": run_down,
    "snapshot-create-retry": run_retry,
    "snapshot-scan": run_scan,
    "snapshot-create-off": run_off,
    "snapshot-create-again": run_again,
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
