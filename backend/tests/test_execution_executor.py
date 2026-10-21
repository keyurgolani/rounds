"""The legacy executor (ROUNDS-00A-L03): wall time, the output cap,
cancel, slots it shares with the routes, process groups, and cleanup that
is confirmed only once the scratch and the group are gone. Candidate
processes never see the worker secret."""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import time

import pytest

from app import sandbox
from execution import executor as ex
from execution.executor import InvalidSpec, LegacyExecutor, RunSpec, Starved

PY = sys.executable


@pytest.fixture
def legacy():
    out = LegacyExecutor(pool=sandbox.SlotPool(2))
    yield out
    out.close()


def _run(legacy, spec, stop=None):
    slot = legacy._pool.try_acquire()
    assert slot is not None
    try:
        return legacy.run(spec, slot, stop)
    finally:
        legacy._pool.release(slot)


def test_a_run_reports_what_the_child_did(legacy):
    spec = RunSpec("r1", [PY, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"])
    obs = _run(legacy, spec)
    assert (obs.exit_status, obs.stdout, obs.stderr, obs.limit, obs.canceled) == (3, "out\n", "err\n", None, False)
    assert obs.cleanup == "confirmed" and legacy.cleanup_status("r1") == "confirmed"
    assert obs.output_bytes == len("out\n") + len("err\n") and len(obs.output_sha256) == 64


def test_the_wall_budget_kills_the_run_and_names_the_limit(legacy):
    start = time.monotonic()
    obs = _run(legacy, RunSpec("r2", [PY, "-c", "import time; print('started', flush=True); time.sleep(30)"],
                               wall_s=0.5))
    assert time.monotonic() - start < 10
    assert (obs.exit_status, obs.limit, obs.canceled) == (None, "wall_time", False)
    assert obs.stdout == "started\n" and obs.cleanup == "confirmed"


def test_each_stream_shows_at_most_the_cap_and_says_it_cut(legacy):
    obs = _run(legacy, RunSpec("r3", [PY, "-c", "print('x' * 300000)"], output_cap=1000))
    assert obs.truncated is True and len(obs.stdout.encode()) == 1000
    # The operator view still gets what the child wrote.
    assert obs.output_bytes == 300001
    assert ex.output_cap() == 256 * 1024


def test_cancel_stops_a_run_at_once(legacy):
    slot = legacy._pool.try_acquire()
    result = {}
    spec = RunSpec("r4", [PY, "-c", "import time; time.sleep(30)"], wall_s=30)
    thread = threading.Thread(target=lambda: result.update(obs=legacy.run(spec, slot)))
    start = time.monotonic()
    thread.start()
    deadline = time.monotonic() + 10
    while legacy.cleanup_status("r4") != "pending" and time.monotonic() < deadline:
        time.sleep(0.01)
    while not legacy.cancel("r4") and time.monotonic() < deadline:
        time.sleep(0.01)
    thread.join(10)
    legacy._pool.release(slot)
    obs = result["obs"]
    assert obs.canceled is True and obs.limit is None and obs.exit_status is None
    assert time.monotonic() - start < 10 and obs.cleanup == "confirmed"
    assert legacy.cancel("r4") is False


def test_the_workers_stop_event_stops_a_run(legacy):
    stop = threading.Event()
    threading.Timer(0.3, stop.set).start()
    obs = _run(legacy, RunSpec("r5", [PY, "-c", "import time; time.sleep(30)"], wall_s=30), stop)
    assert obs.canceled is True and obs.wall_ms < 10_000


def test_the_whole_process_group_goes_with_the_run(legacy, tmp_path):
    marker = tmp_path / "grandchild.pid"
    code = (
        "import subprocess, sys, time\n"
        f"child = subprocess.Popen([{PY!r}, '-c', 'import time; time.sleep(60)'])\n"
        f"open({str(marker)!r}, 'w').write(str(child.pid))\n"
        "time.sleep(60)\n"
    )
    obs = _run(legacy, RunSpec("r6", [PY, "-c", code], wall_s=1))
    assert obs.limit == "wall_time" and obs.cleanup == "confirmed"
    pid = int(marker.read_text())
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not _alive(pid):
            break
        time.sleep(0.05)
    else:
        os.kill(pid, 9)
        pytest.fail("the grandchild outlived the run")


def _alive(pid: int) -> bool:
    """A zombie has exited; only its adopter hasn't collected it yet."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(state) and not state.startswith("Z")


def test_cleanup_is_unconfirmed_while_the_scratch_is_still_there(legacy, monkeypatch, tmp_path):
    kept = tmp_path / "kept"
    kept.mkdir()

    from contextlib import contextmanager

    @contextmanager
    def lasting(_slot):
        yield str(kept)

    monkeypatch.setattr(sandbox, "scratch", lasting)
    obs = _run(legacy, RunSpec("r7", [PY, "-c", "pass"]))
    assert obs.cleanup == "unconfirmed" and legacy.cleanup_status("r7") == "unconfirmed"


def test_an_unknown_run_is_never_confirmed(legacy):
    assert legacy.cleanup_status("nope") == "unconfirmed"


def test_files_land_in_the_scratch_and_nowhere_else(legacy):
    spec = RunSpec("r8", [PY, "-c", "print(open('pkg/a.txt').read())"], files={"pkg/a.txt": "hello"})
    assert _run(legacy, spec).stdout == "hello\n"
    for path in ("../escape.txt", "/etc/x", "a/../../b", "a\\b", ""):
        with pytest.raises(InvalidSpec):
            _run(legacy, RunSpec("r9", [PY, "-c", "pass"], files={path: "x"}))


def test_the_candidate_environment_has_no_worker_or_runner_secret(legacy, monkeypatch):
    monkeypatch.setenv("ROUNDS_EXECUTION_SECRET", "test-execution-key-placeholder-0123456789")
    monkeypatch.setenv("ROUNDS_ADMISSION_SECRET", "test-admission-key-placeholder-0123456789")
    obs = _run(legacy, RunSpec("r10", [PY, "-c", "import os, json; print(json.dumps(dict(os.environ)))"]))
    assert "ROUNDS_EXECUTION_SECRET" not in obs.stdout and "ROUNDS_ADMISSION_SECRET" not in obs.stdout
    assert "placeholder" not in obs.stdout
    assert "ROUNDS_EXECUTION_SECRET" not in sandbox.candidate_env("/tmp")


def test_slots_are_the_routes_slots_and_a_claim_waits_only_so_long():
    pool = sandbox.SlotPool(1)
    legacy = LegacyExecutor(pool=pool)
    try:
        held = pool.try_acquire()
        with pytest.raises(Starved):
            asyncio.run(legacy.acquire(0.2))
        pool.release(held)
        slot = asyncio.run(legacy.acquire(0.2))
        assert slot.index == 0 and legacy.free_slots() == 0
        asyncio.run(legacy.release(slot))
        assert legacy.free_slots() == 1
    finally:
        legacy.close()


def test_the_default_pool_is_the_admitted_routes_pool():
    from app import admission

    legacy = LegacyExecutor()
    try:
        assert legacy._pool is admission.pool() and legacy.slots == admission.REPLICA_SLOTS
    finally:
        legacy.close()


def test_a_closed_executor_stops_its_runs_and_is_not_healthy(legacy):
    assert legacy.healthy()
    legacy.close()
    assert not legacy.healthy()
