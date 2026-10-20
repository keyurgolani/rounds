#!/usr/bin/env python3
"""Read-only cross-owner relation scan for a PocketBase ``pb_data`` database.

Lists every row whose relation field points at a record owned by a
different account, so an operator can hand the list to the relation
quarantine (ROUNDS-00B-L02) before the account-scope rule migration ships.

What it does, in order:

1. Copies ``data.db`` with the SQLite online-backup API into a private
   temporary directory (the source is opened read-only and never written).
2. Opens the copy read-only and reads the collection schema from
   ``_collections``.
3. For every account-owned collection (one with a ``user`` relation to the
   ``users`` auth collection), checks each relation field whose target is
   also account-owned, in a fixed order: collection, field, record id.
4. Writes a JSON report outside the database directory, readable only by
   the operator, then deletes the temporary copy.

The report holds collection names, field names, record ids, target ids,
per-report owner pseudonyms (``acct-01`` ...), and counts. It never holds
field values or account ids, and the tool makes no network request (no
superuser or REST API). Reports are operator-only and must be deleted
within 14 days (``expires_at`` in the report).

Not covered: ids kept inside text or JSON fields (soft references, listed
in the report's ``not_covered``), and rows whose ``user`` was set to
another account without any foreign relation.

Usage::

    python3 pocketbase/tools/scan_cross_owner.py \\
        --db /path/to/pb_data-copy/data.db \\
        --out /path/outside/pb_data/cross-owner-report.json

Exit codes: 0 scan completed with no findings, 1 scan completed with
findings, 2 usage or runtime error (no report written).

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
OWNER_FIELD = "user"
USERS_COLLECTION = "users"
SUPPORTED_POLICY_VERSION = "v1"


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
# Copy and open
# ---------------------------------------------------------------------------


def _source_uri(db: Path) -> str:
    uri = db.resolve().as_uri() + "?mode=ro"
    # Without a write-ahead log there is nothing beyond the main file to
    # read, so open it immutable: no locks and no sidecar files are created
    # next to the source (for example on a read-only mount of a backup).
    if not Path(str(db) + "-wal").exists():
        uri += "&immutable=1"
    return uri


def backup_copy(db: Path, work_dir: Path) -> Path:
    """Copy ``db`` into ``work_dir`` with the SQLite online-backup API.

    The source connection is read-only. The copy is switched to a rollback
    journal so it can later be opened read-only without sidecar files.
    """
    if not db.is_file():
        raise ScanError(f"database not found: {db}")
    dst_path = work_dir / "scan-copy.db"
    src = sqlite3.connect(_source_uri(db), uri=True)
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


def _is_owned(collection: dict[str, Any], users_id: str) -> bool:
    for f in collection["fields"]:
        if (
            f.get("name") == OWNER_FIELD
            and f.get("type") == "relation"
            and (f.get("options") or {}).get("collectionId") == users_id
        ):
            return True
    return False


def plan_relations(collections: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Decide which relation fields the scan checks.

    Returns ``checked`` (account-owned source and target, sorted by
    collection then field), ``shared`` (relations into shared content,
    which have no owner and are not checked), and the owned collections.
    """
    users_id = _users_id(collections)
    owned = {cid for cid, c in collections.items() if _is_owned(c, users_id)}
    checked: list[dict[str, Any]] = []
    shared: list[dict[str, Any]] = []
    for cid in owned:
        source = collections[cid]
        for f in source["fields"]:
            if f.get("type") != "relation" or f.get("name") == OWNER_FIELD:
                continue
            target_id = (f.get("options") or {}).get("collectionId")
            target = collections.get(target_id)
            entry = {
                "collection": source["name"],
                "field": f["name"],
                "target_collection": target["name"] if target else None,
            }
            if target is None:
                raise ScanError(
                    f"{source['name']}.{f['name']} points at an unknown collection"
                )
            if target_id in owned or target_id == users_id:
                entry["target_is_users"] = target_id == users_id
                checked.append(entry)
            else:
                shared.append(entry)
    key = lambda e: (e["collection"], e["field"])  # noqa: E731
    return {
        "checked": sorted(checked, key=key),
        "shared": sorted(shared, key=key),
        "owned": sorted(collections[c]["name"] for c in owned),
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


def _owner_map(conn: sqlite3.Connection, target: str, target_is_users: bool) -> dict[str, str]:
    if target_is_users:
        rows = conn.execute(f"SELECT id FROM {_ident(target)}").fetchall()
        return {r[0]: r[0] for r in rows}
    rows = conn.execute(f"SELECT id, {_ident(OWNER_FIELD)} FROM {_ident(target)}").fetchall()
    return {r[0]: (r[1] or "") for r in rows}


def scan(conn: sqlite3.Connection, plan: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    per_field: list[dict[str, Any]] = []
    owner_cache: dict[str, dict[str, str]] = {}
    for rel in plan["checked"]:
        target = rel["target_collection"]
        if target not in owner_cache:
            owner_cache[target] = _owner_map(conn, target, rel["target_is_users"])
        owners = owner_cache[target]
        rows = conn.execute(
            f"SELECT id, {_ident(OWNER_FIELD)}, {_ident(rel['field'])} "
            f"FROM {_ident(rel['collection'])} ORDER BY id"
        ).fetchall()
        counts = {"rows": len(rows), "references": 0, "cross_owner": 0, "missing_target": 0}
        for record_id, owner, value in rows:
            for ref in _refs(value):
                counts["references"] += 1
                if ref not in owners:
                    counts["missing_target"] += 1
                    findings.append(
                        {
                            "kind": "missing_target",
                            "collection": rel["collection"],
                            "field": rel["field"],
                            "record_id": record_id,
                            "target_collection": target,
                            "target_id": ref,
                            "_owner": owner or "",
                            "_target_owner": None,
                        }
                    )
                elif owners[ref] != (owner or ""):
                    counts["cross_owner"] += 1
                    findings.append(
                        {
                            "kind": "cross_owner",
                            "collection": rel["collection"],
                            "field": rel["field"],
                            "record_id": record_id,
                            "target_collection": target,
                            "target_id": ref,
                            "_owner": owner or "",
                            "_target_owner": owners[ref],
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
    """Replace account ids with per-report labels assigned in scan order."""
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


def policy_check(policy: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Compare the relations this database has with the policy's rule table."""
    listed = {
        (name, field)
        for name, row in policy.get("collections", {}).items()
        for field in row.get("relation_exceptions", [])
    }
    checked = {(r["collection"], r["field"]) for r in plan["checked"]}
    relations_in_db = {
        key for key, ftype in plan["all_fields"].items() if ftype == "relation"
    }
    return {
        "policy_version": policy.get("version"),
        "unlisted_in_policy": [
            {"collection": c, "field": f} for c, f in sorted(checked - listed)
        ],
        "listed_but_absent": [
            {"collection": c, "field": f} for c, f in sorted(listed - relations_in_db)
        ],
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
        "shared_content_relations": [
            {k: v for k, v in e.items()} for e in plan["shared"]
        ],
        "not_covered": _not_covered(plan),
        "policy_check": policy_check(policy, plan) if policy is not None else None,
        "findings": findings,
    }


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def write_report(report: dict[str, Any], out: Path) -> None:
    fd = os.open(str(out), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
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
    """Scan ``db`` and write the report to ``out``. Returns the report."""
    db_dir = db.resolve().parent
    if _inside(out, db_dir):
        raise ScanError("refusing to write the report inside the database directory")
    if out.exists():
        raise ScanError(f"refusing to overwrite an existing report: {out}")
    if not out.parent.is_dir():
        raise ScanError(f"report directory does not exist: {out.parent}")
    policy = load_policy(policy_path) if policy_path is not None else None

    work = Path(tempfile.mkdtemp(prefix="rounds-scan-", dir=str(work_base) if work_base else None))
    try:
        if _inside(work, db_dir):
            raise ScanError("refusing to place the temporary copy inside the database directory")
        copy = backup_copy(db, work)
        conn = open_readonly(copy)
        try:
            collections = load_collections(conn)
            plan = plan_relations(collections)
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

    write_report(report, out)
    return report


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
        return 2

    s = report["summary"]
    print(
        "scan_cross_owner: "
        f"{s['relations_checked']} relation fields, {s['rows_scanned']} rows, "
        f"{s['references_checked']} references checked; "
        f"{s['cross_owner']} cross-owner, {s['missing_target']} missing-target."
    )
    pc = report["policy_check"]
    if pc is not None and (pc["unlisted_in_policy"] or pc["listed_but_absent"]):
        print(
            "scan_cross_owner: the policy rule table and this database disagree on "
            "relation fields; see policy_check in the report.",
            file=sys.stderr,
        )
    print(f"scan_cross_owner: report written to {args.out} (operator-only; delete by {report['expires_at']}).")
    return 1 if (s["cross_owner"] or s["missing_target"]) else 0


if __name__ == "__main__":
    sys.exit(main())
