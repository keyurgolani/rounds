"""Account-scope compatibility for the runner's PocketBase writes (ROUNDS-00B-L01/S3).

The stage-3 rules (pocketbase/pb_migrations/1700006000_account_scope_rules.js)
reject a create whose `user` is not the caller and an update that reassigns
`user`; a partial update that omits `user`, or one that resends the caller's
own id, still passes. So a previously working runner write breaks only if it
mis-sets `user`.

Each test drives a real write endpoint with the PocketBase layer mocked to
record the written payload, then asserts the invariant: a create names the
caller, an update omits `user` or resends the caller's own id. No runner
module writes an older share link or its views since ROUNDS-00B-L06 stage
1, which a static check below asserts. The two-account harness proves the
live rules accept exactly these shapes.
"""
from pathlib import Path
from unittest.mock import patch

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
# resume_share_links and resume_share_views: since ROUNDS-00B-L06 no client
# writes either, the runner included. A new link is CreateShare, which
# PocketBase's hook writes as the caller (tests/test_share_commands.py).
# ---------------------------------------------------------------------------

BACKEND = Path(__file__).resolve().parents[1]


def _runner_modules() -> list[Path]:
    return sorted(path for path in BACKEND.rglob("*.py")
                  if "tests" not in path.relative_to(BACKEND).parts and "__pycache__" not in path.parts)


def test_no_runner_module_writes_an_older_share_link_or_its_views():
    named: dict[str, list[str]] = {}
    for path in _runner_modules():
        text = path.read_text()
        for collection in ("resume_share_links", "resume_share_views"):
            if collection in text:
                named.setdefault(collection, []).append(path.relative_to(BACKEND).as_posix())
    # The one module that names them only lists the caller's own older
    # links (tests/test_share_older_links.py checks it makes no write).
    assert named == {"resume_share_links": ["routers/share.py"]}


# ---------------------------------------------------------------------------
# take_home_attempts and ai_coding_attempts: since ROUNDS-00A-L03 PR 4 the
# runner writes neither with a caller's token. A submission or a grade is a
# job, and the server writes its graded row, naming the job's account, with
# the job's result (test_execution_grading.py). No execution key's value
# writes one from a request (test_execution_grading.py's negative control).
# ---------------------------------------------------------------------------
