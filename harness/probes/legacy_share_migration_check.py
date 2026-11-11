"""Harness check for the older share links' migration (ROUNDS-00B-L06 stage 1).

Runs ``1700008400_legacy_share_migration.js`` with the pinned PocketBase
binary on a ``pb_data`` that holds every other migration, as an upgraded
install does, and a fixture
built in two steps: links that #10 quarantines (another account's resume, a
variant on another account's resume, a resume that's gone) planted before
#10 runs, and then, before this migration, a link for every other outcome
and reason it decides, real and malformed views, a demo account's link, and
10,000 more links so it runs for several batches.

1. Dry run: the migration and ``pocketbase legacy-share-receipt`` on a copy,
   with the original unchanged. The receipt reconciles, and its counts and
   journal match the fixture.
2. Forward on the original: the same journal checksum and counts, every
   link turned off with the outcome and reason expected for it, and no
   fixture link secret, viewer address hash, or user agent left in any
   table or in any log.
3. Resume: killed at its first batch line (after that batch's journal rows,
   before its links), the migration isn't recorded and the database is as
   it was; run again, it gives the same journal checksum.
4. Reverse, after one link got its new link: ``migrate down 1`` confirmed on
   a pseudo terminal keeps the journal, the rules, ``legacy_status``,
   ``replaced_by`` and its triggers, removes the fields it added, and adds
   the dropped ones back empty, with no secret and no link turned back on.
5. Forward again: the same journal checksum, and the link it replaced still
   replaced.

Prints one PASS/FAIL line per check and exits non-zero on any failure.

The harness runs it in the probe image with the seeds at /pb_seeds. A native
run outside a container names their folder in PB_SEEDS_DIR, and the seed
migrations' copies here read from it; nothing else in a copy changes.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from admission_migration_check import Checks, _migrate_down_confirmed
from relation_quarantine_check import _diff, _events, _insert, _users, snapshot

PB_BIN = Path(os.environ.get("PB_BIN", "/pbbin/pocketbase"))
MIGRATIONS = Path(os.environ.get("PB_MIGRATIONS_DIR", "/pb_migrations"))
HOOKS = Path(os.environ.get("PB_HOOKS_DIR", "/pb_hooks"))
SEEDS_DIR = os.environ.get("PB_SEEDS_DIR", "")
MIGRATION = "1700008400_legacy_share_migration.js"
QUARANTINE_MIGRATION = "1700007000_relation_endpoint_authz.js"
JOURNAL = "legacy_share_migration"
LINKS = "resume_share_links"
VIEWS = "resume_share_views"
# The extra links, so the migration runs for many batches; a local smoke
# run may ask for fewer (at least two batches' worth).
BULK = max(1000, int(os.environ.get("LEGACY_SHARES_BULK", "10000")))
STAMP = "2024-01-01 00:00:00.000Z"
DROPPED = ("token", "is_password", "password_hash", "expires_at")
ADDED_ONLY_FORWARD = ("legacy_reason", "turned_off_at", "manifest_id")
KEPT = ("legacy_status", "replaced_by")
LINK_RULE = 'user = @request.auth.id && legacy_status != "revoked_ownership"'
VIEW_RULE = 'user = @request.auth.id && link.legacy_status != "revoked_ownership"'
REPLACED_TRIGGERS = tuple(f"rel_authz_{LINKS}_replaced_by_{k}" for k in ("ins", "upd", "tgt"))
# Marks every fixture viewer value carries, so a scan can find any left.
IP_MARK = "fixtureviewerhash"
AGENT_MARK = "FixtureAgent"


def rid(tag: str) -> str:
    """A fixed 15-character PocketBase id for a fixture row."""
    out = ("ls" + tag + "0" * 15)[:15]
    assert re.fullmatch(r"[a-z0-9]{15}", out), tag
    return out


def token() -> str:
    return secrets.token_urlsafe(16)


# -- the fixture ------------------------------------------------------------------

UA, UB, UL, UD, UX = rid("ua"), rid("ub"), rid("ul"), rid("ud"), rid("ux")
RA, RB, RL, RD, RX, RM, RN = rid("ra"), rid("rb"), rid("rl"), rid("rd"), rid("rx"), rid("rm"), rid("rn")
VB, VL, VN = rid("vb"), rid("vl"), rid("vn")
MISSING = rid("missing")
SNAP, CAP = rid("snap"), rid("cap")

# Planted before #10, which quarantines each: (id, fields, expected reason).
QUARANTINED = [
    (rid("q1"), {"user": UB, "resume": RA}, "quarantined_cross_owner"),
    (rid("q2"), {"user": UB, "variant": VB}, "quarantined_dependent"),
    (rid("q3"), {"user": UB, "resume": MISSING}, "quarantined_missing_target"),
]
# Views of the first, which #10 quarantines with it.
QUARANTINED_VIEWS = [(rid("qw1"), rid("q1"), "2024-02-03 04:05:06.000Z"), (rid("qw2"), rid("q1"), "2024-02-09 00:00:00.000Z")]

ELIGIBLE = rid("le1")
VARIANT_LINK = rid("le2")
# Planted before this migration: (id, fields, expected outcome, reason).
LIVE = [
    (ELIGIBLE, {"user": UL, "resume": RL}, "migrated", "eligible"),
    (VARIANT_LINK, {"user": UL, "variant": VL}, "migrated", "eligible"),
    (rid("ld1"), {"user": UD, "resume": RD}, "revoked_demo", "demo_account"),
    (rid("lo1"), {"user": "", "resume": ""}, "revoked_unverified", "owner_missing"),
    (rid("lo2"), {"user": UX, "resume": RX}, "revoked_unverified", "owner_missing"),
    (rid("ln1"), {"user": UL}, "revoked_unverified", "no_target"),
    (rid("lm1"), {"user": UL, "resume": RM}, "revoked_unverified", "target_missing"),
    (rid("lm2"), {"user": UL, "variant": VN}, "revoked_unverified", "target_missing"),
    (rid("lt1"), {"user": UL, "resume": RL, "token": "fixtureshortmark"}, "revoked_unverified", "token_format"),
    (rid("lp1"), {"user": UL, "resume": RL, "is_password": 1}, "revoked_unverified", "password_set"),
    (rid("lp2"), {"user": UL, "resume": RL, "password_hash": "$fixture$hash$" + secrets.token_hex(8)},
     "revoked_unverified", "password_set"),
    (rid("lx1"), {"user": UL, "resume": RL, "expires_at": "2030-01-01 00:00:00.000Z"}, "revoked_unverified",
     "expiry_set"),
]
# The eligible link's views: two as a reader made them, and two with dates
# that aren't dates, which keep no day.
LIVE_VIEWS = [
    (rid("w1"), "2024-03-04 05:06:07.000Z"),
    (rid("w2"), "2024-05-06 07:08:09.000Z"),
    (rid("w3"), "not-a-date"),
    (rid("w4"), "2024-13-45 99:99:99"),
]


def _ro(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _applied(db: Path, name: str = MIGRATION) -> bool:
    conn = _ro(db)
    try:
        return conn.execute("SELECT 1 FROM _migrations WHERE file = ?", (name,)).fetchone() is not None
    finally:
        conn.close()


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {"PATH": "/usr/bin:/bin"}
    env.update(extra or {})
    return env


def _migrate(data: Path, migrations: Path, extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PB_BIN), "migrate", "up", f"--dir={data}", f"--migrationsDir={migrations}"],
        capture_output=True, text=True, timeout=600, env=_env(extra),
    )


def plant_quarantined(db: Path) -> list[str]:
    """Before #10: two accounts, another account's resume, a variant on it,
    and three links #10 moves, with two views. Returns the secrets planted."""
    planted: list[str] = []
    conn = sqlite3.connect(str(db))
    try:
        _users(conn, (UA, "a"), (UB, "b"))
        _insert(conn, "resumes", id=RA, user=UA, name="a", slug="ls-ra")
        _insert(conn, "resumes", id=RB, user=UB, name="b", slug="ls-rb")
        _insert(conn, "resume_variants", id=VB, user=UB, resume=RA, name="v")
        for link_id, fields, _reason in QUARANTINED:
            secret = token()
            planted.append(secret)
            _insert(conn, LINKS, id=link_id, token=secret, **{"resume": "", "variant": "", **fields})
        for view_id, link_id, at in QUARANTINED_VIEWS:
            _insert(conn, VIEWS, id=view_id, user=UB, link=link_id, viewed_at=at,
                    viewer_ip_hash=f"{IP_MARK}{secrets.token_hex(8)}", user_agent=f"Mozilla/5.0 ({AGENT_MARK} q)")
        conn.commit()
    finally:
        conn.close()
    return planted


def plant_live(db: Path) -> list[str]:
    """Before this migration, with #10's triggers on: a link for every
    other outcome and reason, the eligible link's views, and BULK more
    eligible links. Returns the secrets planted."""
    planted: list[str] = []
    conn = sqlite3.connect(str(db))
    try:
        _users(conn, (UL, "l"), (UD, "d"), (UX, "x"))
        conn.execute("UPDATE users SET is_demo = 1 WHERE id = ?", (UD,))
        for res, owner in ((RL, UL), (RD, UD), (RX, UX), (RM, UL), (RN, UL)):
            _insert(conn, "resumes", id=res, user=owner, name="r", slug=f"ls-{res}")
        _insert(conn, "resume_variants", id=VL, user=UL, resume=RL, name="For Acme")
        _insert(conn, "resume_variants", id=VN, user=UL, resume=RN, name="Gone")
        for link_id, fields, _outcome, _reason in LIVE:
            row = {"resume": "", "variant": "", "is_password": 0, "password_hash": "", "expires_at": "", **fields}
            row.setdefault("token", token())
            planted.append(row["token"])
            if row["password_hash"]:
                planted.append(row["password_hash"])
            _insert(conn, LINKS, id=link_id, **row)
        for view_id, at in LIVE_VIEWS:
            _insert(conn, VIEWS, id=view_id, user=UL, link=ELIGIBLE, viewed_at=at,
                    viewer_ip_hash=f"{IP_MARK}{secrets.token_hex(8)}", user_agent=f"Mozilla/5.0 ({AGENT_MARK} {view_id})")
        bulk = [(f"lsbulk{n:09d}", STAMP, STAMP, UL, RL, token()) for n in range(BULK)]
        conn.executemany(f'INSERT INTO "{LINKS}" (id, created, updated, user, resume, token) VALUES (?, ?, ?, ?, ?, ?)',
                         bulk)
        planted.extend(row[-1] for row in bulk)
        # Gone after the links were made: an owner, a resume, and a
        # variant's resume. Deleting a row runs none of #10's triggers.
        conn.execute("DELETE FROM users WHERE id = ?", (UX,))
        conn.execute("DELETE FROM resumes WHERE id IN (?, ?)", (RM, RN))
        conn.commit()
    finally:
        conn.close()
    return planted


def expected_outcomes() -> dict[str, tuple[str, str]]:
    want = {link_id: (outcome, reason) for link_id, _f, outcome, reason in LIVE}
    want.update({f"lsbulk{n:09d}": ("migrated", "eligible") for n in range(BULK)})
    want.update({link_id: ("revoked_ownership", reason) for link_id, _f, reason in QUARANTINED})
    return want


def expected_counts() -> tuple[dict[str, int], dict[str, int]]:
    outcomes: dict[str, int] = {"migrated": 0, "revoked_ownership": 0, "revoked_demo": 0, "revoked_unverified": 0}
    reasons: dict[str, int] = {}
    for outcome, reason in expected_outcomes().values():
        outcomes[outcome] += 1
        reasons[reason] = reasons.get(reason, 0) + 1
    return outcomes, reasons


# -- PocketBase ------------------------------------------------------------------


def receipt(work: Path, data: Path, migrations: Path, name: str) -> tuple[dict, str]:
    """``pocketbase legacy-share-receipt`` on ``data``, written outside it."""
    out = work / f"receipt-{name}.json"
    run = subprocess.run(
        [str(PB_BIN), "legacy-share-receipt", f"--dir={data}", f"--hooksDir={HOOKS}", f"--migrationsDir={migrations}",
         "--out", str(out), "--commit", "harness"],
        capture_output=True, text=True, timeout=300, env=_env(),
    )
    log = run.stdout + run.stderr
    if run.returncode != 0 or not out.exists():
        return {}, log
    return json.loads(out.read_text()), log


def migrate_killed_at_first_batch(data: Path, migrations: Path, timeout_s: float = 300) -> tuple[bool, str]:
    """``migrate up``, killed with SIGKILL as soon as it logs its first batch
    line. Returns whether that line came, and the output up to it."""
    proc = subprocess.Popen(
        [str(PB_BIN), "migrate", "up", f"--dir={data}", f"--migrationsDir={migrations}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=_env(),
    )
    seen = []
    killed = False
    deadline = time.monotonic() + timeout_s
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            seen.append(line)
            if '"event":"legacy_share_batch"' in line:
                proc.send_signal(signal.SIGKILL)
                killed = True
                break
            if time.monotonic() > deadline:
                break
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=60)
    return killed, "".join(seen)


# -- reads -----------------------------------------------------------------------------


def journal(db: Path) -> dict[str, dict]:
    conn = _ro(db)
    try:
        return {r["link"]: dict(r) for r in conn.execute(f'SELECT * FROM "{JOURNAL}"')}
    finally:
        conn.close()


def links(db: Path) -> dict[str, dict]:
    conn = _ro(db)
    try:
        return {r["id"]: dict(r) for r in conn.execute(f'SELECT * FROM "{LINKS}"')}
    finally:
        conn.close()


def collection(db: Path, name: str) -> dict | None:
    conn = _ro(db)
    try:
        row = conn.execute(
            "SELECT schema, indexes, listRule, viewRule, createRule, updateRule, deleteRule FROM _collections "
            "WHERE name = ?", (name,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {"fields": {f["name"]: f for f in json.loads(row["schema"])}, "indexes": json.loads(row["indexes"]),
            "rules": [row["listRule"], row["viewRule"], row["createRule"], row["updateRule"], row["deleteRule"]]}


def moved_links(db: Path) -> int:
    conn = _ro(db)
    try:
        return conn.execute("SELECT COUNT(*) FROM relation_quarantine WHERE source_collection = ?", (LINKS,)).fetchone()[0]
    finally:
        conn.close()


def columns(db: Path, table: str) -> set[str]:
    conn = _ro(db)
    try:
        return {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
    finally:
        conn.close()


def triggers(db: Path) -> set[str]:
    conn = _ro(db)
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
    finally:
        conn.close()


def left_behind(db: Path, planted: set[str]) -> dict[str, int]:
    """Every fixture secret, viewer hash, and user agent still in any text
    value of any table, by table."""
    found: dict[str, int] = {}
    run = re.compile(r"[A-Za-z0-9_$-]{5,}")
    conn = _ro(db)
    try:
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
            for row in conn.execute(f'SELECT * FROM "{table}"'):
                for value in row:
                    if not isinstance(value, str):
                        continue
                    hits = IP_MARK in value or AGENT_MARK in value or any(m in planted for m in run.findall(value))
                    if hits:
                        found[table] = found.get(table, 0) + 1
    finally:
        conn.close()
    return found


def secrets_in(text: str, planted: set[str]) -> int:
    run = re.compile(r"[A-Za-z0-9_$-]{5,}")
    return sum(1 for m in run.findall(text) if m in planted) + text.count(IP_MARK) + text.count(AGENT_MARK)


def ids_in(text: str) -> int:
    return len(re.findall(r"\bls[a-z0-9]{13}\b", text))


# -- the steps ---------------------------------------------------------------------------


def check_receipt(c: Checks, name: str, got: dict, reissued: int) -> None:
    outcomes, reasons = expected_counts()
    total = sum(outcomes.values())
    c.check(f"legacy-shares.{name}.receipt-reconciles", got.get("reconciled") is True,
            json.dumps({k: got.get(k) for k in ("links", "left", "outcomes")})[:400])
    c.check(f"legacy-shares.{name}.receipt-counts", got.get("outcomes") == outcomes
            and {k: v for k, v in (got.get("reasons") or {}).items() if v} == reasons
            and (got.get("journal") or {}).get("rows") == total,
            json.dumps({"outcomes": got.get("outcomes"), "journal": got.get("journal")})[:400])
    c.check(f"legacy-shares.{name}.receipt-incidents-and-reissued",
            got.get("incidents") == 1 and got.get("reissued") == reissued,
            f"incidents={got.get('incidents')} reissued={got.get('reissued')}")
    c.check(f"legacy-shares.{name}.receipt-left-nothing",
            got.get("left") == {"link_fields": 0, "quarantined_link_secrets": 0, "view_details": 0,
                                "quarantined_view_details": 0}, repr(got.get("left")))


def check_forward(c: Checks, name: str, db: Path, planted: set[str], log: str) -> None:
    want = expected_outcomes()
    rows = journal(db)
    wrong = sorted(k for k, v in want.items() if (rows.get(k) or {}).get("outcome") != v[0]
                   or (rows.get(k) or {}).get("reason") != v[1])
    c.check(f"legacy-shares.{name}.journals-each-link-with-its-outcome", not wrong and len(rows) == len(want),
            f"rows={len(rows)} want={len(want)} wrong={wrong[:5]}")
    now = links(db)
    off = [k for k, v in now.items() if v.get("legacy_status") != want.get(k, ("?",))[0]
           or v.get("manifest_id") != "legacy-shares-v1" or not v.get("turned_off_at")]
    c.check(f"legacy-shares.{name}.turns-every-live-link-off", not off and len(now) == len(LIVE) + BULK,
            f"links={len(now)} wrong={sorted(off)[:5]}")
    eligible = rows.get(ELIGIBLE) or {}
    c.check(f"legacy-shares.{name}.counts-views-by-day",
            (eligible.get("views"), eligible.get("first_view_day"), eligible.get("last_view_day")) ==
            (4, "2024-03-04", "2024-05-06") and not eligible.get("incident"), repr(eligible)[:300])
    q1 = rows.get(QUARANTINED[0][0]) or {}
    c.check(f"legacy-shares.{name}.counts-an-incident",
            (q1.get("origin"), q1.get("views"), bool(q1.get("incident"))) == ("quarantine", 2, True), repr(q1)[:300])
    c.check(f"legacy-shares.{name}.drops-the-link-fields",
            not set(DROPPED) & columns(db, LINKS) and {"legacy_status", "replaced_by", *ADDED_ONLY_FORWARD}
            <= columns(db, LINKS), repr(sorted(columns(db, LINKS))))
    found = collection(db, LINKS) or {"rules": None, "indexes": []}
    views = collection(db, VIEWS) or {"rules": None}
    c.check(f"legacy-shares.{name}.rules", found["rules"] == [LINK_RULE, LINK_RULE, None, None, None]
            and views["rules"] == [VIEW_RULE, VIEW_RULE, None, None, None], repr([found["rules"], views["rules"]]))
    c.check(f"legacy-shares.{name}.drops-the-token-index",
            not any("idx_share_links_token" in i for i in found["indexes"]), repr(found["indexes"]))
    c.check(f"legacy-shares.{name}.replaced-by-triggers", set(REPLACED_TRIGGERS) <= triggers(db),
            repr(sorted(t for t in triggers(db) if "replaced_by" in t)))
    left = left_behind(db, planted)
    c.check(f"legacy-shares.{name}.no-secret-hash-or-agent-left", not left, repr(left))
    c.check(f"legacy-shares.{name}.logs-no-secret-or-id", secrets_in(log, planted) == 0 and ids_in(log) == 0,
            f"secrets={secrets_in(log, planted)} ids={ids_in(log)}")
    events = _events(log, "legacy_share_migrated")
    c.check(f"legacy-shares.{name}.logs-its-counts", len(events) == 1, repr(events)[:300])


def plant_reissue(db: Path) -> None:
    """What Get a new link leaves behind, written straight to SQLite: the
    owner's snapshot, a capability on it, and the eligible link's
    replaced_by."""
    conn = sqlite3.connect(str(db))
    try:
        digest = "sha256:" + "0" * 64
        _insert(conn, "legacy_artifact_snapshots", id=SNAP, user=UL, source_kind="resume", source_id=RL,
                source_updated=STAMP, template_id="modern", design="{}", data="{}", markup="snapshot.html",
                content_checksum=digest, materializer_digest=digest, sanitizer_version="1.0.0", font_families="[]",
                size_bytes=10)
        _insert(conn, "share_capabilities", id=CAP, user=UL, snapshot=SNAP, status="active",
                expires_at="2030-01-01 00:00:00.000Z", capability_version=1, bearer_digest="hmac:" + "1" * 64,
                purpose="Shared resume")
        conn.execute(f'UPDATE "{LINKS}" SET replaced_by = ?, updated = ? WHERE id = ?', (CAP, STAMP, ELIGIBLE))
        conn.commit()
    finally:
        conn.close()


def check_reverse(c: Checks, db: Path, before_down: dict[str, dict]) -> None:
    c.check("legacy-shares.down.unrecorded", not _applied(db), "M1 is still recorded")
    cols = columns(db, LINKS)
    c.check("legacy-shares.down.keeps-status-and-replaced-by", set(KEPT) <= cols, repr(sorted(cols)))
    c.check("legacy-shares.down.removes-what-it-added", not set(ADDED_ONLY_FORWARD) & cols, repr(sorted(cols)))
    found = collection(db, LINKS) or {"fields": {}, "rules": None, "indexes": []}
    back = {name: found["fields"].get(name) for name in DROPPED}
    c.check("legacy-shares.down.adds-the-dropped-fields-back-optional",
            all(f is not None and not f.get("required") for f in back.values()),
            repr({k: (v or {}).get("required") for k, v in back.items()}))
    now = links(db)
    empty = all(not v.get("token") and not v.get("password_hash") and not v.get("expires_at") and not v.get("is_password")
                for v in now.values())
    c.check("legacy-shares.down.restores-no-secret", empty, "a dropped field came back with a value")
    still_off = all(v.get("legacy_status") == before_down[k].get("legacy_status") for k, v in now.items())
    c.check("legacy-shares.down.turns-no-link-back-on", still_off and now[ELIGIBLE].get("replaced_by") == CAP,
            f"replaced_by={now[ELIGIBLE].get('replaced_by')!r}")
    c.check("legacy-shares.down.keeps-the-journal", len(journal(db)) == len(expected_outcomes()),
            f"rows={len(journal(db))}")
    views = collection(db, VIEWS) or {"rules": None}
    c.check("legacy-shares.down.keeps-the-rules", found["rules"] == [LINK_RULE, LINK_RULE, None, None, None]
            and views["rules"] == [VIEW_RULE, VIEW_RULE, None, None, None], repr([found["rules"], views["rules"]]))
    c.check("legacy-shares.down.keeps-the-triggers", set(REPLACED_TRIGGERS) <= triggers(db), "a trigger is gone")
    c.check("legacy-shares.down.adds-no-token-index", not any("idx_share_links_token" in i for i in found["indexes"]),
            repr(found["indexes"]))


def main() -> int:
    c = Checks()
    work = Path(tempfile.mkdtemp(prefix="legacy-shares-"))
    try:
        before_10 = work / "before_quarantine"
        base = work / "base_migrations"
        full = work / "migrations"
        for folder in (before_10, base, full):
            folder.mkdir()
        for path in sorted(MIGRATIONS.glob("*.js")):
            text = path.read_text()
            if SEEDS_DIR and path.name != MIGRATION:
                text = text.replace("/pb_seeds/", SEEDS_DIR.rstrip("/") + "/")
            # An upgraded install has every other migration, the ones that
            # sort after this one included, so `migrate down 1` reverses it.
            folders = [full] + ([base] if path.name != MIGRATION else []) + \
                ([before_10] if path.name < QUARANTINE_MIGRATION else [])
            for folder in folders:
                (folder / path.name).write_text(text)
        admin_env = {"PB_ADMIN_EMAIL": f"ls-admin-{secrets.token_hex(4)}@harness.invalid",
                     "PB_ADMIN_PASSWORD": "Hx" + secrets.token_hex(16)}

        # The fixture: #10's links first, then everything else.
        base_data = work / "base_pb_data"
        up = _migrate(base_data, before_10, admin_env)
        if not c.check("legacy-shares.fixture.before-quarantine", up.returncode == 0, (up.stdout + up.stderr)[-400:]):
            return 1
        planted = set(plant_quarantined(base_data / "data.db"))
        up = _migrate(base_data, base)
        db = base_data / "data.db"
        quarantined = moved_links(db)
        if not c.check("legacy-shares.fixture.quarantines-three-links",
                       up.returncode == 0 and _applied(db, QUARANTINE_MIGRATION) and not _applied(db)
                       and quarantined == len(QUARANTINED), f"moved={quarantined} {(up.stdout + up.stderr)[-400:]}"):
            return 1
        planted |= set(plant_live(db))
        before = snapshot(db)
        pristine = work / "pristine_pb_data"
        shutil.copytree(base_data, pristine)

        # 1. A dry run on a copy.
        dry = work / "dry_pb_data"
        shutil.copytree(base_data, dry)
        started = time.monotonic()
        run = _migrate(dry, full)
        took = time.monotonic() - started
        c.check("legacy-shares.dry-run.applies", run.returncode == 0 and _applied(dry / "data.db"),
                (run.stdout + run.stderr)[-600:])
        dry_receipt, dry_log = receipt(work, dry, full, "dry")
        check_receipt(c, "dry-run", dry_receipt, 0)
        c.check("legacy-shares.dry-run.receipt-logs-no-secret-or-id",
                secrets_in(dry_log, planted) == 0 and ids_in(dry_log) == 0 and not _receipt_ids(dry_receipt),
                f"secrets={secrets_in(dry_log, planted)} ids={ids_in(dry_log)}")
        c.check("legacy-shares.dry-run.original-unchanged", snapshot(db) == before, _diff(snapshot(db), before))
        print(f"INFO legacy-shares.dry-run took {took:.1f}s for {len(LIVE) + BULK} live links")

        # 2. Forward on the original.
        run = _migrate(base_data, full)
        log = run.stdout + run.stderr
        if not c.check("legacy-shares.forward.applies", run.returncode == 0 and _applied(db), log[-600:]):
            return 1
        check_forward(c, "forward", db, planted, log)
        fwd_receipt, _ = receipt(work, base_data, full, "forward")
        check_receipt(c, "forward", fwd_receipt, 0)
        c.check("legacy-shares.forward.same-journal-as-the-dry-run",
                fwd_receipt.get("journal") == dry_receipt.get("journal")
                and fwd_receipt.get("checksum") == dry_receipt.get("checksum"),
                f"{fwd_receipt.get('journal')} != {dry_receipt.get('journal')}")

        # 3. Killed at its first batch line, then run again.
        resumed = work / "resume_pb_data"
        shutil.copytree(pristine, resumed)
        rdb = resumed / "data.db"
        killed, out = migrate_killed_at_first_batch(resumed, full)
        c.check("legacy-shares.resume.killed-at-the-first-batch", killed, out[-400:])
        c.check("legacy-shares.resume.kill-records-nothing", not _applied(rdb) and snapshot(rdb) == before,
                _diff(snapshot(rdb), before))
        run = _migrate(resumed, full)
        c.check("legacy-shares.resume.reruns", run.returncode == 0 and _applied(rdb), (run.stdout + run.stderr)[-600:])
        again, _ = receipt(work, resumed, full, "resumed")
        c.check("legacy-shares.resume.same-journal", again.get("journal") == dry_receipt.get("journal")
                and again.get("reconciled") is True, f"{again.get('journal')} != {dry_receipt.get('journal')}")

        # 4. Reverse, after the eligible link got its new link.
        plant_reissue(db)
        reissued, _ = receipt(work, base_data, full, "reissued")
        check_receipt(c, "reissued", reissued, 1)
        before_down = links(db)
        code, out = _migrate_down_confirmed(base_data, full)
        c.check("legacy-shares.down.exits-zero", code == 0, out[-400:])
        check_reverse(c, db, before_down)
        c.check("legacy-shares.down.logs-no-secret-or-id", secrets_in(out, planted) == 0 and ids_in(out) == 0,
                f"secrets={secrets_in(out, planted)} ids={ids_in(out)}")

        # 5. Forward again.
        run = _migrate(base_data, full)
        c.check("legacy-shares.reapply.applies", run.returncode == 0 and _applied(db), (run.stdout + run.stderr)[-600:])
        second, _ = receipt(work, base_data, full, "second-forward")
        check_receipt(c, "second-forward", second, 1)
        c.check("legacy-shares.reapply.same-journal", second.get("journal") == dry_receipt.get("journal"),
                f"{second.get('journal')} != {dry_receipt.get('journal')}")
        c.check("legacy-shares.reapply.keeps-the-new-link", links(db)[ELIGIBLE].get("replaced_by") == CAP,
                repr(links(db)[ELIGIBLE].get("replaced_by")))
        c.check("legacy-shares.reapply.no-secret-hash-or-agent-left", not left_behind(db, planted),
                repr(left_behind(db, planted)))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print(f"legacy shares check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


def _receipt_ids(got: dict) -> int:
    return ids_in(json.dumps(got))


if __name__ == "__main__":
    sys.exit(main())
