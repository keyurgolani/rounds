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

``ROUNDS_GATE_EXECUTION_LAUNCHER`` (ROUNDS-00A-L05) is ``off`` or ``on``. No
route reads it yet; with it on, the start logs one ``execution.launcher``
line, ``configured``, or ``unconfigured`` naming the launcher URL or token
the runner is missing.
"""
from __future__ import annotations

from typing import Mapping

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


def launcher() -> str:
    """``ROUNDS_GATE_EXECUTION_LAUNCHER``: on or off (ROUNDS-00A-L05). No
    route reads it yet."""
    return gates.value("EXECUTION_LAUNCHER")


def launcher_missing(environ: Mapping[str, str] | None = None) -> list[str]:
    """The runner's launcher settings that are missing, by name."""
    from execution import launcher_client

    return launcher_client.settings(environ)[2]


def log_startup() -> None:
    """At start: when the scratch key is on but acts as off, one line naming
    the settings it needs; and with the launcher's gate on, one line saying
    whether the runner has its launcher settings."""
    if gates.value("EXECUTION_SCRATCH") == "on":
        needs = scratch_needs()
        if needs:
            obs.emit("execution.scratch", code="acting_off", needs=needs, service="runner")
    if launcher() == "on":
        missing = launcher_missing()
        if missing:
            obs.emit("execution.launcher", code="unconfigured", missing=missing, service="runner")
        else:
            obs.emit("execution.launcher", code="configured", service="runner")
