"""Admission state in pb_hooks/admission.js (ROUNDS-00A-L01 stage 3).

Steps 6 and 7 of admission/v1 under node, on an in-memory store with the
PocketBase store's contract (admission_runner.cjs): idempotency by
(account, command_id) and fingerprint, hourly quotas per account,
deployment, and demo bucket, leases as in-flight counts with a window
fixed at admission, one bounded settle, finishing with refunds, the
sweep, the runner key, and the demo-field guards. The harness runs the
same functions on a real PocketBase across two runner replicas."""
from __future__ import annotations

import hashlib
import itertools
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
GRACE = 30
HOLD = {"grade": 90, "take_home_submit": 90}
_tokens = itertools.count(1)


def run(*steps: dict) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run(
        [node, str(RUNNER), str(HOOKS)],
        input=json.dumps({"steps": list(steps)}),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def new_token() -> str:
    """A lease token as the runner makes one: 43 letters and digits."""
    return "tok" + str(next(_tokens)).zfill(40)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def admit(account=A, op="run", key=None, fp=None, wall=None, most=None, mode="enforce", quota=None, now=T0,
          token=None) -> dict:
    """An admit step; its lease token, which only the test (the runner)
    holds, is on the step as ``token``."""
    walls = {"run": 3, "evaluate": 3, "run_project": 10, "grade": 45, "take_home_run": 60,
             "take_home_submit": 120, "pdf_render": 25}
    token = token or new_token()
    body = {"operation": op, "wall_seconds": walls[op] if wall is None else wall, "idempotency": mode,
            "lease_hash": sha256(token)}
    if most is not None:
        body["max_wall_seconds"] = most
    if quota is not None:
        body["quota"] = quota
    if key is not None:
        body["command_id"] = key
        body["fingerprint"] = FP1 if fp is None else fp
    return {"call": "admit", "account": account, "input": body, "now": now, "token": token}


def finish(lease, outcome="completed", result=None, account=A, now=T0) -> dict:
    body = {"lease": lease["token"] if isinstance(lease, dict) else lease, "outcome": outcome}
    if result is not None:
        body["result"] = result
    return {"call": "finish", "account": account, "input": body, "now": now}


def settle(lease, wall, account=A, now=T0) -> dict:
    token = lease["token"] if isinstance(lease, dict) else lease
    return {"call": "settle", "account": account, "input": {"lease": token, "wall_seconds": wall}, "now": now}


def seed(bucket, account="", requests=0, wall=0, now=T0) -> dict:
    return {"call": "seedCounter", "bucket": bucket, "account": account, "hour": now // HOUR,
            "requests": requests, "wall_seconds": wall}


def counters(store: dict) -> dict:
    return {(c["bucket"], c["account"]): (c["requests"], c["wall_seconds"]) for c in store["counters"]}


# ---- idempotency (step 6) ----------------------------------------------------


def test_a_new_command_writes_the_row_the_charge_and_the_lease_together():
    step = admit(key=K1)
    out = run(step)
    (decision,) = out["results"]
    assert decision["idempotency"] == "new" and decision["quota"] == "ok" and decision["leased"] is True
    (command,) = out["store"]["commands"]
    assert (command["account"], command["command_id"], command["state"]) == (A["id"], K1, "in_flight")
    assert command["fingerprint"] == FP1 and command["wall_seconds"] == 3
    assert command["expires_at"] == T0 + 24 * HOUR
    (lease,) = out["store"]["leases"]
    assert lease["command"] == command["id"] and lease["expires_at"] == T0 + 3 + GRACE
    assert lease["counted"] is True and lease["settled"] is False and lease["max_wall_seconds"] == 3
    # The runner makes the token; only its hash reaches the store.
    assert lease["token_hash"] == sha256(step["token"]) and step["token"] not in json.dumps(out)
    assert counters(out["store"]) == {("account", A["id"]): (1, 3), ("deployment", ""): (1, 3)}


def test_a_duplicate_while_in_flight_is_refused_and_writes_nothing():
    out = run(admit(key=K1), admit(key=K1), admit(key=K1, mode="enforce"))
    first, second, third = out["results"]
    assert first["idempotency"] == "new"
    for again in (second, third):
        assert again["idempotency"] == "in_flight" and again["leased"] is False and again["quota"] == "skipped"
    assert len(out["store"]["commands"]) == 1 and len(out["store"]["leases"]) == 1
    assert counters(out["store"])[("account", A["id"])] == (1, 3)


def test_a_duplicate_of_a_running_command_hears_when_to_try_again():
    # At most 10 seconds, or less when the running lease ends sooner.
    soon = run(admit(key=K1), admit(key=K1, now=T0 + 30))
    assert soon["results"][1]["retry_after"] == 3
    later = run(admit(op="grade", key=K1), admit(op="grade", key=K1, now=T0 + 1))
    assert later["results"][1]["retry_after"] == 10


def test_a_completed_replay_returns_the_stored_result_and_writes_nothing():
    first = admit(key=K1)
    result = {"status": 200, "body": {"stdout": "ok\n", "return_value": [1, 2]}}
    out = run(first, finish(first, result=result), admit(key=K1, now=T0 + 60))
    _admitted, finished, replay = out["results"]
    assert finished == {"status": 200, "body": {"v": "admission/v1", "refunded_wall_seconds": 0}}
    assert replay["idempotency"] == "replay" and replay["result"] == result and replay["leased"] is False
    assert out["store"]["leases"] == []
    assert counters(out["store"])[("account", A["id"])] == (1, 3)


@pytest.mark.parametrize("change", [{"fp": FP2}, {"op": "evaluate"}])
def test_a_key_reused_for_another_request_is_refused(change):
    first = admit(key=K1)
    out = run(first, finish(first), admit(key=K1, **change))
    assert out["results"][2]["idempotency"] == "mismatch"
    assert out["results"][2]["result"] is None and out["results"][2]["leased"] is False
    assert len(out["store"]["commands"]) == 1 and out["store"]["commands"][0]["state"] == "completed"


def test_observe_mode_runs_a_refused_duplicate_with_a_charge_and_a_lease_but_no_row_change():
    first = admit(key=K1)
    out = run(first, finish(first, result={"status": 200, "body": {}}),
              admit(key=K1, mode="observe"), admit(key=K1, fp=FP2, mode="observe"))
    _first, _finished, replay, mismatch = out["results"]
    assert replay["idempotency"] == "replay" and replay["leased"] is True and replay["result"] is None
    assert mismatch["idempotency"] == "mismatch" and mismatch["leased"] is True
    (command,) = out["store"]["commands"]
    assert command["state"] == "completed" and command["fingerprint"] == FP1
    assert [lease["command"] for lease in out["store"]["leases"]] == ["", ""]
    assert counters(out["store"])[("account", A["id"])] == (3, 9)


def test_a_key_older_than_24_hours_starts_over():
    later = T0 + 24 * HOUR
    first = admit(key=K1)
    out = run(first, finish(first, result={"status": 200, "body": {}}), admit(key=K1, fp=FP2, now=later))
    assert out["results"][2]["idempotency"] == "new"
    (command,) = out["store"]["commands"]
    assert command["fingerprint"] == FP2 and command["state"] == "in_flight"


@pytest.mark.parametrize("outcome, state", [("denied", "retryable"), ("infrastructure", "failed_infrastructure"),
                                            ("error", "failed_infrastructure")])
def test_a_denied_or_failed_command_runs_admission_again_with_its_key(outcome, state):
    first = admit(key=K1)
    out = run(first, finish(first, outcome=outcome), {"call": "dump"}, admit(key=K1))
    assert out["results"][2]["commands"][0]["state"] == state
    retry = out["results"][3]
    assert retry["idempotency"] == "retry" and retry["leased"] is True
    (command,) = out["store"]["commands"]
    assert command["state"] == "in_flight"


def test_an_in_flight_command_whose_lease_expired_can_be_retried():
    expired = T0 + 3 + GRACE
    out = run(admit(key=K1), admit(key=K1, now=expired))
    assert out["results"][1]["idempotency"] == "retry"
    # The stale lease is gone; only the new one counts.
    (lease,) = out["store"]["leases"]
    assert lease["expires_at"] == expired + 3 + GRACE


def test_a_lost_admit_answer_can_still_be_finished_with_the_runners_token():
    # The runner made the token, so it can release a lease it never heard
    # about; the key then runs admission again.
    first = admit(key=K1)
    out = run(first, finish(first, outcome="infrastructure"), admit(key=K1))
    assert out["results"][1]["status"] == 200
    assert out["results"][2]["idempotency"] == "retry"


def test_a_lease_hash_already_in_use_is_refused():
    token = new_token()
    out = run(admit(key=K1, token=token), admit(key=K2, token=token))
    assert out["results"][1] == {"invalid": True}
    assert len(out["store"]["leases"]) == 1 and len(out["store"]["commands"]) == 1


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


def test_a_request_over_any_limit_writes_nothing_when_quota_enforces():
    out = run(seed("account", A["id"], requests=120), admit(key=K1, quota="enforce"))
    decision = out["results"][-1]
    assert decision["quota"] == "exceeded" and decision["leased"] is False
    assert out["store"]["commands"] == [] and out["store"]["leases"] == []
    assert counters(out["store"]) == {("account", A["id"]): (120, 0)}


def test_observe_keeps_idempotency_past_a_limit_and_counts_nothing_past_it():
    # Observe lets the request run: its command row is written, so a retry
    # with its key replays, and its lease neither charges nor counts.
    first = admit(key=K1, quota="observe")
    out = run(seed("account", A["id"], requests=120), first, admit(quota="observe"),
              finish(first, result={"status": 200, "body": {"ok": True}}), admit(key=K1, quota="observe"))
    over, other = out["results"][1], out["results"][2]
    assert over["quota"] == "exceeded" and over["leased"] is True and other["leased"] is True
    replay = out["results"][4]
    assert replay["idempotency"] == "replay" and replay["result"] == {"status": 200, "body": {"ok": True}}
    assert counters(out["store"]) == {("account", A["id"]): (120, 0)}
    assert all(lease["counted"] is False for lease in out["store"]["leases"])


def test_quota_off_counts_nothing_and_still_keeps_idempotency():
    first = admit(key=K1, quota="off")
    out = run(first, admit(quota="off"), admit(quota="off"), {"call": "usage", "account": A, "now": T0},
              finish(first, outcome="denied"))
    assert [r["quota"] for r in out["results"][:3]] == ["skipped"] * 3
    usage = out["results"][3]
    assert usage["requests"] == 0 and usage["in_flight"] == 0
    assert out["results"][4]["body"]["refunded_wall_seconds"] == 0
    assert out["store"]["counters"] == []
    assert out["store"]["commands"][0]["state"] == "retryable"


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
    first = admit(key=K1)
    out = run(first, admit(account=B, key=K2), finish(first), admit(), admit(account=B))
    assert counters(out["store"]) == {
        ("account", A["id"]): (2, 6),
        ("account", B["id"]): (2, 6),
        ("deployment", ""): (4, 12),
    }


# ---- leases, settling, and finishing -----------------------------------------


@pytest.mark.parametrize("op, wall, most, window", [
    ("run", 3, None, 3 + GRACE),
    ("evaluate", 3, 320, 320 + GRACE),
    ("grade", 45, 360, 360 + HOLD["grade"] + GRACE),
    ("take_home_submit", 120, None, 120 + HOLD["take_home_submit"] + GRACE),
])
def test_a_leases_window_is_fixed_by_what_was_admitted(op, wall, most, window):
    out = run(admit(op=op, wall=wall, most=most))
    assert out["store"]["leases"][0]["expires_at"] == T0 + window


def test_settle_moves_the_charge_once_and_brings_the_window_closer():
    first = admit(op="evaluate", key=K1, most=320)
    out = run(first, settle(first, 30, now=T0 + 1), {"call": "dump"}, settle(first, 9, now=T0 + 2))
    assert out["results"][1] == {"status": 200, "body": {"v": "admission/v1", "wall_seconds": 30}}
    mid = out["results"][2]
    assert counters(mid)[("account", A["id"])] == (1, 30)
    assert mid["leases"][0]["expires_at"] == T0 + 1 + 30 + GRACE and mid["leases"][0]["settled"] is True
    # A second settle changes nothing.
    assert out["results"][3] == {"status": 409, "body": {"v": "admission/v1", "error": "already_settled"}}
    assert counters(out["store"])[("account", A["id"])] == (1, 30)
    assert out["store"]["commands"][0]["wall_seconds"] == 30
    assert out["store"]["leases"][0]["expires_at"] == T0 + 1 + 30 + GRACE


def test_a_settle_never_takes_the_window_past_what_was_admitted():
    first = admit(op="evaluate", most=320)
    out = run(first, settle(first, 320, now=T0 + 100))
    assert out["results"][1]["status"] == 200
    assert out["store"]["leases"][0]["expires_at"] == T0 + 320 + GRACE


def test_settle_can_lower_the_charge():
    first = admit(op="grade", key=K1, most=360)
    out = run(first, settle(first, 0))
    assert out["results"][1]["status"] == 200
    assert counters(out["store"])[("account", A["id"])] == (1, 0)


@pytest.mark.parametrize("op, most, wall", [("evaluate", None, 4), ("evaluate", 320, 321), ("run", None, 4)])
def test_settle_stays_inside_what_was_admitted(op, most, wall):
    lease = admit(op=op, most=most)
    out = run(lease, settle(lease, wall))
    assert out["results"][1]["status"] == 400, out["results"][1]
    assert out["store"]["leases"][0]["settled"] is False


def test_a_settle_that_raises_the_charge_has_to_fit_the_hour():
    first = admit(op="evaluate", key=K1, most=320)
    out = run(seed("account", A["id"], wall=1790), first, settle(first, 30), {"call": "dump"}, settle(first, 10))
    refused = out["results"][2]
    assert refused["status"] == 429 and refused["body"]["quota"] == "exceeded"
    assert refused["body"]["retry_after"] == HOUR - 60
    # Nothing moved, and the lease can still settle within the limit.
    assert counters(out["results"][3])[("account", A["id"])] == (1, 1793)
    assert out["results"][4]["status"] == 200
    assert counters(out["store"])[("account", A["id"])] == (1, 1800)


def test_a_demo_settle_can_not_overdraw_the_shared_demo_hour():
    first = admit(account=D, op="evaluate", most=320)
    out = run(first, settle(first, 320, account=D))
    assert out["results"][1]["status"] == 429 and out["results"][1]["body"]["quota"] == "demo_limit"
    assert counters(out["store"])[("demo", "")] == (1, 3)


def test_an_expired_lease_can_not_settle():
    first = admit(op="evaluate", most=320)
    out = run(first, settle(first, 30, now=T0 + 320 + GRACE))
    assert out["results"][1]["status"] == 404


def test_another_accounts_lease_is_not_found():
    first = admit(key=K1)
    out = run(first, settle(first, 3, account=B), finish(first, account=B))
    assert out["results"][1]["status"] == 404 and out["results"][2]["status"] == 404
    assert out["store"]["commands"][0]["state"] == "in_flight" and len(out["store"]["leases"]) == 1


def test_a_finished_lease_cannot_be_finished_again():
    first = admit(key=K1)
    out = run(first, finish(first, outcome="denied"), finish(first, outcome="denied"))
    assert out["results"][1]["status"] == 200 and out["results"][2]["status"] == 404
    assert counters(out["store"])[("account", A["id"])] == (1, 0)


def test_a_step_8_or_9_denial_leaves_the_command_retryable_refunds_wall_seconds_and_drops_the_lease():
    first = admit(op="grade", key=K1, most=360)
    out = run(first, settle(first, 135), finish(first, outcome="denied"))
    assert out["results"][2]["body"]["refunded_wall_seconds"] == 135
    (command,) = out["store"]["commands"]
    assert command["state"] == "retryable" and command["wall_seconds"] == 0
    assert out["store"]["leases"] == []
    # Only wall seconds come back; the request still counts.
    assert counters(out["store"]) == {("account", A["id"]): (1, 0), ("deployment", ""): (1, 0)}


def test_only_a_typed_infrastructure_failure_refunds_after_running():
    first = admit(op="pdf_render", key=K1)
    infra = run(first, finish(first, outcome="infrastructure"))
    assert counters(infra["store"])[("account", A["id"])] == (1, 0)
    assert infra["store"]["commands"][0]["state"] == "failed_infrastructure"
    for outcome in ("error", "completed"):
        again = admit(op="pdf_render", key=K1)
        kept = run(again, finish(again, outcome=outcome))
        assert counters(kept["store"])[("account", A["id"])] == (1, 25), outcome


def test_a_refund_counts_against_the_hour_it_was_charged_in():
    first = admit(op="take_home_submit", key=K1, now=T0 + HOUR - 61)
    out = run(first, finish(first, outcome="denied", now=T0 + HOUR))
    hours = {(c["bucket"], c["hour"]): c["wall_seconds"] for c in out["store"]["counters"]}
    assert hours == {("account", T0 // HOUR): 0, ("deployment", T0 // HOUR): 0}


def test_a_demo_refund_reaches_the_demo_bucket():
    first = admit(account=D, op="evaluate", most=320)
    out = run(first, settle(first, 30, account=D), finish(first, "denied", account=D))
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
    first = admit(key=K1)
    out = run(first, finish(first, result=result))
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
    second = admit(key=K2, now=T0 + 10)
    out = run(
        admit(key=K1),
        second,
        finish(second, result={"status": 200, "body": {}}, now=T0 + 11),
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


def test_the_sweep_reclaims_a_settled_lease_at_its_admitted_window():
    first = admit(op="grade", key=K1, most=360)
    window = T0 + 360 + HOLD["grade"] + GRACE
    out = run(first, settle(first, 360, now=T0 + 1), {"call": "sweep", "now": window - 1}, {"call": "dump"},
              {"call": "sweep", "now": window})
    assert out["results"][2] == {"repaired": 0} and len(out["results"][3]["leases"]) == 1
    assert out["results"][4] == {"repaired": 1}
    assert out["store"]["leases"] == [] and out["store"]["commands"][0]["state"] == "failed_infrastructure"


# ---- the runner key ----------------------------------------------------------

KEY = "k" * 40


@pytest.mark.parametrize(
    "headers, secret, expected",
    [
        ({"x_rounds_admission_key": KEY}, KEY, None),
        ({}, KEY, {"status": 403, "body": {"v": "admission/v1", "error": "forbidden"}}),
        ({"x_rounds_admission_key": "k" * 39 + "j"}, KEY, {"status": 403, "body": {"v": "admission/v1", "error": "forbidden"}}),
        ({"x_rounds_admission_key": KEY + "k"}, KEY, {"status": 403, "body": {"v": "admission/v1", "error": "forbidden"}}),
        ({"authorization": KEY}, KEY, {"status": 403, "body": {"v": "admission/v1", "error": "forbidden"}}),
        ({"x_rounds_admission_key": ""}, "", {"status": 503, "body": {"v": "admission/v1", "error": "unconfigured"}}),
        ({"x_rounds_admission_key": "short"}, "short", {"status": 503, "body": {"v": "admission/v1", "error": "unconfigured"}}),
        (None, None, {"status": 503, "body": {"v": "admission/v1", "error": "unconfigured"}}),
    ],
)
def test_only_the_runners_key_reaches_the_write_routes(headers, secret, expected):
    assert run({"call": "runnerKeyError", "headers": headers, "secret": secret})["results"] == [expected]


# handle() as the routes call it, with PocketBase's globals faked: the
# answer for each request, and how many transactions it opened.
HANDLE = r"""
const path = require("path");
const [hooksDir, raw] = process.argv.slice(1);
const { secret, requests } = JSON.parse(raw);
globalThis.UnauthorizedError = class UnauthorizedError extends Error {};
globalThis.$apis = { requestInfo: (c) => c.info };
globalThis.$os = { getenv: (name) => (name === "ROUNDS_ADMISSION_SECRET" ? secret : "") };
let transactions = 0;
globalThis.$app = { dao: () => ({ runInTransaction: () => { transactions += 1; } }) };
const admission = require(path.join(hooksDir, "admission.js"));
const out = requests.map((r) => {
  const c = { info: { authRecord: r.signedIn ? { id: "acct00000000001", getBool: () => false } : null,
                      headers: r.headers, data: r.data },
              json: (status, body) => ({ status, body }) };
  try {
    return admission.handle(c, r.action);
  } catch (err) {
    return { thrown: err.constructor.name };
  }
});
process.stdout.write(JSON.stringify({ out, transactions }));
"""


def handle(secret, *requests):
    node = shutil.which("node")
    assert node
    arg = json.dumps({"secret": secret, "requests": list(requests)})
    res = subprocess.run([node, "-e", HANDLE, str(HOOKS), arg], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def test_the_write_routes_check_the_runner_key_before_anything_else():
    good = {"x_rounds_admission_key": KEY}
    admit_body = {"operation": "run", "wall_seconds": 3, "lease_hash": "c" * 64}
    seen = handle(
        KEY,
        {"action": "admit", "signedIn": True, "headers": {}, "data": admit_body},
        {"action": "settle", "signedIn": True, "headers": {"x_rounds_admission_key": "k" * 39 + "j"},
         "data": {"lease": "a" * 43, "wall_seconds": 3}},
        {"action": "finish", "signedIn": True, "headers": {"authorization": KEY},
         "data": {"lease": "a" * 43, "outcome": "denied"}},
        {"action": "finish", "signedIn": True, "headers": good, "data": {"lease": "short", "outcome": "denied"}},
        {"action": "admit", "signedIn": False, "headers": good, "data": admit_body},
    )
    forbidden = {"status": 403, "body": {"v": "admission/v1", "error": "forbidden"}}
    assert seen["out"] == [
        forbidden,
        forbidden,
        forbidden,
        # With the key, a malformed body is refused before any transaction.
        {"status": 400, "body": {"v": "admission/v1", "error": "invalid_request"}},
        {"thrown": "UnauthorizedError"},
    ]
    assert seen["transactions"] == 0
    unconfigured = handle("", {"action": "admit", "signedIn": True, "headers": good, "data": admit_body})
    assert unconfigured["out"] == [{"status": 503, "body": {"v": "admission/v1", "error": "unconfigured"}}]
    assert unconfigured["transactions"] == 0


# ---- input checks ------------------------------------------------------------

LEASE_HASH = "c" * 64


@pytest.mark.parametrize(
    "body",
    [
        {"operation": "execute", "wall_seconds": 3, "lease_hash": LEASE_HASH},
        {"operation": "run", "wall_seconds": 4, "lease_hash": LEASE_HASH},
        {"operation": "run", "wall_seconds": 3.5, "lease_hash": LEASE_HASH},
        {"operation": "evaluate", "wall_seconds": 321, "lease_hash": LEASE_HASH},
        {"operation": "run", "wall_seconds": 3, "account": "someone-else", "lease_hash": LEASE_HASH},
        {"operation": "run", "wall_seconds": 3, "tier": "standard", "lease_hash": LEASE_HASH},
        {"operation": "run", "wall_seconds": 3, "command_id": K1, "lease_hash": LEASE_HASH},
        {"operation": "run", "wall_seconds": 3, "fingerprint": FP1, "lease_hash": LEASE_HASH},
        {"operation": "run", "wall_seconds": 3, "command_id": K1.upper(), "fingerprint": FP1, "lease_hash": LEASE_HASH},
        {"operation": "run", "wall_seconds": 3, "command_id": "0190f000-0000-4000-8000-000000000001", "fingerprint": FP1,
         "lease_hash": LEASE_HASH},
        {"operation": "run", "wall_seconds": 3, "command_id": K1, "fingerprint": "A" * 64, "lease_hash": LEASE_HASH},
        {"operation": "run", "wall_seconds": 3, "idempotency": "off", "lease_hash": LEASE_HASH},
        {"operation": "run", "wall_seconds": 3, "quota": "maybe", "lease_hash": LEASE_HASH},
        # The runner makes every lease's token and sends its hash.
        {"operation": "run", "wall_seconds": 3},
        {"operation": "run", "wall_seconds": 3, "lease_hash": "C" * 64},
        {"operation": "run", "wall_seconds": 3, "lease": "tok" + "1".zfill(40), "lease_hash": LEASE_HASH},
        # Nothing settles past the operation's most, or below what's charged now.
        {"operation": "grade", "wall_seconds": 45, "max_wall_seconds": 361, "lease_hash": LEASE_HASH},
        {"operation": "evaluate", "wall_seconds": 30, "max_wall_seconds": 3, "lease_hash": LEASE_HASH},
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
