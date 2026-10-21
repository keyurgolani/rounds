"""Self-test: the per-fixture rules in ``conformance.execute.run_fixture``
(issue #8, Required tests Unit: outcome comparison, redaction, probe
budget, receipt serialization)."""
from __future__ import annotations

import datetime as _dt
import time
import types

from conformance import manifest as m
from conformance.budget import BudgetExceeded
from conformance.execute import quarantined, run_fixture
from conformance.outcomes import Outcome
from corpus._base import result

from fakes import Target

MANIFEST = m.load_manifest()
EX07 = MANIFEST.by_id("EX-07")
EX02 = MANIFEST.by_id("EX-02")


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
