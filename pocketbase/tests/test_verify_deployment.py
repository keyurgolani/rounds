"""Tests for harness/verify_deployment.py (ROUNDS-00B-L01 stage 4).

Each check runs against a local fake server that answers like a correctly
proxied deployment, then like a misconfigured one, so every check is shown to
pass on the real shape and fail on the wrong one. The rule and admin checks run
on synthetic SQLite copies. No test reaches a real host.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import re
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "harness" / "probes"))

import verify_deployment as vd  # noqa: E402
import receipts  # noqa: E402

NGINX_404 = b"<html>\r\n<head><title>404 Not Found</title></head>\r\n<body>\r\n<center><h1>404 Not Found</h1></center>\r\n<hr><center>nginx</center>\r\n</body>\r\n</html>\r\n"
PB_404 = {"code": 404, "message": "The requested resource wasn't found.", "data": {}}
PB_401 = {"code": 401, "message": "The request requires admin authorization token to be set.", "data": {}}
DENIED_PREFIXES = ("/_/", "/api/admins", "/api/settings", "/api/backups", "/api/logs", "/api/rounds/admission/")


class Deployment:
    """What the fake answers. Defaults to a correctly proxied deployment."""

    def __init__(self) -> None:
        self.overrides: dict[tuple[str, str], tuple[int, object]] = {}
        self.accept_logins: set[tuple[str, str]] = set()
        self.admins = ["ops@example.test"]
        self.health = 200
        self.realtime_event = "PB_CONNECT"
        self.oversize_reaches_pocketbase = False

    def answer(self, method: str, path: str, body: bytes):
        if (method, path) in self.overrides:
            return self.overrides[(method, path)]
        bare = path.split("?", 1)[0]
        if bare == "/api/health":
            return self.health, ({"code": 200, "message": "API is healthy.", "data": {}} if self.health == 200 else NGINX_404)
        if bare == "/api/admins/auth-with-password" and self.pb_port:
            creds = json.loads(body or b"{}")
            if (creds.get("identity"), creds.get("password")) in self.accept_logins:
                return 200, {"token": "fake-admin-token", "admin": {"id": "a1"}}
            return 400, {"code": 400, "message": "Failed to authenticate.", "data": {}}
        if bare == "/api/admins" and self.pb_port:
            return 200, {"items": [{"id": f"a{i}", "email": e} for i, e in enumerate(self.admins)], "totalItems": len(self.admins)}
        if bare == "/api/collections" and self.pb_port:
            return 200, {"items": [], "totalItems": 0}
        if any(bare == p or bare.startswith(p) for p in DENIED_PREFIXES) or re.fullmatch(r"/api/collections(/[^/]+)?/?", bare):
            return 404, NGINX_404
        if bare == "/api/execute":
            return 404, PB_404
        if bare == "/api/collections/campaigns/records":
            return 200, {"page": 1, "perPage": 1, "totalItems": 0, "items": []}
        if bare == "/api/collections/users/auth-methods":
            return 200, {"usernamePassword": False, "emailPassword": True, "authProviders": []}
        if bare == "/api/oauth2-redirect":
            return 400, {"code": 400, "message": "Invalid OAuth2 redirect.", "data": {}}
        if bare.startswith("/api/files/"):
            return 404, PB_404
        return 404, NGINX_404

    pb_port = False


def _server(dep: Deployment):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # quiet
            pass

        def _send(self, status, payload, content_type=None):
            raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type or ("text/html" if isinstance(payload, bytes) else "application/json"))
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _handle(self):
            length = int(self.headers.get("Content-Length") or 0)
            if self.command == "POST" and self.path == "/api/collections/campaigns/records" and length > vd.NGINX_BODY_CAP:
                # Decided on the header alone, like nginx: the body is never read.
                if dep.oversize_reaches_pocketbase:
                    self._send(400, {"code": 400, "message": "Failed to create record.", "data": {}})
                else:
                    self._send(413, {"detail": "too large", "code": "payload_too_large", "correlation_id": "x"})
                self.close_connection = True
                return
            body = self.rfile.read(length) if length else b""
            if self.path == "/api/realtime":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(f"id:abc\nevent:{dep.realtime_event}\ndata:{{}}\n\n".encode())
                self.wfile.flush()
                return
            status, payload = dep.answer(self.command, self.path, body)
            self._send(status, payload)

        do_GET = do_POST = do_PATCH = do_PUT = do_DELETE = _handle

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@contextlib.contextmanager
def deployment(dep: Deployment | None = None, *, pb_port: bool = False):
    dep = dep or Deployment()
    dep.pb_port = pb_port
    srv = _server(dep)
    try:
        yield dep, f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()


def by_id(results):
    out = {}
    for r in results:
        out.setdefault(r.check_id, []).append(r)
    return out


# --------------------------------------------------------------------------
# proxy
# --------------------------------------------------------------------------


def test_a_correctly_proxied_deployment_passes_every_proxy_check():
    with deployment() as (_, url):
        results = vd.check_proxy(url)
    failed = [f"{r.check_id}: {r.detail}" for r in results if not r.passed]
    assert failed == []
    ids = {r.check_id for r in results}
    assert {c for c in vd.CHECKS if c.startswith("deployment.proxy.")} == ids


def test_a_denied_route_that_reaches_pocketbase_fails():
    dep = Deployment()
    dep.overrides[("GET", "/api/admins")] = (401, PB_401)
    with deployment(dep) as (_, url):
        results = by_id(vd.check_denied_routes(url))
    r = results["deployment.proxy.admin-api.denied"][0]
    assert not r.passed and "answered_by=pocketbase" in r.detail


def test_the_admin_ui_served_through_the_proxy_fails():
    dep = Deployment()
    dep.overrides[("GET", "/_/")] = (200, b"<html>PocketBase admin</html>")
    with deployment(dep) as (_, url):
        results = by_id(vd.check_denied_routes(url))
    assert not results["deployment.proxy.admin-ui.denied"][0].passed


def test_collection_metadata_reaching_pocketbase_fails_but_records_stay_open():
    dep = Deployment()
    dep.overrides[("GET", "/api/collections")] = (401, PB_401)
    with deployment(dep) as (_, url):
        denied = by_id(vd.check_denied_routes(url))
        opened = by_id(vd.check_open_routes(url))
    assert not denied["deployment.proxy.collection-metadata.denied"][0].passed
    assert opened["deployment.proxy.records.open"][0].passed


def test_execute_answered_by_the_runner_fails():
    dep = Deployment()
    dep.overrides[("POST", "/api/execute")] = (422, {"detail": [{"loc": ["body"], "msg": "field required"}]})
    with deployment(dep) as (_, url):
        r = vd.check_execute_gone(url)
    assert not r.passed and "answered_by=runner" in r.detail


@pytest.mark.parametrize("path,check_id", [
    ("/api/health", "deployment.proxy.health.open"),
    ("/api/collections/campaigns/records?perPage=1", "deployment.proxy.records.open"),
    ("/api/collections/users/auth-methods", "deployment.proxy.auth.open"),
    ("/api/oauth2-redirect", "deployment.proxy.oauth-redirect.open"),
    ("/api/files/users/verify0deployment/verify.txt", "deployment.proxy.files.open"),
])
def test_an_open_route_the_proxy_blocks_fails(path, check_id):
    dep = Deployment()
    dep.overrides[("GET", path)] = (404, NGINX_404)
    if path == "/api/health":
        dep.health = 404
    with deployment(dep) as (_, url):
        results = by_id(vd.check_open_routes(url))
    assert not results[check_id][0].passed


def test_realtime_without_the_connect_event_fails():
    dep = Deployment()
    dep.realtime_event = "something-else"
    with deployment(dep) as (_, url):
        results = by_id(vd.check_open_routes(url))
    assert not results["deployment.proxy.realtime.open"][0].passed


def test_an_oversized_body_reaching_pocketbase_fails():
    dep = Deployment()
    dep.oversize_reaches_pocketbase = True
    with deployment(dep) as (_, url):
        r = vd.check_oversized_body(url)
    assert not r.passed and r.observed_status == 400


def test_the_oversized_check_sends_no_body():
    # The check declares a large body and sends none, so it can't be slow or
    # push data at a deployment; a server that read the body would hang here.
    with deployment() as (_, url):
        r = vd.check_oversized_body(url, timeout=3)
    assert r.passed


# --------------------------------------------------------------------------
# credentials
# --------------------------------------------------------------------------


def test_default_logins_refused_passes():
    with deployment(pb_port=True) as (_, url):
        r = vd.check_default_logins(url)
    assert r.passed


@pytest.mark.parametrize("label,identity,password", vd.DEFAULT_ADMIN_LOGINS)
def test_any_accepted_default_login_fails(label, identity, password):
    dep = Deployment()
    dep.accept_logins.add((identity, password))
    with deployment(dep, pb_port=True) as (_, url):
        r = vd.check_default_logins(url)
    assert not r.passed and label in r.detail
    assert password not in r.detail and identity not in r.detail


def test_default_logins_fail_closed_when_pocketbase_is_unreachable():
    r = vd.check_default_logins("http://127.0.0.1:9")  # nothing listens on the discard port
    assert not r.passed and "not reachable" in r.detail


def test_an_admin_with_a_shipped_default_password_fails_without_naming_it():
    dep = Deployment()
    dep.admins = ["first@example.test", "second@example.test"]
    dep.accept_logins.add(("second@example.test", vd.DEFAULT_PASSWORDS[0]))
    with deployment(dep, pb_port=True) as (_, url):
        r = vd.check_admin_passwords(url, dep.admins)
    assert not r.passed
    assert "second@example.test" not in r.detail and vd.DEFAULT_PASSWORDS[0] not in r.detail
    assert r.detail.startswith("1 admin login")


def test_admins_without_default_passwords_pass():
    with deployment(pb_port=True) as (dep, url):
        r = vd.check_admin_passwords(url, dep.admins)
    assert r.passed


def test_no_admin_accounts_to_check_fails():
    with deployment(pb_port=True) as (_, url):
        r = vd.check_admin_passwords(url, [])
    assert not r.passed


def test_shipped_defaults_match_the_files_that_ship_them():
    demo = (ROOT / "pocketbase" / "pb_migrations" / "1700000600_demo_user.js").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()
    pb_auth = (ROOT / "backend" / "app" / "pb_auth.py").read_text()
    logins = {(i, p) for _, i, p in vd.DEFAULT_ADMIN_LOGINS}
    demo_email = re.search(r'DEMO_EMAIL = "([^"]+)"', demo).group(1)
    demo_password = re.search(r'DEMO_PASSWORD = "([^"]+)"', demo).group(1)
    assert (demo_email, demo_password) in logins
    for text in (compose, pb_auth):
        email = re.search(r"PB_ADMIN_EMAIL[^\n]*?(?::-|\", \")([^}\"\s]+)", text).group(1)
        password = re.search(r"PB_ADMIN_PASSWORD[^\n]*?(?::-|\", \")([^}\"\s]+)", text).group(1)
        assert (email, password) in logins, (email, password)


# --------------------------------------------------------------------------
# rules and admins
# --------------------------------------------------------------------------


POLICY = {
    "version": "v1",
    "contract": "account-scope",
    "collections": {
        "campaigns": {"current_rules": {"list": "user = @request.auth.id", "create": "x = 1", "update": "y = 1"}},
        "resume_share_views": {"current_rules": {"create": None, "update": None}},
        "users": {"current_rules": {"create": "", "manage": None}},
    },
}


def _live(**overrides):
    live = {
        "campaigns": {"name": "campaigns", "listRule": "user = @request.auth.id", "createRule": "x = 1", "updateRule": "y = 1"},
        "resume_share_views": {"name": "resume_share_views", "createRule": None, "updateRule": None},
        "users": {"name": "users", "createRule": "", "options": {"manageRule": None}},
    }
    for name, fields in overrides.items():
        live[name] = {**live.get(name, {"name": name}), **fields}
    return live


def test_matching_rules_pass():
    assert all(r.passed for r in vd.compare_rules(POLICY, _live()))


def test_a_loosened_rule_fails_for_that_collection_only():
    results = {r.target: r for r in vd.compare_rules(POLICY, _live(campaigns={"updateRule": ""}))}
    assert not results["campaigns"].passed and "update" in results["campaigns"].detail
    assert results["users"].passed


def test_null_and_empty_rules_are_distinct():
    results = {r.target: r for r in vd.compare_rules(POLICY, _live(resume_share_views={"createRule": ""}))}
    assert not results["resume_share_views"].passed


def test_the_old_any_signed_in_create_rule_is_flagged():
    policy = json.loads(json.dumps(POLICY))
    policy["collections"]["campaigns"]["current_rules"]["create"] = vd.CREATE_IF_AUTHED
    results = {r.target: r for r in vd.compare_rules(policy, _live(campaigns={"createRule": vd.CREATE_IF_AUTHED}))}
    assert not results["campaigns"].passed and "still-any-signed-in-account" in results["campaigns"].detail


def test_a_missing_collection_fails():
    live = _live()
    del live["campaigns"]
    results = {r.target: r for r in vd.compare_rules(POLICY, live)}
    assert not results["campaigns"].passed and "collection-missing" in results["campaigns"].detail


def _copy(tmp_path: Path, admins: list[str]) -> str:
    db = tmp_path / "data.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE _collections (name TEXT, listRule TEXT, viewRule TEXT, createRule TEXT, "
                 "updateRule TEXT, deleteRule TEXT, options TEXT)")
    conn.execute("INSERT INTO _collections VALUES ('campaigns','user = @request.auth.id',NULL,'x = 1','y = 1',NULL,'{}')")
    conn.execute("INSERT INTO _collections VALUES ('resume_share_views',NULL,NULL,NULL,NULL,NULL,'{}')")
    conn.execute("INSERT INTO _collections VALUES ('users',NULL,NULL,'',NULL,NULL,'{\"manageRule\":null}')")
    conn.execute("CREATE TABLE _admins (id TEXT, email TEXT)")
    conn.executemany("INSERT INTO _admins VALUES (?, ?)", [(f"a{i}", e) for i, e in enumerate(admins)])
    conn.commit()
    conn.close()
    return str(db)


def test_a_copy_with_matching_rules_and_an_admin_passes(tmp_path):
    collections, emails = vd.read_copy(_copy(tmp_path, ["ops@example.test"]))
    assert vd.check_admins_present(emails).passed
    assert all(r.passed for r in vd.compare_rules(POLICY, collections))


def test_a_copy_with_no_admin_fails(tmp_path):
    _, emails = vd.read_copy(_copy(tmp_path, []))
    r = vd.check_admins_present(emails)
    assert not r.passed and "first-admin setup is open" in r.detail


def test_reading_a_copy_never_changes_the_source(tmp_path):
    db = _copy(tmp_path, ["ops@example.test"])
    before = Path(db).read_bytes()
    Path(db).chmod(0o444)
    vd.read_copy(db)
    assert Path(db).read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["data.db"]


# --------------------------------------------------------------------------
# receipts, policy, and the command line
# --------------------------------------------------------------------------


def test_receipts_use_the_harness_schema():
    assert [f.name for f in dataclasses.fields(vd.Receipt)] == [f.name for f in dataclasses.fields(receipts.Receipt)]


def test_the_policy_lists_exactly_the_checks_this_tool_reports():
    policy = json.loads((ROOT / "docs" / "security" / "account-scope.v1.json").read_text())
    assert set(policy["deployment_checks"]) == set(vd.CHECKS)
    for check_id, entry in policy["deployment_checks"].items():
        assert entry["guarantee"] == vd.CHECKS[check_id]


def test_main_needs_something_to_check():
    assert vd.main([], env={}) == 2


def test_main_refuses_an_admin_login_without_pocketbase_url():
    assert vd.main(["--url", "http://127.0.0.1:9", "--admin-email", "x@example.test"], env={}) == 2


def test_a_full_run_prints_no_credential_and_writes_receipts(tmp_path, capsys):
    dep = Deployment()
    dep.admins = ["ops@example.test"]
    dep.accept_logins.add(("ops@example.test", "operator-test-password"))
    out_path = tmp_path / "receipts.jsonl"
    with deployment(dep, pb_port=True) as (_, url):
        code = vd.main(["--pb-url", url, "--admin-email", "ops@example.test", "--policy",
                        str(ROOT / "docs" / "security" / "account-scope.v1.json"), "--receipts", str(out_path)],
                       env={"PB_ADMIN_PASSWORD": "operator-test-password"})
    printed = capsys.readouterr().out
    for secret in ("ops@example.test", "operator-test-password", *vd.DEFAULT_PASSWORDS):
        assert secret not in printed
    rows = [json.loads(line) for line in out_path.read_text().splitlines()]
    assert rows and all(set(r) == {f.name for f in dataclasses.fields(receipts.Receipt)} for r in rows)
    assert all(not any(s in json.dumps(r) for s in ("operator-test-password", "fake-admin-token")) for r in rows)
    # The fake has no collections, so the rule checks fail; the credential checks pass.
    assert code == 1
    assert {r["probe_id"] for r in rows if r["passed"]} >= {
        "deployment.credentials.defaults.rejected", "deployment.credentials.admin-passwords.rejected"}
