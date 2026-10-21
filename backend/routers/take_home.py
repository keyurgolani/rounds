"""Take-Home Coding Assignment endpoints. Mirrors backend/routers/ai_coding.py's
posture: subprocess sandbox via take_home.runner, server-authoritative
assignment lookup via the user's PB token, optional AI rubric review.

``run`` and ``submit`` are admitted (``app.admission``), and a submit's
``campaign_id`` must name one of the caller's campaigns before anything
runs. What runs comes from the server: the assignment's entrypoint and
harness files at ``ROUNDS_GATE_EXECUTION_DEFINITIONS=legacy``, and at
``enforce`` the compiled take-home harness revision the request names
(``app.execution``), whose grade answers per-result outcomes and the
server's score, never the harness's output. Every seeded assignment is
retired, so at enforce they answer 410 ``definition_retired``."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from take_home.runner import run_assignment
from ai_coding.rubric import (
    REVIEW_TIMED_OUT,
    REVIEW_TIMEOUT_S,
    SYSTEM_PROMPT as _RUBRIC_SYS,
    build_prompt as _build_rubric_prompt,
    parse_ai_output as _parse_rubric,
)
from app import admission, definitions, execution, limits
from app.errors import TypedError
from app.limits import StrictModel
from app.pb_auth import current_user, pb_get, pb_post
from routers.ai import _active_text_config, _call_complete, _call_stream, _friendly_error, _request_id
from routers.ai_coding import _resolve_text_cfg

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/take-home", tags=["take-home"])

RUN_TIMEOUT_S = 60
SUBMIT_TIMEOUT_S = 120
# The longest a submit waits to save its attempt row after the review.
ATTEMPT_WRITE_TIMEOUT_S = 10


async def _auth_user(request: Request) -> dict:
    """Wrapper so existing test mocks against `current_user` keep working
    via name lookup at call time. Same pattern as backend/routers/ai_coding.py.
    On an admitted route it reuses admission's account."""
    admitted = admission.account(request)
    if admitted is not None:
        return admitted
    return await current_user(request)


async def _admitted_assignment(user: dict, slug: str) -> tuple[dict[str, Any], str]:
    """Step 8: the assignment and its entrypoint, or a typed denial."""
    a = await admission.first_item(pb_get, user["token"], "take_home_assignments", slug)
    entrypoint = a.get("entrypoint")
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        raise TypedError("invalid_request", "This assignment can't run here.")
    return a, entrypoint


async def _own_campaign(user: dict, campaign_id: str) -> None:
    """Step 8: a campaign the caller doesn't own is not found."""
    record = await admission.lookup(
        pb_get, user["token"], f"/api/collections/campaigns/records/{campaign_id}"
    )
    if not isinstance(record, dict) or record.get("user") != user["id"]:
        raise TypedError("not_found")


async def _fetch_assignment(token: str, slug: str) -> dict[str, Any]:
    data = await pb_get(
        token,
        "/api/collections/take_home_assignments/records",
        params={"filter": f"slug='{slug}'", "perPage": 1},
    )
    items = (data or {}).get("items") or []
    if not items:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return items[0]


def _merge_with_harness(
    user_files: Dict[str, str],
    harness_files: list[dict[str, Any]],
) -> Dict[str, str]:
    merged = {**user_files}
    for hf in (harness_files or []):
        path = hf.get("path") if isinstance(hf, dict) else None
        contents = hf.get("contents") if isinstance(hf, dict) else None
        if isinstance(path, str) and isinstance(contents, str):
            merged[path] = contents
    return merged


class TakeHomeRunRequest(StrictModel):
    assignment_slug: str = Field(pattern=limits.SLUG_PATTERN)
    files: Dict[str, str]

    @field_validator("files")
    @classmethod
    def _files(cls, v: Dict[str, str]) -> Dict[str, str]:
        return dict(limits.check_files(v))


class DefinitionTakeHomeRunRequest(StrictModel):
    """A take-home run at enforce: the definition and the files."""

    definition: execution.DefinitionRef
    files: Dict[str, str]

    @field_validator("files")
    @classmethod
    def _files(cls, v: Dict[str, str]) -> Dict[str, str]:
        return dict(limits.check_files(v))


class TakeHomeRunResponse(BaseModel):
    score: float
    criteria: List[Dict[str, Any]]
    stdout: str
    stderr: str
    error: str | None
    duration_ms: int
    truncated: bool = False
    # At enforce: the server's verdict, the per-result outcomes, and the
    # definition that ran, for #3 to store.
    passed: bool | None = None
    outcomes: List[Dict[str, str]] | None = None
    definition: Dict[str, Any] | None = None


@router.post("/run", response_model=TakeHomeRunResponse)
async def run_route(
    request: Request,
    user: dict = Depends(_auth_user),
) -> TakeHomeRunResponse:
    body = await execution.parse(request, TakeHomeRunRequest, DefinitionTakeHomeRunRequest)
    if isinstance(body, DefinitionTakeHomeRunRequest):
        return await _run_definition(request, body)
    await admission.begin(request, body, wall_seconds=RUN_TIMEOUT_S)
    a, entrypoint = await _admitted_assignment(user, body.assignment_slug)
    merged = _merge_with_harness(body.files, a.get("harness_files") or [])
    async with admission.allocate() as slot:
        r = await run_in_threadpool(run_assignment, merged, entrypoint, timeout_s=RUN_TIMEOUT_S, sandbox=slot)
    return TakeHomeRunResponse(
        score=r.score,
        criteria=r.criteria,
        stdout=r.stdout[:8000],
        stderr=r.stderr[:8000],
        error=r.error,
        duration_ms=r.duration_ms,
        truncated=r.truncated,
    )


class TakeHomeSubmitRequest(StrictModel):
    assignment_slug: str = Field(pattern=limits.SLUG_PATTERN)
    files: Dict[str, str]
    notes: str = ""
    ai_chats: List[Dict[str, Any]] = Field(default_factory=list)
    campaign_id: str | None = Field(default=None, pattern=limits.OPTIONAL_RECORD_ID_PATTERN)
    duration_ms: int = Field(default=0, ge=0)

    @field_validator("files")
    @classmethod
    def _files(cls, v: Dict[str, str]) -> Dict[str, str]:
        return dict(limits.check_files(v))

    @field_validator("notes")
    @classmethod
    def _notes(cls, v: str) -> str:
        return limits.check_text(v, limits.NOTES_BYTES, "notes")

    @field_validator("ai_chats")
    @classmethod
    def _ai_chats(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return limits.check_json(v, limits.AI_CHATS_BYTES, "ai_chats")


class DefinitionTakeHomeSubmitRequest(StrictModel):
    """A take-home submit at enforce: the definition, the files, and the
    notes, chats, campaign, and time the attempt records."""

    definition: execution.DefinitionRef
    files: Dict[str, str]
    notes: str = ""
    ai_chats: List[Dict[str, Any]] = Field(default_factory=list)
    campaign_id: str | None = Field(default=None, pattern=limits.OPTIONAL_RECORD_ID_PATTERN)
    duration_ms: int = Field(default=0, ge=0)

    @field_validator("files")
    @classmethod
    def _files(cls, v: Dict[str, str]) -> Dict[str, str]:
        return dict(limits.check_files(v))

    @field_validator("notes")
    @classmethod
    def _notes(cls, v: str) -> str:
        return limits.check_text(v, limits.NOTES_BYTES, "notes")

    @field_validator("ai_chats")
    @classmethod
    def _ai_chats(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return limits.check_json(v, limits.AI_CHATS_BYTES, "ai_chats")


@router.post("/submit")
async def submit_route(
    request: Request,
    user: dict = Depends(_auth_user),
) -> Dict[str, Any]:
    body = await execution.parse(request, TakeHomeSubmitRequest, DefinitionTakeHomeSubmitRequest)
    if isinstance(body, DefinitionTakeHomeSubmitRequest):
        return await _submit_definition(request, body, user)
    # A replay answers here, so it saves no second attempt row.
    await admission.begin(request, body, wall_seconds=SUBMIT_TIMEOUT_S)
    a, entrypoint = await _admitted_assignment(user, body.assignment_slug)
    if body.campaign_id:
        await _own_campaign(user, body.campaign_id)
    merged = _merge_with_harness(body.files, a.get("harness_files") or [])
    async with admission.allocate() as slot:
        r = await run_in_threadpool(run_assignment, merged, entrypoint, timeout_s=SUBMIT_TIMEOUT_S, sandbox=slot)
    harness_out = {
        "score": r.score,
        "criteria": r.criteria,
        "stdout": r.stdout[:16000],
        "stderr": r.stderr[:16000],
        "error": r.error,
        "duration_ms": r.duration_ms,
        "truncated": r.truncated,
    }

    rubric = a.get("rubric") or {"items": []}
    rubric_review: Dict[str, Any] = {"items": [], "total": 0.0, "skipped": False}
    try:
        # Bounded, so the review and the attempt write end inside the
        # submit's lease.
        with anyio.fail_after(REVIEW_TIMEOUT_S):
            cfg = await _active_text_config(user)
            prompt = _build_rubric_prompt(
                rubric=rubric,
                files=body.files,
                test_results={"harness": harness_out},
                ai_chats=body.ai_chats,
            )
            raw = await _call_complete(
                cfg["kind"], cfg["model"], cfg["api_key"], cfg["base_url"] or None,
                system=_RUBRIC_SYS,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                destination=cfg.get("destination"),
            )
        rubric_review = _parse_rubric(raw)
    except TimeoutError:
        _log.warning("take-home submit rubric review timed out")
        rubric_review = {"items": [], "total": 0.0, "skipped": True, "reason": REVIEW_TIMED_OUT}
    except Exception as e:  # noqa: BLE001
        _log.exception("take-home submit rubric review failed")
        rubric_review = {"items": [], "total": 0.0, "skipped": True, "reason": str(e)[:300]}

    # Persist the attempt via the user's own token (PB ownerRule applies).
    try:
        attempt_payload = {
            "user": user["id"],
            "assignment": a.get("id") or "",
            "files": body.files,
            "ai_assist_used": bool(body.ai_chats),
            "ai_chats": body.ai_chats,
            "notes": body.notes,
            "harness_output": harness_out,
            "rubric_review": rubric_review,
            "status": "graded",
            "duration_ms": body.duration_ms,
        }
        if body.campaign_id:
            attempt_payload["campaign"] = body.campaign_id
        with anyio.fail_after(ATTEMPT_WRITE_TIMEOUT_S):
            await pb_post(
                user["token"],
                "/api/collections/take_home_attempts/records",
                attempt_payload,
            )
    except HTTPException as e:
        # A persist-time authorization denial (the account may not point this
        # attempt's typed relations at a record it does not own, or may not
        # write the row at all) must reach the caller with the same status and
        # body PocketBase returned, not be masked by a success grade. Any
        # other client-side (4xx) rejection surfaces the same way. Only a
        # server-side failure (5xx), a PocketBase outage included, stays
        # best-effort so it does not drop the user's grade. A write timeout
        # raises TimeoutError, not HTTPException, so it falls to the handler
        # below and stays best-effort too.
        if e.status_code < 500:
            raise
        _log.exception("take-home submit: failed to persist attempt")
    except Exception:  # noqa: BLE001
        # Persistence is best-effort for infrastructure failures; don't fail
        # the user-visible grade because the attempts row didn't save.
        _log.exception("take-home submit: failed to persist attempt")

    return {"harness": harness_out, "rubric_review": rubric_review}


# ---------------------------------------------------------------------------
# ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce
# ---------------------------------------------------------------------------

GRADE_TIMED_OUT = "The grader ran out of time."


def _graded_checkpoint(request: Request, resolved: definitions.Resolved) -> dict[str, Any]:
    """The revision's one checkpoint, when it reports on fd 3. A version
    that scores itself on stdout is never run."""
    if resolved.document.get("result_protocol") != "fd3":
        raise execution.rejected(request, resolved, "invalid_request", "This assignment can't run here.")
    return resolved.document["checkpoints"][0]


def harness_output(checkpoint: dict[str, Any], graded: execution.Graded,
                   resolved: definitions.Resolved) -> Dict[str, Any]:
    """What a take-home run answers and its attempt keeps: the server's
    score and verdict and the per-result outcomes, never the harness's
    output."""
    weights = {r["id"]: r["weight"] for r in checkpoint["results"]}
    score = graded.score
    return {
        "score": score.score,
        "passed": score.passed,
        "criteria": [
            {"id": r.id, "passed": r.outcome == "passed", "weight": weights[r.id], "logs": r.reason}
            for r in score.results
        ],
        "outcomes": score.outcomes(),
        "stdout": "",
        "stderr": "",
        "error": GRADE_TIMED_OUT if graded.timed_out else None,
        "duration_ms": graded.duration_ms,
        "truncated": False,
        "definition": resolved.receipt(),
    }


async def _run_definition(request: Request, body: DefinitionTakeHomeRunRequest) -> TakeHomeRunResponse:
    await admission.begin(request, body, wall_seconds=RUN_TIMEOUT_S)
    resolved = execution.resolve(request, body.definition, "take-home")
    checkpoint = _graded_checkpoint(request, resolved)
    execution.check_paths(request, body.files, resolved)
    async with admission.allocate() as slot:
        graded = await run_in_threadpool(
            execution.grade, checkpoint, resolved.document["files"], body.files, slot, RUN_TIMEOUT_S
        )
    return TakeHomeRunResponse(**harness_output(checkpoint, graded, resolved))


async def _presentation_row(user: dict, slug: str) -> dict[str, Any] | None:
    """The assignment's row, which the attempt points at. The definition,
    not the row, decides what runs."""
    try:
        return await admission.first_item(pb_get, user["token"], "take_home_assignments", slug)
    except TypedError as err:
        if err.code == "not_found":
            return None
        raise


async def _submit_definition(request: Request, body: DefinitionTakeHomeSubmitRequest, user: dict) -> Dict[str, Any]:
    # A replay answers here, so it saves no second attempt row.
    await admission.begin(request, body, wall_seconds=SUBMIT_TIMEOUT_S)
    resolved = execution.resolve(request, body.definition, "take-home")
    checkpoint = _graded_checkpoint(request, resolved)
    execution.check_paths(request, body.files, resolved)
    if body.campaign_id:
        await _own_campaign(user, body.campaign_id)
    row = await _presentation_row(user, resolved.identity.slug)
    async with admission.allocate() as slot:
        graded = await run_in_threadpool(
            execution.grade, checkpoint, resolved.document["files"], body.files, slot, SUBMIT_TIMEOUT_S
        )
    harness_out = harness_output(checkpoint, graded, resolved)

    rubric_review: Dict[str, Any] = {"items": [], "total": 0.0, "skipped": False}
    try:
        # Bounded, so the review and the attempt write end inside the
        # submit's lease. It reads the pinned revision's rubric and the
        # server's outcomes only.
        with anyio.fail_after(REVIEW_TIMEOUT_S):
            cfg = await _active_text_config(user)
            prompt = _build_rubric_prompt(
                rubric=resolved.document["rubric"],
                files=body.files,
                test_results={"harness": {k: harness_out[k] for k in ("score", "passed", "outcomes")}},
                ai_chats=body.ai_chats,
            )
            raw = await _call_complete(
                cfg["kind"], cfg["model"], cfg["api_key"], cfg["base_url"] or None,
                system=_RUBRIC_SYS,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                destination=cfg.get("destination"),
            )
        rubric_review = _parse_rubric(raw)
    except TimeoutError:
        _log.warning("take-home submit rubric review timed out")
        rubric_review = {"items": [], "total": 0.0, "skipped": True, "reason": REVIEW_TIMED_OUT}
    except Exception as e:  # noqa: BLE001
        _log.exception("take-home submit rubric review failed")
        rubric_review = {"items": [], "total": 0.0, "skipped": True, "reason": str(e)[:300]}

    if row is not None:
        try:
            attempt_payload = {
                "user": user["id"],
                "assignment": row.get("id") or "",
                "files": body.files,
                "ai_assist_used": bool(body.ai_chats),
                "ai_chats": body.ai_chats,
                "notes": body.notes,
                "harness_output": harness_out,
                "rubric_review": rubric_review,
                "status": "graded",
                "duration_ms": body.duration_ms,
            }
            if body.campaign_id:
                attempt_payload["campaign"] = body.campaign_id
            with anyio.fail_after(ATTEMPT_WRITE_TIMEOUT_S):
                await pb_post(user["token"], "/api/collections/take_home_attempts/records", attempt_payload)
        except Exception:  # noqa: BLE001
            # Best effort, as at legacy: the grade still answers.
            _log.exception("take-home submit: failed to persist attempt")
    else:
        _log.warning("take-home submit: no assignment row for %s, attempt not saved", resolved.identity.label())

    return {"harness": harness_out, "rubric_review": rubric_review, "definition": resolved.receipt()}


_TAKE_HOME_SYSTEM = (
    "You are a senior pair-programmer helping a candidate during a take-home "
    "assignment practice session. Be concise; point to specific files and "
    "lines; prefer asking clarifying questions over guessing. Don't rewrite "
    "whole files — propose minimal changes the candidate can apply. When "
    "uncertain, say so."
)


class ChatMessage(BaseModel):
    role: str
    content: str


class TakeHomeChatRequest(BaseModel):
    assignment_slug: str = Field(pattern=r"^[a-z0-9-]+$")
    provider_id: str | None = None
    model: str | None = None
    messages: List[ChatMessage]
    files: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _override_must_be_paired(self) -> "TakeHomeChatRequest":
        if (self.provider_id is None) != (self.model is None):
            raise ValueError(
                "provider_id and model must both be supplied or both omitted "
                "(partial override is rejected to surface client bugs)."
            )
        return self


@router.post("/chat")
async def chat_route(
    body: TakeHomeChatRequest,
    user: dict = Depends(_auth_user),
) -> StreamingResponse:
    a = await _fetch_assignment(user["token"], body.assignment_slug)
    if (a.get("ai_policy") or "off") == "off":
        raise HTTPException(status_code=403, detail="AI is disabled for this assignment.")
    cfg = await _resolve_text_cfg(user, body.provider_id, body.model)

    prompt_md = a.get("prompt_md") or ""
    system = _TAKE_HOME_SYSTEM
    system += "\n\nAssignment prompt:\n" + prompt_md[:8000]
    system += "\n\nProject files (JSON):\n" + json.dumps(body.files)[:60_000]

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    async def gen() -> AsyncIterator[bytes]:
        try:
            async for chunk in _call_stream(
                cfg["kind"],
                cfg["model"],
                cfg["api_key"],
                cfg["base_url"] or None,
                system=system,
                messages=messages,
                max_tokens=1200,
                destination=cfg.get("destination"),
            ):
                yield f"data: {json.dumps({'delta': chunk})}\n\n".encode("utf-8")
            yield b"data: {\"done\": true}\n\n"
        except Exception as err:  # noqa: BLE001
            rid = _request_id()
            _log.exception("take-home chat stream failed [rid=%s]", rid)
            kind_, msg = _friendly_error(err)
            yield (
                f"data: {json.dumps({'error': msg, 'error_kind': kind_, 'request_id': rid})}\n\n"
            ).encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")
