from ai_coding.rubric import build_prompt, parse_ai_output


def test_parse_well_formed_output():
    raw = """
    {
      "items": [
        {"id": "correctness", "score": 0.9, "evidence": "all tests passing", "suggestions": []},
        {"id": "code_quality", "score": 0.7, "evidence": "naming is clear", "suggestions": ["add type hints"]}
      ],
      "total": 0.82
    }
    """
    out = parse_ai_output(raw)
    assert out["items"][0]["score"] == 0.9
    assert out["total"] == 0.82


def test_parse_handles_extra_prose():
    raw = "Here is the rubric:\n```json\n{\"items\":[],\"total\":0}\n```\nDone."
    out = parse_ai_output(raw)
    assert out == {"items": [], "total": 0}


def test_parse_includes_evidence_quotes_when_present():
    raw = """
    {
      "items": [
        {"id":"q1","score":0.9,"evidence":"clean fix","evidence_quotes":[{"file":"app.py","line":12,"quote":"return result"}],"suggestions":[]}
      ],
      "total": 0.9
    }
    """
    out = parse_ai_output(raw)
    assert out["items"][0]["evidence_quotes"] == [{"file": "app.py", "line": 12, "quote": "return result"}]


def test_parse_defaults_evidence_quotes_to_empty_list_when_missing():
    raw = '{"items":[{"id":"q1","score":0.5,"evidence":"ok","suggestions":[]}],"total":0.5}'
    out = parse_ai_output(raw)
    assert out["items"][0]["evidence_quotes"] == []


def test_parse_drops_malformed_evidence_quotes_entries():
    raw = """
    {
      "items":[
        {
          "id":"q1","score":0.9,"evidence":"x","suggestions":[],
          "evidence_quotes":[
            {"file":"a.py","line":7,"quote":"good"},
            {"file":"a.py","line":"NaN","quote":"bad-line"},
            {"file":"a.py","quote":"no line"},
            "not even a dict",
            {"line":3,"quote":"no file"}
          ]
        }
      ],
      "total":0.9
    }
    """
    out = parse_ai_output(raw)
    qs = out["items"][0]["evidence_quotes"]
    assert qs == [{"file": "a.py", "line": 7, "quote": "good"}]


def test_build_prompt_includes_rubric_and_files():
    prompt = build_prompt(
        rubric={"items": [{"id": "correctness", "label": "Correctness", "weight": 0.4, "prompt": "Did tests pass?"}]},
        files={"a.py": "x = 1"},
        test_results={"0": {"passed": 1, "failed": 0}},
        ai_chats=[],
    )
    assert "correctness" in prompt
    assert "x = 1" in prompt


import pytest
from unittest.mock import patch


def test_chat_route_blocks_when_ai_disabled_for_checkpoint(client):
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {
            "items": [
                {
                    "checkpoints": [
                        {"label": "cp0", "ai_allowed": False, "test_command": "true"},
                        {"label": "cp1", "ai_allowed": True, "test_command": "true"},
                    ]
                }
            ]
        }

    with patch("routers.ai_coding.current_user", fake_user), \
         patch("routers.ai_coding.pb_get", fake_pb_get):
        res = client.post("/api/ai-coding/chat", json={
            "round_slug": "cart-bugfix-py",
            "checkpoint_index": 0,
            "messages": [{"role": "user", "content": "hi"}],
            "files": {},
        })
    assert res.status_code == 403
    assert "disabled" in res.json()["detail"].lower()


def test_chat_route_404s_when_round_missing(client):
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {"items": []}

    with patch("routers.ai_coding.current_user", fake_user), \
         patch("routers.ai_coding.pb_get", fake_pb_get):
        res = client.post("/api/ai-coding/chat", json={
            "round_slug": "missing-round",
            "checkpoint_index": 0,
            "messages": [{"role": "user", "content": "hi"}],
            "files": {},
        })
    assert res.status_code == 404


def test_chat_route_rejects_invalid_slug_pattern(client):
    # Pydantic regex constraint blocks before the handler runs, so no
    # PB calls need mocking here.
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    with patch("routers.ai_coding.current_user", fake_user):
        res = client.post("/api/ai-coding/chat", json={
            "round_slug": "bad slug!",
            "checkpoint_index": 0,
            "messages": [{"role": "user", "content": "hi"}],
            "files": {},
        })
    assert res.status_code == 422  # Pydantic validation


def test_grade_route_runs_checkpoints_and_calls_ai(client, monkeypatch):
    # Bypass auth + provider config by mocking the helpers.
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {
            "items": [
                {
                    "slug": "test-round",
                    "language": "python",
                    "checkpoints": [
                        {"test_command": "echo '1 passed in 0.0s'", "hidden_files": []},
                    ],
                    "rubric": {"items": [{"id": "correctness", "label": "C", "weight": 1.0, "prompt": "p"}]},
                }
            ]
        }

    async def fake_cfg(_):
        return {"kind": "openai", "model": "gpt-4", "api_key": "k", "base_url": ""}

    async def fake_complete(*args, **kwargs):
        return '{"items":[{"id":"correctness","score":0.9,"evidence":"ok","suggestions":[]}],"total":0.9}'

    with patch("routers.ai_coding.current_user", fake_user), \
         patch("routers.ai_coding.pb_get", fake_pb_get), \
         patch("routers.ai_coding._active_text_config", fake_cfg), \
         patch("routers.ai_coding._call_complete", fake_complete):
        res = client.post("/api/ai-coding/grade", json={
            "round_slug": "test-round",
            "files": {"a.py": "pass"},
            "ai_chats": [],
        })
    assert res.status_code == 200
    body = res.json()
    assert body["rubric_review"]["items"][0]["id"] == "correctness"
    assert body["test_results"][0]["passed"] is True


def test_grade_route_merges_hidden_files_during_grade(client):
    """Hidden test files materialized only when grading — not visible to
    the candidate or to /run-project. Asserts that a hidden test that
    references a marker file (provided in hidden_files) actually runs."""
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {
            "items": [
                {
                    "slug": "t-round",
                    "checkpoints": [
                        {
                            "label": "cp0",
                            "ai_allowed": True,
                            "test_command": (
                                "python3 -c \"import os; "
                                "assert os.path.exists('tests/checkpoint_0/marker.txt'); "
                                "print('1 passed in 0.01s')\""
                            ),
                            "hidden_files": [
                                {"path": "tests/checkpoint_0/marker.txt", "contents": "ok"},
                            ],
                        },
                    ],
                    "rubric": {"items": []},
                }
            ]
        }

    async def fake_cfg(_):
        # Force the rubric AI call to be skipped — we're only testing
        # the deterministic merge path here.
        raise Exception("no provider configured for this test")

    with patch("routers.ai_coding.current_user", fake_user), \
         patch("routers.ai_coding.pb_get", fake_pb_get), \
         patch("routers.ai_coding._active_text_config", fake_cfg):
        res = client.post("/api/ai-coding/grade", json={
            "round_slug": "t-round",
            "files": {"a.py": "pass"},
            "ai_chats": [],
        })
    assert res.status_code == 200
    body = res.json()
    assert body["test_results"][0]["passed"] is True


def test_models_route_flattens_providers_and_cached_models(client):
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_list_providers_raw(_user):
        return [
            {
                "id": "p1",
                "kind": "anthropic",
                "label": "Anthropic prod",
                "encrypted_key": "ZW5j",
                "models_cache": ["claude-sonnet-4-6", "claude-opus-4-7"],
            },
            {
                "id": "p2",
                "kind": "openai",
                "label": "OpenAI test",
                "encrypted_key": "ZW5j",
                "models_cache": ["gpt-4o-mini"],
            },
            {
                "id": "p3",
                "kind": "openai",
                "label": "Empty",
                "encrypted_key": "ZW5j",
                "models_cache": [],  # never enumerated
            },
        ]

    with patch("routers.ai_coding.current_user", fake_user), \
         patch("routers.ai_coding._list_providers_raw", fake_list_providers_raw):
        res = client.get("/api/ai-coding/models")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 3  # 2 + 1 + 0
    assert items[0] == {
        "provider_id": "p1",
        "provider_label": "Anthropic prod",
        "kind": "anthropic",
        "model": "claude-sonnet-4-6",
    }
    assert {it["model"] for it in items} == {"claude-sonnet-4-6", "claude-opus-4-7", "gpt-4o-mini"}


def test_models_route_skips_unusable_provider_rows(client):
    """Rows lacking an id or a stored key must not surface in the
    dropdown — sending those provider_ids back to /chat would 404
    or 400. This is the contract that lets the frontend trust
    every emitted row."""
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_list_providers_raw(_user):
        return [
            {  # no id — malformed row
                "kind": "anthropic", "label": "Bad",
                "encrypted_key": "ZW5j",
                "models_cache": ["claude-sonnet-4-6"],
            },
            {  # no encrypted_key — unusable
                "id": "p2", "kind": "openai", "label": "NoKey",
                "encrypted_key": "",
                "models_cache": ["gpt-4o-mini"],
            },
            {  # valid
                "id": "p3", "kind": "anthropic", "label": "Good",
                "encrypted_key": "ZW5j",
                "models_cache": ["claude-opus-4-7"],
            },
        ]

    with patch("routers.ai_coding.current_user", fake_user), \
         patch("routers.ai_coding._list_providers_raw", fake_list_providers_raw):
        res = client.get("/api/ai-coding/models")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["provider_id"] == "p3"


def test_chat_route_uses_provider_override_when_supplied(client):
    """When the client sends provider_id+model, the handler must call
    _call_stream with that model, NOT the user's active text-model."""
    captured: dict = {}

    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {
            "items": [
                {
                    "checkpoints": [{"label": "cp0", "ai_allowed": True}],
                }
            ]
        }

    async def fake_load_provider(_user, _pid):
        return {
            "id": "p9",
            "kind": "openai",
            "encrypted_key": "ZW5j",   # base64 'enc'
            "key_iv": "aXY=",          # base64 'iv'
            "base_url": "",
        }

    def fake_decrypt(*_args):
        return "K"

    async def fake_call_stream(*args, **kwargs):
        # Resilient against signature changes — handle either positional
        # or keyword call from the handler.
        captured["kind"] = kwargs.get("kind", args[0] if len(args) > 0 else None)
        captured["model"] = kwargs.get("model", args[1] if len(args) > 1 else None)
        if False:
            yield  # make it an async generator

    async def fake_active_cfg_should_not_be_called(_):
        raise AssertionError(
            "_active_text_config must NOT be called when override is supplied"
        )

    with patch("routers.ai_coding.current_user", fake_user), \
         patch("routers.ai_coding.pb_get", fake_pb_get), \
         patch("routers.ai_coding._load_provider", fake_load_provider), \
         patch("routers.ai_coding.decrypt", fake_decrypt), \
         patch("routers.ai_coding._call_stream", fake_call_stream), \
         patch("routers.ai_coding._active_text_config", fake_active_cfg_should_not_be_called):
        res = client.post("/api/ai-coding/chat", json={
            "round_slug": "any",
            "checkpoint_index": 0,
            "provider_id": "p9",
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hi"}],
            "files": {},
        })
    assert res.status_code == 200
    # Drain the SSE stream so the generator is fully consumed.
    list(res.iter_lines())
    assert captured["model"] == "gpt-4o-mini"
    assert captured["kind"] == "openai"


def test_chat_route_rejects_partial_override(client):
    """Sending only provider_id (or only model) is almost always a
    client bug; the request must 422 rather than silently fall back
    to the active text-model setting."""
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    with patch("routers.ai_coding.current_user", fake_user):
        # provider_id without model
        res = client.post("/api/ai-coding/chat", json={
            "round_slug": "any",
            "checkpoint_index": 0,
            "provider_id": "p9",
            "messages": [{"role": "user", "content": "hi"}],
            "files": {},
        })
        assert res.status_code == 422

        # model without provider_id
        res = client.post("/api/ai-coding/chat", json={
            "round_slug": "any",
            "checkpoint_index": 0,
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hi"}],
            "files": {},
        })
        assert res.status_code == 422


def test_grade_route_records_failure_for_missing_test_command(client):
    """A seeded checkpoint without a test_command should produce an
    explicit failure in the grade report rather than a silent pass."""
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {
            "items": [
                {
                    "slug": "broken-round",
                    "checkpoints": [{"label": "no-cmd"}],  # no test_command field
                    "rubric": {"items": []},
                }
            ]
        }

    async def fake_cfg(_):
        raise Exception("no provider — skip rubric AI")

    with patch("routers.ai_coding.current_user", fake_user), \
         patch("routers.ai_coding.pb_get", fake_pb_get), \
         patch("routers.ai_coding._active_text_config", fake_cfg):
        res = client.post("/api/ai-coding/grade", json={
            "round_slug": "broken-round",
            "files": {},
            "ai_chats": [],
        })
    assert res.status_code == 200
    body = res.json()
    assert body["test_results"][0]["passed"] is False
    assert "test_command" in (body["test_results"][0]["error"] or "")
