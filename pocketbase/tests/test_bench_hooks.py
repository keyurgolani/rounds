"""The database benchmark's hook logic (ROUNDS-02-L01).

harness/bench/pb_hooks/bench_lib.js runs here on node's SQLite
(bench_runner.cjs), with the bench's own migration making the tables, so
unique keys, the partial unique index, and rollback are SQLite's own. The
benchmark runs the same logic on PocketBase (harness/bench/bench.py); these
tests keep its guarantees honest before any native run: one command commits
once or not at all, a retry replays, a stale or foreign read writes nothing,
the offer chain keeps one active offer, the relay has one holder and its
projection applies each event once.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "pocketbase" / "tests" / "bench_runner.cjs"
BENCH = ROOT / "harness" / "bench"
sys.path.insert(0, str(BENCH))
import benchlib  # noqa: E402

A = "acctaaaaaaaaaaa"
B = "acctbbbbbbbbbbb"


def run(steps: list[dict]) -> list:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not on PATH")
    res = subprocess.run([node, str(RUNNER), str(ROOT)], input=json.dumps({"steps": steps}), capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def cid(n: int) -> str:
    return benchlib.uuid7(1_800_000_000_000 + n, bytes([n % 256]) * 10)


def agg(id_: str, account: str, kind: str = "fact", status: str = "", parent: str = "", version: int = 1) -> dict:
    return {"op": "seed", "table": "bench_records", "columns": ["id", "account_id", "kind", "version", "status", "parent", "deleted", "payload"],
            "rows": [[id_, account, kind, version, status, parent, False, {"synthetic": True}]]}


def count(table: str, where: str = "1 = 1") -> dict:
    return {"op": "raw", "sql": f"SELECT COUNT(*) AS n FROM {table} WHERE {where}", "shape": {"n": 0}}


def test_an_update_commits_once_with_its_history():
    out = run([
        agg("fact00000000001", A),
        {"op": "command", "account": A, "body": {"command_id": cid(1), "type": "update", "expected": {"fact00000000001": 1},
                                                  "args": {"id": "fact00000000001", "payload": {"v": 2}}}},
        count("bench_change_sets"), count("bench_audit"), count("bench_outbox"), count("bench_idempotency"),
        {"op": "raw", "sql": "SELECT version FROM bench_records WHERE id = 'fact00000000001'", "shape": {"version": 0}},
        {"op": "raw", "sql": "SELECT event_id, aggregate_seq, relay_seq FROM bench_outbox", "shape": {"event_id": "", "aggregate_seq": 0, "relay_seq": 0}},
    ])
    res = out[1]
    assert res["status"] == 200, res
    assert res["body"]["commit_position"] == 1 and res["body"]["writes"] == benchlib.EXPECTED_WRITES["update"]
    assert [o[0]["n"] for o in out[2:6]] == [1, 1, 1, 1]
    assert out[6][0]["version"] == 2
    event = out[7][0]
    assert benchlib.V7.match(event["event_id"]) and event["aggregate_seq"] == 2 and event["relay_seq"] == 1


def test_a_retry_replays_and_a_changed_body_conflicts():
    body = {"command_id": cid(2), "type": "update", "expected": {"fact00000000002": 1}, "args": {"id": "fact00000000002", "payload": {"v": 2}}}
    changed = dict(body, args={"id": "fact00000000002", "payload": {"v": 3}})
    out = run([agg("fact00000000002", A),
               {"op": "command", "account": A, "body": body},
               {"op": "command", "account": A, "body": body},
               {"op": "command", "account": A, "body": changed},
               count("bench_change_sets")])
    first, again, other = out[1], out[2], out[3]
    assert again["status"] == 200 and again["body"]["replay"] is True
    assert again["body"]["commit_position"] == first["body"]["commit_position"]
    assert other["status"] == 409 and other["body"]["error"] == "fingerprint_conflict"
    assert out[4][0]["n"] == 1


def test_a_stale_version_writes_nothing_and_returns_the_current_one():
    out = run([agg("fact00000000003", A, version=4),
               {"op": "command", "account": A, "body": {"command_id": cid(3), "type": "update", "expected": {"fact00000000003": 3},
                                                         "args": {"id": "fact00000000003", "payload": {}}}},
               count("bench_change_sets"), count("bench_idempotency")])
    assert out[1]["status"] == 409 and out[1]["body"] == {"error": "stale_version", "current": {"fact00000000003": 4}}
    assert out[2][0]["n"] == 0 and out[3][0]["n"] == 0


def test_another_accounts_aggregate_and_a_missing_one_get_the_same_answer():
    def cmd(n, target):
        return {"op": "command", "account": A, "body": {"command_id": cid(n), "type": "update", "expected": {target: 1},
                                                         "args": {"id": target, "payload": {}}}}
    out = run([agg("fact0000000000b", B), cmd(4, "fact0000000000b"), cmd(5, "fact0000000none"), count("bench_change_sets")])
    assert out[1] == out[2] == {"status": 404, "body": {"error": "not_found"}}
    assert out[3][0]["n"] == 0


def test_the_offer_chain_keeps_one_active_offer():
    opp, active = "opp000000000001", "off000000000001"
    seed = [agg(opp, A, "opportunity"), agg(active, A, "offer", "active", opp)]
    compose = {"op": "command", "account": A, "body": {"command_id": cid(6), "type": "compose", "expected": {opp: 1, active: 1},
                                                       "args": {"opportunity": opp, "offer": active, "payload": {}}}}
    out = run(seed + [
        compose,
        {"op": "raw", "sql": f"SELECT id, status, version FROM bench_records WHERE kind = 'offer' AND parent = '{opp}' ORDER BY status",
         "shape": {"id": "", "status": "", "version": 0}},
        {"op": "raw", "sql": f"SELECT status, version FROM bench_records WHERE id = '{opp}'", "shape": {"status": "", "version": 0}},
        # A second active offer is refused by the partial unique index itself.
        {"op": "rawWrite", "sql": "INSERT INTO bench_records (id, account_id, kind, version, status, parent) VALUES "
                                  f"('off000000000099', '{A}', 'offer', 1, 'active', '{opp}')"},
        # Composing again on the superseded offer is an invariant violation, and writes nothing.
        {"op": "command", "account": A, "body": {"command_id": cid(7), "type": "compose", "expected": {opp: 2, active: 2},
                                                 "args": {"opportunity": opp, "offer": active, "payload": {}}}},
        count("bench_change_sets"),
    ])
    assert out[2]["status"] == 200 and out[2]["body"]["writes"] == benchlib.EXPECTED_WRITES["compose"]
    offers = out[3]
    assert [o["status"] for o in offers] == ["active", "superseded"]
    assert out[4][0] == {"status": "Offer", "version": 2}
    assert out[5]["ok"] is False and "UNIQUE constraint failed" in out[5]["error"]
    assert out[6]["status"] == 409 and out[6]["body"]["error"] == "invariant_violation"
    assert out[7][0]["n"] == 1


def test_delete_revives_the_prior_offer_in_the_same_transaction():
    opp, prior, active = "opp000000000002", "off000000000002", "off000000000003"
    out = run([agg(opp, A, "opportunity", version=2), agg(prior, A, "offer", "superseded", opp, 2), agg(active, A, "offer", "active", opp),
               {"op": "command", "account": A, "body": {"command_id": cid(8), "type": "delete_revive", "expected": {opp: 2, prior: 2, active: 1},
                                                         "args": {"opportunity": opp, "offer": active, "prior": prior}}},
               {"op": "raw", "sql": "SELECT id, status, deleted FROM bench_records WHERE kind = 'offer' ORDER BY id",
                "shape": {"id": "", "status": "", "deleted": False}}])
    assert out[3]["status"] == 200 and out[3]["body"]["writes"] == benchlib.EXPECTED_WRITES["delete_revive"]
    assert out[4] == [{"id": prior, "status": "active", "deleted": False}, {"id": active, "status": "deleted", "deleted": True}]


def test_before_commit_leaves_nothing_and_the_retry_commits_once():
    body = {"command_id": cid(9), "type": "update", "expected": {"fact00000000009": 1}, "args": {"id": "fact00000000009", "payload": {"v": 2}}}
    tables = ["bench_change_sets", "bench_audit", "bench_outbox", "bench_idempotency"]
    out = run([agg("fact00000000009", A), {"op": "command", "account": A, "body": body, "failpoint": "before-commit"}]
              + [count(t) for t in tables]
              + [{"op": "raw", "sql": "SELECT version FROM bench_records WHERE id = 'fact00000000009'", "shape": {"version": 0}},
                 {"op": "command", "account": A, "body": body}, {"op": "command", "account": A, "body": body}]
              + [count(t) for t in tables])
    assert out[1] == {"status": 503, "body": {"error": "failpoint", "failpoint": "before-commit"}}
    assert [o[0]["n"] for o in out[2:6]] == [0, 0, 0, 0]
    assert out[6][0]["version"] == 1
    assert out[7]["status"] == 200 and out[8]["body"]["replay"] is True
    assert [o[0]["n"] for o in out[9:13]] == [1, 1, 1, 1]


def test_the_relay_has_one_holder_and_a_new_token_on_takeover():
    out = run([
        {"op": "lease", "holder": "relay-a", "ttl_ms": 1000},
        {"op": "lease", "holder": "relay-b", "ttl_ms": 1000},
        {"op": "lease", "holder": "relay-a", "ttl_ms": 1000},
        {"op": "tick", "ms": 1500},
        {"op": "lease", "holder": "relay-b", "ttl_ms": 1000},
        # The old holder's ack is fenced off; the new holder's goes through.
        {"op": "ack", "holder": "relay-a", "token": 1, "cursor": 5},
        {"op": "ack", "holder": "relay-b", "token": 2, "cursor": 5},
    ])
    assert out[0] == {"status": 200, "body": {"held": True, "token": 1}}
    assert out[1]["body"]["held"] is False and out[1]["body"]["holder"] == "relay-a"
    assert out[2]["body"] == {"held": True, "token": 1}
    assert out[4]["body"] == {"held": True, "token": 2}
    assert out[5]["body"] == {"acked": False, "reason": "fenced"}
    assert out[6]["body"] == {"acked": True}


def test_mid_relay_redelivery_is_applied_once():
    steps = [agg(f"fact0000000010{i}", A) for i in range(3)]
    for i in range(3):
        steps.append({"op": "command", "account": A, "body": {"command_id": cid(20 + i), "type": "update",
                                                               "expected": {f"fact0000000010{i}": 1}, "args": {"id": f"fact0000000010{i}", "payload": {}}}})
    steps += [{"op": "lease", "holder": "relay-a", "ttl_ms": 1000}, {"op": "read", "limit": 10}]
    out = run(steps)
    events = out[-1]["body"]["events"]
    assert [e["relay_seq"] for e in events] == [1, 2, 3]
    # Apply, then die before the ack: the cursor hasn't moved, so the next
    # holder reads the same events again and the projection skips them.
    second = run(steps + [{"op": "apply", "events": events}, {"op": "read", "limit": 10}, {"op": "apply", "events": events},
                          {"op": "projection", "account": A, "aggregate_id": "fact00000000100", "min_position": 1},
                          {"op": "projection", "account": A, "aggregate_id": "fact00000000100", "min_position": 9},
                          {"op": "projection", "account": B, "aggregate_id": "fact00000000100", "min_position": 1}])
    applied, again = second[-6]["body"], second[-4]["body"]
    assert applied == {"applied": 3, "skipped": 0, "gaps": 0}
    assert second[-5]["body"]["after"] == 0 and len(second[-5]["body"]["events"]) == 3
    assert again == {"applied": 0, "skipped": 3, "gaps": 0}
    assert second[-3]["body"]["reached"] is True and second[-3]["body"]["version"] == 2
    assert second[-2]["body"]["reached"] is False
    assert second[-1]["body"] == {"found": False, "reached": False}


def test_the_transfer_moves_an_accounts_pipeline_in_bounded_batches():
    steps = [{"op": "seed", "table": "applications", "columns": ["id", "user", "company", "role", "status"],
              "rows": [[f"app{i:012d}", A, "Synthetic Co", "Engineer", "Applied"] for i in range(7)]},
             {"op": "seed", "table": "interview_rounds", "columns": ["id", "user", "application", "round_type"],
              "rows": [[f"rnd{i:012d}", A, f"app{i % 7:012d}", "phone"] for i in range(14)]},
             {"op": "seed", "table": "offers", "columns": ["id", "user", "application", "status"],
              "rows": [[f"ofr{i:012d}", A, f"app{i:012d}", "pending"] for i in range(3)]}]
    out = run(steps + [{"op": "transfer", "account": A, "after": "", "limit": 3},
                       {"op": "transfer", "account": A, "after": "app000000000002", "limit": 3},
                       {"op": "transfer", "account": A, "after": "app000000000005", "limit": 3},
                       count("bench_records", "kind LIKE '%_t'"), count("bench_change_sets")])
    batches = [o["body"] for o in out[3:6]]
    assert [b["applications"] for b in batches] == [3, 3, 1] and [b["done"] for b in batches] == [False, False, True]
    assert out[6][0]["n"] == 7 + 14 + 3 and out[7][0]["n"] == 7


def test_background_writers_write_their_rows():
    out = run([{"op": "background", "kind": "admission", "account": A}, {"op": "background", "kind": "execution", "account": A},
               {"op": "background", "kind": "share", "account": A}, {"op": "background", "kind": "nope", "account": A}])
    assert [o["body"]["writes"] for o in out[:3]] == [3, 1, 1]
    assert out[3]["status"] == 400


def test_seeding_takes_only_named_tables_and_columns():
    out = run([{"op": "seed", "table": "users", "columns": ["id"], "rows": [["x"]]},
               {"op": "seed", "table": "bench_records", "columns": ["id; DROP"], "rows": [["x"]]},
               {"op": "seed", "table": "bench_records", "columns": ["id"], "rows": [["a", "b"]]}])
    assert [o["body"]["error"] for o in out] == ["table_not_seedable", "invalid_columns", "invalid_rows"]


def test_seeding_takes_column_names_with_digits():
    out = run([{"op": "seed", "table": "bench_blobs", "columns": ["id", "account_id", "sha256", "size", "privacy_class", "retain_until", "file"],
                "rows": [["blobaaaaaaaaaaa", A, "ab" * 32, 2097152, "Private", 0, "blob_ab.bin"]]}, count("bench_blobs")])
    assert out[0] == {"status": 200, "body": {"rows": 1}} and out[1][0]["n"] == 1


def test_commands_need_a_v7_id_and_a_known_type():
    out = run([{"op": "checkCommand", "body": {"command_id": "not-an-id", "type": "update"}},
               {"op": "checkCommand", "body": {"command_id": cid(1), "type": "drop"}},
               {"op": "checkCommand", "body": {"command_id": cid(1), "type": "update", "expected": {"x": 1}}},
               {"op": "checkCommand", "body": {"command_id": cid(1), "type": "update", "expected": {"fact00000000001": 1}}}])
    assert out == ["invalid_command_id", "unknown_command", "invalid_request", None]


def test_derived_ids_match_the_python_rule_and_repeat_for_a_retry():
    parts = ["gateway", "update", cid(1), "0"]
    js = run([{"op": "derivedId", "time_ms": 1_800_000_000_123, "parts": parts}, {"op": "derivedId", "time_ms": 1_800_000_000_123, "parts": parts}])
    assert js[0] == js[1] == benchlib.derived_id(1_800_000_000_123, parts)
    assert benchlib.V7.match(js[0])


def test_the_bench_ships_nowhere():
    dockerfile = (ROOT / "pocketbase" / "Dockerfile").read_text()
    # The image copies these three directories under pocketbase/ and nothing else.
    copies = re.findall(r"^COPY\s+(\S+)", dockerfile, re.MULTILINE)
    assert copies == ["pb_migrations", "pb_hooks", "seeds"]
    routes = re.findall(r'routerAdd\("POST", "([^"]+)"', (BENCH / "pb_hooks" / "bench.pb.js").read_text())
    assert routes and all(r.startswith("/api/bench/") for r in routes)
    assert not any((ROOT / "pocketbase" / "pb_hooks").glob("bench*"))
