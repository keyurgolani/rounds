"""Self-test: the context's clients count every request, record the
routes they exercise, declare a body size without sending it, and turn
connection failures into typed answers (issue #8, Required tests Unit)."""
from __future__ import annotations

import http.client
import json
import socket
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from conformance.budget import Budget
from conformance.context import TIMEOUT, UNREACHABLE, CountingClient, RouteLog, RunnerClient

CAP = 1024


@contextmanager
def server(wait_for_body: bool = False):
    """A runner stand-in: a declared body over CAP gets the typed 413 from
    the header alone, unless ``wait_for_body``, when it reads the body
    first, as a runner without the cap would."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, status, body):
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            if length > CAP and not wait_for_body:
                self._send(413, {"detail": "x", "code": "payload_too_large", "correlation_id": "0" * 32})
                self.close_connection = True
                return
            self.rfile.read(length)
            self._send(200, {"ok": True})

        def do_GET(self):  # noqa: N802
            self._send(200, {"status": "ok"})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()


def _client(base: str, budget=None, timeout: float = 5.0) -> RunnerClient:
    return RunnerClient(base, budget or Budget(10, 60), RouteLog(), timeout=timeout)


def test_a_declared_size_over_the_cap_is_answered_from_the_header():
    with server() as base:
        client = _client(base)
        got = client.declare("POST", "/api/run", CAP + 1)
    assert (got.status, got.body["code"], got.error) == (413, "payload_too_large", "")
    assert client.log.routes == ["POST /api/run"]
    assert client.budget.requests == 1


def test_a_runner_that_waits_for_the_body_times_out_as_a_typed_answer():
    with server(wait_for_body=True) as base:
        got = _client(base).declare("POST", "/api/run", CAP + 1, timeout=0.5)
    assert (got.status, got.error) == (0, TIMEOUT)


def test_a_refused_connection_is_a_typed_answer_not_an_exception():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    got = _client(f"http://127.0.0.1:{port}", timeout=2).request("GET", "/health")
    assert got.status == 0 and got.error
    got = _client(f"http://127.0.0.1:{port}", timeout=2).declare("POST", "/api/run", 10)
    assert got.status == 0 and got.error


@pytest.mark.parametrize("failure", [socket.timeout("timed out"), ConnectionRefusedError(61, "refused")],
                         ids=["connect-timeout", "refused"])
def test_both_clients_type_a_failed_connection_the_same(monkeypatch, failure):
    def no_connection(self):
        raise failure

    monkeypatch.setattr(http.client.HTTPConnection, "connect", no_connection)
    client = _client("http://127.0.0.1:9", timeout=1)
    assert client.declare("POST", "/api/run", CAP + 1).error == UNREACHABLE
    assert client.request("GET", "/health").error == UNREACHABLE
    # Only a connection that got no answer is a timeout.
    assert UNREACHABLE != TIMEOUT


def test_requests_are_counted_and_routes_recorded_once_each():
    with server() as base:
        client = _client(base)
        client.request("GET", "/health")
        client.request("GET", "/health?x=1")
        client.request("POST", "/api/run", json_body={"a": 1})
    assert client.budget.requests == 3
    assert client.log.routes == ["GET /health", "POST /api/run"]


def test_the_request_cap_is_enforced_by_the_client():
    from conformance.budget import BudgetExceeded

    with server() as base:
        client = _client(base, Budget(1, 60))
        client.request("GET", "/health")
        with pytest.raises(BudgetExceeded):
            client.request("GET", "/health")


def test_the_pocketbase_wrapper_counts_and_names_each_call():
    calls = []

    class Inner:
        def view(self, collection, record_id, token=None):
            calls.append(("view", collection))
            return "viewed"

        def signup(self, email, password):
            calls.append(("signup", email))
            return "signed-up"

    budget, log = Budget(5, 60), RouteLog()
    pb = CountingClient(Inner(), budget, log)
    assert pb.view("users", "abc", token="t") == "viewed"
    assert pb.signup("a@b.invalid", "pw") == "signed-up"
    assert budget.requests == 2
    assert log.routes == ["GET /api/collections/users/records/:id", "POST /api/collections/users/records"]
    assert calls == [("view", "users"), ("signup", "a@b.invalid")]


def test_wall_time_is_charged_per_request():
    budget = Budget(5, 60)
    with server() as base:
        client = _client(base, budget)
        start = time.monotonic()
        client.request("GET", "/health")
    assert 0 < budget.wall_seconds <= time.monotonic() - start + 0.01
