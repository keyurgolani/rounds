"""Harness check for the relation quarantine and triggers (ROUNDS-00B-L02).

Runs the pinned PocketBase binary offline against throwaway pb_data, with
``1700007000_relation_endpoint_authz.js`` and the hooks from this checkout.

A. Legacy fixture (``quarantine.*``). Applies every migration that sorts
   before 1700007000, plants cross-owner and missing-target rows with direct
   SQL (no trigger exists yet), then:

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
      original row JSON, pseudonyms, and status, and logs counts and the
      checksum only.
   3. Running the migration again adds nothing.

B. Deletes after the migration, through the API on a served copy
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
MIGRATION = "1700007000_relation_endpoint_authz.js"
MIGRATION_ID = MIGRATION[: -len(".js")]
PSEUDONYM = re.compile(r"^acct-\d{2}$")
STAMP = "2024-01-01 00:00:00.000Z"


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


def seed_legacy(db: Path) -> list[str]:
    """Plant the legacy rows; returns every fixture id (for the log checks)."""
    conn = sqlite3.connect(str(db))
    try:
        round_id = conn.execute("SELECT id FROM ai_coding_rounds ORDER BY id LIMIT 1").fetchone()[0]
        for uid, tag in ((UA, "a"), (UB, "b")):
            _insert(conn, "users", id=uid, username=f"lq{tag}user", email=f"lq-{tag}@harness.invalid",
                    tokenKey=secrets.token_hex(16), passwordHash="x")
        _insert(conn, "campaigns", id=CA, user=UA, name="a", slug="lq-a")
        _insert(conn, "campaigns", id=CB, user=UB, name="b", slug="lq-b")
        _insert(conn, "applications", id=XA, user=UA, company="Acme", role="Engineer", campaign=CA)
        _insert(conn, "applications", id=XB, user=UB, company="Acme", role="Engineer", campaign=CB)
        _insert(conn, "applications", id=XM, user=UB, company="Acme", role="Engineer", campaign=MISSING_CAMPAIGN)
        # Two offers chained to each other, both on another account's application.
        _insert(conn, "offers", id=O1, user=UB, application=XA, status="pending")
        _insert(conn, "offers", id=O2, user=UB, application=XA, status="pending", previous_offer=O1)
        # A same-owner offer that points at a moved offer, and one left alone.
        _insert(conn, "offers", id=O3, user=UB, application=XB, status="pending", previous_offer=O1)
        _insert(conn, "offers", id=O4, user=UB, application=XB, status="pending")
        _insert(conn, "resumes", id=RA, user=UA, name="a", slug="lq-ra")
        _insert(conn, "resumes", id=RB, user=UB, name="b", slug="lq-rb")
        # A variant on another account's resume brings its versions, links, and views.
        _insert(conn, "resume_variants", id=VB, user=UB, resume=RA, name="v")
        _insert(conn, "resume_versions", id=RV1, user=UB, resume=RA)
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


# -- A. legacy fixture: dry run, apply, reapply ---------------------------------

def check_quarantine(c: Checks, work: Path, base: Path, full: Path, admin_env: dict[str, str]) -> None:
    base_data = work / "legacy_base"
    up = _migrate(base_data, base, admin_env)
    last_base = sorted(p.name for p in base.glob("*.js"))[-1]
    if not c.check("quarantine.legacy.base-applies",
                   _applied(base_data / "data.db", last_base) and not _applied(base_data / "data.db"),
                   (up.stdout + up.stderr)[-400:]):
        return
    fixture_ids = seed_legacy(base_data / "data.db")
    before = snapshot(base_data / "data.db")

    # 1. Dry run on a copy.
    dry = work / "legacy_dry"
    shutil.copytree(base_data, dry)
    reports = work / "reports"
    reports.mkdir()
    report_path = reports / "dry.json"
    run = _migrate(dry, full, {"ROUNDS_RELATION_QUARANTINE": "dry-run",
                               "ROUNDS_RELATION_QUARANTINE_REPORT": str(report_path)})
    dry_log = run.stdout + run.stderr
    c.check("quarantine.dry-run.exits-zero", run.returncode == 0, f"exit={run.returncode}")
    report = {}
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text())
        except ValueError:
            report = {}
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
        return
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
    base_db = base_data / "data.db"
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
    payloads = {(e["source_collection"], e["source_id"], e["field"]): json.loads(e["payload"]) for e in journal}
    o2 = payloads.get(("offers", O2, "application"), {})
    sbp = payloads.get(("ai_settings", SB, "text_provider"), {})
    c.check("quarantine.apply.journal-keeps-the-original-row",
            o2.get("previous_offer") == O1 and sbp.get("text_provider") == PA1 and sbp.get("vision_provider") == PA2,
            f"o2.previous_offer={o2.get('previous_offer')!r} sb={sbp.get('text_provider')!r}/{sbp.get('vision_provider')!r}")
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


# -- B. deletes through the API on a served copy --------------------------------

def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _ok(resp, *statuses: int) -> dict:
    if resp.status not in statuses:
        raise RuntimeError(f"unexpected status {resp.status}: {resp.body!r}")
    return resp.body if isinstance(resp.body, dict) else {}


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
    port = _free_port()
    log = open(work / "serve.log", "w")
    server = subprocess.Popen(
        [str(PB_BIN), "serve", f"--http=127.0.0.1:{port}", f"--dir={data}",
         f"--migrationsDir={full}", f"--hooksDir={HOOKS}"],
        stdout=log, stderr=subprocess.STDOUT, env=_env(),
    )
    try:
        pb = PBClient(f"http://127.0.0.1:{port}")
        pb.wait_healthy()
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
                not missing and kept.get("text_provider") == keep["provider"] and kept.get("vision_provider") == keep["provider"],
                f"missing={missing}")
    except Exception as err:  # noqa: BLE001 - report, never crash the phase
        c.check("relation-delete.served-copy", False, str(err)[:300])
    finally:
        server.terminate()
        try:
            server.wait(timeout=20)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()


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
        check_quarantine(c, work, base, full, admin_env)
        check_deletes(c, work, full, admin_env)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"relation quarantine check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
