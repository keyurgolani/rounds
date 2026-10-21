"""Legacy Artifact Snapshot creation at the runner (ROUNDS-00A-L04, PR 2).

``POST /api/pdf/snapshots`` (routers/pdf.py) is an admitted route: its gate
``ROUNDS_GATE_LEGACY_SNAPSHOT_CREATE`` ships ``disabled``, the body cap is
4 KiB, and steps 6 and 7 charge one request and the materializer's 10 s.
The runner holds no snapshot state and renders nothing here. It forwards
the caller's bearer, the runner key, and the checked request to
PocketBase's ``POST /api/rounds/legacy-snapshots``
(pocketbase/pb_hooks/legacy_snapshots.js), which reads the caller's own
records, calls the materializer, and writes the snapshot. nginx and the
Vite proxy answer that path with 404, so only the runner reaches it.

The request names a source and the ``updated`` the caller saw, never
markup, a template, or a design. The ``Idempotency-Key`` the runner
admitted the request under goes to the hook as ``command_id``, so the hook
completes that command in the same transaction as the snapshot; a key the
runner didn't record (idempotency off, or refused in observe mode) stays
behind.

The hook's answers, and the runner's:

  201 created, 200 reused, 200 ineligible   the same status and body, which
                                            admission keeps for replay
  404 not_found                             404 not_found
  409 conflict                              409 snapshot_conflict
  429 snapshot_quota_exceeded               429 snapshot_quota_exceeded
  503 route_disabled                        503 route_disabled
  401                                       401 unauthenticated
  anything else, or no answer in time       503 materializer_unavailable

Every refusal is #1's typed envelope and never repeats PocketBase's text.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Literal

import anyio
import httpx
from fastapi import Request
from pydantic import Field

from app import admission, admission_state
from app.errors import TypedError
from app.limits import StrictModel
from app.pb_auth import POCKETBASE_URL

_log = logging.getLogger(__name__)

VERSION = "legacy-snapshot/v1"
HOOK_PATH = "/api/rounds/legacy-snapshots"
# The hook bounds its materializer call at this (legacy_snapshots.js
# MATERIALIZE_TIMEOUT_S), and admission charges it.
MATERIALIZE_TIMEOUT_S = 10
# The whole call to the hook: its reads, the materializer, and the
# transaction. Inside the lease's window, which admission sets at the
# charge plus its 30 s grace.
TIMEOUT_S = MATERIALIZE_TIMEOUT_S + 10

RECORD_ID = r"^[a-z0-9]{15}$"
# PocketBase 0.22's `updated`: "2006-01-02 15:04:05.000Z".
PB_DATETIME = r"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,9})?Z$"
_RECORD_ID = re.compile(RECORD_ID)
_CHECKSUM = re.compile(r"sha256:[0-9a-f]{64}")
# The hook's ineligible reasons (legacy_snapshots.js REASONS).
REASONS = frozenset({
    "data_malformed", "data_too_large", "demo_account", "design_out_of_domain", "markup_unsafe", "parent_invalid",
})
_OUTCOME_KEYS = frozenset({"status", "snapshot_id", "content_checksum"})
# Verdicts under which the runner's admit recorded an in-flight command
# for this request's key.
_RECORDED = frozenset({"new", "retry"})


class SnapshotRequest(StrictModel):
    source_kind: Literal["resume", "variant"]
    source_id: str = Field(pattern=RECORD_ID)
    expected_updated: str = Field(max_length=40, pattern=PB_DATETIME)


def command_for(request: Request) -> str | None:
    """The request's command id when admission recorded a command for it."""
    admitted = admission.state(request)
    if admitted is None or admitted.idempotency not in _RECORDED:
        return None
    return admission_state.command_id(request.scope.get("headers") or [])


def _outcome(status: int, body: Any) -> bool:
    """A created, reused, or ineligible answer in the contract's shape."""
    if not isinstance(body, dict):
        return False
    kind = body.get("status")
    if kind in ("created", "reused"):
        return (
            set(body) == _OUTCOME_KEYS
            and status == (201 if kind == "created" else 200)
            and isinstance(body["snapshot_id"], str) and _RECORD_ID.fullmatch(body["snapshot_id"]) is not None
            and isinstance(body["content_checksum"], str) and _CHECKSUM.fullmatch(body["content_checksum"]) is not None
        )
    if kind == "ineligible":
        return (
            status == 200
            and set(body) == _OUTCOME_KEYS | {"reason"}
            and body["snapshot_id"] is None and body["content_checksum"] is None
            and body["reason"] in REASONS
        )
    return False


def read_answer(status: int, body: Any) -> tuple[int, dict[str, Any]]:
    """The runner's answer for the hook's: the outcome to pass on, or the
    typed refusal raised."""
    if _outcome(status, body):
        return status, body
    error = body.get("error") if isinstance(body, dict) and body.get("v") == VERSION else None
    if status == 404 and error == "not_found":
        raise TypedError("not_found")
    if status == 409 and isinstance(body, dict) and body.get("status") == "conflict":
        raise TypedError("snapshot_conflict")
    if status == 429 and error == "snapshot_quota_exceeded":
        raise TypedError("snapshot_quota_exceeded")
    if status == 503 and error == "route_disabled":
        raise TypedError("route_disabled")
    if status == 401:
        raise TypedError("unauthenticated")
    # The hook's own error code names the cause (materializer_unavailable,
    # unavailable, unconfigured, forbidden); nothing else is logged.
    named = error if isinstance(error, str) and re.fullmatch(r"[a-z_]{1,40}", error) else "none"
    _log.warning("legacy snapshot: PocketBase answered %s (%s)", status, named)
    raise TypedError("materializer_unavailable")


async def create(token: str, req: SnapshotRequest, command_id: str | None) -> tuple[int, dict[str, Any]]:
    """CreateLegacyArtifactSnapshot through the hook, for the bearer's account."""
    try:
        key = admission_state.runner_key()
    except admission_state.Unconfigured:
        _log.warning("legacy snapshot: the runner has no usable %s", admission_state.RUNNER_KEY_ENV)
        raise TypedError("materializer_unavailable") from None
    payload: dict[str, Any] = req.model_dump()
    if command_id is not None:
        payload["command_id"] = command_id
    headers = {"Authorization": f"Bearer {token}", admission_state.RUNNER_KEY_HEADER: key}
    try:
        # The client's timeout bounds each phase; this bounds the call.
        with anyio.fail_after(TIMEOUT_S):
            async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=TIMEOUT_S) as client:
                resp = await client.post(HOOK_PATH, json=payload, headers=headers)
    except (httpx.HTTPError, TimeoutError) as err:
        _log.warning("legacy snapshot: no answer from PocketBase (%s)", type(err).__name__)
        raise TypedError("materializer_unavailable") from None
    try:
        body = resp.json()
    except ValueError:
        body = None
    return read_answer(resp.status_code, body)
