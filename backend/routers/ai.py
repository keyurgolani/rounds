"""AI provider proxy.

Multi-provider model. A user can configure several `ai_providers` rows
(Anthropic, OpenAI, OpenAI-compatible, Anthropic-compatible) and then
assign one model from any of them to a role: ``text`` (used by import,
improve, tailor, ATS) or ``vision`` (reserved for future image-based
imports). Provider keys are AES-GCM-encrypted at rest and only
decrypted server-side when calling the provider.

Endpoints:

  GET    /api/ai/providers                            list configured providers
  POST   /api/ai/providers                            create a provider
  PATCH  /api/ai/providers/{id}                       update a provider
  DELETE /api/ai/providers/{id}                       delete a provider
  POST   /api/ai/providers/{id}/test                  one-shot completion sanity-check
  POST   /api/ai/providers/{id}/refresh-models        fetch the model list

  GET    /api/ai/settings                             role assignments (text + vision)
  PUT    /api/ai/settings                             save role assignments

  POST   /api/ai/improve                              SSE — bullet rewriter
  POST   /api/ai/import                               text → ResumeData
  POST   /api/ai/ats-rule                             rule-only ATS score
  POST   /api/ai/ats-ai                               AI-quality ATS score
  POST   /api/ai/enhance-projects                     AI-rewrite GH repos
"""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Literal

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import ats as ats_mod
from app.crypto import decrypt, encrypt
from app.pb_auth import POCKETBASE_URL, current_user, pb_get, pb_patch, pb_post


router = APIRouter(prefix="/api/ai", tags=["ai"])
_log = logging.getLogger(__name__)


def _request_id() -> str:
    """Short opaque id for correlating a user-facing error with server logs.

    The id is logged alongside the full traceback and echoed in the
    user-visible error message (or SSE error event) so a support
    interaction can pivot from "I saw error abc123" to the matching
    log line in seconds."""
    return secrets.token_hex(4)

ProviderKind = Literal[
    "anthropic", "openai", "openai-compatible", "anthropic-compatible"
]


# -----------------------------------------------------------------------------
#                              Friendly errors
# -----------------------------------------------------------------------------


def _friendly_error(err: Exception) -> tuple[str, str]:
    """Translate a raw provider/SDK exception into a (kind, message) pair.

    SDK exceptions tend to carry the provider's full JSON body in str(),
    which is too noisy to put in front of a user. We inspect the
    exception's status code (when available) and the message text for
    well-known failure modes and return a short, action-oriented
    sentence the UI can render verbatim. Unmatched cases get a clipped
    first line of the original message rather than the whole payload.
    """
    raw = str(err) or err.__class__.__name__
    text = raw.lower()

    # Pull the HTTP status off the SDK exception if it's there.
    status = getattr(err, "status_code", None)
    if status is None:
        resp = getattr(err, "response", None)
        if resp is not None:
            status = getattr(resp, "status_code", None)

    # Quota / billing — the most common explicit failure for paid APIs.
    if (
        "insufficient_quota" in text
        or "exceeded your current quota" in text
        or ("quota" in text and "billing" in text)
        or "billing" in text and "limit" in text
    ):
        return (
            "quota",
            "Your AI provider has no remaining quota for this key. Top up billing or switch to another provider.",
        )

    # Auth — bad / revoked / mistyped key.
    if (
        "invalid_api_key" in text
        or "invalid api key" in text
        or "incorrect api key" in text
        or "authentication" in text
        or "unauthorized" in text
        or status == 401
    ):
        return (
            "auth",
            "The provider rejected the API key. Update or replace it in Settings → AI providers.",
        )

    # Rate limit — temporary, user can retry.
    if (status == 429) or ("rate" in text and "limit" in text) or "too many requests" in text:
        return (
            "rate_limit",
            "Provider rate-limited the request. Wait a minute and try again.",
        )

    # Model not found / unsupported on this key.
    if (
        "model_not_found" in text
        or "model not found" in text
        or "does not exist" in text and "model" in text
        or status == 404
    ):
        return (
            "model_not_found",
            "The selected model isn't available with this key. Refresh the model list in Settings.",
        )

    # Network / timeout.
    if "timeout" in text or "timed out" in text:
        return ("timeout", "AI provider didn't respond in time. Try again.")
    if (
        ("connection" in text and ("refused" in text or "reset" in text))
        or "name resolution" in text
        or "name or service not known" in text
    ):
        return ("network", "Couldn't reach the AI provider. Check the base URL and your network.")

    # Default: clip the original to the first reasonable chunk so the
    # UI doesn't render a wall of JSON.
    short = raw.strip().splitlines()[0]
    if len(short) > 160:
        short = short[:157].rstrip() + "…"
    return ("unknown", short or "Unknown provider error.")


def _status_for_kind(kind: str) -> int:
    """Map a friendly-error kind to an HTTP status the frontend can
    surface verbatim. We deliberately avoid 502: Cloudflare replaces
    origin 502 responses with its own HTML error page, swallowing our
    JSON ``detail`` and leaving the user with an opaque "Bad gateway"
    message instead of the actionable text from ``_friendly_error``.
    """
    if kind in ("auth", "quota", "model_not_found"):
        # The user's provider config is the failing component — surface
        # as a 4xx so the UI can route it to the settings flow.
        return 400
    if kind == "rate_limit":
        return 429
    # network / timeout / unknown — upstream is unavailable. 503 is the
    # closest semantic match and Cloudflare passes it through.
    return 503


# -----------------------------------------------------------------------------
#                                Pydantic models
# -----------------------------------------------------------------------------


class ProviderOut(BaseModel):
    id: str
    kind: ProviderKind | str
    label: str
    base_url: str = ""
    has_key: bool = False
    models: list[str] = Field(default_factory=list)
    models_cached_at: str = ""


class ProviderIn(BaseModel):
    kind: ProviderKind | str
    label: str
    base_url: str = ""
    # See AISettingsIn.key for the three-way semantics.
    key: str | None = None


class SettingsOut(BaseModel):
    text_provider_id: str | None = None
    text_model: str = ""
    vision_provider_id: str | None = None
    vision_model: str = ""


class SettingsIn(BaseModel):
    text_provider_id: str | None = None
    text_model: str = ""
    vision_provider_id: str | None = None
    vision_model: str = ""


class ImproveRequest(BaseModel):
    text: str = Field(..., min_length=1)
    style: Literal["improve", "fix", "shorten", "guided-summary"] = "improve"
    context: dict[str, Any] | None = None
    # Optional whole-resume context. When provided, the model gets
    # the full ResumeData JSON so a single-field rewrite stays
    # consistent with the rest of the document. Computed
    # rule-based ATS suggestions are derived server-side from
    # `resume`, plus any AI ATS suggestions the caller forwards in
    # `ats`.
    resume: dict[str, Any] | None = None
    ats: dict[str, Any] | None = None
    field: str | None = None


class ImportRequest(BaseModel):
    text: str = Field(..., min_length=10)


class ExperienceImportRequest(BaseModel):
    text: str = Field(..., min_length=10)


class TailorRequest(BaseModel):
    data: dict[str, Any]
    job_description: str = Field(..., min_length=20)
    tone: str = "professional"
    role_focus: list[str] = Field(default_factory=list)
    target_company: str = ""
    job_title: str = ""


class CoverLetterRequest(BaseModel):
    data: dict[str, Any]
    job_description: str = Field(..., min_length=20)
    tone: str = "professional"
    target_company: str = ""
    job_title: str = ""


class ATSRequest(BaseModel):
    data: dict[str, Any]
    job_description: str | None = None
    use_ai: bool = True


class EnhanceProjectsRequest(BaseModel):
    # Each project: a partial repo summary the model uses to author a
    # better description + 2–3 highlight bullets.
    projects: list[dict[str, Any]] = Field(default_factory=list)


# -----------------------------------------------------------------------------
#                              PB row helpers
# -----------------------------------------------------------------------------


def _provider_out(row: dict[str, Any]) -> ProviderOut:
    return ProviderOut(
        id=row.get("id") or "",
        kind=row.get("kind") or "provider",
        label=row.get("label") or "",
        base_url=row.get("base_url") or "",
        has_key=bool(row.get("encrypted_key")),
        models=list(row.get("models_cache") or []),
        models_cached_at=row.get("models_cached_at") or "",
    )


async def _list_providers_raw(user: dict) -> list[dict[str, Any]]:
    body = await pb_get(
        user["token"],
        "/api/collections/ai_providers/records",
        params={
            "filter": f'user = "{user["id"]}"',
            "perPage": 50,
            "sort": "created",
        },
    )
    return list((body or {}).get("items") or [])


async def _load_provider(user: dict, provider_id: str) -> dict[str, Any]:
    row = await pb_get(
        user["token"],
        f"/api/collections/ai_providers/records/{provider_id}",
    )
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if row.get("user") != user["id"]:
        # PB's listRule should already enforce this — defense in depth.
        raise HTTPException(status_code=403, detail="Forbidden.")
    return row


async def _load_settings(user: dict) -> dict[str, Any] | None:
    body = await pb_get(
        user["token"],
        "/api/collections/ai_settings/records",
        params={"filter": f'user = "{user["id"]}"', "perPage": 1},
    )
    items = (body or {}).get("items") or []
    return items[0] if items else None


async def _delete_pb(token: str, path: str) -> None:
    async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=8) as client:
        resp = await client.delete(
            path, headers={"Authorization": f"Bearer {token}"}
        )
    if resp.status_code >= 400 and resp.status_code != 404:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"PocketBase error: {resp.text}",
        )


# -----------------------------------------------------------------------------
#                              Provider endpoints
# -----------------------------------------------------------------------------


@router.get("/providers")
async def list_providers(request: Request) -> list[ProviderOut]:
    user = await current_user(request)
    rows = await _list_providers_raw(user)
    return [_provider_out(r) for r in rows]


@router.post("/providers", response_model=ProviderOut)
async def create_provider(request: Request, body: ProviderIn) -> ProviderOut:
    user = await current_user(request)
    payload: dict[str, Any] = {
        "user": user["id"],
        "kind": body.kind,
        "label": body.label,
        "base_url": body.base_url or "",
    }
    if body.key:
        enc = encrypt(body.key.strip())
        payload["encrypted_key"] = enc.ciphertext_b64
        payload["key_iv"] = enc.iv_b64
    res = await pb_post(
        user["token"], "/api/collections/ai_providers/records", payload
    )
    return _provider_out(res)


@router.patch("/providers/{provider_id}", response_model=ProviderOut)
async def update_provider(
    request: Request, provider_id: str, body: ProviderIn
) -> ProviderOut:
    user = await current_user(request)
    row = await _load_provider(user, provider_id)
    payload: dict[str, Any] = {
        "kind": body.kind,
        "label": body.label,
        "base_url": body.base_url or "",
    }
    if body.key is None:
        # Explicit clear.
        payload["encrypted_key"] = ""
        payload["key_iv"] = ""
    elif body.key.strip():
        enc = encrypt(body.key.strip())
        payload["encrypted_key"] = enc.ciphertext_b64
        payload["key_iv"] = enc.iv_b64
    # else: empty string → leave existing key in place (don't touch the field)

    res = await pb_patch(
        user["token"],
        f"/api/collections/ai_providers/records/{provider_id}",
        payload,
    )
    return _provider_out(res)


@router.delete("/providers/{provider_id}")
async def delete_provider(request: Request, provider_id: str) -> dict[str, bool]:
    user = await current_user(request)
    # Defensive ownership check — PB enforces ownerRule but we want a
    # clear 404 instead of a 401-on-unrelated-row.
    await _load_provider(user, provider_id)
    await _delete_pb(
        user["token"], f"/api/collections/ai_providers/records/{provider_id}"
    )
    return {"ok": True}


@router.post("/providers/{provider_id}/test")
async def test_provider(
    request: Request, provider_id: str
) -> dict[str, Any]:
    user = await current_user(request)
    row = await _load_provider(user, provider_id)
    api_key = decrypt(row.get("encrypted_key") or "", row.get("key_iv") or "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No API key on file for this provider.")
    kind = row.get("kind") or "provider"
    base_url = row.get("base_url") or ""

    # Pick the cheapest reasonable model. For the test we ask the model
    # to say PONG; if anything comes back we treat it as success.
    cached = list(row.get("models_cache") or [])
    model = cached[0] if cached else _default_model(kind)
    if not model:
        # Refresh once, then try again.
        try:
            cached = await _fetch_models(kind, api_key, base_url)
            await pb_patch(
                user["token"],
                f"/api/collections/ai_providers/records/{provider_id}",
                {"models_cache": cached, "models_cached_at": _utc_now_iso()},
            )
            model = cached[0] if cached else _default_model(kind)
        except HTTPException:
            raise
        except Exception as err:  # noqa: BLE001
            rid = _request_id()
            _log.exception("provider test: model refresh failed [rid=%s]", rid)
            raise HTTPException(
                status_code=503,
                detail=f"Provider error: {err} (request id: {rid})",
            ) from err

    try:
        text = await _call_complete(
            kind,
            model,
            api_key,
            base_url or None,
            system="You are a connectivity check.",
            messages=[{"role": "user", "content": "Reply with the single word PONG."}],
            max_tokens=12,
        )
    except HTTPException:
        raise
    except Exception as err:  # noqa: BLE001
        rid = _request_id()
        _log.exception("provider test failed [rid=%s]", rid)
        kind_, msg = _friendly_error(err)
        raise HTTPException(
            status_code=_status_for_kind(kind_),
            detail=f"{msg} (request id: {rid})",
        ) from err
    return {"ok": True, "model": model, "reply": text}


@router.post("/providers/{provider_id}/refresh-models")
async def refresh_models(
    request: Request, provider_id: str
) -> dict[str, Any]:
    user = await current_user(request)
    row = await _load_provider(user, provider_id)
    api_key = decrypt(row.get("encrypted_key") or "", row.get("key_iv") or "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No API key on file for this provider.")
    kind = row.get("kind") or "provider"
    base_url = row.get("base_url") or ""

    try:
        models = await _fetch_models(kind, api_key, base_url)
    except HTTPException:
        raise
    except Exception as err:  # noqa: BLE001
        rid = _request_id()
        _log.exception("refresh-models failed [rid=%s]", rid)
        raise HTTPException(
            status_code=503,
            detail=f"Provider error: {err} (request id: {rid})",
        ) from err

    await pb_patch(
        user["token"],
        f"/api/collections/ai_providers/records/{provider_id}",
        {"models_cache": models, "models_cached_at": _utc_now_iso()},
    )
    return {"models": models, "models_cached_at": _utc_now_iso()}


# -----------------------------------------------------------------------------
#                              Settings endpoints
# -----------------------------------------------------------------------------


@router.get("/settings", response_model=SettingsOut)
async def get_settings(request: Request) -> SettingsOut:
    user = await current_user(request)
    row = await _load_settings(user)
    if not row:
        return SettingsOut()
    return SettingsOut(
        text_provider_id=row.get("text_provider") or None,
        text_model=row.get("text_model") or "",
        vision_provider_id=row.get("vision_provider") or None,
        vision_model=row.get("vision_model") or "",
    )


@router.put("/settings", response_model=SettingsOut)
async def put_settings(request: Request, body: SettingsIn) -> SettingsOut:
    user = await current_user(request)
    row = await _load_settings(user)
    payload: dict[str, Any] = {
        "user": user["id"],
        "text_provider": body.text_provider_id or None,
        "text_model": body.text_model or "",
        "vision_provider": body.vision_provider_id or None,
        "vision_model": body.vision_model or "",
    }
    if row:
        await pb_patch(
            user["token"],
            f"/api/collections/ai_settings/records/{row['id']}",
            payload,
        )
    else:
        await pb_post(
            user["token"], "/api/collections/ai_settings/records", payload
        )
    return SettingsOut(
        text_provider_id=body.text_provider_id,
        text_model=body.text_model,
        vision_provider_id=body.vision_provider_id,
        vision_model=body.vision_model,
    )


# -----------------------------------------------------------------------------
#                          Active config + dispatch
# -----------------------------------------------------------------------------


async def _active_text_config(user: dict) -> dict[str, Any]:
    settings = await _load_settings(user)
    if not settings or not settings.get("text_provider") or not settings.get("text_model"):
        raise HTTPException(
            status_code=400,
            detail="No text model configured. Visit Settings → AI providers.",
        )
    provider = await _load_provider(user, settings["text_provider"])
    api_key = decrypt(provider.get("encrypted_key") or "", provider.get("key_iv") or "")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="No API key on file for the selected text provider.",
        )
    return {
        "kind": provider.get("kind") or "provider",
        "model": settings["text_model"],
        "api_key": api_key,
        "base_url": provider.get("base_url") or "",
    }


async def _call_complete(
    kind: str,
    model: str,
    api_key: str,
    base_url: str | None,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 1024,
) -> str:
    if kind in ("anthropic", "anthropic-compatible"):
        return await _anthropic_complete(model, api_key, base_url, system, messages, max_tokens)
    return await _openai_complete(model, api_key, base_url, system, messages, max_tokens)


async def _anthropic_complete(
    model: str,
    api_key: str,
    base_url: str | None,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
) -> str:
    """Native HTTP call to an Anthropic-style messages endpoint.

    We don't use the official ``anthropic`` SDK here because it
    hardcodes ``/v1/messages`` onto whatever base_url it gets — so a
    user-supplied base of ``https://api.example.com/v4`` becomes
    ``…/v4/v1/messages`` and 404s. By driving httpx directly we treat
    ``base_url`` as the full API prefix (the user's ``/v4`` or our
    canonical ``/v1`` for native) and just append ``/messages``,
    matching the same prefix the model-listing endpoint hits.
    """
    base = (base_url or _ANTHROPIC_DEFAULT_BASE).rstrip("/")
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{base}/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
        )
    if resp.status_code >= 400:
        # Surface the provider's error body so _friendly_error can
        # match status codes / quota / auth / model-not-found cases.
        raise httpx.HTTPStatusError(
            f"Error code: {resp.status_code} - {resp.text}",
            request=resp.request,
            response=resp,
        )
    parsed = resp.json()
    parts: list[str] = []
    for block in parsed.get("content") or []:
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts).strip()


async def _openai_complete(
    model: str,
    api_key: str,
    base_url: str | None,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
) -> str:
    from openai import AsyncOpenAI

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = AsyncOpenAI(**kwargs)
    chat = [{"role": "system", "content": system}] + messages
    res = await client.chat.completions.create(
        model=model,
        messages=chat,
        max_tokens=max_tokens,
    )
    return (res.choices[0].message.content or "").strip()


async def _call_stream(
    kind: str,
    model: str,
    api_key: str,
    base_url: str | None,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 512,
) -> AsyncIterator[str]:
    if kind in ("anthropic", "anthropic-compatible"):
        async for chunk in _anthropic_stream(model, api_key, base_url, system, messages, max_tokens):
            yield chunk
    else:
        async for chunk in _openai_stream(model, api_key, base_url, system, messages, max_tokens):
            yield chunk


async def _anthropic_stream(
    model: str,
    api_key: str,
    base_url: str | None,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
) -> AsyncIterator[str]:
    """Streaming version — same base-URL handling as ``_anthropic_complete``.

    Anthropic's streaming protocol is server-sent events; we yield only
    the ``content_block_delta`` text deltas, which is what callers
    actually want.
    """
    base = (base_url or _ANTHROPIC_DEFAULT_BASE).rstrip("/")
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{base}/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "accept": "text/event-stream",
                "content-type": "application/json",
            },
            json=body,
        ) as resp:
            if resp.status_code >= 400:
                error_text = (await resp.aread()).decode("utf-8", errors="replace")
                raise httpx.HTTPStatusError(
                    f"Error code: {resp.status_code} - {error_text}",
                    request=resp.request,
                    response=resp,
                )
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if not payload:
                    continue
                try:
                    obj = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") == "content_block_delta":
                    delta = obj.get("delta") or {}
                    if delta.get("type") == "text_delta":
                        text = delta.get("text") or ""
                        if text:
                            yield text


async def _openai_stream(
    model: str,
    api_key: str,
    base_url: str | None,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
) -> AsyncIterator[str]:
    from openai import AsyncOpenAI

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = AsyncOpenAI(**kwargs)
    chat = [{"role": "system", "content": system}] + messages
    stream = await client.chat.completions.create(
        model=model,
        messages=chat,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield delta.content


# -----------------------------------------------------------------------------
#                              Model list endpoints
# -----------------------------------------------------------------------------


_ANTHROPIC_DEFAULT_BASE = "https://api.anthropic.com/v1"
_OPENAI_DEFAULT_BASE = "https://api.openai.com/v1"


def _models_url(kind: str, base_url: str) -> str:
    base = (base_url or "").rstrip("/")
    if kind == "anthropic":
        return f"{_ANTHROPIC_DEFAULT_BASE}/models"
    if kind == "anthropic-compatible":
        if not base:
            raise HTTPException(status_code=400, detail="Custom Anthropic-compatible endpoint requires a base URL.")
        return f"{base}/models"
    if kind == "openai":
        return f"{_OPENAI_DEFAULT_BASE}/models"
    if kind == "openai-compatible":
        if not base:
            raise HTTPException(status_code=400, detail="Custom OpenAI-compatible endpoint requires a base URL.")
        return f"{base}/models"
    raise HTTPException(status_code=400, detail=f"Unknown provider kind: {kind}")


def _models_headers(kind: str, api_key: str) -> dict[str, str]:
    if kind in ("anthropic", "anthropic-compatible"):
        return {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
    return {"Authorization": f"Bearer {api_key}"}


async def _fetch_models(kind: str, api_key: str, base_url: str) -> list[str]:
    url = _models_url(kind, base_url)
    headers = _models_headers(kind, api_key)
    async with httpx.AsyncClient(timeout=12) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=503,
            detail=f"Provider rejected the model list ({resp.status_code}): {resp.text[:300]}",
        )
    body = resp.json()
    items = body.get("data") if isinstance(body, dict) else None
    if not isinstance(items, list):
        # Some custom endpoints (e.g. Ollama) return {"models": [...]}.
        items = body.get("models") if isinstance(body, dict) else None
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for it in items:
        if isinstance(it, dict):
            mid = it.get("id") or it.get("name")
            if isinstance(mid, str) and mid:
                out.append(mid)
    out.sort()
    return out


def _default_model(kind: str) -> str:
    if kind in ("anthropic", "anthropic-compatible"):
        return "claude-sonnet-4-6"
    return "gpt-4o-mini"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# -----------------------------------------------------------------------------
#                                 Improve
# -----------------------------------------------------------------------------


_IMPROVE_SYSTEM = (
    "You rewrite a single field of a resume. The user message gives "
    "you (in order) the full resume context, ATS feedback (rule + "
    "AI), any role/JD/paper context, and the field's current value. "
    "Use ALL of that to make the rewrite cohere with the rest of "
    "the resume and address ATS gaps — but output ONLY the new "
    "content for the named field. No preamble, no quotes, no "
    "markdown, no leading dashes, no labels, no JSON wrapper. "
    "If the field's current value contains multiple non-empty "
    "newline-separated lines, treat each line as its own bullet "
    "and rewrite each on its own line in the same order, "
    "preserving the line count. Keep each line under 200 "
    "characters when possible. Lead with strong action verbs. "
    "Incorporate missing keywords from the job description when "
    "they fit naturally. Quantify impact when the source implies "
    "a measurable result. Preserve concrete facts; do not invent "
    "details, metrics, users, or team sizes."
)


# Drives the "Guided summary" affordance in the Personal Info editor
# (modal with three structured inputs: years, top skills, signature
# accomplishment). The user payload arrives via context so we can
# reuse the existing /improve plumbing (auth, streaming, errors)
# without a separate endpoint.
_GUIDED_SUMMARY_SYSTEM = (
    "You write a single-paragraph resume professional summary in the "
    "three-part formula:\n"
    "  (1) Years of experience + role/industry\n"
    "  (2) Two or three best-fit skills (verbatim from input top skills, "
    "lightly rephrased only if grammar requires it)\n"
    "  (3) One signature accomplishment with hard numbers (preserve every "
    "number from the input accomplishment exactly — do not invent or "
    "alter quantities, percentages, or dollar amounts)\n\n"
    "Output: 2–3 sentences, 45–75 words, plain prose, no bullets, no "
    "markdown, no preamble, no quotes, no labels. Lead with the years "
    "clause. Do not invent companies, titles, technologies, team sizes, "
    "or metrics not present in the structured input or the resume "
    "context. If a structured input is missing, omit that part rather "
    "than fabricate."
)


# Caps for inlined context. Larger context is more grounded but the
# prompt cost scales linearly so we trim to something usable.
_IMPROVE_RESUME_LIMIT = 12000
_IMPROVE_ATS_LIMIT = 4000
_IMPROVE_PAPER_LIMIT = 8000


def _improve_user_prompt(
    text: str,
    style: str,
    context: dict[str, Any] | None,
    *,
    resume: dict[str, Any] | None = None,
    ats: dict[str, Any] | None = None,
    field: str | None = None,
    paper_text: str | None = None,
) -> str:
    parts: list[str] = []
    if field:
        parts.append(f"You are improving the resume field: {field}.")

    if resume:
        try:
            r_str = json.dumps(resume, separators=(",", ":"))
        except (TypeError, ValueError):
            r_str = ""
        if r_str:
            if len(r_str) > _IMPROVE_RESUME_LIMIT:
                r_str = r_str[:_IMPROVE_RESUME_LIMIT] + " [truncated]"
            parts.append(f"Full resume context (JSON):\n{r_str}")

    if ats:
        try:
            a_str = json.dumps(ats, separators=(",", ":"))
        except (TypeError, ValueError):
            a_str = ""
        if a_str:
            if len(a_str) > _IMPROVE_ATS_LIMIT:
                a_str = a_str[:_IMPROVE_ATS_LIMIT] + " [truncated]"
            parts.append(f"ATS feedback (rule + AI):\n{a_str}")

    if context:
        bits: list[str] = []
        if context.get("position") or context.get("company"):
            bits.append(
                "Specific context: this content is from a role as "
                f"{context.get('position') or 'engineer'} at "
                f"{context.get('company') or 'a company'}."
            )
        if context.get("job_description"):
            bits.append(
                "Target job description (paraphrase relevant phrasing): "
                f"{context['job_description'][:1500]}"
            )
        if context.get("paper_url"):
            bits.append(f"Source paper URL: {context['paper_url']}")
        if bits:
            parts.append(" ".join(bits))
        guided_bits: list[str] = []
        years = context.get("years")
        if isinstance(years, (int, float)) and years > 0:
            guided_bits.append(f"Years of experience: {int(years)}")
        top_skills = context.get("top_skills")
        if isinstance(top_skills, list):
            cleaned = [str(s).strip() for s in top_skills if str(s).strip()]
            if cleaned:
                guided_bits.append("Top skills: " + ", ".join(cleaned))
        accomplishment = context.get("signature_accomplishment")
        if isinstance(accomplishment, str) and accomplishment.strip():
            guided_bits.append(
                "Signature accomplishment (preserve all numbers exactly): "
                + accomplishment.strip()
            )
        if guided_bits:
            parts.append("Structured guided-summary inputs:\n" + "\n".join(guided_bits))

    if paper_text:
        excerpt = paper_text[:_IMPROVE_PAPER_LIMIT]
        parts.append(f"Source paper text excerpt:\n{excerpt}")

    parts.append(f"Style: {style}.")
    parts.append(f"Current value of the field:\n{text}")
    parts.append(
        "Output ONLY the new content for the field — no preamble, no "
        "markdown, no quotes, no labels."
    )
    return "\n\n".join(parts)


async def _fetch_paper_text(url: str) -> str | None:
    """Best-effort fetch + extract for a publication URL.

    Returns plain text from the paper. Handles HTML (strips tags) and
    PDF (via pdfminer.six). Silent on failure — the caller falls back
    to whatever non-paper context it has.
    """
    if not url or not isinstance(url, str):
        return None
    try:
        timeout = httpx.Timeout(15.0, connect=10.0)
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "rounds-resume-studio"},
        ) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            ctype = (r.headers.get("content-type") or "").lower()
            url_l = url.lower()
            if "pdf" in ctype or url_l.endswith(".pdf"):
                from io import BytesIO
                from pdfminer.high_level import extract_text

                text = extract_text(BytesIO(r.content)) or ""
                return text.strip() or None
            if "html" in ctype or "text" in ctype or not ctype:
                from html.parser import HTMLParser

                class _Strip(HTMLParser):
                    def __init__(self) -> None:
                        super().__init__()
                        self.parts: list[str] = []
                        self.skip = 0

                    def handle_starttag(
                        self, tag: str, _attrs: list[tuple[str, str | None]]
                    ) -> None:
                        if tag.lower() in ("script", "style", "noscript"):
                            self.skip += 1

                    def handle_endtag(self, tag: str) -> None:
                        if tag.lower() in ("script", "style", "noscript"):
                            self.skip = max(0, self.skip - 1)

                    def handle_data(self, data: str) -> None:
                        if not self.skip:
                            self.parts.append(data)

                p = _Strip()
                p.feed(r.text)
                text = " ".join(s.strip() for s in p.parts if s.strip())
                return text.strip() or None
            return (r.text or "").strip() or None
    except Exception:  # noqa: BLE001
        _log.exception("paper fetch failed for %s", url)
        return None


@router.post("/improve")
async def improve(request: Request, body: ImproveRequest) -> StreamingResponse:
    user = await current_user(request)
    cfg = await _active_text_config(user)

    # Auto-derive rule-based ATS from the resume so every improve
    # call carries deterministic suggestions even when the caller
    # didn't pre-score. Caller-supplied AI suggestions (in `ats`)
    # are merged on top.
    ats_payload: dict[str, Any] | None = None
    if body.resume:
        try:
            jd = (
                body.context.get("job_description")
                if isinstance(body.context, dict)
                else None
            )
            rule = ats_mod.score_resume(body.resume, jd)
            ats_payload = {
                "rule_score": rule.score,
                "rule_breakdown": rule.breakdown,
                "rule_suggestions": rule.suggestions,
                "missing_keywords": rule.missing_keywords,
            }
        except Exception:  # noqa: BLE001
            _log.exception("rule-based ATS scoring failed during improve; degrading without it")
            ats_payload = None
    if isinstance(body.ats, dict):
        ats_payload = {**(ats_payload or {}), **body.ats}

    # Publications can hand in a `paper_url` to ground the improve
    # in the actual paper text (HTML or PDF). Best effort — failure
    # is silent and we fall through to other context.
    paper_text: str | None = None
    if (
        isinstance(body.context, dict)
        and isinstance(body.context.get("paper_url"), str)
        and body.context["paper_url"].strip()
    ):
        paper_text = await _fetch_paper_text(body.context["paper_url"].strip())

    user_prompt = _improve_user_prompt(
        body.text,
        body.style,
        body.context,
        resume=body.resume,
        ats=ats_payload,
        field=body.field,
        paper_text=paper_text,
    )

    system_prompt = (
        _GUIDED_SUMMARY_SYSTEM if body.style == "guided-summary" else _IMPROVE_SYSTEM
    )

    async def gen() -> AsyncIterator[bytes]:
        try:
            async for chunk in _call_stream(
                cfg["kind"],
                cfg["model"],
                cfg["api_key"],
                cfg["base_url"] or None,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=1200,
            ):
                yield f"data: {json.dumps({'delta': chunk})}\n\n".encode("utf-8")
            yield b"data: {\"done\": true}\n\n"
        except Exception as err:  # noqa: BLE001
            rid = _request_id()
            _log.exception("improve stream failed [rid=%s]", rid)
            kind_, msg = _friendly_error(err)
            yield (
                f"data: {json.dumps({'error': msg, 'error_kind': kind_, 'request_id': rid})}\n\n"
            ).encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")


# -----------------------------------------------------------------------------
#                                 Import
# -----------------------------------------------------------------------------


_IMPORT_SYSTEM = (
    "You parse plain-text resumes into structured JSON. Output ONLY a "
    "JSON object — no markdown, no commentary. Schema:\n"
    "{\n"
    '  "personalInfo": {"fullName":"","email":"","phone":"","location":"","website":"","linkedin":"","github":"","title":"","summary":""},\n'
    '  "experience": [{"company":"","position":"","location":"","startDate":"YYYY-MM","endDate":"YYYY-MM","current":false,"description":"","highlights":[]}],\n'
    '  "education": [{"institution":"","degree":"","field":"","location":"","startDate":"YYYY-MM","endDate":"YYYY-MM","gpa":"","description":""}],\n'
    '  "skills": [{"category":"","items":[]}],\n'
    '  "projects": [{"name":"","description":"","technologies":[],"url":"","github":"","startDate":"","endDate":"","highlights":[]}],\n'
    '  "publications": [{"title":"","publisher":"","releaseDate":"","url":"","summary":""}],\n'
    '  "profiles": [{"network":"","username":"","url":""}]\n'
    "}\n"
    "Rules: dates as YYYY-MM where possible (if only year known, use YYYY-01). "
    "Leave fields empty (\"\" or []) when unknown — never invent. Bullets "
    "go in `highlights`. Group skills by category if the source text "
    "implies one."
)


_EXPERIENCE_IMPORT_SYSTEM = (
    "You extract career experience data from plain text into structured JSON. "
    "Output ONLY a JSON object — no markdown, no commentary. Schema:\n"
    "{\n"
    '  "jobs": [{"company":"","role":"","location":"","employment_type":"","start_date":"YYYY-MM-DD","end_date":"YYYY-MM-DD","description":"","tags":[]}],\n'
    '  "projects": [{"title":"","company":"","role":"","team_size":null,"tech_stack":[],"start_date":"YYYY-MM-DD","end_date":"YYYY-MM-DD","description":"","tags":[]}],\n'
    '  "anecdotes": [{"title":"","situation":"","task":"","action":"","result":"","impact":"","company":"","project":"","date":"YYYY-MM-DD","tags":[]}],\n'
    '  "bullets": [{"title":"","impact":"","category":"","date":"YYYY-MM-DD","tags":[]}],\n'
    '  "connections": [{"parent_type":"","parent_index":0,"child_type":"","child_index":0}]\n'
    "}\n"
    "Rules:\n"
    "- All dates must be YYYY-MM-DD. If only year-month is known, use the 1st. If only year, use YYYY-01-01.\n"
    "- Anecdotes should follow STAR format (Situation, Task, Action, Result).\n"
    "- Connections link entities: valid parent->child pairs are job->project, job->anecdote, "
    "job->bullet, project->anecdote, project->bullet, anecdote->bullet.\n"
    "- Indices in connections are 0-based into their respective arrays.\n"
    "- Extract at most 20 items total across all arrays.\n"
    "- Leave fields empty (\"\" or [] or null) when unknown — never invent information.\n"
    "- Tags should be short skill or domain labels (e.g. \"leadership\", \"Python\", \"B2B sales\").\n"
    "- employment_type values: full-time, part-time, contract, internship, freelance.\n"
    "- category values for bullets: achievement, responsibility, skill, other."
)


_TAILOR_SYSTEM = (
    "You rewrite a resume to better match a target job description. "
    "You receive the current resume as JSON and a job description. "
    "Rewrite bullet points (experience[].highlights, projects[].highlights) "
    "and the personal summary to emphasize the skills and outcomes most "
    "relevant to the JD. You may reorder skill items so JD-aligned ones "
    "appear first. NEVER invent positions, companies, dates, or "
    "achievements that aren't in the source resume — preserve every "
    "factual claim. Keep edits minimal where the source already aligns. "
    "Preserve all `id` fields exactly. Output ONLY the rewritten resume "
    "as a JSON object with the same shape as the input — no markdown, "
    "no commentary."
)


@router.post("/tailor")
async def tailor_resume(request: Request, body: TailorRequest) -> dict[str, Any]:
    user = await current_user(request)
    cfg = await _active_text_config(user)

    user_prompt = json.dumps(
        {
            "current_resume": body.data,
            "job_description": body.job_description[:8000],
            "tone": body.tone or "professional",
            "role_focus": body.role_focus,
            "target_company": body.target_company,
            "job_title": body.job_title,
        }
    )
    try:
        text = await _call_complete(
            cfg["kind"],
            cfg["model"],
            cfg["api_key"],
            cfg["base_url"] or None,
            system=_TAILOR_SYSTEM,
            messages=[{"role": "user", "content": user_prompt[:24000]}],
            max_tokens=6000,
        )
    except Exception as err:  # noqa: BLE001
        rid = _request_id()
        _log.exception("tailor failed [rid=%s]", rid)
        kind_, msg = _friendly_error(err)
        raise HTTPException(
            status_code=_status_for_kind(kind_),
            detail=f"{msg} (request id: {rid})",
        ) from err

    parsed = _safe_json(text)
    if not parsed:
        raise HTTPException(
            status_code=503,
            detail="The provider didn't return valid JSON. Try a different model or shorten the JD.",
        )
    # Make sure ids on existing entries are preserved if the model dropped them.
    _stamp_ids(parsed)
    return {"data": parsed}


_COVER_LETTER_SYSTEM = (
    "You write a single cover letter from the candidate's resume and a "
    "target job description. Output ONLY the letter body — no salutation "
    "(no 'Dear …,'), no signature line. 3 paragraphs:\n"
    "  1. Hook — why this company, this role.\n"
    "  2. Match — 2–3 specific resume facts that map to the JD; do NOT "
    "     invent achievements.\n"
    "  3. Close — what you bring + a clear call to action.\n"
    "Honor the requested tone. Keep it under 350 words. No filler, no "
    "rephrased JD bullets back at the recruiter, no clichés like "
    "'passionate'."
)


@router.post("/cover-letter")
async def cover_letter(
    request: Request, body: CoverLetterRequest
) -> StreamingResponse:
    user = await current_user(request)
    cfg = await _active_text_config(user)

    user_prompt = json.dumps(
        {
            "resume": body.data,
            "job_description": body.job_description[:8000],
            "tone": body.tone or "professional",
            "target_company": body.target_company,
            "job_title": body.job_title,
        }
    )

    async def gen() -> AsyncIterator[bytes]:
        try:
            async for chunk in _call_stream(
                cfg["kind"],
                cfg["model"],
                cfg["api_key"],
                cfg["base_url"] or None,
                system=_COVER_LETTER_SYSTEM,
                messages=[{"role": "user", "content": user_prompt[:18000]}],
                max_tokens=900,
            ):
                yield f"data: {json.dumps({'delta': chunk})}\n\n".encode("utf-8")
            yield b"data: {\"done\": true}\n\n"
        except Exception as err:  # noqa: BLE001
            rid = _request_id()
            _log.exception("cover-letter stream failed [rid=%s]", rid)
            kind_, msg = _friendly_error(err)
            yield (
                f"data: {json.dumps({'error': msg, 'error_kind': kind_, 'request_id': rid})}\n\n"
            ).encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/import")
async def import_resume(request: Request, body: ImportRequest) -> dict[str, Any]:
    user = await current_user(request)
    cfg = await _active_text_config(user)
    raw = body.text.strip()
    if len(raw) < 10:
        raise HTTPException(status_code=400, detail="Text too short to parse.")
    try:
        text = await _call_complete(
            cfg["kind"],
            cfg["model"],
            cfg["api_key"],
            cfg["base_url"] or None,
            system=_IMPORT_SYSTEM,
            messages=[{"role": "user", "content": raw[:30000]}],
            max_tokens=4000,
        )
    except Exception as err:  # noqa: BLE001
        rid = _request_id()
        _log.exception("import failed [rid=%s]", rid)
        kind_, msg = _friendly_error(err)
        raise HTTPException(
            status_code=_status_for_kind(kind_),
            detail=f"{msg} (request id: {rid})",
        ) from err

    parsed = _safe_json(text)
    if not parsed:
        raise HTTPException(
            status_code=503,
            detail="The provider didn't return valid JSON. Try a different model or shorten the input.",
        )
    _stamp_ids(parsed)
    return {"data": parsed}


@router.post("/experience-import")
async def import_experience(request: Request, body: ExperienceImportRequest) -> dict[str, Any]:
    user = await current_user(request)
    cfg = await _active_text_config(user)
    raw = body.text.strip()
    try:
        text = await _call_complete(
            cfg["kind"],
            cfg["model"],
            cfg["api_key"],
            cfg["base_url"] or None,
            system=_EXPERIENCE_IMPORT_SYSTEM,
            messages=[{"role": "user", "content": raw[:30000]}],
            max_tokens=6000,
        )
    except Exception as err:  # noqa: BLE001
        rid = _request_id()
        _log.exception("experience-import failed [rid=%s]", rid)
        kind_, msg = _friendly_error(err)
        raise HTTPException(
            status_code=_status_for_kind(kind_),
            detail=f"{msg} (request id: {rid})",
        ) from err

    parsed = _safe_json(text)
    if not parsed:
        raise HTTPException(
            status_code=503,
            detail="The provider didn't return valid JSON. Try a different model or shorten the input.",
        )
    for key in ("jobs", "projects", "anecdotes", "bullets", "connections"):
        parsed.setdefault(key, [])
    return {"data": parsed, "warnings": []}


def _safe_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    start = text.find("{")
    if start < 0:
        return None
    end = text.rfind("}")
    if end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    # Truncated or otherwise malformed. Try to recover by walking the
    # braces and closing whatever nesting is still open at the cut
    # point — common when the model exhausts max_tokens mid-string.
    return _recover_truncated_json(text[start:])


def _recover_truncated_json(s: str) -> dict[str, Any] | None:
    """Best-effort recovery of a truncated JSON object.

    Scans char-by-char tracking string state and brace/bracket depth,
    then closes whatever's still open. If the cut landed inside a
    string we drop everything from the last safe key boundary onward
    so the result still parses.
    """
    depth_obj = 0
    depth_arr = 0
    in_str = False
    escape = False
    last_safe = -1  # index just after a `,` or `{` while not in a string at depth>=1
    for i, ch in enumerate(s):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth_obj += 1
        elif ch == "}":
            depth_obj -= 1
        elif ch == "[":
            depth_arr += 1
        elif ch == "]":
            depth_arr -= 1
        elif ch == "," and depth_obj >= 1:
            last_safe = i  # cut here if we have to
    # If we ended inside a string, rewind to the last comma at the top
    # object level and retry from there.
    candidate: str
    if in_str and last_safe > 0:
        candidate = s[:last_safe]
    else:
        candidate = s
    # Close any still-open arrays then objects.
    # Re-scan candidate to compute final depths (cheap; same pass as above).
    d_obj = 0
    d_arr = 0
    in_s = False
    esc = False
    for ch in candidate:
        if esc:
            esc = False
            continue
        if ch == "\\" and in_s:
            esc = True
            continue
        if ch == '"':
            in_s = not in_s
            continue
        if in_s:
            continue
        if ch == "{":
            d_obj += 1
        elif ch == "}":
            d_obj -= 1
        elif ch == "[":
            d_arr += 1
        elif ch == "]":
            d_arr -= 1
    if in_s:
        candidate += '"'
    candidate += "]" * max(0, d_arr) + "}" * max(0, d_obj)
    try:
        result = json.loads(candidate)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None


def _stamp_ids(data: dict[str, Any]) -> None:
    import secrets as _s

    for key in ("experience", "education", "skills", "projects", "publications", "profiles"):
        items = data.get(key)
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and not it.get("id"):
                    it["id"] = _s.token_hex(8)


# -----------------------------------------------------------------------------
#                                ATS scoring
# -----------------------------------------------------------------------------


_ATS_SYSTEM = (
    "You evaluate the quality half of a resume's ATS readiness. "
    "Output ONLY a JSON object — no markdown, no preface, no commentary. "
    "Use these exact snake_case keys (do NOT use camelCase): "
    "impact, action_verbs, clarity, semantic, suggestions. "
    "Each numeric field is an integer in 0..100. `suggestions` is an "
    "array of 3–5 specific, actionable strings. Example output:\n"
    "{\"impact\": 72, \"action_verbs\": 65, \"clarity\": 80, "
    "\"semantic\": 60, \"suggestions\": [\"Quantify the migration outcome.\", "
    "\"Lead bullets with verbs.\"]}"
)


def _normalize_keys(obj: Any) -> Any:
    """Lower-case + camelCase→snake_case keys, recursively.

    Models sometimes hand back ``{"actionVerbs": 65}`` even when the
    prompt asks for snake_case. Normalising once here saves us from
    sprinkling alternate-key checks at every call site.
    """
    import re

    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str):
                snake = re.sub(r"(?<!^)(?=[A-Z])", "_", k).lower()
                out[snake] = _normalize_keys(v)
            else:
                out[k] = _normalize_keys(v)
        return out
    if isinstance(obj, list):
        return [_normalize_keys(it) for it in obj]
    return obj


@router.post("/ats-rule")
async def ats_rule(body: ATSRequest) -> dict[str, Any]:
    """Rule-based ATS scoring. Pure computation, no AI provider call.

    Split from /ats-ai so the frontend can render the rule result
    immediately while the (slow) AI call is still in flight.
    """
    rule = ats_mod.score_resume(body.data, body.job_description)
    return {
        "rule_score": rule.score,
        "breakdown": rule.breakdown,
        "suggestions": rule.suggestions,
        "missing_keywords": rule.missing_keywords,
    }


@router.post("/ats-ai")
async def ats_ai(request: Request, body: ATSRequest) -> dict[str, Any]:
    """AI-quality scoring half. Runs the configured provider and
    returns the four signals plus AI-authored suggestions.

    Separate from /ats-rule so the two halves of an ATS score can be
    rendered independently — whichever returns first shows first.
    """
    if not body.use_ai:
        return {
            "ai_score": None,
            "ai": None,
            "ai_status": "off",
            "ai_suggestions": [],
        }

    user = await current_user(request)
    try:
        cfg = await _active_text_config(user)
    except HTTPException as err:
        return {
            "ai_score": None,
            "ai": None,
            "ai_status": "unconfigured",
            "ai_error": err.detail if isinstance(err.detail, str) else None,
            "ai_error_kind": "unconfigured",
            "ai_suggestions": [],
        }

    user_prompt = json.dumps(
        {"resume": body.data, "job_description": body.job_description or ""}
    )
    try:
        text = await _call_complete(
            cfg["kind"],
            cfg["model"],
            cfg["api_key"],
            cfg["base_url"] or None,
            system=_ATS_SYSTEM,
            messages=[{"role": "user", "content": user_prompt[:18000]}],
            max_tokens=1400,
        )
    except Exception as err:  # noqa: BLE001
        rid = _request_id()
        _log.exception("AI ATS scoring failed [rid=%s]", rid)
        kind_, msg = _friendly_error(err)
        return {
            "ai_score": None,
            "ai": None,
            "ai_status": "error",
            "ai_error": f"{msg} (request id: {rid})",
            "ai_error_kind": kind_,
            "ai_suggestions": [],
            "ai_request_id": rid,
        }

    ai_obj = _normalize_keys(_safe_json(text) or {})
    if not any(
        isinstance(ai_obj.get(k), (int, float))
        for k in ("impact", "action_verbs", "clarity", "semantic")
    ):
        _log.warning("ATS AI response had no usable scores: %r", text[:400])
    ai_avg = _avg(
        [
            ai_obj.get("impact"),
            ai_obj.get("action_verbs"),
            ai_obj.get("clarity"),
            ai_obj.get("semantic"),
        ]
    )

    suggestions: list[str] = []
    raw_sugg = ai_obj.get("suggestions") or []
    if isinstance(raw_sugg, list):
        for s in raw_sugg:
            if isinstance(s, str) and s.strip():
                suggestions.append(s)
    suggestions = suggestions[:6]

    return {
        "ai_score": round(ai_avg) if ai_avg is not None else None,
        "ai": {
            "impact": ai_obj.get("impact"),
            "action_verbs": ai_obj.get("action_verbs"),
            "clarity": ai_obj.get("clarity"),
            "semantic": ai_obj.get("semantic"),
        },
        "ai_status": "ok",
        "ai_suggestions": suggestions,
    }


def _avg(vals: list[Any]) -> float | None:
    nums = [float(v) for v in vals if isinstance(v, (int, float))]
    if not nums:
        return None
    return sum(nums) / len(nums)


# -----------------------------------------------------------------------------
#                          Project enhancement (GitHub)
# -----------------------------------------------------------------------------
#
# Multi-pass flow when the input includes `full_name` (i.e., the repo
# really exists on GitHub):
#
#   1. Discover markdown docs in the default branch via the GitHub
#      tree API (README.md, top-level *.md, then docs/**.md, capped).
#   2. Fetch each doc raw from raw.githubusercontent.com — that
#      endpoint is rate-limit-free unlike the contents API.
#   3. Run a per-doc summarizer LLM call (one session per doc, in
#      parallel) that extracts structured signals across niche,
#      achievements, intent, key ideas, vision, architectural
#      decisions, engineering highlights, audience, and novel
#      aspects.
#   4. Run a single aggregator LLM call that takes the structured
#      summaries plus repo metadata and produces the final resume
#      project entry: tagline + 2–3 impact bullets.
#
# When `full_name` is missing the endpoint falls back to a single
# pass over just the repo metadata. The output shape is identical so
# callers don't need to branch on which path ran.

GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"

# Caps to keep cost / latency / GitHub rate-limits in check.
_MAX_DOCS_PER_REPO = 10
_MAX_DOC_CHARS = 15_000


_DOC_SUMMARIZER_SYSTEM = (
    "You read a single markdown document from a software project's "
    "repository and extract structured signals for a resume "
    "writer. Output ONLY a JSON object with these keys: "
    "{ "
    "\"niche\": string, "
    "\"achievements\": [string, ...], "
    "\"intent\": string, "
    "\"key_ideas\": [string, ...], "
    "\"vision\": string, "
    "\"architecture\": [string, ...], "
    "\"engineering_highlights\": [string, ...], "
    "\"users\": string, "
    "\"novel_aspects\": [string, ...] "
    "}. Each string field is one tight sentence (or empty). Each "
    "array field is up to 5 short factual phrases pulled from the "
    "doc. Do NOT invent metrics, users, or facts the doc doesn't "
    "support. No markdown, no preamble — JSON only."
)


_PROJECT_AGGREGATOR_SYSTEM = (
    "You synthesize a polished resume project entry from multiple "
    "structured summaries of a project's documentation. Output "
    "ONLY a JSON object with shape: { \"description\": string, "
    "\"highlights\": [string, string, string] }. The description "
    "is one tight tagline (≤ 140 chars) capturing what the project "
    "is and why it's notable — read across the summaries to pick "
    "the most resonant framing. Highlights are 2–3 impact-focused "
    "bullets (≤ 180 chars each), drawn from achievements, "
    "engineering highlights, architectural decisions, and novel "
    "aspects. Prefer concrete details from the summaries over "
    "generic descriptions. Do NOT invent metrics, users, team "
    "sizes, or facts. No markdown, no preamble — JSON only."
)


def _split_full_name(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, str) or "/" not in value:
        return None
    owner, _, repo = value.partition("/")
    owner = owner.strip()
    repo = repo.strip()
    if not owner or not repo:
        return None
    return owner, repo


async def _gh_default_branch(
    client: httpx.AsyncClient, owner: str, repo: str
) -> str:
    try:
        r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}", timeout=10.0)
        if r.status_code == 200:
            return r.json().get("default_branch") or "main"
    except Exception:  # noqa: BLE001
        _log.debug("gh default branch lookup failed for %s/%s", owner, repo, exc_info=True)
    return "main"


async def _gh_list_markdown(
    client: httpx.AsyncClient, owner: str, repo: str, branch: str
) -> list[str]:
    try:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"},
            timeout=15.0,
        )
        if r.status_code != 200:
            return []
        tree = r.json().get("tree") or []
    except Exception:  # noqa: BLE001
        _log.debug("gh tree fetch failed for %s/%s@%s", owner, repo, branch, exc_info=True)
        return []

    paths: list[str] = []
    for entry in tree:
        if not isinstance(entry, dict) or entry.get("type") != "blob":
            continue
        path = entry.get("path") or ""
        if not isinstance(path, str):
            continue
        lower = path.lower()
        if not (lower.endswith(".md") or lower.endswith(".mdx")):
            continue
        # Skip vendored / generated docs that mostly add noise.
        if any(seg in lower for seg in ("node_modules/", "vendor/", ".github/")):
            continue
        paths.append(path)

    # Score by likely importance — README first, then top-level .md,
    # then docs/, then everything else.
    def score(p: str) -> tuple[int, str]:
        lp = p.lower()
        if lp == "readme.md":
            return (0, lp)
        if "/" not in lp:
            return (1, lp)
        if lp.startswith("docs/"):
            return (2, lp)
        return (3, lp)

    paths.sort(key=score)
    return paths[:_MAX_DOCS_PER_REPO]


async def _gh_fetch_raw(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    branch: str,
    path: str,
) -> str | None:
    try:
        r = await client.get(
            f"{GITHUB_RAW}/{owner}/{repo}/{branch}/{path}", timeout=15.0
        )
        if r.status_code == 200:
            text = r.text or ""
            return text[:_MAX_DOC_CHARS] if text else None
    except Exception:  # noqa: BLE001
        _log.debug("gh raw fetch failed for %s/%s/%s", owner, repo, path, exc_info=True)
    return None


async def _summarize_doc(
    cfg: dict[str, Any], path: str, content: str
) -> dict[str, Any] | None:
    user_prompt = f"Document path: {path}\n\nContent:\n{content}"
    try:
        text = await _call_complete(
            cfg["kind"],
            cfg["model"],
            cfg["api_key"],
            cfg["base_url"] or None,
            system=_DOC_SUMMARIZER_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=900,
        )
    except Exception:  # noqa: BLE001
        _log.exception("doc summarizer failed for %s", path)
        return None
    parsed = _safe_json(text)
    if not isinstance(parsed, dict):
        return None
    parsed["doc_path"] = path
    return parsed


async def _aggregate_project(
    cfg: dict[str, Any],
    repo_meta: dict[str, Any],
    summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    user_prompt = json.dumps({"repo": repo_meta, "doc_summaries": summaries})
    try:
        text = await _call_complete(
            cfg["kind"],
            cfg["model"],
            cfg["api_key"],
            cfg["base_url"] or None,
            system=_PROJECT_AGGREGATOR_SYSTEM,
            messages=[{"role": "user", "content": user_prompt[:30000]}],
            max_tokens=900,
        )
    except Exception:  # noqa: BLE001
        _log.exception("project aggregator failed")
        return {"description": "", "highlights": []}
    parsed = _safe_json(text)
    if not isinstance(parsed, dict):
        return {"description": "", "highlights": []}
    desc = str(parsed.get("description") or "").strip()
    raw_h = parsed.get("highlights") or []
    highlights: list[str] = []
    if isinstance(raw_h, list):
        for h in raw_h:
            if isinstance(h, str) and h.strip():
                highlights.append(h.strip())
    return {"description": desc, "highlights": highlights[:6]}


async def _enhance_one(
    client: httpx.AsyncClient,
    cfg: dict[str, Any],
    repo_in: dict[str, Any],
) -> dict[str, Any]:
    full = _split_full_name(repo_in.get("full_name"))
    summaries: list[dict[str, Any]] = []
    if full is not None:
        owner, repo = full
        branch = await _gh_default_branch(client, owner, repo)
        paths = await _gh_list_markdown(client, owner, repo, branch)
        contents = await asyncio.gather(
            *(
                _gh_fetch_raw(client, owner, repo, branch, p)
                for p in paths
            ),
            return_exceptions=False,
        )
        # Per-doc summarization in parallel — separate sessions so
        # each doc gets its own focused extraction.
        per_doc = await asyncio.gather(
            *(
                _summarize_doc(cfg, p, c)
                for p, c in zip(paths, contents)
                if isinstance(c, str) and c.strip()
            ),
            return_exceptions=False,
        )
        summaries = [s for s in per_doc if isinstance(s, dict)]
    return await _aggregate_project(cfg, repo_in, summaries)


@router.post("/enhance-projects")
async def enhance_projects(
    request: Request, body: EnhanceProjectsRequest
) -> dict[str, Any]:
    """Multi-stage AI enhancement for GitHub projects.

    For each repo with a `full_name` we:
      - discover markdown docs in the default branch,
      - summarize each doc in its own LLM session (parallel),
      - aggregate the per-doc summaries into a polished tagline +
        2–3 impact bullets in a final LLM session.

    Repos without a full_name fall through to the single-pass
    aggregator over just the metadata. Used by the GitHub Import
    dialog when the user opts in to AI Enhancement.
    """
    if not body.projects:
        return {"projects": []}
    user = await current_user(request)
    cfg = await _active_text_config(user)

    timeout = httpx.Timeout(20.0, read=20.0, connect=10.0)
    headers = {
        "User-Agent": "rounds-resume-studio",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        results = await asyncio.gather(
            *(_enhance_one(client, cfg, r) for r in body.projects),
            return_exceptions=False,
        )
    return {"projects": results}
