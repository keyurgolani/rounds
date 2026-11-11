"""The account's own execution jobs (ROUNDS-00A-L03 PR 2).

- ``GET /api/execution/jobs/{job_id}?wait=N`` answers the job as it is, or
  waits up to ``N`` seconds (at most 20, default 0) for it to change or
  end, then answers it: ``execution.jobs.answer``, with the envelope's
  user view once the job ended with one.
- ``POST /api/execution/jobs/{job_id}/cancel`` asks the job to stop: a
  queued job ends canceled at once, a running one at its next heartbeat,
  and an ended one stays as it is. Asking again changes nothing more.

Both need the caller's bearer and nothing else: they aren't admitted, so
reading or stopping a job is never charged. Another account's job, an
unknown id, and a malformed one all answer the same 404 ``not_found``. A
store that doesn't answer is 503 ``worker_unavailable``. They serve every
job the store holds, whatever ``ROUNDS_GATE_EXECUTION_SCRATCH`` says now,
so a page still sees its job through after the key changes.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import admission
from app.errors import TypedError
from execution import jobs, store

router = APIRouter(prefix="/api/execution", tags=["execution"])

JOB_ID = re.compile(r"[a-z0-9]{15}")


async def _account(request: Request) -> dict:
    """The caller's account from its bearer: 401 ``unauthenticated``
    without one PocketBase takes, 503 ``auth_unavailable`` while
    PocketBase doesn't answer."""
    token = admission.bearer_from(request.scope.get("headers") or [])
    if token is None:
        raise TypedError("unauthenticated")
    return await admission.authenticate(token)


def _wait_s(request: Request) -> int:
    raw = request.query_params.get("wait")
    if raw is None:
        return 0
    if not raw.isdigit() or int(raw) > jobs.MAX_WAIT_S:
        raise TypedError("invalid_request")
    return int(raw)


@router.get("/jobs/{job_id}")
async def read_job(request: Request, job_id: str) -> JSONResponse:
    wait = _wait_s(request)
    user = await _account(request)
    if not JOB_ID.fullmatch(job_id):
        raise TypedError("not_found")
    try:
        async with store.Caller(user["token"]) as caller:
            found = await jobs.wait_for(caller, job_id, wait, request.is_disconnected)
    except store.Unavailable:
        raise TypedError("worker_unavailable") from None
    if found is None:
        raise TypedError("not_found")
    return JSONResponse(jobs.answer_of(found))


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(request: Request, job_id: str) -> JSONResponse:
    user = await _account(request)
    if not JOB_ID.fullmatch(job_id):
        raise TypedError("not_found")
    try:
        async with store.Caller(user["token"]) as caller:
            if await caller.cancel(job_id) is None:
                raise TypedError("not_found")
            found = await caller.status(job_id)
    except store.Unavailable:
        raise TypedError("worker_unavailable") from None
    if found is None:
        raise TypedError("not_found")
    return JSONResponse(jobs.answer_of(found))
