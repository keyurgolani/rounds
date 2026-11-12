"""The launcher's slots (ROUNDS-00A-L05).

A slot is room for one worker. It is free, starting a worker, holding a
ready pre-started one, busy with a job, cleaning up, or quarantined:

1. Pre-start: up to ``prestart`` slots hold a worker that is created,
   attached, and started, with init ready and waiting for its job, so a
   job doesn't wait for a cold start. Each runs at most one job. One that
   waits ``PRESTART_TTL_S`` with none is destroyed and replaced.
2. Lease: a job takes a ready slot first, else a free one and starts a
   worker in it. At most twice as many jobs wait as there are slots; past
   that ``acquire`` answers ``Saturated`` at once, and a job that gets no
   slot within ``QUEUE_WAIT_S``, or no worker within ``START_MAX_S``, is
   ``Starved``.
3. Cleanup: once a job ends, its worker is removed, and the slot is free
   again only after the engine answers not-found for it. A removal that
   fails, or a worker still there after ``DESTROY_WAIT_S``, quarantines
   the slot and alerts; the reaper retries it.
4. Reaper: at start every worker this daemon holds is removed, since a
   worker daemon serves exactly one launcher and nothing can attach to a
   worker an earlier run left; then every ``REAP_EVERY_S`` any worker past
   its deadline label goes. Unlabeled containers are never touched.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable

from execution import kinds
from launcher import events, profile as isolation
from launcher.engine import Attachment, Engine, EngineError
from worker import frames

QUEUE_WAIT_S = 5.0
START_MAX_S = 5.0
PRESTART_TTL_S = 600.0
REAP_EVERY_S = 30.0
DESTROY_WAIT_S = 10.0
LABEL_SLACK_S = 120
# A worker's deadline label covers its idle time and the longest job.
JOB_MAX_S = max(k.max_budget_s for k in kinds.KINDS.values()) + max(k.part_wall_s for k in kinds.KINDS.values())
DESTROYED_KEPT = 1024
SELECTOR = f"{isolation.LABEL}={isolation.LABEL_VALUE}"


class Saturated(Exception):
    """Every slot is busy and the queue is full."""


class Starved(Exception):
    """No slot, or no worker, in time."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class Worker:
    cid: str
    attachment: Attachment
    created: float
    prestarted: bool
    start_ms: int


@dataclass
class Slot:
    index: int
    state: str = "free"
    worker: Worker | None = None
    cid: str | None = None


def create_worker(engine: Engine, image: str, runtime: str, profile: dict[str, Any], wall: float,
                  timeout: float, clock: Callable[[], float] = time.monotonic) -> Worker:
    """A worker, created, attached, and started, with init ready."""
    began = clock()
    deadline = int(wall + PRESTART_TTL_S + JOB_MAX_S + LABEL_SLACK_S)
    cid = engine.create(isolation.create_body(image, runtime, profile, deadline))
    attachment = None
    try:
        attachment = engine.attach(cid)
        engine.start(cid)
        seen = bytearray()
        give_up = began + timeout
        while len(seen) < len(frames.READY):
            left = give_up - clock()
            if left <= 0:
                raise EngineError(0, "the worker didn't get ready")
            chunks = attachment.recv(min(left, 0.25))
            if chunks is None:
                raise EngineError(0, "the worker ended before it was ready")
            for stream, data in chunks:
                if stream != 1:
                    raise EngineError(0, "the worker wrote to stderr before it was ready")
                seen += data
        if bytes(seen) != frames.READY:
            raise EngineError(0, "not a worker")
    except BaseException:
        if attachment is not None:
            attachment.close()
        try:
            engine.remove(cid)
        except EngineError:
            pass
        raise
    return Worker(cid=cid, attachment=attachment, created=clock(), prestarted=False,
                  start_ms=int((clock() - began) * 1000))


class Pool:
    def __init__(self, engine: Engine, image: str, runtime: str, profile: dict[str, Any], size: int, prestart: int,
                 clock: Callable[[], float] = time.monotonic, wall: Callable[[], float] = time.time,
                 make_worker: Callable[..., Worker] = create_worker) -> None:
        self.engine = engine
        self.image = image
        self.runtime = runtime
        self.profile = profile
        self.size = size
        self.prestart = max(0, min(prestart, size))
        self.clock = clock
        self.wall = wall
        self._make = make_worker
        self.slots = [Slot(i) for i in range(size)]
        self._cond = threading.Condition()
        self._waiting = 0
        self._destroyed: OrderedDict[str, float | None] = OrderedDict()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self.orphans_removed = 0

    # -- start and stop ----------------------------------------------------

    def start(self, threads: bool = True) -> int:
        """Removes every worker the daemon holds and starts the pre-start
        and reaper loops. Answers how many it removed."""
        removed, stuck = 0, []
        for item in self._labeled():
            cid = item.get("Id", "")
            if self._destroy(cid):
                removed += 1
            else:
                stuck.append(cid)
        with self._cond:
            for slot, cid in zip(self.slots, stuck):
                slot.state, slot.cid = "quarantined", cid
        for _ in stuck:
            events.metric("rounds_worker_cleanup_failed_total")
        self.orphans_removed += removed
        if removed:
            events.metric("rounds_worker_orphan_removed_total", removed)
        if threads:
            for target in (self._filler, self._reaper):
                thread = threading.Thread(target=target, daemon=True, name=f"launcher-{target.__name__.strip('_')}")
                thread.start()
                self._threads.append(thread)
        return removed

    def stop(self) -> None:
        self._stop.set()
        with self._cond:
            self._cond.notify_all()
            held = [s.worker for s in self.slots if s.worker is not None]
        for worker in held:
            worker.attachment.close()
            self._destroy(worker.cid)

    # -- leases ------------------------------------------------------------

    def acquire(self, wait_s: float = QUEUE_WAIT_S) -> Slot:
        """A slot for one job, ready or free, now busy."""
        give_up = self.clock() + wait_s
        with self._cond:
            if self._waiting >= 2 * self.size:
                events.metric("rounds_worker_saturated_total")
                raise Saturated
            self._waiting += 1
            try:
                while True:
                    slot = self._pick()
                    if slot is not None:
                        slot.state = "busy"
                        self._cond.notify_all()
                        return slot
                    left = give_up - self.clock()
                    if left <= 0 or self._stop.is_set():
                        raise Starved("queue")
                    self._cond.wait(left)
            finally:
                self._waiting -= 1

    def _pick(self) -> Slot | None:
        for state in ("ready", "free"):
            for slot in self.slots:
                if slot.state == state and (state == "free" or slot.worker is not None):
                    return slot
        return None

    def take_worker(self, slot: Slot) -> Worker:
        """The slot's pre-started worker, or a new one within
        ``START_MAX_S``."""
        with self._cond:
            worker = slot.worker
        if worker is not None:
            worker.prestarted = True
            return worker
        try:
            worker = self._make(self.engine, self.image, self.runtime, self.profile, self.wall(), START_MAX_S,
                                self.clock)
        except EngineError:
            with self._cond:
                slot.state = "free"
                self._cond.notify_all()
            raise Starved("start") from None
        with self._cond:
            slot.worker = worker
        return worker

    def release(self, slot: Slot) -> str | None:
        """Ends the slot's job: its worker is removed, and the slot frees
        once the engine reports it gone. Answers the worker's id."""
        with self._cond:
            worker, slot.worker = slot.worker, None
            if worker is None:
                slot.state = "free"
                self._cond.notify_all()
                return None
            slot.state, slot.cid = "cleaning", worker.cid
            self._destroyed[worker.cid] = None
            self._destroyed.move_to_end(worker.cid)
            while len(self._destroyed) > DESTROYED_KEPT:
                self._destroyed.popitem(last=False)
        worker.attachment.close()
        threading.Thread(target=self._clean, args=(slot, worker.cid), daemon=True, name="launcher-clean").start()
        return worker.cid

    def destruction(self, cid: str | None) -> tuple[str, float | None]:
        """``pending``, ``confirmed`` with when, or ``unconfirmed``."""
        if cid is None:
            return "unconfirmed", None
        with self._cond:
            if cid not in self._destroyed:
                return "unconfirmed", None
            when = self._destroyed[cid]
            slot = next((s for s in self.slots if s.cid == cid), None)
        if when is not None:
            return "confirmed", when
        return ("unconfirmed", None) if slot is not None and slot.state == "quarantined" else ("pending", None)

    def wait_destroyed(self, cid: str | None, timeout: float) -> tuple[str, float | None]:
        give_up = self.clock() + timeout
        while True:
            state = self.destruction(cid)
            if state[0] != "pending" or self.clock() >= give_up:
                return state
            time.sleep(0.02)

    def status(self) -> dict[str, int]:
        with self._cond:
            counts = {name: 0 for name in ("free", "starting", "ready", "busy", "cleaning", "quarantined")}
            for slot in self.slots:
                counts[slot.state] += 1
            counts["slots"] = self.size
            counts["waiting"] = self._waiting
        return counts

    # -- cleanup -------------------------------------------------------------

    def _destroy(self, cid: str) -> bool:
        """Removes the worker and waits until the engine reports it gone."""
        give_up = self.clock() + DESTROY_WAIT_S
        try:
            self.engine.remove(cid)
            while self.clock() < give_up:
                if self.engine.inspect(cid) is None:
                    return True
                time.sleep(0.05)
        except EngineError:
            return False
        return False

    def _clean(self, slot: Slot, cid: str) -> None:
        gone = self._destroy(cid)
        with self._cond:
            if gone:
                self._destroyed[cid] = self.wall()
                slot.state, slot.cid = "free", None
            else:
                slot.state = "quarantined"
            self._cond.notify_all()
        if not gone:
            events.emit("slot_quarantined")
            events.metric("rounds_worker_cleanup_failed_total")
            events.metric("rounds_worker_slots_quarantined", self.status()["quarantined"])

    def _labeled(self) -> list[dict[str, Any]]:
        try:
            return self.engine.labeled(SELECTOR)
        except EngineError:
            return []

    # -- the loops -----------------------------------------------------------

    def _filler(self) -> None:
        backoff = 0.0
        while not self._stop.is_set():
            slot = None
            with self._cond:
                ready = sum(1 for s in self.slots if s.state in ("ready", "starting"))
                if ready < self.prestart:
                    slot = next((s for s in self.slots if s.state == "free"), None)
                    if slot is not None:
                        slot.state = "starting"
                if slot is None:
                    self._cond.wait(0.5)
                    continue
            try:
                worker = self._make(self.engine, self.image, self.runtime, self.profile, self.wall(), START_MAX_S,
                                    self.clock)
            except EngineError:
                with self._cond:
                    slot.state = "free"
                    self._cond.notify_all()
                backoff = min(max(backoff * 2, 1.0), 30.0)
                self._stop.wait(backoff)
                continue
            backoff = 0.0
            with self._cond:
                slot.worker, slot.state = worker, "ready"
                self._cond.notify_all()
            events.metric("rounds_worker_prestarted", self.status()["ready"])

    def _reaper(self) -> None:
        while not self._stop.wait(REAP_EVERY_S):
            self.reap()

    def reap(self) -> int:
        """One pass: quarantined slots retried, stale pre-started workers
        replaced, and labeled workers past their deadline removed."""
        with self._cond:
            quarantined = [s for s in self.slots if s.state == "quarantined" and s.cid]
            stale = [s for s in self.slots if s.state == "ready" and s.worker is not None
                     and self.clock() - s.worker.created > PRESTART_TTL_S]
            for slot in stale:
                slot.state = "busy"
        for slot in quarantined:
            if self._destroy(slot.cid):
                with self._cond:
                    self._destroyed[slot.cid] = self.wall()
                    slot.state, slot.cid = "free", None
                    self._cond.notify_all()
        for slot in stale:
            self.release(slot)
        removed = 0
        now = self.wall()
        for item in self._labeled():
            cid = item.get("Id", "")
            try:
                deadline = int((item.get("Labels") or {}).get(isolation.DEADLINE_LABEL, "0"))
            except ValueError:
                deadline = 0
            # A worker without a deadline label isn't one this launcher made.
            if deadline > now:
                continue
            if self._destroy(cid):
                removed += 1
        if removed:
            self.orphans_removed += removed
            events.metric("rounds_worker_orphan_removed_total", removed)
        return removed
