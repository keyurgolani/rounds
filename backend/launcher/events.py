"""The launcher's ``execution.launcher`` lines in #1's kit (ROUNDS-00A-L05).

Each is one JSON line on stdout with the kit's allowlisted fields only: a
code, what a start is missing, a metric and its value, and a reason. None
carries a job, an account, a container, or anything a worker wrote.

Codes: ``started`` (with the slots, the pre-start count, the runtime, and
``engine: dedicated``, since the worker daemon serves this launcher alone),
``refused`` (with what is missing), ``slot_quarantined``, ``stopped``.
"""
from __future__ import annotations

import logging
from typing import Any

from app import obs

SERVICE = "launcher"
_log = logging.getLogger("rounds.launcher")


def emit(code: str, **fields: Any) -> dict[str, Any]:
    return obs.emit("execution.launcher", code=code, service=SERVICE, **fields)


def metric(name: str, value: int = 1, **labels: Any) -> dict[str, Any]:
    return obs.emit("execution.launcher", metric=name, value=max(0, int(value)), service=SERVICE, **labels)


def started(slots: int, prestart: int, runtime: str, removed: int) -> None:
    emit("started", slots=slots, prestart=prestart, runtime=runtime, engine="dedicated")
    # The same fact in words for whoever reads the log first.
    _log.warning(
        "launcher started with %d slots: its worker daemon serves this launcher only, and at start it removed "
        "%d workers an earlier run left.", slots, removed,
    )


def refused(missing: list[str]) -> None:
    emit("refused", missing=sorted(set(missing)))
    _log.error("launcher refused to start; missing: %s", ", ".join(sorted(set(missing))))
