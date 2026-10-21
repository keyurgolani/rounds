"""Harness check for the relation quarantine and triggers (ROUNDS-00B-L02).

Runs the pinned PocketBase binary offline against throwaway pb_data, with
``1700007000_relation_endpoint_authz.js``, the hooks, and the replay lever
from this checkout.

A. Legacy fixture (``quarantine.*``). Applies every migration that sorts
   before 1700007000 (PocketBase's own size-default migration among them, so
   the shape is an upgraded deployment's), plants cross-owner and
   missing-target rows with direct SQL (no trigger exists yet), then:

   1. The dry run writes its report and changes nothing. PocketBase 0.22 exits
      0 even after a failed migration, so the report and the log line are the
      signal, not the exit code. The dry run takes the apply's path, so it
      reports the outcomes the apply then has, with the same checksum.
   2. The apply moves each row whose required or cascading relation crosses
      accounts, with its cascade dependents, even when the moved rows point at
      each other (two offers chained through previous_offer). It clears every
      offending optional field of a row in one update and journals each clear,
      clears and journals a reference to a moved row, and moves a row whose
      clear would collide with a unique index. It leaves same-owner rows
      alone, keeps total row counts, journals every entry with the migration,
      the original row (every raw column value, exactly), pseudonyms, and
      status, and logs counts and the checksum only.
   3. Running the migration again adds nothing.

B. Replay (``quarantine.replay.*``). On copies of the applied fixture: the
   admin API marks entries ``dropped`` and ``replayed`` without touching
   their payload; the replay lever writes same-owner entries back exactly,
   created and updated included, parents before dependents, and refuses an
   entry whose target still belongs to another account, changing nothing.

C. Schema drift (``quarantine.guard.*``, ``quarantine.failure.*``). A view,
   an added relation, and a toggled cascade change nothing when there is
   nothing for them to affect; a toggled cascade on a field with something
   to quarantine, or an added relation pointing at a row about to move,
   stops the migration and is reported; and a failure as early as the scan
   still writes the dry run's report and the apply's failure log line.

D. Deletes after the migration, through the API on a served copy
   (``relation-delete.*``). An account deleting a provider set as both its
   text and vision provider, an account deleting an application with two
   chained offers, and a superuser deleting an account that holds both shapes
   all succeed, and another account's rows stay untouched.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import factory
from pbclient import PBClient

PB_BIN = Path(os.environ.get("PB_BIN", "/pbbin/pocketbase"))
MIGRATIONS = Path(os.environ.get("PB_MIGRATIONS_DIR", "/pb_migrations"))
HOOKS = Path(os.environ.get("PB_HOOKS_DIR", "/pb_hooks"))
LEVERS = Path(os.environ.get("PB_LEVERS_DIR", "/pb_levers"))
MIGRATION = "1700007000_relation_endpoint_authz.js"
MIGRATION_ID = MIGRATION[: -len(".js")]
PSEUDONYM = re.compile(r"^acct-\d{2}$")
STAMP = "2024-01-01 00:00:00.000Z"
BIG_INT = 9007199254740993  # 2^53 + 1: a JS number can't hold it
REAL_17 = 0.30000000000000004  # needs all 17 significant digits
JSON_KEYS = '{"z":1,"a":9007199254740993,"2":"two","1":"one"}'  # key order a JS object reorders


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


def rid(tag: str) -> str:
    """A fixed 15-character PocketBase id for a fixture row."""
    out = ("lq" + tag + "0" * 15)[:15]
    assert re.fullmatch(r"[a-z0-9]{15}", out), tag
    return out


# -- the legacy fixture -------------------------------------------------------

UA, UB = rid("ua"), rid("ub")
CA, CB = rid("ca"), rid("cb")
XA, XB, XM = rid("xa"), rid("xb"), rid("xm")
O1, O2, O3, O4 = rid("o1"), rid("o2"), rid("o3"), rid("o4")
RA, RB = rid("ra"), rid("rb")
VB = rid("vb")
RV1, RV2, RV3 = rid("rv1"), rid("rv2"), rid("rv3")
L1, L2, L3 = rid("l1"), rid("l2"), rid("l3")
W1, W2, W3 = rid("w1"), rid("w2"), rid("w3")
PA1, PA2 = rid("pa1"), rid("pa2")
SB = rid("sb")
D1, D2 = rid("d1"), rid("d2")
IR = rid("ir")
T1, T2 = rid("t1"), rid("t2")
MISSING_CAMPAIGN = rid("missing")

# (collection, id) -> (kind, field, unique_fallback) for every row the apply moves.
EXPECT_MOVED = {
    ("offers", O1): ("cross_owner", "application", False),
    ("offers", O2): ("cross_owner", "application", False),
    ("resume_variants", VB): ("cross_owner", "resume", False),
    ("resume_versions", RV1): ("cross_owner", "resume", False),
    ("resume_versions", RV2): ("dependent", "variant", False),
    ("resume_share_links", L1): ("cross_owner", "resume", False),
    ("resume_share_links", L2): ("dependent", "variant", False),
    ("resume_share_views", W1): ("dependent", "link", False),
    ("resume_share_views", W2): ("dependent", "link", False),
    ("ai_coding_drafts", D1): ("cross_owner", "campaign", True),
    ("todos", T1): ("missing_target", "campaign", False),
}
# (collection, id, field) -> kind for every reference the apply clears.
EXPECT_CLEARED = {
    ("offers", O3, "previous_offer"): "reference",
    ("ai_settings", SB, "text_provider"): "cross_owner",
    ("ai_settings", SB, "vision_provider"): "cross_owner",
    ("applications", XM, "campaign"): "missing_target",
    ("interview_rounds", IR, "campaign"): "cross_owner",
}
# Rows the apply must leave exactly as they were.
UNTOUCHED = [
    ("campaigns", CA), ("campaigns", CB), ("applications", XA), ("applications", XB),
    ("offers", O4), ("resumes", RA), ("resumes", RB), ("resume_versions", RV3),
    ("resume_share_links", L3), ("resume_share_views", W3), ("ai_providers", PA1),
    ("ai_providers", PA2), ("ai_coding_drafts", D2), ("todos", T2),
]


def _insert(conn: sqlite3.Connection, table: str, **cols: object) -> None:
    cols.setdefault("created", STAMP)
    cols.setdefault("updated", STAMP)
    names = ", ".join(f'"{k}"' for k in cols)
    marks = ", ".join("?" for _ in cols)
    conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({marks})', list(cols.values()))


def _users(conn: sqlite3.Connection, *pairs: tuple[str, str]) -> None:
    for uid, tag in pairs:
        _insert(conn, "users", id=uid, username=f"lq{tag}user", email=f"lq-{tag}@harness.invalid",
                tokenKey=secrets.token_hex(16), passwordHash="x")


def seed_legacy(db: Path) -> list[str]:
    """Plant the legacy rows; returns every fixture id (for the log checks)."""
    conn = sqlite3.connect(str(db))
    try:
        round_id = conn.execute("SELECT id FROM ai_coding_rounds ORDER BY id LIMIT 1").fetchone()[0]
        _users(conn, (UA, "a"), (UB, "b"))
        _insert(conn, "campaigns", id=CA, user=UA, name="a", slug="lq-a")
        _insert(conn, "campaigns", id=CB, user=UB, name="b", slug="lq-b")
        _insert(conn, "applications", id=XA, user=UA, company="Acme", role="Engineer", campaign=CA)
        _insert(conn, "applications", id=XB, user=UB, company="Acme", role="Engineer", campaign=CB)
        _insert(conn, "applications", id=XM, user=UB, company="Acme", role="Engineer", campaign=MISSING_CAMPAIGN)
        # Two offers chained to each other, both on another account's application.
        # O1 also carries values a lossy copy would change, and its own dates.
        _insert(conn, "offers", id=O1, user=UB, application=XA, status="pending", base_salary=BIG_INT,
                annual_bonus_target_pct=REAL_17, created="2023-05-06 07:08:09.123Z", updated="2023-06-07 08:09:10.456Z")
        _insert(conn, "offers", id=O2, user=UB, application=XA, status="pending", previous_offer=O1,
                created="2023-05-07 07:08:09.123Z")
        # A same-owner offer that points at a moved offer, and one left alone.
        _insert(conn, "offers", id=O3, user=UB, application=XB, status="pending", previous_offer=O1)
        _insert(conn, "offers", id=O4, user=UB, application=XB, status="pending")
        _insert(conn, "resumes", id=RA, user=UA, name="a", slug="lq-ra")
        _insert(conn, "resumes", id=RB, user=UB, name="b", slug="lq-rb")
        # A variant on another account's resume brings its versions, links, and views.
        _insert(conn, "resume_variants", id=VB, user=UB, resume=RA, name="v")
        _insert(conn, "resume_versions", id=RV1, user=UB, resume=RA, data=JSON_KEYS, created="2022-01-02 03:04:05.678Z")
        _insert(conn, "resume_versions", id=RV2, user=UB, resume=RB, variant=VB)
        _insert(conn, "resume_versions", id=RV3, user=UB, resume=RB)
        _insert(conn, "resume_share_links", id=L1, user=UB, resume=RA, token="lq-token-1")
        _insert(conn, "resume_share_links", id=L2, user=UB, variant=VB, token="lq-token-2")
        _insert(conn, "resume_share_links", id=L3, user=UB, resume=RB, token="lq-token-3")
        _insert(conn, "resume_share_views", id=W1, user=UB, link=L1)
        _insert(conn, "resume_share_views", id=W2, user=UB, link=L2)
        _insert(conn, "resume_share_views", id=W3, user=UB, link=L3)
        # Both providers of one settings row belong to another account.
        _insert(conn, "ai_providers", id=PA1, user=UA, kind="openai", label="a1")
        _insert(conn, "ai_providers", id=PA2, user=UA, kind="openai", label="a2")
        _insert(conn, "ai_settings", id=SB, user=UB, text_provider=PA1, vision_provider=PA2)
        # Clearing D1's campaign would collide with D2 on (user, campaign, round, file_path).
        _insert(conn, "ai_coding_drafts", id=D1, user=UB, round=round_id, campaign=CA, file_path="a.py", contents="x")
        _insert(conn, "ai_coding_drafts", id=D2, user=UB, round=round_id, campaign="", file_path="a.py", contents="x")
        _insert(conn, "interview_rounds", id=IR, user=UB, application=XB, campaign=CA, round_type="technical")
        _insert(conn, "todos", id=T1, user=UB, campaign=MISSING_CAMPAIGN, body="t1")
        _insert(conn, "todos", id=T2, user=UB, campaign=CB, body="t2")
        conn.commit()
    finally:
        conn.close()
    return [v for k, v in globals().items() if re.fullmatch(r"lq[a-z0-9]{13}", str(v))]


# -- PocketBase -----------------------------------------------------------------

def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {"PATH": "/usr/bin:/bin"}
    env.update(extra or {})
    return env


def _migrate(data: Path, migrations: Path, extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PB_BIN), "migrate", "up", f"--dir={data}", f"--migrationsDir={migrations}"],
        capture_output=True,
        text=True,
        timeout=300,
        env=_env(extra),
    )


def _ro(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def snapshot(db: Path, skip: tuple[str, ...] = ()) -> dict:
    """Every table's row count and content hash, the triggers, and the applied migrations."""
    conn = _ro(db)
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        out: dict[str, object] = {}
        for t in tables:
            if t in skip:
                continue
            rows = conn.execute(f'SELECT * FROM "{t}" ORDER BY rowid').fetchall()
            digest = hashlib.sha256(json.dumps([list(r) for r in rows], default=str).encode()).hexdigest()
            out[t] = (len(rows), digest)
        out["__triggers__"] = sorted(r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'"))
    finally:
        conn.close()
    return out


def _diff(a: dict, b: dict) -> str:
    names = sorted(n for n in set(a) | set(b) if a.get(n) != b.get(n))
    return ", ".join(names) or "none"


def _row(db: Path, table: str, rec_id: str) -> dict | None:
    conn = _ro(db)
    try:
        row = conn.execute(f'SELECT * FROM "{table}" WHERE id = ?', (rec_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def _raw_row(db: Path, table: str, rec_id: str) -> list[tuple[str, str | None]] | None:
    """Each column's raw value as text, the way the migration copies it."""
    conn = _ro(db)
    try:
        cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]
        expr = ", ".join(
            f"CASE typeof(\"{n}\") WHEN 'null' THEN NULL WHEN 'real' THEN printf('%!.17g', \"{n}\") "
            f"ELSE CAST(\"{n}\" AS TEXT) END" for n in cols
        )
        row = conn.execute(f'SELECT {expr} FROM "{table}" WHERE id = ?', (rec_id,)).fetchone()
    finally:
        conn.close()
    return list(zip(cols, row)) if row else None


def _rows(db: Path, table: str) -> list[dict]:
    conn = _ro(db)
    try:
        return [dict(r) for r in conn.execute(f'SELECT * FROM "{table}" ORDER BY id')]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def _count(db: Path, table: str) -> int:
    conn = _ro(db)
    try:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    except sqlite3.OperationalError:
        return -1
    finally:
        conn.close()


def _applied(db: Path, name: str = MIGRATION) -> bool:
    """Whether `name` is recorded as applied. PocketBase 0.22 exits 0 after a
    failed migration, so this, not the exit code, says whether a run applied."""
    if not db.exists():
        return False
    conn = _ro(db)
    try:
        return conn.execute("SELECT COUNT(*) FROM _migrations WHERE file = ?", (name,)).fetchone()[0] == 1
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()


def _events(out: str, event: str) -> list[dict]:
    """The obs/v1 JSON lines for `event` (PocketBase may prefix a console line)."""
    found = []
    for line in out.splitlines():
        start, end = line.find("{"), line.rfind("}")
        if event not in line or start < 0 or end < start:
            continue
        try:
            obj = json.loads(line[start : end + 1])
        except ValueError:
            continue
        if obj.get("event") == event:
            found.append(obj)
    return found


def _outcome_keys(outcomes: list[dict]) -> tuple[dict, dict]:
    moved, cleared = {}, {}
    for o in outcomes:
        if o.get("action") == "moved":
            moved[(o["collection"], o["record_id"])] = (o["kind"], o["field"], bool(o.get("unique_fallback")))
        elif o.get("action") == "cleared":
            cleared[(o["collection"], o["record_id"], o["field"])] = o["kind"]
    return moved, cleared


def _journal_entry(db: Path, collection: str, rec_id: str, field: str) -> dict | None:
    for e in _rows(db, "relation_quarantine"):
        if (e["source_collection"], e["source_id"], e["field"]) == (collection, rec_id, field):
            return e
    return None


def _dry_run(data: Path, migrations: Path, work: Path, name: str) -> tuple[subprocess.CompletedProcess, dict, Path]:
    reports = work / "reports"
    reports.mkdir(exist_ok=True)
    report_path = reports / f"{name}.json"
    run = _migrate(data, migrations, {"ROUNDS_RELATION_QUARANTINE": "dry-run",
                                      "ROUNDS_RELATION_QUARANTINE_REPORT": str(report_path)})
    report = {}
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text())
        except ValueError:
            report = {}
    return run, report, report_path


# -- A. legacy fixture: dry run, apply, reapply ---------------------------------

def check_quarantine(c: Checks, work: Path, base: Path, full: Path, admin_env: dict[str, str]) -> tuple[Path, Path] | None:
    """Returns (the applied copy, the base fixture db) for the replay checks."""
    base_data = work / "legacy_base"
    up = _migrate(base_data, base, admin_env)
    last_base = sorted(p.name for p in base.glob("*.js"))[-1]
    if not c.check("quarantine.legacy.base-applies",
                   _applied(base_data / "data.db", last_base) and not _applied(base_data / "data.db"),
                   (up.stdout + up.stderr)[-400:]):
        return None
    fixture_ids = seed_legacy(base_data / "data.db")
    base_db = base_data / "data.db"
    before = snapshot(base_db)

    # 1. Dry run on a copy.
    dry = work / "legacy_dry"
    shutil.copytree(base_data, dry)
    run, report, report_path = _dry_run(dry, full, work, "dry")
    dry_log = run.stdout + run.stderr
    c.check("quarantine.dry-run.exits-zero", run.returncode == 0, f"exit={run.returncode}")
    c.check("quarantine.dry-run.writes-report", bool(report) and report.get("status") == "ok" and report.get("dry_run") is True,
            f"exists={report_path.exists()} status={report.get('status')!r} error={report.get('error')!r}")
    c.check("quarantine.dry-run.report-private", report_path.exists() and (report_path.stat().st_mode & 0o777) == 0o600,
            oct(report_path.stat().st_mode & 0o777) if report_path.exists() else "missing")
    c.check("quarantine.dry-run.changes-nothing", snapshot(dry / "data.db") == before,
            _diff(snapshot(dry / "data.db"), before))
    moved, cleared = _outcome_keys(report.get("outcomes") or [])
    c.check("quarantine.dry-run.predicts-the-moves", moved == EXPECT_MOVED,
            f"extra={sorted(set(moved) - set(EXPECT_MOVED))} missing={sorted(set(EXPECT_MOVED) - set(moved))} "
            f"wrong={sorted(k for k in moved if k in EXPECT_MOVED and moved[k] != EXPECT_MOVED[k])}")
    c.check("quarantine.dry-run.predicts-the-clears", cleared == EXPECT_CLEARED,
            f"extra={sorted(set(cleared) - set(EXPECT_CLEARED))} missing={sorted(set(EXPECT_CLEARED) - set(cleared))}")
    dry_events = _events(dry_log, "relation_quarantine_dry_run")
    c.check("quarantine.dry-run.logs-the-outcome",
            len(dry_events) == 1 and dry_events[0].get("status") == "ok" and dry_events[0].get("checksum") == report.get("checksum"),
            repr(dry_events)[:300])
    leaked = sorted(i for i in fixture_ids if i in dry_log)
    c.check("quarantine.dry-run.logs-no-ids", not leaked, f"{len(leaked)} fixture ids in the log")

    # 2. Apply on another copy of the same base.
    app = work / "legacy_apply"
    shutil.copytree(base_data, app)
    run = _migrate(app, full)
    apply_log = run.stdout + run.stderr
    adb = app / "data.db"
    if not c.check("quarantine.apply.applies", run.returncode == 0 and _applied(adb), apply_log[-600:]):
        return None
    gone = [k for k in EXPECT_MOVED if _row(adb, *k) is not None]
    c.check("quarantine.apply.moves-rows-and-dependents", not gone, f"still live: {gone}")
    c.check("quarantine.apply.moves-chained-offers", _row(adb, "offers", O1) is None and _row(adb, "offers", O2) is None,
            "an offer chained through previous_offer was not moved")
    c.check("quarantine.apply.moves-cascading-optional-links",
            _row(adb, "resume_share_links", L1) is None and _row(adb, "resume_versions", RV1) is None,
            "a share link or version on another account's resume was cleared instead of moved")
    sb = _row(adb, "ai_settings", SB) or {}
    c.check("quarantine.apply.clears-both-providers-in-place",
            bool(sb) and sb.get("text_provider") == "" and sb.get("vision_provider") == "",
            f"row={'present' if sb else 'moved'} text={sb.get('text_provider')!r} vision={sb.get('vision_provider')!r}")
    o3 = _row(adb, "offers", O3) or {}
    c.check("quarantine.apply.clears-reference-to-moved-row", bool(o3) and o3.get("previous_offer") == "",
            f"previous_offer={o3.get('previous_offer')!r}")
    xm = _row(adb, "applications", XM) or {}
    ir = _row(adb, "interview_rounds", IR) or {}
    c.check("quarantine.apply.clears-optional-references",
            xm.get("campaign") == "" and ir.get("campaign") == "" and ir.get("application") == XB,
            f"xm={xm.get('campaign')!r} ir={ir.get('campaign')!r}")
    c.check("quarantine.apply.moves-row-on-unique-collision",
            _row(adb, "ai_coding_drafts", D1) is None and _row(adb, "ai_coding_drafts", D2) is not None,
            "the colliding draft was not moved, or the other draft was touched")
    changed = [k for k in UNTOUCHED if _row(adb, *k) != _row(base_db, *k)]
    c.check("quarantine.apply.leaves-same-owner-rows", not changed, f"changed: {changed}")

    journal = _rows(adb, "relation_quarantine")
    reports_rows = _rows(adb, "relation_quarantine_reports")
    report_row = reports_rows[0] if len(reports_rows) == 1 else {}
    checksum = report_row.get("checksum")
    c.check("quarantine.apply.one-report-with-the-dry-run-checksum",
            len(reports_rows) == 1 and checksum and checksum == report.get("checksum"),
            f"reports={len(reports_rows)} apply={checksum!r} dry={report.get('checksum')!r}")
    j_moved = {(e["source_collection"], e["source_id"]): (e["kind"], e["field"], bool(e["unique_fallback"]))
               for e in journal if e["action"] == "moved"}
    j_cleared = {(e["source_collection"], e["source_id"], e["field"]): e["kind"] for e in journal if e["action"] == "cleared"}
    c.check("quarantine.apply.journals-every-move", j_moved == EXPECT_MOVED,
            f"extra={sorted(set(j_moved) - set(EXPECT_MOVED))} missing={sorted(set(EXPECT_MOVED) - set(j_moved))}")
    c.check("quarantine.apply.journals-every-clear", j_cleared == EXPECT_CLEARED,
            f"extra={sorted(set(j_cleared) - set(EXPECT_CLEARED))} missing={sorted(set(EXPECT_CLEARED) - set(j_cleared))}")
    bad = []
    for e in journal:
        payload = json.loads(e["payload"]) if e.get("payload") else {}
        if (e.get("migration") != MIGRATION_ID or e.get("status") != "quarantined"
                or e.get("report_checksum") != checksum or payload.get("id") != e["source_id"]
                or not PSEUDONYM.match(e.get("owner") or "")
                or (e.get("target_owner") and not PSEUDONYM.match(e["target_owner"]))):
            bad.append((e["source_collection"], e["source_id"], e["field"]))
    c.check("quarantine.apply.journal-entry-schema", journal and not bad, f"bad entries: {bad[:5]}")
    # The payload is the base row's every raw column value, in table order.
    inexact = []
    for e in journal:
        want = _raw_row(base_db, e["source_collection"], e["source_id"])
        got = json.loads(e["payload"], object_pairs_hook=list) if e.get("payload") else None
        if want is None or got is None or [tuple(p) for p in got] != want:
            inexact.append((e["source_collection"], e["source_id"], e["field"]))
    c.check("quarantine.apply.journal-keeps-the-raw-row", journal and not inexact, f"inexact: {inexact[:5]}")
    o1p = dict(json.loads((_journal_entry(adb, "offers", O1, "application") or {}).get("payload") or "{}"))
    rv1p = dict(json.loads((_journal_entry(adb, "resume_versions", RV1, "resume") or {}).get("payload") or "{}"))
    c.check("quarantine.apply.journal-is-lossless",
            o1p.get("base_salary") == str(BIG_INT) and o1p.get("annual_bonus_target_pct") == "0.30000000000000004"
            and o1p.get("created") == "2023-05-06 07:08:09.123Z" and rv1p.get("data") == JSON_KEYS,
            f"o1={o1p.get('base_salary')!r}/{o1p.get('annual_bonus_target_pct')!r} rv1={rv1p.get('data')!r}")
    lost = []
    for table in sorted({k[0] for k in EXPECT_MOVED}):
        moved_here = sum(1 for k in EXPECT_MOVED if k[0] == table)
        if _count(adb, table) + moved_here != _count(base_db, table):
            lost.append(table)
    c.check("quarantine.apply.keeps-total-rows", not lost, f"row counts off in {lost}")
    applied_events = _events(apply_log, "relation_quarantine_applied")
    c.check("quarantine.apply.logs-counts-and-checksum",
            len(applied_events) == 1 and applied_events[0].get("checksum") == checksum
            and applied_events[0].get("rows_moved") == len(EXPECT_MOVED)
            and applied_events[0].get("references_cleared") == len(EXPECT_CLEARED),
            repr(applied_events)[:300])
    leaked = sorted(i for i in fixture_ids if i in apply_log)
    c.check("quarantine.apply.logs-no-ids", not leaked, f"{len(leaked)} fixture ids in the log")

    # 3. A second run of the migration adds nothing.
    conn = sqlite3.connect(str(adb))
    try:
        conn.execute("DELETE FROM _migrations WHERE file = ?", (MIGRATION,))
        conn.commit()
    finally:
        conn.close()
    after_apply = snapshot(adb, skip=("_migrations",))
    run = _migrate(app, full)
    c.check("quarantine.reapply.adds-nothing",
            run.returncode == 0 and _applied(adb) and snapshot(adb, skip=("_migrations",)) == after_apply,
            _diff(snapshot(adb, skip=("_migrations",)), after_apply) + " " + (run.stdout + run.stderr)[-300:])
    return app, base_db


# -- PocketBase served on loopback ------------------------------------------------

def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Served:
    """`pocketbase serve` on a loopback port for the duration of a block."""

    def __init__(self, work: Path, data: Path, migrations: Path, name: str) -> None:
        self.port = _free_port()
        self.log = open(work / f"{name}.serve.log", "w")
        self.proc = subprocess.Popen(
            [str(PB_BIN), "serve", f"--http=127.0.0.1:{self.port}", f"--dir={data}",
             f"--migrationsDir={migrations}", f"--hooksDir={HOOKS}"],
            stdout=self.log, stderr=subprocess.STDOUT, env=_env(),
        )
        self.pb = PBClient(f"http://127.0.0.1:{self.port}")

    def __enter__(self) -> PBClient:
        try:
            self.pb.wait_healthy()
        except Exception:
            self.__exit__()
            raise
        return self.pb

    def __exit__(self, *exc) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.log.close()


def _ok(resp, *statuses: int) -> dict:
    if resp.status not in statuses:
        raise RuntimeError(f"unexpected status {resp.status}: {resp.body!r}")
    return resp.body if isinstance(resp.body, dict) else {}


# -- B. replay ----------------------------------------------------------------------

def _lever(work: Path, name: str, entry_ids: list[str]) -> Path:
    """A folder holding only the filled-in replay lever, as an operator makes it."""
    folder = work / f"lever_{name}"
    folder.mkdir()
    src = (LEVERS / "replay_quarantine.template.js").read_text()
    ids = ", ".join(json.dumps(i) for i in entry_ids)
    (folder / "1800000000_replay_quarantine.js").write_text(src.replace('"__ENTRY_ID__"', ids))
    return folder


def check_replay(c: Checks, work: Path, applied: Path, base_db: Path, full: Path, admin_env: dict[str, str]) -> None:
    # Marking entries through the admin API on the upgraded shape keeps the payload.
    marked = work / "replay_marked"
    shutil.copytree(applied, marked)
    mdb = marked / "data.db"
    dropped = _journal_entry(mdb, "ai_settings", SB, "vision_provider") or {}
    replayed = _journal_entry(mdb, "resume_versions", RV1, "resume") or {}
    try:
        with Served(work, marked, full, "replay") as pb:
            admin = _ok(pb.admin_auth(admin_env["PB_ADMIN_EMAIL"], admin_env["PB_ADMIN_PASSWORD"]), 200)["token"]
            r1 = pb.update("relation_quarantine", dropped.get("id", "missing"), {"status": "dropped"}, admin)
            r2 = pb.update("relation_quarantine", replayed.get("id", "missing"), {"status": "replayed"}, admin)
    except Exception as err:  # noqa: BLE001 - report, never crash the phase
        c.check("quarantine.replay.status-through-the-admin-api", False, str(err)[:300])
    else:
        after_d = _journal_entry(mdb, "ai_settings", SB, "vision_provider") or {}
        after_r = _journal_entry(mdb, "resume_versions", RV1, "resume") or {}
        c.check("quarantine.replay.status-through-the-admin-api",
                r1.status == 200 and r2.status == 200
                and after_d.get("status") == "dropped" and after_r.get("status") == "replayed",
                f"dropped={r1.status} {r1.body!r} replayed={r2.status} {r2.body!r}"[:300])
        c.check("quarantine.replay.status-keeps-the-payload",
                bool(dropped.get("payload")) and after_d.get("payload") == dropped.get("payload")
                and bool(replayed.get("payload")) and after_r.get("payload") == replayed.get("payload"),
                "a status update changed or dropped the payload")

    # The lever writes same-owner entries back exactly, parents first.
    same = work / "replay_same_owner"
    shutil.copytree(applied, same)
    sdb = same / "data.db"
    conn = sqlite3.connect(str(sdb))
    try:
        # The operator corrects ownership first, through the same triggers:
        # these targets now belong to B (the application leaves A's campaign
        # as it moves, since the trigger would refuse it otherwise).
        conn.execute('UPDATE "applications" SET "user" = ?, "campaign" = \'\' WHERE id = ?', (UB, XA))
        conn.execute('UPDATE "resumes" SET "user" = ? WHERE id = ?', (UB, RA))
        conn.execute('UPDATE "ai_providers" SET "user" = ? WHERE id = ?', (UB, PA1))
        conn.commit()
    except sqlite3.Error as err:
        c.check("quarantine.replay.ownership-corrected", False, str(err))
        return
    finally:
        conn.close()
    wanted = [("offers", O2, "application"), ("offers", O1, "application"),  # child listed before parent
              ("resume_versions", RV1, "resume"), ("ai_settings", SB, "text_provider")]
    entries = [_journal_entry(sdb, *w) or {} for w in wanted]
    payloads = [e.get("payload") for e in entries]
    run = _migrate(same, _lever(work, "same", [e.get("id", "missing") for e in entries]))
    log = run.stdout + run.stderr
    c.check("quarantine.replay.lever-applies", _applied(sdb, "1800000000_replay_quarantine.js"), log[-500:])
    inexact = [w[:2] for w in wanted[:3] if _raw_row(sdb, w[0], w[1]) != _raw_row(base_db, w[0], w[1])]
    c.check("quarantine.replay.restores-moved-rows-exactly", not inexact,
            f"not restored exactly: {inexact} (created, updated, numbers, and JSON text included)")
    sb = _row(sdb, "ai_settings", SB) or {}
    c.check("quarantine.replay.restores-a-cleared-field", sb.get("text_provider") == PA1,
            f"text_provider={sb.get('text_provider')!r}")
    after = [_journal_entry(sdb, *w) or {} for w in wanted]
    c.check("quarantine.replay.marks-entries-replayed",
            all(e.get("status") == "replayed" for e in after) and [e.get("payload") for e in after] == payloads,
            f"statuses={[e.get('status') for e in after]}")

    # An entry whose target still belongs to another account does not replay.
    foreign = work / "replay_foreign"
    shutil.copytree(applied, foreign)
    fdb = foreign / "data.db"
    before = snapshot(fdb, skip=("_migrations",))
    entry = _journal_entry(fdb, "ai_coding_drafts", D1, "campaign") or {}
    run = _migrate(foreign, _lever(work, "foreign", [entry.get("id", "missing")]))
    c.check("quarantine.replay.refuses-a-foreign-entry",
            not _applied(fdb, "1800000000_replay_quarantine.js") and _row(fdb, "ai_coding_drafts", D1) is None
            and snapshot(fdb, skip=("_migrations",)) == before,
            "a still-foreign entry was written back, or the refused run changed something")


# -- C. schema drift -------------------------------------------------------------------

DRIFT = """migrate((db) => {
  const dao = new Dao(db);
  // A view that selects a relation into a collection the quarantine can move rows from.
  dao.saveCollection(new Collection({
    name: "lq_offer_view", type: "view", listRule: null, viewRule: null,
    options: { query: "SELECT id, application FROM offers" },
  }));
  // A relation outside the frozen table, pointing into todos.
  const timers = dao.findCollectionByNameOrId("question_timers");
  const todos = dao.findCollectionByNameOrId("todos");
  timers.schema.addField(new SchemaField({
    name: "lq_todo", type: "relation", options: { collectionId: todos.id, maxSelect: 1, cascadeDelete: false },
  }));
  dao.saveCollection(timers);
  // A cascade toggled on a frozen optional field.
  const progress = dao.findCollectionByNameOrId("user_progress");
  progress.schema.getFieldByName("campaign").options.cascadeDelete = true;
  dao.saveCollection(progress);
}, (_db) => {});
"""

# A collection the frozen table names is gone, so creating its trigger fails:
# the earliest step of the migration, which must still be reported.
DROP_COLLECTION = """migrate((db) => {
  const dao = new Dao(db);
  dao.deleteCollection(dao.findCollectionByNameOrId("user_progress"));
}, (_db) => {});
"""


def _with_extra(work: Path, src: Path, name: str, extra: str) -> Path:
    """A copy of a migrations folder plus one test-only migration (never committed)."""
    folder = work / name
    shutil.copytree(src, folder)
    (folder / "1700006999_lq_test_schema.js").write_text(extra)
    return folder


def check_guard(c: Checks, work: Path, base: Path, full: Path, admin_env: dict[str, str]) -> None:
    drift_base = _with_extra(work, base, "drift_base_migrations", DRIFT)
    drift_full = _with_extra(work, full, "drift_full_migrations", DRIFT)
    data = work / "drift_base"
    up = _migrate(data, drift_base, admin_env)
    if not c.check("quarantine.guard.drift-base-applies", _applied(data / "data.db", "1700006999_lq_test_schema.js"),
                   (up.stdout + up.stderr)[-400:]):
        return

    def case(name: str, seed) -> tuple[Path, subprocess.CompletedProcess, dict, subprocess.CompletedProcess]:
        copy = work / f"drift_{name}"
        shutil.copytree(data, copy)
        conn = sqlite3.connect(str(copy / "data.db"))
        try:
            seed(conn)
            conn.commit()
        finally:
            conn.close()
        dry = work / f"drift_{name}_dry"
        shutil.copytree(copy, dry)
        dry_run, report, _ = _dry_run(dry, drift_full, work, f"drift_{name}")
        apply = _migrate(copy, drift_full)
        return copy, dry_run, report, apply

    def nothing_to_move(conn):
        # Same-owner rows only; a timer points at a todo that stays.
        _users(conn, (UA, "a"))
        _insert(conn, "campaigns", id=CA, user=UA, name="a", slug="lq-a")
        _insert(conn, "todos", id=T2, user=UA, campaign=CA, body="t2")
        _insert(conn, "question_timers", id=rid("qt"), user=UA, question_type="coding", question_slug="lq",
                accumulated_ms=0, lq_todo=T2)

    copy, _, report, apply = case("clean", nothing_to_move)
    c.check("quarantine.guard.ignores-drift-with-nothing-to-move",
            _applied(copy / "data.db") and report.get("status") == "ok",
            f"status={report.get('status')!r} error={report.get('error')!r} " + (apply.stdout + apply.stderr)[-300:])

    def toggled_with_a_finding(conn):
        _users(conn, (UA, "a"), (UB, "b"))
        _insert(conn, "campaigns", id=CA, user=UA, name="a", slug="lq-a")
        _insert(conn, "user_progress", id=rid("up"), user=UB, campaign=CA, question_type="coding", question_slug="lq")

    def unlisted_dependent(conn):
        _users(conn, (UB, "b"))
        _insert(conn, "todos", id=T1, user=UB, campaign=MISSING_CAMPAIGN, body="t1")
        _insert(conn, "question_timers", id=rid("qt"), user=UB, question_type="coding", question_slug="lq",
                accumulated_ms=0, lq_todo=T1)

    for name, seed in (("toggled", toggled_with_a_finding), ("unlisted", unlisted_dependent)):
        copy, dry_run, report, apply = case(name, seed)
        failed = _events(apply.stdout + apply.stderr, "relation_quarantine_failed")
        c.check(f"quarantine.guard.stops-on-{name}",
                not _applied(copy / "data.db") and report.get("status") == "failed"
                and "schema" in str(report.get("error", "")) and len(failed) == 1
                and failed[0].get("reason") == "schema_mismatch",
                f"applied={_applied(copy / 'data.db')} status={report.get('status')!r} log={failed!r}"[:300])


def check_failure_reporting(c: Checks, work: Path, base: Path, full: Path, admin_env: dict[str, str]) -> None:
    drop_base = _with_extra(work, base, "drop_base_migrations", DROP_COLLECTION)
    drop_full = _with_extra(work, full, "drop_full_migrations", DROP_COLLECTION)
    data = work / "drop_base"
    _migrate(data, drop_base, admin_env)
    if not c.check("quarantine.failure.drop-base-applies", _applied(data / "data.db", "1700006999_lq_test_schema.js"),
                   "the test migration did not apply"):
        return
    dry = work / "drop_dry"
    shutil.copytree(data, dry)
    _, report, _ = _dry_run(dry, drop_full, work, "drop")
    c.check("quarantine.failure.dry-run-reports-an-early-failure",
            report.get("status") == "failed" and report.get("stage") == "triggers",
            f"status={report.get('status')!r} stage={report.get('stage')!r}")
    apply = _migrate(data, drop_full)
    failed = _events(apply.stdout + apply.stderr, "relation_quarantine_failed")
    c.check("quarantine.failure.apply-logs-an-early-failure",
            not _applied(data / "data.db") and len(failed) == 1 and failed[0].get("stage") == "triggers",
            repr(failed)[:300])


# -- D. deletes through the API on a served copy ----------------------------------------

def _shapes(pb: PBClient, acct: factory.Account) -> dict[str, str]:
    """A provider set as both providers, and an application with two chained offers."""
    tok, uid, tag = acct.token, acct.user_id, acct.tag
    ids: dict[str, str] = {}
    ids["provider"] = _ok(pb.create("ai_providers", tok, {"user": uid, "kind": "openai", "label": "p"}), 200)["id"]
    ids["settings"] = _ok(pb.create("ai_settings", tok, {"user": uid, "text_provider": ids["provider"],
                                                         "vision_provider": ids["provider"]}), 200)["id"]
    ids["campaign"] = _ok(pb.create("campaigns", tok, {"user": uid, "name": tag, "slug": f"{tag}-{secrets.token_hex(3)}"}), 200)["id"]
    ids["application"] = _ok(pb.create("applications", tok, {"user": uid, "company": "Acme", "role": "Engineer",
                                                             "campaign": ids["campaign"]}), 200)["id"]
    ids["offer1"] = _ok(pb.create("offers", tok, {"user": uid, "application": ids["application"], "status": "pending"}), 200)["id"]
    ids["offer2"] = _ok(pb.create("offers", tok, {"user": uid, "application": ids["application"], "status": "pending",
                                                  "previous_offer": ids["offer1"]}), 200)["id"]
    return ids


COLLECTION_OF = {"provider": "ai_providers", "settings": "ai_settings", "campaign": "campaigns",
                 "application": "applications", "offer1": "offers", "offer2": "offers"}


def check_deletes(c: Checks, work: Path, full: Path, admin_env: dict[str, str]) -> None:
    data = work / "served"
    up = _migrate(data, full, admin_env)
    if not c.check("relation-delete.migrations-apply", up.returncode == 0 and _applied(data / "data.db"),
                   (up.stdout + up.stderr)[-400:]):
        return
    try:
        with Served(work, data, full, "deletes") as pb:
            admin = _ok(pb.admin_auth(admin_env["PB_ADMIN_EMAIL"], admin_env["PB_ADMIN_PASSWORD"]), 200)["token"]
            accounts = {}
            for tag in ("del1", "del2", "keep"):
                acct = factory.make_account(tag)
                factory.register(pb, acct)
                accounts[tag] = acct
            one = _shapes(pb, accounts["del1"])
            two = _shapes(pb, accounts["del2"])
            keep = _shapes(pb, accounts["keep"])
            tok = accounts["del1"].token

            resp = pb.delete("ai_providers", one["provider"], tok)
            settings = pb.view("ai_settings", one["settings"], tok).body or {}
            c.check("relation-delete.provider-in-both-slots",
                    resp.status == 204 and settings.get("text_provider") == "" and settings.get("vision_provider") == "",
                    f"delete={resp.status} text={settings.get('text_provider')!r} vision={settings.get('vision_provider')!r}")

            resp = pb.delete("applications", one["application"], tok)
            left = [k for k in ("offer1", "offer2") if pb.view("offers", one[k], tok).status != 404]
            c.check("relation-delete.application-with-chained-offers", resp.status == 204 and not left,
                    f"delete={resp.status} offers left={left}")

            resp = pb.delete("users", accounts["del2"].user_id, admin)
            left = [k for k, coll in COLLECTION_OF.items() if pb.view(coll, two[k], admin).status != 404]
            c.check("relation-delete.account-with-both-shapes", resp.status == 204 and not left,
                    f"delete={resp.status} rows left={left}")

            missing = [k for k, coll in COLLECTION_OF.items() if pb.view(coll, keep[k], admin).status != 200]
            kept = pb.view("ai_settings", keep["settings"], admin).body or {}
            c.check("relation-delete.stays-inside-the-account",
                    not missing and kept.get("text_provider") == keep["provider"]
                    and kept.get("vision_provider") == keep["provider"],
                    f"missing={missing}")
    except Exception as err:  # noqa: BLE001 - report, never crash the phase
        c.check("relation-delete.served-copy", False, str(err)[:300])


def main() -> int:
    c = Checks()
    work = Path(tempfile.mkdtemp(prefix="relation-quarantine-"))
    try:
        base = work / "base_migrations"
        full = work / "migrations"
        base.mkdir()
        full.mkdir()
        for path in sorted(MIGRATIONS.glob("*.js")):
            shutil.copy(path, full / path.name)
            if path.name < MIGRATION:
                shutil.copy(path, base / path.name)
        # Generated per run, never printed: the bootstrap migration creates
        # this superuser on a fresh pb_data.
        admin_env = {"PB_ADMIN_EMAIL": f"lq-admin-{secrets.token_hex(4)}@harness.invalid",
                     "PB_ADMIN_PASSWORD": "Hx" + secrets.token_hex(16)}
        applied = check_quarantine(c, work, base, full, admin_env)
        if applied:
            check_replay(c, work, applied[0], applied[1], full, admin_env)
        check_guard(c, work, base, full, admin_env)
        check_failure_reporting(c, work, base, full, admin_env)
        check_deletes(c, work, full, admin_env)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"relation quarantine check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
