"""Probe budget and per-fixture deadline for the containment corpus.

The deployment subset runs against a hosted demo under #1's default
quota, so a fixture may spend only so many requests and so many
wall-seconds per run (#8 body, Required tests: Deployment). Every request
a fixture makes goes through the context's clients, which charge the
budget themselves (``conformance.context``), so nothing a fixture sends
goes uncounted. The budget refuses the request that would pass the
request cap, and fails the fixture as soon as its wall time passes the
wall cap. The run keeps a total of every fixture's spend for the receipt.

``deadline`` bounds a whole fixture, its requests and everything between
them, so a fixture that hangs fails the lane instead of stalling it.
"""
from __future__ import annotations

import signal
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, Iterator


class BudgetExceeded(RuntimeError):
    """A fixture went past its request or wall-second cap."""


class FixtureTimeout(RuntimeError):
    """A fixture ran past its deadline."""


@dataclass
class Budget:
    max_requests: int
    max_wall_seconds: float
    requests: int = 0
    wall_seconds: float = 0.0
    _clock: Callable[[], float] = field(default=time.monotonic, repr=False)

    def charge(self, requests: int = 1, wall_seconds: float = 0.0) -> None:
        if self.requests + requests > self.max_requests:
            raise BudgetExceeded(f"request budget exhausted ({self.requests}/{self.max_requests})")
        if self.wall_seconds + wall_seconds > self.max_wall_seconds + 1e-9:
            raise BudgetExceeded(
                f"wall-second budget exhausted ({self.wall_seconds:.3f}/{self.max_wall_seconds})"
            )
        self.requests += requests
        self.wall_seconds += wall_seconds

    def spend(self) -> "_Spend":
        """Context manager around one request: counts it before it is sent
        and its wall time after, and fails once the wall cap is passed."""
        return _Spend(self)

    def snapshot(self) -> dict[str, float]:
        return {
            "requests": self.requests,
            "max_requests": self.max_requests,
            "wall_seconds": round(self.wall_seconds, 3),
            "max_wall_seconds": self.max_wall_seconds,
        }


class _Spend:
    def __init__(self, budget: Budget) -> None:
        self._budget = budget
        self._start = 0.0

    def __enter__(self) -> Budget:
        # Counted up front, so a fixture can't pass the request cap even if
        # the request raises.
        self._budget.charge(requests=1, wall_seconds=0.0)
        self._start = self._budget._clock()
        return self._budget

    def __exit__(self, exc_type, exc, tb) -> bool:
        elapsed = max(0.0, self._budget._clock() - self._start)
        self._budget.wall_seconds += elapsed
        if exc_type is None and self._budget.wall_seconds > self._budget.max_wall_seconds + 1e-9:
            raise BudgetExceeded(
                f"wall-second budget exhausted ({self._budget.wall_seconds:.3f}/{self._budget.max_wall_seconds})"
            )
        return False


@dataclass
class RunTotals:
    """Every fixture's spend in one run, for the receipt."""

    fixtures: int = 0
    requests: int = 0
    wall_seconds: float = 0.0

    def add(self, budget: Budget) -> None:
        self.add_spend(budget.snapshot())

    def add_spend(self, spend: dict[str, float]) -> None:
        """One fixture's spend, as its receipt entry's ``budget`` holds it."""
        self.fixtures += 1
        self.requests += int(spend.get("requests", 0))
        self.wall_seconds += float(spend.get("wall_seconds", 0.0))

    def snapshot(self) -> dict[str, float]:
        return {"fixtures": self.fixtures, "requests": self.requests, "wall_seconds": round(self.wall_seconds, 3)}


@contextmanager
def deadline(seconds: float) -> Iterator[None]:
    """Raise ``FixtureTimeout`` in the main thread once ``seconds`` pass.

    Uses SIGALRM, so it applies on the main thread of a POSIX process (the
    corpus container, CI). Elsewhere it bounds nothing, and each request's
    own timeout and the budget's wall cap still apply.
    """
    usable = hasattr(signal, "setitimer") and threading.current_thread() is threading.main_thread()
    if not usable or seconds <= 0:
        yield
        return

    def expire(_signum, _frame):
        raise FixtureTimeout(f"fixture ran past its {seconds:g}s deadline")

    previous = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
