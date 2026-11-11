"""Harness check for the demo containment migration (ROUNDS-00B-L07 stage 1).

Applies ``1700006700_demo_contain.js`` with the pinned PocketBase binary,
with no network, in upgrade order: on a ``pb_data`` built from every
migration before it, as an upgrade from ``62d4eae`` applies it. Served once
without the hooks, as a pre-upgrade database would have been, that copy
gets a legacy fixture: one row in every account-scoped collection it has
for the seeded demo account, for a second demo account, and for a standard
account, plus a provider of the second demo account that the standard
account's AI settings point at.

1. Applying it deletes both demo accounts' share links, the views on them,
   their AI settings, and their AI providers, except the one the standard
   account points at, which keeps its row with its stored key cleared.
2. Every other row is as it was: whatever else the demo accounts own,
   every row the standard account owns (its settings included), and the
   users records, compared column by column.
3. Reversing it (``pocketbase migrate down 1``, confirmed on a pseudo
   terminal) changes no row, since it's forward-only, and applying it again
   changes nothing more.
4. A fresh ``pb_data`` served with every migration and the hooks, the demo
   at its default: the first start logs ``demo_lock`` ``not_ready`` (start
   hooks run before migrations), the published password then gets the
   wrong-password answer, and the next start locks the demo account.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import factory
from admission_migration_check import MIGRATIONS, Checks, _migrate_down_confirmed
from relation_quarantine_check import PB_BIN, Served, _env, _events, _free_port, _migrate, _ok
from pbclient import PBClient

MIGRATION = "1700006700_demo_contain.js"
ADMIN = {"PB_ADMIN_EMAIL": "ops@harness.test", "PB_ADMIN_PASSWORD": "harness-admin-pw-123"}
CONTAINED = ("resume_share_links", "resume_share_views", "ai_providers", "ai_settings")
# A stand-in for a stored key, never a real one.
KEY_FIELDS = {"encrypted_key": "harness-ciphertext-placeholder", "key_iv": "harness-iv-placeholder"}


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


def _collections(db: Path) -> set[str]:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return {r[0] for r in conn.execute("SELECT name FROM _collections")}
    finally:
        conn.close()


def _fixture(pb: PBClient, collections: set[str]) -> tuple[dict[str, factory.Account], str]:
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
        factory.seed_account(pb, _signed_in(pb, acct), content, admin, collections)
    for tag in ("seeded", "made"):
        _ok(pb.update("ai_providers", accounts[tag].ids["ai_providers"], KEY_FIELDS, admin), 200)
    # A legacy cross-account reference, which only a database from before
    # 1700007000 can hold: the standard account's settings name a demo
    # account's provider.
    pointed = _ok(pb.create("ai_providers", admin, {"user": made.user_id, "kind": "openai", "label": "pointed",
                                                    **KEY_FIELDS}), 200)["id"]
    _ok(pb.update("ai_settings", standard.ids["ai_settings"], {"text_provider": pointed}, admin), 200)
    return accounts, pointed


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


def _provider(db: Path, rec_id: str) -> dict | None:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute('SELECT * FROM "ai_providers" WHERE id = ?', (rec_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _wrong_password() -> str:
    return "Wrong" + secrets.token_hex(12) + "!1"


def check_fresh_boot(c: Checks, work: Path, migrations: Path) -> None:
    """A new install with the demo at its default, served with the hooks."""
    data = work / "fresh_pb_data"
    try:
        with Served(work, data, migrations, "fresh") as pb:
            right = pb.auth_password(factory._DEMO_EMAIL, factory._DEMO_PASSWORD)
            wrong = pb.auth_password(factory._DEMO_EMAIL, _wrong_password())
        first = _events((work / "fresh.serve.log").read_text(), "demo_lock")
        with Served(work, data, migrations, "restart") as pb:
            again = pb.auth_password(factory._DEMO_EMAIL, factory._DEMO_PASSWORD)
        second = _events((work / "restart.serve.log").read_text(), "demo_lock")
    except Exception as err:  # noqa: BLE001 - report, never crash the phase
        c.check("demo-contain.fresh-boot", False, str(err)[:300])
        return
    c.check("demo-contain.fresh-boot.first-start-is-not-ready",
            [(e.get("demo"), e.get("code")) for e in first] == [("disabled", "not_ready")], repr(first))
    c.check("demo-contain.fresh-boot.the-published-password-fails-as-a-wrong-password",
            right.status == 400 and (right.status, right.body) == (wrong.status, wrong.body),
            f"status={right.status} same-as-wrong={(right.status, right.body) == (wrong.status, wrong.body)}")
    c.check("demo-contain.fresh-boot.the-next-start-locks-it",
            [(e.get("demo"), e.get("locked"), e.get("failed")) for e in second] == [("disabled", 1, 0)]
            and again.status == 400, f"{second!r} status={again.status}")


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
    upto = work / "migrations"
    every = work / "all_migrations"
    for folder in (base, upto, every):
        folder.mkdir()
    # Upgrade order: what came before it, then it.
    for path in sorted(MIGRATIONS.glob("*.js")):
        if path.name < MIGRATION:
            shutil.copy(path, base / path.name)
            shutil.copy(path, upto / path.name)
        shutil.copy(path, every / path.name)
    shutil.copy(MIGRATIONS / MIGRATION, upto / MIGRATION)

    data = work / "pb_data"
    db = data / "data.db"
    up = _migrate(data, base, ADMIN)
    if not c.check("demo-contain.base.applies", up.returncode == 0 and not _applied(db), up.stderr[-400:]):
        print(f"demo containment migration check: {c.passed} passed, {c.failed} failed")
        return 1
    try:
        with Unhooked(work, data, base) as pb:
            accounts, pointed = _fixture(pb, _collections(db))
    except Exception as err:  # noqa: BLE001 - report, never crash the phase
        c.check("demo-contain.fixture", False, str(err)[:300])
        print(f"demo containment migration check: {c.passed} passed, {c.failed} failed")
        return 1
    before = _owned(db, accounts)
    c.check("demo-contain.fixture.every-account-owns-rows-there",
            all(before[tag][name] for tag in accounts for name in CONTAINED)
            and pointed in before["made"]["ai_providers"],
            repr({tag: {n: len(before[tag][n]) for n in CONTAINED} for tag in accounts}))

    up = _migrate(data, upto, ADMIN)
    after = _owned(db, accounts)
    kept_provider = _provider(db, pointed) or {}
    c.check("demo-contain.applies", up.returncode == 0 and _applied(db), (up.stdout + up.stderr)[-400:])
    left = {tag: {n: sorted(after[tag][n]) for n in CONTAINED} for tag in ("seeded", "made")}
    c.check("demo-contain.deletes-the-demo-accounts-shares-views-settings-and-providers",
            all(rows == ([pointed] if (tag, n) == ("made", "ai_providers") else [])
                for tag in left for n, rows in left[tag].items()),
            repr({tag: {n: len(rows) for n, rows in left[tag].items()} for tag in left}))
    c.check("demo-contain.a-demo-provider-another-account-points-at-keeps-its-row-without-its-key",
            bool(kept_provider) and all(kept_provider.get(k) in ("", None) for k in KEY_FIELDS)
            and kept_provider.get("label") == "pointed",
            "row kept" if kept_provider else "row gone")
    kept = {tag: {n: rows for n, rows in before[tag].items() if n not in CONTAINED} for tag in ("seeded", "made")}
    c.check("demo-contain.keeps-everything-else-the-demo-accounts-own",
            all(after[tag][n] == rows for tag in kept for n, rows in kept[tag].items()),
            ", ".join(f"{tag}.{n}" for tag in kept for n, rows in kept[tag].items() if after[tag][n] != rows) or "none")
    c.check("demo-contain.the-standard-account-and-every-users-row-are-as-they-were",
            after["standard"] == before["standard"] and after["users"] == before["users"],
            ", ".join(n for n in before["standard"] if after["standard"].get(n) != before["standard"][n])
            + f" users-same={after['users'] == before['users']}")

    code, out = _migrate_down_confirmed(data, upto)
    reverted = _owned(db, accounts)
    c.check("demo-contain.down-changes-no-row",
            code == 0 and MIGRATION in out and not _applied(db) and reverted == after, f"exit={code} {out[-200:]!r}")
    up = _migrate(data, upto, ADMIN)
    c.check("demo-contain.again-changes-nothing-more",
            up.returncode == 0 and _applied(db) and _owned(db, accounts) == after, (up.stdout + up.stderr)[-400:])

    check_fresh_boot(c, work, every)

    print(f"demo containment migration check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
