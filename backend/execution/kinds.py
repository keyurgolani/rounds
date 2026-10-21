"""The execution kinds and the states every job moves through
(ROUNDS-00A-L03).

A job moves ``queued``, ``leased``, ``started``, then to its attempt's
terminal state, and ``TERMINAL`` says which outcome classes each terminal
state ends with and which of those are authoritative. Each kind names its
purpose (scratch or grading), its job class in #2's ``resource-profile/v1``
(interactive or project), and the admission operation it's admitted
under. Its wall budget per part, one run, case, or checkpoint, is
today's budget for the route, never more than its job class's
``wall_s_max``; its most for an attempt is what admission admits the
operation for.

``pocketbase/pb_hooks/execution.js`` declares the same kinds, states, and
classes, and ``pb_hooks/admission.js`` the most each operation is
admitted for; tests/test_execution_kinds.py keeps the three in step.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

PROFILE_PATH = Path(__file__).resolve().parents[1] / "definitions" / "profiles" / "execution-default.v1.json"

STATES = ("queued", "leased", "started", "completed", "timed-out", "denied", "canceled", "failed")
ACTIVE_STATES = ("leased", "started")
OUTCOME_CLASSES = (
    "passed", "candidate-failure", "resource-limit", "definition-invalid", "policy-violation", "canceled",
    "worker-lost", "infrastructure-degraded",
)


@dataclass(frozen=True)
class Terminal:
    classes: tuple[str, ...]
    authoritative: tuple[str, ...]


TERMINAL: dict[str, Terminal] = {
    "completed": Terminal(("passed", "candidate-failure", "resource-limit"),
                          ("passed", "candidate-failure", "resource-limit")),
    # infrastructure-degraded only on executor-recorded slot or queue
    # starvation, or CPU throttling once #5 reports it.
    "timed-out": Terminal(("resource-limit", "infrastructure-degraded"), ("resource-limit",)),
    "denied": Terminal(("definition-invalid", "policy-violation"), ()),
    "canceled": Terminal(("canceled",), ()),
    "failed": Terminal(("worker-lost", "infrastructure-degraded"), ()),
}
# A same-key retry re-queues a job whose last attempt ended with one of
# these, while fewer than MAX_STARTED attempts have started.
RETRYABLE = ("worker-lost", "infrastructure-degraded")
MAX_STARTED = 3
CLEANUP = ("pending", "confirmed", "unconfirmed")
# The limits a resource-limit names. Only wall_time is enforced until #5.
LIMITS = ("wall_time", "cpu_time", "memory", "processes", "files", "output")
PURPOSES = ("scratch", "grading")
JOB_CLASSES = ("interactive", "project")


@dataclass(frozen=True)
class Kind:
    name: str
    purpose: str
    job_class: str
    operation: str
    # Today's wall budget for one run, case, or checkpoint.
    part_wall_s: int
    max_parts: int
    states: tuple[str, ...] = STATES
    outcome_classes: tuple[str, ...] = OUTCOME_CLASSES

    @property
    def max_budget_s(self) -> int:
        """The most an attempt declares, which is what admission admits
        the operation for."""
        return self.part_wall_s * self.max_parts


KINDS: dict[str, Kind] = {
    kind.name: kind
    for kind in (
        Kind("run", "scratch", "interactive", "run", part_wall_s=3, max_parts=1),
        # Up to 32 cases, each at its time class, 10 s at most.
        Kind("evaluate", "scratch", "interactive", "evaluate", part_wall_s=10, max_parts=32),
        Kind("run_project", "scratch", "interactive", "run_project", part_wall_s=10, max_parts=1),
        Kind("take_home_run", "scratch", "project", "take_home_run", part_wall_s=60, max_parts=1),
        # Up to 8 checkpoints in order, 45 s each.
        Kind("grade", "grading", "project", "grade", part_wall_s=45, max_parts=8),
        Kind("take_home_submit", "grading", "project", "take_home_submit", part_wall_s=120, max_parts=1),
    )
}


@lru_cache(maxsize=1)
def profile(path: Path = PROFILE_PATH) -> dict[str, Any]:
    """The resource profile the job classes come from."""
    return json.loads(path.read_text())


def part_wall_s(name: str) -> int:
    """One part's wall budget for kind ``name``: today's, capped at its
    job class's ``wall_s_max``."""
    kind = KINDS[name]
    return min(kind.part_wall_s, profile()["job_classes"][kind.job_class]["wall_s_max"])


def is_terminal(state: str) -> bool:
    return state in TERMINAL


def authoritative(state: str, outcome_class: str) -> bool:
    terminal = TERMINAL.get(state)
    return terminal is not None and outcome_class in terminal.authoritative
