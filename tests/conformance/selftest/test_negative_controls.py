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
import json

import pytest

from conformance import manifest as m
from conformance.context import UNREACHABLE, Http
from conformance.execute import run_fixture

from fakes import FakeRunner, Target, _http, envelope

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
    "RD-07": ["health-status-only", "health-status-value", "typed-render-failure"],
}


def _run_on(fixture_id: str, off: set[str], target: Target | None = None):
    fx = MANIFEST.by_id(fixture_id)
    module = importlib.import_module(f"corpus.{fx.module}")
    target = target or Target(off=set(off))
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


def test_ex07_canary_in_output_fails_and_keeps_only_a_checksum_and_names():
    ran, target = _run_on("EX-07", {"minimal-env"})
    assert not ran.passed
    assert [name for name, hit in ran.receipt.canary_hits.items() if hit]
    # The output, which held the runner's environment, is never kept: only
    # its checksum and the names of the variables it shouldn't have had.
    assert set(ran.receipt.evidence) == {"output_sha256", "unexpected_names"}
    assert ran.receipt.evidence["output_sha256"].startswith("sha256:")
    assert set(ran.receipt.evidence["unexpected_names"].split(", ")) == set(target.canaries.present_values())
    values = list(target.canaries.present_values().values())
    kept = "\n".join(ran.receipt.evidence.values())
    for value in values:
        assert value not in kept
        assert value not in ran.message
        assert value not in ran.receipt.note and value not in ran.receipt.reason


def _answer_run_with_env(monkeypatch, env):
    real = FakeRunner._answer

    def answer(self, method, path, token, body):
        if path == "/api/run":
            return _http(200, {"stdout": "ENV:" + json.dumps(env), "stderr": "", "return_value": [], "error": None})
        return real(self, method, path, token, body)

    monkeypatch.setattr(FakeRunner, "_answer", answer)


def test_ex07_detects_a_variable_outside_the_minimal_environment_without_a_canary(monkeypatch):
    # A runner secret the corpus never planted would show only this way.
    unplanted = "unplanted-value-" + "7" * 24
    _answer_run_with_env(monkeypatch, [["HOME", "/scratch"], ["PATH", "/usr/bin"], ["UNPLANTED_TOKEN", unplanted]])
    ran, _ = _run_on("EX-07", set())
    assert not ran.passed and ran.receipt.outcome == "detected"
    assert ran.receipt.evidence["unexpected_names"] == "UNPLANTED_TOKEN"
    assert unplanted not in json.dumps(ran.receipt.evidence) and unplanted not in ran.message


def test_ex07_without_an_environment_listing_is_inconclusive(monkeypatch):
    real = FakeRunner._answer

    def answer(self, method, path, token, body):
        if path == "/api/run":
            return _http(200, {"stdout": "no listing", "stderr": "", "return_value": [], "error": None})
        return real(self, method, path, token, body)

    monkeypatch.setattr(FakeRunner, "_answer", answer)
    ran, _ = _run_on("EX-07", set())
    assert ran.receipt.outcome == "inconclusive"


@pytest.mark.parametrize("stop", ["route_disabled", "definitions_disabled"])
def test_ex01_counts_a_route_its_gate_turned_off_as_contained_by_the_gate(stop):
    ran, _ = _run_on("EX-01", set(), Target(gated={"/api/run": stop}))
    assert ran.passed, ran.message
    assert ran.receipt.outcome == "contained"
    assert f"contained by their gates: /api/run ({stop})" in ran.receipt.note
    assert f"POST /api/run -> 503 {stop} (contained by its gate)" in ran.receipt.evidence["answers"]


def test_ex01_still_detects_any_other_503():
    ran, _ = _run_on("EX-01", set(), Target(gated={"/api/run": "worker_unavailable"}))
    assert not ran.passed and ran.receipt.outcome == "detected"


def test_ex04_reads_a_runner_it_couldnt_reach_as_inconclusive_not_a_finding(monkeypatch):
    def unreachable(self, method, path, declared, *, timeout=10.0):
        self.log.add(method, path)
        return Http(0, None, "", {}, UNREACHABLE)

    monkeypatch.setattr(FakeRunner, "declare", unreachable)
    ran, _ = _run_on("EX-04", set())
    assert ran.receipt.outcome == "inconclusive"
    cap = {s["id"]: s.get("outcome") for s in ran.receipt.subcases}["EX-04.body-cap"]
    assert cap == "inconclusive"


@pytest.mark.parametrize("detail", [None, ["URLError"], {"text": "x"}, 503])
def test_rd07_records_a_failed_render_whose_detail_isnt_text(monkeypatch, detail):
    real = FakeRunner._answer

    def answer(self, method, path, token, body):
        if path == "/api/pdf/render":
            return _http(503, {**envelope("worker_unavailable"), "detail": detail})
        return real(self, method, path, token, body)

    monkeypatch.setattr(FakeRunner, "_answer", answer)
    ran, _ = _run_on("RD-07", set())
    assert ran.receipt.outcome == "detected"
    assert {s["id"]: s.get("outcome") for s in ran.receipt.subcases}["RD-07.render-failure-typed"] == "detected"
