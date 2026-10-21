"""The execution job store in pb_hooks/execution.js (ROUNDS-00A-L03 PR 1).

The decisions under node, on an in-memory store with the PocketBase
store's contract (execution_runner.cjs): enqueue against #1's admission
row, owner cancel, claim with its per-account cap, fenced heartbeats and
completes, the three reaper paths, the worker record, and the guard on
attempt rows' envelope. The PocketBase store runs on a real PocketBase in
the harness."""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HOOKS = HERE.parent / "pb_hooks"
RUNNER = HERE / "execution_runner.cjs"

T0 = 1_800_000_000
A = {"id": "acct00000000001"}
B = {"id": "acct00000000002"}
FP = "a" * 64
OTHER_FP = "b" * 64
REF = {"track": "coding", "slug": "two-sum", "variant": "python", "version": 1}
ENVELOPE = "rounds.execution-envelope/v1"
_keys = itertools.count(1)
_tokens = itertools.count(1)


def run(*steps: dict) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run([node, str(RUNNER), str(HOOKS)], input=json.dumps({"steps": list(steps)}),
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def new_key() -> str:
    return f"0190f000-0000-7000-8000-{next(_keys):012d}"


def new_token() -> str:
    """A fencing token as the runner makes one: 43 letters and digits."""
    return "tok" + str(next(_tokens)).zfill(40)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def command(key, account=A, operation="run", fingerprint=FP, state="in_flight", expires_at=T0 + 86400) -> dict:
    return {"call": "seedCommand", "row": {"account": account["id"], "command_id": key, "operation": operation,
                                           "fingerprint": fingerprint, "state": state, "expires_at": expires_at}}


def enqueue(key, account=A, kind="run", fingerprint=FP, now=T0, **overrides) -> dict:
    body = {"command_id": key, "kind": kind, "definition": REF, "fingerprint": fingerprint,
            "source_checksum": "c" * 64, "input_digest": "d" * 64, "input": {"code": "print(1)", "input": {}}}
    body.update(overrides)
    return {"call": "enqueue", "account": account, "input": body, "now": now}


def claim(token, worker="runner-a", now=T0) -> dict:
    return {"call": "claim", "input": {"worker": worker, "token_hash": sha256(token)}, "now": now}


def heartbeat(attempt_id, token, now=T0, budget=None) -> dict:
    body = {"attempt_id": attempt_id, "token": token}
    if budget is not None:
        body.update(started=True, budget_s=budget)
    return {"call": "heartbeat", "input": body, "now": now}


def result(job_id, state="completed", outcome="passed", authoritative=None, limit=None, score=None,
           cleanup="confirmed") -> dict:
    if authoritative is None:
        authoritative = (state, outcome) in {("completed", "passed"), ("completed", "candidate-failure"),
                                             ("completed", "resource-limit"), ("timed-out", "resource-limit")}
    if score is None and outcome in ("passed", "candidate-failure"):
        score = 1.0 if outcome == "passed" else 0.0
    user = {"version": ENVELOPE, "job_id": job_id, "state": state, "outcome_class": outcome,
            "authoritative": authoritative, "limit": limit, "parts": [], "score": score, "definition": None,
            "queued_at": T0, "started_at": T0, "finished_at": T0 + 1, "cleanup": cleanup, "rubric": None,
            "output": None}
    operator = {"version": ENVELOPE, "executor_kind": "legacy-in-process", "worker": "runner-a", "attempt_number": 1,
                "source_checksum": "c" * 64, "input_digest": "d" * 64, "output_sha256": None, "output_bytes": None,
                "exit_status": 0, "cpu_time_ms": None, "peak_rss_bytes": None, "build_revision": None,
                "image_digest": None, "graded_row": None}
    return {"state": state, "outcome_class": outcome, "authoritative": authoritative, "cleanup": cleanup,
            "user_view": user, "operator_view": operator}


def complete(attempt_id, token, body, now=T0 + 1) -> dict:
    return {"call": "complete", "input": {"attempt_id": attempt_id, "token": token, "result": body}, "now": now}


def reap(now) -> dict:
    return {"call": "reap", "now": now}


def started_job(key=None, account=A, kind="run", budget=3, now=T0):
    """Steps that leave one job started under a known token."""
    key = key or new_key()
    token = new_token()
    steps = [command(key, account=account, operation=kind), enqueue(key, account=account, kind=kind, now=now),
             claim(token, now=now)]
    out = run(*steps)
    attempt = out["results"][-1]["body"]["attempt"]
    job = out["results"][-1]["body"]["job"]
    return steps + [heartbeat(attempt["id"], token, now=now, budget=budget)], job, attempt, token


# ---- enqueue ------------------------------------------------------------------


def test_enqueue_needs_the_accounts_in_flight_admission_row():
    key = new_key()
    out = run(enqueue(key), command(key, account=B), enqueue(key),
              command(new_key(), state="completed"))
    assert out["results"][0] == {"status": 404, "body": {"v": "execution/v1", "error": "not_admitted"}}
    assert out["results"][2]["status"] == 404
    assert out["store"]["jobs"] == []


@pytest.mark.parametrize("seed", [{"fingerprint": OTHER_FP}, {"operation": "evaluate"}], ids=["fingerprint", "operation"])
def test_enqueue_refuses_a_command_admitted_for_something_else(seed):
    key = new_key()
    row = command(key)
    row["row"].update(seed)
    out = run(row, enqueue(key))
    assert out["results"][1] == {"status": 409, "body": {"v": "execution/v1", "error": "mismatch"}}
    assert out["store"]["jobs"] == []


@pytest.mark.parametrize("state", ["completed", "retryable", "failed_infrastructure"])
def test_enqueue_needs_the_command_in_flight(state):
    key = new_key()
    out = run(command(key, state=state), enqueue(key))
    assert out["results"][1]["status"] == 409 and out["store"]["jobs"] == []


def test_an_expired_command_is_not_admitted():
    key = new_key()
    out = run(command(key, expires_at=T0), enqueue(key))
    assert out["results"][1]["status"] == 404


def test_enqueue_queues_one_job_and_records_it_on_the_command():
    key = new_key()
    out = run(command(key, operation="take_home_submit"), enqueue(key, kind="take_home_submit"))
    body = out["results"][1]["body"]
    assert body["duplicate"] is False and body["requeued"] is False
    (job,) = out["store"]["jobs"]
    assert (job["state"], job["kind"], job["purpose"], job["queued_at"]) == ("queued", "take_home_submit", "grading", T0)
    assert job["definition"] == REF and job["input"] == {"code": "print(1)", "input": {}}
    assert job["attempts"] == 0 and job["attempts_started"] == 0
    (row,) = out["store"]["commands"]
    assert row["job"] == job["id"] == body["job"]["id"]


def test_a_duplicate_enqueue_answers_the_same_job():
    key = new_key()
    out = run(command(key), enqueue(key), enqueue(key, now=T0 + 5))
    first, second = out["results"][1]["body"], out["results"][2]["body"]
    assert second["duplicate"] is True and second["job"]["id"] == first["job"]["id"]
    assert len(out["store"]["jobs"]) == 1 and out["store"]["jobs"][0]["queued_at"] == T0


def test_a_job_enqueued_under_another_fingerprint_is_a_mismatch():
    key = new_key()
    out = run(command(key), enqueue(key), command(key, fingerprint=OTHER_FP))
    # The account's first command row still matches, so its job does too.
    assert out["results"][1]["status"] == 200
    out = run(command(key), enqueue(key, kind="run"), enqueue(key, kind="run", fingerprint=OTHER_FP))
    assert out["results"][2]["status"] == 409 and len(out["store"]["jobs"]) == 1


@pytest.mark.parametrize(
    "bad",
    [{"kind": "render"}, {"definition": {**REF, "track": "pdf"}}, {"definition": {**REF, "extra": 1}},
     {"definition": {**REF, "version": 0}}, {"fingerprint": "nothex"}, {"input": []}, {"command_id": "not-a-key"},
     {"extra": True}],
    ids=["kind", "track", "definition-key", "version", "fingerprint", "input", "command-id", "unknown-field"],
)
def test_enqueue_refuses_malformed_input(bad):
    body = enqueue(new_key())["input"]
    body.update(bad)
    (checked,) = run({"call": "checkEnqueue", "input": body})["results"]
    assert checked is None


# ---- cancel ------------------------------------------------------------------


def test_cancel_ends_a_queued_job_at_once_and_is_idempotent():
    key = new_key()
    first = run(command(key), enqueue(key))
    job_id = first["results"][1]["body"]["job"]["id"]
    out = run(command(key), enqueue(key), {"call": "cancel", "account": A, "input": {"job_id": job_id}, "now": T0 + 1},
              {"call": "cancel", "account": A, "input": {"job_id": job_id}, "now": T0 + 2})
    (job,) = out["store"]["jobs"]
    assert (job["state"], job["outcome_class"], job["cleanup"], job["finished_at"]) == ("canceled", "canceled", "confirmed", T0 + 1)
    assert out["results"][3]["body"]["job"]["finished_at"] == T0 + 1


def test_cancel_asks_a_running_job_to_stop():
    steps, job, attempt, token = started_job()
    out = run(*steps, {"call": "cancel", "account": A, "input": {"job_id": job["id"]}, "now": T0 + 1},
              heartbeat(attempt["id"], token, now=T0 + 2))
    assert out["results"][-1]["body"]["cancel_requested"] is True
    assert out["store"]["jobs"][0]["state"] == "started"


def test_another_accounts_job_is_the_same_404_as_an_unknown_one():
    key = new_key()
    first = run(command(key), enqueue(key))
    job_id = first["results"][1]["body"]["job"]["id"]
    out = run(command(key), enqueue(key), {"call": "cancel", "account": B, "input": {"job_id": job_id}, "now": T0},
              {"call": "cancel", "account": B, "input": {"job_id": "zzzzzzzzzzzzzzz"}, "now": T0})
    assert out["results"][2] == out["results"][3] == {"status": 404, "body": {"v": "execution/v1", "error": "not_found"}}
    assert out["store"]["jobs"][0]["state"] == "queued"


# ---- claim ---------------------------------------------------------------------


def test_claim_leases_the_oldest_queued_job_for_thirty_seconds():
    k1, k2 = new_key(), new_key()
    token = new_token()
    out = run(command(k1), command(k2), enqueue(k2, now=T0 + 1), enqueue(k1, now=T0 + 2), claim(token, now=T0 + 3))
    body = out["results"][-1]["body"]
    assert body["job"]["id"] == out["results"][2]["body"]["job"]["id"]
    assert body["job"]["input"] == {"code": "print(1)", "input": {}} and body["job"]["definition"] == REF
    assert body["attempt"]["attempt_number"] == 1 and body["attempt"]["lease_expires_at"] == T0 + 33
    attempt = next(a for a in out["store"]["attempts"])
    assert attempt["token_hash"] == sha256(token) and attempt["state"] == "leased" and attempt["worker"] == "runner-a"
    # The token itself never reaches the store.
    assert token not in json.dumps(out["store"])


def test_two_replicas_never_hold_one_job():
    key = new_key()
    out = run(command(key), enqueue(key), claim(new_token(), worker="runner-a"), claim(new_token(), worker="runner-b"))
    assert out["results"][2]["body"]["job"] is not None
    assert out["results"][3]["body"]["job"] is None
    assert len(out["store"]["attempts"]) == 1


def test_claim_skips_an_account_with_two_active_jobs():
    keys = [new_key() for _ in range(3)]
    steps = [command(k) for k in keys] + [enqueue(k, now=T0 + i) for i, k in enumerate(keys)]
    steps += [command(b_key := new_key(), account=B), enqueue(b_key, account=B, now=T0 + 10)]
    steps += [claim(new_token(), now=T0 + 20) for _ in range(4)]
    out = run(*steps)
    claimed = [r["body"]["job"] for r in out["results"][-4:]]
    assert [j["account"] if j else None for j in claimed] == [A["id"], A["id"], B["id"], None]


CLAIM_SCAN = int(re.search(r"^const CLAIM_SCAN = (\d+);$", (HOOKS / "execution.js").read_text(), re.M).group(1))


def test_one_accounts_backlog_never_holds_another_accounts_job_back():
    # More of A's jobs queued first than one claim considers, then B's one.
    keys = [new_key() for _ in range(CLAIM_SCAN + 10)]
    steps = [command(k) for k in keys] + [enqueue(k, now=T0 + i) for i, k in enumerate(keys)]
    steps += [command(b_key := new_key(), account=B), enqueue(b_key, account=B, now=T0 + 100)]
    steps += [claim(new_token(), now=T0 + 200) for _ in range(3)]
    out = run(*steps)
    claimed = [r["body"]["job"] for r in out["results"][-3:]]
    assert [j["account"] if j else None for j in claimed] == [A["id"], A["id"], B["id"]]


def test_a_claim_reads_only_the_job_it_claims_whole():
    keys = [new_key() for _ in range(5)]
    steps = [command(k) for k in keys] + [enqueue(k, now=T0 + i) for i, k in enumerate(keys)]
    steps += [command(b_key := new_key(), account=B), enqueue(b_key, account=B, now=T0 + 10)]
    steps += [claim(new_token(), now=T0 + 20) for _ in range(4)]
    out = run(*steps)
    claims = out["results"][-4:]
    assert [c["body"]["job"] is not None for c in claims] == [True, True, True, False]
    assert [c["job_reads"] for c in claims] == [1, 1, 1, 0]


def test_the_harness_queues_past_what_a_claim_considers():
    probes = (HERE.parents[1] / "harness" / "probes" / "execution_check.py").read_text()
    assert int(re.search(r"^CLAIM_SCAN = (\d+)$", probes, re.M).group(1)) == CLAIM_SCAN


def test_a_reused_token_hash_is_refused():
    k1, k2 = new_key(), new_key()
    token = new_token()
    out = run(command(k1), command(k2), enqueue(k1), enqueue(k2), claim(token), claim(token))
    assert out["results"][-1]["status"] == 400 and len(out["store"]["attempts"]) == 1


# ---- heartbeat ------------------------------------------------------------------


def test_the_first_started_heartbeat_starts_the_attempt_with_its_budget():
    steps, job, attempt, token = started_job(budget=3)
    out = run(*steps, heartbeat(attempt["id"], token, now=T0 + 10))
    (stored,) = out["store"]["attempts"]
    assert (stored["state"], stored["started_at"], stored["budget_s"], stored["deadline_at"]) == ("started", T0, 3, T0 + 3)
    assert stored["heartbeat_at"] == T0 + 10 and stored["lease_expires_at"] == T0 + 40
    assert out["store"]["jobs"][0]["state"] == "started" and out["store"]["jobs"][0]["attempts_started"] == 1
    assert out["results"][-1]["body"] == {"v": "execution/v1", "lease_expires_at": T0 + 40, "cancel_requested": False}


def test_a_budget_over_what_the_kind_is_admitted_for_is_refused():
    key = new_key()
    token = new_token()
    out = run(command(key), enqueue(key), claim(token))
    attempt = out["results"][-1]["body"]["attempt"]
    out = run(command(key), enqueue(key), claim(token), heartbeat(attempt["id"], token, budget=4),
              heartbeat(attempt["id"], token, budget=3), heartbeat(attempt["id"], token, budget=3))
    assert out["results"][3]["status"] == 400
    assert out["results"][4]["status"] == 200
    assert out["results"][5] == {"status": 409, "body": {"v": "execution/v1", "error": "already_started"}}


def test_a_wrong_token_is_not_found_and_writes_nothing():
    steps, job, attempt, token = started_job()
    out = run(*steps, heartbeat(attempt["id"], new_token(), now=T0 + 1))
    assert out["results"][-1]["status"] == 404
    assert out["store"]["attempts"][0]["rejected_writes"] == 0


def test_an_expired_lease_is_superseded_and_the_write_counted_not_applied():
    key = new_key()
    token = new_token()
    out = run(command(key), enqueue(key), claim(token))
    attempt = out["results"][-1]["body"]["attempt"]
    out = run(command(key), enqueue(key), claim(token), heartbeat(attempt["id"], token, now=T0 + 30, budget=3))
    assert out["results"][-1] == {"status": 409, "body": {"v": "execution/v1", "error": "superseded"}}
    (stored,) = out["store"]["attempts"]
    assert stored["state"] == "leased" and stored["rejected_writes"] == 1 and stored["started_at"] == 0


# ---- complete -------------------------------------------------------------------


def test_complete_writes_the_envelope_and_both_terminal_states_together():
    steps, job, attempt, token = started_job()
    out = run(*steps, complete(attempt["id"], token, result(job["id"])))
    (envelope,) = out["store"]["envelopes"]
    assert (envelope["state"], envelope["outcome_class"], envelope["authoritative"]) == ("completed", "passed", True)
    assert envelope["job"] == job["id"] and envelope["attempt"] == attempt["id"] and envelope["user"] == A["id"]
    assert envelope["version"] == ENVELOPE and envelope["graded_row"] == ""
    # The account reads the envelope, so the operator view goes on the
    # attempt, which only the service reads.
    assert "operator_view" not in envelope
    (stored,) = out["store"]["attempts"]
    assert stored["state"] == "completed" and stored["operator_view"]["worker"] == "runner-a"
    stored_job = out["store"]["jobs"][0]
    assert (stored_job["state"], stored_job["outcome_class"], stored_job["cleanup"]) == ("completed", "passed", "confirmed")


def _leaves(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _leaves(item)
    elif isinstance(value, list):
        for item in value:
            yield from _leaves(item)
    else:
        yield value


@pytest.mark.parametrize("kind", ["grade", "take_home_submit"])
def test_a_run_with_hidden_material_shows_its_account_outcome_classes_and_totals_only(kind):
    steps, job, attempt, token = started_job(kind=kind, budget=45)
    body = result(job["id"], outcome="candidate-failure", score=0.5)
    body["user_view"]["parts"] = [{"id": "checkpoint-1", "outcome_class": "passed", "limit": None},
                                  {"id": "checkpoint-2", "outcome_class": "candidate-failure", "limit": None}]
    shown = json.loads(json.dumps(body))
    shown["user_view"]["output"] = {"stdout": "what the hidden tests printed"}
    refused = run(*steps, complete(attempt["id"], token, shown))
    assert refused["results"][-1] == {"status": 400, "body": {"v": "execution/v1", "error": "invalid_request"}}
    assert refused["store"]["envelopes"] == []
    out = run(*steps, complete(attempt["id"], token, body))
    assert out["results"][-1]["status"] == 200
    (envelope,) = out["store"]["envelopes"]
    allowed = {ENVELOPE, job["id"], "completed", "candidate-failure", "passed", "confirmed", "checkpoint-1",
               "checkpoint-2"}
    for leaf in _leaves(envelope["user_view"]):
        assert leaf is None or isinstance(leaf, (bool, int, float)) or leaf in allowed, leaf


@pytest.mark.parametrize(
    "part",
    [
        {"id": "case-1", "outcome_class": "passed", "limit": None, "expected": [1, 2]},
        {"id": "case-1", "outcome_class": "passed", "limit": None, "output": "x"},
        {"id": "case 1", "outcome_class": "passed", "limit": None},
        {"id": "case-1", "outcome_class": "passed", "limit": "memory"},
        {"id": "case-1", "outcome_class": "skipped", "limit": None},
    ],
    ids=["expected", "output", "id", "limit-without-class", "class"],
)
def test_a_part_carries_its_id_outcome_and_limit_and_nothing_else(part):
    steps, job, attempt, token = started_job()
    body = result(job["id"])
    body["user_view"]["parts"] = [part]
    out = run(*steps, complete(attempt["id"], token, body))
    assert out["results"][-1]["status"] == 400 and out["store"]["envelopes"] == []


def test_a_resource_limit_is_authoritative_names_its_limit_and_scores_null():
    steps, job, attempt, token = started_job()
    body = result(job["id"], state="timed-out", outcome="resource-limit", limit="wall_time")
    out = run(*steps, complete(attempt["id"], token, body))
    assert out["results"][-1]["status"] == 200
    assert out["store"]["envelopes"][0]["authoritative"] is True
    assert out["store"]["envelopes"][0]["user_view"]["score"] is None


@pytest.mark.parametrize(
    "change",
    [
        {"authoritative": True, "state": "failed", "outcome_class": "worker-lost"},
        {"state": "completed", "outcome_class": "worker-lost"},
        {"state": "timed-out", "outcome_class": "resource-limit"},  # no named limit
        {"score": 0.0, "state": "failed", "outcome_class": "infrastructure-degraded"},
        {"score": 2.0},
        {"version": "rounds.execution-envelope/v2"},
        {"extra": "x"},
        {"executor_kind": "docker"},
    ],
    ids=["authoritative-failure", "class-for-state", "limit-unnamed", "score-on-failure", "score-range", "version",
         "unknown-key", "executor-kind"],
)
def test_an_envelope_outside_v1_is_refused_before_anything_is_written(change):
    body = result("id0000000000001")
    for key, value in change.items():
        if key in ("state", "outcome_class", "authoritative"):
            body[key] = value
            body["user_view"][key] = value
        elif key == "executor_kind":
            body["operator_view"][key] = value
        else:
            body["user_view"][key] = value
    (checked,) = run({"call": "checkResult", "input": body})["results"]
    assert checked is None


def test_only_a_started_attempt_can_report_what_the_candidate_did():
    key = new_key()
    token = new_token()
    out = run(command(key), enqueue(key), claim(token))
    attempt = out["results"][-1]["body"]["attempt"]
    job = out["results"][-1]["body"]["job"]
    out = run(command(key), enqueue(key), claim(token), complete(attempt["id"], token, result(job["id"])),
              complete(attempt["id"], token, result(job["id"], state="denied", outcome="definition-invalid")))
    assert out["results"][3] == {"status": 409, "body": {"v": "execution/v1", "error": "not_started"}}
    assert out["results"][4]["status"] == 200 and out["store"]["jobs"][0]["state"] == "denied"


@pytest.mark.parametrize(
    "state, outcome, limit, status",
    [("timed-out", "resource-limit", "wall_time", 409), ("timed-out", "infrastructure-degraded", None, 200),
     ("failed", "infrastructure-degraded", None, 200)],
)
def test_a_run_that_never_got_a_slot_ends_without_an_authoritative_result(state, outcome, limit, status):
    key = new_key()
    token = new_token()
    out = run(command(key), enqueue(key), claim(token))
    attempt = out["results"][-1]["body"]["attempt"]
    job = out["results"][-1]["body"]["job"]
    body = result(job["id"], state=state, outcome=outcome, limit=limit, cleanup="confirmed")
    out = run(command(key), enqueue(key), claim(token), complete(attempt["id"], token, body))
    assert out["results"][-1]["status"] == status
    assert out["store"]["jobs"][0]["state"] == (state if status == 200 else "leased")


def test_an_envelope_for_another_job_is_refused():
    steps, job, attempt, token = started_job()
    out = run(*steps, complete(attempt["id"], token, result("zzzzzzzzzzzzzzz")))
    assert out["results"][-1]["status"] == 400 and out["store"]["envelopes"] == []


# ---- reap -----------------------------------------------------------------------


def test_a_lease_lost_before_the_run_started_goes_back_in_the_queue():
    key = new_key()
    out = run(command(key), enqueue(key), claim(new_token()), reap(T0 + 30))
    assert out["results"][-1] == {"requeued": 1, "worker_lost": 0, "over_budget": 0}
    (job,) = out["store"]["jobs"]
    assert (job["state"], job["queued_at"], job["attempts"], job["attempts_started"]) == ("queued", T0 + 30, 1, 0)
    (attempt,) = out["store"]["attempts"]
    assert (attempt["state"], attempt["outcome_class"], attempt["cleanup"]) == ("failed", "worker-lost", "unconfirmed")
    (envelope,) = out["store"]["envelopes"]
    assert envelope["authoritative"] is False and envelope["user_view"]["score"] is None


def test_a_lease_lost_after_the_run_started_ends_the_job_worker_lost():
    steps, job, attempt, token = started_job()
    out = run(*steps, reap(T0 + 30))
    assert out["results"][-1] == {"requeued": 0, "worker_lost": 1, "over_budget": 0}
    stored = out["store"]["jobs"][0]
    assert (stored["state"], stored["outcome_class"]) == ("failed", "worker-lost")


def test_a_run_thirty_seconds_past_its_budget_ends_degraded_while_it_heartbeats():
    steps, job, attempt, token = started_job(kind="take_home_run", budget=60)
    beats = [heartbeat(attempt["id"], token, now=T0 + t) for t in (10, 20, 30, 40, 50, 60, 70, 80)]
    out = run(*steps, *beats, reap(T0 + 90), reap(T0 + 91))
    assert out["results"][-2] == {"requeued": 0, "worker_lost": 0, "over_budget": 0}
    assert out["results"][-1] == {"requeued": 0, "worker_lost": 0, "over_budget": 1}
    stored = out["store"]["jobs"][0]
    assert (stored["state"], stored["outcome_class"]) == ("failed", "infrastructure-degraded")


def test_a_lost_lease_with_a_cancel_asked_for_ends_canceled():
    key = new_key()
    first = run(command(key), enqueue(key), claim(new_token()))
    job_id = first["results"][-1]["body"]["job"]["id"]
    out = run(command(key), enqueue(key), claim(new_token()),
              {"call": "cancel", "account": A, "input": {"job_id": job_id}, "now": T0 + 1}, reap(T0 + 30))
    assert out["store"]["jobs"][0]["state"] == "canceled"


def test_a_job_whose_three_leases_ran_out_ends_degraded():
    key = new_key()
    steps = [command(key), enqueue(key)]
    for i in range(3):
        steps += [claim(new_token(), now=T0 + 40 * i), reap(T0 + 40 * i + 30)]
    out = run(*steps)
    job = out["store"]["jobs"][0]
    assert (job["state"], job["outcome_class"], job["attempts"]) == ("failed", "infrastructure-degraded", 3)
    assert len(out["store"]["attempts"]) == 3


def test_a_retry_after_worker_loss_runs_attempt_two_and_attempt_ones_late_result_is_rejected():
    key = new_key()
    steps, job, attempt, token = started_job(key=key)
    second = new_token()
    out = run(*steps, reap(T0 + 30), enqueue(key, now=T0 + 31), claim(second, now=T0 + 32),
              complete(attempt["id"], token, result(job["id"]), now=T0 + 33))
    assert out["results"][-3]["body"]["requeued"] is True
    assert out["results"][-2]["body"]["attempt"]["attempt_number"] == 2
    assert out["results"][-1] == {"status": 409, "body": {"v": "execution/v1", "error": "superseded"}}
    first = next(a for a in out["store"]["attempts"] if a["attempt_number"] == 1)
    assert first["rejected_writes"] == 1
    # The only envelope is the reaper's, for attempt one.
    assert [(e["attempt"], e["authoritative"]) for e in out["store"]["envelopes"]] == [(attempt["id"], False)]


@pytest.mark.parametrize(
    "ended, requeues",
    [(("failed", "worker-lost"), True), (("failed", "infrastructure-degraded"), True),
     (("timed-out", "infrastructure-degraded"), True), (("denied", "definition-invalid"), False),
     (("completed", "candidate-failure"), False), (("timed-out", "resource-limit"), False)],
)
def test_only_an_infrastructure_loss_is_retried_with_the_same_key(ended, requeues):
    key = new_key()
    steps, job, attempt, token = started_job(key=key)
    state, outcome = ended
    limit = "wall_time" if outcome == "resource-limit" else None
    out = run(*steps, complete(attempt["id"], token, result(job["id"], state=state, outcome=outcome, limit=limit)),
              enqueue(key, now=T0 + 5))
    assert out["results"][-1]["body"]["requeued"] is requeues
    assert out["store"]["jobs"][0]["state"] == ("queued" if requeues else state)


def test_three_started_attempts_leave_no_retry():
    key = new_key()
    steps = [command(key), enqueue(key)]
    for i in range(3):
        token = new_token()
        steps += [claim(token, now=T0 + 100 * i)]
        out = run(*steps)
        attempt = out["results"][-1]["body"]["attempt"]
        steps += [heartbeat(attempt["id"], token, now=T0 + 100 * i, budget=3), reap(T0 + 100 * i + 30),
                  enqueue(key, now=T0 + 100 * i + 31)]
    out = run(*steps)
    assert out["results"][-1]["body"]["requeued"] is False
    job = out["store"]["jobs"][0]
    assert (job["state"], job["attempts_started"]) == ("failed", 3)


# ---- the worker record ------------------------------------------------------------

SECRET = "harness-execution-key-not-a-secret-0123"


@pytest.mark.parametrize(
    "existing, secret, did, password",
    [
        (None, SECRET, "created", SECRET),
        ({"username": "execution-worker", "password": SECRET}, SECRET, "unchanged", SECRET),
        ({"username": "execution-worker", "password": "o" * 40}, SECRET, "updated", SECRET),
        (None, "", "skipped", None),
        (None, "short", "skipped", None),
        ({"username": "execution-worker", "password": SECRET}, "", "disabled", "r" * 64),
        ({"username": "execution-worker", "password": SECRET}, " " + SECRET, "disabled", "r" * 64),
        (None, "x" * 72, "created", "x" * 72),
        (None, "x" * 73, "skipped", None),
        (None, "harness execution key with spaces 0123456", "skipped", None),
    ],
    ids=["created", "unchanged", "updated", "unset", "short", "unset-later", "whitespace", "longest", "too-long",
         "inner-space"],
)
def test_the_worker_record_follows_the_secret(existing, secret, did, password):
    (out,) = run({"call": "ensureWorker", "existing": existing, "secret": secret})["results"]
    assert out["did"] == did
    if password is None:
        assert out["records"] == []
    else:
        assert out["records"] == [{"username": "execution-worker", "password": password}]


# ---- attempt rows' envelope --------------------------------------------------------


@pytest.mark.parametrize(
    "call, fields, original, superuser, allowed",
    [
        ("guardEnvelopeCreate", {"envelope": ""}, None, False, True),
        ("guardEnvelopeCreate", {"envelope": "e" * 15}, None, False, False),
        ("guardEnvelopeCreate", {"envelope": "e" * 15}, None, True, True),
        ("guardEnvelopeUpdate", {"envelope": "e" * 15}, {"envelope": "e" * 15}, False, True),
        ("guardEnvelopeUpdate", {"envelope": "f" * 15}, {"envelope": "e" * 15}, False, False),
        ("guardEnvelopeUpdate", {"envelope": ""}, {"envelope": "e" * 15}, False, False),
        ("guardEnvelopeUpdate", {"envelope": "e" * 15}, {"envelope": ""}, False, False),
    ],
    ids=["create-none", "create-set", "superuser", "update-unchanged", "update-swapped", "update-cleared",
         "update-set"],
)
def test_no_client_links_an_attempt_row_to_an_envelope(call, fields, original, superuser, allowed):
    (out,) = run({"call": call, "fields": fields, "original": original, "superuser": superuser})["results"]
    assert out["allowed"] is allowed
    if not allowed:
        assert out["bad_request"] is True


# ---- in step with admission and the route table -------------------------------------


def test_each_kind_is_admitted_under_its_own_operation_and_budget():
    js = (HOOKS / "execution.js").read_text()
    kinds = dict(re.findall(r"^  (\w+): \{ purpose: \"(?:scratch|grading)\", operation: \"(\w+)\" \},$", js, re.M))
    assert kinds == {k: k for k in ("run", "evaluate", "run_project", "take_home_run", "grade", "take_home_submit")}


def test_the_routes_need_the_right_principal():
    pb = (HOOKS / "execution.pb.js").read_text()
    routes = re.findall(r'"POST",\s*"/api/rounds/execution/(\w+)",\s*\(c\) => [^\n]+\.(handle\w+)\(c, "(\w+)"\),\s*'
                        r'\$apis\.requireRecordAuth\("(\w+)"\)', pb)
    assert sorted(routes) == sorted([
        ("enqueue", "handleCaller", "enqueue", "users"),
        ("cancel", "handleCaller", "cancel", "users"),
        ("claim", "handleService", "claim", "execution_service"),
        ("heartbeat", "handleService", "heartbeat", "execution_service"),
        ("complete", "handleService", "complete", "execution_service"),
        ("reap", "handleService", "reap", "execution_service"),
    ])
    assert pb.count('"ai_coding_attempts", "take_home_attempts");') == 2
    # The worker record follows the secret at every start and before every
    # execution-worker login.
    assert "onAfterBootstrap(" in pb and ".bootstrapWorker()" in pb
    assert re.search(r'onRecordBeforeAuthWithPasswordRequest\(\(e\) => \{\s*require\([^)]+\)\.syncWorkerForLogin\(e\);'
                     r'\s*\}, "execution_service"\);', pb)


RUNNER_KEY = "test-runner-key-placeholder-0123456789"
USERS = {"collection": "users"}
WORKER = {"collection": "execution_service", "username": "execution-worker"}


@pytest.mark.parametrize(
    "case, out",
    [
        ({"env": {"ROUNDS_GATE_EXECUTION_STORE": ""}}, {"reached": False, "status": 503, "error": "store_off"}),
        ({"principal": None}, {"reached": False, "thrown": "UnauthorizedError"}),
        ({"headers": {}}, {"reached": False, "status": 403, "error": "forbidden"}),
        ({"headers": {"x_rounds_admission_key": "not-the-runner-key-0123456789abcdef"}},
         {"reached": False, "status": 403, "error": "forbidden"}),
        ({"env": {"ROUNDS_ADMISSION_SECRET": ""}}, {"reached": False, "status": 503, "error": "unconfigured"}),
        ({}, {"reached": True}),
    ],
    ids=["store-off", "no-bearer", "no-runner-key", "wrong-runner-key", "pocketbase-has-no-key", "admitted"],
)
def test_enqueue_and_cancel_need_the_bearer_and_the_runner_key(case, out):
    step = {"call": "handleCaller", "action": "cancel", "principal": USERS, "data": {"job_id": "job000000000001"},
            "env": {"ROUNDS_ADMISSION_SECRET": RUNNER_KEY}, "headers": {"x_rounds_admission_key": RUNNER_KEY}}
    env = dict(step["env"], **case.get("env", {}))
    step.update(case, env=env)
    (got,) = run(step)["results"]
    assert got == out


@pytest.mark.parametrize(
    "case, out",
    [
        ({"env": {"ROUNDS_GATE_EXECUTION_STORE": "off"}}, {"reached": False, "status": 503, "error": "store_off"}),
        ({"principal": None}, {"reached": False, "thrown": "ForbiddenError"}),
        ({"principal": USERS}, {"reached": False, "thrown": "ForbiddenError"}),
        ({"principal": {"collection": "execution_service", "username": "someone-else"}},
         {"reached": False, "thrown": "ForbiddenError"}),
        ({}, {"reached": True}),
    ],
    ids=["store-off", "no-record", "users-record", "another-service-record", "execution-worker"],
)
def test_the_service_routes_take_only_the_worker_record(case, out):
    step = {"call": "handleService", "action": "reap", "principal": WORKER, "data": {}}
    step.update(case)
    (got,) = run(step)["results"]
    assert got == out


@pytest.mark.parametrize(
    "existing, identity, secret, did, password",
    [
        # The first login after the migration makes the record.
        (None, "execution-worker", SECRET, "created", SECRET),
        ({"username": "execution-worker", "password": "o" * 40}, "execution-worker", SECRET, "updated", SECRET),
        ({"username": "execution-worker", "password": SECRET}, "execution-worker", SECRET, "unchanged", SECRET),
        ({"username": "execution-worker", "password": SECRET}, "execution-worker", "", "disabled", "r" * 64),
        (None, "someone-else", SECRET, None, None),
    ],
    ids=["first-login", "rotated", "same", "unset", "other-identity"],
)
def test_a_login_syncs_the_worker_record_first_and_checks_the_record_as_it_is_now(existing, identity, secret, did,
                                                                                 password):
    (out,) = run({"call": "syncWorkerForLogin", "existing": existing, "identity": identity, "secret": secret})["results"]
    assert out["did"] == did
    if password is None:
        assert out["record"] is None and out["records"] == ([existing] if existing else [])
    else:
        assert out["record"] == {"username": "execution-worker", "password": password}


def test_bootstrap_waits_for_the_collection_the_migration_makes():
    (out,) = run({"call": "bootstrapWorker", "collection": False, "secret": SECRET})["results"]
    assert out == {"did": "absent", "records": []}
    (out,) = run({"call": "bootstrapWorker", "collection": True, "secret": SECRET})["results"]
    assert out == {"did": "created", "records": [{"username": "execution-worker", "password": SECRET}]}
