"""Share links at the runner.

Endpoints:
  POST /api/share   CreateShare (app/share_commands.py, ROUNDS-00B-L04) while
                    ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION is enabled; 503
                    route_disabled while it's closed, its default. With
                    legacy_link_id it is "Get a new link" for one of the
                    caller's older links (ROUNDS-00B-L06).
  GET  /api/share   the caller's older links: every share link made before
                    ROUNDS-00B-L06 stage 1, each one turned off for good.

The list reads PocketBase with the caller's own bearer, so PocketBase's rules
decide what it holds: an account's own older links, never one that pointed
at another account's resume. Each entry says what the link was for, when it
was made and turned off, and whether a new link replaced it, and never holds
a secret. An older link never opens anything again. A caller PocketBase
doesn't sign in gets unauthenticated, and a store that doesn't answer gets
shares_unavailable, never PocketBase's own text.

A share capability's own routes are in routers/share_capabilities.py.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response

from app import admission, obs, share_capabilities, share_commands
from app.errors import TypedError
from app.pb_auth import POCKETBASE_URL

router = APIRouter(prefix="/api/share", tags=["share"])
_log = logging.getLogger(__name__)

# The statuses an older link's owner sees. An empty or unknown one reads as
# a link the server couldn't verify, and one that pointed at another
# account's resume is never listed (PocketBase's rule hides it too).
SHOWN = ("migrated", "revoked_demo", "revoked_unverified")
UNVERIFIED = "revoked_unverified"
HIDDEN = "revoked_ownership"
PAGE = 200
MAX_PAGES = 25
LIST_PATH = "/api/collections/resume_share_links/records"
TIMEOUT_S = 8
_RECORD_ID = re.compile(r"[a-z0-9]{15}")
# What the list asks PocketBase for, and nothing more.
_FIELDS = ",".join((
    "id", "created", "updated", "resume", "variant", "legacy_status", "legacy_reason", "turned_off_at",
    "replaced_by", "expand.variant.resume", "expand.variant.name",
))


@router.post("")
async def create_share(request: Request) -> Response:
    """CreateShare, or 503 route_disabled while resolution is closed: there is
    no other way to make a link."""
    if not share_capabilities.resolution_open():
        obs.emit("share.create", correlation_id=obs.current_correlation_id(), account=None, record=None,
                 code="route_disabled")
        raise TypedError("route_disabled")
    return await share_commands.create(request)


def _id(value: Any) -> str:
    return value if isinstance(value, str) and _RECORD_ID.fullmatch(value) else ""


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def older_link(item: Any) -> dict[str, Any] | None:
    """One older link as its owner sees it, or None for a row not shown."""
    if not isinstance(item, dict) or not _id(item.get("id")):
        return None
    status = item.get("legacy_status")
    if status == HIDDEN:
        return None
    if status not in SHOWN:
        status = UNVERIFIED
    resume_id, variant_id = _id(item.get("resume")), _id(item.get("variant"))
    expand = item.get("expand") if isinstance(item.get("expand"), dict) else {}
    variant = expand.get("variant") if variant_id and isinstance(expand.get("variant"), dict) else None
    replaced_by = _id(item.get("replaced_by"))
    return {
        "id": item["id"],
        "status": status,
        "reason": _text(item.get("legacy_reason")),
        "created": _text(item.get("created")),
        "turned_off_at": _text(item.get("turned_off_at")),
        "replaced_by": replaced_by,
        "replaced_at": _text(item.get("updated")) if replaced_by else "",
        "target": "variant" if variant_id else "resume",
        "resume_id": resume_id,
        "variant_id": variant_id,
        "root_resume_id": _id(variant.get("resume")) if variant is not None else resume_id,
        "variant_name": _text(variant.get("name")) if variant is not None else "",
    }


async def _account(request: Request) -> dict[str, Any]:
    token = admission.bearer_from(request.scope.get("headers") or [])
    if token is None:
        raise TypedError("unauthenticated")
    account = await admission.authenticate(token)
    if not _id(account.get("id")):
        raise TypedError("unauthenticated")
    return account


async def _page(token: str, account_id: str, page: int) -> list[Any]:
    """One page of the caller's older links, read with the caller's bearer."""
    params = {
        "filter": f'user = "{account_id}"',
        "sort": "-created,-id",
        "perPage": PAGE,
        "page": page,
        "skipTotal": 1,
        "expand": "variant",
        "fields": _FIELDS,
    }
    try:
        async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=TIMEOUT_S) as client:
            resp = await client.get(LIST_PATH, params=params, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError as err:
        _log.warning("older share links: no answer from PocketBase (%s)", type(err).__name__)
        raise TypedError("shares_unavailable") from None
    if resp.status_code == 401:
        raise TypedError("unauthenticated")
    try:
        body = resp.json() if resp.status_code == 200 else None
    except ValueError:
        body = None
    items = body.get("items") if isinstance(body, dict) else None
    if not isinstance(items, list):
        _log.warning("older share links: PocketBase answered %s", resp.status_code)
        raise TypedError("shares_unavailable")
    return items


@router.get("")
async def list_older_links(request: Request) -> dict[str, list[dict[str, Any]]]:
    account = await _account(request)
    entries: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        items = await _page(account["token"], account["id"], page)
        entries.extend(entry for entry in (older_link(item) for item in items) if entry is not None)
        if len(items) < PAGE:
            break
    return {"legacy": entries}
