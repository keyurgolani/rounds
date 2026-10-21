"""Harness checks for the execution job store (ROUNDS-00A-L03 PR 1), on
the real PocketBase built from this commit with
``ROUNDS_GATE_EXECUTION_STORE=on``. Every account is generated for the
run, and the worker secrets are the harness's test placeholders.

Phases, in the order harness/run.sh runs them:

- ``execution-store``, PocketBase only: the worker record exists and
  only its secret logs in; a ``users`` token and an anonymous caller are
  refused on the service routes; no client writes the job collections,
  reads jobs or attempts, or links an attempt row to an envelope; an
  account reads its own envelopes and nobody else's, without the
  operator view, and a run with hidden material shows the account
  outcome classes and totals only (D9), and its filters on its envelopes
  name no field of a job or an attempt; enqueue needs the account's admitted command and
  the runner key, answers a duplicate with its job and a different
  request as a mismatch; another account's cancel is the unknown-id 404;
  two sessions racing for one job make one attempt; a superseded token's
  write is counted and never applied; an envelope outside v1 is refused
  whole; and after a real 31 s, reap re-queues a lease lost before it
  started and ends one lost after it started worker-lost, and a same-key
  retry runs attempt two. One account's backlog of queued jobs holds
  no other account's job back.
- ``execution-runners``, both runner replicas up with the store on and
  the secret: each is ready, and each claims jobs and, with no handler
  for any kind yet, ends them ``denied``, ``definition-invalid``, once.
- ``execution-unready``, after PocketBase restarts with another secret:
  neither replica stays ready.
- ``execution-ready-again``, after the replicas restart with that secret:
  both are ready again, and only the new secret logs in.
- ``execution-disabled``, after PocketBase restarts with no secret: the
  last secret no longer logs in.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import string
import sys
import threading
import time
from typing import Any

import factory
from admission_check import Checks, admin_token, call, uuid7
from pbclient import PBClient

POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
RUNNERS = [u.strip().rstrip("/") for u in os.environ.get("RUNNER_URLS", "").split(",") if u.strip()]
RUNNER_KEY = os.environ.get("ROUNDS_ADMISSION_SECRET", "")
SECRET = os.environ.get("ROUNDS_EXECUTION_SECRET", "")
ROTATED = os.environ.get("ROUNDS_EXECUTION_SECRET_ROTATED", "")
STORE = "/api/rounds/execution"
LOGIN = "/api/collections/execution_service/auth-with-password"
COLLECTIONS = ("execution_jobs", "execution_attempts", "execution_envelopes")
# What an account reads of a run with hidden material: these and numbers.
OUTCOME_WORDS = {"completed", "timed-out", "denied", "canceled", "failed", "passed", "candidate-failure",
                 "resource-limit", "definition-invalid", "policy-violation", "worker-lost", "infrastructure-degraded",
                 "pending", "confirmed", "unconfirmed", "wall_time", "cpu_time", "memory", "processes", "files",
                 "output"}
ENVELOPE = "rounds.execution-envelope/v1"
DEFINITION = {"track": "coding", "slug": "two-sum", "variant": "python", "version": 1}
LEASE_S = 30
# The most accounts one claim considers (pb_hooks/execution.js).
CLAIM_SCAN = 50
# The least wall seconds admission admits each operation for.
WALL = {"run": 3, "evaluate": 3, "run_project": 10, "grade": 45, "take_home_run": 60, "take_home_submit": 120}


def token43() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(43))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def login(secret: str) -> tuple[int, str | None]:
    status, body, _ = call(POCKETBASE_URL, "POST", LOGIN, body={"identity": "execution-worker", "password": secret})
    return status, (body or {}).get("token") if status == 200 else None


def service(token: str | None, action: str, body: dict) -> tuple[int, Any]:
    status, parsed, _ = call(POCKETBASE_URL, "POST", f"{STORE}/{action}", token, body)
    return status, parsed


def caller(token: str, action: str, body: dict, key: str | None = None) -> tuple[int, Any]:
    headers = {"X-Rounds-Admission-Key": RUNNER_KEY if key is None else key}
    status, parsed, _ = call(POCKETBASE_URL, "POST", f"{STORE}/{action}", token, body, headers)
    return status, parsed


def admit(token: str, key: str, fingerprint: str, operation: str = "run") -> int:
    """The account's admitted command, as a runner records it."""
    body = {"operation": operation, "wall_seconds": WALL[operation], "idempotency": "enforce", "quota": "off",
            "lease_hash": sha(token43()), "command_id": key, "fingerprint": fingerprint}
    status, _parsed, _ = call(POCKETBASE_URL, "POST", "/api/rounds/admission/admit", token, body,
                              {"X-Rounds-Admission-Key": RUNNER_KEY})
    return status


def enqueue_body(key: str, fingerprint: str, kind: str = "run") -> dict:
    return {"command_id": key, "kind": kind, "definition": DEFINITION, "fingerprint": fingerprint,
            "source_checksum": "c" * 64, "input_digest": "d" * 64, "input": {"code": "print(1)"}}


def new_job(token: str, kind: str = "run") -> tuple[str, str, str | None]:
    """An admitted command and its job: the key, the fingerprint, and the
    job id (None when enqueue refused it)."""
    key, fingerprint = uuid7(), secrets.token_hex(32)
    admit(token, key, fingerprint, kind)
    status, body = caller(token, "enqueue", enqueue_body(key, fingerprint, kind))
    return key, fingerprint, ((body or {}).get("job") or {}).get("id") if status == 200 else None


def seed_queued(pb: PBClient, admin: str, acct: factory.Account, queued_at: int) -> str | None:
    """A queued job written straight to the store as the admin, without an
    admission, so a check can queue many at once."""
    body = {"account": acct.user_id, "command_id": uuid7(), "kind": "run", "purpose": "scratch",
            "definition": DEFINITION, "fingerprint": secrets.token_hex(32), "source_checksum": "c" * 64,
            "input_digest": "d" * 64, "input": {"code": "print(1)"}, "state": "queued", "queued_at": queued_at}
    resp = pb.create("execution_jobs", admin, body)
    return (resp.body or {}).get("id") if resp.status == 200 else None


def envelope(job_id: str, state: str = "completed", outcome: str = "passed", score: float | None = 1.0) -> dict:
    authoritative = outcome in ("passed", "candidate-failure")
    user = {"version": ENVELOPE, "job_id": job_id, "state": state, "outcome_class": outcome,
            "authoritative": authoritative, "limit": None, "parts": [{"id": "case-1", "outcome_class": outcome,
                                                                       "limit": None}],
            "score": score, "definition": None, "queued_at": 1, "started_at": 2, "finished_at": 3,
            "cleanup": "confirmed", "rubric": None, "output": None}
    operator = {"version": ENVELOPE, "executor_kind": "legacy-in-process", "worker": "harness",
                "attempt_number": 1, "source_checksum": "c" * 64, "input_digest": "d" * 64, "output_sha256": None,
                "output_bytes": 0, "exit_status": 0, "cpu_time_ms": None, "peak_rss_bytes": None,
                "build_revision": None, "image_digest": None, "graded_row": None}
    return {"state": state, "outcome_class": outcome, "authoritative": authoritative, "cleanup": "confirmed",
            "user_view": user, "operator_view": operator}


def leaves(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from leaves(item)
    elif isinstance(value, list):
        for item in value:
            yield from leaves(item)
    else:
        yield value


def row(pb: PBClient, admin: str, collection: str, record_id: str) -> dict:
    resp = pb.view(collection, record_id, admin)
    return resp.body if resp.status == 200 and isinstance(resp.body, dict) else {}


def rows(pb: PBClient, admin: str, collection: str, flt: str) -> list[dict]:
    resp = pb.listing(collection, admin, {"filter": flt})
    return (resp.body or {}).get("items", []) if resp.status == 200 else []


# ---- execution-store --------------------------------------------------------


def run_store(c: Checks) -> None:
    pb = PBClient(POCKETBASE_URL)
    pb.wait_healthy()
    admin = admin_token(pb)
    a, b = factory.make_account("exe-a"), factory.make_account("exe-b")
    factory.register(pb, a)
    factory.register(pb, b)

    status, svc = login(SECRET)
    c.check("execution.worker.logs-in-with-its-secret", status == 200 and bool(svc), f"status={status}")
    c.check("execution.worker.another-secret-refused", login("x" * 40)[0] == 400, "a wrong secret logged in")
    if not svc:
        return
    other_status, svc2 = login(SECRET)

    # Only the service record reaches the service routes.
    for action, body in (("claim", {"worker": "harness", "token_hash": "a" * 64}),
                         ("heartbeat", {"attempt_id": "a" * 15, "token": token43()}),
                         ("complete", {"attempt_id": "a" * 15, "token": token43(), "result": {}}),
                         ("reap", {})):
        user_status, _ = service(a.token, action, body)
        anon_status, _ = service(None, action, body)
        c.check(f"execution.service.{action}-refuses-a-user-and-anonymous", (user_status, anon_status) == (403, 401),
                f"user={user_status} anonymous={anon_status}")
    status, _ = caller(svc, "enqueue", enqueue_body(uuid7(), "a" * 64))
    c.check("execution.caller.enqueue-refuses-the-service-record", status == 403, f"status={status}")

    # No client writes the job collections, and none reads a job or an
    # attempt; an account reads its own envelopes only (below).
    for name in COLLECTIONS:
        listed = pb.listing(name, a.token)
        created = pb.create(name, a.token, {"account": a.user_id, "user": a.user_id})
        c.check(f"execution.collections.{name}-closed-to-clients",
                listed.status in (200, 403) and not (listed.body or {}).get("items") and created.status == 403,
                f"list={listed.status} create={created.status}")
    c.check("execution.collections.service-records-closed", pb.listing("execution_service", a.token).status == 403,
            "a user listed the service records")

    # Enqueue needs the account's admitted command and the runner key.
    key, fingerprint = uuid7(), secrets.token_hex(32)
    status, body = caller(a.token, "enqueue", enqueue_body(key, fingerprint))
    c.check("execution.enqueue.needs-an-admitted-command", status == 404 and (body or {}).get("error") == "not_admitted",
            f"status={status}")
    c.check("execution.enqueue.admitted", admit(a.token, key, fingerprint) == 200, "admit failed")
    status, _ = caller(a.token, "enqueue", enqueue_body(key, fingerprint), key="y" * 40)
    c.check("execution.enqueue.needs-the-runner-key", status == 403, f"status={status}")
    status, body = caller(a.token, "enqueue", enqueue_body(key, fingerprint))
    job = (body or {}).get("job") or {}
    c.check("execution.enqueue.queues-one-job", status == 200 and job.get("state") == "queued", f"status={status}")
    status, again = caller(a.token, "enqueue", enqueue_body(key, fingerprint))
    c.check("execution.enqueue.duplicate-answers-the-same-job",
            status == 200 and (again or {}).get("duplicate") is True and (again or {}).get("job", {}).get("id") == job.get("id"),
            f"status={status}")
    status, body = caller(a.token, "enqueue", enqueue_body(key, secrets.token_hex(32)))
    c.check("execution.enqueue.other-request-is-a-mismatch", status == 409 and (body or {}).get("error") == "mismatch",
            f"status={status}")
    command = rows(pb, admin, "admission_commands", f"command_id = '{key}'")
    c.check("execution.enqueue.records-the-job-on-the-command",
            len(command) == 1 and command[0].get("job") == job.get("id"), f"rows={len(command)}")
    status, body = caller(b.token, "cancel", {"job_id": job.get("id", "")})
    unknown = caller(b.token, "cancel", {"job_id": "z" * 15})
    c.check("execution.cancel.another-account-is-the-unknown-404",
            (status, body) == unknown and status == 404, f"status={status}/{unknown[0]}")

    # Two sessions racing for one job make one attempt.
    results: list[tuple[int, Any]] = []

    def claim(token: str) -> None:
        results.append(service(token, "claim", {"worker": "harness", "token_hash": sha(token43())}))

    racers = [threading.Thread(target=claim, args=(t,)) for t in (svc, svc2 or svc)]
    for t in racers:
        t.start()
    for t in racers:
        t.join(30)
    won = [r for r in results if r[0] == 200 and (r[1] or {}).get("job")]
    c.check("execution.claim.two-racers-one-attempt",
            len(results) == 2 and len(won) == 1 and len(rows(pb, admin, "execution_attempts", f"job = '{job.get('id')}'")) == 1,
            f"results={[r[0] for r in results]} won={len(won)}")
    status, _ = caller(a.token, "cancel", {"job_id": job.get("id", "")})
    c.check("execution.cancel.asks-a-leased-job-to-stop",
            status == 200 and row(pb, admin, "execution_jobs", job.get("id", "")).get("cancel_requested") is True,
            f"status={status}")

    # Fencing: a wrong token is unknown, a started run completes once, and
    # a write after that is counted and never applied.
    token = token43()
    key2, fp2, job2 = new_job(a.token)
    status, claimed = service(svc, "claim", {"worker": "harness", "token_hash": sha(token)})
    attempt_row = (claimed or {}).get("attempt") or {}
    attempt = attempt_row.get("id", "")
    lease = attempt_row.get("lease_expires_at", 0) - int(time.time())
    c.check("execution.claim.leases-the-job-for-30s",
            status == 200 and ((claimed or {}).get("job") or {}).get("id") == job2 and LEASE_S - 3 <= lease <= LEASE_S + 3,
            f"status={status} lease={lease}")
    wrong = service(svc, "heartbeat", {"attempt_id": attempt, "token": token43()})[0]
    over = service(svc, "heartbeat", {"attempt_id": attempt, "token": token, "started": True, "budget_s": 4})[0]
    started = service(svc, "heartbeat", {"attempt_id": attempt, "token": token, "started": True, "budget_s": 3})
    c.check("execution.heartbeat.starts-within-what-the-kind-is-admitted-for",
            wrong == 404 and over == 400 and started[0] == 200 and (started[1] or {}).get("cancel_requested") is False,
            f"wrong={wrong} over={over} started={started[0]}")
    bad = envelope(job2)
    bad["user_view"]["score"] = 2
    refused = service(svc, "complete", {"attempt_id": attempt, "token": token, "result": bad})[0]
    c.check("execution.complete.refuses-an-envelope-outside-v1",
            refused == 400 and not rows(pb, admin, "execution_envelopes", f"job = '{job2}'"), f"status={refused}")
    done = service(svc, "complete", {"attempt_id": attempt, "token": token, "result": envelope(job2)})
    late = service(svc, "complete", {"attempt_id": attempt, "token": token, "result": envelope(job2)})
    envs = rows(pb, admin, "execution_envelopes", f"job = '{job2}'")
    c.check("execution.complete.one-authoritative-envelope",
            done[0] == 200 and len(envs) == 1 and envs[0].get("authoritative") is True
            and row(pb, admin, "execution_jobs", job2).get("state") == "completed", f"status={done[0]}")
    c.check("execution.complete.late-write-counted-and-refused",
            late[0] == 409 and (late[1] or {}).get("error") == "superseded"
            and row(pb, admin, "execution_attempts", attempt).get("rejected_writes", 0) >= 1, f"status={late[0]}")

    # D9: the account reads its own envelope, without the operator view,
    # which stays on the attempt; nobody else reads it.
    env_id = envs[0]["id"] if envs else "x" * 15
    own_list = pb.listing("execution_envelopes", a.token)
    own_view = pb.view("execution_envelopes", env_id, a.token)
    seen = own_view.body if own_view.status == 200 and isinstance(own_view.body, dict) else {}
    c.check("execution.envelopes.the-account-reads-its-own",
            [i.get("id") for i in (own_list.body or {}).get("items", [])] == [env_id] and own_view.status == 200
            and "user_view" in seen and "operator_view" not in seen
            and (row(pb, admin, "execution_attempts", attempt).get("operator_view") or {}).get("worker") == "harness",
            f"list={own_list.status} view={own_view.status}")
    other_list = pb.listing("execution_envelopes", b.token)
    other_view = pb.view("execution_envelopes", env_id, b.token)
    anon_list = pb.listing("execution_envelopes", None)
    anon_view = pb.view("execution_envelopes", env_id, None)
    c.check("execution.envelopes.nobody-else-reads-them",
            not (other_list.body or {}).get("items") and other_view.status == 404
            and not (anon_list.body or {}).get("items") and anon_view.status == 404,
            f"other={other_list.status}/{other_view.status} anonymous={anon_list.status}/{anon_view.status}")
    # Nothing in the row an account reads links into the service-only
    # collections: its filters name no field of a job or an attempt.
    through = [pb.listing("execution_envelopes", a.token, {"filter": f"{link}.state != ''"}) for link in ("job", "attempt")]
    c.check("execution.envelopes.filters-reach-no-service-only-field",
            bool(envs) and all(r.status == 400 or (r.status == 200 and not (r.body or {}).get("items")) for r in through),
            f"statuses={[r.status for r in through]}")

    # A run with hidden material shows the account outcome classes and
    # the server's totals, never output.
    grade_token = token43()
    _gkey, _gfp, grade_job = new_job(a.token, "grade")
    grade_claim = service(svc, "claim", {"worker": "harness", "token_hash": sha(grade_token)})[1] or {}
    grade_attempt = (grade_claim.get("attempt") or {}).get("id", "")
    service(svc, "heartbeat", {"attempt_id": grade_attempt, "token": grade_token, "started": True, "budget_s": 45})
    graded = envelope(grade_job or "", outcome="candidate-failure", score=0.5)
    graded["user_view"]["parts"] = [{"id": "checkpoint-1", "outcome_class": "passed", "limit": None},
                                    {"id": "checkpoint-2", "outcome_class": "candidate-failure", "limit": None}]
    shown = json.loads(json.dumps(graded))
    shown["user_view"]["output"] = {"stdout": "printed by a hidden test"}
    refused_output = service(svc, "complete", {"attempt_id": grade_attempt, "token": grade_token, "result": shown})[0]
    graded_done = service(svc, "complete", {"attempt_id": grade_attempt, "token": grade_token, "result": graded})[0]
    grade_envs = rows(pb, admin, "execution_envelopes", f"job = '{grade_job}'")
    grade_seen = pb.view("execution_envelopes", grade_envs[0]["id"] if grade_envs else "x" * 15, a.token)
    words = OUTCOME_WORDS | {ENVELOPE, grade_job, "checkpoint-1", "checkpoint-2"}
    only_outcomes = grade_seen.status == 200 and all(
        leaf is None or isinstance(leaf, (bool, int, float)) or leaf in words
        for leaf in leaves((grade_seen.body or {}).get("user_view")))
    c.check("execution.envelopes.hidden-material-shows-outcomes-and-totals-only",
            refused_output == 400 and graded_done == 200 and len(grade_envs) == 1 and only_outcomes,
            f"with-output={refused_output} without={graded_done} view={grade_seen.status}")

    # An attempt row can't be linked to an envelope by its owner.
    rounds = pb.listing("ai_coding_rounds", a.token, {"perPage": 1})
    round_id = ((rounds.body or {}).get("items") or [{}])[0].get("id")
    if round_id:
        linked = pb.create("ai_coding_attempts", a.token, {"user": a.user_id, "round": round_id, "status": "in-progress",
                                                            "envelope": envs[0]["id"] if envs else "x" * 15})
        plain = pb.create("ai_coding_attempts", a.token, {"user": a.user_id, "round": round_id, "status": "in-progress"})
        relinked = pb.update("ai_coding_attempts", (plain.body or {}).get("id", ""),
                             {"envelope": envs[0]["id"] if envs else "x" * 15}, a.token)
        c.check("execution.attempt-rows.no-client-links-an-envelope",
                linked.status == 400 and plain.status == 200 and relinked.status == 400,
                f"create={linked.status} plain={plain.status} update={relinked.status}")
        # The server links a row to its account's envelope, and the account
        # reads it through the row (D9).
        attempt_row_id = (plain.body or {}).get("id", "")
        pb.update("ai_coding_attempts", attempt_row_id, {"envelope": env_id}, admin)
        expanded = pb.get(f"/api/collections/ai_coding_attempts/records/{attempt_row_id}?expand=envelope", a.token)
        got = ((expanded.body or {}).get("expand") or {}).get("envelope") or {}
        c.check("execution.attempt-rows.the-account-reads-its-envelope-through-the-row",
                expanded.status == 200 and got.get("id") == env_id and "operator_view" not in got,
                f"status={expanded.status}")
    else:
        c.check("execution.attempt-rows.no-client-links-an-envelope", False, "no AI-coding round to attach a row to")
        c.check("execution.attempt-rows.the-account-reads-its-envelope-through-the-row", False, "no AI-coding round")

    # Lost leases, after 31 s of PocketBase time.
    early_token, late_token = token43(), token43()
    _key3, _fp3, early_job = new_job(a.token)
    key4, fp4, late_job = new_job(b.token)
    early = service(svc, "claim", {"worker": "harness", "token_hash": sha(early_token)})[1] or {}
    late_claim = service(svc, "claim", {"worker": "harness", "token_hash": sha(late_token)})[1] or {}
    claimed_jobs = [(early.get("job") or {}).get("id"), (late_claim.get("job") or {}).get("id")]
    c.check("execution.claim.oldest-first", claimed_jobs == [early_job, late_job], f"claimed={claimed_jobs}")
    # The second one starts; the first never does.
    starter, starter_token, starter_job = (late_claim.get("attempt") or {}).get("id", ""), late_token, late_job
    idle_job = early_job
    service(svc, "heartbeat", {"attempt_id": starter, "token": starter_token, "started": True, "budget_s": 3})
    time.sleep(LEASE_S + 1)
    status, reaped = service(svc, "reap", {})
    c.check("execution.reap.requeues-before-start-and-ends-after",
            status == 200 and (reaped or {}).get("requeued") == 1 and (reaped or {}).get("worker_lost") == 1,
            f"status={status} reaped={reaped}")
    canceled = row(pb, admin, "execution_jobs", job.get("id", ""))
    c.check("execution.reap.a-lost-lease-asked-to-stop-ends-canceled",
            (canceled.get("state"), canceled.get("outcome_class")) == ("canceled", "canceled"), repr(canceled.get("state")))
    c.check("execution.reap.unstarted-job-back-in-the-queue", row(pb, admin, "execution_jobs", idle_job or "").get("state") == "queued",
            "not re-queued")
    lost = row(pb, admin, "execution_jobs", starter_job or "")
    c.check("execution.reap.started-job-ends-worker-lost",
            (lost.get("state"), lost.get("outcome_class")) == ("failed", "worker-lost"), repr(lost.get("state")))
    late = service(svc, "complete", {"attempt_id": starter, "token": starter_token, "result": envelope(starter_job or "")})
    c.check("execution.reap.late-result-rejected", late[0] == 409, f"status={late[0]}")
    # As a runner retries: admission again under the same key (its lease
    # may have ended, or the sweep marked it), then enqueue.
    admit(b.token, key4, fp4)
    status, retried = caller(b.token, "enqueue", enqueue_body(key4, fp4))
    second = [service(svc, "claim", {"worker": "harness", "token_hash": sha(token43())})[1] or {} for _ in range(2)]
    numbers = {j: sorted(r.get("attempt_number") for r in rows(pb, admin, "execution_attempts", f"job = '{j}'"))
               for j in (starter_job, idle_job)}
    c.check("execution.retry.same-key-runs-attempt-two",
            status == 200 and (retried or {}).get("requeued") is True and numbers == {starter_job: [1, 2], idle_job: [1, 2]}
            and {(x.get("job") or {}).get("id") for x in second} == {starter_job, idle_job},
            f"status={status} attempts={numbers}")

    # One account's backlog holds no other account's job back: more of one
    # account's jobs queued first than a claim considers, then another's.
    fair = [factory.make_account("exe-fair-c"), factory.make_account("exe-fair-d")]
    for acct in fair:
        factory.register(pb, acct)
    oldest = int(time.time()) - 1000
    backlog = [seed_queued(pb, admin, fair[0], oldest + i) for i in range(CLAIM_SCAN + 1)]
    lone = seed_queued(pb, admin, fair[1], oldest + CLAIM_SCAN + 10)
    picked = [((service(svc, "claim", {"worker": "harness", "token_hash": sha(token43())})[1] or {}).get("job") or {})
              .get("account") for _ in range(3)]
    c.check("execution.claim.one-backlog-holds-no-other-account-back",
            all(backlog) and bool(lone) and picked == [fair[0].user_id, fair[0].user_id, fair[1].user_id],
            f"seeded={sum(map(bool, backlog))}+{int(bool(lone))} picked={[p == fair[1].user_id for p in picked]}")
    for job_id in filter(None, [*backlog, lone]):
        pb.delete("execution_jobs", job_id, admin)

# ---- with the runners --------------------------------------------------------------


def _ready_all(want: int, timeout_s: float) -> dict[str, int]:
    deadline = time.monotonic() + timeout_s
    seen: dict[str, int] = {}
    while time.monotonic() < deadline:
        for runner in RUNNERS:
            try:
                seen[runner] = call(runner, "GET", "/ready", timeout=3)[0]
            except OSError:
                seen[runner] = 0
        if seen and all(s == want for s in seen.values()):
            break
        time.sleep(1)
    return seen


def run_runners(c: Checks) -> None:
    pb = PBClient(POCKETBASE_URL)
    pb.wait_healthy()
    admin = admin_token(pb)
    seen = _ready_all(200, 90)
    c.check("execution.runners.ready-with-the-store-on", len(RUNNERS) == 2 and all(s == 200 for s in seen.values()),
            repr(seen))
    a, b = factory.make_account("exe-r-a"), factory.make_account("exe-r-b")
    factory.register(pb, a)
    factory.register(pb, b)
    jobs = [new_job(acct.token, kind)[2] for acct, kind in ((a, "run"), (a, "grade"), (b, "evaluate"), (b, "run"),
                                                            (a, "take_home_submit"))]
    deadline = time.monotonic() + 60
    ended: list[dict] = []
    while time.monotonic() < deadline:
        ended = [row(pb, admin, "execution_jobs", j) for j in jobs if j]
        if len(ended) == len(jobs) and all(e.get("finished_at") for e in ended):
            break
        time.sleep(1)
    c.check("execution.runners.claim-and-end-every-job",
            len(ended) == 5 and all((e.get("state"), e.get("outcome_class")) == ("denied", "definition-invalid") for e in ended),
            repr([(e.get("state"), e.get("outcome_class")) for e in ended]))
    workers = set()
    once = True
    for j in jobs:
        attempts = rows(pb, admin, "execution_attempts", f"job = '{j}'")
        envs = rows(pb, admin, "execution_envelopes", f"job = '{j}'")
        once = once and len(attempts) == 1 and len(envs) == 1 and envs[0].get("authoritative") is False
        workers.update(a_.get("worker") for a_ in attempts)
    c.check("execution.runners.one-attempt-one-envelope-each", once, "a job ran twice or kept no envelope")
    c.check("execution.runners.named-workers", bool(workers) and all(isinstance(w, str) and w for w in workers),
            repr(sorted(filter(None, workers))))


def run_unready(c: Checks) -> None:
    seen = _ready_all(503, 120)
    c.check("execution.runners.unready-when-the-store-takes-another-secret",
            len(RUNNERS) == 2 and all(s == 503 for s in seen.values()), repr(seen))
    for runner in RUNNERS:
        c.check(f"execution.runners.alive-while-unready.{runner.split('//')[-1].split(':')[0]}",
                call(runner, "GET", "/health", timeout=5)[0] == 200, "health failed")


def run_ready_again(c: Checks) -> None:
    seen = _ready_all(200, 90)
    c.check("execution.runners.ready-after-a-restart-with-the-secret",
            len(RUNNERS) == 2 and all(s == 200 for s in seen.values()), repr(seen))
    c.check("execution.worker.rotated-secret-replaces-the-old", login(ROTATED)[0] == 200 and login(SECRET)[0] == 400,
            "the old secret still logs in, or the new one doesn't")


def run_disabled(c: Checks) -> None:
    PBClient(POCKETBASE_URL).wait_healthy()
    c.check("execution.worker.no-secret-no-login", login(ROTATED)[0] == 400 and login(SECRET)[0] == 400,
            "a secret still logs in with none set")


PHASES = {
    "execution-store": run_store,
    "execution-runners": run_runners,
    "execution-unready": run_unready,
    "execution-ready-again": run_ready_again,
    "execution-disabled": run_disabled,
}


def main(phase: str) -> int:
    c = Checks()
    if len(SECRET) < 32 or len(ROTATED) < 32:
        c.check("execution.secrets-configured", False, "the harness passes two worker secrets")
        return 1
    try:
        PHASES[phase](c)
    except Exception as err:  # noqa: BLE001 - a crash is one failed check, with its type only
        c.check(f"{phase}.ran", False, type(err).__name__)
    print(f"{phase}: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
