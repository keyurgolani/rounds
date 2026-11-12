"""What must hold before the launcher starts any worker (ROUNDS-00A-L05).

1. Its settings (``launcher/config.py``) and #2's profile.
2. The engine in ``DOCKER_HOST`` answers, serves API 1.44, and reports, in
   its ``/info``: rootless and seccomp among its security options, cgroup
   v2 with a real cgroup driver, and memory, swap, CPU quota, and process
   limits. A rootful engine is refused; there is no setting that accepts
   one.
3. The configured runtime is one the engine has.
4. The capacity model leaves at least one slot:
   ``min(concurrency, (MemTotal - reserved) // the profile's memory)``.
5. The worker image is there, or pulls by its digest.
6. A self-check worker with the full profile reports, from its own cgroup,
   the memory, swap, CPU, and process limits the profile sets, and shows
   init's added seccomp filter ending a denied call with ``SIGSYS``. That
   turns "the engine reports the limits" into "the limits hold here".

Nothing in steps 5 and 6 runs unless 1 to 4 hold, so a refused launcher
never creates a worker. ``Result.missing`` names every failed check from a
fixed vocabulary.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from launcher import config as settings, profile as isolation, run as runner
from launcher.engine import API_VERSION, Engine, EngineError
from launcher.pool import START_MAX_S, create_worker
from worker import frames, manifest

LIMIT_FILES = ("memory.max", "memory.swap.max", "cpu.max", "pids.max")
PROBE = (
    "import json\n"
    "def read(name):\n"
    "    try:\n"
    "        with open('/sys/fs/cgroup/' + name) as fh:\n"
    "            return fh.read().strip()\n"
    "    except OSError:\n"
    "        return None\n"
    f"print(json.dumps({{name: read(name) for name in {LIMIT_FILES!r}}}))\n"
)
DENIED_CALL = "import os\nos.unshare(0)\n"
SELF_CHECK_ID = "launcher-self-check"
SELF_CHECK_WALL_MS = 5000
DESTROY_WAIT_S = 10.0


@dataclass
class Result:
    missing: list[str]
    slots: int = 0
    profile: dict[str, Any] | None = None
    facts: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.missing


def _version(text: Any) -> tuple[int, ...]:
    try:
        return tuple(int(p) for p in str(text).split("."))
    except ValueError:
        return ()


def api_ok(version: dict[str, Any]) -> bool:
    want = _version(API_VERSION)
    have, oldest = _version(version.get("ApiVersion")), _version(version.get("MinAPIVersion") or "1.12")
    return bool(have) and have >= want and (not oldest or oldest <= want)


def engine_missing(info: dict[str, Any], runtime: str) -> list[str]:
    """What the engine's ``/info`` lacks, as the vocabulary names it."""
    missing: list[str] = []
    options = {str(option).split(",")[0] for option in (info.get("SecurityOptions") or [])}
    if "name=rootless" not in options:
        missing.append("rootless")
    if "name=seccomp" not in options:
        missing.append("seccomp")
    if str(info.get("CgroupVersion", "")) != "2":
        missing.append("cgroup_v2")
    if info.get("CgroupDriver") in (None, "", "none"):
        missing.append("cgroup_driver")
    for key, token in (("MemoryLimit", "memory_limit"), ("SwapLimit", "swap_limit"), ("CpuCfsQuota", "cpu_quota"),
                       ("CpuCfsPeriod", "cpu_quota"), ("PidsLimit", "pids_limit")):
        if info.get(key) is not True and token not in missing:
            missing.append(token)
    runtimes = info.get("Runtimes")
    if not isinstance(runtimes, dict) or runtime not in runtimes:
        missing.append("runtime")
    return missing


def capacity(mem_total: Any, reserved_mib: int, concurrency: int, worker_bytes: int) -> int:
    if not isinstance(mem_total, int) or mem_total <= 0:
        return 0
    room = (mem_total - reserved_mib * 1024 * 1024) // worker_bytes
    return max(0, min(concurrency, room))


def ensure_image(engine: Engine, ref: str) -> bool:
    if engine.image(ref) is not None:
        return True
    if ref.startswith("sha256:"):
        # A local image id can't be pulled.
        return False
    repository, digest = ref.split("@", 1)
    engine.pull(repository, digest)
    return engine.image(ref) is not None


def _destroy(engine: Engine, cid: str) -> None:
    give_up = time.monotonic() + DESTROY_WAIT_S
    try:
        engine.remove(cid)
        while time.monotonic() < give_up and engine.inspect(cid) is not None:
            time.sleep(0.05)
    except EngineError:
        pass


def self_check(engine: Engine, image: str, runtime: str, profile: dict[str, Any]) -> list[str]:
    """Runs the self-check worker; answers what it found missing."""
    archive = manifest.build(
        parts=[
            {"id": "limits", "argv": ["python3", "-I", "-S", "-c", PROBE], "wall_ms": SELF_CHECK_WALL_MS,
             "result": None, "channel": False},
            {"id": "filter", "argv": ["python3", "-I", "-S", "-c", DENIED_CALL], "wall_ms": SELF_CHECK_WALL_MS,
             "result": None, "channel": False},
        ],
        src={},
    )
    try:
        worker = create_worker(engine, image, runtime, profile, time.time(), START_MAX_S)
    except EngineError:
        return ["self_check"]
    try:
        outcome = runner.run(engine, worker, SELF_CHECK_ID, archive, hashlib.sha256(archive).hexdigest(), 2,
                             3 * SELF_CHECK_WALL_MS, threading.Event())
    finally:
        worker.attachment.close()
        _destroy(engine, worker.cid)
    end = outcome.reader.end
    if outcome.kill_reason is not None or end is None:
        return ["self_check"]
    if end["setup"] == "seccomp_failed":
        return ["seccomp_filter"]
    if end["setup"] != "ok" or len(end["parts"]) != 2:
        return ["self_check"]
    missing: list[str] = []
    try:
        seen = json.loads(bytes(outcome.reader.part(0).out).decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return ["self_check"]
    expected = {
        "memory.max": ("memory_limit", str(profile["memory_bytes"])),
        "memory.swap.max": ("swap_limit", "0"),
        "cpu.max": ("cpu_quota", f"{isolation.NANO_CPUS // 10_000} 100000"),
        "pids.max": ("pids_limit", str(profile["processes"])),
    }
    for name, (token, want) in expected.items():
        if not isinstance(seen, dict) or seen.get(name) != want:
            missing.append(token)
    # Init marks a part whose process the filter ended with SIGSYS.
    denied = end["parts"][1]
    if not denied["policy"] or denied["signal"] is None:
        missing.append("seccomp_filter")
    return missing


def run(cfg: settings.Config, engine: Engine | None = None) -> Result:
    missing = list(cfg.missing)
    try:
        profile = isolation.resource_profile()
        if not frames_cap_matches(profile):
            raise isolation.ProfileError("output_bytes")
    except isolation.ProfileError:
        missing.append("profile")
        profile = None
    if cfg.socket is None:
        return Result(missing)
    engine = engine or Engine(cfg.socket)
    try:
        if not engine.ping():
            return Result(missing + ["engine_unreachable"])
        if not api_ok(engine.version()):
            return Result(missing + ["engine_api"])
        info = engine.info()
    except EngineError:
        return Result(missing + ["engine_unreachable"])
    missing += engine_missing(info, cfg.runtime)
    facts = {"mem_total": info.get("MemTotal"), "ncpu": info.get("NCPU"), "runtime": cfg.runtime}
    slots = capacity(info.get("MemTotal"), cfg.reserved_mib, cfg.concurrency,
                     profile["memory_bytes"] if profile else 1)
    if slots < 1:
        missing.append("capacity")
    if missing or profile is None or cfg.image is None:
        return Result(missing, facts=facts)
    try:
        if not ensure_image(engine, cfg.image):
            missing.append("image_unavailable")
    except EngineError:
        missing.append("image_unavailable")
    if missing:
        return Result(missing, facts=facts)
    missing += self_check(engine, cfg.image, cfg.runtime, profile)
    return Result(missing, slots=slots, profile=profile, facts=facts)


def frames_cap_matches(profile: dict[str, Any]) -> bool:
    """Init's per-part cap is #2's output size."""
    return frames.PART_OUTPUT_CAP == profile["output_bytes"]
