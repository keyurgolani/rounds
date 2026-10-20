"""Admission state in pb_hooks/admission.js (ROUNDS-00A-L01 stage 3).

Steps 6 and 7 of admission/v1 under node, on an in-memory store with the
PocketBase store's contract (admission_runner.cjs): idempotency by
(account, command_id) and fingerprint, hourly quotas per account,
deployment, and demo bucket, leases as in-flight counts, settling,
finishing with refunds, the sweep, and the demo-field guards. The
harness runs the same functions on a real PocketBase across two runner
replicas."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HOOKS = HERE.parent / "pb_hooks"
RUNNER = HERE / "admission_runner.cjs"

HOUR = 3600
T0 = 1_800_000_000 + 60  # a minute into an hour
A = {"id": "acct00000000001", "demo": False}
B = {"id": "acct00000000002", "demo": False}
D = {"id": "acct00000000003", "demo": True}
K1 = "0190f000-0000-7000-8000-000000000001"
K2 = "0190f000-0000-7000-8000-000000000002"
FP1 = "a" * 64
FP2 = "b" * 64


def run(*steps: dict) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run(
        [node, str(RUNNER), str(HOOKS), json.dumps({"steps": list(steps)})],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def admit(account=A, op="run", key=None, fp=None, wall=None, mode="enforce", now=T0) -> dict:
    walls = {"run": 3, "evaluate": 3, "run_project": 10, "grade": 45, "take_home_run": 60,
             "take_home_submit": 120, "pdf_render": 25}
    body = {"operation": op, "wall_seconds": walls[op] if wall is None else wall, "idempotency": mode}
    if key is not None:
        body["command_id"] = key
        body["fingerprint"] = FP1 if fp is None else fp
    return {"call": "admit", "account": account, "input": body, "now": now}


def finish(lease, outcome="completed", result=None, account=A, now=T0) -> dict:
    body = {"lease": lease, "outcome": outcome}
    if result is not None:
        body["result"] = result
    return {"call": "finish", "account": account, "input": body, "now": now}


def settle(lease, wall, account=A, now=T0) -> dict:
    return {"call": "settle", "account": account, "input": {"lease": lease, "wall_seconds": wall}, "now": now}


def seed(bucket, account="", requests=0, wall=0, now=T0) -> dict:
    return {"call": "seedCounter", "bucket": bucket, "account": account, "hour": now // HOUR,
            "requests": requests, "wall_seconds": wall}


def counters(store: dict) -> dict:
    return {(c["bucket"], c["account"]): (c["requests"], c["wall_seconds"]) for c in store["counters"]}


def lease_token(result: dict) -> str:
    assert result["lease"], result
    return result["lease"]


# ---- idempotency (step 6) ----------------------------------------------------


def test_a_new_command_writes_the_row_the_charge_and_the_lease_together():
    out = run(admit(key=K1))
    (decision,) = out["results"]
    assert decision["idempotency"] == "new" and decision["quota"] == "ok"
    assert len(decision["lease"]) == 43
    (command,) = out["store"]["commands"]
    assert (command["account"], command["command_id"], command["state"]) == (A["id"], K1, "in_flight")
    assert command["fingerprint"] == FP1 and command["wall_seconds"] == 3
    assert command["expires_at"] == T0 + 24 * HOUR
    (lease,) = out["store"]["leases"]
    assert lease["command"] == command["id"] and lease["expires_at"] == T0 + 3 + 30
    # Only the hash of the lease token is stored.
    assert decision["lease"] not in json.dumps(out["store"])
    assert counters(out["store"]) == {("account", A["id"]): (1, 3), ("deployment", ""): (1, 3)}


def test_a_duplicate_while_in_flight_is_refused_and_writes_nothing():
    out = run(admit(key=K1), admit(key=K1), admit(key=K1, mode="enforce"))
    first, second, third = out["results"]
    assert first["idempotency"] == "new"
    for again in (second, third):
        assert again["idempotency"] == "in_flight" and again["lease"] == "" and again["quota"] == "skipped"
    assert len(out["store"]["commands"]) == 1 and len(out["store"]["leases"]) == 1
    assert counters(out["store"])[("account", A["id"])] == (1, 3)


def test_a_completed_replay_returns_the_stored_result_and_writes_nothing():
    first = run(admit(key=K1))["results"][0]
    result = {"status": 200, "body": {"stdout": "ok\n", "return_value": [1, 2]}}
    out = run(admit(key=K1), finish("tok" + "1".zfill(40), result=result), admit(key=K1, now=T0 + 60))
    _admitted, finished, replay = out["results"]
    assert first["lease"] == "tok" + "1".zfill(40)
    assert finished == {"status": 200, "body": {"v": "admission/v1", "refunded_wall_seconds": 0}}
    assert replay["idempotency"] == "replay" and replay["result"] == result and replay["lease"] == ""
    assert out["store"]["leases"] == []
    assert counters(out["store"])[("account", A["id"])] == (1, 3)


@pytest.mark.parametrize("change", [{"fp": FP2}, {"op": "evaluate"}])
def test_a_key_reused_for_another_request_is_refused(change):
    out = run(admit(key=K1), finish("tok" + "1".zfill(40)), admit(key=K1, **change))
    assert out["results"][2]["idempotency"] == "mismatch"
    assert out["results"][2]["result"] is None and out["results"][2]["lease"] == ""
    assert len(out["store"]["commands"]) == 1 and out["store"]["commands"][0]["state"] == "completed"


def test_observe_mode_runs_a_refused_duplicate_with_a_charge_and_a_lease_but_no_row_change():
    out = run(admit(key=K1), finish("tok" + "1".zfill(40), result={"status": 200, "body": {}}),
              admit(key=K1, mode="observe"), admit(key=K1, fp=FP2, mode="observe"))
    _first, _finished, replay, mismatch = out["results"]
    assert replay["idempotency"] == "replay" and replay["lease"] and replay["result"] is None
    assert mismatch["idempotency"] == "mismatch" and mismatch["lease"]
    (command,) = out["store"]["commands"]
    assert command["state"] == "completed" and command["fingerprint"] == FP1
    assert [lease["command"] for lease in out["store"]["leases"]] == ["", ""]
    assert counters(out["store"])[("account", A["id"])] == (3, 9)


def test_a_key_older_than_24_hours_starts_over():
    later = T0 + 24 * HOUR
    out = run(admit(key=K1), finish("tok" + "1".zfill(40), result={"status": 200, "body": {}}),
              admit(key=K1, fp=FP2, now=later))
    assert out["results"][2]["idempotency"] == "new"
    (command,) = out["store"]["commands"]
    assert command["fingerprint"] == FP2 and command["state"] == "in_flight"


@pytest.mark.parametrize("outcome, state", [("denied", "retryable"), ("infrastructure", "failed_infrastructure"),
                                            ("error", "failed_infrastructure")])
def test_a_denied_or_failed_command_runs_admission_again_with_its_key(outcome, state):
    out = run(admit(key=K1), finish("tok" + "1".zfill(40), outcome=outcome), {"call": "dump"}, admit(key=K1))
    assert out["results"][2]["commands"][0]["state"] == state
    retry = out["results"][3]
    assert retry["idempotency"] == "retry" and retry["lease"]
    (command,) = out["store"]["commands"]
    assert command["state"] == "in_flight"


def test_an_in_flight_command_whose_lease_expired_can_be_retried():
    expired = T0 + 3 + 30
    out = run(admit(key=K1), admit(key=K1, now=expired))
    assert out["results"][1]["idempotency"] == "retry"
    # The stale lease is gone; only the new one counts.
    (lease,) = out["store"]["leases"]
    assert lease["expires_at"] == expired + 33


def test_accounts_never_share_a_key():
    out = run(admit(key=K1), admit(account=B, key=K1, fp=FP2))
    assert [r["idempotency"] for r in out["results"]] == ["new", "new"]
    assert len(out["store"]["commands"]) == 2


# ---- quotas (step 7) ---------------------------------------------------------


@pytest.mark.parametrize(
    "seeds, account, verdict",
    [
        ([seed("account", A["id"], requests=119)], A, "ok"),
        ([seed("account", A["id"], requests=120)], A, "exceeded"),
        ([seed("account", A["id"], wall=1797)], A, "ok"),
        ([seed("account", A["id"], wall=1798)], A, "exceeded"),
        ([seed("deployment", requests=1999)], A, "ok"),
        ([seed("deployment", requests=2000)], A, "exceeded"),
        # The deployment has no wall-second limit.
        ([seed("deployment", wall=10**6)], A, "ok"),
        ([seed("demo", requests=29)], D, "ok"),
        ([seed("demo", requests=30)], D, "demo_limit"),
        ([seed("demo", wall=298)], D, "demo_limit"),
        # The demo bucket is the demo tier's alone.
        ([seed("demo", requests=30)], A, "ok"),
        # Over both the account and the demo limit, a demo account hears the demo one.
        ([seed("account", D["id"], requests=120), seed("demo", requests=30)], D, "demo_limit"),
    ],
)
def test_each_bucket_has_its_hourly_limits(seeds, account, verdict):
    out = run(*seeds, admit(account=account))
    assert out["results"][-1]["quota"] == verdict


def test_in_flight_counts_live_leases_per_account_deployment_and_demo():
    two = run(admit(), admit(), admit(), admit(account=B))
    assert [r["quota"] for r in two["results"]] == ["ok", "ok", "exceeded", "ok"]

    accounts = [{"id": f"acct{i:011d}", "demo": False} for i in range(10, 15)]
    eight = run(*[admit(account=a) for a in accounts for _ in range(2)])
    assert [r["quota"] for r in eight["results"]] == ["ok"] * 8 + ["exceeded"] * 2

    demo = run(admit(account=D), admit(account={"id": "acct00000000004", "demo": True}))
    assert [r["quota"] for r in demo["results"]] == ["ok", "demo_limit"]

    # An expired lease stops counting.
    later = run(admit(), admit(), admit(now=T0 + 33))
    assert later["results"][2]["quota"] == "ok"


@pytest.mark.parametrize("mode", ["enforce", "observe"])
def test_a_request_over_any_limit_writes_nothing(mode):
    out = run(seed("account", A["id"], requests=120), admit(key=K1, mode=mode))
    decision = out["results"][-1]
    assert decision["quota"] == "exceeded" and decision["lease"] == ""
    assert out["store"]["commands"] == [] and out["store"]["leases"] == []
    assert counters(out["store"]) == {("account", A["id"]): (120, 0)}


def test_retry_after_is_the_rest_of_the_hour_or_a_short_wait_for_in_flight():
    hour_full = run(seed("account", A["id"], requests=120), admit())
    assert hour_full["results"][-1]["retry_after"] == HOUR - 60
    busy = run(admit(op="grade"), admit(op="grade"), admit())
    assert busy["results"][-1]["retry_after"] == 10
    nearly_free = run(admit(), admit(), admit(now=T0 + 31))
    assert nearly_free["results"][-1]["retry_after"] == 2


def test_interleaved_requests_land_in_one_set_of_counters():
    # The harness checks the same across two runner replicas on a real
    # PocketBase, where every call shares its one write connection.
    out = run(admit(key=K1), admit(account=B, key=K2), finish("tok" + "1".zfill(40)), admit(), admit(account=B))
    assert counters(out["store"]) == {
        ("account", A["id"]): (2, 6),
        ("account", B["id"]): (2, 6),
        ("deployment", ""): (4, 12),
    }


# ---- settling and finishing --------------------------------------------------


def test_settle_moves_the_charge_to_the_exact_amount_and_the_lease_expiry():
    lease = "tok" + "1".zfill(40)
    out = run(admit(op="evaluate", key=K1), settle(lease, 30, now=T0 + 1), {"call": "dump"}, settle(lease, 9, now=T0 + 2))
    assert out["results"][1] == {"status": 200, "body": {"v": "admission/v1", "wall_seconds": 30}}
    mid = out["results"][2]
    assert counters(mid)[("account", A["id"])] == (1, 30)
    assert mid["leases"][0]["expires_at"] == T0 + 1 + 30 + 30
    assert counters(out["store"])[("account", A["id"])] == (1, 9)
    assert out["store"]["commands"][0]["wall_seconds"] == 9


def test_settle_stays_inside_the_operations_range():
    lease = "tok" + "1".zfill(40)
    out = run(admit(op="evaluate", key=K1), settle(lease, 321), admit(op="run"), settle("tok" + "2".zfill(40), 4))
    assert out["results"][1]["status"] == 400 and out["results"][3]["status"] == 400


def test_another_accounts_lease_is_not_found():
    lease = "tok" + "1".zfill(40)
    out = run(admit(key=K1), settle(lease, 3, account=B), finish(lease, account=B))
    assert out["results"][1]["status"] == 404 and out["results"][2]["status"] == 404
    assert out["store"]["commands"][0]["state"] == "in_flight" and len(out["store"]["leases"]) == 1


def test_a_finished_lease_cannot_be_finished_again():
    lease = "tok" + "1".zfill(40)
    out = run(admit(key=K1), finish(lease, outcome="denied"), finish(lease, outcome="denied"))
    assert out["results"][1]["status"] == 200 and out["results"][2]["status"] == 404
    assert counters(out["store"])[("account", A["id"])] == (1, 0)


def test_a_step_8_or_9_denial_leaves_the_command_retryable_refunds_wall_seconds_and_drops_the_lease():
    lease = "tok" + "1".zfill(40)
    out = run(admit(op="grade", key=K1), settle(lease, 135), finish(lease, outcome="denied"))
    assert out["results"][2]["body"]["refunded_wall_seconds"] == 135
    (command,) = out["store"]["commands"]
    assert command["state"] == "retryable" and command["wall_seconds"] == 0
    assert out["store"]["leases"] == []
    # Only wall seconds come back; the request still counts.
    assert counters(out["store"]) == {("account", A["id"]): (1, 0), ("deployment", ""): (1, 0)}


def test_only_a_typed_infrastructure_failure_refunds_after_running():
    lease = "tok" + "1".zfill(40)
    infra = run(admit(op="pdf_render", key=K1), finish(lease, outcome="infrastructure"))
    assert counters(infra["store"])[("account", A["id"])] == (1, 0)
    assert infra["store"]["commands"][0]["state"] == "failed_infrastructure"
    for outcome in ("error", "completed"):
        kept = run(admit(op="pdf_render", key=K1), finish(lease, outcome=outcome))
        assert counters(kept["store"])[("account", A["id"])] == (1, 25), outcome


def test_a_refund_counts_against_the_hour_it_was_charged_in():
    lease = "tok" + "1".zfill(40)
    out = run(admit(op="take_home_submit", key=K1, now=T0 + HOUR - 61), finish(lease, outcome="denied", now=T0 + HOUR))
    hours = {(c["bucket"], c["hour"]): c["wall_seconds"] for c in out["store"]["counters"]}
    assert hours == {("account", T0 // HOUR): 0, ("deployment", T0 // HOUR): 0}


def test_a_demo_refund_reaches_the_demo_bucket():
    lease = "tok" + "1".zfill(40)
    out = run(admit(account=D, op="evaluate"), settle(lease, 30, account=D), finish(lease, "denied", account=D))
    assert counters(out["store"])[("demo", "")] == (1, 0)


@pytest.mark.parametrize(
    "result, kept",
    [
        ({"status": 200, "body": {"passed": 1}}, True),
        ({"status": 201, "body": None}, True),
        ({"status": 500, "body": {}}, False),
        ({"status": 200}, False),
        ({"status": 200, "body": {}, "extra": 1}, False),
        ({"status": 200, "body": "x" * (256 * 1024)}, False),
    ],
)
def test_a_completed_command_keeps_only_a_storable_result(result, kept):
    out = run(admit(key=K1), finish("tok" + "1".zfill(40), result=result))
    (command,) = out["store"]["commands"]
    assert command["state"] == "completed"
    assert command["result"] == (result if kept else None)


def test_usage_reports_the_accounts_hour():
    out = run(admit(), admit(op="pdf_render"), {"call": "usage", "account": A, "now": T0})
    assert out["results"][-1] == {
        "v": "admission/v1",
        "hour": T0 // HOUR,
        "tier": "standard",
        "requests": 2,
        "wall_seconds": 28,
        "in_flight": 2,
        "limits": {"requests": 120, "wall_seconds": 1800, "in_flight": 2},
    }


def test_the_sweep_repairs_stuck_commands_and_drops_expired_rows():
    out = run(
        admit(key=K1),
        admit(key=K2, now=T0 + 10),
        finish("tok" + "2".zfill(40), result={"status": 200, "body": {}}, now=T0 + 11),
        {"call": "sweep", "now": T0 + 33},
        {"call": "dump"},
        {"call": "sweep", "now": T0 + 25 * HOUR},
    )
    assert out["results"][3] == {"repaired": 1}
    mid = out["results"][4]
    assert sorted(c["state"] for c in mid["commands"]) == ["completed", "failed_infrastructure"]
    assert mid["leases"] == []
    # Nothing was refunded by the repair.
    assert counters(mid)[("account", A["id"])] == (2, 6)
    assert out["store"] == {"commands": [], "counters": [], "leases": []}


# ---- input checks ------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"operation": "execute", "wall_seconds": 3},
        {"operation": "run", "wall_seconds": 4},
        {"operation": "run", "wall_seconds": 3.5},
        {"operation": "evaluate", "wall_seconds": 321},
        {"operation": "run", "wall_seconds": 3, "account": "someone-else"},
        {"operation": "run", "wall_seconds": 3, "tier": "standard"},
        {"operation": "run", "wall_seconds": 3, "command_id": K1},
        {"operation": "run", "wall_seconds": 3, "fingerprint": FP1},
        {"operation": "run", "wall_seconds": 3, "command_id": K1.upper(), "fingerprint": FP1},
        {"operation": "run", "wall_seconds": 3, "command_id": "0190f000-0000-4000-8000-000000000001", "fingerprint": FP1},
        {"operation": "run", "wall_seconds": 3, "command_id": K1, "fingerprint": "A" * 64},
        {"operation": "run", "wall_seconds": 3, "idempotency": "off"},
        [],
        None,
    ],
)
def test_admit_refuses_malformed_input_and_anything_the_caller_shouldnt_choose(body):
    assert run({"call": "checkAdmit", "input": body})["results"] == [None]


@pytest.mark.parametrize(
    "call, body",
    [
        ("checkSettle", {"lease": "short", "wall_seconds": 3}),
        ("checkSettle", {"lease": "tok" + "1".zfill(40), "wall_seconds": -1}),
        ("checkSettle", {"lease": "tok" + "1".zfill(40), "wall_seconds": 3, "account": "x"}),
        ("checkFinish", {"lease": "tok" + "1".zfill(40), "outcome": "refund"}),
        ("checkFinish", {"lease": "tok" + "1".zfill(40), "outcome": "denied", "result": {"status": 200, "body": {}}}),
    ],
)
def test_settle_and_finish_refuse_malformed_input(call, body):
    assert run({"call": call, "input": body})["results"] == [None]


# ---- tier and demo fields ----------------------------------------------------


def test_the_tier_comes_from_is_demo_on_the_auth_record():
    out = run(
        {"call": "tierOf", "fields": {"is_demo": True}},
        {"call": "tierOf", "fields": {"is_demo": False}},
        {"call": "tierOf", "fields": {}},
        {"call": "tierOf", "fields": None},
    )
    assert out["results"] == ["demo", "standard", "standard", "standard"]


@pytest.mark.parametrize("field", ["is_demo", "demo_run_used", "demo_evaluate_used"])
def test_no_client_sets_or_changes_the_demo_fields(field):
    out = run(
        {"call": "guardDemoCreate", "fields": {field: True}},
        {"call": "guardDemoUpdate", "fields": {field: True}, "original": {field: False}},
        {"call": "guardDemoUpdate", "fields": {field: False}, "original": {field: True}},
        {"call": "guardDemoOAuth2", "data": {"provider": "github", "createData": {field: True}}},
        {"call": "guardDemoOAuth2", "data": {"provider": "github", "createData": {field: False}}},
    )
    for result in out["results"]:
        assert result == {"allowed": False, "bad_request": True, "message": "These account fields can't be changed."}


def test_unchanged_demo_fields_and_superusers_pass():
    out = run(
        {"call": "guardDemoCreate", "fields": {}},
        {"call": "guardDemoUpdate", "fields": {"is_demo": True}, "original": {"is_demo": True}},
        {"call": "guardDemoUpdate", "fields": {"is_demo": True, "demo_run_used": False}, "original": {"is_demo": True}},
        {"call": "guardDemoCreate", "fields": {"is_demo": True}, "superuser": True},
        {"call": "guardDemoUpdate", "fields": {"is_demo": False}, "original": {"is_demo": True}, "superuser": True},
        {"call": "guardDemoOAuth2", "data": {"createData": {"name": "x"}}},
        {"call": "guardDemoOAuth2", "data": {"createData": {"is_demo": True}}, "isNewRecord": False},
    )
    assert out["results"] == [{"allowed": True}] * 7


# ---- registration ------------------------------------------------------------

REGISTRATION = r"""
const path = require("path");
const [hooksDir] = process.argv.slice(1);
const seen = { routes: [], crons: [], hooks: [] };
globalThis.__hooks = hooksDir;
globalThis.$apis = { requireRecordAuth: (...c) => ({ requireRecordAuth: c }) };
globalThis.routerAdd = (method, route, handler, ...middlewares) => seen.routes.push({ method, route, middlewares });
globalThis.cronAdd = (id, expr) => seen.crons.push({ id, expr });
for (const name of ["onRecordBeforeCreateRequest", "onRecordBeforeUpdateRequest", "onRecordBeforeAuthWithOAuth2Request"]) {
  globalThis[name] = (fn, ...tags) => seen.hooks.push({ name, tags });
}
require(path.join(hooksDir, "admission.pb.js"));
process.stdout.write(JSON.stringify(seen));
"""


def test_every_admission_route_needs_a_users_bearer():
    node = shutil.which("node")
    assert node
    res = subprocess.run([node, "-e", REGISTRATION, str(HOOKS)], capture_output=True, text=True, timeout=60, check=True)
    seen = json.loads(res.stdout)
    assert [(r["method"], r["route"]) for r in seen["routes"]] == [
        ("POST", "/api/rounds/admission/admit"),
        ("POST", "/api/rounds/admission/settle"),
        ("POST", "/api/rounds/admission/finish"),
        ("GET", "/api/rounds/admission/usage"),
    ]
    for route in seen["routes"]:
        assert route["middlewares"] == [{"requireRecordAuth": ["users"]}]
    assert seen["crons"] == [{"id": "rounds_admission_sweep", "expr": "*/5 * * * *"}]
    assert seen["hooks"] == [
        {"name": "onRecordBeforeCreateRequest", "tags": ["users"]},
        {"name": "onRecordBeforeUpdateRequest", "tags": ["users"]},
        {"name": "onRecordBeforeAuthWithOAuth2Request", "tags": ["users"]},
    ]


def test_the_admission_module_is_not_auto_loaded_as_a_hook_file():
    # PocketBase loads only *.pb.js files, so admission.js stays a require target.
    assert (HOOKS / "admission.js").exists()
    assert "require(`${__hooks}/admission.js`)" in (HOOKS / "admission.pb.js").read_text()
