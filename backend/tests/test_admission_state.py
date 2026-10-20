"""Admission steps 6 and 7 at the runner (ROUNDS-00A-L01 stage 3).

Each allocating route calls the store once its body is parsed and before
any lookup: steps 1 to 5 never reach it, a completed command replays its
stored response without running anything or calling a provider, refused
and over-limit requests are denied only when their gate enforces, and the
end of every leased request is recorded (completed, denied, an
infrastructure failure, or another error), even when the store lost the
admit answer or missed the first try. Only the runner, with its key,
reaches the store. The store here is conftest's in-memory
FakeAdmissionStore; pocketbase/tests/test_admission_hooks.py covers the
hook's decisions, and the harness runs both together."""
from __future__ import annotations

import asyncio
import collections
import hashlib
import io
import json
import re
import shutil
import subprocess
import urllib.error
from pathlib import Path

import anyio
import httpx
import pytest

from app import admission, admission_state, errors
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
# The most a settle may raise evaluate and grade to: every case or
# checkpoint they may run. Every other route's first charge is its most.
MOST = {"evaluate": 32 * 10, "grade": 8 * 45}
JSON_ROUTES = [name for name in ALLOCATING if name != "pdf_render"]
WITH_LOOKUPS = ("run", "evaluate", "run_project", "grade", "take_home_run", "take_home_submit")
ENFORCE = {"ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "enforce", "ROUNDS_GATE_ENFORCE_QUOTA": "enforce"}
PDF = b"%PDF-1.4 rendered"
# A test value, not a deployment's.
RUNNER_KEY = "test-runner-key-" + "0" * 32


def keyed(headers: dict, key: str = KEY) -> dict:
    return {**headers, "Idempotency-Key": key}


def operation(name: str) -> str:
    method, path, _body, _over = ROUTES[name]
    return admission.ROUTES[(method, path)].operation


@pytest.fixture
def enforcing(gate_env):
    gate_env(ENFORCE)


@pytest.fixture
def runner_key(monkeypatch):
    monkeypatch.setenv(admission_state.RUNNER_KEY_ENV, RUNNER_KEY)
    return RUNNER_KEY


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
    assert call["max_wall_seconds"] == MOST.get(name)
    assert call["token"] == TEST_TOKEN and call["key"] == KEY and call["mode"] == "enforce"
    assert call["quota"] == "enforce" and admission_state.LEASE.fullmatch(call["lease"])
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


def test_a_duplicate_of_a_running_command_is_409_with_when_to_try_again(
    client, signed_in, seeded, tripwires, admission_store, enforcing
):
    from schemas import CodeRunRequest

    body = ROUTES["run"][2]
    fingerprint = admission_state.fingerprint("POST /api/run", "run", CodeRunRequest(**body))
    admission_store.commands[(TEST_TOKEN, KEY)] = {
        "fingerprint": fingerprint, "operation": "run", "state": "in_flight", "result": None, "wall_seconds": 3,
    }
    res = _send(client, "run", keyed(signed_in))
    _assert_typed(res, 409, "already_in_flight")
    assert res.headers["Retry-After"] == str(admission_store.in_flight_retry_after)
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
        return admission_state.Decision(verdict, "ok", 0, True, None)

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
    first = _send(client, "run", keyed(signed_in))
    assert first.status_code == 200
    assert succeeding["run_one"] == 1
    (line,) = _decisions(capsys)
    assert line["quota"] == "demo_limit" and line["would_deny"] == "demo_limit_reached"
    # Nothing was charged past the limit, but the command was recorded,
    # so idempotency still holds for this account.
    (lease,) = [c["lease"] for c in admission_store.called("admit")]
    assert [f["outcome"] for f in admission_store.called("finish")] == ["completed"]
    assert admission_store.commands[(TEST_TOKEN, KEY)]["state"] == "completed"
    assert admission_store.called("settle") == []
    assert lease not in admission_store.leases


def test_with_quota_off_nothing_is_counted_and_idempotency_still_holds(
    client, signed_in, seeded, succeeding, admission_store, gate_env, capsys
):
    gate_env({"ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "enforce", "ROUNDS_GATE_ENFORCE_QUOTA": "off"})
    capsys.readouterr()
    first = _send(client, "evaluate", keyed(signed_in))
    assert first.status_code == 200
    (call,) = admission_store.called("admit")
    assert call["quota"] == "off"
    (line,) = _decisions(capsys)
    assert line["quota"] == "skipped" and "would_deny" not in line
    # Nothing was charged, so nothing settles.
    assert admission_store.called("settle") == []
    again = _send(client, "evaluate", keyed(signed_in))
    assert again.headers[errors.REPLAY_HEADER] == "true" and again.json() == first.json()
    assert succeeding["run_one"] == 1


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


@pytest.mark.parametrize("verdict, code", [("exceeded", "quota_exceeded"), ("demo_limit", "demo_limit_reached")])
def test_a_settle_the_hour_cant_fit_is_a_step_7_denial_when_quota_enforces(
    client, signed_in, seeded, tripwires, admission_store, enforcing, verdict, code
):
    admission_store.settle_quota = verdict
    admission_store.retry_after = 1800
    res = _send(client, "evaluate", keyed(signed_in))
    _assert_typed(res, 429, code)
    assert res.headers["Retry-After"] == "1800"
    assert tripwires == []
    assert [f["outcome"] for f in admission_store.called("finish")] == ["denied"]
    assert admission_store.commands[(TEST_TOKEN, KEY)]["state"] == "retryable"


def test_observe_mode_runs_a_settle_the_hour_cant_fit_and_logs_it(
    client, signed_in, seeded, succeeding, admission_store, capsys
):
    admission_store.settle_quota = "exceeded"
    capsys.readouterr()
    assert _send(client, "evaluate", keyed(signed_in)).status_code == 200
    (line,) = _decisions(capsys)
    assert line["quota"] == "exceeded" and line["would_deny"] == "quota_exceeded"


def test_grade_refuses_a_round_with_more_checkpoints_than_it_is_admitted_for(
    client, signed_in, pocketbase, tripwires, admission_store, enforcing
):
    from routers import ai_coding

    pocketbase.add("ai_coding_rounds", slug="r-1", language="python", rubric={"items": []},
                   checkpoints=[{"test_command": "true"}] * (ai_coding.GRADE_MAX_CHECKPOINTS + 1))
    _assert_typed(_send(client, "grade", keyed(signed_in)), 422, "invalid_request")
    assert tripwires == [] and admission_store.called("settle") == []
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


def _sidecar_answer(status: int, body: dict) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://pdf-renderer:4000/render", status, "x", {},
                                  io.BytesIO(json.dumps(body).encode()))


@pytest.mark.parametrize(
    "failure",
    [
        _sidecar_answer(422, {"error": "render_timeout"}),
    ],
    ids=["sidecar-timeout"],
)
def test_a_render_that_runs_out_of_time_keeps_its_charge_and_is_not_retried(
    client, signed_in, admission_store, monkeypatch, enforcing, capsys, failure
):
    from routers import pdf

    def refuse(_request, timeout=None):
        raise failure

    monkeypatch.setattr(pdf.urllib.request, "urlopen", refuse)
    capsys.readouterr()
    # 422, which the app neither retries nor refunds: the document's
    # content decides how long it takes.
    _assert_typed(_send(client, "pdf_render", keyed(signed_in)), 422, "render_timeout")
    assert [f["outcome"] for f in admission_store.called("finish")] == ["error"]
    assert admission_store.commands[(TEST_TOKEN, KEY)]["state"] == "failed_infrastructure"
    (line,) = _decisions(capsys)
    assert line["quota"] == "charged" and line["code"] == "render_timeout"


@pytest.mark.parametrize(
    "failure",
    [
        _sidecar_answer(500, {"error": "render_failed"}),
        _sidecar_answer(503, {"error": "unavailable"}),
        _sidecar_answer(422, {"error": "something_else"}),
        urllib.error.URLError(TimeoutError("connect timed out")),
        # The sidecar answers a document's own timeout before the runner's
        # wait ends, so no answer at all is the sidecar stalling.
        TimeoutError("timed out"),
    ],
    ids=["render-failed", "no-page-in-time", "other-422", "connect-timeout", "no-answer-in-time"],
)
def test_any_other_render_failure_is_the_infrastructures(
    client, signed_in, admission_store, monkeypatch, enforcing, capsys, failure
):
    from routers import pdf

    def refuse(_request, timeout=None):
        raise failure

    monkeypatch.setattr(pdf.urllib.request, "urlopen", refuse)
    capsys.readouterr()
    _assert_typed(_send(client, "pdf_render", keyed(signed_in)), 503, "worker_unavailable")
    assert [f["outcome"] for f in admission_store.called("finish")] == ["infrastructure"]
    (line,) = _decisions(capsys)
    assert line["quota"] == "refunded"


def test_the_sidecar_answers_before_the_runner_stops_waiting():
    from routers import pdf

    server = (ROOT / "backend" / "pdf_renderer" / "server.js").read_text()
    budget = sum(int(re.search(rf"const {name} = (\d+);", server).group(1))
                 for name in ("PAGE_TIMEOUT_MS", "CONTENT_TIMEOUT_MS", "PDF_TIMEOUT_MS"))
    assert budget < pdf.RENDER_TIMEOUT_S * 1000
    # Opening the page is bounded too, and is the sidecar's 503, not the document's.
    assert "withDeadline(opening, PAGE_TIMEOUT_MS)" in server
    assert "timeout: CONTENT_TIMEOUT_MS" in server and "timeout: PDF_TIMEOUT_MS" in server
    # The whole render ends by the same budget, even when the page stops answering.
    assert "const RENDER_DEADLINE_MS = CONTENT_TIMEOUT_MS + PDF_TIMEOUT_MS;" in server
    assert "withDeadline(renderPdf(opened.page, html, marginMm), RENDER_DEADLINE_MS)" in server
    assert "'render_timeout'" in server and pdf.SIDECAR_TIMEOUT_ERROR == "render_timeout"


@pytest.mark.parametrize("name", ["grade", "take_home_submit"])
def test_the_rubric_review_ends_inside_the_lease(client, signed_in, seeded, succeeding, admission_store, monkeypatch, name):
    from ai_coding.rubric import REVIEW_TIMED_OUT
    from routers import ai_coding, take_home

    async def slow_provider(_user):
        await anyio.sleep(3600)

    for module in (ai_coding, take_home):
        monkeypatch.setattr(module, "_active_text_config", slow_provider)
        monkeypatch.setattr(module, "REVIEW_TIMEOUT_S", 0.05)
    res = _send(client, name, keyed(signed_in))
    assert res.status_code == 200, res.text
    assert res.json()["rubric_review"] == {"items": [], "total": 0.0, "skipped": True, "reason": REVIEW_TIMED_OUT}
    assert [f["outcome"] for f in admission_store.called("finish")] == ["completed"]


def test_the_attempt_write_ends_inside_the_lease(client, signed_in, seeded, succeeding, admission_store, monkeypatch):
    from routers import take_home

    async def hang(*_args, **_kwargs):
        await anyio.sleep(3600)

    monkeypatch.setattr(take_home, "pb_post", hang)
    monkeypatch.setattr(take_home, "ATTEMPT_WRITE_TIMEOUT_S", 0.05)
    assert _send(client, "take_home_submit", keyed(signed_in)).status_code == 200
    assert [f["outcome"] for f in admission_store.called("finish")] == ["completed"]


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
    tries = []

    async def down(*_args, **_kwargs):
        tries.append(1)
        raise admission_state.Unavailable

    monkeypatch.setattr(admission_store, "finish", down)
    capsys.readouterr()
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    assert len(tries) == admission.FINISH_ATTEMPTS
    (line,) = _decisions(capsys)
    # The lease stops counting when its window ends, and the sweep
    # repairs the command.
    assert line["quota"] == "charged"


def test_a_finish_the_store_missed_at_first_is_tried_again_and_recorded(
    client, signed_in, seeded, succeeding, admission_store, enforcing
):
    admission_store.finish_failures = admission.FINISH_ATTEMPTS - 1
    first = _send(client, "run", keyed(signed_in))
    assert first.status_code == 200
    assert len(admission_store.called("finish")) == admission.FINISH_ATTEMPTS
    assert admission_store.commands[(TEST_TOKEN, KEY)]["state"] == "completed" and admission_store.leases == {}
    again = _send(client, "run", keyed(signed_in))
    assert again.headers[errors.REPLAY_HEADER] == "true" and again.json() == first.json()


def test_the_end_of_a_request_waits_on_the_store_only_so_long(signed_in, admission_store, monkeypatch):
    # Every try is bounded too, so a hung store can't hold the response.
    async def hang(*_args, **_kwargs):
        await anyio.sleep(3600)

    monkeypatch.setattr(admission_store, "finish", hang)
    monkeypatch.setattr(admission, "FINISH_TIMEOUT_S", 0.05)
    recorded = asyncio.run(admission._end_lease(TEST_TOKEN, "l" * 43, "completed", None))
    assert recorded is False


def test_every_finish_attempt_fits_the_budget():
    backoffs = admission.FINISH_BACKOFF_S[: admission.FINISH_ATTEMPTS - 1]
    assert len(backoffs) == admission.FINISH_ATTEMPTS - 1
    assert admission.FINISH_ATTEMPTS * admission.FINISH_CALL_TIMEOUT_S + sum(backoffs) < admission.FINISH_TIMEOUT_S


def test_a_store_that_hangs_on_every_finish_gets_every_attempt(signed_in, admission_store, monkeypatch):
    # Each call is cut at its own timeout, whatever the client does, so
    # the last attempt isn't cut short by the overall budget.
    tries = []

    async def hang(*_args, **_kwargs):
        tries.append(1)
        await anyio.sleep(3600)

    monkeypatch.setattr(admission_store, "finish", hang)
    monkeypatch.setattr(admission, "FINISH_TIMEOUT_S", 2.0)
    monkeypatch.setattr(admission, "FINISH_CALL_TIMEOUT_S", 0.2)
    monkeypatch.setattr(admission, "FINISH_BACKOFF_S", (0.05, 0.1))
    recorded = asyncio.run(admission._end_lease(TEST_TOKEN, "l" * 43, "completed", None))
    assert recorded is False
    assert len(tries) == admission.FINISH_ATTEMPTS


def test_a_refused_finish_isnt_tried_again(signed_in, admission_store, monkeypatch):
    tries = []

    async def refuse(*_args, **_kwargs):
        tries.append(1)
        raise admission_state.Refused

    monkeypatch.setattr(admission_store, "finish", refuse)
    recorded = asyncio.run(admission._end_lease(TEST_TOKEN, "l" * 43, "completed", None))
    assert (recorded, len(tries)) == (False, 1)


@pytest.mark.parametrize("env", [ENFORCE, {}])
def test_a_lost_admit_answer_still_ends_its_lease_so_the_key_runs_again(
    client, signed_in, seeded, succeeding, admission_store, gate_env, env
):
    gate_env(env)
    admission_store.lost_answers = 1
    first = _send(client, "run", keyed(signed_in))
    if env:
        _assert_typed(first, 503, "quota_unavailable")
    else:
        assert first.status_code == 200
    # The runner made the lease token, so it could end the lease it never
    # heard about: the command is retryable and nothing still counts.
    (released,) = admission_store.called("finish")[:1]
    assert released["lease"] == admission_store.called("admit")[0]["lease"]
    assert released["outcome"] == "infrastructure"
    assert admission_store.commands[(TEST_TOKEN, KEY)]["state"] == "failed_infrastructure"
    assert admission_store.leases == {}
    again = _send(client, "run", keyed(signed_in))
    assert again.status_code == 200 and errors.REPLAY_HEADER not in again.headers
    assert admission_store.called("admit")[1]["key"] == KEY


def test_a_runner_without_its_key_calls_nothing_and_denies_only_when_a_gate_enforces(
    client, signed_in, seeded, succeeding, admission_store, gate_env, capsys
):
    admission_store.unconfigured = True
    capsys.readouterr()
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    (line,) = _decisions(capsys)
    assert line["would_deny"] == "quota_unavailable"
    # Nothing was sent, so there's no lease to end.
    assert admission_store.called("finish") == []
    gate_env(ENFORCE)
    _assert_typed(_send(client, "run", keyed(signed_in, OTHER_KEY)), 503, "quota_unavailable")
    assert succeeding["run_one"] == 1


def test_a_refused_admit_ends_no_lease_and_denies_only_when_a_gate_enforces(
    client, signed_in, seeded, succeeding, admission_store, gate_env, capsys
):
    # A refusal (a key the store doesn't accept, say) proves no lease was
    # written, so there's nothing to end and no finish call to make.
    admission_store.refused = True
    capsys.readouterr()
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    (line,) = _decisions(capsys)
    assert line["would_deny"] == "quota_unavailable"
    gate_env(ENFORCE)
    _assert_typed(_send(client, "run", keyed(signed_in, OTHER_KEY)), 503, "quota_unavailable")
    assert len(admission_store.called("admit")) == 2
    assert admission_store.called("finish") == []
    assert succeeding["run_one"] == 1


def test_the_decision_line_never_carries_the_key_the_fingerprint_or_the_lease(
    client, signed_in, seeded, succeeding, admission_store, runner_key, capsys
):
    capsys.readouterr()
    assert _send(client, "run", keyed(signed_in)).status_code == 200
    out = capsys.readouterr().out
    (admitted,) = admission_store.called("admit")
    (finished,) = admission_store.called("finish")
    for secret in (KEY, admitted["fingerprint"], finished["lease"], TEST_TOKEN, runner_key):
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


DECISION = {"v": "admission/v1", "idempotency": "new", "quota": "ok", "retry_after": 0, "leased": True, "result": None}
LEASE = "L" * 43


def test_admit_sends_the_bearer_the_runner_key_and_only_the_leases_hash(monkeypatch, runner_key):
    seen = {}

    def answer(request):
        seen["auth"] = request.headers.get("authorization")
        seen["key"] = request.headers.get(admission_state.RUNNER_KEY_HEADER)
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=DECISION)

    _with_store(monkeypatch, answer)
    decision = asyncio.run(admission_state.admit(
        "caller-token", "evaluate", 3, KEY, "f" * 64, "enforce", lease=LEASE, quota="observe", max_wall_seconds=320,
    ))
    assert decision == admission_state.Decision("new", "ok", 0, True, None)
    assert seen["auth"] == "Bearer caller-token" and seen["path"] == "/api/rounds/admission/admit"
    assert seen["key"] == runner_key
    # Never the account, the tier, or the lease token itself.
    assert seen["body"] == {"operation": "evaluate", "wall_seconds": 3, "max_wall_seconds": 320,
                            "idempotency": "enforce", "quota": "observe", "command_id": KEY, "fingerprint": "f" * 64,
                            "lease_hash": hashlib.sha256(LEASE.encode()).hexdigest()}


@pytest.mark.parametrize("value", [None, "", "short", " " + "k" * 40, "k" * 40 + "\n", "k" * 39 + "é"])
def test_a_runner_without_a_usable_key_sends_nothing(monkeypatch, value):
    sent = []

    def answer(request):
        sent.append(request)
        return httpx.Response(200, json=DECISION)

    _with_store(monkeypatch, answer)
    if value is None:
        monkeypatch.delenv(admission_state.RUNNER_KEY_ENV, raising=False)
    else:
        monkeypatch.setenv(admission_state.RUNNER_KEY_ENV, value)
    for call in (
        admission_state.admit("t", "run", 3, None, None, "observe", lease=LEASE),
        admission_state.settle("t", LEASE, 3),
        admission_state.finish("t", LEASE, "completed"),
    ):
        with pytest.raises(admission_state.Unconfigured):
            asyncio.run(call)
    assert sent == []


@pytest.mark.parametrize(
    "respond",
    [
        lambda r: httpx.Response(500, json={}),
        lambda r: httpx.Response(400, json={"v": "admission/v1", "error": "invalid_request"}),
        lambda r: httpx.Response(403, json={"v": "admission/v1", "error": "forbidden"}),
        lambda r: httpx.Response(503, json={"v": "admission/v1", "error": "unconfigured"}),
        lambda r: httpx.Response(200, text="not json"),
        lambda r: httpx.Response(200, json={**DECISION, "v": "admission/v2"}),
        lambda r: httpx.Response(200, json={**DECISION, "quota": "maybe"}),
        lambda r: httpx.Response(200, json={**DECISION, "retry_after": -1}),
        lambda r: httpx.Response(200, json={**DECISION, "leased": "yes"}),
        lambda r: httpx.Response(200, json={k: v for k, v in DECISION.items() if k != "leased"}),
        lambda r: httpx.Response(200, json={**DECISION, "idempotency": "replay", "result": {"status": 500, "body": {}}}),
    ],
)
def test_any_other_store_answer_is_unavailable(monkeypatch, runner_key, respond):
    _with_store(monkeypatch, respond)
    with pytest.raises(admission_state.Unavailable):
        asyncio.run(admission_state.admit("t", "run", 3, None, None, "observe", lease=LEASE))


def test_settle_answers_the_quota_verdict_of_a_raise_the_hour_cant_fit(monkeypatch, runner_key):
    answers = [
        httpx.Response(200, json={"v": "admission/v1", "wall_seconds": 30}),
        httpx.Response(429, json={"v": "admission/v1", "quota": "demo_limit", "retry_after": 600}),
        httpx.Response(429, json={"v": "admission/v1", "quota": "maybe", "retry_after": 600}),
        httpx.Response(409, json={"v": "admission/v1", "error": "already_settled"}),
        httpx.Response(400, json={"v": "admission/v1", "error": "invalid_request"}),
        httpx.Response(404, json={"v": "admission/v1", "error": "not_found"}),
    ]
    _with_store(monkeypatch, lambda r: answers.pop(0))
    assert asyncio.run(admission_state.settle("t", LEASE, 30)) == admission_state.Settled("ok", 0)
    assert asyncio.run(admission_state.settle("t", LEASE, 30)) == admission_state.Settled("demo_limit", 600)
    for _ in range(4):
        with pytest.raises(admission_state.Unavailable):
            asyncio.run(admission_state.settle("t", LEASE, 30))


@pytest.mark.parametrize(
    "respond",
    [
        lambda r: httpx.Response(400, json={"v": "admission/v1", "error": "invalid_request"}),
        lambda r: httpx.Response(401, json={"code": 401, "message": "x", "data": {}}),
        lambda r: httpx.Response(403, json={"v": "admission/v1", "error": "forbidden"}),
        lambda r: httpx.Response(404, text="<html>not found</html>"),
        lambda r: httpx.Response(503, json={"v": "admission/v1", "error": "unconfigured"}),
    ],
    ids=["invalid-request", "unauthenticated", "forbidden", "no-route", "store-unconfigured"],
)
def test_an_answer_that_proves_nothing_was_written_is_a_refusal(monkeypatch, runner_key, respond):
    _with_store(monkeypatch, respond)
    with pytest.raises(admission_state.Refused):
        asyncio.run(admission_state.admit("t", "run", 3, None, None, "observe", lease=LEASE))


@pytest.mark.parametrize(
    "respond",
    [
        lambda r: httpx.Response(500, json={}),
        lambda r: httpx.Response(502, text="bad gateway"),
        lambda r: httpx.Response(503, json={"v": "admission/v1", "error": "busy"}),
        lambda r: httpx.Response(200, text="not json"),
        lambda r: httpx.Response(200, json={**DECISION, "v": "admission/v2"}),
    ],
    ids=["500", "502-text", "503-other", "200-not-json", "200-other-version"],
)
def test_an_answer_that_may_hide_a_written_lease_is_no_refusal(monkeypatch, runner_key, respond):
    _with_store(monkeypatch, respond)
    with pytest.raises(admission_state.Unavailable) as raised:
        asyncio.run(admission_state.admit("t", "run", 3, None, None, "observe", lease=LEASE))
    assert not isinstance(raised.value, admission_state.Refused)


def test_a_store_that_never_answers_is_no_refusal(monkeypatch, runner_key):
    def stall(request):
        raise httpx.ReadTimeout("no answer", request=request)

    _with_store(monkeypatch, stall)
    with pytest.raises(admission_state.Unavailable) as raised:
        asyncio.run(admission_state.admit("t", "run", 3, None, None, "observe", lease=LEASE))
    assert not isinstance(raised.value, admission_state.Refused)


def test_a_finish_the_store_refuses_is_a_refusal(monkeypatch, runner_key):
    _with_store(monkeypatch, lambda r: httpx.Response(403, json={"v": "admission/v1", "error": "forbidden"}))
    with pytest.raises(admission_state.Refused):
        asyncio.run(admission_state.finish("t", LEASE, "completed"))


def test_an_unreachable_store_is_unavailable(monkeypatch, runner_key):
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    _with_store(monkeypatch, refuse)
    with pytest.raises(admission_state.Unavailable) as raised:
        asyncio.run(admission_state.finish("t", LEASE, "completed"))
    assert not isinstance(raised.value, admission_state.Unconfigured)


def test_finish_reports_a_lease_the_store_no_longer_has(monkeypatch, runner_key):
    answers = [
        httpx.Response(404, json={"v": "admission/v1", "error": "not_found"}),
        httpx.Response(200, json={"v": "admission/v1", "refunded_wall_seconds": 3}),
    ]
    _with_store(monkeypatch, lambda r: answers.pop(0))
    assert asyncio.run(admission_state.finish("t", LEASE, "denied")) is False
    assert asyncio.run(admission_state.finish("t", LEASE, "denied")) is True


def test_lease_tokens_are_long_random_and_the_hooks_shape():
    tokens = {admission_state.new_lease() for _ in range(200)}
    assert len(tokens) == 200
    assert all(admission_state.LEASE.fullmatch(t) for t in tokens)
    hook = (ROOT / "pocketbase" / "pb_hooks" / "admission.js").read_text()
    assert f"const LEASE_TOKEN = /^{admission_state.LEASE.pattern}$/;" in hook


# ---- the hook and the runner stay in step -------------------------------------------

HOOK_TABLE = r"""
const path = require("path");
const admission = require(path.join(process.argv[1], "admission.js"));
process.stdout.write(JSON.stringify({
  operations: admission.OPERATIONS,
  resultMaxChars: admission.RESULT_MAX_CHARS,
  hold: admission.HOLD_S,
  keyEnv: admission.RUNNER_KEY_ENV,
  keyHeader: admission.RUNNER_KEY_HEADER,
  keyMinChars: admission.RUNNER_KEY_MIN_CHARS,
}));
"""


def _hook_table() -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    out = subprocess.run([node, "-e", HOOK_TABLE, str(ROOT / "pocketbase" / "pb_hooks")],
                         capture_output=True, text=True, timeout=60, check=True)
    return json.loads(out.stdout)


def test_each_operations_charge_matches_the_runners_timeouts():
    from routers import ai_coding, pdf, runner, take_home

    hook = _hook_table()
    assert hook["operations"] == {
        "run": [runner.DEFAULT_TIMEOUT_S] * 2,
        "evaluate": [0, runner.EVALUATE_MAX_WALL_S],
        "run_project": [ai_coding.RUN_PROJECT_TIMEOUT_S] * 2,
        "grade": [0, ai_coding.GRADE_MAX_WALL_S],
        "take_home_run": [take_home.RUN_TIMEOUT_S] * 2,
        "take_home_submit": [take_home.SUBMIT_TIMEOUT_S] * 2,
        "pdf_render": [pdf.RENDER_TIMEOUT_S] * 2,
    }
    assert set(hook["operations"]) == {r.operation for r in admission.ROUTES.values() if r.allocates}
    # What each route charges at admission is inside the hook's range;
    # evaluate and grade start on one case or checkpoint, admitted up to
    # every case or checkpoint they may run.
    for name, charge in FIRST_CHARGE.items():
        low, high = hook["operations"][operation(name)]
        assert low <= charge <= high, name
        assert MOST.get(name, high) == high, name
    assert FIRST_CHARGE["evaluate"] == runner.DEFAULT_TIMEOUT_S
    assert FIRST_CHARGE["grade"] == ai_coding.GRADE_CHECKPOINT_TIMEOUT_S
    assert runner.EVALUATE_MAX_WALL_S == 32 * runner.LARGE_TAG_TIMEOUT_S
    assert ai_coding.GRADE_MAX_WALL_S == ai_coding.GRADE_MAX_CHECKPOINTS * ai_coding.GRADE_CHECKPOINT_TIMEOUT_S
    assert hook["resultMaxChars"] == admission_state.RESULT_MAX_BYTES


def test_a_lease_holds_long_enough_for_the_work_after_the_run():
    # Grade and submit ask for a rubric review after the run, and submit
    # saves its attempt, so the sweep never ends a lease that's still
    # working. The rest end with the run.
    from ai_coding.rubric import REVIEW_TIMEOUT_S
    from routers import take_home

    hold = _hook_table()["hold"]
    assert set(hold) == {"grade", "take_home_submit"}
    assert hold["grade"] >= REVIEW_TIMEOUT_S
    assert hold["take_home_submit"] >= REVIEW_TIMEOUT_S + take_home.ATTEMPT_WRITE_TIMEOUT_S


def test_the_runner_key_is_named_the_same_on_both_sides():
    hook = _hook_table()
    assert hook["keyEnv"] == admission_state.RUNNER_KEY_ENV
    # requestInfo lowercases header names and turns dashes to underscores.
    assert hook["keyHeader"] == admission_state.RUNNER_KEY_HEADER.lower().replace("-", "_")
    assert hook["keyMinChars"] == admission_state.RUNNER_KEY_MIN_CHARS


def test_the_command_id_pattern_is_the_same_everywhere():
    pattern = admission_state.COMMAND_ID.pattern
    assert f"/^{pattern}$/" in (ROOT / "pocketbase" / "pb_hooks" / "admission.js").read_text()
    assert f'"^{pattern}$"' in (ROOT / "pocketbase" / "pb_migrations" / "1700006100_admission.js").read_text()
    spa = (ROOT / "frontend" / "src" / "lib" / "idempotency.ts").read_text()
    assert f"/^{pattern}$/" in spa
