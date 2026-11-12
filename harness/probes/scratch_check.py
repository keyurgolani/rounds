"""Harness checks for scratch jobs (ROUNDS-00A-L03 PR 2): run, evaluate,
run-project, and take-home run as durable jobs, with both runner replicas
and nginx built from this commit on the real PocketBase, at
``ROUNDS_GATE_EXECUTION_STORE=on``, ``ROUNDS_GATE_EXECUTION_SCRATCH=on``,
and ``ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce``. Every account is
generated for the run.

Phases, in the order harness/run.sh runs them:

- ``execution-scratch``, through nginx:
  - each replica's saved gates line holds the three values;
  - a run answers 202 with its job, and the job ends with its envelope
    and the run's output;
  - a duplicate answers the same job and charges nothing more, and the
    same key for other work is a mismatch;
  - another account reading or canceling a job gets the same 404 as an
    unknown id, and the job is untouched (two receipts, the case table's
    evidence for ``runner:execution-jobs``);
  - a cancel stops a running job;
  - a run that reaches its time limit ends with it named and its charge
    kept.
- ``execution-scratch-start``, with only ``runner`` up: a project run that
  takes a while starts, and its account token, key, body, and job wait in
  the state directory. A run that had already completed when a read saw
  it proves the start only if its output shows the slow test ran, and
  then a fresh one goes in under a new key, up to three runs in all. The
  launcher then kills that replica and starts both again.
- ``execution-scratch-retry``: the job the killed replica held ends
  ``worker-lost``, and a same-key retry through nginx runs it again to
  the end.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
from pathlib import Path
from typing import Any

import factory
import verify_deployment as vd
from admission_check import READ_EVERY_S, SLOW_TRIES, Checks, call, ran_ms, resubmitted, usage, uuid7
from admission_deploy import gates_log, verifier_receipts
from pbclient import PBClient
from receipts import Receipt, ReceiptWriter

POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
FRONTEND = os.environ.get("FRONTEND_URL", "http://frontend").rstrip("/")
RUNNERS = [u.strip().rstrip("/") for u in os.environ.get("RUNNER_URLS", "").split(",") if u.strip()]
STATE = Path(os.environ.get("SCRATCH_STATE_PATH", "/state/scratch.json"))
GATES = {"EXECUTION_STORE": "on", "EXECUTION_SCRATCH": "on", "EXECUTION_DEFINITIONS": "enforce"}
ANSWER_KEYS = {"job_id", "state", "outcome_class", "retryable", "cancel_requested", "envelope"}
ENDED = {"completed", "timed-out", "denied", "canceled", "failed"}
JOBS = "/api/execution/jobs"

TWO_SUM = {"track": "coding", "slug": "two-sum", "variant": "python", "version": 1}
SOLVED = (
    "def two_sum(nums, target):\n"
    "    seen = {}\n"
    "    for i, num in enumerate(nums):\n"
    "        if target - num in seen:\n"
    "            return [seen[target - num], i]\n"
    "        seen[num] = i\n"
)
# Each of the definition's twelve cases takes 2.5 s, so a test run lasts
# past the worker's 10 s heartbeat, the beat a cancel reaches the run at.
SLOW_SOLVED = "import time\n\n\n" + SOLVED.replace("    seen = {}\n", "    time.sleep(2.5)\n    seen = {}\n", 1)
SPINNER = "def two_sum(nums, target):\n    while True:\n        pass\n"
PROJECT = {"track": "ai-coding", "slug": "hallucinated-http-client", "variant": "python", "version": 1}
# A visible test that takes eight of the run step's ten seconds, so the
# launcher can kill the replica running it.
SLOW_S = 8
SLOW_PROJECT = {
    "client.py": "def fetch_user(user_id):\n    return {'id': user_id}\n",
    "tests/checkpoint_0/test_visible.py": f"import time\n\n\ndef test_takes_a_while():\n    time.sleep({SLOW_S})\n",
}


def run_body(code: str, nums: list[int] | None = None) -> dict[str, Any]:
    return {"definition": TWO_SUM, "code": code, "input": {"nums": nums or [1, 2], "target": 3}}


def submit(token: str, path: str, key: str | None, body: dict) -> tuple[int, Any]:
    headers = {"Idempotency-Key": key} if key else {}
    status, parsed, _ = call(FRONTEND, "POST", path, token, body, headers)
    return status, parsed


def read(token: str, job_id: str, wait: int = 0) -> tuple[int, Any, int]:
    started = time.monotonic()
    status, parsed, _ = call(FRONTEND, "GET", f"{JOBS}/{job_id}?wait={wait}", token, timeout=wait + 15)
    return status, parsed, int((time.monotonic() - started) * 1000)


def settle(token: str, job_id: str, timeout_s: float = 120, until=None) -> dict:
    """The job once ``until`` holds, by default once it ended. Only a wait
    for an end long-polls; a wait for ``until`` reads the job as it is, as
    admission_check.job_until does and for the same reason."""
    wait = 0 if until else 20
    done = until or (lambda job: job.get("state") in ENDED)
    deadline = time.monotonic() + timeout_s
    last: dict = {}
    while time.monotonic() < deadline:
        status, parsed, _ = read(token, job_id, wait)
        if status == 200 and isinstance(parsed, dict):
            last = parsed
            if done(parsed):
                return parsed
            if not wait:
                time.sleep(READ_EVERY_S)
        else:
            time.sleep(1)
    return last


def started(job: dict) -> bool:
    return job.get("state") == "started" or job.get("state") in ENDED


def long_run(job: dict) -> str:
    """What the start phase makes of its slow run as a read saw it:
    ``running`` while it runs; ``ran`` once it completed after its slow
    test, which proves it started but leaves the launcher nothing to kill;
    ``failed`` otherwise: it never started, it ended too soon for the slow
    test to have run, or it ended some other way."""
    if job.get("state") == "started":
        return "running"
    took = ran_ms(job)
    if job.get("state") == "completed" and took is not None and took >= SLOW_S * 1000:
        return "ran"
    return "failed"


def ready(runner: str) -> bool:
    """Whether the replica answers its readiness check. One that was just
    started again may refuse the connection until it listens, which reads
    as not ready yet."""
    try:
        return call(runner, "GET", "/ready", timeout=3)[0] == 200
    except (urllib.error.URLError, OSError):
        return False


def wait_ready(runner: str, timeout_s: float = 90) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if ready(runner):
            return True
        time.sleep(1)
    return False


def sans_id(body: Any) -> Any:
    return {k: v for k, v in body.items() if k != "correlation_id"} if isinstance(body, dict) else body


def accounts(pb: PBClient, writer: ReceiptWriter, *tags: str) -> list[factory.Account]:
    out = []
    for tag in tags:
        acct = factory.make_account(tag)
        factory.register(pb, acct)
        writer.register_secret(acct.password, f"password:{tag}")
        writer.register_secret(acct.token, f"token:{tag}")
        out.append(acct)
    return out


def run_scratch(c: Checks, writer: ReceiptWriter) -> None:
    for service in ("runner", "runner-b"):
        results = vd.check_gates_log(gates_log("execution-scratch", service), dict(GATES),
                                     source=f"{service} gates line")
        verifier_receipts(writer, results, service)
        c.check(f"execution.scratch.gates.{service}", all(r.passed for r in results),
                "; ".join(r.detail for r in results if not r.passed))
    pb = PBClient(POCKETBASE_URL)
    pb.wait_healthy()
    a, b = accounts(pb, writer, "scr-a", "scr-b")

    # A run is a job that ends with its envelope.
    key = uuid7()
    status, first = submit(a.token, "/api/run", key, run_body(SOLVED))
    shaped = status == 202 and isinstance(first, dict) and set(first) == ANSWER_KEYS
    c.check("execution.scratch.run.accepted-as-a-job", shaped, f"status={status}")
    if not shaped:
        return
    job_id = first["job_id"]
    done = settle(a.token, job_id)
    output = (done.get("envelope") or {}).get("output") or {}
    c.check("execution.scratch.run.ends-with-its-envelope",
            (done.get("state"), done.get("outcome_class")) == ("completed", "passed")
            and output.get("return_value") == [0, 1],
            f"{done.get('state')}/{done.get('outcome_class')}")

    # The same request again: the same job, and no second charge.
    charged = usage(a.token)
    status, again = submit(a.token, "/api/run", key, run_body(SOLVED))
    c.check("execution.scratch.duplicate.same-job-uncharged",
            status == 202 and (again or {}).get("job_id") == job_id
            and (usage(a.token)["requests"], usage(a.token)["wall_seconds"])
            == (charged["requests"], charged["wall_seconds"]),
            f"status={status}")
    status, other = submit(a.token, "/api/run", key, run_body(SOLVED, [2, 1]))
    c.check("execution.scratch.mismatch.refused", status == 409 and (other or {}).get("code") == "idempotency_mismatch",
            f"status={status}")

    # Another account's read and cancel of A's job are the unknown id's 404.
    unknown = "zzzzzzzzzzzzzzz"
    foreign_read = read(b.token, job_id)
    unknown_read = read(b.token, unknown)
    same_read = foreign_read[0] == 404 and sans_id(foreign_read[1]) == sans_id(unknown_read[1]) \
        and (foreign_read[1] or {}).get("code") == "not_found"
    writer.write(Receipt("isolation.execution-jobs.read.foreign", JOBS, "read", "authenticated-other", 404,
                         foreign_read[0], same_read, foreign_read[2],
                         "" if same_read else f"status={foreign_read[0]} unknown={unknown_read[0]}"))
    c.check("isolation.execution-jobs.read.foreign", same_read, f"status={foreign_read[0]}")
    started_at = time.monotonic()
    fc, fbody, _ = call(FRONTEND, "POST", f"{JOBS}/{job_id}/cancel", b.token, None)
    uc, ubody, _ = call(FRONTEND, "POST", f"{JOBS}/{unknown}/cancel", b.token, None)
    untouched = read(a.token, job_id)[1] or {}
    same_cancel = fc == 404 and sans_id(fbody) == sans_id(ubody) and (fbody or {}).get("code") == "not_found" \
        and untouched.get("state") == "completed" and untouched.get("cancel_requested") is False
    writer.write(Receipt("isolation.execution-jobs.cancel.foreign", JOBS, "cancel", "authenticated-other", 404, fc,
                         same_cancel, int((time.monotonic() - started_at) * 1000),
                         "" if same_cancel else f"status={fc} unknown={uc}"))
    c.check("isolation.execution-jobs.cancel.foreign", same_cancel, f"status={fc}")

    # A cancel stops a running test run before its cases are done.
    status, slow = submit(a.token, "/api/evaluate", uuid7(), {"definition": TWO_SUM, "code": SLOW_SOLVED})
    slow_id = (slow or {}).get("job_id", "")
    running = settle(a.token, slow_id, 30, started) if status == 202 else {}
    asked = call(FRONTEND, "POST", f"{JOBS}/{slow_id}/cancel", a.token, None)[0] \
        if running.get("state") == "started" else 0
    stopped = settle(a.token, slow_id, 45) if asked == 200 else {}
    c.check("execution.scratch.cancel.stops-a-running-job",
            (stopped.get("state"), stopped.get("outcome_class")) == ("canceled", "canceled"),
            f"submit={status} cancel={asked} ended={stopped.get('state')}")

    # The time limit ends a run, names itself, keeps the charge, and shows
    # no output: only an end the run earned does.
    before = usage(a.token)["wall_seconds"]
    status, spin = submit(a.token, "/api/run", uuid7(), run_body(SPINNER))
    spun = settle(a.token, (spin or {}).get("job_id", ""), 60) if status == 202 else {}
    c.check("execution.scratch.limit.named-and-charged",
            (spun.get("state"), spun.get("outcome_class")) == ("timed-out", "resource-limit")
            and (spun.get("envelope") or {}).get("limit") == "wall_time"
            and (spun.get("envelope") or {}).get("output") is None
            and usage(a.token)["wall_seconds"] >= before + 3,
            f"{spun.get('state')}/{spun.get('outcome_class')}")


def run_start(c: Checks, writer: ReceiptWriter) -> None:
    pb = PBClient(POCKETBASE_URL)
    pb.wait_healthy()
    (acct,) = accounts(pb, writer, "scr-kill")
    body = {"definition": PROJECT, "checkpoint": 0, "files": SLOW_PROJECT}
    for tries in range(1, SLOW_TRIES + 1):
        key = uuid7()
        status, first = submit(acct.token, "/api/ai-coding/run-project", key, body)
        job_id = (first or {}).get("job_id", "")
        seen = settle(acct.token, job_id, 60, started) if status == 202 else {}
        seen_as = long_run(seen)
        if seen_as != "ran" or tries == SLOW_TRIES:
            break
        resubmitted("execution.scratch.long-run.started", key, seen, tries + 1)
    ok = seen_as == "running"
    c.check("execution.scratch.long-run.started", ok,
            f"status={status} state={seen.get('state')} ran_ms={ran_ms(seen)} tries={tries}")
    if ok:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps({"token": acct.token, "key": key, "body": body, "job_id": job_id}))
        os.chmod(STATE, 0o600)


def run_retry(c: Checks, writer: ReceiptWriter) -> None:
    try:
        saved = json.loads(STATE.read_text())
    except (OSError, ValueError):
        c.check("execution.scratch.long-run.saved", False, "the start phase saved no job")
        return
    writer.register_secret(saved["token"], "token:scr-kill")
    token, job_id = saved["token"], saved["job_id"]
    back = [runner for runner in RUNNERS if wait_ready(runner)]
    c.check("execution.scratch.killed-replica.replicas-ready", len(back) == len(RUNNERS) > 0,
            f"{len(back)} of {len(RUNNERS)} ready")
    lost = settle(token, job_id, 150)
    c.check("execution.scratch.killed-replica.worker-lost",
            (lost.get("state"), lost.get("outcome_class"), lost.get("retryable")) == ("failed", "worker-lost", True),
            f"{lost.get('state')}/{lost.get('outcome_class')} retryable={lost.get('retryable')}")
    status, again = submit(token, "/api/ai-coding/run-project", saved["key"], saved["body"])
    rerun = settle(token, job_id, 90) if status == 202 and (again or {}).get("job_id") == job_id else {}
    c.check("execution.scratch.killed-replica.same-key-retry-completes",
            rerun.get("state") == "completed" and rerun.get("outcome_class") in ("passed", "candidate-failure"),
            f"retry={status} ended={rerun.get('state')}/{rerun.get('outcome_class')}")
    STATE.unlink(missing_ok=True)


PHASES = {
    "execution-scratch": run_scratch,
    "execution-scratch-start": run_start,
    "execution-scratch-retry": run_retry,
}


def main(phase: str, writer: ReceiptWriter) -> int:
    c = Checks()
    try:
        PHASES[phase](c, writer)
    except Exception as err:  # noqa: BLE001 - a crash is one failed check, with its type only
        c.check(f"{phase}.ran", False, type(err).__name__)
    print(f"{phase}: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0
