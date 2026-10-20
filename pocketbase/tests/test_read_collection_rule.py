"""Tests for harness/probes/read_collection_rule.py (ROUNDS-00B-L01/S3).

The migration check reads collection rules from a data.db to decide whether the
migration produced the right rules and whether a failed migration rolled back.
Only a missing _collections table may read as absent; any other read failure
must be an error, so a check can't pass on a read that never happened.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

PROBES = Path(__file__).resolve().parents[1].parent / "harness" / "probes"
sys.path.insert(0, str(PROBES))

import read_collection_rule as rcr  # noqa: E402


def _db_with_collections(path: Path, rows: list[tuple[str, str | None, str | None]]) -> str:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("CREATE TABLE _collections (name TEXT, createRule TEXT, updateRule TEXT)")
        conn.executemany("INSERT INTO _collections VALUES (?, ?, ?)", rows)
        conn.commit()
    finally:
        conn.close()
    return str(path)


def test_reads_a_rule_value(tmp_path):
    db = _db_with_collections(tmp_path / "data.db", [("campaigns", 'user = "x"', 'user = "y"')])
    assert rcr.read_rule(db, "campaigns", "create") == 'user = "x"'
    assert rcr.read_rule(db, "campaigns", "update") == 'user = "y"'


def test_null_rule_reads_as_null(tmp_path):
    db = _db_with_collections(tmp_path / "data.db", [("resume_share_views", None, None)])
    assert rcr.read_rule(db, "resume_share_views", "create") == "<<NULL>>"
    assert rcr.read_rule(db, "resume_share_views", "update") == "<<NULL>>"


def test_missing_collection_row_reads_as_absent(tmp_path):
    db = _db_with_collections(tmp_path / "data.db", [("campaigns", "", "")])
    assert rcr.read_rule(db, "not_there", "create") == "<<ABSENT>>"


def test_missing_collections_table_reads_as_absent(tmp_path):
    # A rolled-back migration leaves a data.db with no _collections table.
    db = str(tmp_path / "empty.db")
    sqlite3.connect(db).close()
    assert rcr.read_rule(db, "campaigns", "create") == "<<ABSENT>>"


def test_a_non_table_error_is_an_error_not_absent(tmp_path):
    # A file that is not a database must not read as absent, which is the value
    # the rollback check asserts; it has to fail the check instead.
    bad = tmp_path / "garbage.db"
    bad.write_bytes(b"this is not a sqlite database")
    out = rcr.read_rule(str(bad), "campaigns", "create")
    assert out.startswith("<<ERROR:") and "ABSENT" not in out


def test_a_missing_file_is_an_error_not_absent(tmp_path):
    out = rcr.read_rule(str(tmp_path / "nope.db"), "campaigns", "create")
    assert out.startswith("<<ERROR:")


def test_main_rejects_a_bad_which(tmp_path, capsys):
    db = _db_with_collections(tmp_path / "data.db", [("campaigns", "", "")])
    assert rcr.main([db, "campaigns", "sideways"]) == 2
