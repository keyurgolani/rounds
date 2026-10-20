"""Typed error envelope for runner denials (admission/v1).

A typed error answers ``{"detail", "code", "correlation_id"}``. ``code``
comes from ``CODES``, ``detail`` is a fixed sentence that never repeats
request content, and ``correlation_id`` matches the
``X-Correlation-Id`` header. A 429 can carry ``Retry-After``.

Raising ``TypedError`` also writes one obs decision line. Nothing in
the runner raises it yet; admission does from #1's stage 2. Legacy
``HTTPException`` responses keep their shape and gain only the
correlation header.

TODO(ROUNDS-00A-L01): stage 2 raises ``TypedError`` from admission and
moves the admitted routes' internal error text onto fixed details.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import obs

ENVELOPE_VERSION = "admission/v1"
ENVELOPE_KEYS = ("detail", "code", "correlation_id")

# Code -> default HTTP status, in #1's admission order.
CODES: dict[str, int] = {
    "payload_too_large": 413,
    "route_disabled": 503,
    "unauthenticated": 401,
    "auth_unavailable": 503,
    "not_permitted": 403,
    "limit_exceeded": 413,
    "invalid_request": 422,
    "idempotency_key_required": 400,
    "already_completed": 409,
    "quota_exceeded": 429,
    "demo_limit_reached": 429,
    "quota_unavailable": 503,
    "not_found": 404,
    "worker_unavailable": 503,
    "destination_denied": 403,
}


class TypedError(Exception):
    """A denial with a registered code and a fixed, content-free detail."""

    def __init__(
        self,
        code: str,
        detail: str,
        *,
        status: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        if code not in CODES:
            raise ValueError(f"unknown error code {code!r}")
        if not isinstance(detail, str) or not detail.strip():
            raise ValueError("detail must be a non-empty string")
        if retry_after is not None and (isinstance(retry_after, bool) or not isinstance(retry_after, int) or retry_after < 0):
            raise ValueError("retry_after must be a non-negative whole number of seconds")
        self.code = code
        self.detail = detail
        self.status = status if status is not None else CODES[code]
        self.retry_after = retry_after
        super().__init__(f"{self.status} {code}")


def envelope(code: str, detail: str, correlation_id: str) -> dict[str, str]:
    return {"detail": detail, "code": code, "correlation_id": correlation_id}


def request_correlation_id(request: Request) -> str:
    cid = getattr(request.state, "correlation_id", None)
    return cid if obs.is_correlation_id(cid) else obs.correlation_id()


async def typed_error_handler(request: Request, exc: TypedError) -> JSONResponse:
    cid = request_correlation_id(request)
    route = request.scope.get("route")
    obs.emit(
        "decision",
        correlation_id=cid,
        route=getattr(route, "path", None),
        method=request.method,
        status=exc.status,
        code=exc.code,
    )
    # CorrelationIdMiddleware adds X-Correlation-Id to every response.
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after is not None else None
    return JSONResponse(envelope(exc.code, exc.detail, cid), status_code=exc.status, headers=headers)


def install(app: FastAPI) -> None:
    app.add_exception_handler(TypedError, typed_error_handler)
