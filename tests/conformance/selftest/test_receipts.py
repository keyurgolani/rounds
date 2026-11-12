"""Self-test: receipt serialization, checksums, coverage, and evidence
caps (issue #8, Required tests Unit: receipt serialization)."""
from __future__ import annotations

import datetime as _dt
import importlib
import json
import re

import pytest

from conformance import RECEIPT_SCHEMA
from conformance import manifest as m
from conformance import receipts as r
from conformance.execute import quarantined, run_fixture
from conformance.receipts import FixtureReceipt, RunReceipt, cap_evidence, checksum, default_versions, not_run

from fakes import GUARANTEES, Target


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
    # Synthetic ids for the entries that didn't run, so the test says
    # nothing about any real row.
    run = _run_receipt()
    run.add(FixtureReceipt(id="EX-01", status="ran", target="ci",
                           outcome="contained", expectation="contained", verdict="pass",
                           subcases=[{"id": "EX-01.a", "status": "contained", "outcome": "contained"}],
                           routes=["POST /api/run"], evidence={"answers": "401"}, note="fine",
                           canary_hits={"AI_KEY_SECRET": False}))
    run.add(not_run("EX-98"))
    run.add(FixtureReceipt(id="EX-97", status="quarantined",
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
    assert by_id["EX-98"] == {"id": "EX-98", "status": "not-run"}
    assert by_id["EX-97"]["quarantine"]["owner"] == "platform"
    assert run.passed


def test_a_receipt_entry_is_recorded_once():
    run = _run_receipt()
    run.add(not_run("EX-01"))
    with pytest.raises(ValueError):
        run.add(not_run("EX-01"))


def test_missing_names_rows_without_an_entry_and_entries_without_a_row():
    run = _run_receipt()
    run.add(not_run("EX-01"))
    run.add(not_run("ZZ-99"))
    assert run.missing(["EX-01", "EX-02"]) == {"missing": ["EX-02"], "unknown": ["ZZ-99"]}


def test_run_receipt_passed_is_false_on_a_failing_fixture():
    run = _run_receipt()
    run.add(FixtureReceipt(id="EX-01", status="ran", verdict="fail"))
    assert not run.passed


# ---- what a whole run's receipt never says ----------------------------------------------


_LEAF = re.compile(r"ROUNDS-\d{2}[A-Z]?-L\d{2}")


def _strings(value):
    """Every key and string value in a receipt, however deep."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def _whole_run(off: set[str]) -> RunReceipt:
    """The receipt a live run writes, built the way it builds one: every
    fixture without a module recorded up front, one fixture quarantined,
    and every other fixture run against a fake target."""
    import conftest as plugin

    man = m.load_manifest()
    run = _run_receipt()
    plugin.Session(man, {}, None, "", "", None, run, "ci").record_rows_that_dont_run()
    first, *rest = man.runnable()
    skip = m.Skip(first.id, "ci", "platform", _dt.date(2099, 1, 1), "flaky on shared runners")
    run.add(quarantined(first, skip, "ci"))
    for fx in rest:
        target = Target(off=set(off))
        module = importlib.import_module(f"corpus.{fx.module}")
        run.add(run_fixture(fx, module, target.context, target.canaries, "ci", deadline_seconds=0).receipt)
    assert run.missing(f.id for f in man.fixtures) == {"missing": [], "unknown": []}
    return run


@pytest.mark.parametrize("off", [set(), set(GUARANTEES)], ids=["guarantees-hold", "guarantees-off"])
def test_no_receipt_names_a_closing_leaf_or_says_pending(tmp_path, off):
    out = tmp_path / "receipt.json"
    _whole_run(off).write(str(out))
    loaded = json.loads(out.read_text())
    for text in _strings(loaded):
        assert text != "closing_leaf"
        assert "pending" not in text.lower(), text
        assert not _LEAF.search(text), text
    statuses = {entry["status"] for entry in loaded["fixtures"]}
    assert statuses == {"ran", "quarantined", "not-run"}
    for entry in loaded["fixtures"]:
        if entry["status"] == "not-run":
            assert entry == {"id": entry["id"], "status": "not-run"}


def test_evidence_is_capped_with_a_marker(monkeypatch):
    monkeypatch.setattr(r, "EVIDENCE_MAX_CHARS", 10)
    capped = cap_evidence({"a": "x" * 8, "b": "y" * 8, "c": "z"})
    assert capped["a"] == "x" * 8
    assert capped["b"] == "yy<truncated>"
    assert capped["c"] == "<truncated>"
