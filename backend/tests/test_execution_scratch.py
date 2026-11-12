"""Run, evaluate, run-project, and take-home run as durable jobs
(ROUNDS-00A-L03 PR 2).

The routes run end to end in this process: the runner app with its
admission and its worker, and pocketbase/tests/execution_server.cjs
serving pb_hooks/admission.js and pb_hooks/execution.js on one in-memory
store, with the users auth-refresh the runner checks a bearer with. The
harness runs the same routes through nginx on a real PocketBase with two
replicas. The scratch key's values, the job fingerprint, the handlers'
own checks, and the harness retry phase's readiness check are tested
without that server.
"""
from __future__ import annotations

import contextlib
import itertools
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import admission, admission_state, definitions, gates, obs, pb_auth, sandbox
from app.errors import TypedError
from execution import handlers, jobs, keys, kinds, runtime, store
from execution import worker as worker_mod
from execution.worker import InvalidJob, Withdrawn
from tests.test_definitions_enforce import (
    FORGERIES,
    HIDDEN_MARKER,
    JS_SEARCH,
    LEAKING,
    PYTHON_SEARCH,
    _store,
    _take_home_document,
    starter,
    visible_tests,
)

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "pocketbase" / "tests" / "execution_server.cjs"
HOOKS = ROOT / "pocketbase" / "pb_hooks"
SECRET = "test-execution-key-placeholder-0123456789"
RUNNER_KEY = "test-admission-key-placeholder-0123456789"
A = "acct00000000001"
B = "acct00000000002"
ON = {
    "ROUNDS_GATE_EXECUTION_STORE": "on",
    "ROUNDS_GATE_EXECUTION_DEFINITIONS": "enforce",
    "ROUNDS_GATE_EXECUTION_SCRATCH": "on",
    "ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "enforce",
    "ROUNDS_GATE_ENFORCE_QUOTA": "enforce",
}
ANSWER_KEYS = {"job_id", "state", "outcome_class", "retryable", "cancel_requested", "envelope"}
_keys = itertools.count(1)

TWO_SUM = (
    "def two_sum(nums, target):\n"
    "    seen = {}\n"
    "    for i, num in enumerate(nums):\n"
    "        if target - num in seen:\n"
    "            return [seen[target - num], i]\n"
    "        seen[num] = i\n"
)
SLEEPER = "import time\n\ndef two_sum(nums, target):\n    time.sleep(30)\n"
SPINNER = "def two_sum(nums, target):\n    while True:\n        pass\n"
TWO_SUM_REF = {"track": "coding", "slug": "two-sum", "variant": "python", "version": 1}
RUN = {"definition": TWO_SUM_REF, "code": TWO_SUM, "input": {"nums": [1, 2], "target": 3}}
EVALUATE = {"definition": TWO_SUM_REF, "code": TWO_SUM, "tags": ["basic"]}
PROJECT_REF = {"track": "ai-coding", "slug": "hallucinated-http-client", "variant": "python", "version": 1}
TAKE_HOME_REF = {"track": "take-home", "slug": "add-numbers-py", "variant": "python", "version": 1}


def new_key() -> str:
    return f"0190f000-0000-7000-8000-{next(_keys):012d}"


def run_body(code: str = TWO_SUM) -> dict:
    return {**RUN, "code": code}


# ---- the stack --------------------------------------------------------------------


class Node:
    """The hooks' server: tokens for accounts, its store, and its clock."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.http = httpx.Client(base_url=url, timeout=10)
        self._tokens: dict[str, str] = {}

    def token(self, account: str) -> str:
        if account not in self._tokens:
            self._tokens[account] = self.http.post("/__test/user", json={"account": account}).json()["token"]
        return self._tokens[account]

    def dump(self) -> dict:
        return self.http.post("/__test/dump").json()

    def switch(self, on: bool) -> None:
        self.http.post("/__test/store", json={"on": on})

    def charged(self, account: str = A) -> tuple[int, int]:
        """The account's requests and wall seconds this hour."""
        rows = [c for c in self.dump()["counters"] if c["bucket"] == "account" and c["account"] == account]
        return sum(r["requests"] for r in rows), sum(r["wall_seconds"] for r in rows)


@pytest.fixture
def node():
    exe = shutil.which("node")
    assert exe, "node is required for the PocketBase hook checks; CI installs it"
    proc = subprocess.Popen([exe, str(SERVER), str(HOOKS), SECRET, RUNNER_KEY], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        port = json.loads(proc.stdout.readline())["port"]
        yield Node(f"http://127.0.0.1:{port}")
    finally:
        proc.terminate()
        proc.wait(10)


def _until(done, timeout: float = 20, what: str = "") -> None:
    deadline = time.monotonic() + timeout
    while not done():
        assert time.monotonic() < deadline, f"timed out waiting for {what or done}"
        time.sleep(0.05)


@pytest.fixture
def runner(node, monkeypatch):
    """``start(env, secret)`` starts the runner app on ``node`` with the
    gates in ``env`` and the worker's secret, and answers its test client,
    once the worker takes jobs when ``ready``. Everything stops after the
    test."""
    monkeypatch.setattr(worker_mod, "HEARTBEAT_S", 0.2)
    monkeypatch.setattr(worker_mod, "CLAIM_IDLE_S", 0.05)
    monkeypatch.setattr(worker_mod, "REAP_EVERY_S", 0.3)
    monkeypatch.setattr(worker_mod, "BACKOFF_S", (0.05, 0.05, 0.05, 0.05, 0.05))
    for module in (admission, admission_state, pb_auth, store):
        monkeypatch.setattr(module, "POCKETBASE_URL", node.url)
    # The real admission client, on the hooks' server, not conftest's fake.
    monkeypatch.setattr(admission, "store", admission_state)
    monkeypatch.setattr(admission, "FINISH_BACKOFF_S", (0, 0))
    # The app's start reloads both; they go back as they were after.
    monkeypatch.setattr(gates, "_snapshot", gates._snapshot)
    monkeypatch.setattr(definitions, "_store", definitions._store)
    stack = contextlib.ExitStack()

    def start(env: dict[str, str] = ON, secret: str = SECRET, ready: bool = True,
              runner_key: str = RUNNER_KEY) -> TestClient:
        for name in [n for n in os.environ if n.startswith("ROUNDS_GATE_")]:
            monkeypatch.delenv(name)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        # An empty value starts the runner without that secret.
        for name, value in (("ROUNDS_EXECUTION_SECRET", secret), ("ROUNDS_ADMISSION_SECRET", runner_key)):
            if value:
                monkeypatch.setenv(name, value)
            else:
                monkeypatch.delenv(name, raising=False)
        from main import app

        client = stack.enter_context(TestClient(app))
        if ready:
            _until(runtime.accepting_jobs, what="the worker")
        return client

    with stack:
        yield start


def headers(node: Node, account: str = A, key: str | None = None) -> dict[str, str]:
    out = {"Authorization": f"Bearer {node.token(account)}"}
    if key is not None:
        out["Idempotency-Key"] = key
    return out


def typed(res, status: int, code: str) -> dict:
    assert res.status_code == status, res.text
    body = res.json()
    assert body["code"] == code, body
    return body


def submitted(res) -> dict:
    assert res.status_code == 202, res.text
    body = res.json()
    assert set(body) == ANSWER_KEYS, body
    return body


def settled(client: TestClient, node: Node, job_id: str, account: str = A, timeout: float = 60) -> dict:
    """The job once it ended, read the way a page reads it."""
    deadline = time.monotonic() + timeout
    while True:
        res = client.get(f"/api/execution/jobs/{job_id}?wait=5", headers=headers(node, account))
        assert res.status_code == 200, res.text
        body = res.json()
        assert set(body) == ANSWER_KEYS, body
        if kinds.is_terminal(body["state"]):
            return body
        assert time.monotonic() < deadline, body


def obs_lines(capsys) -> list[dict]:
    return [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]


# ---- the scratch key --------------------------------------------------------------


ENFORCED = {"ROUNDS_GATE_EXECUTION_DEFINITIONS": "enforce"}


@pytest.mark.parametrize(
    "env, effective, needs",
    [
        # The defaults: the store and the key are on, definitions aren't
        # enforced.
        ({}, "off", ["EXECUTION_DEFINITIONS=enforce"]),
        (ENFORCED, "on", []),
        ({"ROUNDS_GATE_EXECUTION_SCRATCH": "off"}, "off", ["EXECUTION_DEFINITIONS=enforce"]),
        ({**ENFORCED, "ROUNDS_GATE_EXECUTION_SCRATCH": "off"}, "off", []),
        ({**ENFORCED, "ROUNDS_GATE_EXECUTION_STORE": "off"}, "off", ["EXECUTION_STORE=on"]),
        ({"ROUNDS_GATE_EXECUTION_STORE": "off"}, "off", ["EXECUTION_STORE=on", "EXECUTION_DEFINITIONS=enforce"]),
        ({**ON, "ROUNDS_GATE_EXECUTION_DEFINITIONS": "disabled"}, "off", ["EXECUTION_DEFINITIONS=enforce"]),
        (ON, "on", []),
        # legacy ran each route in its request until PR 4; it acts as off.
        ({**ON, "ROUNDS_GATE_EXECUTION_SCRATCH": "legacy"}, "off", []),
        # A value outside the list is the most restrictive one.
        ({**ON, "ROUNDS_GATE_EXECUTION_SCRATCH": "yes"}, "off", []),
    ],
)
def test_the_scratch_key_is_on_only_with_the_store_on_and_definitions_enforced(job_secrets, monkeypatch, env,
                                                                                effective, needs):
    monkeypatch.setattr(gates, "_snapshot", gates.load(env, gates.RUNNER))
    assert keys.scratch() == effective
    assert keys.scratch_needs() == needs


@pytest.mark.parametrize(
    "unset, needs",
    [
        (("ROUNDS_EXECUTION_SECRET",), ["ROUNDS_EXECUTION_SECRET"]),
        (("ROUNDS_ADMISSION_SECRET",), ["ROUNDS_ADMISSION_SECRET"]),
        (("ROUNDS_EXECUTION_SECRET", "ROUNDS_ADMISSION_SECRET"), ["ROUNDS_EXECUTION_SECRET", "ROUNDS_ADMISSION_SECRET"]),
    ],
)
def test_the_scratch_key_also_needs_both_secrets_on_this_runner(job_secrets, monkeypatch, unset, needs):
    monkeypatch.setattr(gates, "_snapshot", gates.load(ON, gates.RUNNER))
    for name in unset:
        monkeypatch.delenv(name)
    assert keys.scratch() == "off" and keys.scratch_needs() == needs
    # One the runner can't use counts as missing, as the worker and the
    # admission client read them.
    for name in unset:
        monkeypatch.setenv(name, "too-short")
    assert keys.scratch() == "off" and keys.scratch_needs() == needs


def test_on_without_what_it_needs_says_so_once_at_start_and_never_names_a_value(job_secrets, monkeypatch, capsys):
    monkeypatch.setattr(gates, "_snapshot", gates.load({}, gates.RUNNER))
    monkeypatch.delenv("ROUNDS_EXECUTION_SECRET")
    capsys.readouterr()
    keys.log_startup()
    out = capsys.readouterr().out
    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    (line,) = [x for x in lines if x["event"] == "execution.scratch"]
    assert {k: line[k] for k in ("event", "code", "needs", "service")} == {
        "event": "execution.scratch", "code": "acting_off",
        "needs": ["EXECUTION_DEFINITIONS=enforce", "ROUNDS_EXECUTION_SECRET"], "service": "runner"}
    assert "test-admission-key-placeholder" not in out
    for env in (ENFORCED, ON, {**ENFORCED, "ROUNDS_GATE_EXECUTION_SCRATCH": "off",
                               "ROUNDS_GATE_EXECUTION_GRADING": "off"}):
        monkeypatch.setenv("ROUNDS_EXECUTION_SECRET", SECRET)
        monkeypatch.setattr(gates, "_snapshot", gates.load(env, gates.RUNNER))
        keys.log_startup()
        assert [x for x in obs_lines(capsys) if x["event"] == "execution.scratch"] == []


def test_legacy_says_once_at_start_that_it_acts_as_off(job_secrets, monkeypatch, capsys):
    monkeypatch.setattr(gates, "_snapshot", gates.load({**ON, "ROUNDS_GATE_EXECUTION_SCRATCH": "legacy"},
                                                       gates.RUNNER))
    capsys.readouterr()
    keys.log_startup()
    (line,) = [x for x in obs_lines(capsys) if x["event"] == "execution.scratch"]
    assert {k: line[k] for k in ("event", "code", "service")} == {
        "event": "execution.scratch", "code": "legacy_retired", "service": "runner"}
    assert "needs" not in line


def test_the_scratch_line_carries_only_the_settings_a_key_can_need():
    assert {f"{name}={value}" for name, value in keys.SCRATCH_NEEDS} | set(keys.SECRET_NEEDS) == \
        obs.GATE_REQUIREMENTS
    line = obs.build("execution.scratch", code="acting_off", needs=["EXECUTION_STORE=on"], service="runner")
    assert line["needs"] == ["EXECUTION_STORE=on"]
    # A secret by its name only: a line that would carry a value drops it.
    line = obs.build("execution.scratch", code="acting_off", needs=["ROUNDS_EXECUTION_SECRET"], service="runner")
    assert line["needs"] == ["ROUNDS_EXECUTION_SECRET"]
    for needs in (["ROUNDS_EXECUTION_SECRET=x"], ["EXECUTION_STORE=off"], [], "EXECUTION_STORE=on"):
        line = obs.build("execution.scratch", code="acting_off", needs=needs, service="runner")
        assert "needs" not in line and line["dropped"] == ["needs"]


@pytest.mark.parametrize("verdict", ["job", "retry_job"])
def test_a_decision_line_keeps_a_jobs_idempotency_verdict(verdict):
    line = obs.build("decision", idempotency=verdict, quota="skipped")
    assert line["idempotency"] == verdict and "dropped" not in line


def test_the_four_scratch_kinds_agree_everywhere():
    # PR 3 adds the two grading kinds' routes and handlers beside these.
    scratch_routes = {kind for kind in jobs.ROUTES if kinds.KINDS[kind].purpose == "scratch"}
    assert set(handlers.SCRATCH_HANDLERS) == keys.SCRATCH_OPERATIONS == scratch_routes
    for kind, path in jobs.ROUTES.items():
        assert admission.ROUTES[("POST", path)].operation == kind
    assert set(jobs.ROUTES) - scratch_routes == set(handlers.GRADING_HANDLERS)
    assert runtime.default_handlers().keys() == handlers.SCRATCH_HANDLERS.keys() | handlers.GRADING_HANDLERS.keys()


# ---- the fingerprint --------------------------------------------------------------


def test_a_jobs_fingerprint_covers_its_route_definition_source_and_inputs():
    base = jobs.fingerprint("/api/run", TWO_SUM_REF, jobs.digest("code"), jobs.digest({"input": {"a": 1}}))
    assert base == jobs.fingerprint("/api/run", dict(reversed(TWO_SUM_REF.items())), jobs.digest("code"),
                                    jobs.digest({"input": {"a": 1}}))
    changed = [
        jobs.fingerprint("/api/evaluate", TWO_SUM_REF, jobs.digest("code"), jobs.digest({"input": {"a": 1}})),
        jobs.fingerprint("/api/run", {**TWO_SUM_REF, "version": 2}, jobs.digest("code"),
                         jobs.digest({"input": {"a": 1}})),
        jobs.fingerprint("/api/run", TWO_SUM_REF, jobs.digest("code "), jobs.digest({"input": {"a": 1}})),
        jobs.fingerprint("/api/run", TWO_SUM_REF, jobs.digest("code"), jobs.digest({"input": {"a": 2}})),
    ]
    assert len({base, *changed}) == 5


def test_a_value_json_cant_hold_exactly_is_an_invalid_request():
    with pytest.raises(TypedError) as refused:
        jobs.digest({"x": float("nan")})
    assert refused.value.code == "invalid_request"


# ---- the handlers' checks, before a slot --------------------------------------------


class _Job:
    def __init__(self, kind: str, definition: dict, job_input: dict, job_id: str = "job000000000001") -> None:
        self.id, self.kind, self.definition, self.input = job_id, kind, definition, job_input


@pytest.fixture
def scratch_on(job_secrets, monkeypatch):
    monkeypatch.setattr(gates, "_snapshot", gates.load(ON, gates.RUNNER))
    monkeypatch.setattr(definitions, "_store", definitions.Store().load())


@pytest.mark.parametrize("value", ["legacy", "off"])
def test_a_job_claimed_while_the_key_isnt_on_is_withdrawn(job_secrets, monkeypatch, value):
    monkeypatch.setattr(gates, "_snapshot", gates.load({**ON, "ROUNDS_GATE_EXECUTION_SCRATCH": value}, gates.RUNNER))
    with pytest.raises(Withdrawn):
        handlers.SCRATCH_HANDLERS["run"].prepare(_Job("run", TWO_SUM_REF, {"code": TWO_SUM, "input": {}}))


def test_a_claimed_job_needs_the_gates_and_not_the_admission_secret(scratch_on, monkeypatch):
    monkeypatch.delenv("ROUNDS_ADMISSION_SECRET")
    job = _Job("run", TWO_SUM_REF, {"code": TWO_SUM, "input": {}})
    # This runner's own routes act as off, and a job it claims still runs.
    assert (keys.scratch(), keys.scratch(worker=True)) == ("off", "on")
    handlers.SCRATCH_HANDLERS["run"].prepare(job)
    monkeypatch.setattr(gates, "_snapshot", gates.load({**ON, "ROUNDS_GATE_EXECUTION_DEFINITIONS": "legacy"},
                                                       gates.RUNNER))
    with pytest.raises(Withdrawn):
        handlers.SCRATCH_HANDLERS["run"].prepare(job)


@pytest.mark.parametrize(
    "kind, definition, job_input",
    [
        ("run", TWO_SUM_REF, {"code": TWO_SUM}),
        ("run", TWO_SUM_REF, {"code": TWO_SUM, "input": {}, "test_command": "x"}),
        ("run", {**TWO_SUM_REF, "version": 99}, {"code": TWO_SUM, "input": {}}),
        ("run", {**TWO_SUM_REF, "slug": "no-such-question"}, {"code": TWO_SUM, "input": {}}),
        ("run", PROJECT_REF, {"code": TWO_SUM, "input": {}}),
        ("evaluate", TWO_SUM_REF, {"code": TWO_SUM, "case_ids": ["c999"], "tags": None}),
        ("evaluate", TWO_SUM_REF, {"code": TWO_SUM, "case_ids": None, "tags": ["no-such-tag"]}),
        ("run_project", PROJECT_REF, {"checkpoint": 7, "files": {}}),
        ("run_project", PROJECT_REF, {"checkpoint": 0, "files": {"harness/grade.py": "x"}}),
        ("take_home_run", {**TAKE_HOME_REF, "slug": "kv-store-py"}, {"files": {}}),
    ],
)
def test_a_job_its_handler_cant_run_is_invalid_before_anything_starts(scratch_on, kind, definition, job_input):
    with pytest.raises(InvalidJob):
        handlers.SCRATCH_HANDLERS[kind].prepare(_Job(kind, definition, job_input))


def test_a_prepared_job_keeps_its_plan_until_it_runs(scratch_on):
    handler = handlers.SCRATCH_HANDLERS["evaluate"]
    job = _Job("evaluate", TWO_SUM_REF, {"code": TWO_SUM, "case_ids": None, "tags": ["basic"]}, "job000000000777")
    handler.prepare(job)
    assert handler.budget_s(job) == 3 * 3
    assert [case["case_id"] for _i, case in handler.plan(job).extra["selected"]] == ["c000", "c001", "c002"]


def test_cleanup_is_confirmed_only_once_the_directory_and_the_group_are_gone(tmp_path):
    assert handlers.cleanup_of([]) == "confirmed"
    left = sandbox.Control(stop=None)
    left.cwd = str(tmp_path)
    assert handlers.cleanup_of([left]) == "unconfirmed"
    gone = sandbox.Control(stop=None)
    gone.cwd = str(tmp_path / "removed")
    assert handlers.cleanup_of([gone]) == "confirmed"


# ---- a route's job steps, on conftest's admission fake --------------------------------

QUEUED = store.JobView("job000000000001", "run", "queued", None, 0, 0, False, None, 100, None)


class FakeCaller:
    """The store's caller routes for one request: enqueue answers
    ``answer`` or raises ``failure``; status answers ``found``."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.answer = (QUEUED, False, False)
        self.failure: Exception | None = None
        self.found: store.JobStatus | None = store.JobStatus(QUEUED, False, None)

    def __call__(self, _token):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return None

    async def enqueue(self, payload):
        self.calls.append(("enqueue", payload))
        if self.failure is not None:
            raise self.failure
        return self.answer

    async def status(self, job_id):
        self.calls.append(("status", job_id))
        return self.found


@pytest.fixture
def jobs_on(job_secrets, monkeypatch, signed_in, admission_store):
    """The scratch key on, this replica taking jobs, and the store's
    caller routes faked. Answers (headers, the admission fake, the
    caller fake)."""
    monkeypatch.setattr(gates, "_snapshot", gates.load(ON, gates.RUNNER))
    monkeypatch.setattr(definitions, "_store", definitions.Store().load())
    monkeypatch.setattr(runtime, "accepting_jobs", lambda: True)
    caller = FakeCaller()
    monkeypatch.setattr(store, "Caller", caller)
    return signed_in, admission_store, caller


def test_a_new_job_is_admitted_charged_and_enqueued_with_its_digests(client, jobs_on):
    signed_in, admission_store, caller = jobs_on
    key = new_key()
    out = submitted(client.post("/api/run", json=RUN, headers={**signed_in, "Idempotency-Key": key}))
    assert out["job_id"] == QUEUED.id and out["state"] == "queued"
    (admitted,) = admission_store.called("admit")
    assert (admitted["operation"], admitted["wall_seconds"], admitted["mode"]) == ("run", 3, "enforce")
    assert admitted["fingerprint"] == jobs.fingerprint("/api/run", TWO_SUM_REF, jobs.digest(TWO_SUM),
                                                       jobs.digest({"input": RUN["input"]}))
    ((call, payload),) = caller.calls
    assert call == "enqueue"
    assert payload["command_id"] == key and payload["fingerprint"] == admitted["fingerprint"]
    assert payload["input"] == {"code": TWO_SUM, "input": RUN["input"]}
    # The request's lease finished once the 202 was out.
    (finished,) = admission_store.called("finish")
    assert finished["outcome"] == "completed"


def test_a_duplicate_answers_its_job_from_the_store_and_is_never_charged(client, jobs_on):
    signed_in, admission_store, caller = jobs_on
    key = new_key()
    submitted(client.post("/api/run", json=RUN, headers={**signed_in, "Idempotency-Key": key}))
    admission_store.link_job(signed_in["Authorization"].split()[1], key, QUEUED.id)
    caller.calls.clear()
    out = submitted(client.post("/api/run", json=RUN, headers={**signed_in, "Idempotency-Key": key}))
    assert out["job_id"] == QUEUED.id
    assert caller.calls == [("status", QUEUED.id)]
    # One lease, the first request's: the duplicate made none.
    assert len(admission_store.called("finish")) == 1


def test_a_retry_of_a_job_the_infrastructure_lost_is_admitted_again_and_requeued(client, jobs_on):
    signed_in, admission_store, caller = jobs_on
    key = new_key()
    submitted(client.post("/api/run", json=RUN, headers={**signed_in, "Idempotency-Key": key}))
    admission_store.link_job(signed_in["Authorization"].split()[1], key, QUEUED.id, retryable=True)
    caller.answer = (QUEUED, True, True)
    caller.calls.clear()
    out = submitted(client.post("/api/run", json=RUN, headers={**signed_in, "Idempotency-Key": key}))
    assert out["state"] == "queued" and [c[0] for c in caller.calls] == ["enqueue"]
    assert len(admission_store.called("admit")) == 2 and len(admission_store.called("finish")) == 2


@pytest.mark.parametrize(
    "failure, status, code, outcome",
    [
        (store.Mismatch(), 409, "idempotency_mismatch", "denied"),
        (store.Unavailable(), 503, "worker_unavailable", "denied"),
        (store.StoreOff(), 503, "worker_unavailable", "denied"),
    ],
)
def test_an_enqueue_the_store_refuses_ends_the_request_and_its_charge(client, jobs_on, failure, status, code,
                                                                       outcome):
    signed_in, admission_store, caller = jobs_on
    caller.failure = failure
    typed(client.post("/api/run", json=RUN, headers={**signed_in, "Idempotency-Key": new_key()}), status, code)
    (finished,) = admission_store.called("finish")
    assert finished["outcome"] == outcome


def test_over_quota_a_job_route_enqueues_nothing(client, jobs_on):
    signed_in, admission_store, caller = jobs_on
    admission_store.quota, admission_store.retry_after = "exceeded", 600
    res = client.post("/api/run", json=RUN, headers={**signed_in, "Idempotency-Key": new_key()})
    typed(res, 429, "quota_exceeded")
    assert caller.calls == []


def test_an_admission_store_that_doesnt_answer_enqueues_nothing(client, jobs_on):
    signed_in, admission_store, caller = jobs_on
    admission_store.down = True
    typed(client.post("/api/run", json=RUN, headers={**signed_in, "Idempotency-Key": new_key()}), 503,
          "quota_unavailable")
    assert caller.calls == []


def test_a_definition_refusal_comes_before_any_job(client, jobs_on):
    signed_in, admission_store, caller = jobs_on
    body = {**RUN, "definition": {**TWO_SUM_REF, "version": 99}}
    res = client.post("/api/run", json=body, headers={**signed_in, "Idempotency-Key": new_key()})
    assert res.status_code in (404, 409, 410), res.text
    assert caller.calls == []
    (finished,) = admission_store.called("finish")
    assert finished["outcome"] == "denied"


# ---- the routes, end to end ----------------------------------------------------------


SCRATCH_BODIES = {
    "/api/run": RUN,
    "/api/evaluate": EVALUATE,
    "/api/ai-coding/run-project": {"definition": PROJECT_REF, "checkpoint": 0, "files": {}},
    "/api/take-home/run": {"definition": TAKE_HOME_REF, "files": {}},
}


# legacy ran these in their request until PR 4; now it answers as off.
@pytest.mark.parametrize("value", ["off", "legacy"])
@pytest.mark.parametrize("path", sorted(SCRATCH_BODIES))
def test_off_answers_503_before_anything_and_keeps_every_draft(runner, node, path, value):
    client = runner({**ON, "ROUNDS_GATE_EXECUTION_SCRATCH": value})
    out = typed(client.post(path, json=SCRATCH_BODIES[path], headers=headers(node, key=new_key())), 503,
                "execution_disabled")
    assert out["detail"] == "Running practice code is turned off on this server."
    # Before the account check, as the other route switches are.
    typed(client.post(path, json=SCRATCH_BODIES[path]), 503, "execution_disabled")
    state = node.dump()
    assert state["commands"] == [] and state["counters"] == [] and state["jobs"] == []


# The six routes, each with the sentence its key answers while it's off.
ROUTE_OFF = {
    "/api/run": "Running practice code is turned off on this server.",
    "/api/evaluate": "Running practice code is turned off on this server.",
    "/api/ai-coding/run-project": "Running practice code is turned off on this server.",
    "/api/take-home/run": "Running practice code is turned off on this server.",
    "/api/ai-coding/grade": keys.GRADING_OFF,
    "/api/take-home/submit": keys.GRADING_OFF,
}


@pytest.fixture
def unadmitted(job_secrets, monkeypatch):
    """The six routes with no admission in front of them, their body
    reader recording each read, and ``use(value)`` setting both keys."""
    from fastapi import FastAPI

    from app import errors, execution as definition_runs
    from routers import ai_coding, runner as runner_routes, take_home

    reads: list[str] = []

    async def parse(request, *_models):
        reads.append(request.url.path)
        raise TypedError("invalid_request")

    monkeypatch.setattr(definition_runs, "parse", parse)
    app = FastAPI()
    errors.install(app)
    for module in (runner_routes, ai_coding, take_home):
        app.include_router(module.router)
    for module in (ai_coding, take_home):
        app.dependency_overrides[module._auth_user] = lambda: {"id": A, "token": "test-token"}

    def use(value: str) -> TestClient:
        env = {**ON, "ROUNDS_GATE_EXECUTION_SCRATCH": value, "ROUNDS_GATE_EXECUTION_GRADING": value}
        monkeypatch.setattr(gates, "_snapshot", gates.load(env, gates.RUNNER))
        return TestClient(app)

    return use, reads


@pytest.mark.parametrize("value", ["off", "legacy"])
@pytest.mark.parametrize("path", sorted(ROUTE_OFF))
def test_each_route_refuses_below_on_by_itself_before_it_reads_its_body(unadmitted, path, value):
    use, reads = unadmitted
    out = typed(use(value).post(path, json={"definition": TWO_SUM_REF}), 503, "execution_disabled")
    assert out["detail"] == ROUTE_OFF[path] and reads == []


@pytest.mark.parametrize("path", sorted(ROUTE_OFF))
def test_each_route_reads_its_body_once_its_key_is_on(unadmitted, path):
    use, reads = unadmitted
    typed(use("on").post(path, json={"definition": TWO_SUM_REF}), 422, "invalid_request")
    assert reads == [path]


def test_the_defaults_run_each_scratch_route_as_a_job(runner, node):
    # Neither the store nor the key is set: both start on.
    client = runner({**ENFORCED, "ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "enforce", "ROUNDS_GATE_ENFORCE_QUOTA": "enforce"})
    out = submitted(client.post("/api/run", json=RUN, headers=headers(node, key=new_key())))
    assert settled(client, node, out["job_id"])["state"] == "completed"
    assert len(node.dump()["jobs"]) == 1


@pytest.mark.parametrize(
    "missing, start",
    [
        ("EXECUTION_STORE=on", {"env": {**ON, "ROUNDS_GATE_EXECUTION_STORE": "off"}}),
        ("EXECUTION_DEFINITIONS=enforce", {"env": {**ON, "ROUNDS_GATE_EXECUTION_DEFINITIONS": "legacy"}}),
        ("ROUNDS_EXECUTION_SECRET", {"secret": ""}),
        ("ROUNDS_ADMISSION_SECRET", {"runner_key": ""}),
    ],
)
def test_on_without_what_it_needs_acts_as_off(runner, node, capsys, missing, start):
    client = runner(ready=False, **start)
    lines = obs_lines(capsys)
    (line,) = [x for x in lines if x.get("event") == "execution.scratch"]
    assert line["needs"] == [missing] == keys.scratch_needs() and line["code"] == "acting_off"
    out = typed(client.post("/api/run", json=RUN, headers=headers(node, key=new_key())), 503, "execution_disabled")
    assert out["detail"] == "Running practice code is turned off on this server."
    state = node.dump()
    assert state["commands"] == [] and state["counters"] == [] and state["jobs"] == []
    if missing == "ROUNDS_EXECUTION_SECRET":
        # No worker starts, and the runner stays ready: only its code runs
        # are off.
        assert client.get("/ready").json() == {"status": "ok", "store": "unconfigured"}


def _queued_by_another_replica(node: Node, account: str = A) -> str:
    """A run admitted and enqueued the way another replica's request does
    it, with that replica's own admission secret."""
    key = new_key()
    source, inputs = jobs.digest(TWO_SUM), jobs.digest({"input": RUN["input"]})
    fingerprint = jobs.fingerprint("/api/run", TWO_SUM_REF, source, inputs)
    auth = {"Authorization": f"Bearer {node.token(account)}", "X-Rounds-Admission-Key": RUNNER_KEY}
    admit = node.http.post("/api/rounds/admission/admit", headers=auth, json={
        "operation": "run", "command_id": key, "fingerprint": fingerprint, "wall_seconds": 3,
        "idempotency": "enforce", "quota": "enforce", "lease_hash": "b" * 64})
    assert admit.status_code == 200 and admit.json()["leased"] is True, admit.text
    res = node.http.post("/api/rounds/execution/enqueue", headers=auth, json={
        "command_id": key, "kind": "run", "definition": TWO_SUM_REF, "fingerprint": fingerprint,
        "source_checksum": source, "input_digest": inputs, "input": {"code": TWO_SUM, "input": RUN["input"]}})
    assert res.status_code == 200, res.text
    return res.json()["job"]["id"]


def test_a_runner_without_the_admission_secret_runs_a_job_another_replica_queued(runner, node):
    client = runner(runner_key="")
    # Its own routes act as off, as above.
    typed(client.post("/api/run", json=RUN, headers=headers(node, key=new_key())), 503, "execution_disabled")
    job_id = _queued_by_another_replica(node)

    def job():
        (found,) = [j for j in node.dump()["jobs"] if j["id"] == job_id]
        return found

    _until(lambda: kinds.is_terminal(job()["state"]), what="the job's end")
    assert (job()["state"], job()["outcome_class"]) == ("completed", "passed")


def test_a_run_is_a_job_answered_202_that_ends_with_its_envelope(runner, node, pocketbase, capsys):
    client = runner()
    assert not [x for x in obs_lines(capsys) if x.get("event") == "execution.scratch"]
    key = new_key()
    first = submitted(client.post("/api/run", json=RUN, headers=headers(node, key=key)))
    assert (first["state"], first["outcome_class"], first["envelope"]) == ("queued", None, None)
    assert first["retryable"] is False and first["cancel_requested"] is False
    done = settled(client, node, first["job_id"])
    assert (done["state"], done["outcome_class"], done["retryable"]) == ("completed", "passed", False)
    env = done["envelope"]
    assert env["job_id"] == first["job_id"] and env["authoritative"] is True and env["score"] is None
    assert env["parts"] == [{"id": "run", "outcome_class": "passed", "limit": None}]
    assert env["output"]["return_value"] == [0, 1] and env["output"]["definition"]["slug"] == "two-sum"
    assert env["definition"]["checksum"].startswith("sha256:") and env["cleanup"] == "confirmed"
    # One request and the run's three seconds, and no record read.
    assert node.charged() == (1, 3)
    assert pocketbase.calls == []


def test_a_duplicate_answers_its_job_as_it_is_and_charges_nothing_more(runner, node):
    client = runner()
    key = new_key()
    first = submitted(client.post("/api/run", json=RUN, headers=headers(node, key=key)))
    again = submitted(client.post("/api/run", json=RUN, headers=headers(node, key=key)))
    assert again["job_id"] == first["job_id"]
    done = settled(client, node, first["job_id"])
    late = submitted(client.post("/api/run", json=RUN, headers=headers(node, key=key)))
    assert late == done
    assert node.charged() == (1, 3)
    assert len(node.dump()["jobs"]) == 1


def test_the_same_key_for_other_work_is_a_mismatch_and_runs_nothing(runner, node):
    client = runner()
    key = new_key()
    submitted(client.post("/api/run", json=RUN, headers=headers(node, key=key)))
    other = {**RUN, "input": {"nums": [3, 4], "target": 7}}
    typed(client.post("/api/run", json=other, headers=headers(node, key=key)), 409, "idempotency_mismatch")
    typed(client.post("/api/evaluate", json=EVALUATE, headers=headers(node, key=key)), 409, "idempotency_mismatch")
    assert len(node.dump()["jobs"]) == 1 and node.charged() == (1, 3)


def test_a_job_route_needs_a_key_whatever_idempotency_enforces(runner, node):
    client = runner({**ON, "ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "observe"})
    typed(client.post("/api/run", json=RUN, headers=headers(node)), 400, "idempotency_key_required")
    bad = {**headers(node), "Idempotency-Key": "not-a-uuid"}
    typed(client.post("/api/run", json=RUN, headers=bad), 400, "idempotency_key_required")
    state = node.dump()
    assert state["commands"] == [] and state["counters"] == [] and state["jobs"] == []


def test_a_worker_that_cant_log_in_takes_no_job_and_charges_nothing(runner, node):
    client = runner(secret="test-wrong-execution-key-placeholder-0123", ready=False)
    assert client.get("/ready").status_code == 503
    typed(client.post("/api/run", json=RUN, headers=headers(node, key=new_key())), 503, "worker_unavailable")
    state = node.dump()
    assert state["commands"] == [] and state["counters"] == [] and state["jobs"] == []


def test_another_accounts_job_is_the_same_404_as_an_unknown_one(runner, node):
    client = runner()
    mine = submitted(client.post("/api/run", json=RUN, headers=headers(node, key=new_key())))["job_id"]
    seen = []
    for job_id in (mine, "zzzzzzzzzzzzzzz", "not-a-job-id"):
        for res in (client.get(f"/api/execution/jobs/{job_id}", headers=headers(node, B)),
                    client.get(f"/api/execution/jobs/{job_id}?wait=1", headers=headers(node, B)),
                    client.post(f"/api/execution/jobs/{job_id}/cancel", headers=headers(node, B))):
            out = typed(res, 404, "not_found")
            seen.append({k: v for k, v in out.items() if k != "correlation_id"})
    assert all(s == seen[0] for s in seen)
    done = settled(client, node, mine)
    assert done["cancel_requested"] is False and done["state"] == "completed"


def test_a_job_read_needs_the_bearer_and_waits_at_most_20_seconds(runner, node):
    client = runner()
    job_id = submitted(client.post("/api/run", json=RUN, headers=headers(node, key=new_key())))["job_id"]
    typed(client.get(f"/api/execution/jobs/{job_id}"), 401, "unauthenticated")
    typed(client.post(f"/api/execution/jobs/{job_id}/cancel"), 401, "unauthenticated")
    for wait in ("21", "-1", "x", "1.5"):
        typed(client.get(f"/api/execution/jobs/{job_id}?wait={wait}", headers=headers(node)), 422, "invalid_request")
    settled(client, node, job_id)
    node.switch(False)
    typed(client.get(f"/api/execution/jobs/{job_id}", headers=headers(node)), 503, "worker_unavailable")


def test_a_cancel_stops_a_running_job_and_asking_again_changes_nothing(runner, node):
    client = runner()
    job_id = submitted(client.post("/api/run", json=run_body(SLEEPER), headers=headers(node, key=new_key())))["job_id"]
    _until(lambda: any(j["id"] == job_id and j["state"] == "started" for j in node.dump()["jobs"]), what="a start")
    asked = client.post(f"/api/execution/jobs/{job_id}/cancel", headers=headers(node))
    assert asked.status_code == 200 and asked.json()["cancel_requested"] is True
    done = settled(client, node, job_id, timeout=10)
    assert (done["state"], done["outcome_class"], done["retryable"]) == ("canceled", "canceled", False)
    again = client.post(f"/api/execution/jobs/{job_id}/cancel", headers=headers(node))
    assert again.status_code == 200 and again.json() == done
    # It started, so its charge stays.
    assert node.charged() == (1, 3)


def test_a_queued_job_cancels_at_once_and_gets_its_charge_back(runner, node):
    client = runner()
    # Two jobs an account runs at once; a third waits in the queue.
    running = [submitted(client.post("/api/run", json=run_body(SLEEPER), headers=headers(node, key=new_key())))
               for _ in range(2)]
    _until(lambda: sum(j["state"] == "started" for j in node.dump()["jobs"]) == 2, what="two starts")
    queued = submitted(client.post("/api/run", json=run_body(SLEEPER), headers=headers(node, key=new_key())))
    assert node.charged() == (3, 9)
    asked = client.post(f"/api/execution/jobs/{queued['job_id']}/cancel", headers=headers(node))
    assert asked.status_code == 200
    assert (asked.json()["state"], asked.json()["outcome_class"]) == ("canceled", "canceled")
    assert node.charged() == (3, 6)
    for job in running:
        client.post(f"/api/execution/jobs/{job['job_id']}/cancel", headers=headers(node))
        settled(client, node, job["job_id"], timeout=10)


def test_a_run_out_of_time_ends_timed_out_and_keeps_its_charge(runner, node):
    client = runner()
    job_id = submitted(client.post("/api/run", json=run_body(SPINNER), headers=headers(node, key=new_key())))["job_id"]
    done = settled(client, node, job_id)
    assert (done["state"], done["outcome_class"], done["retryable"]) == ("timed-out", "resource-limit", False)
    assert done["envelope"]["limit"] == "wall_time"
    assert done["envelope"]["parts"] == [{"id": "run", "outcome_class": "resource-limit", "limit": "wall_time"}]
    # What it printed before the limit isn't a result: no output.
    assert done["envelope"]["output"] is None
    assert node.charged() == (1, 3)


def test_a_test_run_out_of_time_shows_no_case_result(runner, node):
    client = runner()
    body = {"definition": TWO_SUM_REF, "code": SPINNER, "case_ids": ["c000"]}
    job_id = submitted(client.post("/api/evaluate", json=body, headers=headers(node, key=new_key())))["job_id"]
    done = settled(client, node, job_id)
    assert (done["state"], done["outcome_class"]) == ("timed-out", "resource-limit")
    assert done["envelope"]["parts"] == [{"id": "c000", "outcome_class": "resource-limit", "limit": "wall_time"}]
    # The evaluate body would mark the case failed; the envelope keeps none of it.
    assert done["envelope"]["output"] is None and done["envelope"]["score"] is None
    assert node.charged() == (1, 3)


@pytest.mark.parametrize(
    "grade, ended",
    [("import sys\nsys.exit(0)\n", ("failed", "infrastructure-degraded")),
     ("import os\nos.write(3, b'not a result\\n')\n", ("denied", "definition-invalid"))],
    ids=["nothing-came-back", "malformed"],
)
def test_a_take_home_run_its_harness_didnt_score_shows_no_score(runner, node, tmp_path, monkeypatch, grade, ended):
    # The take-home body for such a channel scores 0 with every criterion
    # failed; nothing the candidate wrote earned that, so it isn't kept.
    client = runner()
    document = _take_home_document()
    document["files"] = [dict(f, contents=grade) if f["path"] == "harness/grade.py" else f for f in document["files"]]
    entry = {"kind": "harness-revision", "track": "take-home", "slug": "add-numbers-py", "variant": "python",
             "content_version": 1}
    monkeypatch.setattr(definitions, "_store", _store(tmp_path, [(entry, document, "active")]))
    body ={"definition": TAKE_HOME_REF, "files": {"solution.py": "def add(a, b):\n    return a + b\n"}}
    job_id = submitted(client.post("/api/take-home/run", json=body, headers=headers(node, key=new_key())))["job_id"]
    done = settled(client, node, job_id)
    assert (done["state"], done["outcome_class"]) == ended
    assert done["envelope"]["output"] is None and done["envelope"]["score"] is None


def test_a_retry_after_the_infrastructure_failed_runs_the_same_job_charged_no_request(runner, node, monkeypatch):
    client = runner()
    real, failures = handlers.RunHandler.execute, []

    def once(self, job, plan, slot, stop):
        if not failures:
            failures.append(job.id)
            raise RuntimeError("the slot broke")
        return real(self, job, plan, slot, stop)

    monkeypatch.setattr(handlers.RunHandler, "execute", once)
    key = new_key()
    job_id = submitted(client.post("/api/run", json=RUN, headers=headers(node, key=key)))["job_id"]
    lost = settled(client, node, job_id)
    assert (lost["state"], lost["outcome_class"], lost["retryable"]) == ("failed", "infrastructure-degraded", True)
    again = submitted(client.post("/api/run", json=RUN, headers=headers(node, key=key)))
    assert again["job_id"] == job_id and again["state"] == "queued"
    done = settled(client, node, job_id)
    assert (done["state"], done["outcome_class"]) == ("completed", "passed")
    # The retry pays its wall seconds, never a second request.
    assert node.charged() == (1, 6)


def test_evaluate_runs_the_cases_it_selects_as_one_job(runner, node):
    client = runner()
    job_id = submitted(client.post("/api/evaluate", json=EVALUATE, headers=headers(node, key=new_key())))["job_id"]
    done = settled(client, node, job_id)
    assert (done["state"], done["outcome_class"]) == ("completed", "passed")
    assert [p["id"] for p in done["envelope"]["parts"]] == ["c000", "c001", "c002"]
    assert (done["envelope"]["output"]["passed"], done["envelope"]["output"]["failed"]) == (3, 0)
    # Charged each selected case's time class.
    assert node.charged() == (1, 9)


def test_evaluate_with_nothing_selected_is_refused_and_charges_no_seconds(runner, node):
    client = runner()
    body = {**EVALUATE, "tags": ["no-such-tag"]}
    typed(client.post("/api/evaluate", json=body, headers=headers(node, key=new_key())), 422, "invalid_request")
    assert node.dump()["jobs"] == [] and node.charged()[1] == 0


def test_a_project_run_is_a_job(runner, node):
    client = runner()
    files = {**starter("python"), **visible_tests("python")}
    body = {"definition": PROJECT_REF, "checkpoint": 0, "files": files}
    job_id = submitted(client.post("/api/ai-coding/run-project", json=body,
                                   headers=headers(node, key=new_key())))["job_id"]
    done = settled(client, node, job_id)
    assert done["state"] == "completed" and done["outcome_class"] in ("passed", "candidate-failure")
    out = done["envelope"]["output"]
    assert out["passed_count"] + out["failed_count"] >= 1 and out["definition"]["slug"] == PROJECT_REF["slug"]
    assert node.charged() == (1, 10)


def test_a_take_home_run_is_a_job_scored_from_its_channel(runner, node, tmp_path, monkeypatch):
    client = runner()
    entry = {"kind": "harness-revision", "track": "take-home", "slug": "add-numbers-py", "variant": "python",
             "content_version": 1}
    monkeypatch.setattr(definitions, "_store", _store(tmp_path, [(entry, _take_home_document(), "active")]))
    honest = {"definition": TAKE_HOME_REF, "files": {"solution.py": "def add(a, b):\n    return a + b\n"}}
    job_id = submitted(client.post("/api/take-home/run", json=honest, headers=headers(node, key=new_key())))["job_id"]
    done = settled(client, node, job_id)
    assert (done["state"], done["outcome_class"]) == ("completed", "passed")
    assert [p["id"] for p in done["envelope"]["parts"]] == ["adds_small", "adds_large"]
    assert done["envelope"]["output"]["score"] == 1.0 and done["envelope"]["score"] is None
    wrong = {"definition": TAKE_HOME_REF, "files": {"solution.py": "def add(a, b):\n    return 0\n"}}
    job_id = submitted(client.post("/api/take-home/run", json=wrong, headers=headers(node, key=new_key())))["job_id"]
    done = settled(client, node, job_id)
    assert (done["state"], done["outcome_class"]) == ("completed", "candidate-failure")


# ---- what the routes answered in their request until PR 4, as jobs ------------------


def _job(client: TestClient, node: Node, path: str, body: dict) -> dict:
    job_id = submitted(client.post(path, json=body, headers=headers(node, key=new_key())))["job_id"]
    return settled(client, node, job_id)


def _take_home_job(client: TestClient, node: Node, monkeypatch, tmp_path, solution: str, **extra: str) -> dict:
    entry = {"kind": "harness-revision", "track": "take-home", "slug": "add-numbers-py", "variant": "python",
             "content_version": 1}
    monkeypatch.setattr(definitions, "_store", _store(tmp_path, [(entry, _take_home_document(), "active")]))
    files = {"solution.py": solution, **extra}
    return _job(client, node, "/api/take-home/run", {"definition": TAKE_HOME_REF, "files": files})


def test_an_evaluate_job_runs_every_case_on_its_validators(runner, node):
    client = runner()
    done = _job(client, node, "/api/evaluate", {"definition": TWO_SUM_REF, "code": TWO_SUM})
    document = definitions.store().resolve("coding", "two-sum", "python", 1).document
    assert (done["state"], done["outcome_class"]) == ("completed", "passed")
    assert [p["id"] for p in done["envelope"]["parts"]] == [c["case_id"] for c in document["cases"]]
    out = done["envelope"]["output"]
    assert (out["passed"], out["failed"]) == (len(document["cases"]), 0)
    assert all(r["expected"] == {"$match": "validator"} for r in out["results"])


def test_a_case_that_raises_in_an_evaluate_job_never_reaches_its_validator(runner, node):
    # Otherwise a validator's own failure could hide what the code raised.
    client = runner()
    code = "def two_sum(nums, target):\n    raise ValueError('boom')\n"
    done = _job(client, node, "/api/evaluate", {"definition": TWO_SUM_REF, "code": code, "tags": ["basic"]})
    assert (done["state"], done["outcome_class"]) == ("completed", "candidate-failure")
    errors = [r["error"] or "" for r in done["envelope"]["output"]["results"]]
    assert errors and all("boom" in e and "Validator error" not in e for e in errors)


def test_an_evaluate_job_takes_case_ids_and_tags(runner, node):
    client = runner()
    base = {"definition": {**TWO_SUM_REF, "slug": "binary-search"}, "code": PYTHON_SEARCH}
    by_id = _job(client, node, "/api/evaluate", {**base, "case_ids": ["c001", "c000"]})
    assert [p["id"] for p in by_id["envelope"]["parts"]] == ["c000", "c001"]
    document = definitions.store().resolve("coding", "binary-search", "python", 1).document
    tagged = [c["case_id"] for c in document["cases"] if "basic" in c["tags"]]
    by_tag = _job(client, node, "/api/evaluate", {**base, "tags": ["basic"]})
    assert [p["id"] for p in by_tag["envelope"]["parts"]] == tagged
    assert by_tag["envelope"]["output"]["results"][0]["expected"] == document["cases"][0]["expected"]["literal"]


def test_the_javascript_variant_runs_its_own_definition_as_a_job(runner, node):
    client = runner()
    body = {"definition": {**TWO_SUM_REF, "slug": "binary-search", "variant": "javascript"}, "code": JS_SEARCH}
    done = _job(client, node, "/api/evaluate", body)
    assert (done["state"], done["outcome_class"]) == ("completed", "passed")
    assert done["envelope"]["output"]["definition"]["variant"] == "javascript"


# The class each criterion's outcome in a graded run's answer ends a part with.
PART_CLASS = {"passed": "passed", "failed": "candidate-failure", "not-run": "infrastructure-degraded"}


@pytest.mark.parametrize("name", sorted(FORGERIES))
def test_a_forged_take_home_result_fails_closed_as_a_job(runner, node, monkeypatch, tmp_path, name):
    client = runner()
    solution, expected = FORGERIES[name]
    done = _take_home_job(client, node, monkeypatch, tmp_path, solution)
    assert [(p["id"], p["outcome_class"]) for p in done["envelope"]["parts"]] == [
        (criterion, PART_CLASS[outcome]) for criterion, outcome, _reason in expected]
    assert done["outcome_class"] != "passed"
    out = done["envelope"]["output"]
    # A run whose grader reported nothing keeps no answer at all.
    if out is not None:
        assert [(o["id"], o["outcome"], o["reason"]) for o in out["outcomes"]] == expected
        assert out["passed"] is False and 0.0 <= out["score"] <= 1.0


def test_a_take_home_jobs_score_is_the_servers_weighting(runner, node, monkeypatch, tmp_path):
    client = runner()
    done = _take_home_job(client, node, monkeypatch, tmp_path, FORGERIES["out-of-range-score"][0])
    assert done["envelope"]["output"]["score"] == 0.5


def test_an_edited_visible_test_doesnt_change_a_take_home_jobs_grade(runner, node, monkeypatch, tmp_path):
    client = runner()
    done = _take_home_job(client, node, monkeypatch, tmp_path, "def add(a, b):\n    return 0\n",
                          **{"tests/test_solution.py": "def test_passes():\n    assert True\n"})
    assert (done["state"], done["outcome_class"]) == ("completed", "candidate-failure")
    assert done["envelope"]["output"]["passed"] is False


def test_a_take_home_job_that_prints_hidden_files_gets_none_back(runner, node, monkeypatch, tmp_path):
    client = runner()
    done = _take_home_job(client, node, monkeypatch, tmp_path, LEAKING)
    assert done["state"] == "completed"
    answer = json.dumps(done)
    assert HIDDEN_MARKER not in answer and "rounds_harness" not in answer


def test_nothing_the_candidate_wrote_or_printed_reaches_a_log(runner, node, capsys):
    client = runner()
    code = "# marker-in-source-5e1f\n" + TWO_SUM.replace("    seen = {}\n", "    seen = {}\n    print('marker-in-output-9a3c')\n")
    job_id = submitted(client.post("/api/run", json=run_body(code), headers=headers(node, key=new_key())))["job_id"]
    done = settled(client, node, job_id)
    assert "marker-in-output-9a3c" in done["envelope"]["output"]["stdout"]
    logged = capsys.readouterr()
    for marker in ("marker-in-source-5e1f", "marker-in-output-9a3c"):
        assert marker not in logged.out and marker not in logged.err


# ---- the harness's retry phase ------------------------------------------------------


def _scratch_probe():
    for extra in (ROOT / "harness", ROOT / "harness" / "probes"):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
    import scratch_check

    return scratch_check


def test_a_replica_that_isnt_listening_yet_reads_as_not_ready_until_the_deadline():
    probe = _scratch_probe()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    # Nothing listens on the port now, so the connection is refused.
    assert probe.ready(f"http://127.0.0.1:{port}") is False
    started = time.monotonic()
    assert probe.wait_ready(f"http://127.0.0.1:{port}", timeout_s=1.5) is False
    assert time.monotonic() - started >= 1.5


def test_a_replica_that_answers_ready_is_ready():
    probe = _scratch_probe()

    class Ready(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - the stdlib's name
            self.send_response(200 if self.path == "/ready" else 404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Ready)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert probe.wait_ready(f"http://127.0.0.1:{server.server_address[1]}", timeout_s=5) is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
