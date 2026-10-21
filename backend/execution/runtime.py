"""This replica's execution worker, from start to shutdown, and what
``/ready`` reports about it (ROUNDS-00A-L03).

1. ``ROUNDS_GATE_EXECUTION_STORE=off``, the default: nothing starts, and
   ``/ready`` is ready without the store.
2. ``on`` with no usable ``ROUNDS_EXECUTION_SECRET``: nothing starts, the
   start logs ``execution.worker`` with ``unconfigured``, and ``/ready``
   stays ready, so a deployment without the secret keeps serving. The
   secret is read once, at start.
3. ``on`` with the secret: the worker claims and reaps, and ``/ready`` is
   ready only while it's logged in as execution-worker, the executor is
   up, and the store answered within 30 s. A secret PocketBase doesn't
   take, or a store that's down, fails it.

``/health`` stays liveness and never looks at the store.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app import gates, obs
from execution import store
from execution.executor import LegacyExecutor
from execution.worker import Handler, Worker

_log = logging.getLogger(__name__)

# Each kind's handler.
# TODO(ROUNDS-00A-L03): PR 2 adds the scratch kinds and PR 3 the grading
# ones; until then a claimed job ends denied, definition-invalid.
HANDLERS: dict[str, Handler] = {}


class _Runtime:
    def __init__(self) -> None:
        self.mode = "off"
        self.worker: Worker | None = None
        self.task: asyncio.Task | None = None
        self.client: store.ServiceClient | None = None
        self.executor: LegacyExecutor | None = None


_runtime = _Runtime()


async def start(handlers: dict[str, Handler] | None = None, base_url: str | None = None) -> str:
    """Starts the worker when the store is on and the secret is usable.
    Answers the mode: ``off``, ``unconfigured``, or ``on``."""
    if gates.value("EXECUTION_STORE") != "on":
        _runtime.mode = "off"
        return _runtime.mode
    secret = store.secret_from_env()
    if secret is None:
        _runtime.mode = "unconfigured"
        obs.emit("execution.worker", code="unconfigured", service="runner")
        return _runtime.mode
    client = store.ServiceClient(secret, base_url=base_url)
    executor = LegacyExecutor()
    worker = Worker(client, executor, HANDLERS if handlers is None else handlers)
    _runtime.client, _runtime.executor, _runtime.worker = client, executor, worker
    _runtime.task = asyncio.create_task(worker.run())
    _runtime.mode = "on"
    obs.emit("execution.worker", code="started", service="runner")
    return _runtime.mode


async def stop() -> None:
    """Stops claiming and every run in flight, then closes the session."""
    worker, task = _runtime.worker, _runtime.task
    if worker is not None:
        await worker.stop()
    if task is not None:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    if _runtime.executor is not None:
        _runtime.executor.close()
    if _runtime.client is not None:
        await _runtime.client.aclose()
    _runtime.__init__()


def readiness() -> dict[str, Any]:
    """``{"ready", "store"}`` for /ready. ``store`` is the mode."""
    if _runtime.mode != "on":
        return {"ready": True, "store": _runtime.mode}
    worker = _runtime.worker
    return {"ready": worker is not None and worker.ready(), "store": "on"}
