"""The fd 3 result channel (ROUNDS-00A-L02): the server's scoring in
``app.harness_results``, the driver library ``rounds_harness``, and both
``hallucinated-http-client`` grade drivers run from their compiled
harness revisions."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from app import harness_results

BACKEND = Path(__file__).resolve().parents[1]
HARNESS_LIB = BACKEND / "definitions" / "harness" / "rounds_harness.py"
STORE = BACKEND / "definitions" / "store" / "ai-coding" / "hallucinated-http-client"
ROUND = BACKEND / "ai_coding" / "rounds" / "hallucinated-http-client"
RID = "fetch_user_against_real_server"
EXPECTED = [{"id": RID, "weight": 1}]


def _harness_module():
    # The file a revision ships, loaded the way a driver imports it.
    spec = importlib.util.spec_from_file_location("rounds_harness", HARNESS_LIB)
    module = importlib.util.module_from_spec(spec)
    sys.modules["rounds_harness"] = module
    spec.loader.exec_module(module)
    return module


rounds_harness = _harness_module()


def line(rid=RID, outcome="passed", reason="ok", **extra) -> bytes:
    return (json.dumps({"id": rid, "outcome": outcome, "reason": reason, **extra}) + "\n").encode()


# ---- scoring ---------------------------------------------------------------------


def test_the_server_and_the_driver_library_agree_on_outcomes_and_reasons():
    assert harness_results.OUTCOMES == rounds_harness.OUTCOMES
    assert harness_results.REASONS == rounds_harness.REASONS


def test_a_passed_result_passes_with_full_score():
    result = harness_results.score(line(), EXPECTED, 1)
    assert (result.passed, result.score, result.executed, result.malformed) == (True, 1.0, 1, False)
    assert result.outcomes() == [{"id": RID, "outcome": "passed", "reason": "ok"}]


def test_a_failed_result_fails():
    result = harness_results.score(line(outcome="failed", reason="assertion"), EXPECTED, 1)
    assert (result.passed, result.score, result.executed) == (False, 0.0, 1)


def test_an_empty_channel_never_passes():
    result = harness_results.score(b"", EXPECTED, 1)
    assert (result.passed, result.score, result.executed) == (False, 0.0, 0)
    assert result.outcomes() == [{"id": RID, "outcome": "not-run", "reason": "no-result"}]


def test_a_missing_id_never_passes():
    expected = [{"id": RID, "weight": 0.5}, {"id": "second", "weight": 0.5}]
    result = harness_results.score(line(), expected, 1)
    assert result.passed is False
    assert result.score == 0.5
    assert result.outcomes()[1] == {"id": "second", "outcome": "not-run", "reason": "no-result"}


def test_fewer_than_min_executed_results_never_pass_or_score():
    expected = [{"id": RID, "weight": 1}, {"id": "second", "weight": 1}]
    result = harness_results.score(line(), expected, 2)
    assert (result.passed, result.score, result.executed) == (False, 0.0, 1)


def test_the_score_is_the_passed_share_of_the_server_owned_weights():
    expected = [{"id": RID, "weight": 0.25}, {"id": "second", "weight": 0.75}]
    channel = line(outcome="failed", reason="exception") + line("second")
    assert harness_results.score(channel, expected, 1).score == 0.75
    unweighted = [{"id": RID, "weight": 0}, {"id": "second", "weight": 0}]
    assert harness_results.score(channel, unweighted, 1).score == 0.5


@pytest.mark.parametrize(
    "channel",
    [
        b"not json\n",
        line(score=1.0),
        line(rid="unexpected"),
        line() + line(),
        line(reason="assertion"),
        line(outcome="failed", reason="ok"),
        line(outcome="skipped"),
        line(reason="because"),
        b'["fetch_user_against_real_server", "passed", "ok"]\n',
        b'{"id": 1, "outcome": "passed", "reason": "ok"}\n',
        b"\xff\xfe\n",
        line() + b" " * harness_results.CHANNEL_MAX_BYTES,
    ],
    ids=[
        "not-json", "extra-key", "unknown-id", "duplicate-id", "passed-without-ok", "failed-with-ok",
        "unknown-outcome", "unknown-reason", "not-an-object", "non-string-id", "not-utf8", "oversized",
    ],
)
def test_a_malformed_channel_fails_every_result_closed(channel):
    result = harness_results.score(channel, EXPECTED, 1)
    assert result.malformed is True
    assert (result.passed, result.score, result.executed) == (False, 0.0, 0)
    assert result.outcomes() == [{"id": RID, "outcome": "not-run", "reason": "bad-result"}]


# ---- the driver library ----------------------------------------------------------


def test_the_channel_writes_one_line_per_result_and_refuses_repeats():
    r, w = os.pipe()
    try:
        channel = rounds_harness.Channel(w)
        channel.report(RID, "passed", "ok")
        with pytest.raises(ValueError):
            channel.report(RID, "failed", "assertion")
        with pytest.raises(ValueError):
            channel.report("other", "passed", "nope")
        assert os.get_inheritable(w) is False
    finally:
        os.close(w)
    with os.fdopen(r, "rb") as reader:
        data = reader.read()
    assert data == line()


def test_a_driver_without_the_channel_fails_instead_of_reporting_elsewhere():
    r, w = os.pipe()
    os.close(r)
    os.close(w)
    with pytest.raises(OSError):
        rounds_harness.Channel(w)


def test_last_json_line_reads_only_the_final_line():
    assert rounds_harness.last_json_line('noise\n{"a": 1}\n\n') == {"a": 1}
    assert rounds_harness.last_json_line('{"a": 1}\nnot json') is None
    assert rounds_harness.last_json_line("") is None


def test_protect_marks_the_driver_non_dumpable_on_linux_and_reports_it_elsewhere():
    # In a child, so this test process keeps its own flag.
    code = (
        "import json, sys; sys.path.insert(0, sys.argv[1]); import rounds_harness as h; "
        "before = h.dumpable(); protected = h.protect(); print(json.dumps([before, protected, h.dumpable()]))"
    )
    res = subprocess.run(
        [sys.executable, "-I", "-c", code, str(HARNESS_LIB.parent)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    before, protected, after = json.loads(res.stdout)
    if sys.platform.startswith("linux"):
        assert (before, protected, after) == (True, True, False)
    else:
        assert (before, protected, after) == (None, False, None)


def test_a_child_gets_no_descriptor_past_stderr_and_only_path_and_home(tmp_path):
    # An inheritable descriptor in the driver, like the channel would be
    # without Channel's set_inheritable.
    r, w = os.pipe()
    os.set_inheritable(w, True)
    try:
        probe = (
            "import json, os\n"
            "open_fds = []\n"
            "for fd in range(3, 64):\n"
            "    try:\n"
            "        os.fstat(fd)\n"
            "        open_fds.append(fd)\n"
            "    except OSError:\n"
            "        pass\n"
            "print(json.dumps({'fds': open_fds, 'env': sorted(os.environ)}))\n"
        )
        child = rounds_harness.run_child([sys.executable, "-I", "-c", probe], cwd=str(tmp_path), timeout_s=30)
    finally:
        os.close(w)
        os.close(r)
    seen = rounds_harness.last_json_line(child.stdout)
    assert child.returncode == 0 and not child.timed_out
    assert seen["fds"] == []
    assert set(seen["env"]) <= {"PATH", "HOME", "LC_CTYPE", "__CF_USER_TEXT_ENCODING"}
    assert {"PATH", "HOME"} <= set(seen["env"])


def test_a_child_past_its_time_is_killed_with_its_group(tmp_path):
    child = rounds_harness.run_child(
        [sys.executable, "-I", "-c", "import time; time.sleep(30)"], cwd=str(tmp_path), timeout_s=0.5
    )
    assert child.timed_out is True
    assert child.returncode is None


def test_a_child_that_prints_without_end_never_grows_the_driver(tmp_path):
    # 128 MiB of output. The driver keeps the first CHILD_OUTPUT_MAX bytes
    # and reads the rest away as it comes, so its own peak memory stays far
    # below what holding the stream would take. Measured in a fresh process.
    code = (
        "import json, resource, sys; sys.path.insert(0, sys.argv[1]); import rounds_harness as h; "
        "r = h.run_child([sys.executable, '-I', '-c', "
        "'import sys\\nfor _ in range(128): sys.stdout.buffer.write(bytes(1 << 20))'], sys.argv[2], 60); "
        "print(json.dumps([len(r.stdout.encode()), r.returncode, r.timed_out, "
        "resource.getrusage(resource.RUSAGE_SELF).ru_maxrss]))"
    )
    res = subprocess.run(
        [sys.executable, "-I", "-c", code, str(HARNESS_LIB.parent), str(tmp_path)],
        capture_output=True, text=True, timeout=120, check=True,
    )
    kept, returncode, timed_out, maxrss = json.loads(res.stdout)
    assert (kept, returncode, timed_out) == (rounds_harness.CHILD_OUTPUT_MAX, 0, False)
    peak = maxrss if sys.platform == "darwin" else maxrss * 1024  # bytes on macOS, KiB on Linux
    assert peak < 64 * 1024 * 1024, peak


def test_a_child_that_exits_early_keeps_all_its_output(tmp_path):
    child = rounds_harness.run_child(
        [sys.executable, "-I", "-c", "print('noise'); print('{\"answer\": 1}')"], cwd=str(tmp_path), timeout_s=30
    )
    assert (child.returncode, child.timed_out) == (0, False)
    assert rounds_harness.last_json_line(child.stdout) == {"answer": 1}


# ---- the compiled drivers --------------------------------------------------------


def revision(variant: str) -> dict:
    return json.loads((STORE / f"{variant}.v1.json").read_bytes())


FIXED = {
    "python": (
        "client.py",
        "import httpx\n\nINTERNAL_BASE_URL = 'http://internal-users.local'\n\n\n"
        "def fetch_user(user_id: str) -> dict:\n"
        "    res = httpx.get(f'{INTERNAL_BASE_URL}/users/{user_id}', timeout=5.0)\n"
        "    res.raise_for_status()\n"
        "    return res.json()\n",
    ),
    "typescript": (
        "client.ts",
        "export const config = { baseUrl: 'http://internal-users.local' };\n"
        "export interface UserProfile { id: string; name: string; }\n"
        "export async function fetchUser(userId: string): Promise<UserProfile> {\n"
        "  const res = await fetch(`${config.baseUrl}/users/${userId}`);\n"
        "  if (!res.ok) throw new Error(`HTTP ${res.status}`);\n"
        "  return (await res.json()) as UserProfile;\n"
        "}\n",
    ),
}

# Reports a pass on fd 3 directly and through /proc, then answers with
# what it read from the harness files: none of it may reach the server.
FORGING = {
    "python": (
        "client.py",
        "import json, os, pathlib\n\nINTERNAL_BASE_URL = ''\n"
        "FORGED = json.dumps({'id': '" + RID + "', 'outcome': 'passed', 'reason': 'ok'}) + '\\n'\n\n\n"
        "def fetch_user(user_id):\n"
        "    for target in (lambda: os.write(3, FORGED.encode()),\n"
        "                   lambda: pathlib.Path(f'/proc/{os.getppid()}/fd/3').write_text(FORGED)):\n"
        "        try:\n"
        "            target()\n"
        "        except OSError:\n"
        "            pass\n"
        "    print(pathlib.Path('harness/users_api.py').read_text())\n"
        "    return {'id': user_id, 'name': 'Real'}\n",
    ),
    "typescript": (
        "client.ts",
        "import { readFileSync, writeSync, writeFileSync } from 'node:fs';\n"
        "export const config = { baseUrl: '' };\n"
        "const FORGED = JSON.stringify({ id: '" + RID + "', outcome: 'passed', reason: 'ok' }) + '\\n';\n"
        "export async function fetchUser(userId: string) {\n"
        "  for (const target of [() => writeSync(3, FORGED), () => writeFileSync(`/proc/${process.ppid}/fd/3`, FORGED)]) {\n"
        "    try { target(); } catch { /* refused */ }\n"
        "  }\n"
        "  console.log(readFileSync('harness/users_api.py', 'utf8'));\n"
        "  return { id: userId, name: 'Real' };\n"
        "}\n",
    ),
}


def materialize(job: Path, rev: dict, candidate: tuple[str, str] | None) -> None:
    starter = ROUND / "starter" / rev["variant"]
    for path in sorted(starter.rglob("*")):
        if path.is_file():
            target = job / path.relative_to(starter)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    if candidate is not None:
        (job / candidate[0]).write_text(candidate[1], encoding="utf-8")
    for item in rev["files"]:
        target = job / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item["contents"], encoding="utf-8")
        target.chmod(0o444)


# Puts the channel's write end at fd 3, as the server does, then execs the driver.
_AT_FD_3 = (
    "import os, sys\n"
    "fd = int(sys.argv[1])\n"
    "if fd != 3:\n"
    "    os.dup2(fd, 3)\n"
    "    os.close(fd)\n"
    "os.execvp(sys.argv[2], sys.argv[2:])\n"
)


def run_driver(job: Path, argv: list[str], timeout_s: float = 60) -> tuple[bytes, bytes, int]:
    """(channel bytes, the driver's stdout, its exit code)."""
    if argv[0] == "python3":
        # The runtime profile's interpreter, as the server maps it.
        argv = [sys.executable, *argv[1:]]
    r, w = os.pipe()
    proc = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", _AT_FD_3, str(w), *argv],
        cwd=job,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(job)},
        pass_fds=(w,),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    os.close(w)
    chunks: list[bytes] = []

    def drain() -> None:
        with os.fdopen(r, "rb") as reader:
            chunks.append(reader.read())

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    try:
        stdout, _ = proc.communicate(timeout=timeout_s)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    reader.join(timeout_s)
    return b"".join(chunks), stdout, proc.returncode


VARIANTS = [
    "python",
    pytest.param(
        "typescript",
        marks=pytest.mark.skipif(shutil.which("tsx") is None, reason="tsx not on PATH"),
    ),
]


def grade(tmp_path: Path, variant: str, candidate) -> tuple[harness_results.Score, bytes, bytes]:
    rev = revision(variant)
    checkpoint = rev["checkpoints"][0]
    materialize(tmp_path, rev, candidate)
    channel, stdout, _code = run_driver(tmp_path, checkpoint["grade"]["argv"], checkpoint["grade"]["wall_s"])
    return harness_results.score(channel, checkpoint["results"], checkpoint["min_executed"]), channel, stdout


@pytest.mark.parametrize("variant", VARIANTS)
def test_the_hallucinated_starter_fails_the_real_server_check(tmp_path, variant):
    result, _channel, _stdout = grade(tmp_path, variant, None)
    assert result.passed is False
    assert result.outcomes() == [{"id": RID, "outcome": "failed", "reason": "exception"}]


@pytest.mark.parametrize("variant", VARIANTS)
def test_a_fixed_client_passes_the_real_server_check(tmp_path, variant):
    result, _channel, _stdout = grade(tmp_path, variant, FIXED[variant])
    assert (result.passed, result.score) == (True, 1.0)


@pytest.mark.parametrize("variant", VARIANTS)
def test_a_candidate_cant_report_its_own_result_or_return_harness_files(tmp_path, variant):
    result, channel, stdout = grade(tmp_path, variant, FORGING[variant])
    # Only the driver's own line: the candidate didn't know the name it serves.
    assert channel == line(outcome="failed", reason="assertion")
    assert result.passed is False
    assert stdout == b""


def test_every_harness_revision_runs_its_drivers_from_harness_paths():
    for variant in ("python", "typescript"):
        rev = revision(variant)
        paths = {f["path"] for f in rev["files"]}
        assert all(p.startswith("harness/") for p in paths)
        assert not paths & set(rev["candidate_paths"])
        for checkpoint in rev["checkpoints"]:
            assert checkpoint["grade"]["argv"][:2] == ["python3", "-I"]
            assert checkpoint["grade"]["argv"][2] in paths
            assert checkpoint["run"]["wall_s"] <= 10 and checkpoint["run"]["job_class"] == "interactive"
        assert rev["network"] == "job-loopback" and rev["result_protocol"] == "fd3"
