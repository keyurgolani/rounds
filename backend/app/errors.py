"""Typed error envelope for runner denials (admission/v1).

A typed error answers ``{"detail", "code", "correlation_id"}``. ``code``
comes from ``CODES``, ``detail`` is a fixed sentence that never repeats
request content, and ``correlation_id`` matches the
``X-Correlation-Id`` header. A 429 can carry ``Retry-After``.

A completed command's replay (``Replayed``) answers its stored response
as it was, with ``Idempotent-Replayed: true``.

``TypedError`` is an ``HTTPException``, so FastAPI passes it through
body parsing and dependencies untouched. On an admitted route the
admission middleware writes the one decision line for the request; on
any other route the handler here writes it. Legacy ``HTTPException``
responses keep their shape and gain only the correlation header.

On admitted routes a request that fails validation answers 422
``invalid_request``, or 413 ``limit_exceeded`` when a field is over its
limit, instead of FastAPI's error list.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
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
    "idempotency_mismatch": 409,
    "already_in_flight": 409,
    "quota_exceeded": 429,
    "demo_limit_reached": 429,
    "quota_unavailable": 503,
    "not_found": 404,
    "worker_unavailable": 503,
    "destination_denied": 403,
}

# The fixed sentence each code answers with unless a caller passes its own.
DETAILS: dict[str, str] = {
    "payload_too_large": "The request is larger than this route accepts.",
    "route_disabled": "This is turned off on this server.",
    "unauthenticated": "Sign in to continue.",
    "auth_unavailable": "Sign-in can't be checked right now. Try again shortly.",
    "not_permitted": "This isn't available for this account.",
    "limit_exceeded": "Part of the request is over its size limit.",
    "invalid_request": "The request doesn't match what this route accepts.",
    "idempotency_key_required": "This request needs an Idempotency-Key.",
    "already_completed": "This request already ran.",
    "idempotency_mismatch": "This Idempotency-Key was already used for a different request.",
    "already_in_flight": "This request is still running. Try again shortly.",
    "quota_exceeded": "You've reached the limit for now.",
    "demo_limit_reached": "The demo limit is reached for now.",
    "quota_unavailable": "Limits can't be checked right now. Try again shortly.",
    "not_found": "Not found.",
    "worker_unavailable": "The runner is busy or unavailable. Try again shortly.",
    "destination_denied": "This provider address isn't allowed.",
}

# Pydantic error type a field validator raises for an over-limit value.
LIMIT_ERROR_TYPE = "limit_exceeded"


class TypedError(HTTPException):
    """A denial with a registered code and a fixed, content-free detail."""

    def __init__(
        self,
        code: str,
        detail: str | None = None,
        *,
        status: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        if code not in CODES:
            raise ValueError(f"unknown error code {code!r}")
        if detail is None:
            detail = DETAILS[code]
        if not isinstance(detail, str) or not detail.strip():
            raise ValueError("detail must be a non-empty string")
        if retry_after is not None and (isinstance(retry_after, bool) or not isinstance(retry_after, int) or retry_after < 0):
            raise ValueError("retry_after must be a non-negative whole number of seconds")
        self.code = code
        self.retry_after = retry_after
        resolved = status if status is not None else CODES[code]
        headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
        super().__init__(status_code=resolved, detail=detail, headers=headers)

    @property
    def status(self) -> int:
        return self.status_code

    def __str__(self) -> str:
        return f"{self.status_code} {self.code}"


class Replayed(Exception):
    """Step 6: a completed command's stored response, answered again
    without running anything."""

    def __init__(self, status: int, body: Any) -> None:
        super().__init__(f"replayed {status}")
        self.status = status
        self.body = body


REPLAY_HEADER = "Idempotent-Replayed"


def envelope(code: str, detail: str, correlation_id: str) -> dict[str, str]:
    return {"detail": detail, "code": code, "correlation_id": correlation_id}


def request_correlation_id(request: Request) -> str:
    cid = getattr(request.state, "correlation_id", None)
    return cid if obs.is_correlation_id(cid) else obs.correlation_id()


def typed_response(request: Request, exc: TypedError) -> JSONResponse:
    """The envelope for ``exc``. Admission's decision line records it."""
    # Imported here: admission imports this module.
    from app import admission

    cid = request_correlation_id(request)
    admitted = admission.state(request)
    if admitted is not None:
        admitted.code = exc.code
    else:
        route = request.scope.get("route")
        obs.emit(
            "decision",
            correlation_id=cid,
            route=getattr(route, "path", None),
            method=request.method,
            status=exc.status_code,
            code=exc.code,
        )
    # CorrelationIdMiddleware adds X-Correlation-Id to every response.
    return JSONResponse(
        envelope(exc.code, exc.detail, cid), status_code=exc.status_code, headers=exc.headers
    )


async def typed_error_handler(request: Request, exc: TypedError) -> JSONResponse:
    return typed_response(request, exc)


async def replayed_handler(_request: Request, exc: Replayed) -> JSONResponse:
    # Admission's decision line records the replay.
    return JSONResponse(exc.body, status_code=exc.status, headers={REPLAY_HEADER: "true"})


async def validation_error_handler(request: Request, exc: RequestValidationError):
    from app import admission

    if admission.state(request) is None:
        return await request_validation_exception_handler(request, exc)
    over_limit = any(err.get("type") == LIMIT_ERROR_TYPE for err in exc.errors())
    code = "limit_exceeded" if over_limit else "invalid_request"
    return typed_response(request, TypedError(code))


def install(app: FastAPI) -> None:
    app.add_exception_handler(TypedError, typed_error_handler)
    app.add_exception_handler(Replayed, replayed_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
