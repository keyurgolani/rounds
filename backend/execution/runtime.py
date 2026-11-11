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

``/health`` stays liveness and never looks at the store. A job-backed
route asks ``accepting_jobs`` first (PR 2): only while this replica's
worker is up and ready does it charge and enqueue anything.
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

# Each kind's handler: the scratch kinds' (PR 2).
# TODO(ROUNDS-00A-L03): PR 3 adds the grading kinds' handlers; until then
# a claimed grading job ends denied, definition-invalid.
def default_handlers() -> dict[str, Handler]:
    # Imported here: the handlers import the routers, which import this.
    from execution import handlers

    return dict(handlers.SCRATCH_HANDLERS)


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
    worker = Worker(client, executor, default_handlers() if handlers is None else handlers)
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


def accepting_jobs() -> bool:
    """Whether this replica's worker runs and is ready: logged in, its
    executor up, and the store answering. A job-backed route needs that
    before it charges or enqueues, so a down store or a secret PocketBase
    doesn't take fails closed with the draft still on the page."""
    worker = _runtime.worker
    return _runtime.mode == "on" and worker is not None and worker.ready()
