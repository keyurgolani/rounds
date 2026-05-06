"""Tiny PocketBase HTTP client for the AI router.

The runner has no shared session with PocketBase; it gets the user's
auth token from the ``Authorization: Bearer …`` header on each AI
request and uses it directly when reading or writing PocketBase rows
(so PB's own ``ownerRule`` enforces access).

Two helpers:

  * ``current_user(request)`` — refreshes the token, returns the user id.
    Raises ``HTTPException(401)`` on a bad/expired token.

  * ``pb_request(token, …)`` — generic typed wrapper for collection
    endpoints, returning the parsed JSON body.

We deliberately keep this small instead of pulling in a Python PB SDK:
only a couple endpoints are involved and httpx is already a dep.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException, Request


POCKETBASE_URL = os.environ.get(
    "POCKETBASE_URL",
    # Default works inside docker-compose (sibling service name).
    "http://pocketbase:8090",
)

_AUTH_REFRESH_PATH = "/api/collections/users/auth-refresh"


def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    return auth.split(" ", 1)[1].strip()


async def current_user(request: Request) -> dict:
    """Validate the request token and return the user record."""
    token = _bearer(request)
    async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=8) as client:
        resp = await client.post(
            _AUTH_REFRESH_PATH,
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Token invalid.")
    body = resp.json()
    record = body.get("record") or {}
    if not record.get("id"):
        raise HTTPException(status_code=401, detail="Token rejected.")
    return {"id": record["id"], "token": token, "record": record}


async def pb_get(token: str, path: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=8) as client:
        resp = await client.get(
            path,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code == 404:
        return None
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"PocketBase error: {resp.text}",
        )
    return resp.json()


async def pb_post(token: str, path: str, body: dict[str, Any]) -> Any:
    async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=10) as client:
        resp = await client.post(
            path,
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"PocketBase error: {resp.text}",
        )
    return resp.json()


async def pb_patch(token: str, path: str, body: dict[str, Any]) -> Any:
    async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=10) as client:
        resp = await client.patch(
            path,
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"PocketBase error: {resp.text}",
        )
    return resp.json()


# ---------------------------------------------------------------------------
#                                Admin auth
# ---------------------------------------------------------------------------
#
# A handful of endpoints (currently just the public share viewer)
# need to read PocketBase rows that don't belong to any logged-in
# user. Rather than relax PB's owner rules, we keep them tight and
# proxy through a short-lived admin token cached here.
#
# Credentials come from the same env vars the bootstrap migration
# uses, so a fresh dev stack works out of the box.

import os
import time


_ADMIN_EMAIL = os.environ.get("PB_ADMIN_EMAIL", "admin@local.dev")
_ADMIN_PASSWORD = os.environ.get("PB_ADMIN_PASSWORD", "changemenowplz")

# 25 minute cache — PB admin tokens last 1 hour by default; refresh
# well ahead of that.
_ADMIN_TTL_S = 25 * 60

_admin_token_cache: dict[str, Any] = {"token": "", "expires_at": 0.0}


async def admin_token() -> str:
    """Returns a cached PocketBase admin token, refreshing on TTL."""
    now = time.time()
    if _admin_token_cache["token"] and now < _admin_token_cache["expires_at"]:
        return _admin_token_cache["token"]
    async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=8) as client:
        resp = await client.post(
            "/api/admins/auth-with-password",
            json={"identity": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Couldn't authenticate as PocketBase admin — check PB_ADMIN_* env vars.",
        )
    body = resp.json()
    token = body.get("token") or ""
    if not token:
        raise HTTPException(status_code=502, detail="PocketBase didn't return an admin token.")
    _admin_token_cache["token"] = token
    _admin_token_cache["expires_at"] = now + _ADMIN_TTL_S
    return token


async def pb_admin_get(path: str, params: dict[str, Any] | None = None) -> Any:
    token = await admin_token()
    return await pb_get(token, path, params)


async def pb_admin_post(path: str, body: dict[str, Any]) -> Any:
    token = await admin_token()
    return await pb_post(token, path, body)
