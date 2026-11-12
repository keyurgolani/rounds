"""The launcher's settings (ROUNDS-00A-L05), read once at start.

- ``DOCKER_HOST``: the worker daemon's socket, ``unix://`` only.
- ``ROUNDS_LAUNCHER_TOKEN``: 32 to 128 printable characters, the same on the
  runner; no default, and the launcher refuses to start without it.
- ``ROUNDS_WORKER_IMAGE``: an override of the image the runner image bakes
  in (``WORKER_IMAGE`` next to this file), by digest only: ``repo@sha256:...``
  or a local image id ``sha256:...``. A tag is refused.
- ``ROUNDS_WORKER_RUNTIME``: ``runc`` (the default) or ``runsc``.
- ``ROUNDS_WORKER_CONCURRENCY``, ``ROUNDS_WORKER_RESERVED_MIB``,
  ``ROUNDS_WORKER_PRESTART``: the capacity model's inputs.
- ``ROUNDS_LAUNCHER_BIND`` and ``ROUNDS_LAUNCHER_PORT``: where it listens;
  ``127.0.0.1`` unless set. The Compose service sets the bind inside its
  container, on the internal network, with no port published.

The launcher also refuses to start while any app secret is in its
environment, so a deployment mistake can't hand one to the process that
holds engine authority.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 4300
SOCKET_PREFIX = "unix://"
TOKEN_MIN, TOKEN_MAX = 32, 128
TOKEN = re.compile(r"[!-~]{32,128}")
RUNTIMES = ("runc", "runsc")
CONCURRENCY_DEFAULT = 2
CONCURRENCY_MAX = 256
RESERVED_MIB_DEFAULT = 2048
PRESTART_DEFAULT = 2
# A repository by digest, optionally with a registry host and port, or a
# local image id. Nothing with a tag.
_REPO = r"(?:[a-z0-9.-]+(?::[0-9]+)?/)?[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*"
IMAGE = re.compile(rf"(?:{_REPO}@)?sha256:[0-9a-f]{{64}}")
BAKED_IMAGE = Path(__file__).resolve().parent / "WORKER_IMAGE"
# Every secret the app's services hold; none may reach the launcher.
APP_SECRETS = (
    "AI_KEY_SECRET", "PB_ADMIN_EMAIL", "PB_ADMIN_PASSWORD", "ROUNDS_EXECUTION_SECRET", "ROUNDS_ADMISSION_SECRET",
    "ROUNDS_SHARE_RESOLVER_PASSWORD",
)


@dataclass(frozen=True)
class Config:
    socket: str | None
    token: str | None
    image: str | None
    image_source: str
    runtime: str
    concurrency: int
    reserved_mib: int
    prestart: int | None
    bind: str
    port: int
    missing: tuple[str, ...]


def _int(raw: str | None, default: int | None, low: int, high: int) -> tuple[int | None, bool]:
    """``raw`` as an int in [low, high]; the default when it is unset; and
    whether it was valid."""
    if raw is None or not raw.strip():
        return default, True
    try:
        value = int(raw.strip())
    except ValueError:
        return default, False
    return (value, True) if low <= value <= high else (default, False)


def baked_image(path: Path = BAKED_IMAGE) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def from_env(environ: Mapping[str, str] | None = None, baked: str | None = None) -> Config:
    env = os.environ if environ is None else environ
    missing: list[str] = []

    host = (env.get("DOCKER_HOST") or "").strip()
    socket = host[len(SOCKET_PREFIX):] if host.startswith(SOCKET_PREFIX) and len(host) > len(SOCKET_PREFIX) else None
    if socket is None or not socket.startswith("/"):
        socket = None
        missing.append("docker_host")

    token = env.get("ROUNDS_LAUNCHER_TOKEN") or ""
    if not TOKEN.fullmatch(token):
        token = ""
        missing.append("token")

    if any((env.get(name) or "").strip() for name in APP_SECRETS):
        missing.append("app_secret")

    override = (env.get("ROUNDS_WORKER_IMAGE") or "").strip()
    image, source = (override, "env") if override else ((baked if baked is not None else baked_image()), "baked")
    if not image or not IMAGE.fullmatch(image):
        missing.append("worker_image")
        image = None
    runtime = (env.get("ROUNDS_WORKER_RUNTIME") or "runc").strip().lower()
    if runtime not in RUNTIMES:
        missing.append("runtime")
        runtime = "runc"

    concurrency, ok_c = _int(env.get("ROUNDS_WORKER_CONCURRENCY"), CONCURRENCY_DEFAULT, 1, CONCURRENCY_MAX)
    reserved, ok_r = _int(env.get("ROUNDS_WORKER_RESERVED_MIB"), RESERVED_MIB_DEFAULT, 0, 1 << 30)
    prestart, ok_p = _int(env.get("ROUNDS_WORKER_PRESTART"), None, 0, CONCURRENCY_MAX)
    if not (ok_c and ok_r and ok_p):
        missing.append("capacity")
    port, ok_port = _int(env.get("ROUNDS_LAUNCHER_PORT"), DEFAULT_PORT, 1, 65535)
    if not ok_port:
        missing.append("port")
    bind = (env.get("ROUNDS_LAUNCHER_BIND") or "").strip() or DEFAULT_BIND
    return Config(
        socket=socket, token=token or None, image=image, image_source=source, runtime=runtime,
        concurrency=concurrency or CONCURRENCY_DEFAULT, reserved_mib=reserved or 0, prestart=prestart, bind=bind,
        port=port or DEFAULT_PORT, missing=tuple(missing),
    )
