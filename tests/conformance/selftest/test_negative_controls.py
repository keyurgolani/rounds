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
from conformance import overlay
from conformance.context import UNREACHABLE, Http
from conformance.execute import run_fixture
from corpus import rd_07_render_no_echo as RD07
from corpus._requests import TAKE_HOME, bodies

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
    "RD-01": ["snapshot-owner"],
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
    assert set(CONTROLS) == {f.id for f in MANIFEST.runnable()}


@pytest.mark.parametrize("fixture_id", sorted(CONTROLS))
def test_contained_when_the_guarantee_holds(fixture_id):
    ran = _run(fixture_id, set())
    assert ran.passed, ran.message
    assert ran.receipt.outcome == "contained"
    # One entry per sub-case the spec lists, each contained.
    assert [s["id"] for s in ran.receipt.subcases] == MANIFEST.by_id(fixture_id).subcases
    assert all(s["outcome"] == "contained" for s in ran.receipt.subcases)


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


@pytest.mark.parametrize("stop", ["route_disabled", "definitions_disabled"])
def test_ex01_with_every_route_gated_tested_nothing_and_is_inconclusive(stop):
    # A gate stop never reaches the account step, so it can't stand in
    # for the 401 on every route at once.
    every_route = {path: stop for _, path in bodies()}
    ran, _ = _run_on("EX-01", set(), Target(gated=every_route))
    assert not ran.passed
    assert (ran.receipt.outcome, ran.receipt.verdict) == ("inconclusive", "fail")
    assert {s["id"]: s.get("outcome") for s in ran.receipt.subcases}["EX-01.anonymous-denied"] == "inconclusive"
    assert "no route reached the account step" in ran.receipt.note
    assert "401" not in ran.receipt.evidence["answers"]


def test_ex01_still_detects_any_other_503():
    ran, _ = _run_on("EX-01", set(), Target(gated={"/api/run": "worker_unavailable"}))
    assert not ran.passed and ran.receipt.outcome == "detected"


def test_ex05_runs_the_corpus_take_home_definition_and_refuses_the_field_there():
    ran, _ = _run_on("EX-05", set())
    assert ran.passed, ran.message
    assert "POST /api/take-home/run" in ran.receipt.routes
    answers = ran.receipt.evidence["answers"].splitlines()
    assert "/api/take-home/run without the field -> 200 None" in answers
    assert "/api/take-home/run -> 422 legacy_request_rejected" in answers


def _answer_take_home_run(monkeypatch, status, body):
    real = FakeRunner._answer

    def answer(self, method, path, token, json_body):
        if path == "/api/take-home/run" and "test_command" not in json_body:
            return _http(status, body)
        return real(self, method, path, token, json_body)

    monkeypatch.setattr(FakeRunner, "_answer", answer)


@pytest.mark.parametrize("status,body", [
    # The corpus definition missing from the stack: the overlay wasn't mounted.
    (410, envelope("definition_retired")),
    (404, envelope("definition_not_found")),
    # A run, but of another definition than the one the body named.
    (200, {"score": 0.0, "definition": {**{k: TAKE_HOME[k] for k in ("track", "variant")}, "slug": "another",
                                        "content_version": TAKE_HOME["version"]}}),
    # A run that names none.
    (200, {"score": 0.0}),
])
def test_ex05_is_inconclusive_when_the_take_home_run_doesnt_run_the_corpus_definition(monkeypatch, status, body):
    # The refusal still holds, but it was never checked against an active
    # take-home definition, so the take-home route proves nothing.
    _answer_take_home_run(monkeypatch, status, body)
    ran, _ = _run_on("EX-05", set())
    assert not ran.passed
    assert (ran.receipt.outcome, ran.receipt.verdict) == ("inconclusive", "fail")
    assert "the corpus take-home definition didn't run" in ran.receipt.note


def test_ex05_still_detects_an_accepted_field_when_the_take_home_definition_is_missing(monkeypatch):
    # The worst outcome wins: a missing definition doesn't hide a finding.
    _answer_take_home_run(monkeypatch, 410, envelope("definition_retired"))
    ran, _ = _run_on("EX-05", {"caller-fields"})
    assert ran.receipt.outcome == "detected"


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


def _answer_pdf(monkeypatch, route, status, body):
    real = FakeRunner._answer

    def answer(self, method, path, token, json_body):
        if path == route:
            return _http(status, body)
        return real(self, method, path, token, json_body)

    monkeypatch.setattr(FakeRunner, "_answer", answer)


@pytest.mark.parametrize("status,value", [(503, "ok"), (200, "unavailable"), (500, "unavailable")])
def test_rd07_requires_healths_own_status_code_with_its_value(monkeypatch, status, value):
    _answer_pdf(monkeypatch, "/api/pdf/health", status, {"status": value})
    ran, _ = _run_on("RD-07", set())
    assert ran.receipt.outcome == "detected"
    assert {s["id"]: s.get("outcome") for s in ran.receipt.subcases}["RD-07.health-status-only"] == "detected"


@pytest.mark.parametrize("status,value", [(200, "ok"), (503, "unavailable")])
def test_rd07_takes_either_health_answer_with_its_code(monkeypatch, status, value):
    _answer_pdf(monkeypatch, "/api/pdf/health", status, {"status": value})
    ran, _ = _run_on("RD-07", set())
    assert ran.passed, ran.message


@pytest.mark.parametrize("status,code,detail", [
    # Text no list of renderer strings would catch: only the exact
    # sentence passes.
    (503, "worker_unavailable", "Render failed: upstream said no."),
    (503, "worker_unavailable", "The runner is busy or unavailable. Try again shortly."),
    # The right sentence under another code's status.
    (500, "worker_unavailable", "The PDF renderer couldn't finish this document. Try again shortly."),
    (503, "render_timeout", "This document took too long to render. Simplify it and try again."),
])
def test_rd07_requires_the_failed_renders_exact_sentence_and_status(monkeypatch, status, code, detail):
    _answer_pdf(monkeypatch, "/api/pdf/render", status, envelope(code, detail))
    ran, _ = _run_on("RD-07", set())
    assert ran.receipt.outcome == "detected"
    assert {s["id"]: s.get("outcome") for s in ran.receipt.subcases}["RD-07.render-failure-typed"] == "detected"


def test_rd07_takes_a_render_timeout_with_its_sentence(monkeypatch):
    status, sentence = RD07.RENDER_FAILURES["render_timeout"]
    _answer_pdf(monkeypatch, "/api/pdf/render", status, envelope("render_timeout", sentence))
    ran, _ = _run_on("RD-07", set())
    assert ran.passed, ran.message


def test_rd01_is_inconclusive_when_even_the_owners_render_is_refused(monkeypatch):
    # A route that refuses every render would also refuse another
    # account's, which proves nothing about the owner check.
    _answer_pdf(monkeypatch, "/api/pdf/render", 404, envelope("not_found", "Not found."))
    ran, _ = _run_on("RD-01", set())
    assert not ran.passed
    assert ran.receipt.outcome == "inconclusive"


def test_rd01_reads_a_snapshot_with_the_wrong_checksum_as_refused_by_the_route(monkeypatch):
    # Only the caller's own snapshot with its checksum reaches the renderer.
    real = FakeRunner._answer

    def answer(self, method, path, token, body):
        if path == "/api/pdf/render":
            body = {**body, "expected_checksum": "sha256:" + "f" * 64}
        return real(self, method, path, token, body)

    monkeypatch.setattr(FakeRunner, "_answer", answer)
    ran, _ = _run_on("RD-01", set())
    assert ran.receipt.outcome == "inconclusive"


def test_rd07_sentences_are_the_backends():
    # The fixture's sentences and codes are the proxy's own, so a reworded
    # sentence fails here first, not as a live finding.
    backend = overlay.repo_root() / "backend"
    pdf = (backend / "routers" / "pdf.py").read_text(encoding="utf-8")
    errors = (backend / "app" / "errors.py").read_text(encoding="utf-8")
    status, sentence = RD07.RENDER_FAILURES["worker_unavailable"]
    assert f'RENDER_FAILED = "{sentence}"' in pdf
    assert 'TypedError("worker_unavailable", RENDER_FAILED)' in pdf
    assert f'"worker_unavailable": {status},' in errors
    status, sentence = RD07.RENDER_FAILURES["render_timeout"]
    assert 'TypedError("render_timeout")' in pdf
    assert f'"render_timeout": "{sentence}",' in errors
    assert f'"render_timeout": {status},' in errors
    assert 'return {"status": "ok"}' in pdf
    assert 'JSONResponse({"status": "unavailable"}, status_code=503)' in pdf
