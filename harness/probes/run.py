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
  scan    with PocketBase stopped, run the cross-owner relation scan against
          the run's pb_data (read-only) and a fixture copy of it; see
          scan_check.py.
  admission
          with two runner replicas up on the one PocketBase, check admission
          state across them (ROUNDS-00A-L01 stage 3); see admission_check.py.
  admission-migration
          apply and reverse the admission migration with the pinned binary on
          a 62d4eae-shaped pb_data; see admission_migration_check.py.

Exit code is non-zero on any failure, any missing result, or any pending
family that has started to behave like an implemented one.
"""
from __future__ import annotations

import os
import sys

import secrets

import families
import factory
import policy
from factory import Account, ensure_content_fixtures, make_account, register, seed_account
from pbclient import PBClient
from receipts import Receipt, ReceiptWriter, read_all

READBACK_PROBE = "account-scope.rules.readback.match"
# Policy rule-key -> PocketBase collection field. Each collection is checked
# only on the keys its policy row declares. The five base rules are top-level;
# an auth collection's manageRule is nested under `options` (PocketBase 0.22
# does not serialize it at the top level), so "manage" is read from there.
RULE_FIELD = {
    "list": "listRule",
    "view": "viewRule",
    "create": "createRule",
    "update": "updateRule",
    "delete": "deleteRule",
}
AUTH_OPTION_RULE = {"manage": "manageRule"}
# A rule PocketBase exposes as null is distinct from one it exposes as the
# empty string: null means superusers only, "" means anyone. _RULE_MISSING
# marks a field the collection does not expose at all, which must not read as
# either null or "".
_RULE_MISSING = object()


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
            for key, want in expected.items():
                if key in RULE_FIELD:
                    got = live.get(RULE_FIELD[key], _RULE_MISSING)
                elif key in AUTH_OPTION_RULE:
                    got = (live.get("options") or {}).get(AUTH_OPTION_RULE[key], _RULE_MISSING)
                else:
                    mismatches.append(f"{key}:unknown-rule-key")
                    continue
                # Exact comparison: null, "", and a rule string are all distinct.
                if got != want:
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


def _expected_status(doc: dict, pid: str) -> int:
    """The expected status for a family, read from the policy's deny_contract."""
    deny_key = doc["probe_families"][pid]["deny_key"]
    return doc["deny_contract"][deny_key]["status"]


def run_main(doc: dict, writer: ReceiptWriter) -> None:
    pb = _pb()
    pb.wait_healthy()
    admin_token = _admin_token(pb)
    content = ensure_content_fixtures(pb, admin_token)

    a = make_account("a")
    b = make_account("b")
    register(pb, a)
    register(pb, b)
    seed_account(pb, a, content, admin_token)
    seed_account(pb, b, content, admin_token)
    # A third account that signs up but seeds nothing. The anonymous-create
    # probe owns its payload with this account so there is no per-user
    # uniqueness collision (it owns no rows), leaving the createRule as the
    # only thing that can deny the write.
    c = make_account("c")
    register(pb, c)

    fam = doc["probe_families"]
    for name, row in doc["collections"].items():
        for pid in row.get("probes", []):
            if fam[pid].get("status") != "enforced":
                continue
            expected = _expected_status(doc, pid)
            if pid in families.MAIN_FAMILIES:
                writer.write(families.MAIN_FAMILIES[pid](pb, name, a, b, expected))
            elif pid == families.CREATE_ANON_FAMILY:
                payload = factory.fresh_payload(name, c.user_id, a, b, content, secrets.token_hex(6))
                writer.write(families.create_anonymous_denied(pb, name, payload, expected))
            elif pid == families.OVERSIZED_FAMILY:
                field = row["oversized_probe"]["field"]
                payload = factory.fresh_payload(name, a.user_id, a, b, content, secrets.token_hex(6))
                payload[field] = families.oversized_filler(row["oversized_probe"]["max_bytes"])
                writer.write(families.oversized_input_rejected(pb, name, a.token, payload, field, expected))
            elif pid == families.FOREIGN_OWNER_FAMILY:
                # Caller b claims a no-rows third account (c) as owner, so the
                # only reason to reject is the createRule and the owner-count
                # check stays at zero on a clean deny.
                payload = factory.fresh_payload(name, c.user_id, a, b, content, secrets.token_hex(6))
                writer.write(families.create_foreign_owner_denied(pb, name, b.token, payload, admin_token, c.user_id, expected))
            elif pid == families.REASSIGN_FAMILY:
                writer.write(families.update_reassign_denied(pb, name, a.ids[name], b.user_id, a.token, admin_token, a.user_id, expected))
            elif pid == families.UPDATE_OWN_FAMILY:
                writer.write(families.update_own_accepted(pb, name, b.ids[name], b.user_id, b.token, expected))
            elif pid == families.SERVER_ONLY_CREATE_FAMILY:
                payload = factory.fresh_payload(name, c.user_id, a, b, content, secrets.token_hex(6))
                writer.write(families.create_server_only_denied(pb, name, b.token, payload, admin_token, c.user_id, expected))
            elif pid == families.SERVER_ONLY_UPDATE_FAMILY:
                writer.write(families.update_server_only_denied(pb, name, a.ids[name], a.token, expected))
            elif pid == families.SUPERUSER_CREATE_FAMILY:
                # Owner a owns both the view row and the share link it points
                # at, so the superuser insert is not a cross-owner relation.
                payload = factory.fresh_payload(name, a.user_id, a, b, content, secrets.token_hex(6))
                writer.write(families.create_superuser_accepted(pb, name, admin_token, payload, expected))
            # hook-phase families are handled in run_hook

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
            writer.write(impl(pb, _expected_status(doc, pid)))


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
        print("usage: run.py {main|hook|verdict|scan|admission|admission-migration}", file=sys.stderr)
        return 2
    phase = sys.argv[1]
    if phase == "scan":
        import scan_check

        return scan_check.main()
    if phase == "admission":
        import admission_check

        return admission_check.main()
    if phase == "admission-migration":
        import admission_migration_check

        return admission_migration_check.main()
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
