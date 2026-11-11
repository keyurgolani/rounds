"""Candidate process containment (ROUNDS-00A-L01, app/sandbox.py).

The child gets a minimal environment, a private scratch directory that
is removed afterwards, its input in a file, its own process session,
and, when the runner is root as in the image, its slot's own uid."""
from __future__ import annotations

import os
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time

import pytest

from ai_coding.project_runner import run_project
from app import sandbox
from runner import run_one

SECRETS = {
    "AI_KEY_SECRET": "test-secret-value-1",
    "PB_ADMIN_EMAIL": "test-admin@example.test",
    "PB_ADMIN_PASSWORD": "test-secret-value-2",
    "ROUNDS_OBS_SECRET": "test-secret-value-3",
    "POCKETBASE_URL": "http://pocketbase.test:8090",
}


@pytest.fixture
def app_secrets(monkeypatch):
    for key, value in SECRETS.items():
        monkeypatch.setenv(key, value)
    return SECRETS


# ---- environment ------------------------------------------------------------


def test_the_candidate_environment_is_an_allowlist(app_secrets):
    env = sandbox.candidate_env("/scratch/run-1", {"PYTHONPATH": "/scratch/run-1"})
    assert set(env) == {
        "PATH", "HOME", "TMPDIR", "USER", "LOGNAME", "LANG", "LC_ALL", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH",
    }
    assert env["HOME"] == env["TMPDIR"] == "/scratch/run-1"
    for value in app_secrets.values():
        assert value not in env.values()


def test_snippet_code_sees_no_app_secret(app_secrets):
    code = "import os\ndef f():\n    return sorted(os.environ.items())\n"
    outcome = run_one(code, "python", {"kind": "function", "name": "f"}, {})
    assert outcome.error is None, outcome.error
    seen = dict(outcome.return_value)
    for key, value in app_secrets.items():
        assert key not in seen
        assert value not in str(outcome.return_value)


def test_project_commands_see_no_app_secret(app_secrets):
    result = run_project({}, "python", "env", timeout_s=10)
    assert result.stdout
    for key, value in app_secrets.items():
        assert key not in result.stdout
        assert value not in result.stdout


# ---- input by file ------------------------------------------------------------


def test_large_input_goes_through_a_file_not_argv():
    nums = list(range(60_000))  # about 400 KB of JSON
    code = (
        "import sys\n"
        "def f(nums):\n"
        "    return [len(nums), len(sys.argv), max(len(a) for a in sys.argv)]\n"
    )
    outcome = run_one(code, "python", {"kind": "function", "name": "f"}, {"nums": nums}, timeout_s=20)
    assert outcome.error is None, outcome.error
    count, argc, longest_arg = outcome.return_value
    assert count == 60_000
    # The script, the input file, and the result file; no argument holds the input.
    assert argc == 3 and longest_arg < 4096


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_javascript_reads_its_input_from_a_file():
    code = "function f(nums) { return [nums.length, process.argv.length]; }\n"
    outcome = run_one(code, "javascript", {"kind": "function", "name": "f"}, {"nums": list(range(30_000))}, timeout_s=20)
    assert outcome.error is None, outcome.error
    assert outcome.return_value[0] == 30_000


# ---- scratch -------------------------------------------------------------------


def test_each_run_gets_a_private_scratch_that_is_removed():
    code = (
        "import os, stat\n"
        "def f():\n"
        "    here = os.getcwd()\n"
        "    return [here, oct(stat.S_IMODE(os.stat(here).st_mode)), os.environ['HOME'], os.environ['TMPDIR']]\n"
    )
    outcome = run_one(code, "python", {"kind": "function", "name": "f"}, {})
    assert outcome.error is None, outcome.error
    here, mode, home, tmpdir = outcome.return_value
    assert mode == "0o700"
    assert os.path.realpath(home) == os.path.realpath(tmpdir) == os.path.realpath(here)
    assert os.path.basename(os.path.dirname(here)) == "rounds-scratch"
    assert not os.path.exists(here)


def test_two_runs_never_share_a_scratch():
    code = "import os\ndef f():\n    return os.getcwd()\n"
    first = run_one(code, "python", {"kind": "function", "name": "f"}, {}).return_value
    second = run_one(code, "python", {"kind": "function", "name": "f"}, {}).return_value
    assert first != second


# ---- uid ----------------------------------------------------------------------------


def test_each_slot_maps_to_its_own_uid_when_the_runner_is_root(monkeypatch):
    monkeypatch.setattr(sandbox, "drops_privileges", lambda: True)
    boxes = [sandbox.sandbox_for(i) for i in range(4)]
    assert [b.uid for b in boxes] == [10001, 10002, 10003, 10004]
    assert {b.gid for b in boxes} == {sandbox.CANDIDATE_GID}


def test_outside_the_image_children_run_as_the_current_user(monkeypatch):
    monkeypatch.setattr(sandbox, "drops_privileges", lambda: False)
    assert sandbox.sandbox_for(0) == sandbox.Sandbox(index=0, uid=None, gid=None)


def _closed_pipe():
    read_end, write_end = os.pipe()
    os.close(write_end)
    return os.fdopen(read_end, "rb")


def test_run_drops_to_the_slot_uid_with_no_groups_and_a_private_umask(monkeypatch, tmp_path):
    seen = {}

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            seen.update(kwargs)
            self.pid = -1
            self.returncode = 0
            self.stdout = _closed_pipe()
            self.stderr = _closed_pipe()

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(sandbox.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(sandbox, "_wait", lambda proc, timeout_s: True)
    monkeypatch.setattr(sandbox, "_kill_group", lambda pid: None)
    monkeypatch.setattr(sandbox, "_kill_uid_pids", lambda uid, proc_root="/proc": [])
    box = sandbox.Sandbox(index=1, uid=10002, gid=10000)
    sandbox.run(["true"], cwd=str(tmp_path), env={"PATH": "/bin"}, timeout_s=1, sandbox=box)
    assert seen["user"] == 10002 and seen["group"] == 10000
    assert seen["extra_groups"] == [] and seen["umask"] == 0o077
    assert seen["start_new_session"] is True
    assert seen["env"] == {"PATH": "/bin"}
    assert seen["stdin"] == subprocess.DEVNULL


def test_hand_over_gives_the_whole_tree_to_the_slot(monkeypatch, tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x")
    (tmp_path / "input.json").write_text("{}")
    owned = []
    monkeypatch.setattr(sandbox.os, "chown", lambda p, u, g: owned.append((p, u, g)))
    monkeypatch.setattr(sandbox.os, "lchown", lambda p, u, g: owned.append((p, u, g)))
    sandbox.hand_over(str(tmp_path), sandbox.Sandbox(index=0, uid=10001, gid=10000))
    paths = {os.path.relpath(p, tmp_path) for p, _u, _g in owned}
    assert paths == {".", "pkg", os.path.join("pkg", "a.py"), "input.json"}
    assert {(u, g) for _p, u, g in owned} == {(10001, 10000)}


def test_hand_over_does_nothing_without_a_uid(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox.os, "chown", lambda *a: pytest.fail("chown"))
    sandbox.hand_over(str(tmp_path), sandbox.Sandbox(index=0, uid=None, gid=None))


# ---- timeouts ------------------------------------------------------------------------


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(state) and not state.startswith("Z")


def test_a_timeout_kills_the_whole_process_group(tmp_path):
    box = sandbox.sandbox_for(0)
    with pytest.raises(subprocess.TimeoutExpired) as err:
        sandbox.run(
            ["bash", "-c", "sleep 30 & echo $!; wait"],
            cwd=str(tmp_path),
            env=sandbox.candidate_env(str(tmp_path)),
            timeout_s=1,
            sandbox=box,
        )
    background = int((err.value.output or "").split()[0])
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not _alive(background):
            break
        time.sleep(0.05)
    else:
        os.kill(background, signal.SIGKILL)
        pytest.fail("the background child outlived the timeout")


def test_a_detached_child_holding_the_pipe_doesnt_hold_the_run(tmp_path):
    script = (
        "import subprocess\n"
        "child = subprocess.Popen(['sleep', '30'], start_new_session=True)\n"
        "print(child.pid, flush=True)\n"
    )
    started = time.monotonic()
    done = sandbox.run(
        [sys.executable, "-c", script],
        cwd=str(tmp_path),
        env=sandbox.candidate_env(str(tmp_path)),
        timeout_s=10,
        sandbox=sandbox.sandbox_for(0),
    )
    elapsed = time.monotonic() - started
    detached = int(done.stdout.split()[0])
    try:
        assert done.returncode == 0
        assert elapsed < sandbox.DRAIN_GRACE_S + 4
    finally:
        try:
            os.kill(detached, signal.SIGKILL)
        except ProcessLookupError:
            pass


def test_a_stopped_run_kills_its_group_and_says_it_was_stopped(tmp_path):
    control = sandbox.Control()
    timer = threading.Timer(0.3, control.stop.set)
    timer.start()
    started = time.monotonic()
    with pytest.raises(sandbox.Stopped) as err:
        sandbox.run(
            ["bash", "-c", "echo started; sleep 30 & wait"],
            cwd=str(tmp_path),
            env=sandbox.candidate_env(str(tmp_path)),
            timeout_s=30,
            sandbox=sandbox.sandbox_for(0),
            control=control,
        )
    assert time.monotonic() - started < 10
    assert err.value.output.startswith("started")
    assert control.pid is not None and sandbox.group_gone(control.pid, wait_s=5)


def test_a_stop_set_after_the_run_exits_changes_nothing(tmp_path):
    control = sandbox.Control()
    done = sandbox.run(["true"], cwd=str(tmp_path), env=sandbox.candidate_env(str(tmp_path)), timeout_s=10,
                       sandbox=sandbox.sandbox_for(0), control=control)
    control.stop.set()
    assert done.returncode == 0


def test_a_group_is_gone_when_only_zombies_are_left(tmp_path):
    def proc(pid: int, stat_line: str) -> None:
        (tmp_path / str(pid)).mkdir()
        (tmp_path / str(pid) / "stat").write_text(stat_line)

    proc(101, "101 (python3) S 1 4242 4242 0 -1")
    proc(102, "102 (a (b) c) Z 1 4242 4242 0 -1")
    proc(103, "103 (sleep) R 1 999 999 0 -1")
    (tmp_path / "self").mkdir()
    assert sandbox._group_members(4242, str(tmp_path)) == [101]
    assert sandbox.group_gone(4242, wait_s=0, proc_root=str(tmp_path)) is False
    shutil.rmtree(tmp_path / "101")
    assert sandbox.group_gone(4242, wait_s=0, proc_root=str(tmp_path)) is True


def test_each_stream_keeps_at_most_its_cap(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "STREAM_KEEP_BYTES", 1000)
    done = sandbox.run(
        [sys.executable, "-c", "import sys; sys.stdout.write('x' * 200000); sys.stderr.write('y' * 5000)"],
        cwd=str(tmp_path),
        env=sandbox.candidate_env(str(tmp_path)),
        timeout_s=10,
        sandbox=sandbox.sandbox_for(0),
    )
    assert done.stdout == "x" * 1000
    assert done.stderr == "y" * 1000


def test_a_run_kills_and_reaps_whatever_its_slot_uid_left_running(monkeypatch, tmp_path):
    killed = []
    reaped = []
    monkeypatch.setattr(sandbox, "_kill_uid_pids", lambda uid, proc_root="/proc": killed.append(uid) or [4242])
    monkeypatch.setattr(sandbox, "reap", lambda pids: reaped.extend(pids))
    box = sandbox.Sandbox(index=0, uid=None, gid=None)
    sandbox.run(["true"], cwd=str(tmp_path), env={"PATH": "/usr/bin:/bin"}, timeout_s=5, sandbox=box)
    assert killed == []
    monkeypatch.setattr(sandbox.subprocess, "Popen", _popen_without_uid(sandbox.subprocess.Popen))
    box = sandbox.Sandbox(index=0, uid=10001, gid=10000)
    sandbox.run(["true"], cwd=str(tmp_path), env={"PATH": "/usr/bin:/bin"}, timeout_s=5, sandbox=box)
    assert killed == [10001]
    assert reaped == [4242]


def _popen_without_uid(real):
    # The kwargs that need root are dropped, so the run itself works here.
    def popen(cmd, **kwargs):
        for key in ("user", "group", "extra_groups", "umask"):
            kwargs.pop(key, None)
        return real(cmd, **kwargs)

    return popen


# ---- release -----------------------------------------------------------------------------


def _fake_proc(root, entries):
    for pid, uid in entries.items():
        (root / str(pid)).mkdir()
        (root / str(pid) / "status").write_text(f"Name:\tx\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n")
    (root / "self").mkdir()


def test_kill_uid_ends_only_the_slots_processes(monkeypatch, tmp_path):
    _fake_proc(tmp_path, {101: 10001, 102: 0, 103: 10001, 104: 10002})
    killed = []
    monkeypatch.setattr(sandbox.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    assert sandbox.kill_uid(10001, proc_root=str(tmp_path)) == 2
    assert sorted(killed) == [(101, signal.SIGKILL), (103, signal.SIGKILL)]


def test_sweep_removes_what_the_uid_owns_without_following_links(tmp_path):
    shared = tmp_path / "tmp"
    outside = tmp_path / "outside"
    shared.mkdir()
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    (shared / "left.txt").write_text("x")
    (shared / "dir").mkdir()
    (shared / "dir" / "inner.txt").write_text("x")
    (shared / "link").symlink_to(outside)
    removed = sandbox.sweep_uid_files(str(shared), os.getuid())
    assert removed == 3
    assert list(shared.iterdir()) == []
    assert (outside / "keep.txt").read_text() == "keep"


def test_sweep_leaves_other_owners_alone(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "b.txt").write_text("x")
    assert sandbox.sweep_uid_files(str(tmp_path), os.getuid() + 12345) == 0
    assert (tmp_path / "d" / "b.txt").exists()


def test_release_skips_cleanup_without_a_uid(monkeypatch):
    monkeypatch.setattr(sandbox, "_kill_uid_pids", lambda *a, **k: pytest.fail("kill"))
    sandbox.release(sandbox.Sandbox(index=0, uid=None, gid=None))


def test_release_cleans_up_the_slot_uid(monkeypatch):
    calls = []
    monkeypatch.setattr(sandbox, "_kill_uid_pids", lambda uid, proc_root="/proc": calls.append(("kill", uid)) or [77])
    monkeypatch.setattr(sandbox, "reap", lambda pids: calls.append(("reap", list(pids))))
    monkeypatch.setattr(sandbox, "sweep_uid_files", lambda root, uid: calls.append(("sweep", root, uid)))
    sandbox.release(sandbox.Sandbox(index=0, uid=10001, gid=10000))
    assert calls == [("kill", 10001), ("reap", [77])] + [("sweep", root, 10001) for root in sandbox.SHARED_TEMP_DIRS]


def test_reap_collects_killed_children_and_skips_other_pids():
    child = subprocess.Popen(["sleep", "30"])
    os.kill(child.pid, signal.SIGKILL)
    assert sandbox.reap([child.pid, os.getpid()]) == 1
    with pytest.raises(ChildProcessError):
        os.waitpid(child.pid, os.WNOHANG)
    child.returncode = -9  # already collected; keeps Popen from waiting again


# ---- the slot pool -------------------------------------------------------------------------


def test_the_pool_hands_out_each_slot_once():
    pool = sandbox.SlotPool(3)
    slots = [pool.try_acquire() for _ in range(3)]
    assert sorted(s.index for s in slots) == [0, 1, 2]
    assert pool.try_acquire() is None
    assert pool.in_use() == 3
    pool.release(slots[1])
    again = pool.try_acquire()
    assert again.index == 1
    for slot in (slots[0], slots[2], again):
        pool.release(slot)
    assert pool.in_use() == 0


def test_a_failed_cleanup_still_frees_the_slot(monkeypatch):
    def broken(_box):
        raise OSError("cleanup failed")

    monkeypatch.setattr(sandbox, "release", broken)
    pool = sandbox.SlotPool(1)
    slot = pool.try_acquire()
    pool.release(slot)
    assert pool.try_acquire() is not None


def test_the_scratch_root_lets_others_enter_but_not_list_when_root(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(sandbox, "drops_privileges", lambda: True)
    monkeypatch.setattr(sandbox.os, "chown", lambda *a: None)
    root = sandbox._scratch_root()
    assert stat.S_IMODE(os.stat(root).st_mode) == 0o711


@pytest.mark.skipif(sys.platform != "linux" or os.geteuid() != 0, reason="needs root on Linux")
def test_as_root_the_candidate_runs_as_its_slot_uid():  # pragma: no cover - image only
    code = "import os\ndef f():\n    return [os.getuid(), os.getgid(), os.getgroups()]\n"
    outcome = run_one(code, "python", {"kind": "function", "name": "f"}, {}, sandbox=sandbox.sandbox_for(2))
    assert outcome.return_value == [10003, 10000, []]


def _live_pids_of(uid: int) -> list[str]:
    live = []
    for pid in (p for p in os.listdir("/proc") if p.isdigit()):
        try:
            with open(f"/proc/{pid}/status") as fh:
                fields = dict(line.split(":", 1) for line in fh if ":" in line)
        except OSError:
            continue
        if int(fields["Uid"].split()[0]) == uid and not fields["State"].strip().startswith("Z"):
            live.append(pid)
    return live


@pytest.mark.skipif(sys.platform != "linux" or os.geteuid() != 0, reason="needs root on Linux")
def test_as_root_a_detached_child_is_killed_when_the_run_ends():  # pragma: no cover - image only
    code = (
        "import subprocess\n"
        "def f():\n"
        "    subprocess.Popen(['sleep', '300'], start_new_session=True)\n"
        "    return 1\n"
    )
    box = sandbox.sandbox_for(3)
    outcome = run_one(code, "python", {"kind": "function", "name": "f"}, {}, sandbox=box, timeout_s=10)
    assert outcome.return_value == 1
    assert _live_pids_of(box.uid) == []


@pytest.mark.skipif(sys.platform != "linux" or os.geteuid() != 0, reason="needs root on Linux")
def test_as_root_a_result_pointed_at_a_root_file_is_not_read():  # pragma: no cover - image only
    code = (
        "import os, sys\n"
        "def f():\n"
        "    os.symlink('/etc/shadow', sys.argv[2])\n"
        "    os._exit(0)\n"
    )
    outcome = run_one(code, "python", {"kind": "function", "name": "f"}, {}, sandbox=sandbox.sandbox_for(2))
    assert outcome.return_value is None
    assert outcome.error == "The program ended without returning a result."
    assert "root:" not in outcome.stdout + outcome.stderr
