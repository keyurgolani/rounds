import json
import pathlib
import shutil

import pytest

from ai_coding.project_runner import run_project


def test_python_project_pass():
    files = {
        "cart.py": "def add(a, b): return a + b\n",
        "tests/test_x.py": (
            "from cart import add\n"
            "def test_add(): assert add(2, 3) == 5\n"
        ),
    }
    result = run_project(
        files=files,
        language="python",
        test_command="pytest tests/test_x.py -q",
        timeout_s=15,
    )
    assert result.passed is True
    assert result.failed_count == 0
    assert "1 passed" in result.stdout


def test_python_project_fail_surfaces_diagnostics():
    files = {
        "cart.py": "def add(a, b): return a - b\n",  # broken
        "tests/test_x.py": (
            "from cart import add\n"
            "def test_add(): assert add(2, 3) == 5\n"
        ),
    }
    result = run_project(
        files=files,
        language="python",
        test_command="pytest tests/test_x.py -q",
        timeout_s=15,
    )
    assert result.passed is False
    assert result.failed_count >= 1
    assert "FAILED" in result.stdout or "assert" in result.stdout


def test_timeout_returns_structured_error():
    files = {}
    result = run_project(
        files=files,
        language="python",
        test_command="while true; do :; done",
        timeout_s=1,
    )
    assert result.passed is False
    assert "Time limit exceeded" in (result.error or "")


def test_parse_counts_ignores_stray_passed_in_failure_messages():
    # Regression: the original regex matched stray "N passed/failed" tokens
    # anywhere in stdout. Last-write-wins meant any such token *after* the
    # summary line would overwrite the real count. Pytest emits the short
    # test summary block (with FAILED <node> - <message>) AFTER the totals
    # line in some configurations, so the stray text really does appear
    # downstream of the summary in practice.
    from ai_coding.project_runner import _parse_counts

    stdout = (
        "============================= test session starts =============================\n"
        "F\n"
        "tests/test_x.py::test_foo FAILED\n"
        "=========================== 2 passed, 1 failed in 0.42s ===========================\n"
        "=========================== short test summary info ============================\n"
        "FAILED test_x.py::test_foo - assertion: expected 99 passed, got 0 failed\n"
    )
    passed, failed = _parse_counts("python", stdout)
    assert passed == 2, f"expected 2, got {passed}"
    assert failed == 1, f"expected 1, got {failed}"


CART_FILES = {
    "cart.py": "def add(a, b): return a + b\n",
    "tests/test_x.py": "from cart import add\ndef test_a(): assert add(2,3)==5\n",
}


@pytest.fixture
def cart_round(pocketbase):
    # The checkpoint's test command lives on the round, not in the request.
    return pocketbase.add(
        "ai_coding_rounds",
        slug="cart-totals",
        language="python",
        checkpoints=[{"label": "cp0", "ai_allowed": True, "test_command": "pytest tests/test_x.py -q"}],
    )


@pytest.fixture
def project_runs(monkeypatch):
    """Every run_project call the AI-coding router makes."""
    from routers import ai_coding

    calls = []
    real = ai_coding.run_project

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    monkeypatch.setattr(ai_coding, "run_project", spy)
    return calls


RUN_PROJECT_BODY = {"round_slug": "cart-totals", "checkpoint_index": 0, "files": CART_FILES}


def test_run_project_route(client, signed_in, cart_round, project_runs):
    res = client.post("/api/ai-coding/run-project", json=RUN_PROJECT_BODY, headers=signed_in)
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] is True
    assert data["passed_count"] == 1
    assert data["failed_count"] == 0
    ((args, kwargs),) = project_runs
    assert args[2] == "pytest tests/test_x.py -q"
    assert kwargs["timeout_s"] == 10


def test_run_project_route_anonymous_is_denied_before_anything_runs(client, cart_round, project_runs, pocketbase):
    # Expected-deny control (#8).
    res = client.post("/api/ai-coding/run-project", json=RUN_PROJECT_BODY)
    assert res.status_code == 401
    assert res.json()["code"] == "unauthenticated"
    assert project_runs == []
    assert pocketbase.calls == []


@pytest.mark.parametrize(
    "extra",
    [
        {"test_command": "pytest tests/test_x.py -q"},
        {"timeout_s": 15},
        {"language": "python", "test_command": "true", "timeout_s": 600},
    ],
)
def test_run_project_refuses_a_caller_command_or_timeout(client, signed_in, cart_round, project_runs, pocketbase, extra):
    res = client.post("/api/ai-coding/run-project", json={**RUN_PROJECT_BODY, **extra}, headers=signed_in)
    assert res.status_code == 422
    assert res.json()["code"] == "invalid_request"
    assert project_runs == []
    assert pocketbase.calls == []


def test_run_project_picks_the_checkpoint_for_the_language(client, signed_in, pocketbase, project_runs):
    pocketbase.add(
        "ai_coding_rounds",
        slug="two-langs",
        language="python",
        checkpoints={
            "python": [{"test_command": "echo '1 passed in 0.01s'"}],
            "typescript": [{"test_command": "echo '# pass 1'"}],
        },
    )
    body = {"round_slug": "two-langs", "checkpoint_index": 0, "files": {}}
    res = client.post("/api/ai-coding/run-project", json={**body, "language": "typescript"}, headers=signed_in)
    assert res.status_code == 200
    assert project_runs[-1][0][1:3] == ("typescript", "echo '# pass 1'")
    res = client.post("/api/ai-coding/run-project", json=body, headers=signed_in)
    assert res.status_code == 200
    assert project_runs[-1][0][1:3] == ("python", "echo '1 passed in 0.01s'")


@pytest.mark.parametrize(
    "body",
    [
        {"round_slug": "missing-round", "checkpoint_index": 0, "files": {}},
        {"round_slug": "cart-totals", "checkpoint_index": 3, "files": {}},
        {"round_slug": "cart-totals", "checkpoint_index": 0, "language": "typescript", "files": {}},
    ],
)
def test_run_project_answers_not_found_before_anything_runs(client, signed_in, cart_round, project_runs, body):
    res = client.post("/api/ai-coding/run-project", json=body, headers=signed_in)
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"
    assert project_runs == []


def test_run_project_refuses_a_checkpoint_without_a_stored_command(client, signed_in, pocketbase, project_runs):
    pocketbase.add("ai_coding_rounds", slug="no-command", language="python", checkpoints=[{"label": "cp0"}])
    res = client.post(
        "/api/ai-coding/run-project",
        json={"round_slug": "no-command", "checkpoint_index": 0, "files": {}},
        headers=signed_in,
    )
    assert res.status_code == 422
    assert res.json()["code"] == "invalid_request"
    assert project_runs == []


def test_chat_route_requires_auth(client):
    res = client.post("/api/ai-coding/chat", json={
        "messages": [{"role": "user", "content": "hello"}],
        "files": {"a.py": "pass"},
    })
    assert res.status_code == 401


# ---------------------------------------------------------------------
# Per-round regression: each seeded round must actually run end-to-end
# through run_project for every supported language. Catches the class
# of bug where a starter file references a path that doesn't exist at
# materialize time, or where a test command points at a runtime the
# runner image doesn't carry.
# ---------------------------------------------------------------------


def _round_dir(slug: str) -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1] / "ai_coding" / "rounds" / slug


def _build_files(round_dir: pathlib.Path, language: str) -> dict[str, str]:
    """Reproduce what build_seed.py emits for one language of a round.
    Includes starter files plus every checkpoint's visible tests."""
    files: dict[str, str] = {}
    manifest = json.loads((round_dir / "manifest.json").read_text())

    starter_root = (
        round_dir / "starter" / language
        if (round_dir / "starter" / language).exists()
        else round_dir / "starter"
    )
    for f in starter_root.rglob("*"):
        if f.is_file():
            files[str(f.relative_to(starter_root))] = f.read_text()

    cps_root = (
        round_dir / "checkpoints" / language
        if (round_dir / "checkpoints" / language).exists()
        else round_dir / "checkpoints"
    )
    cps = (
        manifest.get("variants", {}).get(language, {}).get("checkpoints")
        or manifest.get("checkpoints")
        or []
    )
    for idx, _cp in enumerate(cps):
        cp_tests = cps_root / str(idx) / "tests"
        if cp_tests.exists():
            for f in cp_tests.rglob("*"):
                if f.is_file():
                    files[f"tests/checkpoint_{idx}/{f.relative_to(cp_tests)}"] = f.read_text()
    return files


def test_hallucinated_http_client_python_runs_via_project_runner():
    """The python variant's visible checkpoint must execute through
    run_project against the AI's starter (which embeds the bug). The
    visible test mocks both the bogus method and the real one, so it
    is expected to pass — the bug is only surfaced by the hidden test
    against a real server. Here we just check it runs end-to-end."""
    rd = _round_dir("hallucinated-http-client")
    files = _build_files(rd, "python")
    result = run_project(
        files=files,
        language="python",
        test_command="pytest tests/checkpoint_0/test_visible.py -q",
        timeout_s=20,
    )
    assert (result.passed_count + result.failed_count) >= 1, (
        f"python round failed to run any tests; stderr: {result.stderr[:500]}; "
        f"error: {result.error}"
    )
    assert result.passed, (
        "visible test for python variant should pass against the AI's "
        f"hallucinated starter; stdout: {result.stdout[:500]}"
    )


@pytest.mark.skipif(shutil.which("tsx") is None, reason="tsx not on PATH")
def test_hallucinated_http_client_typescript_runs_via_project_runner():
    """The TS variant's visible checkpoint runs through tsx + node:test.
    Same shape as the python regression — the bug is only caught by the
    hidden test, so the visible run is expected to pass here."""
    rd = _round_dir("hallucinated-http-client")
    files = _build_files(rd, "typescript")
    result = run_project(
        files=files,
        language="typescript",
        test_command="tsx --test tests/checkpoint_0/client.test.ts",
        timeout_s=30,
    )
    assert (result.passed_count + result.failed_count) >= 1, (
        f"typescript round failed to run any tests; stderr: {result.stderr[:500]}; "
        f"error: {result.error}"
    )
    assert result.passed, (
        "visible test for typescript variant should pass against the AI's "
        f"hallucinated starter; stdout: {result.stdout[:500]}"
    )
