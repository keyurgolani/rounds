"""Probe budget for the containment corpus.

The deployment subset runs against a hosted demo under #1's default
quota, so a fixture may spend only so many requests and so many
wall-seconds per run (#8 body, Required tests: Deployment). The budget
counts both and refuses the request that would exceed either, so a
misbehaving fixture fails loudly here rather than tripping the
deployment's own quota. Each fixture gets its own budget; the plugin
sums them for the run and records the spend in the receipt.

The budget only counts and caps; it issues nothing itself. A fixture
calls :meth:`spend` around each request it makes.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    """A fixture tried to spend past its request or wall-second cap."""


@dataclass
class Budget:
    max_requests: int
    max_wall_seconds: float
    requests: int = 0
    wall_seconds: float = 0.0
    _clock: "callable" = field(default=time.monotonic, repr=False)

    def charge(self, requests: int = 1, wall_seconds: float = 0.0) -> None:
        if self.requests + requests > self.max_requests:
            raise BudgetExceeded(
                f"request budget exhausted ({self.requests}/{self.max_requests})"
            )
        if self.wall_seconds + wall_seconds > self.max_wall_seconds + 1e-9:
            raise BudgetExceeded(
                f"wall-second budget exhausted ({self.wall_seconds:.3f}/{self.max_wall_seconds})"
            )
        self.requests += requests
        self.wall_seconds += wall_seconds

    def spend(self):
        """Context manager that counts one request and the wall time it
        took. Raises :class:`BudgetExceeded` before the request if the
        request count is already at the cap."""
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

    def __enter__(self) -> "Budget":
        # Count the request up front so a fixture cannot exceed the request
        # cap even if it raises mid-request.
        self._budget.charge(requests=1, wall_seconds=0.0)
        self._start = self._budget._clock()
        return self._budget

    def __exit__(self, *exc) -> None:
        elapsed = self._budget._clock() - self._start
        # The request was already counted; add only its wall time, and never
        # let a slow request alone blow the wall cap retroactively.
        self._budget.wall_seconds += max(0.0, elapsed)
