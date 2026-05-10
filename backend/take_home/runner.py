"""Take-home subprocess runner. Materializes a candidate's submitted
file tree (plus the assignment's harness files) to a tempdir and
executes the assignment's `entrypoint` command via `bash -c`. Parses
the harness's JSON output (last well-formed object on stdout
containing `criteria` + `score` keys) into a structured result.

Mirrors backend/ai_coding/project_runner.py's posture: subprocess,
hard timeout, output cap, UTF-8 capture. For self-host deployments
this is the same trust posture as the existing code runner.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


DEFAULT_OUTPUT_CAP_BYTES = 256 * 1024


@dataclass
class HarnessCriterion:
    id: str
    passed: bool
    weight: float
    logs: str = ""


@dataclass
class TakeHomeRunResult:
    score: float                         # 0.0 - 1.0, weighted sum of passed criteria
    criteria: List[Dict[str, Any]] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    duration_ms: int = 0
    truncated: bool = False


def _cap(s: str, n: int) -> str:
    if len(s.encode("utf-8", errors="ignore")) <= n:
        return s
    return s.encode("utf-8", errors="ignore")[:n].decode("utf-8", errors="ignore")


def _over_cap(s: str, n: int) -> bool:
    return len(s.encode("utf-8", errors="ignore")) > n


def _materialize(workdir: str, files: Dict[str, str]) -> None:
    for rel, contents in files.items():
        if rel.startswith("/") or ".." in rel.split("/"):
            raise ValueError(f"unsafe file path: {rel}")
        target = os.path.join(workdir, rel)
        os.makedirs(os.path.dirname(target) or workdir, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(contents)


def _parse_harness_output(stdout: str) -> tuple[float, list[dict[str, Any]], str | None]:
    """Walk stdout lines from the bottom up. Return the first line that
    parses as a JSON object containing `criteria` AND `score` keys."""
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    for ln in reversed(lines):
        ln = ln.strip()
        if not (ln.startswith("{") and ln.endswith("}")):
            continue
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if "criteria" in obj and "score" in obj:
            score = obj.get("score")
            criteria = obj.get("criteria") or []
            try:
                score_f = float(score)
            except (TypeError, ValueError):
                return 0.0, [], "harness `score` is not a number"
            if not isinstance(criteria, list):
                return 0.0, [], "harness `criteria` is not a list"
            return score_f, list(criteria), None
    return 0.0, [], "couldn't find harness JSON in stdout (expected a {criteria,score,...} object on its own line)"


def run_assignment(
    files: Dict[str, str],
    entrypoint: str,
    timeout_s: int = 60,
    output_cap_bytes: int = DEFAULT_OUTPUT_CAP_BYTES,
) -> TakeHomeRunResult:
    """Execute `entrypoint` (a bash command string) inside a fresh
    tempdir populated with `files`. Returns a TakeHomeRunResult with
    parsed harness criteria + score, plus captured stdout/stderr."""
    workdir = tempfile.mkdtemp(prefix="takehome_")
    start = time.monotonic()
    try:
        _materialize(workdir, files)
        existing_pp = os.environ.get("PYTHONPATH", "")
        pythonpath = workdir if not existing_pp else f"{workdir}{os.pathsep}{existing_pp}"
        proc = subprocess.run(
            ["bash", "-c", entrypoint],
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
        score, criteria, parse_err = _parse_harness_output(stdout)
        return TakeHomeRunResult(
            score=score,
            criteria=criteria,
            stdout=stdout,
            stderr=stderr,
            error=parse_err if (parse_err and proc.returncode == 0) else (
                None if proc.returncode == 0 else (_cap(stderr.strip(), output_cap_bytes) or parse_err or "harness exited non-zero")
            ),
            duration_ms=duration_ms,
            truncated=truncated,
        )
    except subprocess.TimeoutExpired:
        return TakeHomeRunResult(
            score=0.0,
            stdout="",
            stderr="",
            error=f"Time limit exceeded ({timeout_s}s)",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as e:  # noqa: BLE001
        return TakeHomeRunResult(
            score=0.0,
            stdout="",
            stderr="",
            error=str(e),
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
