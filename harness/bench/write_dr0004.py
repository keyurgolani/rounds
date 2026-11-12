"""Writes DR-0004's record (ROUNDS-02-L01),
docs/decisions/DR-0004-canonical-database.json, from the text below, the
numbers in the benchmark receipt, and code facts counted on the tree. Run it
from the repository root, then render the ADR:

    python harness/bench/write_dr0004.py [receipt.json]
    node scripts/conformance/run.mjs --write

With no receipt the numbers read "pending", which the rule rejects, so a
draft without a receipt never passes. The counts are labeled with the commit
of next whose files they counted, and the script stops if the counted files
differ from that commit. Like the rest of harness/bench/, it ships nowhere."""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "contracts/database/benchmark.json"
OUT = ROOT / "docs/decisions/DR-0004-canonical-database.json"
DOCKERFILE = ROOT / "pocketbase/Dockerfile"
HOOKS = ROOT / "pocketbase/pb_hooks"
MIGRATIONS = ROOT / "pocketbase/pb_migrations"
RUNNER = {"ai.py": ROOT / "backend/routers/ai.py", "take_home.py": ROOT / "backend/routers/take_home.py"}
COUNTED_PATHS = ["pocketbase/pb_hooks", "pocketbase/pb_migrations", "backend/routers/ai.py", "backend/routers/take_home.py"]

rc = json.loads(RECEIPT.read_text()) if RECEIPT.exists() else None
_pin = re.search(r"^ARG PB_VERSION=(\d+\.\d+\.\d+)$", DOCKERFILE.read_text(), re.M)
if not _pin:
    raise SystemExit("pocketbase/Dockerfile has no ARG PB_VERSION=<x.y.z>")
PIN = _pin.group(1)
LINE = ".".join(PIN.split(".")[:2])
BENCH_VERSION = (rc or {}).get("profile", {}).get("pocketbase", {}).get("version") or "pending"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--no-optional-locks", *args], cwd=ROOT, capture_output=True, text=True)


def counted_at() -> str:
    """The commit of next this branch carries, if the counted files match it."""
    base = git("merge-base", "HEAD", "origin/next")
    if base.returncode != 0:
        raise SystemExit(f"can't find next's commit: {base.stderr.strip()}")
    sha = base.stdout.strip()
    if git("diff", "--quiet", sha, "--", *COUNTED_PATHS).returncode != 0:
        raise SystemExit(f"the counted files differ from next's {sha[:7]}; count them at a commit of next")
    return sha


COUNTED_AT = counted_at()


def count(paths: list[Path], pattern: str) -> tuple[int, list[str]]:
    rx = re.compile(pattern)
    per = {p: len(rx.findall(p.read_text())) for p in paths}
    return sum(per.values()), sorted(p.name for p, n in per.items() if n)


TOP = sorted(HOOKS.glob("*.pb.js"))
LIBS = sorted(p for p in HOOKS.glob("*.js") if not p.name.endswith(".pb.js"))
MIGS = sorted(MIGRATIONS.glob("*.js"))
F = {
    "pbjs": len(TOP),
    "routes": count(TOP, r"\brouterAdd\(")[0],
    "routerUse": count(TOP, r"\brouterUse\(")[0],
    "cron": count(TOP, r"\bcronAdd\(")[0],
    "boot": count(TOP, r"\bonAfterBootstrap\(")[0],
    "modelHooks": count(TOP, r"\bon(?:Record|Model)\w*\(")[0],
    "cli": count(TOP, r"rootCmd\.addCommand\(")[0],
    "guards": count(TOP, r"\bonRecordBeforeAuthWith\w+Request\("),
    "dao": count(TOP + LIBS, r"\$app\.dao\(\)"),
    "tx": count(LIBS, r"\brunInTransaction\("),
    "admin": count(LIBS, r"\.admin\b"),
    "migrations": len(MIGS),
    "newDao": sum("new Dao(" in p.read_text() for p in MIGS),
    "triggers": sum(bool(re.search(r"CREATE TRIGGER", p.read_text(), re.I)) for p in MIGS),
    "indexes": sum(bool(re.search(r"CREATE (UNIQUE )?INDEX", p.read_text(), re.I)) for p in MIGS),
    "requestData": [p.name for p in MIGS if "@request.data" in p.read_text()],
    # The runner's REST writes with the caller's token: calls, not the helper's definition.
    "runner": {k: count([p], r"(?<!def )\b(?:pb_post|pb_patch|_delete_pb)\(")[0] for k, p in RUNNER.items()},
}
F["registrations"] = F["routes"] + F["routerUse"] + F["cron"] + F["boot"] + F["modelHooks"] + F["cli"]
F["runnerWrites"] = sum(F["runner"].values())
# #3's PR 4 checks the execution keys first in both take-home routes, so the
# runner's in-request take-home writes can't run.
_take_home = RUNNER["take_home.py"].read_text()
TAKE_HOME_GATED = all(f'keys.require_on("{r}")' in _take_home for r in ("take_home_run", "take_home_submit"))
# Which binary made the schema snapshot; the record says so (DB9).
SNAP_VERSION = json.loads((ROOT / "contracts/database/schema-snapshot.json").read_text())["pocketbaseVersion"]
if F["newDao"] != F["migrations"]:
    raise SystemExit(f"{F['migrations'] - F['newDao']} migrations don't call new Dao(; the version analysis assumes they all do")
AT = COUNTED_AT[:7]


def scale(n: str) -> dict:
    return ((rc or {}).get("scales") or {}).get(n) or {}


def get(d: dict, *path, default=None):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return default
        d = d[p]
    return d


def ms(v) -> str:
    if v is None:
        return "pending"
    if v >= 1000:
        return f"{v / 1000:.1f} s"
    return f"{v:.0f} ms" if v >= 10 or v == int(v) else f"{v:.1f} ms"


def mib(v) -> str:
    return "pending" if not v else f"{v / 1024 ** 2:.0f} MiB"


def target(tid: str) -> dict:
    return next((t for t in (rc or {}).get("targets", []) if t["id"] == tid), {})


S1, S10 = scale("1"), scale("10")


def sweep(sc: dict) -> list[tuple[int, int]]:
    return sorted((int(c), round(x.get("perSecond") or 0)) for c, x in (sc.get("sweep") or {}).items())


def series(items: list[str]) -> str:
    """a, b, and c."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])}{',' if len(items) > 2 else ''} and {items[-1]}"


SWEEP10 = sweep(S10)
peak = max((r for _, r in SWEEP10), default=None)
peak1 = max((r for _, r in sweep(S1)), default=None)
by_clients = series([f"{r} with {c} client{'s' if c != 1 else ''}" if i == 0 else f"{r} with {c}" for i, (c, r) in enumerate(SWEEP10)]) if SWEEP10 else "pending"
hold99 = get(S10, "steady", "holdMs", "p99")
hold50 = get(S10, "steady", "holdMs", "p50")
queue99 = get(S10, "steady", "queueMs", "p99")
amp = get(S10, "steady", "writeAmplification")
lag95 = get(S10, "steady", "relayLagMs", "p95")
lag999 = get(S10, "steady", "relayLagMs", "p999")
ryw99 = get(S10, "steady", "readYourWritesMs", "p99")
wal = get(S10, "samplers", "walMaxBytes")
rss = max(get(S1, "samplers", "rssMaxBytes", default=0) or 0, get(S10, "samplers", "rssMaxBytes", default=0) or 0) or None
db1 = S1.get("databaseBytes")
db10 = S10.get("databaseBytes")
freeze10 = get(S10, "freeze", "seconds")
accounts10 = S10.get("accounts") or 10
freeze_per_account = (freeze10 / accounts10) if freeze10 else None
freeze_accounts = math.floor(900 / freeze_per_account) if freeze_per_account else None
batch99 = get(S10, "freeze", "transfer", "batchHoldMs", "p99")
schema_s = get(S10, "schemaChange", "downtimeSeconds")
tar_down = get(S10, "stopAndTar", "downtimeSeconds")
pragmas = get(S10, "pragmas", "write") or {}
restore = target("restore_rto")
result = (rc or {}).get("result", "pending")
checkpoint = get(S10, "steady", "checkpoint") or {}
steady_failed = sum(n for s, n in (get(S10, "steady", "statuses") or {}).items() if s not in ("200", "409"))


def backup(sc: dict, method: str) -> dict:
    return next((b for b in sc.get("backups", []) if b.get("method") == method), {})


def restore_of(sc: dict, method: str) -> dict:
    return next((r for r in sc.get("restores", []) if r.get("method") == method), {})


zip10 = backup(S10, "pocketbase-backup-api")
vac10 = backup(S10, "vacuum-into")
ext10 = backup(S10, "sqlite-backup-api")
per_account_db = (db10 / 10) if db10 else None
_ex = next((e for e in (rc or {}).get("extrapolations") or [] if e.get("target") == "restore_rto"), {})
copy_rate = f"{_ex['throughputBytesPerSecond'] / 1000 ** 2:.0f} MB/s" if _ex.get("throughputBytesPerSecond") else "pending"
gb = lambda b: "pending" if not b else f"{b / 1000 ** 3:.2f} GB"  # noqa: E731

# The target closest to its limit, if one is; rpo_zero has no headroom to compare.
_ratios = {t["id"]: t["value"] / t["limit"] for t in (rc or {}).get("targets", []) if t.get("limit") and t.get("value") is not None}
CLOSEST = max(_ratios, key=_ratios.get) if _ratios else None

LEAVES = {
    "gateway": "ROUNDS-02-L02", "versions": "ROUNDS-02-L03", "history": "ROUNDS-02-L04", "outbox": "ROUNDS-02-L05",
    "projectors": "ROUNDS-02-L06", "backup": "ROUNDS-32-L03", "bytes": "ROUNDS-10-L01", "keyring": "ROUNDS-14-L02", "purge": "ROUNDS-14-L05",
}
BEST_CASE = "a best case for the shipped limit (DB1)"

record = {
    "$schema": "./decision-record.schema.json",
    "id": "DR-0004",
    "title": "Canonical database and transaction owner",
    "leaf": "ROUNDS-02-L01",
    "status": "draft",
    "owner": "Domain Platform",
    "approver": "",
    "approvalRef": None,
    "compatibility": "additive",
    "revision": 1,
    "supersedes": None,
    "consumers": sorted({
        "ROUNDS-02-L02", "ROUNDS-02-L03", "ROUNDS-02-L05", "ROUNDS-02-L06", "ROUNDS-03-L01", "ROUNDS-06-L01", "ROUNDS-07-L01", "ROUNDS-07-L03",
        "ROUNDS-08-L01", "ROUNDS-10-L01", "ROUNDS-10-L02", "ROUNDS-11-L01", "ROUNDS-12-L04", "ROUNDS-14-L01", "ROUNDS-14-L02", "ROUNDS-14-L03",
        "ROUNDS-14-L05", "ROUNDS-15-L02", "ROUNDS-17-L04", "ROUNDS-18-L03", "ROUNDS-18-L06", "ROUNDS-19-L01", "ROUNDS-19-L02", "ROUNDS-20-L01",
        "ROUNDS-24-L01", "ROUNDS-26-L01", "ROUNDS-26-L03", "ROUNDS-28-L01", "ROUNDS-31-L01", "ROUNDS-31-L08", "ROUNDS-32-L01", "ROUNDS-32-L02",
        "ROUNDS-32-L03", "ROUNDS-33-L01", "ROUNDS-34-L01", "ROUNDS-34-L05", "ROUNDS-34-L08",
        "ROUNDS-02-L04", "ROUNDS-01-L03", "ROUNDS-34-L03", "ROUNDS-32-L05", "ROUNDS-00A-L06", "ROUNDS-00B-L07", "ROUNDS-34-L07",
        "ROUNDS-25-L01", "ROUNDS-06-L02",
    }),
    "prerequisites": ["ROUNDS-01-L01", "ROUNDS-01-L02", "ROUNDS-01-L03/S2", "ROUNDS-00B-L01", "ROUNDS-00A-L01/S3"],
    "authorityBoundary": "contracts/database/erd-decisions.json",
    "affectedPackages": [
        "command-gateway", "revision-audit", "read-model", "account", "artifact", "capture-ingestion", "practice", "public-share",
        "execution-control-plane", "provider-gateway",
    ],
    "versioning": (
        "This record, the ERD's written part (contracts/database/erd-decisions.json), and contracts/database/benchmark.json share one "
        "revision counter, so a decision is cited as DR-0004@<revision>:<decision-id> (for example DR-0004@1:DB2) and a store as "
        "DR-0004@<revision>:<store-id>. A revision is needed only when one of those changes. A change to a decision's store, owning "
        "process, or owning leaf, or to a written entity's store, partition, or delete behavior, is breaking; adding an entity, a "
        "planned table, an index, or a limit is additive. The schema snapshot and the generated ERD (contracts/database/erd.json and "
        "docs/decisions/DR-0004-erd.md) are not governed: a PR that adds or changes a migration regenerates them, or DB_ERD_STALE "
        "fails it, and needs no revision of this record unless it changes a written field. A new table or relation field needs its "
        "written fields, so it comes with an additive revision. A ratified revision pins the SHA-256 of the written part, the "
        "receipt, their schemas, and the generated ADR, so an unapproved edit fails DR_APPROVAL_STALE. PocketBase is ratified by its "
        f"line: a patch on the {LINE} line is a pin change, and a port to another line supersedes this record first."
    ),
    "supersession": (
        "A ratified revision is never edited. A leaf that needs another store, transaction owner, or process supersedes this record "
        "first: the new revision names DR-0004@<n> in supersedes, gives supersessionReason, and lists per decision whether it is kept "
        "or changed. Leaves citing a changed decision go back to blocked until they re-cite; leaves citing an unchanged one keep "
        "their citation. An unratified revision can be reverted."
    ),
    "context": (
        "Issue #18 (ROUNDS-02-L01). Spec lines cite rounds-review's docs/superpowers/specs/2026-10-18-rounds-review-board-design.md. "
        f"A citation path@62d4eae:L<a>-L<b> is lines at the audited revision; facts about next were read at {AT}. Alternative A "
        "was the starting point because every store next added since R0 already works that way, and the SQLite benchmark "
        "(contracts/database/benchmark.json, synthetic data only) decides whether it holds."
    ),
    "securityConsequences": {
        "account": (
            "No runtime or privilege change here. DB2 and DB4 read the account from the bearer's auth record inside the command's "
            "transaction, so no command names its own account, and a record from another account answers like a missing one. "
            "Gateway-owned collections lose their REST write rules at each transfer."
        ),
        "privacy": (
            "Rows keep the privacy floor DR-0002 gives them, and the ERD names each entity's partition column and what account "
            "deletion does to it. The byte store dedupes within one account only, so whether a file exists never shows across "
            "accounts, and its bytes are read only through a route that checks the account (DB10). The benchmark seeds synthetic "
            "data and generates its accounts and passwords per run."
        ),
        "secret": (
            "Credentials appear by name only. No runtime writer uses the superuser; it keeps the bootstrap migration and operator "
            "use. Each service identity is a non-superuser auth record with its own secret, and its login answers only under its "
            "collection's exact name. #73's keyring encrypts provider keys, and later the byte store's files."
        ),
        "publicBoundary": (
            "#19's command routes sit behind nginx's existing /api/ pass-through to PocketBase: no new port, hostname, or route "
            "outside /api/. Each route authorizes the account inside its transaction (DB4), and #19's own PR carries the exposure "
            "review. The hook routes only the runner calls stay refused at the public URL, as nginx already refuses the admission, "
            "execution, snapshot, and share routes."
        ),
    },
}

record["decisions"] = [
    {
        "id": "DB1",
        "title": "Canonical write database",
        "status": "draft",
        "concern": "canonical-write-database",
        "store": "sqlite-data",
        "process": "PocketBase (the pocketbase container), the only process that writes pb_data",
        "owningLeaf": "ROUNDS-02-L01",
        "decision": (
            "Career data has one canonical write database: PocketBase's SQLite file pb_data/data.db, in WAL mode. Canonical records, "
            "relations, versions, change sets, audit entries, idempotency results, and the outbox all live in it, so one SQLite "
            "transaction covers a command and everything it records. File bytes sit beside it in pb_data/storage (DB10). "
            "pb_data/logs.db is PocketBase's request log and never canonical. No other process writes these files while PocketBase "
            "runs; #157's backup reader opens data.db read-only on the same host, since WAL mode needs its shared-memory file there."
        ),
        "alternatives": [
            {"option": "A second database the runner owns (alternative C)", "reason": "No transaction would cover a command's rows and its history; auth, files, and the containment stores stay in PocketBase."},
            {"option": "Postgres through PocketBase", "reason": "PocketBase runs only on its embedded SQLite (rejected options)."},
        ],
        "failureModes": [
            "One node: a deploy, restart, or crash makes the product unavailable until PocketBase is back (one replica, Recreate).",
            "A full disk stops every write, the audit and outbox rows with them.",
            "A long read transaction, such as a backup's, keeps the WAL from checkpointing, so the WAL grows until it ends.",
            ("A TRUNCATE, RESTART, or FULL checkpoint holds every writer until it ends, and a command waiting behind it can fail "
             "unacknowledged (limits). So no leaf runs one while commands run, and SQLite's passive autocheckpoint keeps the WAL "
             "in check."),
            f"The live pragmas are journal_mode={pragmas.get('journal_mode', 'pending')} and synchronous={pragmas.get('synchronous', 'pending')} "
            "(1 is NORMAL): a process crash loses no commit, but a power or kernel crash can lose the last commits before a checkpoint.",
            ("PocketBase's memory outgrows the shipped 512Mi limit at 10 accounts (limits), so under that load the kernel's OOM killer "
             "would end the container until #176 raises the limit." if rss and rss > 512 * 1024 ** 2 else
             "PocketBase's memory stays under the shipped 512Mi limit at 10 accounts (limits)."),
        ],
        "limits": [
            f"One writer: at most {peak or 'pending'} commands per second with 10 accounts ({peak1 or 'pending'} with 1), on one Go "
            "scheduler thread standing in for the 500m CPU limit. That is a best case for the shipped limit: one core here is more "
            "than the 500m quota and never throttles, so the shipped throughput is at most this, and its hold times and lag at least "
            "those measured.",
            f"Commands per second at 10 accounts were {by_clients}: past the peak, more clients lost throughput and queued longer, and "
            f"at 64 clients a command waited {ms(get(S10, 'sweep', '64', 'queueMs', 'p99'))} at p99 for the writer.",
            f"A TRUNCATE checkpoint under the steady load at 10 accounts took {ms(checkpoint.get('ms'))}. The "
            f"{checkpoint.get('commandsDuring', 'pending')} commands in flight took up to {ms(get(checkpoint, 'clientMsDuring', 'max'))} "
            "end to end, and "
            + (f"{steady_failed} of the phase's commands failed unacknowledged, so nothing was lost. " if steady_failed else "none failed. ")
            + "Passive autocheckpoints fall inside the hold percentiles.",
            f"The WAL peaked at {mib(wal)} with 10 accounts and {mib(get(S1, 'samplers', 'walMaxBytes'))} with 1.",
            f"PocketBase's RSS peaked at {mib(get(S10, 'samplers', 'rssMaxBytes'))} with 10 accounts and "
            f"{mib(get(S1, 'samplers', 'rssMaxBytes'))} with 1, against the 512Mi limit, with GOMEMLIMIT at 460MiB. GOMEMLIMIT bounds only "
            "the Go heap, and PocketBase's SQLite driver allocates outside it, which likely holds the rest. #176 (ROUNDS-34-L07) ships a "
            "limit of at least 1Gi.",
            "It scales up, not out: no second replica and no second writer.",
        ],
        "consequences": "#19 to #23 and every context build on one SQLite file, and throughput is bounded by one writer, which the receipt measures against the floor's load.",
        "migrationImpact": "None. The data already lives here.",
        "rollbackImpact": "Nothing to roll back. A revision that picks another database is a full authority transfer under spec 2699's template, scheduled by #17.",
        "sources": ["spec 1942-1951", "spec 2069-2071", "https://pocketbase.io/faq/", "contracts/database/benchmark.json"],
    },
    {
        "id": "DB2",
        "title": "Transaction owner and isolation",
        "status": "draft",
        "concern": "transaction-owner",
        "store": "sqlite-data",
        "process": "the command's gateway hook route, in PocketBase's JSVM",
        "owningLeaf": LEAVES["gateway"],
        "decision": (
            "Each command runs in exactly one runInTransaction that its gateway route owns, and commits or rolls back whole. "
            "PocketBase 0.22 runs every write and explicit transaction on its one write connection, Dao.nonconcurrentDB() in its JSVM "
            "API, whose pragmas the receipt reads, so commands run one at a time and see each other as serial. Every read that "
            "decides the outcome (the expected versions, the account check, the invariant checks) goes through the transaction's Dao, "
            "never $app.dao(), so it sees the command's own writes and nothing that commits after it. No network call runs inside a "
            "transaction: provider calls, renders, and relays run outside and come back as new commands. Batch work (backfills, "
            "transfers, purges) commits at most 500 rows per transaction, as #14's migration does."
        ),
        "alternatives": [
            {"option": "Optimistic transactions over several connections", "reason": "PocketBase 0.22 writes on one connection; there is nothing to run concurrently."},
            {"option": "One REST call per record with compensation", "reason": "Not atomic: a failure between calls leaves half a command (rejected options)."},
        ],
        "failureModes": [
            "A slow transaction holds the only writer, and every other command queues behind it; the lock budget bounds it.",
            "A read through $app.dao() inside the callback sees only committed state, so a check can pass on rows the command already changed; #19 lints for it.",
            "A network call inside the callback would hold the writer for the call's whole length; #19 refuses it.",
            "A command that throws after its writes leaves nothing behind (the before-commit failpoint), and its retry with the same command_id commits once.",
        ],
        "limits": [
            f"Lock budget: at the steady rate with 10 accounts the writer is held {ms(hold50)} at p50 and {ms(hold99)} at p99 per command, "
            f"and a command waits {ms(queue99)} at p99 for it, {BEST_CASE}.",
            f"Batches of at most 500 rows; the transfer's batches of 30 applications held the writer {ms(batch99)} at p99.",
            (f"A transfer's write freeze grows with its accounts: {freeze_per_account:.2f} s per account at the floor here, backup and "
             f"transfer together, so about {freeze_accounts} accounts fit under 15 minutes on this machine, {BEST_CASE}."
             if freeze_per_account else "A transfer's write freeze per account: pending."),
            ("The largest single transaction, an account delete cascading the floor's legacy rows and #1's and #20's rows, isn't "
             f"measured here; #76 ({LEAVES['purge']}) measures it before account deletion ships."),
        ],
        "consequences": "#19's API is one function per command that takes the transaction's Dao. Throughput falls as hold time grows, so commands stay small and do their slow work outside.",
        "migrationImpact": "None now. #19 builds the gateway on it.",
        "rollbackImpact": "None until #19 ships; after that, a superseding revision.",
        "sources": ["spec 1942-1951", "PocketBase 0.22's JSVM API: Dao.nonconcurrentDB()", "contracts/database/benchmark.json"],
    },
    {
        "id": "DB3",
        "title": "Gateway placement",
        "status": "draft",
        "concern": "gateway-placement",
        "store": "sqlite-data",
        "process": "PocketBase hook routes; the runner is only ever a caller",
        "owningLeaf": LEAVES["gateway"],
        "decision": (
            "The command gateway is a set of PocketBase hook routes under /api/rounds/commands/, registered as Caller rows in "
            "docs/security/server-writes.md. The SPA reaches them through nginx's existing /api/ pass-through, under its 1m body cap; "
            "no port, hostname, or route outside /api/ is added. The runner reaches PocketBase only through hook routes, never a "
            + (f"collection write. At {AT} its code holds {F['runnerWrites']} direct collection writes, all with the caller's token, and "
               f"{F['runner']['ai.py']} of them run: the provider and settings writes in backend/routers/ai.py, which move behind #73's "
               f"routes. The {F['runner']['take_home.py']} in backend/routers/take_home.py can't run since #3's PR 4 turned the execution "
               "keys on and made graded rows server-only. Its "
               if TAKE_HOME_GATED else
               f"collection write. At {AT} it still makes {F['runnerWrites']} direct collection writes, all with the caller's token: the "
               f"{F['runner']['ai.py']} provider and settings writes in backend/routers/ai.py move behind #73's routes, and the "
               f"{F['runner']['take_home.py']} in backend/routers/take_home.py end with #3's PR 4, which makes graded rows server-only. Its ")
            + "share and execution calls already use hook routes. PocketBase 0.22 loads *.pb.js only from the top of pb_hooks (checked on "
            "the native binary: a nested file never ran), so each package registers its routes in one top-level <package-id>.pb.js and "
            "keeps its code at its DR-0002@2 target path."
        ),
        "alternatives": [
            {"option": "Routes in the runner that call PocketBase's REST API", "reason": "Not atomic, and a second authorization point (rejected options)."},
            {"option": "Runner-fronted gateway routes (alternative D)", "reason": "An extra hop and process per command with no gain for commands that need no runner work."},
        ],
        "failureModes": [
            "A route that doesn't register as a Caller row is an unrecorded writer; #19's registry check fails it.",
            "A gateway-owned collection that keeps a REST write rule is a path around the gateway; DB4 nulls it at each transfer.",
            (f"Until #73 lands, the runner's {F['runner']['ai.py']} provider and settings writes keep going around the gateway with the caller's token."
             if TAKE_HOME_GATED else
             f"Until #73 and #3's PR 4 land, the runner's {F['runnerWrites']} writes keep going around the gateway with the caller's token."),
        ],
        "limits": [
            "A command body up to nginx's 1m default under /api/.",
            "Handlers run on PocketBase's pool of JS VMs, and a handler's CPU time inside the transaction adds to the lock hold.",
        ],
        "consequences": "#19 builds routes, not a service. Each later context adds its commands as hook routes in its package directory.",
        "migrationImpact": "None. No route exists yet.",
        "rollbackImpact": "Before #19 ships, none. After, moving the gateway is a superseding revision and a route-by-route transfer.",
        "sources": ["spec 1206-1210", "spec 1942-1951", "frontend/nginx.conf", "docs/security/server-writes.md", "backend/routers/ai.py", "backend/routers/take_home.py"],
    },
    {
        "id": "DB4",
        "title": "Account authorization",
        "status": "draft",
        "concern": "account-authorization",
        "store": "sqlite-data",
        "process": "the command's gateway hook route, inside its transaction",
        "owningLeaf": LEAVES["gateway"],
        "decision": (
            "The account is the bearer's auth record, which the route reads inside its transaction; no command body names its account. "
            "Each record a command loads and each relation endpoint it writes is checked against that account in the same "
            "transaction with #10's predicate (pocketbase/pb_hooks/relation_endpoints.js), and #10's triggers stay as the backstop. "
            "Share capabilities keep #11's and #12's checks. #9's collection rules (docs/security/account-scope.v1.json) keep guarding "
            "legacy REST writes until each context transfers; the transfer leaf then sets that context's create, update, and delete "
            "rules to null, and #21's tables are born with null rules. #1's three writer kinds (Caller, Service, System) are ratified "
            "as they stand. Service identities are non-superuser auth collections whose login answers only under the collection's "
            "exact name: execution_service and share_resolvers today, ai_gateway (#73) and dispatcher_service (#22) planned. The "
            "gateway never authenticates as the superuser."
        ),
        "alternatives": [
            {"option": "Keep #9's collection rules as the only check", "reason": "Hook routes write through the Dao, which skips collection rules (account-scope's superuser_bypass entry)."},
            {"option": "Authorize in the runner before calling PocketBase", "reason": "The check would sit outside the transaction it protects, and a second process would hold the decision."},
        ],
        "failureModes": [
            "A route that loads a record without the account check would cross accounts; the bench answers another account's id and a missing id with the same 404, and #19 keeps that.",
            "A REST write rule left open on a transferred collection is a second writer; #19's bypass guard checks every gateway-owned collection.",
            "Because Dao writes skip collection rules, the route's own check is the only one on its writes.",
        ],
        "limits": ["One account per command; no command spans accounts."],
        "consequences": "Authorization lives in one place per command, inside the transaction. #172 registers each route's rule in its matrix.",
        "migrationImpact": "None now. Each transfer leaf nulls its context's REST write rules in its own migration.",
        "rollbackImpact": "A transfer's rule change rolls back with that transfer, before its point of no return.",
        "sources": ["spec 1942-1951", "docs/security/server-writes.md", "docs/security/account-scope.v1.json", "pocketbase/pb_hooks/relation_endpoints.js"],
    },
    {
        "id": "DB5",
        "title": "Idempotency store",
        "status": "draft",
        "concern": "idempotency-store",
        "store": "sqlite-data",
        "process": "the command's gateway hook route",
        "owningLeaf": LEAVES["versions"],
        "decision": (
            "Command idempotency uses #1's admission_commands, keyed by its unique (account, command_id) index, with the v7 id check it "
            "already enforces. #20 adds domain-command rows kept 30 days; they cascade with the account, and the 30-day expiry bounds "
            "that cascade. #20's body keys its rows on a non-cascading account_id; this record reads adopting #1's store as keeping "
            "its cascading relation instead, bounded by the 30-day expiry, as #18's body says. A replay with the same fingerprint "
            "returns the stored result and writes nothing, and a changed body under the same id is a conflict. #22's due-work removes "
            "expired rows, and #20 owns the behavior."
        ),
        "alternatives": [
            {"option": "A new idempotency table for domain commands", "reason": "Two stores for one key; admission_commands already has the key, the v7 check, and the cascade."},
            {"option": "No stored result, only a dedupe key", "reason": "A retry couldn't return the original result, so clients couldn't tell a replay from a conflict."},
        ],
        "failureModes": [
            "A retry after 30 days is a new command; the window is the contract.",
            "Deleting an account cascades its window of rows in one transaction, about 10,000 at the floor (the bench's idempotency seed).",
        ],
        "limits": ["30 days of rows per account; the receipt's seed holds 10,000 per account, and the replay share of the mix writes nothing."],
        "consequences": "#20 extends a live table instead of adding one, and #19's replay path reads it inside the command's transaction.",
        "migrationImpact": "#20 adds its columns and the domain row kind in an additive migration.",
        "rollbackImpact": "#20's migration has a down step; admission rows are untouched.",
        "sources": ["docs/security/server-writes.md", "pocketbase/pb_hooks/admission.js"],
    },
    {
        "id": "DB6",
        "title": "Aggregate and version model",
        "status": "draft",
        "concern": "aggregate-version-model",
        "store": "sqlite-data",
        "process": "the command's gateway hook route",
        "owningLeaf": LEAVES["versions"],
        "decision": (
            "Every aggregate row carries an integer version that each committed change raises by one. A command sends the versions it "
            "read as a vector keyed by aggregate id; one stale entry rejects the whole command with the current versions and writes "
            "nothing. #19 composes cross-aggregate work, such as a new offer superseding the active one and the opportunity's status "
            "following it, as sub-commands of one command in one transaction, each checking and raising its own version. #21's change "
            "set log is the default history: one change set per command, with a per-account commit_position assigned in the "
            "transaction. Revision tables exist only where a record pins a version (#21)."
        ),
        "alternatives": [
            {"option": "Timestamps or ETags instead of integer versions", "reason": "Clock-based checks can tie or skew; an integer per aggregate is exact and cheap to compare."},
            {"option": "A revision row for every write", "reason": "Doubles the write amplification for history the change-set log already keeps."},
        ],
        "failureModes": [
            "A client holding stale versions gets a conflict with the current ones and must re-read; nothing is half applied.",
            "Two commands on one aggregate serialize on the writer; the second sees the first's version.",
        ],
        "limits": [f"The mix writes {amp or 'pending'} rows per command on average (weighted), counting the record, its change set, audit, outbox, and idempotency rows."],
        "consequences": "#20 owns versions and conflicts, #21 the change-set log, and #19 the composition of sub-commands.",
        "migrationImpact": "Each context's transfer adds its version column; no data changes here.",
        "rollbackImpact": "A context's version column rolls back with its transfer.",
        "sources": ["spec 1942-1951", "contracts/database/benchmark.json"],
    },
    {
        "id": "DB7",
        "title": "Outbox and projectors",
        "status": "draft",
        "concern": "outbox-projectors",
        "store": "sqlite-data",
        "process": "the runner's dispatcher, as dispatcher_service",
        "owningLeaf": LEAVES["outbox"],
        "decision": (
            "A command writes its domain events to domain_outbox in its own transaction, with #22's library in "
            "pocketbase/pb_hooks/lib/revision-audit/. The relay, the job queue, and the due-work tick run in the runner's dispatcher as "
            "dispatcher_service and call PocketBase routes under /api/outbox/. With two runner replicas, one consumer stays active "
            "through #22's outbox-relay lease in platform_leases: each grant carries a fencing token, and a write under an older token "
            "is refused. Projectors apply events in PocketBase transactions and record progress in projector_checkpoints (#23), and "
            "outbox_watermarks skips a redelivered event. cronAdd keeps only the sweeps, since its one-minute granularity can't meet a "
            "2 s lag target."
        ),
        "alternatives": [
            {"option": "cronAdd as the relay", "reason": "A one-minute tick can't keep p95 lag under 2 s."},
            {"option": "A relay inside PocketBase hooks after commit", "reason": "Network delivery from a hook would hold a JS VM, and an after-commit hook has no retry or lease."},
        ],
        "failureModes": [
            "A relay that applies events and dies before its checkpoint redelivers them; the bench's mid-relay failpoint shows they're skipped once.",
            ("A relay with a lapsed lease keeps writing; its fencing token is refused. The native run's mid-relay step acks once more "
             "under the crashed relay's old token and is fenced, and pocketbase/tests/test_bench_hooks.py checks that a takeover fences "
             "the old holder."),
            "A crash after commit and before the relay leaves events in the outbox; the next holder relays them once (the after-commit failpoint).",
        ],
        "limits": [
            f"Relay lag p95 {ms(lag95)} at the steady rate with 10 accounts, against 2 s, and {ms(get(S1, 'steady', 'relayLagMs', 'p95'))} "
            "with 1, counted over the phase's own events once the sweep's backlog had drained; #22 sizes its batches and poll interval "
            f"against it{', and it is the closest of the five targets' if CLOSEST == 'projection_lag_p95' else ''}. The tail is the "
            f"checkpoint's: p99.9 {ms(lag999)} at 10 accounts while a TRUNCATE checkpoint held the writer (DB1).",
            f"Read-your-writes p99 {ms(ryw99)} through the projection, against 5 s, with "
            f"{get(S10, 'steady', 'readYourWritesFallbacks', default='pending')} of {get(S10, 'steady', 'readYourWritesMs', 'n', default='pending')} "
            "reads taking the canonical fallback.",
        ],
        "consequences": "#22 runs the relay in the runner and #23 the projectors in PocketBase; both write through dispatcher_service.",
        "migrationImpact": "#22 and #23 add their tables in additive migrations with null rules.",
        "rollbackImpact": "Their migrations have down steps; no canonical row depends on a projection.",
        "sources": ["spec 2056-2067", "docs/security/server-writes.md", "contracts/database/benchmark.json", "pocketbase/tests/test_bench_hooks.py"],
    },
    {
        "id": "DB8",
        "title": "Backup and restore owner",
        "status": "draft",
        "concern": "backup-restore",
        "store": "n/a:a procedure over sqlite-data and files; #157 names the backup target",
        "process": "an operator procedure with a read-only reader process beside PocketBase, owned by #157",
        "owningLeaf": LEAVES["backup"],
        "decision": (
            "#157 owns backup and restore. The method is an online, SQLite-consistent copy of data.db by a reader (SQLite's backup API, "
            "or VACUUM INTO), then the byte store, with file deletes held until the next backup has run. A backup then stops nothing. "
            "PocketBase's own backup API zips all of pb_data while holding the writer, and today's procedure (docs/operations.md) "
            "stops PocketBase for as long as its tar takes; the receipt measured all three. A restore runs on the same image tag and "
            "is verified before traffic returns. docs/operations.md stays as it is until #157 changes it."
        ),
        "alternatives": [
            {"option": "Stop PocketBase and tar pb_data (today)",
             "reason": f"A full outage for the archive's length: {tar_down if tar_down is not None else 'pending'} s at 10 accounts, and "
                       f"{get(S1, 'stopAndTar', 'downtimeSeconds', default='pending')} s at 1 account with its 2 GiB of files."},
            {"option": "PocketBase's backup API",
             "reason": f"It holds the writer for the whole zip: commands waited up to {ms(zip10.get('queueMsDuring', {}).get('max'))} behind "
                       f"its {zip10.get('seconds', 'pending')} s zip at 10 accounts, and up to "
                       f"{ms(backup(S1, 'pocketbase-backup-api').get('queueMsDuring', {}).get('max'))} at 1 account with its files."},
        ],
        "failureModes": [
            "A file deleted before the backup that last saw it can't be restored; deletes wait for the next backup.",
            "A copy taken mid-write by a plain file copy can be torn; only SQLite's own copy is consistent.",
            "A restore onto another image tag could migrate on first start; restores use the backup's tag.",
            ("A restore needs the runner's AI_KEY_SECRET, which pb_data and so the backup don't hold: without it, what the runner "
             "sealed or keyed with it stops working, so #157's procedure keeps the key with the deployment's secrets."),
        ],
        "limits": [
            f"Restore at 10 accounts: {restore.get('value', 'pending')} s against 30 minutes ({restore.get('basis', 'pending')}): the "
            f"database restored and checked in {restore_of(S10, 'vacuum-into').get('restoreSeconds', 'pending')} s, and 100 GB of files at "
            f"the 2 GiB sample's {copy_rate}.",
            f"Taking the online copy at 10 accounts: VACUUM INTO {round((vac10.get('ms') or 0) / 1000, 1)} s and SQLite's backup API "
            f"{ext10.get('seconds', 'pending')} s, with commands waiting at most {ms(vac10.get('queueMsDuring', {}).get('max'))} meanwhile.",
        ],
        "consequences": "#157 writes the procedure and its rehearsal; #76 holds file purges until a backup has run.",
        "migrationImpact": "None here. #157 changes docs/operations.md.",
        "rollbackImpact": "The old procedure stays valid until #157 replaces it.",
        "sources": ["spec 2064-2065", "https://pocketbase.io/docs/going-to-production/", "docs/operations.md", "contracts/database/benchmark.json"],
    },
    {
        "id": "DB9",
        "title": "PocketBase retained, upgraded, or replaced",
        "status": "draft",
        "concern": "pocketbase-version",
        "store": "n/a:a binary version, not a store",
        "process": "the pocketbase image build (pocketbase/Dockerfile)",
        "owningLeaf": "ROUNDS-02-L01",
        "decision": (
            f"Retain PocketBase and stay on its {LINE} line, which upstream patched through 0.22.57. Stage P3 (ROUNDS-02-L01/P3) moves "
            "the pin to 0.22.57, the newest 0.22 release, which adds no database migration and changes no hook API. This record "
            "ratifies the line: a patch on it is a pin change, and a port to another line supersedes the record first. The port is "
            "deferred until a trigger in the version analysis fires. From #19 on, new hook code reaches PocketBase's API through one "
            "module, pocketbase/pb_hooks/lib/pocketbase.js, so that port rewrites one module and the migrations instead of every package."
        ),
        "alternatives": [
            {"option": "Port to a newer line before #19", "reason": f"Rewrites all {F['migrations']} migrations and every containment hook now, for no target the benchmark misses."},
            {"option": "Replace PocketBase", "reason": "PocketBase holds auth, files, and every containment store on next, and runs only on its embedded SQLite; replacing it means alternative C's two authorities or a rewrite of all of them (rejected options)."},
        ],
        "failureModes": [
            "Upstream publishes no further 0.22 release, so a later change needs the port; that is the first trigger.",
            "Upstream archived its GitHub repository on 2026-10-26 and its README points to a new home; the Dockerfile still fetches the release zip from GitHub against its pinned SHA-256, and a build fails rather than take another file.",
        ],
        "limits": ["Every hook and migration on next is written against 0.22's API."],
        "consequences": "P3 is a pin change on the ratified line; the port, when a trigger fires, is its own leaf with the strategy below, and supersedes this record first.",
        "migrationImpact": "None within the 0.22 line. The port's migration plan is in the version analysis.",
        "rollbackImpact": "Within the 0.22 line, roll back by image tag. The port's boundary is in the version analysis.",
        "sources": ["https://pocketbase.io/v023upgrade/jsvm/", "PocketBase's 0.22 release line"],
    },
    {
        "id": "DB10",
        "title": "Byte store",
        "status": "draft",
        "concern": "byte-store",
        "store": "files",
        "process": "PocketBase file storage, written by gateway routes",
        "owningLeaf": LEAVES["bytes"],
        "decision": (
            "Bytes live in PocketBase's file storage, pb_data/storage, behind one account-scoped collection, account_blobs: one row "
            "per stored file, its SHA-256, size, privacy class, and retention metadata, unique on (account_id, sha256). Identical "
            "bytes in two accounts are two files. Its file field is protected and its REST rules are null, so bytes are read only "
            "through a gateway route that checks the account, never from a URL alone. #73's keyring encrypts files once its keys "
            "exist, and older files are rewrapped as #22 due-work. #157's backup copies the files after the database, and #76 purges a "
            "row, then its file once the next backup has run. #53 (ROUNDS-10-L01) writes it first. #4's snapshot markup files stay "
            "where they are and are adopted as they stand. #6's render outputs get a path only: the same collection, written by "
            "complete as execution_service, held with the containment release. users.avatar, PocketBase's default file field, has no "
            "writer in the app, and this decision doesn't adopt it. PocketBase's S3 setting is the path past one disk."
        ),
        "dedupe": (
            "Within one account only. The unique key starts with account_id, and a lookup never reads another account's rows, so "
            "uploading bytes can't reveal whether another account holds them."
        ),
        "alternatives": [
            {"option": "A volume outside PocketBase", "reason": "A second store with its own backup and purge, and no transaction tying a row to its file."},
            {"option": "An object store now", "reason": "Self-hosters would need one before they need the scale; PocketBase's S3 setting keeps it a later switch."},
        ],
        "failureModes": [
            "A file whose row commits but whose write fails leaves a row without bytes; the row is written after the file, and a sweep finds orphans.",
            "A file field that isn't protected is served to anyone holding its URL; account_blobs' field is protected, so a URL alone never reads it.",
            "Bytes written before #73's keys exist are plaintext until rewrapped.",
            "The disk fills with bytes before rows; the PVC sizing in the storage plan sets the floor.",
        ],
        "limits": [f"The 2 GiB sample copied at {copy_rate} in a restore; 10 GB per account is extrapolated from that rate, labeled so in the receipt."],
        "consequences": "#53, #91, #6, and #4 share one byte store with one dedupe rule, one read path, and one purge path.",
        "migrationImpact": "#53 adds account_blobs in an additive migration; #4's files are adopted without moving.",
        "rollbackImpact": "#53's migration has a down step while account_blobs is empty; after files land, a forward fix.",
        "sources": ["spec 2020-2028", "docs/security/server-writes.md", "contracts/database/benchmark.json"],
    },
]

record["alternativesEvaluated"] = [
    {
        "id": "A", "name": "PocketBase hook routes owning the transaction",
        "runnerWritePath": "Hook routes only, with the caller's bearer or a service identity, as the runner already does for admission, execution, snapshots, and shares.",
        "imageBuild": "Unchanged: the published PocketBase binary with pb_migrations, pb_hooks, and seeds copied in.",
        "bindings": "None new: hooks are JavaScript in PocketBase's JSVM, and #182's contracts are JSON Schema the SPA, hooks, and runner share.",
        "nginxChange": "None: commands use the existing /api/ pass-through.",
        "verdict": "chosen",
        "reason": "One process and one transaction per command, the pattern every containment store on next already uses; the receipt decides whether it holds.",
    },
    {
        "id": "B", "name": "PocketBase as a Go framework",
        "runnerWritePath": "Go routes in a custom PocketBase build; the runner calls them as in A.",
        "imageBuild": "A CI-built Go binary instead of the published release, rebuilt and re-pinned for every upstream release.",
        "bindings": "Go types for every command contract, which #182 doesn't generate.",
        "nginxChange": "None.",
        "verdict": "rejected",
        "reason": "The same database and transaction model as A, plus a Go toolchain, a custom binary, and a port of every JS hook on next, for nothing the benchmark asks for.",
    },
    {
        "id": "C", "name": "A separate database behind a runner gateway",
        "runnerWritePath": "The runner owns a new database and writes it directly.",
        "imageBuild": "A new database service with its own image, volume, backup, and credentials.",
        "bindings": "Runner models for every aggregate, plus a sync to PocketBase for auth and what stays there.",
        "nginxChange": "Command routes move to runner locations.",
        "verdict": "rejected",
        "reason": "Two authorities: auth, files, and the containment stores stay in PocketBase, so no transaction covers a command that touches both, and every account check crosses the network.",
    },
    {
        "id": "D", "name": "A PocketBase gateway the runner calls as a non-superuser client",
        "runnerWritePath": "The runner forwards each command to gateway hook routes as a service identity, passing the caller's bearer.",
        "imageBuild": "Unchanged.",
        "bindings": "None new.",
        "nginxChange": "Command routes go to the runner, and the gateway routes are refused at the public URL.",
        "verdict": "rejected",
        "reason": "An extra hop and process per command, and the route must still verify the forwarded bearer. A keeps this shape for the runner's own calls, such as execution completions and provider results.",
    },
]

record["rejected"] = [
    {"id": "fastapi-rest", "option": "FastAPI orchestrating PocketBase's REST API",
     "reason": "Each REST call commits alone, so a command spanning records can stop halfway, which is how the browser invariants break today.",
     "source": "spec 1206-1210"},
    {"id": "fastapi-sqlite", "option": "FastAPI writing the SQLite file directly",
     "reason": "A second writer outside PocketBase's write connection that skips its rules, hooks, and realtime events, on a volume only PocketBase mounts.",
     "source": "docker-compose.prod.yml@62d4eae:L38-L39"},
    {"id": "postgres-pocketbase", "option": "Postgres through PocketBase, as the k8s comment promised",
     "reason": "PocketBase runs only on embedded SQLite; its FAQ says \"there are no plans for supporting other databases\".",
     "source": "https://pocketbase.io/faq/"},
]

record["benchmark"] = {
    "receipt": "contracts/database/benchmark.json",
    "revision": (rc or {}).get("revision", 1),
    "result": result,
    "seedReading": ("the floor's 50,000 Activities, Actions, and audit entries is read as one combined count, 40,000 activities "
                    "and actions plus 10,000 audit entries per account, the lighter of its two readings"),
}

GUIDE = "https://pocketbase.io/v023upgrade/jsvm/"
GUARD_LEAVES = {"admission.pb.js": "#1", "execution.pb.js": "#3", "share_secrets.pb.js": "#12", "demo.pb.js": "#177", "profile_files.pb.js": "#177"}
guard_files = F["guards"][1]
_unknown = [g for g in guard_files if g not in GUARD_LEAVES]
if _unknown:
    raise SystemExit(f"sign-in hooks in {', '.join(_unknown)}: name their leaf in GUARD_LEAVES")
guard_leaves = series(sorted({GUARD_LEAVES[g] for g in guard_files}, key=lambda s: int(s[1:])))
record["pocketbase"] = {
    "line": LINE,
    "pinAtRatification": PIN,
    "decision": f"retain the {LINE} line",
    "countedAt": COUNTED_AT,
    "summary": (
        f"PocketBase stays, on the {LINE} line, which this record ratifies. P3 moves the pin to 0.22.57, the newest 0.22 release; "
        "the port to another line waits for a trigger, and new hook code goes through one module so the port stays bounded. The "
        "break sites below are what that port would touch."
    ),
    "breakSites": [
        {"id": "migrations", "site": "pocketbase/pb_migrations/", "count": F["migrations"], "upstream": f"{GUIDE} (migrate((app)) replaces migrate((db)) and new Dao(db); a collection's schema becomes fields)",
         "note": f"All {F['migrations']} call new Dao(, with the schema and options shapes, raw-SQL triggers in {F['triggers']} files, and indexes in {F['indexes']}."},
        {"id": "admin-bootstrap", "site": "pocketbase/pb_migrations/1700000500_bootstrap_admin.js", "count": 1, "upstream": f"{GUIDE} (admins become _superusers records)",
         "note": "findAdminByEmail, new Admin(), and saveAdmin."},
        {"id": "runner-admin-login", "site": "backend/app/pb_auth.py", "count": 1, "upstream": f"{GUIDE} (admin auth moves to the _superusers collection)",
         "note": "Unused helpers a test bans; #14 S3 removes them with PB_ADMIN_*."},
        {"id": "request-data-rules", "site": ", ".join(F["requestData"]), "count": len(F["requestData"]), "upstream": f"{GUIDE} (@request.data becomes @request.body)",
         "note": f"The {'only file' if len(F['requestData']) == 1 else 'files'} that {'uses' if len(F['requestData']) == 1 else 'use'} it."},
        {"id": "hook-registrations", "site": f"pocketbase/pb_hooks/*.pb.js ({F['pbjs']} files)", "count": F["registrations"],
         "upstream": f"{GUIDE} (handlers call e.next(); onAfterBootstrap becomes onBootstrap; path params use {{id}}; requireRecordAuth becomes requireAuth)",
         "note": (f"{F['routes']} routes, {F['routerUse']} routerUse middlewares, {F['cron']} cronAdd jobs, {F['boot']} onAfterBootstrap hooks, "
                  f"{F['modelHooks']} record and model hooks, and {F['cli']} CLI commands, listed in server-writes.md and account-scope.v1.json.")},
        {"id": "dao-and-transactions", "site": "pocketbase/pb_hooks/*.js", "count": F["dao"][0] + F["tx"][0], "upstream": f"{GUIDE} (the Dao is removed; $app.runInTransaction((txApp) => ...))",
         "note": f"$app.dao() {F['dao'][0]} times in {len(F['dao'][1])} files, and runInTransaction at {F['tx'][0]} sites in {len(F['tx'][1])} libraries."},
        {"id": "superuser-checks", "site": ", ".join(F["admin"][1]), "count": F["admin"][0], "upstream": f"{GUIDE} (requestInfo's admin becomes a _superusers auth record)",
         "note": f"{F['admin'][0]} checks of requestInfo().admin in {len(F['admin'][1])} libraries."},
        {"id": "after-delete-hook", "site": "pocketbase/pb_hooks/share_capabilities.pb.js", "count": 1, "upstream": f"{GUIDE} (model hooks become record hooks with explicit after-success events)",
         "note": "#11's onModelAfterDelete revoke relies on 0.22's after-commit timing."},
        {"id": "login-guards", "site": ", ".join(guard_files), "count": F["guards"][0], "upstream": f"{GUIDE} (auth request hooks change name and take e.next())",
         "note": f"{F['guards'][0]} sign-in hooks in {len(guard_files)} files: the guards of {guard_leaves} on PocketBase's password and OAuth2 hooks."},
        {"id": "system-migration-name", "site": "scripts/lint_migrations.py and scripts/migration-lint-allowlist.json (D10's 1702134273)", "count": 1,
         "upstream": f"{GUIDE} (system migrations are squashed)",
         "note": "D10 names a migration that follows 0.22's own system migration."},
        {"id": "admins-denials", "site": "frontend/nginx.conf, harness/verify_deployment.py (deployment.admins.present)", "count": 2,
         "upstream": f"{GUIDE} (implied: admins become _superusers records, so /api/admins goes)",
         "note": "The nginx refusal and the verifier's check both name /api/admins."},
        {"id": "verifier-shapes", "site": "harness/verify_deployment.py:123 and :431", "count": 2, "upstream": f"{GUIDE} (response shapes change)",
         "note": "The deployment verifier pins 0.22 answers."},
        {"id": "sdk-skew", "site": "frontend/package.json (pocketbase ^0.26.8)", "count": 1, "upstream": f"{GUIDE} (a 0.22 server keeps the JS SDK below 0.22.0)",
         "note": "The SPA runs SDK 0.26.8 against a 0.22 server; #19's client uses only calls a 0.22 server answers, and the port settles the skew."},
        {"id": "gateway-transactions", "site": "#19's gateway routes (not built)", "count": 0, "upstream": f"{GUIDE} ($app.runInTransaction((txApp) => ...))",
         "note": "Goes through pocketbase/pb_hooks/lib/pocketbase.js, so the port changes one module."},
        {"id": "normalization-pin", "site": "#172's normalization.v1.json (not on next)", "count": 0, "upstream": "n/a: a repository pin, not an upstream change",
         "note": "#172 cites this record's line when it lands."},
    ],
    "strategy": (
        f"Within the {LINE} line (P3): a pin change with no migration, no hook change, and no data change; CI's harness checks the new "
        "image. New hook code goes through pocketbase/pb_hooks/lib/pocketbase.js, the only module that calls the Dao, "
        "runInTransaction, requestInfo, and the record API. When a trigger fires, the port is its own leaf: each deployment first runs "
        f"the last {LINE} release, then the new image; fresh installs get a squashed baseline (one current-format snapshot plus the "
        "seed, the admin bootstrap, and the JSON size step) that passes #1's migration lint; existing installs keep their _migrations "
        "history; and the port re-runs this benchmark on the new version."
    ),
    "freezeWindow": (
        f"Within the {LINE} line, none: the new binary starts on the same data with no migration. For the port, the new binary's first "
        "start, which runs its system migrations over the whole database; the port measures it on a copy at the floor against the "
        f"15-minute freeze target. For scale, a startup schema change at 10 accounts here was down {schema_s if schema_s is not None else 'pending'} s."
    ),
    "rollbackBoundary": (
        f"Within the {LINE} line, roll back by image tag at any time. For the port, roll back by image tag before the new binary's first "
        "start; after it, only the pre-upgrade backup, which loses later writes, or a forward fix (spec 2699)."
    ),
    "triggers": [
        f"Upstream publishes no further {LINE} release.",
        "A fix the deployment needs lands only on a newer line.",
        "A leaf needs a feature only a newer line has.",
    ],
}
if BENCH_VERSION not in ("pending", PIN):
    record["pocketbase"]["benchmark"] = (
        f"The receipt ran on {BENCH_VERSION}, before P3 moved the pin to {PIN}. Both are on the {LINE} line; the numbers are "
        f"{BENCH_VERSION}'s, and the port re-runs the benchmark."
    )
record["pocketbase"]["snapshot"] = (
    (f"At this revision, contracts/database/schema-snapshot.json comes from migrate up on the {SNAP_VERSION} binary, not {PIN}: "
     f"the {LINE} releases between them add no database migration, so the schema is the same. A PR that changes a migration "
     "regenerates it.")
    if SNAP_VERSION != PIN else
    (f"At this revision, contracts/database/schema-snapshot.json comes from migrate up on the pinned {PIN} binary. A PR that "
     "changes a migration regenerates it.")
)

record["identifiers"] = [
    {"id": "partition-columns", "owner": "ROUNDS-02-L01",
     "rule": ("Existing collections keep user as the partition column, logically account_id and set by the server once #9's rules ship; #24 "
              "and #159 decide any rename. Platform tables (#21 to #23) use indexed, non-cascading account_id text, because a 50,000-row "
              "cascade would hold the single writer, and #76 purges them in batches. #1's and #3's stores keep their cascading relations "
              "as built, and #20's idempotency rows cascade, bounded by their 30-day expiry.")},
    {"id": "record-ids", "owner": "ROUNDS-02-L02",
     "rule": ("Account data has opaque ids the server makes; a client never picks a canonical id. Content is keyed by (pack, track, slug, "
              "content version). Slugs become aliases through #156's redirect table (slug_redirects), which replaces both slug paths at "
              "62d4eae: getApplication's slug match and the mention index's title slugs.")},
    {"id": "command-ids", "owner": "ROUNDS-02-L02",
     "rule": ("A command_id is a UUIDv7 that #19's SPA client makes per user action. Other actors and #22's retries derive a UUIDv7-shaped "
              "id: the 48-bit time of the source event or job, then 74 bits of SHA-256 over actor kind, handler or consumer name, source "
              "id, and effect index. #124's registered effects hash system and the effect key, timed by the first EffectArmed, so a "
              "re-arm reuses the id. No id hashes the attempt number, and every id passes #19's v7 check and #20's 30-day window. The "
              "bench's derivedId implements this rule and its test checks it against Python's.")},
    {"id": "temporal-kinds", "owner": "ROUNDS-08-L01",
     "rule": ("#44's kinds are stored as: instant, a UTC date field plus an IANA zone in text; local datetime, floating ISO text; calendar "
              "date and all-day, YYYY-MM-DD text, never a date field; partial date, ISO text at its precision plus an approximate flag "
              "or unknown, with a sort key; duration, integer minutes.")},
]

record["invariants"] = [
    {"id": "offer-chain", "row": "offer", "mechanism": ["transaction", "unique-index"], "owningLeaf": "ROUNDS-24-L01",
     "site": "frontend/src/applications/api.ts@62d4eae:L498-L544",
     "detail": ("Creating an offer supersedes the active one, and deleting it revives the prior one, in one command. A partial unique "
                "index allows one active offer per opportunity, so two concurrent creates can't both commit.")},
    {"id": "status-flip", "row": "pursuit", "mechanism": "composed-sub-command", "owningLeaf": "ROUNDS-19-L02",
     "site": "frontend/src/pages/ApplicationDetail.tsx@62d4eae:L119-L211",
     "detail": ("The status change that follows an offer is a sub-command of the offer's command, with its own expected version, instead "
                "of a whole-row write from page state.")},
    {"id": "default-campaign", "row": "campaign-definition", "mechanism": ["transaction", "unique-index"], "owningLeaf": "ROUNDS-25-L01",
     "site": "frontend/src/campaign/CampaignContext.tsx@62d4eae:L127-L138",
     "detail": ("The account bootstrap command creates the Default campaign if it is absent, inside one transaction, and the unique "
                "(user, slug) index backs it (line 299 of the init migration at 62d4eae).")},
    {"id": "junction-pairs", "row": "typed-relation", "mechanism": ["unique-index", "transaction"], "owningLeaf": "ROUNDS-06-L02",
     "site": "frontend/src/experience/connectionApi.ts@62d4eae:L207-L239",
     "detail": ("The browser creates pairs one call at a time, and the pair index leaves out user (1700003000_experience_connections.js, "
                "lines 42 to 59 at 62d4eae). A pair becomes unique per account, on (user, parent, child), with #10's checks and triggers "
                "on both ends, and a merge repoints pairs inside the merge's transaction.")},
]

record["containment"] = [
    {"store": "server-write record, idempotency, and quota state", "leaf": "ROUNDS-00A-L01", "disposition": "ratified",
     "entities": ["admission_commands", "admission_counters", "admission_leases"],
     "detail": "#1's Caller routes and sweep keep these tables; DB5 extends admission_commands for domain commands."},
    {"store": "execution store", "leaf": "ROUNDS-00A-L03", "disposition": "ratified",
     "entities": ["execution_service", "execution_jobs", "execution_attempts", "execution_envelopes"],
     "detail": "#3's routes and its service identity stay as built, at class level."},
    {"store": "legacy artifact snapshots", "leaf": "ROUNDS-00A-L04", "disposition": "ratified", "entities": ["legacy_artifact_snapshots"],
     "detail": "#4's rows and markup files stay where they are; DB10 adopts the files in place."},
    {"store": "render outputs", "leaf": "ROUNDS-00A-L06", "disposition": "path", "owningLeaf": "ROUNDS-00A-L06", "entities": ["account_blobs"],
     "detail": "Held with the containment release; when it ships, #6 writes account_blobs through complete as execution_service."},
    {"store": "definitions journal", "leaf": "ROUNDS-00A-L02", "disposition": "ratified", "entities": ["definition_migration_journal"],
     "detail": "#2's migration journal, written once at start."},
    {"store": "account scope rules", "leaf": "ROUNDS-00B-L01", "disposition": "ratified", "entities": [],
     "detail": "#9's collection rules guard legacy REST writes until each context transfers (DB4)."},
    {"store": "relation quarantine", "leaf": "ROUNDS-00B-L02", "disposition": "ratified", "entities": ["relation_quarantine", "relation_quarantine_reports"],
     "detail": "#10's quarantine and reports, and its predicate and triggers, which DB4 builds on."},
    {"store": "share capabilities", "leaf": "ROUNDS-00B-L03", "disposition": "ratified", "entities": ["share_capabilities"],
     "detail": "#11's capability store, at class level."},
    {"store": "share secrets", "leaf": "ROUNDS-00B-L04", "disposition": "ratified", "entities": ["share_resolvers", "share_throttle"],
     "detail": "#12's resolver identity and throttle, at class level."},
    {"store": "older share links", "leaf": "ROUNDS-00B-L06", "disposition": "ratified", "entities": ["legacy_share_migration"],
     "detail": "#14's migration journal."},
    {"store": "demo account state", "leaf": "ROUNDS-00B-L07", "disposition": "path", "owningLeaf": "ROUNDS-00B-L07", "entities": ["account_system_state"],
     "detail": "#177's stage 2 adds account_system_state, partitioned by user and cascading with the account."},
]

record["storagePlan"] = [
    {"store": "sqlite-data", "location": "pb_data/data.db (with -wal and -shm)",
     "growthAtFloor": f"{gb(db1)} at 1 account and {gb(db10)} at 10 accounts (about {gb(per_account_db)} each), synthetic rows at the floor",
     "writeAmplification": f"{amp or 'pending'} rows per command, weighted over the mix",
     "compaction": ("Expired idempotency rows, relayed outbox rows, and #21's tombstones are #22 due-work, in batches of at most 500 "
                    "rows; SQLite's passive autocheckpoint folds the WAL back, and no job runs a blocking checkpoint under load."),
     "lockBudget": f"hold p99 {ms(hold99)}, queue p99 {ms(queue99)} at the steady rate, a best case; batches at most 500 rows",
     "sizing": (f"The WAL peaked at {mib(wal)}; keep twice the database size free for VACUUM INTO and a restore copy. PocketBase's "
                f"RSS reached {mib(get(S10, 'samplers', 'rssMaxBytes'))} at 10 accounts, so its memory limit is at least 1Gi (#176).")},
    {"store": "files", "location": "pb_data/storage",
     "growthAtFloor": "10 GB per account at the floor (spec 2020-2028); 100 GB at 10 accounts",
     "writeAmplification": "one file and one account_blobs row per stored file",
     "compaction": "#76's purges remove files once the next backup has run; orphans are swept as #22 due-work.",
     "lockBudget": "file writes happen outside the transaction; only the row holds the writer",
     "sizing": ("The shipped 5Gi PVC holds well under one account at the floor. Size pb_data for 10 GB per account plus twice the "
                "database, plus a backup's staging copy; #176 (ROUNDS-34-L07) sets the shipped default from this plan.")},
    {"store": "sqlite-logs", "location": "pb_data/logs.db",
     "growthAtFloor": "bounded by PocketBase's log retention setting",
     "writeAmplification": "one row per logged request, written outside command transactions",
     "compaction": "PocketBase's own retention",
     "lockBudget": "its own file and writer; it never holds the data writer",
     "sizing": "small next to the database; not part of a restore"},
]

record["credentials"] = [
    {"credential": "PocketBase superuser (PB_ADMIN_EMAIL, PB_ADMIN_PASSWORD)", "holder": "superuser",
     "disposition": "No runtime writer uses it. It keeps the bootstrap migration and operator use; #14 S3 removes the runner's unused admin helpers and PB_ADMIN_* from the runner.",
     "leaf": "ROUNDS-00B-L06"},
    {"credential": "ROUNDS_EXECUTION_SECRET", "holder": "execution_service",
     "disposition": "Kept: the execution worker's non-superuser identity, whose login answers only under its collection's exact name; #6 and #91 reuse it.", "leaf": "ROUNDS-00A-L03"},
    {"credential": "ROUNDS_SHARE_RESOLVER_PASSWORD", "holder": "share_resolvers",
     "disposition": "Kept: the share resolver's non-superuser identity, at class level.", "leaf": "ROUNDS-00B-L04"},
    {"credential": "ROUNDS_AI_GATEWAY_SECRET", "holder": "ai_gateway",
     "disposition": f"Planned: #73's provider gateway identity, which takes over the runner's {F['runner']['ai.py']} provider and settings writes.", "leaf": "ROUNDS-14-L02"},
    {"credential": "ROUNDS_DISPATCHER_SECRET", "holder": "dispatcher_service",
     "disposition": "Planned: #22's relay, job queue, and due-work identity.", "leaf": "ROUNDS-02-L05"},
    {"credential": "ROUNDS_ADMISSION_SECRET", "holder": "PocketBase and the runner",
     "disposition": "Kept: the shared key #1's routes require beside the caller's bearer; PocketBase checks it, the runner sends it, and no client holds it.", "leaf": "ROUNDS-00A-L01"},
    {"credential": "AI_KEY_SECRET", "holder": "the runner",
     "disposition": ("Kept: the runner's key for what it seals or keys, stored provider keys among them (docs/operations.md), kept apart "
                     "from the backups (DB8); #73's keyring takes over the provider keys."), "leaf": "ROUNDS-14-L02"},
]

_ratified = [c["leaf"] for c in record["containment"] if c["disposition"] == "ratified"]
_stage = {"ROUNDS-00A-L01": "ROUNDS-00A-L01/S3"}
record["changes"] = [
    {"authority": "containment-stores", "disposition": "ratified in place, and #6's and #177's stores get a path (containment)",
     "dependsOn": sorted(_stage.get(leaf, leaf) for leaf in _ratified),
     "rollback": "Nothing moves, so nothing rolls back; a superseding revision would transfer a store under spec 2699."},
    {"authority": "pocketbase-version", "disposition": f"retain the {LINE} line; P3 moves the pin to 0.22.57; the port to another line waits for a trigger (DB9)",
     "dependsOn": ["ROUNDS-02-L01/P3"],
     "rollback": "P3 rolls back by image tag; the port's boundary is the new binary's first start (DB9)."},
    {"authority": "byte-store", "disposition": "account_blobs in pb_data/storage, deduped per account, read through the gateway (DB10)",
     "dependsOn": ["ROUNDS-10-L01", "ROUNDS-14-L02", "ROUNDS-32-L03", "ROUNDS-14-L05"],
     "rollback": "#53's migration drops account_blobs while it is empty; after files land, a forward fix."},
    {"authority": "authority-matrix-cells", "disposition": "DR-0002@2 fills #16's 85 storage cells and 18 target paths from this record",
     "dependsOn": ["ROUNDS-01-L02"],
     "rollback": "Revert DR-0002@2 while it is unratified; after, a superseding revision."},
    {"authority": "k8s-comment", "disposition": "k8s/pocketbase.yaml's comment drops the Postgres plan and points here",
     "dependsOn": ["ROUNDS-02-L01"],
     "rollback": "Reverting this PR restores the comment; no manifest value changes."},
]

record["exportGate"] = [
    {"item": "this record and its ERD, ratified and indexed by account", "producer": ["ROUNDS-02-L01"]},
    {"item": "the command contracts: request, result, error, aggregate, and state machine", "producer": ["ROUNDS-02-L02", "ROUNDS-02-L03"]},
    {"item": "the authorization matrix, the Audit Entry schema, and the Domain Event catalogue",
     "producer": ["ROUNDS-34-L03", "ROUNDS-00B-L01", "ROUNDS-02-L02", "ROUNDS-02-L04", "ROUNDS-02-L05"]},
    {"item": "the product and leaf non-goals and one fully populated reference issue", "producer": ["ROUNDS-01-L03"]},
]
record["foundationExemption"] = (
    "This leaf produces the gate's first item, so the gate doesn't apply to its own merge (spec 3232-3236). The other three gate "
    "ROUNDS-02's closure and their consumers, not this PR."
)
record["catalogRule"] = (
    "AI proposes typed commands through the validation boundary, like any other client. It never writes canonical storage, and it "
    "never skips an expected version or a review rule."
)
record["exposure"] = (
    "#19's command routes sit behind nginx's existing /api/ pass-through to PocketBase, with no new port, hostname, or route outside "
    "it. Each route authorizes the account inside its transaction (DB4). #19's own PR carries the exposure review."
)

record["baselineFacts"] = [
    {"id": "spa-client", "citation": "frontend/src/lib/pocketbase.ts@62d4eae:L14",
     "now": "11 SPA modules still write through the pb client on next."},
    {"id": "runner-writes-ai", "citation": "backend/routers/ai.py@62d4eae:L367-L542",
     "now": f"{F['runner']['ai.py']} provider and settings writes in ai.py at {AT}, all with the caller's token (DB3)."},
    {"id": "runner-writes-take-home", "citation": "backend/routers/take_home.py@62d4eae:L164-L167",
     "now": (f"{F['runner']['take_home.py']} take-home writes in take_home.py at {AT}, which can't run since #3's PR 4 turned the execution keys on."
             if TAKE_HOME_GATED else f"{F['runner']['take_home.py']} take-home writes in take_home.py at {AT} with the caller's token, until #3's PR 4.")},
    {"id": "runner-writes-share", "citation": "backend/routers/share.py@62d4eae:L1",
     "now": "3 share writes at the audited revision; on next every share write is a hook route."},
    {"id": "pin", "citation": "pocketbase/Dockerfile@62d4eae:L3-L11",
     "now": f"{PIN} at {AT}, with SHA-256 checks for amd64 and arm64."},
    {"id": "sdk", "citation": "frontend/package.json@62d4eae:L29", "now": "^0.26.8, resolved to 0.26.8."},
    {"id": "signup-hook", "citation": "pocketbase/pb_hooks/main.pb.js@62d4eae:L3-L9",
     "now": f"{F['pbjs']} .pb.js files with {F['routes']} routes at {AT}; runInTransaction at {F['tx'][0]} sites."},
    {"id": "admin-bootstrap", "citation": "pocketbase/pb_migrations/1700000500_bootstrap_admin.js@62d4eae:L33-L44",
     "now": f"Unchanged; {F['migrations']} migrations at {AT}, all with new Dao(."},
    {"id": "pb-data-mount", "citation": "docker-compose.prod.yml@62d4eae:L38-L39", "now": "Only pocketbase mounts pb_data."},
    {"id": "k8s", "citation": "k8s/pocketbase.yaml@62d4eae:L2-L68",
     "now": "A 5Gi RWO PVC and one Recreate replica at 500m and 512Mi; this PR fixes the comment at lines 2 to 5."},
    {"id": "runner-replicas", "citation": "k8s/runner.yaml@62d4eae:L30", "now": "2 runner replicas, so DB7 needs its lease."},
    {"id": "backup", "citation": "docs/operations.md@62d4eae:L66-L75",
     "now": "operations.md now stops PocketBase before the tar, so a backup is an outage (DB8)."},
    {"id": "slug-paths", "citation": "frontend/src/applications/api.ts@62d4eae:L329-L346",
     "now": "getApplication still falls back to a slug match, and the mention index keys by title slug (identifiers)."},
    {"id": "nginx", "citation": "frontend/nginx.conf@62d4eae:L17-L41",
     "now": "/api/ passes through to PocketBase, and the runner-only hook routes are refused at the public URL."},
]
record["deferred"] = [
    {"item": "The port to another PocketBase line", "detail": "Waits for a DB9 trigger; it would be its own leaf under scope decision 3, and supersedes this record first."},
    {"item": "The full 10 GB of bytes per account at 10 accounts", "detail": "Extrapolated from a measured 2 GiB sample, labeled extrapolated in the receipt."},
    {"item": "Real cgroup limits", "detail": ("macOS has none; one Go scheduler thread and GOMEMLIMIT stand in, and RSS is reported against "
                                               "512Mi. One core here is more than the 500m quota and never throttles, so throughput, hold "
                                               "times, and lag are a best case for the shipped limits.")},
    {"item": "A CI benchmark job", "detail": "A full run takes about half an hour of one machine, too long for the shared CI pool; CI runs the bench's unit tests."},
    {"item": "Resizing the PVC", "detail": "The storage plan sizes it; #176 sets the shipped default, and only the k8s comment changes here."},
    {"item": "The account delete", "detail": f"The largest single transaction isn't measured here (DB2); #76 ({LEAVES['purge']}) measures it."},
]
if rss and rss > 512 * 1024 ** 2:
    record["deferred"].insert(4, {"item": "PocketBase's memory limit", "detail": (
        f"RSS reached {mib(rss)} at 10 accounts, over the shipped 512Mi (DB1); #176 (ROUNDS-34-L07) ships a limit of at least 1Gi "
        "with its release.")})


def pretty(value, indent: str = "", prefix: str = "", width: int = 140) -> str:
    one = json.dumps(value, ensure_ascii=False)
    if value is None or not isinstance(value, (dict, list)) or len(indent) + len(prefix) + len(one) <= width:
        return one
    inner = indent + "  "
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[\n" + ",\n".join(inner + pretty(x, inner, "") for x in value) + "\n" + indent + "]"
    lines = [inner + json.dumps(k) + ": " + pretty(v, inner, json.dumps(k) + ": ") for k, v in value.items()]
    return "{\n" + ",\n".join(lines) + "\n" + indent + "}"


if __name__ == "__main__":
    OUT.write_text(pretty(record) + "\n")
    print("wrote", OUT.relative_to(ROOT), "receipt" if rc else "NO RECEIPT", "pin", PIN, "result", result, "counted at", AT)
