"""Isolation profile v1 (ROUNDS-00A-L05): the one container spec every code
worker gets.

``create_body`` is a pure function of the constants here, #2's resource
profile (``backend/definitions/profiles/execution-default.v1.json``), the
runtime, the image digest, and the worker's deadline label. A job's spec
never reaches it: pre-started workers are created before their job exists.

Each worker runs as 65532 with every capability dropped and no new
privileges; on a read-only root with ``/work`` the only writable path, a
64 MiB tmpfs counted against the memory limit; with no network but its own
loopback; under the engine's default seccomp profile, which init extends
(``worker/seccomp.py``); within #2's process and memory limits, one CPU, no
swap, and the core, file-size, and open-file limits below; with no log
kept; and with exactly the six environment variables in ``ENV`` for its
processes. No bind, volume, or device reaches it. AppArmor doesn't apply
under the rootless engine the launcher requires.
"""
from __future__ import annotations

from typing import Any, Mapping

from execution import kinds

PROFILE_VERSION = "execution-default.v1"
USER = "65532:65532"
ENTRYPOINT = ["/usr/local/bin/python3", "-I", "-S", "/opt/rounds/worker/init.py"]
ENV = (
    "PATH=/opt/node/bin:/opt/rounds/node/node_modules/.bin:/usr/local/bin:/usr/bin:/bin",
    "HOME=/work/home",
    "TMPDIR=/work/tmp",
    "LANG=C.UTF-8",
    "PYTHONPATH=/work/src",
    # Node sizes its pool from the host's CPUs, and the process limit
    # counts threads.
    "NODE_OPTIONS=--v8-pool-size=2",
)
WORK_TMPFS = "rw,nosuid,nodev,size=64m"
NANO_CPUS = 1_000_000_000
CORE_MAX = 0
FSIZE_MAX = 16 * 1024 * 1024
NOFILE_MAX = 256
LABEL = "io.rounds.worker"
LABEL_VALUE = "v1"
DEADLINE_LABEL = "io.rounds.deadline"


class ProfileError(ValueError):
    """#2's profile isn't the one this launcher was built for."""


def resource_profile() -> dict[str, Any]:
    """#2's profile, checked for the fields the workers take."""
    try:
        profile = kinds.profile()
    except (OSError, ValueError) as err:
        raise ProfileError("unreadable") from err
    if profile.get("schema") != "resource-profile/v1" or profile.get("profile_id") != "execution-default":
        raise ProfileError("version")
    for key in ("processes", "memory_bytes", "output_bytes"):
        value = profile.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ProfileError(key)
    return profile


def create_body(image: str, runtime: str, profile: Mapping[str, Any], deadline: int) -> dict[str, Any]:
    """The engine's container-create body for one worker."""
    return {
        "Image": image,
        "Entrypoint": list(ENTRYPOINT),
        "Cmd": [],
        "User": USER,
        "Env": list(ENV),
        "WorkingDir": "/work",
        "AttachStdin": True,
        "AttachStdout": True,
        "AttachStderr": True,
        "OpenStdin": True,
        "StdinOnce": True,
        "Tty": False,
        "StopSignal": "SIGKILL",
        "Labels": {LABEL: LABEL_VALUE, DEADLINE_LABEL: str(int(deadline))},
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "CapAdd": [],
            "SecurityOpt": ["no-new-privileges"],
            "Privileged": False,
            "PidsLimit": int(profile["processes"]),
            "Memory": int(profile["memory_bytes"]),
            "MemorySwap": int(profile["memory_bytes"]),
            "NanoCpus": NANO_CPUS,
            "Ulimits": [
                {"Name": "core", "Soft": CORE_MAX, "Hard": CORE_MAX},
                {"Name": "fsize", "Soft": FSIZE_MAX, "Hard": FSIZE_MAX},
                {"Name": "nofile", "Soft": NOFILE_MAX, "Hard": NOFILE_MAX},
            ],
            "Tmpfs": {"/work": WORK_TMPFS},
            "Binds": [],
            "Mounts": [],
            "Devices": [],
            "LogConfig": {"Type": "none", "Config": {}},
            "IpcMode": "private",
            "CgroupnsMode": "private",
            "Runtime": runtime,
            "Init": False,
            "RestartPolicy": {"Name": "no"},
            "AutoRemove": False,
            "PublishAllPorts": False,
            "OomKillDisable": False,
        },
    }
