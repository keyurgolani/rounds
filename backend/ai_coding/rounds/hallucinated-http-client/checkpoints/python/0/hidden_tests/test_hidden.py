"""Hidden test — exercises fetch_user against a real local HTTP server.
A solution that still calls `httpx.get_json` raises AttributeError at
import-time exercise, because that method does not exist on the real
library. The visible mock-based test cannot catch this."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import client


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/users/"):
            user_id = self.path.removeprefix("/users/")
            body = json.dumps({"id": user_id, "name": "Real"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_args, **_kwargs):
        pass


@pytest.fixture(scope="module")
def server():
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def test_fetch_user_against_real_server(server, monkeypatch):
    monkeypatch.setattr(client, "INTERNAL_BASE_URL", server)
    result = client.fetch_user("u-42")
    assert result == {"id": "u-42", "name": "Real"}
