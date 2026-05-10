"""Project-level subprocess runner. Materializes a file tree to a temp
directory, executes a test command via `bash -c`, and parses pass/fail
counts from common test runner output (pytest, node --test).

Mirrors backend/runner.py's posture: subprocess, hard timeout, output cap.
For self-host deployments where the existing runner already executes
user code this way, the trust posture is the same."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Dict


DEFAULT_OUTPUT_CAP_BYTES = 256 * 1024


@dataclass
class ProjectRunResult:
    passed: bool
    passed_count: int
    failed_count: int
    stdout: str
    stderr: str
    error: str | None
    duration_ms: int
    truncated: bool = False


# Pytest summary lines look like:
#   verbose:  ===== 2 passed, 1 failed in 0.42s =====
#   quiet -q:  2 passed, 1 failed in 0.42s
# We anchor to the trailing " in <duration>s" pattern, which is unique to
# summary lines, plus a (passed|failed) count token, to avoid matching stray
# "N passed/failed" text inside failure messages.
_PYTEST_SUMMARY_LINE = re.compile(
    r"^(?:=+\s)?\d+\s+(?:passed|failed|error|errors|skipped|xfailed|xpassed|warnings?|deselected)\b.*?\sin\s\d",
    re.MULTILINE,
)
_PYTEST_COUNT = re.compile(r"(\d+)\s+(passed|failed)")
# node --test TAP output:  # pass 3  /  # fail 1
_NODE_SUMMARY = re.compile(r"^#\s+(pass|fail)\s+(\d+)\s*$", re.MULTILINE)


def _cap(s: str, n: int) -> str:
    """Cap a string at n bytes (UTF-8). Avoids cutting in the middle of a
    multi-byte sequence by decoding with errors='ignore'."""
    if len(s.encode("utf-8", errors="ignore")) <= n:
        return s
    return s.encode("utf-8", errors="ignore")[:n].decode("utf-8", errors="ignore")


def _over_cap(s: str, n: int) -> bool:
    return len(s.encode("utf-8", errors="ignore")) > n


def _parse_counts(language: str, stdout: str) -> tuple[int, int]:
    passed = 0
    failed = 0
    if language == "python":
        # Find the pytest summary line(s); take the last one (most recent run).
        summary_lines = _PYTEST_SUMMARY_LINE.findall(stdout)
        if not summary_lines:
            # Fallback for "no tests ran" or empty: stay at 0/0.
            return 0, 0
        last = summary_lines[-1]
        for m in _PYTEST_COUNT.finditer(last):
            n, kind = int(m.group(1)), m.group(2)
            if kind == "passed":
                passed = n
            elif kind == "failed":
                failed = n
    elif language in ("javascript", "typescript"):
        for m in _NODE_SUMMARY.finditer(stdout):
            kind, n = m.group(1), int(m.group(2))
            if kind == "pass":
                passed = n
            elif kind == "fail":
                failed = n
    return passed, failed


def _materialize(workdir: str, files: Dict[str, str]) -> None:
    for rel, contents in files.items():
        # Reject absolute paths and parent escapes.
        if rel.startswith("/") or ".." in rel.split("/"):
            raise ValueError(f"unsafe file path: {rel}")
        target = os.path.join(workdir, rel)
        os.makedirs(os.path.dirname(target) or workdir, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(contents)


def run_project(
    files: Dict[str, str],
    language: str,
    test_command: str,
    timeout_s: int = 30,
    output_cap_bytes: int = DEFAULT_OUTPUT_CAP_BYTES,
) -> ProjectRunResult:
    workdir = tempfile.mkdtemp(prefix="aicoding_")
    start = time.monotonic()
    try:
        _materialize(workdir, files)
        # PYTHONPATH=workdir makes the project root importable for
        # pytest/node test commands without requiring users to ship a
        # conftest.py or package marker. Pytest 8+ does not add the
        # rootdir to sys.path by default.
        existing_pp = os.environ.get("PYTHONPATH", "")
        pythonpath = workdir if not existing_pp else f"{workdir}{os.pathsep}{existing_pp}"
        proc = subprocess.run(
            ["bash", "-c", test_command],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": pythonpath,
            },
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        truncated = _over_cap(proc.stdout, output_cap_bytes) or _over_cap(proc.stderr, output_cap_bytes)
        stdout = _cap(proc.stdout, output_cap_bytes)
        stderr = _cap(proc.stderr, output_cap_bytes)
        passed_count, failed_count = _parse_counts(language, stdout)
        passed = proc.returncode == 0 and failed_count == 0
        return ProjectRunResult(
            passed=passed,
            passed_count=passed_count,
            failed_count=failed_count,
            stdout=stdout,
            stderr=stderr,
            error=None if passed else (_cap(stderr.strip(), output_cap_bytes) or None),
            duration_ms=duration_ms,
            truncated=truncated,
        )
    except subprocess.TimeoutExpired:
        return ProjectRunResult(
            passed=False,
            passed_count=0,
            failed_count=0,
            stdout="",
            stderr="",
            error=f"Time limit exceeded ({timeout_s}s)",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as e:  # noqa: BLE001
        return ProjectRunResult(
            passed=False,
            passed_count=0,
            failed_count=0,
            stdout="",
            stderr="",
            error=str(e),
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
