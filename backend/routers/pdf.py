"""PDF rendering proxy.

Forwards a serialized HTML document to the Node Puppeteer sidecar and
streams the resulting PDF back to the caller. The sidecar disables
network access during render, so we don't expose anything new from
the inside of our network — but we still keep the sidecar
inside-only and require this proxy as the public entrypoint.

Both routes are admitted (``app.admission``). A failed render answers a
typed 503 and never repeats the sidecar's text, and health answers only
``{"status"}``.

TODO(ROUNDS-00A-L06): #6's ephemeral no-script render workers replace
the pooled sidecar behind this proxy.
"""
import http.client
import json
import logging
import os
import urllib.error
import urllib.request

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from pydantic import Field

from app import admission
from app.errors import TypedError
from app.limits import StrictModel

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdf", tags=["pdf"])

PDF_RENDERER_URL = os.environ.get("PDF_RENDERER_URL", "http://pdf-renderer:4000")
RENDER_TIMEOUT_S = 25
HEALTH_TIMEOUT_S = 2
RENDER_FAILED = "The PDF renderer couldn't finish this document. Try again shortly."


class RenderRequest(StrictModel):
    # The HTML payload to render. Templates serialize the live preview
    # DOM (which already carries inline styles), so this is typically
    # one A4-sized <article> wrapped in a small <html>/<style> shell.
    html: str = Field(..., min_length=1)
    margin_mm: int = Field(default=0, ge=0, le=30)


def _sidecar_ok() -> bool:
    try:
        with urllib.request.urlopen(f"{PDF_RENDERER_URL}/health", timeout=HEALTH_TIMEOUT_S) as resp:
            return resp.status == 200
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
        return False


@router.get("/health")
async def health():
    """Reachability of the sidecar, and nothing else."""
    if await run_in_threadpool(_sidecar_ok):
        return {"status": "ok"}
    return JSONResponse({"status": "unavailable"}, status_code=503)


def _render(html: str, margin_mm: int) -> Response:
    body = json.dumps({"html": html, "marginMm": margin_mm}).encode("utf-8")
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
    except urllib.error.HTTPError as err:
        _log.warning("pdf render failed: sidecar answered %s", err.code)
        raise TypedError("worker_unavailable", RENDER_FAILED) from None
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as err:
        _log.warning("pdf render failed: %s", type(err).__name__)
        raise TypedError("worker_unavailable", RENDER_FAILED) from None
    return Response(content=data, media_type=content_type)


@router.post("/render")
async def render(request: Request, req: RenderRequest):
    # No PDF is kept, so a completed render's replay answers 409
    # already_completed.
    # TODO(ROUNDS-00A-L06): #6's stage 3 stores render output and replays it.
    await admission.begin(request, req, wall_seconds=RENDER_TIMEOUT_S)
    async with admission.allocate():
        return await run_in_threadpool(_render, req.html, req.margin_mm)
