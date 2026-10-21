"""Harness check for the execution job store's migration (ROUNDS-00A-L03
PR 1).

Applies and reverses ``1700007100_execution_jobs.js`` with the pinned
PocketBase binary on a ``pb_data`` with every migration before it, seeds
and the demo account included:

1. Applying it adds ``execution_service``, ``execution_jobs``,
   ``execution_attempts``, and ``execution_envelopes``, with every client
   write rule null, adds the ``envelope`` and ``job`` links, raises
   ``take_home_attempts.files`` to 8 MiB, and changes no other table, row,
   collection, or field.
2. Reversing it (``pocketbase migrate down 1``, confirmed on a pseudo
   terminal as an operator would) puts the data back to the base snapshot.
3. Applying it again after the reversal works.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

from admission_migration_check import (
    MIGRATIONS,
    RULES,
    Checks,
    _differences,
    _migrate,
    _migrate_down_confirmed,
    _snapshot,
)

MIGRATION = "1700007100_execution_jobs.js"
NEW = ("execution_service", "execution_jobs", "execution_attempts", "execution_envelopes")
CHANGED = {"ai_coding_attempts": ["envelope"], "take_home_attempts": ["envelope"], "admission_commands": ["job"]}
SERVICE_ONLY = '@request.auth.collectionName = "execution_service"'
MIB = 1024 * 1024


def _fields(db: Path, name: str) -> list[dict]:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT schema FROM _collections WHERE name = ?", (name,)).fetchone()
    finally:
        conn.close()
    return json.loads(row[0]) if row else []


def _rules(db: Path) -> dict[str, list]:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        rows = conn.execute(
            f"SELECT name, {', '.join(RULES)} FROM _collections WHERE name IN ({', '.join('?' * len(NEW))})", NEW
        ).fetchall()
    finally:
        conn.close()
    return {row[0]: list(row[1:]) for row in rows}


def _files_options(snapshot: dict) -> dict:
    schema = json.loads(snapshot["collections"]["take_home_attempts"][1])
    return next(f["options"] for f in schema if f["name"] == "files")


def _without_changes(snapshot: dict, base: dict) -> dict:
    """The snapshot with the new collections left out, the changed
    collections' added fields taken back out of their schema, and
    ``take_home_attempts.files`` given the base's limit back."""
    out = {
        "counts": {t: n for t, n in snapshot["counts"].items() if t not in NEW},
        "collections": {},
        "migrations": [m for m in snapshot["migrations"] if m != MIGRATION],
    }
    for name, value in snapshot["collections"].items():
        if name in NEW:
            continue
        if name in CHANGED:
            schema = [f for f in json.loads(value[1]) if f["name"] not in CHANGED[name]]
            for field in schema:
                if name == "take_home_attempts" and field["name"] == "files":
                    field["options"] = _files_options(base)
            value = (value[0], json.dumps(schema, separators=(",", ":")), *value[2:])
        out["collections"][name] = value
    return out


def _normalized(snapshot: dict) -> dict:
    """The base snapshot with each changed collection's schema re-encoded
    the way ``_without_changes`` writes it."""
    out = {"counts": snapshot["counts"], "collections": {}, "migrations": snapshot["migrations"]}
    for name, value in snapshot["collections"].items():
        if name in CHANGED:
            value = (value[0], json.dumps(json.loads(value[1]), separators=(",", ":")), *value[2:])
        out["collections"][name] = value
    return out


def main() -> int:
    c = Checks()
    work = Path(tempfile.mkdtemp(prefix="execution-migration-check-"))
    base = work / "base_migrations"
    full = work / "migrations"
    base.mkdir()
    full.mkdir()
    for path in sorted(MIGRATIONS.glob("*.js")):
        if path.name < MIGRATION:
            shutil.copy(path, base / path.name)
            shutil.copy(path, full / path.name)
    shutil.copy(MIGRATIONS / MIGRATION, full / MIGRATION)

    base_data = work / "base_pb_data"
    up = _migrate(base_data, base, "up")
    c.check("execution-migration.base.applies", up.returncode == 0, up.stderr[-500:])
    if up.returncode != 0:
        print(f"execution migration check: {c.passed} passed, {c.failed} failed")
        return 1
    before = _snapshot(base_data / "data.db")
    c.check("execution-migration.base.has-data", before["counts"].get("users", 0) >= 1,
            f"users={before['counts'].get('users')}")

    data = work / "pb_data"
    shutil.copytree(base_data, data)
    db = data / "data.db"
    up = _migrate(data, full, "up")
    c.check("execution-migration.applies", up.returncode == 0 and MIGRATION in up.stdout, (up.stdout + up.stderr)[-500:])
    applied = _snapshot(db)
    c.check("execution-migration.adds-four-collections", all(n in applied["collections"] for n in NEW),
            f"present={sorted(n for n in applied['collections'] if n.startswith('execution_'))}")
    rules = _rules(db)
    want = {"execution_service": [None] * 5,
            **{n: [SERVICE_ONLY, SERVICE_ONLY, None, None, None] for n in NEW[1:]}}
    c.check("execution-migration.no-client-writes", rules == want, repr(rules))
    links = {name: {f["name"]: f for f in _fields(db, name)} for name in CHANGED}
    c.check("execution-migration.adds-the-links",
            all(field in links[name] and links[name][field]["type"] == "relation" and not links[name][field]["required"]
                for name, fields in CHANGED.items() for field in fields),
            repr({n: sorted(f) for n, f in links.items()}))
    c.check("execution-migration.files-hold-8-mib", links["take_home_attempts"]["files"]["options"]["maxSize"] == 8 * MIB,
            repr(links["take_home_attempts"]["files"]["options"]))
    c.check("execution-migration.touches-nothing-else", _without_changes(applied, before) == _normalized(before),
            _differences(_without_changes(applied, before), _normalized(before)))

    code, out = _migrate_down_confirmed(data, full)
    c.check("execution-migration.reverses", code == 0 and MIGRATION in out, f"exit={code} {out[-300:]!r}")
    reverted = _snapshot(db)
    c.check("execution-migration.down-restores-the-base", _normalized(reverted) == _normalized(before),
            _differences(_normalized(reverted), _normalized(before)))

    up = _migrate(data, full, "up")
    again = _snapshot(db)
    c.check("execution-migration.reapplies", up.returncode == 0 and all(n in again["collections"] for n in NEW)
            and _without_changes(again, before) == _normalized(before), (up.stdout + up.stderr)[-500:])

    print(f"execution migration check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
