"""The execution worker (ROUNDS-00A-L03).

Each runner replica runs one while ``ROUNDS_GATE_EXECUTION_STORE`` is on
and ``ROUNDS_EXECUTION_SECRET`` logs in as ``execution-worker``:

1. Claim. While the replica has a free in-flight slot, it claims the
   oldest queued job of an account with fewer than 2 active, under a new
   fencing token. A claim reaps first.
2. Run. The job's kind's handler runs its parts through the executor in a
   slot. Before the first part, a heartbeat marks the candidate tree
   started with the attempt's wall budget, which is never more than the
   kind is admitted for. A kind with no handler here ends ``denied``,
   ``definition-invalid``, before anything runs, and a job that gets no
   slot in time ends ``timed-out``, ``infrastructure-degraded``.
3. Heartbeat every 10 s. A cancel the heartbeat reports stops the run,
   which ends ``canceled``. A heartbeat or complete the store refuses as
   superseded means the lease was lost: the run stops and its result is
   dropped, and the store already counted the write as rejected.
4. Complete. The envelope goes with both terminal states in one write.
   An exception in a handler is the infrastructure's failure, never the
   candidate's.
5. Reap every 15 s, beside the reap each claim runs.

Each step writes a ``execution.job`` line in #1's kit, labeled by kind,
purpose, state, outcome class, and executor kind, never by account.

No kind has a handler yet: PR 2 adds the scratch kinds and PR 3 the
grading ones.
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from app import obs, sandbox
from execution import envelope, kinds, store
from execution.envelope import Outcome, Part
from execution.executor import LegacyExecutor, Observation, Starved

_log = logging.getLogger(__name__)

HEARTBEAT_S = 10.0
REAP_EVERY_S = 15.0
# How long an idle claim loop waits before it asks again.
CLAIM_IDLE_S = 1.0
# How long a claimed job waits for a slot before it ends starved.
SLOT_WAIT_S = 5.0
# Backoff after a failed store call, up to the last.
BACKOFF_S = (1.0, 2.0, 5.0, 10.0, 15.0)
COMPLETE_TRIES = 3
# /ready holds while a store call answered within this long.
READY_WINDOW_S = 30.0
WORKER_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")


def worker_id(hostname: str | None = None) -> str:
    """This replica's name in the store: its hostname, lowercased and
    kept to the store's pattern."""
    name = re.sub(r"[^a-z0-9-]+", "-", (hostname or socket.gethostname()).lower()).strip("-")[:63]
    return name if WORKER_ID.fullmatch(name) else "runner"


@dataclass
class Result:
    """What a handler hands back for the envelope."""

    parts: list[Part]
    score: float | None = None
    output: dict[str, Any] | None = None
    definition: dict[str, Any] | None = None
    rubric: dict[str, Any] | None = None
    observation: Observation | None = None


class Handler(Protocol):
    def budget_s(self, job: store.Job) -> int:
        """The attempt's wall budget, at most the kind's ``max_budget_s``."""
        ...

    def run(self, job: store.Job, executor: LegacyExecutor, slot: sandbox.Sandbox, stop: threading.Event) -> Result:
        """Runs the job's parts and stops between them, and in one, once
        ``stop`` is set. Blocks; the worker calls it on the executor's
        threads."""
        ...


@dataclass
class _Attempt:
    claim: store.Claim
    stop: threading.Event = field(default_factory=threading.Event)
    canceled: bool = False
    lost: bool = False
    started_at: int | None = None


def _metric(metric: str, value: int = 1, job: store.Job | None = None, **labels: Any) -> None:
    if job is not None:
        labels.setdefault("kind", job.kind)
        labels.setdefault("purpose", job.purpose)
    obs.emit("execution.job", metric=metric, value=value, service="runner", **labels)


class Worker:
    def __init__(self, client: store.ServiceClient, executor: LegacyExecutor,
                 handlers: Mapping[str, Handler] | None = None, name: str | None = None) -> None:
        self._client = client
        self._executor = executor
        self._handlers = dict(handlers or {})
        self.name = name or worker_id()
        self._tasks: set[asyncio.Task] = set()
        self._attempts: dict[str, _Attempt] = {}
        self._stopping = asyncio.Event()
        self._last_ok: float | None = None
        self._claimed = 0

    # -- readiness ---------------------------------------------------------

    def _ok(self) -> None:
        self._last_ok = time.monotonic()

    def ready(self) -> bool:
        """Logged in, the executor up, and a store call answered within
        ``READY_WINDOW_S``."""
        return (
            self._client.logged_in
            and self._executor.healthy()
            and self._last_ok is not None
            and time.monotonic() - self._last_ok < READY_WINDOW_S
        )

    # -- the loops ---------------------------------------------------------

    async def run(self) -> None:
        """Claims and reaps until ``stop``."""
        reaper = asyncio.create_task(self._reap_loop())
        try:
            await self._claim_loop()
        finally:
            reaper.cancel()
            await asyncio.gather(reaper, return_exceptions=True)

    async def stop(self) -> None:
        """Stops claiming, stops every run in flight, and waits for their
        tasks to end."""
        self._stopping.set()
        for attempt in self._attempts.values():
            attempt.stop.set()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _pause(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stopping.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass

    async def _claim_loop(self) -> None:
        failures = 0
        while not self._stopping.is_set():
            if self._executor.free_slots() - self._claimed <= 0:
                await self._pause(CLAIM_IDLE_S)
                continue
            try:
                claim = await self._client.claim(self.name)
            except store.LoginRejected:
                obs.emit("execution.worker", code="login_rejected", service="runner")
                failures += 1
                await self._pause(BACKOFF_S[min(failures, len(BACKOFF_S)) - 1])
                continue
            except store.Unavailable:
                failures += 1
                await self._pause(BACKOFF_S[min(failures, len(BACKOFF_S)) - 1])
                continue
            failures = 0
            self._ok()
            self._reaped(claim.reaped if claim else None)
            if claim is None:
                await self._pause(CLAIM_IDLE_S * (0.5 + random.random()))
                continue
            self._claimed += 1
            task = asyncio.create_task(self._process(claim))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _reap_loop(self) -> None:
        while not self._stopping.is_set():
            await self._pause(REAP_EVERY_S)
            if self._stopping.is_set():
                return
            try:
                self._reaped(await self._client.reap())
                self._ok()
            except store.Unavailable:
                continue

    def _reaped(self, counts: Mapping[str, int] | None) -> None:
        if not counts:
            return
        expired = counts.get("requeued", 0) + counts.get("worker_lost", 0)
        if expired:
            _metric("rounds_job_lease_expired_total", expired)
        if counts.get("over_budget"):
            _metric("rounds_job_terminal_total", counts["over_budget"], state="failed",
                    outcome_class="infrastructure-degraded")

    # -- one job -----------------------------------------------------------

    async def _process(self, claim: store.Claim) -> None:
        job = claim.job
        attempt = _Attempt(claim)
        self._attempts[claim.attempt.id] = attempt
        _metric("rounds_job_queue_wait_seconds", max(0, int(time.time()) - job.queued_at), job)
        slot: sandbox.Sandbox | None = None
        waiting = True
        try:
            handler = self._handlers.get(job.kind)
            if job.kind not in kinds.KINDS or handler is None:
                self._claimed, waiting = self._claimed - 1, False
                await self._finish(attempt, envelope.outcome("denied", "definition-invalid"), "confirmed")
                return
            try:
                slot = await self._executor.acquire(SLOT_WAIT_S)
            except Starved:
                self._claimed, waiting = self._claimed - 1, False
                await self._finish(attempt, envelope.outcome("timed-out", "infrastructure-degraded"), "confirmed")
                return
            self._claimed, waiting = self._claimed - 1, False
            await self._run(attempt, handler, slot)
        except Exception:  # noqa: BLE001
            _log.exception("execution attempt failed")
        finally:
            if waiting:
                self._claimed -= 1
            self._attempts.pop(claim.attempt.id, None)
            if slot is not None:
                await self._executor.release(slot)

    async def _run(self, attempt: _Attempt, handler: Handler, slot: sandbox.Sandbox) -> None:
        job, claim = attempt.claim.job, attempt.claim
        kind = kinds.KINDS[job.kind]
        try:
            budget = max(1, min(int(handler.budget_s(job)), kind.max_budget_s))
            beat = await self._client.heartbeat(claim.attempt.id, claim.token, budget_s=budget)
        except store.Superseded:
            _metric("rounds_job_late_result_rejected_total", 1, job)
            return
        except (store.Unavailable, ValueError):
            # Nothing started; the lease runs out and reap puts the job back.
            return
        self._ok()
        attempt.started_at = int(time.time())
        if beat.cancel_requested:
            attempt.canceled = True
            attempt.stop.set()
        beats = asyncio.create_task(self._heartbeats(attempt))
        try:
            result: Result | None = await self._executor.call(handler.run, job, self._executor, slot, attempt.stop)
            failed = False
        except Exception:  # noqa: BLE001
            _log.exception("execution handler failed")
            result, failed = None, True
        finally:
            beats.cancel()
            await asyncio.gather(beats, return_exceptions=True)
        if attempt.lost:
            # The store already counted this attempt's writes as rejected.
            _metric("rounds_job_late_result_rejected_total", 1, job)
            return
        observation = result.observation if result else None
        cleanup = observation.cleanup if observation else "confirmed"
        if attempt.canceled:
            await self._finish(attempt, envelope.outcome("canceled", "canceled"), cleanup, result=result)
            return
        if failed or result is None:
            await self._finish(attempt, envelope.outcome("failed", "infrastructure-degraded"), cleanup)
            return
        try:
            outcome = envelope.aggregate(result.parts)
        except envelope.InvalidEnvelope:
            outcome = envelope.outcome("failed", "infrastructure-degraded")
        await self._finish(attempt, outcome, cleanup, result=result)

    async def _heartbeats(self, attempt: _Attempt) -> None:
        claim = attempt.claim
        while True:
            await asyncio.sleep(HEARTBEAT_S)
            try:
                beat = await self._client.heartbeat(claim.attempt.id, claim.token)
            except store.Superseded:
                attempt.lost = True
                attempt.stop.set()
                return
            except store.Unavailable:
                # The lease outlasts a missed beat; if it runs out, the
                # next one is superseded.
                continue
            self._ok()
            if beat.cancel_requested and not attempt.canceled:
                attempt.canceled = True
                attempt.stop.set()

    async def _finish(self, attempt: _Attempt, outcome: Outcome, cleanup: str, result: Result | None = None) -> None:
        job, claim = attempt.claim.job, attempt.claim
        scored = result is not None and outcome.outcome_class in ("passed", "candidate-failure")
        observation = result.observation if result else None
        kind = kinds.KINDS.get(job.kind)
        hidden = kind is not None and kind.hidden_material
        # TODO(ROUNDS-00A-L03): build_revision stays null until the runner
        # image carries its revision; image_digest until #5's launcher
        # reports it (ROUNDS-00A-L05).
        try:
            body = envelope.build(
                job_id=job.id,
                result=outcome,
                cleanup=cleanup,
                worker=self.name,
                attempt_number=claim.attempt.attempt_number,
                source_checksum=job.source_checksum,
                input_digest=job.input_digest,
                queued_at=job.queued_at,
                started_at=attempt.started_at,
                finished_at=int(time.time()),
                parts=result.parts if result else (),
                score=result.score if scored else None,
                definition=result.definition if result else None,
                rubric=result.rubric if result else None,
                output=result.output if result else None,
                executor_kind=self._executor.kind,
                output_sha256=observation.output_sha256 if observation else None,
                output_bytes=observation.output_bytes if observation else None,
                exit_status=observation.exit_status if observation else None,
                hidden_material=hidden,
            )
        except envelope.InvalidEnvelope:
            _log.exception("execution envelope invalid")
            outcome = envelope.outcome("failed", "infrastructure-degraded")
            body = envelope.build(
                job_id=job.id, result=outcome, cleanup=cleanup, worker=self.name,
                attempt_number=claim.attempt.attempt_number, source_checksum=job.source_checksum,
                input_digest=job.input_digest, queued_at=job.queued_at, started_at=attempt.started_at,
                finished_at=int(time.time()), executor_kind=self._executor.kind,
            )
        for tries in range(COMPLETE_TRIES):
            try:
                await self._client.complete(claim.attempt.id, claim.token, body)
            except store.Superseded:
                _metric("rounds_job_late_result_rejected_total", 1, job)
                return
            except store.Refused:
                _log.error("execution complete refused for a %s job", job.kind)
                return
            except store.Unavailable:
                if tries + 1 < COMPLETE_TRIES:
                    await asyncio.sleep(BACKOFF_S[tries])
                continue
            self._ok()
            labels = {"state": outcome.state, "outcome_class": outcome.outcome_class,
                      "executor_kind": self._executor.kind}
            _metric("rounds_job_terminal_total", 1, job, **labels)
            if attempt.started_at is not None:
                _metric("rounds_job_attempt_seconds", max(0, int(time.time()) - attempt.started_at), job, **labels)
            if cleanup == "unconfirmed":
                _metric("rounds_job_cleanup_unconfirmed_total", 1, job, executor_kind=self._executor.kind)
            return
