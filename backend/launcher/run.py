"""One job in one worker (ROUNDS-00A-L05).

``run`` writes the job to the worker's stdin and closes it, then reads the
worker's stdout through frame protocol v1 (``worker/frames.py``), holding
every stream to its cap while it arrives, until init's end. It stops early
on a cancel, at the job's deadline plus ``GRACE_S`` (init ends each part at
its own wall time, so this is the backstop), on a stream that breaks the
protocol, or when the worker's stream ends without an end. Whatever came
before then is kept.

The launcher, not the worker, measures the worker: the engine's stats give
its CPU time, its ``nr_throttled`` count, and the highest memory any sample
saw, with one last sample at the end while the worker still exists, and the
engine's state gives its exit and whether the kernel killed it for memory.
What the worker wrote on stderr is never logged.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from launcher.engine import Engine, EngineError, STDERR, STDOUT
from launcher.pool import Worker
from worker import frames

GRACE_S = 2.0
RECV_S = 0.25
DIAG_MAX = 4096


@dataclass
class Measured:
    cpu_time_ms: int | None = None
    nr_throttled: int | None = None
    peak_memory_bytes: int | None = None

    def take(self, sample: dict[str, Any]) -> None:
        cpu = (sample.get("cpu_stats") or {})
        usage = (cpu.get("cpu_usage") or {}).get("total_usage")
        if isinstance(usage, int) and usage >= 0:
            self.cpu_time_ms = max(self.cpu_time_ms or 0, usage // 1_000_000)
        throttled = (cpu.get("throttling_data") or {}).get("throttled_periods")
        if isinstance(throttled, int) and throttled >= 0:
            self.nr_throttled = max(self.nr_throttled or 0, throttled)
        memory = (sample.get("memory_stats") or {}).get("usage")
        if isinstance(memory, int) and memory >= 0:
            self.peak_memory_bytes = max(self.peak_memory_bytes or 0, memory)


@dataclass
class Outcome:
    reader: frames.Reader
    # Why the launcher ended the worker before init's end, if it did:
    # canceled, wall_time, malformed, or lost.
    kill_reason: str | None
    started: float
    ended: float
    # When the first frame arrived, on the same clock as ``started``.
    first_frame_at: float | None
    measured: Measured = field(default_factory=Measured)
    exit_code: int | None = None
    oom: bool = False
    diag_bytes: int = 0


def run(engine: Engine, worker: Worker, job_id: str, archive: bytes, sha256: str, parts: int, deadline_ms: int,
        cancel: threading.Event, clock: Callable[[], float] = time.monotonic) -> Outcome:
    measured = Measured()
    stop_stats = threading.Event()
    sampler = threading.Thread(target=engine.stats_stream, args=(worker.cid, measured.take, stop_stats),
                               daemon=True, name="launcher-stats")
    sampler.start()
    reader = frames.Reader(parts=parts, ready_seen=True)
    kill_reason: str | None = None
    diag = 0
    started = clock()
    try:
        worker.attachment.send(frames.encode_input(job_id, archive, sha256))
        worker.attachment.close_write()
        give_up = started + deadline_ms / 1000 + GRACE_S
        while not reader.finished():
            if cancel.is_set():
                kill_reason = "canceled"
                break
            now = clock()
            if now >= give_up:
                kill_reason = "wall_time"
                break
            chunks = worker.attachment.recv(min(RECV_S, give_up - now))
            if chunks is None:
                kill_reason = "lost"
                break
            for stream, data in chunks:
                if stream == STDOUT:
                    reader.feed(data, now=clock())
                elif stream == STDERR:
                    diag += len(data)
    except frames.Malformed:
        kill_reason = "malformed"
    except (EngineError, OSError):
        kill_reason = "lost"
    ended = clock()
    if kill_reason is None:
        last = engine.stats_once(worker.cid)
        if last is not None:
            measured.take(last)
    stop_stats.set()
    try:
        engine.kill(worker.cid)
        state = (engine.inspect(worker.cid) or {}).get("State") or {}
    except EngineError:
        state = {}
    sampler.join(1.0)
    exit_code = state.get("ExitCode") if isinstance(state.get("ExitCode"), int) else None
    return Outcome(
        reader=reader, kill_reason=kill_reason, started=started, ended=ended, first_frame_at=reader.first_frame_at,
        measured=measured, exit_code=exit_code, oom=bool(state.get("OOMKilled")), diag_bytes=min(diag, DIAG_MAX),
    )
