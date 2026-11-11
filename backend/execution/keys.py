"""The execution keys' effective values (ROUNDS-00A-L03 PR 2).

``ROUNDS_GATE_EXECUTION_SCRATCH`` decides how run, evaluate, run-project,
and take-home run execute:

- ``legacy``, the default: in their request, as before this leaf.
- ``on``: as durable jobs on the execution job store. That needs the store
  on (``ROUNDS_GATE_EXECUTION_STORE=on``) and server-owned definitions
  only (``ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce``), since a job runs a
  compiled definition the worker loads itself. Without either, ``on``
  acts as ``off``, never as ``legacy``, and the start logs an
  ``execution.scratch`` line naming what it needs.
- ``off``: the four routes answer 503 ``execution_disabled`` and every
  draft is kept. A queued scratch job a worker claims while the key isn't
  ``on`` ends ``canceled`` before anything runs.

Every reader asks ``scratch()``, so the routes, the worker, and the
startup line can't disagree.
"""
from __future__ import annotations

from app import gates, obs

SCRATCH_OPERATIONS = frozenset({"evaluate", "run", "take_home_run", "run_project"})
# What ``on`` needs, as NAME=value.
SCRATCH_NEEDS = (("EXECUTION_STORE", "on"), ("EXECUTION_DEFINITIONS", "enforce"))


def scratch_needs() -> list[str]:
    """The settings ``on`` is missing, as NAME=value; empty when none."""
    return [f"{name}={value}" for name, value in SCRATCH_NEEDS if gates.value(name) != value]


def scratch() -> str:
    """The scratch key's effective value: legacy, on, or off."""
    value = gates.value("EXECUTION_SCRATCH")
    if value == "on" and scratch_needs():
        return "off"
    return value


def log_startup() -> None:
    """At start: when the key is on but acts as off, one line naming the
    settings it needs."""
    if gates.value("EXECUTION_SCRATCH") == "on":
        needs = scratch_needs()
        if needs:
            obs.emit("execution.scratch", code="acting_off", needs=needs, service="runner")
