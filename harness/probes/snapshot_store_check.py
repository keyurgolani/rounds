"""Harness check for the Legacy Artifact Snapshot store (ROUNDS-00A-L04, PR 1).

Applies and reverses ``1700008000_legacy_artifact_snapshots.js`` with the
pinned PocketBase binary on a ``pb_data`` with every migration that sorts
before it, seeds and the demo account included.

1. Applying it adds ``legacy_artifact_snapshots`` with owner-only list and
   view rules, null create, update, and delete, the fields and limits the
   migration states, and the unique reuse index, and changes no other table,
   row, or collection.
2. With one snapshot in it, reversing it (``pocketbase migrate down 1``,
   confirmed on a pseudo terminal as an operator would) fails and keeps the
   collection, the row, and the migration record.
3. Once the store is empty, reversing it drops only that collection, and the
   data is back to the base snapshot.
4. Applying it again after the reversal works.

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
    Checks,
    _differences,
    _migrate,
    _migrate_down_confirmed,
    _snapshot,
)

MIGRATION = "1700008000_legacy_artifact_snapshots.js"
COLLECTION = "legacy_artifact_snapshots"
OWNER_RULE = "user = @request.auth.id"
INDEX = (
    "CREATE UNIQUE INDEX idx_legacy_artifact_snapshots_reuse ON legacy_artifact_snapshots "
    "(user, source_kind, source_id, content_checksum, materializer_digest)"
)
MiB = 1024 * 1024
# name -> (type, required, the options the check pins)
FIELDS = {
    "user": ("relation", True, {"cascadeDelete": True, "maxSelect": 1}),
    "source_kind": ("text", True, {"pattern": "^(resume|variant)$"}),
    "source_id": ("text", True, {"pattern": "^[a-z0-9]{15}$"}),
    "source_updated": ("text", True, {}),
    "parent_id": ("text", False, {"pattern": "^([a-z0-9]{15})?$"}),
    "parent_updated": ("text", False, {}),
    "template_id": ("text", True, {"pattern": "^[a-z0-9-]{1,64}$"}),
    "template_fallback": ("bool", False, {}),
    "design": ("json", False, {"maxSize": 64 * 1024}),
    "data": ("json", True, {"maxSize": 2 * MiB}),
    "markup": ("file", True, {"maxSelect": 1, "maxSize": 2 * MiB, "mimeTypes": ["text/html"], "protected": True}),
    "content_checksum": ("text", True, {"pattern": "^sha256:[0-9a-f]{64}$"}),
    "materializer_digest": ("text", True, {"pattern": "^sha256:[0-9a-f]{64}$"}),
    "sanitizer_version": ("text", True, {}),
    "font_families": ("json", False, {"maxSize": 4 * 1024}),
    "size_bytes": ("number", True, {"min": 1, "max": 2 * MiB, "noDecimal": True}),
}
SNAPSHOT_ID = "harnesssnap0001"


def _connect(db: Path, write: bool = False) -> sqlite3.Connection:
    mode = "rw" if write else "ro"
    return sqlite3.connect(db.resolve().as_uri() + f"?mode={mode}", uri=True)


def _applied(db: Path, name: str) -> bool:
    conn = _connect(db)
    try:
        return conn.execute("SELECT 1 FROM _migrations WHERE file = ?", (name,)).fetchone() is not None
    finally:
        conn.close()


def _collection(db: Path) -> dict | None:
    conn = _connect(db)
    try:
        row = conn.execute(
            "SELECT schema, indexes, listRule, viewRule, createRule, updateRule, deleteRule FROM _collections WHERE name = ?",
            (COLLECTION,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    schema, indexes, *rules = row
    return {"schema": json.loads(schema), "indexes": json.loads(indexes), "rules": rules}


def _field_problems(schema: list[dict]) -> list[str]:
    by_name = {f["name"]: f for f in schema}
    problems = sorted(set(by_name) ^ set(FIELDS))
    for name, (ftype, required, options) in FIELDS.items():
        field = by_name.get(name)
        if field is None:
            continue
        if field.get("type") != ftype or bool(field.get("required")) != required:
            problems.append(f"{name}:type-or-required")
        for key, want in options.items():
            if (field.get("options") or {}).get(key) != want:
                problems.append(f"{name}.{key}")
    return problems


def _fresh_field_problems(schema: list[dict]) -> list[str]:
    # On a fresh database, PocketBase's own 1702134272_set_default_json_max_size
    # runs after this migration (decision D10) and resets every JSON field's
    # maxSize to its 2,000,000 default, so the intended smaller design and
    # font_families limits are not in force until #200's re-apply registry
    # restores them. The structural guarantee that must hold on a fresh
    # database: the collection exists, every field has its type and required
    # flag, and no JSON field is left at maxSize 0 (which would reject every
    # value). The exact small limits are checked on the upgraded database.
    by_name = {f["name"]: f for f in schema}
    problems = sorted(set(by_name) ^ set(FIELDS))
    for name, (ftype, required, options) in FIELDS.items():
        field = by_name.get(name)
        if field is None:
            continue
        if field.get("type") != ftype or bool(field.get("required")) != required:
            problems.append(f"{name}:type-or-required")
        if ftype == "json" and not ((field.get("options") or {}).get("maxSize", 0) > 0):
            problems.append(f"{name}.maxSize-zero")
        if ftype != "json":
            for key, want in options.items():
                if (field.get("options") or {}).get(key) != want:
                    problems.append(f"{name}.{key}")
    return problems


def _without_store(snapshot: dict) -> dict:
    return {
        "counts": {t: n for t, n in snapshot["counts"].items() if t != COLLECTION},
        "collections": {n: v for n, v in snapshot["collections"].items() if n != COLLECTION},
        "migrations": [m for m in snapshot["migrations"] if m != MIGRATION],
    }


def _plant(db: Path) -> None:
    """One snapshot row, written straight to SQLite, since no client may."""
    conn = _connect(db, write=True)
    try:
        (user,) = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
        stamp = "2026-10-20 00:00:00.000Z"
        digest = "sha256:" + "0" * 64
        conn.execute(
            f"INSERT INTO {COLLECTION} (id, created, updated, user, source_kind, source_id, source_updated, parent_id, "
            "parent_updated, template_id, template_fallback, design, data, markup, content_checksum, "
            "materializer_digest, sanitizer_version, font_families, size_bytes) "
            "VALUES (?, ?, ?, ?, 'resume', 'harnessresume01', ?, '', '', 'modern', 0, '{}', '{}', 'snapshot.html', ?, ?, "
            "'1.0.0', '[]', 10)",
            (SNAPSHOT_ID, stamp, stamp, user, stamp, digest, digest),
        )
        conn.commit()
    finally:
        conn.close()


def _remove_planted(db: Path) -> None:
    conn = _connect(db, write=True)
    try:
        conn.execute(f"DELETE FROM {COLLECTION} WHERE id = ?", (SNAPSHOT_ID,))
        conn.commit()
    finally:
        conn.close()


def _rows(db: Path) -> int | None:
    conn = _connect(db)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {COLLECTION}").fetchone()[0]
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def main() -> int:
    c = Checks()
    work = Path(tempfile.mkdtemp(prefix="snapshot-store-"))
    try:
        base = work / "base_migrations"
        full = work / "migrations"
        base.mkdir()
        full.mkdir()
        earlier = sorted(p for p in MIGRATIONS.glob("*.js") if p.name < MIGRATION)
        for path in earlier:
            shutil.copy(path, base / path.name)
            shutil.copy(path, full / path.name)
        shutil.copy(MIGRATIONS / MIGRATION, full / MIGRATION)

        base_data = work / "base_pb_data"
        up = _migrate(base_data, base, "up")
        if not c.check("snapshot-store.base.applies", _applied(base_data / "data.db", earlier[-1].name), up.stderr[-500:]):
            print(f"snapshot store check: {c.passed} passed, {c.failed} failed")
            return 1
        before = _snapshot(base_data / "data.db")

        data = work / "pb_data"
        shutil.copytree(base_data, data)
        db = data / "data.db"
        up = _migrate(data, full, "up")
        c.check("snapshot-store.applies", _applied(db, MIGRATION), (up.stdout + up.stderr)[-500:])
        found = _collection(db)
        c.check("snapshot-store.adds-the-collection", found is not None, "collection missing")
        if found is None:
            print(f"snapshot store check: {c.passed} passed, {c.failed} failed")
            return 1
        c.check("snapshot-store.owner-reads-and-no-client-writes",
                found["rules"] == [OWNER_RULE, OWNER_RULE, None, None, None], repr(found["rules"]))
        problems = _field_problems(found["schema"])
        c.check("snapshot-store.fields-and-limits", not problems, ", ".join(problems))
        c.check("snapshot-store.unique-reuse-index", found["indexes"] == [INDEX], repr(found["indexes"]))
        applied = _snapshot(db)
        c.check("snapshot-store.touches-nothing-else", _without_store(applied) == before,
                _differences(_without_store(applied), before))

        _plant(db)
        code, out = _migrate_down_confirmed(data, full)
        kept = _collection(db) is not None and _rows(db) == 1 and _applied(db, MIGRATION)
        c.check("snapshot-store.down-keeps-a-non-empty-store", kept, f"exit={code} rows={_rows(db)} {out[-300:]!r}")

        _remove_planted(db)
        code, out = _migrate_down_confirmed(data, full)
        reverted = _snapshot(db)
        c.check("snapshot-store.down-drops-an-empty-store",
                _collection(db) is None and not _applied(db, MIGRATION) and reverted == before,
                f"exit={code} {_differences(reverted, before)} {out[-300:]!r}")

        up = _migrate(data, full, "up")
        again = _collection(db)
        c.check("snapshot-store.reapplies",
                _applied(db, MIGRATION) and again is not None and _without_store(_snapshot(db)) == before,
                (up.stdout + up.stderr)[-500:])

        # A fresh database: the whole migration set applied in one `migrate
        # up` on an empty pb_data, so PocketBase's own JSON-size-default
        # migration runs after this one (decision D10). The collection must
        # still be created, owner-read, uniquely indexed, and usable; the
        # exact small JSON limits land with #200's re-apply registry.
        fresh = work / "fresh_pb_data"
        up = _migrate(fresh, full, "up")
        fdb = fresh / "data.db"
        c.check("snapshot-store.fresh.applies", _applied(fdb, MIGRATION), (up.stdout + up.stderr)[-500:])
        ffound = _collection(fdb)
        c.check("snapshot-store.fresh.adds-the-collection", ffound is not None,
                "collection missing on a fresh database")
        if ffound is not None:
            c.check("snapshot-store.fresh.owner-reads-and-no-client-writes",
                    ffound["rules"] == [OWNER_RULE, OWNER_RULE, None, None, None], repr(ffound["rules"]))
            c.check("snapshot-store.fresh.unique-reuse-index", ffound["indexes"] == [INDEX],
                    repr(ffound["indexes"]))
            fresh_problems = _fresh_field_problems(ffound["schema"])
            c.check("snapshot-store.fresh.fields-usable", not fresh_problems, ", ".join(fresh_problems))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print(f"snapshot store check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
