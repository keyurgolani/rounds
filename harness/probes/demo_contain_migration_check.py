"""Harness check for the demo containment migration (ROUNDS-00B-L07 stage 1).

Applies ``1700006700_demo_contain.js`` with the pinned PocketBase binary,
with no network, on a ``pb_data`` built from every migration before it.
Served once without the hooks, as a pre-upgrade database would have been,
that copy gets a legacy fixture: one row in every account-scoped
collection for the seeded demo account, for a second demo account, and
for a standard account.

1. Applying it deletes both demo accounts' share links, the views on them,
   their AI providers, and their AI settings.
2. Every other row is as it was: whatever else the demo accounts own,
   every row the standard account owns, and the users records, compared
   column by column.
3. Reversing it (``pocketbase migrate down 1``, confirmed on a pseudo
   terminal) changes no row, since it's forward-only, and applying it again
   deletes nothing more.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import factory
from admission_migration_check import MIGRATIONS, Checks, _migrate_down_confirmed
from relation_quarantine_check import PB_BIN, _env, _free_port, _migrate, _ok
from pbclient import PBClient

MIGRATION = "1700006700_demo_contain.js"
ADMIN = {"PB_ADMIN_EMAIL": "ops@harness.test", "PB_ADMIN_PASSWORD": "harness-admin-pw-123"}
CONTAINED = ("resume_share_links", "resume_share_views", "ai_providers", "ai_settings")


class Unhooked:
    """`pocketbase serve` on loopback with no hooks, as before this PR."""

    def __init__(self, work: Path, data: Path, migrations: Path) -> None:
        hooks = work / "no_hooks"
        hooks.mkdir(exist_ok=True)
        self.log = open(work / "fixture.serve.log", "w")
        port = _free_port()
        self.proc = subprocess.Popen(
            [str(PB_BIN), "serve", f"--http=127.0.0.1:{port}", f"--dir={data}", f"--migrationsDir={migrations}",
             f"--hooksDir={hooks}"], stdout=self.log, stderr=subprocess.STDOUT, env=_env())
        self.pb = PBClient(f"http://127.0.0.1:{port}")

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


def _signed_in(pb: PBClient, acct: factory.Account) -> factory.Account:
    auth = _ok(pb.auth_password(acct.email, acct.password), 200)
    acct.user_id, acct.token = auth["record"]["id"], auth["token"]
    return acct


def _fixture(pb: PBClient) -> dict[str, factory.Account]:
    admin = _ok(pb.admin_auth(ADMIN["PB_ADMIN_EMAIL"], ADMIN["PB_ADMIN_PASSWORD"]), 200)["token"]
    content = factory.ensure_content_fixtures(pb, admin)
    seeded = factory.Account(tag="seeded", email=factory._DEMO_EMAIL, password=factory._DEMO_PASSWORD)
    made = factory.make_account("demo")
    _ok(pb.create("users", admin, {"email": made.email, "password": made.password, "passwordConfirm": made.password,
                                   "is_demo": True}), 200)
    standard = factory.make_account("standard")
    _ok(pb.create("users", admin, {"email": standard.email, "password": standard.password,
                                   "passwordConfirm": standard.password}), 200)
    accounts = {"seeded": seeded, "made": made, "standard": standard}
    for acct in accounts.values():
        factory.seed_account(pb, _signed_in(pb, acct), content, admin)
    return accounts


def _owned(db: Path, accounts: dict[str, factory.Account]) -> dict[str, dict[str, dict[str, str]]]:
    """For each account and each base collection with a user field, each
    row's id and the hash of all its columns; and every users row."""
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        names = [r[0] for r in conn.execute("SELECT name FROM _collections WHERE type = 'base' ORDER BY name")]
        out: dict[str, dict[str, dict[str, str]]] = {tag: {} for tag in accounts}
        out["users"] = {}
        for name in names:
            cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{name}")')]
            if "user" not in cols:
                continue
            for tag, acct in accounts.items():
                rows = conn.execute(f'SELECT * FROM "{name}" WHERE "user" = ? ORDER BY id', (acct.user_id,)).fetchall()
                out[tag][name] = {r[0]: hashlib.sha256(json.dumps(list(r), default=str).encode()).hexdigest()
                                  for r in rows}
        for r in conn.execute('SELECT * FROM "users" ORDER BY id').fetchall():
            out["users"][r[0]] = hashlib.sha256(json.dumps(list(r), default=str).encode()).hexdigest()
    finally:
        conn.close()
    return out


def _applied(db: Path) -> bool:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return conn.execute("SELECT COUNT(*) FROM _migrations WHERE file = ?", (MIGRATION,)).fetchone()[0] == 1
    finally:
        conn.close()


def main() -> int:
    c = Checks()
    work = Path(tempfile.mkdtemp(prefix="demo-contain-check-"))
    base = work / "base_migrations"
    full = work / "migrations"
    base.mkdir()
    full.mkdir()
    for path in sorted(MIGRATIONS.glob("*.js")):
        if path.name < MIGRATION:
            shutil.copy(path, base / path.name)
            shutil.copy(path, full / path.name)
    shutil.copy(MIGRATIONS / MIGRATION, full / MIGRATION)

    data = work / "pb_data"
    db = data / "data.db"
    up = _migrate(data, base, ADMIN)
    if not c.check("demo-contain.base.applies", up.returncode == 0 and not _applied(db), up.stderr[-400:]):
        print(f"demo containment migration check: {c.passed} passed, {c.failed} failed")
        return 1
    try:
        with Unhooked(work, data, base) as pb:
            accounts = _fixture(pb)
    except Exception as err:  # noqa: BLE001 - report, never crash the phase
        c.check("demo-contain.fixture", False, str(err)[:300])
        print(f"demo containment migration check: {c.passed} passed, {c.failed} failed")
        return 1
    before = _owned(db, accounts)
    c.check("demo-contain.fixture.every-account-owns-rows-there",
            all(before[tag][name] for tag in accounts for name in CONTAINED),
            repr({tag: {n: len(before[tag][n]) for n in CONTAINED} for tag in accounts}))

    up = _migrate(data, full, ADMIN)
    after = _owned(db, accounts)
    c.check("demo-contain.applies", up.returncode == 0 and _applied(db), (up.stdout + up.stderr)[-400:])
    c.check("demo-contain.deletes-the-demo-accounts-shares-views-providers-and-settings",
            all(after[tag][name] == {} for tag in ("seeded", "made") for name in CONTAINED),
            repr({tag: {n: len(after[tag][n]) for n in CONTAINED} for tag in ("seeded", "made")}))
    kept = {tag: {n: rows for n, rows in before[tag].items() if n not in CONTAINED} for tag in ("seeded", "made")}
    c.check("demo-contain.keeps-everything-else-the-demo-accounts-own",
            all(after[tag][n] == rows for tag in kept for n, rows in kept[tag].items()),
            ", ".join(f"{tag}.{n}" for tag in kept for n, rows in kept[tag].items() if after[tag][n] != rows) or "none")
    c.check("demo-contain.the-standard-account-and-every-users-row-are-as-they-were",
            after["standard"] == before["standard"] and after["users"] == before["users"],
            ", ".join(n for n in before["standard"] if after["standard"].get(n) != before["standard"][n])
            + f" users-same={after['users'] == before['users']}")

    code, out = _migrate_down_confirmed(data, full)
    reverted = _owned(db, accounts)
    c.check("demo-contain.down-changes-no-row",
            code == 0 and MIGRATION in out and not _applied(db) and reverted == after, f"exit={code} {out[-200:]!r}")
    up = _migrate(data, full, ADMIN)
    c.check("demo-contain.again-deletes-nothing-more",
            up.returncode == 0 and _applied(db) and _owned(db, accounts) == after, (up.stdout + up.stderr)[-400:])

    print(f"demo containment migration check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
