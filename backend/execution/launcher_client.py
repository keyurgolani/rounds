"""The runner's side of the code launcher (ROUNDS-00A-L05).

- ``LauncherClient`` sends job spec v1 (``launcher/jobspec.py``) to the
  launcher at ``ROUNDS_LAUNCHER_URL`` with ``ROUNDS_LAUNCHER_TOKEN``, and
  answers a ``LauncherResult``. A client without its settings, a launcher it
  can't reach, one that isn't ready, and a full queue are each
  ``LauncherUnavailable`` before any attempt starts; a connection lost
  mid-job is ``LauncherLost``.
- ``classify`` and ``classify_part`` turn the launcher's observation into
  #3's names (``execution/kinds.py``): a deadline kill is ``resource-limit``
  ``wall_time``, or ``infrastructure-degraded`` when the engine recorded CPU
  throttling or the job was starved of a slot or a worker; ``SIGSYS`` from
  the added filter is ``policy-violation``; the memory, process, file, and
  output limits are ``resource-limit`` with their names; and a malformed
  stream, a worker that ended without its summary, or one gone mid-run is
  ``infrastructure-degraded``, never the candidate's failure. A part that
  ended normally is left to its handler's scoring.
- ``IsolatedExecutor`` is #3's executor port over the launcher, kind
  ``isolated-worker``, with the surface the worker loop uses on
  ``LegacyExecutor``. Its answers carry the envelope v1 fields that fit:
  the image digest, CPU time, peak memory, exit status, output bytes and
  checksum.

Nothing in the runner constructs either yet: no route uses the launcher
until a later stage cuts it over, and ``runtime.start()`` keeps the legacy
executor.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import re
import secrets
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import httpx

from app import sandbox
from execution import envelope, kinds
from execution.executor import InvalidSpec, Observation, RunSpec, Starved
from launcher import config as launcher_config, jobspec
from worker import manifest

KIND = "isolated-worker"
DEFAULT_URL = "http://launcher:4300"
URL = re.compile(r"https?://[A-Za-z0-9.-]+(?::[0-9]{1,5})?")
# Past the job's own deadline, the most the launcher may take: its queue
# wait, a cold start, its grace, and the cleanup report.
OVERHEAD_S = 20.0
RESULT_MAX = 24 * 1024 * 1024
CLEANUP_KEPT = 256


class LauncherUnavailable(Exception):
    """No attempt started: the launcher isn't configured, reachable, or
    ready, or its queue is full."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class LauncherLost(Exception):
    """The connection to the launcher broke while a job ran."""


@dataclass(frozen=True)
class PartOutput:
    id: str
    out: bytes
    err: bytes
    result: bytes | None
    verdict: bytes | None


@dataclass(frozen=True)
class LauncherResult:
    observation: dict[str, Any]
    parts: list[PartOutput]
    verdict: bytes | None


def settings(environ: Mapping[str, str] | None = None) -> tuple[str, str | None, list[str]]:
    """The launcher's URL and token, and what's missing, as names."""
    env = os.environ if environ is None else environ
    url = (env.get("ROUNDS_LAUNCHER_URL") or DEFAULT_URL).strip().rstrip("/")
    token = env.get("ROUNDS_LAUNCHER_TOKEN") or ""
    missing = []
    if not URL.fullmatch(url):
        missing.append("launcher_url")
    if not launcher_config.TOKEN.fullmatch(token):
        missing.append("token")
    return url, (token if "token" not in missing else None), missing


def _bytes(value: Any) -> bytes | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise LauncherLost("a malformed answer")
    try:
        return base64.b64decode(value, validate=True)
    except ValueError:
        raise LauncherLost("a malformed answer") from None


class LauncherClient:
    def __init__(self, url: str, token: str, transport: httpx.BaseTransport | None = None) -> None:
        self.url = url
        self._headers = {"Authorization": f"Bearer {token}"}
        self._transport = transport

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "LauncherClient":
        url, token, missing = settings(environ)
        if missing:
            raise LauncherUnavailable("unconfigured")
        return cls(url, token)

    def _client(self, timeout: float) -> httpx.Client:
        return httpx.Client(base_url=self.url, headers=self._headers, timeout=timeout, transport=self._transport,
                            trust_env=False, follow_redirects=False)

    def ready(self) -> dict[str, Any]:
        try:
            with self._client(5.0) as client:
                resp = client.get("/ready")
        except httpx.HTTPError:
            raise LauncherUnavailable("unreachable") from None
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if resp.status_code != 200 or not isinstance(body, dict) or body.get("ready") is not True:
            raise LauncherUnavailable("not_ready")
        return body

    def submit(self, *, job_id: str, kind: str, definition: dict[str, Any] | None, deadline_ms: int,
               archive: bytes) -> LauncherResult:
        body = jobspec.encode(job_id, kind, definition, deadline_ms, archive)
        timeout = httpx.Timeout(deadline_ms / 1000 + OVERHEAD_S, connect=5.0)
        try:
            with self._client(5.0) as client:
                resp = client.post("/v1/jobs", content=body, headers={"Content-Type": jobspec.CONTENT_TYPE},
                                   timeout=timeout)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise LauncherUnavailable("unreachable") from None
        except httpx.HTTPError:
            raise LauncherLost("the connection broke mid-job") from None
        if resp.status_code in (409, 503):
            raise LauncherUnavailable(_code(resp, "not_ready"))
        if resp.status_code in (400, 413):
            # The runner built a spec the launcher refused: the runner's own bug.
            raise InvalidSpec(_code(resp, "job_rejected"))
        if resp.status_code != 200 or len(resp.content) > RESULT_MAX:
            raise LauncherLost("an unexpected answer")
        return parse_result(resp.json())

    def cancel(self, job_id: str) -> bool:
        try:
            with self._client(5.0) as client:
                resp = client.post(f"/v1/jobs/{job_id}/cancel")
            return resp.status_code == 200 and resp.json().get("canceled") is True
        except (httpx.HTTPError, ValueError, AttributeError):
            return False

    def cleanup(self, job_id: str) -> str:
        try:
            with self._client(5.0) as client:
                resp = client.get(f"/v1/jobs/{job_id}")
            state = resp.json().get("cleanup") if resp.status_code == 200 else None
        except (httpx.HTTPError, ValueError, AttributeError):
            return "unconfirmed"
        return state if state in kinds.CLEANUP else "unconfirmed"


def _code(resp: httpx.Response, default: str) -> str:
    try:
        code = resp.json().get("code")
    except (ValueError, AttributeError):
        code = None
    return code if isinstance(code, str) and re.fullmatch(r"[a-z_]{1,32}", code) else default


def parse_result(body: Any) -> LauncherResult:
    if not isinstance(body, dict) or body.get("version") != "rounds.launcher-result/v1":
        raise LauncherLost("a malformed answer")
    observation, output = body.get("observation"), body.get("output")
    if not isinstance(observation, dict) or not isinstance(output, dict):
        raise LauncherLost("a malformed answer")
    if observation.get("version") != "rounds.launcher-observation/v1":
        raise LauncherLost("a malformed answer")
    parts = []
    for item in output.get("parts") or []:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise LauncherLost("a malformed answer")
        parts.append(PartOutput(id=item["id"], out=_bytes(item.get("out")) or b"", err=_bytes(item.get("err")) or b"",
                                result=_bytes(item.get("result")), verdict=_bytes(item.get("verdict"))))
    return LauncherResult(observation=observation, parts=parts, verdict=_bytes(output.get("verdict")))


# -- #3's names ----------------------------------------------------------------


def throttled(observation: Mapping[str, Any]) -> bool:
    count = observation.get("nr_throttled")
    return isinstance(count, int) and count > 0


def classify(observation: Mapping[str, Any]) -> envelope.Outcome | None:
    """The job's outcome when the launcher's facts decide it alone, or None
    when each part's class does."""
    reason = observation.get("kill_reason")
    if reason == "starved":
        return envelope.outcome("timed-out", "infrastructure-degraded")
    if reason == "canceled":
        return envelope.outcome("canceled", "canceled")
    if reason == "wall_time":
        if throttled(observation):
            return envelope.outcome("timed-out", "infrastructure-degraded")
        return envelope.outcome("timed-out", "resource-limit", "wall_time")
    if reason is not None:
        # malformed, lost, or anything else the launcher saw go wrong.
        return envelope.outcome("failed", "infrastructure-degraded")
    if observation.get("oom") and not observation.get("end"):
        return envelope.outcome("completed", "resource-limit", "memory")
    if not observation.get("end") or observation.get("setup") != "ok" or observation.get("residue"):
        return envelope.outcome("failed", "infrastructure-degraded")
    return None


def classify_part(entry: Mapping[str, Any] | None, observation: Mapping[str, Any]) -> envelope.Part | None:
    """One part's class from init's summary of it, or None when the part
    ended normally and its handler scores it."""
    part_id = entry["id"] if entry is not None else "part"
    if entry is None or (entry.get("exit") is None and entry.get("signal") is None):
        return envelope.Part(part_id, "infrastructure-degraded")
    if entry.get("policy"):
        return envelope.Part(part_id, "policy-violation")
    limit = entry.get("limit")
    if limit == "wall_time":
        if throttled(observation):
            return envelope.Part(part_id, "infrastructure-degraded")
        return envelope.Part(part_id, "resource-limit", "wall_time")
    if limit in ("output", "files"):
        return envelope.Part(part_id, "resource-limit", limit)
    if entry.get("oom_kills"):
        return envelope.Part(part_id, "resource-limit", "memory")
    if entry.get("pid_limit_hits") and entry.get("exit") != 0:
        return envelope.Part(part_id, "resource-limit", "processes")
    return None


def image_digest(ref: Any) -> str | None:
    if not isinstance(ref, str):
        return None
    match = re.search(r"sha256:[0-9a-f]{64}$", ref)
    return match.group(0) if match else None


# -- #3's executor port --------------------------------------------------------


@dataclass(frozen=True)
class IsolatedObservation(Observation):
    cpu_time_ms: int | None = None
    peak_rss_bytes: int | None = None
    image_digest: str | None = None
    starved: bool = False
    throttled: bool = False
    policy: bool = False
    outcome: envelope.Outcome | None = None


JOB_ID = re.compile(r"[A-Za-z0-9_-]{8,64}")


class IsolatedExecutor:
    """#3's executor port, running each spec in a fresh worker."""

    kind = KIND

    def __init__(self, client: LauncherClient, slots: int = 2) -> None:
        self._client = client
        self._pool = sandbox.SlotPool(slots)
        self.threads = ThreadPoolExecutor(max_workers=slots, thread_name_prefix="isolated")
        self._lock = threading.Lock()
        self._jobs: dict[str, str] = {}
        self._done: OrderedDict[str, str] = OrderedDict()
        self._closed = False

    # -- slots, as LegacyExecutor has them -----------------------------------

    @property
    def slots(self) -> int:
        return self._pool.size

    def free_slots(self) -> int:
        return self._pool.size - self._pool.in_use()

    async def acquire(self, wait_s: float) -> sandbox.Sandbox:
        deadline = time.monotonic() + wait_s
        while True:
            slot = self._pool.try_acquire()
            if slot is not None:
                return slot
            if time.monotonic() >= deadline:
                raise Starved
            await asyncio.sleep(0.1)

    async def release(self, slot: sandbox.Sandbox) -> None:
        self._pool.release(slot)

    async def call(self, fn: Callable[..., Any], *args: Any) -> Any:
        return await asyncio.get_running_loop().run_in_executor(self.threads, fn, *args)

    # -- the port ------------------------------------------------------------

    def run(self, spec: RunSpec, slot: sandbox.Sandbox, stop: threading.Event | None = None, *,
            kind: str = "run_project", definition: dict[str, Any] | None = None) -> IsolatedObservation:
        """Runs ``spec`` as a one-part job in its own worker and waits.
        Blocks; call it on the executor's threads."""
        if spec.env:
            raise InvalidSpec("a worker's environment is fixed")
        if not spec.argv or spec.argv[0] not in manifest.PROGRAMS:
            raise InvalidSpec("a program the worker image doesn't run")
        job_id = spec.run_id if JOB_ID.fullmatch(spec.run_id) else secrets.token_hex(12)
        archive = manifest.build(
            parts=[{"id": "run", "argv": list(spec.argv), "wall_ms": max(1, int(spec.wall_s * 1000)),
                    "result": None, "channel": False}],
            src=dict(spec.files),
        )
        with self._lock:
            self._jobs[spec.run_id] = job_id
        watcher = None
        if stop is not None:
            watcher = threading.Thread(target=self._watch, args=(stop, job_id), daemon=True)
            watcher.start()
        try:
            result = self._client.submit(job_id=job_id, kind=kind, definition=definition,
                                         deadline_ms=max(1, int(spec.wall_s * 1000)), archive=archive)
        finally:
            with self._lock:
                self._jobs.pop(spec.run_id, None)
                self._done[spec.run_id] = job_id
                while len(self._done) > CLEANUP_KEPT:
                    self._done.popitem(last=False)
        return self._observe(spec, result)

    def _watch(self, stop: threading.Event, job_id: str) -> None:
        while True:
            with self._lock:
                running = job_id in self._jobs.values()
            if not running:
                return
            if stop.wait(0.1):
                self._client.cancel(job_id)
                return

    def _observe(self, spec: RunSpec, result: LauncherResult) -> IsolatedObservation:
        observation = result.observation
        part = result.parts[0] if result.parts else PartOutput("run", b"", b"", None, None)
        entries = observation.get("parts") or []
        entry = entries[0] if entries else None
        job_outcome = classify(observation)
        part_class = classify_part(entry, observation) if job_outcome is None else None
        outcome = job_outcome or (envelope.aggregate([part_class]) if part_class is not None else None)
        out = part.out[: spec.output_cap]
        err = part.err[: spec.output_cap]
        return IsolatedObservation(
            run_id=spec.run_id,
            exit_status=entry.get("exit") if entry else None,
            stdout=out.decode("utf-8", errors="replace"),
            stderr=err.decode("utf-8", errors="replace"),
            truncated=bool(entry and entry.get("truncated")) or len(part.out) > spec.output_cap
            or len(part.err) > spec.output_cap,
            output_bytes=len(part.out) + len(part.err),
            output_sha256=hashlib.sha256(part.out + b"\x00" + part.err).hexdigest(),
            wall_ms=int(entry.get("wall_ms", 0)) if entry else 0,
            limit=outcome.limit if outcome is not None else None,
            canceled=observation.get("kill_reason") == "canceled",
            cleanup=observation.get("cleanup") if observation.get("cleanup") in kinds.CLEANUP else "unconfirmed",
            cpu_time_ms=observation.get("cpu_time_ms"),
            peak_rss_bytes=observation.get("peak_memory_bytes"),
            image_digest=image_digest(observation.get("image")),
            starved=observation.get("kill_reason") == "starved",
            throttled=throttled(observation),
            policy=bool(entry and entry.get("policy")),
            outcome=outcome,
        )

    def cancel(self, run_id: str) -> bool:
        with self._lock:
            job_id = self._jobs.get(run_id)
        return self._client.cancel(job_id) if job_id is not None else False

    def cleanup_status(self, run_id: str) -> str:
        with self._lock:
            if run_id in self._jobs:
                return "pending"
            job_id = self._done.get(run_id)
        return self._client.cleanup(job_id) if job_id is not None else "unconfirmed"

    def healthy(self) -> bool:
        return not self._closed

    def close(self) -> None:
        self._closed = True
        with self._lock:
            running = list(self._jobs.values())
        for job_id in running:
            self._client.cancel(job_id)
        self.threads.shutdown(wait=False, cancel_futures=True)
