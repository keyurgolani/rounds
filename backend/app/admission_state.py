"""Admission state client for steps 6 and 7 (ROUNDS-00A-L01 stage 3).

The runner keeps no admission state. ``pocketbase/pb_hooks/admission.js``
keeps it in ``admission_commands``, ``admission_counters``, and
``admission_leases``, and this module calls its routes under
``/api/rounds/admission/``. Each call carries the caller's bearer, which
names the account, and the runner key (``ROUNDS_ADMISSION_SECRET`` in
``X-Rounds-Admission-Key``), which only the runner and PocketBase hold, so
a bearer alone never reaches them. PocketBase runs each call in one
transaction on its one write connection, so every runner replica sees one
count.

1. ``admit`` runs steps 6 and 7 together. The runner makes the lease
   token and sends only its hash, so it can still end a lease whose answer
   it lost. The store answers the idempotency verdict (``new``, ``retry``,
   ``replay``, ``mismatch``, ``in_flight``, or ``none`` without a key), the
   quota verdict (``ok``, ``exceeded``, ``demo_limit``, or ``skipped``), a
   Retry-After, and whether it leased the request. A lease ends by itself
   once the most the request was admitted for has passed.
2. ``settle`` sets evaluate's and grade's exact charge once step 8 has
   loaded the definitions: once per lease, no more than was admitted, and
   a raise has to fit the hour, or the store answers the quota verdict.
3. ``finish`` ends an admitted request: ``completed`` with the response to
   replay, ``denied`` for a denial before anything ran (retryable, wall
   seconds refunded), ``infrastructure`` for an infrastructure failure
   (``failed_infrastructure``, refunded), or ``error`` for anything else
   (``failed_infrastructure``, kept).

A transport error, any status but the expected ones, or a body that isn't
the contract's shape is ``Unavailable``; a runner without its key is
``Unconfigured`` and calls nothing.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import string
from dataclasses import dataclass
from typing import Any, Iterable

import httpx
from pydantic import BaseModel

from app.pb_auth import POCKETBASE_URL

VERSION = "admission/v1"
BASE_PATH = "/api/rounds/admission"
TIMEOUT_S = 5
IDEMPOTENCY_HEADER = b"idempotency-key"
# The secret the runner and PocketBase share, and the header it rides in.
RUNNER_KEY_ENV = "ROUNDS_ADMISSION_SECRET"
RUNNER_KEY_HEADER = "X-Rounds-Admission-Key"
RUNNER_KEY_MIN_CHARS = 32
# runnerFetch mints one UUIDv7 per user action (frontend/src/lib/idempotency.ts).
COMMAND_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
LEASE = re.compile(r"[A-Za-z0-9]{43}")
_LEASE_ALPHABET = string.ascii_letters + string.digits
_LEASE_CHARS = 43
# The largest response the runner sends to be kept for replay.
# pb_hooks/admission.js keeps up to as many characters of JSON.
RESULT_MAX_BYTES = 256 * 1024

IDEMPOTENCY_VERDICTS = frozenset({"new", "retry", "replay", "mismatch", "in_flight", "none"})
QUOTA_VERDICTS = frozenset({"ok", "exceeded", "demo_limit", "skipped"})
QUOTA_MODES = frozenset({"enforce", "observe", "off"})
OUTCOMES = frozenset({"completed", "denied", "infrastructure", "error"})

# Request fields a route leaves out of its fingerprint. No admitted
# request model carries a secret today, so each route fingerprints its
# whole parsed body; a route that adds one lists it here.
FINGERPRINT_EXCLUDE: dict[str, frozenset[str]] = {}


class Unavailable(Exception):
    """The admission store didn't answer in the contract's shape."""


class Unconfigured(Unavailable):
    """The runner has no usable ``ROUNDS_ADMISSION_SECRET``, so it sent
    nothing."""


@dataclass(frozen=True)
class Decision:
    idempotency: str
    quota: str
    retry_after: int
    # The store wrote a lease under the runner's token.
    leased: bool
    # {"status", "body"} of a completed command, for a replay.
    result: dict[str, Any] | None


@dataclass(frozen=True)
class Settled:
    # "ok", or the verdict that kept the charge where it was.
    quota: str
    retry_after: int


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


def new_lease() -> str:
    """A lease token: 43 letters and digits, about 256 bits. Only the
    runner that made it holds it; the store keeps its hash."""
    return "".join(secrets.choice(_LEASE_ALPHABET) for _ in range(_LEASE_CHARS))


def lease_hash(lease: str) -> str:
    return hashlib.sha256(lease.encode("ascii")).hexdigest()


def runner_key() -> str:
    """The runner key from the environment, read on each call. Shorter
    than ``RUNNER_KEY_MIN_CHARS``, or anything but printable ASCII with no
    surrounding space, is ``Unconfigured``."""
    key = os.environ.get(RUNNER_KEY_ENV, "")
    if len(key) < RUNNER_KEY_MIN_CHARS or not (key.isascii() and key.isprintable()) or key != key.strip():
        raise Unconfigured
    return key


async def _post(path: str, token: str, payload: dict[str, Any], timeout: float = TIMEOUT_S) -> tuple[int, Any]:
    headers = {"Authorization": f"Bearer {token}", RUNNER_KEY_HEADER: runner_key()}
    try:
        async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=timeout) as client:
            resp = await client.post(BASE_PATH + path, json=payload, headers=headers)
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
    *,
    lease: str,
    quota: str = "enforce",
    max_wall_seconds: int | None = None,
) -> Decision:
    """Steps 6 and 7 for one request. ``lease`` is the token the runner
    made for it (``new_lease``); ``wall_seconds`` is the first charge and
    ``max_wall_seconds`` the most a settle may raise it to, which also
    sets when the lease ends."""
    payload: dict[str, Any] = {
        "operation": operation,
        "wall_seconds": wall_seconds,
        "idempotency": mode,
        "quota": quota,
        "lease_hash": lease_hash(lease),
    }
    if max_wall_seconds is not None:
        payload["max_wall_seconds"] = max_wall_seconds
    if key is not None:
        payload["command_id"] = key
        payload["fingerprint"] = fingerprint_hex
    status, body = await _post("/admit", token, payload)
    if status != 200 or not isinstance(body, dict) or body.get("v") != VERSION:
        raise Unavailable
    idempotency, verdict, retry_after = body.get("idempotency"), body.get("quota"), body.get("retry_after")
    leased, result = body.get("leased"), body.get("result")
    if idempotency not in IDEMPOTENCY_VERDICTS or verdict not in QUOTA_VERDICTS:
        raise Unavailable
    if not _int(retry_after) or retry_after < 0 or not isinstance(leased, bool):
        raise Unavailable
    if result is not None and not (
        isinstance(result, dict) and _int(result.get("status")) and 200 <= result["status"] < 300 and "body" in result
    ):
        raise Unavailable
    return Decision(idempotency, verdict, retry_after, leased, result)


async def settle(token: str, lease: str, wall_seconds: int) -> Settled:
    """The exact charge. A raise that doesn't fit the hour leaves the
    charge where it was and answers the quota verdict."""
    status, body = await _post("/settle", token, {"lease": lease, "wall_seconds": wall_seconds})
    if not isinstance(body, dict) or body.get("v") != VERSION:
        raise Unavailable
    if status == 200:
        return Settled("ok", 0)
    verdict, retry_after = body.get("quota"), body.get("retry_after")
    if status == 429 and verdict in ("exceeded", "demo_limit") and _int(retry_after) and retry_after >= 0:
        return Settled(verdict, retry_after)
    raise Unavailable


async def finish(
    token: str,
    lease: str,
    outcome: str,
    result: dict[str, Any] | None = None,
    timeout: float = TIMEOUT_S,
) -> bool:
    """Records the end of an admitted request. False when the lease is
    gone: already finished, or past its window and swept."""
    payload: dict[str, Any] = {"lease": lease, "outcome": outcome}
    if result is not None:
        payload["result"] = result
    status, body = await _post("/finish", token, payload, timeout)
    if status == 404:
        return False
    if status != 200 or not isinstance(body, dict) or body.get("v") != VERSION:
        raise Unavailable
    return True
