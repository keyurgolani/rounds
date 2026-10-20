#!/usr/bin/env python3
"""Deployment verification for the account-scope invariant (ROUNDS-00B-L01 stage 4).

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

It never writes. Every request is a read, a login that is expected to fail, or a
request nginx refuses on its headers before PocketBase sees it. It prints no
credentials, emails, tokens, or record contents. The admin password, when
given, comes from an environment variable, never the command line.

Standard library only, Python 3.9 or newer.

Exit status: 0 every check passed, 1 a check failed, 2 the checks could not run
(bad arguments, nothing to check).
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import shutil
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
    opener = urllib.request.build_opener(_NoRedirect)
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

    # Without a provider's state and code PocketBase refuses the redirect, but
    # it is PocketBase that answers, not nginx.
    path = "/api/oauth2-redirect"
    resp = req("GET", base_url + path)
    out.append(_open_route("deployment.proxy.oauth-redirect.open", path, resp,
                           answered_by(resp) == "pocketbase" or 300 <= resp.status < 400,
                           resp.status, "expected PocketBase to answer"))

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
        resp = urllib.request.urlopen(req, timeout=timeout)
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


def check_oversized_body(base_url: str, declared: int = NGINX_BODY_CAP + 1, timeout: float = 10.0) -> Result:
    """Declare a body one byte over nginx's cap and send none of it: nginx
    decides on the Content-Length header alone, so nothing large is sent and
    PocketBase never sees the request."""
    path = "/api/collections/campaigns/records"
    parts = urllib.parse.urlsplit(base_url)
    conn_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    kwargs: dict[str, Any] = {"timeout": timeout}
    if parts.scheme == "https":
        kwargs["context"] = ssl.create_default_context()
    start = time.monotonic()
    try:
        conn = conn_cls(parts.netloc, **kwargs)
        try:
            conn.putrequest("POST", (parts.path.rstrip("/") or "") + path)
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", str(declared))
            conn.endheaders()
            resp = conn.getresponse()
            status, raw = resp.status, resp.read()
        finally:
            conn.close()
    except (OSError, http.client.HTTPException) as err:
        return Result("deployment.proxy.oversized-body.rejected", path, "proxy", "anonymous", 413, 0, False,
                      int((time.monotonic() - start) * 1000), f"no response ({type(err).__name__})")
    elapsed = int((time.monotonic() - start) * 1000)
    try:
        code = json.loads(raw.decode("utf-8")).get("code")
    except (ValueError, UnicodeDecodeError, AttributeError):
        code = None
    ok = status == 413 and code == "payload_too_large"
    return Result("deployment.proxy.oversized-body.rejected", path, "proxy", "anonymous", 413, status, ok, elapsed,
                  "" if ok else f"status={status} code={code!r}")


def check_proxy(base_url: str) -> list[Result]:
    base = base_url.rstrip("/")
    return (check_denied_routes(base) + [check_execute_gone(base)] + check_open_routes(base)
            + [check_oversized_body(base)])


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


def load_policy(path: str) -> dict:
    with open(path) as f:
        doc = json.load(f)
    if doc.get("version") != "v1" or doc.get("contract") != "account-scope":
        raise ValueError(f"unsupported policy {doc.get('contract')!r} {doc.get('version')!r}")
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


def run(args: argparse.Namespace, env: dict[str, str]) -> list[Result]:
    results: list[Result] = []
    if args.url:
        results += check_proxy(args.url)

    admin_emails: list[str] | None = None
    policy = load_policy(args.policy) if args.policy else None

    if args.db:
        collections, emails = read_copy(args.db)
        admin_emails = emails
        results.append(check_admins_present(emails))
        if policy:
            results += compare_rules(policy, collections)

    if args.pb_url:
        pb = args.pb_url.rstrip("/")
        results.append(check_default_logins(pb))
        if args.admin_email:
            password = env.get(args.admin_password_env, "")
            if not password:
                raise SystemExit(f"--admin-email needs the password in ${args.admin_password_env}")
            token = admin_token(pb, args.admin_email, password)
            admin_emails = live_admin_emails(pb, token)
            if policy:
                results += compare_rules(policy, live_rules(pb, token))
        if admin_emails is not None:
            results.append(check_admin_passwords(pb, admin_emails))
    return results


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--url", help="the deployment's public URL (through the frontend nginx)")
    p.add_argument("--pb-url", help="PocketBase's own port, for example http://127.0.0.1:8090 in its container")
    p.add_argument("--db", help="data.db in a pb_data copy taken with PocketBase stopped")
    p.add_argument("--policy", help="docs/security/account-scope.v1.json, to compare rules")
    p.add_argument("--admin-email", help="an admin login to read the live rules and admin list (read-only)")
    p.add_argument("--admin-password-env", default="PB_ADMIN_PASSWORD",
                   help="environment variable holding that admin's password (default PB_ADMIN_PASSWORD)")
    p.add_argument("--receipts", help="append one JSON line per check (harness receipt schema) to this file")
    return p.parse_args(argv)


def main(argv: list[str] | None = None, env: dict[str, str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    env = dict(os.environ) if env is None else env
    if not (args.url or args.pb_url or args.db):
        print("verify_deployment: give at least one of --url, --pb-url, --db", file=sys.stderr)
        return 2
    if args.admin_email and not args.pb_url:
        print("verify_deployment: --admin-email needs --pb-url", file=sys.stderr)
        return 2
    try:
        results = run(args, env)
    except (RuntimeError, ValueError, OSError, sqlite3.Error) as err:
        print(f"verify_deployment: could not run: {err}", file=sys.stderr)
        return 2
    for r in results:
        print(("PASS " if r.passed else "FAIL ") + f"{r.check_id} [{r.target}]" + ("" if r.passed else f": {r.detail}"))
    if args.receipts:
        write_receipts(args.receipts, results, {
            "run_id": env.get("RUN_ID", ""), "commit": env.get("GIT_COMMIT", ""), "phase": "deployment",
        })
    failed = sum(1 for r in results if not r.passed)
    print(f"verify_deployment: {len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
