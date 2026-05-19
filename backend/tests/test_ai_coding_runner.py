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


def test_run_project_route(client):
    res = client.post("/api/ai-coding/run-project", json={
        "files": {
            "cart.py": "def add(a, b): return a + b\n",
            "tests/test_x.py": "from cart import add\ndef test_a(): assert add(2,3)==5\n",
        },
        "language": "python",
        "test_command": "pytest tests/test_x.py -q",
        "timeout_s": 15,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] is True
    assert data["passed_count"] == 1
    assert data["failed_count"] == 0


def test_chat_route_requires_auth(client):
    res = client.post("/api/ai-coding/chat", json={
        "messages": [{"role": "user", "content": "hello"}],
        "files": {"a.py": "pass"},
    })
    assert res.status_code == 401


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_seeded_ts_round_runs_via_project_runner():
    """Regression test: the seeded log-parser-ts round must actually
    execute via run_project(). The original test files imported a path
    that didn't exist at materialize-time, so the entire TS round was
    non-functional in production. This test catches that class of bug."""
    import json
    import pathlib
    from ai_coding.project_runner import run_project

    round_dir = pathlib.Path(__file__).resolve().parents[1] / "ai_coding" / "rounds" / "log-parser-ts"
    manifest = json.loads((round_dir / "manifest.json").read_text())

    # Build the same starter_files dict the seed migration would write to PB.
    files = {}
    for f in (round_dir / "starter").rglob("*"):
        if f.is_file():
            files[str(f.relative_to(round_dir / "starter"))] = f.read_text()
    # Embed checkpoint 0's tests just like the seed does.
    cp0_tests = round_dir / "checkpoints" / "0" / "tests"
    for f in cp0_tests.rglob("*"):
        if f.is_file():
            files[f"tests/checkpoint_0/{f.relative_to(cp0_tests)}"] = f.read_text()

    # Reference manifest for documentation; the test_command below matches
    # what build_seed.py emits for checkpoint 0 of this round.
    assert manifest["slug"] == "log-parser-ts"

    # Run with the rewritten test_command (matches what build_seed.py emits).
    result = run_project(
        files=files,
        language="typescript",
        test_command="node --test tests/checkpoint_0/parser.test.ts",
        timeout_s=20,
    )
    # We expect the round's seeded bug to make some tests fail, but they
    # must at least RUN (no module-not-found errors). passed_count + failed_count > 0.
    assert (result.passed_count + result.failed_count) > 0, (
        f"TS round failed to run any tests; stderr: {result.stderr[:500]}; error: {result.error}"
    )


def test_seeded_python_round_runs_via_project_runner():
    """Companion to the TS-round test — exercises the seeded Python round
    end-to-end through run_project()."""
    import json
    import pathlib
    from ai_coding.project_runner import run_project

    round_dir = pathlib.Path(__file__).resolve().parents[1] / "ai_coding" / "rounds" / "cart-bugfix-py"
    files = {}
    for f in (round_dir / "starter").rglob("*"):
        if f.is_file():
            files[str(f.relative_to(round_dir / "starter"))] = f.read_text()
    cp0_tests = round_dir / "checkpoints" / "0" / "tests"
    for f in cp0_tests.rglob("*"):
        if f.is_file():
            files[f"tests/checkpoint_0/{f.relative_to(cp0_tests)}"] = f.read_text()

    result = run_project(
        files=files,
        language="python",
        test_command="pytest tests/checkpoint_0/test_checkpoint.py -q",
        timeout_s=20,
    )
    # Round ships with an intentional bug; expect failures (cp0 is the bug-fix
    # checkpoint), but tests must at least be collected and run.
    assert (result.passed_count + result.failed_count) >= 3, (
        f"Python round failed to run expected 3 tests; stderr: {result.stderr[:500]}; error: {result.error}"
    )


