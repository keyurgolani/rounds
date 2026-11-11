"""Share capabilities at the runner (ROUNDS-00B-L03 stage 2).

The routes (routers/share_capabilities.py):

  GET  /api/share/capabilities              the caller's capabilities
  POST /api/share/capabilities/{id}/revoke  revoke one; again answers the same
  POST /api/share/resolve                   anonymous: a capability's markup

The owner routes call PocketBase's hook routes under /api/rounds/share
(pocketbase/pb_hooks/share_capabilities.pb.js) with the owner's bearer and
answer only the owner's fields; another account's capability and a missing
one get the same 404. nginx and the Vite proxy answer /api/rounds/share with
404, so a browser never reaches the hook routes. No PocketBase text reaches
a response.

The resolver answers ``{"projection_version": 1, "markup"}`` or the uniform
not-found, both with the resolver headers. Before any lookup, in order: the
PUBLIC_SHARES switch, the SHARE_CAPABILITY_RESOLUTION gate (closed by
default), and the request's shape, a JSON object holding exactly one
string, ``token``, in the bearer format, within 1 KiB. Then one lookup.
Every failure, the store being down included, gets the same bytes.
The lookup has no implementation until #12 (ROUNDS-00B-L04) brings the
digest and its service identity, so until then even an open gate resolves
nothing.

A log line holds the capability id when one resolves and an outcome code.
It holds no token, address, owner, or content; owner events name the
account by its pseudonym.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

from app import admission, gates, obs
from app.errors import TypedError
from app.pb_auth import POCKETBASE_URL

_log = logging.getLogger(__name__)

VERSION = "share-capability/v1"
HOOK_PATH = "/api/rounds/share/capabilities"
TIMEOUT_S = 8
PROJECTION_VERSION = 1
RESOLVE_ROUTE = "/api/share/resolve"
# The bearer format #12 issues (ROUNDS-00B-L04): a key version, then 22
# URL-safe characters.
TOKEN_RE = re.compile(r"sd[0-9]{1,3}_[A-Za-z0-9_-]{22}")
MAX_RESOLVE_BODY = 1024
RECORD_ID = re.compile(r"[a-z0-9]{15}")
# What an owner sees of a capability; nothing else leaves these routes.
OWNER_FIELDS = ("id", "status", "revoked_reason", "purpose", "expires_at", "created", "revoked_at")
STATUSES = ("active", "revoked")

# The headers every public share read answers with, found or not: no
# caching, no indexing, no referrer, no sniffing, no framing.
RESOLVER_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
NOT_FOUND_BODY = {"detail": "Not found."}


# ---------------------------------------------------------------------------
# The two share gates, read on each request
# ---------------------------------------------------------------------------


def public_shares_disabled(environ: Mapping[str, str] | None = None) -> bool:
    """Whether the emergency switch has turned every public share read off."""
    env = os.environ if environ is None else environ
    return gates.resolve(gates.BY_NAME["PUBLIC_SHARES"], env, gates.RUNNER).value == "disabled"


def resolution_open(environ: Mapping[str, str] | None = None) -> bool:
    """Whether the capability resolver may look anything up."""
    env = os.environ if environ is None else environ
    return gates.resolve(gates.BY_NAME["SHARE_CAPABILITY_RESOLUTION"], env, gates.RUNNER).value == "enabled"


def resolver_response(status: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(body, status_code=status, headers=dict(RESOLVER_HEADERS))


# ---------------------------------------------------------------------------
# The resolver
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Found:
    """A capability that resolves: its record id and its snapshot's markup."""

    capability_id: str
    markup: str


class LookupUnavailable(Exception):
    """The lookup couldn't run; the resolver answers it as degraded."""


async def _no_lookup(token: str) -> Found | None:
    # TODO(ROUNDS-00B-L04): #12 makes the bearer's digest, signs in as its
    # service identity, and calls its lookup route under /api/rounds/share,
    # which calls lookup_capability. Until then nothing resolves.
    raise LookupUnavailable("capability lookup arrives with ROUNDS-00B-L04")


# The one lookup the resolver makes for a well-formed request. Tests swap it.
lookup: Callable[[str], Awaitable[Found | None]] = _no_lookup


class _Miss(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _log_resolve(code: str, record: str | None = None) -> None:
    obs.emit("share.resolve", correlation_id=obs.current_correlation_id(), record=record, code=code)


async def _token_of(request: Request) -> str | None:
    """The request's token, or None for anything else."""
    media = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media != "application/json":
        return None
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_RESOLVE_BODY:
            return None
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(doc, dict) or set(doc) != {"token"}:
        return None
    token = doc["token"]
    if not isinstance(token, str) or TOKEN_RE.fullmatch(token) is None:
        return None
    return token


async def resolve(request: Request) -> JSONResponse:
    """A capability's projection, or the uniform not-found."""
    try:
        if public_shares_disabled():
            raise _Miss("kill_switch")
        if not resolution_open():
            raise _Miss("gate_closed")
        token = await _token_of(request)
        if token is None:
            raise _Miss("not_found")
        found = await lookup(token)
        if found is None:
            raise _Miss("not_found")
        if not isinstance(found.markup, str) or not found.markup:
            raise LookupUnavailable("lookup answered without markup")
    except _Miss as miss:
        _log_resolve(miss.code)
        return resolver_response(404, NOT_FOUND_BODY)
    except Exception:  # noqa: BLE001 - a store or lookup failure is the same not-found
        _log_resolve("degraded")
        return resolver_response(404, NOT_FOUND_BODY)
    record = found.capability_id if isinstance(found.capability_id, str) else None
    _log_resolve("available", record)
    return resolver_response(200, {"projection_version": PROJECTION_VERSION, "markup": found.markup})


# ---------------------------------------------------------------------------
# The owner's routes
# ---------------------------------------------------------------------------


def owner_view(item: Any) -> dict[str, str] | None:
    """The owner's fields of one capability, or None for any other shape."""
    if not isinstance(item, dict):
        return None
    out: dict[str, str] = {}
    for key in OWNER_FIELDS:
        value = item.get(key, "")
        if not isinstance(value, str):
            return None
        out[key] = value
    if RECORD_ID.fullmatch(out["id"]) is None or out["status"] not in STATUSES:
        return None
    return out


def _log_revoke(account: str, record: str | None, code: str) -> None:
    obs.emit("share.revoke", correlation_id=obs.current_correlation_id(),
             account=obs.account_pseudonym(account), record=record, code=code)


async def _authenticate(request: Request) -> dict[str, Any]:
    token = admission.bearer_from(request.scope.get("headers") or [])
    if token is None:
        raise TypedError("unauthenticated")
    return await admission.authenticate(token)


async def _hook(method: str, path: str, token: str) -> tuple[int, Any]:
    try:
        async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=TIMEOUT_S) as client:
            resp = await client.request(
                method, path, headers={"Authorization": f"Bearer {token}"}, json={} if method == "POST" else None,
            )
    except httpx.HTTPError as err:
        _log.warning("share capabilities: no answer from PocketBase (%s)", type(err).__name__)
        raise TypedError("shares_unavailable") from None
    try:
        body = resp.json()
    except ValueError:
        body = None
    return resp.status_code, body


def _unavailable(status: int) -> TypedError:
    _log.warning("share capabilities: PocketBase answered %s", status)
    return TypedError("shares_unavailable")


async def list_own(request: Request) -> list[dict[str, str]]:
    """The caller's capabilities, newest first, the owner's fields only."""
    account = await _authenticate(request)
    status, body = await _hook("GET", HOOK_PATH, account["token"])
    if status == 401:
        raise TypedError("unauthenticated")
    if status != 200 or not isinstance(body, dict) or body.get("v") != VERSION or not isinstance(body.get("items"), list):
        raise _unavailable(status)
    items = [owner_view(item) for item in body["items"]]
    if any(item is None for item in items):
        raise _unavailable(status)
    return items  # type: ignore[return-value]


async def revoke(request: Request, capability_id: str) -> dict[str, str]:
    """Revoke one of the caller's capabilities; revoking it again answers the
    same. Another account's, a missing one, and a malformed id get one 404."""
    account = await _authenticate(request)
    raw = await request.body()
    if raw.strip() not in (b"", b"{}"):
        raise TypedError("invalid_request", status=400)
    if RECORD_ID.fullmatch(capability_id) is None:
        _log_revoke(account["id"], None, "not_found")
        raise TypedError("not_found")
    status, body = await _hook("POST", f"{HOOK_PATH}/{capability_id}/revoke", account["token"])
    if status == 404 and isinstance(body, dict) and body.get("v") == VERSION and body.get("error") == "not_found":
        _log_revoke(account["id"], None, "not_found")
        raise TypedError("not_found")
    if status == 401:
        raise TypedError("unauthenticated")
    view = owner_view(body.get("capability")) if isinstance(body, dict) and body.get("v") == VERSION else None
    changed = body.get("changed") if isinstance(body, dict) else None
    if status != 200 or view is None or view["id"] != capability_id or not isinstance(changed, bool):
        raise _unavailable(status)
    _log_revoke(account["id"], view["id"], "revoked" if changed else "unchanged")
    return view
