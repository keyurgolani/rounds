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
