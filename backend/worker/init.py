"""A code worker's init (ROUNDS-00A-L05): PID 1 of every rounds-worker
container.

1. It refuses to run unless it is PID 1 on Linux, so the step that ends
   every other process can never run on a developer's machine.
2. Setup, before it reads anything: it makes itself non-dumpable, so no
   process of the same uid can open its ``/proc`` entries, trace it, or read
   its memory; it installs the added seccomp filter (``worker/seccomp.py``);
   and it lowers its core, file-size, and open-file limits to the profile's.
   Its children inherit the filter and the limits. A setup that fails runs
   nothing: the job's end says which step failed, and the launcher reports
   it as the infrastructure's failure.
3. It writes ``READY`` and waits for one job on stdin
   (``worker/frames.py``). A pre-started worker that gets none within
   ``IDLE_MAX_S`` exits.
4. Each part starts from a fresh ``/work/src``, ``/work/home``, and
   ``/work/tmp``, written from the copy of the archive init holds in its
   own memory, with ``/dev/shm`` empty and no other process alive. Init owns
   every pipe: a part's program gets ``/dev/null`` on stdin, a pipe each for
   stdout and stderr, and fd 3 only when it is a harness driver, and nothing
   else. Init streams what the part writes, cut at the part's output cap,
   and ends the part at its wall time, at its cap, or once its program
   exits; then it ends every other process and checks that ``/proc`` shows
   only itself.
5. The verdict step runs only after that check, with its files and fd 3
   created only then.
6. It writes the end summary and waits, at most ``LINGER_S``, to be
   destroyed.

Init runs single-threaded on one selector, so the hook each child runs
between fork and exec is safe.
"""
from __future__ import annotations

import hashlib
import os
import resource
import select
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from worker import frames, manifest, seccomp  # noqa: E402

WORK = "/work"
IDLE_MAX_S = 15 * 60
LINGER_S = 10
EMPTY_WAIT_S = 2.0
DRAIN_GRACE_S = 0.2
POLL_S = 0.05
READ_CHUNK = 64 * 1024
CORE_MAX = 0
FSIZE_MAX = 16 * 1024 * 1024
NOFILE_MAX = 256
# The most any part, and any job, may take, whatever its kind; the launcher
# holds each job to its own kind's, tighter, budgets.
PART_WALL_MAX_MS = 120_000
JOB_WALL_MAX_MS = 480_000
# A child's OOM score, so the kernel ends candidate processes, never init.
OOM_SCORE_ADJ = b"1000"
# A child's environment: exactly these names, from the container's own.
ENV_NAMES = ("PATH", "HOME", "TMPDIR", "LANG", "PYTHONPATH", "NODE_OPTIONS")
PR_GET_DUMPABLE, PR_SET_DUMPABLE = 3, 4

# Puts a harness driver's channel at fd 3, then runs the step.
AT_FD3 = (
    "import os, sys\n"
    "fd = int(sys.argv[1])\n"
    "if fd != 3:\n"
    "    os.dup2(fd, 3)\n"
    "    os.close(fd)\n"
    "os.execv(sys.argv[2], sys.argv[2:])\n"
)


# -- where things go ---------------------------------------------------------


@dataclass(frozen=True)
class Paths:
    work: str = WORK
    shm: str = "/dev/shm"

    @property
    def src(self) -> str:
        return os.path.join(self.work, "src")

    @property
    def home(self) -> str:
        return os.path.join(self.work, "home")

    @property
    def tmp(self) -> str:
        return os.path.join(self.work, "tmp")

    @property
    def verdict(self) -> str:
        return os.path.join(self.work, "verdict")


def _remove(path: str) -> None:
    """Removes ``path`` without following links. Everything under /work
    and /dev/shm belongs to init's own uid, so a mode a part set can be
    undone."""

    def retry(func: Callable[..., Any], target: str, _exc: BaseException) -> None:
        try:
            os.chmod(os.path.dirname(target), 0o700)
            if not os.path.islink(target):
                os.chmod(target, 0o700)
        except OSError:
            pass
        func(target)

    if os.path.islink(path) or not os.path.isdir(path):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        return
    _chmod(path)
    shutil.rmtree(path, onexc=retry)


def _chmod(path: str) -> None:
    # /work and /dev/shm themselves belong to the container's root.
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def empty(path: str) -> None:
    """Leaves ``path`` an empty directory, whatever was there."""
    if os.path.islink(path) or (os.path.lexists(path) and not os.path.isdir(path)):
        os.unlink(path)
    if os.path.isdir(path):
        if os.stat(path).st_uid == os.getuid():
            _chmod(path)
        for entry in os.scandir(path):
            _remove(entry.path)
    os.makedirs(path, mode=0o700, exist_ok=True)


def write_tree(root: str, files: Mapping[str, tuple[bytes, int]]) -> None:
    """Writes ``files`` under ``root``, which ``wipe`` just emptied."""
    for rel, (data, mode) in sorted(files.items()):
        target = os.path.join(root, rel)
        os.makedirs(os.path.dirname(target), mode=0o700, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(fd, view):]
        finally:
            os.close(fd)


def read_below(root: str, rel: str, limit: int) -> tuple[str, bytes, bool]:
    """``rel`` under ``root``, read without following any link: the result
    state, at most ``limit`` bytes, and whether there were more."""
    parts = rel.split("/")
    fds: list[int] = []
    try:
        try:
            fds.append(os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
            for name in parts[:-1]:
                fds.append(os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fds[-1]))
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fds[-1])
        except FileNotFoundError:
            return "none", b"", False
        except OSError:
            return "invalid", b"", False
        fds.append(fd)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return "invalid", b"", False
        chunks, size = [], 0
        while size <= limit:
            chunk = os.read(fd, min(READ_CHUNK, limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        data = b"".join(chunks)
        return "present", data[:limit], len(data) > limit
    finally:
        for fd in reversed(fds):
            os.close(fd)


# -- the process operations ---------------------------------------------------


def _set_oom_score() -> None:
    # Runs in the child between fork and exec.
    try:
        with open("/proc/self/oom_score_adj", "wb") as fh:
            fh.write(OOM_SCORE_ADJ)
    except OSError:
        pass


class SystemOps:
    """The process operations, for real, as PID 1 of a worker."""

    proc = "/proc"
    cgroup = "/sys/fs/cgroup"

    def setup(self) -> str:
        prctl = seccomp._prctl()
        if prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) != 0 or prctl(PR_GET_DUMPABLE, 0, 0, 0, 0) != 0:
            return "not_dumpable"
        try:
            seccomp.install()
        except seccomp.Unsupported:
            return "seccomp_failed"
        try:
            for which, value in ((resource.RLIMIT_CORE, CORE_MAX), (resource.RLIMIT_FSIZE, FSIZE_MAX),
                                 (resource.RLIMIT_NOFILE, NOFILE_MAX)):
                _soft, hard = resource.getrlimit(which)
                cap = value if hard == resource.RLIM_INFINITY else min(value, hard)
                resource.setrlimit(which, (cap, cap))
        except (OSError, ValueError):
            return "rlimits_failed"
        # PID 1 ignores a signal it has no handler for; Python's own handler
        # for SIGINT would let a candidate process end init.
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        return "ok"

    def spawn(self, argv: list[str], cwd: str, env: dict[str, str], stdout: int, stderr: int,
              keep: tuple[int, ...]) -> subprocess.Popen:
        return subprocess.Popen(
            argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, pass_fds=keep,
            close_fds=True, start_new_session=True, preexec_fn=_set_oom_score,
        )

    def kill_all(self) -> None:
        try:
            os.kill(-1, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def reap(self) -> dict[int, int]:
        out: dict[int, int] = {}
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                return out
            if pid == 0:
                return out
            out[pid] = status

    def others(self) -> list[int]:
        alive = []
        for entry in os.listdir(self.proc):
            if not entry.isdigit() or entry == "1":
                continue
            try:
                with open(os.path.join(self.proc, entry, "stat"), encoding="utf-8") as fh:
                    line = fh.read()
                state = line[line.rindex(")") + 2:].split()[0]
            except (OSError, ValueError, IndexError):
                continue
            if state not in ("Z", "X"):
                alive.append(int(entry))
        return alive

    def counters(self) -> dict[str, int]:
        """The cgroup's OOM kills and process-limit refusals so far."""
        return {
            "oom_kills": _event(os.path.join(self.cgroup, "memory.events"), "oom_kill"),
            "pid_limit_hits": _event(os.path.join(self.cgroup, "pids.events"), "max"),
        }

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def _event(path: str, key: str) -> int:
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                name, _, value = line.partition(" ")
                if name == key:
                    return int(value)
    except (OSError, ValueError):
        pass
    return 0


# -- one step ---------------------------------------------------------------


@dataclass
class StepRun:
    exit: int | None = None
    signal: int | None = None
    wall_ms: int = 0
    limit: str | None = None
    truncated: bool = False
    verdict: bytearray = field(default_factory=bytearray)
    verdict_truncated: bool = False
    policy: bool = False
    out: bytearray = field(default_factory=bytearray)
    err: bytearray = field(default_factory=bytearray)
    residue: bool = False
    oom_kills: int = 0
    pid_limit_hits: int = 0


def _decode(status: int | None) -> tuple[int | None, int | None]:
    if status is None:
        return None, None
    code = os.waitstatus_to_exitcode(status)
    return (None, -code) if code < 0 else (min(code, 255), None)


class Init:
    """Runs one job's parts and verdict step through ``ops``, writing
    frames with ``writer``."""

    def __init__(self, ops: Any, writer: frames.Writer, paths: Paths = Paths(),
                 programs: Mapping[str, str] = manifest.PROGRAMS, environ: Mapping[str, str] | None = None,
                 now: Callable[[], float] = time.monotonic) -> None:
        self.ops = ops
        self.writer = writer
        self.paths = paths
        self.programs = dict(programs)
        source = os.environ if environ is None else environ
        self.env = {name: source[name] for name in ENV_NAMES if name in source}
        self.now = now

    # -- the job ---------------------------------------------------------

    def run(self, job_id: str, job: manifest.Job) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []
        captured: list[tuple[bytes, bytes, bytes | None]] = []
        residue = False
        for index, part in enumerate(job.parts):
            entry, outputs, residue = self._part(index, part, job)
            entries.append(entry)
            captured.append(outputs)
            if residue:
                break
        verdict = None
        if job.verdict is not None and not residue:
            verdict = self._verdict(job, captured)
        elif job.verdict is not None:
            verdict = {"state": "skipped", "exit": None, "signal": None, "wall_ms": 0, "limit": None,
                       "truncated": False}
        return {"version": frames.END_VERSION, "job_id": job_id, "setup": "ok", "residue": residue,
                "parts": entries, "verdict": verdict}

    def _fresh(self, src: Mapping[str, tuple[bytes, int]]) -> None:
        # Everything a part could have written: all of /work, not only the
        # three directories, and /dev/shm.
        empty(self.paths.work)
        if os.path.isdir(self.paths.shm):
            for entry in os.scandir(self.paths.shm):
                try:
                    _remove(entry.path)
                except OSError:
                    pass
        for path in (self.paths.src, self.paths.home, self.paths.tmp):
            os.makedirs(path, mode=0o700, exist_ok=True)
        write_tree(self.paths.src, src)

    def _part(self, index: int, part: manifest.Part, job: manifest.Job):
        self._fresh(job.src)
        run = self._step(index, list(part.argv), self.paths.src, part.wall_ms, part.channel,
                         room=frames.PART_OUTPUT_CAP, emit=True)
        result_state, result = "none", None
        if part.result is not None and not run.residue:
            room = frames.PART_OUTPUT_CAP - len(run.out) - len(run.err)
            result_state, result, cut = read_below(self.paths.src, part.result, room)
            if cut:
                run.truncated = True
                run.limit = run.limit or "output"
            if result_state == "present":
                self.writer.frame(frames.RESULT, index, result)
        if part.channel and run.verdict:
            self.writer.frame(frames.VERDICT, index, bytes(run.verdict))
        entry = {
            "id": part.id, "exit": run.exit, "signal": run.signal, "wall_ms": run.wall_ms, "limit": run.limit,
            "truncated": run.truncated, "verdict_truncated": run.verdict_truncated, "result": result_state,
            "oom_kills": run.oom_kills, "pid_limit_hits": run.pid_limit_hits, "policy": run.policy,
        }
        return entry, (bytes(run.out), bytes(run.err), result if result_state == "present" else None), run.residue

    def _verdict(self, job: manifest.Job, captured: list[tuple[bytes, bytes, bytes | None]]) -> dict[str, Any]:
        # Every candidate process is gone: the last part's check saw /proc
        # hold only init. The verdict's files exist only from here.
        files = dict(job.verdict_files)
        for index, (out, err, result) in enumerate(captured):
            files[f".parts/{index}/out"] = (out, 0o644)
            files[f".parts/{index}/err"] = (err, 0o644)
            if result is not None:
                files[f".parts/{index}/result"] = (result, 0o644)
        self._fresh({})
        os.makedirs(self.paths.verdict, mode=0o700, exist_ok=True)
        write_tree(self.paths.verdict, files)
        step = job.verdict
        run = self._step(frames.JOB_PART, list(step.argv), self.paths.verdict, step.wall_ms, True, room=0,
                         emit=False)
        if run.verdict:
            self.writer.frame(frames.VERDICT, frames.JOB_PART, bytes(run.verdict))
        return {"state": "ran", "exit": run.exit, "signal": run.signal, "wall_ms": run.wall_ms, "limit": run.limit,
                "truncated": run.verdict_truncated}

    # -- one process tree --------------------------------------------------

    def _argv(self, argv: list[str], channel_fd: int | None) -> list[str]:
        program = self.programs[argv[0]]
        if channel_fd is None:
            return [program, *argv[1:]]
        return [self.programs["python3"], "-I", "-S", "-c", AT_FD3, str(channel_fd), program, *argv[1:]]

    def _step(self, part: int, argv: list[str], cwd: str, wall_ms: int, channel: bool, room: int,
              emit: bool) -> StepRun:
        run = StepRun()
        # No process from earlier is alive; this tree starts alone.
        if not self._settle():
            run.residue = True
            return run
        before = self.ops.counters()
        out_r, out_w = os.pipe()
        err_r, err_w = os.pipe()
        chan_r, chan_w = os.pipe() if channel else (None, None)
        start = self.now()
        popen = None
        try:
            popen = self.ops.spawn(self._argv(argv, chan_w), cwd, dict(self.env), out_w, err_w,
                                   (chan_w,) if chan_w is not None else ())
        except OSError:
            popen = None
        finally:
            for fd in (out_w, err_w, chan_w):
                if fd is not None:
                    os.close(fd)
        selector = selectors.DefaultSelector()
        streams = {out_r: frames.OUT, err_r: frames.ERR}
        if chan_r is not None:
            streams[chan_r] = frames.VERDICT
        for fd, kind in streams.items():
            os.set_blocking(fd, False)
            selector.register(fd, selectors.EVENT_READ, kind)
        statuses: dict[int, int] = {}
        try:
            if popen is not None:
                self._watch(run, popen.pid, part, selector, statuses, start + wall_ms / 1000, room, emit)
            self.ops.kill_all()
            if popen is not None:
                self._await(popen.pid, statuses)
        finally:
            for key in list(selector.get_map().values()):
                selector.unregister(key.fd)
                os.close(key.fd)
            selector.close()
        run.wall_ms = max(0, int((self.now() - start) * 1000))
        if not self._settle(statuses):
            run.residue = True
        if popen is not None:
            run.exit, run.signal = _decode(statuses.get(popen.pid))
            # The Popen object never reaps; init already did.
            popen.returncode = statuses.get(popen.pid, 0)
        run.policy = any(os.WIFSIGNALED(s) and os.WTERMSIG(s) == signal.SIGSYS for s in statuses.values())
        if run.limit is None and run.signal == signal.SIGXFSZ:
            run.limit = "files"
        after = self.ops.counters()
        run.oom_kills = max(0, after["oom_kills"] - before["oom_kills"])
        run.pid_limit_hits = max(0, after["pid_limit_hits"] - before["pid_limit_hits"])
        return run

    def _watch(self, run: StepRun, pid: int, part: int, selector: selectors.BaseSelector, statuses: dict[int, int],
               deadline: float, room: int, emit: bool) -> None:
        exited_at: float | None = None
        while True:
            now = self.now()
            if now >= deadline:
                run.limit = "wall_time"
                return
            if exited_at is not None and (not selector.get_map() or now - exited_at >= DRAIN_GRACE_S):
                return
            wait = min(POLL_S, deadline - now)
            for key, _events in selector.select(wait):
                try:
                    data = os.read(key.fd, READ_CHUNK)
                except BlockingIOError:
                    continue
                if not data:
                    selector.unregister(key.fd)
                    os.close(key.fd)
                    continue
                if key.data == frames.VERDICT:
                    space = frames.VERDICT_CAP - len(run.verdict)
                    run.verdict += data[:space]
                    run.verdict_truncated = run.verdict_truncated or len(data) > space
                    continue
                if not emit:
                    continue
                keep = data[:room]
                room -= len(keep)
                if keep:
                    (run.out if key.data == frames.OUT else run.err).extend(keep)
                    self.writer.frame(key.data, part, keep)
                if len(keep) < len(data):
                    run.truncated = True
                    run.limit = "output"
                    return
            statuses.update(self.ops.reap())
            if exited_at is None and pid in statuses:
                exited_at = self.now()

    def _await(self, pid: int, statuses: dict[int, int]) -> None:
        give_up = self.now() + EMPTY_WAIT_S
        while pid not in statuses and self.now() < give_up:
            statuses.update(self.ops.reap())
            if pid not in statuses:
                self.ops.sleep(0.005)

    def _settle(self, statuses: dict[int, int] | None = None) -> bool:
        """Ends every other process and reaps it; True once ``/proc`` shows
        none left."""
        give_up = self.now() + EMPTY_WAIT_S
        while True:
            self.ops.kill_all()
            reaped = self.ops.reap()
            if statuses is not None:
                for pid, status in reaped.items():
                    statuses.setdefault(pid, status)
            if not self.ops.others():
                return True
            if self.now() >= give_up:
                return False
            self.ops.sleep(0.01)


# -- the process -------------------------------------------------------------


def _end(job_id: str, setup: str) -> dict[str, Any]:
    return {"version": frames.END_VERSION, "job_id": job_id, "setup": setup, "residue": False, "parts": [],
            "verdict": None}


def serve(ops: Any, stdin: int, writer: frames.Writer, paths: Paths = Paths(),
          programs: Mapping[str, str] = manifest.PROGRAMS, environ: Mapping[str, str] | None = None,
          idle_s: float = IDLE_MAX_S) -> dict[str, Any] | None:
    """Sets up, says READY, takes one job, runs it, and writes its end.
    Answers the end, or None when no job came."""
    setup = ops.setup()
    writer.ready()
    readable, _, _ = select.select([stdin], [], [], idle_s)
    if not readable:
        return None
    job_id = ""
    try:
        header, archive = frames.read_input(lambda n: os.read(stdin, min(n, READ_CHUNK)), manifest.ARCHIVE_MAX)
        job_id = header["job_id"] if isinstance(header["job_id"], str) else ""
        if hashlib.sha256(archive).hexdigest() != header["archive_sha256"]:
            raise frames.Malformed("the archive's checksum")
        job = manifest.load(archive, max_parts=frames.MAX_PARTS, part_wall_ms=PART_WALL_MAX_MS,
                            deadline_ms=JOB_WALL_MAX_MS)
    except (frames.Malformed, manifest.Refused):
        setup = "input_invalid" if setup == "ok" else setup
        job = None
    if setup != "ok" or job is None:
        summary = _end(job_id, setup)
    else:
        summary = Init(ops, writer, paths, programs, environ).run(job_id, job)
    writer.end(summary)
    return summary


def main() -> int:
    if not sys.platform.startswith("linux") or os.getpid() != 1:
        sys.stderr.write("rounds-worker init runs only as PID 1 of a worker container.\n")
        return 2
    if serve(SystemOps(), 0, frames.Writer(1)) is not None:
        # The launcher takes its last measurements, then destroys the worker.
        time.sleep(LINGER_S)
    return 0


if __name__ == "__main__":
    sys.exit(main())
