"""The read-only count of what the demo's reset clears (ROUNDS-00B-L07).

pocketbase/tools/demo_rows.py counts, from a stopped copy's data.db, the
rows the reset would delete for the demo accounts, under the names the
reset's demo_reset line counts. These checks run it on small databases
with PocketBase's table layout, and keep its collection list, and the
harness probe's, equal to the reset's own.
"""
from __future__ import annotations

import ast
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "pocketbase" / "tools" / "demo_rows.py"
HOOKS = ROOT / "pocketbase" / "pb_hooks"
DEMO = "demo00000000001"
STANDARD = "user00000000001"


def reset_lists() -> tuple[list[str], list[str]]:
    """demo.js RESET and RESET_EXTRA, read by loading the hook file."""
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    script = (
        "globalThis.__hooks = process.argv[1];"
        "const demo = require(require('path').join(process.argv[1], 'demo.js'));"
        "process.stdout.write(JSON.stringify([demo.RESET, demo.RESET_EXTRA]));"
    )
    res = subprocess.run([node, "-e", script, str(HOOKS)], capture_output=True, text=True, timeout=60, check=True)
    reset, extra = json.loads(res.stdout)
    return reset, extra


def literal(path: Path, name: str):
    """A module-level constant's literal value in a Python file."""
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in {path}")


def make_db(path: Path, *, execution: bool = True) -> Path:
    """A database with PocketBase's layout for what the tool reads: one
    demo and one standard account, each with rows in every reset
    collection, and the demo's code-run rows and OAuth2 links."""
    reset, _extra = reset_lists()
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE _collections (id TEXT PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO _collections VALUES ('_pb_users_auth_', 'users'), ('col000000000002', 'campaigns')")
    conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY, is_demo BOOLEAN DEFAULT FALSE)")
    conn.execute("INSERT INTO users VALUES (?, 1), (?, 0)", (DEMO, STANDARD))
    n = 0
    for name in reset:
        conn.execute(f'CREATE TABLE "{name}" (id TEXT PRIMARY KEY, "user" TEXT)')
        for owner, rows in ((DEMO, 2 if name == "resumes" else 1), (STANDARD, 3)):
            for _ in range(rows):
                n += 1
                conn.execute(f'INSERT INTO "{name}" VALUES (?, ?)', (f"row{n:012d}", owner))
    if execution:
        conn.execute("CREATE TABLE execution_jobs (id TEXT PRIMARY KEY, account TEXT, command_id TEXT, state TEXT)")
        conn.executemany("INSERT INTO execution_jobs VALUES (?, ?, ?, ?)", [
            ("job000000000001", DEMO, "c1", "completed"),
            ("job000000000002", DEMO, "c2", "started"),
            ("job000000000003", DEMO, "c5", "queued"),
            ("job000000000004", STANDARD, "c3", "completed"),
        ])
        conn.execute("CREATE TABLE execution_envelopes (id TEXT PRIMARY KEY, job TEXT, user TEXT)")
        conn.executemany("INSERT INTO execution_envelopes VALUES (?, ?, ?)", [
            ("env000000000001", "job000000000001", DEMO),
            ("env000000000002", "job000000000002", DEMO),
            ("env000000000004", "job000000000004", STANDARD),
        ])
        conn.execute("CREATE TABLE admission_commands (id TEXT PRIMARY KEY, account TEXT, command_id TEXT, job TEXT)")
        conn.executemany("INSERT INTO admission_commands VALUES (?, ?, ?, ?)", [
            ("cmd000000000001", DEMO, "c1", "job000000000001"),
            ("cmd000000000002", DEMO, "c2", "job000000000002"),
            ("cmd000000000003", DEMO, "c9", ""),
            ("cmd000000000004", STANDARD, "c3", "job000000000004"),
        ])
    conn.execute("CREATE TABLE _externalAuths (id TEXT PRIMARY KEY, collectionId TEXT, recordId TEXT)")
    conn.executemany("INSERT INTO _externalAuths VALUES (?, ?, ?)", [
        ("ext000000000001", "_pb_users_auth_", DEMO),
        ("ext000000000002", "_pb_users_auth_", DEMO),
        ("ext000000000003", "_pb_users_auth_", STANDARD),
    ])
    conn.commit()
    conn.close()
    return path


def run_tool(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, timeout=60)


def test_it_counts_what_the_reset_would_clear_for_the_demo_accounts_alone(tmp_path):
    db = make_db(tmp_path / "data.db")
    res = run_tool("--db", str(db))
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    reset, extra = reset_lists()
    expected = {name: 2 if name == "resumes" else 1 for name in reset}
    # The ended and the queued job, the ended one's envelope and the
    # command that names it, and both OAuth2 links; the started job and
    # what it holds, and a command no job names, stay.
    expected.update(execution_jobs=2, execution_envelopes=1, admission_commands=1, external_auths=2)
    assert out == {"version": "demo-rows/v1", "demo_accounts": 1, "deleted": expected}
    assert list(out["deleted"]) == reset + extra


def test_it_names_no_id_and_changes_nothing_beside_the_database(tmp_path):
    source = tmp_path / "pb_data"
    source.mkdir()
    db = make_db(source / "data.db")
    before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in source.iterdir()}
    res = run_tool("--db", str(db))
    assert res.returncode == 0, res.stderr
    assert DEMO not in res.stdout and STANDARD not in res.stdout
    after = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in source.iterdir()}
    assert after == before


def test_a_database_from_before_the_execution_store_counts_zero_there_and_says_so(tmp_path):
    db = make_db(tmp_path / "data.db", execution=False)
    res = run_tool("--db", str(db))
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    assert out["deleted"]["execution_jobs"] == out["deleted"]["admission_commands"] == 0
    assert out["missing"] == ["admission_commands", "execution_envelopes", "execution_jobs"]


def test_with_no_demo_account_every_count_is_zero(tmp_path):
    db = make_db(tmp_path / "data.db")
    conn = sqlite3.connect(db)
    conn.execute("UPDATE users SET is_demo = 0")
    conn.commit()
    conn.close()
    out = json.loads(run_tool("--db", str(db)).stdout)
    assert out["demo_accounts"] == 0 and set(out["deleted"].values()) == {0}


def test_a_database_it_cant_read_exits_2(tmp_path):
    res = run_tool("--db", str(tmp_path / "missing.db"))
    assert res.returncode == 2 and "demo_rows:" in res.stderr and res.stdout == ""


@pytest.mark.parametrize("path, names", [
    (TOOL, ("RESET", "RESET_EXTRA")),
    (ROOT / "harness" / "probes" / "demo_check.py", ("DEMO_RESET",)),
])
def test_its_collection_list_is_the_resets(path, names):
    reset, extra = reset_lists()
    assert list(literal(path, names[0])) == reset
    if len(names) > 1:
        assert list(literal(path, names[1])) == extra
