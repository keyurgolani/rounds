"""Jobs on the execution routes (ROUNDS-00A-L03 PRs 2 and 3).

While ``ROUNDS_GATE_EXECUTION_SCRATCH`` is on (``execution/keys.py``),
run, evaluate, run-project, and take-home run never run in their request,
and while ``ROUNDS_GATE_EXECUTION_GRADING`` is, neither do grade and
take-home submit (PR 3). Each route, in order:

1. checks this replica's worker is up and ready (``runtime``), so a store
   it can't reach or a worker secret PocketBase doesn't take is 503
   ``worker_unavailable`` before anything is charged, and the draft stays
   on the page;
2. runs admission's job steps (``admission.begin_job``) on the job's
   fingerprint: SHA-256 over the route, the definition, the candidate's
   source, and its typed inputs, never session time;
3. resolves the definition and runs the checks it runs in-request, so a
   typed refusal comes before any job exists;
4. enqueues the job with the caller's bearer and the runner key, and
   answers 202 with it.

A duplicate (step 2) answers 202 with its job as it is now, its envelope
included once it ended, and charges nothing. ``routers/execution.py``
reads and cancels the account's own job.

Every answer is ``answer``: ``{job_id, state, outcome_class, retryable,
cancel_requested, envelope}``, where ``envelope`` is the user view of
rounds.execution-envelope/v1 once the job ended with one, and
``retryable`` says whether a same-key retry would run it again. Nothing
here logs the candidate's source, input, or output.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, replace
from typing import Any, Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import admission, admission_state, canonical, obs
from app.errors import TypedError
from execution import kinds, runtime, store

FINGERPRINT_VERSION = "execution-job/v1"
# The route each kind is enqueued from; a fingerprint covers it. The two
# grading kinds join in PR 3.
ROUTES = {
    "run": "/api/run",
    "evaluate": "/api/evaluate",
    "run_project": "/api/ai-coding/run-project",
    "take_home_run": "/api/take-home/run",
    "grade": "/api/ai-coding/grade",
    "take_home_submit": "/api/take-home/submit",
}
# The longest a job read may wait for its job to change, and how often it
# asks the store while it waits: quickly at first, then each second.
MAX_WAIT_S = 20
POLL_S = (0.25, 0.25, 0.5, 0.5, 0.5)
POLL_EVERY_S = 1.0


def digest(value: Any) -> str:
    """The hex SHA-256 of ``value``'s RFC 8785 JSON. A value JSON can't
    hold exactly is 422 ``invalid_request``."""
    try:
        data = canonical.canonical(value)
    except canonical.CanonicalError:
        raise TypedError("invalid_request") from None
    return hashlib.sha256(data).hexdigest()


def fingerprint(route: str, definition: dict[str, Any], source_checksum: str, input_digest: str) -> str:
    """A job-backed request's fingerprint: the route, the definition it
    names, and the digests of its source and its typed inputs. Session
    time and anything else a body carries stay out, so a retry of the same
    work matches."""
    return digest({"v": FINGERPRINT_VERSION, "route": route, "definition": definition,
                   "source_checksum": source_checksum, "input_digest": input_digest})


@dataclass(frozen=True)
class Submission:
    """A job-backed request between admission and enqueue."""

    kind: str
    command_id: str
    definition: dict[str, Any]
    source_checksum: str
    input_digest: str
    fingerprint: str
    # A duplicate's answer, which the route returns as it is.
    answer: JSONResponse | None = None


def answer(job: store.JobView, retryable: bool, envelope: dict[str, Any] | None) -> dict[str, Any]:
    """What a job-backed route, the job read, and cancel answer."""
    return {
        "job_id": job.id,
        "state": job.state,
        "outcome_class": job.outcome_class,
        "retryable": retryable,
        "cancel_requested": job.cancel_requested,
        "envelope": envelope,
    }


def answer_of(found: store.JobStatus) -> dict[str, Any]:
    return answer(found.job, found.retryable, found.envelope)


def _metric(metric: str, kind: str) -> None:
    obs.emit("execution.job", metric=metric, value=1, kind=kind, purpose=kinds.KINDS[kind].purpose, service="runner")


def _token(request: Request) -> str:
    return admission.account(request)["token"]


async def begin(request: Request, kind: str, definition: BaseModel, source: Any, inputs: dict[str, Any],
                wall_seconds: int, max_wall_seconds: int | None = None) -> Submission:
    """Steps 1 and 2 for a scratch job. ``source`` is the candidate's code
    or files and ``inputs`` its typed inputs; the fingerprint covers both
    by digest."""
    if not runtime.accepting_jobs():
        raise TypedError("worker_unavailable")
    ref = definition.model_dump(mode="json")
    source_checksum, input_digest = digest(source), digest(inputs)
    job_fingerprint = fingerprint(ROUTES[kind], ref, source_checksum, input_digest)
    try:
        job_id = await admission.begin_job(request, job_fingerprint, wall_seconds, max_wall_seconds)
    except TypedError as refused:
        if refused.code == "idempotency_mismatch":
            _metric("rounds_job_fingerprint_conflict_total", kind)
        raise
    key = admission_state.command_id(request.scope.get("headers") or [])
    submission = Submission(kind, key, ref, source_checksum, input_digest, job_fingerprint)
    if job_id is None:
        return submission
    _metric("rounds_job_duplicate_total", kind)
    try:
        async with store.Caller(_token(request)) as caller:
            found = await caller.status(job_id)
    except store.Unavailable:
        raise TypedError("worker_unavailable") from None
    if found is None:
        # Gone between admission and this read: a retry runs admission again.
        raise TypedError("worker_unavailable")
    return replace(submission, answer=JSONResponse(answer_of(found), status_code=202))


async def enqueue(request: Request, submission: Submission, job_input: dict[str, Any]) -> JSONResponse:
    """Step 4: the job for the admitted command, answered 202."""
    payload = {
        "command_id": submission.command_id,
        "kind": submission.kind,
        "definition": submission.definition,
        "fingerprint": submission.fingerprint,
        "source_checksum": submission.source_checksum,
        "input_digest": submission.input_digest,
        "input": job_input,
    }
    try:
        async with store.Caller(_token(request)) as caller:
            job, duplicate, requeued = await caller.enqueue(payload)
            if duplicate and not requeued:
                # The job was there already and won't run again.
                found = await caller.status(job.id)
                if found is not None:
                    return JSONResponse(answer_of(found), status_code=202)
    except store.Mismatch:
        _metric("rounds_job_fingerprint_conflict_total", submission.kind)
        raise TypedError("idempotency_mismatch") from None
    except store.Unavailable:
        raise TypedError("worker_unavailable") from None
    return JSONResponse(answer(job, False, None), status_code=202)


async def wait_for(caller: store.Caller, job_id: str, wait_s: float,
                   gone: Callable[[], Awaitable[bool]] | None = None) -> store.JobStatus | None:
    """The account's job, once it changed from how it was when this was
    asked, once it ended, or after ``wait_s``, whichever comes first.
    None for another account's or an unknown job. ``gone`` says the caller
    stopped waiting."""
    first = await caller.status(job_id)
    if first is None or wait_s <= 0 or kinds.is_terminal(first.job.state):
        return first
    deadline = time.monotonic() + min(wait_s, MAX_WAIT_S)
    current, polls = first, 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return current
        delay = POLL_S[polls] if polls < len(POLL_S) else POLL_EVERY_S
        polls += 1
        await asyncio.sleep(min(delay, remaining))
        if gone is not None and await gone():
            return current
        current = await caller.status(job_id)
        if current is None:
            return None
        changed = (current.job.state, current.job.cancel_requested) != (first.job.state, first.job.cancel_requested)
        if changed or kinds.is_terminal(current.job.state):
            return current
