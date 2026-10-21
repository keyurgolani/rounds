"""Run context the fixtures receive.

The context gives a fixture the stack clients (the runner and
PocketBase), the run's canary set, a per-fixture probe budget, and #9's
synthetic-account factory. It also tracks what a fixture creates so the
plugin can tear it down and fail the run if a teardown fails (#8 body,
Domain ownership and invariants).

The harness account factory and PocketBase client (``harness/probes``)
are imported lazily, because the self-tests exercise the framework
without the harness on the path; only a real corpus run in the container
reaches this module.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .budget import Budget
from .canaries import CanarySet


@dataclass
class Http:
    status: int
    body: Any
    text: str
    headers: dict[str, str]


class RunnerClient:
    """A tiny HTTP client for the runner, kept separate from the
    PocketBase client so a fixture controls the exact bytes it sends (an
    oversized body, a missing bearer) and reads the raw response text for
    redaction."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: Any = None,
        raw_body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Http:
        data = raw_body
        hdrs = {"Accept": "application/json"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
        if token:
            hdrs["Authorization"] = "Bearer " + token
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(self.base_url + path, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                text = resp.read().decode("utf-8", "replace")
                return Http(resp.status, _maybe_json(text), text, dict(resp.headers))
        except urllib.error.HTTPError as err:
            text = err.read().decode("utf-8", "replace")
            return Http(err.code, _maybe_json(text), text, dict(err.headers or {}))


def _maybe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return None


@dataclass
class RunContext:
    runner: RunnerClient
    pb: Any  # harness PBClient
    admin_token: str
    canaries: CanarySet
    budget: Budget
    content: dict[str, str] = field(default_factory=dict)
    _accounts: list[Any] = field(default_factory=list)

    # -- account factory (lazy harness import) ------------------------------

    def new_account(self, tag: str):
        import factory  # harness/probes

        acct = factory.make_account(tag)
        factory.register(self.pb, acct)
        self._accounts.append(acct)
        return acct

    def seed_account(self, acct) -> None:
        import factory

        factory.seed_account(self.pb, acct, self.content, self.admin_token)

    def ensure_content(self) -> None:
        import factory

        if not self.content:
            self.content = factory.ensure_content_fixtures(self.pb, self.admin_token)

    # -- teardown -----------------------------------------------------------

    def teardown(self) -> list[str]:
        """Remove accounts this fixture made. Returns the ids of any that
        could not be removed; a non-empty list fails the run."""
        failed: list[str] = []
        for acct in self._accounts:
            try:
                resp = self.pb.delete("users", acct.user_id, token=self.admin_token)
                if resp.status not in (200, 204, 404):
                    failed.append(acct.user_id)
            except Exception:
                failed.append(acct.user_id)
        self._accounts.clear()
        return failed


def wait_for_runner(client: RunnerClient, attempts: int = 60, delay: float = 1.0) -> None:
    for _ in range(attempts):
        try:
            resp = client.request("GET", "/health")
            if resp.status == 200:
                return
        except Exception:
            pass
        time.sleep(delay)
    raise RuntimeError("runner did not become healthy")
