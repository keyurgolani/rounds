"""Bait services for the containment corpus's internal network.

Three decoys a contained worker must never reach: a fake cloud metadata
endpoint, a fake RFC1918 internal service, and a logging DNS resolver.
Each logs every request it receives to stdout, so a later leaf's fixture
can assert, from the service's log, that a no-network worker reached none
of them (EX-08, EX-09) and that a render worker fetched nothing (RD-03).
They sit on an ``internal: true`` network and embed a per-run canary, so
reaching one and reading its body leaks a value the receipt scans for.

Standard library only. The mode is the first argument:
``metadata``, ``rfc1918``, or ``dns``. These services are the bait, not a
probe: they run idle at stage 1 (the fixtures that exercise them are
pending rows), and a closing leaf attaches the worker and reads the logs.
"""
from __future__ import annotations

import os
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CANARY = os.environ.get("BAIT_CANARY", "bait-canary-unset")
# High ports so the decoys run as a non-root user. A closing leaf that
# needs the real link-local metadata address (169.254.169.254:80) remaps
# there; the fixtures that exercise these are pending at stage 1.
HTTP_PORT = int(os.environ.get("BAIT_HTTP_PORT", "8080"))
DNS_PORT = int(os.environ.get("BAIT_DNS_PORT", "5353"))


def _log(kind: str, detail: str) -> None:
    # One line per hit; a fixture greps these logs. No real secret here.
    print(f'{{"event":"bait-hit","service":"{kind}","detail":"{detail}"}}', flush=True)


class _MetadataHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        _log("metadata", self.path)
        body = (
            '{"accessKeyId":"AKIA-FAKE","secretAccessKey":"' + CANARY + '"}'
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):  # silence default logging
        pass


class _ServiceHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        _log("rfc1918", self.path)
        body = ('{"internal":true,"token":"' + CANARY + '"}').encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def _run_http(handler) -> None:
    server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), handler)
    print(f'{{"event":"bait-ready","port":{HTTP_PORT}}}', flush=True)
    server.serve_forever()


def _run_dns() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", DNS_PORT))
    print(f'{{"event":"bait-ready","dns_port":{DNS_PORT}}}', flush=True)
    while True:
        try:
            data, addr = sock.recvfrom(512)
        except OSError:
            continue
        name = _dns_qname(data)
        _log("dns", name)
        # Answer NXDOMAIN so a lookup resolves to nothing; the log is the
        # signal, not the answer.
        if len(data) >= 2:
            resp = data[:2] + b"\x81\x83" + data[4:6] + b"\x00\x00\x00\x00\x00\x00"
            try:
                sock.sendto(resp, addr)
            except OSError:
                pass


def _dns_qname(data: bytes) -> str:
    try:
        i = 12
        labels = []
        while i < len(data) and data[i] != 0:
            length = data[i]
            labels.append(data[i + 1 : i + 1 + length].decode("ascii", "replace"))
            i += 1 + length
        return ".".join(labels) or "."
    except Exception:
        return "?"


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "metadata":
        _run_http(_MetadataHandler)
    elif mode == "rfc1918":
        _run_http(_ServiceHandler)
    elif mode == "dns":
        _run_dns()
    else:
        print(f"unknown bait mode {mode!r}; use metadata|rfc1918|dns", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
