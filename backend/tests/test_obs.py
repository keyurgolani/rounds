"""Observability kit (ROUNDS-00A-L01): correlation ids, account
pseudonyms, and the allowlisted decision line."""
import hashlib
import json
import re

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from app import obs
from routers import ai

HEX32 = re.compile(r"[0-9a-f]{32}")
CID = "0123456789abcdef0123456789abcdef"


@pytest.fixture(autouse=True)
def _fresh_pseudonym_key():
    obs.reset_pseudonym_key()
    yield
    obs.reset_pseudonym_key()


def _probe_app():
    app = FastAPI()
    app.add_middleware(obs.CorrelationIdMiddleware)

    @app.get("/sync")
    def sync_probe(request: Request):
        return {
            "state": request.state.correlation_id,
            "bound": obs.current_correlation_id(),
            "request_id": ai._request_id(),
        }

    @app.get("/async")
    async def async_probe(request: Request):
        return {"state": request.state.correlation_id, "bound": obs.current_correlation_id()}

    @app.get("/stream")
    def stream():
        return StreamingResponse(iter([b"data: {}\n\n"]), media_type="text/event-stream")

    return app


# ---- correlation ids -----------------------------------------------------


def test_correlation_ids_are_32_hex_and_unique():
    ids = {obs.new_correlation_id() for _ in range(64)}
    assert len(ids) == 64
    assert all(HEX32.fullmatch(i) for i in ids)


@pytest.mark.parametrize("value", ["0" * 31, "0" * 33, "A" * 32, "g" * 32, "0" * 31 + "\n", None, 7])
def test_is_correlation_id_accepts_only_32_lowercase_hex(value):
    assert obs.is_correlation_id("0" * 32)
    assert not obs.is_correlation_id(value)


def test_outside_a_request_correlation_id_is_fresh():
    assert obs.current_correlation_id() is None
    assert HEX32.fullmatch(obs.correlation_id())
    assert obs.correlation_id() != obs.correlation_id()


@pytest.mark.parametrize("path", ["/sync", "/async"])
def test_one_correlation_id_covers_header_state_and_context(path):
    with TestClient(_probe_app()) as client:
        res = client.get(path)
    header = res.headers[obs.CORRELATION_HEADER]
    assert HEX32.fullmatch(header)
    body = res.json()
    assert body["state"] == header
    assert body["bound"] == header


def test_request_id_in_ai_errors_matches_the_correlation_header():
    with TestClient(_probe_app()) as client:
        res = client.get("/sync")
    assert res.json()["request_id"] == res.headers[obs.CORRELATION_HEADER]


def test_each_request_gets_its_own_id_and_the_context_resets():
    with TestClient(_probe_app()) as client:
        first = client.get("/sync").headers[obs.CORRELATION_HEADER]
        second = client.get("/sync").headers[obs.CORRELATION_HEADER]
    assert first != second
    assert obs.current_correlation_id() is None


def test_a_client_supplied_correlation_id_is_never_used():
    with TestClient(_probe_app()) as client:
        res = client.get("/sync", headers={obs.CORRELATION_HEADER: CID})
    assert res.headers[obs.CORRELATION_HEADER] != CID
    assert res.headers.get_list(obs.CORRELATION_HEADER) == [res.json()["state"]]


def test_streaming_responses_carry_the_correlation_header():
    with TestClient(_probe_app()) as client:
        res = client.get("/stream")
    assert HEX32.fullmatch(res.headers[obs.CORRELATION_HEADER])
    assert res.text == "data: {}\n\n"


# ---- account pseudonyms -------------------------------------------------


def test_account_pseudonym_is_keyed_stable_and_never_the_id(monkeypatch):
    monkeypatch.setenv("AI_KEY_SECRET", "test-placeholder-secret-one")
    first = obs.account_pseudonym("user123")
    assert re.fullmatch(r"acct_[0-9a-f]{16}", first)
    assert obs.account_pseudonym("user123") == first
    assert obs.account_pseudonym("user456") != first
    assert "user123" not in first
    # Keyed, so it isn't a plain digest anyone could recompute.
    assert first[5:] != hashlib.sha256(b"user123").hexdigest()[:16]

    monkeypatch.setenv("AI_KEY_SECRET", "test-placeholder-secret-two")
    obs.reset_pseudonym_key()
    assert obs.account_pseudonym("user123") != first


def test_account_pseudonym_without_a_secret_holds_only_within_the_process(monkeypatch, caplog):
    monkeypatch.delenv("AI_KEY_SECRET", raising=False)
    with caplog.at_level("WARNING"):
        first = obs.account_pseudonym("user123")
    assert obs.account_pseudonym("user123") == first
    assert any("AI_KEY_SECRET is unset" in r.getMessage() for r in caplog.records)
    obs.reset_pseudonym_key()
    assert obs.account_pseudonym("user123") != first


@pytest.mark.parametrize("value", [None, ""])
def test_account_pseudonym_of_no_account_is_none(value):
    assert obs.account_pseudonym(value) is None


# ---- allowlisted lines --------------------------------------------------

SENSITIVE = {
    "source": "def solve():\n    return 42",
    "stdout": "candidate output line",
    "stderr": "Traceback (most recent call last)",
    "html": "<html><body><script>void 0</script></body></html>",
    "authorization": "Bearer test-token-placeholder",
    "payload": {"messages": [{"role": "user", "content": "prompt text"}]},
    "account_id": "user123",
    "email": "person@example.test",
}


def test_decision_lines_drop_every_field_outside_the_allowlist():
    record = obs.build("decision", correlation_id=CID, route="/api/run", **SENSITIVE)
    assert set(record) == {"v", "event", "correlation_id", "route", "dropped"}
    assert record["dropped"] == sorted(SENSITIVE)
    line = json.dumps(record)
    for needle in ("solve", "candidate output", "Traceback", "<html", "Bearer", "prompt text", "user123", "person@"):
        assert needle not in line


@pytest.mark.parametrize(
    "field,value",
    [
        ("correlation_id", "not-a-correlation-id"),
        ("account", "user123"),
        ("route", "/api/run?code=print(1)"),
        ("route", "/api/" + "a" * 200),
        ("route", "<script>"),
        ("method", "TRACE"),
        ("status", 99),
        ("status", True),
        ("status", "200"),
        ("code", "Quota exceeded!"),
        ("tier", "admin"),
        ("quota", "free"),
        ("latency_ms", -1),
        ("service", "database"),
        ("gates", {"RUN": {"value": "enabled", "source": "env", "raw": " Enabled "}}),
        ("gates", {"RUN": {"value": "en abled", "source": "env"}}),
        ("gates", {"RUN": {"value": "enabled", "source": "header"}}),
    ],
)
def test_values_that_fail_their_field_check_are_dropped(field, value):
    record = obs.build("decision", **{field: value})
    assert field not in record
    assert record["dropped"] == [field]


def test_dropped_names_never_echo_odd_field_names():
    record = obs.build("decision", **{"Authorization: Bearer test-token-placeholder": "x"})
    assert record["dropped"] == ["unnamed"]
    assert "Bearer" not in json.dumps(record)


def test_none_values_are_left_out_quietly():
    record = obs.build("decision", correlation_id=CID, account=None)
    assert record == {"v": obs.KIT_VERSION, "event": "decision", "correlation_id": CID}


def test_valid_decision_fields_pass_through():
    fields = {
        "correlation_id": CID,
        "account": "acct_0123456789abcdef",
        "tier": "demo",
        "route": "/api/take-home/submit",
        "method": "POST",
        "status": 429,
        "code": "demo_limit_reached",
        "quota": "demo_limit",
        "latency_ms": 12,
        "service": "runner",
    }
    assert obs.build("decision", **fields) == {"v": "obs/v1", "event": "decision", **fields}


def test_unknown_events_are_refused():
    with pytest.raises(ValueError):
        obs.build("request_body", correlation_id=CID)


def test_emit_writes_one_compact_sorted_json_line(capsys):
    record = obs.emit(
        "decision",
        correlation_id=CID,
        route="/api/run",
        method="POST",
        status=429,
        code="quota_exceeded",
        stdout="candidate output line",
    )
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    assert lines[0] == json.dumps(record, separators=(",", ":"), sort_keys=True)
    assert json.loads(lines[0])["dropped"] == ["stdout"]
    assert "candidate output" not in lines[0]
