"""Account-scope two-account harness entrypoint.

Phases (run in order by the launcher, sharing one receipts file and run id):

  main    create two accounts, seed a fixture graph for each, run every
          enforced probe family against each collection it applies to, and
          read the live rules back against the policy table.
  hook    after PocketBase restarts with signups disabled, run the signup
          hook probe.
  verdict read every receipt and the policy and decide the run: every
          enforced (collection, family) pair and every collection's rule
          read-back must have a passing receipt; a pending family must be
          neither implemented nor present in any receipt. Prints pass /
          expected-fail / fail counts.

Exit code is non-zero on any failure, any missing result, or any pending
family that has started to behave like an implemented one.
"""
from __future__ import annotations

import os
import sys

import families
import policy
from factory import Account, ensure_content_fixtures, make_account, register, seed_account
from pbclient import PBClient
from receipts import Receipt, ReceiptWriter, read_all

READBACK_PROBE = "account-scope.rules.readback.match"
RULE_KEYS = [
    ("list", "listRule"),
    ("view", "viewRule"),
    ("create", "createRule"),
    ("update", "updateRule"),
    ("delete", "deleteRule"),
]


def _context(phase: str) -> dict:
    migrations: list[str] = []
    mig_dir = os.environ.get("PB_MIGRATIONS_DIR", "/pb_migrations")
    if os.path.isdir(mig_dir):
        migrations = sorted(
            f for f in os.listdir(mig_dir) if f.endswith(".js")
        )
    return {
        "run_id": os.environ.get("RUN_ID", "local"),
        "commit": os.environ.get("GIT_COMMIT", "unknown"),
        "binary_digest": os.environ.get("PB_BINARY_SHA256", ""),
        "binary_arch": os.environ.get("PB_BINARY_ARCH", ""),
        "phase": phase,
        "migrations": migrations,
    }


def _pb() -> PBClient:
    return PBClient(os.environ.get("POCKETBASE_URL", "http://pocketbase:8090"))


def _admin_token(pb: PBClient) -> str:
    email = os.environ.get("PB_ADMIN_EMAIL", "")
    password = os.environ.get("PB_ADMIN_PASSWORD", "")
    resp = pb.admin_auth(email, password)
    if resp.status != 200 or not isinstance(resp.body, dict) or not resp.body.get("token"):
        raise RuntimeError(f"admin auth failed: status={resp.status}")
    return resp.body["token"]


def _readback(pb: PBClient, doc: dict, admin_token: str, writer: ReceiptWriter) -> None:
    meta = pb.collections_meta(admin_token)
    if meta.status != 200 or not isinstance(meta.body, dict):
        raise RuntimeError(f"collections metadata read failed: status={meta.status}")
    by_name = {c["name"]: c for c in (meta.body.get("items") or [])}
    for name, row in doc["collections"].items():
        live = by_name.get(name)
        expected = row["current_rules"]
        mismatches = []
        if live is None:
            mismatches.append("collection-missing")
        else:
            for key, pb_key in RULE_KEYS:
                if key not in expected:
                    continue
                want = expected[key]
                got = live.get(pb_key)
                if (got or None) != (want or None) and not (want == "" and (got or "") == ""):
                    mismatches.append(key)
        writer.write(
            Receipt(
                probe_id=READBACK_PROBE,
                collection=name,
                operation="contract",
                actor="superuser",
                expected_status=200,
                observed_status=meta.status,
                passed=not mismatches,
                request_time_ms=meta.elapsed_ms,
                detail="" if not mismatches else "rules differ: " + ",".join(mismatches),
            )
        )


def run_main(doc: dict, writer: ReceiptWriter) -> None:
    pb = _pb()
    pb.wait_healthy()
    admin_token = _admin_token(pb)
    content = ensure_content_fixtures(pb, admin_token)

    a = make_account("a")
    b = make_account("b")
    register(pb, a)
    register(pb, b)
    seed_account(pb, a, content)
    seed_account(pb, b, content)

    fam = doc["probe_families"]
    for name, row in doc["collections"].items():
        for pid in row.get("probes", []):
            if fam[pid].get("status") != "enforced":
                continue
            impl = families.MAIN_FAMILIES.get(pid)
            if impl is None:
                continue  # hook-phase family, handled elsewhere
            writer.write(impl(pb, name, a, b))

    _readback(pb, doc, admin_token, writer)


def run_hook(doc: dict, writer: ReceiptWriter) -> None:
    pb = _pb()
    pb.wait_healthy()
    fam = doc["probe_families"]
    for name, row in doc["collections"].items():
        for pid in row.get("probes", []):
            if fam[pid].get("status") != "enforced":
                continue
            impl = families.HOOK_FAMILIES.get(pid)
            if impl is None:
                continue
            writer.write(impl(pb, name, None, None))


def run_verdict(doc: dict, receipts_path: str) -> int:
    receipts = read_all(receipts_path)
    fam = doc["probe_families"]
    enforced = set(policy.enforced_pairs(doc))
    pending = set(policy.pending_pairs(doc))

    seen: dict[tuple[str, str], list[dict]] = {}
    for r in receipts:
        seen.setdefault((r["collection"], r["probe_id"]), []).append(r)

    failures: list[str] = []

    # 1. Pending families must not be implemented and must not have receipts.
    for coll, pid in sorted(pending):
        if pid in families.IMPLEMENTED_FAMILIES:
            failures.append(
                f"pending family {pid} is implemented; flip its policy rows to enforced "
                f"and land the probe in the same PR"
            )
        if (coll, pid) in seen:
            failures.append(f"pending family {pid} produced a receipt for {coll}")

    # 2. Every enforced (collection, family) pair needs a passing receipt.
    for coll, pid in sorted(enforced):
        results = seen.get((coll, pid))
        if not results:
            failures.append(f"missing result for probe {pid} on {coll}")
            continue
        if not all(x["passed"] for x in results):
            failures.append(f"probe {pid} failed on {coll}")

    # 3. Every policy collection needs a passing rule read-back.
    for coll in doc["collections"]:
        results = seen.get((coll, READBACK_PROBE))
        if not results:
            failures.append(f"missing rule read-back for {coll}")
        elif not all(x["passed"] for x in results):
            detail = next((x.get("detail") for x in results if not x["passed"]), "")
            failures.append(f"rule read-back failed for {coll}: {detail}")

    # 4. No stray receipts for unknown or pending families.
    known = families.IMPLEMENTED_FAMILIES | {READBACK_PROBE}
    for (coll, pid), results in seen.items():
        if pid not in known:
            failures.append(f"receipt for unknown probe id {pid} ({coll})")

    total = len(receipts)
    passed = sum(1 for r in receipts if r["passed"])
    failed = sum(1 for r in receipts if not r["passed"])
    expected_fail = 0  # D4: no expected-fail probes are committed for open gaps.

    print("=" * 60)
    print("account-scope harness verdict")
    print(f"  receipts:       {total}")
    print(f"  pass:           {passed}")
    print(f"  expected-fail:  {expected_fail}")
    print(f"  fail:           {failed}")
    print(f"  enforced pairs: {len(enforced)}")
    print(f"  pending pairs:  {len(pending)} (no probe committed; closed by later leaves)")
    print("=" * 60)
    if failures:
        print("FAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("OK: every enforced guarantee holds and no pending probe leaked.")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run.py {main|hook|verdict}", file=sys.stderr)
        return 2
    phase = sys.argv[1]
    policy_path = os.environ.get("POLICY_PATH", "/policy/account-scope.v1.json")
    receipts_path = os.environ.get("RECEIPTS_PATH", "/out/receipts.jsonl")
    doc = policy.load(policy_path)

    if phase == "verdict":
        return run_verdict(doc, receipts_path)

    writer = ReceiptWriter(receipts_path, _context(phase))
    if phase == "main":
        run_main(doc, writer)
    elif phase == "hook":
        run_hook(doc, writer)
    else:
        print(f"unknown phase {phase!r}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
