"""Admission chain (ROUNDS-00A-L01, admission/v1).

Each admitted route, each step in order: the byte cap, the gate, the
account, the (tier, operation) table, the fields, the lookups, and the
in-flight cap. No denial reaches a subprocess, a scratch directory, or
the PDF sidecar, and nothing reads a record before step 8."""
from __future__ import annotations

import asyncio
import json
import re
import tempfile
import threading
import time
import urllib.request

import anyio
import httpx
import pytest
from fastapi import HTTPException

from app import admission, gates, obs
from app.errors import TypedError

HEX32 = re.compile(r"[0-9a-f]{32}")
KIB = 1024
MIB = 1024 * KIB


class Tripped(Exception):
    """A guarded call ran."""


# (method, path, a valid body, the body's step 5 over-limit variant)
ROUTES = {
    "run": (
        "POST",
        "/api/run",
        {"question_slug": "q-1", "language": "python", "code": "def f(): pass", "input": {}},
        {"question_slug": "q-1", "language": "python", "code": "x" * (256 * KIB + 1), "input": {}},
    ),
    "evaluate": (
        "POST",
        "/api/evaluate",
        {"question_slug": "q-1", "language": "python", "code": "def f(): pass"},
        {"question_slug": "q-1", "language": "python", "code": "x" * (256 * KIB + 1)},
    ),
    "run_project": (
        "POST",
        "/api/ai-coding/run-project",
        {"round_slug": "r-1", "checkpoint_index": 0, "files": {"a.py": "pass"}},
        {"round_slug": "r-1", "checkpoint_index": 0, "files": {f"f{i}.py": "" for i in range(201)}},
    ),
    "grade": (
        "POST",
        "/api/ai-coding/grade",
        {"round_slug": "r-1", "files": {"a.py": "pass"}, "ai_chats": []},
        {"round_slug": "r-1", "files": {}, "ai_chats": [{"role": "user", "content": "x" * (512 * KIB)}]},
    ),
    "take_home_run": (
        "POST",
        "/api/take-home/run",
        {"assignment_slug": "a-1", "files": {"a.py": "pass"}},
        {"assignment_slug": "a-1", "files": {f"f{i}.py": "" for i in range(201)}},
    ),
    "take_home_submit": (
        "POST",
        "/api/take-home/submit",
        {"assignment_slug": "a-1", "files": {"a.py": "pass"}},
        {"assignment_slug": "a-1", "files": {}, "notes": "x" * (64 * KIB + 1)},
    ),
    "pdf_render": ("POST", "/api/pdf/render", {"html": "<p>hi</p>"}, None),
    "pdf_health": ("GET", "/api/pdf/health", None, None),
    "ats_rule": (
        "POST",
        "/api/ai/ats-rule",
        {"data": {}, "job_description": None, "use_ai": False},
        {"data": {}, "job_description": "x" * (64 * KIB + 1)},
    ),
}
CAPS = {
    "run": 512 * KIB,
    "evaluate": 512 * KIB,
    "run_project": 6 * MIB,
    "grade": 6 * MIB,
    "take_home_run": 6 * MIB,
    "take_home_submit": 6 * MIB,
    "pdf_render": 2 * MIB,
    "pdf_health": 0,
    "ats_rule": 1 * MIB,
}
GATES = {
    "run": "RUN",
    "evaluate": "EVALUATE",
    "run_project": "AI_CODING_RUN_PROJECT",
    "grade": "AI_CODING_GRADE",
    "take_home_run": "TAKE_HOME_RUN",
    "take_home_submit": "TAKE_HOME_SUBMIT",
    "pdf_render": "PDF_RENDER",
    "pdf_health": "PDF_HEALTH",
    "ats_rule": "ATS_RULE",
}
ALLOCATING = sorted(n for n in ROUTES if n not in ("ats_rule", "pdf_health"))
WITH_BODY = sorted(n for n in ROUTES if ROUTES[n][2] is not None)
WITH_LIMITS = sorted(n for n in ROUTES if ROUTES[n][3] is not None)
WITH_LOOKUPS = ("run", "evaluate", "run_project", "grade", "take_home_run", "take_home_submit")


def _send(client, name, headers=None, body=None, content=None):
    method, path, valid, _ = ROUTES[name]
    if content is not None:
        return client.request(method, path, content=content, headers={"Content-Type": "application/json", **(headers or {})})
    payload = valid if body is None else body
    if payload is None:
        return client.request(method, path, headers=headers or {})
    return client.request(method, path, json=payload, headers=headers or {})


def _assert_typed(res, status, code):
    assert res.status_code == status, res.text
    body = res.json()
    assert set(body) == {"detail", "code", "correlation_id"}
    assert body["code"] == code
    assert isinstance(body["detail"], str) and body["detail"]
    assert HEX32.fullmatch(body["correlation_id"])
    assert res.headers[obs.CORRELATION_HEADER] == body["correlation_id"]


@pytest.fixture
def tripwires(monkeypatch):
    """Execution, scratch, and sidecar calls, each recorded and refused."""
    from routers import ai_coding, runner, take_home

    hits: list[str] = []

    def trip(name):
        def guarded(*_args, **_kwargs):
            hits.append(name)
            raise Tripped(name)

        return guarded

    monkeypatch.setattr(runner, "run_one", trip("run_one"))
    monkeypatch.setattr(ai_coding, "run_project", trip("run_project"))
    monkeypatch.setattr(take_home, "run_assignment", trip("run_assignment"))
    monkeypatch.setattr(urllib.request, "urlopen", trip("urlopen"))
    monkeypatch.setattr(tempfile, "mkdtemp", trip("mkdtemp"))
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", trip("NamedTemporaryFile"))
    return hits


@pytest.fixture
def seeded(pocketbase):
    """One record for every lookup the valid bodies make."""
    pocketbase.add("coding_questions", slug="q-1", entry={"kind": "function", "name": "f"}, test_cases=[{"input": {}, "expected": None}])
    pocketbase.add("ai_coding_rounds", slug="r-1", language="python", checkpoints=[{"test_command": "true"}], rubric={"items": []})
    pocketbase.add("take_home_assignments", slug="a-1", entrypoint="true", harness_files=[], rubric={"items": []})
    return pocketbase


@pytest.fixture
def gate_env(monkeypatch):
    def set_env(env):
        monkeypatch.setattr(gates, "_snapshot", gates.load(env, gates.RUNNER))

    return set_env


@pytest.fixture
def busy(monkeypatch):
    """Every in-flight slot taken."""
    pool = admission.pool()
    taken = []
    while (slot := pool.try_acquire()) is not None:
        taken.append(slot)
    yield
    for slot in taken:
        pool.release(slot)


# ---- the positive control: the tripwires are wired -----------------------------


@pytest.mark.parametrize("name", ALLOCATING)
def test_an_admitted_request_reaches_execution(client, signed_in, seeded, tripwires, name):
    with pytest.raises(Tripped):
        _send(client, name, signed_in)
    assert tripwires


# ---- step 1: byte cap -----------------------------------------------------------


@pytest.mark.parametrize("name", sorted(ROUTES))
def test_a_body_over_the_cap_is_413_before_the_gate_or_the_account(client, gate_env, tripwires, pocketbase, name):
    gate_env({gates.BY_NAME[GATES[name]].env: "disabled"})
    res = _send(client, name, content=b"x" * (CAPS[name] + 1))
    _assert_typed(res, 413, "payload_too_large")
    assert tripwires == [] and pocketbase.calls == []


@pytest.mark.parametrize("name", WITH_BODY)
def test_a_body_at_the_cap_passes_step_1(client, tripwires, name):
    # Anonymous, so step 3 answers.
    res = _send(client, name, content=b" " * CAPS[name])
    _assert_typed(res, 401, "unauthenticated")


def test_a_body_without_a_length_is_counted_as_it_arrives(signed_in):
    # ASGI level, so the request really has no Content-Length.
    from main import app

    chunks = [b" " * (100 * KIB)] * 10
    sent: list[dict] = []

    async def receive():
        body = chunks.pop(0) if chunks else b""
        return {"type": "http.request", "body": body, "more_body": bool(chunks)}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/run",
        "raw_path": b"/api/run",
        "root_path": "",
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"transfer-encoding", b"chunked"),
            (b"authorization", signed_in["Authorization"].encode()),
        ],
        "client": ("127.0.0.1", 1),
        "server": ("testserver", 80),
        "state": {},
    }
    asyncio.run(app(scope, receive, send))
    start = next(m for m in sent if m["type"] == "http.response.start")
    assert start["status"] == 413
    body = json.loads(b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body"))
    assert body["code"] == "payload_too_large"
    # Reading stopped at the sixth chunk, the first past 512 KiB.
    assert len(chunks) == 4


def test_a_streamed_body_over_the_cap_is_413_while_it_arrives(client, signed_in, tripwires, pocketbase):
    def chunks():
        for _ in range(9):
            yield b" " * (64 * KIB)

    res = client.post("/api/run", content=chunks(), headers={"Content-Type": "application/json", **signed_in})
    _assert_typed(res, 413, "payload_too_large")
    assert tripwires == [] and pocketbase.calls == []


# ---- step 2: gate ---------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(ROUTES))
def test_a_disabled_route_is_503_before_the_account(client, gate_env, tripwires, pocketbase, name):
    gate_env({gates.BY_NAME[GATES[name]].env: "disabled"})
    res = _send(client, name)
    _assert_typed(res, 503, "route_disabled")
    assert tripwires == [] and pocketbase.calls == []


def test_disabling_one_route_leaves_the_others_serving(client, signed_in, gate_env, seeded, tripwires):
    gate_env({"ROUNDS_GATE_RUN": "disabled"})
    _assert_typed(_send(client, "run", signed_in), 503, "route_disabled")
    assert _send(client, "ats_rule", signed_in).status_code == 200


# ---- step 3: account --------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(ROUTES))
@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer"}, {"Authorization": "Basic dXNlcjpwYXNz"}, {"Authorization": "Bearer a b"}],
)
def test_no_usable_bearer_is_401(client, tripwires, pocketbase, name, headers):
    res = _send(client, name, headers)
    _assert_typed(res, 401, "unauthenticated")
    assert tripwires == [] and pocketbase.calls == []


@pytest.mark.parametrize("name", sorted(ROUTES))
def test_a_bearer_pocketbase_rejects_is_401(client, signed_in, tripwires, pocketbase, name):
    res = _send(client, name, {"Authorization": "Bearer not-the-test-token"})
    _assert_typed(res, 401, "unauthenticated")
    assert tripwires == [] and pocketbase.calls == []


def test_the_body_is_never_parsed_for_an_anonymous_caller(client, tripwires):
    # Malformed JSON would be a 422 if the body were read first.
    res = _send(client, "run", content=b"{not json")
    _assert_typed(res, 401, "unauthenticated")


def _with_pocketbase(monkeypatch, handler):
    real = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        return real(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(admission.httpx, "AsyncClient", client_factory)


@pytest.mark.parametrize(
    "respond, code",
    [
        (lambda r: httpx.Response(500, text="boom"), "auth_unavailable"),
        (lambda r: httpx.Response(503, text="down"), "auth_unavailable"),
        (lambda r: httpx.Response(200, text="not json"), "auth_unavailable"),
        (lambda r: httpx.Response(401, json={"message": "nope"}), "unauthenticated"),
        (lambda r: httpx.Response(400, json={}), "unauthenticated"),
        (lambda r: httpx.Response(200, json={"record": {}}), "unauthenticated"),
    ],
)
def test_authenticate_maps_pocketbase_answers(monkeypatch, respond, code):
    _with_pocketbase(monkeypatch, respond)
    with pytest.raises(TypedError) as err:
        asyncio.run(admission.authenticate("t"))
    assert err.value.code == code


def test_authenticate_maps_an_unreachable_pocketbase_to_503(monkeypatch):
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    _with_pocketbase(monkeypatch, refuse)
    with pytest.raises(TypedError) as err:
        asyncio.run(admission.authenticate("t"))
    assert err.value.code == "auth_unavailable" and err.value.status_code == 503


def test_authenticate_returns_the_account_and_sends_the_bearer(monkeypatch):
    seen = {}

    def answer(request):
        seen["auth"] = request.headers.get("authorization")
        seen["path"] = request.url.path
        return httpx.Response(200, json={"token": "t", "record": {"id": "abc123def456ghi", "is_demo": True}})

    _with_pocketbase(monkeypatch, answer)
    account = asyncio.run(admission.authenticate("caller-token"))
    assert account == {"id": "abc123def456ghi", "token": "caller-token", "record": {"id": "abc123def456ghi", "is_demo": True}}
    assert seen == {"auth": "Bearer caller-token", "path": admission.AUTH_REFRESH_PATH}


@pytest.mark.parametrize("name", sorted(ROUTES))
def test_pocketbase_down_is_503_auth_unavailable(client, monkeypatch, tripwires, pocketbase, name):
    async def down(_token):
        raise TypedError("auth_unavailable")

    monkeypatch.setattr(admission, "authenticate", down)
    res = _send(client, name, {"Authorization": "Bearer t"})
    _assert_typed(res, 503, "auth_unavailable")
    assert tripwires == [] and pocketbase.calls == []


# ---- step 4: tier and operation -----------------------------------------------------


def test_every_tier_and_operation_is_permitted_until_stage_3():
    operations = {r.operation for r in admission.ROUTES.values()}
    assert set(admission.PERMITS) == {(t, o) for t in ("standard", "demo") for o in operations}
    assert all(admission.PERMITS.values())


@pytest.mark.parametrize("name", sorted(ROUTES))
def test_a_refused_operation_is_403_before_the_body(client, signed_in, monkeypatch, tripwires, pocketbase, name):
    route = admission.ROUTES[(ROUTES[name][0], ROUTES[name][1])]
    monkeypatch.setitem(admission.PERMITS, ("standard", route.operation), False)
    res = _send(client, name, signed_in, content=b"{not json" if ROUTES[name][2] is not None else None)
    _assert_typed(res, 403, "not_permitted")
    assert tripwires == [] and pocketbase.calls == []


def test_the_tier_comes_from_the_account_record(monkeypatch, client, tripwires, capsys):
    async def demo(token):
        return {"id": "u2", "token": token, "record": {"id": "u2", "is_demo": True}}

    monkeypatch.setattr(admission, "authenticate", demo)
    monkeypatch.setitem(admission.PERMITS, ("demo", "ats_rule"), False)
    res = _send(client, "ats_rule", {"Authorization": "Bearer t"})
    _assert_typed(res, 403, "not_permitted")
    (line,) = _decisions(capsys)
    assert line["tier"] == "demo"


def test_a_forged_tier_in_the_body_is_refused(client, signed_in, tripwires):
    res = _send(client, "ats_rule", signed_in, body={"data": {}, "tier": "standard"})
    _assert_typed(res, 422, "invalid_request")


# ---- step 5: fields ------------------------------------------------------------------


@pytest.mark.parametrize("name", WITH_BODY)
@pytest.mark.parametrize("extra", [{"account_id": "u2"}, {"timeout_s": 600}, {"entry": {"kind": "custom"}}])
def test_an_unknown_field_is_422_before_any_lookup(client, signed_in, tripwires, pocketbase, name, extra):
    res = _send(client, name, signed_in, body={**ROUTES[name][2], **extra})
    _assert_typed(res, 422, "invalid_request")
    assert tripwires == [] and pocketbase.calls == []


@pytest.mark.parametrize("name", WITH_LIMITS)
def test_a_field_over_its_limit_is_413_limit_exceeded(client, signed_in, tripwires, pocketbase, name):
    res = _send(client, name, signed_in, body=ROUTES[name][3])
    _assert_typed(res, 413, "limit_exceeded")
    assert tripwires == [] and pocketbase.calls == []


@pytest.mark.parametrize("name", WITH_BODY)
def test_malformed_json_is_422(client, signed_in, tripwires, pocketbase, name):
    res = _send(client, name, signed_in, content=b"{not json")
    _assert_typed(res, 422, "invalid_request")
    assert tripwires == [] and pocketbase.calls == []


@pytest.mark.parametrize(
    "path",
    ["../escape.py", "/etc/passwd", "a/../../b.py", "a\\b.py", "", "a//b.py", "./a.py"],
)
def test_a_file_path_outside_the_project_is_422(client, signed_in, tripwires, pocketbase, path):
    res = _send(client, "take_home_run", signed_in, body={"assignment_slug": "a-1", "files": {path: "x"}})
    _assert_typed(res, 422, "invalid_request")
    assert tripwires == [] and pocketbase.calls == []


@pytest.mark.parametrize("slug", ["Q1", "q 1", "q'1", "q\"1", "x" * 129])
def test_a_slug_outside_the_pattern_is_422(client, signed_in, tripwires, pocketbase, slug):
    body = {**ROUTES["run"][2], "question_slug": slug}
    _assert_typed(_send(client, "run", signed_in, body=body), 422, "invalid_request")
    assert pocketbase.calls == []


@pytest.mark.parametrize("campaign_id", ["abc", "ABCDEFGHIJKLMNO", "abc123def456gh'", "x" * 16])
def test_a_campaign_id_that_isnt_a_record_id_is_422(client, signed_in, tripwires, pocketbase, campaign_id):
    body = {**ROUTES["take_home_submit"][2], "campaign_id": campaign_id}
    _assert_typed(_send(client, "take_home_submit", signed_in, body=body), 422, "invalid_request")
    assert pocketbase.calls == []


def test_more_than_32_selected_cases_is_413(client, signed_in, pocketbase, tripwires):
    pocketbase.add(
        "coding_questions",
        slug="many",
        entry={"kind": "function", "name": "f"},
        test_cases=[{"input": {}, "expected": None} for _ in range(33)],
    )
    res = _send(client, "evaluate", signed_in, body={"question_slug": "many", "language": "python", "code": "x"})
    _assert_typed(res, 413, "limit_exceeded")
    assert tripwires == []
    # 32 selected cases run.
    with pytest.raises(Tripped):
        _send(
            client,
            "evaluate",
            signed_in,
            body={"question_slug": "many", "language": "python", "code": "x", "filter": {"indices": list(range(32))}},
        )
    assert tripwires == ["run_one"]


@pytest.mark.parametrize("field, entries", [("tags", [f"t{i}" for i in range(33)]), ("indices", list(range(33)))])
def test_more_than_32_filter_entries_is_413_before_any_lookup(client, signed_in, tripwires, pocketbase, field, entries):
    body = {**ROUTES["evaluate"][2], "filter": {field: entries}}
    _assert_typed(_send(client, "evaluate", signed_in, body=body), 413, "limit_exceeded")
    assert tripwires == [] and pocketbase.calls == []


# ---- step 8: lookups with the caller's token ------------------------------------------


@pytest.mark.parametrize("name", WITH_LOOKUPS)
def test_a_missing_record_is_404_before_execution(client, signed_in, pocketbase, tripwires, name):
    res = _send(client, name, signed_in)
    _assert_typed(res, 404, "not_found")
    assert tripwires == []
    assert all(token == signed_in["Authorization"].split(" ", 1)[1] for token, _p, _q in pocketbase.calls)


def test_a_foreign_campaign_is_404_before_execution(client, signed_in, seeded, tripwires):
    foreign = seeded.add("campaigns", user="u2", hidden=True)
    res = _send(client, "take_home_submit", signed_in, body={**ROUTES["take_home_submit"][2], "campaign_id": foreign["id"]})
    _assert_typed(res, 404, "not_found")
    assert tripwires == []


def test_a_campaign_owned_by_someone_else_is_404_even_if_visible(client, signed_in, seeded, tripwires):
    visible = seeded.add("campaigns", user="u2")
    res = _send(client, "take_home_submit", signed_in, body={**ROUTES["take_home_submit"][2], "campaign_id": visible["id"]})
    _assert_typed(res, 404, "not_found")
    assert tripwires == []


def test_the_callers_own_campaign_is_admitted(client, signed_in, seeded, tripwires):
    own = seeded.add("campaigns", user="u1")
    with pytest.raises(Tripped):
        _send(client, "take_home_submit", signed_in, body={**ROUTES["take_home_submit"][2], "campaign_id": own["id"]})
    assert tripwires == ["run_assignment"]


def test_a_stored_custom_entry_is_422_before_execution(client, signed_in, pocketbase, tripwires):
    pocketbase.add("coding_questions", slug="custom-q", entry={"kind": "custom", "driver": "print(1)"}, test_cases=[])
    res = _send(client, "run", signed_in, body={**ROUTES["run"][2], "question_slug": "custom-q"})
    _assert_typed(res, 422, "invalid_request")
    assert tripwires == []


def test_a_stored_take_home_without_an_entrypoint_is_422(client, signed_in, pocketbase, tripwires):
    pocketbase.add("take_home_assignments", slug="a-1", entrypoint="", harness_files=[])
    _assert_typed(_send(client, "take_home_run", signed_in), 422, "invalid_request")
    assert tripwires == []


@pytest.mark.parametrize(
    "error, status, code",
    [
        (httpx.ConnectError("refused"), 503, "auth_unavailable"),
        (HTTPException(status_code=500, detail="PocketBase error text"), 503, "auth_unavailable"),
        (HTTPException(status_code=401, detail="expired"), 401, "unauthenticated"),
        (HTTPException(status_code=403, detail="no"), 404, "not_found"),
    ],
)
def test_lookup_failures_are_typed_and_never_echo_pocketbase(client, signed_in, monkeypatch, tripwires, error, status, code):
    from routers import runner

    async def failing(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(runner, "pb_get", failing)
    res = _send(client, "run", signed_in)
    _assert_typed(res, status, code)
    assert "PocketBase error text" not in res.text
    assert tripwires == []


# ---- step 9: the replica's in-flight cap ---------------------------------------------------


@pytest.mark.parametrize("name", ALLOCATING)
def test_a_full_replica_is_503_before_execution(client, signed_in, seeded, tripwires, busy, name):
    res = _send(client, name, signed_in)
    _assert_typed(res, 503, "worker_unavailable")
    assert tripwires == []


@pytest.mark.parametrize("name", ["ats_rule", "pdf_health"])
def test_rule_scoring_and_health_skip_the_in_flight_cap(client, signed_in, busy, monkeypatch, name):
    from routers import pdf

    monkeypatch.setattr(pdf, "_sidecar_ok", lambda: True)
    assert _send(client, name, signed_in).status_code == 200


def test_a_slot_is_released_after_the_run(client, signed_in, seeded, tripwires):
    before = admission.pool().in_use()
    with pytest.raises(Tripped):
        _send(client, "run", signed_in)
    assert admission.pool().in_use() == before


def test_the_in_flight_cap_is_the_replica_slot_count():
    assert admission.pool().size == admission.REPLICA_SLOTS == 4


def test_slot_cleanup_runs_off_the_event_loop(monkeypatch):
    pool = admission.pool()
    real_release = pool.release
    cleanup_threads: list[int] = []

    def slow_release(slot):
        cleanup_threads.append(threading.get_ident())
        time.sleep(0.3)
        real_release(slot)

    monkeypatch.setattr(pool, "release", slow_release)

    async def go():
        ticks = 0

        async def tick():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        ticker = asyncio.create_task(tick())
        before = pool.in_use()
        async with admission.allocate():
            assert pool.in_use() == before + 1
        ticker.cancel()
        assert pool.in_use() == before
        return threading.get_ident(), ticks

    loop_thread, ticks = asyncio.run(go())
    assert cleanup_threads and cleanup_threads[0] != loop_thread
    # The loop kept serving while the cleanup ran.
    assert ticks >= 10


def test_a_slot_is_cleaned_up_and_freed_when_the_run_raises(monkeypatch):
    pool = admission.pool()
    released = []
    real_release = pool.release
    monkeypatch.setattr(pool, "release", lambda slot: (released.append(slot.index), real_release(slot)))
    before = pool.in_use()

    async def go():
        async with admission.allocate():
            raise Tripped()

    with pytest.raises(Tripped):
        asyncio.run(go())
    assert len(released) == 1 and pool.in_use() == before


@pytest.mark.parametrize("how", ["move_on_after", "task_group"])
def test_a_request_cancelled_mid_run_still_cleans_up_and_frees_its_slot(monkeypatch, how):
    # anyio cancellation stays in force inside the cancelled scope, so an
    # unshielded await in the cleanup would be cancelled before it started.
    pool = admission.pool()
    released = []
    real_release = pool.release
    monkeypatch.setattr(pool, "release", lambda slot: (released.append(slot.index), real_release(slot)))
    before = pool.in_use()

    async def handler():
        async with admission.allocate():
            await anyio.sleep(10)

    async def go():
        if how == "move_on_after":
            with anyio.move_on_after(0.05):
                await handler()
        else:
            async with anyio.create_task_group() as group:
                group.start_soon(handler)
                await anyio.sleep(0.05)
                group.cancel_scope.cancel()

    anyio.run(go)
    assert len(released) == 1 and pool.in_use() == before


# ---- decision lines --------------------------------------------------------------------


def _decisions(capsys) -> list[dict]:
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    return [line for line in lines if line.get("event") == "decision"]


def test_one_decision_line_per_admitted_request_without_content(client, signed_in, capsys, tripwires):
    capsys.readouterr()
    res = _send(client, "ats_rule", signed_in, body={"data": {"secret-marker": 1}, "job_description": "jd-marker"})
    assert res.status_code == 200
    out = capsys.readouterr().out
    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    (line,) = [entry for entry in lines if entry.get("event") == "decision"]
    assert line["route"] == "/api/ai/ats-rule" and line["method"] == "POST"
    assert line["status"] == 200 and line["tier"] == "standard"
    assert line["quota"] == "skipped" and line["service"] == "runner"
    assert re.fullmatch(r"acct_[0-9a-f]{16}", line["account"])
    assert HEX32.fullmatch(line["correlation_id"])
    assert line["correlation_id"] == res.headers[obs.CORRELATION_HEADER]
    assert "dropped" not in line
    for marker in ("secret-marker", "jd-marker", "test-token-placeholder", '"u1"'):
        assert marker not in out


def test_a_denial_logs_its_code_and_the_anonymous_tier(client, capsys, tripwires):
    capsys.readouterr()
    _send(client, "run")
    (line,) = _decisions(capsys)
    assert line["code"] == "unauthenticated" and line["status"] == 401
    assert line["tier"] == "anonymous" and "account" not in line


def test_routes_outside_admission_are_untouched(client, capsys):
    capsys.readouterr()
    res = client.get("/health")
    assert res.status_code == 200 and res.json() == {"status": "ok"}
    assert _decisions(capsys) == []
    res = client.get("/api/ai/providers")
    assert res.status_code == 401
    assert "code" not in res.json()
