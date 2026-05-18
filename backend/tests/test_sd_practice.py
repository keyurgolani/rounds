"""Unit tests for the system-design practice chat helpers.

These cover pure conversion logic — no provider calls. The SSE
endpoint itself is exercised indirectly via the frontend.
"""
from __future__ import annotations

import json

from routers.sd_practice import (
    ANTHROPIC_CANVAS_TOOLS,
    OPENAI_CANVAS_TOOLS,
    _messages_anthropic_to_openai,
)


def test_openai_tool_envelope_matches_anthropic_definitions() -> None:
    """The OpenAI tool list must carry the same six canvas tools, in
    the {type, function:{name, description, parameters}} shape."""
    assert len(OPENAI_CANVAS_TOOLS) == len(ANTHROPIC_CANVAS_TOOLS)
    by_name = {t["function"]["name"]: t for t in OPENAI_CANVAS_TOOLS}
    for src in ANTHROPIC_CANVAS_TOOLS:
        wrapped = by_name[src["name"]]
        assert wrapped["type"] == "function"
        assert wrapped["function"]["description"] == src["description"]
        # The OpenAI envelope reuses the JSON schema verbatim.
        assert wrapped["function"]["parameters"] == src["input_schema"]


def test_converter_handles_plain_string_turn() -> None:
    out = _messages_anthropic_to_openai(
        [{"role": "user", "content": "hello"}]
    )
    assert out == [{"role": "user", "content": "hello"}]


def test_converter_collapses_assistant_text_and_tool_use() -> None:
    out = _messages_anthropic_to_openai(
        [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Adding an API gateway."},
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "add_component",
                        "input": {"label": "API Gateway", "kind": "lb"},
                    },
                ],
            }
        ]
    )
    assert len(out) == 1
    msg = out[0]
    assert msg["role"] == "assistant"
    assert msg["content"] == "Adding an API gateway."
    assert len(msg["tool_calls"]) == 1
    tc = msg["tool_calls"][0]
    assert tc["id"] == "toolu_1"
    assert tc["type"] == "function"
    assert tc["function"]["name"] == "add_component"
    # arguments comes through as a JSON string (OpenAI's wire format)
    assert json.loads(tc["function"]["arguments"]) == {
        "label": "API Gateway",
        "kind": "lb",
    }


def test_converter_expands_tool_results_into_role_tool_entries() -> None:
    out = _messages_anthropic_to_openai(
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_1",
                        "content": '{"id":"c1","kind":"component"}',
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_2",
                        "content": "error: not found",
                        "is_error": True,
                    },
                ],
            }
        ]
    )
    assert out == [
        {
            "role": "tool",
            "tool_call_id": "toolu_1",
            "content": '{"id":"c1","kind":"component"}',
        },
        {
            "role": "tool",
            "tool_call_id": "toolu_2",
            "content": "error: not found",
        },
    ]


def test_converter_emits_assistant_content_none_when_only_tool_use() -> None:
    """OpenAI tolerates content=None on assistant messages that only
    carry tool_calls; we should NOT fabricate an empty string."""
    out = _messages_anthropic_to_openai(
        [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "read_canvas",
                        "input": {},
                    }
                ],
            }
        ]
    )
    assert out[0]["content"] is None
    assert out[0]["tool_calls"][0]["function"]["name"] == "read_canvas"


def test_converter_round_trip_realistic_turn() -> None:
    """A user turn → assistant turn with tool_use → user turn with
    tool_result → user follow-up: the order must be preserved and
    each block placed in the correct OpenAI role."""
    messages = [
        {"role": "user", "content": "Let's design a URL shortener."},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Starting with the write path."},
                {
                    "type": "tool_use",
                    "id": "toolu_A",
                    "name": "add_component",
                    "input": {"label": "Shortener API", "kind": "service"},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_A",
                    "content": '{"id":"c1"}',
                }
            ],
        },
        {"role": "user", "content": "Now add the datastore."},
    ]
    out = _messages_anthropic_to_openai(messages)
    roles = [m["role"] for m in out]
    assert roles == ["user", "assistant", "tool", "user"]
    assert out[3]["content"] == "Now add the datastore."
    assert out[2]["tool_call_id"] == "toolu_A"
