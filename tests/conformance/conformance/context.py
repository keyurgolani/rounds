"""Run context the fixtures receive.

The context gives a fixture the stack clients (the runner and
PocketBase), the run's canary set, its probe budget, and #9's
synthetic-account factory. Both clients charge the budget and record the
route on every request themselves, so the receipt lists the routes a
fixture actually exercised and nothing a fixture sends goes uncounted.
The context also tracks the accounts a fixture makes, so the plugin can
remove them and fail the run if that fails (#8 body, Domain ownership
and invariants).

The harness account factory and PocketBase client (``harness/probes``)
are imported lazily, so the self-tests exercise the framework without the
harness on the path; tests pass their own account factory and clients.
"""
from __future__ import annotations

import http.client
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

from .budget import Budget
from .canaries import CanarySet


@dataclass
class Http:
    status: int
    body: Any
    text: str
    headers: dict[str, str]
    # "" when the request got an answer; "timeout" when nothing answered in
    # time; otherwise the name of the connection error. A fixture turns
    # these into typed outcomes instead of letting them escape.
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
        data = None
        hdrs = {"Accept": "application/json"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
        if token:
            hdrs["Authorization"] = "Bearer " + token
        if headers:
            hdrs.update(headers)
        self.log.add(method, path)
        req = urllib.request.Request(self.base_url + path, data=data, headers=hdrs, method=method)
        with self.budget.spend():
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    text = resp.read().decode("utf-8", "replace")
                    return Http(resp.status, _maybe_json(text), text, dict(resp.headers))
            except urllib.error.HTTPError as err:
                text = err.read().decode("utf-8", "replace")
                return Http(err.code, _maybe_json(text), text, dict(err.headers or {}))
            except (socket.timeout, TimeoutError):
                return Http(0, None, "", {}, "timeout")
            except (urllib.error.URLError, OSError, http.client.HTTPException) as err:
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
                return Http(0, None, "", {}, "timeout")
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


def harness_accounts(pb: Any) -> Callable[[str], Any]:
    """#9's account factory: a fresh synthetic account per call."""

    def make(tag: str) -> Any:
        import factory  # harness/probes

        acct = factory.make_account(tag)
        factory.register(pb, acct)
        return acct

    return make


@dataclass
class RunContext:
    runner: Any
    pb: Any
    admin_token: str
    canaries: CanarySet
    budget: Budget
    log: RouteLog = field(default_factory=RouteLog)
    content: dict[str, str] = field(default_factory=dict)
    make_account: Callable[[str], Any] | None = None
    # The uncounted client teardown uses, so cleaning up never fails on a
    # fixture's spent budget.
    admin_pb: Any = None
    _accounts: list[Any] = field(default_factory=list)

    def new_account(self, tag: str) -> Any:
        make = self.make_account or harness_accounts(self.pb)
        acct = make(tag)
        self._accounts.append(acct)
        return acct

    def ensure_content(self) -> None:
        import factory  # harness/probes

        # Updated in place: the session shares this dict across fixtures.
        if not self.content:
            self.content.update(factory.ensure_content_fixtures(self.pb, self.admin_token))

    def teardown(self) -> list[str]:
        """Remove the accounts this fixture made. Returns the ids of any
        that could not be removed; a non-empty list fails the run."""
        failed: list[str] = []
        client = self.admin_pb if self.admin_pb is not None else self.pb
        for acct in self._accounts:
            try:
                resp = client.delete("users", acct.user_id, token=self.admin_token)
                if resp.status not in (200, 204, 404):
                    failed.append(acct.user_id)
            except Exception:
                failed.append(acct.user_id)
        self._accounts.clear()
        return failed


def wait_for_runner(base_url: str, attempts: int = 60, delay: float = 1.0) -> None:
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(base_url.rstrip("/") + "/health", timeout=5) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(delay)
    raise RuntimeError("runner did not become healthy")
