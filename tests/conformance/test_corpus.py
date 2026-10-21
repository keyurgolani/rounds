"""The live containment corpus run.

One parametrized case per ``contained`` fixture in the manifest, selected
by fixture id so ``pytest -k EX-07`` (or the compose repro
``... run --rm corpus -k EX-07``) runs one fixture and its context. Each
case imports the fixture module, runs it against the built stack, redacts
and checksums the retained artifacts, scans the output for canaries,
records a receipt, and asserts the strict expected outcome. A fixture
that detects a regression fails here with its id and the redacted
evidence.

This module runs only when ``CORPUS_RUN`` is set; otherwise every case is
skipped (the corpus needs a built stack). The framework self-tests under
``selftest/`` do not need it.
"""
from __future__ import annotations

import importlib

import pytest

from conformance import manifest as _m
from conformance.budget import Budget
from conformance.context import RunContext
from conformance.outcomes import decide
from conformance.receipts import FixtureReceipt, checksum
from conformance.redaction import clean, redact

# Per-fixture probe budget. The corpus counts requests and wall-seconds so
# the deployment subset stays under #1's default quota; in CI it only
# records the spend.
_MAX_REQUESTS = 25
_MAX_WALL_SECONDS = 120.0

_MANIFEST = _m.load_manifest()
_CONTAINED = _MANIFEST.contained()


@pytest.mark.parametrize("fixture_id", [f.id for f in _CONTAINED], ids=[f.id for f in _CONTAINED])
def test_fixture_contained(fixture_id, corpus_session):
    session = corpus_session
    fx = session.manifest.by_id(fixture_id)

    skip = session.skips.get((fx.id, session.target))
    if skip:
        pytest.skip(f"skip ledger: {skip.reason} (owner {skip.owner}, expires {skip.expiry.isoformat()})")

    module = importlib.import_module(f"corpus.{fx.module}")
    budget = Budget(_MAX_REQUESTS, _MAX_WALL_SECONDS)
    ctx = RunContext(
        runner=session.runner,
        pb=session.pb,
        admin_token=session.admin_token,
        canaries=session.canaries,
        budget=budget,
        content=session.content,
    )

    canary_values = list(session.canaries.present_values().values())
    try:
        result = module.run(ctx)
        # Keep the session's content fixtures for the next fixture.
        session.content.update(ctx.content)
        # Redact and checksum every retained artifact; a canary must never
        # survive into an artifact on this public repo.
        checksums: dict[str, str] = {}
        for name, text in result.evidence.items():
            safe = redact(text, canary_values)
            assert clean(safe, canary_values), f"{fx.id}: canary survived redaction of {name}"
            checksums[name] = checksum(safe)
        canary_hits = session.canaries.hits(result.canary_text) if result.canary_text else session.canaries.hits("")
        verdict = decide(result.outcome, fx.expectation(session.target))
    finally:
        failed_teardown = ctx.teardown()

    session.receipt.add(
        FixtureReceipt(
            id=fx.id,
            status="contained",
            closing_leaf=fx.closing_leaf,
            target=session.target,
            outcome=verdict.outcome,
            expectation=fx.expectation(session.target),
            verdict=verdict.verdict,
            legacy_classified=result.legacy_classified,
            routes=fx.routes,
            checksums=checksums,
            canary_hits=canary_hits,
            budget=budget.snapshot(),
            note=result.note,
        )
    )
    session.ran += 1

    assert not failed_teardown, f"{fx.id}: teardown left accounts behind: {failed_teardown}"
    assert verdict.passed, f"{fx.id} [{session.target}]: {verdict.outcome} ({verdict.reason or result.note})"
