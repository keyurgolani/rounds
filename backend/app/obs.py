"""Observability kit for runner decisions (ROUNDS-00A-L01).

Every decision is one JSON line on stdout. A line carries only the
allowlisted fields below: a 32-hex correlation id, a keyed account
pseudonym, the route template, the result code, the idempotency and
quota results, the code an observe-mode gate would have answered with,
and latency. ``definition.*`` lines carry a definition's identity
(``track/slug/variant@version``), never its content (ROUNDS-00A-L02).
``execution.job`` lines are the job metrics (ROUNDS-00A-L03): a metric
name and a count or seconds, labeled by kind, purpose, state, outcome
class, and executor kind, never by account; ``execution.worker`` says
what the replica's worker did at start.
Unknown fields are dropped, and every value has to match its field's
pattern, so source code, program output, HTML, bearer tokens, provider
payloads, and raw account ids never reach the log.

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
import re
import secrets
import sys
from typing import Any, Callable

from app.provider_gateway import keyring

KIT_VERSION = "obs/v1"
LOGGER_NAME = "rounds.obs"
CORRELATION_HEADER = "X-Correlation-Id"

_CORRELATION_RE = re.compile(r"[0-9a-f]{32}")
_FIELD_NAME_RE = re.compile(r"[a-z][a-z0-9_]{0,31}")
_PSEUDONYM_INFO = keyring.OBS_PSEUDONYM

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
    """The keyring's key for the versioned pseudonym label.

    Without a usable AI_KEY_SECRET the key is random for this process, so
    pseudonyms stay comparable within one process and nowhere else.
    """
    global _pseudonym_key_cache
    if _pseudonym_key_cache is None:
        try:
            _pseudonym_key_cache = keyring.derive(_PSEUDONYM_INFO)
        except keyring.Unavailable:
            _pseudonym_key_cache = secrets.token_bytes(32)
            if keyring.status().reason == "unset":
                why = "AI_KEY_SECRET is unset"
            else:
                why = "AI_KEY_SECRET isn't usable here"
            logging.getLogger(__name__).warning("%s, so account pseudonyms only match within this process.", why)
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


# What a key can need (execution/keys.py), and nothing else: the gate
# settings as NAME=value, and the secrets by name, never a value.
GATE_REQUIREMENTS = frozenset({
    "EXECUTION_STORE=on", "EXECUTION_DEFINITIONS=enforce", "ROUNDS_EXECUTION_SECRET", "ROUNDS_ADMISSION_SECRET",
})


def _gate_requirements(value: Any) -> bool:
    """A short list of the settings in GATE_REQUIREMENTS."""
    return (
        isinstance(value, list)
        and 0 < len(value) <= len(GATE_REQUIREMENTS)
        and all(isinstance(v, str) and v in GATE_REQUIREMENTS for v in value)
    )


def _gate_table(value: Any) -> bool:
    if not isinstance(value, dict) or len(value) > 128:
        return False
    for name, entry in value.items():
        if not _GATE_NAME(name) or not isinstance(entry, dict) or set(entry) != {"value", "source"}:
            return False
        if not _GATE_VALUE(entry["value"]) or not _GATE_SOURCE(entry["source"]):
            return False
    return True


# definition.* lines name a definition by its identity, never its content.
# share.resolve lines carry the record id of the share link or capability
# that resolved and a coarse outcome in `code` (available, not_found,
# gate_closed, kill_switch, degraded; throttled, password_required, and
# password_wrong from ROUNDS-00B-L04), never the token or a password.
# share.revoke lines (ROUNDS-00B-L03 stage 2) carry the owner's pseudonym,
# the capability id, and revoked, unchanged, or not_found. share.create and
# share.rotate lines (ROUNDS-00B-L04) carry the same three: issued,
# already_issued, ineligible, or the refusal's error code.
# execution.scratch (ROUNDS-00A-L03 PR 2) is the startup line that says
# ROUNDS_GATE_EXECUTION_SCRATCH is on but acts as off, and names what it
# needs (since PR 4, a missing secret by its name too), or that it's set
# to legacy, which acts as off; execution.grading (PR 3) says the same of
# ROUNDS_GATE_EXECUTION_GRADING. execution.review lines (PR 3) carry a
# grading kind and a coarse outcome in `code` (requested, completed,
# provider_failed, lost, in_flight, no_provider, files_changed,
# not_reviewable, or a refusal's error code), never the prompt, the files,
# or what the provider answered.
EVENTS = frozenset({
    "decision", "gates", "definitions.loaded", "definition.resolved", "definition.rejected", "execution.job",
    "execution.worker", "execution.scratch", "execution.grading", "execution.review", "share.resolve",
    "share.revoke", "share.create", "share.rotate",
})
# The job metrics' names (ROUNDS-00A-L03). #54, #22, #154, and #174 reuse
# the shape.
JOB_METRICS = (
    "rounds_job_queue_depth",
    "rounds_job_queue_wait_seconds",
    "rounds_job_attempt_seconds",
    "rounds_job_terminal_total",
    "rounds_job_lease_expired_total",
    "rounds_job_reconciled_total",
    "rounds_job_duplicate_total",
    "rounds_job_fingerprint_conflict_total",
    "rounds_job_late_result_rejected_total",
    "rounds_job_cleanup_unconfirmed_total",
)

FIELDS: dict[str, Callable[[Any], bool]] = {
    "correlation_id": is_correlation_id,
    "account": _matches(r"acct_[0-9a-f]{16}", 21),
    "tier": _one_of("anonymous", "standard", "demo"),
    "route": _matches(r"/[A-Za-z0-9/_{}.-]*", 96),
    "method": _one_of("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    "status": _int_between(100, 599),
    "code": _matches(r"[a-z][a-z0-9_]{0,63}", 64),
    "quota": _one_of("charged", "exceeded", "demo_limit", "refunded", "unavailable", "skipped"),
    # job and retry_job: a key whose command enqueued a job (ROUNDS-00A-L03).
    "idempotency": _one_of(
        "new", "retry", "replay", "mismatch", "in_flight", "none", "missing", "unavailable", "skipped", "job",
        "retry_job",
    ),
    # The code an observe-mode gate would have answered with.
    "would_deny": _matches(r"[a-z][a-z0-9_]{0,63}", 64),
    "latency_ms": _int_between(0, 86_400_000),
    "service": _one_of("runner", "pocketbase", "frontend"),
    "gates": _gate_table,
    # track/slug/variant@content_version, e.g. coding/two-sum/python@1.
    "definition": _matches(
        r"(?:coding|ai-coding|take-home)/[a-z0-9]+(?:-[a-z0-9]+)*/[a-z]{1,16}@[1-9][0-9]{0,3}", 128
    ),
    "entries": _int_between(0, 100_000),
    "mismatched": _int_between(0, 100_000),
    # The request field a definition.rejected line counts, such as
    # test_command for legacy_request_rejected: a field name, never a value.
    "field": _matches(r"[a-z][a-z0-9_]{0,31}", 32),
    # execution.job (ROUNDS-00A-L03).
    "metric": _one_of(*JOB_METRICS),
    "value": _int_between(0, 1_000_000_000),
    "kind": _one_of("run", "evaluate", "run_project", "take_home_run", "grade", "take_home_submit"),
    "purpose": _one_of("scratch", "grading"),
    "state": _one_of("queued", "leased", "started", "completed", "timed-out", "denied", "canceled", "failed"),
    "outcome_class": _one_of(
        "passed", "candidate-failure", "resource-limit", "definition-invalid", "policy-violation", "canceled",
        "worker-lost", "infrastructure-degraded",
    ),
    "executor_kind": _one_of("legacy-in-process", "isolated-worker"),
    # A PocketBase record id, such as the share link or capability a
    # share.resolve or share.revoke line names.
    "record": _matches(r"[a-z0-9]{15}", 15),
    # What a key needs, such as EXECUTION_STORE=on or ROUNDS_EXECUTION_SECRET.
    "needs": _gate_requirements,
}
# The fields an event may carry, where that's fewer than FIELDS: a job
# metric never carries an account or a correlation id.
EVENT_FIELDS: dict[str, frozenset[str]] = {
    "execution.job": frozenset({"metric", "value", "kind", "purpose", "state", "outcome_class", "executor_kind",
                                "service"}),
    "execution.worker": frozenset({"code", "service"}),
    "execution.scratch": frozenset({"code", "needs", "service"}),
    "execution.grading": frozenset({"code", "needs", "service"}),
    "execution.review": frozenset({"correlation_id", "kind", "code", "service"}),
    "share.resolve": frozenset({"correlation_id", "record", "code"}),
    "share.revoke": frozenset({"correlation_id", "account", "record", "code"}),
    "share.create": frozenset({"correlation_id", "account", "record", "code"}),
    "share.rotate": frozenset({"correlation_id", "account", "record", "code"}),
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
    allowed = EVENT_FIELDS.get(event)
    for name, value in fields.items():
        if value is None:
            continue
        check = FIELDS.get(name)
        if check is None or (allowed is not None and name not in allowed) or not check(value):
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
