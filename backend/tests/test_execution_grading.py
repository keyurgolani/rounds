"""Grade and take-home submit as durable jobs, and their rubric review
(ROUNDS-00A-L03 PR 3).

The routes run end to end in this process, as test_execution_scratch.py
runs the scratch routes: the runner app with its admission and its worker,
and pocketbase/tests/execution_server.cjs serving pb_hooks/admission.js
and pb_hooks/execution.js on one in-memory store. The harness runs the same
routes through nginx on a real PocketBase with two replicas. The grading
key's values, the handlers' own checks, and the review routes' path match
are tested without that server.
"""
from __future__ import annotations

import json
import sys

import httpx
import pytest
from fastapi import HTTPException

from app import admission, definitions, execution as definition_runs, gates, harness_results
from execution import envelope, handlers, keys, kinds
from execution.worker import InvalidJob, Withdrawn
from tests.test_definitions_enforce import FIXED_CLIENT, FORGING_CLIENT, _project, _store, _take_home_document
from tests.test_execution_scratch import (  # noqa: F401  (node and runner are fixtures)
    ROOT,
    A,
    B,
    Node,
    headers,
    new_key,
    node,
    obs_lines,
    runner,
    settled,
    submitted,
    typed,
)

GRADING_ON = {
    "ROUNDS_GATE_EXECUTION_STORE": "on",
    "ROUNDS_GATE_EXECUTION_DEFINITIONS": "enforce",
    "ROUNDS_GATE_EXECUTION_GRADING": "on",
    "ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "enforce",
    "ROUNDS_GATE_ENFORCE_QUOTA": "enforce",
}
GRADE_REF = {"track": "ai-coding", "slug": "hallucinated-http-client", "variant": "python", "version": 1}
TAKE_HOME_REF = {"track": "take-home", "slug": "add-numbers-py", "variant": "python", "version": 1}
TAKE_HOME_ENTRY = {"kind": "harness-revision", "track": "take-home", "slug": "add-numbers-py", "variant": "python",
                   "content_version": 1}
SLEEPING_CLIENT = "import time\n\nINTERNAL_BASE_URL = ''\n\n\ndef fetch_user(user_id):\n    time.sleep(60)\n"
ADDS = "def add(a, b):\n    return a + b\n"
CAMPAIGN_A = "campaign0000001"
CAMPAIGN_B = "campaign0000002"


def grade_body(client_code: str = FIXED_CLIENT, **extra) -> dict:
    return {"definition": GRADE_REF, "files": _project(client_code), "ai_chats": [], **extra}


def submit_body(code: str = ADDS, **extra) -> dict:
    return {"definition": TAKE_HOME_REF, "files": {"solution.py": code}, "notes": "my notes",
            "ai_chats": [], **extra}


def seed_round(node: Node) -> str:
    return node.http.post("/__test/item", json={"collection": "ai_coding_rounds",
                                                 "slug": GRADE_REF["slug"]}).json()["id"]


def seed_assignment(node: Node) -> str:
    return node.http.post("/__test/item", json={"collection": "take_home_assignments",
                                                 "slug": TAKE_HOME_REF["slug"]}).json()["id"]


@pytest.fixture
def take_home_store(tmp_path, monkeypatch):
    """The test-only take-home harness: every seeded one is retired."""
    store = _store(tmp_path, [(TAKE_HOME_ENTRY, _take_home_document(), "active")])

    def use():
        monkeypatch.setattr(definitions, "_store", store)

    return use


def envelope_of(node: Node, job_id: str) -> dict:
    (found,) = [e for e in node.dump()["envelopes"] if e["job"] == job_id]
    return found


def graded_rows(node: Node, collection: str = "ai_coding_attempts") -> list[dict]:
    return node.dump()["graded"][collection]


def graded_row_of(node: Node, job_id: str) -> dict:
    env = envelope_of(node, job_id)
    (row,) = [r for r in graded_rows(node, env["graded_collection"]) if r["id"] == env["graded_row"]]
    return row


def graded(runner_client, node: Node, body: dict, account: str = A, path: str = "/api/ai-coding/grade") -> dict:
    job_id = submitted(runner_client.post(path, json=body, headers=headers(node, account, key=new_key())))["job_id"]
    return settled(runner_client, node, job_id, account=account, timeout=90)


class Provider:
    """The account's provider settings and its calls, faked: each call
    records the rubric state its envelope had when the call was made."""

    def __init__(self, node: Node, answer: str | Exception = '{"items": [], "total": 0.5}', missing=False):
        self.node, self.answer, self.missing = node, answer, missing
        self.calls: list[str | None] = []
        self.prompts: list[str] = []

    async def config(self, _user):
        if self.missing:
            raise HTTPException(status_code=400, detail="No text model configured.")
        return {"kind": "openai", "model": "m", "api_key": "test-key-placeholder", "base_url": ""}

    async def complete(self, *_args, messages, **_kwargs):
        states = [(e["user_view"].get("rubric") or {}).get("state") for e in self.node.dump()["envelopes"]]
        self.calls.append(states[-1] if states else None)
        self.prompts.append(messages[0]["content"])
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


@pytest.fixture
def provider(node, monkeypatch):
    def use(**kwargs) -> Provider:
        fake = Provider(node, **kwargs)
        monkeypatch.setattr("routers.ai._active_text_config", fake.config)
        monkeypatch.setattr("routers.ai._call_complete", fake.complete)
        return fake

    return use


def review(client, node: Node, job_id: str, files: dict, account: str = A, key: str | None = None,
           path: str = "/api/ai-coding/grade/{}/review"):
    return client.post(path.format(job_id), json={"files": files}, headers=headers(node, account, key=key or new_key()))


# ---- the grading key ----------------------------------------------------------------


@pytest.mark.parametrize(
    "env, effective",
    [
        # The defaults: the store and the key are on, definitions aren't
        # enforced.
        ({}, "off"),
        ({"ROUNDS_GATE_EXECUTION_DEFINITIONS": "enforce"}, "on"),
        ({"ROUNDS_GATE_EXECUTION_GRADING": "off", "ROUNDS_GATE_EXECUTION_DEFINITIONS": "enforce"}, "off"),
        ({"ROUNDS_GATE_EXECUTION_STORE": "off", "ROUNDS_GATE_EXECUTION_DEFINITIONS": "enforce"}, "off"),
        (GRADING_ON, "on"),
        # legacy graded in the request until PR 4; it acts as off.
        ({**GRADING_ON, "ROUNDS_GATE_EXECUTION_GRADING": "legacy"}, "off"),
        ({**GRADING_ON, "ROUNDS_GATE_EXECUTION_GRADING": "yes"}, "off"),
    ],
)
def test_the_grading_key_is_on_only_with_the_store_on_and_definitions_enforced(job_secrets, monkeypatch, env,
                                                                                effective):
    monkeypatch.setattr(gates, "_snapshot", gates.load(env, gates.RUNNER))
    assert keys.grading() == effective
    assert keys.for_operation("grade") == keys.for_operation("take_home_submit") == keys.for_operation("review")
    # The scratch key is a key of its own.
    assert keys.scratch() == ("on" if env.get("ROUNDS_GATE_EXECUTION_DEFINITIONS") == "enforce"
                              and env.get("ROUNDS_GATE_EXECUTION_STORE") != "off" else "off")


@pytest.mark.parametrize("unset", ["ROUNDS_EXECUTION_SECRET", "ROUNDS_ADMISSION_SECRET"])
def test_the_grading_key_also_needs_both_secrets_on_this_runner(job_secrets, monkeypatch, unset):
    monkeypatch.setattr(gates, "_snapshot", gates.load(GRADING_ON, gates.RUNNER))
    monkeypatch.delenv(unset)
    assert keys.grading() == "off" and keys.grading_needs() == [unset]


def test_grading_on_without_what_it_needs_says_so_once_at_start(job_secrets, monkeypatch, capsys):
    monkeypatch.setattr(gates, "_snapshot", gates.load({"ROUNDS_GATE_EXECUTION_STORE": "off"}, gates.RUNNER))
    monkeypatch.delenv("ROUNDS_ADMISSION_SECRET")
    keys.log_startup()
    (line,) = [l for l in obs_lines(capsys) if l["event"] == "execution.grading"]
    assert line == {"v": "obs/v1", "event": "execution.grading", "code": "acting_off",
                    "needs": ["EXECUTION_STORE=on", "EXECUTION_DEFINITIONS=enforce", "ROUNDS_ADMISSION_SECRET"],
                    "service": "runner"}


def test_grading_legacy_says_once_at_start_that_it_acts_as_off(job_secrets, monkeypatch, capsys):
    monkeypatch.setattr(gates, "_snapshot", gates.load({**GRADING_ON, "ROUNDS_GATE_EXECUTION_GRADING": "legacy"},
                                                       gates.RUNNER))
    keys.log_startup()
    (line,) = [l for l in obs_lines(capsys) if l["event"] == "execution.grading"]
    assert line == {"v": "obs/v1", "event": "execution.grading", "code": "legacy_retired", "service": "runner"}


@pytest.fixture
def grading_on(job_secrets, monkeypatch):
    monkeypatch.setattr(gates, "_snapshot", gates.load(GRADING_ON, gates.RUNNER))
    monkeypatch.setattr(definitions, "_store", definitions.Store().load())


class _Job:
    def __init__(self, kind: str, definition: dict, job_input: dict, job_id: str = "job000000000001") -> None:
        self.id, self.kind, self.definition, self.input = job_id, kind, definition, job_input


@pytest.mark.parametrize("value", ["legacy", "off"])
def test_a_grading_job_claimed_while_its_key_isnt_on_is_withdrawn(job_secrets, monkeypatch, value):
    monkeypatch.setattr(gates, "_snapshot", gates.load({**GRADING_ON, "ROUNDS_GATE_EXECUTION_GRADING": value},
                                                       gates.RUNNER))
    for kind in ("grade", "take_home_submit"):
        with pytest.raises(Withdrawn):
            handlers.GRADING_HANDLERS[kind].prepare(_Job(kind, GRADE_REF, {"files": {}}))


@pytest.mark.parametrize(
    "kind, definition, job_input",
    [
        ("grade", GRADE_REF, {"files": {}, "test_command": "x"}),
        ("grade", {**GRADE_REF, "version": 99}, {"files": {}}),
        ("grade", {**GRADE_REF, "slug": "word-count-py"}, {"files": {}}),
        ("grade", TAKE_HOME_REF, {"files": {}}),
        ("grade", GRADE_REF, {"files": {"harness/grade.py": "x"}}),
        ("take_home_submit", {**TAKE_HOME_REF, "slug": "kv-store-py"}, {"files": {}}),
    ],
)
def test_a_grading_job_its_handler_cant_run_is_invalid_before_anything_starts(grading_on, kind, definition,
                                                                               job_input):
    with pytest.raises(InvalidJob):
        handlers.GRADING_HANDLERS[kind].prepare(_Job(kind, definition, job_input))


def test_a_grade_declares_one_checkpoint_budget_per_checkpoint(grading_on):
    handler = handlers.GRADING_HANDLERS["grade"]
    job = _Job("grade", GRADE_REF, {"files": _project(FIXED_CLIENT)}, "job000000000555")
    handler.prepare(job)
    checkpoints = len(handler.plan(job).extra["checkpoints"])
    assert handler.budget_s(job) == 45 * checkpoints
    assert kinds.KINDS["grade"].max_budget_s == 45 * 8
    assert handlers.GRADING_HANDLERS["take_home_submit"].budget_s(job) == 120


def test_a_checkpoint_folds_its_results_into_one_class():
    parts = [envelope.Part("a", "passed"), envelope.Part("b", "resource-limit", "wall_time")]
    assert envelope.fold("checkpoint-0", parts) == envelope.Part("checkpoint-0", "resource-limit", "wall_time")
    assert envelope.fold("checkpoint-1", [envelope.Part("a", "passed")]).outcome_class == "passed"
    failed = [envelope.Part("a", "passed"), envelope.Part("b", "candidate-failure")]
    assert envelope.fold("checkpoint-2", failed).outcome_class == "candidate-failure"
    broken = [envelope.Part("a", "definition-invalid"), envelope.Part("b", "passed")]
    assert envelope.fold("checkpoint-3", broken).outcome_class == "definition-invalid"


# ---- the review routes' paths ---------------------------------------------------------


@pytest.mark.parametrize("path", ["/api/ai-coding/grade/{}/review", "/api/take-home/submit/{}/review"])
def test_a_review_route_matches_one_job_id_segment_and_nothing_wider(path):
    template = path.format("{job}")
    for segment in ("abc123def456ghi", "x", "UPPER", "a.b", "%7Bjob%7D"):
        assert admission.route_for("POST", path.format(segment)) == (template, admission.ROUTES[("POST", template)])
    wider = [
        path.format(""), path.format("a/b"), path.format("abc") + "/", path.format("abc") + "/x",
        "/x" + path.format("abc"), path.format("abc").replace("/review", "/reviews"),
        path.format("abc").replace("/api/", "/API/"),
    ]
    for candidate in wider:
        assert admission.route_for("POST", candidate) is None, candidate
    assert admission.route_for("GET", path.format("abc123def456ghi")) is None
    route = admission.ROUTES[("POST", template)]
    assert (route.operation, route.allocates) == ("review", False)


def test_the_app_router_serves_exactly_the_paths_admission_matches():
    from starlette.routing import Match

    from main import app

    def served(path: str) -> bool:
        scope = {"type": "http", "method": "POST", "path": path, "root_path": "", "query_string": b"",
                 "headers": []}
        return any(r.matches(scope)[0] == Match.FULL for r in app.router.routes)

    for path in ("/api/ai-coding/grade/{}/review", "/api/take-home/submit/{}/review"):
        for segment in ("abc123def456ghi", "x", "a/b", ""):
            assert served(path.format(segment)) == (admission.route_for("POST", path.format(segment)) is not None)


# ---- the routes' key values -----------------------------------------------------------


# legacy graded in the request until PR 4; now it answers as off.
@pytest.mark.parametrize("value", ["off", "legacy"])
@pytest.mark.parametrize("path, body", [
    ("/api/ai-coding/grade", grade_body()),
    ("/api/take-home/submit", submit_body()),
    ("/api/ai-coding/grade/job000000000001/review", {"files": {}}),
    ("/api/take-home/submit/job000000000001/review", {"files": {}}),
])
def test_off_answers_503_before_anything_and_keeps_every_draft(runner, node, path, body, value):
    client = runner({**GRADING_ON, "ROUNDS_GATE_EXECUTION_GRADING": value}, ready=False)
    # No bearer at all: the key answers before the account is looked up.
    res = client.post(path, json=body, headers={"Idempotency-Key": new_key()})
    typed(res, 503, "execution_disabled")
    assert "turned off" in res.json()["detail"]
    dump = node.dump()
    assert dump["jobs"] == [] and dump["commands"] == [] and dump["counters"] == []


def test_the_defaults_grade_as_a_job_whose_row_the_server_writes(runner, node):
    # Neither the store nor the key is set: both start on.
    client = runner({"ROUNDS_GATE_EXECUTION_DEFINITIONS": "enforce", "ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "enforce",
                     "ROUNDS_GATE_ENFORCE_QUOTA": "enforce"})
    seed_round(node)
    done = graded(client, node, grade_body())
    assert (done["state"], done["outcome_class"]) == ("completed", "passed")
    row = graded_row_of(node, done["job_id"])
    assert row["status"] == "graded" and row["envelope"] == envelope_of(node, done["job_id"])["id"]


@pytest.mark.parametrize(
    "missing, start",
    [
        ("ROUNDS_GATE_EXECUTION_STORE", {"env": {k: v for k, v in GRADING_ON.items()
                                                 if k != "ROUNDS_GATE_EXECUTION_STORE"} | {
                                                     "ROUNDS_GATE_EXECUTION_STORE": "off"}}),
        ("ROUNDS_GATE_EXECUTION_DEFINITIONS", {"env": {k: v for k, v in GRADING_ON.items()
                                                       if k != "ROUNDS_GATE_EXECUTION_DEFINITIONS"}}),
        ("ROUNDS_EXECUTION_SECRET", {"env": GRADING_ON, "secret": ""}),
        ("ROUNDS_ADMISSION_SECRET", {"env": GRADING_ON, "runner_key": ""}),
    ],
)
def test_on_without_what_it_needs_acts_as_off(runner, node, missing, start):
    client = runner(ready=False, **start)
    res = client.post("/api/ai-coding/grade", json=grade_body(), headers=headers(node, key=new_key()))
    typed(res, 503, "execution_disabled")
    assert "turned off" in res.json()["detail"]
    dump = node.dump()
    assert dump["jobs"] == [] and dump["commands"] == [] and dump["counters"] == []


@pytest.mark.parametrize("path", ["/api/ai-coding/grade/{}/review", "/api/take-home/submit/{}/review"])
def test_a_review_is_served_only_while_grading_runs_as_jobs(runner, node, path):
    client = runner({**GRADING_ON, "ROUNDS_GATE_EXECUTION_GRADING": "legacy"})
    typed(review(client, node, "job000000000001", {}, path=path), 503, "execution_disabled")


# ---- a grade as a job ------------------------------------------------------------------


def test_a_grade_is_a_job_whose_graded_row_the_server_writes_with_its_result(runner, node):
    client = runner(GRADING_ON)
    round_id = seed_round(node)
    node.http.post("/__test/campaign", json={"id": CAMPAIGN_A, "user": A})
    chats = [{"checkpoint": 0, "role": "user", "content": "why", "ts": 1}]
    body = grade_body(ai_chats=chats, campaign_id=CAMPAIGN_A, duration_ms=1234)
    done = graded(client, node, body)
    assert (done["state"], done["outcome_class"], done["retryable"]) == ("completed", "passed", False)
    env = done["envelope"]
    assert env["authoritative"] is True and env["score"] == 1.0 and env["output"] is None
    assert env["parts"] == [{"id": "checkpoint-0", "outcome_class": "passed", "limit": None}]
    assert env["rubric"] is None and env["definition"]["slug"] == GRADE_REF["slug"]
    row = graded_row_of(node, done["job_id"])
    stored = envelope_of(node, done["job_id"])
    assert row["envelope"] == stored["id"] and stored["graded_collection"] == "ai_coding_attempts"
    assert (row["user"], row["round"], row["campaign"], row["status"]) == (A, round_id, CAMPAIGN_A, "graded")
    assert (row["duration_ms"], row["ai_chats"], row["rubric_review"]) == (1234, chats, None)
    (checkpoint,) = row["test_results"]
    assert (checkpoint["outcome_class"], checkpoint["passed"], checkpoint["score"]) == ("passed", True, 1.0)
    assert checkpoint["outcomes"] == [{"id": "fetch_user_against_real_server", "outcome": "passed", "reason": "ok"}]
    (attempt,) = [a for a in node.dump()["attempts"] if a["job"] == done["job_id"]]
    assert attempt["operator_view"]["graded_row"] == row["id"]
    # One checkpoint's budget, declared at the start; the charge is final.
    assert attempt["budget_s"] == 45
    assert node.charged() == (1, 45)


def test_a_failing_solution_is_an_authoritative_failure_with_its_row(runner, node):
    client = runner(GRADING_ON)
    seed_round(node)
    done = graded(client, node, grade_body(FORGING_CLIENT))
    assert (done["state"], done["outcome_class"]) == ("completed", "candidate-failure")
    assert done["envelope"]["score"] == 0.0
    (checkpoint,) = graded_row_of(node, done["job_id"])["test_results"]
    assert (checkpoint["passed"], checkpoint["score"]) == (False, 0.0)
    # Nothing the forged client printed or read reaches the row.
    assert "ThreadingHTTPServer" not in json.dumps(graded_rows(node))


def test_a_grade_out_of_time_is_a_limit_with_no_score_and_keeps_its_charge(runner, node, monkeypatch):
    monkeypatch.setattr(kinds, "part_wall_s", lambda name: 2)
    client = runner(GRADING_ON)
    seed_round(node)
    done = graded(client, node, grade_body(SLEEPING_CLIENT))
    assert (done["state"], done["outcome_class"], done["retryable"]) == ("timed-out", "resource-limit", False)
    env = done["envelope"]
    assert env["authoritative"] is True and env["limit"] == "wall_time" and env["score"] is None
    (checkpoint,) = graded_row_of(node, done["job_id"])["test_results"]
    assert (checkpoint["outcome_class"], checkpoint["limit"]) == ("resource-limit", "wall_time")
    assert checkpoint["passed"] is None and checkpoint["score"] is None
    assert checkpoint["error"] == "This checkpoint ran out of time."
    assert node.charged() == (1, 45)


def _fake_grade(monkeypatch, channel: bytes, timed_out: bool = False, limit: str | None = None, before=None):
    def grade(checkpoint, _harness_files, _files, _slot, _wall_s=None, control=None):
        if before is not None:
            before()
        score = harness_results.score(channel, checkpoint["results"], checkpoint["min_executed"],
                                      missing_reason="timeout" if timed_out else "no-result")
        return definition_runs.Graded(score, timed_out, 5, limit)

    monkeypatch.setattr(handlers.definition_runs, "grade", grade)


THREE_STEP_SLUG = "three-step-client"
THREE_STEP_REF = {**GRADE_REF, "slug": THREE_STEP_SLUG}
PASSED_CHANNEL = b'{"id": "fetch_user_against_real_server", "outcome": "passed", "reason": "ok"}\n'


@pytest.fixture
def three_step_store(tmp_path, monkeypatch):
    """A test-only round with three checkpoints, made from the committed
    round's one: the same harness and result id at indexes 0, 1, and 2.
    Swapped in after the runner starts, which loads the committed store."""
    committed = json.loads((ROOT / "backend" / "definitions" / "store" / "ai-coding" / GRADE_REF["slug"]
                            / "python.v1.json").read_text())
    (checkpoint,) = committed["checkpoints"]
    document = {**committed, "slug": THREE_STEP_SLUG,
                "checkpoints": [{**checkpoint, "index": i, "label": f"Step {i + 1}"} for i in range(3)]}
    entry = {"kind": "harness-revision", "track": "ai-coding", "slug": THREE_STEP_SLUG, "variant": "python",
             "content_version": 1}
    store = _store(tmp_path, [(entry, document, "active")])

    def use():
        monkeypatch.setattr(definitions, "_store", store)

    return use


def test_a_grade_runs_its_checkpoints_in_order_and_a_limit_keeps_the_others_verdicts(runner, node, monkeypatch,
                                                                                     three_step_store):
    ran = []

    def grade(checkpoint, _harness_files, _files, _slot, wall_s=None, control=None):
        ran.append((checkpoint["index"], wall_s))
        limited = checkpoint["index"] == 1
        score = harness_results.score(b"" if limited else PASSED_CHANNEL, checkpoint["results"],
                                      checkpoint["min_executed"], missing_reason="timeout" if limited else "no-result")
        return definition_runs.Graded(score, limited, 5, None)

    monkeypatch.setattr(handlers.definition_runs, "grade", grade)
    client = runner(GRADING_ON)
    three_step_store()
    node.http.post("/__test/item", json={"collection": "ai_coding_rounds", "slug": THREE_STEP_SLUG})
    done = graded(client, node, {**grade_body(), "definition": THREE_STEP_REF})
    # In order, each held to its own 45 s.
    assert ran == [(0, 45), (1, 45), (2, 45)]
    assert (done["state"], done["outcome_class"]) == ("timed-out", "resource-limit")
    env = done["envelope"]
    assert (env["authoritative"], env["limit"], env["score"]) == (True, "wall_time", None)
    assert env["parts"] == [
        {"id": "checkpoint-0", "outcome_class": "passed", "limit": None},
        {"id": "checkpoint-1", "outcome_class": "resource-limit", "limit": "wall_time"},
        {"id": "checkpoint-2", "outcome_class": "passed", "limit": None},
    ]
    # The limit takes no verdict from the checkpoints around it.
    first, limited, last = graded_row_of(node, done["job_id"])["test_results"]
    assert (first["index"], first["passed"], first["score"]) == (0, True, 1.0)
    assert (limited["index"], limited["outcome_class"], limited["passed"], limited["score"]) == (
        1, "resource-limit", None, None)
    assert (last["index"], last["passed"], last["score"]) == (2, True, 1.0)
    # Three checkpoints' budget, declared at the start and charged.
    (attempt,) = [a for a in node.dump()["attempts"] if a["job"] == done["job_id"]]
    assert attempt["budget_s"] == 135
    assert node.charged() == (1, 135)


@pytest.mark.parametrize("limit", [name for name in kinds.LIMITS if name != "wall_time"])
def test_each_other_limit_is_a_limit_naming_it_with_a_row_and_no_score(runner, node, monkeypatch, limit):
    _fake_grade(monkeypatch, b"", limit=limit)
    client = runner(GRADING_ON)
    seed_round(node)
    done = graded(client, node, grade_body())
    assert (done["state"], done["outcome_class"]) == ("completed", "resource-limit")
    assert done["envelope"]["limit"] == limit and done["envelope"]["score"] is None
    (checkpoint,) = graded_row_of(node, done["job_id"])["test_results"]
    assert (checkpoint["limit"], checkpoint["passed"], checkpoint["score"]) == (limit, None, None)


@pytest.mark.parametrize(
    "channel, ended, retryable",
    [(b"not a result\n", ("denied", "definition-invalid"), False),
     (b"", ("failed", "infrastructure-degraded"), True)],
    ids=["malformed", "nothing-came-back"],
)
def test_a_grade_its_harness_didnt_score_writes_no_row_and_no_score(runner, node, monkeypatch, channel, ended,
                                                                    retryable):
    _fake_grade(monkeypatch, channel)
    client = runner(GRADING_ON)
    seed_round(node)
    done = graded(client, node, grade_body())
    assert (done["state"], done["outcome_class"], done["retryable"]) == (*ended, retryable)
    assert done["envelope"]["score"] is None and done["envelope"]["authoritative"] is False
    assert graded_rows(node) == []


# The two grading kinds, as the tests below run each: its route, its body,
# the page row its graded row points at, and a channel whose results pass.
GRADING_KINDS = {
    "grade": ("/api/ai-coding/grade", grade_body, "ai_coding_rounds", GRADE_REF["slug"], "ai_coding_attempts",
              PASSED_CHANNEL),
    "take_home_submit": ("/api/take-home/submit", submit_body, "take_home_assignments", TAKE_HOME_REF["slug"],
                         "take_home_attempts",
                         b'{"id": "adds_small", "outcome": "passed", "reason": "ok"}\n'
                         b'{"id": "adds_large", "outcome": "passed", "reason": "ok"}\n'),
}


@pytest.mark.parametrize("kind", sorted(GRADING_KINDS))
def test_a_result_whose_row_cant_be_written_ends_degraded_and_scores_nothing(runner, node, monkeypatch,
                                                                            take_home_store, kind):
    path, body, collection, slug, rows, channel = GRADING_KINDS[kind]

    def drop():
        httpx.post(f"{node.url}/__test/drop-item", json={"collection": collection, "slug": slug})

    _fake_grade(monkeypatch, channel, before=drop)
    client = runner(GRADING_ON)
    if kind == "take_home_submit":
        take_home_store()
    node.http.post("/__test/item", json={"collection": collection, "slug": slug})
    done = graded(client, node, body(), path=path)
    assert (done["state"], done["outcome_class"], done["retryable"]) == ("failed", "infrastructure-degraded", True)
    assert done["envelope"]["score"] is None and graded_rows(node, rows) == []


def test_a_round_without_its_own_row_is_refused_before_any_job(runner, node):
    client = runner(GRADING_ON)
    typed(client.post("/api/ai-coding/grade", json=grade_body(), headers=headers(node, key=new_key())),
          404, "not_found")
    assert node.dump()["jobs"] == [] and node.charged() == (1, 0)


@pytest.mark.parametrize("kind", sorted(GRADING_KINDS))
def test_another_accounts_campaign_is_refused_before_any_job(runner, node, take_home_store, kind):
    path, body, collection, slug, _rows, _channel = GRADING_KINDS[kind]
    client = runner(GRADING_ON)
    if kind == "take_home_submit":
        take_home_store()
    node.http.post("/__test/item", json={"collection": collection, "slug": slug})
    node.http.post("/__test/campaign", json={"id": CAMPAIGN_B, "user": B})
    res = client.post(path, json=body(campaign_id=CAMPAIGN_B), headers=headers(node, key=new_key()))
    typed(res, 404, "not_found")
    assert node.dump()["jobs"] == [] and node.charged() == (1, 0)


def test_a_duplicate_grade_answers_its_job_and_charges_nothing_more(runner, node):
    client = runner(GRADING_ON)
    seed_round(node)
    key = new_key()
    first = submitted(client.post("/api/ai-coding/grade", json=grade_body(), headers=headers(node, key=key)))
    again = submitted(client.post("/api/ai-coding/grade", json=grade_body(duration_ms=99),
                                  headers=headers(node, key=key)))
    assert again["job_id"] == first["job_id"]
    settled(client, node, first["job_id"])
    assert len(graded_rows(node)) == 1 and node.charged() == (1, 45)
    other = grade_body(FORGING_CLIENT)
    typed(client.post("/api/ai-coding/grade", json=other, headers=headers(node, key=key)), 409, "idempotency_mismatch")


def test_a_cancel_mid_grade_ends_canceled_with_no_row(runner, node):
    client = runner(GRADING_ON)
    seed_round(node)
    job_id = submitted(client.post("/api/ai-coding/grade", json=grade_body(SLEEPING_CLIENT),
                                   headers=headers(node, key=new_key())))["job_id"]
    for _ in range(100):
        state = client.get(f"/api/execution/jobs/{job_id}?wait=1", headers=headers(node)).json()["state"]
        if state == "started":
            break
    assert client.post(f"/api/execution/jobs/{job_id}/cancel", headers=headers(node)).status_code == 200
    done = settled(client, node, job_id)
    assert (done["state"], done["outcome_class"]) == ("canceled", "canceled")
    assert graded_rows(node) == []


# ---- a take-home submission as a job --------------------------------------------------


def test_a_submission_is_a_job_whose_graded_row_keeps_what_was_submitted(runner, node, take_home_store):
    client = runner(GRADING_ON)
    take_home_store()
    assignment = seed_assignment(node)
    node.http.post("/__test/campaign", json={"id": CAMPAIGN_A, "user": A})
    chats = [{"role": "user", "content": "hint?"}]
    done = graded(client, node, submit_body(ai_chats=chats, campaign_id=CAMPAIGN_A, duration_ms=500),
                  path="/api/take-home/submit")
    assert (done["state"], done["outcome_class"]) == ("completed", "passed")
    assert [p["id"] for p in done["envelope"]["parts"]] == ["adds_small", "adds_large"]
    assert done["envelope"]["score"] == 1.0 and done["envelope"]["output"] is None
    row = graded_row_of(node, done["job_id"])
    assert (row["user"], row["assignment"], row["campaign"], row["status"]) == (A, assignment, CAMPAIGN_A, "graded")
    assert row["files"] == {"solution.py": ADDS} and row["notes"] == "my notes"
    assert (row["ai_chats"], row["ai_assist_used"], row["duration_ms"]) == (chats, True, 500)
    out = row["harness_output"]
    assert (out["outcome_class"], out["score"], out["passed"]) == ("passed", 1.0, True)
    assert [c["passed"] for c in out["criteria"]] == [True, True]
    assert out["stdout"] == out["stderr"] == ""
    assert node.charged() == (1, 120)


def test_a_wrong_submission_is_a_failure_and_a_limited_one_scores_nothing(runner, node, take_home_store,
                                                                         monkeypatch):
    client = runner(GRADING_ON)
    take_home_store()
    seed_assignment(node)
    done = graded(client, node, submit_body("def add(a, b):\n    return 0\n"), path="/api/take-home/submit")
    assert (done["state"], done["outcome_class"]) == ("completed", "candidate-failure")
    assert graded_row_of(node, done["job_id"])["harness_output"]["passed"] is False
    _fake_grade(monkeypatch, b"", limit="memory")
    done = graded(client, node, submit_body(), path="/api/take-home/submit")
    assert (done["state"], done["outcome_class"]) == ("completed", "resource-limit")
    out = graded_row_of(node, done["job_id"])["harness_output"]
    assert (out["limit"], out["score"], out["passed"]) == ("memory", None, None)
    assert [c["passed"] for c in out["criteria"]] == [None, None]


def test_a_retired_take_home_answers_before_any_job(runner, node):
    client = runner(GRADING_ON)
    body = {**submit_body(), "definition": {**TAKE_HOME_REF, "slug": "kv-store-py"}}
    typed(client.post("/api/take-home/submit", json=body, headers=headers(node, key=new_key())),
          410, "definition_retired")
    assert node.dump()["jobs"] == []


# ---- the rubric review ----------------------------------------------------------------


def test_a_review_runs_once_per_result_marked_before_the_call_and_charged_once(runner, node, provider):
    client = runner(GRADING_ON)
    seed_round(node)
    fake = provider(answer='{"items": [{"id": "spotted_hallucination", "score": 0.8, "evidence": "e", '
                           '"suggestions": ["s"]}], "total": 0.8}')
    done = graded(client, node, grade_body())
    files = _project(FIXED_CLIENT)
    res = review(client, node, done["job_id"], files)
    assert res.status_code == 200, res.text
    answer = res.json()
    assert (answer["rubric_state"], answer["unavailable"]) == ("completed", None)
    assert answer["rubric_review"]["total"] == 0.8
    # The rubric read requested before the provider was called.
    assert fake.calls == ["requested"]
    assert "Spotted the hallucination" in fake.prompts[0]
    row = graded_row_of(node, done["job_id"])
    assert row["rubric_review"]["items"][0]["id"] == "spotted_hallucination"
    assert envelope_of(node, done["job_id"])["user_view"]["rubric"] == {"state": "completed"}
    again = review(client, node, done["job_id"], files)
    assert again.json()["rubric_state"] == "completed" and fake.calls == ["requested"]
    # The grade's one request and its 45 s, and the review's one request
    # and no seconds.
    assert node.charged() == (2, 45)
    status = client.get(f"/api/execution/jobs/{done['job_id']}", headers=headers(node)).json()
    assert status["envelope"]["rubric"] == {"state": "completed"}


def test_a_review_needs_the_files_that_ran(runner, node, provider):
    client = runner(GRADING_ON)
    seed_round(node)
    fake = provider()
    done = graded(client, node, grade_body())
    changed = review(client, node, done["job_id"], _project(FORGING_CLIENT)).json()
    assert (changed["rubric_state"], changed["unavailable"]) == (None, "files_changed")
    assert fake.calls == [] and node.charged() == (1, 45)
    assert envelope_of(node, done["job_id"])["user_view"]["rubric"] is None


def test_a_review_without_a_provider_charges_and_marks_nothing(runner, node, provider):
    client = runner(GRADING_ON)
    seed_round(node)
    fake = provider(missing=True)
    done = graded(client, node, grade_body())
    answer = review(client, node, done["job_id"], _project(FIXED_CLIENT)).json()
    assert (answer["rubric_state"], answer["unavailable"]) == (None, "no_provider")
    assert fake.calls == [] and node.charged() == (1, 45)
    assert envelope_of(node, done["job_id"])["user_view"]["rubric"] is None


def test_another_accounts_review_is_the_same_404_as_an_unknown_job(runner, node, provider):
    client = runner(GRADING_ON)
    seed_round(node)
    fake = provider()
    done = graded(client, node, grade_body())
    files = _project(FIXED_CLIENT)
    foreign = review(client, node, done["job_id"], files, account=B)
    unknown = review(client, node, "zzzzzzzzzzzzzzz", files)
    malformed = review(client, node, "not-an-id", files)
    other_kind = review(client, node, done["job_id"], files, path="/api/take-home/submit/{}/review")
    for res in (foreign, unknown, malformed, other_kind):
        assert res.status_code == 404 and res.json()["code"] == "not_found"
    assert fake.calls == [] and envelope_of(node, done["job_id"])["user_view"]["rubric"] is None
    assert node.charged(B) == (0, 0)


def test_a_provider_failure_completes_a_skipped_review_that_never_runs_again(runner, node, provider):
    client = runner(GRADING_ON)
    seed_round(node)
    fake = provider(answer=RuntimeError("provider said: secret-provider-text-41ab"))
    done = graded(client, node, grade_body())
    files = _project(FIXED_CLIENT)
    answer = review(client, node, done["job_id"], files).json()
    assert answer["rubric_state"] == "completed"
    assert answer["rubric_review"]["skipped"] is True and "secret-provider-text" not in json.dumps(answer)
    assert "secret-provider-text" not in json.dumps(graded_row_of(node, done["job_id"]))
    assert review(client, node, done["job_id"], files).json()["rubric_state"] == "completed"
    assert fake.calls == ["requested"]


def test_a_review_whose_call_outlived_its_lease_is_lost(runner, node, provider, monkeypatch):
    client = runner(GRADING_ON)
    seed_round(node)
    fake = provider()
    done = graded(client, node, grade_body())

    async def outlived(*args, **kwargs):
        # The call comes back after the review's lease ran out.
        out = await fake.complete(*args, **kwargs)
        node.http.post("/__test/advance", json={"seconds": 120})
        return out

    monkeypatch.setattr("routers.ai._call_complete", outlived)
    files = _project(FIXED_CLIENT)
    assert review(client, node, done["job_id"], files).json()["rubric_state"] == "lost"
    assert graded_row_of(node, done["job_id"])["rubric_review"] is None
    assert review(client, node, done["job_id"], files).json()["rubric_state"] == "lost"
    assert fake.calls == ["requested"]


def test_a_job_that_ended_with_no_result_isnt_reviewable(runner, node, provider, monkeypatch):
    _fake_grade(monkeypatch, b"")
    client = runner(GRADING_ON)
    seed_round(node)
    fake = provider()
    done = graded(client, node, grade_body())
    answer = review(client, node, done["job_id"], _project(FIXED_CLIENT)).json()
    assert (answer["rubric_state"], answer["unavailable"]) == (None, "not_reviewable")
    assert fake.calls == []


def test_a_submission_is_reviewed_on_its_own_route(runner, node, provider, take_home_store):
    client = runner(GRADING_ON)
    take_home_store()
    seed_assignment(node)
    fake = provider()
    done = graded(client, node, submit_body(), path="/api/take-home/submit")
    files = {"solution.py": ADDS}
    assert review(client, node, done["job_id"], files, path="/api/ai-coding/grade/{}/review").status_code == 404
    res = review(client, node, done["job_id"], files, path="/api/take-home/submit/{}/review")
    assert res.json()["rubric_state"] == "completed" and fake.calls == ["requested"]
    assert graded_row_of(node, done["job_id"])["rubric_review"]["total"] == 0.5


def test_a_review_needs_its_own_key(runner, node, provider):
    client = runner(GRADING_ON)
    seed_round(node)
    provider()
    done = graded(client, node, grade_body())
    res = client.post(f"/api/ai-coding/grade/{done['job_id']}/review", json={"files": {}},
                      headers={"Authorization": headers(node)["Authorization"]})
    typed(res, 400, "idempotency_key_required")


def test_nothing_the_candidate_wrote_or_the_provider_answered_reaches_a_log(runner, node, provider, capsys):
    client = runner(GRADING_ON)
    seed_round(node)
    provider(answer='{"items": [{"id": "x", "score": 1, "evidence": "provider-marker-77aa"}], "total": 1}')
    marked = FIXED_CLIENT + "\n# source-marker-3c9d\n"
    done = graded(client, node, grade_body(marked))
    review(client, node, done["job_id"], _project(marked))
    logged = capsys.readouterr()
    for marker in ("source-marker-3c9d", "provider-marker-77aa"):
        assert marker not in logged.out and marker not in logged.err
    lines = [json.loads(l) for l in logged.out.splitlines() if l.startswith('{"') and '"execution.review"' in l]
    assert {line["code"] for line in lines} >= {"requested", "completed"}


# ---- the harness's grading phase ----------------------------------------------------


def _grading_probe():
    for extra in (ROOT / "harness", ROOT / "harness" / "probes"):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
    import grading_check

    return grading_check


def test_the_harness_grading_phase_grades_what_these_tests_grade_and_proves_its_case():
    probe = _grading_probe()
    assert set(probe.PHASES) == {"execution-grading"}
    assert probe.GRADE == GRADE_REF and probe.FIXED_CLIENT == FIXED_CLIENT
    assert probe.GATES == {"EXECUTION_STORE": "on", "EXECUTION_GRADING": "on", "EXECUTION_DEFINITIONS": "enforce"}
    cases = json.loads((ROOT / "docs" / "security" / "account-scope.v1.json").read_text())["cases"]
    case = cases["isolation.execution-review.foreign"]
    assert (case["surface"], case["status"], case["evidence"]) == (
        "runner:execution-review", "pass", ["isolation.execution-review.foreign"])
