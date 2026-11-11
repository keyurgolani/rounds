"""Share capability routes (ROUNDS-00B-L03 stage 2).

  GET  /api/share/capabilities              the caller's capabilities
  POST /api/share/capabilities/{id}/revoke  revoke one of them
  POST /api/share/resolve                   anonymous: a capability's markup,
                                            or the uniform not-found

The logic is in app/share_capabilities.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import share_capabilities

router = APIRouter(prefix="/api/share", tags=["share"])


@router.get("/capabilities")
async def list_capabilities(request: Request) -> list[dict[str, str]]:
    return await share_capabilities.list_own(request)


@router.post("/capabilities/{capability_id}/revoke")
async def revoke_capability(request: Request, capability_id: str) -> dict[str, str]:
    return await share_capabilities.revoke(request, capability_id)


@router.post("/resolve")
async def resolve(request: Request) -> JSONResponse:
    return await share_capabilities.resolve(request)
