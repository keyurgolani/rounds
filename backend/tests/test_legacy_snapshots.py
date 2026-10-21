"""Legacy Artifact Snapshot creation at the runner (ROUNDS-00A-L04, PR 2).

``POST /api/pdf/snapshots`` through the whole admission chain: the gate
ships off and answers before the account, the request carries ids and the
``updated`` the caller saw and nothing else, steps 6 and 7 run before the
hook is asked, the hook gets the caller's bearer, the runner key, and the
admitted command id, and each of the hook's answers becomes the outcome or
the typed refusal. The hook itself is faked here (httpx.MockTransport);
pocketbase/tests/test_legacy_snapshot_hooks.py tests its decisions and
the harness runs the two together."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest

from app import admission_state, errors, legacy_snapshots
from tests.test_admission import _assert_typed, _decisions, busy, gate_env  # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "pocketbase" / "pb_hooks"
PATH = "/api/pdf/snapshots"
KEY = "0190f000-0000-7000-8000-000000000001"
OTHER_KEY = "0190f000-0000-7000-8000-000000000002"
BODY = {"source_kind": "resume", "source_id": "resumeaaaaaaaa1", "expected_updated": "2026-10-20 10:00:00.000Z"}
CREATED = {"status": "created", "snapshot_id": "snapaaaaaaaaaa1", "content_checksum": "sha256:" + "c" * 64}
REUSED = {**CREATED, "status": "reused"}
INELIGIBLE = {"status": "ineligible", "snapshot_id": None, "content_checksum": None, "reason": "design_out_of_domain"}
ON = {"ROUNDS_GATE_LEGACY_SNAPSHOT_CREATE": "enabled"}
ENFORCE = {**ON, "ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "enforce", "ROUNDS_GATE_ENFORCE_QUOTA": "enforce"}
# A test value, not a deployment's.
RUNNER_KEY = "test-runner-key-" + "0" * 32


def hook_error(status: int, code: str) -> httpx.Response:
    return httpx.Response(status, json={"v": "legacy-snapshot/v1", "error": code})


class FakeHook:
    """PocketBase's POST /api/rounds/legacy-snapshots, answering in turn."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.answers: list[httpx.Response | Exception] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append({
            "path": request.url.path,
            "authorization": request.headers.get("authorization"),
            "runner_key": request.headers.get(admission_state.RUNNER_KEY_HEADER),
            "json": json.loads(request.content),
        })
        answer = self.answers.pop(0) if self.answers else httpx.Response(201, json=CREATED)
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def hook(monkeypatch):
    fake = FakeHook()
    real = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        return real(*args, transport=httpx.MockTransport(fake.handler), **kwargs)

    monkeypatch.setattr(legacy_snapshots.httpx, "AsyncClient", client_factory)
    return fake


@pytest.fixture
def runner_key(monkeypatch):
    monkeypatch.setenv(admission_state.RUNNER_KEY_ENV, RUNNER_KEY)
    return RUNNER_KEY


def post(client, headers=None, body=None, key: str | None = KEY, **kwargs):
    sent = dict(headers or {})
    if key is not None:
        sent["Idempotency-Key"] = key
    return client.post(PATH, json=BODY if body is None else body, headers=sent, **kwargs)


# ---- the gate ships off -------------------------------------------------------------


@pytest.mark.parametrize("bearer", [None, "Bearer test-token-placeholder", "Bearer not-a-token"])
def test_the_route_ships_off_and_answers_before_the_account(client, gate_env, signed_in, hook, admission_store, bearer):
    gate_env({})
    res = post(client, {"Authorization": bearer} if bearer else {})
    _assert_typed(res, 503, "route_disabled")
    assert hook.calls == [] and admission_store.calls == []


# ---- what the request may carry -------------------------------------------------------


def test_without_a_bearer_it_is_401(client, gate_env, hook, admission_store):
    gate_env(ON)
    _assert_typed(post(client), 401, "unauthenticated")
    assert hook.calls == [] and admission_store.calls == []


@pytest.mark.parametrize("change", [
    {"html": "<p>x</p>"},
    {"template_id": "modern"},
    {"design": {}},
    {"markup": "<p>x</p>"},
    {"command_id": KEY},
    {"source_kind": "draft"},
    {"source_id": "RESUMEAAAAAAAA1"},
    {"source_id": "short"},
    {"expected_updated": "yesterday"},
    {"expected_updated": "2026-10-20T10:00:00Z"},
])
def test_the_request_names_a_source_and_its_updated_and_nothing_else(
    client, gate_env, signed_in, hook, admission_store, runner_key, change
):
    gate_env(ON)
    _assert_typed(post(client, signed_in, body={**BODY, **change}), 422, "invalid_request")
    # Step 5 comes before steps 6 and 7, and the hook is never asked.
    assert hook.calls == [] and admission_store.calls == []


def test_a_body_over_4_kib_is_413_before_the_account(client, gate_env, hook, admission_store):
    gate_env(ON)
    res = client.post(PATH, content=b"{" + b" " * (4 * 1024) + b"}", headers={"Content-Type": "application/json"})
    _assert_typed(res, 413, "payload_too_large")
    assert hook.calls == [] and admission_store.calls == []


# ---- through the hook -------------------------------------------------------------------


def test_the_hook_gets_the_bearer_the_runner_key_and_the_admitted_command(
    client, gate_env, signed_in, hook, admission_store, runner_key
):
    gate_env(ENFORCE)
    res = post(client, signed_in)
    assert res.status_code == 201 and res.json() == CREATED
    (call,) = hook.calls
    assert call["path"] == legacy_snapshots.HOOK_PATH
    assert call["authorization"] == signed_in["Authorization"] and call["runner_key"] == RUNNER_KEY
    assert call["json"] == {**BODY, "command_id": KEY}
    (admitted,) = admission_store.called("admit")
    assert admitted["operation"] == "snapshot_create"
    assert admitted["wall_seconds"] == legacy_snapshots.MATERIALIZE_TIMEOUT_S and admitted["key"] == KEY
    (finished,) = admission_store.called("finish")
    assert finished["outcome"] == "completed" and finished["result"] == {"status": 201, "body": CREATED}


def test_a_completed_command_replays_without_asking_the_hook(client, gate_env, signed_in, hook, runner_key):
    gate_env(ENFORCE)
    first = post(client, signed_in)
    again = post(client, signed_in)
    assert again.status_code == 201 and again.json() == first.json()
    assert again.headers[errors.REPLAY_HEADER] == "true"
    assert len(hook.calls) == 1


@pytest.mark.parametrize("answer, status, body", [
    (httpx.Response(201, json=CREATED), 201, CREATED),
    (httpx.Response(200, json=REUSED), 200, REUSED),
    (httpx.Response(200, json=INELIGIBLE), 200, INELIGIBLE),
])
def test_each_outcome_passes_through_as_the_hook_answered_it(
    client, gate_env, signed_in, hook, runner_key, answer, status, body
):
    gate_env(ON)
    hook.answers = [answer]
    res = post(client, signed_in)
    assert res.status_code == status and res.json() == body


@pytest.mark.parametrize("answer, status, code", [
    (hook_error(404, "not_found"), 404, "not_found"),
    (httpx.Response(409, json={"status": "conflict", "snapshot_id": None, "content_checksum": None}), 409,
     "snapshot_conflict"),
    (hook_error(429, "snapshot_quota_exceeded"), 429, "snapshot_quota_exceeded"),
    (hook_error(503, "route_disabled"), 503, "route_disabled"),
    (httpx.Response(401, json={"code": 401, "message": "The request requires valid record authorization token."}),
     401, "unauthenticated"),
    (hook_error(503, "materializer_unavailable"), 503, "materializer_unavailable"),
    (hook_error(503, "unavailable"), 503, "materializer_unavailable"),
    (hook_error(503, "unconfigured"), 503, "materializer_unavailable"),
    (hook_error(403, "forbidden"), 503, "materializer_unavailable"),
    (hook_error(400, "invalid_request"), 503, "materializer_unavailable"),
    (httpx.Response(500, text="Traceback: something inside PocketBase"), 503, "materializer_unavailable"),
    # Outcomes off the contract's shape.
    (httpx.Response(200, json=CREATED), 503, "materializer_unavailable"),
    (httpx.Response(201, json={**CREATED, "markup": "<p>x</p>"}), 503, "materializer_unavailable"),
    (httpx.Response(201, json={**CREATED, "snapshot_id": "../x"}), 503, "materializer_unavailable"),
    (httpx.Response(201, json={**CREATED, "content_checksum": "md5:x"}), 503, "materializer_unavailable"),
    (httpx.Response(200, json={**INELIGIBLE, "reason": "a reason it never gives"}), 503, "materializer_unavailable"),
    (httpx.Response(200, json={**INELIGIBLE, "snapshot_id": "snapaaaaaaaaaa1"}), 503, "materializer_unavailable"),
    (httpx.Response(200, json=[CREATED]), 503, "materializer_unavailable"),
    (httpx.Response(201, text="not json"), 503, "materializer_unavailable"),
    (httpx.ConnectError("refused"), 503, "materializer_unavailable"),
    (httpx.ReadTimeout("slow"), 503, "materializer_unavailable"),
])
def test_each_refusal_is_typed_and_repeats_nothing_from_pocketbase(
    client, gate_env, signed_in, hook, runner_key, answer, status, code
):
    gate_env(ON)
    hook.answers = [answer]
    res = post(client, signed_in)
    _assert_typed(res, status, code)
    assert "Traceback" not in res.text and "PocketBase" not in res.text


def test_a_hook_that_never_answers_is_cut_off(client, gate_env, signed_in, monkeypatch, runner_key):
    gate_env(ON)
    monkeypatch.setattr(legacy_snapshots, "TIMEOUT_S", 0.2)

    async def stalled(_request):
        import anyio

        await anyio.sleep(5)
        return httpx.Response(201, json=CREATED)

    real = httpx.AsyncClient
    monkeypatch.setattr(legacy_snapshots.httpx, "AsyncClient",
                        lambda *a, **k: real(*a, transport=httpx.MockTransport(stalled), **k))
    _assert_typed(post(client, signed_in), 503, "materializer_unavailable")


def test_a_runner_without_its_key_asks_nothing(client, gate_env, signed_in, hook, monkeypatch):
    gate_env(ON)
    monkeypatch.delenv(admission_state.RUNNER_KEY_ENV, raising=False)
    _assert_typed(post(client, signed_in), 503, "materializer_unavailable")
    assert hook.calls == []


@pytest.mark.parametrize("answer", [
    httpx.Response(409, json={"status": "conflict", "snapshot_id": None, "content_checksum": None}),
    hook_error(503, "materializer_unavailable"),
    httpx.ConnectError("refused"),
])
def test_a_same_key_retry_after_conflict_or_an_outage_runs_again(
    client, gate_env, signed_in, hook, admission_store, runner_key, answer
):
    gate_env(ENFORCE)
    hook.answers = [answer, httpx.Response(201, json=CREATED)]
    assert post(client, signed_in).status_code in (409, 503)
    # Nothing ran before the refusal, so the lease ends denied: the
    # command stays retryable and the charge comes back.
    assert [f["outcome"] for f in admission_store.called("finish")] == ["denied"]
    again = post(client, signed_in)
    assert again.status_code == 201 and again.json() == CREATED
    assert [c["json"]["command_id"] for c in hook.calls] == [KEY, KEY]


def test_without_a_recorded_command_no_command_id_goes_to_the_hook(
    client, gate_env, signed_in, hook, admission_store, runner_key
):
    # Idempotency off: admission records no command.
    gate_env({**ON, "ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "off", "ROUNDS_GATE_ENFORCE_QUOTA": "off"})
    assert post(client, signed_in).status_code == 201
    # Observe mode with a key already used for another request: the
    # request runs, but its key names that other command.
    gate_env({**ON, "ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "observe"})
    assert post(client, signed_in, key=OTHER_KEY).status_code == 201
    assert post(client, signed_in, body={**BODY, "source_id": "resumebbbbbbbb1"}, key=OTHER_KEY).status_code == 201
    assert [c["json"].get("command_id") for c in hook.calls] == [None, OTHER_KEY, None]


def test_the_route_takes_no_in_flight_slot(client, gate_env, signed_in, hook, runner_key, busy):
    gate_env(ON)
    assert post(client, signed_in).status_code == 201


def test_one_decision_line_names_the_refusal_and_repeats_no_ids(
    client, gate_env, signed_in, hook, runner_key, capsys
):
    gate_env(ON)
    hook.answers = [httpx.Response(409, json={"status": "conflict", "snapshot_id": None, "content_checksum": None})]
    capsys.readouterr()
    post(client, signed_in)
    out = capsys.readouterr().out
    (line,) = _decisions_from(out)
    assert line["route"] == PATH and line["status"] == 409 and line["code"] == "snapshot_conflict"
    assert BODY["source_id"] not in out and KEY not in out


def _decisions_from(out: str) -> list[dict]:
    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    return [line for line in lines if line.get("event") == "decision"]


# ---- the runner and the hook stay in step ------------------------------------------------

HOOK_CONSTANTS = r"""
const path = require("path");
globalThis.BadRequestError = class extends Error {};
globalThis.UnauthorizedError = class extends Error {};
const snapshots = require(path.join(process.argv[1], "legacy_snapshots.js"));
const admission = require(path.join(process.argv[1], "admission.js"));
process.stdout.write(JSON.stringify({
  version: snapshots.VERSION,
  timeout: snapshots.MATERIALIZE_TIMEOUT_S,
  reasons: snapshots.REASONS,
  charge: admission.OPERATIONS[snapshots.OPERATION],
}));
"""


def _hook_constants() -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    out = subprocess.run([node, "-e", HOOK_CONSTANTS, str(HOOKS)], capture_output=True, text=True, timeout=60,
                         check=True)
    return json.loads(out.stdout)


def test_the_runner_and_the_hook_agree_on_the_contract():
    hook = _hook_constants()
    assert hook["version"] == legacy_snapshots.VERSION
    assert hook["timeout"] == legacy_snapshots.MATERIALIZE_TIMEOUT_S
    assert hook["charge"] == [legacy_snapshots.MATERIALIZE_TIMEOUT_S] * 2
    assert set(hook["reasons"]) == legacy_snapshots.REASONS
    route = (HOOKS / "legacy_snapshots.pb.js").read_text()
    assert f'"{legacy_snapshots.HOOK_PATH}"' in route
    source = (HOOKS / "legacy_snapshots.js").read_text()
    # The request patterns, written the same on both sides.
    assert f"const RECORD_ID = /{legacy_snapshots.RECORD_ID}/;" in source
    assert f"const PB_DATETIME = /{legacy_snapshots.PB_DATETIME}/;" in source


def test_the_call_ends_inside_the_leases_window():
    admitted = legacy_snapshots.MATERIALIZE_TIMEOUT_S
    grace = int(re.search(r"const LEASE_GRACE_S = (\d+);", (HOOKS / "admission.js").read_text()).group(1))
    assert legacy_snapshots.MATERIALIZE_TIMEOUT_S < legacy_snapshots.TIMEOUT_S < admitted + grace
