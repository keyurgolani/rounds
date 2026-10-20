"""Candidate process containment until #5's workers (ROUNDS-00A-L01).

Every candidate process the runner starts goes through ``run``:

1. A minimal environment. Only the variables in ``candidate_env`` reach
   the child, so ``AI_KEY_SECRET``, ``PB_ADMIN_*``, and every other app
   setting stay in the runner.
2. A private scratch directory per run, mode 0700, which is also the
   child's ``HOME`` and ``TMPDIR``. It's removed when the run ends.
3. Its own uid when the runner is root, as it is in the image. Each of
   the replica's in-flight slots maps to one uid in
   ``CANDIDATE_UID_BASE``.., so concurrent runs can't read each other's
   scratch, and none of them can write ``/app`` or read the runner's
   ``/proc`` entries. When a run ends, any process still running as its
   uid is killed and anything it left in the shared temp directories is
   removed, so the next run on that slot starts clean.
4. Its own process session. The run waits for the process, not its
   output pipes, and when it exits or times out its group and, with a
   uid, everything running as that uid is killed.

Outside the image (local dev, CI) the runner isn't root, so step 3 is
skipped and children run as the current user.

TODO(ROUNDS-00A-L05): ephemeral no-secret, no-network workers replace
this module.
"""
from __future__ import annotations

import logging
import os
import shutil
import signal
import stat
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Mapping, Sequence

_log = logging.getLogger(__name__)

CANDIDATE_UID_BASE = 10001
CANDIDATE_GID = 10000
# Directories every uid can write. A run's leftovers there are removed
# when the run ends.
SHARED_TEMP_DIRS = ("/tmp", "/var/tmp", "/dev/shm")
_ENV_PASSTHROUGH = ("PATH",)
_DEFAULT_PATH = "/usr/local/bin:/usr/bin:/bin"


@dataclass(frozen=True)
class Sandbox:
    """One in-flight slot: its index and, when the runner is root, the
    uid and gid its candidate processes run as."""

    index: int
    uid: int | None
    gid: int | None


def drops_privileges() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


def sandbox_for(index: int) -> Sandbox:
    if drops_privileges():
        return Sandbox(index=index, uid=CANDIDATE_UID_BASE + index, gid=CANDIDATE_GID)
    return Sandbox(index=index, uid=None, gid=None)


def candidate_env(home: str, extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """The whole environment a candidate process gets."""
    env = {key: os.environ[key] for key in _ENV_PASSTHROUGH if os.environ.get(key)}
    env.setdefault("PATH", _DEFAULT_PATH)
    env.update(
        {
            "HOME": home,
            "TMPDIR": home,
            "USER": "candidate",
            "LOGNAME": "candidate",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    if extra:
        env.update(extra)
    return env


def _scratch_root() -> str:
    root = os.path.join(tempfile.gettempdir(), "rounds-scratch")
    os.makedirs(root, exist_ok=True)
    if drops_privileges():
        # Others may enter but not list, so run directories stay unguessable.
        os.chown(root, 0, 0)
        os.chmod(root, 0o711)
    return root


def _chown_tree(path: str, uid: int, gid: int) -> None:
    os.chown(path, uid, gid)
    for dirpath, dirnames, filenames in os.walk(path):
        for name in dirnames + filenames:
            os.lchown(os.path.join(dirpath, name), uid, gid)


@contextmanager
def scratch(sandbox: Sandbox) -> Iterator[str]:
    """A private working directory for one run, removed afterwards."""
    path = tempfile.mkdtemp(prefix="run-", dir=_scratch_root())
    os.chmod(path, 0o700)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def hand_over(path: str, sandbox: Sandbox) -> None:
    """Give the materialized scratch tree to the candidate uid."""
    if sandbox.uid is not None and sandbox.gid is not None:
        _chown_tree(path, sandbox.uid, sandbox.gid)


# Each stream keeps at most this much; callers cap their own output lower.
STREAM_KEEP_BYTES = 4 * 1024 * 1024
# How long to keep reading once the process is gone. A process that left
# the group and still holds the pipe doesn't hold the run any longer.
DRAIN_GRACE_S = 1.0
_READ_CHUNK = 64 * 1024


class _Drain(threading.Thread):
    """Reads one pipe to EOF, keeping the first ``keep`` bytes. The
    thread owns the pipe and closes it when it's done."""

    def __init__(self, stream, keep: int) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._keep = keep
        self._chunks: list[bytes] = []
        self._size = 0

    def run(self) -> None:
        fd = self._stream.fileno()
        try:
            while True:
                chunk = os.read(fd, _READ_CHUNK)
                if not chunk:
                    break
                room = self._keep - self._size
                if room > 0:
                    kept = chunk[:room]
                    self._chunks.append(kept)
                    self._size += len(kept)
        except OSError:
            pass
        finally:
            self._stream.close()

    def text(self) -> str:
        return b"".join(self._chunks).decode("utf-8", errors="replace")


def run(
    cmd: Sequence[str],
    *,
    cwd: str,
    env: Mapping[str, str],
    timeout_s: float,
    sandbox: Sandbox,
) -> subprocess.CompletedProcess:
    """Run ``cmd`` contained and wait for it, not for its output pipes.
    When it exits or times out, its process group and, with a uid, every
    process running as the slot's uid is killed. Raises
    ``subprocess.TimeoutExpired`` with the output so far on a timeout."""
    kwargs: dict = {
        "cwd": cwd,
        "env": dict(env),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
        "start_new_session": True,
    }
    if sandbox.uid is not None:
        kwargs.update(user=sandbox.uid, group=sandbox.gid, extra_groups=[], umask=0o077)
    proc = subprocess.Popen(list(cmd), **kwargs)
    drains = [_Drain(proc.stdout, STREAM_KEEP_BYTES), _Drain(proc.stderr, STREAM_KEEP_BYTES)]
    for drain in drains:
        drain.start()
    exited = False
    try:
        exited = _wait(proc, timeout_s)
    finally:
        _end(proc, sandbox)
    for drain in drains:
        drain.join(DRAIN_GRACE_S)
    stdout, stderr = (drain.text() for drain in drains)
    if not exited:
        raise subprocess.TimeoutExpired(list(cmd), timeout_s, output=stdout, stderr=stderr)
    return subprocess.CompletedProcess(list(cmd), proc.returncode, stdout, stderr)


def _wait(proc: subprocess.Popen, timeout_s: float) -> bool:
    """True when the process exits within ``timeout_s``. On Linux it's
    left unreaped, so its group id can't be reused before ``_end``
    kills the group."""
    if not hasattr(os, "waitid"):
        try:
            proc.wait(timeout=timeout_s)
            return True
        except subprocess.TimeoutExpired:
            return False
    deadline = time.monotonic() + timeout_s
    delay = 0.0005
    while True:
        try:
            if os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOWAIT | os.WNOHANG) is not None:
                return True
        except ChildProcessError:
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        delay = min(delay * 2, remaining, 0.05)
        time.sleep(delay)


def _end(proc: subprocess.Popen, sandbox: Sandbox) -> None:
    """Kill what the run left behind and reap it, the process itself
    first, so no orphan stays a zombie under the runner."""
    _kill_group(proc.pid)
    killed = _kill_uid_pids(sandbox.uid) if sandbox.uid is not None else []
    proc.wait()
    reap(pid for pid in killed if pid != proc.pid)


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def release(sandbox: Sandbox, proc_root: str = "/proc") -> None:
    """End anything still running as the slot's uid and remove what it
    left in the shared temp directories."""
    if sandbox.uid is None:
        return
    reap(_kill_uid_pids(sandbox.uid, proc_root=proc_root))
    for root in SHARED_TEMP_DIRS:
        sweep_uid_files(root, sandbox.uid)


def kill_uid(uid: int, proc_root: str = "/proc") -> int:
    """SIGKILL every process whose real uid is ``uid``. Linux only."""
    return len(_kill_uid_pids(uid, proc_root=proc_root))


def _kill_uid_pids(uid: int, proc_root: str = "/proc") -> list[int]:
    killed: list[int] = []
    try:
        entries = os.listdir(proc_root)
    except OSError:
        return killed
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(os.path.join(proc_root, entry, "status"), encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("Uid:"):
                        real_uid = int(line.split()[1])
                        break
                else:
                    continue
        except (OSError, ValueError, IndexError):
            continue
        if real_uid != uid:
            continue
        try:
            os.kill(int(entry), signal.SIGKILL)
            killed.append(int(entry))
        except (ProcessLookupError, PermissionError):
            pass
    return killed


REAP_WAIT_S = 0.5


def reap(pids) -> int:
    """Collect killed processes that ended up as the runner's own
    children. A candidate's orphans are reparented to the container's
    PID 1, the runner, and would stay zombies otherwise. Pids that
    aren't the runner's children are skipped."""
    reaped = 0
    deadline = time.monotonic() + REAP_WAIT_S
    for pid in pids:
        while True:
            try:
                done, _status = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                break
            if done:
                reaped += 1
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(0.01)
    return reaped


def sweep_uid_files(root: str, uid: int, max_depth: int = 4) -> int:
    """Remove the entries under ``root`` that ``uid`` owns, looking
    ``max_depth`` levels down. Symlinks are removed, never followed."""
    removed = 0
    try:
        entries = list(os.scandir(root))
    except OSError:
        return 0
    for entry in entries:
        try:
            info = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        is_dir = stat.S_ISDIR(info.st_mode)
        if info.st_uid != uid:
            if is_dir and max_depth > 1:
                removed += sweep_uid_files(entry.path, uid, max_depth - 1)
            continue
        try:
            if is_dir:
                shutil.rmtree(entry.path, ignore_errors=True)
            else:
                os.unlink(entry.path)
            removed += 1
        except OSError:
            continue
    return removed


class SlotPool:
    """The replica's in-flight cap. Each slot is one candidate uid."""

    def __init__(self, size: int) -> None:
        self._free = list(range(size))
        self._lock = threading.Lock()
        self.size = size

    def try_acquire(self) -> Sandbox | None:
        with self._lock:
            if not self._free:
                return None
            index = self._free.pop(0)
        return sandbox_for(index)

    def release(self, sandbox: Sandbox) -> None:
        try:
            release(sandbox)
        except Exception:  # noqa: BLE001
            _log.exception("candidate cleanup failed for slot %d", sandbox.index)
        with self._lock:
            self._free.append(sandbox.index)
            self._free.sort()

    def in_use(self) -> int:
        with self._lock:
            return self.size - len(self._free)
