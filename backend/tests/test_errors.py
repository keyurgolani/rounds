"""Typed error envelope (ROUNDS-00A-L01, admission/v1)."""
import json
import re

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import errors, obs

HEX32 = re.compile(r"[0-9a-f]{32}")


def _app():
    app = FastAPI()
    app.add_middleware(obs.CorrelationIdMiddleware)
    errors.install(app)

    @app.post("/api/run")
    def limited():
        raise errors.TypedError("quota_exceeded", "You've reached the limit for now.", retry_after=30)

    @app.get("/api/items/{item_id}")
    def not_permitted(item_id: str):
        raise errors.TypedError("not_permitted", "This isn't available for this account.")

    @app.get("/api/override")
    def override():
        raise errors.TypedError("route_disabled", "This is turned off.", status=410)

    @app.get("/api/legacy")
    def legacy():
        raise HTTPException(status_code=404, detail="Not found.")

    return app


@pytest.fixture
def client():
    with TestClient(_app()) as c:
        yield c


def test_a_typed_error_answers_exactly_detail_code_and_correlation_id(client):
    res = client.post("/api/run")
    assert res.status_code == 429
    body = res.json()
    assert tuple(body) == errors.ENVELOPE_KEYS
    assert body["code"] == "quota_exceeded"
    assert body["detail"] == "You've reached the limit for now."
    assert isinstance(body["detail"], str)
    assert HEX32.fullmatch(body["correlation_id"])


def test_the_body_correlation_id_matches_the_header(client):
    res = client.post("/api/run")
    assert res.headers.get_list(obs.CORRELATION_HEADER) == [res.json()["correlation_id"]]


def test_retry_after_is_sent_only_when_set(client):
    assert client.post("/api/run").headers["Retry-After"] == "30"
    assert "Retry-After" not in client.get("/api/items/abc").headers


def test_the_status_follows_the_code_unless_overridden(client):
    assert client.get("/api/items/abc").status_code == errors.CODES["not_permitted"]
    assert client.get("/api/override").status_code == 410


def test_a_typed_error_writes_one_decision_line_without_request_content(client, capsys):
    capsys.readouterr()
    res = client.get("/api/items/private-path-value")
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    decisions = [line for line in lines if line["event"] == "decision"]
    assert decisions == [
        {
            "v": obs.KIT_VERSION,
            "event": "decision",
            "correlation_id": res.json()["correlation_id"],
            "route": "/api/items/{item_id}",
            "method": "GET",
            "status": 403,
            "code": "not_permitted",
        }
    ]
    assert "private-path-value" not in json.dumps(decisions)


def test_legacy_http_errors_keep_their_shape_and_gain_the_header(client):
    res = client.get("/api/legacy")
    assert res.status_code == 404
    assert res.json() == {"detail": "Not found."}
    assert HEX32.fullmatch(res.headers[obs.CORRELATION_HEADER])


@pytest.mark.parametrize(
    "kwargs",
    [
        {"code": "made_up_code", "detail": "Nope."},
        {"code": "quota_exceeded", "detail": ""},
        {"code": "quota_exceeded", "detail": "   "},
        {"code": "quota_exceeded", "detail": "Wait.", "retry_after": -1},
        {"code": "quota_exceeded", "detail": "Wait.", "retry_after": True},
        {"code": "quota_exceeded", "detail": "Wait.", "retry_after": 1.5},
    ],
)
def test_typed_errors_refuse_unregistered_codes_and_bad_parts(kwargs):
    code = kwargs.pop("code")
    detail = kwargs.pop("detail")
    with pytest.raises(ValueError):
        errors.TypedError(code, detail, **kwargs)


def test_every_code_is_snake_case_with_an_error_status():
    for code, status in errors.CODES.items():
        assert re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code)
        assert 400 <= status <= 599


def test_the_runner_app_installs_the_envelope_and_correlation_ids():
    from main import app

    assert errors.TypedError in app.exception_handlers
    with TestClient(app) as c:
        res = c.get("/health", headers={"Origin": "http://frontend.test"})
    assert res.json() == {"status": "ok"}
    assert HEX32.fullmatch(res.headers[obs.CORRELATION_HEADER])
    exposed = {h.strip().lower() for h in res.headers["access-control-expose-headers"].split(",")}
    assert {"retry-after", obs.CORRELATION_HEADER.lower()} <= exposed
