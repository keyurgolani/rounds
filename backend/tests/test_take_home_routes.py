from unittest.mock import patch


def test_run_route_404s_when_assignment_missing(client):
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {"items": []}

    with patch("routers.take_home.current_user", fake_user), \
         patch("routers.take_home.pb_get", fake_pb_get):
        res = client.post("/api/take-home/run", json={
            "assignment_slug": "missing",
            "files": {"a.py": "pass"},
        })
    assert res.status_code == 404


def test_run_route_executes_harness_and_returns_score(client):
    """Real subprocess. The 'harness' embedded in this test is just a
    Python one-liner that prints the canonical {criteria, score} JSON."""
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {
            "items": [
                {
                    "id": "a1",
                    "slug": "tinytest",
                    "entrypoint": "python3 harness.py",
                    "harness_files": [
                        {
                            "path": "harness.py",
                            "contents": (
                                "import json\n"
                                "print(json.dumps({"
                                "\"criteria\":[{\"id\":\"a\",\"passed\":True,\"weight\":1.0,\"logs\":\"\"}],"
                                "\"score\":1.0,\"duration_ms\":1"
                                "}))\n"
                            ),
                        }
                    ],
                }
            ]
        }

    with patch("routers.take_home.current_user", fake_user), \
         patch("routers.take_home.pb_get", fake_pb_get):
        res = client.post("/api/take-home/run", json={
            "assignment_slug": "tinytest",
            "files": {"main.py": "# user file"},
        })
    assert res.status_code == 200
    body = res.json()
    assert body["score"] == 1.0
    assert body["criteria"][0]["id"] == "a"
    assert body["error"] is None


def test_run_route_rejects_invalid_slug_pattern(client):
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    with patch("routers.take_home.current_user", fake_user):
        res = client.post("/api/take-home/run", json={
            "assignment_slug": "BAD SLUG",
            "files": {},
        })
    assert res.status_code == 422


def test_submit_route_persists_attempt_and_returns_combined(client):
    captured_attempt: dict = {}

    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {
            "items": [
                {
                    "id": "a1",
                    "slug": "tinytest",
                    "entrypoint": "python3 harness.py",
                    "harness_files": [
                        {
                            "path": "harness.py",
                            "contents": (
                                "import json\n"
                                "print(json.dumps({"
                                "\"criteria\":[{\"id\":\"a\",\"passed\":True,\"weight\":1.0,\"logs\":\"\"}],"
                                "\"score\":1.0,\"duration_ms\":1"
                                "}))\n"
                            ),
                        }
                    ],
                    "rubric": {"items": []},
                }
            ]
        }

    async def fake_pb_post(_token, _path, body):
        captured_attempt.update(body)
        return {"id": "att1"}

    async def fake_cfg(_):
        # Force rubric AI to be skipped (no provider).
        raise Exception("no provider")

    with patch("routers.take_home.current_user", fake_user), \
         patch("routers.take_home.pb_get", fake_pb_get), \
         patch("routers.take_home.pb_post", fake_pb_post), \
         patch("routers.take_home._active_text_config", fake_cfg):
        res = client.post("/api/take-home/submit", json={
            "assignment_slug": "tinytest",
            "files": {"main.py": "# user file"},
            "notes": "design notes",
            "ai_chats": [],
            "duration_ms": 12345,
        })
    assert res.status_code == 200
    body = res.json()
    assert body["harness"]["score"] == 1.0
    assert body["rubric_review"]["skipped"] is True
    assert captured_attempt["status"] == "graded"
    assert captured_attempt["assignment"] == "a1"
    assert captured_attempt["notes"] == "design notes"
