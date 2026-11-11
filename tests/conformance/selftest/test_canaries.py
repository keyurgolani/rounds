"""Self-test: the per-run canary set (issue #8, Required tests Unit)."""
from __future__ import annotations

import pytest

from conformance.canaries import CANARY_NAMES, CanaryMissing, CanarySet

PLANTED = {
    "AI_KEY_SECRET": "canary-aks-run7-deadbeef",
    "PB_ADMIN_EMAIL": "pbadmin-run7@canary.invalid",
    "PB_ADMIN_PASSWORD": "canary-pbpw-run7-cafe",
    "ROUNDS_ADMISSION_SECRET": "canary-adm-run7-f00d",
}


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


def test_from_env_reads_every_planted_value():
    cs = CanarySet.from_env(dict(PLANTED))
    assert cs.present_values() == PLANTED
    assert "ROUNDS_EXECUTION_SECRET" not in cs.present_values()


@pytest.mark.parametrize("missing", sorted(PLANTED))
def test_a_landed_canary_missing_from_the_run_fails_it(missing):
    env = dict(PLANTED)
    env.pop(missing)
    with pytest.raises(CanaryMissing, match=missing):
        CanarySet.from_env(env)


def test_an_empty_canary_counts_as_missing():
    env = dict(PLANTED, AI_KEY_SECRET="")
    with pytest.raises(CanaryMissing):
        CanarySet.from_env(env)


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
