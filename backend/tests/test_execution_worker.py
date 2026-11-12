"""The execution worker (ROUNDS-00A-L03) against the store's own checks
and decisions: pocketbase/tests/execution_server.cjs serves
pb_hooks/execution.js over HTTP on an in-memory store with a clock the
tests move. Jobs run through the legacy executor with test handlers,
since no kind has one until PR 2. The harness runs the same worker
against a real PocketBase. The claim loop's pauses are also tested on a
scripted store, some on a clock only those pauses move."""
from __future__ import annotations

import asyncio
import itertools
import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app import sandbox
from execution import runtime, store, worker as worker_mod
from execution.envelope import Part
from execution.executor import LegacyExecutor, RunSpec, Starved
from execution.worker import Result, Worker

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "pocketbase" / "tests" / "execution_server.cjs"
HOOKS = ROOT / "pocketbase" / "pb_hooks"
PY = sys.executable
SECRET = "test-execution-key-placeholder-0123456789"
RUNNER_KEY = "test-admission-key-placeholder-0123456789"
A = "acct00000000001"
B = "acct00000000002"
_keys = itertools.count(1)


class Server:
    def __init__(self, url: str) -> None:
        self.url = url
        self.http = httpx.Client(base_url=url, timeout=10)
        self._users: dict[str, str] = {}

    def token(self, account: str) -> str:
        if account not in self._users:
            self._users[account] = self.http.post("/__test/user", json={"account": account}).json()["token"]
        return self._users[account]

    def job(self, account: str = A, kind: str = "run", key: str | None = None) -> str:
        key = key or f"0190f000-0000-7000-8000-{next(_keys):012d}"
        operation = kind
        self.http.post("/__test/command", json={"account": account, "command_id": key, "operation": operation,
                                                "fingerprint": "a" * 64, "state": "in_flight"})
        res = self.enqueue(account, key, kind)
        assert res.status_code == 200, res.text
        return res.json()["job"]["id"]

    def enqueue(self, account: str, key: str, kind: str = "run") -> httpx.Response:
        body = {"command_id": key, "kind": kind, "definition": {"track": "coding", "slug": "two-sum",
                                                                  "variant": "python", "version": 1},
                "fingerprint": "a" * 64, "source_checksum": "c" * 64, "input_digest": "d" * 64,
                "input": {"code": "print(1)"}}
        return self.http.post("/api/rounds/execution/enqueue", json=body,
                              headers={"Authorization": f"Bearer {self.token(account)}",
                                       "X-Rounds-Admission-Key": RUNNER_KEY})

    def readmit(self, account: str, key: str, kind: str = "run") -> dict:
        """Admits the same key again, as a route does before it retries a
        job (ROUNDS-00A-L03 PR 2): a retryable job's command ends with
        it, and admission's retry verdict puts it back in flight."""
        wall = {"run": 3, "evaluate": 3, "run_project": 10, "take_home_run": 60}[kind]
        body = {"operation": kind, "command_id": key, "fingerprint": "a" * 64, "wall_seconds": wall,
                "lease_hash": "b" * 64}
        res = self.http.post("/api/rounds/admission/admit", json=body,
                             headers={"Authorization": f"Bearer {self.token(account)}",
                                      "X-Rounds-Admission-Key": RUNNER_KEY})
        assert res.status_code == 200, res.text
        return res.json()

    def cancel(self, account: str, job_id: str) -> httpx.Response:
        return self.http.post("/api/rounds/execution/cancel", json={"job_id": job_id},
                              headers={"Authorization": f"Bearer {self.token(account)}",
                                       "X-Rounds-Admission-Key": RUNNER_KEY})

    def advance(self, seconds: int) -> None:
        self.http.post("/__test/advance", json={"seconds": seconds})

    def dump(self) -> dict:
        return self.http.post("/__test/dump").json()

    def switch(self, on: bool) -> None:
        self.http.post("/__test/store", json={"on": on})

    def revoke(self) -> None:
        self.http.post("/__test/revoke")


@pytest.fixture
def server():
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    proc = subprocess.Popen([node, str(SERVER), str(HOOKS), SECRET, RUNNER_KEY], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        port = json.loads(proc.stdout.readline())["port"]
        yield Server(f"http://127.0.0.1:{port}")
    finally:
        proc.terminate()
        proc.wait(10)


@pytest.fixture(autouse=True)
def quick(monkeypatch):
    monkeypatch.setattr(worker_mod, "HEARTBEAT_S", 0.2)
    monkeypatch.setattr(worker_mod, "CLAIM_IDLE_S", 0.05)
    monkeypatch.setattr(worker_mod, "REAP_EVERY_S", 0.3)
    monkeypatch.setattr(worker_mod, "BACKOFF_S", (0.05, 0.05, 0.05, 0.05, 0.05))


class PythonHandler:
    """Runs one Python snippet per part, the way PR 2's handlers run a
    kind's steps."""

    def __init__(self, snippets: dict[str, str], wall_s: float = 10, budget: int = 3) -> None:
        self.snippets = snippets
        self.wall_s = wall_s
        self.budget = budget
        self.ran: list[str] = []
        self.returned = threading.Event()

    def budget_s(self, job):
        return self.budget

    def run(self, job, executor, slot, stop):
        parts, observation = [], None
        for part_id, code in self.snippets.items():
            if stop.is_set():
                break
            observation = executor.run(RunSpec(f"{job.id}-{part_id}", [PY, "-c", code], wall_s=self.wall_s), slot,
                                       stop)
            self.ran.append(part_id)
            if observation.canceled:
                break
            if observation.limit:
                parts.append(Part(part_id, "resource-limit", observation.limit))
            else:
                parts.append(Part(part_id, "passed" if observation.exit_status == 0 else "candidate-failure"))
        passed = sum(1 for p in parts if p.outcome_class == "passed")
        self.returned.set()
        return Result(parts=parts, score=passed / len(self.snippets), observation=observation)


class Raising:
    def budget_s(self, job):
        return 3

    def run(self, job, executor, slot, stop):
        raise RuntimeError("the handler broke")


async def _until(server: Server, done, timeout: float = 20) -> dict:
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient(base_url=server.url, timeout=10) as http:
        while True:
            state = (await http.post("/__test/dump")).json()
            if done(state):
                return state
            if time.monotonic() > deadline:
                raise AssertionError(f"timed out: {json.dumps(state)[:2000]}")
            await asyncio.sleep(0.05)


def _workers(server: Server, handlers, count: int = 1, slots: int = 2, secret: str = SECRET):
    out = []
    for i in range(count):
        client = store.ServiceClient(secret, base_url=server.url)
        executor = LegacyExecutor(pool=sandbox.SlotPool(slots))
        out.append(Worker(client, executor, handlers, name=f"runner-{i}"))
    return out


async def _run(server: Server, handlers, done, count: int = 1, slots: int = 2, during=None, secret: str = SECRET,
               timeout: float = 20):
    workers = _workers(server, handlers, count, slots, secret)
    tasks = [asyncio.create_task(w.run()) for w in workers]
    try:
        if during is not None:
            await during(workers)
        return await _until(server, done, timeout), workers
    finally:
        for w in workers:
            await w.stop()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for w in workers:
            w._executor.close()
            await w._client.aclose()


def _job(state: dict, job_id: str) -> dict:
    (job,) = [j for j in state["jobs"] if j["id"] == job_id]
    return job


def _ended(job_id: str):
    return lambda state: any(j["id"] == job_id and j["finished_at"] for j in state["jobs"])


# ---- one job, start to end ---------------------------------------------------


def test_a_claimed_job_runs_and_completes_with_one_authoritative_envelope(server):
    job_id = server.job(kind="run")
    handler = PythonHandler({"case-1": "print('ok')"})
    state, _ = asyncio.run(_run(server, {"run": handler}, _ended(job_id)))
    job = _job(state, job_id)
    assert (job["state"], job["outcome_class"], job["cleanup"]) == ("completed", "passed", "confirmed")
    (attempt,) = state["attempts"]
    assert attempt["state"] == "completed" and attempt["budget_s"] == 3 and attempt["started_at"] > 0
    (env,) = state["envelopes"]
    assert env["authoritative"] is True and env["user_view"]["score"] == 1.0
    assert env["user_view"]["parts"] == [{"id": "case-1", "outcome_class": "passed", "limit": None}]
    # The account reads the envelope; the operator view stays on the attempt.
    assert env["user"] == A and "operator_view" not in env
    operator = attempt["operator_view"]
    assert operator["executor_kind"] == "legacy-in-process" and operator["worker"] == "runner-0"
    assert operator["exit_status"] == 0 and operator["output_bytes"] == 3


def test_a_kind_without_a_handler_ends_definition_invalid_before_anything_runs(server):
    job_id = server.job(kind="grade")
    state, _ = asyncio.run(_run(server, {}, _ended(job_id)))
    job = _job(state, job_id)
    assert (job["state"], job["outcome_class"], job["attempts_started"]) == ("denied", "definition-invalid", 0)
    (env,) = state["envelopes"]
    assert env["authoritative"] is False and env["user_view"]["score"] is None
    assert state["attempts"][0]["started_at"] == 0


def test_a_failing_solution_is_an_authoritative_candidate_failure(server):
    job_id = server.job()
    handler = PythonHandler({"case-1": "print(1)", "case-2": "raise SystemExit(1)"})
    state, _ = asyncio.run(_run(server, {"run": handler}, _ended(job_id)))
    (env,) = state["envelopes"]
    assert (env["outcome_class"], env["authoritative"], env["user_view"]["score"]) == ("candidate-failure", True, 0.5)


def test_a_run_past_its_wall_budget_is_a_resource_limit_with_no_score(server):
    job_id = server.job()
    handler = PythonHandler({"case-1": "import time; time.sleep(30)"}, wall_s=0.5)
    state, _ = asyncio.run(_run(server, {"run": handler}, _ended(job_id)))
    job = _job(state, job_id)
    assert (job["state"], job["outcome_class"]) == ("timed-out", "resource-limit")
    (env,) = state["envelopes"]
    assert env["authoritative"] is True and env["user_view"]["limit"] == "wall_time"
    assert env["user_view"]["score"] is None


class Answering(PythonHandler):
    """Runs one snippet, then answers ``parts`` with ``output``, the body
    a scratch handler answers its route with."""

    def __init__(self, parts: list[Part], output: dict) -> None:
        super().__init__({"p": "print('ran')"})
        self.parts, self.output = parts, output

    def run(self, job, executor, slot, stop):
        ran = super().run(job, executor, slot, stop)
        return Result(parts=list(self.parts), output=dict(self.output), observation=ran.observation)


# The take-home handler's body when nothing came back from its channel:
# every criterion failed and a score of 0, which nothing earned.
UNSCORED = {"score": 0.0, "passed": False, "stdout": "", "stderr": "", "error": None, "duration_ms": 40,
            "truncated": False, "criteria": [{"id": "adds_small", "passed": False, "weight": 1, "logs": "no-result"}]}


@pytest.mark.parametrize(
    "parts, ended, kept",
    [([Part("p", "passed")], ("completed", "passed"), True),
     ([Part("p", "candidate-failure")], ("completed", "candidate-failure"), True),
     ([Part("p", "resource-limit", "wall_time")], ("timed-out", "resource-limit"), False),
     ([Part("p", "resource-limit", "memory")], ("completed", "resource-limit"), False),
     ([Part("p", "infrastructure-degraded")], ("failed", "infrastructure-degraded"), False),
     ([Part("p", "definition-invalid")], ("denied", "definition-invalid"), False)],
    ids=["passed", "candidate-failure", "time-limit", "memory-limit", "infrastructure", "definition"],
)
def test_only_an_end_the_run_earned_keeps_the_handlers_output(server, parts, ended, kept):
    job_id = server.job(kind="run")
    state, _ = asyncio.run(_run(server, {"run": Answering(parts, UNSCORED)}, _ended(job_id)))
    job = _job(state, job_id)
    assert (job["state"], job["outcome_class"]) == ended
    (env,) = state["envelopes"]
    assert env["user_view"]["output"] == (UNSCORED if kept else None)


def test_a_handler_that_raises_is_the_infrastructures_failure_and_retryable(server):
    key = "0190f000-0000-7000-8000-900000000001"
    job_id = server.job(key=key)
    state, _ = asyncio.run(_run(server, {"run": Raising()}, _ended(job_id)))
    job = _job(state, job_id)
    assert (job["state"], job["outcome_class"]) == ("failed", "infrastructure-degraded")
    assert state["envelopes"][0]["authoritative"] is False
    assert server.readmit(A, key)["idempotency"] == "retry_job"
    assert server.enqueue(A, key).json()["requeued"] is True


def test_a_job_that_gets_no_slot_in_time_ends_starved_and_never_started(server, monkeypatch):
    async def starved(self, wait_s):
        raise Starved

    monkeypatch.setattr(LegacyExecutor, "acquire", starved)
    job_id = server.job()
    state, _ = asyncio.run(_run(server, {"run": PythonHandler({"case-1": "print(1)"})}, _ended(job_id)))
    job = _job(state, job_id)
    assert (job["state"], job["outcome_class"], job["attempts_started"]) == ("timed-out", "infrastructure-degraded", 0)


class Refusing(PythonHandler):
    """A handler whose check before a slot refuses the job (PR 2)."""

    def __init__(self, refusal: Exception) -> None:
        super().__init__({"case-1": "print(1)"})
        self.refusal = refusal

    def prepare(self, job):
        raise self.refusal


@pytest.mark.parametrize(
    "refusal, ended",
    [
        (worker_mod.Withdrawn(), ("canceled", "canceled")),
        (worker_mod.InvalidJob(), ("denied", "definition-invalid")),
        (RuntimeError("the check broke"), ("failed", "infrastructure-degraded")),
    ],
)
def test_a_job_its_handler_refuses_before_a_slot_ends_without_a_start(server, refusal, ended):
    job_id = server.job()
    handler = Refusing(refusal)
    state, _ = asyncio.run(_run(server, {"run": handler}, _ended(job_id)))
    job = _job(state, job_id)
    assert (job["state"], job["outcome_class"]) == ended
    assert job["attempts_started"] == 0 and handler.ran == []
    (env,) = state["envelopes"]
    assert env["user_view"]["started_at"] is None and env["user_view"]["parts"] == []


# ---- cancel, lost leases, and races -----------------------------------------------


def _started(job_id: str):
    return lambda state: any(j["id"] == job_id and j["state"] == "started" for j in state["jobs"])


def test_a_cancel_reaches_the_run_at_the_next_heartbeat(server):
    job_id = server.job()
    handler = PythonHandler({"case-1": "import time; time.sleep(60)"}, wall_s=60, budget=3)

    async def cancel_once_started(_workers):
        await _until(server, _started(job_id))
        assert server.cancel(A, job_id).status_code == 200

    started = time.monotonic()
    state, _ = asyncio.run(_run(server, {"run": handler}, _ended(job_id), during=cancel_once_started))
    assert time.monotonic() - started < 20
    job = _job(state, job_id)
    assert (job["state"], job["outcome_class"]) == ("canceled", "canceled")
    (env,) = state["envelopes"]
    assert env["authoritative"] is False and env["user_view"]["score"] is None


def test_another_account_cant_cancel_the_job(server):
    job_id = server.job(account=A)
    assert server.cancel(B, job_id).json() == {"v": "execution/v1", "error": "not_found"}


def test_a_lost_lease_stops_the_run_and_its_late_result_is_rejected(server, capsys):
    job_id = server.job()
    handler = PythonHandler({"case-1": "import time; time.sleep(60)"}, wall_s=60)

    async def lose_the_lease(_workers):
        await _until(server, _started(job_id))
        server.advance(31)
        # The next heartbeat is refused, and the run stops long before
        # its 60 s sleep would end.
        await _until(server, lambda s: s["attempts"][0]["rejected_writes"] >= 1)
        for _ in range(100):
            if handler.returned.is_set():
                break
            await asyncio.sleep(0.05)
        assert handler.returned.is_set()

    asyncio.run(_run(server, {"run": handler}, _ended(job_id), during=lose_the_lease))
    # Once the worker has stopped, every write it tried is in.
    state = server.dump()
    job = _job(state, job_id)
    assert (job["state"], job["outcome_class"]) == ("failed", "worker-lost")
    (attempt,) = state["attempts"]
    assert attempt["rejected_writes"] >= 1
    # The only envelope is the reaper's, never authoritative.
    (env,) = state["envelopes"]
    assert env["authoritative"] is False and attempt["operator_view"]["worker"] == "runner-0"
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    assert any(line.get("metric") == "rounds_job_late_result_rejected_total" for line in lines)


def test_a_stop_just_after_a_run_ended_returns():
    """A run that ended a moment before the stop is done, but its own
    callback hasn't dropped it from the worker's set yet. The stop still
    returns. It runs on a thread so a stop that spins can't hold the suite."""
    returned = threading.Event()

    async def scenario():
        worker = Worker(None, None, {}, name="runner-x")

        async def ended():
            return None

        task = asyncio.create_task(ended())
        worker._tasks.add(task)
        task.add_done_callback(worker._tasks.discard)
        await asyncio.sleep(0)
        assert task.done() and task in worker._tasks
        await worker.stop()
        returned.set()

    threading.Thread(target=lambda: asyncio.run(scenario()), daemon=True).start()
    assert returned.wait(5)


def test_a_run_the_replica_stops_mid_way_ends_worker_lost_never_from_the_parts_that_ran(server):
    key = "0190f000-0000-7000-8000-900000000002"
    job_id = server.job(key=key)
    handler = PythonHandler({"case-1": "print(1)", "case-2": "import time; time.sleep(60)", "case-3": "print(3)"},
                            wall_s=60, budget=3)

    async def stop_once_a_part_passed(workers):
        await _until(server, _started(job_id))
        for _ in range(200):
            if handler.ran:
                break
            await asyncio.sleep(0.05)
        assert handler.ran == ["case-1"]
        await workers[0].stop()

    started = time.monotonic()
    state, _ = asyncio.run(_run(server, {"run": handler}, _ended(job_id), during=stop_once_a_part_passed))
    assert time.monotonic() - started < 20 and handler.ran == ["case-1", "case-2"]
    job = _job(state, job_id)
    assert (job["state"], job["outcome_class"]) == ("failed", "worker-lost")
    (env,) = state["envelopes"]
    assert env["authoritative"] is False and env["user_view"]["score"] is None
    # Nothing from the parts that ran reaches the account: no parts, no output.
    assert env["user_view"]["parts"] == [] and env["user_view"]["output"] is None
    # worker-lost is retryable: the same key runs attempt two.
    assert server.readmit(A, key)["idempotency"] == "retry_job"
    assert server.enqueue(A, key).json()["requeued"] is True


def test_a_job_the_replica_stops_before_it_started_goes_back_to_the_queue(server, monkeypatch):
    job_id = server.job()
    handler = PythonHandler({"case-1": "print(1)"})
    held: dict = {}
    acquire = LegacyExecutor.acquire

    async def slot_once_stopping(self, wait_s):
        # The slot comes only once the replica has begun to stop.
        while not (held.get("worker") and held["worker"]._stopping.is_set()):
            await asyncio.sleep(0.02)
        return await acquire(self, wait_s)

    monkeypatch.setattr(LegacyExecutor, "acquire", slot_once_stopping)

    async def stop_once_claimed(workers):
        held["worker"] = workers[0]
        await _until(server, lambda s: any(j["id"] == job_id and j["state"] == "leased" for j in s["jobs"]))
        await workers[0].stop()
        server.advance(31)
        await workers[0]._client.reap()

    asyncio.run(_run(server, {"run": handler}, lambda s: _job(s, job_id)["state"] == "queued",
                     during=stop_once_claimed))
    state = server.dump()
    job = _job(state, job_id)
    assert (job["state"], job["attempts_started"]) == ("queued", 0) and handler.ran == []
    # The only envelope is the reaper's, never authoritative.
    (env,) = state["envelopes"]
    assert (env["outcome_class"], env["authoritative"]) == ("worker-lost", False)


def _leased(job_id: str):
    return lambda state: any(j["id"] == job_id and j["state"] == "leased" for j in state["jobs"])


def test_a_claim_that_returns_once_the_replica_is_stopping_never_starts(server, monkeypatch):
    job_id = server.job()
    handler = PythonHandler({"case-1": "print(1)"})
    held: dict = {}
    claim = store.ServiceClient.claim

    async def claim_back_once_stopping(self, *args, **kwargs):
        out = await claim(self, *args, **kwargs)
        if out is not None:
            # The claim is still in flight when the replica begins to stop.
            while not (held.get("worker") and held["worker"]._stopping.is_set()):
                await asyncio.sleep(0.02)
        return out

    monkeypatch.setattr(store.ServiceClient, "claim", claim_back_once_stopping)

    async def stop_once_claimed(workers):
        held["worker"] = workers[0]
        await _until(server, _leased(job_id))
        await workers[0].stop()
        # Long enough for a run the claim started to get going.
        await asyncio.sleep(1.0)
        job = _job(server.dump(), job_id)
        assert (job["state"], job["attempts_started"]) == ("leased", 0) and handler.ran == []
        server.advance(31)
        await workers[0]._client.reap()

    asyncio.run(_run(server, {"run": handler}, lambda s: _job(s, job_id)["state"] == "queued",
                     during=stop_once_claimed))
    state = server.dump()
    job = _job(state, job_id)
    assert (job["state"], job["attempts_started"]) == ("queued", 0) and handler.ran == []
    # The only envelope is the reaper's, never authoritative.
    (env,) = state["envelopes"]
    assert (env["outcome_class"], env["authoritative"]) == ("worker-lost", False)


def test_a_slot_wait_that_runs_out_while_the_replica_stops_puts_the_job_back_in_the_queue(server, monkeypatch):
    job_id = server.job()
    handler = PythonHandler({"case-1": "print(1)"})
    held: dict = {}

    async def starved_once_stopping(self, wait_s):
        while not (held.get("worker") and held["worker"]._stopping.is_set()):
            await asyncio.sleep(0.02)
        raise Starved

    monkeypatch.setattr(LegacyExecutor, "acquire", starved_once_stopping)

    async def stop_once_claimed(workers):
        held["worker"] = workers[0]
        await _until(server, _leased(job_id))
        await workers[0].stop()
        # No terminal result: the job is still leased and never started.
        job = _job(server.dump(), job_id)
        assert (job["state"], job["attempts_started"]) == ("leased", 0)
        server.advance(31)
        await workers[0]._client.reap()

    asyncio.run(_run(server, {"run": handler}, lambda s: _job(s, job_id)["state"] == "queued",
                     during=stop_once_claimed))
    state = server.dump()
    job = _job(state, job_id)
    assert (job["state"], job["attempts_started"]) == ("queued", 0) and handler.ran == []
    # The only envelope is the reaper's, never authoritative.
    (env,) = state["envelopes"]
    assert (env["outcome_class"], env["authoritative"]) == ("worker-lost", False)


def test_two_replicas_racing_for_one_job_make_one_attempt(server):
    job_id = server.job()
    handler = PythonHandler({"case-1": "print(1)"})
    state, _ = asyncio.run(_run(server, {"run": handler}, _ended(job_id), count=2))
    assert [a["job"] for a in state["attempts"]] == [job_id]
    assert _job(state, job_id)["outcome_class"] == "passed"


def test_an_account_never_has_more_than_two_jobs_running_across_replicas(server):
    jobs = [server.job(account=A) for _ in range(4)] + [server.job(account=B)]
    handler = PythonHandler({"case-1": "import time; time.sleep(0.6)"})
    peak = {"A": 0}

    async def watch(_workers):
        async with httpx.AsyncClient(base_url=server.url, timeout=10) as http:
            for _ in range(60):
                state = (await http.post("/__test/dump")).json()
                active = [j for j in state["jobs"] if j["account"] == A and j["state"] in ("leased", "started")]
                peak["A"] = max(peak["A"], len(active))
                await asyncio.sleep(0.05)

    state, _ = asyncio.run(_run(server, {"run": handler}, lambda s: all(_ended(j)(s) for j in jobs), count=2,
                                slots=4, during=watch))
    assert 1 <= peak["A"] <= 2
    assert all(_job(state, j)["outcome_class"] == "passed" for j in jobs)


# ---- the session and readiness -----------------------------------------------------


def test_the_worker_is_ready_once_the_store_answers(server):
    async def check(workers):
        await asyncio.sleep(0.5)
        assert workers[0].ready() is True

    asyncio.run(_run(server, {}, lambda s: True, during=check))


def test_a_secret_the_store_rejects_keeps_the_worker_unready(server, capsys):
    async def check(workers):
        await asyncio.sleep(0.5)
        assert workers[0].ready() is False

    asyncio.run(_run(server, {}, lambda s: True, during=check, secret="wrong-placeholder-secret-0123456789abcd"))
    out = capsys.readouterr().out
    assert '"code":"login_rejected"' in out and SECRET not in out


def test_a_store_turned_off_makes_the_worker_unready(server, monkeypatch):
    monkeypatch.setattr(worker_mod, "READY_WINDOW_S", 0.4)

    async def check(workers):
        await asyncio.sleep(0.3)
        assert workers[0].ready() is True
        server.switch(False)
        await asyncio.sleep(0.8)
        assert workers[0].ready() is False

    asyncio.run(_run(server, {}, lambda s: True, during=check))


def test_a_revoked_session_logs_in_again(server):
    async def check(workers):
        await asyncio.sleep(0.3)
        server.revoke()
        await asyncio.sleep(0.5)
        assert workers[0].ready() is True

    asyncio.run(_run(server, {}, lambda s: True, during=check))
    assert server.dump()["logins"] >= 2


def test_the_service_routes_refuse_a_users_token(server):
    res = server.http.post("/api/rounds/execution/claim", json={"worker": "x", "token_hash": "a" * 64},
                           headers={"Authorization": f"Bearer {server.token(A)}"})
    assert res.status_code == 403


def test_the_client_reads_the_contract(server):
    async def go():
        client = store.ServiceClient(SECRET, base_url=server.url)
        try:
            assert await client.claim("runner-x") is None
            job_id = server.job()
            claim = await client.claim("runner-x")
            assert claim.job.id == job_id and claim.attempt.attempt_number == 1
            assert claim.job.input == {"code": "print(1)"} and claim.reaped == {
                "requeued": 0, "worker_lost": 0, "over_budget": 0}
            beat = await client.heartbeat(claim.attempt.id, claim.token, budget_s=3)
            assert beat.cancel_requested is False
            with pytest.raises(store.Superseded):
                await client.heartbeat(claim.attempt.id, store.new_token())
            server.advance(31)
            with pytest.raises(store.Superseded):
                await client.heartbeat(claim.attempt.id, claim.token)
            assert await client.reap() == {"requeued": 0, "worker_lost": 1, "over_budget": 0}
            server.switch(False)
            with pytest.raises(store.StoreOff):
                await client.reap()
        finally:
            await client.aclose()

    asyncio.run(go())


def test_a_wrong_secret_is_login_rejected(server):
    async def go():
        client = store.ServiceClient("wrong-placeholder-secret-0123456789abcd", base_url=server.url)
        try:
            with pytest.raises(store.LoginRejected):
                await client.login()
        finally:
            await client.aclose()

    asyncio.run(go())


@pytest.mark.parametrize("secret, usable", [
    (SECRET, True), ("x" * 32, True), ("x" * 72, True), ("x" * 31, False), ("x" * 73, False),
    ("has a space 0123456789abcdefghijklmnop", False), ("", False), (None, False),
])
def test_the_secret_takes_what_the_worker_record_takes(secret, usable):
    assert store.usable_secret(secret) is usable


def test_the_job_metrics_carry_their_labels_and_never_an_account(server, capsys):
    job_id = server.job()
    asyncio.run(_run(server, {"run": PythonHandler({"case-1": "print(1)"})}, _ended(job_id)))
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    jobs = [line for line in lines if line.get("event") == "execution.job"]
    terminal = [line for line in jobs if line["metric"] == "rounds_job_terminal_total"]
    assert terminal == [{"v": "obs/v1", "event": "execution.job", "metric": "rounds_job_terminal_total", "value": 1,
                         "kind": "run", "purpose": "scratch", "state": "completed", "outcome_class": "passed",
                         "executor_kind": "legacy-in-process", "service": "runner"}]
    assert {line["metric"] for line in jobs} >= {"rounds_job_queue_wait_seconds", "rounds_job_attempt_seconds"}
    assert all("account" not in line and "dropped" not in line for line in jobs)


# ---- the runtime and /ready ---------------------------------------------------------


def _ready(client, want: int, timeout: float = 8) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        res = client.get("/ready")
        if res.status_code == want or time.monotonic() > deadline:
            assert res.status_code == want, res.text
            return res.json()
        time.sleep(0.05)


def test_with_the_store_off_nothing_starts_and_ready_holds(client):
    assert client.get("/ready").json() == {"status": "ok", "store": "off"}
    assert client.get("/health").json() == {"status": "ok"}


def test_on_without_a_secret_logs_it_and_stays_ready(monkeypatch, capsys):
    from fastapi.testclient import TestClient

    from main import app

    monkeypatch.setenv("ROUNDS_GATE_EXECUTION_STORE", "on")
    monkeypatch.delenv("ROUNDS_EXECUTION_SECRET", raising=False)
    with TestClient(app) as client:
        assert client.get("/ready").json() == {"status": "ok", "store": "unconfigured"}
    assert '"code":"unconfigured","event":"execution.worker"' in capsys.readouterr().out


def test_on_with_the_secret_is_ready_once_the_worker_reaches_the_store(server, monkeypatch):
    from fastapi.testclient import TestClient

    from main import app

    monkeypatch.setenv("ROUNDS_GATE_EXECUTION_STORE", "on")
    monkeypatch.setenv("ROUNDS_EXECUTION_SECRET", SECRET)
    monkeypatch.setattr(store, "POCKETBASE_URL", server.url)
    job_id = server.job(kind="grade")
    with TestClient(app) as client:
        assert _ready(client, 200) == {"status": "ok", "store": "on"}
        # The grading key isn't on, so the claimed job ends before it runs
        # (PR 3 gave the grading kinds their handlers).
        deadline = time.monotonic() + 8
        while not _job(server.dump(), job_id)["finished_at"] and time.monotonic() < deadline:
            time.sleep(0.05)
    ended = _job(server.dump(), job_id)
    assert (ended["outcome_class"], ended["attempts_started"]) == ("canceled", 0)


def test_on_with_a_secret_the_store_rejects_is_unready(server, monkeypatch):
    from fastapi.testclient import TestClient

    from main import app

    monkeypatch.setenv("ROUNDS_GATE_EXECUTION_STORE", "on")
    monkeypatch.setenv("ROUNDS_EXECUTION_SECRET", "wrong-placeholder-secret-0123456789abcd")
    monkeypatch.setattr(store, "POCKETBASE_URL", server.url)
    with TestClient(app) as client:
        time.sleep(0.5)
        assert _ready(client, 503) == {"status": "unready", "store": "on"}
        assert client.get("/health").status_code == 200


def test_on_with_the_store_down_is_unready(monkeypatch):
    from fastapi.testclient import TestClient

    from main import app

    monkeypatch.setenv("ROUNDS_GATE_EXECUTION_STORE", "on")
    monkeypatch.setenv("ROUNDS_EXECUTION_SECRET", SECRET)
    # Nothing listens here.
    monkeypatch.setattr(store, "POCKETBASE_URL", "http://127.0.0.1:9")
    with TestClient(app) as client:
        time.sleep(0.3)
        assert _ready(client, 503)["status"] == "unready"


# ---- the claim loop's pauses ---------------------------------------------------------

# The cadence as it ships, which the quick fixture scales down for the
# tests above.
SHIPPED = {name: getattr(worker_mod, name) for name in ("CLAIM_IDLE_S", "REAP_EVERY_S")}


class Clock:
    """The worker's clock where only its pauses move it, at once."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def time(self) -> float:
        return self.now


class Slots:
    """An executor that always has a slot free."""

    kind = "legacy-in-process"

    def free_slots(self) -> int:
        return 4

    def healthy(self) -> bool:
        return True


NOTHING_REAPED = {"requeued": 0, "worker_lost": 0, "over_budget": 0}
CLAIMED = store.Claim(
    store.Job("job000000000001", A, "run", "scratch", {}, "a" * 64, "c" * 64, "d" * 64, {}, 0),
    store.Attempt("att000000000001", 1, 0), "test-token-placeholder", NOTHING_REAPED)


class Claims:
    """The store's claims as a script: True answers a job and False
    nothing queued, and once the script is used up the worker stops.
    ``at`` keeps each claim's time on ``clock`` and ``ready`` what /ready
    said just before it. The first claim takes ``hold`` seconds."""

    logged_in = True

    def __init__(self, script: list[bool], clock=time, hold: float = 0) -> None:
        self.script = list(script)
        self.clock = clock
        self.hold = hold
        self.at: list[float] = []
        self.ready: list[bool] = []
        self.worker: Worker | None = None

    async def claim(self, name: str):
        self.at.append(self.clock.monotonic())
        self.ready.append(runtime.readiness()["ready"])
        await asyncio.sleep(self.hold if len(self.at) == 1 else 0)
        if not self.script:
            self.worker._stopping.set()
            return None
        return CLAIMED if self.script.pop(0) else None

    async def reap(self):
        return dict(NOTHING_REAPED)


def _paced(monkeypatch, script: list[bool], draw: float | None = None) -> tuple[Claims, list[float]]:
    """Runs the claim loop alone over ``script`` at the shipped cadence,
    with the jitter's draw fixed at ``draw`` when one is given, on a clock
    each pause moves on at once by what it asked for. A claimed job ends
    at once. Answers the claims and each pause the loop asked for."""
    for name, value in SHIPPED.items():
        monkeypatch.setattr(worker_mod, name, value)
    clock, asked = Clock(), []

    async def pause(self, seconds, wakes=False):
        asked.append(seconds)
        clock.now += seconds
        await asyncio.sleep(0)
        return False

    async def process(self, claim):
        self._claimed -= 1

    monkeypatch.setattr(worker_mod, "time", clock)
    monkeypatch.setattr(Worker, "_pause", pause)
    monkeypatch.setattr(Worker, "_process", process)
    if draw is not None:
        monkeypatch.setattr(worker_mod, "random", SimpleNamespace(random=lambda: draw))
    claims = Claims(script, clock)

    async def scenario():
        worker = Worker(claims, Slots(), {}, name="runner-x")
        claims.worker = worker
        monkeypatch.setattr(runtime._runtime, "mode", "on")
        monkeypatch.setattr(runtime._runtime, "worker", worker)
        await asyncio.wait_for(worker._claim_loop(), 10)

    asyncio.run(scenario())
    return claims, asked


@pytest.mark.parametrize(
    "draw, pauses",
    [(0.5, [1.0, 2.0, 4.0, 8.0, 15.0, 15.0]),
     (0.0, [0.5, 1.0, 2.0, 4.0, 7.5, 7.5]),
     (0.999, [1.499, 2.998, 5.996, 11.992, 15.0, 15.0])],
    ids=["middle", "shortest", "longest"],
)
def test_an_idle_worker_backs_off_to_15_s_and_a_claimed_job_starts_it_over(monkeypatch, draw, pauses):
    claims, asked = _paced(monkeypatch, [False] * 6 + [True] + [False] * 2, draw)
    # Each claim that finds nothing doubles the pause, from about 1 s up to
    # 15 s, with a jitter of half either way that never passes 15 s.
    assert asked[:6] == pytest.approx(pauses)
    # A claim that gets a job asks again at once, and the pauses after it
    # start over from the shortest.
    assert claims.at[7] == claims.at[6]
    assert asked[6:8] == pytest.approx(pauses[:2])


def test_an_idle_worker_at_15_s_stays_ready(monkeypatch):
    # Every pause as long as the jitter lets it be, which is the cap from
    # the fifth on.
    claims, asked = _paced(monkeypatch, [False] * 40, draw=0.999)
    assert asked[4:40] == [15.0] * 36 == [worker_mod.CLAIM_IDLE_MAX_S] * 36
    # /ready counts a claim's answer as the store answering, and its window
    # is twice the cap, so it holds at every claim after the first.
    assert worker_mod.CLAIM_IDLE_MAX_S * 2 <= worker_mod.READY_WINDOW_S
    assert claims.ready[0] is False and all(claims.ready[1:])


def test_an_idle_worker_at_15_s_still_reaps_with_a_claim_at_least_every_15_s(monkeypatch):
    claims, asked = _paced(monkeypatch, [False] * 40, draw=0.999)
    assert asked[4:40] == [15.0] * 36
    # Each claim reaps first, so without the reap loop's own call, the jobs
    # a replica that died held still go back to the queue that often.
    gaps = [later - earlier for earlier, later in zip(claims.at, claims.at[1:])]
    assert max(gaps) <= worker_mod.REAP_EVERY_S + 1e-9 and worker_mod.REAP_EVERY_S == 15.0


async def _claimed(claims: Claims, count: int, timeout: float = 5) -> None:
    deadline = time.monotonic() + timeout
    while len(claims.at) < count:
        assert time.monotonic() < deadline, f"{len(claims.at)} claims, not {count}"
        await asyncio.sleep(0.01)


@pytest.mark.parametrize("during, caller", [("pause", "loop"), ("pause", "thread"), ("claim", "loop")],
                         ids=["pause", "pause-from-a-thread", "claim-in-flight"])
def test_a_wake_ends_an_idle_pause_and_the_next_claim_comes_at_once(monkeypatch, during, caller):
    # The pause after a claim that finds nothing is 10 s here.
    monkeypatch.setattr(worker_mod, "CLAIM_IDLE_S", 10.0)
    monkeypatch.setattr(worker_mod, "random", SimpleNamespace(random=lambda: 0.5))
    asked = []
    pause = Worker._pause

    async def recorded(self, seconds, *args, **kwargs):
        asked.append(seconds)
        return await pause(self, seconds, *args, **kwargs)

    monkeypatch.setattr(Worker, "_pause", recorded)

    async def scenario() -> float:
        # In flight, the first claim takes long enough for the wake to come
        # before it answers.
        claims = Claims([False] * 4, hold=0.4 if during == "claim" else 0)
        worker = Worker(claims, Slots(), {}, name="runner-x")
        claims.worker = worker
        claiming = asyncio.create_task(worker._claim_loop())
        try:
            await _claimed(claims, 1)
            await asyncio.sleep(0.1 if during == "claim" else 0.3)
            woken = time.monotonic()
            if caller == "thread":
                await asyncio.to_thread(worker.wake)
            else:
                worker.wake()
            await _claimed(claims, 2, timeout=3)
            return claims.at[1] - woken
        finally:
            await worker.stop()
            await asyncio.wait_for(claiming, 2)

    assert asyncio.run(scenario()) < 1
    # The pause after the claim the wake brought is the shortest again.
    assert asked[:2] == [10.0, 10.0]


def test_a_stop_ends_an_idle_worker_at_once(monkeypatch):
    # A long idle pause, and a reap loop that waits as long.
    monkeypatch.setattr(worker_mod, "CLAIM_IDLE_S", 10.0)
    monkeypatch.setattr(worker_mod, "REAP_EVERY_S", 10.0)

    async def scenario() -> float:
        claims = Claims([False] * 4)
        worker = Worker(claims, Slots(), {}, name="runner-x")
        claims.worker = worker
        running = asyncio.create_task(worker.run())
        await _claimed(claims, 1)
        await asyncio.sleep(0.3)
        began = time.monotonic()
        await worker.stop()
        await asyncio.wait_for(running, 2)
        return time.monotonic() - began

    assert asyncio.run(scenario()) < 1


def test_a_run_that_ends_has_its_replica_claim_at_once(server, monkeypatch):
    """The account's third job waits for one of its 2 running to end,
    and the end has the worker claim at once instead of after the idle
    pause, 10 s or more here, that the third job's empty claim began."""
    monkeypatch.setattr(worker_mod, "CLAIM_IDLE_S", 20.0)
    jobs = [server.job() for _ in range(3)]
    handler = PythonHandler({"case-1": "import time; time.sleep(0.3)"})
    state, _ = asyncio.run(_run(server, {"run": handler}, lambda s: all(_ended(j)(s) for j in jobs), slots=4,
                                timeout=8))
    assert [_job(state, j)["outcome_class"] for j in jobs] == ["passed"] * 3
