"""Admission state client for steps 6 and 7 (ROUNDS-00A-L01 stage 3).

The runner keeps no admission state. ``pocketbase/pb_hooks/admission.js``
keeps it in ``admission_commands``, ``admission_counters``, and
``admission_leases``, and this module calls its routes under
``/api/rounds/admission/`` with the caller's bearer. PocketBase runs each
call in one transaction on its one write connection, so every runner
replica sees one count.

1. ``admit`` runs steps 6 and 7 together. It answers the idempotency
   verdict (``new``, ``retry``, ``replay``, ``mismatch``, ``in_flight``, or
   ``none`` without a key), the quota verdict (``ok``, ``exceeded``, or
   ``demo_limit``), a Retry-After, and a lease token when it charged and
   leased the request. It never charges past a limit. In observe mode a
   refused duplicate is still charged and leased, and its command row is
   left as it was.
2. ``settle`` moves evaluate's and grade's charge to the exact amount once
   step 8 has loaded the definitions.
3. ``finish`` ends an admitted request: ``completed`` with the response to
   replay, ``denied`` for a step 8 or 9 denial (retryable, wall seconds
   refunded), ``infrastructure`` for a typed failure after allocation
   (``failed_infrastructure``, refunded), or ``error`` for anything else
   (``failed_infrastructure``, kept).

A transport error, any status but the expected ones, or a body that isn't
the contract's shape is ``Unavailable``.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

import httpx
from pydantic import BaseModel

from app.pb_auth import POCKETBASE_URL

VERSION = "admission/v1"
BASE_PATH = "/api/rounds/admission"
TIMEOUT_S = 5
IDEMPOTENCY_HEADER = b"idempotency-key"
# runnerFetch mints one UUIDv7 per user action (frontend/src/lib/idempotency.ts).
COMMAND_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
LEASE = re.compile(r"[A-Za-z0-9]{43}")
# The largest response the runner sends to be kept for replay.
# pb_hooks/admission.js keeps up to as many characters of JSON.
RESULT_MAX_BYTES = 256 * 1024

IDEMPOTENCY_VERDICTS = frozenset({"new", "retry", "replay", "mismatch", "in_flight", "none"})
QUOTA_VERDICTS = frozenset({"ok", "exceeded", "demo_limit", "skipped"})
OUTCOMES = frozenset({"completed", "denied", "infrastructure", "error"})

# Request fields a route leaves out of its fingerprint. No admitted
# request model carries a secret today, so each route fingerprints its
# whole parsed body; a route that adds one lists it here.
FINGERPRINT_EXCLUDE: dict[str, frozenset[str]] = {}


class Unavailable(Exception):
    """The admission store didn't answer in the contract's shape."""


@dataclass(frozen=True)
class Decision:
    idempotency: str
    quota: str
    retry_after: int
    lease: str | None
    # {"status", "body"} of a completed command, for a replay.
    result: dict[str, Any] | None


def command_id(headers: Iterable[tuple[bytes, bytes]]) -> str | None:
    """The first Idempotency-Key header as a command id, or None when it's
    missing or isn't a UUIDv7."""
    for name, value in headers:
        if name.lower() != IDEMPOTENCY_HEADER:
            continue
        key = value.decode("latin-1").strip().lower()
        return key if COMMAND_ID.fullmatch(key) else None
    return None


def fingerprint(route: str, operation: str, body: BaseModel) -> str:
    """SHA-256 of the route and the parsed request, minus excluded fields."""
    fields = body.model_dump(mode="json", exclude=set(FINGERPRINT_EXCLUDE.get(operation, frozenset())))
    text = json.dumps(
        {"v": VERSION, "route": route, "fields": fields},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()


async def _post(path: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
    try:
        async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=TIMEOUT_S) as client:
            resp = await client.post(BASE_PATH + path, json=payload, headers={"Authorization": f"Bearer {token}"})
        return resp.status_code, resp.json()
    except (httpx.HTTPError, ValueError):
        raise Unavailable from None


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


async def admit(
    token: str,
    operation: str,
    wall_seconds: int,
    key: str | None,
    fingerprint_hex: str | None,
    mode: str,
) -> Decision:
    payload: dict[str, Any] = {"operation": operation, "wall_seconds": wall_seconds, "idempotency": mode}
    if key is not None:
        payload["command_id"] = key
        payload["fingerprint"] = fingerprint_hex
    status, body = await _post("/admit", token, payload)
    if status != 200 or not isinstance(body, dict) or body.get("v") != VERSION:
        raise Unavailable
    idempotency, quota, retry_after = body.get("idempotency"), body.get("quota"), body.get("retry_after")
    lease, result = body.get("lease"), body.get("result")
    if idempotency not in IDEMPOTENCY_VERDICTS or quota not in QUOTA_VERDICTS:
        raise Unavailable
    if not _int(retry_after) or retry_after < 0:
        raise Unavailable
    if not isinstance(lease, str) or (lease and not LEASE.fullmatch(lease)):
        raise Unavailable
    if result is not None and not (
        isinstance(result, dict) and _int(result.get("status")) and 200 <= result["status"] < 300 and "body" in result
    ):
        raise Unavailable
    return Decision(idempotency, quota, retry_after, lease or None, result)


async def settle(token: str, lease: str, wall_seconds: int) -> None:
    status, body = await _post("/settle", token, {"lease": lease, "wall_seconds": wall_seconds})
    if status != 200 or not isinstance(body, dict) or body.get("v") != VERSION:
        raise Unavailable


async def finish(token: str, lease: str, outcome: str, result: dict[str, Any] | None = None) -> bool:
    """Records the end of an admitted request. False when the lease is
    gone, which the sweep does once it expires."""
    payload: dict[str, Any] = {"lease": lease, "outcome": outcome}
    if result is not None:
        payload["result"] = result
    status, body = await _post("/finish", token, payload)
    if status == 404:
        return False
    if status != 200 or not isinstance(body, dict) or body.get("v") != VERSION:
        raise Unavailable
    return True
