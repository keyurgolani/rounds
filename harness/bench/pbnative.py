"""Native PocketBase for the database benchmark (ROUNDS-02-L01).

The benchmark and its schema dump run the pinned PocketBase binary directly,
never in a container. Each run gets its own scratch directory under
harness/bench/.scratch/ with copies of the repository's migrations and hooks,
so the repository's own files run unchanged and the bench's overlays never
touch them. The one edit is in the copy of the seed migration: it reads
/pb_seeds/ (the image's mount), so the copy reads the repository's
pocketbase/seeds/ instead.

A server binds 127.0.0.1 on a free port and is stopped by the pid this module
started; nothing here signals any other process. Finished scratch goes to the
Trash by its exact path, never deleted.

This is a non-shipping spike: the image copies only pocketbase/pb_hooks and
pocketbase/pb_migrations, so nothing under harness/bench/ reaches a release.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO_MIGRATIONS = ROOT / "pocketbase" / "pb_migrations"
REPO_HOOKS = ROOT / "pocketbase" / "pb_hooks"
REPO_SEEDS = ROOT / "pocketbase" / "seeds"
SCRATCH = ROOT / "harness" / "bench" / ".scratch"
SEED_MIGRATION = "1700000100_seed_data.js"
CONTAINER_SEEDS = "/pb_seeds/"
LOOPBACK = "127.0.0.1"
DEFAULT_BINARY = Path.home() / "Library" / "Caches" / "rounds-lane" / "tools" / "pocketbase-0.22.22" / "bin" / "pocketbase"

# The environment a native PocketBase gets: nothing from the caller's shell
# but what a process needs to run, so no unrelated setting leaks in.
_PASS_THROUGH = ("PATH", "HOME", "TMPDIR", "LANG")


@dataclass
class Dirs:
    root: Path
    migrations: Path
    hooks: Path
    data: Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def binary_path(value: str | os.PathLike[str] | None = None) -> Path:
    path = Path(value) if value else DEFAULT_BINARY
    if not path.is_file() or not os.access(path, os.X_OK):
        raise FileNotFoundError(f"no executable PocketBase at {path}")
    return path


def binary_version(binary: Path) -> str:
    out = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=30, check=True).stdout
    # "pocketbase version 0.22.22"
    return out.strip().rsplit(" ", 1)[-1]


def run_dir(label: str) -> Path:
    """A new, empty scratch directory for one phase of one run."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = SCRATCH / f"{label}-{stamp}-{os.getpid()}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def _copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "types.d.ts"))


def _overlay(extra: Path | None, dst: Path) -> list[str]:
    """Adds the bench's own files; refuses to replace a repository file."""
    added: list[str] = []
    if extra is None:
        return added
    for item in sorted(extra.iterdir()):
        if not item.is_file():
            continue
        target = dst / item.name
        if target.exists():
            raise RuntimeError(f"{item.name} would replace a repository file in {dst}")
        shutil.copy2(item, target)
        added.append(item.name)
    return added


def prepare(root: Path, *, with_hooks: bool = True, extra_migrations: Path | None = None,
            extra_hooks: Path | None = None) -> tuple[Dirs, dict]:
    """Copies the repository's migrations (and hooks) into root.

    Returns the directories and a note of what the copy changed, for the
    receipt: the seed path rewrite and the overlay file names.
    """
    dirs = Dirs(root=root, migrations=root / "pb_migrations", hooks=root / "pb_hooks", data=root / "pb_data")
    _copy_tree(REPO_MIGRATIONS, dirs.migrations)
    seed = dirs.migrations / SEED_MIGRATION
    text = seed.read_text()
    if text.count(CONTAINER_SEEDS) != 1:
        raise RuntimeError(f"{SEED_MIGRATION} no longer reads {CONTAINER_SEEDS} exactly once; update pbnative.prepare")
    seed.write_text(text.replace(CONTAINER_SEEDS, f"{REPO_SEEDS}/"))
    if with_hooks:
        _copy_tree(REPO_HOOKS, dirs.hooks)
    else:
        dirs.hooks.mkdir()
    note = {
        "seedPathRewrite": f"{SEED_MIGRATION}: {CONTAINER_SEEDS} -> pocketbase/seeds/ (native run only)",
        "repositoryHooksLoaded": with_hooks,
        "benchMigrations": _overlay(extra_migrations, dirs.migrations),
        "benchHooks": _overlay(extra_hooks, dirs.hooks),
    }
    dirs.data.mkdir()
    return dirs, note


def base_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: os.environ[k] for k in _PASS_THROUGH if k in os.environ}
    env.update(extra or {})
    return env


def _args(dirs: Dirs) -> list[str]:
    return [f"--dir={dirs.data}", f"--migrationsDir={dirs.migrations}", f"--hooksDir={dirs.hooks}",
            "--hooksWatch=false", "--automigrate=false"]


def migrate_up(binary: Path, dirs: Dirs, env: dict[str, str] | None = None, timeout: float = 600) -> subprocess.CompletedProcess:
    """Applies every migration without serving: no listener, no port."""
    res = subprocess.run([str(binary), "migrate", "up", *_args(dirs)], capture_output=True, text=True,
                         env=base_env(env), timeout=timeout)
    if res.returncode != 0 or "Failed to apply migration" in (res.stdout + res.stderr):
        raise RuntimeError(f"migrate up failed ({res.returncode}): {(res.stdout + res.stderr)[-2000:]}")
    return res


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((LOOPBACK, 0))
        return s.getsockname()[1]


@dataclass
class Server:
    """One native PocketBase serving on 127.0.0.1. Only its own pid is ever signalled."""

    binary: Path
    dirs: Dirs
    env: dict[str, str]
    port: int = 0
    proc: subprocess.Popen | None = None
    log_path: Path | None = None
    starts: list[float] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"http://{LOOPBACK}:{self.port}"

    def start(self, timeout: float = 120) -> float:
        """Starts serving and waits for /api/health. Returns seconds to healthy (migrations included)."""
        if self.proc and self.proc.poll() is None:
            raise RuntimeError("already running")
        self.port = self.port or free_port()
        self.log_path = self.dirs.root / f"pocketbase-{len(self.starts)}.log"
        log = self.log_path.open("ab")
        t0 = time.monotonic()
        self.proc = subprocess.Popen([str(self.binary), "serve", f"--http={LOOPBACK}:{self.port}", *_args(self.dirs)],
                                     stdout=log, stderr=subprocess.STDOUT, env=base_env(self.env),
                                     start_new_session=True)
        log.close()
        deadline = t0 + timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"PocketBase exited with {self.proc.returncode}; its log ends:\n{self.tail()}")
            try:
                with urllib.request.urlopen(f"{self.url}/api/health", timeout=2) as r:
                    if r.status == 200:
                        took = time.monotonic() - t0
                        self.starts.append(took)
                        return took
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
                pass
            time.sleep(0.05)
        self.stop()
        raise TimeoutError(f"PocketBase not healthy after {timeout}s; its log ends:\n{self.tail()}")

    def tail(self, lines: int = 40) -> str:
        """The end of this server's log, for a failure report (the scratch dir moves to the Trash after)."""
        if not self.log_path or not self.log_path.exists():
            return ""
        return "\n".join(self.log_path.read_text(errors="replace").splitlines()[-lines:])

    @property
    def pid(self) -> int | None:
        return self.proc.pid if self.proc else None

    def stop(self, timeout: float = 30) -> None:
        if not self.proc or self.proc.poll() is not None:
            return
        self.proc.send_signal(signal.SIGTERM)
        try:
            self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=timeout)

    def kill9(self) -> None:
        """The crash failpoint: SIGKILL to this server's own pid, no shutdown."""
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=30)

    def listening_on_loopback_only(self) -> bool:
        """lsof's view of this pid's TCP listeners: every one must be 127.0.0.1."""
        if not self.pid:
            return False
        out = subprocess.run(["lsof", "-nP", "-a", "-p", str(self.pid), "-iTCP", "-sTCP:LISTEN"],
                             capture_output=True, text=True).stdout
        names = [line.split()[-2] for line in out.splitlines()[1:] if line.strip()]
        return bool(names) and all(n.startswith(f"{LOOPBACK}:") for n in names)


def to_trash(path: Path, label: str) -> Path | None:
    """Moves a finished scratch directory to ~/.Trash by its exact path."""
    if not path.exists():
        return None
    trash = Path.home() / ".Trash"
    target = trash / f"rounds-18-bench-{label}-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    shutil.move(str(path), str(target))
    print(f"moved {path} to {target}", flush=True)
    return target
