"""Public share requests leave no access-log line (ROUNDS-00B-L04,
app/access_log.py). The filter is checked on uvicorn's own access logging,
through a real server on 127.0.0.1, and on the paths it decides by."""
from __future__ import annotations

import logging
import socket
import threading
import time

import httpx
import pytest
import uvicorn
from fastapi import FastAPI

from app import access_log

SECRET_SEGMENT = "sd1_" + "Q" * 22


@pytest.mark.parametrize(
    "path",
    [
        "/r", "/r/", "/r/" + SECRET_SEGMENT, "/R/" + SECRET_SEGMENT, "/r?x=1",
        "/api/share/by-token/" + SECRET_SEGMENT, "/api/share/by-token/" + SECRET_SEGMENT + "?q=1",
        "/API/Share/By-Token/" + SECRET_SEGMENT, "/api/share/by-token", "/api/share/by-token/",
        "//api//share//by-token//" + SECRET_SEGMENT, "/api/share/x/../by-token/" + SECRET_SEGMENT,
        "/api/share/by%2Dtoken/" + SECRET_SEGMENT, "/api%2Fshare%2Fby-token%2F" + SECRET_SEGMENT,
        "/api/share/resolve", "/api/share/resolve/", "/API/SHARE/RESOLVE",
    ],
)
def test_public_share_paths_are_recognised_however_they_are_spelled(path):
    assert access_log.is_public_share_path(path)


@pytest.mark.parametrize(
    "path",
    ["/", "/health", "/ready", "/api/share", "/api/share/", "/api/share/capabilities", "/api/run", "/resumes",
     "/rx", "/api/share/resolver", "/api/share/by-tokens", "/api/sharex/by-token/x", "/api/pdf/render"],
)
def test_other_paths_keep_their_line(path):
    assert not access_log.is_public_share_path(path)


def _record(path: str) -> logging.LogRecord:
    # The call uvicorn's protocols make for each request (0.30).
    return logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                             ("203.0.113.7:51234", "GET", path, "1.1", 404), None)


def test_the_filter_drops_a_share_requests_line_and_keeps_the_rest():
    f = access_log.PublicShareFilter()
    assert f.filter(_record("/api/share/by-token/" + SECRET_SEGMENT)) is False
    assert f.filter(_record("/api/share/resolve")) is False
    assert f.filter(_record("/api/run")) is True


def test_the_filter_reads_the_request_line_when_the_arguments_differ():
    f = access_log.PublicShareFilter()
    record = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1,
                               '203.0.113.7:1 - "GET /api/share/by-token/%s HTTP/1.1" 404', (SECRET_SEGMENT,), None)
    assert f.filter(record) is False
    kept = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, "server started", None, None)
    assert f.filter(kept) is True


def test_install_adds_the_filter_once():
    logger = logging.getLogger("test.access.install")
    first = access_log.install(logger)
    assert access_log.install(logger) is first
    assert [f for f in logger.filters if isinstance(f, access_log.PublicShareFilter)] == [first]
    logger.removeFilter(first)


# ---- through uvicorn --------------------------------------------------------


class _Lines(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/share/by-token/{token}")
    def read(token: str):
        return {"ok": True}

    @app.post("/api/share/resolve")
    def resolve():
        return {"ok": True}

    @app.get("/api/run")
    def other():
        return {"ok": True}

    return app


@pytest.fixture
def served():
    """A uvicorn server on 127.0.0.1 with the filter installed, and the
    access lines it wrote. Stopped afterwards."""
    logger = logging.getLogger("uvicorn.access")
    lines = _Lines()
    logger.addHandler(lines)
    old_level = logger.level
    logger.setLevel(logging.INFO)
    installed = access_log.install()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    config = uvicorn.Config(_app(), log_config=None, access_log=True, lifespan="off")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started
    try:
        yield f"http://127.0.0.1:{port}", lines
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()
        logger.removeHandler(lines)
        logger.removeFilter(installed)
        logger.setLevel(old_level)


def test_uvicorn_writes_no_line_for_a_public_share_request(served):
    base, lines = served
    with httpx.Client(base_url=base) as http:
        assert http.get(f"/api/share/by-token/{SECRET_SEGMENT}").status_code == 200
        assert http.get(f"/API/SHARE/BY-TOKEN/{SECRET_SEGMENT}").status_code == 404
        assert http.post("/api/share/resolve", json={"token": SECRET_SEGMENT}).status_code == 200
        assert http.get("/api/run").status_code == 200
    deadline = time.monotonic() + 5
    while not lines.lines and time.monotonic() < deadline:
        time.sleep(0.01)
    # The control: the one other request is logged, with its address.
    assert len(lines.lines) == 1 and "/api/run" in lines.lines[0] and "127.0.0.1" in lines.lines[0]
    joined = "\n".join(lines.lines)
    assert SECRET_SEGMENT not in joined and "share" not in joined.lower()
