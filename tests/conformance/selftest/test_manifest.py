"""Self-test: the manifest loader and validator (issue #8, Required tests
Unit). These run without a stack."""
from __future__ import annotations

import json
import os

import pytest

from conformance import manifest as m


def test_real_manifest_loads_and_covers_the_table():
    man = m.load_manifest()
    ids = {f.id for f in man.fixtures}
    assert ids == set(m.REQUIRED_IDS)
    assert len(man.fixtures) == len(m.REQUIRED_IDS) == 33


def test_contained_rows_have_an_existing_module_and_targets():
    man = m.load_manifest()
    for fx in man.contained():
        assert fx.module, fx.id
        assert os.path.exists(os.path.join(m.CORPUS_DIR, fx.module + ".py")), fx.id
        assert set(fx.expected) == set(m.TARGETS), fx.id


def test_pending_rows_carry_no_module_and_name_a_closing_leaf():
    man = m.load_manifest()
    pend = man.pending()
    assert pend, "stage 1 keeps most rows pending"
    for fx in pend:
        assert fx.module is None, fx.id
        assert fx.closing_leaf.startswith("ROUNDS-"), fx.id
        assert not fx.expected, fx.id


def _write(tmp_path, rows, corpus_dir=None):
    data = {
        "schema": m.MANIFEST_SCHEMA,
        "corpus_version": "1",
        "targets": list(m.TARGETS),
        "defaults": {},
        "fixtures": rows,
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    return str(path), str(corpus_dir or tmp_path)


def _row(fid, status="pending", **over):
    base = {
        "id": fid,
        "attack": "a",
        "spec_ref": "s",
        "status": status,
        "closing_leaf": "ROUNDS-00A-L05",
        "routes": ["POST /api/run"],
        "languages": ["python"],
        "control": "c",
        "destructive": False,
        "environment_sensitive": False,
        "setup": "u",
        "teardown": "t",
    }
    base.update(over)
    return base


def test_contained_without_module_is_rejected(tmp_path):
    path, cdir = _write(tmp_path, [_row("EX-01", status="contained",
                                        expected={"ci": "contained", "compose": "contained", "k8s": "contained"})])
    with pytest.raises(m.ManifestError):
        m.load_manifest(path, corpus_dir=cdir, required_ids=("EX-01",))


def test_pending_with_module_is_rejected(tmp_path):
    (tmp_path / "ex_x.py").write_text("def run(ctx):\n    pass\n")
    path, cdir = _write(tmp_path, [_row("EX-01", status="pending", module="ex_x")])
    with pytest.raises(m.ManifestError):
        m.load_manifest(path, corpus_dir=cdir, required_ids=("EX-01",))


def test_missing_required_row_is_rejected(tmp_path):
    path, cdir = _write(tmp_path, [_row("EX-01")])
    with pytest.raises(m.ManifestError):
        m.load_manifest(path, corpus_dir=cdir, required_ids=("EX-01", "EX-02"))


def test_duplicate_id_is_rejected(tmp_path):
    path, cdir = _write(tmp_path, [_row("EX-01"), _row("EX-01")])
    with pytest.raises(m.ManifestError):
        m.load_manifest(path, corpus_dir=cdir, required_ids=("EX-01",))


def test_not_applicable_needs_a_reason(tmp_path):
    path, cdir = _write(tmp_path, [_row("EX-01", status="not-applicable")])
    with pytest.raises(m.ManifestError):
        m.load_manifest(path, corpus_dir=cdir, required_ids=("EX-01",))


def test_contained_module_file_must_exist(tmp_path):
    path, cdir = _write(tmp_path, [_row("EX-01", status="contained", module="nope",
                                        expected={"ci": "contained", "compose": "contained", "k8s": "contained"})])
    with pytest.raises(m.ManifestError):
        m.load_manifest(path, corpus_dir=cdir, required_ids=("EX-01",))


ALL_TARGETS = {"ci": "contained", "compose": "contained", "k8s": "contained"}


def _contained_row(tmp_path, subcases):
    (tmp_path / "ex_x.py").write_text("def run(ctx):\n    pass\n")
    over = {"module": "ex_x", "expected": ALL_TARGETS}
    if subcases is not None:
        over["subcases"] = subcases
    return _write(tmp_path, [_row("EX-01", status="contained", **over)])


def test_every_real_contained_fixture_lists_a_contained_subcase():
    man = m.load_manifest()
    for fx in man.contained():
        assert fx.contained_subcases(), fx.id
        for sub in fx.subcases:
            assert sub.id.startswith(fx.id + "."), sub.id
            assert sub.closing_leaf.startswith("ROUNDS-"), sub.id


def test_a_contained_fixture_without_subcases_is_rejected(tmp_path):
    path, cdir = _contained_row(tmp_path, None)
    with pytest.raises(m.ManifestError, match="sub-cases"):
        m.load_manifest(path, corpus_dir=cdir, required_ids=("EX-01",))


def test_a_contained_fixture_with_only_pending_subcases_is_rejected(tmp_path):
    path, cdir = _contained_row(tmp_path, [{"id": "EX-01.a", "status": "pending", "closing_leaf": "ROUNDS-00A-L05"}])
    with pytest.raises(m.ManifestError):
        m.load_manifest(path, corpus_dir=cdir, required_ids=("EX-01",))


def test_duplicate_or_misnamed_subcases_are_rejected(tmp_path):
    dup = {"id": "EX-01.a", "status": "contained", "closing_leaf": "ROUNDS-00A-L01"}
    path, cdir = _contained_row(tmp_path, [dup, dict(dup)])
    with pytest.raises(m.ManifestError, match="duplicate"):
        m.load_manifest(path, corpus_dir=cdir, required_ids=("EX-01",))
    path, cdir = _contained_row(tmp_path, [{"id": "EX-02.a", "status": "contained", "closing_leaf": "ROUNDS-00A-L01"}])
    with pytest.raises(m.ManifestError):
        m.load_manifest(path, corpus_dir=cdir, required_ids=("EX-01",))


def test_a_pending_row_cannot_claim_a_contained_subcase(tmp_path):
    sub = [{"id": "EX-01.a", "status": "contained", "closing_leaf": "ROUNDS-00A-L01"}]
    path, cdir = _write(tmp_path, [_row("EX-01", subcases=sub)])
    with pytest.raises(m.ManifestError):
        m.load_manifest(path, corpus_dir=cdir, required_ids=("EX-01",))
