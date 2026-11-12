"""The database benchmark's pure parts (ROUNDS-02-L01).

harness/bench/benchlib.py and bench.py's receipt builder, without a
PocketBase: the seed plan is the spec's scale floor, ids keep DR-0004's
rules, percentiles and verdicts are what the receipt says they are, an
extrapolated miss is a miss with its consequence, and a receipt validates
against contracts/database/benchmark.schema.json with the same validator the
conformance rule uses.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness" / "bench"))
import bench  # noqa: E402
import benchlib  # noqa: E402

SCHEMA = ROOT / "contracts" / "database" / "benchmark.schema.json"


def test_the_seed_is_the_spec_scale_floor():
    f = benchlib.FLOOR
    assert f["fact"] == 10_000 and f["organization"] == 2_000 and f["person"] == 10_000 and f["opportunity"] == 2_000
    assert f["activity"] + benchlib.FLOOR_AUDIT == 50_000
    assert f["attempt"] == 10_000 and f["artifact_revision"] == 5_000
    assert benchlib.FLOOR_BYTES_PER_ACCOUNT == 10 * 1000**3
    rows = benchlib.rows_per_account()
    assert rows["bench_records"] == sum(f.values()) + benchlib.ADDED_OFFERS
    assert rows["applications"] == 2_000


def test_the_mix_is_a_whole_and_every_command_has_its_writes():
    assert sum(w for _, w in benchlib.MIX) == 100
    assert {n for n, _ in benchlib.MIX} == set(benchlib.EXPECTED_WRITES)
    rng = random.Random(1)
    picks = [benchlib.pick(benchlib.MIX, rng) for _ in range(20_000)]
    assert abs(picks.count("update") / len(picks) - 0.5) < 0.02


def test_amplification_prefers_what_was_measured():
    expected = benchlib.weighted_amplification({})
    manual = sum(w * benchlib.EXPECTED_WRITES[n] for n, w in benchlib.MIX) / 100
    assert expected == pytest.approx(manual, abs=0.001)
    assert benchlib.weighted_amplification({"update": [7, 7]}) > expected


def test_percentiles_are_nearest_rank():
    v = sorted(range(1, 101))
    assert benchlib.percentile(v, 50) == 50 and benchlib.percentile(v, 95) == 95 and benchlib.percentile(v, 99) == 99
    assert benchlib.percentile(v, 100) == 100 and math.isnan(benchlib.percentile([], 50))
    s = benchlib.summarize([3, 1, 2])
    assert s["n"] == 3 and s["p50"] == 2 and s["max"] == 3
    assert benchlib.summarize([]) == {"n": 0}


def test_ids_follow_the_identifier_rules():
    t = 1_800_000_000_123
    cid = benchlib.uuid7(t)
    assert benchlib.V7.match(cid) and int(cid.replace("-", "")[:12], 16) == t
    a = benchlib.derived_id(t, ["gateway", "update", cid, "0"])
    assert a == benchlib.derived_id(t, ["gateway", "update", cid, "0"])
    assert a != benchlib.derived_id(t, ["gateway", "update", cid, "1"])
    assert benchlib.V7.match(a)
    rid = benchlib.record_id(random.Random(2))
    assert len(rid) == 15 and rid.isalnum() and rid == rid.lower()


def test_extrapolation_is_labeled_with_its_formula():
    ex = benchlib.extrapolate(2 * 1024**3, 4.0, 100 * 1000**3)
    assert ex["basis"] == "extrapolated" and ex["formula"].startswith("seconds = targetBytes")
    # Rounded to the millisecond in the receipt.
    assert ex["seconds"] == pytest.approx(100 * 1000**3 / (2 * 1024**3 / 4.0), abs=0.001)


def test_verdicts_fail_on_a_miss_a_gap_or_a_lost_write():
    assert benchlib.verdict("projection_lag_p95", 1999, "measured", "x").passed
    miss = benchlib.verdict("projection_lag_p95", 2001, "measured", "x")
    assert not miss.passed and miss.as_dict()["consequence"] == benchlib.CONSEQUENCES["projection_lag_p95"]
    assert not benchlib.verdict("write_freeze", None, "measured", "x").passed
    extrapolated = benchlib.verdict("restore_rto", 1801, "extrapolated", "x").as_dict()
    assert extrapolated["result"] == "fail" and extrapolated["basis"] == "extrapolated" and extrapolated["consequence"]
    assert benchlib.verdict("rpo_zero", 0, "measured", "x").passed
    assert not benchlib.verdict("rpo_zero", 1, "measured", "x").passed


def test_the_k8s_limits_come_from_the_manifest():
    limits = benchlib.parse_k8s_limits((ROOT / "k8s" / "pocketbase.yaml").read_text())
    assert limits == {"cpuLimit": "500m", "memoryLimit": "512Mi", "cpuRequest": "50m", "memoryRequest": "128Mi",
                      "replicas": 1, "strategy": "Recreate", "pvc": "5Gi"}
    assert benchlib.mem_to_bytes("512Mi") == 512 * 1024**2


def _scale(n: int, *, lag_p95: float = 120.0, freeze_s: float = 40.0, missing: int = 0, restore_s: float = 30.0) -> dict:
    summary = {"n": 100, "p50": 10.0, "p95": lag_p95, "p99": 300.0, "p999": 400.0, "max": 500.0, "mean": 50.0}
    out = {
        "accounts": n, "pragmas": {}, "seed": {"seconds": 1, "rowsPerAccount": {}, "rowsTotal": 1}, "sweep": {}, "backups": [],
        "steady": {"relayLagMs": summary, "readYourWritesMs": summary, "readYourWritesFallbacks": 0, "queueMs": summary, "holdMs": summary,
                   "writeAmplification": 5.9},
        "restores": [{"method": "vacuum-into", "restoreSeconds": restore_s, "copySeconds": 2.0, "consistent": True}],
        "crash": {"ackedMissing": missing}, "samplers": {},
        "freeze": {"seconds": freeze_s, "acceptedDuringFreeze": 0, "rollback": {"ackedMissing": 0}, "transfer": {"applications": 2000 * n}},
    }
    if n == 1:
        out["bytesSample"] = {"blobs": 1024, "bytes": 2 * 1024**3, "seconds": 9.0}
    return out


def _receipt(**kw) -> dict:
    prof = {"hardware": {"cpu": "test cpu", "cores": 8, "memoryBytes": 16 * 1024**3, "os": "macOS 1", "arch": "arm64", "storage": "SSD (APFS)"},
            "pocketbase": {"version": "0.22.22", "binarySha256": "a" * 64,
                           "dockerfilePin": {"PB_VERSION": "0.22.22", "PB_SHA256": "b" * 64, "PB_SHA256_ARM64": "c" * 64}},
            "k8sLimits": {"cpuLimit": "500m", "memoryLimit": "512Mi", "replicas": 1, "strategy": "Recreate", "pvc": "5Gi"},
            "emulation": {"GOMAXPROCS": 1, "note": "x"}, "revision": "d" * 40, "sharedMachine": "x"}
    args = argparse.Namespace(steady_rate=20.0, bytes_mb=2048, fraction=1.0)
    return bench.build_receipt(prof, {"1": _scale(1), "10": _scale(10, **kw)}, args, time.monotonic())


def _validate(doc: dict, tmp_path: Path) -> list:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not on PATH")
    target = tmp_path / "receipt.json"
    target.write_text(json.dumps(doc))
    script = ("import fs from 'node:fs'; import { validate } from " + json.dumps(str(ROOT / "scripts/conformance/lib/json-schema.mjs")) + ";"
              "const s = JSON.parse(fs.readFileSync(process.argv[1], 'utf8')); const d = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));"
              "process.stdout.write(JSON.stringify(validate(d, s)));")
    res = subprocess.run([node, "--input-type=module", "-e", script, str(SCHEMA), str(target)], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def test_a_receipt_validates_against_its_schema(tmp_path):
    doc = _receipt()
    assert _validate(doc, tmp_path) == []
    assert doc["synthetic"] is True and doc["result"] == "pass"
    assert [t["id"] for t in doc["targets"]] == list(benchlib.TARGETS)
    rto = next(t for t in doc["targets"] if t["id"] == "restore_rto")
    assert rto["basis"] == "extrapolated" and doc["extrapolations"][0]["targetBytes"] == 100 * 1000**3


def test_a_miss_fails_the_receipt_and_names_its_consequence(tmp_path):
    doc = _receipt(lag_p95=2500.0, missing=1)
    assert _validate(doc, tmp_path) == []
    assert doc["result"] == "fail"
    failed = {t["id"]: t for t in doc["targets"] if t["result"] == "fail"}
    assert set(failed) == {"projection_lag_p95", "rpo_zero"}
    assert all(t["consequence"] and t["consequence"] != "unrecorded" for t in failed.values())
    assert doc["rollbackDefaults"]["zeroAcceptedWritesLost"] is False


def test_the_schema_refuses_a_receipt_without_its_label_or_a_target(tmp_path):
    doc = _receipt()
    unlabeled = dict(doc, synthetic=False)
    assert _validate(unlabeled, tmp_path)
    short = dict(doc, targets=doc["targets"][:4])
    assert _validate(short, tmp_path)
    no_consequence = json.loads(json.dumps(_receipt(lag_p95=2500.0)))
    for t in no_consequence["targets"]:
        t.pop("consequence", None)
    assert _validate(no_consequence, tmp_path)
