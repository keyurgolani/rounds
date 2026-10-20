#!/usr/bin/env python3
"""Deployment verification for the account-scope invariant (ROUNDS-00B-L01 stage 4)
and the admission chain and gates (ROUNDS-00A-L01 stage 4).

Read-only checks an operator runs against a Rounds deployment they operate:

  proxy        Through the public URL (the frontend nginx): the routes #1 stage 2
               denies answer nginx's own 404 and never reach PocketBase or the
               runner, /api/execute is gone, the routes it leaves open (records,
               auth, OAuth redirect, realtime, files, health) still reach
               PocketBase, and a body declared over the default 1 MiB cap gets
               the typed 413.
  credentials  At PocketBase's own port (127.0.0.1:8090 inside its container):
               the repository's shipped default admin login and the demo
               account's login do not authenticate as an admin. When the admin
               list is available (admin credentials, or a data copy), every
               admin is also checked against the shipped default passwords.
  rules        The collection rules match docs/security/account-scope.v1.json,
               read live through the admin API (operator credentials) or from a
               pb_data copy, and no account-owned collection still creates with
               the old any-signed-in-account rule.
  admins       A pb_data copy holds at least one admin, so PocketBase's
               first-admin setup is closed.
  admission    (--admission, with --url) Through the public URL: each of the
               nine admitted routes refuses a caller without a bearer before
               reading the body, 401 unauthenticated (or the 503 that
               --expect-disabled names for a route that is off), in the typed
               {detail, code, correlation_id} envelope whose id the
               X-Correlation-Id header repeats, and a body declared over its
               cap gets the typed 413. No account is admitted, so nothing is
               charged or run.
  disabled     (--expect-disabled PATH[=CODE], with --url) After an emergency
               disable: that route answers 503 CODE, with no bearer and with
               a made-up one. CODE is route_disabled (the default) when the
               route's own gate is off, or definitions_disabled when
               ROUNDS_GATE_EXECUTION_DEFINITIONS=disabled stops the six
               execution routes.
  gates        (--gates-log FILE) A saved runner log from its start: the
               gates line lists every admitted route's gate and both
               enforcement gates with valid values, none fell back from an
               invalid setting, and each --expect-gate NAME=VALUE holds.

It never writes. Every request is a read, a login that is expected to fail, a
request nginx refuses on its headers before PocketBase sees it, or a request to
an admitted route that the runner refuses before it reads the body or names an
account. It prints no
credentials, emails, tokens, or record contents. The admin password, when
given, comes from an environment variable, never the command line. It never
uses an environment proxy, and it refuses a plain-HTTP --pb-url that is not
loopback unless --allow-insecure is given, since that URL carries the admin
password and token. Rules are compared with docs/security/account-scope.v1.json
in this checkout unless --policy names another copy.

Standard library only, Python 3.9 or newer.

Exit status: 0 no check failed, 1 a check failed, 2 a usage or configuration
error (results gathered before it are still printed). A check that can't
decide from where it runs prints INCONCLUSIVE and does not fail the run: a
body-cap check behind a proxy that waits for the whole body, or that refuses
the declared size with its own 413 page before the frontend sees it.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import ipaddress
import shutil
import socket
import sqlite3
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

# The repository's shipped default credentials. Each must fail as an admin
# login on every deployment. Kept in step with the files that ship them by
# pocketbase/tests/test_verify_deployment.py.
#   - docker-compose.yml and backend/app/pb_auth.py fall back to this admin.
#   - pocketbase/pb_migrations/1700000600_demo_user.js seeds the demo account.
DEFAULT_ADMIN_LOGINS: tuple[tuple[str, str, str], ...] = (
    ("the development compose default admin", "admin@local.dev", "changemenowplz"),
    ("the demo account", "demo@rounds.keyurgolani.name", "RoundsDemo123!"),
)
DEFAULT_PASSWORDS: tuple[str, ...] = tuple(dict.fromkeys(p for _, _, p in DEFAULT_ADMIN_LOGINS))

CREATE_IF_AUTHED = '@request.auth.id != ""'
NGINX_BODY_CAP = 1024 * 1024  # client_max_body_size 1m in frontend/nginx.conf
# PocketBase 0.22.22's answer to /api/oauth2-redirect without state and code.
OAUTH_FAILURE_LOCATION = "../_/#/auth/oauth2-redirect-failure"

# (check id, path, methods). nginx answers these itself (frontend/nginx.conf,
# "Never proxied"); none may reach PocketBase or the runner.
DENIED_ROUTES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("deployment.proxy.admin-ui.denied", "/_/", ("GET",)),
    ("deployment.proxy.admin-api.denied", "/api/admins", ("GET", "POST")),
    ("deployment.proxy.admin-api.denied", "/api/admins/auth-with-password", ("POST",)),
    ("deployment.proxy.settings-api.denied", "/api/settings", ("GET",)),
    ("deployment.proxy.backups-api.denied", "/api/backups", ("GET", "POST")),
    ("deployment.proxy.logs-api.denied", "/api/logs", ("GET",)),
    ("deployment.proxy.collection-metadata.denied", "/api/collections", ("GET", "POST")),
    ("deployment.proxy.collection-metadata.denied", "/api/collections/users", ("GET",)),
    ("deployment.proxy.admission-hooks.denied", "/api/rounds/admission/", ("GET", "POST")),
)

# Every check id this tool can report, with the guarantee it states. The
# account-scope policy's deployment_checks section must list exactly these.
CHECKS: dict[str, str] = {
    "deployment.proxy.admin-ui.denied": "the PocketBase admin UI is not served at the public URL",
    "deployment.proxy.admin-api.denied": "the PocketBase admin API, including admin login, is not reachable at the public URL",
    "deployment.proxy.settings-api.denied": "PocketBase settings are not reachable at the public URL",
    "deployment.proxy.backups-api.denied": "PocketBase backups are not reachable at the public URL",
    "deployment.proxy.logs-api.denied": "PocketBase logs are not reachable at the public URL",
    "deployment.proxy.collection-metadata.denied": "collection schema routes are not reachable at the public URL",
    "deployment.proxy.admission-hooks.denied": "the admission hook routes are not reachable at the public URL",
    "deployment.proxy.execute.gone": "/api/execute no longer reaches a code runner",
    "deployment.proxy.health.open": "the health route still reaches PocketBase",
    "deployment.proxy.records.open": "record routes still reach PocketBase",
    "deployment.proxy.auth.open": "auth routes still reach PocketBase",
    "deployment.proxy.oauth-redirect.open": "the OAuth redirect route still reaches PocketBase",
    "deployment.proxy.realtime.open": "the realtime stream still reaches PocketBase",
    "deployment.proxy.files.open": "file routes still reach PocketBase",
    "deployment.proxy.oversized-body.rejected": "a body over the default 1 MiB cap gets the typed 413",
    "deployment.credentials.defaults.rejected": "no shipped default login authenticates as an admin",
    "deployment.credentials.admin-passwords.rejected": "no admin account accepts a shipped default password",
    "deployment.rules.match": "the collection rules match the account-scope rule table",
    "deployment.admins.present": "at least one admin exists, so first-admin setup is closed",
}

# Policy rule key -> PocketBase field, as harness/probes/run.py reads them.
RULE_FIELD = {"list": "listRule", "view": "viewRule", "create": "createRule", "update": "updateRule", "delete": "deleteRule"}
AUTH_OPTION_RULE = {"manage": "manageRule"}
_MISSING = object()


# --------------------------------------------------------------------------
# results and receipts
# --------------------------------------------------------------------------


@dataclass
class Result:
    check_id: str
    target: str
    operation: str
    actor: str
    expected_status: int
    observed_status: int
    passed: bool
    elapsed_ms: int = 0
    detail: str = ""
    # The check could not decide from here (for example a buffering proxy in
    # front of nginx). Not a pass: the harness, where nginx is the first hop,
    # still fails on it. The command line reports it apart from failures.
    inconclusive: bool = False


# The two-account harness's receipt schema (harness/probes/receipts.py). Kept
# identical so deployment checks sit in the same receipts file; a unit test
# compares the field lists.
@dataclass
class Receipt:
    probe_id: str
    collection: str
    operation: str
    actor: str
    expected_status: int
    observed_status: int
    passed: bool
    request_time_ms: int
    detail: str = ""
    version: str = "v1"
    run_id: str = ""
    commit: str = ""
    binary_digest: str = ""
    binary_arch: str = ""
    phase: str = ""
    migrations: list[str] = field(default_factory=list)


def to_receipt(r: Result, context: dict[str, Any]) -> Receipt:
    return Receipt(
        probe_id=r.check_id,
        collection=r.target,
        operation=r.operation,
        actor=r.actor,
        expected_status=r.expected_status,
        observed_status=r.observed_status,
        passed=r.passed,
        request_time_ms=r.elapsed_ms,
        detail=r.detail,
        run_id=context.get("run_id", ""),
        commit=context.get("commit", ""),
        binary_digest=context.get("binary_digest", ""),
        binary_arch=context.get("binary_arch", ""),
        phase=context.get("phase", "deployment"),
        migrations=list(context.get("migrations", [])),
    )


def write_receipts(path: str, results: Iterable[Result], context: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a") as f:
        for r in results:
            f.write(json.dumps(asdict(to_receipt(r, context)), separators=(",", ":")) + "\n")


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------


@dataclass
class Response:
    status: int
    body: bytes
    headers: dict[str, str]
    elapsed_ms: int
    error: str = ""

    def json(self) -> Any:
        try:
            return json.loads(self.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401 - urllib hook
        return None


def _opener() -> urllib.request.OpenerDirector:
    """No redirects followed, and never an environment proxy: the admin
    password and token must go straight to the URL given, not through whatever
    http_proxy or https_proxy points at."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


def request(method: str, url: str, *, body: Any = None, token: str = "", timeout: float = 10.0) -> Response:
    """One request, redirects not followed, errors returned as status 0."""
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = _opener()
    start = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw, status, hdrs = resp.read(), resp.status, dict(resp.headers)
    except urllib.error.HTTPError as err:
        raw, status, hdrs = err.read(), err.code, dict(err.headers or {})
    except (urllib.error.URLError, OSError) as err:
        return Response(0, b"", {}, int((time.monotonic() - start) * 1000), error=type(err).__name__)
    return Response(status, raw, {k.lower(): v for k, v in hdrs.items()}, int((time.monotonic() - start) * 1000))


def is_pocketbase_json(resp: Response) -> bool:
    """PocketBase's JSON shape: an error ({code, message, data}) or health."""
    doc = resp.json()
    return isinstance(doc, dict) and isinstance(doc.get("code"), int) and isinstance(doc.get("message"), str)


def is_runner_json(resp: Response) -> bool:
    """The runner's shapes: FastAPI's {detail} or the typed admission envelope."""
    doc = resp.json()
    return isinstance(doc, dict) and ("detail" in doc or isinstance(doc.get("code"), str))


def answered_by(resp: Response) -> str:
    if resp.status == 0:
        return f"unreachable ({resp.error})"
    if is_pocketbase_json(resp):
        return "pocketbase"
    if is_runner_json(resp):
        return "runner"
    return "proxy"


# --------------------------------------------------------------------------
# proxy checks (public URL)
# --------------------------------------------------------------------------


def check_denied_routes(base_url: str, req: Callable[..., Response] = request) -> list[Result]:
    results: dict[str, Result] = {}
    for check_id, path, methods in DENIED_ROUTES:
        failures = []
        last = None
        for method in methods:
            resp = req(method, base_url + path, body={} if method == "POST" else None)
            last = resp
            who = answered_by(resp)
            if resp.status != 404 or who != "proxy":
                failures.append(f"{method} {path} status={resp.status} answered_by={who}")
        r = results.get(check_id)
        if r is None:
            r = Result(check_id, path, "proxy", "anonymous", 404, last.status if last else 0, True, last.elapsed_ms if last else 0)
            results[check_id] = r
        else:
            r.target = f"{r.target},{path}"
        if failures:
            r.passed = False
            r.observed_status = last.status if last else 0
            r.detail = "; ".join(filter(None, [r.detail] + failures))
    return list(results.values())


def check_execute_gone(base_url: str, req: Callable[..., Response] = request) -> Result:
    failures = []
    status = 0
    elapsed = 0
    for method in ("GET", "POST"):
        resp = req(method, base_url + "/api/execute", body={} if method == "POST" else None)
        status, elapsed = resp.status, resp.elapsed_ms
        who = answered_by(resp)
        if resp.status != 404 or who == "runner" or who.startswith("unreachable"):
            failures.append(f"{method} status={resp.status} answered_by={who}")
    return Result("deployment.proxy.execute.gone", "/api/execute", "proxy", "anonymous", 404, status,
                  not failures, elapsed, "; ".join(failures))


def _open_route(check_id: str, path: str, resp: Response, ok: bool, expected: int, why: str) -> Result:
    detail = "" if ok else f"status={resp.status} answered_by={answered_by(resp)} {why}".strip()
    return Result(check_id, path, "proxy", "anonymous", expected, resp.status, ok, resp.elapsed_ms, detail)


def check_open_routes(base_url: str, req: Callable[..., Response] = request,
                      read_event: Callable[[str], tuple[int, str, str]] | None = None) -> list[Result]:
    out = []

    resp = req("GET", base_url + "/api/health")
    doc = resp.json() if resp.status == 200 else None
    out.append(_open_route("deployment.proxy.health.open", "/api/health", resp,
                           isinstance(doc, dict) and doc.get("code") == 200, 200, "expected PocketBase's health JSON"))

    path = "/api/collections/campaigns/records?perPage=1"
    resp = req("GET", base_url + path)
    doc = resp.json() if resp.status == 200 else None
    out.append(_open_route("deployment.proxy.records.open", path, resp,
                           isinstance(doc, dict) and isinstance(doc.get("items"), list), 200,
                           "expected a PocketBase record page"))

    path = "/api/collections/users/auth-methods"
    resp = req("GET", base_url + path)
    doc = resp.json() if resp.status == 200 else None
    out.append(_open_route("deployment.proxy.auth.open", path, resp,
                           isinstance(doc, dict) and "authProviders" in doc, 200,
                           "expected PocketBase's auth methods"))

    # Without a provider's state and code, PocketBase 0.22.22 answers this route
    # with a bodyless 307 to its own failure page. Only PocketBase answers that
    # way, so it shows the route reaches PocketBase (the redirect is not
    # followed; its target is the admin UI path nginx denies).
    path = "/api/oauth2-redirect"
    resp = req("GET", base_url + path)
    location = resp.headers.get("location", "")
    out.append(_open_route("deployment.proxy.oauth-redirect.open", path, resp,
                           resp.status == 307 and location == OAUTH_FAILURE_LOCATION and not resp.body.strip(),
                           307, f"location={location!r}, expected PocketBase's redirect to its failure page"))

    # No collection has a file field, so a file request finds nothing, but
    # PocketBase answers it.
    path = "/api/files/users/verify0deployment/verify.txt"
    resp = req("GET", base_url + path)
    out.append(_open_route("deployment.proxy.files.open", path, resp,
                           answered_by(resp) == "pocketbase", resp.status, "expected PocketBase to answer"))

    status, content_type, first_event = (read_event or read_first_sse_event)(base_url + "/api/realtime")
    ok = status == 200 and content_type.startswith("text/event-stream") and first_event == "PB_CONNECT"
    out.append(Result("deployment.proxy.realtime.open", "/api/realtime", "proxy", "anonymous", 200, status, ok, 0,
                      "" if ok else f"status={status} content_type={content_type!r} first_event={first_event!r}"))
    return out


def read_first_sse_event(url: str, timeout: float = 8.0) -> tuple[int, str, str]:
    """Status, content type, and the first SSE event name; the stream is closed."""
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    try:
        resp = _opener().open(req, timeout=timeout)
    except urllib.error.HTTPError as err:
        return err.code, (err.headers or {}).get("Content-Type", ""), ""
    except (urllib.error.URLError, OSError) as err:
        return 0, "", type(err).__name__
    try:
        content_type = resp.headers.get("Content-Type", "")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = resp.readline()
            if not line:
                break
            text = line.decode("utf-8", "replace").strip()
            if text.startswith("event:"):
                return resp.status, content_type, text[len("event:"):].strip()
        return resp.status, content_type, ""
    except OSError as err:
        return resp.status, resp.headers.get("Content-Type", ""), type(err).__name__
    finally:
        resp.close()


@dataclass
class Declared:
    """The answer to a request that declared a body and sent none of it."""

    status: int
    raw: bytes
    headers: dict[str, str]
    elapsed_ms: int
    # "timeout" when nothing answered in time, an exception name when the
    # connection failed, "" otherwise.
    error: str = ""


def declare_oversize(base_url: str, path: str, declared: int, method: str = "POST",
                     timeout: float = 10.0) -> Declared:
    """Send only the headers of a request whose Content-Length is
    ``declared``. nginx, and the runner's own byte cap, decide on that
    header alone, so nothing large crosses the network."""
    parts = urllib.parse.urlsplit(base_url)
    conn_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    kwargs: dict[str, Any] = {"timeout": timeout}
    if parts.scheme == "https":
        kwargs["context"] = ssl.create_default_context()
    start = time.monotonic()
    try:
        conn = conn_cls(parts.netloc, **kwargs)
        try:
            conn.putrequest(method, (parts.path.rstrip("/") or "") + path)
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", str(declared))
            conn.endheaders()
            resp = conn.getresponse()
            status, raw = resp.status, resp.read()
            headers = {k.lower(): v for k, v in resp.getheaders()}
        finally:
            conn.close()
    except (socket.timeout, TimeoutError):
        return Declared(0, b"", {}, int((time.monotonic() - start) * 1000), "timeout")
    except (OSError, http.client.HTTPException) as err:
        return Declared(0, b"", {}, int((time.monotonic() - start) * 1000), type(err).__name__)
    return Declared(status, raw, headers, int((time.monotonic() - start) * 1000))


def check_oversized_body(base_url: str, declared: int = NGINX_BODY_CAP + 1, timeout: float = 10.0) -> Result:
    """Declare a body one byte over nginx's cap and send none of it: nginx
    decides on the Content-Length header alone, so nothing large is sent and
    PocketBase never sees the request.

    That only works when this repository's nginx is the first hop. A buffering
    proxy in front (the repository's Kubernetes ingress-nginx, with request
    buffering on and a 6 MiB cap) waits for the whole declared body, so the
    request times out; that is reported as inconclusive, not as a failure.
    """
    path = "/api/collections/campaigns/records"
    got = declare_oversize(base_url, path, declared, timeout=timeout)
    if got.error == "timeout":
        return Result("deployment.proxy.oversized-body.rejected", path, "proxy", "anonymous", 413, 0, False,
                      got.elapsed_ms,
                      f"inconclusive (buffering proxy in front): no answer within {timeout:g}s, so a proxy is "
                      f"waiting for the body; check the frontend's own cap through a port-forward to it",
                      inconclusive=True)
    if got.error:
        return Result("deployment.proxy.oversized-body.rejected", path, "proxy", "anonymous", 413, 0, False,
                      got.elapsed_ms, f"no response ({got.error})")
    try:
        code = json.loads(got.raw.decode("utf-8")).get("code")
    except (ValueError, UnicodeDecodeError, AttributeError):
        code = None
    ok = got.status == 413 and code == "payload_too_large"
    return Result("deployment.proxy.oversized-body.rejected", path, "proxy", "anonymous", 413, got.status, ok,
                  got.elapsed_ms, "" if ok else f"status={got.status} code={code!r}")


def check_proxy(base_url: str) -> list[Result]:
    base = base_url.rstrip("/")
    return (check_denied_routes(base) + [check_execute_gone(base)] + check_open_routes(base)
            + [check_oversized_body(base)])


# --------------------------------------------------------------------------
# admission and gate checks (ROUNDS-00A-L01 stage 4)
# --------------------------------------------------------------------------

MIB = 1024 * 1024
KIB = 1024
# The admitted routes, as backend/app/admission.py ROUTES lists them: method,
# path, the gate that turns the route off, the runner's own byte cap, and the
# cap nginx puts in front of it (frontend/nginx.conf). Kept in step with
# both by backend/tests/test_verify_deployment_admission.py.
ADMITTED_ROUTES: tuple[tuple[str, str, str, int, int], ...] = (
    ("POST", "/api/run", "RUN", 512 * KIB, 512 * KIB),
    ("POST", "/api/evaluate", "EVALUATE", 512 * KIB, 512 * KIB),
    ("POST", "/api/ai-coding/run-project", "AI_CODING_RUN_PROJECT", 6 * MIB, 6 * MIB),
    ("POST", "/api/ai-coding/grade", "AI_CODING_GRADE", 6 * MIB, 6 * MIB),
    ("POST", "/api/take-home/run", "TAKE_HOME_RUN", 6 * MIB, 6 * MIB),
    ("POST", "/api/take-home/submit", "TAKE_HOME_SUBMIT", 6 * MIB, 6 * MIB),
    ("POST", "/api/pdf/render", "PDF_RENDER", 2 * MIB, 6 * MIB),
    ("GET", "/api/pdf/health", "PDF_HEALTH", 0, 6 * MIB),
    ("POST", "/api/ai/ats-rule", "ATS_RULE", 1 * MIB, 6 * MIB),
)
ENVELOPE_KEYS = frozenset({"detail", "code", "correlation_id"})
ROUTE_GATE_VALUES = ("enabled", "disabled")
# The 503 an operator's stop answers, before the account
# (backend/app/admission.py): a route's own gate, and
# ROUNDS_GATE_EXECUTION_DEFINITIONS=disabled, which stops the six routes
# that run a definition. Kept in step with the runner by
# backend/tests/test_verify_deployment_admission.py.
STOP_CODES = ("route_disabled", "definitions_disabled")
STOPPED_BY = {
    "route_disabled": "its gate is off",
    "definitions_disabled": "ROUNDS_GATE_EXECUTION_DEFINITIONS is disabled",
}
DEFINITION_ROUTES = frozenset({
    "/api/run", "/api/evaluate", "/api/ai-coding/run-project", "/api/ai-coding/grade",
    "/api/take-home/run", "/api/take-home/submit",
})
ENFORCEMENT_GATES: dict[str, tuple[str, ...]] = {
    "ENFORCE_IDEMPOTENCY": ("off", "observe", "enforce"),
    "ENFORCE_QUOTA": ("off", "observe", "enforce"),
}
# A made-up bearer no deployment ever issued: a disabled route must refuse
# it before it asks PocketBase who it is.
BOGUS_BEARER = "verify-deployment-not-a-token"

# Every admission and gate check id this tool can report, with the
# guarantee it states. The harness verdict requires a passing receipt for
# each (harness/probes/run.py).
ADMISSION_CHECKS: dict[str, str] = {
    "deployment.admission.anonymous.denied":
        "every admitted route refuses a caller without a bearer before it reads the body: 401, or the 503 "
        "the operator expects for a route they turned off",
    "deployment.admission.error-shape.safe":
        "every admitted route's refusal is the typed envelope with the response's correlation id and nothing else",
    "deployment.admission.body-cap.rejected":
        "a body declared over an admitted route's cap gets the typed 413 before anything reads it",
    "deployment.gates.logged":
        "the runner's startup log lists every admitted route's gate and both enforcement gates",
    "deployment.gates.valid":
        "every logged gate holds one of its values, and none fell back from a value it doesn't know",
    "deployment.gates.expected":
        "each gate the operator named holds the value they expect",
    "deployment.gates.disabled-route.denied":
        "a route the operator turned off answers 503 with their stop's code for every caller",
}


def envelope_problem(status: int, raw: bytes, headers: dict[str, str]) -> str:
    """Why an answer isn't the typed admission/v1 envelope, or "" when it
    is: a JSON object of exactly detail, code, and correlation_id, a
    non-empty string detail and code, and a 32-hex correlation id that the
    X-Correlation-Id header repeats."""
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return "not JSON"
    if not isinstance(doc, dict):
        return "not a JSON object"
    if set(doc) != ENVELOPE_KEYS:
        extra = sorted(set(doc) - ENVELOPE_KEYS)
        missing = sorted(ENVELOPE_KEYS - set(doc))
        return f"keys differ (extra={extra}, missing={missing})"
    if not (isinstance(doc["detail"], str) and doc["detail"].strip()):
        return "detail isn't a sentence"
    if not (isinstance(doc["code"], str) and doc["code"]):
        return "code isn't a string"
    cid = doc["correlation_id"]
    if not (isinstance(cid, str) and len(cid) == 32 and all(c in "0123456789abcdef" for c in cid)):
        return "correlation_id isn't 32 hex"
    if headers.get("x-correlation-id") != cid:
        return "X-Correlation-Id header doesn't match"
    if status < 400:
        return f"status {status} isn't a refusal"
    return ""


def _code_of(raw: bytes) -> Any:
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return doc.get("code") if isinstance(doc, dict) else None


def parse_expected_disabled(items: Iterable[str]) -> dict[str, str]:
    """``--expect-disabled PATH[=CODE]`` values as {path: code}. CODE is
    the 503 the stop answers: route_disabled (the default) for the route's
    own gate, or definitions_disabled for one of the six execution routes
    while ROUNDS_GATE_EXECUTION_DEFINITIONS is disabled."""
    out: dict[str, str] = {}
    for item in items:
        path, sep, code = item.partition("=")
        path, code = path.strip(), (code.strip().lower() if sep else "route_disabled")
        admitted_method(path)
        if code not in STOP_CODES:
            raise ConfigError(f"--expect-disabled takes PATH or PATH=CODE, with CODE one of "
                              f"{', '.join(STOP_CODES)}, not {item!r}")
        if code == "definitions_disabled" and path not in DEFINITION_ROUTES:
            raise ConfigError(f"ROUNDS_GATE_EXECUTION_DEFINITIONS doesn't stop {path}; "
                              f"it stops {', '.join(sorted(DEFINITION_ROUTES))}")
        if out.get(path, code) != code:
            raise ConfigError(f"--expect-disabled names {path} with two codes")
        out[path] = code
    return out


def _expect_disabled_arg(path: str, code: str) -> str:
    return path if code == "route_disabled" else f"{path}={code}"


def check_admitted_routes(base_url: str, req: Callable[..., Response] = request,
                          actor: str = "anonymous", disabled: Iterable[str] = ()) -> list[Result]:
    """Every admitted route, without a bearer: refused before the body is
    read, in the typed envelope. That is 401 unauthenticated, or for a route
    in ``disabled`` (``PATH[=CODE]``, the ones the operator turned off) the
    503 its stop answers; a route that is off without being named fails, so
    a stop left on after a re-enable shows. One request per route; nothing
    is charged or run, since no account is admitted."""
    base = base_url.rstrip("/")
    off = parse_expected_disabled(disabled)
    out: list[Result] = []
    for method, path, _gate, _runner_cap, _edge_cap in ADMITTED_ROUTES:
        resp = req(method, base + path, body={} if method == "POST" else None)
        code = _code_of(resp.body)
        want = (503, off[path]) if path in off else (401, "unauthenticated")
        refused = (resp.status, code) == want
        if refused:
            why = ""
        elif resp.status == 503 and code in STOP_CODES:
            why = (f"{STOPPED_BY[code]}; give --expect-disabled {_expect_disabled_arg(path, code)} "
                   f"if you turned it off")
        else:
            why = f"status={resp.status} code={code!r} answered_by={answered_by(resp)}"
        out.append(Result("deployment.admission.anonymous.denied", path, "admission", actor, want[0], resp.status,
                          refused, resp.elapsed_ms, why))
        problem = envelope_problem(resp.status, resp.body, resp.headers) if resp.status else "unreachable"
        out.append(Result("deployment.admission.error-shape.safe", path, "admission", actor, resp.status or 401,
                          resp.status, not problem, resp.elapsed_ms, problem))
    return out


def _proxy_page(got: Declared) -> bool:
    """A 413 in neither the runner's shapes nor PocketBase's: a proxy ahead
    of the frontend refused the declared size with its own page (the
    Kubernetes ingress above its proxy-body-size, for one), so the
    frontend's cap was never reached."""
    return got.status == 413 and answered_by(Response(got.status, got.raw, got.headers, got.elapsed_ms)) == "proxy"


def check_admission_body_caps(base_url: str, *, at_runner: bool = False, timeout: float = 10.0,
                              actor: str = "anonymous") -> list[Result]:
    """Each POST route, with a body declared one byte over its cap and none
    of it sent: the typed 413. Through the public URL that is nginx's cap;
    with ``at_runner`` (the harness, straight at a replica) it is the
    runner's own, which it checks before the account. A proxy in front
    that waits for the body, or that answers its own 413 page for a size
    over its own cap, is inconclusive."""
    base = base_url.rstrip("/")
    out: list[Result] = []
    for method, path, _gate, runner_cap, edge_cap in ADMITTED_ROUTES:
        if method != "POST":
            continue
        cap = runner_cap if at_runner else edge_cap
        got = declare_oversize(base, path, cap + 1, timeout=timeout)
        target = f"{path} ({cap + 1} bytes declared)"
        if got.error == "timeout":
            out.append(Result("deployment.admission.body-cap.rejected", target, "admission", actor, 413, 0, False,
                              got.elapsed_ms,
                              f"inconclusive (buffering proxy in front): no answer within {timeout:g}s",
                              inconclusive=True))
            continue
        if got.error:
            out.append(Result("deployment.admission.body-cap.rejected", target, "admission", actor, 413, 0, False,
                              got.elapsed_ms, f"no response ({got.error})"))
            continue
        if _proxy_page(got):
            out.append(Result("deployment.admission.body-cap.rejected", target, "admission", actor, 413, got.status,
                              False, got.elapsed_ms,
                              "inconclusive (capped proxy in front): a 413 page that isn't the typed envelope, "
                              "so a proxy refused the size before the frontend saw it",
                              inconclusive=True))
            continue
        problem = envelope_problem(got.status, got.raw, got.headers)
        code = _code_of(got.raw)
        ok = got.status == 413 and code == "payload_too_large" and not problem
        out.append(Result("deployment.admission.body-cap.rejected", target, "admission", actor, 413, got.status, ok,
                          got.elapsed_ms, "" if ok else f"status={got.status} code={code!r} {problem}".strip()))
    return out


def admitted_method(path: str) -> str:
    for method, route, *_rest in ADMITTED_ROUTES:
        if route == path:
            return method
    raise ConfigError(f"{path} isn't an admitted route; give one of {', '.join(r[1] for r in ADMITTED_ROUTES)}")


def check_disabled_routes(base_url: str, paths: Iterable[str], req: Callable[..., Response] = request) -> list[Result]:
    """Each route the operator turned off (``PATH[=CODE]``) answers 503
    with its stop's code in the typed envelope, with no bearer and with a
    made-up one: both stops come before the account, so neither caller
    reaches PocketBase."""
    base = base_url.rstrip("/")
    out: list[Result] = []
    for path, want in parse_expected_disabled(paths).items():
        method = admitted_method(path)
        failures, last = [], None
        for actor, token in (("anonymous", ""), ("unknown-bearer", BOGUS_BEARER)):
            last = req(method, base + path, body={} if method == "POST" else None, token=token)
            code = _code_of(last.body)
            problem = envelope_problem(last.status, last.body, last.headers)
            if last.status != 503 or code != want or problem:
                failures.append(f"{actor}: status={last.status} code={code!r} {problem}".strip())
        out.append(Result("deployment.gates.disabled-route.denied", path, "gates", "anonymous", 503,
                          last.status if last else 0, not failures, last.elapsed_ms if last else 0,
                          "; ".join(failures)))
    return out


def parse_gates_log(text: str) -> dict[str, dict[str, str]] | None:
    """The gate table from the last runner ``gates`` line in a saved log.
    Lines may carry a compose or kubectl prefix before the JSON."""
    found = None
    for line in text.splitlines():
        start = line.find("{")
        if start < 0:
            continue
        try:
            doc = json.loads(line[start:])
        except ValueError:
            continue
        if isinstance(doc, dict) and doc.get("event") == "gates" and doc.get("service") == "runner" \
                and isinstance(doc.get("gates"), dict):
            found = doc["gates"]
    return found


def check_gates_log(text: str, expected: dict[str, str] | None = None, source: str = "runner log") -> list[Result]:
    """The runner's startup gates line: it lists every admitted route's gate
    and both enforcement gates, each value is one of its gate's values, none
    came from an invalid setting, and the gates the operator named hold the
    values they expect. Gate values aren't secret; the log is only read."""
    gates = parse_gates_log(text)
    if gates is None:
        missing = Result("deployment.gates.logged", source, "gates", "operator", 200, 0, False, 0,
                         "no runner gates line in the log; save the log from the runner's start")
        out = [missing, Result("deployment.gates.valid", source, "gates", "operator", 200, 0, False, 0,
                               "no gates line to check")]
        if expected:
            out.append(Result("deployment.gates.expected", source, "gates", "operator", 200, 0, False, 0,
                              "no gates line to check"))
        return out
    required = [r[2] for r in ADMITTED_ROUTES] + list(ENFORCEMENT_GATES)
    absent = [name for name in required if name not in gates]
    out = [Result("deployment.gates.logged", source, "gates", "operator", 200, 200, not absent, 0,
                  "" if not absent else "missing: " + ", ".join(absent))]
    problems = []
    route_gates = {r[2] for r in ADMITTED_ROUTES}
    for name, entry in sorted(gates.items()):
        if not isinstance(entry, dict):
            problems.append(f"{name}: not a value and source")
            continue
        value, how = entry.get("value"), entry.get("source")
        if how == "invalid":
            problems.append(f"{name} fell back to {value!r} from a value it doesn't know")
        allowed = ROUTE_GATE_VALUES if name in route_gates else ENFORCEMENT_GATES.get(name)
        if allowed is not None and value not in allowed:
            problems.append(f"{name}={value!r} isn't one of {', '.join(allowed)}")
    out.append(Result("deployment.gates.valid", source, "gates", "operator", 200, 200, not problems, 0,
                      "; ".join(problems)))
    if expected:
        wrong = [f"{name}={(gates.get(name) or {}).get('value')!r}, expected {want!r}"
                 for name, want in sorted(expected.items()) if (gates.get(name) or {}).get("value") != want]
        out.append(Result("deployment.gates.expected", source, "gates", "operator", 200, 200, not wrong, 0,
                          "; ".join(wrong)))
    return out


def parse_expected_gates(items: Iterable[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        name, sep, value = item.partition("=")
        name = name.strip().upper()
        if name.startswith("ROUNDS_GATE_"):
            name = name[len("ROUNDS_GATE_"):]
        if not sep or not name or not value.strip():
            raise ConfigError(f"--expect-gate takes NAME=VALUE, not {item!r}")
        out[name] = value.strip().lower()
    return out


# --------------------------------------------------------------------------
# credential checks (PocketBase's own port)
# --------------------------------------------------------------------------


def _admin_login(pb_url: str, identity: str, password: str, req: Callable[..., Response]) -> Response:
    return req("POST", pb_url + "/api/admins/auth-with-password", body={"identity": identity, "password": password})


def _login_refused(resp: Response) -> bool:
    doc = resp.json()
    return resp.status == 400 and not (isinstance(doc, dict) and doc.get("token"))


def check_default_logins(pb_url: str, req: Callable[..., Response] = request) -> Result:
    health = req("GET", pb_url + "/api/health")
    if health.status != 200:
        return Result("deployment.credentials.defaults.rejected", "_admins", "credentials", "anonymous", 400,
                      health.status, False, health.elapsed_ms,
                      f"PocketBase not reachable at the given --pb-url (status={health.status})")
    failures, last = [], None
    for label, identity, password in DEFAULT_ADMIN_LOGINS:
        last = _admin_login(pb_url, identity, password, req)
        if not _login_refused(last):
            failures.append(f"{label}: status={last.status}")
    return Result("deployment.credentials.defaults.rejected", "_admins", "credentials", "anonymous", 400,
                  last.status if last else 0, not failures, last.elapsed_ms if last else 0, "; ".join(failures))


def check_admin_passwords(pb_url: str, admin_emails: list[str], req: Callable[..., Response] = request) -> Result:
    if not admin_emails:
        return Result("deployment.credentials.admin-passwords.rejected", "_admins", "credentials", "anonymous", 400,
                      0, False, 0, "no admin accounts to check")
    accepted, last = 0, None
    for email in admin_emails:
        for password in DEFAULT_PASSWORDS:
            last = _admin_login(pb_url, email, password, req)
            if not _login_refused(last):
                accepted += 1
    ok = accepted == 0
    # Counts only: no email or password is ever printed.
    detail = "" if ok else (f"{accepted} admin login(s) with a shipped default password were not refused "
                            f"(of {len(admin_emails)} admin(s) x {len(DEFAULT_PASSWORDS)} password(s))")
    return Result("deployment.credentials.admin-passwords.rejected", "_admins", "credentials", "anonymous", 400,
                  last.status if last else 0, ok, last.elapsed_ms if last else 0, detail)


def admin_token(pb_url: str, email: str, password: str, req: Callable[..., Response] = request) -> str:
    resp = _admin_login(pb_url, email, password, req)
    doc = resp.json()
    if resp.status != 200 or not isinstance(doc, dict) or not doc.get("token"):
        raise RuntimeError(f"admin login with the given credentials failed (status={resp.status})")
    return doc["token"]


def live_admin_emails(pb_url: str, token: str, req: Callable[..., Response] = request) -> list[str]:
    resp = req("GET", pb_url + "/api/admins?perPage=500", token=token)
    doc = resp.json()
    if resp.status != 200 or not isinstance(doc, dict):
        raise RuntimeError(f"admin list failed (status={resp.status})")
    return [a["email"] for a in doc.get("items") or [] if isinstance(a, dict) and a.get("email")]


# --------------------------------------------------------------------------
# rule and admin checks
# --------------------------------------------------------------------------


class ConfigError(Exception):
    """A usage or configuration problem. The command line exits 2 with this
    message, after printing any results it had gathered."""


# The rule table in this checkout, used when --policy is not given.
DEFAULT_POLICY = Path(__file__).resolve().parents[1] / "docs" / "security" / "account-scope.v1.json"


def load_policy(path: str) -> dict:
    try:
        with open(path) as f:
            doc = json.load(f)
    except OSError as err:
        raise ConfigError(f"cannot read the policy at {path}: {err.strerror or err}") from None
    except ValueError as err:
        raise ConfigError(f"the policy at {path} is not valid JSON: {err}") from None
    if not isinstance(doc, dict) or doc.get("version") != "v1" or doc.get("contract") != "account-scope":
        raise ConfigError(f"{path} is not an account-scope v1 policy")
    cols = doc.get("collections")
    if not (isinstance(cols, dict) and cols
            and all(isinstance(r, dict) and isinstance(r.get("current_rules"), dict) for r in cols.values())):
        raise ConfigError(f"{path} has no collections with current_rules to compare")
    return doc


def compare_rules(policy: dict, live: dict[str, dict]) -> list[Result]:
    """One result per policy collection; `live` maps name -> collection fields."""
    out = []
    for name, row in policy["collections"].items():
        col = live.get(name)
        mismatches = []
        if col is None:
            mismatches.append("collection-missing")
        else:
            for key, want in row["current_rules"].items():
                if key in RULE_FIELD:
                    got = col.get(RULE_FIELD[key], _MISSING)
                elif key in AUTH_OPTION_RULE:
                    got = (col.get("options") or {}).get(AUTH_OPTION_RULE[key], _MISSING)
                else:
                    mismatches.append(f"{key}:unknown-rule-key")
                    continue
                if got != want:  # null, "", and a rule string are all distinct
                    mismatches.append(key)
            if name != "users" and col.get("createRule") == CREATE_IF_AUTHED:
                mismatches.append("create:still-any-signed-in-account")
        out.append(Result("deployment.rules.match", name, "rules", "operator", 200, 200, not mismatches, 0,
                          "" if not mismatches else "rules differ: " + ",".join(dict.fromkeys(mismatches))))
    return out


def live_rules(pb_url: str, token: str, req: Callable[..., Response] = request) -> dict[str, dict]:
    resp = req("GET", pb_url + "/api/collections?perPage=500", token=token)
    doc = resp.json()
    if resp.status != 200 or not isinstance(doc, dict):
        raise RuntimeError(f"collection list failed (status={resp.status})")
    return {c["name"]: c for c in doc.get("items") or [] if isinstance(c, dict) and "name" in c}


def _private_copy(db: Path, work: Path) -> Path:
    """Copy data.db (and its write-ahead log) with plain reads, then open the
    copy: the source may sit on a read-only mount, and is never opened with
    SQLite or changed."""
    target = work / "data.db"
    shutil.copyfile(db, target)
    for suffix in ("-wal", "-shm"):
        side = Path(str(db) + suffix)
        if side.exists():
            shutil.copyfile(side, Path(str(target) + suffix))
    return target


def read_copy(db_path: str) -> tuple[dict[str, dict], list[str]]:
    """Collection rules and admin emails from a pb_data copy."""
    with tempfile.TemporaryDirectory(prefix="verify-deployment-") as tmp:
        copy = _private_copy(Path(db_path), Path(tmp))
        conn = sqlite3.connect(str(copy))
        try:
            rows = conn.execute(
                "SELECT name, listRule, viewRule, createRule, updateRule, deleteRule, options FROM _collections"
            ).fetchall()
            emails = [r[0] for r in conn.execute("SELECT email FROM _admins") if r[0]]
        finally:
            conn.close()
    collections = {}
    for name, lst, view, create, update, delete, options in rows:
        try:
            opts = json.loads(options) if options else {}
        except ValueError:
            opts = {}
        collections[name] = {"name": name, "listRule": lst, "viewRule": view, "createRule": create,
                             "updateRule": update, "deleteRule": delete, "options": opts}
    return collections, emails


def check_admins_present(admin_emails: list[str]) -> Result:
    ok = len(admin_emails) >= 1
    return Result("deployment.admins.present", "_admins", "admins", "operator", 200, 200, ok, 0,
                  "" if ok else "no admin account: PocketBase's first-admin setup is open")


# --------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------


def is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_pb_transport(pb_url: str, allow_insecure: bool) -> None:
    """--pb-url carries the admin password, the superuser token, and admin
    emails, so plain HTTP is only for a loopback address (PocketBase's port
    forwarded to 127.0.0.1) unless the operator says otherwise."""
    parts = urllib.parse.urlsplit(pb_url)
    if parts.scheme == "https":
        return
    if parts.scheme != "http" or not parts.hostname:
        raise ConfigError(f"--pb-url must be an http or https URL, not {pb_url!r}")
    if is_loopback(parts.hostname) or allow_insecure:
        return
    raise ConfigError(
        "--pb-url is plain HTTP to a host that is not loopback, so the admin password, token, and admin emails "
        "would cross the network unencrypted; use https, forward PocketBase's port to 127.0.0.1, or pass "
        "--allow-insecure for a private network you trust"
    )


def validate(args: argparse.Namespace, env: dict[str, str]) -> dict | None:
    """Usage and configuration checks before any request. Returns the policy
    when rules will be compared."""
    if not (args.url or args.pb_url or args.db or args.gates_log):
        raise ConfigError("give at least one of --url, --pb-url, --db, --gates-log")
    if (args.admission or args.expect_disabled) and not args.url:
        raise ConfigError("--admission and --expect-disabled need --url")
    if args.expect_gate and not args.gates_log:
        raise ConfigError("--expect-gate needs --gates-log")
    parse_expected_disabled(args.expect_disabled or [])
    parse_expected_gates(args.expect_gate or [])
    if args.admin_email and not args.pb_url:
        raise ConfigError("--admin-email needs --pb-url")
    if args.admin_email and not env.get(args.admin_password_env):
        raise ConfigError(f"--admin-email needs that admin's password in ${args.admin_password_env}")
    if args.policy and not (args.db or args.admin_email):
        raise ConfigError("--policy needs --db or --admin-email, which supply the rules to compare")
    if args.pb_url:
        check_pb_transport(args.pb_url, args.allow_insecure)
    if args.db or args.admin_email:
        return load_policy(args.policy or str(DEFAULT_POLICY))
    return None


def run(args: argparse.Namespace, env: dict[str, str], policy: dict | None, results: list[Result]) -> None:
    """Runs the requested checks, appending to `results` as it goes so a later
    error keeps what was already gathered."""
    if args.url:
        results += check_proxy(args.url)
        if args.admission:
            results += check_admitted_routes(args.url, disabled=args.expect_disabled or [])
            results += check_admission_body_caps(args.url)
        if args.expect_disabled:
            results += check_disabled_routes(args.url, args.expect_disabled)

    if args.gates_log:
        try:
            text = Path(args.gates_log).read_text(encoding="utf-8", errors="replace")
        except OSError as err:
            raise ConfigError(f"cannot read the gates log at {args.gates_log}: {err.strerror or err}") from None
        results += check_gates_log(text, parse_expected_gates(args.expect_gate or []), source=args.gates_log)

    admin_emails: list[str] | None = None
    if args.db:
        collections, emails = read_copy(args.db)
        admin_emails = emails
        results.append(check_admins_present(emails))
        results += compare_rules(policy, collections)

    if args.pb_url:
        pb = args.pb_url.rstrip("/")
        results.append(check_default_logins(pb))
        if args.admin_email:
            token = admin_token(pb, args.admin_email, env[args.admin_password_env])
            admin_emails = live_admin_emails(pb, token)
            results += compare_rules(policy, live_rules(pb, token))
        if admin_emails is not None:
            results.append(check_admin_passwords(pb, admin_emails))


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--url", help="the deployment's public URL (through the frontend nginx)")
    p.add_argument("--pb-url", help="PocketBase's own port, for example http://127.0.0.1:8090 forwarded from its container")
    p.add_argument("--db", help="data.db in a pb_data copy taken with PocketBase stopped")
    p.add_argument("--policy", help="the rule table to compare with (default: docs/security/account-scope.v1.json in this checkout)")
    p.add_argument("--admin-email", help="an admin login to read the live rules and admin list (read-only)")
    p.add_argument("--admin-password-env", default="PB_ADMIN_PASSWORD",
                   help="environment variable holding that admin's password (default PB_ADMIN_PASSWORD)")
    p.add_argument("--allow-insecure", action="store_true",
                   help="allow a plain-HTTP --pb-url that is not loopback (a private network you trust)")
    p.add_argument("--admission", action="store_true",
                   help="with --url: every admitted route refuses an anonymous caller in the typed envelope (401, "
                        "or the 503 --expect-disabled names for a route that is off), and a body declared over its "
                        "cap gets the typed 413 (headers only; nothing is charged or run)")
    p.add_argument("--expect-disabled", action="append", metavar="PATH[=CODE]",
                   help="with --url: this admitted route is off, so it answers 503 CODE for every caller: "
                        "route_disabled (the default) when its own gate is off, or definitions_disabled for the six "
                        "execution routes when ROUNDS_GATE_EXECUTION_DEFINITIONS is disabled (repeatable; for "
                        "confirming an emergency disable)")
    p.add_argument("--gates-log", metavar="FILE",
                   help="a saved runner log from its start: check the gates line it writes")
    p.add_argument("--expect-gate", action="append", metavar="NAME=VALUE",
                   help="with --gates-log: this gate should hold this value (repeatable), e.g. RUN=disabled")
    p.add_argument("--receipts", help="append one JSON line per check (harness receipt schema) to this file")
    return p.parse_args(argv)


def _line(r: Result) -> str:
    label = "PASS" if r.passed else ("INCONCLUSIVE" if r.inconclusive else "FAIL")
    return f"{label} {r.check_id} [{r.target}]" + ("" if r.passed else f": {r.detail}")


def main(argv: list[str] | None = None, env: dict[str, str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    env = dict(os.environ) if env is None else env
    results: list[Result] = []
    error = ""
    try:
        policy = validate(args, env)
        run(args, env, policy, results)
    except ConfigError as err:
        error = str(err)
    except (RuntimeError, OSError, sqlite3.Error) as err:
        error = f"could not finish: {err}"
    for r in results:
        print(_line(r))
    if args.receipts and results:
        write_receipts(args.receipts, results, {
            "run_id": env.get("RUN_ID", ""), "commit": env.get("GIT_COMMIT", ""), "phase": "deployment",
        })
    if error:
        print(f"verify_deployment: {error}", file=sys.stderr)
        return 2
    inconclusive = sum(1 for r in results if r.inconclusive)
    failed = sum(1 for r in results if not r.passed and not r.inconclusive)
    passed = len(results) - failed - inconclusive
    print(f"verify_deployment: {passed} passed, {failed} failed, {inconclusive} inconclusive")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
