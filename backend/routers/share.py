"""Public share links for resumes and variants.

Endpoints:
  POST   /api/share                          create a link (authed)
  GET    /api/share                          list my links (authed)
  DELETE /api/share/{id}                     delete a link (authed)
  GET    /api/share/by-token/{token}         public read of the link's projection

The owner routes go through PocketBase with the caller's own token, so the
collection rules decide (``resume_share_links`` reads only its owner's rows
and takes no updates, ROUNDS-00B-L03 stage 1).

The public read answers only ``{data, template_id, design}``: hidden sections
are emptied and every key the templates don't read is dropped, so it never
carries the owner's resume name, the link's kind, a record id, or the owner.
Every failure (kill switch, malformed token, unknown link, missing target,
PocketBase down) is the same 404 with the same body and headers, and the read
writes nothing.
TODO(ROUNDS-00B-L06): legacy links move to share capabilities.
"""
from __future__ import annotations

import os
import re
import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import obs
from app.errors import TypedError
from app.pb_auth import (
    current_user,
    pb_admin_get,
    pb_get,
    pb_post,
)
import httpx
from app.pb_auth import POCKETBASE_URL


router = APIRouter(prefix="/api/share", tags=["share"])

# The public read's kill switch. It fails closed: unset, empty, false, 0, no,
# or off (any case) leaves public reads on, and any other value turns every
# public read into the uniform not-found before any lookup. Read on each
# request.
# TODO(ROUNDS-00B-L03): stage 2 registers it as a gate with this as its alias.
KILL_SWITCH_ENV = "ROUNDS_DISABLE_PUBLIC_SHARES"
_KILL_SWITCH_OFF = ("", "false", "0", "no", "off")

# What a share token may look like. Anything else is answered before any
# lookup.
PUBLIC_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{16,64}")

# The headers every public read answers with, found or not.
PUBLIC_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
NOT_FOUND_BODY = {"detail": "Not found."}


class CreateShareRequest(BaseModel):
    # Exactly one must be set.
    resume_id: str | None = None
    variant_id: str | None = None


class ShareLinkOut(BaseModel):
    id: str
    token: str
    resume_id: str | None
    variant_id: str | None
    created: str


def _new_token() -> str:
    # 22 chars of urlsafe entropy (~130 bits), the format the link hook
    # requires (pocketbase/pb_hooks/share_links.js).
    return secrets.token_urlsafe(16)


def _link_out(record: dict[str, Any]) -> ShareLinkOut:
    return ShareLinkOut(
        id=record["id"],
        token=record["token"],
        resume_id=record.get("resume") or None,
        variant_id=record.get("variant") or None,
        created=record.get("created") or "",
    )


# ---------------------------------------------------------------------------
#                              Authed endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=ShareLinkOut)
async def create_link(request: Request, body: CreateShareRequest) -> ShareLinkOut:
    user = await current_user(request)
    if bool(body.resume_id) == bool(body.variant_id):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of resume_id or variant_id.",
        )

    payload: dict[str, Any] = {
        "user": user["id"],
        "token": _new_token(),
        "is_password": False,
    }
    if body.resume_id:
        payload["resume"] = body.resume_id
    if body.variant_id:
        payload["variant"] = body.variant_id

    try:
        record = await pb_post(
            user["token"], "/api/collections/resume_share_links/records", payload
        )
    except HTTPException as exc:
        # PocketBase gives a target the caller doesn't own and one that
        # doesn't exist the same denial (ROUNDS-00B-L02's relation check);
        # the runner answers both with one not-found and no PocketBase text.
        if exc.status_code in (400, 403, 404):
            raise TypedError("not_found") from None
        raise
    return _link_out(record)


@router.get("")
async def list_my_links(request: Request) -> list[ShareLinkOut]:
    user = await current_user(request)
    links = await pb_get(
        user["token"],
        "/api/collections/resume_share_links/records",
        params={
            "filter": f'user = "{user["id"]}"',
            "sort": "-created",
            "perPage": 100,
        },
    )
    items = (links or {}).get("items") or []
    return [_link_out(it) for it in items]


@router.delete("/{link_id}")
async def delete_link(request: Request, link_id: str) -> dict[str, bool]:
    user = await current_user(request)
    async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=8) as client:
        resp = await client.delete(
            f"/api/collections/resume_share_links/records/{link_id}",
            headers={"Authorization": f"Bearer {user['token']}"},
        )
    if resp.status_code >= 400 and resp.status_code != 404:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return {"ok": True}


# ---------------------------------------------------------------------------
#                              Public viewer
# ---------------------------------------------------------------------------


class _NotFound(Exception):
    """Any reason a public read answers the uniform not-found."""

    def __init__(self, outcome: str, record: str | None = None) -> None:
        super().__init__(outcome)
        self.outcome = outcome
        self.record = record


def public_shares_disabled() -> bool:
    return (os.environ.get(KILL_SWITCH_ENV) or "").strip().lower() not in _KILL_SWITCH_OFF


def _log_read(outcome: str, record: str | None) -> None:
    # Only the link's record id and a coarse outcome: never the token, the
    # caller's address or user agent, the owner, or any content.
    obs.emit("share.resolve", correlation_id=obs.current_correlation_id(), record=record, code=outcome)


def _public_response(status: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(body, status_code=status, headers=dict(PUBLIC_HEADERS))


@router.get("/by-token/{token}")
async def public_read(token: str) -> JSONResponse:
    """The link's projection, or the uniform not-found."""
    try:
        if public_shares_disabled():
            raise _NotFound("kill_switch")
        if PUBLIC_TOKEN_RE.fullmatch(token) is None:
            raise _NotFound("not_found")
        out, record = await _resolve(token)
    except _NotFound as nf:
        _log_read(nf.outcome, nf.record)
        return _public_response(404, NOT_FOUND_BODY)
    except Exception:  # noqa: BLE001 - the store couldn't be read
        _log_read("degraded", None)
        return _public_response(404, NOT_FOUND_BODY)
    _log_read("available", record)
    return _public_response(200, out)


async def _resolve(token: str) -> tuple[dict[str, Any], str]:
    # Only a value that matched PUBLIC_TOKEN_RE gets here.
    body = await pb_admin_get(
        "/api/collections/resume_share_links/records",
        params={"filter": f'token = "{token}"', "perPage": 1},
    )
    items = (body or {}).get("items") or []
    if not items or not isinstance(items[0], dict):
        raise _NotFound("not_found")
    link = items[0]
    link_id = link.get("id") if isinstance(link.get("id"), str) else None

    variant_id, resume_id = link.get("variant"), link.get("resume")
    if variant_id:
        variant = await pb_admin_get(f"/api/collections/resume_variants/records/{variant_id}")
        if not isinstance(variant, dict) or not variant.get("resume"):
            raise _NotFound("not_found", link_id)
        parent = await pb_admin_get(f"/api/collections/resumes/records/{variant['resume']}")
        if not isinstance(parent, dict):
            raise _NotFound("not_found", link_id)
        source, look = variant, parent
    elif resume_id:
        resume = await pb_admin_get(f"/api/collections/resumes/records/{resume_id}")
        if not isinstance(resume, dict):
            raise _NotFound("not_found", link_id)
        source, look = resume, resume
    else:
        raise _NotFound("not_found", link_id)

    # The link's owner must own what it points at, the variant's parent
    # resume included; anything else is the same not-found.
    owner = link.get("user")
    if not isinstance(owner, str) or not owner or any(r.get("user") != owner for r in (source, look)):
        raise _NotFound("not_found", link_id)

    return project(source.get("data"), look.get("template_id"), look.get("design")), link_id or ""


# ---------------------------------------------------------------------------
#                              The projection
# ---------------------------------------------------------------------------
#
# Only what the templates read (frontend/src/features/resume/types.ts):
# unknown keys at any level are dropped, values of the wrong type are dropped,
# and a section the owner hid is emptied. hiddenSections itself is not sent.

_PERSONAL = ("fullName", "email", "phone", "location", "website", "linkedin", "github",
             "title", "subtitle", "summary")
_SECTIONS: dict[str, dict[str, str]] = {
    "experience": {"id": "str", "company": "str", "position": "str", "location": "str",
                   "startDate": "str", "endDate": "str", "current": "bool",
                   "description": "str", "highlights": "strs"},
    "education": {"id": "str", "institution": "str", "degree": "str", "field": "str",
                  "location": "str", "startDate": "str", "endDate": "str", "gpa": "str",
                  "description": "str"},
    "skills": {"id": "str", "category": "str", "items": "strs"},
    "projects": {"id": "str", "name": "str", "description": "str", "technologies": "strs",
                 "url": "str", "github": "str", "startDate": "str", "endDate": "str",
                 "highlights": "strs"},
    "publications": {"id": "str", "title": "str", "publisher": "str", "releaseDate": "str",
                     "url": "str", "summary": "str"},
    "profiles": {"id": "str", "network": "str", "username": "str", "url": "str"},
}
SECTION_KEYS = ("personal", *_SECTIONS)

_DESIGN: dict[str, Any] = {
    "layout": "str",
    "colors": {k: "str" for k in ("primary", "secondary", "background", "text", "accent")},
    "typography": {
        "heading": {"family": "str", "weight": "num", "transform": "str", "size": "num"},
        "body": {"family": "str", "size": "num", "lineHeight": "num"},
    },
    "spacing": {k: "num" for k in ("margin", "padding", "gap")},
    "style": {"borderRadius": "num", "borderWidth": "num", "shadow": "str"},
    "showPhoto": "bool",
    "showIcons": "bool",
    "divider": "str",
    "bulletStyle": "str",
}
_TEMPLATE_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")
DEFAULT_TEMPLATE = "modern"


def _value(kind: Any, value: Any) -> Any:
    """``value`` if it has the type ``kind`` names, else a sentinel."""
    if isinstance(kind, dict):
        return _shape(kind, value) if isinstance(value, dict) else _DROP
    if kind == "str":
        return value if isinstance(value, str) else _DROP
    if kind == "bool":
        return value if isinstance(value, bool) else _DROP
    if kind == "num":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        return value if ok else _DROP
    if kind == "strs":
        # The templates read these lists without a guard, so a missing or
        # odd value is an empty list, never dropped.
        return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []
    return _DROP


_DROP = object()


def _shape(spec: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, kind in spec.items():
        if kind == "strs":
            out[key] = _value(kind, value.get(key))
        elif key in value:
            v = _value(kind, value[key])
            if v is not _DROP:
                out[key] = v
    return out


def project(data: Any, template_id: Any, design: Any) -> dict[str, Any]:
    """The only shape a public read returns."""
    data = data if isinstance(data, dict) else {}
    hidden_raw = data.get("hiddenSections")
    hidden = {k for k in hidden_raw if isinstance(k, str)} if isinstance(hidden_raw, list) else set()

    personal = data.get("personalInfo")
    if "personal" in hidden or not isinstance(personal, dict):
        personal_out: dict[str, Any] = {"fullName": ""}
    else:
        personal_out = _shape({k: "str" for k in _PERSONAL}, personal)
        personal_out.setdefault("fullName", "")

    out_data: dict[str, Any] = {"personalInfo": personal_out}
    for section, spec in _SECTIONS.items():
        items = data.get(section)
        if section in hidden or not isinstance(items, list):
            out_data[section] = []
        else:
            out_data[section] = [_shape(spec, it) for it in items if isinstance(it, dict)]

    order = data.get("sectionOrder")
    if isinstance(order, list) and all(isinstance(k, str) for k in order):
        # The templates read the order only when it names every section once.
        if sorted(order) == sorted(SECTION_KEYS):
            out_data["sectionOrder"] = list(order)

    tid = template_id if isinstance(template_id, str) and _TEMPLATE_ID_RE.fullmatch(template_id) else DEFAULT_TEMPLATE
    return {
        "data": out_data,
        "template_id": tid,
        "design": _shape(_DESIGN, design) if isinstance(design, dict) else {},
    }
