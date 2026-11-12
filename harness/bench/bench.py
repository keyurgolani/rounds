"""The database benchmark (ROUNDS-02-L01): DR-0004's SQLite analysis.

    python harness/bench/bench.py --accounts 1,10 --out contracts/database/benchmark.json

A non-shipping spike. It runs the pinned PocketBase natively (pbnative.py) on
127.0.0.1 with the repository's own migrations and hooks plus the bench's
overlay (pb_hooks/, pb_migrations/), seeds synthetic accounts at the spec's
scale floor (spec 2020-2028), and measures what spec 2056-2071 asks of the
single SQLite writer: write-lock queueing and hold, WAL checkpoint stalls,
read-your-writes, projection lag through a prototype relay, backup
consistency under load and restore, the freeze of a bounded-context
transfer, and zero accepted writes lost. It writes a receipt per
contracts/database/benchmark.schema.json with pass or fail per target.

Run it on a quiet machine; a full run takes about half an hour. It signals only the processes
it starts, and moves each phase's scratch to the Trash when the phase ends.
Accounts, passwords, and data are generated per run and never printed.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import platform
import random
import shutil
import signal
import sqlite3
import subprocess
import sys
import tarfile
import threading
import time
import traceback
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import benchlib  # noqa: E402
import pbnative  # noqa: E402

BENCH = Path(__file__).resolve().parent
ROOT = pbnative.ROOT
KEY = "x-bench-key"
STOP = threading.Event()


class Bench(Exception):
    pass


# ---------------------------------------------------------------------------
# HTTP: one keep-alive connection per thread, as a browser or runner holds.
# ---------------------------------------------------------------------------

class Conn:
    def __init__(self, port: int, timeout: float = 60):
        self.port = port
        self.timeout = timeout
        self.c: http.client.HTTPConnection | None = None

    def post(self, path: str, body: dict | None = None, token: str | None = None, key: str | None = None) -> tuple[int, dict, float]:
        data = json.dumps(body or {}).encode()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = token
        if key:
            headers[KEY] = key
        for attempt in (0, 1):
            if self.c is None:
                self.c = http.client.HTTPConnection(pbnative.LOOPBACK, self.port, timeout=self.timeout)
            t0 = time.perf_counter()
            try:
                self.c.request("POST", path, body=data, headers=headers)
                r = self.c.getresponse()
                raw = r.read()
                ms = (time.perf_counter() - t0) * 1000
                try:
                    doc = json.loads(raw) if raw else {}
                except ValueError:
                    doc = {"raw": raw[:200].decode(errors="replace")}
                return r.status, doc, ms
            except (http.client.HTTPException, ConnectionError, OSError):
                self.close()
                if attempt:
                    raise
        raise Bench("unreachable")

    def close(self) -> None:
        if self.c is not None:
            try:
                self.c.close()
            except Exception:  # noqa: BLE001
                pass
        self.c = None


# ---------------------------------------------------------------------------
# Accounts and the driver's view of their aggregates.
# ---------------------------------------------------------------------------

class Account:
    def __init__(self, user_id: str, token: str, rng: random.Random):
        self.id = user_id
        self.token = token
        self.lock = threading.Lock()
        self.versions: dict[str, int] = {}
        self.kinds: dict[str, list[str]] = defaultdict(list)
        self.active_offer: dict[str, str] = {}
        self.prior_offer: dict[str, str] = {}
        self.recent: list[dict] = []
        self.rng = rng


def signup(conn: Conn, tag: str) -> tuple[str, str]:
    email = f"bench-{tag}-{os.urandom(4).hex()}@bench.invalid"
    password = benchlib.generated_password()
    s, doc, _ = conn.post("/api/collections/users/records", {"email": email, "password": password, "passwordConfirm": password, "name": f"Bench {tag}"})
    if s != 200:
        raise Bench(f"signup refused ({s}): {doc}")
    s, doc, _ = conn.post("/api/collections/users/auth-with-password", {"identity": email, "password": password})
    if s != 200 or not doc.get("token"):
        raise Bench(f"sign-in refused ({s}): {doc.get('message', '')}")
    return doc["record"]["id"], doc["token"]


# ---------------------------------------------------------------------------
# Seeding at the floor.
# ---------------------------------------------------------------------------

def seed_account(conn: Conn, key: str, acct: Account, fraction: float, rng: random.Random, state: dict) -> dict:
    t0 = time.monotonic()
    counts: dict[str, int] = defaultdict(int)
    batch = 1000

    def send(table: str, columns: list[str], rows: list[list]) -> None:
        for i in range(0, len(rows), batch):
            s, doc, _ = conn.post("/api/bench/seed", {"table": table, "columns": columns, "rows": rows[i:i + batch]}, key=key)
            if s != 200:
                raise Bench(f"seed {table} failed ({s}): {doc}")
        counts[table] += len(rows)

    n = lambda x: max(1, int(round(x * fraction)))  # noqa: E731
    recs, sets, outbox, proj = [], [], [], []
    now = int(time.time() * 1000)
    position = 0
    for kind, count in list(benchlib.FLOOR.items()):
        for _ in range(n(count)):
            rid = benchlib.record_id(rng)
            recs.append([rid, acct.id, kind, 1, "", "", False, benchlib.payload(rng, kind)])
            acct.versions[rid] = 1
            acct.kinds[kind].append(rid)
    for opp in acct.kinds["opportunity"][: n(benchlib.ADDED_OFFERS)]:
        oid = benchlib.record_id(rng)
        recs.append([oid, acct.id, "offer", 1, "active", opp, False, benchlib.payload(rng, "offer")])
        acct.versions[oid] = 1
        acct.active_offer[opp] = oid
    for r in recs:
        position += 1
        state["seq"] += 1
        state["relay_seq"] += 1
        cmd = benchlib.derived_id(now, ["seed", "floor", r[0], "0"])
        sets.append([benchlib.record_id(rng), acct.id, position, state["seq"], cmd, "seed", {r[0]: 1}, [{"op": "insert", "id": r[0], "version": 1}]])
        outbox.append([benchlib.record_id(rng), acct.id, position, 0, state["relay_seq"], benchlib.derived_id(now, ["seed", "event", r[0], "0"]),
                       r[0], 1, r[2] + ".insert", {"version": 1}, now])
        proj.append([benchlib.record_id(rng), acct.id, r[0], r[2], 1, 1, position, now, {"type": r[2] + ".insert"}])
    send("bench_records", ["id", "account_id", "kind", "version", "status", "parent", "deleted", "payload"], recs)
    send("bench_change_sets", ["id", "account_id", "commit_position", "seq", "command_id", "actor", "vector", "ops"], sets)
    send("bench_outbox", ["id", "account_id", "commit_position", "ordinal", "relay_seq", "event_id", "aggregate_id", "aggregate_seq", "type", "payload", "occurred_at"], outbox)
    send("bench_projection", ["id", "account_id", "aggregate_id", "kind", "version", "aggregate_seq", "position", "applied_at", "summary"], proj)
    audit = [[benchlib.record_id(rng), acct.id, "", rng.randint(1, position), "seed", "seed.note", rng.choice(recs)[0], {"synthetic": True}]
             for _ in range(n(benchlib.FLOOR_AUDIT))]
    send("bench_audit", ["id", "account_id", "change_set", "commit_position", "actor", "action", "target", "meta"], audit)
    idem = [[benchlib.record_id(rng), acct.id, benchlib.uuid7(now - rng.randint(0, 29 * 86400 * 1000)), "seed", "completed", {}, now // 1000 + 86400]
            for _ in range(n(benchlib.IDEMPOTENCY_WINDOW_ROWS))]
    send("bench_idempotency", ["id", "account_id", "command_id", "fingerprint", "state", "result", "expires_at"], idem)
    state["position"][acct.id] = position
    # The legacy pipeline, for the transfer: one campaign, applications with
    # their rounds and offers, and todos.
    camp = benchlib.record_id(rng)
    send("campaigns", ["id", "user", "name", "slug", "status"], [[camp, acct.id, "Default", "default", "active"]])
    apps = [benchlib.record_id(rng) for _ in range(n(benchlib.LEGACY_PIPELINE["applications"]))]
    send("applications", ["id", "user", "company", "role", "status", "campaign"], [[a, acct.id, "Synthetic Co", "Engineer", "Applied", camp] for a in apps])
    send("interview_rounds", ["id", "user", "application", "round_type", "campaign"],
         [[benchlib.record_id(rng), acct.id, rng.choice(apps), "phone", camp] for _ in range(n(benchlib.LEGACY_PIPELINE["interview_rounds"]))])
    send("offers", ["id", "user", "application", "status"], [[benchlib.record_id(rng), acct.id, a, "pending"] for a in apps[: n(benchlib.LEGACY_PIPELINE["offers"])]])
    send("todos", ["id", "user", "campaign", "body"], [[benchlib.record_id(rng), acct.id, camp, "synthetic"] for _ in range(n(benchlib.LEGACY_PIPELINE["todos"]))])
    return {"seconds": round(time.monotonic() - t0, 2), "rows": dict(counts)}


def seed_blobs(conn: Conn, key: str, dirs: pbnative.Dirs, acct: Account, total_bytes: int, rng: random.Random) -> dict:
    """The byte store's sample: content-addressed files in pb_data/storage."""
    col = collection_id(dirs, "bench_blobs")
    count = max(1, total_bytes // benchlib.BLOB_SIZE)
    t0 = time.monotonic()
    rows = []
    for _ in range(count):
        data = os.urandom(benchlib.BLOB_SIZE)
        digest = hashlib.sha256(data).hexdigest()
        rid = benchlib.record_id(rng)
        name = f"blob_{digest[:12]}.bin"
        target = dirs.data / "storage" / col / rid / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        rows.append([rid, acct.id, digest, len(data), "Private", 0, name])
    for i in range(0, len(rows), 500):
        s, doc, _ = conn.post("/api/bench/seed", {"table": "bench_blobs", "columns": ["id", "account_id", "sha256", "size", "privacy_class", "retain_until", "file"],
                                                 "rows": rows[i:i + 500]}, key=key)
        if s != 200:
            raise Bench(f"seed blobs failed ({s}): {doc}")
    return {"blobs": count, "bytes": count * benchlib.BLOB_SIZE, "seconds": round(time.monotonic() - t0, 2)}


def collection_id(dirs: pbnative.Dirs, name: str) -> str:
    con = sqlite3.connect(f"file:{dirs.data / 'data.db'}?mode=ro", uri=True)
    try:
        return con.execute("SELECT id FROM _collections WHERE name = ?", (name,)).fetchone()[0]
    finally:
        con.close()


# ---------------------------------------------------------------------------
# The relay (two instances, one lease) and the samplers.
# ---------------------------------------------------------------------------

class Relay(threading.Thread):
    def __init__(self, port: int, key: str, holder: str, ttl_ms: int = 3000, batch: int = 500):
        super().__init__(daemon=True, name=holder)
        self.port, self.key, self.holder, self.ttl_ms, self.batch = port, key, holder, ttl_ms, batch
        self.lags: list[float] = []
        self.applied = self.skipped = self.gaps = self.fenced = self.batches = self.errors = 0
        self.holding = False
        self.crash_before_ack = threading.Event()
        self.crashed = threading.Event()
        self.paused = threading.Event()
        self.stop = threading.Event()
        self.lock = threading.Lock()

    def run(self) -> None:
        conn = Conn(self.port)
        while not self.stop.is_set() and not STOP.is_set():
            if self.paused.is_set():
                time.sleep(0.05)
                continue
            try:
                s, lease, _ = conn.post("/api/bench/relay/lease", {"holder": self.holder, "ttl_ms": self.ttl_ms}, key=self.key)
                self.holding = s == 200 and bool(lease.get("held"))
                if not self.holding:
                    time.sleep(self.ttl_ms / 3000)
                    continue
                s, got, _ = conn.post("/api/bench/relay/read", {"limit": self.batch}, key=self.key)
                events = got.get("events") or []
                if not events:
                    time.sleep(0.05)
                    continue
                s, applied, _ = conn.post("/api/bench/relay/apply", {"events": events}, key=self.key)
                now = time.time() * 1000
                with self.lock:
                    self.lags.extend(now - e["occurred_at"] for e in events)
                    self.applied += applied.get("applied", 0)
                    self.skipped += applied.get("skipped", 0)
                    self.gaps += applied.get("gaps", 0)
                    self.batches += 1
                if self.crash_before_ack.is_set():
                    # mid-relay: the projection has the batch, the cursor
                    # doesn't. The process dies here, lease and all.
                    self.crashed.set()
                    return
                s, ack, _ = conn.post("/api/bench/relay/ack", {"holder": self.holder, "token": lease["token"], "cursor": events[-1]["relay_seq"]}, key=self.key)
                if not ack.get("acked"):
                    with self.lock:
                        self.fenced += 1
            except Exception:  # noqa: BLE001
                with self.lock:
                    self.errors += 1
                conn.close()
                time.sleep(0.2)
        conn.close()

    def take_lags(self) -> list[float]:
        with self.lock:
            out, self.lags = self.lags, []
        return out


class Sampler(threading.Thread):
    """WAL file size every 100 ms and the server's RSS every second. It reads
    the server's pid each time, so a restart (the crash, the stop-and-tar, the
    schema change) keeps the RSS samples coming."""

    def __init__(self, dirs: pbnative.Dirs, server: pbnative.Server):
        super().__init__(daemon=True, name="sampler")
        self.dirs, self.server = dirs, server
        self.wal: list[tuple[float, int]] = []
        self.rss: list[int] = []
        self.stop = threading.Event()

    def run(self) -> None:
        wal = self.dirs.data / "data.db-wal"
        tick = 0
        while not self.stop.is_set() and not STOP.is_set():
            try:
                self.wal.append((time.time(), wal.stat().st_size))
            except FileNotFoundError:
                self.wal.append((time.time(), 0))
            pid = self.server.pid
            if tick % 10 == 0 and pid:
                out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
                if out.isdigit():
                    self.rss.append(int(out) * 1024)
            tick += 1
            time.sleep(0.1)

    def summary(self) -> dict:
        sizes = [s for _, s in self.wal]
        drops = sum(1 for a, b in zip(sizes, sizes[1:]) if b < a)
        return {"walMaxBytes": max(sizes) if sizes else 0, "walTruncations": drops, "rssMaxBytes": max(self.rss) if self.rss else 0,
                "rssSamples": len(self.rss)}


# ---------------------------------------------------------------------------
# The load: closed-loop clients running the mix.
# ---------------------------------------------------------------------------

class Load:
    def __init__(self, port: int, accounts: list[Account], seed: int):
        self.port = port
        self.accounts = accounts
        self.rng = random.Random(seed)
        self.lock = threading.Lock()
        self.records: list[dict] = []
        self.acked: list[tuple[str, str, int, float]] = []
        self.frozen_refusals = 0
        self.unknown = 0

    def _command(self, conn: Conn, acct: Account, rng: random.Random, kind: str) -> dict:
        if kind.startswith("bg_"):
            s, doc, ms = conn.post("/api/bench/background", {"kind": kind[3:]}, token=acct.token)
            return {"type": kind, "status": s, "client_ms": ms, "writes": doc.get("writes", 0), "timing": doc.get("timing") or {}}
        body = None
        with acct.lock:
            if kind == "replay" and acct.recent:
                body = dict(rng.choice(acct.recent))
            elif kind == "conflict":
                stale = [i for i, v in acct.versions.items() if v >= 2]
                if stale:
                    i = rng.choice(stale)
                    body = {"type": "update", "expected": {i: acct.versions[i] - 1}, "args": {"id": i, "payload": {"n": rng.random()}}}
            elif kind == "compose" and acct.active_offer:
                opp = rng.choice(list(acct.active_offer))
                off = acct.active_offer[opp]
                body = {"type": "compose", "expected": {opp: acct.versions[opp], off: acct.versions[off]}, "args": {"opportunity": opp, "offer": off, "payload": {"n": rng.random()}}}
            elif kind == "delete_revive" and acct.prior_offer:
                opp = rng.choice(list(acct.prior_offer))
                off, prev = acct.active_offer[opp], acct.prior_offer[opp]
                body = {"type": "delete_revive", "expected": {opp: acct.versions[opp], off: acct.versions[off], prev: acct.versions[prev]},
                        "args": {"opportunity": opp, "offer": off, "prior": prev}}
            elif kind == "create":
                body = {"type": "create", "expected": {}, "args": {"kind": rng.choice(["fact", "activity", "person"]), "payload": benchlib.payload(rng, "fact")}}
            if body is None:
                kind = "update"
                i = rng.choice(acct.kinds[rng.choice(["fact", "activity", "person", "attempt"])])
                body = {"type": "update", "expected": {i: acct.versions[i]}, "args": {"id": i, "payload": benchlib.payload(rng, "fact")}}
            if "command_id" not in body:
                body["command_id"] = benchlib.uuid7()
        s, doc, ms = conn.post("/api/bench/command", body, token=acct.token)
        rec = {"type": kind, "status": s, "client_ms": ms, "writes": doc.get("writes", 0), "timing": doc.get("timing") or {},
               "error": doc.get("error"), "replay": bool(doc.get("replay")), "position": doc.get("commit_position"), "body": body,
               "versions": doc.get("versions") or {}}
        if s == 200 and not doc.get("replay"):
            with acct.lock:
                for i, v in (doc.get("versions") or {}).items():
                    acct.versions[i] = v
                if body["type"] == "compose":
                    opp, old = body["args"]["opportunity"], body["args"]["offer"]
                    new = [i for i in doc["versions"] if i not in body["expected"]][0]
                    acct.prior_offer[opp], acct.active_offer[opp] = old, new
                elif body["type"] == "delete_revive":
                    opp = body["args"]["opportunity"]
                    acct.active_offer[opp] = body["args"]["prior"]
                    acct.prior_offer.pop(opp, None)
                elif body["type"] == "create":
                    for i in doc["versions"]:
                        acct.kinds[body["args"]["kind"]].append(i)
                acct.recent.append({k: body[k] for k in ("command_id", "type", "expected", "args")})
                if len(acct.recent) > 200:
                    acct.recent.pop(0)
            with self.lock:
                self.acked.append((acct.id, body["command_id"], doc.get("commit_position") or 0, time.time()))
        elif s == 409 and doc.get("error") == "stale_version":
            with acct.lock:
                for i, v in (doc.get("current") or {}).items():
                    acct.versions[i] = v
        elif s == 503 and doc.get("error") == "frozen":
            with self.lock:
                self.frozen_refusals += 1
        return rec

    def run(self, clients: int, seconds: float, rate: float | None = None, probe=None, probe_every: int = 5,
            until: threading.Event | None = None) -> list[dict]:
        """Closed loop, or open at `rate` commands per second in total, for
        `seconds` or until `until` is set."""
        out: list[dict] = []
        deadline = time.monotonic() + seconds
        interval = (clients / rate) if rate else 0.0

        def worker(n: int) -> None:
            # A long timeout: a command waiting behind a held writer (a backup
            # that zips under a transaction) is a measurement, not a failure.
            conn = Conn(self.port, timeout=900)
            rng = random.Random(self.rng.random())
            i = 0
            next_at = time.monotonic()
            while time.monotonic() < deadline and not STOP.is_set() and not (until and until.is_set()):
                if interval:
                    next_at += interval
                    delay = next_at - time.monotonic()
                    if delay > 0:
                        time.sleep(delay)
                acct = rng.choice(self.accounts)
                try:
                    rec = self._command(conn, acct, rng, benchlib.pick(benchlib.MIX, rng))
                except Exception:  # noqa: BLE001
                    with self.lock:
                        self.unknown += 1
                    conn.close()
                    time.sleep(0.05)
                    continue
                rec["at"] = time.time()
                with self.lock:
                    out.append(rec)
                    self.records.append(rec)
                i += 1
                if probe and rec["status"] == 200 and rec.get("position") and not rec["replay"] and i % probe_every == 0:
                    probe(acct, rec)
            conn.close()

        threads = [threading.Thread(target=worker, args=(n,), daemon=True) for n in range(clients)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=seconds + 120)
        return out


def summarize_records(recs: list[dict], seconds: float) -> dict:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        by_type[r["type"]].append(r)
    ok = [r for r in recs if r["status"] == 200]
    writes_by_type = {t: [r["writes"] for r in rs if r["status"] == 200] for t, rs in by_type.items()}
    return {
        "commands": len(recs),
        "perSecond": round(len(ok) / seconds, 1) if seconds else None,
        "statuses": {str(s): sum(1 for r in recs if r["status"] == s) for s in sorted({r["status"] for r in recs})},
        "clientMs": benchlib.summarize([r["client_ms"] for r in ok]),
        "queueMs": benchlib.summarize([r["timing"].get("queue_ms", 0) for r in ok if r["timing"]]),
        "holdMs": benchlib.summarize([r["timing"].get("hold_ms", 0) for r in ok if r["timing"]]),
        "writesByType": {t: (round(sum(v) / len(v), 2) if v else None) for t, v in writes_by_type.items()},
        "writeAmplification": benchlib.weighted_amplification(writes_by_type),
        "conflicts": sum(1 for r in recs if r.get("error") == "stale_version"),
        "replays": sum(1 for r in recs if r.get("replay")),
    }


# ---------------------------------------------------------------------------
# Verification on a copy (read-only SQLite) and restores.
# ---------------------------------------------------------------------------

def verify(data_dir: Path, acked: list[tuple[str, str, int, float]] | None, blobs: bool) -> dict:
    db = data_dir / "data.db"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        out: dict = {"quickCheck": con.execute("PRAGMA quick_check").fetchone()[0]}
        present = set(con.execute("SELECT account_id || ':' || command_id FROM bench_idempotency WHERE state = 'completed'").fetchall())
        present = {p[0] for p in present}
        if acked is not None:
            missing = [a for a in acked if f"{a[0]}:{a[1]}" not in present]
            out["ackedChecked"] = len(acked)
            out["ackedMissing"] = len(missing)
        out["changeSetsWithoutIdempotency"] = con.execute(
            "SELECT COUNT(*) FROM bench_change_sets cs WHERE cs.actor LIKE 'user:%' AND NOT EXISTS (SELECT 1 FROM bench_idempotency i "
            "WHERE i.account_id = cs.account_id AND i.command_id = cs.command_id)").fetchone()[0]
        out["idempotencyWithoutChangeSet"] = con.execute(
            "SELECT COUNT(*) FROM bench_idempotency i WHERE i.state = 'completed' AND i.fingerprint != 'seed' AND NOT EXISTS (SELECT 1 FROM bench_change_sets cs "
            "WHERE cs.account_id = i.account_id AND cs.command_id = i.command_id)").fetchone()[0]
        out["changeSetsWithWrongOutbox"] = con.execute(
            "SELECT COUNT(*) FROM bench_change_sets cs WHERE cs.actor LIKE 'user:%' AND json_array_length(cs.ops) != (SELECT COUNT(*) FROM bench_outbox o "
            "WHERE o.account_id = cs.account_id AND o.commit_position = cs.commit_position)").fetchone()[0]
        out["activeOfferDuplicates"] = con.execute(
            "SELECT COUNT(*) FROM (SELECT parent FROM bench_records WHERE kind = 'offer' AND status = 'active' GROUP BY parent HAVING COUNT(*) > 1)").fetchone()[0]
        if blobs:
            col = con.execute("SELECT id FROM _collections WHERE name = 'bench_blobs'").fetchone()[0]
            bad = 0
            rows = con.execute("SELECT id, sha256, file FROM bench_blobs").fetchall()
            for rid, digest, name in rows:
                path = data_dir / "storage" / col / rid / name
                if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    bad += 1
            out["blobsChecked"], out["blobsBad"] = len(rows), bad
    finally:
        con.close()
    out["consistent"] = (out["quickCheck"] == "ok" and out.get("ackedMissing", 0) == 0 and out["changeSetsWithoutIdempotency"] == 0
                         and out["idempotencyWithoutChangeSet"] == 0 and out["changeSetsWithWrongOutbox"] == 0
                         and out["activeOfferDuplicates"] == 0 and out.get("blobsBad", 0) == 0)
    return out


def tree_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def restore_and_check(binary: Path, label: str, fill, acked, blobs: bool, env: dict) -> dict:
    """Restores a backup into a fresh scratch dir with fill(data_dir), starts
    PocketBase on it, and verifies the copy. Returns the timings."""
    root = pbnative.run_dir(f"restore-{label}")
    try:
        dirs, _ = pbnative.prepare(root, extra_migrations=BENCH / "pb_migrations", extra_hooks=BENCH / "pb_hooks")
        t0 = time.monotonic()
        fill(dirs.data)
        copy_s = time.monotonic() - t0
        server = pbnative.Server(binary, dirs, env)
        try:
            start_s = server.start(timeout=600)
            if not server.listening_on_loopback_only():
                raise Bench("restored server is not on loopback only")
        finally:
            server.stop()
        t1 = time.monotonic()
        result = verify(dirs.data, acked, blobs)
        verify_s = time.monotonic() - t1
        return {"method": label, "copySeconds": round(copy_s, 2), "startSeconds": round(start_s, 2), "verifySeconds": round(verify_s, 2),
                "restoreSeconds": round(copy_s + start_s + verify_s, 2), "bytes": tree_bytes(dirs.data), **result}
    finally:
        pbnative.to_trash(root, f"restore-{label}")


# ---------------------------------------------------------------------------
# One scale.
# ---------------------------------------------------------------------------

def run_scale(args, binary: Path, n_accounts: int) -> dict:
    out: dict = {"accounts": n_accounts}
    rng = random.Random(1800 + n_accounts)
    root = pbnative.run_dir(f"scale{n_accounts}")
    key = os.urandom(24).hex()
    env = {"GOMAXPROCS": "1", "GOMEMLIMIT": args.gomemlimit, "ROUNDS_GATE_SIGNUPS": "enabled", "BENCH_KEY": key,
           "BENCH_FAILPOINTS": "1", "BENCH_SCRATCH": str(pbnative.SCRATCH)}
    restore_env = {"GOMAXPROCS": "1", "GOMEMLIMIT": args.gomemlimit, "BENCH_KEY": key, "BENCH_SCRATCH": str(pbnative.SCRATCH)}
    server = relays = sampler = None
    try:
        dirs, note = pbnative.prepare(root, extra_migrations=BENCH / "pb_migrations", extra_hooks=BENCH / "pb_hooks")
        out["overlay"] = note
        server = pbnative.Server(binary, dirs, env)
        out["firstStartSeconds"] = round(server.start(timeout=600), 2)
        if not server.listening_on_loopback_only():
            raise Bench("PocketBase is not listening on 127.0.0.1 only")
        conn = Conn(server.port)
        # A throwaway admin for PocketBase's own backup API, made through its
        # first-admin route on this loopback server (the password never goes
        # on a command line).
        admin_email = f"bench-admin-{os.urandom(4).hex()}@bench.invalid"
        admin_password = benchlib.generated_password()
        s, doc, _ = conn.post("/api/admins", {"email": admin_email, "password": admin_password, "passwordConfirm": admin_password})
        if s != 200:
            raise Bench(f"could not make the bench admin ({s}): {doc.get('message', '')}")
        s, pragmas, _ = conn.post("/api/bench/pragmas", {}, key=key)
        out["pragmas"] = pragmas
        accounts = []
        for i in range(n_accounts):
            uid, token = signup(conn, f"{n_accounts}-{i}")
            accounts.append(Account(uid, token, random.Random(rng.random())))
        state = {"seq": 0, "relay_seq": 0, "position": {}}
        seeds = [seed_account(conn, key, a, args.fraction, rng, state) for a in accounts]
        # Seeded events count as already relayed.
        s, _, _ = conn.post("/api/bench/seed", {"table": "bench_checkpoints", "columns": ["id", "name", "last_seq", "updated_at"],
                                                "rows": [[benchlib.record_id(rng), "relay", state["relay_seq"], int(time.time() * 1000)]]}, key=key)
        out["seed"] = {"fraction": args.fraction, "seconds": round(sum(x["seconds"] for x in seeds), 2),
                       "rowsPerAccount": seeds[0]["rows"], "rowsTotal": sum(sum(x["rows"].values()) for x in seeds)}
        blob_info = None
        if n_accounts == 1 and args.bytes_mb:
            blob_info = seed_blobs(conn, key, dirs, accounts[0], args.bytes_mb * 1024 * 1024, rng)
            out["bytesSample"] = blob_info
        db_bytes = (dirs.data / "data.db").stat().st_size
        out["databaseBytes"] = db_bytes
        relays = [Relay(server.port, key, "relay-a"), Relay(server.port, key, "relay-b")]
        for r in relays:
            r.start()
        sampler = Sampler(dirs, server)
        sampler.start()
        load = Load(server.port, accounts, rng.randint(0, 10**9))

        # 1. The concurrency sweep (closed loop): lock queueing and hold.
        sweep = {}
        for clients in args.sweep:
            recs = load.run(clients, args.sweep_seconds)
            sweep[str(clients)] = summarize_records(recs, args.sweep_seconds)
            for r in relays:
                r.take_lags()
        out["sweep"] = sweep

        # 2. Steady load at a normal rate, with read-your-writes probes.
        ryw: list[float] = []
        fallbacks = [0]
        probes: list[threading.Thread] = []

        def probe(acct: Account, rec: dict) -> None:
            def watch() -> None:
                conn2 = Conn(server.port)
                target = next(iter(rec["versions"]))
                t0 = rec["at"]
                try:
                    while time.time() - t0 < 5.0 and not STOP.is_set():
                        s, doc, _ = conn2.post("/api/bench/projection", {"aggregate_id": target, "min_position": rec["position"]}, token=acct.token)
                        if s == 200 and doc.get("reached"):
                            ryw.append((time.time() - t0) * 1000)
                            return
                        time.sleep(0.02)
                    fallbacks[0] += 1
                finally:
                    conn2.close()
            t = threading.Thread(target=watch, daemon=True)
            t.start()
            probes.append(t)

        recs = load.run(args.steady_clients, args.steady_seconds, rate=args.steady_rate, probe=probe)
        for t in probes:
            t.join(timeout=10)
        lags = [x for r in relays for x in r.take_lags()]
        out["steady"] = summarize_records(recs, args.steady_seconds)
        out["steady"].update({"rate": args.steady_rate, "relayLagMs": benchlib.summarize(lags), "readYourWritesMs": benchlib.summarize(ryw),
                              "readYourWritesFallbacks": fallbacks[0], "probes": len(probes)})

        # 3. Backups under load, each restored and checked.
        backups = []
        backups_done = threading.Event()
        bg = threading.Thread(target=lambda: load.run(args.steady_clients, 3600, rate=args.steady_rate, until=backups_done), daemon=True)
        bg.start()
        time.sleep(2)
        with load.lock:
            acked_before = list(load.acked)
        # 3a. VACUUM INTO, inside PocketBase (an online SQLite-consistent copy).
        vac = pbnative.run_dir("backup-vacuum")
        copy_path = vac / "data.db"
        n_before = len(load.records)
        s, doc, _ = conn.post("/api/bench/vacuum-into", {"path": str(copy_path)}, key=key)
        vac_ms = doc.get("ms")
        storage_copy_s = None
        if blob_info:
            t0 = time.monotonic()
            shutil.copytree(dirs.data / "storage", vac / "storage")
            storage_copy_s = time.monotonic() - t0
        during = load.records[n_before:]
        backups.append({"method": "vacuum-into", "status": s, "ms": vac_ms, "storageCopySeconds": storage_copy_s,
                        "holdMsDuring": benchlib.summarize([r["timing"].get("hold_ms", 0) for r in during if r["timing"]]),
                        "queueMsDuring": benchlib.summarize([r["timing"].get("queue_ms", 0) for r in during if r["timing"]])})
        # 3b. An external reader with SQLite's backup API (a sidecar or CLI).
        ext = pbnative.run_dir("backup-reader")
        n_before = len(load.records)
        t0 = time.monotonic()
        src = sqlite3.connect(f"file:{dirs.data / 'data.db'}?mode=ro", uri=True)
        dst = sqlite3.connect(str(ext / "data.db"))
        src.backup(dst)
        dst.close()
        src.close()
        ext_s = time.monotonic() - t0
        during = load.records[n_before:]
        backups.append({"method": "sqlite-backup-api", "seconds": round(ext_s, 2),
                        "queueMsDuring": benchlib.summarize([r["timing"].get("queue_ms", 0) for r in during if r["timing"]])})
        # 3c. PocketBase's own backup (a zip of pb_data).
        n_before = len(load.records)
        s, doc, _ = conn.post("/api/admins/auth-with-password", {"identity": admin_email, "password": admin_password})
        admin_token = doc.get("token")
        t0 = time.monotonic()
        s_bk, doc_bk, _ = Conn(server.port, timeout=3600).post("/api/backups", {"name": "bench.zip"}, token=admin_token)
        pb_s = time.monotonic() - t0
        during = load.records[n_before:]
        zip_path = dirs.data / "backups" / "bench.zip"
        backups.append({"method": "pocketbase-backup-api", "status": s_bk, "seconds": round(pb_s, 2), "zipBytes": zip_path.stat().st_size if zip_path.exists() else None,
                        "queueMsDuring": benchlib.summarize([r["timing"].get("queue_ms", 0) for r in during if r["timing"]]),
                        "holdMsDuring": benchlib.summarize([r["timing"].get("hold_ms", 0) for r in during if r["timing"]])})
        backups_done.set()
        bg.join(timeout=120)
        out["backups"] = backups
        # Restores, each verified against what was acked before the backup.
        restores = []

        def fill_vac(target: Path) -> None:
            shutil.copy2(copy_path, target / "data.db")
            if (vac / "storage").exists():
                shutil.copytree(vac / "storage", target / "storage")

        restores.append(restore_and_check(binary, "vacuum-into", fill_vac, acked_before, bool(blob_info), restore_env))
        restores.append(restore_and_check(binary, "sqlite-backup-api", lambda t: shutil.copy2(ext / "data.db", t / "data.db"), acked_before, False, restore_env))
        if zip_path.exists():
            def fill_zip(target: Path) -> None:
                with zipfile.ZipFile(zip_path) as z:
                    z.extractall(target)
            restores.append(restore_and_check(binary, "pocketbase-backup-api", fill_zip, acked_before, bool(blob_info), restore_env))
        out["restores"] = restores
        pbnative.to_trash(vac, "backup-vacuum")
        pbnative.to_trash(ext, "backup-reader")
        if zip_path.exists():
            moved = pbnative.run_dir("backup-zip")
            shutil.move(str(zip_path), str(moved / "bench.zip"))
            pbnative.to_trash(moved, "backup-zip")

        # 4. Failpoints (#19 to #23): before commit, after commit before relay, mid relay.
        if args.failpoints:
            out["failpoints"] = run_failpoints(server, conn, key, load, accounts, relays, dirs, rng)

        # 5. A crash mid-load: kill -9, restart, and every acked write is there.
        crash_load = threading.Thread(target=lambda: load.run(args.steady_clients, 6, rate=args.steady_rate), daemon=True)
        crash_load.start()
        time.sleep(3)
        with load.lock:
            acked_before_kill = list(load.acked)
        server.kill9()
        crash_load.join(timeout=60)
        restart_s = server.start(timeout=600)
        out["crash"] = {"restartSeconds": round(restart_s, 2), **verify(dirs.data, acked_before_kill, False)}

        # 6. The freeze: one bounded context's transfer under a write freeze,
        # with the freeze-start backup as the rollback point.
        t_freeze = time.monotonic()
        conn.post("/api/bench/freeze", {"on": True}, key=key)
        frozen_at = time.time()
        # A command already inside its transaction finishes; give it a second.
        time.sleep(1.0)
        with load.lock:
            acked_before_freeze = list(load.acked)
            refusals_before = load.frozen_refusals
        rollback = pbnative.run_dir("freeze-rollback")
        s, doc, _ = conn.post("/api/bench/vacuum-into", {"path": str(rollback / "data.db")}, key=key)
        backup_ms = doc.get("ms")
        storage_s = 0.0
        if blob_info:
            t0 = time.monotonic()
            shutil.copytree(dirs.data / "storage", rollback / "storage")
            storage_s = time.monotonic() - t0
        # Clients keep sending during the freeze; every one must be refused.
        freeze_clients = threading.Thread(target=lambda: load.run(2, 5, rate=10), daemon=True)
        freeze_clients.start()
        transfer = {"applications": 0, "rows": 0, "batches": 0}
        t_tr = time.monotonic()
        batch_ms: list[float] = []
        for acct in accounts:
            after = ""
            while not STOP.is_set():
                s, doc, ms = conn.post("/api/bench/transfer", {"account": acct.id, "after": after, "limit": args.transfer_batch}, key=key)
                if s != 200:
                    raise Bench(f"transfer failed ({s}): {doc}")
                batch_ms.append(doc.get("timing", {}).get("hold_ms", 0))
                transfer["applications"] += doc["applications"]
                transfer["rows"] += doc["rows"]
                transfer["batches"] += 1
                after = doc["cursor"]
                if doc["done"]:
                    break
        transfer["seconds"] = round(time.monotonic() - t_tr, 2)
        transfer["batchHoldMs"] = benchlib.summarize(batch_ms)
        freeze_clients.join(timeout=60)
        thawed_at = time.time()
        conn.post("/api/bench/freeze", {"on": False}, key=key)
        freeze_s = time.monotonic() - t_freeze
        with load.lock:
            accepted_during = [a for a in load.acked if frozen_at + 1.0 < a[3] < thawed_at]
            refused_during = load.frozen_refusals - refusals_before

        def fill_rollback(target: Path) -> None:
            shutil.copy2(rollback / "data.db", target / "data.db")
            if (rollback / "storage").exists():
                shutil.copytree(rollback / "storage", target / "storage")

        rollback_check = restore_and_check(binary, "freeze-rollback", fill_rollback, acked_before_freeze, bool(blob_info), restore_env)
        pbnative.to_trash(rollback, "freeze-rollback")
        out["freeze"] = {"seconds": round(freeze_s, 2), "backupMs": backup_ms, "storageCopySeconds": round(storage_s, 2), "transfer": transfer,
                         "acceptedDuringFreeze": len(accepted_during), "refusedDuringFreeze": refused_during, "rollback": rollback_check}

        # 7. Stop-and-tar (operations.md today): the stop lasts as long as the archive.
        tar_root = pbnative.run_dir("backup-tar")
        t_stop = time.monotonic()
        for r in relays:
            r.paused.set()
        server.stop()
        archive = tar_root / "pb_data.tar.gz"
        # gzip at its default level 6, as operations.md's tar czf does.
        with tarfile.open(archive, "w:gz", compresslevel=6) as tar:
            tar.add(str(dirs.data), arcname="pb_data")
        tar_s = time.monotonic() - t_stop
        start_s = server.start(timeout=600)
        for r in relays:
            r.paused.clear()
        out["stopAndTar"] = {"archiveSeconds": round(tar_s, 2), "startSeconds": round(start_s, 2), "downtimeSeconds": round(time.monotonic() - t_stop, 2),
                             "archiveBytes": archive.stat().st_size}

        def fill_tar(target: Path) -> None:
            with tarfile.open(archive) as tar:
                tar.extractall(target.parent / "extract", filter="data")
            for item in (target.parent / "extract" / "pb_data").iterdir():
                shutil.move(str(item), str(target / item.name))

        out["restores"].append(restore_and_check(binary, "stop-and-tar", fill_tar, acked_before_freeze, bool(blob_info), restore_env))
        pbnative.to_trash(tar_root, "backup-tar")

        # 8. A startup schema migration: the downtime is the next start.
        if args.schema_change:
            for r in relays:
                r.paused.set()
            server.stop()
            shutil.copy2(BENCH / "pb_migrations_later" / "1800000100_bench_schema_change.js", dirs.migrations)
            t0 = time.monotonic()
            start_s = server.start(timeout=1800)
            out["schemaChange"] = {"startSeconds": round(start_s, 2), "rows": sum(sum(x["rows"].values()) for x in seeds),
                                   "downtimeSeconds": round(time.monotonic() - t0, 2)}
            for r in relays:
                r.paused.clear()
        out["samplers"] = sampler.summary()
        out["relays"] = [{"holder": r.holder, "applied": r.applied, "skipped": r.skipped, "gaps": r.gaps, "fenced": r.fenced, "errors": r.errors} for r in relays]
        out["unknownOutcomes"] = load.unknown
    except Exception as err:
        # What the scale got through, and the server's own last words, go
        # into the partial results before the scratch dir moves to the Trash.
        out["error"] = str(err)
        out["pocketbaseLogTail"] = server.tail() if server else ""
        err.partial = out  # type: ignore[attr-defined]
        raise
    finally:
        for r in relays or []:
            r.stop.set()
        if sampler:
            sampler.stop.set()
        if server:
            server.stop()
        pbnative.to_trash(root, f"scale{n_accounts}")
    return out


def run_failpoints(server, conn, key, load, accounts, relays, dirs, rng) -> dict:
    acct = accounts[0]
    out: dict = {}
    # before-commit: nothing persists, and a retry commits once.
    ok = True
    for _ in range(10):
        i = rng.choice(acct.kinds["fact"])
        body = {"command_id": benchlib.uuid7(), "type": "update", "expected": {i: acct.versions[i]}, "args": {"id": i, "payload": {}}}
        s1, d1, _ = conn.post("/api/bench/command", dict(body, failpoint="before-commit"), token=acct.token)
        s2, d2, _ = conn.post("/api/bench/command", body, token=acct.token)
        s3, d3, _ = conn.post("/api/bench/command", body, token=acct.token)
        ok = ok and s1 == 503 and d1.get("failpoint") == "before-commit" and s2 == 200 and not d2.get("replay") and d3.get("replay") is True
        if s2 == 200:
            acct.versions.update(d2.get("versions") or {})
    out["beforeCommit"] = {"commands": 10, "passed": ok}
    # after-commit-before-relay: commit, kill -9 before the relay runs, restart.
    for r in relays:
        r.paused.set()
    acked = []
    for _ in range(20):
        i = rng.choice(acct.kinds["fact"])
        body = {"command_id": benchlib.uuid7(), "type": "update", "expected": {i: acct.versions[i]}, "args": {"id": i, "payload": {}}}
        s, d, _ = conn.post("/api/bench/command", body, token=acct.token)
        if s == 200:
            acct.versions.update(d.get("versions") or {})
            acked.append((acct.id, body["command_id"], d["commit_position"], time.time(), i, d["versions"][i]))
    server.kill9()
    server.start(timeout=600)
    conn.close()
    for r in relays:
        r.paused.clear()
    deadline = time.time() + 30
    projected = 0
    conn2 = Conn(server.port)
    for a in acked:
        while time.time() < deadline:
            s, d, _ = conn2.post("/api/bench/projection", {"aggregate_id": a[4], "min_position": a[2]}, token=acct.token)
            if s == 200 and d.get("reached") and d.get("version") >= a[5]:
                projected += 1
                break
            time.sleep(0.05)
    conn2.close()
    present = verify(dirs.data, [a[:4] for a in acked], False)
    out["afterCommitBeforeRelay"] = {"commands": len(acked), "projectedOnce": projected, "ackedMissing": present["ackedMissing"],
                                     "passed": projected == len(acked) and present["ackedMissing"] == 0}
    # mid-relay: the active relay applies a batch and dies before its ack;
    # the other takes the lease after it expires and redelivers.
    deadline = time.time() + 15
    while time.time() < deadline and not any(r.holding and r.is_alive() for r in relays):
        time.sleep(0.05)
    active = next((r for r in relays if r.holding and r.is_alive()), relays[0])
    skipped_before = sum(r.skipped for r in relays)
    active.crash_before_ack.set()
    for _ in range(20):
        i = rng.choice(acct.kinds["fact"])
        body = {"command_id": benchlib.uuid7(), "type": "update", "expected": {i: acct.versions[i]}, "args": {"id": i, "payload": {}}}
        s, d, _ = conn.post("/api/bench/command", body, token=acct.token)
        if s == 200:
            acct.versions.update(d.get("versions") or {})
    active.crashed.wait(timeout=30)
    time.sleep(active.ttl_ms / 1000 + 2)
    skipped_after = sum(r.skipped for r in relays)
    survivor = [r for r in relays if r is not active][0]
    replacement = Relay(server.port, key, active.holder + "-restarted")
    replacement.start()
    relays[relays.index(active)] = replacement
    out["midRelay"] = {"crashed": active.crashed.is_set(), "redeliveredSkipped": skipped_after - skipped_before,
                       "survivorFenced": survivor.fenced, "passed": active.crashed.is_set() and skipped_after > skipped_before}
    return out


def disk_kind() -> str:
    out = subprocess.run(["diskutil", "info", "/"], capture_output=True, text=True).stdout
    flat = " ".join(out.split())
    solid = "Solid State: Yes" in flat
    fs = next((l.split(":", 1)[1].strip() for l in out.splitlines() if "File System Personality" in l), "unknown")
    return ("SSD" if solid else "disk") + f" ({fs})"


def profile(binary: Path) -> dict:
    def sysctl(name: str) -> str:
        return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True).stdout.strip()
    dockerfile = (ROOT / "pocketbase" / "Dockerfile").read_text()
    pin = {}
    for k in ("PB_VERSION", "PB_SHA256", "PB_SHA256_ARM64"):
        line = next((l for l in dockerfile.splitlines() if l.startswith(f"ARG {k}=")), "")
        pin[k] = line.split("=", 1)[1] if line else None
    k8s = benchlib.parse_k8s_limits((ROOT / "k8s" / "pocketbase.yaml").read_text())
    rev = subprocess.run(["git", "--no-optional-locks", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {
        "hardware": {"cpu": sysctl("machdep.cpu.brand_string"), "cores": int(sysctl("hw.ncpu") or 0),
                     "memoryBytes": int(sysctl("hw.memsize") or 0), "os": f"macOS {platform.mac_ver()[0]}", "arch": platform.machine(),
                     "storage": disk_kind()},
        "pocketbase": {"version": pbnative.binary_version(binary), "binarySha256": pbnative.sha256_file(binary), "dockerfilePin": pin},
        "k8sLimits": k8s,
        "emulation": {"GOMAXPROCS": 1, "note": "macOS has no cgroups: the 500m CPU limit is approximated with one Go scheduler thread and the memory limit with GOMEMLIMIT; RSS is reported against 512Mi"},
        "revision": rev,
        "loadAverageAtStart": os.getloadavg(),
        "sharedMachine": "a shared machine, not an exclusive one: other workloads may have run during the measurement, so the load averages at start and end are recorded",
    }


def build_receipt(prof: dict, scales: dict, args, started: float) -> dict:
    big = scales.get("10") or scales[max(scales, key=int)]
    small = scales.get("1") or big
    st = big["steady"]
    ryw = st["readYourWritesMs"]
    verdicts = [
        benchlib.verdict("read_your_writes", ryw.get("p99"), "measured",
                         f"p99 of {ryw.get('n', 0)} projection reads at {args.steady_rate}/s and {big['accounts']} accounts; "
                         f"{st['readYourWritesFallbacks']} took the canonical fallback",
                         passed=(ryw.get("p99") is not None and ryw["p99"] <= 5000)),
        benchlib.verdict("projection_lag_p95", st["relayLagMs"].get("p95"), "measured",
                         f"relay lag p95 over {st['relayLagMs'].get('n', 0)} events at {args.steady_rate}/s and {big['accounts']} accounts"),
        benchlib.verdict("write_freeze", big["freeze"]["seconds"], "measured",
                         f"the pipeline transfer of {big['freeze']['transfer']['applications']} applications under a write freeze, {big['accounts']} accounts"),
    ]
    lost = 0
    for sc in scales.values():
        lost += sc["crash"].get("ackedMissing", 0) + sc["freeze"]["rollback"].get("ackedMissing", 0) + sc["freeze"]["acceptedDuringFreeze"]
        lost += sc.get("failpoints", {}).get("afterCommitBeforeRelay", {}).get("ackedMissing", 0)
    verdicts.append(benchlib.verdict("rpo_zero", float(lost), "measured",
                                     "acked writes missing after a kill -9, after the freeze rollback restore, and after the commit-then-crash failpoint, plus writes accepted during a freeze"))
    vac = next(r for r in big["restores"] if r["method"] == "vacuum-into")
    sample = small.get("bytesSample")
    bytes_restore = next((r for r in small["restores"] if r["method"] == "vacuum-into"), None)
    if sample and bytes_restore:
        storage_s = bytes_restore["copySeconds"]
        ex = benchlib.extrapolate(sample["bytes"], storage_s, benchlib.FLOOR_BYTES_PER_ACCOUNT * big["accounts"])
    else:
        ex = None
    total = vac["restoreSeconds"] + (ex["seconds"] if ex else 0)
    verdicts.append(benchlib.verdict("restore_rto", round(total, 2), "extrapolated" if ex else "measured",
                                     f"the {big['accounts']}-account database restored and checked ({vac['restoreSeconds']} s, measured) plus "
                                     f"{benchlib.FLOOR_BYTES_PER_ACCOUNT * big['accounts'] / 1000**3:.0f} GB of bytes at the measured copy rate ({ex['seconds'] if ex else 0} s, extrapolated)"))
    return {
        "$schema": "./benchmark.schema.json",
        "version": benchlib.RECEIPT_VERSION,
        "synthetic": True,
        "decisionRecord": "DR-0004",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "durationSeconds": round(time.monotonic() - started, 1),
        "command": "python harness/bench/bench.py " + " ".join(sys.argv[1:]),
        "profile": prof,
        "seedPlan": {"floorPerAccount": benchlib.FLOOR, "auditPerAccount": benchlib.FLOOR_AUDIT, "addedOffersPerAccount": benchlib.ADDED_OFFERS,
                     "idempotencyWindowRows": benchlib.IDEMPOTENCY_WINDOW_ROWS, "legacyPipelinePerAccount": benchlib.LEGACY_PIPELINE,
                     "bytesPerAccountAtFloor": benchlib.FLOOR_BYTES_PER_ACCOUNT, "bytesSampleMeasured": args.bytes_mb * 1024 * 1024,
                     "fraction": args.fraction},
        "commandMix": {"weights": dict(benchlib.MIX), "expectedWrites": benchlib.EXPECTED_WRITES},
        "scales": scales,
        "extrapolations": [ex] if ex else [],
        "targets": [v.as_dict() for v in verdicts],
        "rollbackDefaults": {
            "source": "DR-0003 P5",
            "freezeUnder15Minutes": verdicts[2].passed,
            "zeroAcceptedWritesLost": verdicts[3].passed,
            "restoreWithin30Minutes": verdicts[4].passed,
            "restoreRehearsed": all(r.get("consistent") for sc in scales.values() for r in sc["restores"]),
        },
        "result": "pass" if all(v.passed for v in verdicts) else "fail",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DR-0004's database benchmark")
    ap.add_argument("--accounts", default="1,10")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pocketbase", default=None)
    ap.add_argument("--fraction", type=float, default=1.0, help="share of the scale floor to seed (1.0 is the floor)")
    ap.add_argument("--bytes-mb", type=int, default=2048)
    ap.add_argument("--sweep", default="1,4,16,64")
    ap.add_argument("--sweep-seconds", type=float, default=30)
    ap.add_argument("--steady-seconds", type=float, default=60)
    ap.add_argument("--steady-rate", type=float, default=20)
    ap.add_argument("--steady-clients", type=int, default=4)
    ap.add_argument("--transfer-batch", type=int, default=30)
    ap.add_argument("--gomemlimit", default="460MiB")
    ap.add_argument("--no-failpoints", dest="failpoints", action="store_false")
    ap.add_argument("--no-schema-change", dest="schema_change", action="store_false")
    ap.add_argument("--min-free-gb", type=float, default=70)
    args = ap.parse_args(argv)
    args.sweep = [int(x) for x in args.sweep.split(",") if x]
    binary = pbnative.binary_path(args.pocketbase)
    free = benchlib.free_disk_gb(str(ROOT))
    if free < args.min_free_gb:
        print(f"refusing to start: {free:.0f} GB free, need {args.min_free_gb:.0f}", file=sys.stderr)
        return 75
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: STOP.set())
    started = time.monotonic()
    prof = profile(binary)
    scales: dict = {}
    try:
        for n in [int(x) for x in args.accounts.split(",")]:
            print(f"scale {n}: starting", flush=True)
            scales[str(n)] = run_scale(args, binary, n)
            print(f"scale {n}: done in {time.monotonic() - started:.0f} s", flush=True)
            if STOP.is_set():
                raise Bench("stopped")
        prof["loadAverageAtEnd"] = os.getloadavg()
        receipt = build_receipt(prof, scales, args, started)
        Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"wrote {args.out}: {receipt['result']}", flush=True)
        for t in receipt["targets"]:
            print(f"  {t['id']}: {t['result']} ({t['value']} {t['unit']}, {t['basis']})", flush=True)
        return 0
    except Exception as err:  # noqa: BLE001
        partial = Path(args.out).with_suffix(".partial.json")
        partial.write_text(json.dumps({"error": str(err), "trace": traceback.format_exc()[-4000:], "scales": scales,
                                       "failedScale": getattr(err, "partial", None)}, indent=2, default=str) + "\n")
        print(f"failed: {err}; partial results in {partial}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
