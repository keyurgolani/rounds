"""Self-test: outcome comparison and the denial classifier (issue #8,
Required tests Unit: outcome comparison)."""
from __future__ import annotations

from conformance.outcomes import Outcome, classify_denial, decide


def test_contained_meets_a_contained_expectation():
    v = decide(Outcome.CONTAINED.value, "contained")
    assert v.passed and v.outcome == "contained"


def test_detected_fails_a_contained_expectation():
    v = decide(Outcome.DETECTED.value, "contained")
    assert not v.passed and v.outcome == "detected"


def test_inconclusive_always_fails():
    v = decide(Outcome.INCONCLUSIVE.value, "contained")
    assert not v.passed and v.outcome == "inconclusive"


def test_not_applicable_met_passes_and_is_recorded_not_applicable():
    v = decide(Outcome.NOT_APPLICABLE.value, "not-applicable")
    assert v.passed and v.outcome == "not-applicable"


def test_a_not_applicable_expectation_is_met_only_by_not_applicable():
    for observed in (Outcome.CONTAINED.value, Outcome.DETECTED.value, Outcome.INCONCLUSIVE.value):
        v = decide(observed, "not-applicable")
        assert not v.passed and v.outcome in ("detected", "inconclusive"), observed


def test_contained_expected_but_surface_absent_is_a_finding():
    v = decide(Outcome.NOT_APPLICABLE.value, "contained")
    assert not v.passed and v.outcome == "detected"


def test_denial_classifier():
    assert classify_denial(401)
    assert classify_denial(413)
    assert classify_denial(503)
    assert not classify_denial(200)
    assert not classify_denial(500)
