"""Self-test: the per-run canary set (issue #8, Required tests Unit:
the fixture builder's canary handling)."""
from __future__ import annotations

from conformance.canaries import CANARY_NAMES, CanarySet


def test_generate_sets_present_values_and_leaves_absent_ones_none():
    cs = CanarySet.generate("run7")
    by_name = {c.name: c for c in cs.canaries}
    assert set(by_name) == set(CANARY_NAMES)
    assert by_name["AI_KEY_SECRET"].present
    assert by_name["AI_KEY_SECRET"].value and "run7" in by_name["AI_KEY_SECRET"].value
    # Introduced by later leaves; absent here.
    assert not by_name["ROUNDS_EXECUTION_SECRET"].present
    assert by_name["ROUNDS_EXECUTION_SECRET"].value is None
    assert by_name["ROUNDS_EXECUTION_SECRET"].landed_by == "ROUNDS-00A-L03"


def test_from_env_reads_planted_values(monkeypatch):
    monkeypatch.setenv("AI_KEY_SECRET", "canary-aks-run7-deadbeef")
    monkeypatch.delenv("ROUNDS_EXECUTION_SECRET", raising=False)
    cs = CanarySet.from_env()
    vals = cs.present_values()
    assert vals["AI_KEY_SECRET"] == "canary-aks-run7-deadbeef"
    assert "ROUNDS_EXECUTION_SECRET" not in vals


def test_hits_detects_a_present_value_only():
    cs = CanarySet.generate("run7")
    value = cs.present_values()["AI_KEY_SECRET"]
    hits = cs.hits(f"leaked {value} here")
    assert hits["AI_KEY_SECRET"] is True
    assert hits["ROUNDS_EXECUTION_SECRET"] is False
    assert cs.any_hit(f"x {value} y")
    assert not cs.any_hit("nothing here")


def test_env_maps_present_canaries_to_variables():
    cs = CanarySet.generate("run7")
    env = cs.env()
    assert env["AI_KEY_SECRET"] == cs.present_values()["AI_KEY_SECRET"]
    assert "ROUNDS_EXECUTION_SECRET" not in env
