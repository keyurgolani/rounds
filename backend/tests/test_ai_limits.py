"""AI limits from #1 stage 2 (ROUNDS-00A-L01).

GitHub enhancement takes at most 25 projects, the improve paper fetch
waits for ``ROUNDS_GATE_PAPER_FETCH``, and rule-based ATS scoring is an
admitted route with a strict body."""
from __future__ import annotations

import pytest

from app import gates


def _user():
    return {"id": "u1", "token": "test-token-placeholder", "record": {"id": "u1"}}


@pytest.fixture
def ai_user(monkeypatch):
    from routers import ai

    async def user(_request):
        return _user()

    monkeypatch.setattr(ai, "current_user", user)
    return ai


@pytest.fixture
def provider(monkeypatch, ai_user):
    """A configured text provider whose every use is recorded."""
    used = []

    async def cfg(_user):
        used.append("config")
        return {"kind": "openai", "model": "m", "api_key": "test-key", "base_url": ""}

    monkeypatch.setattr(ai_user, "_active_text_config", cfg)
    return used


# ---- enhance-projects ---------------------------------------------------------------


def _projects(n):
    return [{"name": f"repo-{i}", "full_name": f"octo/repo-{i}"} for i in range(n)]


def test_more_than_25_projects_is_413_before_any_provider_or_github_call(client, ai_user, provider, monkeypatch):
    async def enhance(*_args, **_kwargs):
        pytest.fail("a project was enhanced")

    monkeypatch.setattr(ai_user, "_enhance_one", enhance)
    res = client.post("/api/ai/enhance-projects", json={"projects": _projects(26)})
    assert res.status_code == 413
    body = res.json()
    assert body["code"] == "limit_exceeded"
    assert set(body) == {"detail", "code", "correlation_id"}
    assert provider == []


def test_25_projects_are_enhanced(client, ai_user, provider, monkeypatch):
    seen = []

    async def enhance(_client, _cfg, repo):
        seen.append(repo["name"])
        return {"name": repo["name"], "description": "d", "highlights": []}

    monkeypatch.setattr(ai_user, "_enhance_one", enhance)
    res = client.post("/api/ai/enhance-projects", json={"projects": _projects(25)})
    assert res.status_code == 200
    assert len(res.json()["projects"]) == 25 and len(seen) == 25


def test_the_project_cap_matches_the_spa():
    from pathlib import Path

    from app import limits

    dialog = Path(__file__).resolve().parents[2] / "frontend/src/features/resume/studio/editors/GithubImportDialog.tsx"
    assert f"AI_ENHANCE_MAX_PROJECTS = {limits.ENHANCE_MAX_PROJECTS};" in dialog.read_text()
    assert limits.ENHANCE_MAX_PROJECTS == 25


# ---- improve: paper fetch behind its gate ------------------------------------------------


@pytest.fixture
def improve(monkeypatch, ai_user, provider):
    fetched = []

    async def fetch(url):
        fetched.append(url)
        return "paper text"

    async def stream(*_args, **_kwargs):
        yield "ok"

    monkeypatch.setattr(ai_user, "_fetch_paper_text", fetch)
    monkeypatch.setattr(ai_user, "_call_stream", stream)
    return fetched


def _improve(client):
    res = client.post(
        "/api/ai/improve",
        json={"text": "Wrote a paper.", "context": {"paper_url": "https://papers.example.com/a.pdf"}},
    )
    assert res.status_code == 200
    list(res.iter_lines())
    return res


def test_the_paper_fetch_is_off_by_default(client, improve, monkeypatch):
    monkeypatch.setattr(gates, "_snapshot", gates.load({}, gates.RUNNER))
    _improve(client)
    assert improve == []


def test_the_paper_fetch_runs_only_while_its_gate_is_enabled(client, improve, monkeypatch):
    monkeypatch.setattr(gates, "_snapshot", gates.load({"ROUNDS_GATE_PAPER_FETCH": "enabled"}, gates.RUNNER))
    _improve(client)
    assert improve == ["https://papers.example.com/a.pdf"]
    monkeypatch.setattr(gates, "_snapshot", gates.load({"ROUNDS_GATE_PAPER_FETCH": "disabled"}, gates.RUNNER))
    _improve(client)
    assert improve == ["https://papers.example.com/a.pdf"]


# ---- ats-rule --------------------------------------------------------------------------------


def test_signed_in_rule_scoring_still_scores(client, signed_in):
    res = client.post(
        "/api/ai/ats-rule",
        json={"data": {"basics": {"name": "A"}}, "job_description": "Python engineer", "use_ai": False},
        headers=signed_in,
    )
    assert res.status_code == 200
    assert {"rule_score", "breakdown", "suggestions", "missing_keywords"} <= set(res.json())


def test_anonymous_rule_scoring_is_denied(client):
    res = client.post("/api/ai/ats-rule", json={"data": {}, "job_description": None, "use_ai": False})
    assert res.status_code == 401
    assert res.json()["code"] == "unauthenticated"
