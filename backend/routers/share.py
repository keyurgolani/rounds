"""Share links at the runner.

Endpoints:
  POST /api/share   CreateShare (app/share_commands.py, ROUNDS-00B-L04) while
                    ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION is enabled, its
                    default; 503 route_disabled while it's closed. With
                    legacy_link_id it is "Get a new link" for one of the
                    caller's older links (ROUNDS-00B-L06).
  GET  /api/share   the caller's older links: every share link made before
                    ROUNDS-00B-L06 stage 1, each one turned off for good.

The list reads PocketBase with the caller's own bearer, so PocketBase's rules
decide what it holds: an account's own older links, never one that pointed
at another account's resume. Each entry says what the link was for, when it
was made and turned off, and whether a new link replaced it, and never holds
a secret. An older link never opens anything again.

A share capability's own routes are in routers/share_capabilities.py.
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app import obs, share_capabilities, share_commands
from app.errors import TypedError
from app.pb_auth import current_user, pb_get

router = APIRouter(prefix="/api/share", tags=["share"])

# The statuses an older link's owner sees. An empty or unknown one reads as
# a link the server couldn't verify, and one that pointed at another
# account's resume is never listed (PocketBase's rule hides it too).
SHOWN = ("migrated", "revoked_demo", "revoked_unverified")
UNVERIFIED = "revoked_unverified"
HIDDEN = "revoked_ownership"
PAGE = 200
MAX_PAGES = 25
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


@router.get("")
async def list_older_links(request: Request) -> dict[str, list[dict[str, Any]]]:
    user = await current_user(request)
    entries: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        body = await pb_get(
            user["token"],
            "/api/collections/resume_share_links/records",
            params={
                "filter": f'user = "{user["id"]}"',
                "sort": "-created,-id",
                "perPage": PAGE,
                "page": page,
                "skipTotal": 1,
                "expand": "variant",
                "fields": _FIELDS,
            },
        )
        items = (body or {}).get("items") or []
        entries.extend(entry for entry in (older_link(item) for item in items) if entry is not None)
        if len(items) < PAGE:
            break
    return {"legacy": entries}
