"""PDF rendering proxy.

``POST /api/pdf/render`` renders one of the caller's own Legacy Artifact
Snapshots (ROUNDS-00A-L04): markup the server built and stored, never
markup a caller sends. It takes only ``render-request/v1``, the snapshot's
id and checksum and fixed output options. A body in the shape from before
snapshots answers 422 ``legacy_request_rejected``, which asks the page to
reload, and is never charged. The snapshot, its source, and its file are
read with the caller's bearer (``app.legacy_snapshots``) before a slot is
taken, and the markup goes to the Node Puppeteer sidecar, which disables
network access during render and stays inside-only behind this proxy.

Every route here is admitted (``app.admission``). A render whose document
ran out of time answers 422 ``render_timeout``: the sidecar says so within
its budgets, the document decides how long it takes, so it keeps its
charge and isn't retried. Any other failed render, a sidecar that
couldn't open a page in time or didn't answer within ``RENDER_TIMEOUT_S``
included, answers a typed 503, which the infrastructure caused and
admission refunds. Neither repeats the sidecar's text, and health answers
only ``{"status"}``.

``POST /api/pdf/snapshots`` creates a Legacy Artifact Snapshot through
PocketBase's hook (``app.legacy_snapshots``). It ships off behind
``ROUNDS_GATE_LEGACY_SNAPSHOT_CREATE``, and the render route's own gate,
``ROUNDS_GATE_PDF_RENDER``, is separate: either one off turns server PDF
off.

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
from pydantic import ValidationError

from app import admission, errors, legacy_snapshots
from app.errors import TypedError

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdf", tags=["pdf"])

PDF_RENDERER_URL = os.environ.get("PDF_RENDERER_URL", "http://pdf-renderer:4000")
# The sidecar's page, load, and print budgets end before this (server.js),
# so it always answers first unless it's stalled itself.
RENDER_TIMEOUT_S = 25
HEALTH_TIMEOUT_S = 2
RENDER_FAILED = "The PDF renderer couldn't finish this document. Try again shortly."
# What the sidecar answers for a document that ran out of time.
SIDECAR_TIMEOUT_STATUS = 422
SIDECAR_TIMEOUT_ERROR = "render_timeout"
_SIDECAR_ERROR_BYTES = 1024
# The field only the request shape from before snapshots carried.
LEGACY_FIELD = "html"
IDEMPOTENCY_HEADER = "idempotency-key"


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


def _sidecar_timed_out(err: urllib.error.HTTPError) -> bool:
    if err.code != SIDECAR_TIMEOUT_STATUS:
        return False
    try:
        answer = json.loads(err.read(_SIDECAR_ERROR_BYTES) or b"null")
    except (OSError, ValueError, http.client.HTTPException):
        return False
    return isinstance(answer, dict) and answer.get("error") == SIDECAR_TIMEOUT_ERROR


def _render(html: str, margin_mm: float) -> Response:
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
        if _sidecar_timed_out(err):
            raise TypedError("render_timeout") from None
        raise TypedError("worker_unavailable", RENDER_FAILED) from None
    except TimeoutError:
        # Connected, but no answer within the whole wait. The sidecar
        # answers a document that ran out of time itself, before this, so
        # the sidecar stalled. A failed connect arrives as a URLError.
        _log.warning("pdf render failed: no answer in %ss", RENDER_TIMEOUT_S)
        raise TypedError("worker_unavailable", RENDER_FAILED) from None
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as err:
        _log.warning("pdf render failed: %s", type(err).__name__)
        raise TypedError("worker_unavailable", RENDER_FAILED) from None
    return Response(content=data, media_type=content_type)


async def _render_request(request: Request) -> legacy_snapshots.RenderRequestV1:
    """Step 5 for a render: the body as render-request/v1. The older
    shape answers 422 ``legacy_request_rejected``; anything else that
    isn't the contract, or an ``Idempotency-Key`` that isn't the body's
    ``idempotency_id``, answers 422 ``invalid_request``."""
    try:
        raw = json.loads(await request.body() or b"null")
    except (ValueError, RecursionError):
        raise TypedError("invalid_request") from None
    if isinstance(raw, dict) and LEGACY_FIELD in raw:
        raise TypedError("legacy_request_rejected")
    try:
        req = legacy_snapshots.RenderRequestV1.model_validate(raw)
    except ValidationError as err:
        raise TypedError(errors.validation_code(err.errors())) from None
    # A missing key is step 6's to answer; a different one names another
    # command than the body does.
    sent = request.headers.get(IDEMPOTENCY_HEADER)
    if sent is not None and sent.strip().lower() != req.idempotency_id:
        raise TypedError("invalid_request")
    return req


@router.post("/render")
async def render(request: Request):
    req = await _render_request(request)
    # No PDF is kept, so a completed render's replay answers 409
    # already_completed.
    # TODO(ROUNDS-00A-L06): #6's stage 3 stores render output and replays it.
    await admission.begin(request, req, wall_seconds=RENDER_TIMEOUT_S)
    caller = admission.account(request)
    try:
        markup = await legacy_snapshots.markup_for_render(caller["token"], caller["id"], req)
    except legacy_snapshots.StoredMarkupUnusable as unusable:
        # The operator's alert: a stored snapshot no longer holds what its
        # checksum says, so no render of it can run.
        _log.warning("pdf render refused: the snapshot's stored markup is unusable (%s)", unusable)
        raise TypedError("worker_unavailable", RENDER_FAILED) from None
    async with admission.allocate():
        return await run_in_threadpool(_render, markup, req.margin_mm)


@router.post("/snapshots")
async def create_snapshot(request: Request, req: legacy_snapshots.SnapshotRequest):
    """A Legacy Artifact Snapshot of the caller's own resume or variant
    (ROUNDS-00A-L04), made by PocketBase's hook (app.legacy_snapshots).
    It takes no in-flight slot: the runner runs nothing itself."""
    await admission.begin(request, req, wall_seconds=legacy_snapshots.MATERIALIZE_TIMEOUT_S)
    token = admission.account(request)["token"]
    status, body = await legacy_snapshots.create(token, req, legacy_snapshots.command_for(request))
    return JSONResponse(body, status_code=status)
