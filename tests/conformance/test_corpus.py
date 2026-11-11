"""The live containment corpus run.

One parametrized case per fixture with a module, selected by fixture id
so ``pytest -k EX-07`` (or ``tests/conformance/run.sh -k EX-07``) runs
one fixture and its context. Each case runs the fixture through
``conformance.execute.run_fixture`` against the built stack, records its
receipt entry, and asserts the strict expected outcome; a fixture that
detects a regression fails here with its id, the reason, its note, and
its redacted evidence. A quarantined fixture records the skip ledger's
owner and expiry and is skipped. The last case checks that the receipt
has one entry for every manifest row.

This module runs only when ``CORPUS_RUN`` is set; otherwise every case is
skipped (the corpus needs a built stack).
"""
from __future__ import annotations

import importlib

import pytest

from conformance import manifest as _m
from conformance.context import CountingClient, RouteLog, RunContext, RunnerClient
from conformance.execute import quarantined, run_fixture

_MANIFEST = _m.load_manifest()
_RUNNABLE = _MANIFEST.runnable()


@pytest.mark.parametrize("fixture_id", [f.id for f in _RUNNABLE], ids=[f.id for f in _RUNNABLE])
def test_fixture(fixture_id, corpus_session):
    session = corpus_session
    fx = session.manifest.by_id(fixture_id)

    skip = session.skips.get((fx.id, session.target))
    if skip:
        session.receipt.add(quarantined(fx, skip, session.target))
        pytest.skip(f"quarantined: {skip.reason} (owner {skip.owner}, expires {skip.expiry.isoformat()})")

    module = importlib.import_module(f"corpus.{fx.module}")

    def make_context(budget):
        log = RouteLog()
        return RunContext(
            runner=RunnerClient(session.runner_url, budget, log),
            pb=CountingClient(session.pb, budget, log),
            admin_token=session.admin_token,
            canaries=session.canaries,
            budget=budget,
            log=log,
            content=session.content,
            admin_pb=session.pb,
        )

    ran = run_fixture(fx, module, make_context, session.canaries, session.target)
    session.totals.add_spend(ran.receipt.budget)
    session.receipt.add(ran.receipt)
    assert ran.passed, ran.message


def test_every_manifest_row_has_a_receipt_entry(corpus_session):
    gaps = corpus_session.receipt.missing(f.id for f in corpus_session.manifest.fixtures)
    assert gaps == {"missing": [], "unknown": []}, gaps
