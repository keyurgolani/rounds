"""Harness dry run of the attempt grade rules (ROUNDS-00A-L03 PR 4).

With the pinned PocketBase binary and no network, on a pb_data with every
migration but ``1700008700_attempt_grade_rules.js``, seeds and the demo
account included:

1. Plants, for two accounts and both attempt collections, an in-progress
   row, a graded row with no envelope (as clients wrote them before this
   release), and a graded row whose envelope names it back (as the server
   writes one).
2. Takes each collection's census (manifest attempt-grade-rules-v1),
   applies the migration to a copy, and takes it again. The two must be
   equal: that comparison is the reconciliation report, printed as one
   line with counts and checksums only. The new rules are the policy's,
   the ``_params`` record holds the rules they replaced, and no other
   table, row, or rule changed. On another copy, a lock the lock lever put
   on take_home_attempts before the upgrade stays: its two rules stay
   null, the other collection takes the new rules, and the record holds
   what the up step found.
3. Serves the copy on loopback with no hooks, so only the rules decide:
   each client write to a graded row, or one that would grade a row or
   give it an envelope, is refused and leaves the rows as they were, and
   the in-progress create and updates still go through.
4. ``pocketbase migrate down 1``, confirmed on a pseudo terminal as an
   operator would, keeps the rules and the record, and applying the
   migration again changes neither.
5. Serves a copy without the migration, whose two rules hash to the ones
   the manifest says it replaces, which still take an owner's graded
   write, with the execution hooks only: their record checks alone refuse
   every client write that would grade a row, change a graded row, or set
   an envelope, in each request form, and open rows still save.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import factory
import families
from admission_migration_check import MIGRATIONS, PB_BIN, RULES, Checks, _migrate_down_confirmed
from pbclient import PBClient

MIGRATION = "1700008700_attempt_grade_rules.js"
LEVERS = Path(os.environ.get("PB_LEVERS_DIR", "/pb_levers"))
HOOKS = Path(os.environ.get("PB_HOOKS_DIR", "/pb_hooks"))
# The execution hooks and the modules they load: nothing else is served
# in step 5.
EXECUTION_HOOKS = ("execution.pb.js", "execution.js", "admission.js", "gates.js")
# The lock lever as an operator copies it in, with a fresh timestamp, so
# it sorts after this migration and was applied before it.
LOCK_FILE = "1762000000_lock_take_home_attempts.js"
COLLECTIONS = ("ai_coding_attempts", "take_home_attempts")
POLICY = Path(os.environ.get("POLICY_PATH", "/policy/account-scope.v1.json"))
MANIFEST = Path(os.environ.get("PB_MANIFESTS_DIR", "/pb_manifests")) / "attempt-grade-rules-v1.json"
STAMP = "2026-11-01 00:00:00.000Z"
# What the attempt rows hang off: one seeded round and assignment.
PARENT = {"ai_coding_attempts": ("round", "ai_coding_rounds"),
          "take_home_attempts": ("assignment", "take_home_assignments")}
# A field each collection takes on an update that changes nothing else.
EDIT = {"ai_coding_attempts": {"current_checkpoint": 1}, "take_home_attempts": {"notes": "edited"}}


def rid(tag: str) -> str:
    out = ("gr" + tag).ljust(15, "0")
    assert len(out) == 15 and out.isalnum() and out.islower(), tag
    return out


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    return {"PATH": "/usr/bin:/bin", **(extra or {})}


def _migrate(data: Path, migrations: Path, extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([str(PB_BIN), "migrate", "up", f"--dir={data}", f"--migrationsDir={migrations}"],
                          capture_output=True, text=True, timeout=300, env=_env(extra))


def _ro(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _insert(conn: sqlite3.Connection, table: str, **cols: object) -> None:
    cols.setdefault("created", STAMP)
    cols.setdefault("updated", STAMP)
    names = ", ".join(f'"{k}"' for k in cols)
    conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({", ".join("?" for _ in cols)})', list(cols.values()))


def seed(db: Path) -> dict[str, str]:
    """The fixture rows; answers one envelope id for the served checks.
    The seeds hold no take-home assignment, so the fixture plants one for
    its attempts to hang off, as it does any parent the seeds lack."""
    conn = sqlite3.connect(str(db))
    try:
        parents = {}
        for collection, (field, table) in PARENT.items():
            found = conn.execute(f'SELECT id FROM "{table}" ORDER BY id LIMIT 1').fetchone()
            if found is None and table == "take_home_assignments":
                _insert(conn, table, id=rid("thparent"), slug="grade-rules-fixture", title="Fixture",
                        language="python", entrypoint="main.py", ai_policy="off")
                found = (rid("thparent"),)
            if found is None:
                raise RuntimeError(f"no {table} row to hang the fixture's attempts off")
            parents[collection] = (field, found[0])
        for tag in ("a", "b"):
            user = rid(f"user{tag}")
            _insert(conn, "users", id=user, username=f"gr{tag}user", email=f"gr-{tag}@harness.invalid",
                    tokenKey=secrets.token_hex(16), passwordHash="x")
            for short, collection in (("ai", "ai_coding_attempts"), ("th", "take_home_attempts")):
                field, parent = parents[collection]
                _insert(conn, collection, id=rid(f"{short}{tag}progress"), user=user, status="in-progress",
                        **{field: parent})
                _insert(conn, collection, id=rid(f"{short}{tag}legacy"), user=user, status="graded",
                        **{field: parent})
                row, envelope = rid(f"{short}{tag}server"), rid(f"{short}{tag}envelope")
                _insert(conn, "execution_envelopes", id=envelope, user=user, job=rid(f"{short}{tag}job"),
                        attempt=rid(f"{short}{tag}attempt"), version="rounds.execution-envelope/v1",
                        state="completed", outcome_class="passed", authoritative=True, user_view="{}",
                        graded_collection=collection, graded_row=row)
                _insert(conn, collection, id=row, user=user, status="graded", envelope=envelope, **{field: parent})
        conn.commit()
    finally:
        conn.close()
    return {"envelope": rid("aiaenvelope")}


def census(db: Path, collection: str) -> dict:
    """The manifest's census of one collection: its counts, and a checksum
    over every row. Never a row's content."""
    conn = _ro(db)
    try:
        rows = [dict(r) for r in conn.execute(f'SELECT * FROM "{collection}" ORDER BY id')]
        envelopes = {r["id"]: (r["user"], r["graded_collection"], r["graded_row"])
                     for r in conn.execute("SELECT id, user, graded_collection, graded_row FROM execution_envelopes")}
    finally:
        conn.close()
    graded = [r for r in rows if r["status"] == "graded"]
    server = [r for r in graded if r["envelope"] and envelopes.get(r["envelope"]) == (r["user"], collection, r["id"])]
    text = json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str)
    return {"rows": len(rows), "in_progress": sum(r["status"] == "in-progress" for r in rows),
            "submitted": sum(r["status"] == "submitted" for r in rows), "graded": len(graded),
            "server_written": len(server), "legacy_client_written": len(graded) - len(server),
            "checksum": hashlib.sha256(text.encode()).hexdigest()}


def _rules(db: Path) -> dict[str, dict[str, str | None]]:
    conn = _ro(db)
    try:
        return {r["name"]: {rule: r[rule] for rule in RULES}
                for r in conn.execute(f"SELECT name, {', '.join(RULES)} FROM _collections")}
    finally:
        conn.close()


def _tables(db: Path) -> dict[str, tuple[int, str]]:
    """Each table's row count and content hash, but the three a migration
    writes its own record and rules to."""
    conn = _ro(db)
    try:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        out = {}
        for name in names:
            if name in ("_collections", "_migrations", "_params"):
                continue
            rows = [tuple(r) for r in conn.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
            out[name] = (len(rows), hashlib.sha256(repr(rows).encode()).hexdigest())
        return out
    finally:
        conn.close()


def _collections_but_the_two_rules(db: Path) -> dict[str, tuple]:
    conn = _ro(db)
    try:
        out = {}
        for r in conn.execute("SELECT * FROM _collections ORDER BY name"):
            row = dict(r)
            row.pop("updated", None)
            if row["name"] in COLLECTIONS:
                row.pop("createRule")
                row.pop("updateRule")
            out[row["name"]] = tuple(sorted(row.items()))
        return out
    finally:
        conn.close()


def _record(db: Path) -> object:
    conn = _ro(db)
    try:
        row = conn.execute("SELECT value FROM _params WHERE key = ?", (MIGRATION,)).fetchone()
    finally:
        conn.close()
    return None if row is None else json.loads(row[0])


def _applied(db: Path) -> bool:
    conn = _ro(db)
    try:
        return conn.execute("SELECT COUNT(*) FROM _migrations WHERE file = ?", (MIGRATION,)).fetchone()[0] == 1
    finally:
        conn.close()


def check_a_lock_is_kept(c: Checks, work: Path, base_data: Path, base: Path, full: Path,
                         base_rules: dict, want: dict) -> None:
    """The lock lever on take_home_attempts before the upgrade, then the
    upgrade, on a copy of its own."""
    lever = (LEVERS / "lock_collection.template.js").read_text().replace("__COLLECTION__", "take_home_attempts")
    locked_base, locked_full = work / "locked_base_migrations", work / "locked_migrations"
    shutil.copytree(base, locked_base)
    shutil.copytree(full, locked_full)
    for folder in (locked_base, locked_full):
        (folder / LOCK_FILE).write_text(lever)
    data = work / "locked_pb_data"
    shutil.copytree(base_data, data)
    db = data / "data.db"
    lock = _migrate(data, locked_base)
    held = _rules(db)["take_home_attempts"]
    up = _migrate(data, locked_full)
    rules = _rules(db)
    other = "ai_coding_attempts"
    found = [{"collection": other, "create": base_rules[other]["createRule"],
              "update": base_rules[other]["updateRule"]},
             {"collection": "take_home_attempts", "create": None, "update": None}]
    kept = (held["createRule"], held["updateRule"]) == (None, None) and rules["take_home_attempts"] == held
    c.check("grade-rules.a-locked-collection-keeps-its-lock",
            lock.returncode == 0 and up.returncode == 0 and _applied(db) and kept
            and rules[other] == want[other] and _record(db) == found,
            f"lock={lock.returncode} up={up.returncode} kept={kept} other={rules[other] == want[other]} "
            f"record={_record(db) == found}")


# -- PocketBase served on loopback, with no hooks ------------------------------------

def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Served:
    def __init__(self, work: Path, data: Path, migrations: Path, hooks: Path | None = None) -> None:
        if hooks is None:
            hooks = work / "no_hooks"
            hooks.mkdir(exist_ok=True)
        self.port = _free_port()
        self.log = open(work / f"served-{hooks.name}.log", "w")
        self.proc = subprocess.Popen(
            [str(PB_BIN), "serve", f"--http=127.0.0.1:{self.port}", f"--dir={data}",
             f"--migrationsDir={migrations}", f"--hooksDir={hooks}", "--hooksWatch=false"],
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


def _count(pb: PBClient, collection: str, admin: str, owner: str) -> int | None:
    resp = pb.listing(collection, token=admin, params={"filter": f'user = "{owner}"'})
    body = resp.body if isinstance(resp.body, dict) else {}
    total = body.get("totalItems")
    return total if resp.status == 200 and isinstance(total, int) else None


def check_client_writes(c: Checks, pb: PBClient, admin: str, envelope: str, parents: dict[str, str]) -> None:
    acct = factory.make_account("grade")
    factory.register(pb, acct)
    tok, uid = acct.token, acct.user_id
    for collection in COLLECTIONS:
        field = PARENT[collection][0]
        base = {"user": uid, field: parents[collection]}
        own = pb.create(collection, tok, {**base, "status": "in-progress"})
        row = own.body.get("id", "") if own.status == 200 and isinstance(own.body, dict) else ""
        c.check(f"grade-rules.{collection}.in-progress-create-saves", bool(row), f"status={own.status}")
        edits = [pb.update(collection, row, body, token=tok)
                 for body in ({}, EDIT[collection], {"user": uid}, {"status": "in-progress"})]
        c.check(f"grade-rules.{collection}.in-progress-updates-save", all(r.status == 200 for r in edits),
                f"statuses={[r.status for r in edits]}")

        before = _count(pb, collection, admin, uid)
        creates = [pb.create(collection, tok, body) for body in
                   ({**base, "status": "graded"}, {**base, "status": ["graded"]},
                    {**base, "status": "in-progress", "envelope": envelope})]
        after = _count(pb, collection, admin, uid)
        c.check(f"grade-rules.{collection}.graded-or-enveloped-create-refused",
                all(r.status == 400 for r in creates) and before is not None and after == before,
                f"statuses={[r.status for r in creates]} rows={before}->{after}")

        server = pb.create(collection, admin, {**base, "status": "graded"})
        graded = server.body.get("id", "") if server.status == 200 and isinstance(server.body, dict) else ""
        tries = [(graded, {}), (graded, {"status": "in-progress"}), (graded, EDIT[collection]),
                 (row, {"status": "graded"}), (row, {"status": ["graded"]}), (row, {"envelope": envelope})]
        seen = {r: pb.view(collection, r, token=admin).body for r in (graded, row)}
        answers = [pb.update(collection, r, body, token=tok) for r, body in tries]
        unchanged = all(pb.view(collection, r, token=admin).body == seen[r] for r in (graded, row))
        c.check(f"grade-rules.{collection}.graded-row-and-grading-updates-refused",
                bool(graded) and all(a.status in (400, 404) for a in answers) and unchanged,
                f"graded={bool(graded)} statuses={[a.status for a in answers]} unchanged={unchanged}")


def holds_the_rules_before(db: Path, manifest: dict) -> tuple[bool, str]:
    """Whether both collections' create and update rules on ``db`` hash to
    the manifest's record of the rules this migration replaces."""
    rules = _rules(db)
    differ = []
    for name in COLLECTIONS:
        for key, field in (("create", "createRule"), ("update", "updateRule")):
            text = rules.get(name, {}).get(field)
            want = manifest["collections"][name]["before"][f"{key}_sha256"]
            if not isinstance(text, str) or hashlib.sha256(text.encode()).hexdigest() != want:
                differ.append(f"{name}.{key}")
    return not differ, "rules differ: " + ", ".join(differ)


def check_the_guards_alone(c: Checks, pb: PBClient, admin: str, envelope: str, parents: dict[str, str]) -> None:
    acct = factory.make_account("guard")
    factory.register(pb, acct)
    tok, uid = acct.token, acct.user_id
    for collection in COLLECTIONS:
        field = PARENT[collection][0]
        open_row = {"user": uid, field: parents[collection], "status": "in-progress"}
        own = pb.create(collection, tok, open_row)
        row = own.body.get("id", "") if own.status == 200 and isinstance(own.body, dict) else ""
        edits = [pb.update(collection, row, body, token=tok) for body in (EDIT[collection], {"status": "submitted"})]
        c.check(f"grade-rules.guards.{collection}.open-rows-still-save",
                bool(row) and all(r.status == 200 for r in edits), f"create={own.status} "
                f"updates={[r.status for r in edits]}")

        plain = [("plain", pb.create(collection, tok, {**open_row, "status": "graded"})),
                 ("envelope", pb.create(collection, tok, {**open_row, "envelope": envelope}))]
        sent = plain + families.graded_create_forms(pb, collection, tok, open_row, envelope)
        landed = families.graded_or_enveloped(pb, collection, admin, uid)
        c.check(f"grade-rules.guards.{collection}.no-client-create-is-graded-or-linked", landed == 0,
                f"landed={landed} " + " ".join(f"{form}={r.status}" for form, r in sent))

        server = pb.create(collection, admin, {**open_row, "status": "graded"})
        graded = server.body.get("id", "") if server.status == 200 and isinstance(server.body, dict) else ""
        seen = pb.view(collection, graded, token=admin)
        plain = [(f"graded:{i}", pb.update(collection, graded, body, token=tok))
                 for i, body in enumerate(({}, {"status": "in-progress"}, EDIT[collection]))]
        plain += [("open:plain", pb.update(collection, row, {"status": "graded"}, token=tok)),
                  ("open:envelope", pb.update(collection, row, {"envelope": envelope}, token=tok))]
        sent = plain + families.graded_update_forms(pb, collection, tok, graded, row, envelope)
        kept = pb.view(collection, graded, token=admin)
        ok = (bool(graded) and seen.status == 200 and kept.status == 200 and kept.body == seen.body
              and families.still_open(pb, collection, admin, row))
        c.check(f"grade-rules.guards.{collection}.no-client-update-grades-a-row-or-changes-a-graded-one", ok,
                f"graded={bool(graded)} " + " ".join(f"{form}={r.status}" for form, r in sent))


def main() -> int:
    c = Checks()
    work = Path(tempfile.mkdtemp(prefix="grade-rules-check-"))
    try:
        base = work / "base_migrations"
        full = work / "migrations"
        base.mkdir()
        full.mkdir()
        for path in sorted(MIGRATIONS.glob("*.js")):
            shutil.copy(path, full / path.name)
            if path.name != MIGRATION:
                shutil.copy(path, base / path.name)
        # Generated per run, never printed: the bootstrap migration makes
        # this superuser on the fresh pb_data.
        admin_env = {"PB_ADMIN_EMAIL": f"gr-admin-{secrets.token_hex(4)}@harness.invalid",
                     "PB_ADMIN_PASSWORD": "Hx" + secrets.token_hex(16)}
        base_data = work / "base_pb_data"
        up = _migrate(base_data, base, admin_env)
        if not c.check("grade-rules.base.applies", up.returncode == 0, (up.stdout + up.stderr)[-400:]):
            print(f"grade rules migration check: {c.passed} passed, {c.failed} failed")
            return 1
        envelope = seed(base_data / "data.db")["envelope"]
        base_db = base_data / "data.db"
        before = {name: census(base_db, name) for name in COLLECTIONS}
        manifest = json.loads(MANIFEST.read_text())
        expected = manifest["harness_fixture"]["expected"]
        c.check("grade-rules.fixture.is-the-manifests",
                all({k: v for k, v in before[n].items() if k != "checksum"} == expected for n in COLLECTIONS),
                json.dumps({n: {k: v for k, v in before[n].items() if k != "checksum"} for n in COLLECTIONS}))

        data = work / "pb_data"
        shutil.copytree(base_data, data)
        db = data / "data.db"
        up = _migrate(data, full)
        c.check("grade-rules.applies", up.returncode == 0 and _applied(db), (up.stdout + up.stderr)[-400:])
        after = {name: census(db, name) for name in COLLECTIONS}
        print(json.dumps({"report": "grade-rules.reconciliation", "manifest": manifest["manifest"],
                          "before": before, "after": after, "equal": before == after}, sort_keys=True))
        c.check("grade-rules.reconciles", before == after, "the census changed")

        policy = json.loads(POLICY.read_text())
        rules, base_rules = _rules(db), _rules(base_db)
        want = {n: {**base_rules[n], "createRule": policy["collections"][n]["current_rules"]["create"],
                    "updateRule": policy["collections"][n]["current_rules"]["update"]} for n in COLLECTIONS}
        c.check("grade-rules.rules-are-the-policys", {n: rules[n] for n in COLLECTIONS} == want,
                "rules differ: " + ", ".join(n for n in COLLECTIONS if rules[n] != want[n]))
        replaced = [{"collection": n, "create": base_rules[n]["createRule"], "update": base_rules[n]["updateRule"]}
                    for n in COLLECTIONS]
        c.check("grade-rules.records-the-rules-it-replaced", _record(db) == replaced, "record differs")
        c.check("grade-rules.touches-nothing-else",
                _tables(db) == _tables(base_db)
                and _collections_but_the_two_rules(db) == _collections_but_the_two_rules(base_db),
                "a table or another rule changed")
        check_a_lock_is_kept(c, work, base_data, base, full, base_rules, want)

        parents = {}
        conn = _ro(base_db)
        try:
            for collection, (_field, table) in PARENT.items():
                parents[collection] = conn.execute(f'SELECT id FROM "{table}" ORDER BY id LIMIT 1').fetchone()[0]
        finally:
            conn.close()
        try:
            with Served(work, data, full) as pb:
                auth = pb.admin_auth(admin_env["PB_ADMIN_EMAIL"], admin_env["PB_ADMIN_PASSWORD"])
                admin = auth.body.get("token", "") if isinstance(auth.body, dict) else ""
                if c.check("grade-rules.served.superuser", auth.status == 200 and bool(admin), f"status={auth.status}"):
                    check_client_writes(c, pb, admin, envelope, parents)
        except Exception as err:  # noqa: BLE001 - report, never crash the phase
            c.check("grade-rules.served-copy", False, str(err)[:300])

        # Step 5, on a copy of its own, before the down step.
        guarded = work / "guarded_pb_data"
        shutil.copytree(base_data, guarded)
        hooks = work / "execution_hooks"
        hooks.mkdir()
        for name in EXECUTION_HOOKS:
            shutil.copy(HOOKS / name, hooks / name)
        held, why = holds_the_rules_before(guarded / "data.db", manifest)
        if c.check("grade-rules.guards.copy-holds-the-rules-before-this-migration", held, why):
            try:
                with Served(work, guarded, base, hooks) as pb:
                    auth = pb.admin_auth(admin_env["PB_ADMIN_EMAIL"], admin_env["PB_ADMIN_PASSWORD"])
                    admin = auth.body.get("token", "") if isinstance(auth.body, dict) else ""
                    if c.check("grade-rules.guards.superuser", auth.status == 200 and bool(admin),
                               f"status={auth.status}"):
                        check_the_guards_alone(c, pb, admin, envelope, parents)
            except Exception as err:  # noqa: BLE001 - report, never crash the phase
                c.check("grade-rules.guards-copy", False, str(err)[:300])

        kept_rules, kept_record = _rules(db), _record(db)
        code, out = _migrate_down_confirmed(data, full)
        c.check("grade-rules.down-keeps-the-rules-and-the-record",
                code == 0 and not _applied(db) and _rules(db) == kept_rules and _record(db) == kept_record,
                f"exit={code} {out[-300:]!r}")
        up = _migrate(data, full)
        c.check("grade-rules.reapplies-without-a-change",
                up.returncode == 0 and _applied(db) and _rules(db) == kept_rules and _record(db) == kept_record,
                (up.stdout + up.stderr)[-400:])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"grade rules migration check: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
