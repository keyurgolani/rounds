"""Tests for pocketbase/tools/scan_cross_owner.py.

Every database here is synthetic: a small file shaped like PocketBase
0.22's storage (``_collections`` plus one table per collection), written
directly with sqlite3 by the fixture. Cross-owner rows are planted with
direct SQLite writes in the fixture only.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parents[1] / "tools" / "scan_cross_owner.py"
_spec = importlib.util.spec_from_file_location("scan_cross_owner", _TOOL)
scan_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan_tool)

USERS_ID = "_pb_users_auth_"
UA = "uaaaaaaaaaaaaa1"
UB = "ubbbbbbbbbbbbb2"


def _rel(name: str, target: str, max_select: int | None = 1) -> dict:
    return {
        "name": name,
        "type": "relation",
        "options": {"collectionId": target, "cascadeDelete": False, "maxSelect": max_select},
    }


def _text(name: str) -> dict:
    return {"name": name, "type": "text", "options": {}}


def _json(name: str) -> dict:
    return {"name": name, "type": "json", "options": {"maxSize": 2097152}}


COLLECTIONS = [
    ("_pb_users_auth_", "users", "auth", [_text("name")]),
    ("col_campaigns00", "campaigns", "base", [_rel("user", USERS_ID), _text("name")]),
    (
        "col_todos000000",
        "todos",
        "base",
        [_rel("user", USERS_ID), _rel("campaign", "col_campaigns00"), _text("body"), _json("mentions")],
    ),
    (
        "col_bundles0000",
        "bundles",
        "base",
        [_rel("user", USERS_ID), _rel("items", "col_todos000000", None)],
    ),
    ("col_content0000", "content_rounds", "base", [_text("title")]),
    (
        "col_drafts00000",
        "drafts",
        "base",
        [_rel("user", USERS_ID), _rel("round", "col_content0000")],
    ),
]

COLUMNS = {
    "users": ["id", "name"],
    "campaigns": ["id", "user", "name"],
    "todos": ["id", "user", "campaign", "body", "mentions"],
    "bundles": ["id", "user", "items"],
    "content_rounds": ["id", "title"],
    "drafts": ["id", "user", "round"],
}

CLEAN_ROWS = {
    "users": [(UA, "VALUE-name-A"), (UB, "VALUE-name-B")],
    "campaigns": [("campaignaaaaaa1", UA, "VALUE-campaign-A"), ("campaignbbbbbb2", UB, "VALUE-campaign-B")],
    "todos": [
        ("todoaaaaaaaaaa1", UA, "campaignaaaaaa1", "VALUE-todo-A", "[]"),
        ("todobbbbbbbbbb2", UB, "campaignbbbbbb2", "VALUE-todo-B", "[]"),
    ],
    "bundles": [
        ("bundleaaaaaaaa1", UA, '["todoaaaaaaaaaa1"]'),
        ("bundlebbbbbbbb2", UB, '["todobbbbbbbbbb2"]'),
    ],
    "content_rounds": [("roundcontent001", "VALUE-round"), ("roundcontent002", "VALUE-round-2")],
    "drafts": [("draftaaaaaaaaa1", UA, "roundcontent001"), ("draftbbbbbbbbb2", UB, "roundcontent001")],
}


def make_db(path: Path, wal: bool = False) -> Path:
    conn = sqlite3.connect(str(path))
    if wal:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE _collections (id TEXT PRIMARY KEY, name TEXT, type TEXT, schema TEXT)")
    conn.execute("CREATE TABLE _migrations (file TEXT PRIMARY KEY, applied INTEGER)")
    conn.executemany(
        "INSERT INTO _migrations VALUES (?, ?)",
        [("1700000000_init_collections.js", 1), ("1700005100_drop_resume_bullets.js", 2)],
    )
    for cid, name, ctype, fields in COLLECTIONS:
        conn.execute(
            "INSERT INTO _collections VALUES (?, ?, ?, ?)", (cid, name, ctype, json.dumps(fields))
        )
        cols = ", ".join(f'"{c}" TEXT' for c in COLUMNS[name])
        conn.execute(f'CREATE TABLE "{name}" ({cols})')
    for name, rows in CLEAN_ROWS.items():
        marks = ", ".join("?" for _ in COLUMNS[name])
        conn.executemany(f'INSERT INTO "{name}" VALUES ({marks})', rows)
    conn.commit()
    conn.close()
    return path


def plant(path: Path, sql: str, params: tuple = ()) -> None:
    """Direct SQLite write used only to build the fixture."""
    conn = sqlite3.connect(str(path))
    conn.execute(sql, params)
    conn.commit()
    conn.close()


@pytest.fixture()
def layout(tmp_path: Path) -> dict:
    pb_data = tmp_path / "pb_data"
    reports = tmp_path / "reports"
    pb_data.mkdir()
    reports.mkdir()
    db = make_db(pb_data / "data.db")
    return {"db": db, "pb_data": pb_data, "reports": reports, "tmp": tmp_path}


def run_cli(layout: dict, name: str = "report.json", *extra: str) -> tuple[int, dict | None]:
    out = layout["reports"] / name
    code = scan_tool.main(["--db", str(layout["db"]), "--out", str(out), "--no-policy", *extra])
    report = json.loads(out.read_text()) if out.exists() else None
    return code, report


def test_clean_database_reports_no_findings(layout):
    code, report = run_cli(layout)
    assert code == 0
    assert report["findings"] == []
    assert report["summary"]["cross_owner"] == 0
    assert report["summary"]["missing_target"] == 0
    checked = {(r["collection"], r["field"]) for r in report["relations"]}
    assert checked == {("todos", "campaign"), ("bundles", "items")}
    assert report["summary"]["rows_scanned"] == 4


def test_reports_relation_whose_target_belongs_to_another_account(layout):
    plant(layout["db"], 'UPDATE todos SET campaign = ? WHERE id = ?', ("campaignaaaaaa1", "todobbbbbbbbbb2"))
    code, report = run_cli(layout)
    assert code == 1
    assert report["summary"]["cross_owner"] == 1
    [finding] = report["findings"]
    assert finding == {
        "kind": "cross_owner",
        "collection": "todos",
        "field": "campaign",
        "record_id": "todobbbbbbbbbb2",
        "target_collection": "campaigns",
        "target_id": "campaignaaaaaa1",
        "owner": "acct-01",
        "target_owner": "acct-02",
    }


def test_checks_every_id_in_a_multi_relation(layout):
    plant(
        layout["db"],
        "UPDATE bundles SET items = ? WHERE id = ?",
        ('["todobbbbbbbbbb2","todoaaaaaaaaaa1"]', "bundlebbbbbbbb2"),
    )
    code, report = run_cli(layout)
    assert code == 1
    [finding] = report["findings"]
    assert (finding["collection"], finding["field"], finding["record_id"], finding["target_id"]) == (
        "bundles",
        "items",
        "bundlebbbbbbbb2",
        "todoaaaaaaaaaa1",
    )
    items = next(r for r in report["relations"] if r["field"] == "items")
    assert items["references"] == 3


def test_relations_into_shared_content_are_not_checked(layout):
    plant(layout["db"], "UPDATE drafts SET round = ? WHERE id = ?", ("roundcontent002", "draftbbbbbbbbb2"))
    code, report = run_cli(layout)
    assert code == 0
    assert report["findings"] == []
    shared = {(r["collection"], r["field"]) for r in report["shared_content_relations"]}
    assert ("drafts", "round") in shared


def test_missing_target_is_reported_separately(layout):
    plant(
        layout["db"],
        "UPDATE bundles SET items = ? WHERE id = ?",
        ('["todoaaaaaaaaaa1","todogonegonego9"]', "bundleaaaaaaaa1"),
    )
    code, report = run_cli(layout)
    assert code == 1
    [finding] = report["findings"]
    assert finding["kind"] == "missing_target"
    assert finding["target_id"] == "todogonegonego9"
    assert finding["target_owner"] is None
    assert report["summary"] == {**report["summary"], "cross_owner": 0, "missing_target": 1}


def test_report_holds_no_field_values_or_account_ids(layout):
    plant(layout["db"], 'UPDATE todos SET campaign = ? WHERE id = ?', ("campaignaaaaaa1", "todobbbbbbbbbb2"))
    _, report = run_cli(layout)
    text = (layout["reports"] / "report.json").read_text()
    assert "VALUE-" not in text
    assert UA not in text and UB not in text
    for f in report["findings"]:
        assert re.fullmatch(r"acct-\d{2}", f["owner"])
        assert re.fullmatch(r"acct-\d{2}", f["target_owner"])


def test_checksum_is_stable_for_the_same_data(layout):
    plant(layout["db"], 'UPDATE todos SET campaign = ? WHERE id = ?', ("campaignaaaaaa1", "todobbbbbbbbbb2"))
    _, first = run_cli(layout, "first.json")
    _, second = run_cli(layout, "second.json")
    assert first["checksum"] == second["checksum"]
    assert first["checksum"].startswith("sha256:")


def test_report_expires_within_14_days(layout):
    now = datetime(2026, 10, 20, 8, 0, 0, tzinfo=timezone.utc)
    report = scan_tool.run(layout["db"], layout["reports"] / "r.json", None, now=now)
    generated = datetime.strptime(report["generated_at"], "%Y-%m-%dT%H:%M:%SZ")
    expires = datetime.strptime(report["expires_at"], "%Y-%m-%dT%H:%M:%SZ")
    assert expires - generated == timedelta(days=14)
    assert report["retention_days"] == 14


def test_report_file_is_private_to_the_operator(layout):
    run_cli(layout)
    mode = os.stat(layout["reports"] / "report.json").st_mode & 0o777
    assert mode == 0o600


def test_refuses_to_write_the_report_inside_the_database_directory(layout):
    out = layout["pb_data"] / "report.json"
    code = scan_tool.main(["--db", str(layout["db"]), "--out", str(out), "--no-policy"])
    assert code == 2
    assert not out.exists()


def test_refuses_to_overwrite_an_existing_report(layout):
    assert run_cli(layout)[0] == 0
    before = (layout["reports"] / "report.json").read_bytes()
    assert run_cli(layout)[0] == 2
    assert (layout["reports"] / "report.json").read_bytes() == before


def test_source_database_and_its_directory_are_left_unchanged(layout):
    before_hash = hashlib.sha256(layout["db"].read_bytes()).hexdigest()
    before_listing = sorted(os.listdir(layout["pb_data"]))
    run_cli(layout)
    assert hashlib.sha256(layout["db"].read_bytes()).hexdigest() == before_hash
    assert sorted(os.listdir(layout["pb_data"])) == before_listing


def test_temporary_copy_is_removed(layout):
    work = layout["tmp"] / "work"
    work.mkdir()
    run_cli(layout, "report.json", "--work-dir", str(work))
    assert os.listdir(work) == []


def test_live_wal_database_is_copied_consistently(tmp_path):
    pb_data = tmp_path / "pb_data"
    reports = tmp_path / "reports"
    pb_data.mkdir()
    reports.mkdir()
    db = make_db(pb_data / "data.db", wal=True)
    # Keep a writer open with its last commit still in the WAL, as a running
    # PocketBase would; the scan must see that commit through the backup API.
    writer = sqlite3.connect(str(db))
    writer.execute("PRAGMA wal_autocheckpoint=0")
    writer.execute('UPDATE todos SET campaign = ? WHERE id = ?', ("campaignaaaaaa1", "todobbbbbbbbbb2"))
    writer.commit()
    try:
        assert (pb_data / "data.db-wal").exists()
        code = scan_tool.main(["--db", str(db), "--out", str(reports / "r.json"), "--no-policy"])
        report = json.loads((reports / "r.json").read_text())
    finally:
        writer.close()
    assert code == 1
    assert report["summary"]["cross_owner"] == 1


def test_rejects_unknown_policy_version_before_scanning(layout):
    policy = layout["tmp"] / "policy.json"
    policy.write_text(json.dumps({"version": "v2", "collections": {}}))
    out = layout["reports"] / "report.json"
    code = scan_tool.main(["--db", str(layout["db"]), "--out", str(out), "--policy", str(policy)])
    assert code == 2
    assert not out.exists()


def test_policy_check_flags_relations_the_rule_table_does_not_list(layout):
    policy = layout["tmp"] / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "version": "v1",
                "collections": {
                    "todos": {"relation_exceptions": ["campaign"]},
                    "campaigns": {"relation_exceptions": ["owner_org"]},
                },
            }
        )
    )
    out = layout["reports"] / "report.json"
    assert scan_tool.main(["--db", str(layout["db"]), "--out", str(out), "--policy", str(policy)]) == 0
    check = json.loads(out.read_text())["policy_check"]
    assert check["unlisted_in_policy"] == [{"collection": "bundles", "field": "items"}]
    assert check["listed_but_absent"] == [{"collection": "campaigns", "field": "owner_org"}]


def test_lists_soft_references_present_in_the_schema_as_not_covered(layout):
    _, report = run_cli(layout)
    assert {"collection": "todos", "field": "mentions", "reason": "JSON mention tokens"} in report["not_covered"]
    assert all(r["collection"] != "applications" for r in report["not_covered"])


def test_not_a_pocketbase_database_fails_without_a_report(tmp_path):
    db = tmp_path / "pb_data" / "data.db"
    db.parent.mkdir()
    sqlite3.connect(str(db)).close()
    (tmp_path / "reports").mkdir()
    out = tmp_path / "reports" / "r.json"
    assert scan_tool.main(["--db", str(db), "--out", str(out), "--no-policy"]) == 2
    assert not out.exists()


def test_default_policy_is_the_repo_rule_table():
    path = scan_tool.default_policy()
    assert path is not None and path.name == "account-scope.v1.json"
    assert scan_tool.load_policy(path)["version"] == "v1"


def test_runs_from_a_copy_outside_the_repository(tmp_path, layout):
    # Operators may copy or mount the tool on its own (for example
    # /tools/scan_cross_owner.py in a container) with no rule table beside it.
    copy = tmp_path / "scan_cross_owner_copy.py"
    copy.write_text(_TOOL.read_text())
    spec = importlib.util.spec_from_file_location("scan_cross_owner_copy", copy)
    detached = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(detached)
    assert detached.default_policy() is None
    out = layout["reports"] / "detached.json"
    assert detached.main(["--db", str(layout["db"]), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["policy_check"] is None
