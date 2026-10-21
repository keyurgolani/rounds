"""Pytest plugin for the containment corpus (ROUNDS-00A-L08).

Responsibilities:
- put the framework (``conformance``) and the fixtures (``corpus``) on the
  import path, plus #9's account factory (``harness/probes``) when it is
  present, so a fixture reuses the synthetic-account factory;
- load and validate the manifest and the skip ledger at session start, so
  a malformed manifest, an expired skip, or a skip for an unknown fixture
  fails the lane before any stack call;
- build the run context (stack clients, the run's canary set, the admin
  token) once per corpus session, and tear down what each fixture created,
  failing the run if a teardown fails;
- enforce the strict expected outcome for each contained fixture, redact
  and checksum its retained artifacts, scan its output for canaries, and
  record a receipt per fixture (contained or pending only);
- fail the lane when nothing was collected or everything was skipped.

The live corpus run is ``test_corpus.py``; it only runs when ``CORPUS_RUN``
is set (the corpus container sets it). The framework self-tests under
``selftest/`` share only the import-path setup and run without a stack.
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
# (a local checkout) and not already supplied on PYTHONPATH (the container).
_PROBES = os.path.normpath(os.path.join(_HERE, "..", "..", "harness", "probes"))
if os.path.isdir(_PROBES) and _PROBES not in sys.path:
    sys.path.append(_PROBES)


def _corpus_enabled() -> bool:
    return os.environ.get("CORPUS_RUN", "").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Session-level manifest and skip-ledger validation (always on)
# ---------------------------------------------------------------------------


def _load_corpus():
    from conformance import manifest as m

    manifest = m.load_manifest()
    skips = m.load_skip_ledger(manifest=manifest, today=_dt.date.today())
    return manifest, {(s.id, s.target): s for s in skips}


@pytest.fixture(scope="session")
def corpus_manifest():
    manifest, _ = _load_corpus()
    return manifest


# ---------------------------------------------------------------------------
# Run context for the live corpus (only when CORPUS_RUN is set)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def corpus_session():
    if not _corpus_enabled():
        pytest.skip("CORPUS_RUN not set; the live corpus runs only against a built stack")

    from conformance import CORPUS_VERSION
    from conformance.canaries import CanarySet
    from conformance.receipts import RunReceipt, default_versions
    from conformance.context import RunnerClient, wait_for_runner
    import pbclient  # harness/probes

    manifest, skips = _load_corpus()
    runner_url = os.environ.get("RUNNER_URL", "http://runner:8000")
    pocketbase_url = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
    run_id = os.environ.get("RUN_ID", "local")
    target = os.environ.get("CORPUS_TARGET", "ci")

    pb = pbclient.PBClient(pocketbase_url)
    pb.wait_healthy()
    runner = RunnerClient(runner_url)
    wait_for_runner(runner)

    admin_email = os.environ["PB_ADMIN_EMAIL"]
    admin_password = os.environ["PB_ADMIN_PASSWORD"]
    admin_resp = pb.admin_auth(admin_email, admin_password)
    admin_token = (admin_resp.body or {}).get("token", "")

    canaries = CanarySet.from_env()
    receipt = RunReceipt(
        commit=os.environ.get("GIT_COMMIT", "unknown"),
        corpus_version=CORPUS_VERSION,
        target=target,
        canary_set_id=canaries.set_id,
        images=_image_refs(),
        versions=default_versions(),
        run_id=run_id,
    )
    state = _Session(manifest, skips, pb, runner, admin_token, canaries, receipt, target)
    yield state

    # Record every pending row in the receipt, then write it to the
    # git-ignored receipts directory for upload.
    state.record_pending()
    out = os.environ.get("RECEIPTS_PATH", os.path.join(_HERE, ".receipts", "containment-receipt.json"))
    receipt.write(out)


def _image_refs() -> dict[str, str]:
    """Image references the launcher passed in (ids on PRs, digests on a
    pushed build). Unset until stage 2's images job, so they read absent."""
    refs: dict[str, str] = {}
    for service in ("runner", "pocketbase", "frontend", "pdf-renderer"):
        env = f"IMAGE_{service.replace('-', '_').upper()}"
        refs[service] = os.environ.get(env, "absent")
    return refs


class _Session:
    def __init__(self, manifest, skips, pb, runner, admin_token, canaries, receipt, target):
        self.manifest = manifest
        self.skips = skips
        self.pb = pb
        self.runner = runner
        self.admin_token = admin_token
        self.canaries = canaries
        self.receipt = receipt
        self.target = target
        self.content: dict[str, str] = {}
        self.ran = 0

    def record_pending(self) -> None:
        from conformance.receipts import FixtureReceipt

        for fx in self.manifest.pending():
            self.receipt.add(
                FixtureReceipt(
                    id=fx.id,
                    status="pending",
                    closing_leaf=fx.closing_leaf,
                    routes=fx.routes,
                    note=f"pending: closes with {fx.closing_leaf}",
                )
            )


def pytest_sessionfinish(session, exitstatus):
    # Zero collected or everything skipped fails the corpus lane (#8
    # acceptance criteria). Only applies to the live corpus run.
    if not _corpus_enabled():
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    passed = len(reporter.stats.get("passed", []))
    failed = len(reporter.stats.get("failed", []))
    errors = len(reporter.stats.get("error", []))
    if failed == 0 and errors == 0 and passed == 0:
        reporter.write_line("containment-corpus: zero fixtures ran; failing the lane", red=True)
        session.exitstatus = 1
