"""Observability kit for runner decisions (ROUNDS-00A-L01).

Every decision is one JSON line on stdout. A line carries only the
allowlisted fields below: a 32-hex correlation id, a keyed account
pseudonym, the route template, the result code, the quota result, and
latency. Unknown fields are dropped, and every value has to match its
field's pattern, so source code, program output, HTML, bearer tokens,
provider payloads, and raw account ids never reach the log.

One correlation id covers a request: ``CorrelationIdMiddleware`` mints
it, puts it on ``request.state.correlation_id`` and the
``X-Correlation-Id`` response header, and binds it for
``correlation_id()`` so error messages and log lines agree.
"""
from __future__ import annotations

import contextvars
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sys
from typing import Any, Callable

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KIT_VERSION = "obs/v1"
LOGGER_NAME = "rounds.obs"
CORRELATION_HEADER = "X-Correlation-Id"

_CORRELATION_RE = re.compile(r"[0-9a-f]{32}")
_FIELD_NAME_RE = re.compile(r"[a-z][a-z0-9_]{0,31}")
_PSEUDONYM_INFO = b"rounds/obs/account-pseudonym/v1"

_current: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "rounds_correlation_id", default=None
)


# ---------------------------------------------------------------------------
# Correlation ids
# ---------------------------------------------------------------------------


def new_correlation_id() -> str:
    """A fresh 32-hex (128-bit) correlation id."""
    return secrets.token_hex(16)


def is_correlation_id(value: object) -> bool:
    return isinstance(value, str) and _CORRELATION_RE.fullmatch(value) is not None


def current_correlation_id() -> str | None:
    """The id bound to the request being handled, if any."""
    return _current.get()


def correlation_id() -> str:
    """The current request's id, or a fresh one outside a request."""
    return _current.get() or new_correlation_id()


class CorrelationIdMiddleware:
    """Mints one correlation id per HTTP request.

    Pure ASGI, so streaming responses keep working. The id is never
    taken from the client.
    """

    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        cid = new_correlation_id()
        scope.setdefault("state", {})["correlation_id"] = cid
        header = (CORRELATION_HEADER.lower().encode("latin-1"), cid.encode("latin-1"))

        async def send_with_id(message: dict) -> None:
            if message.get("type") == "http.response.start":
                message = {**message, "headers": [*message.get("headers", []), header]}
            await send(message)

        token = _current.set(cid)
        try:
            await self.app(scope, receive, send_with_id)
        finally:
            _current.reset(token)


# ---------------------------------------------------------------------------
# Account pseudonyms
# ---------------------------------------------------------------------------

_pseudonym_key_cache: bytes | None = None


def _pseudonym_key() -> bytes:
    """HKDF-SHA256 over AI_KEY_SECRET with a versioned label.

    Without AI_KEY_SECRET the key is random for this process, so
    pseudonyms stay comparable within one process and nowhere else.
    """
    global _pseudonym_key_cache
    if _pseudonym_key_cache is None:
        root = os.environ.get("AI_KEY_SECRET", "")
        if root:
            _pseudonym_key_cache = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=_PSEUDONYM_INFO,
            ).derive(root.encode("utf-8"))
        else:
            _pseudonym_key_cache = secrets.token_bytes(32)
            logging.getLogger(__name__).warning(
                "AI_KEY_SECRET is unset, so account pseudonyms only match within this process."
            )
    return _pseudonym_key_cache


def reset_pseudonym_key() -> None:
    """Forget the derived key (tests change AI_KEY_SECRET)."""
    global _pseudonym_key_cache
    _pseudonym_key_cache = None


def account_pseudonym(account_id: str | None) -> str | None:
    """A keyed, non-reversible handle for an account id."""
    if not account_id:
        return None
    digest = hmac.new(_pseudonym_key(), account_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return "acct_" + digest[:16]


# ---------------------------------------------------------------------------
# Allowlisted decision lines
# ---------------------------------------------------------------------------


def _one_of(*allowed: str) -> Callable[[Any], bool]:
    options = frozenset(allowed)
    return lambda v: isinstance(v, str) and v in options


def _matches(pattern: str, max_len: int) -> Callable[[Any], bool]:
    compiled = re.compile(pattern)
    return lambda v: isinstance(v, str) and len(v) <= max_len and compiled.fullmatch(v) is not None


def _int_between(low: int, high: int) -> Callable[[Any], bool]:
    return lambda v: isinstance(v, int) and not isinstance(v, bool) and low <= v <= high


_GATE_NAME = _matches(r"[A-Z][A-Z0-9_]{0,63}", 64)
_GATE_VALUE = _matches(r"[a-z_]{1,16}", 16)
_GATE_SOURCE = _one_of("default", "env", "alias", "invalid")


def _gate_table(value: Any) -> bool:
    if not isinstance(value, dict) or len(value) > 128:
        return False
    for name, entry in value.items():
        if not _GATE_NAME(name) or not isinstance(entry, dict) or set(entry) != {"value", "source"}:
            return False
        if not _GATE_VALUE(entry["value"]) or not _GATE_SOURCE(entry["source"]):
            return False
    return True


EVENTS = frozenset({"decision", "gates"})

FIELDS: dict[str, Callable[[Any], bool]] = {
    "correlation_id": is_correlation_id,
    "account": _matches(r"acct_[0-9a-f]{16}", 21),
    "tier": _one_of("anonymous", "standard", "demo"),
    "route": _matches(r"/[A-Za-z0-9/_{}.-]*", 96),
    "method": _one_of("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    "status": _int_between(100, 599),
    "code": _matches(r"[a-z][a-z0-9_]{0,63}", 64),
    "quota": _one_of("charged", "exceeded", "demo_limit", "refunded", "unavailable", "skipped"),
    "latency_ms": _int_between(0, 86_400_000),
    "service": _one_of("runner", "pocketbase", "frontend"),
    "gates": _gate_table,
}


def build(event: str, **fields: Any) -> dict[str, Any]:
    """Return the line for ``event`` with only valid, allowlisted fields.

    Unknown fields and values that fail their check are dropped. Their
    names go in ``dropped`` so a caller bug shows up without its value.
    """
    if event not in EVENTS:
        raise ValueError(f"unknown obs event {event!r}")
    record: dict[str, Any] = {"v": KIT_VERSION, "event": event}
    dropped: list[str] = []
    for name, value in fields.items():
        if value is None:
            continue
        check = FIELDS.get(name)
        if check is None or not check(value):
            dropped.append(name if _FIELD_NAME_RE.fullmatch(name) else "unnamed")
            continue
        record[name] = value
    if dropped:
        record["dropped"] = sorted(set(dropped))
    return record


class _StdoutHandler(logging.Handler):
    """Writes each record to the current ``sys.stdout``."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            sys.stdout.write(self.format(record) + "\n")
            sys.stdout.flush()
        except Exception:  # noqa: BLE001
            self.handleError(record)


def _logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if not any(isinstance(h, _StdoutHandler) for h in logger.handlers):
        handler = _StdoutHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def emit(event: str, **fields: Any) -> dict[str, Any]:
    """Build the line, write it as compact JSON, and return it."""
    record = build(event, **fields)
    _logger().info(json.dumps(record, separators=(",", ":"), sort_keys=True))
    return record
