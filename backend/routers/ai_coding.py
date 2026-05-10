"""AI-Assisted Coding endpoints. Project-level run/grade plus an SSE
chat proxy that reuses backend.routers.ai's call-stream helpers."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from ai_coding.edit_mode import EDIT_SYSTEM_PROMPT, parse_patches as _parse_patches
from ai_coding.project_runner import run_project
from ai_coding.rubric import (
    SYSTEM_PROMPT as _RUBRIC_SYS,
    build_prompt as _build_rubric_prompt,
    parse_ai_output as _parse_rubric,
)
from app.pb_auth import current_user, pb_get
from routers.ai import (
    _active_text_config,
    _call_complete,
    _call_stream,
    _friendly_error,
    _list_providers_raw,
    _load_provider,
    _request_id,
)
from app.crypto import decrypt

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-coding", tags=["ai-coding"])


async def _auth_user(request: Request) -> dict:
    """FastAPI dependency wrapper around `current_user`.

    Using a local wrapper (rather than `Depends(current_user)` directly)
    means tests that `patch("routers.ai_coding.current_user", …)` keep
    working — the lookup happens at call time, not at route registration.
    Switching to a Depends() also makes auth fire BEFORE Pydantic body
    validation, so unauthenticated POSTs return 401 instead of 422.
    """
    return await current_user(request)


class RunProjectRequest(BaseModel):
    files: Dict[str, str] = Field(..., description="path → contents")
    language: str
    test_command: str
    timeout_s: int = 30


class RunProjectResponse(BaseModel):
    passed: bool
    passed_count: int
    failed_count: int
    stdout: str
    stderr: str
    error: str | None
    duration_ms: int
    truncated: bool = False


@router.post("/run-project", response_model=RunProjectResponse)
def run_project_route(req: RunProjectRequest) -> RunProjectResponse:
    result = run_project(
        files=req.files,
        language=req.language,
        test_command=req.test_command,
        timeout_s=req.timeout_s,
    )
    return RunProjectResponse(
        passed=result.passed,
        passed_count=result.passed_count,
        failed_count=result.failed_count,
        stdout=result.stdout,
        stderr=result.stderr,
        error=result.error,
        duration_ms=result.duration_ms,
        truncated=result.truncated,
    )


_AI_CODING_SYSTEM = (
    "You are a senior pair-programmer helping a candidate during a coding "
    "interview practice session. Be concise, point to specific files and "
    "lines, and prefer asking clarifying questions over guessing. Do not "
    "rewrite whole files — propose minimal changes the candidate can apply. "
    "When uncertain, say so. The candidate's code is given below as a JSON "
    "object of {path: contents}."
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    # Slug constraint mirrors the pattern enforced by the PocketBase
    # collection schema, so a malicious client can't smuggle quotes
    # into the round-lookup filter.
    round_slug: str = Field(pattern=r"^[a-z0-9-]+$")
    checkpoint_index: int = Field(ge=0)
    provider_id: str | None = None
    model: str | None = None
    messages: List[ChatMessage]
    files: Dict[str, str] = Field(default_factory=dict)
    checkpoint_prompt: str | None = None

    @model_validator(mode="after")
    def _override_must_be_paired(self) -> "ChatRequest":
        if (self.provider_id is None) != (self.model is None):
            raise ValueError(
                "provider_id and model must both be supplied or both omitted "
                "(partial override is rejected to surface client bugs)."
            )
        return self


async def _resolve_text_cfg(user: dict, provider_id: str | None, model: str | None) -> dict:
    """Use the explicit override if supplied, otherwise fall back to
    the user's active text-model setting. Both paths return the same
    cfg dict shape: {kind, model, api_key, base_url}."""
    if provider_id and model:
        provider = await _load_provider(user, provider_id)
        api_key = decrypt(provider.get("encrypted_key") or "", provider.get("key_iv") or "")
        if not api_key:
            raise HTTPException(status_code=400, detail="No API key on file for the chosen provider.")
        return {
            "kind": provider.get("kind") or "provider",
            "model": model,
            "api_key": api_key,
            "base_url": provider.get("base_url") or "",
        }
    return await _active_text_config(user)


class AICodingModel(BaseModel):
    provider_id: str
    provider_label: str
    kind: str
    model: str


async def _enforce_ai_allowed(token: str, slug: str, idx: int) -> None:
    """403 if the round's checkpoint disallows AI. Defense-in-depth — the
    UI already disables the chat input, but the endpoint must not trust
    the client."""
    data = await pb_get(
        token,
        "/api/collections/ai_coding_rounds/records",
        params={"filter": f"slug='{slug}'", "perPage": 1},
    )
    items = (data or {}).get("items") or []
    if not items:
        raise HTTPException(status_code=404, detail="Round not found.")
    checkpoints = items[0].get("checkpoints") or []
    if idx >= len(checkpoints):
        raise HTTPException(status_code=400, detail="Invalid checkpoint index.")
    if not checkpoints[idx].get("ai_allowed"):
        raise HTTPException(status_code=403, detail="AI is disabled for this checkpoint.")


@router.post("/chat")
async def chat(body: ChatRequest, user: dict = Depends(_auth_user)) -> StreamingResponse:
    await _enforce_ai_allowed(user["token"], body.round_slug, body.checkpoint_index)
    cfg = await _resolve_text_cfg(user, body.provider_id, body.model)

    file_context = json.dumps(body.files)[:60_000]  # cap to avoid blowing token budget
    system = _AI_CODING_SYSTEM
    if body.checkpoint_prompt:
        system += "\n\nCurrent checkpoint goal:\n" + body.checkpoint_prompt
    system += "\n\nProject files (JSON):\n" + file_context

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
            _log.exception("ai-coding chat stream failed [rid=%s]", rid)
            kind_, msg = _friendly_error(err)
            yield (
                f"data: {json.dumps({'error': msg, 'error_kind': kind_, 'request_id': rid})}\n\n"
            ).encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/edit")
async def edit(body: ChatRequest, user: dict = Depends(_auth_user)) -> StreamingResponse:
    """SSE: streams the model's response as `delta` events while
    accumulating it, then emits ONE `patches` event and ONE `done`.

    Events on success:  delta(s) → patches → done
    Events on failure:  error  (no patches, no done)

    `patches` is always a list (possibly empty). `parse_error` is
    optional and present only when the model output couldn't be
    parsed as a JSON patch array.
    """
    await _enforce_ai_allowed(user["token"], body.round_slug, body.checkpoint_index)
    cfg = await _resolve_text_cfg(user, body.provider_id, body.model)

    file_context = json.dumps(body.files)[:60_000]
    system = EDIT_SYSTEM_PROMPT
    if body.checkpoint_prompt:
        system += "\n\nCurrent checkpoint goal:\n" + body.checkpoint_prompt
    system += "\n\nProject files (JSON):\n" + file_context
    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    async def gen() -> AsyncIterator[bytes]:
        accumulated = ""
        try:
            async for chunk in _call_stream(
                cfg["kind"], cfg["model"], cfg["api_key"], cfg["base_url"] or None,
                system=system, messages=messages, max_tokens=2400,
            ):
                accumulated += chunk
                yield f"data: {json.dumps({'delta': chunk})}\n\n".encode("utf-8")
            patches, err = _parse_patches(accumulated)
            payload: Dict[str, Any] = {"patches": patches}
            if err:
                payload["parse_error"] = err
            yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
            yield b"data: {\"done\": true}\n\n"
        except Exception as err:  # noqa: BLE001
            rid = _request_id()
            _log.exception("ai-coding edit stream failed [rid=%s]", rid)
            kind_, msg = _friendly_error(err)
            yield (
                f"data: {json.dumps({'error': msg, 'error_kind': kind_, 'request_id': rid})}\n\n"
            ).encode("utf-8")
    return StreamingResponse(gen(), media_type="text/event-stream")


class GradeRequest(BaseModel):
    round_slug: str = Field(pattern=r"^[a-z0-9-]+$")
    files: Dict[str, str]
    ai_chats: List[Dict[str, Any]] = Field(default_factory=list)


@router.post("/grade")
async def grade(body: GradeRequest, user: dict = Depends(_auth_user)) -> Dict[str, Any]:
    # Look up the round server-side. Don't trust the client to ship
    # checkpoints/rubric/hidden_files — those drive grading and must
    # come from the seeded source of truth.
    data = await pb_get(
        user["token"],
        "/api/collections/ai_coding_rounds/records",
        params={"filter": f"slug='{body.round_slug}'", "perPage": 1},
    )
    items = (data or {}).get("items") or []
    if not items:
        raise HTTPException(status_code=404, detail="Round not found.")
    round_row = items[0]
    checkpoints = round_row.get("checkpoints") or []
    rubric = round_row.get("rubric") or {"items": []}
    language = round_row.get("language") or "python"

    test_results = []
    for idx, cp in enumerate(checkpoints):
        test_command = cp.get("test_command")
        if not test_command:
            _log.warning(
                "ai-coding grade: round %r checkpoint %d has no test_command; recording failure",
                body.round_slug, idx,
            )
            test_results.append({
                "passed": False,
                "passed_count": 0,
                "failed_count": 0,
                "stdout": "",
                "error": "Checkpoint is missing a test_command in the seeded round.",
            })
            continue
        merged = {**body.files}
        for hf in (cp.get("hidden_files") or []):
            path = hf.get("path") if isinstance(hf, dict) else None
            contents = hf.get("contents") if isinstance(hf, dict) else None
            if not isinstance(path, str) or not isinstance(contents, str):
                _log.warning(
                    "ai-coding grade: round %r checkpoint %d has malformed hidden_files entry; skipping",
                    body.round_slug, idx,
                )
                continue
            merged[path] = contents
        r = run_project(merged, language, test_command, timeout_s=45)
        test_results.append({
            "passed": r.passed,
            "passed_count": r.passed_count,
            "failed_count": r.failed_count,
            "stdout": r.stdout[:8000],
            "error": r.error,
        })

    rubric_review: Dict[str, Any] = {"items": [], "total": 0.0, "skipped": False}
    try:
        cfg = await _active_text_config(user)
        prompt = _build_rubric_prompt(
            rubric=rubric,
            files=body.files,
            test_results={str(i): tr for i, tr in enumerate(test_results)},
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
        _log.exception("ai-coding grade rubric review failed")
        rubric_review = {"items": [], "total": 0.0, "skipped": True, "reason": str(e)[:300]}

    return {"test_results": test_results, "rubric_review": rubric_review}


@router.get("/models", response_model=List[AICodingModel])
async def list_available_models(user: dict = Depends(_auth_user)) -> List[AICodingModel]:
    rows = await _list_providers_raw(user)
    out: List[AICodingModel] = []
    for r in rows:
        # Skip malformed (no id) or unusable (no key on file) providers —
        # the dropdown emits provider_id back to /chat, so a row without
        # both an id AND a decryptable key is actively broken UX.
        if not r.get("id") or not r.get("encrypted_key"):
            continue
        for m in (r.get("models_cache") or []):
            out.append(AICodingModel(
                provider_id=r["id"],
                provider_label=r.get("label") or "",
                kind=r.get("kind") or "provider",
                model=m,
            ))
    return out
