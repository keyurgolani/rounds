"""Legacy Artifact Snapshots at the runner (ROUNDS-00A-L04): creation
(PR 2) and the reads a render makes (PR 3).

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
  409 idempotency_mismatch                  409 idempotency_mismatch
  429 snapshot_quota_exceeded               429 snapshot_quota_exceeded
  503 route_disabled                        503 route_disabled
  401                                       401 unauthenticated
  anything else, or no answer in time       503 materializer_unavailable

Every refusal is #1's typed envelope and never repeats PocketBase's text.

``POST /api/pdf/render`` takes ``render-request/v1`` (``RenderRequestV1``):
one snapshot id, its checksum, and fixed output options, never markup.
``markup_for_render`` reads, with the caller's bearer and nothing else:

1. the snapshot, which only its owner can view, so a missing one and
   another account's both answer 404 ``not_found``;
2. its checksum, which must be the one the request expects, or 409
   ``checksum_mismatch``;
3. its source resume or variant, which must still exist, or the same
   404 (a variant goes when its parent does);
4. its markup file, through a file token, which must hash to the
   checksum. A file that doesn't is ``StoredMarkupUnusable``, which the
   route answers as a failed render and logs for the operator.
"""
from __future__ import annotations

import hashlib
import logging
import re
import urllib.parse
from typing import Any, Literal

import anyio
import httpx
from fastapi import Request
from pydantic import Field

from app import admission, admission_state
from app.errors import TypedError
from app.limits import StrictModel
from app.pb_auth import POCKETBASE_URL, pb_get

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
    if status == 409 and error == "idempotency_mismatch":
        raise TypedError("idempotency_mismatch")
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


# ---- render (PR 3) ------------------------------------------------------------

SNAPSHOTS = "legacy_artifact_snapshots"
SOURCE_COLLECTIONS = {"resume": "resumes", "variant": "resume_variants"}
# A snapshot's markup is at most this many bytes, as the collection's file
# field allows (1700008000_legacy_artifact_snapshots.js).
MAX_MARKUP_BYTES = 2 * 1024 * 1024
FILE_TOKEN_PATH = "/api/files/token"
READ_TIMEOUT_S = 8
CHECKSUM = r"^sha256:[0-9a-f]{64}$"
# A UUIDv7, as render-request/v1 and the admission store take it.
COMMAND_ID = r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
# A stored file's name, as PocketBase writes it.
_FILE_NAME = re.compile(r"[A-Za-z0-9_.-]{1,255}")


class RenderRequestV1(StrictModel):
    """render-request/v1 (contracts/definitions/render-request.v1.schema.json,
    ROUNDS-00A-L02). The runner image doesn't carry contracts/, so this model
    mirrors the schema and tests/test_render_request.py runs one set of
    bodies through both."""

    snapshot_id: str = Field(pattern=RECORD_ID)
    expected_checksum: str = Field(pattern=CHECKSUM)
    format: Literal["pdf"]
    page_size: Literal["A4"]
    margin_mm: float = Field(ge=0, le=30, strict=True)
    locale: Literal["en"]
    idempotency_id: str = Field(pattern=COMMAND_ID)


class StoredMarkupUnusable(Exception):
    """The snapshot's stored file is missing, too large, or doesn't hold
    what its checksum says. Nothing a retry or a new snapshot fixes."""


def sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


async def _read(token: str, collection: str, record_id: str) -> dict[str, Any]:
    record = await admission.lookup(pb_get, token, f"/api/collections/{collection}/records/{record_id}")
    if not isinstance(record, dict) or record.get("id") != record_id:
        raise TypedError("not_found")
    return record


async def read_markup(token: str, snapshot_id: str, name: Any) -> bytes:
    """The snapshot's protected markup file, through a file token issued to
    the caller. PocketBase checks the snapshot's view rule for it again."""
    if not isinstance(name, str) or _FILE_NAME.fullmatch(name) is None:
        raise StoredMarkupUnusable("name")
    path = f"/api/files/{SNAPSHOTS}/{snapshot_id}/{urllib.parse.quote(name)}"
    chunks: list[bytes] = []
    size = 0
    try:
        async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=READ_TIMEOUT_S) as client:
            grant = await client.post(FILE_TOKEN_PATH, headers={"Authorization": f"Bearer {token}"})
            if grant.status_code == 401:
                raise TypedError("unauthenticated")
            try:
                file_token = grant.json().get("token") if grant.status_code == 200 else None
            except (ValueError, AttributeError):
                file_token = None
            if not isinstance(file_token, str) or not file_token:
                raise TypedError("auth_unavailable")
            async with client.stream("GET", path, params={"token": file_token}) as resp:
                if resp.status_code in (400, 403, 404):
                    raise StoredMarkupUnusable("missing")
                if resp.status_code != 200:
                    raise TypedError("auth_unavailable")
                async for chunk in resp.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_MARKUP_BYTES:
                        raise StoredMarkupUnusable("size")
                    chunks.append(chunk)
    except httpx.HTTPError:
        raise TypedError("auth_unavailable") from None
    return b"".join(chunks)


async def markup_for_render(token: str, account_id: str, req: RenderRequestV1) -> str:
    """Step 8 for ``POST /api/pdf/render``: the markup of the caller's own
    snapshot that ``req`` names, once its checksum and source check out.
    The record's owner is compared with the account as well as by the view
    rule."""
    record = await _read(token, SNAPSHOTS, req.snapshot_id)
    if record.get("user") != account_id:
        raise TypedError("not_found")
    checksum = record.get("content_checksum")
    if checksum != req.expected_checksum:
        raise TypedError("checksum_mismatch")
    collection = SOURCE_COLLECTIONS.get(record.get("source_kind"))
    source_id = record.get("source_id")
    if collection is None or not isinstance(source_id, str) or _RECORD_ID.fullmatch(source_id) is None:
        raise TypedError("not_found")
    source = await _read(token, collection, source_id)
    if source.get("user") != account_id:
        raise TypedError("not_found")
    raw = await read_markup(token, req.snapshot_id, record.get("markup"))
    if sha256(raw) != checksum:
        raise StoredMarkupUnusable("checksum")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise StoredMarkupUnusable("encoding") from None
