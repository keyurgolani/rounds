"""Pytest plugin for the containment corpus (ROUNDS-00A-L08).

Responsibilities:
- put the framework (``conformance``) and the fixtures (``corpus``) on the
  import path, plus #9's account factory (``harness/probes``) when it is
  beside us, so a fixture reuses the synthetic-account factory;
- load and validate the manifest and the skip ledger at session start, so
  a malformed manifest, an expired skip, or a skip for an unknown fixture
  fails the lane before any stack call;
- read the run's canaries, failing the run when one that has landed
  wasn't planted;
- build the session (stack clients, canaries, the admin token), record
  every row that doesn't run (pending, and not-applicable without a
  module) in the receipt up front, and write the receipt at the end;
- fail the lane when nothing was collected or everything was skipped.

The per-fixture run, its strict expected outcome, redaction, canary
checks, and the receipt entry are in ``test_corpus.py``, which runs only
when ``CORPUS_RUN`` is set (the corpus container sets it). The framework
self-tests under ``selftest/`` share only the import-path setup.
"""
from __future__ import annotations

import datetime as _dt
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
# #9's account factory and PocketBase client, when the harness is beside us
# (a checkout) and not already on PYTHONPATH (the container).
_HARNESS = os.path.normpath(os.path.join(_HERE, "..", "..", "harness"))
for _extra in (os.path.join(_HARNESS, "probes"), _HARNESS):
    if os.path.isdir(_extra) and _extra not in sys.path:
        sys.path.append(_extra)


def corpus_enabled() -> bool:
    return os.environ.get("CORPUS_RUN", "").lower() in ("1", "true", "yes")


def load_corpus():
    from conformance import manifest as m

    manifest = m.load_manifest()
    skips = m.load_skip_ledger(manifest=manifest, today=_dt.date.today())
    return manifest, {(s.id, s.target): s for s in skips}


class Session:
    def __init__(self, manifest, skips, pb, runner_url, admin_token, canaries, receipt, target):
        self.manifest = manifest
        self.skips = skips
        self.pb = pb
        self.runner_url = runner_url
        self.admin_token = admin_token
        self.canaries = canaries
        self.receipt = receipt
        self.target = target
        self.content: dict[str, str] = {}
        from conformance.budget import RunTotals

        self.totals = RunTotals()

    def record_rows_that_dont_run(self) -> None:
        from conformance.receipts import FixtureReceipt

        for fx in self.manifest.fixtures:
            if fx.status == "pending":
                self.receipt.add(FixtureReceipt(id=fx.id, status="pending", closing_leaf=fx.closing_leaf,
                                                note=f"pending: closes with {fx.closing_leaf}"))
            elif fx.status == "not-applicable" and not fx.module:
                self.receipt.add(FixtureReceipt(id=fx.id, status="ran", closing_leaf=fx.closing_leaf,
                                                target=self.target, outcome="not-applicable",
                                                expectation="not-applicable", verdict="pass",
                                                note=f"not-applicable: {fx.reason}"))


def _image_refs() -> dict[str, str]:
    """Image references the launcher passed in (ids on PRs, digests on a
    pushed build). Unset until stage 2's images job, so they read absent."""
    refs: dict[str, str] = {}
    for service in ("runner", "pocketbase", "frontend", "pdf-renderer"):
        refs[service] = os.environ.get(f"IMAGE_{service.replace('-', '_').upper()}", "absent")
    return refs


@pytest.fixture(scope="session")
def corpus_session():
    if not corpus_enabled():
        pytest.skip("CORPUS_RUN not set; the live corpus runs only against a built stack")

    from conformance import CORPUS_VERSION
    from conformance.canaries import CanarySet
    from conformance.context import wait_for_runner
    from conformance.receipts import RunReceipt, default_versions
    import pbclient  # harness/probes

    manifest, skips = load_corpus()
    # Fails the run when a canary that has landed wasn't planted.
    canaries = CanarySet.from_env()
    runner_url = os.environ.get("RUNNER_URL", "http://runner:8000")
    pb = pbclient.PBClient(os.environ.get("POCKETBASE_URL", "http://pocketbase:8090"))
    pb.wait_healthy()
    wait_for_runner(runner_url)
    admin = pb.admin_auth(os.environ["PB_ADMIN_EMAIL"], os.environ["PB_ADMIN_PASSWORD"])
    admin_token = (admin.body or {}).get("token", "")
    if not admin_token:
        raise RuntimeError(f"couldn't sign in as the run's admin (status {admin.status})")

    target = os.environ.get("CORPUS_TARGET", "ci")
    receipt = RunReceipt(
        commit=os.environ.get("GIT_COMMIT", "unknown"),
        corpus_version=CORPUS_VERSION,
        target=target,
        canary_set_id=canaries.set_id,
        images=_image_refs(),
        versions=default_versions(),
        run_id=os.environ.get("RUN_ID", "local"),
    )
    session = Session(manifest, skips, pb, runner_url, admin_token, canaries, receipt, target)
    session.record_rows_that_dont_run()
    try:
        yield session
    finally:
        receipt.budget_total = session.totals.snapshot()
        out = os.environ.get("RECEIPTS_PATH", os.path.join(_HERE, ".receipts", "containment-receipt.json"))
        receipt.write(out)


def pytest_sessionfinish(session, exitstatus):
    # Zero collected or everything skipped fails the corpus lane (#8
    # acceptance criteria). Only applies to the live corpus run. Only the
    # fixture cases count: the receipt-coverage case passes on its own,
    # even when every fixture was quarantined.
    if not corpus_enabled():
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    from conformance.execute import fixtures_decided

    decided = fixtures_decided(reporter.stats.get("passed", []) + reporter.stats.get("failed", []))
    if decided == 0:
        reporter.write_line("containment-corpus: no fixture ran; failing the lane", red=True)
        session.exitstatus = 1
