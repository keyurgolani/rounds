"""Self-test: receipt serialization, checksums, coverage, and evidence
caps (issue #8, Required tests Unit: receipt serialization)."""
from __future__ import annotations

import json

import pytest

from conformance import RECEIPT_SCHEMA
from conformance import receipts as r
from conformance.receipts import FixtureReceipt, RunReceipt, cap_evidence, checksum, default_versions


def test_checksum_is_stable_and_prefixed():
    a = checksum("hello")
    assert a == checksum("hello")
    assert a.startswith("sha256:")
    assert a != checksum("world")


def test_default_versions_mark_unlanded_as_absent():
    v = default_versions()
    assert v["renderer_contract"] == "absent"
    assert v["envelope"] == "absent"
    assert v["definition"] == "test-definition/v1"


def _run_receipt() -> RunReceipt:
    return RunReceipt(commit="abc123", corpus_version="1", target="ci", canary_set_id="canary-set/v1",
                      images={"runner": "absent"}, versions=default_versions(), run_id="r1")


def test_run_receipt_round_trips_with_every_entry_kind(tmp_path):
    run = _run_receipt()
    run.add(FixtureReceipt(id="EX-01", status="ran", closing_leaf="ROUNDS-00A-L01", target="ci",
                           outcome="contained", expectation="contained", verdict="pass",
                           subcases=[{"id": "EX-01.a", "status": "contained", "outcome": "contained",
                                      "closing_leaf": "ROUNDS-00A-L01"}],
                           routes=["POST /api/run"], evidence={"answers": "401"}, note="fine",
                           canary_hits={"AI_KEY_SECRET": False}))
    run.add(FixtureReceipt(id="EX-08", status="pending", closing_leaf="ROUNDS-00A-L05"))
    run.add(FixtureReceipt(id="EX-03", status="quarantined", closing_leaf="ROUNDS-00A-L01",
                           quarantine={"owner": "platform", "expiry": "2099-01-01", "reason": "flaky"}))
    run.budget_total = {"fixtures": 1, "requests": 7, "wall_seconds": 1.2}
    out = tmp_path / "receipt.json"
    run.write(str(out))
    loaded = json.loads(out.read_text())
    assert loaded["schema"] == RECEIPT_SCHEMA
    assert loaded["budget_total"]["requests"] == 7
    by_id = {f["id"]: f for f in loaded["fixtures"]}
    assert by_id["EX-01"]["routes"] == ["POST /api/run"]
    assert by_id["EX-01"]["evidence"] == {"answers": "401"} and by_id["EX-01"]["note"] == "fine"
    assert by_id["EX-08"]["status"] == "pending" and by_id["EX-08"]["verdict"] == ""
    assert by_id["EX-03"]["quarantine"]["owner"] == "platform"
    assert run.passed


def test_a_receipt_entry_is_recorded_once():
    run = _run_receipt()
    run.add(FixtureReceipt(id="EX-01", status="pending", closing_leaf="L"))
    with pytest.raises(ValueError):
        run.add(FixtureReceipt(id="EX-01", status="pending", closing_leaf="L"))


def test_missing_names_rows_without_an_entry_and_entries_without_a_row():
    run = _run_receipt()
    run.add(FixtureReceipt(id="EX-01", status="pending", closing_leaf="L"))
    run.add(FixtureReceipt(id="ZZ-99", status="pending", closing_leaf="L"))
    assert run.missing(["EX-01", "EX-02"]) == {"missing": ["EX-02"], "unknown": ["ZZ-99"]}


def test_run_receipt_passed_is_false_on_a_failing_fixture():
    run = _run_receipt()
    run.add(FixtureReceipt(id="EX-01", status="ran", closing_leaf="L", verdict="fail"))
    assert not run.passed


def test_evidence_is_capped_with_a_marker(monkeypatch):
    monkeypatch.setattr(r, "EVIDENCE_MAX_CHARS", 10)
    capped = cap_evidence({"a": "x" * 8, "b": "y" * 8, "c": "z"})
    assert capped["a"] == "x" * 8
    assert capped["b"] == "yy<truncated>"
    assert capped["c"] == "<truncated>"
