"""The execution keys' effective values (ROUNDS-00A-L03 PRs 2 and 3).

``ROUNDS_GATE_EXECUTION_SCRATCH`` decides how run, evaluate, run-project,
and take-home run execute, and ``ROUNDS_GATE_EXECUTION_GRADING`` how grade,
take-home submit, and their two review routes do (PR 3). Each takes the
same three values:

- ``legacy``, the default: in their request, as before this leaf.
- ``on``: as durable jobs on the execution job store. That needs the store
  on (``ROUNDS_GATE_EXECUTION_STORE=on``) and server-owned definitions
  only (``ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce``), since a job runs a
  compiled definition the worker loads itself. Without either, ``on``
  acts as ``off``, never as ``legacy``, and the start logs an
  ``execution.scratch`` or ``execution.grading`` line naming what it needs.
- ``off``: the routes answer 503 ``execution_disabled`` and every draft is
  kept. A queued job a worker claims while its key isn't ``on`` ends
  ``canceled`` before anything runs.

Every reader asks ``scratch()`` or ``grading()``, so the routes, the
worker, and the startup line can't disagree.
"""
from __future__ import annotations

from app import gates, obs

SCRATCH_OPERATIONS = frozenset({"evaluate", "run", "take_home_run", "run_project"})
# Grade, take-home submit, and the rubric review of either (PR 3).
GRADING_OPERATIONS = frozenset({"grade", "take_home_submit", "review"})
# What ``on`` needs, as NAME=value. Both keys need the same.
SCRATCH_NEEDS = (("EXECUTION_STORE", "on"), ("EXECUTION_DEFINITIONS", "enforce"))
GRADING_NEEDS = SCRATCH_NEEDS
KEYS = {"EXECUTION_SCRATCH": ("execution.scratch", SCRATCH_NEEDS),
        "EXECUTION_GRADING": ("execution.grading", GRADING_NEEDS)}


def _needs(pairs: tuple[tuple[str, str], ...]) -> list[str]:
    return [f"{name}={value}" for name, value in pairs if gates.value(name) != value]


def _effective(name: str) -> str:
    value = gates.value(name)
    if value == "on" and _needs(KEYS[name][1]):
        return "off"
    return value


def scratch_needs() -> list[str]:
    """The settings the scratch key's ``on`` is missing, as NAME=value;
    empty when none."""
    return _needs(SCRATCH_NEEDS)


def grading_needs() -> list[str]:
    """The settings the grading key's ``on`` is missing, as NAME=value;
    empty when none."""
    return _needs(GRADING_NEEDS)


def scratch() -> str:
    """The scratch key's effective value: legacy, on, or off."""
    return _effective("EXECUTION_SCRATCH")


def grading() -> str:
    """The grading key's effective value: legacy, on, or off."""
    return _effective("EXECUTION_GRADING")


def for_operation(operation: str) -> str | None:
    """The effective value of the key an admitted operation runs under, or
    None for an operation neither key covers."""
    if operation in SCRATCH_OPERATIONS:
        return scratch()
    if operation in GRADING_OPERATIONS:
        return grading()
    return None


def log_startup() -> None:
    """At start: for each key that's on but acts as off, one line naming
    the settings it needs."""
    for name, (event, pairs) in KEYS.items():
        if gates.value(name) == "on":
            needs = _needs(pairs)
            if needs:
                obs.emit(event, code="acting_off", needs=needs, service="runner")
