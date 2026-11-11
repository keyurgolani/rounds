"""Self-test: the fixture builder and discovery (issue #8, Required tests
Unit: self-test the fixture builder).

Every contained manifest row maps to a module that imports and exposes a
callable ``run``; every fixture module under ``corpus/`` is referenced by
exactly one contained row, so no orphan fixture ships and no contained
row points at a missing module.
"""
from __future__ import annotations

import importlib
import os

from conformance import manifest as m


def test_every_contained_row_has_a_runnable_module():
    man = m.load_manifest()
    for fx in man.contained():
        mod = importlib.import_module(f"corpus.{fx.module}")
        assert callable(getattr(mod, "run", None)), f"{fx.id}: corpus.{fx.module}.run is not callable"


def test_no_orphan_fixture_module():
    man = m.load_manifest()
    referenced = {fx.module for fx in man.contained()}
    on_disk = {
        name[:-3]
        for name in os.listdir(m.CORPUS_DIR)
        if name.endswith(".py") and not name.startswith("_")
    }
    assert on_disk == referenced, f"orphan or missing fixture modules: {on_disk ^ referenced}"


def test_stage_1_contains_the_enforced_guarantees_only():
    man = m.load_manifest()
    contained = {fx.id for fx in man.contained()}
    # The guarantees already enforced on the branch; every other row is pending.
    assert contained == {"EX-01", "EX-02", "EX-03", "EX-04", "EX-05", "EX-06", "EX-07", "RD-07"}
