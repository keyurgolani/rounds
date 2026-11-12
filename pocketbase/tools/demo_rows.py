#!/usr/bin/env python3
"""Count what the demo's reset would clear, read-only (ROUNDS-00B-L07).

    python3 pocketbase/tools/demo_rows.py --db /path/to/copy/pb_data/data.db

It reads a stopped copy of a PocketBase database the way
scan_cross_owner.py does: it copies ``data.db`` and its write-ahead log
into a private temporary directory with plain file reads, opens that copy
read-only, and deletes it when it's done. It never opens the source with
SQLite, changes nothing beside it, starts no PocketBase, and makes no
network request.

It prints one JSON object: how many demo accounts (``users`` with
``is_demo`` set) the database holds, and, per collection the reset clears,
how many of their rows it would delete, under the names the reset's
``demo_reset`` log line counts in ``deleted``. The first such line after a
deploy can be compared with it; several demo accounts log one line each,
which add up to these totals. It holds no id, email, or value.

Exit status: 0 with the counts, 2 when the database can't be read.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from scan_cross_owner import ScanError, _ident, backup_copy, open_readonly

VERSION = "demo-rows/v1"
# pb_hooks/demo.js RESET, in its order: every collection a demo account
# writes itself, by its `user` field. test_demo_rows.py keeps them equal.
RESET = (
    "exp_anecdote_bullets", "exp_project_bullets", "exp_project_anecdotes", "exp_job_bullets", "exp_job_anecdotes",
    "exp_job_projects",
    "experience_bullets", "experience_anecdotes", "experience_projects", "experience_jobs",
    "resume_versions", "resume_variants", "resumes",
    "ai_coding_attempts", "take_home_attempts", "ai_coding_drafts", "take_home_drafts", "question_timers",
    "todos", "code_drafts", "offers", "interview_rounds", "user_progress", "user_preferences", "applications",
    "campaigns",
)
# pb_hooks/demo.js RESET_EXTRA: the code-run jobs no worker holds, their
# envelopes, the admission commands that name them, and the OAuth2 links.
RESET_EXTRA = ("execution_jobs", "execution_envelopes", "admission_commands", "external_auths")

# The jobs execution.js purgeAccount takes, none a worker may hold, as a
# filter on the jobs table under the alias `j`.
_PURGEABLE = "j.account IN ({ids}) AND j.state NOT IN ('leased', 'started')"


def _tables(conn) -> set[str]:
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _demo_ids(conn) -> list[str]:
    rows = conn.execute("SELECT id FROM users WHERE is_demo = 1 OR is_demo = 'true'")
    return [row[0] for row in rows]


def count(conn) -> dict:
    """The counts, from an open read-only connection."""
    tables = _tables(conn)
    ids = _demo_ids(conn) if "users" in tables else []
    marks = ", ".join("?" for _ in ids) or "NULL"
    deleted: dict[str, int] = {}
    missing: list[str] = []

    def one(sql: str, table: str, *needs: str) -> int:
        if any(need not in tables for need in (table, *needs)):
            missing.append(table)
            return 0
        return int(conn.execute(sql, ids).fetchone()[0]) if ids else 0

    for name in RESET:
        deleted[name] = one(f'SELECT COUNT(*) FROM {_ident(name)} WHERE "user" IN ({marks})', name)
    purgeable = _PURGEABLE.format(ids=marks)
    deleted["execution_jobs"] = one(f"SELECT COUNT(*) FROM execution_jobs j WHERE {purgeable}", "execution_jobs")
    deleted["execution_envelopes"] = one(
        f"SELECT COUNT(*) FROM execution_envelopes WHERE job IN (SELECT j.id FROM execution_jobs j WHERE {purgeable})",
        "execution_envelopes", "execution_jobs")
    # A command goes with its job when it names that job, as
    # execution.js deleteCommandOf finds it.
    deleted["admission_commands"] = one(
        "SELECT COUNT(*) FROM admission_commands c JOIN execution_jobs j"
        " ON c.job = j.id AND c.account = j.account AND c.command_id = j.command_id"
        f" WHERE {purgeable}",
        "admission_commands", "execution_jobs")
    deleted["external_auths"] = one(
        "SELECT COUNT(*) FROM _externalAuths WHERE collectionId = (SELECT id FROM _collections WHERE name = 'users')"
        f" AND recordId IN ({marks})",
        "_externalAuths", "_collections")
    out = {"version": VERSION, "demo_accounts": len(ids), "deleted": deleted}
    if missing:
        out["missing"] = sorted(set(missing))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", required=True, type=Path, help="path to a stopped copy's pb_data/data.db")
    args = parser.parse_args(argv)
    try:
        with tempfile.TemporaryDirectory(prefix="demo-rows-") as work:
            copy = backup_copy(args.db, Path(work))
            conn = open_readonly(copy)
            try:
                out = count(conn)
            finally:
                conn.close()
    except (ScanError, OSError) as err:
        print(f"demo_rows: {err}", file=sys.stderr)
        return 2
    except Exception as err:  # noqa: BLE001 - a database this can't read
        print(f"demo_rows: could not read the database: {type(err).__name__}", file=sys.stderr)
        return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
