#!/usr/bin/env python3
"""Read-only cross-owner relation scan for a PocketBase ``pb_data`` database.

Lists every row whose relation field points at a record owned by a
different account, so an operator can hand the list to the relation
quarantine (ROUNDS-00B-L02) before the account-scope rule migration ships.

What it does, in order:

1. Copies ``data.db`` and its write-ahead log (``data.db-wal``, when present)
   into a private temporary directory with plain file reads, retrying if the
   files change while they are copied. It never opens the source with SQLite
   and never creates or changes anything in the source directory.
2. Copies that private copy with the SQLite online-backup API into a scan
   copy, opens the scan copy read-only, and reads the collection schema from
   ``_collections``.
3. For every account-owned collection (one whose owner field, ``user`` unless
   the policy names another, is a relation to the ``users`` auth collection),
   checks each relation field whose target is also account-owned or is
   ``users``, in a fixed order: collection, field, record id.
4. Writes a JSON report outside the database directory, readable only by the
   operator, then deletes every temporary copy.

The report holds collection names, field names, record ids, target ids,
per-report owner pseudonyms (``acct-01`` ...), and counts. It never holds
field values or account ids: a target id that is itself an account (a
relation into ``users``) is replaced with that account's pseudonym. The tool
makes no network request (no superuser or REST API). Reports are
operator-only and must be deleted within 14 days (``expires_at``).

Not covered: ids kept inside text or JSON fields (soft references, listed in
the report's ``not_covered``), and rows whose owner was set to another account
without any foreign relation.

Usage::

    python3 pocketbase/tools/scan_cross_owner.py \\
        --db /path/to/pb_data-copy/data.db \\
        --out /path/outside/pb_data/cross-owner-report.json

Exit codes: 0 scan completed with no findings; 1 scan completed with
findings; 2 usage or runtime error (no report written); 3 scan completed but
the policy check failed (the policy and this database disagree about owned
collections or relation fields, so the scan may be incomplete; see
``policy_check``).

Standard library only; Python 3.9 or newer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

REPORT_VERSION = "v1"
REPORT_KIND = "rounds.cross-owner-scan"
RETENTION_DAYS = 14
DEFAULT_OWNER_FIELD = "user"
USERS_COLLECTION = "users"
SUPPORTED_POLICY_VERSION = "v1"
COPY_ATTEMPTS = 3

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2
EXIT_POLICY_MISMATCH = 3


def default_policy() -> Path | None:
    """The repository's rule table when the tool runs from a checkout.

    Returns ``None`` when the tool was copied or mounted elsewhere (for
    example ``/tools/scan_cross_owner.py`` in a container) and no rule
    table sits at the expected place relative to it.
    """
    here = Path(__file__).resolve()
    if len(here.parents) < 3:
        return None
    candidate = here.parents[2] / "docs" / "security" / "account-scope.v1.json"
    return candidate if candidate.is_file() else None


# Ids kept inside text or JSON fields. The scan cannot see these; the
# report lists the ones present in the scanned schema so the reader knows.
SOFT_REFERENCES = [
    ("applications", "resume_variant", "text field holding a resume_variants id"),
    ("resumes", "links", "JSON reference graph into the experience library"),
    ("resume_variants", "links", "JSON reference graph into the experience library"),
    ("resume_versions", "links", "JSON reference graph into the experience library"),
    ("todos", "mentions", "JSON mention tokens"),
]


class ScanError(RuntimeError):
    """A condition that stops the scan before any report is written."""


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def _same_file(a: Path, b: Path) -> bool:
    try:
        sa, sb = os.stat(a), os.stat(b)
    except OSError:
        return False
    return (sa.st_dev, sa.st_ino) == (sb.st_dev, sb.st_ino)


def _within(path: Path, directory: Path) -> bool:
    """True when the existing directory ``path`` is ``directory`` or inside it.

    Compared by device and inode along the ancestry, so a differently cased
    path on a case-insensitive filesystem, or a symlink, cannot hide that
    two paths are the same directory.
    """
    p = path.resolve()
    return any(_same_file(candidate, directory) for candidate in (p, *p.parents))


# ---------------------------------------------------------------------------
# Copy and open
# ---------------------------------------------------------------------------


def _copy_file(src: Path, dst: Path) -> None:
    shutil.copyfile(src, dst)


def _snapshot(paths: list[Path]) -> tuple:
    """Size and modification time of each path (None when absent)."""
    out = []
    for p in paths:
        try:
            st = os.stat(p)
            out.append((p.name, st.st_size, st.st_mtime_ns))
        except FileNotFoundError:
            out.append((p.name, None, None))
    return tuple(out)


def stage_source(db: Path, staging: Path, attempts: int = COPY_ATTEMPTS) -> Path:
    """Copy ``db`` and its ``-wal`` into ``staging`` with plain file reads.

    The source is never opened with SQLite, so nothing (not even a shared-
    memory ``-shm`` file) is created or changed beside it, and a read-only
    source directory works. The ``-shm`` file is not copied: it is a cache
    that SQLite rebuilds from the WAL when the copy is opened. If the files
    change while they are copied (a running PocketBase), the copy is retried;
    after ``attempts`` tries the scan stops rather than read a torn copy.
    """
    wal = db.with_name(db.name + "-wal")
    staged_db = staging / db.name
    staged_wal = staging / wal.name
    for _ in range(attempts):
        for leftover in (staged_db, staged_wal):
            if leftover.exists():
                leftover.unlink()
        before = _snapshot([db, wal])
        _copy_file(db, staged_db)
        if wal.exists():
            _copy_file(wal, staged_wal)
        if _snapshot([db, wal]) == before:
            return staged_db
    raise ScanError(
        "the database kept changing while it was copied; stop PocketBase or "
        "scan a backup copy taken with PocketBase stopped"
    )


def backup_copy(db: Path, work_dir: Path) -> Path:
    """Make a private, read-only-openable scan copy of ``db`` in ``work_dir``.

    The source files are first copied into a private staging directory
    (``stage_source``); the staged copy is then copied with the SQLite
    online-backup API into ``scan-copy.db``, which is switched to a rollback
    journal so it opens read-only without sidecar files. The staging copy is
    deleted before returning.
    """
    db = db.resolve()
    if not db.is_file():
        raise ScanError(f"database not found: {db}")
    staging = work_dir / "staging"
    staging.mkdir(mode=0o700)
    dst_path = work_dir / "scan-copy.db"
    try:
        staged = stage_source(db, staging)
        src = sqlite3.connect(str(staged))
        try:
            dst = sqlite3.connect(str(dst_path))
            try:
                src.backup(dst, pages=256)
                dst.execute("PRAGMA journal_mode=DELETE")
            finally:
                dst.close()
        except sqlite3.Error as err:
            raise ScanError(f"could not copy the database: {err}") from err
        finally:
            src.close()
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    os.chmod(dst_path, 0o600)
    return dst_path


def open_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def _ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def load_collections(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    """Collections keyed by id: name, type, and parsed field list."""
    try:
        rows = conn.execute("SELECT id, name, type, schema FROM _collections").fetchall()
    except sqlite3.Error as err:
        raise ScanError(f"not a PocketBase database (no _collections): {err}") from err
    out: dict[str, dict[str, Any]] = {}
    for cid, name, ctype, schema in rows:
        try:
            fields = json.loads(schema or "[]")
        except ValueError as err:
            raise ScanError(f"unreadable schema for collection {name}: {err}") from err
        out[cid] = {"id": cid, "name": name, "type": ctype, "fields": fields}
    return out


def _users_id(collections: dict[str, dict[str, Any]]) -> str:
    for c in collections.values():
        if c["name"] == USERS_COLLECTION and c["type"] == "auth":
            return c["id"]
    raise ScanError("no users auth collection in this database")


def _has_owner_field(collection: dict[str, Any], users_id: str, owner_field: str) -> bool:
    for f in collection["fields"]:
        if (
            f.get("name") == owner_field
            and f.get("type") == "relation"
            and (f.get("options") or {}).get("collectionId") == users_id
        ):
            return True
    return False


def plan_relations(
    collections: dict[str, dict[str, Any]],
    owner_fields: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Decide which relation fields the scan checks.

    ``owner_fields`` maps a collection name to the field that names its
    owning account (from the policy); any other collection uses ``user``.
    Returns ``checked`` (account-owned source and an account-owned or
    ``users`` target, sorted by collection then field), ``shared`` (relations
    into shared content, which have no owner and are not checked), and the
    owned collections.
    """
    owner_fields = owner_fields or {}
    users_id = _users_id(collections)

    def owner_field_of(c: dict[str, Any]) -> str:
        return owner_fields.get(c["name"], DEFAULT_OWNER_FIELD)

    owned = {
        cid for cid, c in collections.items()
        if c["id"] != users_id and _has_owner_field(c, users_id, owner_field_of(c))
    }
    checked: list[dict[str, Any]] = []
    shared: list[dict[str, Any]] = []
    for cid in owned:
        source = collections[cid]
        source_owner = owner_field_of(source)
        for f in source["fields"]:
            if f.get("type") != "relation" or f.get("name") == source_owner:
                continue
            target_id = (f.get("options") or {}).get("collectionId")
            target = collections.get(target_id)
            if target is None:
                raise ScanError(
                    f"{source['name']}.{f['name']} points at an unknown collection"
                )
            entry = {
                "collection": source["name"],
                "field": f["name"],
                "target_collection": target["name"],
            }
            if target_id == users_id or target_id in owned:
                entry["owner_field"] = source_owner
                entry["target_is_users"] = target_id == users_id
                entry["target_owner_field"] = None if target_id == users_id else owner_field_of(target)
                checked.append(entry)
            else:
                shared.append(entry)
    key = lambda e: (e["collection"], e["field"])  # noqa: E731
    return {
        "checked": sorted(checked, key=key),
        "shared": sorted(shared, key=key),
        "owned": sorted(collections[c]["name"] for c in owned),
        "users_id": users_id,
        "collections_by_name": {c["name"]: c for c in collections.values()},
        "all_fields": {
            (c["name"], f.get("name")): f.get("type")
            for c in collections.values()
            for f in c["fields"]
        },
    }


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


def _refs(value: Any) -> list[str]:
    """Relation ids stored in a column: a plain id or a JSON array of ids."""
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            items = json.loads(text)
        except ValueError:
            return []
        return [str(i) for i in items if isinstance(i, str) and i]
    return [text]


def _owner_map(conn: sqlite3.Connection, rel: dict[str, Any]) -> dict[str, str]:
    target = rel["target_collection"]
    if rel["target_is_users"]:
        rows = conn.execute(f"SELECT id FROM {_ident(target)}").fetchall()
        return {r[0]: r[0] for r in rows}
    rows = conn.execute(
        f"SELECT id, {_ident(rel['target_owner_field'])} FROM {_ident(target)}"
    ).fetchall()
    return {r[0]: (r[1] or "") for r in rows}


def scan(conn: sqlite3.Connection, plan: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    per_field: list[dict[str, Any]] = []
    owner_cache: dict[tuple[str, str | None], dict[str, str]] = {}
    for rel in plan["checked"]:
        target = rel["target_collection"]
        cache_key = (target, rel["target_owner_field"])
        if cache_key not in owner_cache:
            owner_cache[cache_key] = _owner_map(conn, rel)
        owners = owner_cache[cache_key]
        rows = conn.execute(
            f"SELECT id, {_ident(rel['owner_field'])}, {_ident(rel['field'])} "
            f"FROM {_ident(rel['collection'])} ORDER BY id"
        ).fetchall()
        counts = {"rows": len(rows), "references": 0, "cross_owner": 0, "missing_target": 0}
        for record_id, owner, value in rows:
            for ref in _refs(value):
                counts["references"] += 1
                if ref not in owners:
                    kind, target_owner = "missing_target", None
                elif owners[ref] != (owner or ""):
                    kind, target_owner = "cross_owner", owners[ref]
                else:
                    continue
                counts[kind] += 1
                findings.append(
                    {
                        "kind": kind,
                        "collection": rel["collection"],
                        "field": rel["field"],
                        "record_id": record_id,
                        "target_collection": target,
                        "target_id": ref,
                        "_owner": owner or "",
                        "_target_owner": target_owner,
                        "_target_is_users": rel["target_is_users"],
                    }
                )
        per_field.append(
            {
                "collection": rel["collection"],
                "field": rel["field"],
                "target_collection": target,
                **counts,
            }
        )
    findings.sort(key=lambda f: (f["collection"], f["field"], f["record_id"], f["target_id"]))
    return {"findings": findings, "per_field": per_field}


def pseudonymize(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace every account id with a per-report label assigned in scan order.

    Owners and target owners are accounts. A target id is also an account
    when the relation points into ``users``; it gets the same label space, so
    the report holds no account id anywhere.
    """
    labels: dict[str, str] = {}

    def label(account: str | None) -> str | None:
        if account is None:
            return None
        if account not in labels:
            labels[account] = f"acct-{len(labels) + 1:02d}"
        return labels[account]

    out = []
    for f in findings:
        g = {k: v for k, v in f.items() if not k.startswith("_")}
        g["owner"] = label(f["_owner"])
        if f.get("_target_is_users"):
            g["target_id"] = label(f["target_id"])
        g["target_owner"] = label(f["_target_owner"])
        out.append(g)
    return out


# ---------------------------------------------------------------------------
# Policy cross-check (optional)
# ---------------------------------------------------------------------------


def load_policy(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError) as err:
        raise ScanError(f"could not read policy {path}: {err}") from err
    if doc.get("version") != SUPPORTED_POLICY_VERSION:
        raise ScanError(
            f"unsupported policy version {doc.get('version')!r}; "
            f"this tool understands {SUPPORTED_POLICY_VERSION!r}"
        )
    return doc


def policy_owner_fields(policy: dict[str, Any] | None) -> dict[str, str]:
    """Owner field per account-owned collection named in the policy."""
    if policy is None:
        return {}
    return {
        name: row.get("owner_field", DEFAULT_OWNER_FIELD)
        for name, row in policy.get("collections", {}).items()
        if name != USERS_COLLECTION
    }


def policy_check(policy: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Compare this database's owned collections and relations with the policy.

    ``ok`` is false when the scan can see a relation between owned collections
    that the policy does not list (the policy is stale), or when a collection
    the policy lists exists but lacks its owner field (the scan would treat it
    as shared content and skip it). Policy entries this database does not have
    at all (an older release) are reported but do not fail the check.
    """
    listed = {
        (name, field)
        for name, row in policy.get("collections", {}).items()
        for field in row.get("relation_exceptions", [])
    }
    checked = {(r["collection"], r["field"]) for r in plan["checked"]}
    relations_in_db = {key for key, ftype in plan["all_fields"].items() if ftype == "relation"}
    by_name = plan["collections_by_name"]
    owner_field_missing = []
    collections_absent = []
    for name, owner_field in sorted(policy_owner_fields(policy).items()):
        collection = by_name.get(name)
        if collection is None:
            collections_absent.append({"collection": name})
        elif not _has_owner_field(collection, plan["users_id"], owner_field):
            owner_field_missing.append({"collection": name, "owner_field": owner_field})
    unlisted = [{"collection": c, "field": f} for c, f in sorted(checked - listed)]
    return {
        "policy_version": policy.get("version"),
        "ok": not unlisted and not owner_field_missing,
        "unlisted_in_policy": unlisted,
        "owner_field_missing": owner_field_missing,
        "listed_but_absent": [
            {"collection": c, "field": f} for c, f in sorted(listed - relations_in_db)
        ],
        "collections_absent": collections_absent,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _not_covered(plan: dict[str, Any]) -> list[dict[str, str]]:
    present = plan["all_fields"]
    return [
        {"collection": c, "field": f, "reason": reason}
        for c, f, reason in SOFT_REFERENCES
        if (c, f) in present
    ]


def _migrations(conn: sqlite3.Connection) -> dict[str, Any]:
    try:
        rows = conn.execute("SELECT file FROM _migrations ORDER BY file").fetchall()
    except sqlite3.Error:
        return {"applied": None, "last": None}
    files = [r[0] for r in rows]
    return {"applied": len(files), "last": files[-1] if files else None}


def build_report(
    conn: sqlite3.Connection,
    plan: dict[str, Any],
    result: dict[str, Any],
    policy: dict[str, Any] | None,
    now: datetime,
) -> dict[str, Any]:
    findings = pseudonymize(result["findings"])
    body = {
        "version": REPORT_VERSION,
        "relations": result["per_field"],
        "findings": findings,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    summary = {
        "owned_collections": len(plan["owned"]),
        "relations_checked": len(plan["checked"]),
        "rows_scanned": sum(r["rows"] for r in result["per_field"]),
        "references_checked": sum(r["references"] for r in result["per_field"]),
        "cross_owner": sum(1 for f in findings if f["kind"] == "cross_owner"),
        "missing_target": sum(1 for f in findings if f["kind"] == "missing_target"),
    }
    return {
        "kind": REPORT_KIND,
        "version": REPORT_VERSION,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": (now + timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "retention_days": RETENTION_DAYS,
        "checksum": "sha256:" + hashlib.sha256(canonical).hexdigest(),
        "migrations": _migrations(conn),
        "summary": summary,
        "relations": result["per_field"],
        "shared_content_relations": [dict(e) for e in plan["shared"]],
        "not_covered": _not_covered(plan),
        "policy_check": policy_check(policy, plan) if policy is not None else None,
        "findings": findings,
    }


def write_report(report: dict[str, Any], out: Path) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(out), flags, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run(
    db: Path,
    out: Path,
    policy_path: Path | None,
    work_base: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Scan ``db`` and write the report to ``out``. Returns the report.

    Every check that can fail runs before anything is created: the database,
    the report location, the work location, and the policy.
    """
    db = db.resolve()
    if not db.is_file():
        raise ScanError(f"database not found: {db}")
    db_dir = db.parent

    out = Path(os.path.abspath(out))
    if not out.parent.is_dir():
        raise ScanError(f"report directory does not exist: {out.parent}")
    if _within(out.parent, db_dir):
        raise ScanError("refusing to write the report inside the database directory")
    if out.exists() or out.is_symlink():
        raise ScanError(f"refusing to overwrite an existing report: {out}")
    if not os.access(out.parent, os.W_OK | os.X_OK):
        raise ScanError(f"report directory is not writable: {out.parent}")

    base = Path(work_base) if work_base is not None else Path(tempfile.gettempdir())
    if not base.is_dir():
        raise ScanError(f"work directory does not exist: {base}")
    if _within(base, db_dir):
        raise ScanError("refusing to place the temporary copy inside the database directory")

    policy = load_policy(policy_path) if policy_path is not None else None

    work = Path(tempfile.mkdtemp(prefix="rounds-scan-", dir=str(base)))
    try:
        copy = backup_copy(db, work)
        conn = open_readonly(copy)
        try:
            collections = load_collections(conn)
            plan = plan_relations(collections, policy_owner_fields(policy))
            result = scan(conn, plan)
            report = build_report(
                conn, plan, result, policy, now or datetime.now(timezone.utc)
            )
        except sqlite3.Error as err:
            raise ScanError(f"scan failed: {err}") from err
        finally:
            conn.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)

    try:
        write_report(report, out)
    except OSError as err:
        raise ScanError(f"could not write the report: {err}") from err
    return report


def exit_code(report: dict[str, Any]) -> int:
    pc = report["policy_check"]
    if pc is not None and not pc["ok"]:
        return EXIT_POLICY_MISMATCH
    s = report["summary"]
    return EXIT_FINDINGS if (s["cross_owner"] or s["missing_target"]) else EXIT_CLEAN


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only cross-owner relation scan for a PocketBase pb_data copy."
    )
    parser.add_argument("--db", required=True, type=Path, help="path to pb_data/data.db (preferably a backup copy)")
    parser.add_argument("--out", required=True, type=Path, help="report path, outside the database directory")
    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="account-scope policy to cross-check (default: the repo's docs/security/account-scope.v1.json when present)",
    )
    parser.add_argument("--no-policy", action="store_true", help="skip the policy cross-check")
    parser.add_argument("--work-dir", type=Path, default=None, help="where to place the temporary copy (default: system temp)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    policy_path: Path | None = None
    if not args.no_policy:
        policy_path = args.policy if args.policy is not None else default_policy()

    try:
        report = run(args.db, args.out, policy_path, args.work_dir)
    except ScanError as err:
        print(f"scan_cross_owner: {err}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as err:  # noqa: BLE001 - every failure must map to the error code
        print(f"scan_cross_owner: unexpected error ({type(err).__name__}): {err}", file=sys.stderr)
        return EXIT_ERROR

    s = report["summary"]
    print(
        "scan_cross_owner: "
        f"{s['relations_checked']} relation fields, {s['rows_scanned']} rows, "
        f"{s['references_checked']} references checked; "
        f"{s['cross_owner']} cross-owner, {s['missing_target']} missing-target."
    )
    pc = report["policy_check"]
    if pc is not None and not pc["ok"]:
        print(
            "scan_cross_owner: the policy check failed (the policy and this database "
            "disagree about owned collections or relation fields, so the scan may be "
            "incomplete); see policy_check in the report.",
            file=sys.stderr,
        )
    print(f"scan_cross_owner: report written to {args.out} (operator-only; delete by {report['expires_at']}).")
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
