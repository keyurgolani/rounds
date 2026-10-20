"""Harness check for the admission migration (ROUNDS-00A-L01 stage 3).

Applies and reverses ``1700006100_admission.js`` with the pinned
PocketBase binary on a ``pb_data`` shaped like ``62d4eae``: every
migration that sorts before ``1700006000``, seeds and the demo account
included, and nothing newer, so the admission migration is shown not to
depend on #9's ``1700006000``.

1. Applying it adds ``admission_commands``, ``admission_counters``, and
   ``admission_leases`` with every client rule null, and changes no other
   table, row, or collection.
2. Reversing it (``pocketbase migrate down 1``, confirmed on a pseudo
   terminal as an operator would) drops only those three, and the data is
   back to the base snapshot.
3. Applying it again after the reversal works.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import fcntl
import os
import pty
import select
import shutil
import signal
import sqlite3
import struct
import subprocess
import sys
import tempfile
import termios
import time
from pathlib import Path

PB_BIN = Path(os.environ.get("PB_BIN", "/pbbin/pocketbase"))
MIGRATIONS = Path(os.environ.get("PB_MIGRATIONS_DIR", "/pb_migrations"))
MIGRATION = "1700006100_admission.js"
# 62d4eae's last migration sorts before this; #9's stage 3 adds it.
BASE_BEFORE = "1700006000"
COLLECTIONS = ("admission_commands", "admission_counters", "admission_leases")
RULES = ("listRule", "viewRule", "createRule", "updateRule", "deleteRule")


class Checks:
    def __init__(self) -> None:
        self.failed = 0
        self.passed = 0

    def check(self, name: str, ok: bool, why: str = "") -> bool:
        if ok:
            self.passed += 1
            print(f"PASS {name}")
        else:
            self.failed += 1
            print(f"FAIL {name}: {why}")
        return ok


def _migrate(data: Path, migrations: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PB_BIN), "migrate", *args, f"--dir={data}", f"--migrationsDir={migrations}"],
        capture_output=True,
        text=True,
        timeout=300,
        env={"PATH": "/usr/bin:/bin"},
    )


def _migrate_down_confirmed(data: Path, migrations: Path, timeout_s: float = 120) -> tuple[int, str]:
    """``migrate down 1`` on a pseudo terminal, answering its prompt with yes,
    as an operator at a terminal would. The prompt asks the terminal for the
    cursor position first, so each query gets an answer, and the yes goes
    only once the prompt has gone quiet."""
    argv = [str(PB_BIN), "migrate", "down", "1", f"--dir={data}", f"--migrationsDir={migrations}"]
    pid, fd = pty.fork()
    if pid == 0:  # pragma: no cover - the child
        os.execve(argv[0], argv, {"PATH": "/usr/bin:/bin", "TERM": "xterm"})
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    out = b""
    answered = False
    positions = 0
    finished = False
    deadline = time.monotonic() + timeout_s
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.5)
            if fd not in ready:
                if not answered and b"(y/N)" in out:
                    answered = True
                    os.write(fd, b"y\r")
                continue
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                finished = True
                break
            if not chunk:
                finished = True
                break
            out += chunk
            while out.count(b"\x1b[6n") > positions:
                positions += 1
                os.write(fd, b"\x1b[24;1R")
        if not finished:
            os.kill(pid, signal.SIGKILL)
    finally:
        _, status = os.waitpid(pid, 0)
        os.close(fd)
    return os.waitstatus_to_exitcode(status), out.decode("utf-8", errors="replace")


def _snapshot(db: Path) -> dict:
    """Every table's row count, every collection but the admission ones, and
    the applied migrations."""
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        # Collections and migrations are compared by content below.
        counts = {
            t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            for t in tables
            if t not in ("_migrations", "_collections")
        }
        collections = {
            row[0]: row[1:]
            for row in conn.execute(
                f"SELECT name, type, schema, indexes, {', '.join(RULES)}, options FROM _collections ORDER BY name"
            )
        }
        migrations = [r[0] for r in conn.execute("SELECT file FROM _migrations ORDER BY file")]
    finally:
        conn.close()
    return {"counts": counts, "collections": collections, "migrations": migrations}


def _without_admission(snapshot: dict) -> dict:
    return {
        "counts": {t: n for t, n in snapshot["counts"].items() if t not in COLLECTIONS},
        "collections": {n: v for n, v in snapshot["collections"].items() if n not in COLLECTIONS},
        "migrations": [m for m in snapshot["migrations"] if m != MIGRATION],
    }


def _differences(got: dict, want: dict) -> str:
    """Which tables, collections, or migrations differ, by name only."""
    out = []
    for part in ("counts", "collections"):
        names = set(got[part]) | set(want[part])
        changed = sorted(n for n in names if got[part].get(n) != want[part].get(n))
        if changed:
            out.append(f"{part}: {', '.join(changed)}")
    if got["migrations"] != want["migrations"]:
        out.append("migrations: " + ", ".join(sorted(set(got["migrations"]) ^ set(want["migrations"]))))
    return "; ".join(out) or "none"


def _admission_rules(db: Path) -> dict:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        rows = conn.execute(
            f"SELECT name, {', '.join(RULES)} FROM _collections WHERE name IN ({', '.join('?' * len(COLLECTIONS))})",
            COLLECTIONS,
        ).fetchall()
    finally:
        conn.close()
    return {row[0]: list(row[1:]) for row in rows}


def main() -> int:
    c = Checks()
    work = Path(tempfile.mkdtemp(prefix="migration-check-"))
    base = work / "base_migrations"
    full = work / "migrations"
    base.mkdir()
    full.mkdir()
    for path in sorted(MIGRATIONS.glob("*.js")):
        if path.name < BASE_BEFORE:
            shutil.copy(path, base / path.name)
            shutil.copy(path, full / path.name)
    shutil.copy(MIGRATIONS / MIGRATION, full / MIGRATION)

    base_data = work / "base_pb_data"
    up = _migrate(base_data, base, "up")
    c.check("migration.base.applies", up.returncode == 0, up.stderr[-500:])
    if up.returncode != 0:
        print(f"admission migration check: {c.passed} passed, {c.failed} failed")
        return 1
    before = _snapshot(base_data / "data.db")
    c.check("migration.base.has-data", before["counts"].get("users", 0) >= 1 and before["counts"].get("coding_questions", 0) > 0,
            f"users={before['counts'].get('users')} questions={before['counts'].get('coding_questions')}")
    c.check("migration.base.is-62d4eae-shaped",
            MIGRATION not in before["migrations"] and not any(m.startswith(BASE_BEFORE) for m in before["migrations"]),
            "an admission or #9 stage 3 migration is already applied")

    # A copy of the base, as an operator upgrades a copy of pb_data.
    data = work / "pb_data"
    shutil.copytree(base_data, data)

    up = _migrate(data, full, "up")
    c.check("migration.admission.applies", up.returncode == 0 and MIGRATION in up.stdout, (up.stdout + up.stderr)[-500:])
    applied = _snapshot(data / "data.db")
    c.check("migration.admission.adds-three-collections", all(n in applied["collections"] for n in COLLECTIONS),
            f"present={sorted(n for n in applied['collections'] if n.startswith('admission_'))}")
    rules = _admission_rules(data / "data.db")
    c.check("migration.admission.server-only-rules", rules == {n: [None] * 5 for n in COLLECTIONS}, repr(rules))
    c.check("migration.admission.touches-nothing-else", _without_admission(applied) == before,
            _differences(_without_admission(applied), before))

    code, out = _migrate_down_confirmed(data, full)
    c.check("migration.admission.reverses", code == 0 and MIGRATION in out, f"exit={code} {out[-300:]!r}")
    reverted = _snapshot(data / "data.db")
    c.check("migration.admission.down-drops-only-its-collections", reverted == before,
            _differences(reverted, before))

    up = _migrate(data, full, "up")
    again = _snapshot(data / "data.db")
    c.check("migration.admission.reapplies", up.returncode == 0 and _without_admission(again) == before
            and all(n in again["collections"] for n in COLLECTIONS), (up.stdout + up.stderr)[-500:])

    print(f"admission migration check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
