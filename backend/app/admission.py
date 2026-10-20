"""Admission chain for execution and render routes (ROUNDS-00A-L01).

admission/v1. One chain decides every admitted request before any
subprocess, sidecar, or provider call, in this order:

1. Byte cap: 413 ``payload_too_large``.
2. Gate: 503 ``route_disabled``; on the six execution routes,
   ``ROUNDS_GATE_EXECUTION_DEFINITIONS=disabled`` is 503
   ``definitions_disabled`` (ROUNDS-00A-L02).
3. Account from the bearer through PocketBase's auth-refresh: 401
   ``unauthenticated``; PocketBase down or 5xx: 503 ``auth_unavailable``.
4. ``(tier, operation)`` table: 403 ``not_permitted``.
5. Fields, from the parsed body only: 413 ``limit_exceeded``, 422
   ``invalid_request`` (request models, ``app.limits``, ``app.errors``).
6. Idempotency, keyed on the ``Idempotency-Key`` (the command id) and a
   fingerprint of the route and the parsed body: 400
   ``idempotency_key_required``, the stored result of a completed
   command, 409 ``already_completed`` when none was kept, 409
   ``idempotency_mismatch``, or 409 ``already_in_flight``.
7. Quota: 429 ``quota_exceeded`` or ``demo_limit_reached`` with
   ``Retry-After``; the store down: 503 ``quota_unavailable``.
8. Lookups with the caller's token, in each route: 404 ``not_found``.
9. The replica's in-flight cap: 503 ``worker_unavailable``, then
   allocation through ``allocate``.

``AdmissionMiddleware`` runs steps 1 to 4 before the app reads the body
and writes one obs decision line per admitted request. Each allocating
route calls ``begin`` once FastAPI has parsed its body, which runs steps 6
and 7 in one call to the store (``app.admission_state``): the command
row, the charge, and the lease are written together or not at all.
Evaluate and grade ``settle`` their exact charge after step 8. When the
request ends, the middleware finishes the lease: a completed response is
kept for replay, a denial before anything ran leaves the command
retryable, and a failure after allocation leaves it
``failed_infrastructure``; a same-key retry of either runs admission
again. Only the infrastructure's failures (``INFRASTRUCTURE_CODES``) give
the wall seconds back. A lease whose end the store never hears about
stops counting when its window ends, and the sweep repairs its command.

``ENFORCE_IDEMPOTENCY`` and ``ENFORCE_QUOTA`` decide what steps 6 and 7
do: ``off`` skips the step, ``observe`` records what it would have
answered in the decision line (``would_deny``) and denies nothing, and
``enforce`` denies. Idempotency doesn't depend on the quota gate: with
quota ``off`` nothing is counted or charged, and the command is still
recorded. ``ats-rule`` and ``pdf/health`` skip steps 6, 7, and 9. Routes
outside ``ROUTES`` are untouched; the 23 routes already on
``current_user`` and the anonymous share read stay outside admission.
"""
from __future__ import annotations

import contextvars
import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable

import anyio
import httpx
from fastapi import HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app import admission_state, errors, gates, obs, sandbox
from app.errors import TypedError
from app.limits import KIB, MIB
from app.pb_auth import POCKETBASE_URL

STATE_KEY = "admission"
AUTH_REFRESH_PATH = "/api/collections/users/auth-refresh"
AUTH_TIMEOUT_S = 8
MAX_BEARER_CHARS = 4096
# Proposed: 4 in-flight runs per replica. The owner ratifies it.
REPLICA_SLOTS = 4
# How long the end of a request may wait on the store, over at most
# FINISH_ATTEMPTS calls of FINISH_CALL_TIMEOUT_S each with the backoffs
# between them, which together fit the budget (3 x 1.5 s + 0.75 s). It
# runs shielded, so a cancelled request still ends its lease when the
# store answers.
FINISH_TIMEOUT_S = 6
FINISH_ATTEMPTS = 3
FINISH_CALL_TIMEOUT_S = 1.5
FINISH_BACKOFF_S = (0.25, 0.5)
# Typed failures after allocation that are the infrastructure's, not the
# request's: they give the wall seconds back, and the app retries them.
# Any other failure once a slot ran the request, a render that ran out of
# time on its content included, keeps its charge and isn't retried.
INFRASTRUCTURE_CODES = frozenset({"auth_unavailable", "quota_unavailable", "worker_unavailable"})


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

# The routes that run a definition's code and tests (ROUNDS-00A-L02).
DEFINITION_OPERATIONS = frozenset({"run", "evaluate", "run_project", "grade", "take_home_run", "take_home_submit"})

TIERS = ("standard", "demo")
# (tier, operation) -> permitted. Every pair is permitted, as #1 starts;
# the demo tier's limits are its quota bucket in pb_hooks/admission.js.
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
    # Steps 6 and 7.
    begun: bool = False
    idempotency: str = "skipped"
    quota: str = "skipped"
    would_deny: str | None = None
    lease: str | None = None
    # Step 9 handed this request an in-flight slot.
    allocated: bool = False


_current: contextvars.ContextVar[Admission | None] = contextvars.ContextVar("rounds_admission", default=None)


def state(request: Request) -> Admission | None:
    return request.scope.get("state", {}).get(STATE_KEY)


def account(request: Request) -> dict[str, Any] | None:
    admitted = state(request)
    return admitted.account if admitted is not None else None


def tier_of(record: dict[str, Any]) -> str:
    # TODO(ROUNDS-00B-L07): #177 repoints this accessor at
    # account_system_state, with tierOf() in pb_hooks/admission.js. A
    # users hook there keeps clients from setting is_demo.
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
        # A leased request's response waits until the store has recorded
        # its end, so the caller never sees a result its key can't replay
        # yet, and a finished request never still counts as in flight.
        kept = _Kept()
        held: list[dict] = []

        async def send_tracked(message: dict) -> None:
            kind = message.get("type")
            if kind == "http.response.start":
                response["status"] = message.get("status")
            if admitted.lease is None:
                await send(message)
                return
            if kind == "http.response.start":
                kept.start(message)
            elif kind == "http.response.body":
                kept.add(message.get("body") or b"")
            held.append(message)
            if kind == "http.response.body" and not message.get("more_body", False):
                await _finish(admitted, response.get("status"), kept)
                for waiting in held:
                    await send(waiting)
                held.clear()

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

        current = _current.set(admitted)
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
            _current.reset(current)
            # A request that ended without a whole response: an exception,
            # or a cancellation.
            if admitted.lease is not None:
                await _finish(admitted, response.get("status"), kept)
            _log_decision(admitted, response.get("status"), started)
            # Whatever part of that response there was goes out as it was.
            for waiting in held:
                await send(waiting)

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
        if route.operation in DEFINITION_OPERATIONS and gates.value("EXECUTION_DEFINITIONS") == "disabled":
            raise TypedError("definitions_disabled")
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
        # 5 to 9 run in the route: FastAPI parses the body, then the
        # route calls begin().


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
        idempotency=admitted.idempotency,
        quota=admitted.quota,
        would_deny=admitted.would_deny,
        latency_ms=int((time.monotonic() - started) * 1000),
        service="runner",
    )


# ---------------------------------------------------------------------------
# Steps 6 and 7: idempotency and quota
# ---------------------------------------------------------------------------

# The store's client; tests swap in a fake with the same functions.
store = admission_state

# Step 6 verdicts that refuse the request, and the code each answers.
_REFUSALS = {"mismatch": "idempotency_mismatch", "in_flight": "already_in_flight"}


def _quota_code(verdict: str) -> str:
    return "quota_exceeded" if verdict == "exceeded" else "demo_limit_reached"


async def begin(
    request: Request, body: BaseModel, wall_seconds: int, max_wall_seconds: int | None = None
) -> None:
    """Steps 6 and 7 for an allocating route, once FastAPI has parsed its
    body, before any lookup. ``wall_seconds`` is the most this request's
    execution can run. Evaluate and grade pass their first case or
    checkpoint here, and as ``max_wall_seconds`` the most their cases or
    checkpoints can run, then ``settle`` after step 8; the lease ends by
    itself once that most has passed.

    A completed command answers its stored response (``errors.Replayed``)
    and runs nothing. A refused or over-limit request raises its typed
    denial when its gate enforces, and otherwise only records what the
    gate would have answered."""
    admitted = state(request)
    if admitted is None or not admitted.route.allocates:
        return
    admitted.begun = True
    idempotency = gates.value("ENFORCE_IDEMPOTENCY")
    quota = gates.value("ENFORCE_QUOTA")
    if idempotency == "off" and quota == "off":
        return

    key = fingerprint = None
    if idempotency != "off":
        key = admission_state.command_id(request.scope.get("headers") or [])
        if key is None:
            if idempotency == "enforce":
                raise TypedError("idempotency_key_required")
            admitted.idempotency = "missing"
            admitted.would_deny = "idempotency_key_required"
        else:
            fingerprint = admission_state.fingerprint(
                f"{admitted.method} {admitted.path}", admitted.route.operation, body
            )

    token = admitted.account["token"]
    lease = store.new_lease()
    try:
        decision = await store.admit(
            token,
            admitted.route.operation,
            wall_seconds,
            key,
            fingerprint,
            "enforce" if idempotency == "enforce" else "observe",
            lease=lease,
            quota=quota,
            max_wall_seconds=max_wall_seconds,
        )
    except store.Unavailable as unavailable:
        # With no answer, or one in the wrong shape, the store may have
        # written the lease and lost only its answer: end it, so its
        # command can be retried and it stops counting. A refusal (a
        # 4xx, 503 unconfigured, or no runner key) wrote nothing.
        if not isinstance(unavailable, store.Refused):
            await _end_lease(token, lease, "infrastructure", None)
        admitted.quota = "unavailable"
        if key is not None:
            admitted.idempotency = "unavailable"
        if "enforce" in (idempotency, quota):
            raise TypedError("quota_unavailable") from None
        admitted.would_deny = admitted.would_deny or "quota_unavailable"
        return
    if decision.leased:
        # From here the end of the request is recorded, whatever it is.
        admitted.lease = lease

    # Step 6.
    if key is not None:
        admitted.idempotency = decision.idempotency
    if decision.idempotency == "replay" and idempotency == "enforce":
        if decision.result is None:
            raise TypedError("already_completed")
        raise errors.Replayed(decision.result["status"], decision.result["body"])
    refusal = _REFUSALS.get(decision.idempotency)
    if refusal is not None:
        if idempotency == "enforce":
            wait = decision.retry_after if refusal == "already_in_flight" and decision.retry_after > 0 else None
            raise TypedError(refusal, retry_after=wait)
        admitted.would_deny = admitted.would_deny or refusal

    # Step 7.
    if decision.quota in ("exceeded", "demo_limit"):
        admitted.quota = decision.quota
        if quota == "enforce":
            raise TypedError(_quota_code(decision.quota), retry_after=decision.retry_after)
        admitted.would_deny = admitted.would_deny or _quota_code(decision.quota)
    elif decision.quota == "ok" and decision.leased:
        admitted.quota = "charged"


async def settle(request: Request, wall_seconds: int) -> None:
    """Evaluate and grade: the exact charge, once step 8 has loaded the
    definitions, at most the ``max_wall_seconds`` ``begin`` was given. A
    raise that doesn't fit the hour is a step 7 denial like admission's,
    and only a charged lease settles."""
    admitted = state(request)
    if admitted is None or admitted.lease is None or admitted.quota != "charged":
        return
    quota = gates.value("ENFORCE_QUOTA")
    try:
        settled = await store.settle(admitted.account["token"], admitted.lease, wall_seconds)
    except store.Unavailable:
        if quota == "enforce":
            raise TypedError("quota_unavailable") from None
        admitted.would_deny = admitted.would_deny or "quota_unavailable"
        return
    if settled.quota != "ok":
        admitted.quota = settled.quota
        if quota == "enforce":
            raise TypedError(_quota_code(settled.quota), retry_after=settled.retry_after)
        admitted.would_deny = admitted.would_deny or _quota_code(settled.quota)


class _Kept:
    """A leased request's JSON response, up to the store's limit."""

    def __init__(self) -> None:
        self.json = False
        self.chunks: list[bytes] = []
        self.size = 0
        self.over = False

    def start(self, message: dict) -> None:
        for name, value in message.get("headers") or []:
            if name.lower() == b"content-type":
                self.json = value.decode("latin-1").split(";")[0].strip().lower() == "application/json"

    def add(self, chunk: bytes) -> None:
        if self.over:
            return
        self.size += len(chunk)
        if self.size > admission_state.RESULT_MAX_BYTES:
            self.over, self.chunks = True, []
        else:
            self.chunks.append(chunk)

    def result(self, status: int) -> dict[str, Any] | None:
        if not self.json or self.over:
            return None
        try:
            return {"status": status, "body": json.loads(b"".join(self.chunks) or b"null")}
        except ValueError:
            return None


def _outcome(admitted: Admission, status: int | None, kept: _Kept) -> tuple[str, dict[str, Any] | None]:
    if status is not None and 200 <= status < 300:
        return "completed", kept.result(status)
    if admitted.code is not None:
        # Anything typed before a slot ran the request is a denial.
        if not admitted.allocated:
            return "denied", None
        if admitted.code in INFRASTRUCTURE_CODES:
            return "infrastructure", None
    return "error", None


async def _end_lease(token: str, lease: str, outcome: str, result: dict[str, Any] | None) -> bool:
    """Records a lease's end, trying again while the store doesn't answer.
    Shielded and bounded: a cancelled request still ends its lease, and a
    lease the store never hears about stops counting when its window
    ends. True when the store recorded it."""
    recorded = False
    with anyio.move_on_after(FINISH_TIMEOUT_S, shield=True):
        for attempt in range(FINISH_ATTEMPTS):
            try:
                # Bounds the whole call, which the client's timeout
                # bounds only per phase.
                with anyio.fail_after(FINISH_CALL_TIMEOUT_S):
                    recorded = await store.finish(token, lease, outcome, result, timeout=FINISH_CALL_TIMEOUT_S)
                break
            except store.Refused:
                break
            except (store.Unavailable, TimeoutError):
                if attempt < len(FINISH_BACKOFF_S):
                    await anyio.sleep(FINISH_BACKOFF_S[attempt])
    return recorded


async def _finish(admitted: Admission, status: int | None, kept: _Kept) -> None:
    lease, admitted.lease = admitted.lease, None
    outcome, result = _outcome(admitted, status, kept)
    recorded = await _end_lease(admitted.account["token"], lease, outcome, result)
    if recorded and outcome in ("denied", "infrastructure") and admitted.quota == "charged":
        admitted.quota = "refunded"


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
    before the slot is free again, even when the request is cancelled.

    An admitted route allocates only after ``begin``, so nothing runs
    without passing steps 6 and 7."""
    admitted = _current.get()
    if admitted is not None and admitted.route.allocates and not admitted.begun:
        raise RuntimeError("an admitted route allocates only after admission.begin()")
    slot = _pool.try_acquire()
    if slot is None:
        raise TypedError("worker_unavailable")
    if admitted is not None:
        admitted.allocated = True
    try:
        yield slot
    finally:
        # A cancelled anyio scope cancels every await inside it, this one
        # included, so the cleanup is shielded or the slot would leak.
        with anyio.CancelScope(shield=True):
            await run_in_threadpool(_pool.release, slot)
