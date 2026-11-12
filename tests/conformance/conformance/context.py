"""Run context the fixtures receive.

The context gives a fixture the stack clients (the runner and
PocketBase), the run's canary set, its probe budget, and #9's
synthetic-account factory. Both clients charge the budget and record the
route on every request themselves, so the receipt lists the routes a
fixture actually exercised and nothing a fixture sends goes uncounted.
The context also tracks the accounts a fixture makes, from before the
first request that creates one, so the plugin can remove every one of
them, even one whose signup landed before its sign-in failed, the budget
refused, or the deadline fired, and fail the run if that fails (#8 body,
Domain ownership and invariants).

Both clients type a failed connection the same way, ``unreachable``
(refused, unresolvable, or not connected in time), apart from
``timeout``, a connection that got no answer in time; a fixture reads
the first as inconclusive.

Since ROUNDS-00A-L03 PR 4 every code run is a durable job: the six
code-run routes answer 202 with the job, and each needs an
``Idempotency-Key``, the job's command id. The runner client sends one
with a code run that has none, as the app does, and follows a job to its
end, so a fixture gets the run's own result as the route answered it in
its request before: 200 and the job's output. A job that ended without a
result, or didn't end in time, comes back under its 202, as the job, so
a fixture reads no result from it. Every read of a job is counted and
recorded as one route, ``GET /api/execution/jobs/{job_id}``.

The harness account factory and PocketBase client (``harness/probes``)
are imported lazily, so the self-tests exercise the framework without the
harness on the path; tests pass their own account factory and clients.
"""
from __future__ import annotations

import http.client
import json
import re
import secrets
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

from .budget import Budget
from .canaries import CanarySet

# No connection was made: refused, unresolvable, or not connected in time.
UNREACHABLE = "unreachable"
# Connected, and no answer came in time.
TIMEOUT = "timeout"
# The emails #9's factory makes, the only ones teardown looks up.
_FACTORY_EMAIL = re.compile(r"harness-[a-z0-9-]{1,40}-[0-9a-f]{12}@harness\.invalid")
# The six code-run routes, each a durable job since ROUNDS-00A-L03 PR 4.
JOB_ROUTES = frozenset({
    ("POST", "/api/run"), ("POST", "/api/evaluate"), ("POST", "/api/ai-coding/run-project"),
    ("POST", "/api/ai-coding/grade"), ("POST", "/api/take-home/run"), ("POST", "/api/take-home/submit"),
})
JOB_READ = "/api/execution/jobs/{job_id}"
JOB_ENDED = frozenset({"completed", "timed-out", "denied", "canceled", "failed"})
_JOB_ID = re.compile(r"[a-z0-9]{15}")
# One read waits up to the runner's most for the job to change; a job gets
# this many reads before the client hands it back as it last was.
JOB_WAIT_S = 20
JOB_READS = 5


def command_id() -> str:
    """A fresh UUIDv7, the key shape the runner takes."""
    raw = bytearray(secrets.token_bytes(16))
    raw[0:6] = int(time.time() * 1000).to_bytes(6, "big")
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    h = raw.hex()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


@dataclass
class Http:
    status: int
    body: Any
    text: str
    headers: dict[str, str]
    # "" when the request got an answer; UNREACHABLE when no connection
    # was made; TIMEOUT when a connection got no answer in time; otherwise
    # the name of the error that ended it. A fixture turns these into
    # typed outcomes instead of letting them escape.
    error: str = ""


def _maybe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return None


@dataclass
class RouteLog:
    """The routes a fixture exercised, as ``METHOD /path`` in first-use order."""

    routes: list[str] = field(default_factory=list)

    def add(self, method: str, path: str) -> None:
        route = f"{method.upper()} {path.split('?', 1)[0]}"
        if route not in self.routes:
            self.routes.append(route)


class RunnerClient:
    """A small HTTP client for the runner. A fixture controls the exact
    request it sends (a missing bearer, a declared size) and reads the raw
    response text for redaction."""

    def __init__(self, base_url: str, budget: Budget, log: RouteLog, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.budget = budget
        self.log = log
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Http:
        job_route = (method.upper(), path.split("?", 1)[0]) in JOB_ROUTES
        if job_route and not any(name.lower() == "idempotency-key" for name in headers or {}):
            headers = {**(headers or {}), "Idempotency-Key": command_id()}
        answer = self._send(method, path, token=token, json_body=json_body, headers=headers)
        if job_route and answer.status == 202:
            return self._follow(answer, token)
        return answer

    def _follow(self, started: Http, token: str | None) -> Http:
        """The job a code run started, read until it ended: 200 and its
        output when it ended with one, else the job as it last was under
        the start's 202. A read that fails comes back as it is."""
        job = started.body if isinstance(started.body, dict) else {}
        job_id = job.get("job_id")
        if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
            return started
        last = started
        for _ in range(JOB_READS):
            if job.get("state") in JOB_ENDED:
                break
            last = self._send("GET", JOB_READ.format(job_id=job_id) + f"?wait={JOB_WAIT_S}", token=token,
                              route=JOB_READ)
            if last.error or last.status != 200 or not isinstance(last.body, dict):
                return last
            job = last.body
        envelope = job.get("envelope")
        output = envelope.get("output") if isinstance(envelope, dict) else None
        if job.get("state") in JOB_ENDED and isinstance(output, dict):
            return Http(200, output, last.text, last.headers)
        return Http(202, job, last.text, last.headers)

    def _send(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        route: str | None = None,
    ) -> Http:
        data = None
        hdrs = {"Accept": "application/json"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
        if token:
            hdrs["Authorization"] = "Bearer " + token
        if headers:
            hdrs.update(headers)
        self.log.add(method, route or path)
        req = urllib.request.Request(self.base_url + path, data=data, headers=hdrs, method=method)
        with self.budget.spend():
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    text = resp.read().decode("utf-8", "replace")
                    return Http(resp.status, _maybe_json(text), text, dict(resp.headers))
            except urllib.error.HTTPError as err:
                text = err.read().decode("utf-8", "replace")
                return Http(err.code, _maybe_json(text), text, dict(err.headers or {}))
            except urllib.error.URLError:
                # urllib wraps every failure to connect, a connect timeout
                # included.
                return Http(0, None, "", {}, UNREACHABLE)
            except (socket.timeout, TimeoutError):
                return Http(0, None, "", {}, TIMEOUT)
            except (OSError, http.client.HTTPException) as err:
                return Http(0, None, "", {}, type(err).__name__)

    def declare(self, method: str, path: str, declared: int, *, timeout: float = 10.0) -> Http:
        """Send only the headers of a request whose Content-Length is
        ``declared``, as the harness's verifier does. The runner's byte cap
        decides on that header alone, so nothing large crosses the network."""
        parts = urllib.parse.urlsplit(self.base_url)
        self.log.add(method, path)
        with self.budget.spend():
            try:
                conn = http.client.HTTPConnection(parts.netloc, timeout=timeout)
                try:
                    try:
                        conn.connect()
                    except OSError:
                        # As request() types it: no connection, whether
                        # refused or not made in time. Only a connection
                        # that got no answer is a timeout.
                        return Http(0, None, "", {}, UNREACHABLE)
                    conn.putrequest(method, (parts.path.rstrip("/") or "") + path)
                    conn.putheader("Content-Type", "application/json")
                    conn.putheader("Content-Length", str(declared))
                    conn.endheaders()
                    resp = conn.getresponse()
                    text = resp.read().decode("utf-8", "replace")
                    return Http(resp.status, _maybe_json(text), text, {k.lower(): v for k, v in resp.getheaders()})
                finally:
                    conn.close()
            except (socket.timeout, TimeoutError):
                return Http(0, None, "", {}, TIMEOUT)
            except (OSError, http.client.HTTPException) as err:
                return Http(0, None, "", {}, type(err).__name__)


class CountingClient:
    """Wraps #9's PocketBase client so every call charges the budget and
    records its route, like the runner client."""

    # Methods that take a collection as their first argument, and the
    # route each one uses.
    _ROUTES = {
        "create": ("POST", "/api/collections/{c}/records"),
        "update": ("PATCH", "/api/collections/{c}/records/:id"),
        "view": ("GET", "/api/collections/{c}/records/:id"),
        "listing": ("GET", "/api/collections/{c}/records"),
        "delete": ("DELETE", "/api/collections/{c}/records/:id"),
    }
    # Methods with a fixed route.
    _FIXED = {
        "signup": ("POST", "/api/collections/users/records"),
        "auth_password": ("POST", "/api/collections/users/auth-with-password"),
        "admin_auth": ("POST", "/api/admins/auth-with-password"),
        "wait_healthy": ("GET", "/api/health"),
        "collections_meta": ("GET", "/api/collections"),
    }

    def __init__(self, inner: Any, budget: Budget, log: RouteLog) -> None:
        self._inner = inner
        self._budget = budget
        self._log = log

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._inner, name)
        if not callable(target):
            return target

        def counted(*args: Any, **kwargs: Any) -> Any:
            route = self._ROUTES.get(name)
            if route and args:
                self._log.add(route[0], route[1].replace("{c}", str(args[0])))
            elif name in self._FIXED:
                self._log.add(*self._FIXED[name])
            elif name in ("post", "get") and args:
                self._log.add(name.upper(), str(args[0]))
            else:
                self._log.add("CALL", f"pocketbase.{name}")
            with self._budget.spend():
                return target(*args, **kwargs)

        return counted


def _harness_make(tag: str) -> Any:
    """#9's factory: a fresh synthetic identity, before any request."""
    import factory  # harness/probes

    return factory.make_account(tag)


def _harness_register(pb: Any) -> Callable[[Any], None]:
    """#9's factory: the signup, then the sign-in."""

    def register(acct: Any) -> None:
        import factory  # harness/probes

        factory.register(pb, acct)

    return register


@dataclass
class RunContext:
    runner: Any
    pb: Any
    admin_token: str
    canaries: CanarySet
    budget: Budget
    log: RouteLog = field(default_factory=RouteLog)
    content: dict[str, str] = field(default_factory=dict)
    # Makes an account's identity (no request); #9's factory unless a test
    # passes its own.
    make_account: Callable[[str], Any] | None = None
    # Signs that identity up and in; #9's factory over ``pb`` unless a test
    # passes its own. A test's make_account alone returns a ready account.
    register_account: Callable[[Any], None] | None = None
    # The uncounted client teardown uses, so cleaning up never fails on a
    # fixture's spent budget.
    admin_pb: Any = None
    _accounts: list[Any] = field(default_factory=list)

    def new_account(self, tag: str) -> Any:
        """A fresh synthetic account. It is tracked before the request that
        creates it, so teardown removes it whatever stops its sign-in."""
        if self.make_account is not None and self.register_account is None:
            acct = self.make_account(tag)
            self._accounts.append(acct)
            return acct
        acct = (self.make_account or _harness_make)(tag)
        self._accounts.append(acct)
        (self.register_account or _harness_register(self.pb))(acct)
        return acct

    def ensure_content(self) -> None:
        import factory  # harness/probes

        # Updated in place: the session shares this dict across fixtures.
        if not self.content:
            self.content.update(factory.ensure_content_fixtures(self.pb, self.admin_token))

    def teardown(self) -> list[str]:
        """Remove the accounts this fixture made, each one whose signup may
        have landed included. Returns a label for each that could not be
        removed or looked up; a non-empty list fails the run."""
        failed: list[str] = []
        client = self.admin_pb if self.admin_pb is not None else self.pb
        for acct in self._accounts:
            label = getattr(acct, "user_id", "") or f"unknown id ({getattr(acct, 'tag', '')})"
            try:
                user_id = getattr(acct, "user_id", "") or self._landed(client, acct)
                if not user_id:
                    continue  # its signup never landed
                resp = client.delete("users", user_id, token=self.admin_token)
                if resp.status not in (200, 204, 404):
                    failed.append(user_id)
            except Exception:
                failed.append(label)
        self._accounts.clear()
        return failed

    def _landed(self, client: Any, acct: Any) -> str:
        """The id of an account whose signup got no answer, found by its
        email, or "" when it never landed."""
        email = getattr(acct, "email", "")
        if not isinstance(email, str) or not _FACTORY_EMAIL.fullmatch(email):
            raise RuntimeError("an account without a factory email can't be looked up")
        resp = client.listing("users", token=self.admin_token, params={"filter": f'email = "{email}"', "perPage": 1})
        if resp.status != 200 or not isinstance(resp.body, dict):
            raise RuntimeError(f"the account lookup answered {resp.status}")
        items = resp.body.get("items") or []
        return items[0].get("id", "") if items and isinstance(items[0], dict) else ""


def wait_for_runner(base_url: str, attempts: int = 60, delay: float = 1.0) -> None:
    """Until the runner answers ``/ready``: with the job store on, once its
    worker is logged in, so a code run's job can start (ROUNDS-00A-L03);
    otherwise as soon as it answers ``/health``."""
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(base_url.rstrip("/") + "/ready", timeout=5) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(delay)
    raise RuntimeError("runner did not become ready")
