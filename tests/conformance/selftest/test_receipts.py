"""Self-test: receipt serialization and checksums (issue #8, Required
tests Unit: receipt serialization)."""
from __future__ import annotations

import json

from conformance import RECEIPT_SCHEMA
from conformance.receipts import FixtureReceipt, RunReceipt, checksum, default_versions


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


def test_run_receipt_round_trips(tmp_path):
    run = RunReceipt(
        commit="abc123",
        corpus_version="1",
        target="ci",
        canary_set_id="canary-set/v1",
        images={"runner": "absent"},
        versions=default_versions(),
        run_id="r1",
    )
    run.add(FixtureReceipt(id="EX-01", status="contained", closing_leaf="ROUNDS-00A-L01",
                           target="ci", outcome="contained", expectation="contained",
                           verdict="pass", canary_hits={"AI_KEY_SECRET": False}))
    run.add(FixtureReceipt(id="EX-08", status="pending", closing_leaf="ROUNDS-00A-L05"))
    out = tmp_path / "receipt.json"
    run.write(str(out))
    loaded = json.loads(out.read_text())
    assert loaded["schema"] == RECEIPT_SCHEMA
    assert loaded["target"] == "ci"
    assert {f["id"] for f in loaded["fixtures"]} == {"EX-01", "EX-08"}
    pending = next(f for f in loaded["fixtures"] if f["id"] == "EX-08")
    assert pending["status"] == "pending" and pending["verdict"] == ""
    assert run.passed


def test_run_receipt_passed_is_false_on_a_failing_fixture():
    run = RunReceipt(commit="c", corpus_version="1", target="ci", canary_set_id="x")
    run.add(FixtureReceipt(id="EX-01", status="contained", closing_leaf="L", verdict="fail"))
    assert not run.passed
