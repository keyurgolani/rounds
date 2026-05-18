"""System-design practice chat endpoint with canvas tool-calling.

Mirrors the shape of /api/ai-coding/chat but adds tool-use support
so the model can mutate the candidate's diagram (add components /
connections / labels) rather than just emitting prose. The frontend
executes each tool_use against an Excalidraw scene driver.

Both provider families are supported:
  * Anthropic / Anthropic-compatible → /v1/messages with tools=[...]
  * OpenAI / OpenAI-compatible       → /v1/chat/completions with
    tools=[{type:"function", function:{...}}]

The wire protocol the frontend speaks is Anthropic-shaped (text +
tool_use + tool_result blocks). For OpenAI providers we convert
on the way in and translate streaming tool_calls back into the same
SSE event types (tool_use_start/delta/stop) so the chat panel
doesn't need to branch.

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


_TOOL_DEFS: List[Dict[str, Any]] = [
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
        "name": "draw_diagram",
        "description": (
            "BATCH lay-out — place multiple components, connections, and "
            "notes in one call. STRONGLY PREFER this over many granular "
            "add_component/add_connection calls when the candidate has "
            "asked you to draw more than 2 boxes (or any time you're in "
            "direct mode laying out a full system).\n\n"
            "Why this exists: the granular tools require you to predict "
            "what the driver will assign as ids, which means connections "
            "have to come in a follow-up turn. With draw_diagram you "
            "supply your OWN short ids (e.g. 'lb', 'gateway', 'chat') "
            "and reference them in the connections[] array in the SAME "
            "call. Boxes and arrows land together; no orphaned "
            "components and no missed connections.\n\n"
            "Layout responsibility: YOU decide the (x, y) for every "
            "component. Cluster related boxes; leave room for arrows. "
            "Recommended grid: 200–300 px between sibling boxes "
            "horizontally, 130–180 px vertically. Start the diagram "
            "around (80, 80). Place notes ABOVE the grid (y < 60) for "
            "titles or BELOW (y > grid_height + 120) for capacity math; "
            "never at (0, 0) over the first row."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "components": {
                    "type": "array",
                    "description": "Components to place. Each needs an ai-chosen `id` (short, used only within this call to reference from connections), a `label`, a `kind`, and an explicit `position`.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Short ai-chosen id (e.g. 'lb', 'gateway', 'chat-svc'). Used to reference this component in connections within this same call. The driver returns the real id in the tool_result.",
                            },
                            "label": {"type": "string"},
                            "kind": {"type": "string", "enum": _COMPONENT_KINDS},
                            "position": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number"},
                                    "y": {"type": "number"},
                                },
                                "required": ["x", "y"],
                            },
                        },
                        "required": ["id", "label", "kind", "position"],
                    },
                },
                "connections": {
                    "type": "array",
                    "description": "Connections to draw. `from_id` and `to_id` reference the ai-chosen ids in components[] from this call — OR existing canvas ids when extending a diagram you already drew.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from_id": {"type": "string"},
                            "to_id": {"type": "string"},
                            "label": {"type": "string"},
                        },
                        "required": ["from_id", "to_id"],
                    },
                },
                "notes": {
                    "type": "array",
                    "description": "Optional free-floating annotations placed at absolute coordinates.",
                    "items": {
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
            },
            "required": ["components"],
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


# Anthropic-style tool list — the API takes input_schema directly.
ANTHROPIC_CANVAS_TOOLS: List[Dict[str, Any]] = _TOOL_DEFS


# OpenAI function-calling shape — the same six tools wrapped in the
# {type:"function", function:{name, description, parameters}} envelope.
OPENAI_CANVAS_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    }
    for t in _TOOL_DEFS
]


# Backwards-compatibility alias for callers/tests that import the old name.
CANVAS_TOOLS = ANTHROPIC_CANVAS_TOOLS


_SD_PRACTICE_SYSTEM = """You are a system-design interview SPARRING PARTNER, not the architect.

Your default mode is conversational. You can draw on a shared canvas via the provided tools, but the candidate owns the design decisions.

# Two modes — read the candidate's intent

DEFAULT (sparring) mode — when the candidate is reasoning through the design:
- Ask before drawing. If the candidate says "let me think about hot keys" — wait. If they ask "what would you add here?" — propose, explain trade-offs, and only mutate the canvas when they say go.
- Challenge, don't agree. Ask "what's the scale assumption?" / "what about p99?" / "what happens during a partition?". Push them to defend choices.
- Never decide for them. Give trade-offs; let the candidate pick.

DIRECT (just-draw-it) mode — when the candidate explicitly directs you to place things:
Phrases that put you in this mode: "just draw it", "put it on the canvas", "skip the questions", "bypass the due diligence", "I'm testing the canvas", "lay it all out", "add these components", "I'm the developer testing this feature", or any variant where the candidate is clearly directing rather than reasoning.
- Do it. Drop the Socratic checklist. Issue the tool calls back-to-back without narrating each one. Brief one-line confirmation is fine; a paragraph of due diligence is not.
- Batch tool calls aggressively. Anthropic supports many tool calls per assistant turn — use that. For an N-component diagram, issue all N add_component calls plus the connections in a single response.
- Don't ask "does this look right?" before drawing. Draw, then offer to refine.

If the candidate switches modes mid-conversation ("ok now let's actually think about this"), switch with them.

# Tool-use playbook

You have seven tools:
- **draw_diagram** — BATCH. Lay out N components, their connections, and notes in ONE call. Strongly prefer this whenever you're drawing more than 2 boxes.
- add_component / add_connection / add_note — granular. Use for incremental edits to an existing diagram.
- update_component, delete_element — edit/remove existing items by id.
- read_canvas — read current state (already provided in the system prompt every turn; only call when you need it inline).

**Plan the whole picture before any tool call.** Whenever you're about to draw:
1. Enumerate every component you'll need.
2. Enumerate every connection that exists between them.
3. Place them on a mental grid with enough room for arrows to route between boxes WITHOUT crossing unrelated ones.
4. Then issue ONE draw_diagram call with components[], connections[], and notes[] all included.

Forgetting connections is a common failure — when you draw the boxes, draw the arrows in the SAME call. The candidate should never have to ask "did we miss the connections?"

**Component dimensions** (for layout math): each box renders at roughly 200 wide × 84 tall.

**Spacing rules**:
- Sibling boxes in a horizontal row: leave **≥ 240 px** between their (x) positions (so 40+px of arrow space sits between adjacent boxes).
- Rows of boxes: leave **≥ 180 px** between their (y) positions.
- Tightly-coupled boxes (e.g. a service and its DB): may be closer — 220 px horizontal works.
- Loosely-related boxes: push them farther apart so arrows don't run through neighbors.
- Long labels (3+ words) — give them even more horizontal room, ~280 px between centers.

**Note placement**: notes are absolute-coordinate text. Place TITLE notes ABOVE the grid (y < 60). Place capacity/RPS/p99 callouts BELOW the grid (y > total_grid_height + 120). NEVER drop a note at (0, 0) — it overlaps the first row of components.

**Reuse, don't duplicate**: every turn the canvas state is in the prompt below. If a component already exists, use its existing id when adding connections — don't add a duplicate.

# What to grade against (Meta's signal areas)

- Problem Navigation — does the candidate clarify before designing?
- Solution Design — is the architecture coherent, sized, and justified?
- Technical Excellence — depth on a chosen subsystem
- Technical Communication — narration, naming, trade-off articulation
- AI Judgment (implicit) — does the candidate validate your suggestions, push back, or rubber-stamp?

After a substantive choice in sparring mode, briefly reflect what you observed. Skip this in direct mode.

# Boundaries

- You see the canvas state in every turn — use it. Don't duplicate existing components.
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


def _messages_anthropic_to_openai(
    messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert the Anthropic-shaped wire messages the frontend sends
    into OpenAI chat-completions format.

    The frontend always speaks Anthropic shapes:
      - user.content: str | [tool_result, ...]
      - assistant.content: [text|tool_use, ...]

    OpenAI's chat API instead wants:
      - user/assistant.content: str (plus optional tool_calls on assistant)
      - tool results as separate {role:"tool", tool_call_id, content} entries
    """
    out: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue
        if not isinstance(content, list):
            continue
        if role == "assistant":
            text_parts: List[str] = []
            tool_calls: List[Dict[str, Any]] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    text_parts.append(block.get("text") or "")
                elif btype == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.get("id") or "",
                            "type": "function",
                            "function": {
                                "name": block.get("name") or "",
                                "arguments": json.dumps(block.get("input") or {}),
                            },
                        }
                    )
            msg: Dict[str, Any] = {
                "role": "assistant",
                "content": "".join(text_parts) or None,
            }
            if tool_calls:
                msg["tool_calls"] = tool_calls
            out.append(msg)
        elif role == "user":
            # The array form on user turns is tool_result blocks; emit
            # each as its own {role:"tool"} entry. Any stray text block
            # becomes a separate plain user message so it isn't lost.
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "tool_result":
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id") or "",
                            "content": block.get("content") or "",
                        }
                    )
                elif btype == "text":
                    out.append(
                        {"role": "user", "content": block.get("text") or ""}
                    )
    return out


async def _openai_stream_with_tools(
    model: str,
    api_key: str,
    base_url: str | None,
    system: str,
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    max_tokens: int = 1600,
) -> AsyncIterator[Dict[str, Any]]:
    """OpenAI-style streaming with function-calling support.

    Yields the same event vocabulary as ``_anthropic_stream_with_tools``
    (text_delta / tool_use_start / tool_use_delta / tool_use_stop /
    done) so the SSE layer and the frontend don't need to branch.

    OpenAI only sends a tool_call's id and function.name in the first
    chunk per ``index`` — we track index→id ourselves and synthesise
    a ``tool_use_stop`` for every open call when ``finish_reason``
    fires.
    """
    from openai import AsyncOpenAI

    kwargs: Dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = AsyncOpenAI(**kwargs)
    chat = [{"role": "system", "content": system}] + messages

    index_to_id: Dict[int, str] = {}
    started: set[int] = set()

    stream = await client.chat.completions.create(
        model=model,
        messages=chat,
        tools=tools,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        delta = choice.delta
        if delta is None:
            continue
        text_part = getattr(delta, "content", None)
        if text_part:
            yield {"type": "text_delta", "text": text_part}
        tcs = getattr(delta, "tool_calls", None) or []
        for tc in tcs:
            idx = getattr(tc, "index", 0) or 0
            fn = getattr(tc, "function", None)
            if idx not in started:
                tc_id = getattr(tc, "id", None) or f"call_{idx}"
                name = (getattr(fn, "name", None) if fn else None) or ""
                index_to_id[idx] = tc_id
                started.add(idx)
                yield {
                    "type": "tool_use_start",
                    "id": tc_id,
                    "name": name,
                }
            args = getattr(fn, "arguments", None) if fn else None
            if args:
                yield {
                    "type": "tool_use_delta",
                    "id": index_to_id[idx],
                    "partial_json": args,
                }
        if choice.finish_reason:
            for tc_id in index_to_id.values():
                yield {"type": "tool_use_stop", "id": tc_id}
            yield {"type": "done"}
            return


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
    kind = cfg["kind"]

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
            if kind in ("anthropic", "anthropic-compatible"):
                stream_iter = _anthropic_stream_with_tools(
                    cfg["model"],
                    cfg["api_key"],
                    cfg["base_url"] or None,
                    system=system,
                    messages=out_messages,
                    tools=ANTHROPIC_CANVAS_TOOLS,
                )
            else:
                # OpenAI / OpenAI-compatible. Convert the Anthropic-shaped
                # history to OpenAI chat format. The OpenAI tools schema
                # carries the same six canvas tools.
                oa_messages = _messages_anthropic_to_openai(out_messages)
                stream_iter = _openai_stream_with_tools(
                    cfg["model"],
                    cfg["api_key"],
                    cfg["base_url"] or None,
                    system=system,
                    messages=oa_messages,
                    tools=OPENAI_CANVAS_TOOLS,
                )
            async for evt in stream_iter:
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
