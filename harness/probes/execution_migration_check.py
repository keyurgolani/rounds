"""Harness check for the execution job store's migration (ROUNDS-00A-L03
PR 1).

Applies and reverses ``1700007100_execution_jobs.js`` with the pinned
PocketBase binary on a ``pb_data`` with every migration before it, seeds
and the demo account included:

1. Applying it adds ``execution_service``, ``execution_jobs``,
   ``execution_attempts``, and ``execution_envelopes``, with every client
   write rule null and an account reading only its own envelopes (D9),
   which name their job and attempt by plain id, so no collection anyone
   but the service reads links into the service-only ones,
   adds the ``envelope`` and ``job`` links, raises
   ``take_home_attempts.files`` to 8 MiB, records the size that field held
   in its own ``_params`` row, and changes no other table, row,
   collection, or field.
2. Reversing it (``pocketbase migrate down 1``, confirmed on a pseudo
   terminal as an operator would) puts the data back to the base snapshot
   and removes the record.
3. Applying it again after the reversal works.
4. On a ``pb_data`` where PocketBase's own JSON reset ran first, so
   ``files`` still holds the 2 MiB ``1700001300_take_home.js`` declares,
   reversing it puts that 2 MiB back.

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
OWNER_ONLY = "user = @request.auth.id"
SERVICE_ONLY_COLLECTIONS = ("execution_service", "execution_jobs", "execution_attempts")
MIB = 1024 * 1024
# The _params row the migration records the files limit it found in.
PRIOR_KEY = MIGRATION


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


def _links_into_service_only(db: Path) -> list[str]:
    """Each relation field, on a collection an account or anyone reads, that
    points at a collection only the execution service reads."""
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT id, name, listRule, viewRule, schema FROM _collections").fetchall()
    finally:
        conn.close()
    service_only = {cid for cid, name, *_rest in rows if name in SERVICE_ONLY_COLLECTIONS}
    return sorted(f"{name}.{f['name']}" for cid, name, list_rule, view_rule, schema in rows
                  if cid not in service_only and (list_rule is not None or view_rule is not None)
                  for f in json.loads(schema)
                  if f.get("type") == "relation" and (f.get("options") or {}).get("collectionId") in service_only)


def _files_options(snapshot: dict) -> dict:
    schema = json.loads(snapshot["collections"]["take_home_attempts"][1])
    return next(f["options"] for f in schema if f["name"] == "files")


def _params(db: Path) -> dict[str, str]:
    """Every ``_params`` row but the migration's record."""
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return {k: v for k, v in conn.execute("SELECT key, value FROM _params ORDER BY key") if k != PRIOR_KEY}
    finally:
        conn.close()


def _record(db: Path) -> dict | None:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM _params WHERE key = ?", (PRIOR_KEY,)).fetchone()
    finally:
        conn.close()
    return None if row is None else json.loads(row[0])


def _without_changes(snapshot: dict, base: dict) -> dict:
    """The snapshot with the new collections and the ``_params`` count left
    out (``_params`` is compared apart, by row), the changed collections'
    added fields taken back out of their schema, and
    ``take_home_attempts.files`` given the base's limit back."""
    out = {
        "counts": {t: n for t, n in snapshot["counts"].items() if t not in NEW and t != "_params"},
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

    base_params = _params(base_data / "data.db")
    base_files = _files_options(before)["maxSize"]
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
            "execution_jobs": [SERVICE_ONLY, SERVICE_ONLY, None, None, None],
            "execution_attempts": [SERVICE_ONLY, SERVICE_ONLY, None, None, None],
            "execution_envelopes": [OWNER_ONLY, OWNER_ONLY, None, None, None]}
    c.check("execution-migration.no-client-writes", rules == want, repr(rules))
    links = {name: {f["name"]: f for f in _fields(db, name)} for name in CHANGED}
    c.check("execution-migration.adds-the-links",
            all(field in links[name] and links[name][field]["type"] == "relation" and not links[name][field]["required"]
                for name, fields in CHANGED.items() for field in fields),
            repr({n: sorted(f) for n, f in links.items()}))
    envelope = {f["name"]: f for f in _fields(db, "execution_envelopes")}
    c.check("execution-migration.envelopes-link-into-no-service-only-collection",
            all(envelope.get(n, {}).get("type") == "text" for n in ("job", "attempt"))
            and _links_into_service_only(db) == [],
            f"links={_links_into_service_only(db)}")
    c.check("execution-migration.files-hold-8-mib", links["take_home_attempts"]["files"]["options"]["maxSize"] == 8 * MIB,
            repr(links["take_home_attempts"]["files"]["options"]))
    c.check("execution-migration.touches-nothing-else",
            _without_changes(applied, before) == _without_changes(before, before) and _params(db) == base_params,
            _differences(_without_changes(applied, before), _without_changes(before, before)))
    c.check("execution-migration.records-the-files-limit-it-found", _record(db) == {"files": base_files},
            f"record={_record(db)} base={base_files}")

    code, out = _migrate_down_confirmed(data, full)
    c.check("execution-migration.reverses", code == 0 and MIGRATION in out, f"exit={code} {out[-300:]!r}")
    reverted = _snapshot(db)
    c.check("execution-migration.down-restores-the-base", _normalized(reverted) == _normalized(before),
            _differences(_normalized(reverted), _normalized(before)))
    c.check("execution-migration.down-removes-the-record", _record(db) is None and _params(db) == base_params,
            f"record={_record(db)}")

    up = _migrate(data, full, "up")
    again = _snapshot(db)
    c.check("execution-migration.reapplies", up.returncode == 0 and all(n in again["collections"] for n in NEW)
            and _without_changes(again, before) == _without_changes(before, before), (up.stdout + up.stderr)[-500:])

    # PocketBase's own JSON reset first, then the base, so files holds what
    # 1700001300 declares when this migration runs, as on a database built
    # from scratch, where the reset sorts after this migration.
    empty = work / "empty_migrations"
    empty.mkdir()
    declared_data = work / "declared_pb_data"
    first = _migrate(declared_data, empty, "up")
    then = _migrate(declared_data, base, "up")
    ddb = declared_data / "data.db"
    held = _files_options(_snapshot(ddb))["maxSize"]
    up = _migrate(declared_data, full, "up")
    code, out = _migrate_down_confirmed(declared_data, full)
    restored = _files_options(_snapshot(ddb))["maxSize"]
    c.check("execution-migration.down-restores-a-declared-files-limit",
            first.returncode == 0 and then.returncode == 0 and up.returncode == 0 and held == 2 * MIB
            and restored == held and MIGRATION not in _snapshot(ddb)["migrations"] and _record(ddb) is None,
            (first.stderr + then.stderr + up.stderr)[-400:] or f"held={held} restored={restored} exit={code}")

    print(f"execution migration check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
