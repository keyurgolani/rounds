from unittest.mock import patch


# The run and submit shapes from before definitions. Since ROUNDS-00A-L03
# PR 4 both routes run definitions only, as jobs (test_execution_scratch.py
# and test_execution_grading.py), and at the shipped gates the execution
# keys act as off: each answers 503 before the account check, reads no
# assignment, runs nothing, and saves no attempt.
OLDER_REQUESTS = {
    "/api/take-home/run": {"assignment_slug": "tinytest", "files": {"main.py": "# user file"}},
    "/api/take-home/submit": {"assignment_slug": "tinytest", "files": {"main.py": "# user file"},
                              "notes": "design notes", "ai_chats": [], "duration_ms": 12345},
}


def test_the_older_run_and_submit_requests_are_turned_off_before_anything_runs(client, signed_in):
    touched = []

    async def tripped(*_args, **_kwargs):
        touched.append("pocketbase")
        raise AssertionError("nothing is read or saved")

    def ran(*_args, **_kwargs):
        touched.append("run")
        raise AssertionError("nothing runs")

    with patch("routers.take_home.pb_get", tripped), \
         patch("routers.take_home.pb_post", tripped), \
         patch("routers.take_home.run_assignment", ran):
        for path, body in OLDER_REQUESTS.items():
            for headers in ({}, signed_in):
                res = client.post(path, headers=headers, json=body)
                assert res.status_code == 503, res.text
                assert res.json()["code"] == "execution_disabled"
    assert touched == []


def test_chat_route_404s_when_assignment_missing(client):
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {"items": []}

    with patch("routers.take_home.current_user", fake_user), \
         patch("routers.take_home.pb_get", fake_pb_get):
        res = client.post("/api/take-home/chat", json={
            "assignment_slug": "missing",
            "messages": [{"role": "user", "content": "hi"}],
            "files": {},
        })
    assert res.status_code == 404


def test_chat_route_blocks_when_ai_policy_off(client):
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    async def fake_pb_get(_token, _path, params=None):
        return {
            "items": [
                {
                    "id": "a1",
                    "slug": "tinytest",
                    "ai_policy": "off",
                    "prompt_md": "Build a tiny KV store.",
                }
            ]
        }

    with patch("routers.take_home.current_user", fake_user), \
         patch("routers.take_home.pb_get", fake_pb_get):
        res = client.post("/api/take-home/chat", json={
            "assignment_slug": "tinytest",
            "messages": [{"role": "user", "content": "hi"}],
            "files": {},
        })
    assert res.status_code == 403


def test_chat_route_rejects_invalid_slug_pattern(client):
    async def fake_user(_):
        return {"id": "u1", "token": "t"}

    with patch("routers.take_home.current_user", fake_user):
        res = client.post("/api/take-home/chat", json={
            "assignment_slug": "BAD SLUG",
            "messages": [{"role": "user", "content": "hi"}],
            "files": {},
        })
    assert res.status_code == 422
