"""Frame protocol v1 between a worker's init and the launcher
(ROUNDS-00A-L05).

Into the worker, on its stdin, the launcher writes ``INPUT``, a 4-byte
big-endian length, the input header (``rounds.worker-input/v1`` JSON), the
job archive, and then end of file.

Out of the worker, on its stdout, init writes ``READY`` once it is set up and
waiting, then frames. A frame is a type (1 byte), a part (1 byte), a length
(4 bytes, big-endian), and that many bytes:

- ``out`` and ``err``: what a part's processes wrote, as they wrote it;
- ``result``: the part's result file, read once its processes are gone;
- ``verdict``: what a harness driver, or the verdict step, wrote on fd 3;
- ``end``: init's summary, ``rounds.worker-end/v1`` JSON, once and last.

``part`` is the part's index in the job, or ``JOB_PART`` for the verdict
step. For each part, ``out``, ``err``, and ``result`` together carry at most
``PART_OUTPUT_CAP`` bytes, and ``verdict`` carries at most ``VERDICT_CAP``
of its own, so a flood on one stream never displaces the other. Init cuts
at those caps while it reads its children, and the launcher's ``Reader``
holds the stream to the same caps while it reads. Anything else is
``Malformed``: an unknown type or part, a frame past a cap, a part's frame
after the end, a second end, bytes after it, or an end that isn't its JSON.
"""
from __future__ import annotations

import json
import os
import struct
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

READY = b"RNDW\x01"
INPUT = b"RNDJ\x01"
INPUT_VERSION = "rounds.worker-input/v1"
END_VERSION = "rounds.worker-end/v1"

OUT, ERR, RESULT, VERDICT, END = 1, 2, 3, 4, 5
NAMES = {OUT: "out", ERR: "err", RESULT: "result", VERDICT: "verdict", END: "end"}
JOB_PART = 255
MAX_PARTS = 64

# #2's resource profile, output_bytes: what a part may show, out, err, and
# result together. tests/test_worker_frames.py keeps the two equal.
PART_OUTPUT_CAP = 256 * 1024
# A verdict channel holds at most 64 result lines, well under this.
VERDICT_CAP = 16 * 1024
END_MAX = 16 * 1024
INPUT_HEADER_MAX = 4096
JSON_DEPTH = 64
# The most one frame carries; init splits longer writes.
CHUNK = 64 * 1024

FRAME = struct.Struct(">BBI")
LENGTH = struct.Struct(">I")

# What ends a part early, as init reports it. #3's limit names.
PART_LIMITS = ("wall_time", "output", "files")
RESULT_STATES = ("none", "present", "invalid")
VERDICT_STATES = ("ran", "skipped")
# How a worker's setup went; anything but ok means nothing ran.
SETUP_STATES = ("ok", "not_dumpable", "seccomp_failed", "rlimits_failed", "input_invalid")


class Malformed(ValueError):
    """The worker's stream breaks protocol v1."""


# -- bounded JSON ----------------------------------------------------------


def depth_within(value: Any, limit: int = JSON_DEPTH) -> bool:
    """True when ``value`` nests at most ``limit`` arrays and objects deep."""
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        if not isinstance(item, (dict, list)):
            continue
        if depth > limit:
            return False
        children = item.values() if isinstance(item, dict) else item
        stack.extend((child, depth + 1) for child in children)
    return True


def loads(data: bytes, limit: int, depth: int = JSON_DEPTH) -> Any:
    """``data`` as JSON, refused past ``limit`` bytes or ``depth`` levels."""
    if len(data) > limit:
        raise Malformed("JSON past its size")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise Malformed("not JSON") from None
    if not depth_within(value, depth):
        raise Malformed("JSON nested too deep")
    return value


def dumps(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


# -- the input ---------------------------------------------------------------


def encode_input(job_id: str, archive: bytes, sha256: str) -> bytes:
    """What the launcher writes on a worker's stdin, before end of file."""
    header = dumps({"version": INPUT_VERSION, "job_id": job_id, "archive_bytes": len(archive),
                    "archive_sha256": sha256})
    return INPUT + LENGTH.pack(len(header)) + header + archive


def read_input(read: Callable[[int], bytes], archive_max: int) -> tuple[dict[str, Any], bytes]:
    """The input header and archive, read with ``read(n)`` (which answers
    at most n bytes, and b"" at end of file). Raises Malformed unless the
    stream is exactly one input and then end of file."""

    def exactly(n: int) -> bytes:
        chunks, got = [], 0
        while got < n:
            chunk = read(n - got)
            if not chunk:
                raise Malformed("the input ended early")
            chunks.append(chunk)
            got += len(chunk)
        return b"".join(chunks)

    if exactly(len(INPUT)) != INPUT:
        raise Malformed("not a worker input")
    (size,) = LENGTH.unpack(exactly(LENGTH.size))
    header = loads(exactly(size), INPUT_HEADER_MAX) if size <= INPUT_HEADER_MAX else None
    if not isinstance(header, dict) or set(header) != {"version", "job_id", "archive_bytes", "archive_sha256"}:
        raise Malformed("the input header")
    if header["version"] != INPUT_VERSION:
        raise Malformed("the input version")
    count = header["archive_bytes"]
    if not isinstance(count, int) or isinstance(count, bool) or not 0 < count <= archive_max:
        raise Malformed("the archive size")
    archive = exactly(count)
    if read(1):
        raise Malformed("bytes after the input")
    return header, archive


# -- frames out of the worker -------------------------------------------------


def encode(kind: int, part: int, payload: bytes = b"") -> bytes:
    if kind not in NAMES or not (0 <= part < MAX_PARTS or part == JOB_PART):
        raise ValueError("not a frame")
    return FRAME.pack(kind, part, len(payload)) + payload


class Writer:
    """Init's side: writes frames to a file descriptor, in chunks of at
    most ``CHUNK`` bytes, and blocks until each is written."""

    def __init__(self, fd: int) -> None:
        self._fd = fd

    def _write(self, data: bytes) -> None:
        view = memoryview(data)
        while view:
            written = os.write(self._fd, view)
            view = view[written:]

    def ready(self) -> None:
        self._write(READY)

    def frame(self, kind: int, part: int, payload: bytes) -> None:
        for start in range(0, max(len(payload), 1), CHUNK):
            self._write(encode(kind, part, payload[start:start + CHUNK]))

    def end(self, summary: dict[str, Any]) -> None:
        data = dumps(summary)
        if len(data) > END_MAX:
            raise ValueError("the end summary is past its size")
        self._write(encode(END, JOB_PART, data))


@dataclass
class PartStreams:
    """What one part's frames carried."""

    out: bytearray = field(default_factory=bytearray)
    err: bytearray = field(default_factory=bytearray)
    result: bytearray | None = None
    verdict: bytearray | None = None

    def shown(self) -> int:
        return len(self.out) + len(self.err) + (len(self.result) if self.result is not None else 0)


class Reader:
    """The launcher's side: frames out of a worker's stdout, held to the
    caps while they arrive. ``parts`` is how many parts the job has."""

    def __init__(self, parts: int, ready_seen: bool = False) -> None:
        if not 0 <= parts <= MAX_PARTS:
            raise ValueError("parts")
        self.parts = parts
        self.ready = ready_seen
        self.streams: dict[int, PartStreams] = {}
        self.end: dict[str, Any] | None = None
        self.first_frame_at: float | None = None
        self._buffer = bytearray()

    def part(self, index: int) -> PartStreams:
        return self.streams.setdefault(index, PartStreams())

    def feed(self, data: bytes, now: float | None = None) -> None:
        """Takes the next bytes of the stream; raises Malformed on the
        first byte that breaks the protocol."""
        if self.end is not None and data:
            raise Malformed("bytes after the end")
        self._buffer += data
        if not self.ready:
            if len(self._buffer) < len(READY):
                if not READY.startswith(bytes(self._buffer)):
                    raise Malformed("not a worker")
                return
            if bytes(self._buffer[:len(READY)]) != READY:
                raise Malformed("not a worker")
            del self._buffer[:len(READY)]
            self.ready = True
        while len(self._buffer) >= FRAME.size:
            kind, part, length = FRAME.unpack_from(self._buffer)
            self._check_header(kind, part, length)
            if len(self._buffer) < FRAME.size + length:
                return
            payload = bytes(self._buffer[FRAME.size:FRAME.size + length])
            del self._buffer[:FRAME.size + length]
            if self.first_frame_at is None and now is not None:
                self.first_frame_at = now
            self._take(kind, part, payload)

    def _check_header(self, kind: int, part: int, length: int) -> None:
        if self.end is not None:
            raise Malformed("bytes after the end")
        if kind not in NAMES:
            raise Malformed("an unknown frame type")
        if kind == END:
            if part != JOB_PART or length > END_MAX:
                raise Malformed("the end frame")
            return
        if part != JOB_PART and part >= self.parts:
            raise Malformed("a frame for a part the job doesn't have")
        if kind == VERDICT:
            have = self.streams.get(part)
            used = len(have.verdict) if have is not None and have.verdict is not None else 0
            if used + length > VERDICT_CAP:
                raise Malformed("a verdict past its cap")
            return
        if part == JOB_PART:
            raise Malformed("output for the verdict step")
        have = self.streams.get(part)
        if (have.shown() if have is not None else 0) + length > PART_OUTPUT_CAP:
            raise Malformed("output past its cap")

    def _take(self, kind: int, part: int, payload: bytes) -> None:
        if kind == END:
            self.end = check_end(loads(payload, END_MAX), self.parts)
            return
        streams = self.part(part)
        if kind == OUT:
            streams.out += payload
        elif kind == ERR:
            streams.err += payload
        elif kind == RESULT:
            streams.result = (streams.result or bytearray()) + payload
        else:
            streams.verdict = (streams.verdict or bytearray()) + payload

    def finished(self) -> bool:
        return self.end is not None and not self._buffer

    def pending(self) -> int:
        """Bytes of a frame that hasn't fully arrived."""
        return len(self._buffer)


# -- init's summary ---------------------------------------------------------

PART_KEYS = frozenset({
    "id", "exit", "signal", "wall_ms", "limit", "truncated", "verdict_truncated", "result", "oom_kills",
    "pid_limit_hits", "policy",
})
VERDICT_KEYS = frozenset({"state", "exit", "signal", "wall_ms", "limit", "truncated"})
END_KEYS = frozenset({"version", "job_id", "setup", "residue", "parts", "verdict"})


def _int(value: Any, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def _status_ok(entry: dict[str, Any]) -> bool:
    """An exit code or a signal, never both; neither only when the process
    never ran."""
    exit_ok = entry["exit"] is None or _int(entry["exit"], 0, 255)
    signal_ok = entry["signal"] is None or _int(entry["signal"], 1, 64)
    return exit_ok and signal_ok and not (entry["exit"] is not None and entry["signal"] is not None)


def check_end(value: Any, parts: int) -> dict[str, Any]:
    """``value`` if it is a ``rounds.worker-end/v1`` summary for a job of
    ``parts`` parts, or Malformed."""
    if not isinstance(value, dict) or set(value) != END_KEYS:
        raise Malformed("the end's keys")
    if value["version"] != END_VERSION or value["setup"] not in SETUP_STATES:
        raise Malformed("the end's version or setup")
    if not isinstance(value["job_id"], str) or not isinstance(value["residue"], bool):
        raise Malformed("the end's job or residue")
    entries = value["parts"]
    if not isinstance(entries, list) or len(entries) > parts:
        raise Malformed("the end's parts")
    if value["setup"] != "ok" and (entries or value["verdict"] is not None):
        raise Malformed("a job that didn't set up ran something")
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != PART_KEYS or not isinstance(entry["id"], str):
            raise Malformed("a part's keys")
        if not _status_ok(entry) or not _int(entry["wall_ms"], 0, 86_400_000):
            raise Malformed("a part's status")
        if entry["limit"] is not None and entry["limit"] not in PART_LIMITS:
            raise Malformed("a part's limit")
        if entry["result"] not in RESULT_STATES:
            raise Malformed("a part's result")
        if not all(isinstance(entry[k], bool) for k in ("truncated", "verdict_truncated", "policy")):
            raise Malformed("a part's flags")
        if not _int(entry["oom_kills"], 0, 1_000_000) or not _int(entry["pid_limit_hits"], 0, 1_000_000_000):
            raise Malformed("a part's counters")
    verdict = value["verdict"]
    if verdict is not None:
        if not isinstance(verdict, dict) or set(verdict) != VERDICT_KEYS:
            raise Malformed("the verdict step's keys")
        if verdict["state"] not in VERDICT_STATES or not _status_ok(verdict):
            raise Malformed("the verdict step's status")
        if not _int(verdict["wall_ms"], 0, 86_400_000) or not isinstance(verdict["truncated"], bool):
            raise Malformed("the verdict step's figures")
        if verdict["limit"] is not None and verdict["limit"] not in PART_LIMITS:
            raise Malformed("the verdict step's limit")
    return value


def iter_chunks(data: bytes, size: int = CHUNK) -> Iterator[bytes]:
    for start in range(0, len(data), size):
        yield data[start:start + size]
