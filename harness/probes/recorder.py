"""A recording proxy between the runner and PocketBase (ROUNDS-00B-L05).

The harness points the runner's POCKETBASE_URL here. Each call is forwarded
to PocketBase unchanged and one JSON line is appended to the log:

  seq, method, path (the query is dropped), auth class, status, response
  length, and owner pseudonyms (an HMAC under a per-run salt of every
  `user` value in the response body).

The auth class comes from the bearer token's payload alone, never its
signature or value: `superuser` (a PocketBase admin token), `user` (an auth
record in `users`), `service` (an auth record in any other auth collection,
such as the execution worker), `none`, or `malformed`. The log never holds a
header, a token, a query string, or a body, so nothing a caller sent and
nothing PocketBase stored can reach it; the probes read the log to check
which identity the runner used and whether another account's row reached it
before the runner answered.

Standard library only. Binds 127.0.0.1 unless RECORDER_HOST says otherwise;
the harness compose runs it on the stack's private network and publishes no
port.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

# PocketBase 0.22's built-in users collection id.
USERS_COLLECTION_ID = "_pb_users_auth_"
AUTH_CLASSES = ("superuser", "user", "service", "none", "malformed")
# Request headers not forwarded as they are (hop-by-hop, or set by urllib).
_HOP = frozenset({"connection", "keep-alive", "proxy-connection", "transfer-encoding", "upgrade",
                  "te", "trailer", "host", "content-length", "accept-encoding"})


def _payload(token: str) -> dict[str, Any] | None:
    parts = token.split(".")
    if len(parts) != 3 or not parts[1]:
        return None
    seg = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        doc = json.loads(base64.urlsafe_b64decode(seg.encode("ascii")))
    except (ValueError, binascii.Error, UnicodeError):
        return None
    return doc if isinstance(doc, dict) else None


def classify(authorization: str | None) -> str:
    """The auth class of an Authorization header value."""
    if authorization is None or not authorization.strip():
        return "none"
    value = authorization.strip()
    # PocketBase takes the token with or without the Bearer prefix.
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    doc = _payload(value)
    if doc is None:
        return "malformed"
    kind = doc.get("type")
    if kind == "admin":
        return "superuser"
    if kind == "authRecord":
        cid = doc.get("collectionId")
        if not isinstance(cid, str) or not cid:
            return "malformed"
        return "user" if cid == USERS_COLLECTION_ID else "service"
    return "malformed"


def pseudonym(salt: bytes, value: str) -> str:
    return hmac.new(salt, value.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def owners_in(body: Any) -> set[str]:
    """Every string `user` value anywhere in a JSON body."""
    found: set[str] = set()
    stack = [body]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "user" and isinstance(v, str) and v:
                    found.add(v)
                else:
                    stack.append(v)
        elif isinstance(node, list):
            stack.extend(node)
    return found


def entry(seq: int, method: str, raw_path: str, authorization: str | None, status: int,
          body: bytes, salt: bytes) -> dict[str, Any]:
    """The one log line for a call. Takes the raw request path and header,
    and keeps neither."""
    path = urllib.parse.urlsplit(raw_path).path
    try:
        parsed = json.loads(body.decode("utf-8")) if body else None
    except (ValueError, UnicodeDecodeError):
        parsed = None
    return {
        "seq": seq,
        "method": method,
        "path": path,
        "auth": classify(authorization),
        "status": status,
        "length": len(body),
        "owners": sorted(pseudonym(salt, o) for o in owners_in(parsed)),
    }


def read_log(path: str, start: int = 0) -> list[dict[str, Any]]:
    """Log lines from line `start` on."""
    try:
        with open(path) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []
    return [json.loads(line) for line in lines[start:] if line.strip()]


def log_length(path: str) -> int:
    try:
        with open(path) as f:
            return sum(1 for line in f if line.strip())
    except FileNotFoundError:
        return 0


class _Recorder:
    def __init__(self, upstream: str, log_path: str, salt: bytes) -> None:
        self.upstream = upstream.rstrip("/")
        self.log_path = log_path
        self.salt = salt
        self.lock = threading.Lock()
        self.seq = 0

    def record(self, line_for) -> None:
        with self.lock:
            self.seq += 1
            line = line_for(self.seq)
            with open(self.log_path, "a") as f:
                f.write(json.dumps(line, separators=(",", ":")) + "\n")


def _handler(rec: _Recorder):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args: Any) -> None:
            # The default access log would print the path and query.
            pass

        def _forward(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            data = self.rfile.read(length) if length else None
            headers = {k: v for k, v in self.headers.items() if k.lower() not in _HOP}
            req = urllib.request.Request(rec.upstream + self.path, data=data, headers=headers, method=self.command)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    status, resp_headers, body = resp.status, resp.headers.items(), resp.read()
            except urllib.error.HTTPError as err:
                status, resp_headers, body = err.code, err.headers.items(), err.read()
            except (urllib.error.URLError, OSError):
                status, resp_headers, body = 502, [("Content-Type", "application/json")], b'{"recorder":"upstream unreachable"}'
            auth = self.headers.get("Authorization")
            rec.record(lambda seq: entry(seq, self.command, self.path, auth, status, body, rec.salt))
            self.send_response(status)
            for k, v in resp_headers:
                if k.lower() not in _HOP:
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = do_PATCH = do_PUT = do_DELETE = do_HEAD = _forward

    return Handler


def main() -> int:
    upstream = os.environ.get("RECORDER_UPSTREAM", "http://pocketbase:8090")
    log_path = os.environ.get("RECORDER_LOG", "/out/recorder.jsonl")
    salt = os.environ.get("RECORDER_SALT", "")
    if len(salt) < 16:
        print("RECORDER_SALT must be set (16+ characters)", file=sys.stderr)
        return 2
    host = os.environ.get("RECORDER_HOST", "127.0.0.1")
    port = int(os.environ.get("RECORDER_PORT", "8090"))
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    rec = _Recorder(upstream, log_path, salt.encode("utf-8"))
    server = ThreadingHTTPServer((host, port), _handler(rec))
    print(f"recorder listening on {host}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
