"""Self-tests for the two-account isolation suite's harness parts
(ROUNDS-00B-L05): the case table's validation, the verdict's case rules
(unexpected pass, expired row, zero receipts, pending and slot rows), the
response comparator, the recording proxy's auth classifier and log line,
the receipt redactor, and the log scanner.

These run in the backend gate via ``pytest ../pocketbase/tests``; the
suite's probes run in the harness stack in CI.
"""
from __future__ import annotations

import base64
import datetime
import http.client
import json
import sqlite3
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROBES = ROOT / "harness" / "probes"
sys.path.insert(0, str(PROBES))

import compare  # noqa: E402
import logscan  # noqa: E402
import policy  # noqa: E402
import recorder  # noqa: E402
import run  # noqa: E402
from pbclient import Response  # noqa: E402
from receipts import Receipt, ReceiptWriter, Redactor, read_all  # noqa: E402

POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"
ENFORCED = "account-scope.view.cross-account.denied"
TODAY = datetime.date(2026, 11, 11)

# Test placeholders shaped like what the harness issues; not real secrets.
PLANTED_PASSWORD = "Hx" + "0123456789abcdef" * 2 + "!9"


def _jwt(payload: dict) -> str:
    def seg(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")

    return f"{seg({'alg': 'HS256', 'typ': 'JWT'})}.{seg(payload)}.c2lnbmF0dXJlLXBsYWNlaG9sZGVy"


USER_TOKEN = _jwt({"id": "u1", "type": "authRecord", "collectionId": "_pb_users_auth_", "exp": 1})
ADMIN_TOKEN = _jwt({"id": "x1", "type": "admin", "exp": 1})
SERVICE_TOKEN = _jwt({"id": "s1", "type": "authRecord", "collectionId": "pbc_service0000", "exp": 1})


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def case(status: str = "pass", **over) -> dict:
    row = {
        "surface": "runner:providers",
        "actor": "authenticated-other",
        "variant": "foreign_owner",
        "expected": "uniform_not_found",
        "control": "the owner's own id",
        "owner_leaf": "ROUNDS-00B-L05" if status in ("pass", "quarantined") else "ROUNDS-00B-L04",
        "status": status,
        "lane": "pr",
        "guarantee": "foreign and missing answer alike",
    }
    if status == "pass":
        row["evidence"] = ["isolation.case.one"]
    if status == "quarantined":
        row.update(evidence=["campaigns:isolation.case.one"], quarantined_on="2026-11-05", expires="2026-11-15")
    row.update(over)
    return row


def doc_with(cases: dict) -> dict:
    return {
        "version": "v1",
        "contract": "account-scope",
        "deny_contract": {"view": {"status": 404}},
        "probe_families": {ENFORCED: {"status": "enforced", "deny_key": "view"}},
        "collections": {"campaigns": {"current_rules": {"list": "user = @request.auth.id"}, "probes": [ENFORCED]}},
        "cases": cases,
    }


def rcpt(probe_id: str, passed: bool = True, collection: str = "campaigns") -> dict:
    return {"probe_id": probe_id, "collection": collection, "operation": "view", "actor": "authenticated-other",
            "expected_status": 404, "observed_status": 404 if passed else 200, "passed": passed,
            "request_time_ms": 1}


def baseline() -> list[dict]:
    return [rcpt(ENFORCED), rcpt(run.READBACK_PROBE)]


def verdict(tmp_path: Path, doc: dict, rows: list[dict]) -> int:
    path = tmp_path / "r.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return run.run_verdict(doc, str(path), today=TODAY)


def load(tmp_path: Path, doc: dict) -> dict:
    p = tmp_path / "policy.json"
    p.write_text(json.dumps(doc))
    return policy.load(str(p))


# --------------------------------------------------------------------------
# the case table
# --------------------------------------------------------------------------


def test_committed_case_table_loads():
    doc = policy.load(str(POLICY))
    cases = doc["cases"]
    assert cases, "the committed policy has a case table"
    # Every row the suite doesn't prove yet names the leaf that will.
    for cid, row in cases.items():
        if row["status"] in ("pending", "slot"):
            assert row["owner_leaf"] != policy.CASE_LEAF, cid
    # The two open exceptions moved to the relation leaf, each with its row.
    exceptions = {e["id"]: e for e in doc["open_exceptions"]}
    for eid in ("owner-id-create-shape", "client-chosen-record-id"):
        assert exceptions[eid]["closed_by"] == "ROUNDS-00B-L02"
        assert cases[exceptions[eid]["case"]]["status"] == "pending"
        assert cases[exceptions[eid]["case"]]["owner_leaf"] == "ROUNDS-00B-L02"


def test_committed_pass_rows_name_checks_a_run_reports():
    doc = policy.load(str(POLICY))
    known = (run.families.IMPLEMENTED_FAMILIES | set(doc["deployment_checks"]))
    for cid, row in policy.cases_by_status(doc, "pass").items():
        for e in row["evidence"]:
            kind, ident, target = policy.parse_evidence(e)
            assert kind == "phase" or ident in known or ident == cid, (cid, e)
            if target is not None:
                assert ident in doc["collections"][target]["probes"], (cid, e)


def test_committed_share_rows_count_only_their_collection():
    doc = policy.load(str(POLICY))
    for cid in ("isolation.share-views.client-write.denied", "isolation.share-link.owner-only.isolated"):
        for e in doc["cases"][cid]["evidence"]:
            assert policy.parse_evidence(e)[2] is not None, (cid, e)


def test_committed_pending_and_slot_rows_have_no_probe():
    doc = policy.load(str(POLICY))
    for status in ("pending", "slot"):
        for cid in policy.cases_by_status(doc, status):
            assert cid not in run.families.IMPLEMENTED_FAMILIES, cid


@pytest.mark.parametrize("change, message", [
    ({"status": "maybe"}, "unknown status"),
    ({"surface": "ftp:/x"}, "unknown surface"),
    ({"expected": "probably"}, "unknown expected outcome"),
    ({"lane": "nightly"}, "unknown lane"),
    ({"control": ""}, "missing control"),
    ({"evidence": []}, "names no evidence"),
    ({"evidence": ["phase:nope"]}, "unknown evidence phase"),
    ({"expires": "soon"}, "not an ISO date"),
])
def test_load_rejects_a_bad_pass_row(tmp_path, change, message):
    with pytest.raises(policy.PolicyError, match=message):
        load(tmp_path, doc_with({"isolation.case.one": case(**change)}))


def test_load_takes_absent_for_a_value_that_must_never_appear(tmp_path):
    # ROUNDS-00B-L04's log rows: the row's value is absent where it looks.
    doc = load(tmp_path, doc_with({"isolation.case.one": case(surface="logs:share-secrets", expected="absent")}))
    assert doc["cases"]["isolation.case.one"]["expected"] == "absent"
    assert verdict(tmp_path, doc, baseline() + [rcpt("isolation.case.one", collection="logs:share")]) == 0
    assert verdict(tmp_path, doc, baseline() + [rcpt("isolation.case.one", False, "logs:share")]) == 1
    with pytest.raises(policy.PolicyError, match="unknown expected outcome"):
        load(tmp_path, doc_with({"isolation.case.one": case(expected="absent_or_not")}))


def test_load_rejects_a_pending_row_with_evidence_or_without_another_leaf(tmp_path):
    with pytest.raises(policy.PolicyError, match="must carry no evidence"):
        load(tmp_path, doc_with({"isolation.case.one": case("pending", evidence=["x"])}))
    with pytest.raises(policy.PolicyError, match="must name the leaf"):
        load(tmp_path, doc_with({"isolation.case.one": case("slot", owner_leaf=policy.CASE_LEAF)}))


def test_load_rejects_a_quarantine_longer_than_fourteen_days_or_without_dates(tmp_path):
    with pytest.raises(policy.PolicyError, match="within 14 days"):
        load(tmp_path, doc_with({"isolation.case.one": case("quarantined", expires="2026-11-30")}))
    row = case("quarantined")
    del row["quarantined_on"]
    with pytest.raises(policy.PolicyError, match="without quarantined_on"):
        load(tmp_path, doc_with({"isolation.case.one": row}))


def test_load_rejects_a_pending_family_named_as_evidence(tmp_path):
    d = doc_with({"isolation.case.one": case(evidence=["account-scope.synthetic.pending"])})
    d["probe_families"]["account-scope.synthetic.pending"] = {"status": "pending", "deny_key": "view"}
    with pytest.raises(policy.PolicyError, match="pending family"):
        load(tmp_path, d)


@pytest.mark.parametrize("cases", [None, {}])
def test_load_rejects_a_missing_or_empty_case_table(tmp_path, cases):
    d = doc_with(cases)
    if cases is None:
        del d["cases"]
    with pytest.raises(policy.PolicyError, match="no case table"):
        load(tmp_path, d)


def test_load_rejects_an_unknown_key(tmp_path):
    with pytest.raises(policy.PolicyError, match="unknown keys expiry"):
        load(tmp_path, doc_with({"isolation.case.one": case(expiry="2026-11-20")}))


@pytest.mark.parametrize("evidence", [
    [f"campaigns:{ENFORCED}"],
    ["campaigns:deployment.rules.match"],
    ["phase:demo-on"],
    ["isolation.case.one"],
])
def test_load_rejects_a_quarantine_over_shared_checks_or_without_a_target(tmp_path, evidence):
    d = doc_with({"isolation.case.one": case("quarantined", evidence=evidence)})
    d["deployment_checks"] = {"deployment.rules.match": {}}
    with pytest.raises(policy.PolicyError, match="can't cover|must name the target"):
        load(tmp_path, d)


def test_load_rejects_a_check_that_backs_a_pass_and_a_quarantined_row(tmp_path):
    d = doc_with({"isolation.case.one": case(evidence=["isolation.case.x"]),
                  "isolation.case.two": case("quarantined", evidence=["campaigns:isolation.case.x"])})
    with pytest.raises(policy.PolicyError, match="both a pass and a quarantined row"):
        load(tmp_path, d)


def test_load_rejects_a_pending_id_another_check_uses(tmp_path):
    d = doc_with({ENFORCED: case("pending")})
    with pytest.raises(policy.PolicyError, match="uses the id of an existing check"):
        load(tmp_path, d)
    d = doc_with({"isolation.case.one": case(evidence=["isolation.case.two"]),
                  "isolation.case.two": case("slot")})
    with pytest.raises(policy.PolicyError, match="named as another row's evidence"):
        load(tmp_path, d)


def test_load_rejects_scoped_evidence_on_a_collection_that_doesnt_run_it(tmp_path):
    with pytest.raises(policy.PolicyError, match="doesn't run"):
        load(tmp_path, doc_with({"isolation.case.one": case(evidence=[f"offers:{ENFORCED}"])}))
    assert load(tmp_path, doc_with({"isolation.case.one": case(evidence=[f"campaigns:{ENFORCED}"])}))


# --------------------------------------------------------------------------
# the verdict's case rules
# --------------------------------------------------------------------------


def test_verdict_passes_a_pass_row_with_passing_receipts(tmp_path):
    d = doc_with({"isolation.case.one": case()})
    assert verdict(tmp_path, d, baseline() + [rcpt("isolation.case.one")]) == 0


def test_verdict_fails_a_pass_row_without_receipts_or_with_a_failure(tmp_path):
    d = doc_with({"isolation.case.one": case()})
    assert verdict(tmp_path, d, baseline()) == 1
    assert verdict(tmp_path, d, baseline() + [rcpt("isolation.case.one", passed=False)]) == 1


def test_verdict_takes_a_phase_as_evidence_without_receipts(tmp_path):
    d = doc_with({"isolation.case.one": case(evidence=["phase:demo-on"])})
    assert verdict(tmp_path, d, baseline()) == 0


def test_verdict_fails_on_zero_receipts(tmp_path):
    d = doc_with({})
    d["collections"] = {}
    assert verdict(tmp_path, d, []) == 1


def test_verdict_fails_on_an_expired_row(tmp_path):
    d = doc_with({"isolation.case.two": case("pending", expires="2026-11-10")})
    assert verdict(tmp_path, d, baseline()) == 1
    d = doc_with({"isolation.case.two": case("pending", expires="2026-11-11")})
    assert verdict(tmp_path, d, baseline()) == 0


def test_verdict_fails_when_a_pending_or_slot_row_produces_a_receipt(tmp_path):
    for status in ("pending", "slot"):
        d = doc_with({"isolation.case.two": case(status)})
        assert verdict(tmp_path, d, baseline() + [rcpt("isolation.case.two")]) == 1


def test_verdict_fails_when_a_pending_row_is_implemented(tmp_path, monkeypatch):
    d = doc_with({"isolation.case.two": case("pending")})
    monkeypatch.setattr(run.families, "IMPLEMENTED_FAMILIES",
                        run.families.IMPLEMENTED_FAMILIES | {"isolation.case.two"})
    assert verdict(tmp_path, d, baseline()) == 1


def test_verdict_reports_a_quarantined_failure_and_fails_an_unexpected_pass(tmp_path, capsys):
    d = doc_with({"isolation.case.one": case("quarantined")})
    assert verdict(tmp_path, d, baseline() + [rcpt("isolation.case.one", passed=False)]) == 0
    out = capsys.readouterr().out
    assert "expected-fail:  1" in out and "fail:           0" in out
    assert verdict(tmp_path, d, baseline() + [rcpt("isolation.case.one")]) == 1
    assert verdict(tmp_path, d, baseline()) == 1  # a quarantined row still runs


def test_verdict_tolerates_a_quarantined_failure_only_on_its_target(tmp_path):
    d = doc_with({"isolation.case.one": case("quarantined")})
    covered = rcpt("isolation.case.one", passed=False)
    other = rcpt("isolation.case.one", passed=False, collection="offers")
    assert verdict(tmp_path, d, baseline() + [covered, rcpt("isolation.case.one", collection="offers")]) == 0
    assert verdict(tmp_path, d, baseline() + [covered, other]) == 1


@pytest.mark.parametrize("start, end", [("2026-11-20", "2026-11-25"), ("2026-11-15", "2026-11-28")])
def test_verdict_fails_a_quarantine_window_that_doesnt_hold_today(tmp_path, start, end):
    # Both start in the future; the second also ends more than 14 days out.
    d = doc_with({"isolation.case.one": case("quarantined", quarantined_on=start, expires=end)})
    assert verdict(tmp_path, d, baseline() + [rcpt("isolation.case.one", passed=False)]) == 1


def test_verdict_counts_scoped_evidence_on_its_collection_only(tmp_path):
    d = doc_with({"isolation.case.one": case(evidence=[f"campaigns:{ENFORCED}"])})
    assert verdict(tmp_path, d, baseline()) == 0
    # A passing receipt on another collection doesn't stand in for it.
    rows = [rcpt(ENFORCED, passed=True, collection="offers"), rcpt(run.READBACK_PROBE)]
    assert verdict(tmp_path, d, rows) == 1


def test_verdict_fails_on_a_receipt_for_an_unknown_case(tmp_path):
    d = doc_with({"isolation.case.one": case()})
    rows = baseline() + [rcpt("isolation.case.one"), rcpt("isolation.case.unlisted")]
    assert verdict(tmp_path, d, rows) == 1


# --------------------------------------------------------------------------
# the comparator
# --------------------------------------------------------------------------


def _resp(status=404, body=None, headers=None, length=None, raw=None) -> Response:
    body = {"detail": "Not found.", "code": "not_found", "correlation_id": "c" * 32} if body is None else body
    raw = json.dumps(body).encode() if raw is None else raw
    return Response(status, body, 1, headers or {"content-type": "application/json", "date": "Tue"},
                    len(raw) if length is None else length, raw)


def test_comparator_compares_the_raw_body():
    # Same parsed body, different key order: two answers, not one.
    a = _resp(raw=b'{"detail":"Not found.","code":"not_found"}')
    b = _resp(raw=b'{"code":"not_found","detail":"Not found."}')
    assert "body" in compare.differences(a, b)
    # Non-JSON bodies of one length still differ.
    c = _resp(body=None, raw=b"<html>one</html>")
    c.body = None
    e = _resp(body=None, raw=b"<html>two</html>")
    e.body = None
    assert compare.differences(c, e) == ["body"]
    # Per-request ids in the raw body are set aside, whatever the spacing.
    f = _resp(raw=b'{"detail":"x", "correlation_id" : "' + b"a" * 32 + b'"}')
    g = _resp(raw=b'{"detail":"x", "correlation_id" : "' + b"b" * 32 + b'"}')
    assert compare.differences(f, g) == []


def test_comparator_sets_aside_only_per_request_values():
    a = _resp()
    b = _resp(body={"detail": "Not found.", "code": "not_found", "correlation_id": "d" * 32},
              headers={"content-type": "application/json", "date": "Wed", "x-correlation-id": "z"})
    assert compare.differences(a, b) == []
    msg_a = _resp(400, {"detail": "No key (request id: abc123)"})
    msg_b = _resp(400, {"detail": "No key (request id: def456)"})
    assert compare.differences(msg_a, msg_b) == []


@pytest.mark.parametrize("other, named", [
    (_resp(403), "status"),
    (_resp(body={"detail": "Forbidden.", "code": "not_found", "correlation_id": "c" * 32}), "body"),
    (_resp(length=999), "length"),
    (_resp(headers={"content-type": "application/json", "date": "Tue", "x-extra": "1"}), "header:x-extra"),
])
def test_comparator_names_each_difference_without_values(other, named):
    diffs = compare.differences(_resp(), other)
    assert named in diffs
    assert all("Forbidden" not in d for d in diffs)


def test_call_sequence_templates_the_probed_ids():
    log = [{"method": "GET", "path": "/api/collections/ai_providers/records/aaaaaaaaaaaaaaa", "auth": "user",
            "status": 404}]
    other = [{"method": "GET", "path": "/api/collections/ai_providers/records/zzzzzzzzzzzzzzz", "auth": "user",
              "status": 404}]
    assert (compare.call_sequence(log, ["aaaaaaaaaaaaaaa"])
            == compare.call_sequence(other, ["zzzzzzzzzzzzzzz"])
            == [("GET", "/api/collections/ai_providers/records/{id}", "user", 404)])


# --------------------------------------------------------------------------
# the recording proxy
# --------------------------------------------------------------------------


@pytest.mark.parametrize("header, cls", [
    (None, "none"),
    ("", "none"),
    (f"Bearer {USER_TOKEN}", "user"),
    (USER_TOKEN, "user"),
    (f"Bearer {ADMIN_TOKEN}", "superuser"),
    (f"Bearer {SERVICE_TOKEN}", "service"),
    ("Bearer not-a-token", "malformed"),
    ("Bearer a.b.c", "malformed"),
    (f"Bearer {_jwt({'type': 'authRecord'})}", "malformed"),
    (f"Bearer {_jwt({'type': 'something'})}", "malformed"),
])
def test_classifier(header, cls):
    assert recorder.classify(header) == cls


def test_log_line_keeps_no_header_token_query_or_body():
    body = json.dumps({"items": [{"user": "owner000000000a", "secret_field": PLANTED_PASSWORD,
                                  "expand": {"user": {"user": "owner000000000b"}}}]}).encode()
    line = recorder.entry(1, "GET", f"/api/collections/x/records?q={PLANTED_PASSWORD}",
                          f"Bearer {USER_TOKEN}", 200, body, b"salt-for-tests-0000")
    text = json.dumps(line)
    assert USER_TOKEN not in text and PLANTED_PASSWORD not in text
    assert "owner000000000a" not in text and "q=" not in text
    assert line["path"] == "/api/collections/x/records"
    assert line["auth"] == "user" and line["status"] == 200 and line["length"] == len(body)
    salt = b"salt-for-tests-0000"
    assert line["owners"] == sorted({recorder.pseudonym(salt, "owner000000000a"),
                                     recorder.pseudonym(salt, "owner000000000b")})


def test_recorder_forwards_and_logs(tmp_path):
    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            out = json.dumps({"user": "owner000000000a", "seen_auth": self.headers.get("Authorization", "")}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

    up = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    log = tmp_path / "rec.jsonl"
    rec = recorder._Recorder(f"http://127.0.0.1:{up.server_port}", str(log), b"salt-for-tests-0000")
    proxy = ThreadingHTTPServer(("127.0.0.1", 0), recorder._handler(rec))
    for s in (up, proxy):
        threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{proxy.server_port}/api/x?q=abc",
                                     headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            got = json.loads(resp.read())
        assert got["seen_auth"] == f"Bearer {ADMIN_TOKEN}"  # forwarded unchanged
        lines = recorder.read_log(str(log))
        assert [(x["method"], x["path"], x["auth"], x["status"]) for x in lines] == [("GET", "/api/x", "superuser", 200)]
        assert ADMIN_TOKEN not in log.read_text() and "abc" not in log.read_text()
        assert recorder.log_length(str(log)) == 1 and recorder.read_log(str(log), 1) == []

        # Two Authorization headers: one value is forwarded, and the line
        # says malformed rather than describing the other one.
        conn = http.client.HTTPConnection("127.0.0.1", proxy.server_port, timeout=5)
        conn.putrequest("GET", "/api/y")
        conn.putheader("Authorization", f"Bearer {USER_TOKEN}")
        conn.putheader("Authorization", f"Bearer {ADMIN_TOKEN}")
        conn.endheaders()
        got = json.loads(conn.getresponse().read())
        conn.close()
        assert got["seen_auth"] == f"Bearer {ADMIN_TOKEN}"
        assert recorder.read_log(str(log), 1)[0]["auth"] == "malformed"
    finally:
        proxy.shutdown()
        up.shutdown()


def test_auth_class_of_header_values():
    assert recorder.auth_class([]) == "none"
    assert recorder.auth_class([f"Bearer {USER_TOKEN}"]) == "user"
    assert recorder.auth_class([f"Bearer {USER_TOKEN}", f"Bearer {USER_TOKEN}"]) == "malformed"


def test_recorder_refuses_to_start_without_a_salt(monkeypatch):
    monkeypatch.setenv("RECORDER_LOG", "/var/lib/rounds-recorder/recorder.jsonl")
    monkeypatch.setenv("RECORDER_SALT", "")
    assert recorder.main() == 2


def test_recorder_log_stays_out_of_the_uploaded_folder(monkeypatch, tmp_path):
    # The default log path is outside the probe container's /out, which
    # compose binds to the host folder CI uploads.
    compose = (ROOT / "harness" / "compose.yml").read_text()
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "./.receipts:/out" in compose and "path: harness/.receipts/" in ci
    assert not recorder.log_is_uploaded(recorder.DEFAULT_LOG)
    for inside in ("/out/recorder.jsonl", "/out/sub/recorder.jsonl", "/out/../out/recorder.jsonl"):
        assert recorder.log_is_uploaded(inside), inside
    monkeypatch.setenv("RECORDER_SALT", "salt-for-tests-000000")
    monkeypatch.setenv("RECORDER_LOG", "/out/recorder.jsonl")
    assert recorder.main() == 2
    monkeypatch.setenv("RECORDER_LOG", str(tmp_path / "up" / "recorder.jsonl"))
    monkeypatch.setenv("RECORDER_UPLOADED_DIRS", str(tmp_path / "up"))
    assert recorder.main() == 2


def test_discard_log_deletes_it(tmp_path):
    log = tmp_path / "recorder.jsonl"
    log.write_text('{"seq":1}\n')
    recorder.discard_log(str(log))
    assert not log.exists()
    recorder.discard_log(str(log))  # already gone is fine


# --------------------------------------------------------------------------
# the receipt redactor
# --------------------------------------------------------------------------


def test_a_planted_token_and_password_never_reach_a_receipt(tmp_path):
    path = tmp_path / "out" / "receipts.jsonl"
    writer = ReceiptWriter(str(path), {"run_id": "t"})
    registered = "registered-session-value-0123456789"
    writer.register_secret(registered, "token:a")
    writer.write(Receipt("isolation.case.one", "campaigns", "view", "authenticated-other", 404, 404, True, 1,
                         detail=f"saw {USER_TOKEN} and {PLANTED_PASSWORD} and {registered}"))
    writer.write(Receipt("isolation.case.one", PLANTED_PASSWORD, ADMIN_TOKEN, "x", 404, 404, True, 1))
    text = path.read_text()
    for value in (USER_TOKEN, ADMIN_TOKEN, PLANTED_PASSWORD, registered):
        assert value not in text
    first = read_all(str(path))[0]
    assert "<token:a>" in first["detail"] and "<redacted:token>" in first["detail"]
    assert "<redacted:password>" in first["detail"]


def test_receipts_carry_the_policy_and_migration_checksums(tmp_path, monkeypatch):
    monkeypatch.setenv("POLICY_PATH", str(POLICY))
    monkeypatch.setenv("PB_MIGRATIONS_DIR", str(ROOT / "pocketbase" / "pb_migrations"))
    ctx = run._context("main")
    assert ctx["policy_checksum"].startswith("sha256:") and len(ctx["policy_checksum"]) == 71
    assert ctx["migrations_checksum"].startswith("sha256:")
    path = tmp_path / "r.jsonl"
    ReceiptWriter(str(path), ctx).write(Receipt("p", "c", "o", "a", 1, 1, True, 1))
    got = read_all(str(path))[0]
    assert got["policy_checksum"] == ctx["policy_checksum"] and got["migrations"] == ctx["migrations"]


def test_redactor_covers_tuples_dict_keys_and_the_serialized_line(tmp_path):
    r = Redactor()
    r.register("registered-session-value-0123456789", "token:a")
    got = r.value({"k": (USER_TOKEN, "ok"), PLANTED_PASSWORD: "v", "registered-session-value-0123456789": 1})
    assert got == {"k": ["<redacted:token>", "ok"], "<redacted:password>": "v", "<token:a>": 1}
    path = tmp_path / "r.jsonl"
    writer = ReceiptWriter(str(path), {"migrations": [PLANTED_PASSWORD]})
    writer.write(Receipt("p", "c", "o", "a", 1, 1, True, 1))
    assert PLANTED_PASSWORD not in path.read_text()
    assert read_all(str(path))[0]["migrations"] == ["<redacted:password>"]


def test_every_phase_writer_redacts_the_admin_password(tmp_path, monkeypatch):
    placeholder = "harness-admin-placeholder-123"  # no fixed shape, like the harness's
    monkeypatch.setenv("PB_ADMIN_PASSWORD", placeholder)
    path = tmp_path / "r.jsonl"
    for phase in ("deploy", "admission-deploy", "hook"):
        run.new_writer(str(path), phase).write(Receipt("p", "c", "o", "a", 1, 1, True, 1, detail=f"pw {placeholder}"))
    assert placeholder not in path.read_text()
    assert all(r["detail"] == "pw <password:superuser>" for r in read_all(str(path)))


def test_short_registered_values_are_ignored():
    # A short value would redact ordinary words; every harness secret is long.
    r = Redactor()
    r.register("abc", "x")
    assert r.text("abc") == "abc"


# --------------------------------------------------------------------------
# the log scanner
# --------------------------------------------------------------------------


def test_log_scanner_finds_planted_credentials_and_reports_no_value(tmp_path):
    text = "\n".join([
        "GET /api/health 200",
        f"request carried {USER_TOKEN}",
        f'{{"msg": "login", "password": "{PLANTED_PASSWORD}"}}',
        "admin uses harness-admin-literal-0001",
    ])
    found = logscan.scan_text(text, "runner", ("harness-admin-literal-0001",))
    assert (found.tokens, found.passwords, found.literals) == (1, 1, 1)
    assert not found.clean and found.where == {"runner"}
    summary = found.summary()
    assert USER_TOKEN not in summary and PLANTED_PASSWORD not in summary
    assert logscan.scan_text("GET /api/health 200\n", "nginx").clean


def test_log_scanner_reads_a_sqlite_log_database_read_only(tmp_path):
    db = tmp_path / "service.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE events (id TEXT, data TEXT, blobby BLOB)")
    con.execute("INSERT INTO events VALUES ('1', ?, ?)", (json.dumps({"msg": "started"}), b"plain"))
    con.commit()
    assert logscan.scan_sqlite(str(db), "service").clean
    con.execute("INSERT INTO events VALUES ('2', ?, NULL)", (json.dumps({"msg": ADMIN_TOKEN}),))
    con.commit()
    con.close()
    found = logscan.scan_sqlite(str(db), "service")
    assert found.tokens == 1 and found.where == {"service:events"}
    before = db.read_bytes()
    logscan.scan_sqlite(str(db), "service")
    assert db.read_bytes() == before
