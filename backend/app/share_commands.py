"""CreateShare and RotateShareBearer at the runner (ROUNDS-00B-L04).

  POST /api/share                            CreateShare, while
                                             ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION
                                             is enabled (routers/share.py)
  POST /api/share/capabilities/{id}/rotate   RotateShareBearer
                                             (routers/share_capabilities.py)

A share link's secret is shown once. The runner mints the bearer
(app/share_secrets.py) and sends PocketBase only its digest and, for a
password, its pw1 verifier (app/share_password.py). The bearer goes back in
the one response that issues it, with ``secret_delivery: "issued"``. A retry
under the same Idempotency-Key answers the same capability with
``secret_delivery: "already-issued"`` and no bearer; an owner who lost the
first response rotates.

Both commands need an Idempotency-Key, whatever ENFORCE_IDEMPOTENCY says,
and neither is an admission route, since admission keeps a route's whole
response for its replay. Their rows are #1's admission_commands rows, which
PocketBase's hook routes under /api/rounds/share (share_secrets.js) write
in the same transaction as the capability, with the result a replay
answers: the capability's fields and never the bearer. The fingerprint sees
whether a password was set, never the password. Each body is at most 4 KiB
of JSON with no field beyond the model's; anything else is a fixed 400 that
never repeats the request.

CreateShare, in order: the caller's bearer (401), the key, the body, the
digest key (503), then the command's row: a completed one answers
already-issued before anything else runs. Then the source's ``updated``,
read with the owner's bearer (404 for a missing or another account's), and
#4's snapshot command under the key the row keeps for it, admitted as
snapshot_create, so a retry gets the same snapshot. #4's ineligible answers
as it is, and a source edited since the first attempt is 409
snapshot_conflict; neither writes a capability. Then the verifier, and the
capability in one PocketBase transaction.

RotateShareBearer takes ``{expected_capability_version}``. One transaction
swaps the digest and raises the version, so the old bearer resolves nothing
once it commits. A stale version is 409 capability_version_conflict, a
revoked or expired capability 409 capability_revoked or capability_expired,
and another account's or a missing one 404. Its target, password, and
expiry stay. With the gate closed it's 503 route_disabled.

Each command logs one share.create or share.rotate line: the account's
pseudonym, the capability id once there is one, and a coarse code.
"""
from __future__ import annotations

import logging
import re
import secrets
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StrictInt, ValidationError

from app import admission, admission_state, gates, legacy_snapshots, obs, share_password, share_secrets
from app.errors import TypedError
from app.limits import KIB, StrictModel
from app.pb_auth import POCKETBASE_URL, pb_get

_log = logging.getLogger(__name__)

VERSION = "share-secrets/v1"
BEGIN_PATH = "/api/rounds/share/commands"
CAPABILITIES_PATH = "/api/rounds/share/capabilities"
TIMEOUT_S = 8
MAX_BODY = 4 * KIB
# The routes as the fingerprints name them.
CREATE_ROUTE = "POST /api/share"
ROTATE_ROUTE = "POST /api/share/capabilities/{capability_id}/rotate"
# #4's route, as its hook fingerprints the snapshot command.
SNAPSHOT_ROUTE = "POST /api/pdf/snapshots"
SNAPSHOT_GATE = "LEGACY_SNAPSHOT_CREATE"

RECORD_ID = r"^[a-z0-9]{15}$"
_RECORD_ID = re.compile(RECORD_ID)
DATE = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
# #11's bounds (share_capabilities.js): the most days a link may last, and
# the longest purpose.
MAX_DAYS = 365
PURPOSE_MAX = 80
# Kept under #11's ceiling, in case PocketBase's clock runs behind.
_CLOCK_MARGIN = timedelta(seconds=60)
# Which source each target field names, and where the owner reads it.
SOURCES = {"resume_id": ("resume", "resumes"), "variant_id": ("variant", "resume_variants")}
TARGET_KIND = "legacy_artifact_snapshot"
NO_STORE = {"Cache-Control": "no-store"}


class CreateShareBody(StrictModel):
    resume_id: str | None = Field(None, pattern=RECORD_ID)
    variant_id: str | None = Field(None, pattern=RECORD_ID)
    # A day: the link works through the end of it, UTC.
    expires_at: str | None = Field(None, pattern=DATE)
    purpose: str | None = Field(None, max_length=PURPOSE_MAX)
    password: str | None = None


class _CreateFingerprint(StrictModel):
    resume_id: str | None
    variant_id: str | None
    expires_at: str | None
    purpose: str | None
    password_set: bool


class RotateBody(StrictModel):
    expected_capability_version: StrictInt = Field(ge=1)


class _RotateFingerprint(StrictModel):
    capability_id: str
    expected_capability_version: int


# ---------------------------------------------------------------------------
# Shared steps
# ---------------------------------------------------------------------------


def new_command_id() -> str:
    """A UUIDv7 (RFC 9562): 48-bit Unix milliseconds, then random bits."""
    raw = bytearray((time.time_ns() // 1_000_000).to_bytes(6, "big") + secrets.token_bytes(10))
    raw[6] = 0x70 | (raw[6] & 0x0F)
    raw[8] = 0x80 | (raw[8] & 0x3F)
    return str(uuid.UUID(bytes=bytes(raw)))


def _invalid() -> TypedError:
    return TypedError("invalid_request", status=400)


async def _account(request: Request) -> dict[str, Any]:
    token = admission.bearer_from(request.scope.get("headers") or [])
    if token is None:
        raise TypedError("unauthenticated")
    return await admission.authenticate(token)


def _key(request: Request) -> str:
    key = admission_state.command_id(request.scope.get("headers") or [])
    if key is None:
        raise TypedError("idempotency_key_required")
    return key


async def _body(request: Request, model: type[BaseModel]) -> Any:
    """The request's JSON body as ``model``, or the fixed 400."""
    media = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_BODY:
            raise _invalid()
    if media != "application/json":
        raise _invalid()
    try:
        return model.model_validate_json(bytes(raw))
    except ValidationError:
        raise _invalid() from None


def _bearer() -> tuple[str, str]:
    """A new bearer and its digest. 503 without the digest key."""
    token = share_secrets.new_token()
    try:
        return token, share_secrets.digest(token)
    except share_secrets.Unavailable:
        _log.warning("share commands: %s is unset, so no share link can be made", share_secrets.SECRET_ENV)
        raise TypedError("shares_unavailable") from None


async def _hook(path: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
    """One call to a share hook route, with the owner's bearer and the
    runner key."""
    try:
        key = admission_state.runner_key()
    except admission_state.Unconfigured:
        _log.warning("share commands: the runner has no usable %s", admission_state.RUNNER_KEY_ENV)
        raise TypedError("shares_unavailable") from None
    headers = {"Authorization": f"Bearer {token}", admission_state.RUNNER_KEY_HEADER: key}
    try:
        async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=TIMEOUT_S) as client:
            resp = await client.post(path, json=payload, headers=headers)
    except httpx.HTTPError as err:
        _log.warning("share commands: no answer from PocketBase (%s)", type(err).__name__)
        raise TypedError("shares_unavailable") from None
    try:
        body = resp.json()
    except ValueError:
        body = None
    return resp.status_code, body


# The hook's refusals, by status and code, and the runner's.
_REFUSALS: dict[tuple[int, str], tuple[str, int | None]] = {
    (400, "invalid_request"): ("invalid_request", 400),
    (404, "not_found"): ("not_found", None),
    (409, "idempotency_mismatch"): ("idempotency_mismatch", None),
    (409, "capability_revoked"): ("capability_revoked", None),
    (409, "capability_expired"): ("capability_expired", None),
    (409, "capability_version_conflict"): ("capability_version_conflict", None),
}


def _refusal(status: int, body: Any) -> TypedError:
    error = body.get("error") if isinstance(body, dict) and body.get("v") == VERSION else None
    if status == 401:
        return TypedError("unauthenticated")
    named = _REFUSALS.get((status, error)) if isinstance(error, str) else None
    if named is not None:
        return TypedError(named[0], status=named[1])
    code = error if isinstance(error, str) and re.fullmatch(r"[a-z_]{1,40}", error) else "none"
    _log.warning("share commands: PocketBase answered %s (%s)", status, code)
    return TypedError("shares_unavailable")


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _scope_ok(scope: Any) -> bool:
    if not isinstance(scope, dict) or scope.get("target_kind") != TARGET_KIND or scope.get("projection_version") != 1:
        return False
    named = set(scope) - {"target_kind", "projection_version"}
    return len(named) == 1 and named <= {"resume_id", "variant_id"} and all(
        isinstance(scope[k], str) and _RECORD_ID.fullmatch(scope[k]) for k in named)


def _fields(result: Any, status: int, with_scope: bool) -> dict[str, Any] | None:
    """A kept result's capability fields, or None for another shape."""
    if not isinstance(result, dict) or set(result) != {"status", "body"} or result["status"] != status:
        return None
    fields = result["body"]
    keys = {"capability_id", "state", "expires_at", "capability_version"} | ({"scope"} if with_scope else set())
    if not isinstance(fields, dict) or set(fields) != keys:
        return None
    if not (isinstance(fields["capability_id"], str) and _RECORD_ID.fullmatch(fields["capability_id"])):
        return None
    if not isinstance(fields["state"], str) or not isinstance(fields["expires_at"], str):
        return None
    if not (_whole(fields["capability_version"]) and fields["capability_version"] >= 1):
        return None
    if with_scope and not _scope_ok(fields["scope"]):
        return None
    return fields


def _delivered(status: int, body: Any, issued: int, with_scope: bool) -> tuple[str, dict[str, Any]] | None:
    """("issued" or "already-issued", the fields) for a write's answer."""
    if not isinstance(body, dict) or body.get("v") != VERSION or set(body) != {"v", "delivery", "result"}:
        return None
    if body["delivery"] == "issued" and status == issued:
        delivery = "issued"
    elif body["delivery"] == "already_issued" and status == 200:
        delivery = "already-issued"
    else:
        return None
    fields = _fields(body["result"], issued, with_scope)
    return (delivery, fields) if fields is not None else None


def _answer(delivery: str, fields: dict[str, Any], token: str, issued: int) -> JSONResponse:
    out = dict(fields, secret_delivery=delivery)
    if delivery == "issued":
        out["token"] = token
        return JSONResponse(out, status_code=issued, headers=dict(NO_STORE))
    return JSONResponse(out, status_code=200, headers=dict(NO_STORE))


def _log_line(event: str, account: dict[str, Any] | None, record: str | None, code: str) -> None:
    obs.emit(event, correlation_id=obs.current_correlation_id(),
             account=obs.account_pseudonym(account["id"]) if account else None, record=record, code=code)


# ---------------------------------------------------------------------------
# CreateShare
# ---------------------------------------------------------------------------


def expiry(day: str | None, now: datetime) -> str | None:
    """#11's expiry text for a chosen day: the end of that day, UTC, or the
    latest #11 allows when that's sooner. None takes #11's default."""
    if day is None:
        return None
    try:
        chosen = date.fromisoformat(day)
    except ValueError:
        raise _invalid() from None
    end = datetime(chosen.year, chosen.month, chosen.day, 23, 59, 59, 999000, tzinfo=timezone.utc)
    end = min(end, now + timedelta(days=MAX_DAYS) - _CLOCK_MARGIN)
    if end <= now:
        raise _invalid()
    return end.strftime("%Y-%m-%d %H:%M:%S.") + f"{end.microsecond // 1000:03d}Z"


async def _source_updated(token: str, kind_field: str, source_id: str) -> str:
    """The owner's source's ``updated``, read with the owner's bearer; 404
    for a missing one and another account's alike."""
    collection = SOURCES[kind_field][1]
    record = await admission.lookup(pb_get, token, f"/api/collections/{collection}/records/{source_id}",
                                    {"fields": "id,updated"})
    updated = record.get("updated") if isinstance(record, dict) else None
    if not isinstance(updated, str):
        raise TypedError("not_found")
    return updated


async def _snapshot(token: str, kind: str, source_id: str, updated: str, key: str) -> dict[str, Any]:
    """#4's snapshot command under ``key``, admitted as snapshot_create as
    its own route admits it, so a retry under the key replays its answer:
    the created, reused, or ineligible body."""
    if not gates.route_enabled(SNAPSHOT_GATE):
        raise TypedError("route_disabled")
    try:
        req = legacy_snapshots.SnapshotRequest(source_kind=kind, source_id=source_id, expected_updated=updated)
    except ValidationError:
        raise TypedError("shares_unavailable") from None
    fingerprint = admission_state.fingerprint(SNAPSHOT_ROUTE, "snapshot_create", req)
    quota = gates.value("ENFORCE_QUOTA")
    # admission's store client, which tests swap, as admission.begin uses it.
    store = admission.store
    lease = store.new_lease()
    try:
        decision = await store.admit(token, "snapshot_create", legacy_snapshots.MATERIALIZE_TIMEOUT_S, key,
                                     fingerprint, "enforce", lease=lease, quota=quota)
    except store.Unavailable as unavailable:
        if not isinstance(unavailable, store.Refused):
            await admission.end_lease(token, lease, "infrastructure", None)
        raise TypedError("quota_unavailable") from None

    outcome, kept = "denied", None
    try:
        if decision.idempotency == "replay":
            if decision.result is None:
                raise TypedError("already_completed")
            return legacy_snapshots.read_answer(decision.result["status"], decision.result["body"])[1]
        if decision.idempotency == "mismatch":
            # The first attempt snapshotted the source as it was then.
            raise TypedError("snapshot_conflict")
        if decision.idempotency == "in_flight":
            raise TypedError("already_in_flight", retry_after=decision.retry_after or None)
        if decision.quota in ("exceeded", "demo_limit") and quota == "enforce":
            code = "quota_exceeded" if decision.quota == "exceeded" else "demo_limit_reached"
            raise TypedError(code, retry_after=decision.retry_after)
        status, body = await legacy_snapshots.create(token, req, key)
        outcome, kept = "completed", {"status": status, "body": body}
        return body
    except TypedError:
        raise
    except Exception:
        outcome = "error"
        raise
    finally:
        if decision.leased:
            await admission.end_lease(token, lease, outcome, kept)


async def create(request: Request) -> JSONResponse:
    """CreateShare. The bearer is in the answer once."""
    account: dict[str, Any] | None = None
    record: str | None = None
    try:
        account = await _account(request)
        key = _key(request)
        body: CreateShareBody = await _body(request, CreateShareBody)
        named = [field for field in SOURCES if getattr(body, field) is not None]
        if len(named) != 1:
            raise _invalid()
        if body.password is not None and not share_password.valid_password(body.password):
            raise _invalid()
        expires_at = expiry(body.expires_at, datetime.now(timezone.utc))
        token, bearer = _bearer()
        fingerprint = admission_state.fingerprint(CREATE_ROUTE, "share_create", _CreateFingerprint(
            resume_id=body.resume_id, variant_id=body.variant_id, expires_at=body.expires_at, purpose=body.purpose,
            password_set=body.password is not None))

        status, begun = await _hook(BEGIN_PATH, account["token"], {
            "command_id": key, "operation": "share_create", "fingerprint": fingerprint,
            "snapshot_command_id": new_command_id(),
        })
        if status != 200 or not isinstance(begun, dict) or begun.get("v") != VERSION:
            raise _refusal(status, begun)
        if begun.get("verdict") == "replay":
            fields = _fields(begun.get("result"), 201, with_scope=True)
            if fields is None:
                raise _refusal(503, None)
            record = fields["capability_id"]
            _log_line("share.create", account, record, "already_issued")
            return _answer("already-issued", fields, token, 201)
        snapshot_key = begun.get("snapshot_command_id")
        if begun.get("verdict") not in ("new", "retry") or not isinstance(snapshot_key, str) or \
                admission_state.COMMAND_ID.fullmatch(snapshot_key) is None:
            raise _refusal(503, None)

        field = named[0]
        source_id = getattr(body, field)
        updated = await _source_updated(account["token"], field, source_id)
        snapshot = await _snapshot(account["token"], SOURCES[field][0], source_id, updated, snapshot_key)
        if snapshot["status"] == "ineligible":
            _log_line("share.create", account, None, "ineligible")
            return JSONResponse({"status": "ineligible", "reason": snapshot["reason"]}, status_code=200,
                                headers=dict(NO_STORE))

        verifier = await share_password.hash_password(body.password) if body.password is not None else ""
        status, made = await _hook(CAPABILITIES_PATH, account["token"], {
            "command_id": key, "fingerprint": fingerprint, "snapshot_id": snapshot["snapshot_id"],
            "purpose": body.purpose, "expires_at": expires_at, "password_policy_ref": verifier,
            "bearer_digest": bearer, "digest_key_version": share_secrets.DIGEST_KEY_VERSION,
        })
        delivered = _delivered(status, made, 201, with_scope=True)
        if delivered is None:
            raise _refusal(status, made)
        delivery, fields = delivered
        record = fields["capability_id"]
        _log_line("share.create", account, record, delivery.replace("-", "_"))
        return _answer(delivery, fields, token, 201)
    except TypedError as err:
        _log_line("share.create", account, record, err.code)
        raise


# ---------------------------------------------------------------------------
# RotateShareBearer
# ---------------------------------------------------------------------------


async def rotate(request: Request, capability_id: str, gate_open: bool) -> JSONResponse:
    """RotateShareBearer. The new bearer is in the answer once."""
    account: dict[str, Any] | None = None
    try:
        account = await _account(request)
        if not gate_open:
            raise TypedError("route_disabled")
        key = _key(request)
        body: RotateBody = await _body(request, RotateBody)
        if _RECORD_ID.fullmatch(capability_id) is None:
            raise TypedError("not_found")
        token, bearer = _bearer()
        fingerprint = admission_state.fingerprint(ROTATE_ROUTE, "share_rotate", _RotateFingerprint(
            capability_id=capability_id, expected_capability_version=body.expected_capability_version))
        status, answer = await _hook(f"{CAPABILITIES_PATH}/{capability_id}/rotate", account["token"], {
            "command_id": key, "fingerprint": fingerprint,
            "expected_capability_version": body.expected_capability_version,
            "bearer_digest": bearer, "digest_key_version": share_secrets.DIGEST_KEY_VERSION,
        })
        delivered = _delivered(status, answer, 200, with_scope=False)
        if delivered is None or delivered[1]["capability_id"] != capability_id:
            raise _refusal(status, answer)
        delivery, fields = delivered
        _log_line("share.rotate", account, capability_id, delivery.replace("-", "_"))
        return _answer(delivery, fields, token, 200)
    except TypedError as err:
        named = account is not None and err.code != "not_found" and _RECORD_ID.fullmatch(capability_id) is not None
        _log_line("share.rotate", account, capability_id if named else None, err.code)
        raise
