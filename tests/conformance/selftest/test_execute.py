"""Self-test: the per-fixture rules in ``conformance.execute.run_fixture``
(issue #8, Required tests Unit: outcome comparison, redaction, probe
budget, receipt serialization)."""
from __future__ import annotations

import datetime as _dt
import time
import types

import pytest

from conformance import execute
from conformance import manifest as m
from conformance.budget import BudgetExceeded
from conformance.execute import fixtures_decided, quarantined, run_fixture
from conformance.outcomes import Outcome
from corpus._base import not_applicable, result, whole

from fakes import Target

MANIFEST = m.load_manifest()
EX07 = MANIFEST.by_id("EX-07")
EX02 = MANIFEST.by_id("EX-02")
# A runnable not-applicable row: a surface this branch doesn't have yet.
NA = m.Fixture(
    id="EX-09", attack="a surface this branch doesn't have", spec_ref="selftest", status="not-applicable",
    closing_leaf="ROUNDS-00A-L05", routes=["POST /api/run"], languages=[], control="selftest",
    destructive=False, environment_sensitive=False, setup="none", teardown="none", module="selftest_only",
    reason="the surface lands with ROUNDS-00A-L05",
)


def _module(run):
    return types.SimpleNamespace(run=run)


def _go(fx, run, target=None, **kwargs):
    target = target or Target()
    return run_fixture(fx, _module(run), target.context, target.canaries, "ci", deadline_seconds=0, **kwargs), target


def _exercise(ctx, *routes):
    for method, path in routes:
        ctx.runner.request(method, path, token="token-1", json_body={})


def test_a_contained_result_passes_and_records_routes_and_pending_subcases():
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value}, "fine", evidence={"out": "ok"})

    ran, _ = _go(EX07, run)
    assert ran.passed, ran.message
    assert ran.receipt.routes == ["POST /api/run"]
    statuses = {s["id"]: s["status"] for s in ran.receipt.subcases}
    assert statuses == {"EX-07.candidate-env-minimal": "contained", "EX-07.other-process-env": "pending"}
    pending = [s for s in ran.receipt.subcases if s["status"] == "pending"]
    assert pending[0]["closing_leaf"] == "ROUNDS-00A-L05"
    assert ran.receipt.note == "fine" and ran.receipt.evidence == {"out": "ok"}


def test_a_canary_seen_fails_even_when_the_fixture_says_contained():
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        leaked = next(iter(ctx.canaries.present_values().values()))
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value}, "", canary_text=f"x {leaked} y")

    ran, _ = _go(EX07, run)
    assert not ran.passed
    assert ran.receipt.outcome == Outcome.DETECTED.value
    assert "canary seen" in ran.receipt.reason


def test_a_canary_only_in_the_evidence_also_fails_and_is_redacted():
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        leaked = next(iter(ctx.canaries.present_values().values()))
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value}, "", evidence={"out": leaked})

    ran, target = _go(EX07, run)
    assert not ran.passed
    assert ran.receipt.evidence["out"] == "<redacted:canary>"
    assert all(v not in ran.message for v in target.canaries.present_values().values())


def test_a_listed_route_not_exercised_fails():
    def run(ctx):
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value})

    ran, _ = _go(EX07, run)
    assert not ran.passed
    assert "not exercised" in ran.receipt.reason


def test_a_contained_subcase_without_an_outcome_is_inconclusive():
    def run(ctx):
        _exercise(ctx, *[tuple(r.split(" ", 1)) for r in EX02.routes])
        return result({"EX-02.result-read-denied": Outcome.CONTAINED.value})

    ran, _ = _go(EX02, run)
    assert not ran.passed
    assert ran.receipt.outcome == Outcome.INCONCLUSIVE.value
    assert "no outcome for EX-02.foreign-reads-as-missing" in ran.receipt.reason


def test_an_outcome_for_an_unlisted_subcase_fails():
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value, "EX-07.made-up": "contained"})

    ran, _ = _go(EX07, run)
    assert not ran.passed
    assert "doesn't list" in ran.receipt.reason


def test_a_fixture_that_raises_is_inconclusive_with_its_error():
    def run(ctx):
        raise RuntimeError("stack went away")

    ran, _ = _go(EX07, run)
    assert not ran.passed
    assert ran.receipt.outcome == Outcome.INCONCLUSIVE.value
    assert "RuntimeError: stack went away" in ran.receipt.reason


def test_running_past_the_request_budget_fails_the_fixture():
    def run(ctx):
        for _ in range(5):
            ctx.runner.request("POST", "/api/run", token="token-1", json_body={})
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value})

    ran, _ = _go(EX07, run, max_requests=3)
    assert not ran.passed
    assert BudgetExceeded.__name__ in ran.receipt.reason
    assert ran.receipt.budget["requests"] == 3


def test_running_past_the_deadline_fails_the_fixture():
    def run(ctx):
        time.sleep(5)
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value})

    target = Target()
    ran = run_fixture(EX07, _module(run), target.context, target.canaries, "ci", deadline_seconds=0.2)
    assert not ran.passed
    assert "FixtureTimeout" in ran.receipt.reason


def test_a_failed_teardown_fails_the_fixture():
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        acct = ctx.new_account("x")
        ctx.admin_pb.delete = lambda *a, **k: types.SimpleNamespace(status=500)
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value}, acct.tag)

    ran, _ = _go(EX07, run)
    assert not ran.passed
    assert "teardown" in ran.receipt.reason


def test_every_request_is_counted_including_the_pocketbase_client():
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        ctx.pb.view("users", "nope", token="token-1")
        ctx.pb.listing("users", token="token-1")
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value})

    ran, _ = _go(EX07, run)
    assert ran.receipt.budget["requests"] == 3
    assert "GET /api/collections/users/records" in ran.receipt.routes


def test_a_quarantined_fixture_gets_an_entry_with_owner_and_expiry():
    skip = m.Skip("EX-07", "ci", "platform", _dt.date(2099, 1, 1), "flaky on shared runners")
    entry = quarantined(EX07, skip, "ci")
    assert entry.status == "quarantined"
    assert entry.quarantine == {"owner": "platform", "expiry": "2099-01-01", "reason": "flaky on shared runners"}


# ---- not-applicable is an outcome of its own ------------------------------------------


def test_a_not_applicable_row_passes_as_not_applicable():
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        return not_applicable("the surface is still absent")

    ran, _ = _go(NA, run)
    assert ran.passed, ran.message
    assert (ran.receipt.outcome, ran.receipt.expectation, ran.receipt.verdict) == (
        "not-applicable", "not-applicable", "pass")


@pytest.mark.parametrize("outcome", [Outcome.CONTAINED.value, Outcome.DETECTED.value])
def test_a_not_applicable_row_whose_surface_answers_fails(outcome):
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        return whole(outcome, "the surface answered")

    ran, _ = _go(NA, run)
    assert not ran.passed
    assert (ran.receipt.outcome, ran.receipt.verdict) == ("detected", "fail")


def test_a_not_applicable_row_with_a_problem_is_inconclusive_never_met():
    def run(ctx):
        # Never exercises its route.
        return not_applicable("the surface is still absent")

    ran, _ = _go(NA, run)
    assert not ran.passed
    assert (ran.receipt.outcome, ran.receipt.verdict) == ("inconclusive", "fail")
    assert "not exercised" in ran.receipt.reason


def test_a_not_applicable_row_without_an_outcome_is_inconclusive():
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        return result({})

    ran, _ = _go(NA, run)
    assert (ran.receipt.outcome, ran.receipt.verdict) == ("inconclusive", "fail")
    assert "no outcome for the fixture" in ran.receipt.reason


def test_a_problem_never_leaves_contained_beside_a_failing_verdict():
    def run(ctx):
        # Contained, but the listed route never ran.
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value})

    ran, _ = _go(EX07, run)
    assert (ran.receipt.outcome, ran.receipt.verdict) == ("inconclusive", "fail")
    subcase = {s["id"]: s for s in ran.receipt.subcases}["EX-07.candidate-env-minimal"]
    assert subcase["outcome"] == "contained"


# ---- whatever a fixture hands back is recorded ------------------------------------------


@pytest.mark.parametrize("shape, problem", [
    (types.SimpleNamespace(subcases={"EX-07.candidate-env-minimal": 3}, evidence={}, canary_text="", note=""),
     "not an outcome"),
    (types.SimpleNamespace(subcases={"EX-07.candidate-env-minimal": "kind of"}, evidence={}, canary_text="",
                           note=""), "not an outcome"),
    (types.SimpleNamespace(subcases=["contained"], evidence="text", canary_text=b"bytes", note=7),
     "aren't a mapping"),
    ("not a result", "no outcome for EX-07.candidate-env-minimal"),
])
def test_a_result_in_the_wrong_shape_is_a_recorded_failure(shape, problem):
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        return shape

    ran, _ = _go(EX07, run)
    assert ran.receipt.id == "EX-07"
    assert (ran.receipt.outcome, ran.receipt.verdict) == ("inconclusive", "fail")
    assert problem in ran.receipt.reason


def test_evidence_and_canary_text_that_arent_text_are_read_as_text():
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        leaked = next(iter(ctx.canaries.present_values().values()))
        return types.SimpleNamespace(subcases={"EX-07.candidate-env-minimal": "contained"},
                                     evidence={"listing": [leaked, 1]}, canary_text={"seen": leaked}, note=None)

    ran, target = _go(EX07, run)
    assert (ran.receipt.outcome, ran.receipt.verdict) == ("detected", "fail")
    assert "canary seen" in ran.receipt.reason
    for value in target.canaries.present_values().values():
        assert value not in ran.receipt.evidence["listing"] and value not in ran.message


def test_a_canary_that_survives_redaction_is_withheld_and_fails_with_an_entry(monkeypatch):
    monkeypatch.setattr(execute, "redact", lambda text, values: text)

    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        leaked = next(iter(ctx.canaries.present_values().values()))
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value}, evidence={"out": leaked})

    ran, target = _go(EX07, run)
    assert not ran.passed and ran.receipt.verdict == "fail"
    assert ran.receipt.evidence["out"] == "<withheld: a canary survived redaction>"
    assert "survived redaction of out" in ran.receipt.reason
    for value in target.canaries.present_values().values():
        assert value not in ran.message


# ---- accounts are torn down whatever stops their sign-in ----------------------------------


@pytest.mark.parametrize("sign_in", ["auth-fails", "answer-lost"])
def test_an_account_whose_signup_landed_is_torn_down(sign_in):
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        ctx.new_account("x")
        return result({"EX-07.candidate-env-minimal": Outcome.CONTAINED.value})

    target = Target(sign_in=sign_in)
    ran, _ = _go(EX07, run, target=target)
    assert not ran.passed and ran.receipt.outcome == "inconclusive"
    assert "teardown" not in ran.receipt.reason
    assert target.pb.rows["users"] == {}


def test_an_account_that_cant_be_looked_up_fails_the_run():
    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        ctx.admin_pb.listing = lambda *a, **k: types.SimpleNamespace(status=500, body=None)
        ctx.new_account("x")

    ran, _ = _go(EX07, run, target=Target(sign_in="answer-lost"))
    assert "teardown left accounts behind: 1" in ran.receipt.reason


def test_an_account_whose_signup_never_landed_needs_no_teardown():
    def no_signup(acct):
        raise TimeoutError("no connection")

    def run(ctx):
        _exercise(ctx, ("POST", "/api/run"))
        ctx.register_account = no_signup
        ctx.new_account("x")

    ran, target = _go(EX07, run, target=Target(sign_in="answer-lost"))
    assert "teardown" not in ran.receipt.reason
    assert target.pb.rows["users"] == {}


# ---- the lane fails when no fixture ran ---------------------------------------------------


def _report(nodeid):
    return types.SimpleNamespace(nodeid=nodeid)


COVERAGE = "test_corpus.py::test_every_manifest_row_has_a_receipt_entry"
FIXTURE = "test_corpus.py::test_fixture[EX-07]"


def test_only_fixture_cases_count_as_decided():
    assert fixtures_decided([_report(COVERAGE)]) == 0
    assert fixtures_decided([_report(FIXTURE), _report(COVERAGE)]) == 1


@pytest.mark.parametrize("passed, failed, exits", [
    ([COVERAGE], [], 1),
    ([], [], 1),
    ([COVERAGE, FIXTURE], [], 0),
    ([COVERAGE], [FIXTURE], 0),
])
def test_the_lane_fails_when_every_fixture_was_skipped(monkeypatch, passed, failed, exits):
    import conftest as plugin

    monkeypatch.setenv("CORPUS_RUN", "1")
    stats = {"passed": [_report(n) for n in passed], "failed": [_report(n) for n in failed],
             "skipped": [_report("test_corpus.py::test_fixture[EX-01]")]}
    reporter = types.SimpleNamespace(stats=stats, write_line=lambda *a, **k: None)
    plugins = types.SimpleNamespace(get_plugin=lambda name: reporter)
    session = types.SimpleNamespace(exitstatus=0, config=types.SimpleNamespace(pluginmanager=plugins))
    plugin.pytest_sessionfinish(session, 0)
    assert session.exitstatus == exits
