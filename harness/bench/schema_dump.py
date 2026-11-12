"""Dump the real PocketBase schema at this revision (ROUNDS-02-L01).

    python harness/bench/schema_dump.py [--pocketbase PATH] [--out contracts/database/schema-snapshot.json]

Runs `pocketbase migrate up` (no serve, no port) on a throwaway directory
under harness/bench/.scratch/, reads the migrated data.db read-only, and
writes the collections, fields, relations, indexes, rules, system tables,
and triggers as JSON. scripts/conformance/rules/database-adr.mjs builds the
ERD's generated part, contracts/database/erd.json, from this snapshot, so the
ERD's cascade flags, relation targets, and indexes are PocketBase's own, not
a reading of the migration files. A PR that adds or changes a migration runs
this, then node scripts/conformance/run.mjs --write; until it does, the rule
fails it with DB_ERD_STALE. The scratch goes to the Trash afterwards.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pbnative  # noqa: E402

SNAPSHOT = pbnative.ROOT / "contracts" / "database" / "schema-snapshot.json"
# PocketBase's own tables (0.22): not collections, never account rows except
# _externalAuths, which links an account to its OAuth2 identities.
SYSTEM_TABLES = ("_admins", "_collections", "_externalAuths", "_migrations", "_params")


def git_head() -> dict:
    def run(*args: str) -> str:
        return subprocess.run(["git", "--no-optional-locks", *args], cwd=pbnative.ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    # The newest commit that changed a migration: the schema below is that
    # commit's, and the commit stays on next after a squash merge.
    dirty = run("status", "--porcelain", "--", "pocketbase/pb_migrations")
    return {"commit": run("log", "-1", "--format=%H", "--", "pocketbase/pb_migrations"), "migrationsClean": dirty == ""}


def _field(f: dict, names: dict[str, str]) -> dict:
    out = {"name": f["name"], "type": f["type"], "required": bool(f.get("required"))}
    opts = f.get("options") or {}
    if f["type"] == "relation":
        target = opts.get("collectionId")
        out["relation"] = {
            "collection": names.get(target, target),
            "cascadeDelete": bool(opts.get("cascadeDelete")),
            "minSelect": opts.get("minSelect"),
            "maxSelect": opts.get("maxSelect"),
        }
    elif f["type"] == "file":
        out["file"] = {"maxSelect": opts.get("maxSelect"), "maxSize": opts.get("maxSize"), "protected": bool(opts.get("protected"))}
    elif f["type"] == "json":
        out["maxSize"] = opts.get("maxSize")
    if f.get("unique"):
        out["unique"] = True
    return out


_INDEX = re.compile(
    r"^\s*CREATE\s+(UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(\w+)[`\"]?\s+ON\s+[`\"]?(\w+)[`\"]?\s*\((.*)\)\s*(?:WHERE\s+(.*))?$",
    re.IGNORECASE | re.DOTALL,
)


def _index(sql: str) -> dict:
    """An index as name, uniqueness, and table-qualified columns in key order.

    The SQL text itself stays in the migration that creates it.
    """
    m = _INDEX.match(sql)
    if not m:
        return {"unparsed": True, "sha256": hashlib.sha256(sql.encode()).hexdigest()}
    unique, name, table, cols, where = m.groups()
    quotes = "`\""
    columns = [table + "." + c.strip().strip(quotes) for c in cols.split(",")]
    out = {"name": name, "unique": bool(unique), "columns": columns}
    if where:
        out["partial"] = True
    return out


def _rule_class(rule: str | None) -> str:
    """null (superuser and server code only), open (anyone), or expression.

    The expressions themselves live in docs/security/account-scope.v1.json;
    the ERD needs only who can reach the API at all.
    """
    if rule is None:
        return "null"
    return "open" if rule == "" else "expression"


def dump(db_path: Path) -> dict:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT id, name, type, system, schema, indexes, listRule, viewRule, createRule, updateRule, deleteRule "
            "FROM _collections ORDER BY name").fetchall()
        names = {r[0]: r[1] for r in rows}
        collections = []
        for cid, name, ctype, system, schema, indexes, *rules in rows:
            # Sorted by name, so a regenerated snapshot diffs by field.
            fields = sorted((_field(f, names) for f in json.loads(schema or "[]")), key=lambda f: f["name"])
            collections.append({
                "name": name,
                "type": ctype,
                "system": bool(system),
                "fields": fields,
                "indexes": sorted((_index(i) for i in json.loads(indexes or "[]")), key=lambda i: i.get("name", "")),
                "rules": dict(zip(("list", "view", "create", "update", "delete"), (_rule_class(r) for r in rules))),
            })
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        triggers = [{"name": n, "table": t} for n, t in con.execute(
            "SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger' ORDER BY name")]
        applied = [r[0] for r in con.execute("SELECT file FROM _migrations ORDER BY file")]
    finally:
        con.close()
    return {"collections": collections, "systemTables": [t for t in SYSTEM_TABLES if t in tables],
            "triggers": triggers, "appliedMigrations": applied}


def relation_semantics(binary: Path) -> dict:
    """What PocketBase does to a reference when its target goes, read from
    a probe migration in a throwaway directory of its own."""
    root = pbnative.run_dir("relation-probe")
    try:
        dirs = pbnative.Dirs(root=root, migrations=root / "pb_migrations", hooks=root / "pb_hooks", data=root / "pb_data")
        for d in (dirs.migrations, dirs.hooks, dirs.data):
            d.mkdir()
        probe = Path(__file__).resolve().parent / "pb_migrations_probe" / "1900000000_relation_delete_probe.js"
        (dirs.migrations / probe.name).write_text(probe.read_text())
        pbnative.migrate_up(binary, dirs)
        con = sqlite3.connect(f"file:{dirs.data / 'data.db'}?mode=ro", uri=True)
        try:
            return dict(con.execute("SELECT \"case\", outcome FROM probe_results ORDER BY \"case\"").fetchall())
        finally:
            con.close()
    finally:
        pbnative.to_trash(root, "relation-probe")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--pocketbase", default=None)
    ap.add_argument("--out", default=str(SNAPSHOT))
    args = ap.parse_args(argv)
    binary = pbnative.binary_path(args.pocketbase)
    root = pbnative.run_dir("schema")
    try:
        dirs, note = pbnative.prepare(root, with_hooks=False)
        pbnative.migrate_up(binary, dirs)
        snap = dump(dirs.data / "data.db")
    finally:
        moved = pbnative.to_trash(root, "schema")
    repo_files = sorted(p.name for p in pbnative.REPO_MIGRATIONS.glob("*.js"))
    doc = {
        "$schema": "./schema-snapshot.schema.json",
        "description": "PocketBase's own schema after every migration at the revision below, from `pocketbase migrate up` on an empty directory (harness/bench/schema_dump.py). Regenerate it with that script; never edit it by hand. The ERD (erd.json) is checked against it.",
        "pocketbaseVersion": pbnative.binary_version(binary),
        "revision": git_head(),
        "migrations": [{"file": f, "sha256": pbnative.sha256_file(pbnative.REPO_MIGRATIONS / f)} for f in repo_files],
        "nativeRun": note["seedPathRewrite"],
        "relationDeleteSemantics": relation_semantics(binary),
        **snap,
    }
    missing = sorted(set(repo_files) - set(doc["appliedMigrations"]))
    if missing:
        print(f"not applied: {missing}", file=sys.stderr)
        return 1
    Path(args.out).write_text(json.dumps(doc, indent=2, sort_keys=False) + "\n")
    print(f"wrote {args.out}: {len(doc['collections'])} collections, {len(doc['triggers'])} triggers; scratch moved to {moved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
