"""Code-execution orchestrator. Spawns user code in a subprocess with a
language-specific wrapper. Per-kind dispatch logic lives in
backend/drivers/<language>/<kind>.py — this module only stitches the
wrapper, runs it, and reads its result.

The child runs through ``app.sandbox``: a private scratch directory,
a minimal environment, and the slot's own uid in the image. Input
goes in a file, not argv, so its size doesn't depend on the argv limit.
The result comes back in its own file, not on stdout, so however much
the program prints can't push the result out of the kept output.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

from app import sandbox as sandboxes
from drivers import get_driver


DEFAULT_TIMEOUT_S = 3
DEFAULT_OUTPUT_CAP_BYTES = 64 * 1024
RESULT_FILE = "result.json"
# The largest result the runner reads back, the same as each kept stream.
RESULT_MAX_BYTES = sandboxes.STREAM_KEEP_BYTES
NO_RESULT = "The program ended without returning a result."
RESULT_TOO_LARGE = "The result is over 4 MiB."


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
    sandbox: sandboxes.Sandbox | None = None,
) -> ExecutionOutcome:
    box = sandbox if sandbox is not None else sandboxes.sandbox_for(0)
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
        return _exec_python(code, snippet, input, timeout_s, output_cap_bytes, box)
    if language == "javascript":
        return _exec_javascript(code, snippet, input, timeout_s, output_cap_bytes, box)
    return ExecutionOutcome(
        stdout="", stderr="", return_value=None,
        error=f"Unsupported language: {language}",
        duration_ms=0, truncated=False,
    )


def _exec_python(code, snippet, inp, timeout_s, cap, box) -> ExecutionOutcome:
    wrapper = f"""
import json, sys, traceback

{code}

{snippet}

def _rounds_write_result(_text):
    with open(sys.argv[2], "w", encoding="utf-8") as _result_file:
        _result_file.write(_text)

try:
    with open(sys.argv[1], encoding="utf-8") as _input_file:
        _input = json.load(_input_file)
    _result = _drive(_input)
    _rounds_write_result(json.dumps(_result))
except Exception:
    _rounds_write_result("null")
    traceback.print_exc(file=sys.stderr)
"""
    return _run_subprocess(wrapper, ".py", [sys.executable], json.dumps(inp), timeout_s, cap, box)


def _exec_javascript(code, snippet, inp, timeout_s, cap, box) -> ExecutionOutcome:
    wrapper = f"""
{code}

{snippet}

(() => {{
  const _roundsFs = require("fs");
  try {{
    const _data = JSON.parse(_roundsFs.readFileSync(process.argv[2], "utf8"));
    const _result = _drive(_data);
    const _text = JSON.stringify(_result === undefined ? null : _result);
    _roundsFs.writeFileSync(process.argv[3], _text === undefined ? "null" : _text);
  }} catch (e) {{
    _roundsFs.writeFileSync(process.argv[3], "null");
    process.stderr.write((e && e.stack) || String(e));
  }}
}})();
"""
    return _run_subprocess(wrapper, ".js", ["node"], json.dumps(inp), timeout_s, cap, box)


def _run_subprocess(wrapper_src, suffix, cmd_prefix, input_json, timeout_s, cap, box) -> ExecutionOutcome:
    with sandboxes.scratch(box) as workdir:
        path = os.path.join(workdir, "main" + suffix)
        input_path = os.path.join(workdir, "input.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(wrapper_src)
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(input_json)
        sandboxes.hand_over(workdir, box)
        return _run_in(workdir, path, input_path, cmd_prefix, timeout_s, cap, box)


def _run_in(workdir, path, input_path, cmd_prefix, timeout_s, cap, box) -> ExecutionOutcome:
    start = time.monotonic()
    result_path = os.path.join(workdir, RESULT_FILE)
    try:
        proc = sandboxes.run(
            cmd_prefix + [path, input_path, result_path],
            cwd=workdir,
            env=sandboxes.candidate_env(workdir),
            timeout_s=timeout_s,
            sandbox=box,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        stdout = proc.stdout
        stderr = proc.stderr
        truncated = _over_cap(stdout, cap) or _over_cap(stderr, cap)

        payload, too_large = _read_result(result_path, box)
        if payload is None:
            return ExecutionOutcome(
                stdout=_cap(stdout, cap),
                stderr=_cap(stderr, cap),
                return_value=None,
                error=RESULT_TOO_LARGE if too_large else (stderr.strip() or NO_RESULT),
                duration_ms=duration_ms,
                truncated=truncated,
            )

        try:
            return_value = json.loads(payload) if payload.strip() else None
        except json.JSONDecodeError:
            return_value = None

        error = stderr.strip() if proc.returncode != 0 or "Traceback" in stderr else None
        return ExecutionOutcome(
            stdout=_cap(stdout, cap),
            stderr=_cap(stderr, cap),
            return_value=return_value,
            error=error,
            duration_ms=duration_ms,
            truncated=truncated,
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        return ExecutionOutcome(
            stdout="", stderr="", return_value=None,
            error=f"Time limit exceeded ({timeout_s}s)",
            duration_ms=duration_ms, truncated=False,
        )


def _read_result(path: str, box: sandboxes.Sandbox) -> tuple[str | None, bool]:
    """The result the wrapper wrote, and whether it was over
    RESULT_MAX_BYTES. Only a regular file counts, owned by the run's uid
    when it has one, and a symlink is never followed, so the run can't
    point the runner at another file. The run's processes are gone by
    now, so nothing changes the file while it's read."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return None, False
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or (box.uid is not None and info.st_uid != box.uid):
            return None, False
        chunks: list[bytes] = []
        size = 0
        while size <= RESULT_MAX_BYTES:
            chunk = os.read(fd, min(64 * 1024, RESULT_MAX_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
    finally:
        os.close(fd)
    if size > RESULT_MAX_BYTES:
        return None, True
    return b"".join(chunks).decode("utf-8", errors="replace"), False


def _cap(s: str, n: int) -> str:
    if len(s.encode("utf-8", errors="ignore")) <= n:
        return s
    b = s.encode("utf-8", errors="ignore")[:n]
    return b.decode("utf-8", errors="ignore")


def _over_cap(s: str, n: int) -> bool:
    return len(s.encode("utf-8", errors="ignore")) > n
