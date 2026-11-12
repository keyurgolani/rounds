"""The execution keys' effective values (ROUNDS-00A-L03 PRs 2 to 4).

``ROUNDS_GATE_EXECUTION_SCRATCH`` decides how run, evaluate, run-project,
and take-home run execute, and ``ROUNDS_GATE_EXECUTION_GRADING`` how grade,
take-home submit, and their two review routes do (PR 3). Each takes the
same values, and since PR 4 each starts ``on``:

- ``on``: as durable jobs on the execution job store. That needs the store
  on (``ROUNDS_GATE_EXECUTION_STORE=on``, also the default), server-owned
  definitions only (``ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce``), since a
  job runs a compiled definition the worker loads itself, and the two
  secrets a job uses on this runner: ``ROUNDS_EXECUTION_SECRET``, which its
  worker logs in with, and ``ROUNDS_ADMISSION_SECRET``, which each job's
  admission and enqueue carry. Without any of them, ``on`` acts as ``off``,
  and the start logs an ``execution.scratch`` or ``execution.grading`` line
  naming each missing setting, never a value.
- ``off``: the routes answer 503 ``execution_disabled`` and every draft is
  kept. A queued job a worker claims while its key isn't ``on`` ends
  ``canceled`` before anything runs.
- ``legacy``: the value that ran each in its request until PR 4. It acts as
  ``off``, and the start says so, so no value runs code in a request.

Every reader asks ``scratch()`` or ``grading()``, so the routes, the
worker, and the startup line can't disagree. Each of the six routes also
calls ``require_on`` before it reads its body. The worker asks with
``worker=True``, which needs the gates only: whichever replica took the
request admitted and enqueued the job, and the worker that claimed it is
logged in, so a job runs on a replica whose own routes lack the admission
secret.
"""
from __future__ import annotations

from app import admission_state, gates, obs
from app.errors import TypedError
from execution import store

SCRATCH_OPERATIONS = frozenset({"evaluate", "run", "take_home_run", "run_project"})
# Grade, take-home submit, and the rubric review of either (PR 3).
GRADING_OPERATIONS = frozenset({"grade", "take_home_submit", "review"})
# What ``on`` needs of the gates, as NAME=value. Both keys need the same.
SCRATCH_NEEDS = (("EXECUTION_STORE", "on"), ("EXECUTION_DEFINITIONS", "enforce"))
GRADING_NEEDS = SCRATCH_NEEDS
# And the secrets it needs on this runner, by name only (PR 4).
SECRET_NEEDS = (store.SECRET_ENV, admission_state.RUNNER_KEY_ENV)
KEYS = {"EXECUTION_SCRATCH": ("execution.scratch", SCRATCH_NEEDS),
        "EXECUTION_GRADING": ("execution.grading", GRADING_NEEDS)}
# The fixed sentence a grading route answers while its key is off.
GRADING_OFF = "Grading practice code is turned off on this server."


def _missing_secrets() -> list[str]:
    """The secrets a job needs that this runner lacks or can't use, by
    name."""
    missing = []
    if store.secret_from_env() is None:
        missing.append(store.SECRET_ENV)
    try:
        admission_state.runner_key()
    except admission_state.Unconfigured:
        missing.append(admission_state.RUNNER_KEY_ENV)
    return missing


def _gate_needs(pairs: tuple[tuple[str, str], ...]) -> list[str]:
    return [f"{name}={value}" for name, value in pairs if gates.value(name) != value]


def _needs(pairs: tuple[tuple[str, str], ...]) -> list[str]:
    return _gate_needs(pairs) + _missing_secrets()


def _effective(name: str, worker: bool = False) -> str:
    value = gates.value(name)
    if value == "legacy":
        return "off"
    pairs = KEYS[name][1]
    if value == "on" and (_gate_needs(pairs) if worker else _needs(pairs)):
        return "off"
    return value


def scratch_needs() -> list[str]:
    """What the scratch key's ``on`` is missing: gate settings as
    NAME=value, then secrets by name; empty when none."""
    return _needs(SCRATCH_NEEDS)


def grading_needs() -> list[str]:
    """What the grading key's ``on`` is missing, as ``scratch_needs``
    names it; empty when none."""
    return _needs(GRADING_NEEDS)


def scratch(worker: bool = False) -> str:
    """The scratch key's effective value: on or off. With ``worker``, the
    value a claimed job runs under, which needs the gates only."""
    return _effective("EXECUTION_SCRATCH", worker)


def grading(worker: bool = False) -> str:
    """The grading key's effective value: on or off. With ``worker``, the
    value a claimed job runs under, which needs the gates only."""
    return _effective("EXECUTION_GRADING", worker)


def for_operation(operation: str) -> str | None:
    """The effective value of the key an admitted operation runs under, or
    None for an operation neither key covers."""
    if operation in SCRATCH_OPERATIONS:
        return scratch()
    if operation in GRADING_OPERATIONS:
        return grading()
    return None


def require_on(operation: str) -> None:
    """503 ``execution_disabled``, as admission step 2 answers, unless the
    key ``operation`` runs under is ``on``. The six execution routes call
    it first, so none of them runs anything in its request at any value."""
    if for_operation(operation) != "on":
        raise TypedError("execution_disabled", GRADING_OFF if operation in GRADING_OPERATIONS else None)


def log_startup() -> None:
    """At start: for each key set to ``legacy``, one line saying it acts as
    off; for each key that's on but acts as off, one line naming what it
    needs."""
    for name, (event, pairs) in KEYS.items():
        value = gates.value(name)
        if value == "legacy":
            obs.emit(event, code="legacy_retired", service="runner")
        elif value == "on":
            needs = _needs(pairs)
            if needs:
                obs.emit(event, code="acting_off", needs=needs, service="runner")
