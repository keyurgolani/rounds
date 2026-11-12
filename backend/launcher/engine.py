"""A small client of the worker engine's API (ROUNDS-00A-L05).

The launcher talks to one engine, over the unix socket ``DOCKER_HOST`` names,
with the standard library only: HTTP/1.1 requests for everything but a
worker's stdio, and for that one connection upgraded to a raw stream
(``attach``), whose output frames the engine multiplexes with an 8-byte
header per chunk. Every path uses API ``API_VERSION``; an engine that can't
serve it fails the launcher's start.

Errors surface as ``EngineError`` with the status and a short reason, never
with what a worker wrote.
"""
from __future__ import annotations

import http.client
import json
import re
import socket
import struct
import threading
import urllib.parse
from typing import Any, Callable, Iterator

API_VERSION = "1.44"
API = f"/v{API_VERSION}"
CONTAINER_ID = re.compile(r"[0-9a-f]{12,64}")
# Docker's multiplexed stream: type (0 stdin, 1 stdout, 2 stderr), 3 zero
# bytes, and a big-endian length.
MUX = struct.Struct(">BxxxI")
STDOUT, STDERR = 1, 2
HEAD_MAX = 16 * 1024
RESPONSE_MAX = 8 * 1024 * 1024


class EngineError(Exception):
    def __init__(self, status: int, reason: str) -> None:
        super().__init__(f"{status}: {reason}")
        self.status = status
        self.reason = reason


class NotFound(EngineError):
    pass


class _UnixConnection(http.client.HTTPConnection):
    def __init__(self, path: str, timeout: float) -> None:
        super().__init__("engine", timeout=timeout)
        self._path = path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self._path)
        self.sock = sock


def _cid(value: str) -> str:
    if not isinstance(value, str) or not CONTAINER_ID.fullmatch(value):
        raise EngineError(0, "not a container id")
    return value


def _reason(body: bytes) -> str:
    try:
        message = json.loads(body.decode("utf-8", "replace")).get("message", "")
    except (ValueError, AttributeError):
        message = ""
    return str(message)[:200]


class Engine:
    def __init__(self, path: str, timeout: float = 30.0) -> None:
        self.path = path
        self.timeout = timeout

    # -- plain requests ----------------------------------------------------

    def request(self, method: str, path: str, query: dict[str, Any] | None = None, body: Any = None,
                timeout: float | None = None, versioned: bool = True) -> tuple[int, bytes]:
        target = (API if versioned else "") + path
        if query:
            target += "?" + urllib.parse.urlencode(query)
        conn = _UnixConnection(self.path, timeout or self.timeout)
        try:
            headers = {"Host": "engine"}
            data = None
            if body is not None:
                data = json.dumps(body).encode()
                headers["Content-Type"] = "application/json"
            conn.request(method, target, body=data, headers=headers)
            resp = conn.getresponse()
            payload = resp.read(RESPONSE_MAX + 1)
            if len(payload) > RESPONSE_MAX:
                raise EngineError(resp.status, "a response past its size")
            return resp.status, payload
        except (OSError, http.client.HTTPException) as err:
            raise EngineError(0, type(err).__name__) from None
        finally:
            conn.close()

    def _json(self, method: str, path: str, ok: tuple[int, ...] = (200,), **kwargs: Any) -> Any:
        status, payload = self.request(method, path, **kwargs)
        if status == 404:
            raise NotFound(status, _reason(payload))
        if status not in ok:
            raise EngineError(status, _reason(payload))
        if not payload:
            return None
        try:
            return json.loads(payload)
        except ValueError:
            raise EngineError(status, "not JSON") from None

    def ping(self) -> bool:
        status, payload = self.request("GET", "/_ping", versioned=False, timeout=5)
        return status == 200 and payload.strip() == b"OK"

    def version(self) -> dict[str, Any]:
        return self._json("GET", "/version", versioned=False)

    def info(self) -> dict[str, Any]:
        return self._json("GET", "/info")

    def image(self, ref: str) -> dict[str, Any] | None:
        try:
            return self._json("GET", f"/images/{urllib.parse.quote(ref, safe='')}/json")
        except NotFound:
            return None

    def pull(self, repository: str, digest: str, timeout: float = 600) -> None:
        """Pulls ``repository@digest``; the engine checks the digest."""
        status, payload = self.request("POST", "/images/create", query={"fromImage": repository, "tag": digest},
                                       timeout=timeout)
        if status != 200:
            raise EngineError(status, _reason(payload))
        for line in payload.splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict) and item.get("error"):
                raise EngineError(status, "the pull failed")

    def create(self, body: dict[str, Any]) -> str:
        created = self._json("POST", "/containers/create", ok=(201,), body=body)
        return _cid(created.get("Id", ""))

    def start(self, cid: str) -> None:
        self._json("POST", f"/containers/{_cid(cid)}/start", ok=(204, 304))

    def kill(self, cid: str) -> None:
        """Ends the worker at once; one already stopped or gone is fine."""
        try:
            self._json("POST", f"/containers/{_cid(cid)}/kill", ok=(204, 409), query={"signal": "KILL"})
        except NotFound:
            pass

    def remove(self, cid: str) -> None:
        try:
            self._json("DELETE", f"/containers/{_cid(cid)}", ok=(204,), query={"force": "1", "v": "1"})
        except NotFound:
            pass

    def inspect(self, cid: str) -> dict[str, Any] | None:
        """The worker's state, or None once the engine reports it gone."""
        try:
            return self._json("GET", f"/containers/{_cid(cid)}/json")
        except NotFound:
            return None

    def labeled(self, label: str) -> list[dict[str, Any]]:
        filters = json.dumps({"label": [label]})
        return self._json("GET", "/containers/json", query={"all": "1", "filters": filters}) or []

    def stats_once(self, cid: str) -> dict[str, Any] | None:
        try:
            return self._json("GET", f"/containers/{_cid(cid)}/stats", query={"stream": "0", "one-shot": "1"},
                              timeout=5)
        except EngineError:
            return None

    def stats_stream(self, cid: str, on_sample: Callable[[dict[str, Any]], None], stop: threading.Event) -> None:
        """Calls ``on_sample`` with each stats sample until ``stop`` is set or
        the worker is gone. Blocks; run it on its own thread."""
        conn = _UnixConnection(self.path, 5)
        try:
            conn.request("GET", f"{API}/containers/{_cid(cid)}/stats?stream=1", headers={"Host": "engine"})
            resp = conn.getresponse()
            if resp.status != 200:
                return
            while not stop.is_set():
                line = resp.readline(1024 * 1024)
                if not line:
                    return
                try:
                    sample = json.loads(line)
                except ValueError:
                    continue
                if isinstance(sample, dict):
                    on_sample(sample)
        except (OSError, http.client.HTTPException, EngineError):
            return
        finally:
            conn.close()

    # -- a worker's stdio ---------------------------------------------------

    def attach(self, cid: str) -> "Attachment":
        """The worker's stdin, stdout, and stderr, before it starts."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(self.path)
            sock.sendall(
                f"POST {API}/containers/{_cid(cid)}/attach?stream=1&stdin=1&stdout=1&stderr=1 HTTP/1.1\r\n"
                "Host: engine\r\nUpgrade: tcp\r\nConnection: Upgrade\r\nContent-Length: 0\r\n\r\n".encode()
            )
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = sock.recv(4096)
                if not chunk or len(head) > HEAD_MAX:
                    raise EngineError(0, "the attach didn't answer")
                head += chunk
        except OSError as err:
            sock.close()
            raise EngineError(0, type(err).__name__) from None
        except EngineError:
            sock.close()
            raise
        status_line, _, rest = head.partition(b"\r\n")
        _headers, _, early = rest.partition(b"\r\n\r\n")
        parts = status_line.split()
        if len(parts) < 2 or parts[1] not in (b"101", b"200"):
            sock.close()
            raise EngineError(int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0, "the attach was refused")
        return Attachment(sock, early)


class Attachment:
    """A worker's attached stdio: write its input, then read its output."""

    def __init__(self, sock: socket.socket, early: bytes = b"") -> None:
        self.sock = sock
        self._buffer = bytearray(early)
        self.eof = False

    def send(self, data: bytes) -> None:
        self.sock.settimeout(30)
        self.sock.sendall(data)

    def close_write(self) -> None:
        try:
            self.sock.shutdown(socket.SHUT_WR)
        except OSError:
            pass

    def recv(self, timeout: float) -> list[tuple[int, bytes]] | None:
        """The output chunks that arrive within ``timeout``, as (stream,
        bytes); None once the stream has ended and nothing is left."""
        if not self.eof:
            self.sock.settimeout(max(timeout, 0.001))
            try:
                data = self.sock.recv(256 * 1024)
                if data:
                    self._buffer += data
                else:
                    self.eof = True
            except socket.timeout:
                pass
            except OSError:
                self.eof = True
        out = list(self._frames())
        if not out and self.eof:
            # Ended, and whatever is left can't be a whole chunk.
            return None
        return out

    def _frames(self) -> Iterator[tuple[int, bytes]]:
        while len(self._buffer) >= MUX.size:
            stream, size = MUX.unpack_from(self._buffer)
            if len(self._buffer) < MUX.size + size:
                return
            payload = bytes(self._buffer[MUX.size:MUX.size + size])
            del self._buffer[:MUX.size + size]
            yield stream, payload

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass
