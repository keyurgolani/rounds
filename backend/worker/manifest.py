"""The job archive and its manifest, ``rounds.worker-job/v1``
(ROUNDS-00A-L05).

A job's input is one uncompressed tar the runner builds from a server-owned
definition and the candidate's source:

- ``rounds-job.json``, the manifest: the parts, in order, and an optional
  verdict step;
- ``src/``, the files every part starts from;
- ``verdict/``, the files only the verdict step sees.

Each part runs one program from ``PROGRAMS`` with its own wall time, and may
name a result file under ``src/`` and ask for an fd 3 channel for a harness
driver. The verdict step runs once every part is done, with every other
process gone, and always gets fd 3.

The launcher loads the archive before any worker exists, and init loads it
again before anything runs, both through ``load``: only regular files and
directories, relative paths with no ``..``, at most ``ARCHIVE_MAX`` bytes
and ``MEMBERS_MAX`` members, and a manifest with no unknown key whose budgets
fit the job's. Anything else is ``Refused`` with a reason code.
"""
from __future__ import annotations

import io
import json
import re
import tarfile
from dataclasses import dataclass, field
from typing import Any, Mapping

VERSION = "rounds.worker-job/v1"
MANIFEST = "rounds-job.json"
SRC = "src"
VERDICT = "verdict"

# The programs a step may run, and where the worker image keeps each.
PROGRAMS = {
    "python3": "/usr/local/bin/python3",
    "node": "/opt/node/bin/node",
    "tsx": "/opt/rounds/node/node_modules/.bin/tsx",
    "bash": "/bin/bash",
}
ARCHIVE_MAX = 8 * 1024 * 1024
MEMBERS_MAX = 1024
MANIFEST_MAX = 64 * 1024
NAME_MAX = 255
PATH_MAX = 1024
ARGV_MAX = 64
ARG_MAX = 4096
MAX_PARTS = 64
PART_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}")

PART_KEYS = frozenset({"id", "argv", "wall_ms", "result", "channel"})
VERDICT_KEYS = frozenset({"argv", "wall_ms"})
TOP_KEYS = frozenset({"version", "parts", "verdict"})


class Refused(ValueError):
    """An archive or manifest outside v1. ``code`` names the rule."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Step:
    argv: tuple[str, ...]
    wall_ms: int


@dataclass(frozen=True)
class Part(Step):
    id: str = ""
    result: str | None = None
    channel: bool = False


@dataclass
class Job:
    parts: list[Part]
    verdict: Step | None
    src: dict[str, tuple[bytes, int]] = field(default_factory=dict)
    verdict_files: dict[str, tuple[bytes, int]] = field(default_factory=dict)

    @property
    def wall_ms(self) -> int:
        return sum(p.wall_ms for p in self.parts) + (self.verdict.wall_ms if self.verdict else 0)


def _int(value: Any, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def relative(path: str) -> str | None:
    """``path`` as a clean relative path, or None."""
    if not path or path.startswith("/") or "\\" in path or "\x00" in path or len(path.encode()) > PATH_MAX:
        return None
    parts = path.split("/")
    if parts[-1] == "":
        parts = parts[:-1]
    if not parts or any(p in ("", ".", "..") or len(p.encode()) > NAME_MAX for p in parts):
        return None
    return "/".join(parts)


def _argv(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= ARGV_MAX:
        raise Refused("manifest_argv")
    if not all(isinstance(a, str) and "\x00" not in a and len(a.encode()) <= ARG_MAX for a in value):
        raise Refused("manifest_argv")
    if value[0] not in PROGRAMS:
        raise Refused("manifest_program")
    return tuple(value)


def _wall(value: Any, part_wall_ms: int) -> int:
    if not _int(value, 1, part_wall_ms):
        raise Refused("manifest_wall")
    return value


def parse_manifest(data: bytes, *, max_parts: int, part_wall_ms: int, deadline_ms: int) -> tuple[list[Part], Step | None]:
    if len(data) > MANIFEST_MAX:
        raise Refused("manifest_size")
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise Refused("manifest_json") from None
    if not isinstance(doc, dict) or set(doc) != TOP_KEYS or doc["version"] != VERSION:
        raise Refused("manifest_version")
    raw_parts = doc["parts"]
    if not isinstance(raw_parts, list) or not 1 <= len(raw_parts) <= min(max_parts, MAX_PARTS):
        raise Refused("manifest_parts")
    parts: list[Part] = []
    seen: set[str] = set()
    for raw in raw_parts:
        if not isinstance(raw, dict) or set(raw) != PART_KEYS:
            raise Refused("manifest_part")
        if not isinstance(raw["id"], str) or not PART_ID.fullmatch(raw["id"]) or raw["id"] in seen:
            raise Refused("manifest_part_id")
        seen.add(raw["id"])
        result = raw["result"]
        if result is not None and (not isinstance(result, str) or relative(result) != result):
            raise Refused("manifest_result")
        if not isinstance(raw["channel"], bool):
            raise Refused("manifest_part")
        parts.append(Part(argv=_argv(raw["argv"]), wall_ms=_wall(raw["wall_ms"], part_wall_ms), id=raw["id"],
                          result=result, channel=raw["channel"]))
    verdict = None
    if doc["verdict"] is not None:
        raw = doc["verdict"]
        if not isinstance(raw, dict) or set(raw) != VERDICT_KEYS:
            raise Refused("manifest_verdict")
        verdict = Step(argv=_argv(raw["argv"]), wall_ms=_wall(raw["wall_ms"], part_wall_ms))
    total = sum(p.wall_ms for p in parts) + (verdict.wall_ms if verdict else 0)
    if total > deadline_ms:
        raise Refused("manifest_over_deadline")
    return parts, verdict


def load(archive: bytes, *, max_parts: int, part_wall_ms: int, deadline_ms: int) -> Job:
    """The job in ``archive``, or Refused."""
    if not 0 < len(archive) <= ARCHIVE_MAX:
        raise Refused("archive_size")
    try:
        tar = tarfile.open(fileobj=io.BytesIO(archive), mode="r:")
    except (tarfile.TarError, EOFError, OSError):
        raise Refused("archive_format") from None
    src: dict[str, tuple[bytes, int]] = {}
    verdict_files: dict[str, tuple[bytes, int]] = {}
    manifest: bytes | None = None
    total = 0
    with tar:
        try:
            members = tar.getmembers()
        except (tarfile.TarError, EOFError, OSError):
            raise Refused("archive_format") from None
        if len(members) > MEMBERS_MAX:
            raise Refused("archive_members")
        names: set[str] = set()
        for member in members:
            name = relative(member.name)
            if name is None:
                raise Refused("archive_path")
            if name in names:
                raise Refused("archive_duplicate")
            names.add(name)
            top = name.split("/", 1)[0]
            if member.isdir():
                if top not in (SRC, VERDICT):
                    raise Refused("archive_path")
                continue
            if not member.isreg():
                raise Refused("archive_member_type")
            total += member.size
            if total > ARCHIVE_MAX:
                raise Refused("archive_size")
            handle = tar.extractfile(member)
            data = handle.read() if handle is not None else b""
            mode = 0o755 if member.mode & 0o111 else 0o644
            if name == MANIFEST:
                manifest = data
            elif top == SRC and "/" in name:
                src[name.split("/", 1)[1]] = (data, mode)
            elif top == VERDICT and "/" in name:
                verdict_files[name.split("/", 1)[1]] = (data, mode)
            else:
                raise Refused("archive_path")
    if manifest is None:
        raise Refused("manifest_missing")
    for files in (src, verdict_files):
        folders = {"/".join(p.split("/")[:i]) for p in files for i in range(1, p.count("/") + 1)}
        if folders & set(files):
            raise Refused("archive_conflict")
    parts, verdict = parse_manifest(manifest, max_parts=max_parts, part_wall_ms=part_wall_ms, deadline_ms=deadline_ms)
    for part in parts:
        if part.result is not None and part.result in folders_of(src):
            raise Refused("manifest_result")
    if verdict is None and verdict_files:
        raise Refused("archive_verdict_files")
    return Job(parts=parts, verdict=verdict, src=src, verdict_files=verdict_files)


def folders_of(files: Mapping[str, Any]) -> set[str]:
    return {"/".join(p.split("/")[:i]) for p in files for i in range(1, p.count("/") + 1)}


def build(parts: list[dict[str, Any]], src: Mapping[str, bytes | str], verdict: dict[str, Any] | None = None,
          verdict_files: Mapping[str, bytes | str] | None = None) -> bytes:
    """A v1 archive, byte for byte the same for the same inputs: sorted
    members, no owners, and a fixed time. The runner's archives come from
    here."""
    doc = {"version": VERSION, "parts": parts, "verdict": verdict}
    entries: list[tuple[str, bytes, int]] = [(MANIFEST, json.dumps(doc, sort_keys=True).encode(), 0o644)]
    for top, files in ((SRC, src), (VERDICT, verdict_files or {})):
        for path in sorted(files):
            clean = relative(path)
            if clean is None or clean != path:
                raise Refused("archive_path")
            data = files[path]
            entries.append((f"{top}/{path}", data.encode() if isinstance(data, str) else data, 0o644))
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:", format=tarfile.PAX_FORMAT) as tar:
        for name, data, mode in entries:
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), mode, 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    return out.getvalue()
