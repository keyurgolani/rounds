"""Self-test: the probe budget counts requests and wall-seconds and
refuses the request that would exceed either (issue #8, Required tests
Unit: probe-budget counting)."""
from __future__ import annotations

import pytest

from conformance.budget import Budget, BudgetExceeded


def test_charge_counts_requests_and_wall_seconds():
    b = Budget(max_requests=3, max_wall_seconds=10)
    b.charge(requests=1, wall_seconds=2.0)
    b.charge(requests=1, wall_seconds=3.0)
    assert b.requests == 2
    assert b.wall_seconds == pytest.approx(5.0)


def test_request_cap_is_enforced():
    b = Budget(max_requests=1, max_wall_seconds=10)
    b.charge(requests=1)
    with pytest.raises(BudgetExceeded):
        b.charge(requests=1)


def test_wall_cap_is_enforced():
    b = Budget(max_requests=5, max_wall_seconds=1.0)
    with pytest.raises(BudgetExceeded):
        b.charge(requests=1, wall_seconds=2.0)


def test_spend_counts_the_request_up_front():
    ticks = iter([100.0, 100.5])
    b = Budget(max_requests=1, max_wall_seconds=10, _clock=lambda: next(ticks))
    with b.spend():
        pass
    assert b.requests == 1
    assert b.wall_seconds == pytest.approx(0.5)
    with pytest.raises(BudgetExceeded):
        with b.spend():
            pass


def test_spend_counts_the_request_even_if_the_body_raises():
    b = Budget(max_requests=5, max_wall_seconds=10, _clock=lambda: 0.0)
    with pytest.raises(RuntimeError):
        with b.spend():
            raise RuntimeError("boom")
    assert b.requests == 1


def test_snapshot_reports_caps_and_spend():
    b = Budget(max_requests=25, max_wall_seconds=120)
    b.charge(requests=2, wall_seconds=1.5)
    snap = b.snapshot()
    assert snap == {"requests": 2, "max_requests": 25, "wall_seconds": 1.5, "max_wall_seconds": 120}


def test_a_request_that_takes_the_fixture_past_its_wall_cap_fails_it():
    ticks = iter([0.0, 3.0])
    b = Budget(max_requests=5, max_wall_seconds=2.0, _clock=lambda: next(ticks))
    with pytest.raises(BudgetExceeded, match="wall-second"):
        with b.spend():
            pass
    assert b.wall_seconds == pytest.approx(3.0)


def test_run_totals_sum_every_fixture():
    from conformance.budget import RunTotals

    totals = RunTotals()
    first = Budget(max_requests=10, max_wall_seconds=10)
    first.charge(requests=3, wall_seconds=1.0)
    totals.add(first)
    totals.add_spend({"requests": 2, "wall_seconds": 0.5})
    assert totals.snapshot() == {"fixtures": 2, "requests": 5, "wall_seconds": 1.5}


def test_the_deadline_stops_a_fixture_that_hangs():
    import time

    from conformance.budget import FixtureTimeout, deadline

    with pytest.raises(FixtureTimeout):
        with deadline(0.1):
            time.sleep(2)


def test_a_deadline_that_isnt_reached_changes_nothing():
    from conformance.budget import deadline

    with deadline(5):
        value = 1 + 1
    assert value == 2
