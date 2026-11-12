"""Job spec v1, ``rounds.launcher-job/v1`` (ROUNDS-00A-L05): what the runner
sends the launcher for one job, checked before any worker exists.

The body is a 4-byte big-endian length, the spec as JSON, and then the
job's archive (``worker/manifest.py``). The spec has exactly these keys:

- ``version``: ``rounds.launcher-job/v1``;
- ``job_id``: opaque, ``[A-Za-z0-9_-]{8,64}``;
- ``kind``: one of #3's kinds (``execution/kinds.py``);
- ``definition``: #2's ``{track, slug, variant, version}``, or null;
- ``profile``: ``execution-default.v1``;
- ``deadline_ms``: the job's wall budget, at most what its kind is
  admitted for;
- ``archive``: ``{bytes, sha256}`` of the archive that follows.

A key outside these, the ones ``FORBIDDEN`` names among them (a worker's
image, environment, mounts, network, limits, command, user, privileges,
devices, runtime, or anything about an account), an unknown version, kind,
or profile, a deadline past the kind's budget, and an archive whose size,
checksum, layout, or manifest isn't v1's are all ``Rejected``, with a code
and before any engine call. Nothing in a spec reaches a worker's container:
``profile.create_body`` takes none of it.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
from dataclasses import dataclass
from typing import Any

from execution import kinds
from launcher import profile
from worker import manifest

VERSION = "rounds.launcher-job/v1"
CONTENT_TYPE = "application/vnd.rounds.launcher-job"
SPEC_MAX = 16 * 1024
LENGTH = struct.Struct(">I")
BODY_MAX = LENGTH.size + SPEC_MAX + manifest.ARCHIVE_MAX
KEYS = frozenset({"version", "job_id", "kind", "definition", "profile", "deadline_ms", "archive"})
# Keys a caller might reach for to change what a worker is. Every unknown
# key is refused anyway; these are named so their refusal is pinned.
FORBIDDEN = frozenset({
    "image", "env", "environment", "mounts", "binds", "volumes", "tmpfs", "network", "network_mode", "dns",
    "extra_hosts", "limits", "memory", "cpus", "pids", "ulimits", "argv", "command", "cmd", "entrypoint", "workdir",
    "user", "privileged", "cap_add", "capabilities", "security_opt", "devices", "runtime", "labels", "host_config",
    "account", "account_id", "user_id", "pseudonym", "quota", "tier",
})
JOB_ID = re.compile(r"[A-Za-z0-9_-]{8,64}")
SHA256 = re.compile(r"[0-9a-f]{64}")
TRACKS = ("coding", "ai-coding", "take-home")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
VARIANT = re.compile(r"[a-z]{1,16}")


class Rejected(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Spec:
    job_id: str
    kind: str
    definition: dict[str, Any] | None
    deadline_ms: int
    archive_bytes: int
    archive_sha256: str


def _int(value: Any, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def _definition(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"track", "slug", "variant", "version"}:
        raise Rejected("definition")
    if value["track"] not in TRACKS or not isinstance(value["slug"], str) or not SLUG.fullmatch(value["slug"]) \
            or len(value["slug"]) > 100:
        raise Rejected("definition")
    if not isinstance(value["variant"], str) or not VARIANT.fullmatch(value["variant"]):
        raise Rejected("definition")
    if not _int(value["version"], 1, 9999):
        raise Rejected("definition")
    return dict(value)


def parse(body: bytes) -> tuple[Spec, bytes]:
    """The spec and the archive, or Rejected."""
    if len(body) < LENGTH.size:
        raise Rejected("body")
    (size,) = LENGTH.unpack_from(body)
    if size > SPEC_MAX or len(body) < LENGTH.size + size:
        raise Rejected("spec_size")
    try:
        raw = json.loads(body[LENGTH.size:LENGTH.size + size].decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise Rejected("spec_json") from None
    if not isinstance(raw, dict):
        raise Rejected("spec_json")
    lowered = {str(key).lower() for key in raw}
    if lowered & FORBIDDEN:
        raise Rejected("forbidden_field")
    if set(raw) != KEYS:
        raise Rejected("unknown_field" if set(raw) - KEYS else "missing_field")
    if raw["version"] != VERSION:
        raise Rejected("version")
    if not isinstance(raw["job_id"], str) or not JOB_ID.fullmatch(raw["job_id"]):
        raise Rejected("job_id")
    if raw["kind"] not in kinds.KINDS:
        raise Rejected("kind")
    if raw["profile"] != profile.PROFILE_VERSION:
        raise Rejected("profile")
    kind = kinds.KINDS[raw["kind"]]
    if not _int(raw["deadline_ms"], 1, kind.max_budget_s * 1000):
        raise Rejected("deadline")
    archive_ref = raw["archive"]
    if not isinstance(archive_ref, dict) or set(archive_ref) != {"bytes", "sha256"}:
        raise Rejected("archive_ref")
    if not _int(archive_ref["bytes"], 1, manifest.ARCHIVE_MAX):
        raise Rejected("archive_size")
    if not isinstance(archive_ref["sha256"], str) or not SHA256.fullmatch(archive_ref["sha256"]):
        raise Rejected("archive_ref")
    archive = body[LENGTH.size + size:]
    if len(archive) != archive_ref["bytes"]:
        raise Rejected("archive_size")
    if hashlib.sha256(archive).hexdigest() != archive_ref["sha256"]:
        raise Rejected("archive_checksum")
    spec = Spec(job_id=raw["job_id"], kind=raw["kind"], definition=_definition(raw["definition"]),
                deadline_ms=raw["deadline_ms"], archive_bytes=archive_ref["bytes"], archive_sha256=archive_ref["sha256"])
    return spec, archive


def check(spec: Spec, archive: bytes) -> manifest.Job:
    """The archive's job, held to the kind's budgets, or Rejected."""
    kind = kinds.KINDS[spec.kind]
    try:
        return manifest.load(archive, max_parts=kind.max_parts, part_wall_ms=kinds.part_wall_s(spec.kind) * 1000,
                             deadline_ms=spec.deadline_ms)
    except manifest.Refused as err:
        raise Rejected(err.code) from None


def encode(job_id: str, kind: str, definition: dict[str, Any] | None, deadline_ms: int, archive: bytes) -> bytes:
    """A request body, as the runner's client builds it."""
    spec = json.dumps({
        "version": VERSION, "job_id": job_id, "kind": kind, "definition": definition,
        "profile": profile.PROFILE_VERSION, "deadline_ms": deadline_ms,
        "archive": {"bytes": len(archive), "sha256": hashlib.sha256(archive).hexdigest()},
    }, separators=(",", ":"), sort_keys=True).encode()
    return LENGTH.pack(len(spec)) + spec + archive
