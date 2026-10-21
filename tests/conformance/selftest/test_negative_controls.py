"""Negative controls: every committed fixture reports ``contained`` against
a target whose guarantee holds and ``detected`` once that guarantee is
switched off (issue #8, Required tests: Negative control).

The targets are the fakes in ``fakes.py``, which answer as the stack does
with and without each guarantee. Each fixture runs through
``run_fixture``, the same path the live plugin uses, so the verdict, the
sub-case outcomes, and the receipt entry are what a real run records.
"""
from __future__ import annotations

import importlib

import pytest

from conformance import manifest as m
from conformance.execute import run_fixture

from fakes import Target

MANIFEST = m.load_manifest()

# fixture id -> the guarantees whose removal it must detect.
CONTROLS = {
    "EX-01": ["account-step", "account-before-body"],
    "EX-02": ["owner-read", "uniform-missing"],
    "EX-03": ["demo-flags"],
    "EX-04": ["byte-cap", "caller-fields"],
    "EX-05": ["caller-fields"],
    "EX-06": ["caller-fields"],
    "EX-07": ["minimal-env"],
    "RD-07": ["health-status-only", "typed-render-failure"],
}


def _run_on(fixture_id: str, off: set[str]):
    fx = MANIFEST.by_id(fixture_id)
    module = importlib.import_module(f"corpus.{fx.module}")
    target = Target(off=set(off))
    return run_fixture(fx, module, target.context, target.canaries, "ci", deadline_seconds=0), target


def _run(fixture_id: str, off: set[str]):
    return _run_on(fixture_id, off)[0]


def test_every_committed_fixture_has_a_control():
    assert set(CONTROLS) == {f.id for f in MANIFEST.contained()}


@pytest.mark.parametrize("fixture_id", sorted(CONTROLS))
def test_contained_when_the_guarantee_holds(fixture_id):
    ran = _run(fixture_id, set())
    assert ran.passed, ran.message
    assert ran.receipt.outcome == "contained"
    contained = [s for s in ran.receipt.subcases if s["status"] == "contained"]
    assert contained and all(s["outcome"] == "contained" for s in contained)


@pytest.mark.parametrize(
    "fixture_id,guarantee",
    [(fid, g) for fid, guarantees in sorted(CONTROLS.items()) for g in guarantees],
)
def test_detected_when_the_guarantee_is_off(fixture_id, guarantee):
    ran = _run(fixture_id, {guarantee})
    assert not ran.passed
    assert ran.receipt.outcome == "detected", ran.message
    assert ran.receipt.verdict == "fail"
    assert fixture_id in ran.message


def test_ex01_requires_the_account_denial_itself():
    # A stack that refuses anonymous callers for any other reason, a body
    # error first, is not containing them at the account step.
    ran = _run("EX-01", {"account-before-body"})
    assert ran.receipt.outcome == "detected"
    assert "422" in ran.receipt.note


def test_ex07_canary_in_output_fails_and_is_redacted():
    ran, target = _run_on("EX-07", {"minimal-env"})
    assert not ran.passed
    assert [name for name, hit in ran.receipt.canary_hits.items() if hit]
    values = list(target.canaries.present_values().values())
    kept = "\n".join(ran.receipt.evidence.values())
    assert "<redacted:canary>" in kept
    for value in values:
        assert value not in kept
        assert value not in ran.message
        assert value not in ran.receipt.note and value not in ran.receipt.reason
