"""Compare two answers that must be indistinguishable (ROUNDS-00B-L05).

A denial of another account's record and the same request on a record that
does not exist must answer alike: same status, same headers, same body, same
length, and the same calls upstream. Only what changes on every request is
set aside: the `Date` header, correlation ids, and the request id a runner
error quotes. Everything else that differs is reported by name, never by
value, so a difference never puts record contents in a receipt.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable

# Headers that differ between any two requests, whatever they ask.
VOLATILE_HEADERS = frozenset({"date", "x-correlation-id", "x-request-id"})
# Body keys that carry a per-request id.
VOLATILE_KEYS = frozenset({"correlation_id", "request_id"})
# The request id the runner quotes inside an error message.
_REQUEST_ID_TEXT = re.compile(r"(request id: )[A-Za-z0-9_-]+")
# A per-request id as it sits in a raw JSON body, whatever the spacing.
_VOLATILE_RAW = re.compile(r'("(?:' + "|".join(sorted(VOLATILE_KEYS)) + r')"\s*:\s*)"[^"\\]*"')
# Raw lengths are compared as they are: a per-request id always has one
# length, so two answers that differ only in those ids have equal lengths.


def body_digest(resp: Any) -> str:
    """sha256 of the raw body with only the per-request ids replaced, so key
    order, spacing, and non-JSON bodies all count. A response with no raw
    bytes (a test double) is digested from its parsed body."""
    raw = getattr(resp, "raw", b"") or b""
    if not raw and resp.body is not None:
        raw = json.dumps(resp.body, separators=(",", ":")).encode("utf-8")
    text = raw.decode("utf-8", "surrogateescape")
    text = _VOLATILE_RAW.sub(r'\1"<volatile>"', text)
    text = _REQUEST_ID_TEXT.sub(r"\1<volatile>", text)
    return hashlib.sha256(text.encode("utf-8", "surrogateescape")).hexdigest()


def _headers(h: dict[str, str]) -> dict[str, str]:
    return {k.lower(): v for k, v in (h or {}).items() if k.lower() not in VOLATILE_HEADERS}


def differences(first: Any, second: Any) -> list[str]:
    """What tells two responses apart, by name: `status`, `body`, `length`,
    and `header:<name>`. Empty when they're indistinguishable."""
    out: list[str] = []
    if first.status != second.status:
        out.append("status")
    if body_digest(first) != body_digest(second):
        out.append("body")
    if getattr(first, "length", 0) != getattr(second, "length", 0):
        out.append("length")
    h1, h2 = _headers(getattr(first, "headers", {})), _headers(getattr(second, "headers", {}))
    for name in sorted(set(h1) | set(h2)):
        if h1.get(name) != h2.get(name):
            out.append(f"header:{name}")
    return out


def template_path(path: str, ids: Iterable[str]) -> str:
    """The path with each probed id replaced, so a foreign id's calls and a
    missing id's calls compare as one sequence."""
    for value in sorted({i for i in ids if i}, key=len, reverse=True):
        path = path.replace(value, "{id}")
    return path


def call_sequence(entries: list[dict[str, Any]], ids: Iterable[str]) -> list[tuple[str, str, str, int]]:
    """Upstream calls as (method, templated path, auth class, status)."""
    ids = list(ids)
    return [(e["method"], template_path(e["path"], ids), e["auth"], e["status"]) for e in entries]
