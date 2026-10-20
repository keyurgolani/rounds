"""Chat and edit find a multi-language round's checkpoint in the request's
language (ROUNDS-00A-L02), the way run-project and grade do, instead of
indexing the per-language map by number."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException

MULTI_LANGUAGE_ROUND = {
    "slug": "hallucinated-http-client",
    "language": "python",
    "starter_files": {
        "python": [{"path": "client.py", "contents": ""}],
        "typescript": [{"path": "client.ts", "contents": ""}],
    },
    "checkpoints": {
        "python": [{"label": "py0", "ai_allowed": True, "test_command": "true"}],
        "typescript": [
            {"label": "ts0", "ai_allowed": False, "test_command": "true"},
            {"label": "ts1", "ai_allowed": True, "test_command": "true"},
        ],
    },
}
# Past the AI check, the route asks for the provider config; this stands
# in for it, so a test sees the check let the request through.
PASSED = 418


async def _user(_request):
    return {"id": "u1", "token": "t"}


async def _round(_token, _path, params=None):
    return {"items": [MULTI_LANGUAGE_ROUND]}


async def _past_the_check(*_args, **_kwargs):
    raise HTTPException(status_code=PASSED, detail="past the AI check")


@pytest.mark.parametrize("route", ["/api/ai-coding/chat", "/api/ai-coding/edit"])
@pytest.mark.parametrize(
    "extra, status",
    [
        ({"checkpoint_index": 0, "language": "typescript"}, 403),
        ({"checkpoint_index": 1, "language": "typescript"}, PASSED),
        ({"checkpoint_index": 0, "files": {"client.ts": "export {}"}}, 403),
        ({"checkpoint_index": 0}, PASSED),
        ({"checkpoint_index": 1, "language": "python"}, 400),
        ({"checkpoint_index": 0, "language": "go"}, 400),
    ],
    ids=["named-language-off", "named-language-on", "language-from-files", "primary-language",
         "index-past-the-language", "language-the-round-lacks"],
)
def test_a_multi_language_rounds_checkpoint_is_found_in_its_language(client, route, extra, status):
    body = {"round_slug": "hallucinated-http-client", "messages": [{"role": "user", "content": "hi"}], **extra}
    with patch("routers.ai_coding.current_user", _user), \
         patch("routers.ai_coding.pb_get", _round), \
         patch("routers.ai_coding._resolve_text_cfg", _past_the_check):
        res = client.post(route, json=body)
    assert res.status_code == status, res.text


def test_a_language_outside_the_pattern_is_refused_before_the_lookup(client):
    with patch("routers.ai_coding.current_user", _user):
        res = client.post("/api/ai-coding/chat", json={
            "round_slug": "hallucinated-http-client", "checkpoint_index": 0, "language": "py thon",
            "messages": [{"role": "user", "content": "hi"}],
        })
    assert res.status_code == 422
