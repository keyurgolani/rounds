"""Admission steps 6 and 7 at the runner (ROUNDS-00A-L01 stage 3).

Each allocating route calls the store once its body is parsed and before
any lookup: steps 1 to 5 never reach it, a completed command replays its
stored response without running anything or calling a provider, refused
and over-limit requests are denied only when their gate enforces, and the
end of every leased request is recorded (completed, denied, an
infrastructure failure, or another error). The store here is conftest's
in-memory FakeAdmissionStore; pocketbase/tests/test_admission_hooks.py
covers the hook's decisions, and the harness runs both together."""
from __future__ import annotations

import asyncio
import collections
import json
import shutil
import subprocess
import urllib.error
from pathlib import Path

import httpx
import pytest

from app import admission, admission_state, errors, limits
from conftest import TEST_TOKEN
from tests.test_admission import (  # noqa: F401  (fixtures)
    ALLOCATING,
    ROUTES,
    Tripped,
    _assert_typed,
    _decisions,
    _send,
    busy,
    gate_env,
    seeded,
    tripwires,
)

ROOT = Path(__file__).resolve().parents[2]
KEY = "0190f000-0000-7000-8000-000000000001"
OTHER_KEY = "0190f000-0000-7000-8000-000000000002"
# What each route charges at admission: one request plus the longest its
# execution can run, or one case or checkpoint for evaluate and grade.
FIRST_CHARGE = {
    "run": 3,
    "evaluate": 3,
    "run_project": 10,
    "grade": 45,
    "take_home_run": 60,
    "take_home_submit": 120,
    "pdf_render": 25,
}
JSON_ROUTES = [name for name in ALLOCATING if name != "pdf_render"]
WITH_LOOKUPS = ("run", "evaluate", "run_project", "grade", "take_home_run", "take_home_submit")
ENFORCE = {"ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "enforce", "ROUNDS_GATE_ENFORCE_QUOTA": "enforce"}
PDF = b"%PDF-1.4 rendered"


def keyed(headers: dict, key: str = KEY) -> dict:
    return {**headers, "Idempotency-Key": key}


def operation(name: str) -> str:
    method, path, _body, _over = ROUTES[name]
    return admission.ROUTES[(method, path)].operation


@pytest.fixture
def enforcing(gate_env):
    gate_env(ENFORCE)


class _Rendered:
    status = 200
    headers = {"Content-Type": "application/pdf"}

    def read(self) -> bytes:
        return PDF

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None


@pytest.fixture
def succeeding(monkeypatch):
    """Every execution, render, provider config, and attempt write, faked
    and counted."""
    from ai_coding.project_runner import ProjectRunResult
    from routers import ai_coding, pdf, runner, take_home
    from runner import ExecutionOutcome
    from take_home.runner import TakeHomeRunResult

    counts: collections.Counter = collections.Counter()

    def run_one(*_args, **_kwargs):
        counts["run_one"] += 1
        return ExecutionOutcome(stdout="out", stderr="", return_value=None, error=None, duration_ms=1, truncated=False)

    def run_project(*_args, **_kwargs):
        counts["run_project"] += 1
        return ProjectRunResult(True, 1, 0, "ok", "", None, 1)

    def run_assignment(*_args, **_kwargs):
        counts["run_assignment"] += 1
        return TakeHomeRunResult(score=1.0, stdout="ok")

    async def provider_config(_user):
        counts["provider"] += 1
        raise RuntimeError("no provider in tests")

    async def pb_post(_token, _path, _payload):
        counts["attempt_rows"] += 1
        return {"id": "a" * 15}

    def urlopen(_request, timeout=None):
        counts["render"] += 1
        return _Rendered()

    monkeypatch.setattr(runner, "run_one", run_one)
    monkeypatch.setattr(ai_coding, "run_project", run_project)
    monkeypatch.setattr(take_home, "run_assignment", run_assignment)
    monkeypatch.setattr(ai_coding, "_active_text_config", provider_config)
    monkeypatch.setattr(take_home, "_active_text_config", provider_config)
    monkeypatch.setattr(take_home, "pb_post", pb_post)
    monkeypatch.setattr(pdf.urllib.request, "urlopen", urlopen)
    return counts


# ---- where steps 6 and 7 run ------------------------------------------------------


@pytest.mark.parametrize("name", ALLOCATING)
def test_steps_6_and_7_run_once_the_body_is_parsed_and_before_any_lookup(
    client, signed_in, seeded, tripwires, admission_store, enforcing, name
):
    admission_store.quota = "exceeded"
    admission_store.retry_after = 1234
    res = _send(client, name, keyed(signed_in))
    _assert_typed(res, 429, "quota_exceeded")
    assert res.headers["Retry-After"] == "1234"
    assert tripwires == [] and seeded.calls == []
    (call,) = admission_store.called("admit")
    assert call["operation"] == operation(name) and call["wall_seconds"] == FIRST_CHARGE[name]
    assert call["token"] == TEST_TOKEN and call["key"] == KEY and call["mode"] == "enforce"
    assert len(call["fingerprint"]) == 64
    # Nothing was written, so there's nothing to finish.
    assert admission_store.called("finish") == []


@pytest.mark.parametrize("name", ALLOCATING)
def test_denials_at_steps_1_to_5_never_reach_the_store(client, signed_in, gate_env, tripwires, admission_store, name):
    method, path, valid, over = ROUTES[name]
    _assert_typed(_send(client, name, keyed({})), 401, "unauthenticated")
    _assert_typed(_send(client, name, keyed(signed_in), body={**valid, "account_id": "u2"}), 422, "invalid_request")
    if over is not None:
        _assert_typed(_send(client, name, keyed(signed_in), body=over), 413, "limit_exceeded")
    gate_env({**ENFORCE, admission.gates.BY_NAME[admission.ROUTES[(method, path)].gate].env: "disabled"})
    _assert_typed(_send(client, name, keyed(signed_in)), 503, "route_disabled")
    assert admission_store.calls == [] and tripwires == []


@pytest.mark.parametrize("name", ["ats_rule", "pdf_health"])
def test_rule_scoring_and_health_skip_steps_6_and_7(client, signed_in, admission_store, monkeypatch, enforcing, name):
    from routers import pdf

    monkeypatch.setattr(pdf, "_sidecar_ok", lambda: True)
    assert _send(client, name, signed_in).status_code == 200
    assert admission_store.calls == []


def test_with_both_gates_off_nothing_reaches_the_store(client, signed_in, seeded, succeeding, admission_store, gate_env, capsys):
    gate_env({"ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "off", "ROUNDS_GATE_ENFORCE_QUOTA": "off"})
    capsys.readouterr()
    assert _send(client, "run", signed_in).status_code == 200
    assert admission_store.calls == [] and succeeding["run_one"] == 1
    (line,) = _decisions(capsys)
    assert line["idempotency"] == "skipped" and line["quota"] == "skipped" and "would_deny" not in line


def test_an_admitted_route_cannot_allocate_before_steps_6_and_7():
    admitted = admission.Admission(route=admission.ROUTES[("POST", "/api/run")], path="/api/run", method="POST")

    async def allocate_now():
        async with admission.allocate():
            pass

    token = admission._current.set(admitted)
    try:
        with pytest.raises(RuntimeError, match="begin"):
            asyncio.run(allocate_now())
    finally:
        admission._current.reset(token)
    assert admission.pool().in_use() == 0


# ---- step 6: idempotency ------------------------------------------------------------


@pytest.mark.parametrize("key", [None, "not-a-key", "0190f000-0000-4000-8000-000000000001", KEY + "0"])
def test_a_missing_or_malformed_key_is_400_when_idempotency_enforces(
    client, signed_in, seeded, tripwires, admission_store, enforcing, key
):
    headers = signed_in if key is None else keyed(signed_in, key)
    _assert_typed(_send(client, "run", headers), 400, "idempotency_key_required")
    assert admission_store.calls == [] and tripwires == [] and seeded.calls == []


def test_observe_mode_runs_a_request_without_a_key_and_logs_what_enforcing_would_answer(
    client, signed_in, seeded, succeeding, admission_store, capsys
):
    capsys.readouterr()
    assert _send(client, "run", signed_in).status_code == 200
    assert succeeding["run_one"] == 1
    (call,) = admission_store.called("admit")
    assert call["key"] is None and call["fingerprint"] is None and call["mode"] == "observe"
    (line,) = _decisions(capsys)
    assert line["idempotency"] == "missing" and line["would_deny"] == "idempotency_key_required"
    assert line["quota"] == "charged"


def test_an_uppercase_key_is_the_same_command():
    lower = admission_state.command_id([(b"idempotency-key", KEY.encode())])
    upper = admission_state.command_id([(b"Idempotency-Key", (" " + KEY.upper() + " ").encode())])
    assert lower == upper == KEY
    assert admission_state.command_id([]) is None


@pytest.mark.parametrize("name", JSON_ROUTES)
def test_a_completed_command_replays_its_stored_response_and_runs_nothing(
    client, signed_in, seeded, succeeding, admission_store, enforcing, name
):
    first = _send(client, name, keyed(signed_in))
    assert first.status_code == 200, first.text
    ran, lookups = dict(succeeding), len(seeded.calls)
    again = _send(client, name, keyed(signed_in))
    assert again.status_code == 200 and again.json() == first.json()
    assert again.headers[errors.REPLAY_HEADER] == "true"
    # No execution, provider call, attempt row, or lookup.
    assert dict(succeeding) == ran and len(seeded.calls) == lookups
    assert [f["outcome"] for f in admission_store.called("finish")] == ["completed"]


def test_a_completed_render_answers_already_completed_and_no_pdf_is_kept(
    client, signed_in, succeeding, admission_store, enforcing
):
    first = _send(client, "pdf_render", keyed(signed_in))
    assert first.status_code == 200 and first.content == PDF
    (finished,) = admission_store.called("finish")
    assert finished["outcome"] == "completed" and finished["result"] is None
    _assert_typed(_send(client, "pdf_render", keyed(signed_in)), 409, "already_completed")
    assert succeeding["render"] == 1


def test_a_key_reused_for_a_different_request_is_409(client, signed_in, seeded, succeeding, admission_store, enforcing):
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    changed = {**ROUTES["run"][2], "code": "def f(): return 2"}
    _assert_typed(_send(client, "run", keyed(signed_in), body=changed), 409, "idempotency_mismatch")
    # The same key on another route is another request too.
    _assert_typed(_send(client, "evaluate", keyed(signed_in)), 409, "idempotency_mismatch")
    assert succeeding["run_one"] == 1


def test_a_duplicate_of_a_running_command_is_409(client, signed_in, seeded, tripwires, admission_store, enforcing):
    from schemas import CodeRunRequest

    body = ROUTES["run"][2]
    fingerprint = admission_state.fingerprint("POST /api/run", "run", CodeRunRequest(**body))
    admission_store.commands[(TEST_TOKEN, KEY)] = {
        "fingerprint": fingerprint, "operation": "run", "state": "in_flight", "result": None, "wall_seconds": 3,
    }
    _assert_typed(_send(client, "run", keyed(signed_in)), 409, "already_in_flight")
    assert tripwires == [] and seeded.calls == []


def test_observe_mode_runs_a_replay_again_and_logs_it(client, signed_in, seeded, succeeding, admission_store, capsys):
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    capsys.readouterr()
    again = _send(client, "run", keyed(signed_in))
    assert again.status_code == 200 and errors.REPLAY_HEADER not in again.headers
    assert succeeding["run_one"] == 2
    (line,) = _decisions(capsys)
    assert line["idempotency"] == "replay" and line["quota"] == "charged"


@pytest.mark.parametrize("verdict, code", [("mismatch", "idempotency_mismatch"), ("in_flight", "already_in_flight")])
def test_observe_mode_runs_a_refused_duplicate_and_logs_the_would_be_409(
    client, signed_in, seeded, succeeding, admission_store, monkeypatch, capsys, verdict, code
):
    async def refused(*_args, **_kwargs):
        return admission_state.Decision(verdict, "ok", 0, "l" * 43, None)

    monkeypatch.setattr(admission_store, "admit", refused)
    monkeypatch.setattr(admission_store, "finish", lambda *a, **k: asyncio.sleep(0, result=True))
    capsys.readouterr()
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    (line,) = _decisions(capsys)
    assert line["idempotency"] == verdict and line["would_deny"] == code


# ---- step 7: quota ------------------------------------------------------------------


@pytest.mark.parametrize("verdict, code", [("exceeded", "quota_exceeded"), ("demo_limit", "demo_limit_reached")])
def test_over_quota_is_429_with_retry_after_when_quota_enforces(
    client, signed_in, seeded, tripwires, admission_store, gate_env, verdict, code
):
    gate_env({"ROUNDS_GATE_ENFORCE_QUOTA": "enforce"})
    admission_store.quota = verdict
    admission_store.retry_after = 3540
    res = _send(client, "evaluate", keyed(signed_in))
    _assert_typed(res, 429, code)
    assert res.headers["Retry-After"] == "3540"
    assert tripwires == [] and seeded.calls == []


def test_observe_mode_runs_an_over_quota_request_and_logs_the_would_be_denial(
    client, signed_in, seeded, succeeding, admission_store, capsys
):
    admission_store.quota = "demo_limit"
    capsys.readouterr()
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    assert succeeding["run_one"] == 1
    (line,) = _decisions(capsys)
    assert line["quota"] == "demo_limit" and line["would_deny"] == "demo_limit_reached"
    # Nothing was charged or leased, so nothing is finished.
    assert admission_store.called("finish") == []


@pytest.mark.parametrize(
    "env",
    [{"ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "enforce"}, {"ROUNDS_GATE_ENFORCE_QUOTA": "enforce"}, ENFORCE],
)
def test_the_store_down_is_503_when_either_gate_enforces(
    client, signed_in, seeded, tripwires, admission_store, gate_env, env
):
    gate_env(env)
    admission_store.down = True
    _assert_typed(_send(client, "run", keyed(signed_in)), 503, "quota_unavailable")
    assert tripwires == [] and seeded.calls == []


def test_the_store_down_denies_nothing_in_observe_mode(client, signed_in, seeded, succeeding, admission_store, capsys):
    admission_store.down = True
    capsys.readouterr()
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    (line,) = _decisions(capsys)
    assert line["quota"] == "unavailable" and line["idempotency"] == "unavailable"
    assert line["would_deny"] == "quota_unavailable"


# ---- settling and finishing ---------------------------------------------------------


def test_evaluate_settles_on_its_selected_cases_timeouts(client, signed_in, pocketbase, succeeding, admission_store):
    pocketbase.add(
        "coding_questions",
        slug="q-1",
        entry={"kind": "function", "name": "f"},
        test_cases=[{"input": {}}, {"input": {}, "tags": ["large"]}, {"input": {}, "tags": ["edge"]}],
    )
    assert _send(client, "evaluate", keyed(signed_in)).status_code == 200
    (settled,) = admission_store.called("settle")
    assert settled["wall_seconds"] == 3 + 10 + 3
    filtered = {**ROUTES["evaluate"][2], "filter": {"tags": ["large"]}}
    assert _send(client, "evaluate", keyed(signed_in, OTHER_KEY), body=filtered).status_code == 200
    assert admission_store.called("settle")[1]["wall_seconds"] == 10


def test_grade_settles_on_45_seconds_per_checkpoint(client, signed_in, pocketbase, succeeding, admission_store):
    pocketbase.add("ai_coding_rounds", slug="r-1", language="python",
                   checkpoints=[{"test_command": "true"}] * 3, rubric={"items": []})
    assert _send(client, "grade", keyed(signed_in)).status_code == 200
    (settled,) = admission_store.called("settle")
    assert settled["wall_seconds"] == 3 * 45


def test_a_settle_the_store_cant_record_is_503_when_quota_enforces(
    client, signed_in, seeded, tripwires, admission_store, monkeypatch, enforcing
):
    async def down(*_args, **_kwargs):
        raise admission_state.Unavailable

    monkeypatch.setattr(admission_store, "settle", down)
    _assert_typed(_send(client, "evaluate", keyed(signed_in)), 503, "quota_unavailable")
    assert tripwires == []
    # Denied before it ran, so the command is retryable and refunded.
    assert [f["outcome"] for f in admission_store.called("finish")] == ["denied"]


def test_the_response_waits_until_the_store_recorded_the_end(signed_in, seeded, succeeding, admission_store, monkeypatch):
    # So a caller never holds a result its key can't replay yet, and a
    # finished request never still counts as in flight.
    from main import app

    order: list[str] = []
    finish = admission_store.finish

    async def recording_finish(*args, **kwargs):
        order.append("finish")
        return await finish(*args, **kwargs)

    monkeypatch.setattr(admission_store, "finish", recording_finish)
    body = json.dumps(ROUTES["run"][2]).encode()
    sent = [False]

    async def receive():
        if sent[0]:
            return {"type": "http.disconnect"}
        sent[0] = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        order.append(message["type"])

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http",
        "path": "/api/run", "raw_path": b"/api/run", "root_path": "", "query_string": b"",
        "headers": [(b"host", b"testserver"), (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"authorization", signed_in["Authorization"].encode()), (b"idempotency-key", KEY.encode())],
        "client": ("127.0.0.1", 1), "server": ("testserver", 80), "state": {},
    }
    asyncio.run(app(scope, receive, send))
    assert order[0] == "finish" and order[1] == "http.response.start"
    assert order.count("finish") == 1


def test_a_completed_response_is_kept_for_replay(client, signed_in, seeded, succeeding, admission_store):
    res = _send(client, "run", keyed(signed_in))
    (finished,) = admission_store.called("finish")
    assert finished["outcome"] == "completed"
    assert finished["result"] == {"status": 200, "body": res.json()}


def test_a_response_too_large_to_keep_completes_without_a_result(client, signed_in, seeded, admission_store, monkeypatch):
    from routers import runner
    from runner import ExecutionOutcome

    big = "x" * (admission_state.RESULT_MAX_BYTES + 1)
    monkeypatch.setattr(runner, "run_one", lambda *a, **k: ExecutionOutcome(big, "", None, None, 1, False))
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    (finished,) = admission_store.called("finish")
    assert finished["outcome"] == "completed" and finished["result"] is None


@pytest.mark.parametrize("name", WITH_LOOKUPS)
def test_a_step_8_denial_leaves_the_command_retryable_and_its_key_runs_admission_again(
    client, signed_in, pocketbase, tripwires, admission_store, enforcing, name
):
    _assert_typed(_send(client, name, keyed(signed_in)), 404, "not_found")
    assert [f["outcome"] for f in admission_store.called("finish")] == ["denied"]
    assert admission_store.commands[(TEST_TOKEN, KEY)]["state"] == "retryable"
    assert admission_store.leases == {}
    _assert_typed(_send(client, name, keyed(signed_in)), 404, "not_found")
    assert len(admission_store.called("admit")) == 2 and tripwires == []


def test_a_full_replica_is_a_step_9_denial(client, signed_in, seeded, tripwires, busy, admission_store, enforcing):
    _assert_typed(_send(client, "run", keyed(signed_in)), 503, "worker_unavailable")
    assert [f["outcome"] for f in admission_store.called("finish")] == ["denied"]
    assert admission_store.commands[(TEST_TOKEN, KEY)]["state"] == "retryable"


def test_a_render_that_fails_after_admission_is_an_infrastructure_failure(
    client, signed_in, admission_store, monkeypatch, enforcing, capsys
):
    from routers import pdf

    def refuse(_request, timeout=None):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(pdf.urllib.request, "urlopen", refuse)
    capsys.readouterr()
    _assert_typed(_send(client, "pdf_render", keyed(signed_in)), 503, "worker_unavailable")
    assert [f["outcome"] for f in admission_store.called("finish")] == ["infrastructure"]
    assert admission_store.commands[(TEST_TOKEN, KEY)]["state"] == "failed_infrastructure"
    (line,) = _decisions(capsys)
    assert line["quota"] == "refunded"


def test_an_untyped_failure_after_admission_keeps_its_charge(client, signed_in, seeded, admission_store, monkeypatch, enforcing):
    from routers import runner

    def crash(*_args, **_kwargs):
        raise RuntimeError("driver bug")

    monkeypatch.setattr(runner, "run_one", crash)
    with pytest.raises(RuntimeError):
        _send(client, "run", keyed(signed_in))
    assert [f["outcome"] for f in admission_store.called("finish")] == ["error"]
    assert admission_store.commands[(TEST_TOKEN, KEY)]["state"] == "failed_infrastructure"


def test_a_finish_the_store_misses_still_answers_the_caller(client, signed_in, seeded, succeeding, admission_store, monkeypatch, capsys):
    async def down(*_args, **_kwargs):
        raise admission_state.Unavailable

    monkeypatch.setattr(admission_store, "finish", down)
    capsys.readouterr()
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    (line,) = _decisions(capsys)
    # The lease expires on its own and the sweep repairs the command.
    assert line["quota"] == "charged"


def test_the_decision_line_never_carries_the_key_the_fingerprint_or_the_lease(
    client, signed_in, seeded, succeeding, admission_store, capsys
):
    capsys.readouterr()
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    out = capsys.readouterr().out
    (admitted,) = admission_store.called("admit")
    (finished,) = admission_store.called("finish")
    for secret in (KEY, admitted["fingerprint"], finished["lease"], TEST_TOKEN):
        assert secret not in out
    (line,) = [json.loads(x) for x in out.splitlines() if x.startswith("{") and '"decision"' in x]
    assert line["idempotency"] == "new" and line["quota"] == "charged" and "dropped" not in line


# ---- the fingerprint ----------------------------------------------------------------


def test_the_fingerprint_covers_the_route_and_every_parsed_field():
    from schemas import CodeRunRequest

    a = CodeRunRequest(question_slug="q-1", code="x = 1", input={"a": 1, "b": 2})
    same = CodeRunRequest(question_slug="q-1", code="x = 1", input={"b": 2, "a": 1})
    other = CodeRunRequest(question_slug="q-1", code="x = 2", input={"a": 1, "b": 2})
    run = admission_state.fingerprint("POST /api/run", "run", a)
    assert run == admission_state.fingerprint("POST /api/run", "run", same)
    assert run != admission_state.fingerprint("POST /api/run", "run", other)
    assert run != admission_state.fingerprint("POST /api/evaluate", "evaluate", a)
    assert admission_state.FINGERPRINT_EXCLUDE == {}


# ---- the store's client -------------------------------------------------------------


def _with_store(monkeypatch, handler):
    real = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        return real(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(admission_state.httpx, "AsyncClient", client_factory)


DECISION = {"v": "admission/v1", "idempotency": "new", "quota": "ok", "retry_after": 0, "lease": "L" * 43, "result": None}


def test_admit_sends_the_bearer_and_never_the_account_or_tier(monkeypatch):
    seen = {}

    def answer(request):
        seen["auth"] = request.headers.get("authorization")
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=DECISION)

    _with_store(monkeypatch, answer)
    decision = asyncio.run(admission_state.admit("caller-token", "run", 3, KEY, "f" * 64, "enforce"))
    assert decision == admission_state.Decision("new", "ok", 0, "L" * 43, None)
    assert seen["auth"] == "Bearer caller-token" and seen["path"] == "/api/rounds/admission/admit"
    assert seen["body"] == {"operation": "run", "wall_seconds": 3, "idempotency": "enforce",
                            "command_id": KEY, "fingerprint": "f" * 64}


@pytest.mark.parametrize(
    "respond",
    [
        lambda r: httpx.Response(500, json={}),
        lambda r: httpx.Response(400, json={"v": "admission/v1", "error": "invalid_request"}),
        lambda r: httpx.Response(200, text="not json"),
        lambda r: httpx.Response(200, json={**DECISION, "v": "admission/v2"}),
        lambda r: httpx.Response(200, json={**DECISION, "quota": "maybe"}),
        lambda r: httpx.Response(200, json={**DECISION, "retry_after": -1}),
        lambda r: httpx.Response(200, json={**DECISION, "lease": "short"}),
        lambda r: httpx.Response(200, json={**DECISION, "idempotency": "replay", "result": {"status": 500, "body": {}}}),
    ],
)
def test_any_other_store_answer_is_unavailable(monkeypatch, respond):
    _with_store(monkeypatch, respond)
    with pytest.raises(admission_state.Unavailable):
        asyncio.run(admission_state.admit("t", "run", 3, None, None, "observe"))


def test_an_unreachable_store_is_unavailable(monkeypatch):
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    _with_store(monkeypatch, refuse)
    with pytest.raises(admission_state.Unavailable):
        asyncio.run(admission_state.finish("t", "L" * 43, "completed"))


def test_finish_reports_a_lease_the_store_no_longer_has(monkeypatch):
    answers = [
        httpx.Response(404, json={"v": "admission/v1", "error": "not_found"}),
        httpx.Response(200, json={"v": "admission/v1", "refunded_wall_seconds": 3}),
    ]
    _with_store(monkeypatch, lambda r: answers.pop(0))
    assert asyncio.run(admission_state.finish("t", "L" * 43, "denied")) is False
    assert asyncio.run(admission_state.finish("t", "L" * 43, "denied")) is True


# ---- the hook and the runner stay in step -------------------------------------------

HOOK_TABLE = r"""
const path = require("path");
const admission = require(path.join(process.argv[1], "admission.js"));
process.stdout.write(JSON.stringify({
  operations: admission.OPERATIONS,
  resultMaxChars: admission.RESULT_MAX_CHARS,
}));
"""


def test_each_operations_charge_matches_the_runners_timeouts():
    from routers import ai_coding, pdf, runner, take_home

    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    out = subprocess.run([node, "-e", HOOK_TABLE, str(ROOT / "pocketbase" / "pb_hooks")],
                         capture_output=True, text=True, timeout=60, check=True)
    hook = json.loads(out.stdout)
    assert hook["operations"] == {
        "run": [runner.DEFAULT_TIMEOUT_S] * 2,
        "evaluate": [0, limits.EVALUATE_MAX_CASES * runner.LARGE_TAG_TIMEOUT_S],
        "run_project": [ai_coding.RUN_PROJECT_TIMEOUT_S] * 2,
        "grade": [0, (limits.MAX_CHECKPOINT_INDEX + 1) * ai_coding.GRADE_CHECKPOINT_TIMEOUT_S],
        "take_home_run": [take_home.RUN_TIMEOUT_S] * 2,
        "take_home_submit": [take_home.SUBMIT_TIMEOUT_S] * 2,
        "pdf_render": [pdf.RENDER_TIMEOUT_S] * 2,
    }
    assert set(hook["operations"]) == {r.operation for r in admission.ROUTES.values() if r.allocates}
    # What each route charges at admission is inside the hook's range;
    # evaluate and grade start on one case or checkpoint.
    for name, charge in FIRST_CHARGE.items():
        low, high = hook["operations"][operation(name)]
        assert low <= charge <= high, name
    assert FIRST_CHARGE["evaluate"] == runner.DEFAULT_TIMEOUT_S
    assert FIRST_CHARGE["grade"] == ai_coding.GRADE_CHECKPOINT_TIMEOUT_S
    assert hook["resultMaxChars"] == admission_state.RESULT_MAX_BYTES


def test_the_command_id_pattern_is_the_same_everywhere():
    pattern = admission_state.COMMAND_ID.pattern
    assert f"/^{pattern}$/" in (ROOT / "pocketbase" / "pb_hooks" / "admission.js").read_text()
    assert f'"^{pattern}$"' in (ROOT / "pocketbase" / "pb_migrations" / "1700006100_admission.js").read_text()
    spa = (ROOT / "frontend" / "src" / "lib" / "idempotency.ts").read_text()
    assert f"/^{pattern}$/" in spa
