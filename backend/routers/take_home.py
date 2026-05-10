"""Take-Home Coding Assignment endpoints. Mirrors backend/routers/ai_coding.py's
posture: subprocess sandbox via take_home.runner, server-authoritative
assignment lookup via the user's PB token, optional AI rubric review."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from take_home.runner import run_assignment
from ai_coding.rubric import (
    SYSTEM_PROMPT as _RUBRIC_SYS,
    build_prompt as _build_rubric_prompt,
    parse_ai_output as _parse_rubric,
)
from app.pb_auth import current_user, pb_get, pb_post
from routers.ai import _active_text_config, _call_complete, _call_stream, _friendly_error, _request_id
from routers.ai_coding import _resolve_text_cfg

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/take-home", tags=["take-home"])


async def _auth_user(request: Request) -> dict:
    """Wrapper so existing test mocks against `current_user` keep working
    via name lookup at call time. Same pattern as backend/routers/ai_coding.py."""
    return await current_user(request)


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


class TakeHomeRunRequest(BaseModel):
    assignment_slug: str = Field(pattern=r"^[a-z0-9-]+$")
    files: Dict[str, str]


class TakeHomeRunResponse(BaseModel):
    score: float
    criteria: List[Dict[str, Any]]
    stdout: str
    stderr: str
    error: str | None
    duration_ms: int
    truncated: bool = False


@router.post("/run", response_model=TakeHomeRunResponse)
async def run_route(
    body: TakeHomeRunRequest,
    user: dict = Depends(_auth_user),
) -> TakeHomeRunResponse:
    a = await _fetch_assignment(user["token"], body.assignment_slug)
    entrypoint = a.get("entrypoint") or ""
    if not entrypoint:
        raise HTTPException(status_code=422, detail="Assignment has no entrypoint configured.")
    merged = _merge_with_harness(body.files, a.get("harness_files") or [])
    r = run_assignment(merged, entrypoint, timeout_s=60)
    return TakeHomeRunResponse(
        score=r.score,
        criteria=r.criteria,
        stdout=r.stdout[:8000],
        stderr=r.stderr[:8000],
        error=r.error,
        duration_ms=r.duration_ms,
        truncated=r.truncated,
    )


class TakeHomeSubmitRequest(BaseModel):
    assignment_slug: str = Field(pattern=r"^[a-z0-9-]+$")
    files: Dict[str, str]
    notes: str = ""
    ai_chats: List[Dict[str, Any]] = Field(default_factory=list)
    campaign_id: str | None = None
    duration_ms: int = 0


@router.post("/submit")
async def submit_route(
    body: TakeHomeSubmitRequest,
    user: dict = Depends(_auth_user),
) -> Dict[str, Any]:
    a = await _fetch_assignment(user["token"], body.assignment_slug)
    entrypoint = a.get("entrypoint") or ""
    if not entrypoint:
        raise HTTPException(status_code=422, detail="Assignment has no entrypoint configured.")
    merged = _merge_with_harness(body.files, a.get("harness_files") or [])
    r = run_assignment(merged, entrypoint, timeout_s=120)
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
        )
        rubric_review = _parse_rubric(raw)
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
        await pb_post(
            user["token"],
            "/api/collections/take_home_attempts/records",
            attempt_payload,
        )
    except Exception:  # noqa: BLE001
        # Persistence is best-effort; don't fail the user-visible grade
        # because the attempts row didn't save. Log + continue.
        _log.exception("take-home submit: failed to persist attempt")

    return {"harness": harness_out, "rubric_review": rubric_review}


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
