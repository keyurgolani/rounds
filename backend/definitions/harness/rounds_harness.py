"""The result channel for a Rounds harness driver (harness-revision/v1).

A driver is the harness-owned program a revision's ``grade`` argv runs. It
calls ``protect()`` before it starts any child, so the kernel marks it
non-dumpable and a process running as the same uid can't open
``/proc/<pid>/fd/3``, read its memory, or trace it. It then reports one
``{id, outcome, reason}`` line per expected result on fd 3, which only it
holds: ``run_child`` starts the candidate's code with every descriptor past
stderr closed. The server reads fd 3 and computes ``passed`` and ``score``;
whatever a child prints is never a result.

Outside Linux, on a developer's machine, there's no prctl and ``protect()``
reports that it couldn't protect the channel.

The compiler (backend/definitions/build.py) copies this file into each
revision as ``harness/rounds_harness.py``, so its bytes are part of the
revision's checksum.
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
from dataclasses import dataclass

RESULT_FD = 3
OUTCOMES = ("passed", "failed", "not-run")
REASONS = ("ok", "assertion", "exception", "timeout", "no-result", "bad-result")
PR_SET_DUMPABLE = 4
CHILD_PATH = "/usr/local/bin:/usr/bin:/bin"
# The most of a child's output a driver keeps to read its answer.
CHILD_OUTPUT_MAX = 256 * 1024


class Unprotected(RuntimeError):
    """The kernel refused to make the driver non-dumpable."""


def protect() -> bool:
    """Marks this process non-dumpable. True once it is; False outside
    Linux. Raises Unprotected when Linux refuses, so nothing runs."""
    if not sys.platform.startswith("linux"):
        return False
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) != 0:
        raise Unprotected(os.strerror(ctypes.get_errno()))
    return True


def dumpable() -> bool | None:
    """This process's dumpable flag from /proc, or None outside Linux."""
    try:
        with open("/proc/self/status", encoding="ascii") as status:
            for line in status:
                if line.startswith("Dumpable:"):
                    return line.split()[1] != "0"
    except OSError:
        return None
    return None


class Channel:
    """Writes result lines to fd 3."""

    def __init__(self, fd: int = RESULT_FD) -> None:
        os.fstat(fd)  # OSError when the server didn't open the channel
        os.set_inheritable(fd, False)
        self._fd = fd
        self._reported: set[str] = set()

    def report(self, result_id: str, outcome: str, reason: str) -> None:
        if outcome not in OUTCOMES or reason not in REASONS:
            raise ValueError("unknown outcome or reason")
        if result_id in self._reported:
            raise ValueError(f"{result_id} was already reported")
        self._reported.add(result_id)
        line = json.dumps({"id": result_id, "outcome": outcome, "reason": reason}) + "\n"
        os.write(self._fd, line.encode("utf-8"))


@dataclass(frozen=True)
class ChildResult:
    returncode: int | None
    stdout: str
    timed_out: bool


def run_child(argv: list[str], cwd: str, timeout_s: float) -> ChildResult:
    """Runs the candidate's side of a check in its own session. Only
    stdin, stdout, and stderr reach the child, its environment is a PATH
    and a HOME, and on timeout its whole process group is killed."""
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        env={"PATH": os.environ.get("PATH", CHILD_PATH), "HOME": cwd},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )
    try:
        out, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        proc.communicate()
        return ChildResult(None, "", True)
    finally:
        _kill_group(proc)
    stdout = out[:CHILD_OUTPUT_MAX].decode("utf-8", errors="replace")
    return ChildResult(proc.returncode, stdout, False)


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, 9)
    except OSError:
        pass


def last_json_line(text: str):
    """The last non-empty line of ``text`` as JSON, or None."""
    for line in reversed(text.splitlines()):
        if line.strip():
            try:
                return json.loads(line)
            except ValueError:
                return None
    return None
