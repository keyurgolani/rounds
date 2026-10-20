"""Unit tests for the account-scope harness logic (ROUNDS-00B-L01).

Covers policy.load validation, the rule read-back's exact comparison
(including null vs "" and the users manageRule), and the verdict's
pass/fail decisions. These run in the backend gate via
``pytest ../pocketbase/tests``; the full two-account run lives in the
Finch/Docker harness.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

PROBES = Path(__file__).resolve().parents[1].parent / "harness" / "probes"
sys.path.insert(0, str(PROBES))

import families  # noqa: E402
import policy  # noqa: E402
import run  # noqa: E402
from receipts import Receipt  # noqa: E402

ENFORCED = "account-scope.view.cross-account.denied"
PENDING = "account-scope.create.foreign-owner.denied"


def minimal_doc() -> dict:
    return {
        "version": "v1",
        "contract": "account-scope",
        "deny_contract": {"view": {"status": 404}, "create_foreign_owner": {"status": 400}},
        "probe_families": {
            ENFORCED: {"status": "enforced", "deny_key": "view", "operation": "view", "actor": "authenticated-other"},
            PENDING: {"status": "pending", "deny_key": "create_foreign_owner", "operation": "create", "actor": "authenticated-other"},
        },
        "collections": {
            "campaigns": {
                "current_rules": {"list": "user = @request.auth.id"},
                "probes": [ENFORCED, PENDING],
            }
        },
    }


def write_receipts(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def receipt(probe_id: str, collection: str, passed: bool = True) -> dict:
    return {
        "probe_id": probe_id,
        "collection": collection,
        "operation": "view",
        "actor": "authenticated-other",
        "expected_status": 404,
        "observed_status": 404 if passed else 200,
        "passed": passed,
        "request_time_ms": 1,
    }


def baseline_rows() -> list[dict]:
    return [receipt(ENFORCED, "campaigns"), receipt(run.READBACK_PROBE, "campaigns")]


# --------------------------------------------------------------------------
# policy.load
# --------------------------------------------------------------------------


def _write_policy(tmp_path: Path, doc: dict) -> Path:
    p = tmp_path / "policy.json"
    p.write_text(json.dumps(doc))
    return p


def test_load_accepts_the_minimal_valid_policy(tmp_path):
    doc = policy.load(_write_policy(tmp_path, minimal_doc()))
    assert doc["version"] == "v1"


def test_load_rejects_unknown_version(tmp_path):
    d = minimal_doc()
    d["version"] = "v2"
    with pytest.raises(policy.PolicyError, match="unsupported policy version"):
        policy.load(_write_policy(tmp_path, d))


def test_load_rejects_unknown_family_status(tmp_path):
    d = minimal_doc()
    d["probe_families"][ENFORCED]["status"] = "maybe"
    with pytest.raises(policy.PolicyError, match="unknown status"):
        policy.load(_write_policy(tmp_path, d))


def test_load_rejects_a_collection_referencing_an_undeclared_family(tmp_path):
    d = minimal_doc()
    d["collections"]["campaigns"]["probes"].append("account-scope.make-believe")
    with pytest.raises(policy.PolicyError, match="undeclared probe family"):
        policy.load(_write_policy(tmp_path, d))


def test_enforced_and_pending_pairs_split_by_status():
    d = minimal_doc()
    assert policy.enforced_pairs(d) == [("campaigns", ENFORCED)]
    assert policy.pending_pairs(d) == [("campaigns", PENDING)]


def test_committed_policy_loads_and_covers_every_denial_cell():
    doc = policy.load(run.os.environ.get("POLICY_PATH", str(
        Path(__file__).resolve().parents[1].parent / "docs" / "security" / "account-scope.v1.json")))
    # Every enforced family the committed policy references has an
    # implementation, and every pending one does not.
    fam = doc["probe_families"]
    for name, row in doc["collections"].items():
        for pid in row["probes"]:
            if fam[pid]["status"] == "enforced":
                assert pid in families.IMPLEMENTED_FAMILIES, pid
            else:
                assert pid not in families.IMPLEMENTED_FAMILIES, pid


# --------------------------------------------------------------------------
# run_verdict
# --------------------------------------------------------------------------


def test_verdict_passes_when_every_enforced_result_and_readback_pass(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, baseline_rows())
    assert run.run_verdict(minimal_doc(), str(path)) == 0


def test_verdict_fails_on_a_missing_enforced_result(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, [receipt(run.READBACK_PROBE, "campaigns")])
    assert run.run_verdict(minimal_doc(), str(path)) == 1


def test_verdict_fails_on_a_failed_enforced_result(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, [receipt(ENFORCED, "campaigns", passed=False), receipt(run.READBACK_PROBE, "campaigns")])
    assert run.run_verdict(minimal_doc(), str(path)) == 1


def test_verdict_fails_on_a_missing_readback(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, [receipt(ENFORCED, "campaigns")])
    assert run.run_verdict(minimal_doc(), str(path)) == 1


def test_verdict_fails_when_a_pending_family_produces_a_receipt(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, baseline_rows() + [receipt(PENDING, "campaigns")])
    assert run.run_verdict(minimal_doc(), str(path)) == 1


def test_verdict_fails_when_a_pending_family_is_implemented(tmp_path, monkeypatch):
    path = tmp_path / "r.jsonl"
    write_receipts(path, baseline_rows())
    monkeypatch.setattr(families, "IMPLEMENTED_FAMILIES", families.IMPLEMENTED_FAMILIES | {PENDING})
    assert run.run_verdict(minimal_doc(), str(path)) == 1


def test_verdict_fails_on_a_stray_receipt_for_an_unknown_family(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, baseline_rows() + [receipt("account-scope.not-a-real-family", "campaigns")])
    assert run.run_verdict(minimal_doc(), str(path)) == 1


# --------------------------------------------------------------------------
# _readback
# --------------------------------------------------------------------------


@dataclass
class _Resp:
    status: int
    body: Any
    elapsed_ms: int = 1


class FakePB:
    def __init__(self, collections: list[dict]):
        self._collections = collections

    def collections_meta(self, admin_token: str) -> _Resp:
        return _Resp(200, {"items": self._collections})


class CapturingWriter:
    def __init__(self):
        self.receipts: list[Receipt] = []

    def write(self, r: Receipt) -> None:
        self.receipts.append(r)


def _readback_once(current_rules: dict, live_rules: dict) -> Receipt:
    doc = {"collections": {"c": {"current_rules": current_rules}}}
    live = {"name": "c", **live_rules}
    writer = CapturingWriter()
    run._readback(FakePB([live]), doc, "admin", writer)
    assert len(writer.receipts) == 1
    return writer.receipts[0]


def test_readback_passes_when_live_rules_match_exactly():
    r = _readback_once(
        {"list": "user = @request.auth.id", "create": '@request.auth.id != ""'},
        {"listRule": "user = @request.auth.id", "createRule": '@request.auth.id != ""'},
    )
    assert r.passed and r.detail == ""


def test_readback_distinguishes_null_from_empty_string():
    # Policy says create is "" (anyone); PocketBase reports null (superusers).
    r = _readback_once({"create": ""}, {"createRule": None})
    assert not r.passed and "create" in r.detail


def test_readback_flags_a_loosened_rule():
    r = _readback_once({"update": "user = @request.auth.id"}, {"updateRule": ""})
    assert not r.passed and "update" in r.detail


def test_readback_checks_the_users_manage_rule_under_options():
    # PocketBase 0.22 nests an auth collection's manageRule under options.
    passing = _readback_once({"manage": None}, {"options": {"manageRule": None}})
    assert passing.passed
    failing = _readback_once({"manage": None}, {"options": {"manageRule": "id = @request.auth.id"}})
    assert not failing.passed and "manage" in failing.detail
    # manageRule missing entirely (not an auth collection) is also a mismatch.
    absent = _readback_once({"manage": None}, {})
    assert not absent.passed and "manage" in absent.detail


def test_readback_flags_a_missing_collection():
    doc = {"collections": {"c": {"current_rules": {"list": "x"}}}}
    writer = CapturingWriter()
    run._readback(FakePB([]), doc, "admin", writer)
    assert not writer.receipts[0].passed and "collection-missing" in writer.receipts[0].detail
