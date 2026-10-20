"""Harness check for the cross-owner relation scan (ROUNDS-00B-L01 stage 2).

Runs ``pocketbase/tools/scan_cross_owner.py`` against the ``pb_data`` the
main phase produced (real PocketBase 0.22.22 storage after every migration,
two accounts with a full fixture graph), with PocketBase stopped and the
volume mounted read-only:

1. The clean data has no findings, and the policy's relation table matches
   the relation fields in the live schema.
2. On a fixture copy, one relation is pointed at another account's record
   with a direct SQLite write (fixture only, never through the API); the
   scan reports exactly that row.
3. Reports carry no field values or account ids, are private to the
   operator, have a stable checksum, and are refused inside ``pb_data``.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

PB_DATA = Path(os.environ.get("SCAN_PB_DATA", "/pb_data"))
TOOL = Path(os.environ.get("SCAN_TOOL", "/tools/scan_cross_owner.py"))
POLICY = Path(os.environ.get("POLICY_PATH", "/policy/account-scope.v1.json"))


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


def _load_tool():
    spec = importlib.util.spec_from_file_location("scan_cross_owner", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _scan(db: Path, out: Path, *extra: str) -> tuple[int, dict | None]:
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--db", str(db), "--out", str(out), *extra],
        capture_output=True,
        text=True,
    )
    report = json.loads(out.read_text()) if out.exists() else None
    return proc.returncode, report


def _sensitive_strings(db: Path) -> list[str]:
    """Identifiers and field values the report must never contain.

    The real guarantee is that the report carries no account identity: no
    account (``users``) id and no email. The report legitimately lists record
    ids and target ids (campaign ids, todo ids, ...), which are not account
    ids. We also include two distinctive seeded field values as a check that
    no row content leaks; generic values like "a resume" are deliberately
    excluded because they appear as substrings of the report's own schema
    descriptions ("...holding a resume_variants id") and would false-positive.
    """
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        account_ids = [r[0] for r in conn.execute("SELECT id FROM users")]
        emails = [r[0] for r in conn.execute("SELECT email FROM users") if r[0]]
    finally:
        conn.close()
    distinctive_values = ["Acme", "Engineer", "@harness.invalid"]
    return account_ids + emails + distinctive_values


def _plant_cross_owner(db: Path) -> dict:
    """Point one account's todo at another account's campaign (fixture only)."""
    conn = sqlite3.connect(str(db))
    try:
        todo_id, todo_owner = conn.execute(
            "SELECT id, user FROM todos ORDER BY id LIMIT 1"
        ).fetchone()
        campaign_id = conn.execute(
            "SELECT id FROM campaigns WHERE user != ? ORDER BY id LIMIT 1", (todo_owner,)
        ).fetchone()[0]
        conn.execute("UPDATE todos SET campaign = ? WHERE id = ?", (campaign_id, todo_id))
        conn.commit()
    finally:
        conn.close()
    return {"record_id": todo_id, "target_id": campaign_id}


def main() -> int:
    c = Checks()
    db = PB_DATA / "data.db"
    work = Path(tempfile.mkdtemp(prefix="scan-check-"))
    reports = work / "reports"
    reports.mkdir()

    # 1. Clean data straight from the read-only volume.
    code, clean = _scan(db, reports / "clean.json", "--policy", str(POLICY))
    c.check("scan.clean-data.no-findings", code == 0 and clean is not None and clean["findings"] == [],
            f"exit={code} findings={None if clean is None else len(clean['findings'])}")
    if clean is not None:
        s = clean["summary"]
        print(
            f"scan summary: owned_collections={s['owned_collections']} "
            f"relations_checked={s['relations_checked']} rows_scanned={s['rows_scanned']}"
        )
        c.check("scan.clean-data.relations-scanned", s["relations_checked"] > 0 and s["rows_scanned"] > 0,
                f"relations={s['relations_checked']} rows={s['rows_scanned']}")
        pc = clean["policy_check"] or {}
        c.check("scan.policy-table.matches-schema",
                pc.get("ok") is True
                and pc.get("unlisted_in_policy") == []
                and pc.get("owner_field_missing") == []
                and pc.get("listed_but_absent") == []
                and pc.get("collections_absent") == [],
                json.dumps(pc))

    # 2. A fixture copy with one planted cross-owner relation.
    tool = _load_tool()
    fixture_dir = work / "fixture" / "pb_data"
    fixture_dir.mkdir(parents=True)
    copied = tool.backup_copy(db, fixture_dir)
    fixture_db = copied.rename(fixture_dir / "data.db")
    planted = _plant_cross_owner(fixture_db)
    code, report = _scan(fixture_db, reports / "planted.json", "--policy", str(POLICY))
    findings = (report or {}).get("findings") or []
    ok = (
        code == 1
        and len(findings) == 1
        and findings[0]["kind"] == "cross_owner"
        and findings[0]["collection"] == "todos"
        and findings[0]["field"] == "campaign"
        and findings[0]["record_id"] == planted["record_id"]
        and findings[0]["target_id"] == planted["target_id"]
        and findings[0]["owner"] != findings[0]["target_owner"]
    )
    c.check("scan.cross-owner-relation.reported", ok, f"exit={code} findings={len(findings)}")

    # 3. Report hygiene.
    leaked = []
    for name in ("clean.json", "planted.json"):
        path = reports / name
        if not path.exists():
            continue
        text = path.read_text()
        for s in _sensitive_strings(fixture_db):
            if s and s in text:
                leaked.append(f"{name}:{s!r}")
    c.check("scan.report.no-values-or-account-ids", not leaked, f"leaks: {sorted(set(leaked))}")

    modes = {p.name: os.stat(p).st_mode & 0o777 for p in reports.iterdir()}
    c.check("scan.report.private", all(m == 0o600 for m in modes.values()), json.dumps(modes))

    code2, again = _scan(fixture_db, reports / "planted-again.json", "--policy", str(POLICY))
    c.check("scan.report.checksum-stable",
            report is not None and again is not None and report["checksum"] == again["checksum"],
            "checksums differ")

    inside = fixture_dir / "report.json"
    code3, _ = _scan(fixture_db, inside, "--policy", str(POLICY))
    c.check("scan.report.refused-inside-pb-data", code3 == 2 and not inside.exists(), f"exit={code3}")

    print(f"scan check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
