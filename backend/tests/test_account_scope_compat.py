"""Account-scope compatibility for the runner's PocketBase writes (ROUNDS-00B-L01/S3).

The stage-3 rules (pocketbase/pb_migrations/1700006000_account_scope_rules.js)
reject a create whose `user` is not the caller and an update that reassigns
`user`; a partial update that omits `user`, or one that resends the caller's
own id, still passes. So a previously working runner write breaks only if it
mis-sets `user`.

Each test drives a real write endpoint with the PocketBase layer mocked to
record the written payload, then asserts the invariant: a create names the
caller, an update omits `user` or resends the caller's own id. The one
exception is the public share viewer's view-tracking insert, which runs under
the admin token (bypassing the rules) and names the share link's owner on
purpose; it is asserted separately. The two-account harness proves the live
rules accept exactly these shapes.
"""
from unittest.mock import patch

from fastapi import HTTPException

CALLER = "user-caller-000"


async def _fake_user(_request):
    return {"id": CALLER, "token": "caller-token"}


def _collection(path: str) -> str:
    parts = path.strip("/").split("/")
    return parts[parts.index("collections") + 1]


def _assert_create_names_caller(writes):
    assert writes, "expected at least one write"
    for op, path, body in writes:
        coll = _collection(path)
        assert op == "post", f"{coll}: expected a create, got {op}"
        assert body.get("user") == CALLER, f"{coll} create set user={body.get('user')!r}, not the caller"


def _assert_update_keeps_owner(writes):
    assert writes, "expected at least one write"
    for op, path, body in writes:
        coll = _collection(path)
        assert op == "patch", f"{coll}: expected an update, got {op}"
        assert "user" not in body or body["user"] == CALLER, (
            f"{coll} update set user={body.get('user')!r}, which would reassign the row"
        )


class _Recorder:
    def __init__(self):
        self.writes = []

    async def post(self, _token, path, body):
        self.writes.append(("post", path, dict(body)))
        return {"id": "rec-1", **body}

    async def patch(self, _token, path, body):
        self.writes.append(("patch", path, dict(body)))
        return {"id": "rec-1", **body}


# ---------------------------------------------------------------------------
# ai_providers
# ---------------------------------------------------------------------------


def test_create_provider_names_the_caller(client):
    rec = _Recorder()
    with patch("routers.ai.current_user", _fake_user), patch("routers.ai.pb_post", rec.post):
        res = client.post("/api/ai/providers", json={"kind": "openai", "label": "Prov"})
    assert res.status_code == 200
    _assert_create_names_caller([w for w in rec.writes if _collection(w[1]) == "ai_providers"])


def test_update_provider_does_not_reassign(client):
    rec = _Recorder()

    async def fake_load_provider(_user, provider_id):
        return {"id": provider_id, "kind": "openai", "label": "x", "base_url": "",
                "encrypted_key": "", "key_iv": "", "models_cache": []}

    with patch("routers.ai.current_user", _fake_user), \
         patch("routers.ai._load_provider", fake_load_provider), \
         patch("routers.ai.pb_patch", rec.patch):
        res = client.patch("/api/ai/providers/p1", json={"kind": "openai", "label": "x2"})
    assert res.status_code == 200
    _assert_update_keeps_owner(rec.writes)


def test_refresh_models_update_does_not_reassign(client):
    rec = _Recorder()

    async def fake_load_provider(_user, provider_id):
        return {"id": provider_id, "kind": "openai", "encrypted_key": "enc", "key_iv": "iv",
                "base_url": "", "models_cache": []}

    async def fake_fetch_models(_kind, _key, _base, **_kwargs):
        return ["model-a", "model-b"]

    with patch("routers.ai.current_user", _fake_user), \
         patch("routers.ai._load_provider", fake_load_provider), \
         patch("routers.ai.decrypt", lambda *_a, **_k: "sk-test"), \
         patch("routers.ai._fetch_models", fake_fetch_models), \
         patch("routers.ai.pb_patch", rec.patch):
        res = client.post("/api/ai/providers/p1/refresh-models")
    assert res.status_code == 200
    _assert_update_keeps_owner(rec.writes)


# ---------------------------------------------------------------------------
# ai_settings (put_settings: create when absent, update when present; both
# resend the caller's own id)
# ---------------------------------------------------------------------------


def test_put_settings_create_branch_names_the_caller(client):
    rec = _Recorder()

    async def no_row(_user):
        return None

    with patch("routers.ai.current_user", _fake_user), \
         patch("routers.ai._load_settings", no_row), \
         patch("routers.ai.pb_post", rec.post):
        res = client.put("/api/ai/settings", json={"text_model": "m"})
    assert res.status_code == 200
    _assert_create_names_caller(rec.writes)


def test_put_settings_update_branch_resends_the_caller(client):
    rec = _Recorder()

    async def existing(_user):
        return {"id": "s1", "user": CALLER}

    with patch("routers.ai.current_user", _fake_user), \
         patch("routers.ai._load_settings", existing), \
         patch("routers.ai.pb_patch", rec.patch):
        res = client.put("/api/ai/settings", json={"text_model": "m"})
    assert res.status_code == 200
    # put_settings resends the owner's own id on the update, which the rule's
    # `@request.data.user = @request.auth.id` branch accepts.
    _assert_update_keeps_owner(rec.writes)


# ---------------------------------------------------------------------------
# resume_share_links (user token) + resume_share_views (admin insert)
# ---------------------------------------------------------------------------


def test_create_share_link_names_the_caller(client):
    rec = _Recorder()
    with patch("routers.share.current_user", _fake_user), patch("routers.share.pb_post", rec.post):
        res = client.post("/api/share", json={"resume_id": "r1"})
    assert res.status_code == 200
    _assert_create_names_caller(rec.writes)


def test_public_view_insert_uses_admin_token_and_names_the_link_owner(client):
    link_owner = "owner-of-the-link"
    captured = {}

    async def fake_admin_get(path, params=None):
        if "resume_share_links" in path:
            return {"items": [{"id": "l1", "user": link_owner, "resume": "r1", "token": "tok"}]}
        if "resumes" in path:
            return {"id": "r1", "data": {}, "template_id": "modern", "design": {}, "name": "R"}
        return None

    async def fake_admin_post(path, body):
        captured["path"] = path
        captured["body"] = dict(body)
        return {"id": "v1"}

    with patch("routers.share.pb_admin_get", fake_admin_get), \
         patch("routers.share.pb_admin_post", fake_admin_post):
        res = client.get("/api/share/by-token/sometoken")
    assert res.status_code == 200
    # The view insert is server-only (create rule null); it runs under the
    # admin token and stamps the share link's owner, read from the stored link.
    assert _collection(captured["path"]) == "resume_share_views"
    assert captured["body"]["user"] == link_owner


# ---------------------------------------------------------------------------
# take_home_attempts (submit is an admitted route, so the account comes from
# admission). A client-side (4xx) persist rejection, including an
# authorization denial, surfaces to the caller with PocketBase's own status
# and body; only a server-side (5xx) persist failure stays best-effort so the
# grade is not dropped. The first test asserts the create's payload; the next
# two assert each of those two persist outcomes.
# ---------------------------------------------------------------------------

# The account conftest's `signed_in` fixture admits (TEST_ACCOUNT_ID there).
ADMITTED = "u1"


def test_take_home_submit_attempt_names_the_caller(client, signed_in):
    captured = {}

    async def fake_pb_get(_token, _path, params=None):
        return {"items": [{
            "id": "a1", "slug": "tinytest", "entrypoint": "python3 harness.py",
            "harness_files": [{"path": "harness.py", "contents": (
                "import json\nprint(json.dumps({"
                "\"criteria\":[{\"id\":\"a\",\"passed\":True,\"weight\":1.0,\"logs\":\"\"}],"
                "\"score\":1.0,\"duration_ms\":1}))\n"
            )}],
            "rubric": {"items": []},
        }]}

    async def fake_pb_post(_token, _path, body):
        captured.update(body)
        return {"id": "att1"}

    async def no_provider(_user):
        raise Exception("no provider")

    with patch("routers.take_home.pb_get", fake_pb_get), \
         patch("routers.take_home.pb_post", fake_pb_post), \
         patch("routers.take_home._active_text_config", no_provider):
        res = client.post("/api/take-home/submit", headers=signed_in, json={
            "assignment_slug": "tinytest",
            "files": {"main.py": "# user file"},
            "notes": "n",
            "ai_chats": [],
            "duration_ms": 10,
        })
    assert res.status_code == 200
    assert captured.get("user") == ADMITTED, f"take_home attempt set user={captured.get('user')!r}"
    assert captured.get("status") == "graded"


def test_take_home_submit_surfaces_a_persist_time_authorization_denial(client, signed_in):
    # PocketBase refuses the attempts insert at persist time (for example a
    # typed relation pointed at a record the account does not own). The grade
    # must not mask it: the caller sees the same status and body PocketBase
    # returned.
    denial = {"code": 400, "message": "Failed to create record.", "data": {}}

    async def denying_pb_post(_token, _path, _body):
        raise HTTPException(status_code=400, detail=f"PocketBase error: {denial}")

    async def fake_pb_get(_token, _path, params=None):
        return {"items": [{
            "id": "a1", "slug": "tinytest", "entrypoint": "python3 harness.py",
            "harness_files": [{"path": "harness.py", "contents": (
                "import json\nprint(json.dumps({"
                "\"criteria\":[{\"id\":\"a\",\"passed\":True,\"weight\":1.0,\"logs\":\"\"}],"
                "\"score\":1.0,\"duration_ms\":1}))\n"
            )}],
            "rubric": {"items": []},
        }]}

    async def no_provider(_user):
        raise Exception("no provider")

    with patch("routers.take_home.pb_get", fake_pb_get), \
         patch("routers.take_home.pb_post", denying_pb_post), \
         patch("routers.take_home._active_text_config", no_provider):
        res = client.post("/api/take-home/submit", headers=signed_in, json={
            "assignment_slug": "tinytest",
            "files": {"main.py": "# user file"},
            "notes": "n",
            "ai_chats": [],
            "duration_ms": 10,
        })
    assert res.status_code == 400
    assert "Failed to create record." in res.json()["detail"]


def test_take_home_submit_keeps_the_grade_on_a_persist_infrastructure_failure(client, signed_in):
    # A server-side persistence failure (PocketBase outage, 5xx) stays
    # best-effort so it doesn't drop the user's grade.
    async def failing_pb_post(_token, _path, _body):
        raise HTTPException(status_code=502, detail="PocketBase error: upstream down")

    async def fake_pb_get(_token, _path, params=None):
        return {"items": [{
            "id": "a1", "slug": "tinytest", "entrypoint": "python3 harness.py",
            "harness_files": [{"path": "harness.py", "contents": (
                "import json\nprint(json.dumps({"
                "\"criteria\":[{\"id\":\"a\",\"passed\":True,\"weight\":1.0,\"logs\":\"\"}],"
                "\"score\":1.0,\"duration_ms\":1}))\n"
            )}],
            "rubric": {"items": []},
        }]}

    async def no_provider(_user):
        raise Exception("no provider")

    with patch("routers.take_home.pb_get", fake_pb_get), \
         patch("routers.take_home.pb_post", failing_pb_post), \
         patch("routers.take_home._active_text_config", no_provider):
        res = client.post("/api/take-home/submit", headers=signed_in, json={
            "assignment_slug": "tinytest",
            "files": {"main.py": "# user file"},
            "notes": "n",
            "ai_chats": [],
            "duration_ms": 10,
        })
    assert res.status_code == 200
    assert res.json()["harness"]["score"] == 1.0
