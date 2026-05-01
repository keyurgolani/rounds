"""Code-execution orchestrator. Spawns user code in a subprocess with a
language-specific wrapper. Per-kind dispatch logic lives in
backend/drivers/<language>/<kind>.py — this module only stitches the
wrapper, runs it, and parses the result marker."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any

from drivers import get_driver


DEFAULT_TIMEOUT_S = 3
DEFAULT_OUTPUT_CAP_BYTES = 64 * 1024
_RESULT_MARKER = "__RUNNER_RESULT__"


@dataclass
class ExecutionOutcome:
    stdout: str
    stderr: str
    return_value: Any
    error: str | None
    duration_ms: int
    truncated: bool


def run_one(
    code: str,
    language: str,
    entry: dict,
    input: Any,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    output_cap_bytes: int = DEFAULT_OUTPUT_CAP_BYTES,
) -> ExecutionOutcome:
    try:
        driver = get_driver(language, entry.get("kind", ""))
    except KeyError as e:
        return ExecutionOutcome(
            stdout="", stderr="", return_value=None,
            error=str(e).strip("'"),
            duration_ms=0, truncated=False,
        )
    errors = driver.validate(entry)
    if errors:
        return ExecutionOutcome(
            stdout="", stderr="", return_value=None,
            error="; ".join(errors), duration_ms=0, truncated=False,
        )

    snippet = driver.wrapper_snippet(entry)
    if language == "python":
        return _exec_python(code, snippet, input, timeout_s, output_cap_bytes)
    if language == "javascript":
        return _exec_javascript(code, snippet, input, timeout_s, output_cap_bytes)
    return ExecutionOutcome(
        stdout="", stderr="", return_value=None,
        error=f"Unsupported language: {language}",
        duration_ms=0, truncated=False,
    )


def _exec_python(code, snippet, inp, timeout_s, cap) -> ExecutionOutcome:
    wrapper = f"""
import json, sys, traceback

{code}

{snippet}

try:
    _result = _drive(json.loads(sys.argv[1]))
    sys.stdout.write("\\n" + {_RESULT_MARKER!r} + json.dumps(_result))
except Exception:
    sys.stdout.write("\\n" + {_RESULT_MARKER!r} + "null")
    traceback.print_exc(file=sys.stderr)
"""
    return _run_subprocess(wrapper, ".py", [sys.executable], json.dumps(inp), timeout_s, cap)


def _exec_javascript(code, snippet, inp, timeout_s, cap) -> ExecutionOutcome:
    wrapper = f"""
{code}

{snippet}

(() => {{
  try {{
    const _data = JSON.parse(process.argv[2]);
    const _result = _drive(_data);
    process.stdout.write("\\n{_RESULT_MARKER}" + JSON.stringify(_result === undefined ? null : _result));
  }} catch (e) {{
    process.stdout.write("\\n{_RESULT_MARKER}null");
    process.stderr.write((e && e.stack) || String(e));
  }}
}})();
"""
    return _run_subprocess(wrapper, ".js", ["node"], json.dumps(inp), timeout_s, cap)


def _run_subprocess(wrapper_src, suffix, cmd_prefix, input_json, timeout_s, cap) -> ExecutionOutcome:
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
        f.write(wrapper_src)
        path = f.name
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd_prefix + [path, input_json],
            capture_output=True, text=True, timeout=timeout_s,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        raw_out = proc.stdout
        stderr = proc.stderr

        marker_idx = raw_out.rfind(_RESULT_MARKER)
        if marker_idx == -1:
            return ExecutionOutcome(
                stdout=_cap(raw_out, cap),
                stderr=_cap(stderr, cap),
                return_value=None,
                error=(stderr.strip() or "No result marker in output"),
                duration_ms=duration_ms,
                truncated=_over_cap(raw_out, cap) or _over_cap(stderr, cap),
            )

        user_stdout = raw_out[:marker_idx].rstrip("\n")
        payload = raw_out[marker_idx + len(_RESULT_MARKER):].strip()
        try:
            return_value = json.loads(payload) if payload else None
        except json.JSONDecodeError:
            return_value = None

        error = stderr.strip() if proc.returncode != 0 or "Traceback" in stderr else None
        return ExecutionOutcome(
            stdout=_cap(user_stdout, cap),
            stderr=_cap(stderr, cap),
            return_value=return_value,
            error=error,
            duration_ms=duration_ms,
            truncated=_over_cap(user_stdout, cap) or _over_cap(stderr, cap),
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        return ExecutionOutcome(
            stdout="", stderr="", return_value=None,
            error=f"Time limit exceeded ({timeout_s}s)",
            duration_ms=duration_ms, truncated=False,
        )
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _cap(s: str, n: int) -> str:
    if len(s.encode("utf-8", errors="ignore")) <= n:
        return s
    b = s.encode("utf-8", errors="ignore")[:n]
    return b.decode("utf-8", errors="ignore")


def _over_cap(s: str, n: int) -> bool:
    return len(s.encode("utf-8", errors="ignore")) > n
