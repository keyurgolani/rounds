"""The executor port and its legacy adapter (ROUNDS-00A-L03).

A job's processes run through an ``Executor``: ``run`` one process for
one part, ``cancel`` a run in flight, and ``cleanup_status`` of a run.

``LegacyExecutor`` runs them in this replica, the way the routes run
candidate code today (app/sandbox.py: a minimal environment, a private
scratch directory, a candidate uid in the image, and a process group per
child), on a pool of 4 threads with the replica's 4 in-flight slots,
which it shares with the admitted routes (``admission.pool()``):

1. Wall time: a run gets its part's budget, then its process group is
   killed and the run reports the ``wall_time`` limit.
2. Output: each stream keeps at most the profile's ``output_bytes`` for
   the user and reports what it cut; the operator view gets the size and
   SHA-256 of what the child wrote, up to what the runner keeps.
3. Cancel: ``cancel``, or the stop event the worker sets when a heartbeat
   says a cancel was asked for, kills the run's process group at once.
4. Cleanup is ``confirmed`` only once the run's scratch directory is gone
   and its process group is empty, and ``unconfirmed`` otherwise.

A legacy envelope is never isolation evidence: its ``executor_kind`` is
``legacy-in-process``.

TODO(ROUNDS-00A-L05): #5's isolated worker is the second Executor.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import subprocess
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, Sequence

from app import admission, sandbox
from execution import kinds

LEGACY_KIND = "legacy-in-process"
# The slot poll while a claimed job waits for one, and how long it waits
# before the run ends timed-out, infrastructure-degraded.
SLOT_POLL_S = 0.1
# How many finished runs' cleanup statuses are kept.
CLEANUP_HISTORY = 256


class Starved(Exception):
    """No in-flight slot came free in time."""


class InvalidSpec(ValueError):
    """A run that can't be laid out: a file path outside the scratch."""


@dataclass(frozen=True)
class RunSpec:
    """One process for one part."""

    run_id: str
    argv: Sequence[str]
    files: Mapping[str, str] = field(default_factory=dict)
    wall_s: float = 10
    output_cap: int = 256 * 1024
    env: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Observation:
    """What one run did."""

    run_id: str
    exit_status: int | None
    stdout: str
    stderr: str
    truncated: bool
    output_bytes: int
    output_sha256: str
    wall_ms: int
    # The enforced limit that ended the run, if one did.
    limit: str | None
    canceled: bool
    cleanup: str


class Executor(Protocol):
    kind: str

    def run(self, spec: RunSpec, slot: sandbox.Sandbox, stop: threading.Event | None = None) -> Observation: ...

    def cancel(self, run_id: str) -> bool: ...

    def cleanup_status(self, run_id: str) -> str: ...


def output_cap() -> int:
    """The profile's output bytes per stream."""
    return int(kinds.profile()["output_bytes"])


def _cap(text: str, cap: int) -> tuple[str, bool]:
    data = text.encode("utf-8", errors="surrogatepass")
    if len(data) <= cap:
        return text, False
    return data[:cap].decode("utf-8", errors="ignore"), True


def _lay(workdir: str, files: Mapping[str, str]) -> None:
    root = os.path.realpath(workdir)
    for rel, contents in files.items():
        parts = rel.split("/")
        if not rel or rel.startswith("/") or "\\" in rel or "\x00" in rel or any(p in ("", ".", "..") for p in parts):
            raise InvalidSpec("a file path outside the scratch")
        target = os.path.join(root, *parts)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(contents)


class LegacyExecutor:
    """Today's in-process runners behind the executor port."""

    kind = LEGACY_KIND

    def __init__(self, pool: sandbox.SlotPool | None = None, threads: int | None = None) -> None:
        self._pool = pool if pool is not None else admission.pool()
        self.threads = ThreadPoolExecutor(max_workers=threads or self._pool.size, thread_name_prefix="execution")
        self._lock = threading.Lock()
        self._controls: dict[str, sandbox.Control] = {}
        self._cleanup: OrderedDict[str, str] = OrderedDict()
        self._closed = False

    # -- slots -------------------------------------------------------------

    @property
    def slots(self) -> int:
        return self._pool.size

    def free_slots(self) -> int:
        return self._pool.size - self._pool.in_use()

    async def acquire(self, wait_s: float) -> sandbox.Sandbox:
        """A slot within ``wait_s``, or ``Starved``."""
        deadline = time.monotonic() + wait_s
        while True:
            slot = self._pool.try_acquire()
            if slot is not None:
                return slot
            if time.monotonic() >= deadline:
                raise Starved
            await asyncio.sleep(SLOT_POLL_S)

    async def release(self, slot: sandbox.Sandbox) -> None:
        """Frees the slot once its uid's processes and temp files are
        gone, off the event loop."""
        await self.call(self._pool.release, slot)

    async def call(self, fn: Callable[..., Any], *args: Any) -> Any:
        """``fn(*args)`` on the executor's threads."""
        return await asyncio.get_running_loop().run_in_executor(self.threads, fn, *args)

    # -- the port ----------------------------------------------------------

    def run(self, spec: RunSpec, slot: sandbox.Sandbox, stop: threading.Event | None = None) -> Observation:
        """Runs ``spec`` in ``slot`` and waits for it. Blocks; call it on
        the executor's threads."""
        control = sandbox.Control(stop=stop if stop is not None else threading.Event())
        with self._lock:
            self._controls[spec.run_id] = control
        start = time.monotonic()
        workdir: str | None = None
        exit_status: int | None = None
        limit: str | None = None
        canceled = False
        stdout = stderr = ""
        try:
            with sandbox.scratch(slot) as scratch:
                workdir = scratch
                _lay(scratch, spec.files)
                sandbox.hand_over(scratch, slot)
                env = sandbox.candidate_env(scratch, spec.env)
                try:
                    proc = sandbox.run(spec.argv, cwd=scratch, env=env, timeout_s=spec.wall_s, sandbox=slot,
                                       control=control)
                    exit_status, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
                except subprocess.TimeoutExpired as err:
                    limit = "wall_time"
                    stdout, stderr = _text(err.output), _text(err.stderr)
                except sandbox.Stopped as err:
                    canceled = True
                    stdout, stderr = err.output, err.stderr
        finally:
            with self._lock:
                self._controls.pop(spec.run_id, None)
        gone = workdir is not None and not os.path.exists(workdir)
        cleanup = "confirmed" if gone and (control.pid is None or sandbox.group_gone(control.pid)) else "unconfirmed"
        self._record(spec.run_id, cleanup)
        out = stdout.encode("utf-8", errors="surrogatepass")
        err_bytes = stderr.encode("utf-8", errors="surrogatepass")
        shown_out, cut_out = _cap(stdout, spec.output_cap)
        shown_err, cut_err = _cap(stderr, spec.output_cap)
        return Observation(
            run_id=spec.run_id,
            exit_status=exit_status,
            stdout=shown_out,
            stderr=shown_err,
            truncated=cut_out or cut_err,
            output_bytes=len(out) + len(err_bytes),
            output_sha256=hashlib.sha256(out + b"\x00" + err_bytes).hexdigest(),
            wall_ms=int((time.monotonic() - start) * 1000),
            limit=limit,
            canceled=canceled,
            cleanup=cleanup,
        )

    def cancel(self, run_id: str) -> bool:
        """Stops the run if it's still going. True when it was."""
        with self._lock:
            control = self._controls.get(run_id)
        if control is None:
            return False
        control.stop.set()
        return True

    def cleanup_status(self, run_id: str) -> str:
        """``pending`` while the run is going, then what its cleanup
        confirmed. A run this executor doesn't know is ``unconfirmed``."""
        with self._lock:
            if run_id in self._controls:
                return "pending"
            return self._cleanup.get(run_id, "unconfirmed")

    def _record(self, run_id: str, cleanup: str) -> None:
        with self._lock:
            self._cleanup[run_id] = cleanup
            while len(self._cleanup) > CLEANUP_HISTORY:
                self._cleanup.popitem(last=False)

    # -- the process -------------------------------------------------------

    def healthy(self) -> bool:
        return not self._closed

    def close(self) -> None:
        """Stops every run and lets the threads go."""
        self._closed = True
        with self._lock:
            controls = list(self._controls.values())
        for control in controls:
            control.stop.set()
        self.threads.shutdown(wait=False, cancel_futures=True)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
