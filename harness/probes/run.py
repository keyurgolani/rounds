"""Account-scope two-account harness entrypoint.

Phases (run in order by the launcher, sharing one receipts file and run id):

  main      create two accounts, seed a fixture graph for each, run every
            enforced probe family against each collection it applies to, and
            read the live rules back against the policy table.
  hook      after PocketBase restarts with signups disabled, run the signup
            hook probe.
  deploy    with the runner and the nginx frontend up, run the deployment
            verifier (../verify_deployment.py) through the real proxy config
            and at PocketBase's own port, with its admission and gate checks.
  degraded  with PocketBase stopped and the runner and frontend still up, run
            the fails-closed runner probe through nginx.
  deploy-db with PocketBase stopped, run the verifier's checks on the run's
            pb_data (read-only): rules against the table, and an admin row.
  verdict   read every receipt and the policy and decide the run: every
            enforced (collection, family) pair, every collection's rule
            read-back, and every deployment check must have a passing
            receipt; a pending family must be neither implemented nor present
            in any receipt; every receipt has the same fields. Prints pass /
            expected-fail / fail counts.
  scan      with PocketBase stopped, run the cross-owner relation scan against
            the run's pb_data (read-only) and a fixture copy of it; see
            scan_check.py.
  admission
            with two runner replicas up on the one PocketBase, check admission
            state across them (ROUNDS-00A-L01 stage 3); see admission_check.py.
  admission-migration
            apply and reverse the admission migration with the pinned binary on
            a 62d4eae-shaped pb_data; see admission_migration_check.py.
  demo-contain-migration
            apply and reverse the demo containment migration with the pinned
            binary on a pb_data with a legacy demo fixture; see
            demo_contain_migration_check.py.
  demo-on, demo-off
            the demo account's containment (ROUNDS-00B-L07 stage 1): with
            ROUNDS_ENABLE_DEMO=true, what a demo caller may change and own,
            through PocketBase and the runner; after a restart with the demo
            at its default, no demo account signs in and an earlier token is
            refused; see demo_check.py.
  snapshot-create, snapshot-create-down, snapshot-create-retry,
  snapshot-scan, snapshot-create-off, snapshot-create-again
            Legacy Artifact Snapshot creation (ROUNDS-00A-L04 PR 2) with its
            gate on, the materializer stopped and back, the operator's scan,
            the gate off, and on again; see legacy_snapshot_check.py.
  admission-deploy
            with both replicas up: the admission policy, its order and byte
            caps, and stage 2's closures on each replica (ROUNDS-00A-L01 stage
            4); see admission_deploy.py.
  emergency-disable, emergency-enable
            with both replicas restarted with ROUNDS_GATE_RUN=disabled, then
            cleared: the route is refused for every caller on each and
            charges nothing, the other routes still admit, and it comes
            back; see admission_deploy.py.
  execution-store, execution-runners, execution-unready,
  execution-ready-again, execution-disabled
            the execution job store on the real PocketBase with
            ROUNDS_GATE_EXECUTION_STORE on, then both replicas' workers and
            readiness through a secret rotation (ROUNDS-00A-L03); see
            execution_check.py.
  execution-scratch, execution-scratch-start, execution-scratch-retry
            run, evaluate, and run-project as durable jobs through nginx,
            with the scratch key on and definitions enforced, then a job
            whose replica is killed mid-run retried under its key
            (ROUNDS-00A-L03 PR 2); see scratch_check.py.
  execution-migration
            apply and reverse the execution job store's migration with the
            pinned binary; see execution_migration_check.py.
  json-limits
            every JSON field's declared limit on fresh and upgraded databases
            with the pinned binary, and the registry migration's down step
            (ROUNDS-00A-L03, D10); see json_limits_check.py.
  share-capabilities
            Share Capabilities (ROUNDS-00B-L03 stage 2) with both replicas and
            nginx up: the owner list and revoke through nginx, resume and
            variant deletes with active and revoked capabilities, the named
            snapshot's delete refused, superuser changes refused, and an
            account delete; see share_capability_check.py.

Exit code is non-zero on any failure, any missing result, or any pending
family that has started to behave like an implemented one.
"""
from __future__ import annotations

import datetime
import os
import sys

import secrets

import families
import factory
import policy
from factory import Account, ensure_content_fixtures, make_account, register, seed_account
from pbclient import PBClient
from receipts import Receipt, ReceiptWriter, file_checksum, list_checksum, read_all

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
        # The fixture manifest's pins (ROUNDS-00B-L05): which rule table and
        # which migration set a receipt was produced against.
        "policy_checksum": file_checksum(os.environ.get("POLICY_PATH", "/policy/account-scope.v1.json")),
        "migrations_checksum": list_checksum(migrations),
    }


def new_writer(receipts_path: str, phase: str) -> ReceiptWriter:
    """A phase's receipt writer. The harness admin password has no fixed
    shape the redactor knows, so every phase registers it."""
    writer = ReceiptWriter(receipts_path, _context(phase))
    writer.register_secret(os.environ.get("PB_ADMIN_PASSWORD", ""), "password:superuser")
    return writer


def _register_account(writer: ReceiptWriter, acct: Account) -> None:
    # Receipts carry neither an account's password nor its session token.
    writer.register_secret(acct.password, f"password:{acct.tag}")
    writer.register_secret(acct.token, f"token:{acct.tag}")


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


def _readback_token(row: dict, admin_token: str) -> str | None:
    """Who reads a row back around a refused write: its owner, or the
    superuser for a store whose view rule is null, which nobody else reads
    (share capabilities, ROUNDS-00B-L03 stage 2)."""
    return admin_token if row.get("current_rules", {}).get("view", "") is None else None


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
    # uniqueness collision (it owns no rows), so the write is rejected only
    # because the account is not allowed to create it.
    c = make_account("c")
    register(pb, c)
    for acct in (a, b, c):
        _register_account(writer, acct)
    writer.register_secret(admin_token, "token:superuser")

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
                writer.write(families.create_anonymous_denied(pb, name, payload, admin_token, c.user_id, expected))
            elif pid == families.REPLAY_FAMILY:
                payload = factory.fresh_payload(name, c.user_id, a, b, content, secrets.token_hex(6))
                writer.write(families.create_replayed_denied(pb, name, b.token, payload, admin_token, c.user_id, expected))
            elif pid == families.NONEXISTENT_OWNER_FAMILY:
                # An owner id no account has; the payload is otherwise valid.
                missing_owner = families.missing_record_id()
                payload = factory.fresh_payload(name, missing_owner, a, b, content, secrets.token_hex(6))
                writer.write(families.create_nonexistent_owner_denied(
                    pb, name, b.token, payload, admin_token, missing_owner, expected))
            elif pid == families.OVERSIZED_FAMILY:
                field = row["oversized_probe"]["field"]
                payload = factory.fresh_payload(name, a.user_id, a, b, content, secrets.token_hex(6))
                payload[field] = families.oversized_filler(row["oversized_probe"]["max_bytes"])
                writer.write(families.oversized_input_rejected(
                    pb, name, a.token, payload, field, admin_token, a.user_id, expected))
            elif pid == families.FOREIGN_OWNER_FAMILY:
                # Caller b claims a no-rows third account (c) as owner, so the
                # write is rejected only because the caller does not own the
                # row, and the owner-count check stays at zero on a clean deny.
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
                writer.write(families.update_server_only_denied(pb, name, a.ids[name], a.token, expected,
                                                                reader_token=_readback_token(row, admin_token)))
            elif pid == families.SERVER_ONLY_DELETE_FAMILY:
                writer.write(families.delete_server_only_denied(pb, name, a.ids[name], a.token, expected,
                                                                reader_token=_readback_token(row, admin_token)))
            elif pid == families.SUPERUSER_CREATE_FAMILY:
                # Owner a owns both the view row and the share link it points
                # at, so the superuser insert is not a cross-owner relation.
                payload = factory.fresh_payload(name, a.user_id, a, b, content, secrets.token_hex(6))
                writer.write(families.create_superuser_accepted(pb, name, admin_token, payload, expected))
            elif pid == families.RELATION_CREATE_FOREIGN_FAMILY:
                # Owner b creates its own row but points one typed relation at
                # account a's record; the write must be rejected because the
                # target is not owned by the same account.
                writer.write(families.create_relation_foreign_denied(
                    pb, name, row.get("relation_endpoints", []), b, a, content, admin_token, expected))
            elif pid == families.RELATION_CREATE_INDISTINGUISHABLE_FAMILY:
                writer.write(families.create_relation_foreign_or_missing_indistinguishable(
                    pb, name, row.get("relation_endpoints", []), b, a, content, expected))
            elif pid == families.RELATION_SUPERUSER_CREATE_FAMILY:
                # The superuser creates an a-owned row pointing one relation at
                # account b's record: an admin token is no exemption.
                writer.write(families.create_relation_superuser_denied(
                    pb, name, row.get("relation_endpoints", []), a, b, content, admin_token, expected))
            elif pid == families.RELATION_UPDATE_FOREIGN_FAMILY:
                writer.write(families.update_relation_foreign_denied(
                    pb, name, row.get("relation_endpoints", []), b, a, expected))
            elif pid == families.RELATION_UPDATE_INDISTINGUISHABLE_FAMILY:
                writer.write(families.update_relation_foreign_or_missing_indistinguishable(
                    pb, name, row.get("relation_endpoints", []), b, a, expected))
            # hook-phase families run in run_hook, degraded ones in run_degraded

    _readback(pb, doc, admin_token, writer)


def run_hook(doc: dict, writer: ReceiptWriter) -> None:
    pb = _pb()
    pb.wait_healthy()
    admin_token = _admin_token(pb)
    fam = doc["probe_families"]
    for name, row in doc["collections"].items():
        for pid in row.get("probes", []):
            if fam[pid].get("status") != "enforced":
                continue
            impl = families.HOOK_FAMILIES.get(pid)
            if impl is None:
                continue
            writer.write(impl(pb, admin_token, _expected_status(doc, pid)))


def _frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://frontend")


def _wait_for_runner(frontend: PBClient) -> None:
    # The degraded probe stops PocketBase and then needs the runner answering,
    # so before that: the runner listening on its own port (its /health is for
    # container checks and nginx doesn't route it), then nginx routing to it.
    # GET /api/ai/providers without a bearer is the runner's own 401 and needs
    # no PocketBase.
    runner = PBClient(os.environ.get("RUNNER_URL", "http://runner:8000"))
    runner.wait_for("/health", lambda r: r.status == 200)
    frontend.wait_for("/api/ai/providers",
                      lambda r: r.status == 401 and isinstance(r.body, dict) and "detail" in r.body)


def _verifier_receipt(r) -> Receipt:
    """A verify_deployment result as a harness receipt (same fields)."""
    return Receipt(r.check_id, r.target, r.operation, r.actor, r.expected_status, r.observed_status,
                   r.passed, r.elapsed_ms, r.detail)


def run_deploy(doc: dict, writer: ReceiptWriter) -> None:
    # The deployment verifier, run the way an operator runs it: proxy checks
    # through the real nginx frontend, credential and live-rule checks at
    # PocketBase's own port with the operator's admin login.
    import verify_deployment as vd

    pb_url = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090").rstrip("/")
    frontend = PBClient(_frontend_url())
    frontend.wait_healthy()  # nginx up, and PocketBase behind it
    _wait_for_runner(frontend)
    results = vd.check_proxy(_frontend_url())
    # The admission chain through nginx (ROUNDS-00A-L01 stage 4): every
    # admitted route refuses an anonymous caller in the typed envelope, each
    # edge cap holds, and the runner's startup line lists its gates, with
    # this run's enforcing values.
    results += vd.check_admitted_routes(_frontend_url())
    results += vd.check_admission_body_caps(_frontend_url())
    import admission_deploy

    results += vd.check_gates_log(admission_deploy.gates_log("deploy"), dict(admission_deploy.ENFORCING),
                                  source="runner log at deploy")
    results.append(vd.check_default_logins(pb_url))
    token = vd.admin_token(pb_url, os.environ.get("PB_ADMIN_EMAIL", ""), os.environ.get("PB_ADMIN_PASSWORD", ""))
    results += vd.compare_rules(doc, vd.live_rules(pb_url, token))
    results.append(vd.check_admin_passwords(pb_url, vd.live_admin_emails(pb_url, token)))
    for r in results:
        writer.write(_verifier_receipt(r))


def run_degraded(doc: dict, writer: ReceiptWriter) -> None:
    frontend = PBClient(_frontend_url())
    fam = doc["probe_families"]
    for name, row in doc["collections"].items():
        for pid in row.get("probes", []):
            impl = families.DEGRADED_FAMILIES.get(pid)
            if impl is None or fam[pid].get("status") != "enforced":
                continue
            writer.write(impl(frontend, name, _expected_status(doc, pid)))


def run_deploy_db(doc: dict, writer: ReceiptWriter) -> None:
    # The verifier's checks on the run's pb_data, read-only, PocketBase stopped:
    # the rules there match the table, and at least one admin exists.
    import verify_deployment as vd

    collections, admin_emails = vd.read_copy(os.environ.get("DEPLOY_DB", "/pb_data/data.db"))
    writer.write(_verifier_receipt(vd.check_admins_present(admin_emails)))
    for r in vd.compare_rules(doc, collections):
        writer.write(_verifier_receipt(r))


def admission_check_ids() -> set[str]:
    """Every admission and gate check id a full run reports (ROUNDS-00A-L01
    stage 4): the verifier's and the harness phases'."""
    import admission_deploy
    import verify_deployment as vd

    return set(vd.ADMISSION_CHECKS) | set(admission_deploy.CHECKS)


def _verdict_cases(doc: dict, receipts: list[dict],
                   today: datetime.date) -> tuple[list[str], set[str], set[tuple[str, str]]]:
    """The case table's part of the verdict: (failures, ids a receipt may
    carry, the (target, id) pairs a quarantine covers).

    - a `pass` row needs passing receipts for every check it names, on the
      named target when it names one (a `phase:` entry is the launcher's own
      exit code, so it needs none here);
    - a `pending` or `slot` row has no implementation and no receipt;
    - a `quarantined` row still runs; a failure on a target it covers is
      reported as the known flake, a failure anywhere else under the same id
      fails the run, and a pass on every covered target fails the run until
      the row is flipped back;
    - a quarantine that starts in the future or ends more than 14 days from
      today fails the run, and so does any row past its expiry.
    """
    cases = doc.get("cases") or {}
    by_id: dict[str, list[dict]] = {}
    for r in receipts:
        by_id.setdefault(r["probe_id"], []).append(r)
    failures: list[str] = []
    allowed: set[str] = set()
    covered = policy.quarantined_targets(doc)
    for cid in policy.expired_cases(doc, today):
        failures.append(f"case {cid} expired on {cases[cid]['expires']}; renew it with an owner or fix it")
    failures += policy.quarantine_window_problems(doc, today)
    for cid, row in sorted(cases.items()):
        status = row["status"]
        checks = [(ident, target) for kind, ident, target in map(policy.parse_evidence, row.get("evidence", []))
                  if kind == "check"]
        if status == "pass":
            for ident, target in checks:
                allowed.add(ident)
                results = [x for x in by_id.get(ident, []) if target is None or x["collection"] == target]
                label = ident if target is None else f"{target}:{ident}"
                if not results:
                    failures.append(f"missing result for case {cid} ({label})")
                elif not all(x["passed"] for x in results):
                    bad = next(x for x in results if not x["passed"])
                    failures.append(f"case {cid} failed ({label}): {bad.get('detail', '')}")
        elif status == "quarantined":
            results = []
            for ident, target in checks:
                allowed.add(ident)
                for x in by_id.get(ident, []):
                    if x["collection"] == target:
                        results.append(x)
                    elif not x["passed"]:
                        failures.append(f"case {cid} failed on {x['collection']}, which its quarantine doesn't cover")
            if not results:
                failures.append(f"missing result for quarantined case {cid}")
            elif all(x["passed"] for x in results):
                failures.append(f"quarantined case {cid} passed; flip it back to pass")
        else:
            if cid in families.IMPLEMENTED_FAMILIES:
                failures.append(f"{status} case {cid} is implemented; flip it to pass in the same PR")
            if cid in by_id:
                failures.append(f"{status} case {cid} produced a receipt")
    return failures, allowed, covered


def run_verdict(doc: dict, receipts_path: str, admission_ids: set[str] | frozenset[str] = frozenset(),
                today: datetime.date | None = None) -> int:
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

    # 4. Every deployment check in the policy needs receipts, all passing.
    deployment = doc.get("deployment_checks") or {}
    by_check: dict[str, list[dict]] = {}
    for r in receipts:
        if r["probe_id"] in deployment:
            by_check.setdefault(r["probe_id"], []).append(r)
    for check_id in sorted(deployment):
        results = by_check.get(check_id)
        if not results:
            failures.append(f"missing result for deployment check {check_id}")
        elif not all(x["passed"] for x in results):
            bad = next(x for x in results if not x["passed"])
            failures.append(f"deployment check {check_id} failed on {bad['collection']}: {bad.get('detail', '')}")

    # 4b. Every admission and gate check the run requires (ROUNDS-00A-L01
    # stage 4; main() passes them all) needs receipts, all passing.
    admission_ids = set(admission_ids)
    for check_id in sorted(admission_ids):
        results = [r for r in receipts if r["probe_id"] == check_id]
        if not results:
            failures.append(f"missing result for admission check {check_id}")
        elif not all(x["passed"] for x in results):
            bad = next(x for x in results if not x["passed"])
            failures.append(f"admission check {check_id} failed on {bad['collection']}: {bad.get('detail', '')}")

    # 4c. The case table (ROUNDS-00B-L05).
    case_failures, case_ids, quarantined_pairs = _verdict_cases(doc, receipts, today or datetime.date.today())
    failures += case_failures

    # 5. No stray receipts for unknown or pending families.
    known = families.IMPLEMENTED_FAMILIES | {READBACK_PROBE} | set(deployment) | admission_ids | case_ids
    for (coll, pid), results in seen.items():
        if pid not in known:
            failures.append(f"receipt for unknown probe id {pid} ({coll})")

    # 5b. A run that collected nothing proves nothing.
    if not receipts:
        failures.append("no receipts were collected")

    # 6. Every receipt has the same fields, so a denial reads like any other.
    shapes = {tuple(sorted(r)) for r in receipts}
    if len(shapes) > 1:
        failures.append(f"receipts have {len(shapes)} different field sets")

    total = len(receipts)
    passed = sum(1 for r in receipts if r["passed"])
    # A failure on a target a quarantine covers is its known flake, reported
    # apart; a failure on any other target counts as a failure.
    expected_fail = sum(1 for r in receipts
                        if not r["passed"] and (r["collection"], r["probe_id"]) in quarantined_pairs)
    failed = sum(1 for r in receipts if not r["passed"]) - expected_fail

    print("=" * 60)
    print("account-scope harness verdict")
    print(f"  receipts:       {total}")
    print(f"  pass:           {passed}")
    print(f"  expected-fail:  {expected_fail}")
    print(f"  fail:           {failed}")
    print(f"  enforced pairs: {len(enforced)}")
    print(f"  deploy checks:  {len(deployment)}")
    print(f"  admission checks: {len(admission_ids)}")
    print(f"  pending pairs:  {len(pending)} (no probe committed; closed by later leaves)")
    for status in policy.CASE_STATUSES:
        print(f"  cases {status + ':':<12} {len(policy.cases_by_status(doc, status))}")
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
        print("usage: run.py {main|hook|deploy|degraded|deploy-db|verdict|scan|admission|admission-migration|"
              "admission-deploy|emergency-disable|emergency-enable|relation-quarantine|snapshot-store|"
              "execution-store|execution-runners|execution-unready|execution-ready-again|execution-disabled|"
              "execution-scratch|execution-scratch-start|execution-scratch-retry|"
              "execution-migration|json-limits|demo-on|demo-off|demo-contain-migration|snapshot-create|"
              "snapshot-create-down|snapshot-create-retry|snapshot-scan|snapshot-create-off|snapshot-create-again|"
              "share-capabilities|share-secrets|share-secrets-down|share-secrets-scan}",
              file=sys.stderr)
        return 2
    phase = sys.argv[1]
    if phase == "relation-quarantine":
        import relation_quarantine_check

        return relation_quarantine_check.main()
    if phase == "snapshot-store":
        import snapshot_store_check

        return snapshot_store_check.main()
    if phase.startswith("snapshot-create") or phase == "snapshot-scan":
        import legacy_snapshot_check

        if phase not in legacy_snapshot_check.PHASES:
            print(f"unknown phase {phase!r}", file=sys.stderr)
            return 2
        return legacy_snapshot_check.main(phase)
    if phase == "share-capabilities":
        import share_capability_check

        return share_capability_check.main()
    if phase == "scan":
        import scan_check

        return scan_check.main()
    if phase == "admission":
        import admission_check

        return admission_check.main()
    if phase == "admission-migration":
        import admission_migration_check

        return admission_migration_check.main()
    if phase == "execution-migration":
        import execution_migration_check

        return execution_migration_check.main()
    if phase == "json-limits":
        import json_limits_check

        return json_limits_check.main()
    if phase.startswith("execution-scratch"):
        import scratch_check

        if phase not in scratch_check.PHASES:
            print(f"unknown phase {phase!r}", file=sys.stderr)
            return 2
        return scratch_check.main(phase, new_writer(os.environ.get("RECEIPTS_PATH", "/out/receipts.jsonl"), phase))
    if phase.startswith("execution-"):
        import execution_check

        if phase not in execution_check.PHASES:
            print(f"unknown phase {phase!r}", file=sys.stderr)
            return 2
        return execution_check.main(phase)
    if phase == "demo-contain-migration":
        import demo_contain_migration_check

        return demo_contain_migration_check.main()
    if phase in ("demo-on", "demo-off"):
        import demo_check

        return demo_check.main(phase)
    policy_path = os.environ.get("POLICY_PATH", "/policy/account-scope.v1.json")
    receipts_path = os.environ.get("RECEIPTS_PATH", "/out/receipts.jsonl")
    doc = policy.load(policy_path)

    if phase == "verdict":
        return run_verdict(doc, receipts_path, admission_check_ids())

    writer = new_writer(receipts_path, phase)
    if phase.startswith("share-secrets"):
        # ROUNDS-00B-L04: its case rows' receipts, and an exit code for the rest.
        import share_secrets_check

        if phase not in share_secrets_check.PHASES:
            print(f"unknown phase {phase!r}", file=sys.stderr)
            return 2
        return share_secrets_check.main(phase, writer)
    if phase == "main":
        run_main(doc, writer)
    elif phase == "hook":
        run_hook(doc, writer)
    elif phase == "deploy":
        run_deploy(doc, writer)
    elif phase == "degraded":
        run_degraded(doc, writer)
    elif phase == "deploy-db":
        run_deploy_db(doc, writer)
    elif phase in ("admission-deploy", "emergency-disable", "emergency-enable"):
        import admission_deploy

        {"admission-deploy": admission_deploy.run_admission_deploy,
         "emergency-disable": admission_deploy.run_emergency_disable,
         "emergency-enable": admission_deploy.run_emergency_enable}[phase](writer)
    else:
        print(f"unknown phase {phase!r}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
