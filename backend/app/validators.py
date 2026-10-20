"""Runs validator predicates outside the API process (ROUNDS-00A-L02).

From step 1, in every ``ROUNDS_GATE_EXECUTION_DEFINITIONS`` state, a
validator matcher's predicate runs in ``app/validator_worker.py``, started
as ``python3 -I -S`` with an empty environment and its working directory
at ``/``. Nothing it could import or read comes from the runner's
settings, and ``-I`` keeps the current directory and ``PYTHON*`` variables
out of its path. One process checks every validator case of one request.

The process answers within ``TIMEOUT_S``; a timeout, a crash, or an
answer that isn't the expected shape fails every check in the batch with
a fixed error, never with the process's output.

TODO(ROUNDS-00A-L05): #5 runs this process in the code worker.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

WORKER = Path(__file__).resolve().parent / "validator_worker.py"
TIMEOUT_S = 10
# The worker's answer is one bool and an error per check.
ANSWER_MAX_BYTES = 1024 * 1024
UNAVAILABLE = "Validator error: the validator process didn't answer."


@dataclass(frozen=True)
class Check:
    code: Any
    input: Any
    output: Any


def command() -> list[str]:
    """The validator process's argv."""
    return [sys.executable, "-I", "-S", str(WORKER)]


def run(checks: Sequence[Check], timeout_s: float = TIMEOUT_S) -> list[tuple[bool, str | None]]:
    """``(passed, error)`` for each check, in order."""
    if not checks:
        return []
    request = json.dumps({"checks": [{"code": c.code, "input": c.input, "output": c.output} for c in checks]})
    failed = [(False, UNAVAILABLE)] * len(checks)
    try:
        proc = subprocess.run(
            command(),
            input=request,
            capture_output=True,
            text=True,
            env={},
            cwd="/",
            timeout=timeout_s,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return failed
    if proc.returncode != 0 or len(proc.stdout) > ANSWER_MAX_BYTES:
        return failed
    try:
        results = json.loads(proc.stdout)["results"]
    except (ValueError, KeyError, TypeError):
        return failed
    if not isinstance(results, list) or len(results) != len(checks):
        return failed
    out: list[tuple[bool, str | None]] = []
    for item in results:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], bool)
            or not (item[1] is None or isinstance(item[1], str))
        ):
            return failed
        out.append((item[0], item[1]))
    return out


def check_one(code: Any, input: Any, output: Any) -> tuple[bool, str | None]:
    return run([Check(code, input, output)])[0]
