"""PDF proxy (ROUNDS-00A-L01): admitted, a failed render never repeats
the sidecar's text, and health answers only ``{"status"}``."""
from __future__ import annotations

import io
import urllib.error

import pytest

SIDECAR_TEXT = "sidecar-internal-detail at /srv/render.js:42"


class FakeResponse:
    def __init__(self, status=200, body=b"%PDF-1.7 test", content_type="application/pdf"):
        self.status = status
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def sidecar(monkeypatch):
    from routers import pdf

    state = {"answer": FakeResponse(), "calls": []}

    def urlopen(request, timeout=None):
        state["calls"].append(getattr(request, "full_url", request))
        answer = state["answer"]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(pdf.urllib.request, "urlopen", urlopen)
    return state


def test_a_signed_in_render_returns_the_pdf(client, signed_in, sidecar):
    res = client.post("/api/pdf/render", json={"html": "<p>hi</p>", "margin_mm": 5}, headers=signed_in)
    assert res.status_code == 200
    assert res.content == b"%PDF-1.7 test"
    assert res.headers["content-type"].startswith("application/pdf")


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.HTTPError("http://pdf-renderer:4000/render", 500, "x", {}, io.BytesIO(SIDECAR_TEXT.encode())),
        urllib.error.HTTPError("http://pdf-renderer:4000/render", 400, "x", {}, io.BytesIO(SIDECAR_TEXT.encode())),
        urllib.error.HTTPError("http://pdf-renderer:4000/render", 422, "x", {}, io.BytesIO(SIDECAR_TEXT.encode())),
        urllib.error.URLError(SIDECAR_TEXT),
        urllib.error.URLError(TimeoutError(SIDECAR_TEXT)),
        ConnectionResetError(SIDECAR_TEXT),
    ],
)
def test_a_failed_render_is_a_typed_503_without_sidecar_text(client, signed_in, sidecar, failure):
    sidecar["answer"] = failure
    res = client.post("/api/pdf/render", json={"html": "<p>hi</p>"}, headers=signed_in)
    assert res.status_code == 503
    body = res.json()
    assert set(body) == {"detail", "code", "correlation_id"}
    assert body["code"] == "worker_unavailable"
    assert SIDECAR_TEXT not in res.text and "pdf-renderer" not in res.text


@pytest.mark.parametrize(
    "failure",
    [
        # Connected, but no PDF within the runner's wait.
        TimeoutError(SIDECAR_TEXT),
        # The sidecar's own answer for a document that ran out of time.
        urllib.error.HTTPError("http://pdf-renderer:4000/render", 422, "x", {},
                               io.BytesIO(b'{"error":"render_timeout"}')),
    ],
)
def test_a_render_that_runs_out_of_time_is_a_typed_422_without_sidecar_text(client, signed_in, sidecar, failure):
    sidecar["answer"] = failure
    res = client.post("/api/pdf/render", json={"html": "<p>hi</p>"}, headers=signed_in)
    assert res.status_code == 422
    body = res.json()
    assert set(body) == {"detail", "code", "correlation_id"}
    assert body["code"] == "render_timeout"
    assert SIDECAR_TEXT not in res.text and "pdf-renderer" not in res.text


def test_an_anonymous_render_never_reaches_the_sidecar(client, sidecar):
    res = client.post("/api/pdf/render", json={"html": "<p>hi</p>"})
    assert res.status_code == 401
    assert sidecar["calls"] == []


def test_health_answers_only_its_status(client, signed_in, sidecar):
    res = client.get("/api/pdf/health", headers=signed_in)
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "failure",
    [urllib.error.URLError(SIDECAR_TEXT), ConnectionRefusedError(SIDECAR_TEXT), FakeResponse(status=500)],
)
def test_an_unreachable_sidecar_is_503_with_only_its_status(client, signed_in, sidecar, failure):
    sidecar["answer"] = failure
    res = client.get("/api/pdf/health", headers=signed_in)
    assert res.status_code == 503
    assert res.json() == {"status": "unavailable"}
    assert SIDECAR_TEXT not in res.text


def test_anonymous_health_is_denied(client, sidecar):
    res = client.get("/api/pdf/health")
    assert res.status_code == 401
    assert sidecar["calls"] == []
