import json
from unittest.mock import patch

from ai_coding.edit_mode import parse_patches, EDIT_SYSTEM_PROMPT


def test_parses_well_formed_patch_array():
    raw = """
    [
      {"file": "cart.py", "patch_kind": "replace", "contents": "x = 1"},
      {"file": "tests/x.py", "patch_kind": "replace", "contents": "assert True"}
    ]
    """
    patches, err = parse_patches(raw)
    assert err is None
    assert len(patches) == 2
    assert patches[0]["file"] == "cart.py"
    assert patches[1]["contents"] == "assert True"


def test_parses_array_inside_fenced_code_block():
    raw = "Sure! Here are the changes:\n```json\n[{\"file\":\"a.py\",\"patch_kind\":\"replace\",\"contents\":\"pass\"}]\n```\nDone."
    patches, err = parse_patches(raw)
    assert err is None
    assert patches == [{"file": "a.py", "patch_kind": "replace", "contents": "pass"}]


def test_drops_unknown_patch_kinds():
    raw = '[{"file":"a.py","patch_kind":"diff","contents":"@@"},{"file":"b.py","patch_kind":"replace","contents":"y = 2"}]'
    patches, err = parse_patches(raw)
    assert err is None
    assert patches == [{"file": "b.py", "patch_kind": "replace", "contents": "y = 2"}]


def test_returns_error_on_unparseable():
    raw = "Sorry, I can't help with that."
    patches, err = parse_patches(raw)
    assert patches == []
    assert err is not None
    assert "JSON" in err or "parse" in err.lower()


def test_system_prompt_mentions_required_schema():
    assert "patch_kind" in EDIT_SYSTEM_PROMPT
    assert "replace" in EDIT_SYSTEM_PROMPT


def test_returns_error_when_array_has_items_but_none_validate():
    """All entries have unsupported patch_kind — distinct from
    a deliberate empty array."""
    raw = '[{"file":"a.py","patch_kind":"diff","contents":"@@"},{"file":"b.py","patch_kind":"unknown","contents":"x"}]'
    patches, err = parse_patches(raw)
    assert patches == []
    assert err is not None
    assert "patch_kind" in err.lower() or "unsupported" in err.lower() or "valid" in err.lower()


def test_empty_array_is_a_deliberate_signal_not_an_error():
    """The prompt explicitly tells the model to emit [] when it would
    rather discuss before coding. That MUST NOT be treated as an
    error — the UI uses it to nudge the user back to Ask mode."""
    patches, err = parse_patches("[]")
    assert patches == []
    assert err is None


def test_edit_route_streams_then_emits_parsed_patches(client):
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {"items": [{"checkpoints": [{"label": "cp", "ai_allowed": True}]}]}

    async def fake_cfg(*_args, **_kwargs):
        return {"kind": "openai", "model": "m", "api_key": "k", "base_url": ""}

    async def fake_call_stream(*args, **kwargs):
        for chunk in ['[{"file":"a.py",', '"patch_kind":"replace",', '"contents":"x = 1"}]']:
            yield chunk

    with patch("routers.ai_coding.current_user", fake_user), \
         patch("routers.ai_coding.pb_get", fake_pb_get), \
         patch("routers.ai_coding._resolve_text_cfg", fake_cfg), \
         patch("routers.ai_coding._call_stream", fake_call_stream):
        res = client.post("/api/ai-coding/edit", json={
            "round_slug": "any",
            "checkpoint_index": 0,
            "messages": [{"role": "user", "content": "fix the bug"}],
            "files": {"a.py": "x = 0"},
        })
    assert res.status_code == 200
    body = res.text
    # The stream must contain delta events (raw chunks) AND a final
    # `patches` event with the parsed array.
    assert '"delta":' in body
    assert '"patches":' in body
    # Find the patches event line.
    patches_line = next(l for l in body.splitlines() if l.startswith('data:') and '"patches"' in l)
    obj = json.loads(patches_line[len('data:'):].strip())
    assert obj["patches"] == [{"file": "a.py", "patch_kind": "replace", "contents": "x = 1"}]


def test_edit_route_emits_events_in_order_deltas_then_patches_then_done(client):
    """Contract: every successful response must have all delta events
    BEFORE the single patches event, and patches BEFORE done. A
    regression that emits patches before deltas would still pass the
    happy-path test, so guard the order explicitly."""
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {"items": [{"checkpoints": [{"label": "cp", "ai_allowed": True}]}]}

    async def fake_cfg(*_args, **_kwargs):
        return {"kind": "openai", "model": "m", "api_key": "k", "base_url": ""}

    async def fake_call_stream(*args, **kwargs):
        for chunk in ['[{"file":"a.py",', '"patch_kind":"replace","contents":"x"}]']:
            yield chunk

    with patch("routers.ai_coding.current_user", fake_user), \
         patch("routers.ai_coding.pb_get", fake_pb_get), \
         patch("routers.ai_coding._resolve_text_cfg", fake_cfg), \
         patch("routers.ai_coding._call_stream", fake_call_stream):
        res = client.post("/api/ai-coding/edit", json={
            "round_slug": "any",
            "checkpoint_index": 0,
            "messages": [{"role": "user", "content": "fix"}],
            "files": {"a.py": ""},
        })
    assert res.status_code == 200

    # Walk the SSE events, classify each by which key dominates.
    seen: list[str] = []
    for line in res.text.splitlines():
        if not line.startswith("data:"):
            continue
        obj = json.loads(line[len("data:"):].strip())
        if "delta" in obj:
            seen.append("delta")
        elif "patches" in obj:
            seen.append("patches")
        elif obj.get("done"):
            seen.append("done")

    # Must contain at least one delta, exactly one patches, exactly one done.
    assert seen.count("delta") >= 1
    assert seen.count("patches") == 1
    assert seen.count("done") == 1
    # All deltas must precede patches; patches must precede done.
    patches_idx = seen.index("patches")
    done_idx = seen.index("done")
    assert all(seen[i] == "delta" for i in range(patches_idx))
    assert patches_idx < done_idx


def test_edit_route_surfaces_parse_error_when_model_emits_garbage(client):
    """When the model returns text that doesn't parse as a JSON patch
    array, the route must still emit a single `patches` event with
    patches=[] and parse_error set, so the UI can show the model's
    output as plain prose rather than silently dropping it."""
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {"items": [{"checkpoints": [{"label": "cp", "ai_allowed": True}]}]}

    async def fake_cfg(*_args, **_kwargs):
        return {"kind": "openai", "model": "m", "api_key": "k", "base_url": ""}

    async def fake_call_stream(*args, **kwargs):
        # No JSON array anywhere — parse_patches returns ([], "Couldn't parse...").
        for chunk in ["I'd rather discuss the bug first. ", "What did you have in mind?"]:
            yield chunk

    with patch("routers.ai_coding.current_user", fake_user), \
         patch("routers.ai_coding.pb_get", fake_pb_get), \
         patch("routers.ai_coding._resolve_text_cfg", fake_cfg), \
         patch("routers.ai_coding._call_stream", fake_call_stream):
        res = client.post("/api/ai-coding/edit", json={
            "round_slug": "any",
            "checkpoint_index": 0,
            "messages": [{"role": "user", "content": "fix"}],
            "files": {"a.py": ""},
        })
    assert res.status_code == 200

    patches_line = next(l for l in res.text.splitlines() if l.startswith("data:") and "patches" in l)
    obj = json.loads(patches_line[len("data:"):].strip())
    assert obj["patches"] == []
    assert "parse_error" in obj
    assert isinstance(obj["parse_error"], str) and obj["parse_error"]
