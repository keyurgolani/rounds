"""Definition requests on the six execution routes (ROUNDS-00A-L02 step 2).

``ROUNDS_GATE_EXECUTION_DEFINITIONS`` decides what run, evaluate,
run-project, grade, and take-home run and submit take:

- ``legacy``: #1 stage 2's request shapes. Each route loads what it runs
  from PocketBase with the caller's token.
- ``enforce``: only definition requests. ``definition`` names one compiled
  version, ``{track, slug, variant, version}``; ``app.definitions``
  resolves it to an active, checksum-verified file before anything runs,
  and the rest of the request is the candidate's code, files, and typed
  inputs, none of which changes what runs or how it scores. A field from
  an older request shape answers 422 ``legacy_request_rejected`` with the
  field's name in ``detail``; any other unknown field answers 422
  ``invalid_request``.
- ``disabled``: admission answers 503 ``definitions_disabled`` first.

``parse`` reads a route's body for the gate's value, ``resolve`` returns
the named definition, ``check_paths`` keeps a submission's files off the
harness's paths, away from files that change how a harness runs, and
clear of each other, and ``run_step`` and ``grade`` run a harness
revision's argv in a slot: the visible run with the candidate's files
only, the grade with the harness files read-only and its fd 3 result
channel.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, TypeVar

from fastapi import Request
from pydantic import BaseModel, Field, ValidationError

from app import definitions, errors, gates, harness_results, limits, obs, sandbox
from app.errors import TypedError
from app.limits import StrictModel

M = TypeVar("M", bound=BaseModel)
N = TypeVar("N", bound=BaseModel)

# Fields of the request shapes before enforce, and the inputs the spec
# forbids a caller (spec lines 2505-2515). At enforce each answers 422
# legacy_request_rejected, so a stale tab gets a reload prompt.
LEGACY_FIELDS = frozenset({
    # #1 stage 2's shapes.
    "question_slug", "language", "checkpoint_index", "round_slug", "assignment_slug",
    # The shapes at 62d4eae.
    "entry", "test_cases", "expected", "filter",
    # Caller-chosen execution.
    "test_command", "command", "validators", "tests", "hidden_files", "harness_files", "env",
    "image", "network", "limits", "timeout_s",
})

TRACKS = ("coding", "ai-coding", "take-home")

# Files a submission can't carry, by why. Each answers 422
# path_not_allowed with a fixed sentence, never the path itself.
CONFIG_FILES = frozenset({
    "conftest.py", "pytest.ini", ".pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini",
    "package.json", "package-lock.json", ".npmrc", "tsconfig.json", "jsconfig.json",
})
STARTUP_FILES = frozenset({"sitecustomize.py", "usercustomize.py"})
RUNTIME_DIRS = frozenset({"node_modules", "__pycache__", ".pytest_cache"})
# Modules the harness, pytest, or a seeded round's code imports, beyond
# the standard library.
RUNTIME_MODULES = frozenset({
    "pytest", "_pytest", "pluggy", "iniconfig", "packaging", "py",
    "httpx", "httpcore", "h11", "anyio", "sniffio", "idna", "certifi",
    "rounds_harness",
})
SHADOWED_MODULES = frozenset(sys.stdlib_module_names) | RUNTIME_MODULES
PATH_DETAILS = {
    "harness": "A file uses a path the grader owns. Rename or remove it and try again.",
    "config": (
        "Test and package configuration files, such as conftest.py, pytest.ini, or package.json, "
        "can't be sent. Remove it and try again."
    ),
    "startup": "Python startup files, such as sitecustomize.py or a .pth file, can't be sent. Remove it and try again.",
    "shadow": "A file is named like a Python library module, such as json.py. Rename it and try again.",
    "conflict": "A file in this submission has the same name as a folder. Rename one of them and try again.",
    "name": "A file or folder name in this submission is too long. Shorten it and try again.",
}
# The longest file or folder name the runner's filesystem takes.
NAME_MAX_BYTES = 255
# A body nested deeper than this many arrays and objects answers 422
# invalid_request before any request model or fingerprint walks it.
MAX_JSON_DEPTH = 64

# The result channel's write end reaches the driver as this descriptor.
CHANNEL_FD = 3


class DefinitionRef(StrictModel):
    """The one compiled version a request runs."""

    track: Literal["coding", "ai-coding", "take-home"]
    slug: str = Field(pattern=limits.SLUG_PATTERN)
    variant: str = Field(pattern=r"^[a-z]{1,16}$")
    version: int = Field(ge=1, le=9999)


def mode() -> str:
    return gates.value("EXECUTION_DEFINITIONS")


def enforced() -> bool:
    return mode() == "enforce"


def _route(request: Request) -> str | None:
    return request.scope.get("path")


def _reject_legacy(request: Request, field: str) -> TypedError:
    obs.emit("definition.rejected", route=_route(request), code="legacy_request_rejected", field=field,
             service="runner")
    return TypedError(
        "legacy_request_rejected",
        f"This page sent {field}, which this server no longer takes. Reload the page to continue.",
    )


def _depth_within(value: Any, limit: int) -> bool:
    """True when ``value`` nests at most ``limit`` arrays and objects deep."""
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        children = item.values() if isinstance(item, dict) else item
        if depth > limit:
            return False
        stack.extend((child, depth + 1) for child in children if isinstance(child, (dict, list)))
    return True


async def parse(request: Request, legacy: type[M], definition: type[N]) -> M | N:
    """Step 5 for an execution route: the body as ``definition`` at
    enforce, otherwise as ``legacy``. Over a field limit is 413
    ``limit_exceeded``, anything else wrong, a body nested deeper than
    ``MAX_JSON_DEPTH`` included, 422 ``invalid_request``."""
    try:
        raw = json.loads(await request.body() or b"null")
    except (ValueError, RecursionError):
        raise TypedError("invalid_request") from None
    if isinstance(raw, (dict, list)) and not _depth_within(raw, MAX_JSON_DEPTH):
        raise TypedError("invalid_request")
    model: type[BaseModel] = legacy
    if enforced():
        model = definition
        if isinstance(raw, dict):
            stale = sorted(key for key in raw if key in LEGACY_FIELDS)
            if stale:
                raise _reject_legacy(request, stale[0])
    try:
        return model.model_validate(raw)  # type: ignore[return-value]
    except ValidationError as err:
        raise TypedError(errors.validation_code(err.errors())) from None


def rejected(request: Request, resolved: definitions.Resolved, code: str, detail: str | None = None) -> TypedError:
    """A typed refusal of a resolved definition's request, logged as a
    ``definition.rejected`` line with the definition and the code."""
    obs.emit("definition.rejected", definition=resolved.identity.label(), route=_route(request), code=code,
             service="runner")
    return TypedError(code, detail)


def resolve(request: Request, ref: DefinitionRef, track: str) -> definitions.Resolved:
    """The active definition ``ref`` names, or its typed failure. A
    reference to another track is not found, like any unknown one."""
    route = _route(request)
    if ref.track != track:
        identity = definitions.Identity(ref.track, ref.slug, ref.variant, ref.version)
        obs.emit("definition.rejected", definition=identity.label(), route=route, code="definition_not_found",
                 service="runner")
        raise TypedError("definition_not_found")
    return definitions.store().resolve(ref.track, ref.slug, ref.variant, ref.version, route=route)


# ---------------------------------------------------------------------------
# Paths a submission may use
# ---------------------------------------------------------------------------


def path_problem(path: str, harness_paths: frozenset[str]) -> str | None:
    """Why ``path`` can't be part of a submission, or None. ``path`` has
    already passed ``limits.check_files``."""
    parts = path.split("/")
    name = parts[-1].lower()
    if path in harness_paths or parts[0] == "harness":
        return "harness"
    if name in CONFIG_FILES or any(part.lower() in RUNTIME_DIRS for part in parts):
        return "config"
    if name in STARTUP_FILES or name.endswith(".pth"):
        return "startup"
    if path.lower().endswith(".py"):
        top = parts[0][:-3] if len(parts) == 1 else parts[0]
        if top in SHADOWED_MODULES:
            return "shadow"
    return None


def _folders(paths: Iterable[str]) -> set[str]:
    """Every folder the paths are in."""
    out: set[str] = set()
    for path in paths:
        parts = path.split("/")
        out.update("/".join(parts[:i]) for i in range(1, len(parts)))
    return out


def _encodes(text: str) -> bool:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def layout_problem(path: str, harness_paths: frozenset[str], folders: set[str]) -> str | None:
    """Why ``path`` can't be written beside the other files, or None:
    it's also a folder of another file, one of its folders is a harness
    file, or a name in it is longer than the filesystem takes.
    ``folders`` holds every folder of the submission's and the harness's
    files."""
    if path in folders or any(folder in harness_paths for folder in _folders([path])):
        return "conflict"
    if any(len(part.encode("utf-8")) > NAME_MAX_BYTES for part in path.split("/")):
        return "name"
    return None


def check_paths(request: Request, files: Mapping[str, str], resolved: definitions.Resolved) -> None:
    """422 ``path_not_allowed`` for the first file a submission can't
    carry or the runner can't write beside the others, and 422
    ``invalid_request`` for a path or contents that aren't text UTF-8 can
    hold (a lone surrogate). Everything here runs before a slot does, so
    a refusal refunds its charge."""
    if not all(_encodes(path) and _encodes(contents) for path, contents in files.items()):
        raise rejected(request, resolved, "invalid_request")
    harness = frozenset(item["path"] for item in resolved.document.get("files") or [])
    folders = _folders([*files, *harness])
    for path in sorted(files):
        problem = path_problem(path, harness) or layout_problem(path, harness, folders)
        if problem is not None:
            raise rejected(request, resolved, "path_not_allowed", PATH_DETAILS[problem])


# ---------------------------------------------------------------------------
# Running a harness revision's steps
# ---------------------------------------------------------------------------


def argv(step_argv: list[str]) -> list[str]:
    """A step's argv with its interpreter resolved: python3 is the
    runner's own Python, tsx and node come from PATH."""
    program, *rest = step_argv
    if program == "python3":
        return [sys.executable, *rest]
    return [shutil.which(program) or program, *rest]


def _write(workdir: str, path: str, contents: str, mode: int | None = None) -> None:
    target = os.path.join(workdir, path)
    os.makedirs(os.path.dirname(target) or workdir, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(contents)
    if mode is not None:
        os.chmod(target, mode)


def _lay_files(workdir: str, files: Mapping[str, str]) -> None:
    """The candidate's files. ``check_paths`` already refused any the
    runner can't write, so a write that fails here is the runner's own
    trouble, such as a full disk: 503 ``worker_unavailable``, which
    refunds the charge."""
    try:
        for path, contents in files.items():
            _write(workdir, path, contents)
    except (OSError, UnicodeError):
        raise TypedError("worker_unavailable") from None


def _lay_harness(workdir: str, files: list[dict[str, Any]]) -> None:
    """The harness files, written after the scratch is handed over: owned
    by the runner, files 0444 and directories 0755, so the candidate's
    uid can read them and change none."""
    try:
        for item in files:
            _write(workdir, item["path"], item["contents"])
        for item in files:
            directory = os.path.dirname(os.path.join(workdir, item["path"]))
            while directory.startswith(workdir) and directory != workdir:
                os.chmod(directory, 0o755)
                directory = os.path.dirname(directory)
            os.chmod(os.path.join(workdir, item["path"]), 0o444)
    except (OSError, UnicodeError):
        raise TypedError("worker_unavailable") from None


@dataclass(frozen=True)
class StepRun:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    duration_ms: int


def run_step(step: dict[str, Any], files: Mapping[str, str], slot: sandbox.Sandbox,
             extra_env: Mapping[str, str] | None = None) -> StepRun:
    """A visible run: the candidate's files only, the step's argv, and
    its wall time."""
    start = time.monotonic()
    with sandbox.scratch(slot) as workdir:
        _lay_files(workdir, files)
        sandbox.hand_over(workdir, slot)
        env = sandbox.candidate_env(workdir, {"PYTHONPATH": workdir, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                                              **(extra_env or {})})
        try:
            proc = sandbox.run(argv(step["argv"]), cwd=workdir, env=env, timeout_s=step["wall_s"], sandbox=slot)
        except subprocess.TimeoutExpired:
            return StepRun(None, "", "", True, int((time.monotonic() - start) * 1000))
    return StepRun(proc.returncode, proc.stdout, proc.stderr, False, int((time.monotonic() - start) * 1000))


@dataclass(frozen=True)
class Graded:
    score: harness_results.Score
    timed_out: bool
    duration_ms: int


def grade(checkpoint: dict[str, Any], harness_files: list[dict[str, Any]], files: Mapping[str, str],
          slot: sandbox.Sandbox, wall_s: int | None = None) -> Graded:
    """One checkpoint's grade: the candidate's files and the harness
    files in a fresh scratch, the grade argv with the result channel at
    fd 3, and the server's score of what came back on it. Nothing the
    driver or its children print is kept."""
    step = checkpoint["grade"]
    timeout = min(step["wall_s"], wall_s) if wall_s is not None else step["wall_s"]
    start = time.monotonic()
    with sandbox.scratch(slot) as workdir:
        _lay_files(workdir, files)
        sandbox.hand_over(workdir, slot)
        _lay_harness(workdir, harness_files)
        channel, timed_out = sandbox.run_with_channel(
            argv(step["argv"]),
            cwd=workdir,
            env=sandbox.candidate_env(workdir),
            timeout_s=timeout,
            sandbox=slot,
            channel_max=harness_results.CHANNEL_MAX_BYTES,
        )
    scored = harness_results.score(channel, checkpoint["results"], checkpoint["min_executed"],
                                   missing_reason="timeout" if timed_out else "no-result")
    return Graded(scored, timed_out, int((time.monotonic() - start) * 1000))
