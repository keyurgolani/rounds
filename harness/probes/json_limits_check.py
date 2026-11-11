"""Harness check for the JSON field limits (ROUNDS-00A-L03, decision D10).

PocketBase's own ``1702134272_set_default_json_max_size`` migration sets
every JSON field to 2,000,000 bytes, and it sorts after the repository's
migrations, so on a fresh database it overwrote the limits they declare.
``1702134273_json_limits.js`` sorts right after it and sets them back. With
the pinned binary and no network:

1. Declared: PocketBase's own migrations first, then the repository's
   without the json_limits ones, leaves each JSON field at the limit its
   migrations declare. The other checks are held to that.
2. Without the registry, a fresh database holds every JSON field at the
   2,000,000-byte default.
3. Fresh: every migration on an empty ``pb_data`` leaves every JSON field
   at its declared limit, the snapshot store's three among them.
4. Upgraded: a ``pb_data`` built with every migration before
   ``1700007100_execution_jobs.js``, then given the rest, holds every
   declared limit, and the registry's own step changes JSON limits only,
   plus its record of the size each field it changed held before.
5. Again: on the declared database, where every limit already holds, the
   registry saves no collection and records nothing.
6. Down: ``pocketbase migrate down 1`` on the upgraded database, confirmed
   on a pseudo terminal, reverses the registry, puts each JSON field back at
   the size it held before, so a field that already held its declared size
   keeps it, removes the record, and changes nothing else; applying it again
   restores the declared limits.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

from admission_migration_check import MIGRATIONS, Checks, _differences, _migrate, _migrate_down_confirmed, _snapshot

REGISTRY = "1702134273_json_limits.js"
# The _params row the registry records the sizes it changed in.
PRIOR_KEY = REGISTRY
# The same names scripts/lint_migrations.py treats as json_limits migrations.
REGISTRY_FILE = re.compile(r"\A\d+_json_limits(?:_[a-z0-9]+)*\.js\Z")
# The upgrade starts from every migration before this PR's first.
UPGRADE_FROM = "1700007100_execution_jobs.js"
DEFAULT_BYTES = 2_000_000
# The snapshot store's JSON fields (1700008000_legacy_artifact_snapshots.js).
SNAPSHOT_LIMITS = {
    ("legacy_artifact_snapshots", "design"): 64 * 1024,
    ("legacy_artifact_snapshots", "data"): 2 * 1024 * 1024,
    ("legacy_artifact_snapshots", "font_families"): 4 * 1024,
}


def _connect(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)


def _limits(db: Path) -> dict[tuple[str, str], int | None]:
    """Every JSON field's maxSize."""
    conn = _connect(db)
    try:
        rows = conn.execute("SELECT name, schema FROM _collections ORDER BY name").fetchall()
    finally:
        conn.close()
    return {(name, field["name"]): (field.get("options") or {}).get("maxSize")
            for name, schema in rows for field in json.loads(schema) if field.get("type") == "json"}


def _rows(db: Path) -> dict[str, tuple]:
    """Every ``_collections`` row whole, its ``updated`` time included."""
    conn = _connect(db)
    try:
        return {row[0]: row for row in conn.execute("SELECT name, * FROM _collections ORDER BY name")}
    finally:
        conn.close()


def _params(db: Path) -> dict[str, str]:
    """Every ``_params`` row but the registry's record."""
    conn = _connect(db)
    try:
        return {key: value for key, value in conn.execute("SELECT key, value FROM _params ORDER BY key")
                if key != PRIOR_KEY}
    finally:
        conn.close()


def _record(db: Path) -> dict[tuple[str, str], int] | None:
    """The registry's record, field to the size it held before, or None."""
    conn = _connect(db)
    try:
        row = conn.execute("SELECT value FROM _params WHERE key = ?", (PRIOR_KEY,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    entries = json.loads(row[0])
    record = {(c, f): size for c, f, size in entries}
    return record if len(record) == len(entries) else {}


def _without_limits(snapshot: dict) -> dict:
    """The snapshot with each JSON field's maxSize, the json_limits
    migrations, and the ``_params`` count taken out, so what's left is
    everything else; ``_params`` is compared apart, by row."""
    collections = {}
    for name, value in snapshot["collections"].items():
        schema = json.loads(value[1])
        for field in schema:
            if field.get("type") == "json":
                field.setdefault("options", {})["maxSize"] = None
        collections[name] = (value[0], json.dumps(schema, sort_keys=True), *value[2:])
    return {"counts": {t: n for t, n in snapshot["counts"].items() if t != "_params"}, "collections": collections,
            "migrations": [m for m in snapshot["migrations"] if not REGISTRY_FILE.match(m)]}


def _limit_differences(got: dict, want: dict) -> str:
    keys = sorted(set(got) | set(want))
    wrong = [f"{c}.{f}={got.get((c, f))} (want {want.get((c, f))})" for c, f in keys if got.get((c, f)) != want.get((c, f))]
    return f"{len(wrong)} differ: " + ", ".join(wrong[:6]) if wrong else "none"


def _dir(work: Path, name: str, files: list[str]) -> Path:
    out = work / name
    out.mkdir()
    for file in files:
        shutil.copy(MIGRATIONS / file, out / file)
    return out


def main() -> int:
    c = Checks()
    work = Path(tempfile.mkdtemp(prefix="json-limits-check-"))
    every = sorted(p.name for p in MIGRATIONS.glob("*.js"))
    registries = [name for name in every if REGISTRY_FILE.match(name)]
    c.check("json-limits.registry.sorts-right-after-the-reset", registries[:1] == [REGISTRY], repr(registries))
    empty = _dir(work, "empty", [])
    repo = _dir(work, "repo", [name for name in every if name not in registries])
    full = _dir(work, "full", every)
    base = _dir(work, "base", [name for name in every if name < UPGRADE_FROM])

    # 1. The reference: PocketBase's reset first, so nothing overwrites what
    #    the repository's migrations declare.
    declared_data = work / "declared"
    first = _migrate(declared_data, empty, "up")
    then = _migrate(declared_data, repo, "up")
    declared = _limits(declared_data / "data.db")
    c.check("json-limits.declared.every-field-has-its-limit",
            first.returncode == 0 and then.returncode == 0 and len(declared) >= 90
            and all(isinstance(v, int) and v > 0 for v in declared.values()),
            (first.stderr + then.stderr)[-400:] or f"fields={len(declared)}")
    if not declared:
        print(f"json limits check: {c.passed} passed, {c.failed} failed")
        return 1

    # 2. What the registry undoes.
    reset_data = work / "reset"
    up = _migrate(reset_data, repo, "up")
    reset = _limits(reset_data / "data.db")
    c.check("json-limits.without-the-registry.every-field-at-the-default",
            up.returncode == 0 and set(reset) == set(declared) and set(reset.values()) == {DEFAULT_BYTES},
            up.stderr[-400:] or _limit_differences(reset, {k: DEFAULT_BYTES for k in declared}))

    # 3. A database built from scratch.
    fresh_data = work / "fresh"
    up = _migrate(fresh_data, full, "up")
    fresh = _limits(fresh_data / "data.db")
    c.check("json-limits.fresh.holds-the-declared-limits", up.returncode == 0 and fresh == declared,
            up.stderr[-400:] or _limit_differences(fresh, declared))
    c.check("json-limits.fresh.snapshot-store-limits",
            {k: fresh.get(k) for k in SNAPSHOT_LIMITS} == SNAPSHOT_LIMITS == {k: declared.get(k) for k in SNAPSHOT_LIMITS},
            _limit_differences({k: fresh.get(k) for k in SNAPSHOT_LIMITS}, SNAPSHOT_LIMITS))

    # 4. A database upgraded in place, in one step and with the registry's
    #    own step on its own.
    base_data = work / "base_pb_data"
    up = _migrate(base_data, base, "up")
    c.check("json-limits.upgrade.base-applies", up.returncode == 0 and UPGRADE_FROM not in _snapshot(
        base_data / "data.db")["migrations"], up.stderr[-400:])
    one_step = work / "one_step"
    shutil.copytree(base_data, one_step)
    up = _migrate(one_step, full, "up")
    upgraded = _limits(one_step / "data.db")
    c.check("json-limits.upgrade.holds-the-declared-limits", up.returncode == 0 and upgraded == declared,
            up.stderr[-400:] or _limit_differences(upgraded, declared))
    data = work / "pb_data"
    shutil.copytree(base_data, data)
    db = data / "data.db"
    up = _migrate(data, repo, "up")
    before = _snapshot(db)
    held = _limits(db)
    params = _params(db)
    up_registry = _migrate(data, full, "up")
    after = _snapshot(db)
    c.check("json-limits.upgrade.changes-only-json-limits",
            up.returncode == 0 and up_registry.returncode == 0 and REGISTRY in after["migrations"]
            and _limits(db) == declared and _without_limits(after) == _without_limits(before)
            and _params(db) == params,
            (up.stderr + up_registry.stderr)[-400:] or _differences(_without_limits(after), _without_limits(before)))
    # Here the fields from 1700007100 on already held their declared sizes,
    # and the rest held the default.
    changed = {k: v for k, v in held.items() if v != declared.get(k)}
    kept = [k for k, v in held.items() if v == declared.get(k)]
    record = _record(db)
    c.check("json-limits.upgrade.records-what-it-changed",
            record == changed and bool(changed) and bool(kept),
            f"changed={len(changed)} kept={len(kept)} "
            + ("no record" if record is None else _limit_differences(record, changed)))

    # 5. Where every limit already holds.
    rows = _rows(declared_data / "data.db")
    up = _migrate(declared_data, full, "up")
    again = _rows(declared_data / "data.db")
    applied = REGISTRY in _snapshot(declared_data / "data.db")["migrations"]
    c.check("json-limits.again.saves-no-collection",
            up.returncode == 0 and applied and again == rows and _record(declared_data / "data.db") is None,
            up.stderr[-400:] or ", ".join(sorted(n for n in set(rows) | set(again) if rows.get(n) != again.get(n)))
            or "recorded a change")

    # 6. Reversing it, as an operator would, and applying it again.
    code, out = _migrate_down_confirmed(data, full)
    reverted = _snapshot(db)
    limits = _limits(db)
    c.check("json-limits.down.restores-what-each-field-held",
            code == 0 and REGISTRY in out and REGISTRY not in reverted["migrations"]
            and limits == held and _record(db) is None and _params(db) == params
            and reverted["counts"] == before["counts"] and _without_limits(reverted) == _without_limits(before),
            f"exit={code} {out[-300:]!r}" if code else _limit_differences(limits, held))
    up = _migrate(data, full, "up")
    c.check("json-limits.down.reapplies", up.returncode == 0 and _limits(db) == declared,
            up.stderr[-400:] or _limit_differences(_limits(db), declared))

    print(f"json limits check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
