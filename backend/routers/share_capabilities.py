"""Share capability routes (ROUNDS-00B-L03 stage 2, ROUNDS-00B-L04).

  GET  /api/share/capabilities              the caller's capabilities
  POST /api/share/capabilities/{id}/revoke  revoke one of them
  POST /api/share/capabilities/{id}/rotate  RotateShareBearer: a new bearer,
                                            shown once, and the old one
                                            resolves nothing
  POST /api/share/resolve                   anonymous: a capability's markup,
                                            or the uniform not-found

The logic is in app/share_capabilities.py and, for rotate,
app/share_commands.py.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import share_capabilities, share_commands

router = APIRouter(prefix="/api/share", tags=["share"])


@router.get("/capabilities")
async def list_capabilities(request: Request) -> list[dict[str, Any]]:
    return await share_capabilities.list_own(request)


@router.post("/capabilities/{capability_id}/revoke")
async def revoke_capability(request: Request, capability_id: str) -> dict[str, Any]:
    return await share_capabilities.revoke(request, capability_id)


@router.post("/capabilities/{capability_id}/rotate")
async def rotate_capability(request: Request, capability_id: str) -> JSONResponse:
    return await share_commands.rotate(request, capability_id, share_capabilities.resolution_open())


@router.post("/resolve")
async def resolve(request: Request) -> JSONResponse:
    return await share_capabilities.resolve(request)
