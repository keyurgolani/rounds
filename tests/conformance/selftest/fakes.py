"""Fake targets for the framework self-tests and the negative controls.

``FakeRunner`` and ``FakePocketBase`` answer the way the stack does when
each guarantee holds. Each guarantee can be switched off by name, and the
fake then answers the way a stack without it would, so a test can show
that every fixture reports ``contained`` against the guarded target and
``detected`` once its guarantee is gone (the negative control). They
model status codes and response bodies only; nothing here runs code.
"""
from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass, field
from typing import Any

from conformance.budget import Budget
from conformance.canaries import CanarySet
from conformance.context import Http, RouteLog, RunContext

ADMITTED = {
    ("POST", "/api/run"), ("POST", "/api/evaluate"), ("POST", "/api/ai-coding/run-project"),
    ("POST", "/api/ai-coding/grade"), ("POST", "/api/take-home/run"), ("POST", "/api/take-home/submit"),
    ("POST", "/api/pdf/render"), ("GET", "/api/pdf/health"),
}
CALLER_FIELDS = {"test_command", "timeout_s", "validators", "entry", "env", "image", "limits"}
BYTE_CAP = 512 * 1024
TOKEN = "fake-token-placeholder"

# The guarantees a fake can switch off, by the fixture that checks them.
GUARANTEES = (
    "account-step",         # EX-01: admitted routes refuse anonymous callers
    "account-before-body",  # EX-01: the account is checked before the body
    "owner-read",           # EX-02: another account's result row is hidden
    "uniform-missing",      # EX-02: a foreign id reads as a missing one
    "demo-flags",           # EX-03: client writes to the demo flags are refused
    "byte-cap",             # EX-04: the cap is decided from the declared length
    "caller-fields",        # EX-04/05/06: caller-chosen fields are refused by name
    "minimal-env",          # EX-07: candidate processes get a minimal environment
    "health-status-only",   # RD-07: health answers only its status
    "health-status-value",  # RD-07: that status is one of health's own values
    "typed-render-failure", # RD-07: a failed render is the typed envelope
)
# Routes a test turns off by their gate, and the stop each answers.
GATE_STOPS = {"route_disabled", "definitions_disabled"}


def envelope(code: str, detail: str = "A fixed sentence.") -> dict:
    return {"detail": detail, "code": code, "correlation_id": "0" * 32}


def _http(status: int, body: Any) -> Http:
    return Http(status, body, json.dumps(body), {})


@dataclass
class Account:
    user_id: str
    token: str
    tag: str = ""
    email: str = ""


class FakeRunner:
    def __init__(self, budget: Budget, log: RouteLog, off: set[str], canaries: CanarySet,
                 gated: dict[str, str] | None = None) -> None:
        self.budget = budget
        self.log = log
        self.off = off
        self.canaries = canaries
        # path -> the stop its gate answers, before the account.
        self.gated = gated or {}

    def request(self, method: str, path: str, *, token: str | None = None, json_body: Any = None,
                headers: dict[str, str] | None = None) -> Http:
        self.log.add(method, path)
        with self.budget.spend():
            return self._answer(method, path, token, json_body or {})

    def declare(self, method: str, path: str, declared: int, *, timeout: float = 10.0) -> Http:
        self.log.add(method, path)
        with self.budget.spend():
            if (method, path) in ADMITTED and declared > BYTE_CAP:
                if "byte-cap" in self.off:
                    # Without the cap from the declared length the runner
                    # waits for a body that never comes.
                    return Http(0, None, "", {}, "timeout")
                return _http(413, envelope("payload_too_large"))
            return _http(401, envelope("unauthenticated"))

    def _answer(self, method: str, path: str, token: str | None, body: dict) -> Http:
        if (method, path) not in ADMITTED:
            return _http(404, envelope("not_found"))
        if path in self.gated:
            return _http(503, envelope(self.gated[path]))
        if not token and "account-before-body" in self.off:
            # A stack that validates the body before the account answers an
            # anonymous caller with a body error, not the account denial.
            return _http(422, envelope("invalid_request"))
        if not token and "account-step" not in self.off:
            return _http(401, envelope("unauthenticated"))
        if CALLER_FIELDS & set(body) and "caller-fields" not in self.off:
            return _http(422, envelope("legacy_request_rejected"))
        if path == "/api/pdf/health":
            out = {"status": "unavailable"}
            if "health-status-only" in self.off:
                out["code"] = 503
            if "health-status-value" in self.off:
                out["status"] = "URLError: renderer unreachable"
            return _http(503, out)
        if path == "/api/pdf/render":
            detail = "The PDF renderer couldn't finish this document. Try again shortly."
            if "typed-render-failure" in self.off:
                detail = "URLError: renderer unreachable"
            return _http(503, envelope("worker_unavailable", detail))
        if path == "/api/run":
            env = [["PATH", "/usr/bin"], ["HOME", "/scratch"]]
            if "minimal-env" in self.off:
                env += [[name, value] for name, value in self.canaries.present_values().items()]
            return _http(200, {"stdout": "ENV:" + json.dumps(env), "stderr": "", "return_value": [], "error": None})
        return _http(200, {"status": "ran"})


class FakePocketBase:
    def __init__(self, budget: Budget, log: RouteLog, off: set[str]) -> None:
        self.budget = budget
        self.log = log
        self.off = off
        self.rows: dict[str, dict[str, dict]] = {"take_home_attempts": {}, "users": {}}
        self._ids = 0

    def _count(self, method: str, route: str) -> Budget:
        self.log.add(method, route)
        return self.budget.spend()

    def _next(self) -> str:
        self._ids += 1
        return f"r{self._ids:014d}"

    def owner_of(self, token: str) -> str:
        return token.replace("token-", "user-")

    def create(self, collection: str, token: str, payload: dict) -> Http:
        with self._count("POST", f"/api/collections/{collection}/records"):
            row = {"id": self._next(), **payload}
            self.rows.setdefault(collection, {})[row["id"]] = row
            return _http(200, row)

    def view(self, collection: str, record_id: str, token: str | None = None) -> Http:
        with self._count("GET", f"/api/collections/{collection}/records/:id"):
            row = self.rows.get(collection, {}).get(record_id)
            admin = token == "admin-token"
            if row is not None and (admin or row.get("user") == self.owner_of(token or "")
                                    or "owner-read" in self.off):
                return _http(200, row)
            if row is not None and "uniform-missing" in self.off:
                return _http(403, {"code": 403, "message": "Only the owner can read this.", "data": {}})
            return _http(404, {"code": 404, "message": "The requested resource wasn't found.", "data": {}})

    def listing(self, collection: str, token: str | None = None, params: dict | None = None) -> Http:
        with self._count("GET", f"/api/collections/{collection}/records"):
            by_email = re.fullmatch(r'email = "([^"]+)"', (params or {}).get("filter", ""))
            if token == "admin-token" and by_email:
                items = [r for r in self.rows.get(collection, {}).values() if r.get("email") == by_email.group(1)]
                return _http(200, {"items": items, "totalItems": len(items)})
            owner = self.owner_of(token or "")
            items = [r for r in self.rows.get(collection, {}).values()
                     if r.get("user") == owner or "owner-read" in self.off]
            return _http(200, {"items": items, "totalItems": len(items)})

    def update(self, collection: str, record_id: str, payload: dict, token: str | None = None) -> Http:
        with self._count("PATCH", f"/api/collections/{collection}/records/:id"):
            row = self.rows.get(collection, {}).get(record_id)
            if row is None:
                return _http(404, {"code": 404, "message": "The requested resource wasn't found.", "data": {}})
            if collection == "users" and "demo_run_used" in payload and "demo-flags" not in self.off:
                return _http(400, {"code": 400, "message": "These account fields can't be changed.", "data": {}})
            row.update(payload)
            return _http(200, row)

    def delete(self, collection: str, record_id: str, token: str | None = None) -> Http:
        self.rows.get(collection, {}).pop(record_id, None)
        return _http(204, None)


@dataclass
class Target:
    """One fake stack and the accounts the fixtures make on it.

    ``sign_in`` sets how an account is made: ``ready`` makes it whole in
    one step; the others sign it up, as #9's factory does, and then
    ``auth-fails`` fails the sign-in after the signup landed, and
    ``answer-lost`` loses the signup's answer after it landed."""

    off: set[str] = field(default_factory=set)
    canaries: CanarySet = field(default_factory=lambda: CanarySet.generate("selftest"))
    made: list[Account] = field(default_factory=list)
    gated: dict[str, str] = field(default_factory=dict)
    sign_in: str = "ready"
    pb: FakePocketBase | None = None

    def context(self, budget: Budget) -> RunContext:
        log = RouteLog()
        pb = self.pb = FakePocketBase(budget, log, self.off)

        def make_account(tag: str) -> Account:
            n = len(self.made) + 1
            acct = Account("" if self.sign_in != "ready" else f"user-{n:010d}", "", tag,
                           f"harness-{tag}-{secrets.token_hex(6)}@harness.invalid")
            self.made.append(acct)
            if self.sign_in == "ready":
                acct.token = f"token-{n:010d}"
                pb.rows["users"][acct.user_id] = {"id": acct.user_id, "email": acct.email, "demo_run_used": False}
            return acct

        def register_account(acct: Account) -> None:
            n = len(self.made)
            user_id = f"user-{n:010d}"
            pb.rows["users"][user_id] = {"id": user_id, "email": acct.email, "demo_run_used": False}
            if self.sign_in == "answer-lost":
                raise TimeoutError("signup sent, no answer")
            acct.user_id = user_id
            raise RuntimeError("auth failed")

        return RunContext(
            runner=FakeRunner(budget, log, self.off, self.canaries, self.gated),
            pb=pb,
            admin_token="admin-token",
            canaries=self.canaries,
            budget=budget,
            log=log,
            content={"assignment": "a0000000000000a"},
            make_account=make_account,
            register_account=None if self.sign_in == "ready" else register_account,
            admin_pb=pb,
        )
