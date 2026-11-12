"""Self-test: the fixture builder and discovery (issue #8, Required tests
Unit: self-test the fixture builder).

Every fixture with a module imports, exposes a callable ``run``, and
carries at run time the same ``SPEC`` the validator read; every fixture
module under ``corpus/`` belongs to exactly one manifest row, so no
orphan fixture ships.
"""
from __future__ import annotations

import importlib
import os

from conformance import manifest as m


def test_every_fixture_module_imports_and_has_a_runnable_run():
    man = m.load_manifest()
    for fx in man.runnable():
        mod = importlib.import_module(f"corpus.{fx.module}")
        assert callable(getattr(mod, "run", None)), f"{fx.id}: corpus.{fx.module}.run is not callable"


def test_the_spec_a_module_runs_with_is_the_one_the_validator_read():
    man = m.load_manifest()
    for fx in man.runnable():
        spec = importlib.import_module(f"corpus.{fx.module}").SPEC
        assert spec["routes"] == fx.routes and spec["subcases"] == fx.subcases, fx.id
        assert spec["expected"] == fx.expected and spec["languages"] == fx.languages, fx.id


def test_no_orphan_fixture_module():
    man = m.load_manifest()
    referenced = {fx.module for fx in man.runnable()}
    on_disk = {
        name[:-3]
        for name in os.listdir(m.CORPUS_DIR)
        if name.endswith(".py") and not name.startswith("_")
    }
    assert on_disk == referenced, f"orphan or missing fixture modules: {on_disk ^ referenced}"


def test_stage_1_runs_the_enforced_guarantees_only():
    man = m.load_manifest()
    runnable = {fx.id for fx in man.runnable()}
    # The guarantees already enforced on the branch. RD-01 joined with
    # server PDF on snapshot ids (ROUNDS-00A-L04).
    assert runnable == {"EX-01", "EX-02", "EX-03", "EX-04", "EX-05", "EX-06", "EX-07", "RD-01", "RD-07"}
