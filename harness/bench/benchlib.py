"""Pure helpers for the database benchmark (ROUNDS-02-L01).

No I/O here, so backend/tests/test_bench_harness.py covers all of it: the
seed plan at the spec's scale floor, the command mix, ids, percentiles, the
five targets of spec 2056-2067 with their verdicts, the extrapolation of
byte-store timings, and the receipt's shape (contracts/database/benchmark.schema.json).
"""
from __future__ import annotations

import hashlib
import math
import os
import random
import re
import secrets
import string
import time
from dataclasses import dataclass

RECEIPT_VERSION = "rounds-db-benchmark/v1"

# Spec 2020-2028, per account. Activities, actions, and audit entries share
# the 50,000: 40,000 activities and actions as aggregates and 10,000 audit
# entries. Offers are added (one active per opportunity) so the offer chain
# command has its rows; the floor names no offer count.
FLOOR = {
    "fact": 10_000,
    "organization": 2_000,
    "person": 10_000,
    "opportunity": 2_000,
    "activity": 40_000,
    "attempt": 10_000,
    "artifact_revision": 5_000,
}
FLOOR_AUDIT = 10_000
ADDED_OFFERS = 2_000
FLOOR_BYTES_PER_ACCOUNT = 10 * 1000**3  # spec 2028: 10 GB retained source and artifact data
IDEMPOTENCY_WINDOW_ROWS = 10_000  # commands inside the 30-day idempotency window
LEGACY_PIPELINE = {"applications": 2_000, "interview_rounds": 10_000, "offers": 2_000, "todos": 10_000}
BYTES_SAMPLE = 2 * 1024**3
BLOB_SIZE = 2 * 1024**2

# The command mix: weights, and the rows each command writes (the route
# reports its own count; these are what the logic writes, for the checks).
MIX = (
    ("update", 50),
    ("create", 15),
    ("compose", 10),
    ("delete_revive", 5),
    ("replay", 5),
    ("conflict", 5),
    ("bg_admission", 4),
    ("bg_execution", 4),
    ("bg_share", 2),
)
# update and create touch one aggregate: 1 record, 1 change set, 1 audit
# row, 1 outbox event, 1 idempotency row. compose and delete_revive touch
# three aggregates: 3 + 1 + 3 + 3 + 1.
EXPECTED_WRITES = {"update": 5, "create": 5, "compose": 11, "delete_revive": 11, "replay": 0, "conflict": 0,
                   "bg_admission": 3, "bg_execution": 1, "bg_share": 1}

TARGETS = {
    "read_your_writes": {"spec": "spec 2059-2060", "text": "read-your-writes within 5 seconds or the canonical fallback", "limit": 5000, "unit": "ms"},
    "projection_lag_p95": {"spec": "spec 2061", "text": "normal projection lag p95 below 2 seconds", "limit": 2000, "unit": "ms"},
    "write_freeze": {"spec": "spec 2062", "text": "final bounded-context write freeze below 15 minutes", "limit": 900, "unit": "s"},
    "rpo_zero": {"spec": "spec 2063", "text": "zero accepted writes lost through freeze, rollback, and a crash", "limit": 0, "unit": "writes"},
    "restore_rto": {"spec": "spec 2064-2065", "text": "rollback or restore within 30 minutes at the scale floor", "limit": 1800, "unit": "s"},
}

_ID_ALPHABET = string.ascii_lowercase + string.digits


def record_id(rng: random.Random | None = None) -> str:
    """A PocketBase-shaped record id: 15 characters of [a-z0-9]."""
    r = rng or random.SystemRandom()
    return "".join(r.choice(_ID_ALPHABET) for _ in range(15))


def uuid7(time_ms: int | None = None, rand: bytes | None = None) -> str:
    """A client command_id: UUIDv7 with 74 random bits."""
    t = int(time.time() * 1000) if time_ms is None else int(time_ms)
    h = (rand or secrets.token_bytes(10)).hex()
    return _v7(t, h)


def _v7(time_ms: int, h: str) -> str:
    t = f"{time_ms:012x}"
    variant = format(8 + (int(h[3], 16) >> 2), "x")
    return f"{t[:8]}-{t[8:12]}-7{h[0:3]}-{variant}{h[4:7]}-{h[7:19]}"


def derived_id(time_ms: int, parts: list[str]) -> str:
    """DR-0004's derived id: the source's time plus 74 bits of SHA-256 over
    the parts (actor kind, handler, source id, effect index). Same as
    bench_lib.js derivedId; a retry of the same effect gets the same id."""
    return _v7(int(time_ms), hashlib.sha256("\x00".join(parts).encode()).hexdigest())


V7 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def percentile(sorted_values: list[float], p: float) -> float:
    """Nearest-rank percentile of an already sorted list."""
    if not sorted_values:
        return math.nan
    k = max(0, min(len(sorted_values) - 1, math.ceil(p / 100 * len(sorted_values)) - 1))
    return float(sorted_values[k])


def summarize(values: list[float]) -> dict:
    v = sorted(values)
    if not v:
        return {"n": 0}
    return {"n": len(v), "p50": percentile(v, 50), "p95": percentile(v, 95), "p99": percentile(v, 99),
            "p999": percentile(v, 99.9), "max": float(v[-1]), "mean": round(sum(v) / len(v), 3)}


def pick(mix: tuple[tuple[str, int], ...], rng: random.Random) -> str:
    total = sum(w for _, w in mix)
    x = rng.uniform(0, total)
    for name, w in mix:
        x -= w
        if x <= 0:
            return name
    return mix[-1][0]


def weighted_amplification(writes_by_type: dict[str, list[int]], mix=MIX) -> float:
    """Rows written per command across the mix, weighted by the mix."""
    total_w = sum(w for _, w in mix)
    acc = 0.0
    for name, w in mix:
        seen = writes_by_type.get(name) or []
        mean = (sum(seen) / len(seen)) if seen else EXPECTED_WRITES[name]
        acc += w * mean
    return round(acc / total_w, 3)


def rows_per_account() -> dict[str, int]:
    """Rows the seed writes for one account, by table."""
    aggregates = sum(FLOOR.values()) + ADDED_OFFERS
    out = {
        "bench_records": aggregates,
        "bench_change_sets": aggregates,
        "bench_outbox": aggregates,
        "bench_projection": aggregates,
        "bench_audit": FLOOR_AUDIT,
        "bench_idempotency": IDEMPOTENCY_WINDOW_ROWS,
        "campaigns": 1,
    }
    out.update(LEGACY_PIPELINE)
    return out


def extrapolate(measured_bytes: int, measured_seconds: float, target_bytes: int, target: str) -> dict:
    """Linear extrapolation of a byte-store timing, labeled as such, naming the target it feeds."""
    throughput = measured_bytes / measured_seconds if measured_seconds > 0 else math.inf
    seconds = target_bytes / throughput if throughput > 0 else math.inf
    return {
        "basis": "extrapolated",
        "target": target,
        "measuredBytes": measured_bytes,
        "measuredSeconds": round(measured_seconds, 3),
        "throughputBytesPerSecond": round(throughput, 1),
        "targetBytes": target_bytes,
        "seconds": round(seconds, 3),
        "formula": "seconds = targetBytes / (measuredBytes / measuredSeconds)",
    }


@dataclass
class Verdict:
    id: str
    value: float | None
    basis: str
    passed: bool
    detail: str
    consequence: str | None = None

    def as_dict(self) -> dict:
        t = TARGETS[self.id]
        out = {"id": self.id, "spec": t["spec"], "target": t["text"], "limit": t["limit"], "unit": t["unit"],
               "value": self.value, "basis": self.basis, "result": "pass" if self.passed else "fail", "detail": self.detail}
        if not self.passed:
            out["consequence"] = self.consequence or "unrecorded"
        return out


CONSEQUENCES = {
    "read_your_writes": "Projection reads miss 5 s, so #23's reads take the canonical fallback until the relay keeps up; the ADR's lock budget and relay interval are revised before #23.",
    "projection_lag_p95": "The relay can't keep p95 under 2 s on one writer, so #22 batches differently or the ADR picks another authority before #19.",
    "write_freeze": "A context transfer can't freeze writes for under 15 minutes at the floor, so #156's transfers run per account or in smaller batches, and DR-0003's P5 default is revised before the first transfer.",
    "rpo_zero": "An accepted write was lost, so the database authority is not retained as decided; the ADR selects another authority before #19 (spec 2069-2071).",
    "restore_rto": "Restore at the floor takes over 30 minutes, so #157's procedure moves the byte store to a faster medium or object storage, and installs size storage for it, before any transfer.",
}


def verdict(target_id: str, value: float | None, basis: str, detail: str, passed: bool | None = None) -> Verdict:
    """Pass or fail against the spec limit. A missing value fails; an
    extrapolated miss is a miss."""
    limit = TARGETS[target_id]["limit"]
    if passed is None:
        passed = value is not None and not math.isnan(value) and (value <= limit if target_id != "rpo_zero" else value == 0)
    return Verdict(target_id, value, basis, bool(passed), detail, None if passed else CONSEQUENCES[target_id])


def parse_k8s_limits(manifest_text: str) -> dict:
    """The PocketBase Deployment's limits, replicas, strategy, and PVC size."""
    def first(pattern: str) -> str | None:
        m = re.search(pattern, manifest_text, re.MULTILINE)
        return m.group(1).strip() if m else None
    limits = re.search(r"limits:\s*\n\s*cpu:\s*(\S+)\s*\n\s*memory:\s*(\S+)", manifest_text)
    requests = re.search(r"requests:\s*\n\s*cpu:\s*(\S+)\s*\n\s*memory:\s*(\S+)", manifest_text)
    return {
        "cpuLimit": limits.group(1) if limits else None,
        "memoryLimit": limits.group(2) if limits else None,
        "cpuRequest": requests.group(1) if requests else None,
        "memoryRequest": requests.group(2) if requests else None,
        "replicas": int(first(r"^\s*replicas:\s*(\d+)") or 0),
        "strategy": first(r"type:\s*(\w+)\s*#"),
        "pvc": first(r"storage:\s*(\S+)"),
    }


def mem_to_bytes(text: str | None) -> int | None:
    if not text:
        return None
    m = re.fullmatch(r"(\d+)(Ki|Mi|Gi)?", text)
    if not m:
        return None
    scale = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, None: 1}[m.group(2)]
    return int(m.group(1)) * scale


def payload(rng: random.Random, kind: str) -> dict:
    """A synthetic aggregate body of a realistic size (no real data)."""
    words = ["alpha", "beta", "gamma", "delta", "kappa", "sigma", "omega", "theta", "lambda", "zeta"]
    size = {"fact": 40, "artifact_revision": 60}.get(kind, 20)
    return {"synthetic": True, "kind": kind, "title": " ".join(rng.choice(words) for _ in range(4)),
            "text": " ".join(rng.choice(words) for _ in range(size)), "n": rng.randint(0, 10**6)}


def generated_password() -> str:
    """A per-run test password; never printed or written."""
    return "Bx" + secrets.token_hex(16) + "!7"


def free_disk_gb(path: str) -> float:
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / 1000**3
