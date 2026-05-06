"""PDF rendering proxy.

Forwards a serialized HTML document to the Node Puppeteer sidecar and
streams the resulting PDF back to the caller. The sidecar disables
network access during render, so we don't expose anything new from
the inside of our network — but we still keep the sidecar
inside-only and require this proxy as the public entrypoint.
"""
import os
import urllib.request
import urllib.error

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/pdf", tags=["pdf"])

PDF_RENDERER_URL = os.environ.get("PDF_RENDERER_URL", "http://pdf-renderer:4000")
RENDER_TIMEOUT_S = 25


class RenderRequest(BaseModel):
    # The HTML payload to render. Templates serialize the live preview
    # DOM (which already carries inline styles), so this is typically
    # one A4-sized <article> wrapped in a small <html>/<style> shell.
    html: str = Field(..., min_length=1)
    margin_mm: int = Field(default=0, ge=0, le=30)


@router.get("/health")
def health():
    """Quick reachability check for the sidecar."""
    try:
        with urllib.request.urlopen(f"{PDF_RENDERER_URL}/health", timeout=2) as resp:
            return {"status": "ok" if resp.status == 200 else "degraded", "code": resp.status}
    except (urllib.error.URLError, OSError) as err:
        raise HTTPException(status_code=502, detail=f"renderer unreachable: {err}")


@router.post("/render")
def render(req: RenderRequest):
    import json
    body = json.dumps({"html": req.html, "marginMm": req.margin_mm}).encode("utf-8")
    request = urllib.request.Request(
        f"{PDF_RENDERER_URL}/render",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=RENDER_TIMEOUT_S) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "application/pdf")
            return Response(content=data, media_type=content_type)
    except urllib.error.HTTPError as err:
        # Bubble the sidecar's error body up so the user sees something
        # actionable (e.g. timeout, bad HTML).
        detail = err.read().decode("utf-8", errors="replace") if err.fp else str(err)
        raise HTTPException(status_code=502, detail=detail)
    except (urllib.error.URLError, OSError) as err:
        raise HTTPException(status_code=502, detail=f"renderer unreachable: {err}")
