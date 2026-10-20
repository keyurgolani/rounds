"""Admission chain for execution and render routes (ROUNDS-00A-L01).

admission/v1. One chain decides every admitted request before any
subprocess, sidecar, or provider call, in this order:

1. Byte cap: 413 ``payload_too_large``.
2. Gate: 503 ``route_disabled``.
3. Account from the bearer through PocketBase's auth-refresh: 401
   ``unauthenticated``; PocketBase down or 5xx: 503 ``auth_unavailable``.
4. ``(tier, operation)`` table: 403 ``not_permitted``.
5. Fields, from the parsed body only: 413 ``limit_exceeded``, 422
   ``invalid_request`` (request models, ``app.limits``, ``app.errors``).
6. Idempotency and 7. quota: passed through until stage 3.
8. Lookups with the caller's token, in each route: 404 ``not_found``.
9. The replica's in-flight cap: 503 ``worker_unavailable``, then
   allocation through ``allocate``.

``AdmissionMiddleware`` runs steps 1 to 4 before the app reads the body
and writes one obs decision line per admitted request. ``ats-rule`` and
``pdf/health`` skip steps 6, 7, and 9. Routes outside ``ROUTES`` are
untouched; the 23 routes already on ``current_user`` and the anonymous
share read stay outside admission.
"""
from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable

import httpx
from fastapi import HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app import errors, gates, obs, sandbox
from app.errors import TypedError
from app.limits import KIB, MIB
from app.pb_auth import POCKETBASE_URL

STATE_KEY = "admission"
AUTH_REFRESH_PATH = "/api/collections/users/auth-refresh"
AUTH_TIMEOUT_S = 8
MAX_BEARER_CHARS = 4096
# Proposed: 4 in-flight runs per replica. The owner ratifies it.
REPLICA_SLOTS = 4


@dataclass(frozen=True)
class Route:
    gate: str
    operation: str
    max_body: int
    # Steps 6, 7, and 9 (idempotency, quota, in-flight cap) apply.
    allocates: bool = True


ROUTES: dict[tuple[str, str], Route] = {
    ("POST", "/api/run"): Route("RUN", "run", 512 * KIB),
    ("POST", "/api/evaluate"): Route("EVALUATE", "evaluate", 512 * KIB),
    ("POST", "/api/ai-coding/run-project"): Route("AI_CODING_RUN_PROJECT", "run_project", 6 * MIB),
    ("POST", "/api/ai-coding/grade"): Route("AI_CODING_GRADE", "grade", 6 * MIB),
    ("POST", "/api/take-home/run"): Route("TAKE_HOME_RUN", "take_home_run", 6 * MIB),
    ("POST", "/api/take-home/submit"): Route("TAKE_HOME_SUBMIT", "take_home_submit", 6 * MIB),
    ("POST", "/api/pdf/render"): Route("PDF_RENDER", "pdf_render", 2 * MIB),
    ("GET", "/api/pdf/health"): Route("PDF_HEALTH", "pdf_health", 0, allocates=False),
    ("POST", "/api/ai/ats-rule"): Route("ATS_RULE", "ats_rule", 1 * MIB, allocates=False),
}

TIERS = ("standard", "demo")
# (tier, operation) -> permitted. Every pair is permitted until stage 3
# adds the demo tier's limits.
PERMITS: dict[tuple[str, str], bool] = {
    (tier, route.operation): True for tier in TIERS for route in ROUTES.values()
}


@dataclass
class Admission:
    """What admission knows about one request, on ``request.state``."""

    route: Route
    path: str
    method: str
    account: dict[str, Any] | None = None
    tier: str = "anonymous"
    code: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def state(request: Request) -> Admission | None:
    return request.scope.get("state", {}).get(STATE_KEY)


def account(request: Request) -> dict[str, Any] | None:
    admitted = state(request)
    return admitted.account if admitted is not None else None


def tier_of(record: dict[str, Any]) -> str:
    # TODO(ROUNDS-00B-L07): #177 repoints this accessor at
    # account_system_state; stage 3 makes is_demo immutable to clients.
    return "demo" if record.get("is_demo") is True else "standard"


def bearer_from(headers: list[tuple[bytes, bytes]]) -> str | None:
    for name, value in headers:
        if name.lower() != b"authorization":
            continue
        raw = value.decode("latin-1").strip()
        scheme, _, token = raw.partition(" ")
        token = token.strip()
        if scheme.lower() != "bearer" or not token or len(token) > MAX_BEARER_CHARS or any(c.isspace() for c in token):
            return None
        return token
    return None


async def authenticate(token: str) -> dict[str, Any]:
    """Step 3: the account behind ``token``, from PocketBase."""
    try:
        async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=AUTH_TIMEOUT_S) as client:
            resp = await client.post(AUTH_REFRESH_PATH, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError:
        raise TypedError("auth_unavailable") from None
    if resp.status_code >= 500:
        raise TypedError("auth_unavailable")
    if resp.status_code != 200:
        raise TypedError("unauthenticated")
    try:
        record = (resp.json() or {}).get("record") or {}
    except ValueError:
        raise TypedError("auth_unavailable") from None
    if not isinstance(record, dict) or not record.get("id"):
        raise TypedError("unauthenticated")
    return {"id": record["id"], "token": token, "record": record}


def _content_length(headers: list[tuple[bytes, bytes]]) -> int | None:
    for name, value in headers:
        if name.lower() == b"content-length":
            try:
                return int(value)
            except ValueError:
                return -1
    return None


class AdmissionMiddleware:
    """Steps 1 to 4 for the routes in ``ROUTES``, before the body is read."""

    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        route = ROUTES.get((scope.get("method", ""), scope.get("path", "")))
        if route is None:
            await self.app(scope, receive, send)
            return

        started = time.monotonic()
        admitted = Admission(route=route, path=scope["path"], method=scope["method"])
        scope.setdefault("state", {})[STATE_KEY] = admitted
        response: dict[str, Any] = {}

        async def send_tracked(message: dict) -> None:
            if message.get("type") == "http.response.start":
                response["status"] = message.get("status")
            await send(message)

        try:
            await self._before_body(scope, admitted)
        except TypedError as denial:
            admitted.code = denial.code
            await _send_typed(scope, send_tracked, denial)
            _log_decision(admitted, response.get("status"), started)
            return

        received = 0

        async def receive_capped() -> dict:
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body") or b"")
                if received > route.max_body:
                    raise TypedError("payload_too_large")
            return message

        try:
            await self.app(scope, receive_capped, send_tracked)
        except TypedError as denial:
            # Raised outside the app's exception handling.
            if "status" in response:
                raise
            admitted.code = denial.code
            await _send_typed(scope, send_tracked, denial)
        except Exception:
            # Starlette's error handler answers 500 further out.
            response.setdefault("status", 500)
            raise
        finally:
            _log_decision(admitted, response.get("status"), started)

    async def _before_body(self, scope: dict, admitted: Admission) -> None:
        route = admitted.route
        headers = scope.get("headers") or []
        # 1. Byte cap from the declared length. Bodies without one are
        # counted as they arrive.
        declared = _content_length(headers)
        if declared is not None and (declared < 0 or declared > route.max_body):
            raise TypedError("payload_too_large")
        # 2. Gate.
        if not gates.route_enabled(route.gate):
            raise TypedError("route_disabled")
        # 3. Account.
        token = bearer_from(headers)
        if token is None:
            raise TypedError("unauthenticated")
        user = await authenticate(token)
        admitted.account = user
        admitted.tier = tier_of(user.get("record") or {})
        # 4. Tier and operation.
        if not PERMITS.get((admitted.tier, route.operation), False):
            raise TypedError("not_permitted")
        # 6. Idempotency and 7. quota.
        # TODO(ROUNDS-00A-L01): stage 3 checks the Idempotency-Key and
        # charges the quota here, behind ENFORCE_IDEMPOTENCY and
        # ENFORCE_QUOTA.


async def _send_typed(scope: dict, send: Callable, denial: TypedError) -> None:
    cid = obs.current_correlation_id() or obs.correlation_id()
    body = errors.envelope(denial.code, denial.detail, cid)
    payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(payload)).encode("latin-1")),
    ]
    for name, value in (denial.headers or {}).items():
        headers.append((name.lower().encode("latin-1"), str(value).encode("latin-1")))
    await send({"type": "http.response.start", "status": denial.status_code, "headers": headers})
    await send({"type": "http.response.body", "body": payload})


def _log_decision(admitted: Admission, status: int | None, started: float) -> None:
    record = admitted.account.get("record") if admitted.account else None
    obs.emit(
        "decision",
        correlation_id=obs.current_correlation_id(),
        account=obs.account_pseudonym(record.get("id")) if isinstance(record, dict) else None,
        tier=admitted.tier,
        route=admitted.path,
        method=admitted.method,
        status=status,
        code=admitted.code,
        quota="skipped",
        latency_ms=int((time.monotonic() - started) * 1000),
        service="runner",
    )


# ---------------------------------------------------------------------------
# Step 8: lookups with the caller's token
# ---------------------------------------------------------------------------

Fetch = Callable[..., Awaitable[Any]]


async def lookup(fetch: Fetch, token: str, path: str, params: dict[str, Any] | None = None) -> Any:
    """One PocketBase read for step 8. A missing or foreign record is
    ``None``; PocketBase trouble is 503 ``auth_unavailable`` and never
    echoes PocketBase's text."""
    try:
        if params is None:
            return await fetch(token, path)
        return await fetch(token, path, params=params)
    except TypedError:
        raise
    except HTTPException as err:
        if err.status_code == 401:
            raise TypedError("unauthenticated") from None
        if err.status_code in (400, 403, 404):
            return None
        raise TypedError("auth_unavailable") from None
    except httpx.HTTPError:
        raise TypedError("auth_unavailable") from None


async def first_item(fetch: Fetch, token: str, collection: str, slug: str) -> dict[str, Any]:
    """The record in ``collection`` whose ``slug`` is ``slug``, or 404.
    ``slug`` is already validated against ``limits.SLUG_PATTERN``."""
    data = await lookup(
        fetch,
        token,
        f"/api/collections/{collection}/records",
        {"filter": f"slug='{slug}'", "perPage": 1},
    )
    items = (data or {}).get("items") if isinstance(data, dict) else None
    if not items or not isinstance(items[0], dict):
        raise TypedError("not_found")
    return items[0]


# ---------------------------------------------------------------------------
# Step 9: the replica's in-flight cap
# ---------------------------------------------------------------------------

_pool = sandbox.SlotPool(REPLICA_SLOTS)


def pool() -> sandbox.SlotPool:
    return _pool


@asynccontextmanager
async def allocate() -> AsyncIterator[sandbox.Sandbox]:
    """Step 9: one in-flight slot, or 503 ``worker_unavailable``. The
    slot's cleanup (the uid's process scan, the reap wait, and the temp
    sweeps) runs in the threadpool, off the event loop, and finishes
    before the slot is free again, even when the request is cancelled."""
    slot = _pool.try_acquire()
    if slot is None:
        raise TypedError("worker_unavailable")
    try:
        yield slot
    finally:
        await run_in_threadpool(_pool.release, slot)
