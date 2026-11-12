"""The launcher's HTTP routes (ROUNDS-00A-L05).

Every route needs ``Authorization: Bearer <ROUNDS_LAUNCHER_TOKEN>``,
compared in constant time; anything else gets 401 before routing. Only the
runner, on the internal ``exec`` network, holds the token.

- ``POST /v1/jobs``: job spec v1 and its archive (``launcher/jobspec.py``).
  A body past its cap is 413 and a spec or archive outside v1 is 400
  ``job_rejected`` with a reason, both before any worker exists. A refused
  or not-ready launcher answers 503 ``not_ready``, a full queue 503
  ``saturated``, and a job id already running 409. Otherwise the job runs
  in one worker and the answer is ``rounds.launcher-result/v1``: the
  launcher observation (``rounds.launcher-observation/v1``) and what each
  part's frames carried, base64. A caller that disconnects cancels its job.
- ``POST /v1/jobs/{job_id}/cancel``: ends the job's worker if it is running.
- ``GET /v1/jobs/{job_id}``: the job's cleanup, ``pending`` until the engine
  reports its worker gone, then ``confirmed`` or, after a cleanup failure,
  ``unconfirmed``.
- ``GET /ready``: 200 while the launcher started and has a slot that isn't
  quarantined, else 503 with what is missing.
- ``GET /health``: liveness.
"""
from __future__ import annotations

import asyncio
import base64
import hmac
import logging
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from launcher import events, jobspec, pool as slots, run as runner
from launcher.engine import Engine
from worker import frames, manifest

RESULT_VERSION = "rounds.launcher-result/v1"
OBSERVATION_VERSION = "rounds.launcher-observation/v1"
# How long an answer waits for its worker's destruction before it says
# pending.
DESTROY_REPORT_S = 2.0
FINISHED_KEPT = 1024


class TooLarge(Exception):
    pass


@dataclass
class Handle:
    job_id: str
    cancel: threading.Event
    cid: str | None = None


class State:
    def __init__(self, token: str | None, engine: Engine | None = None, pool: slots.Pool | None = None,
                 image: str | None = None, runtime: str = "runc", missing: list[str] | None = None,
                 wall: Callable[[], float] = time.time, clock: Callable[[], float] = time.monotonic) -> None:
        self.token = token
        self.engine = engine
        self.pool = pool
        self.image = image
        self.runtime = runtime
        self.missing = list(missing or [])
        self.wall = wall
        self.clock = clock
        self.jobs: dict[str, Handle] = {}
        self.finished: OrderedDict[str, str | None] = OrderedDict()
        self.lock = threading.Lock()
        size = pool.size if pool is not None else 1
        self.executor = ThreadPoolExecutor(max_workers=3 * size + 4, thread_name_prefix="launcher-job")

    @property
    def started(self) -> bool:
        return self.pool is not None and not self.missing


class TokenGate:
    """Refuses every request without the launcher's token, before routing."""

    def __init__(self, app: Any, token: str | None) -> None:
        self.app = app
        self.expected = f"Bearer {token}".encode() if token else None

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") == "http":
            given = dict(scope.get("headers") or []).get(b"authorization", b"")
            if self.expected is None or not hmac.compare_digest(given, self.expected):
                await JSONResponse({"code": "unauthorized"}, status_code=401)(scope, receive, send)
                return
        await self.app(scope, receive, send)


async def _body(request: Request, limit: int) -> bytes:
    declared = request.headers.get("content-length")
    if declared is not None and (not declared.isdigit() or int(declared) > limit):
        raise TooLarge
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise TooLarge
        chunks.append(chunk)
    return b"".join(chunks)


def _b64(data: bytes | bytearray | None) -> str | None:
    return None if data is None else base64.b64encode(bytes(data)).decode("ascii")


def _ms(epoch: float | None) -> int | None:
    return None if epoch is None else int(epoch * 1000)


def _observation(state: State, spec: jobspec.Spec, received: float, **fields: Any) -> dict[str, Any]:
    out = {
        "version": OBSERVATION_VERSION, "job_id": spec.job_id, "kind": spec.kind, "image": state.image,
        "runtime": state.runtime, "profile": jobspec.profile.PROFILE_VERSION, "received_at": _ms(received),
        "started_at": None, "ended_at": None, "destroyed_at": None, "first_byte_ms": None, "queue_ms": 0,
        "start_ms": None, "prestarted": False, "cpu_time_ms": None, "nr_throttled": None, "peak_memory_bytes": None,
        "peak_tasks": None, "exit_code": None, "oom": False, "kill_reason": None, "end": False, "setup": None, "residue": False,
        "bytes": {"out": 0, "err": 0, "result": 0, "verdict": 0}, "truncated": False, "cleanup": "unconfirmed",
        "parts": [], "verdict_step": None,
    }
    out.update(fields)
    return out


def _starved(state: State, spec: jobspec.Spec, received: float, queue_ms: int, start_ms: int | None) -> dict[str, Any]:
    events.metric("rounds_worker_kill_total", reason="starved")
    # A queue wait created nothing; a start that ran out of time may have
    # left a worker, which the reaper removes by its label.
    cleanup = "confirmed" if start_ms is None else "unconfirmed"
    return {"version": RESULT_VERSION,
            "observation": _observation(state, spec, received, queue_ms=queue_ms, start_ms=start_ms,
                                        kill_reason="starved", cleanup=cleanup),
            "output": {"parts": [], "verdict": None}}


def execute(state: State, handle: Handle, spec: jobspec.Spec, archive: bytes, job: manifest.Job) -> dict[str, Any]:
    """Runs one job; blocks. Answers the result body."""
    received, began = state.wall(), state.clock()
    try:
        slot = state.pool.acquire(slots.QUEUE_WAIT_S)
    except slots.Starved:
        return _starved(state, spec, received, int((state.clock() - began) * 1000), None)
    queue_ms = int((state.clock() - began) * 1000)
    worker = None
    try:
        try:
            worker = state.pool.take_worker(slot)
        except slots.Starved:
            return _starved(state, spec, received, queue_ms, int((state.clock() - began) * 1000) - queue_ms)
        handle.cid = worker.cid
        started_wall = state.wall()
        outcome = runner.run(state.engine, worker, spec.job_id, archive, spec.archive_sha256, len(job.parts),
                             spec.deadline_ms, handle.cancel, clock=state.clock)
    finally:
        cid = state.pool.release(slot) if worker is not None else None
    cleanup, destroyed = state.pool.wait_destroyed(cid, DESTROY_REPORT_S)
    reader = outcome.reader
    end = reader.end
    if worker.prestarted is False:
        events.metric("rounds_worker_start_ms", worker.start_ms)
    first_byte = None if outcome.first_frame_at is None else int((outcome.first_frame_at - began) * 1000)
    if first_byte is not None:
        events.metric("rounds_worker_first_byte_ms", first_byte)
    if outcome.kill_reason is not None:
        events.metric("rounds_worker_kill_total", reason=outcome.kill_reason)
    parts_out = []
    sizes = {"out": 0, "err": 0, "result": 0, "verdict": 0}
    for index in range(len(job.parts)):
        streams = reader.part(index)
        for name in ("out", "err", "result", "verdict"):
            value = getattr(streams, name)
            sizes[name] += len(value) if value is not None else 0
        parts_out.append({"id": job.parts[index].id, "out": _b64(streams.out), "err": _b64(streams.err),
                          "result": _b64(streams.result), "verdict": _b64(streams.verdict)})
    job_verdict = reader.streams.get(frames.JOB_PART)
    if job_verdict is not None and job_verdict.verdict is not None:
        sizes["verdict"] += len(job_verdict.verdict)
    entries = end["parts"] if end is not None else []
    truncated = any(e["truncated"] or e["verdict_truncated"] for e in entries)
    for entry in entries:
        if entry["truncated"]:
            events.metric("rounds_worker_cap_hit_total", reason="output")
        if entry["limit"] in ("wall_time", "files"):
            events.metric("rounds_worker_kill_total", reason=entry["limit"])
    observation = _observation(
        state, spec, received, started_at=_ms(started_wall),
        ended_at=_ms(started_wall + (outcome.ended - outcome.started)), destroyed_at=_ms(destroyed),
        first_byte_ms=first_byte, queue_ms=queue_ms, start_ms=None if worker.prestarted else worker.start_ms,
        prestarted=worker.prestarted, cpu_time_ms=outcome.measured.cpu_time_ms,
        nr_throttled=outcome.measured.nr_throttled, peak_memory_bytes=outcome.measured.peak_memory_bytes,
        peak_tasks=outcome.measured.peak_tasks, exit_code=outcome.exit_code, oom=outcome.oom, kill_reason=outcome.kill_reason, end=end is not None,
        setup=end["setup"] if end is not None else None, residue=bool(end and end["residue"]), bytes=sizes,
        truncated=truncated, cleanup=cleanup, parts=entries, verdict_step=end["verdict"] if end is not None else None,
    )
    return {"version": RESULT_VERSION, "observation": observation,
            "output": {"parts": parts_out,
                       "verdict": _b64(job_verdict.verdict) if job_verdict is not None else None}}


def create_app(state: State) -> Any:
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def ready(_request: Request) -> JSONResponse:
        if not state.started:
            return JSONResponse({"ready": False, "missing": sorted(set(state.missing))}, status_code=503)
        counts = state.pool.status()
        ok = counts["quarantined"] < counts["slots"]
        return JSONResponse({"ready": ok, "missing": [] if ok else ["capacity"], **counts},
                            status_code=200 if ok else 503)

    async def submit(request: Request) -> JSONResponse:
        if request.headers.get("content-type", "").split(";")[0].strip() != jobspec.CONTENT_TYPE:
            return JSONResponse({"code": "job_rejected", "reason": "content_type"}, status_code=400)
        try:
            body = await _body(request, jobspec.BODY_MAX)
        except TooLarge:
            return JSONResponse({"code": "job_rejected", "reason": "body_size"}, status_code=413)
        try:
            spec, archive = jobspec.parse(body)
            job = jobspec.check(spec, archive)
        except jobspec.Rejected as err:
            return JSONResponse({"code": "job_rejected", "reason": err.code}, status_code=400)
        if not state.started:
            return JSONResponse({"code": "not_ready", "missing": sorted(set(state.missing))}, status_code=503)
        handle = Handle(spec.job_id, threading.Event())
        with state.lock:
            if spec.job_id in state.jobs:
                return JSONResponse({"code": "job_in_flight"}, status_code=409)
            state.jobs[spec.job_id] = handle
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(state.executor, execute, state, handle, spec, archive, job)
        try:
            while True:
                done, _pending = await asyncio.wait({future}, timeout=0.5)
                if done:
                    break
                if await request.is_disconnected():
                    handle.cancel.set()
            try:
                result = future.result()
            except slots.Saturated:
                return JSONResponse({"code": "saturated"}, status_code=503)
            except Exception:  # noqa: BLE001
                # Our own fault, never the candidate's; its message names no
                # job content.
                logging.getLogger("rounds.launcher").exception("a job failed inside the launcher")
                return JSONResponse({"code": "launcher_error"}, status_code=500)
        finally:
            with state.lock:
                state.jobs.pop(spec.job_id, None)
                state.finished[spec.job_id] = handle.cid
                while len(state.finished) > FINISHED_KEPT:
                    state.finished.popitem(last=False)
        return JSONResponse(result)

    async def cancel(request: Request) -> JSONResponse:
        job_id = request.path_params["job_id"]
        if not jobspec.JOB_ID.fullmatch(job_id):
            return JSONResponse({"code": "job_rejected", "reason": "job_id"}, status_code=400)
        with state.lock:
            handle = state.jobs.get(job_id)
        if handle is not None:
            handle.cancel.set()
        return JSONResponse({"canceled": handle is not None})

    async def status(request: Request) -> JSONResponse:
        job_id = request.path_params["job_id"]
        if not jobspec.JOB_ID.fullmatch(job_id):
            return JSONResponse({"code": "job_rejected", "reason": "job_id"}, status_code=400)
        with state.lock:
            running = job_id in state.jobs
            cid = state.finished.get(job_id)
            known = running or job_id in state.finished
        if running:
            return JSONResponse({"cleanup": "pending"})
        if not known or state.pool is None:
            return JSONResponse({"cleanup": "unconfirmed"})
        return JSONResponse({"cleanup": state.pool.destruction(cid)[0]})

    app = Starlette(routes=[
        Route("/health", health, methods=["GET"]),
        Route("/ready", ready, methods=["GET"]),
        Route("/v1/jobs", submit, methods=["POST"]),
        Route("/v1/jobs/{job_id}/cancel", cancel, methods=["POST"]),
        Route("/v1/jobs/{job_id}", status, methods=["GET"]),
    ])
    return TokenGate(app, state.token)
