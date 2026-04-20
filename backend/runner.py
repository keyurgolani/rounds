"""Shared code-execution primitive used by both /api/run and /api/evaluate.

Executes user code in a subprocess with:
- stdout / stderr capture (64 KB cap by default)
- function or class-based entry point (auto-detected from input shape)
- configurable timeout
- structured outcome (return value, captured streams, error, duration)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any


DEFAULT_TIMEOUT_S = 3
DEFAULT_OUTPUT_CAP_BYTES = 64 * 1024


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
    function_name: str,
    input: Any,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    output_cap_bytes: int = DEFAULT_OUTPUT_CAP_BYTES,
) -> ExecutionOutcome:
    """Execute user code once with the given input; capture outputs.

    `input` is passed via argv as JSON; the wrapper calls the function (or
    simulates a class-op sequence) and emits a final JSON result marker on
    stdout after the user's own prints. The marker is stripped before
    returning the captured stdout to the caller.
    """
    if language == "python":
        return _run_python(code, function_name, input, timeout_s, output_cap_bytes)
    if language in ("javascript", "js"):
        return _run_javascript(code, function_name, input, timeout_s, output_cap_bytes)
    return ExecutionOutcome(
        stdout="",
        stderr="",
        return_value=None,
        error=f"Unsupported language: {language}",
        duration_ms=0,
        truncated=False,
    )


_RESULT_MARKER = "__RUNNER_RESULT__"


def _run_python(code, fn_name, inp, timeout_s, cap) -> ExecutionOutcome:
    wrapper = f"""
import json, sys, traceback

{code}

def _invoke():
    raw = sys.argv[1]
    data = json.loads(raw)
    # Class-based sequence: {{ops, args}}. ops[0] must equal the class name.
    if isinstance(data, dict) and "ops" in data and "args" in data and data["ops"] and data["ops"][0] == {fn_name!r}:
        ops = data["ops"]
        args_list = data["args"]
        cls = globals()[{fn_name!r}]
        results = []
        instance = cls(*args_list[0])
        results.append(None)
        for op, args in zip(ops[1:], args_list[1:]):
            method = getattr(instance, op)
            results.append(method(*args))
        return results
    # Function call
    fn = globals()[{fn_name!r}]
    if isinstance(data, dict):
        return fn(**data)
    if isinstance(data, list):
        return fn(*data)
    return fn(data)

try:
    result = _invoke()
    sys.stdout.write("\\n" + {_RESULT_MARKER!r} + json.dumps(result))
except Exception:
    sys.stdout.write("\\n" + {_RESULT_MARKER!r} + "null")
    traceback.print_exc(file=sys.stderr)
"""
    return _exec_wrapper(wrapper, ".py", [sys.executable], json.dumps(inp), timeout_s, cap)


def _run_javascript(code, fn_name, inp, timeout_s, cap) -> ExecutionOutcome:
    wrapper = f"""
{code}

(() => {{
  try {{
    const data = JSON.parse(process.argv[2]);
    let result;
    if (data && typeof data === 'object' && !Array.isArray(data) && Array.isArray(data.ops) && Array.isArray(data.args) && data.ops[0] === {fn_name!r}) {{
      const Cls = eval({fn_name!r});
      const inst = new Cls(...data.args[0]);
      result = [null];
      for (let i = 1; i < data.ops.length; i++) {{
        const out = inst[data.ops[i]](...data.args[i]);
        result.push(out === undefined ? null : out);
      }}
    }} else {{
      const fn = eval({fn_name!r});
      if (data && typeof data === 'object' && !Array.isArray(data)) {{
        result = fn(...Object.values(data));
      }} else if (Array.isArray(data)) {{
        result = fn(...data);
      }} else {{
        result = fn(data);
      }}
    }}
    process.stdout.write("\\n{_RESULT_MARKER}" + JSON.stringify(result === undefined ? null : result));
  }} catch (e) {{
    process.stdout.write("\\n{_RESULT_MARKER}null");
    process.stderr.write((e && e.stack) || String(e));
  }}
}})();
"""
    return _exec_wrapper(wrapper, ".js", ["node"], json.dumps(inp), timeout_s, cap)


def _exec_wrapper(wrapper_src, suffix, cmd_prefix, input_json, timeout_s, cap) -> ExecutionOutcome:
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
        f.write(wrapper_src)
        path = f.name
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd_prefix + [path, input_json],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        raw_out = proc.stdout
        stderr = proc.stderr

        # Strip and parse the result marker.
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
            stdout="",
            stderr="",
            return_value=None,
            error=f"Time limit exceeded ({timeout_s}s)",
            duration_ms=duration_ms,
            truncated=False,
        )
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _cap(s: str, n: int) -> str:
    if len(s.encode("utf-8", errors="ignore")) <= n:
        return s
    # Byte-cap with UTF-8 safety — trim to last valid char boundary under n bytes.
    b = s.encode("utf-8", errors="ignore")[:n]
    return b.decode("utf-8", errors="ignore")


def _over_cap(s: str, n: int) -> bool:
    return len(s.encode("utf-8", errors="ignore")) > n
