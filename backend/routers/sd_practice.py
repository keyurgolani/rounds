"""System-design practice chat endpoint with canvas tool-calling.

Mirrors the shape of /api/ai-coding/chat but adds Anthropic tool-use
support so the model can mutate the candidate's diagram (add
components / connections / labels) rather than just emitting prose.
The frontend executes each tool_use against an Excalidraw or tldraw
scene driver.

The system prompt frames the AI as a sparring partner, not the
architect — it asks questions, proposes options, narrates intent
before mutating, and never makes a decision the candidate hasn't
validated. This matches Meta's stated philosophy for AI-Enabled
rounds ("don't prompt your way out of it").
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from app.crypto import decrypt
from app.pb_auth import current_user
from routers.ai import (
    _ANTHROPIC_DEFAULT_BASE,
    _active_text_config,
    _friendly_error,
    _load_provider,
    _request_id,
)

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sd-practice", tags=["sd-practice"])


async def _auth_user(request: Request) -> dict:
    return await current_user(request)


# ─────────────────────────────────────────────────────────────────────────────
# Request shape
# ─────────────────────────────────────────────────────────────────────────────


class SDChatMessage(BaseModel):
    role: str  # 'user' | 'assistant' | 'tool_result'
    content: Any  # str for user/assistant; for tool_result use the structured form


class CanvasElement(BaseModel):
    id: str
    kind: str  # 'component' | 'connection' | 'note'
    label: Optional[str] = None
    component_kind: Optional[str] = None  # 'service' | 'db' | ... when kind=='component'
    from_id: Optional[str] = None  # for connections
    to_id: Optional[str] = None  # for connections
    position: Optional[Dict[str, float]] = None  # {x, y}


class SDChatRequest(BaseModel):
    question_slug: str = Field(pattern=r"^[a-z0-9-]+$")
    question_prompt: str | None = None  # the original SD question text
    canvas_elements: List[CanvasElement] = Field(default_factory=list)
    messages: List[SDChatMessage]
    provider_id: str | None = None
    model: str | None = None

    @model_validator(mode="after")
    def _override_must_be_paired(self) -> "SDChatRequest":
        if (self.provider_id is None) != (self.model is None):
            raise ValueError(
                "provider_id and model must both be supplied or both omitted."
            )
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Canvas tools the AI can call
# ─────────────────────────────────────────────────────────────────────────────


_COMPONENT_KINDS = [
    "service",
    "db",
    "queue",
    "cache",
    "cdn",
    "client",
    "lb",
    "external",
]


CANVAS_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "add_component",
        "description": (
            "Add a component box to the canvas. Use this when the candidate "
            "agrees to a component you've proposed, OR when you're laying out "
            "the candidate's stated architecture for them. Always narrate "
            "what you're adding and why BEFORE calling this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {
                    "type": "string",
                    "description": "Short human-readable label (e.g. 'API Gateway', 'Postgres', 'Redis cache').",
                },
                "kind": {
                    "type": "string",
                    "enum": _COMPONENT_KINDS,
                    "description": (
                        "Visual category. 'service' for application services, 'db' for "
                        "any datastore, 'queue' for message brokers, 'cache' for caches, "
                        "'cdn' for edge / CDN, 'client' for end-user or browser, 'lb' "
                        "for load balancers, 'external' for third-party services."
                    ),
                },
                "position": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                    },
                    "description": (
                        "Optional canvas coordinates. Omit to let the driver auto-place."
                    ),
                },
            },
            "required": ["label", "kind"],
        },
    },
    {
        "name": "add_connection",
        "description": (
            "Connect two existing components with an arrow. Use the IDs "
            "returned by previous add_component calls (or read_canvas)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_id": {"type": "string"},
                "to_id": {"type": "string"},
                "label": {
                    "type": "string",
                    "description": "Optional edge label (e.g. 'writes', 'reads via SQL').",
                },
                "direction": {
                    "type": "string",
                    "enum": ["one-way", "two-way"],
                    "description": "Default 'one-way'.",
                },
            },
            "required": ["from_id", "to_id"],
        },
    },
    {
        "name": "update_component",
        "description": "Rename or recategorise an existing component.",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "label": {"type": "string"},
                "kind": {"type": "string", "enum": _COMPONENT_KINDS},
            },
            "required": ["id"],
        },
    },
    {
        "name": "delete_element",
        "description": (
            "Delete a component or connection. Always confirm with the "
            "candidate before deleting unless they explicitly asked for the "
            "removal."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "add_note",
        "description": (
            "Add a free-floating text annotation (a sticky-style note) "
            "anchored to a canvas position. Use for capacity numbers, "
            "constraint notes, or callouts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "position": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                    },
                    "required": ["x", "y"],
                },
            },
            "required": ["text", "position"],
        },
    },
    {
        "name": "read_canvas",
        "description": (
            "Return a structured summary of the current canvas. Use this "
            "before proposing changes if you need to confirm what's already "
            "there."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


_SD_PRACTICE_SYSTEM = """You are a system-design interview SPARRING PARTNER, not the architect.

Your job is to help the candidate practice. You can draw on a shared canvas via the provided tools, but the candidate owns the design decisions. Be conversational, probing, and honest about uncertainty.

# Stance

- Ask before drawing. If the candidate says "let me think about how to handle hot keys" — wait. If they ask "what would you add here?" — propose, explain trade-offs, and only mutate the canvas when they say go.
- Challenge, don't agree. When the candidate proposes something, ask "what's the scale assumption?" / "what about p99?" / "what happens during a partition?" / "where does this break first?". Push them to defend choices.
- Narrate before mutating. Before calling add_component or add_connection, say out loud what you're adding and why. The candidate must be able to follow.
- Never decide. If asked "should I use Cassandra or DynamoDB?" — give the trade-off, ask what they think, let them choose. You can advocate, but the call is theirs.
- Use note annotations for capacity math, p99 budgets, RPS estimates — but only when the candidate has agreed on the number.

# Tools

You have six tools: add_component, add_connection, update_component, delete_element, add_note, read_canvas. Use them sparingly. A good 45-minute round might have 8–15 tool calls total — not 40. Most of your value is conversational.

# What to grade against (Meta's signal areas)

- Problem Navigation — does the candidate clarify before designing?
- Solution Design — is the architecture coherent, sized, and justified?
- Technical Excellence — depth on a chosen subsystem (deep-dive on one component)
- Technical Communication — narration, naming, trade-off articulation
- AI Judgment (implicit) — does the candidate validate your suggestions, push back, or rubber-stamp?

After the candidate makes a substantive choice, briefly reflect what you observed. ("That's a clean separation of read and write paths — nice. One thing I'd push on: did you decide the cache invalidation story?")

# Boundaries

- You see the canvas state in every turn — use it. If something already exists, don't duplicate.
- If the candidate asks you to "design the whole thing" — politely refuse and ask them to start somewhere. They're the architect.
- If the candidate asks for a specific scale number you don't know, say so honestly.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Streaming with tool support
# ─────────────────────────────────────────────────────────────────────────────


async def _resolve_text_cfg(
    user: dict, provider_id: str | None, model: str | None
) -> dict:
    if provider_id and model:
        provider = await _load_provider(user, provider_id)
        api_key = decrypt(
            provider.get("encrypted_key") or "", provider.get("key_iv") or ""
        )
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="No API key on file for the chosen provider.",
            )
        return {
            "kind": provider.get("kind") or "provider",
            "model": model,
            "api_key": api_key,
            "base_url": provider.get("base_url") or "",
        }
    return await _active_text_config(user)


def _format_canvas_for_prompt(elements: List[CanvasElement]) -> str:
    if not elements:
        return "(canvas is empty)"
    lines = []
    for el in elements:
        if el.kind == "component":
            lines.append(
                f"- [{el.id}] component ({el.component_kind}): {el.label}"
            )
        elif el.kind == "connection":
            lines.append(
                f"- [{el.id}] connection: {el.from_id} → {el.to_id}"
                + (f" — {el.label}" if el.label else "")
            )
        elif el.kind == "note":
            lines.append(f"- [{el.id}] note: {el.label}")
    return "\n".join(lines)


async def _anthropic_stream_with_tools(
    model: str,
    api_key: str,
    base_url: str | None,
    system: str,
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    max_tokens: int = 1600,
) -> AsyncIterator[Dict[str, Any]]:
    """Streams Anthropic responses, surfacing both text deltas and
    tool_use blocks. Each yielded dict has a `type` field the SSE
    layer can serialise.
    """
    base = (base_url or _ANTHROPIC_DEFAULT_BASE).rstrip("/")
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
        "tools": tools,
        "stream": True,
    }
    # Track the currently-open content block so we can correlate
    # input_json_delta events back to the tool_use that started them.
    current_block: Dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=180) as client:
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
                err_text = (await resp.aread()).decode("utf-8", errors="replace")
                raise httpx.HTTPStatusError(
                    f"Error code: {resp.status_code} - {err_text}",
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
                etype = obj.get("type")
                if etype == "content_block_start":
                    block = obj.get("content_block") or {}
                    if block.get("type") == "tool_use":
                        current_block = {
                            "index": obj.get("index"),
                            "id": block.get("id"),
                            "name": block.get("name"),
                        }
                        yield {
                            "type": "tool_use_start",
                            "id": block.get("id"),
                            "name": block.get("name"),
                        }
                    else:
                        current_block = {"index": obj.get("index"), "type": "text"}
                elif etype == "content_block_delta":
                    delta = obj.get("delta") or {}
                    if delta.get("type") == "text_delta":
                        text = delta.get("text") or ""
                        if text:
                            yield {"type": "text_delta", "text": text}
                    elif delta.get("type") == "input_json_delta":
                        chunk = delta.get("partial_json") or ""
                        if chunk and current_block.get("id"):
                            yield {
                                "type": "tool_use_delta",
                                "id": current_block["id"],
                                "partial_json": chunk,
                            }
                elif etype == "content_block_stop":
                    if current_block.get("id"):
                        yield {
                            "type": "tool_use_stop",
                            "id": current_block["id"],
                        }
                    current_block = {}
                elif etype == "message_stop":
                    yield {"type": "done"}


@router.post("/chat")
async def chat(
    body: SDChatRequest, user: dict = Depends(_auth_user)
) -> StreamingResponse:
    cfg = await _resolve_text_cfg(user, body.provider_id, body.model)
    if cfg["kind"] not in ("anthropic", "anthropic-compatible"):
        raise HTTPException(
            status_code=400,
            detail=(
                "SD practice chat currently requires an Anthropic-compatible "
                "provider with tool-use support."
            ),
        )

    system = _SD_PRACTICE_SYSTEM
    if body.question_prompt:
        system += "\n\n# Question the candidate is working\n\n" + body.question_prompt
    system += "\n\n# Current canvas state\n\n" + _format_canvas_for_prompt(
        body.canvas_elements
    )

    # Convert messages to Anthropic format. Tool results come back as
    # role='user' with a structured content array — the frontend
    # packages them that way.
    out_messages: List[Dict[str, Any]] = []
    for m in body.messages:
        out_messages.append({"role": m.role, "content": m.content})

    async def gen() -> AsyncIterator[bytes]:
        try:
            async for evt in _anthropic_stream_with_tools(
                cfg["model"],
                cfg["api_key"],
                cfg["base_url"] or None,
                system=system,
                messages=out_messages,
                tools=CANVAS_TOOLS,
            ):
                yield f"data: {json.dumps(evt)}\n\n".encode("utf-8")
            yield b"data: {\"type\": \"end\"}\n\n"
        except Exception as err:  # noqa: BLE001
            rid = _request_id()
            _log.exception("sd-practice chat stream failed [rid=%s]", rid)
            kind_, msg = _friendly_error(err)
            yield (
                f"data: {json.dumps({'type': 'error', 'message': msg, 'error_kind': kind_, 'request_id': rid})}\n\n"
            ).encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")
