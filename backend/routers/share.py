"""Public share links for resumes and variants.

Endpoints:
  POST   /api/share                          create a link (authed)
  GET    /api/share                          list my links + view counts (authed)
  DELETE /api/share/{id}                     delete a link (authed)
  GET    /api/share/by-token/{token}         public read — returns the resume data
                                             rendered against the chosen template

The public endpoint pierces PocketBase's owner rules via a cached
admin token (see ``app.pb_auth.admin_token``). Each call inserts a
``resume_share_views`` row so the owner can see how many times the
link was opened.
"""
from __future__ import annotations

import logging
import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.pb_auth import (
    admin_token,
    current_user,
    pb_admin_get,
    pb_admin_post,
    pb_get,
    pb_post,
)
import httpx
from app.pb_auth import POCKETBASE_URL


router = APIRouter(prefix="/api/share", tags=["share"])
_log = logging.getLogger(__name__)


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
    view_count: int


def _new_token() -> str:
    # 22 chars of urlsafe entropy — ~130 bits, comfortable for a
    # public secret while staying short enough for a clean URL.
    return secrets.token_urlsafe(16)


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

    record = await pb_post(
        user["token"], "/api/collections/resume_share_links/records", payload
    )
    return ShareLinkOut(
        id=record["id"],
        token=record["token"],
        resume_id=record.get("resume") or None,
        variant_id=record.get("variant") or None,
        created=record.get("created") or "",
        view_count=0,
    )


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
    if not items:
        return []
    # Bulk-count views per link via the admin token. PocketBase's
    # filter API supports OR; chunk to keep URLs sane.
    counts = await _view_counts([it["id"] for it in items])
    return [
        ShareLinkOut(
            id=it["id"],
            token=it["token"],
            resume_id=it.get("resume") or None,
            variant_id=it.get("variant") or None,
            created=it.get("created") or "",
            view_count=counts.get(it["id"], 0),
        )
        for it in items
    ]


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


@router.get("/by-token/{token}")
async def public_read(token: str, request: Request) -> dict[str, Any]:
    """Returns the resume data + template + design for a share token.

    Records a view per call. Anonymous; PB's own listRule on
    ``resume_share_links`` stays owner-only — we proxy with the
    server-held admin token instead of widening the rule.
    """
    safe = token.replace('"', "")
    body = await pb_admin_get(
        "/api/collections/resume_share_links/records",
        params={"filter": f'token = "{safe}"', "perPage": 1},
    )
    items = (body or {}).get("items") or []
    if not items:
        raise HTTPException(status_code=404, detail="Share link not found.")
    link = items[0]

    # Fetch the underlying record. Variant first if both are set.
    if link.get("variant"):
        record = await pb_admin_get(
            f"/api/collections/resume_variants/records/{link['variant']}"
        )
        if not record:
            raise HTTPException(status_code=404, detail="Variant no longer exists.")
        master = await pb_admin_get(
            f"/api/collections/resumes/records/{record['resume']}"
        )
        out = {
            "data": record.get("data") or {},
            "template_id": (master or {}).get("template_id") or "modern",
            "design": (master or {}).get("design") or {},
            "name": record.get("name") or (master or {}).get("name") or "",
            "kind": "variant",
        }
    elif link.get("resume"):
        record = await pb_admin_get(
            f"/api/collections/resumes/records/{link['resume']}"
        )
        if not record:
            raise HTTPException(status_code=404, detail="Resume no longer exists.")
        out = {
            "data": record.get("data") or {},
            "template_id": record.get("template_id") or "modern",
            "design": record.get("design") or {},
            "name": record.get("name") or "",
            "kind": "resume",
        }
    else:
        raise HTTPException(status_code=500, detail="Share link points nowhere.")

    # Best-effort view tracking. Failures here shouldn't block the
    # viewer, but we want the full traceback in logs so a broken
    # admin token / missing `resume_share_views` collection / PB outage
    # doesn't silently drop view counts on the floor.
    try:
        ip = request.client.host if request.client else ""
        ua = request.headers.get("user-agent", "")[:300]
        await pb_admin_post(
            "/api/collections/resume_share_views/records",
            {
                "user": link["user"],
                "link": link["id"],
                "viewer_ip_hash": _hash_ip(ip),
                "user_agent": ua,
                "viewed_at": _utc_now_iso(),
            },
        )
    except Exception:  # noqa: BLE001
        _log.exception("view tracking failed for share link %s", link["id"])

    return out


# ---------------------------------------------------------------------------
#                                Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash_ip(ip: str) -> str:
    import hashlib

    if not ip:
        return ""
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:24]


async def _view_counts(link_ids: list[str]) -> dict[str, int]:
    if not link_ids:
        return {}
    counts: dict[str, int] = {lid: 0 for lid in link_ids}
    token = await admin_token()
    # PocketBase doesn't expose count directly; getList returns
    # totalItems. One call per link keeps the filter expression simple.
    async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=8) as client:
        for lid in link_ids:
            resp = await client.get(
                "/api/collections/resume_share_views/records",
                params={"filter": f'link = "{lid}"', "perPage": 1},
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code != 200:
                continue
            body = resp.json()
            counts[lid] = int(body.get("totalItems") or 0)
    return counts
