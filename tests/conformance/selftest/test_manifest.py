"""Self-test: the manifest loader and validator, and each fixture's spec
(issue #8, Required tests Unit). These run without a stack."""
from __future__ import annotations

import json
import os

import pytest

from conformance import manifest as m

ALL_TARGETS = {"ci": "contained", "compose": "contained", "k8s": "contained"}
NOT_APPLICABLE = {"ci": "not-applicable", "compose": "not-applicable", "k8s": "not-applicable"}


def test_real_manifest_loads_and_covers_the_table():
    man = m.load_manifest()
    ids = {f.id for f in man.fixtures}
    assert ids == set(m.REQUIRED_IDS)
    assert len(man.fixtures) == len(m.REQUIRED_IDS) == 33


def test_every_public_manifest_row_is_its_id_and_family_only():
    with open(m.DEFAULT_MANIFEST) as fh:
        raw = json.load(fh)
    assert raw["schema"] == m.MANIFEST_SCHEMA
    for row in raw["fixtures"]:
        assert set(row) == {"id", "family"}, row.get("id")
        assert row["family"] == m.FAMILIES[row["id"][:2]], row["id"]
    # The defaults are framework settings, not a row's detail.
    assert set(raw["defaults"]) <= m.DEFAULT_KEYS


def test_runnable_fixtures_have_a_module_and_cover_every_target():
    man = m.load_manifest()
    assert man.runnable()
    for fx in man.runnable():
        assert os.path.exists(os.path.join(m.CORPUS_DIR, fx.module + ".py")), fx.id
        assert set(fx.expected) == set(m.TARGETS), fx.id
        assert fx.routes and fx.control and fx.setup and fx.teardown, fx.id


def test_a_fixture_without_a_module_carries_nothing_but_its_id_and_family():
    man = m.load_manifest()
    assert man.not_run()
    for fx in man.not_run():
        assert fx == m.Fixture(id=fx.id, family=m.FAMILIES[fx.id[:2]]), fx.id


def test_every_real_spec_lists_its_own_subcases():
    man = m.load_manifest()
    for fx in man.runnable():
        assert fx.subcases, fx.id
        assert all(s.startswith(fx.id + ".") for s in fx.subcases), fx.id


# ---- the manifest's own shape ------------------------------------------------------------


def _write(tmp_path, rows, *, defaults=None, extra=None, schema=m.MANIFEST_SCHEMA):
    data = {
        "schema": schema,
        "corpus_version": "1",
        "targets": list(m.TARGETS),
        "defaults": defaults or {},
        "fixtures": rows,
        **(extra or {}),
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    return str(path)


def _rows(*ids):
    return [{"id": fid, "family": m.FAMILIES[fid[:2]]} for fid in ids]


def _load(tmp_path, path, ids=("EX-01",)):
    return m.load_manifest(path, corpus_dir=str(tmp_path), required_ids=ids)


def test_a_minimal_manifest_loads_with_every_row_not_run(tmp_path):
    man = _load(tmp_path, _write(tmp_path, _rows("EX-01", "FG-01", "RD-01")), ("EX-01", "FG-01", "RD-01"))
    assert [f.family for f in man.fixtures] == ["execution", "grading", "render"]
    assert man.runnable() == []


@pytest.mark.parametrize("key", ["attack", "guarantee", "routes", "spec_ref", "control", "setup", "teardown",
                                 "closing_leaf", "status", "subcases", "expected", "module"])
def test_a_row_carrying_anything_but_its_id_and_family_is_rejected(tmp_path, key):
    rows = _rows("EX-01")
    rows[0][key] = "x"
    with pytest.raises(m.ManifestError, match="only its id and family"):
        _load(tmp_path, _write(tmp_path, rows))


@pytest.mark.parametrize("family", [None, "grading", "render", "EX"])
def test_a_row_with_the_wrong_family_is_rejected(tmp_path, family):
    rows = [{"id": "EX-01"} if family is None else {"id": "EX-01", "family": family}]
    with pytest.raises(m.ManifestError, match="family"):
        _load(tmp_path, _write(tmp_path, rows))


def test_missing_required_row_is_rejected(tmp_path):
    with pytest.raises(m.ManifestError, match="missing"):
        _load(tmp_path, _write(tmp_path, _rows("EX-01")), ("EX-01", "EX-02"))


def test_duplicate_id_is_rejected(tmp_path):
    with pytest.raises(m.ManifestError, match="duplicate"):
        _load(tmp_path, _write(tmp_path, _rows("EX-01", "EX-01")))


@pytest.mark.parametrize("key", ["languages", "control", "destructive", "environment_sensitive"])
def test_a_row_level_default_is_rejected(tmp_path, key):
    with pytest.raises(m.ManifestError, match="framework settings"):
        _load(tmp_path, _write(tmp_path, _rows("EX-01"), defaults={key: False}))


def test_an_unknown_top_level_key_is_rejected(tmp_path):
    with pytest.raises(m.ManifestError, match="unknown keys"):
        _load(tmp_path, _write(tmp_path, _rows("EX-01"), extra={"pending": []}))


def test_the_old_schema_is_rejected(tmp_path):
    with pytest.raises(m.ManifestError, match="schema"):
        _load(tmp_path, _write(tmp_path, _rows("EX-01"), schema="containment-corpus-manifest/v1"))


# ---- each module's SPEC --------------------------------------------------------------------


def _spec(**over):
    spec = {
        "routes": ["POST /api/run"],
        "subcases": ["EX-01.a"],
        "expected": dict(ALL_TARGETS),
        "languages": ["python"],
        "control": "c",
        "setup": "u",
        "teardown": "t",
        "destructive": False,
        "environment_sensitive": False,
    }
    spec.update(over)
    return spec


def _module(tmp_path, spec, name="ex_01_x", source=None):
    text = source if source is not None else f"SPEC = {spec!r}\n\n\ndef run(ctx):\n    pass\n"
    (tmp_path / f"{name}.py").write_text(text)


def _with_module(tmp_path, spec, **kwargs):
    _module(tmp_path, spec, **kwargs)
    return _load(tmp_path, _write(tmp_path, _rows("EX-01")))


def test_a_module_carries_the_fixtures_spec(tmp_path):
    fx = _with_module(tmp_path, _spec()).by_id("EX-01")
    assert fx.runnable and fx.module == "ex_01_x"
    assert (fx.routes, fx.subcases, fx.expected, fx.languages) == (["POST /api/run"], ["EX-01.a"], ALL_TARGETS,
                                                                    ["python"])
    assert (fx.control, fx.setup, fx.teardown, fx.destructive, fx.environment_sensitive) == ("c", "u", "t", False,
                                                                                             False)
    assert fx.expectation("ci") == "contained"


def test_the_spec_is_read_without_importing_the_module(tmp_path):
    source = f"raise SystemExit('imported')\nSPEC = {_spec()!r}\n"
    fx = _with_module(tmp_path, None, source=source).by_id("EX-01")
    assert fx.subcases == ["EX-01.a"]


@pytest.mark.parametrize("source", [
    "def run(ctx):\n    pass\n",
    "SPEC = {}\nSPEC = {}\n",
    "SUBCASES = ['EX-01.a']\nSPEC = {'subcases': SUBCASES}\n",
    "SPEC: dict\n",
])
def test_a_module_without_one_literal_spec_is_rejected(tmp_path, source):
    with pytest.raises(m.ManifestError, match="SPEC"):
        _with_module(tmp_path, None, source=source)


@pytest.mark.parametrize("key", sorted(m.SPEC_KEYS))
def test_a_spec_missing_a_key_is_rejected(tmp_path, key):
    spec = _spec()
    del spec[key]
    with pytest.raises(m.ManifestError, match="missing"):
        _with_module(tmp_path, spec)


@pytest.mark.parametrize("key", ["closing_leaf", "status", "attack", "guarantee", "pending"])
def test_a_spec_with_an_unknown_key_is_rejected(tmp_path, key):
    with pytest.raises(m.ManifestError, match="unknown keys"):
        _with_module(tmp_path, _spec(**{key: "x"}))


@pytest.mark.parametrize("over", [
    {"routes": []},
    {"routes": "POST /api/run"},
    {"routes": [""]},
    {"subcases": "EX-01.a"},
    {"subcases": ["EX-02.a"]},
    {"subcases": ["EX-01"]},
    {"subcases": ["EX-01.Not_Kebab"]},
    {"subcases": ["EX-01.a", "EX-01.a"]},
    {"expected": {"ci": "contained", "compose": "contained"}},
    {"expected": {**ALL_TARGETS, "k8s": "detected"}},
    {"expected": {**ALL_TARGETS, "dev": "contained"}},
    {"languages": ["cobol"]},
    {"control": ""},
    {"setup": None},
    {"teardown": ""},
    {"destructive": "no"},
    {"environment_sensitive": 0},
])
def test_a_malformed_spec_is_rejected(tmp_path, over):
    with pytest.raises(m.ManifestError):
        _with_module(tmp_path, _spec(**over))


def test_a_spec_with_no_subcases_expects_not_applicable_and_gives_a_reason(tmp_path):
    spec = _spec(subcases=[], expected=dict(NOT_APPLICABLE), reason="no surface yet")
    fx = _with_module(tmp_path, spec).by_id("EX-01")
    assert fx.subcases == [] and fx.reason == "no surface yet"
    assert fx.expectation("ci") == "not-applicable"


@pytest.mark.parametrize("over", [
    {"subcases": []},
    {"subcases": [], "expected": dict(NOT_APPLICABLE)},
    {"subcases": [], "reason": "no surface yet"},
    {"subcases": [], "expected": dict(NOT_APPLICABLE), "reason": ""},
    {"reason": "a reason only a spec with no sub-cases gives"},
])
def test_a_reason_goes_with_no_subcases_and_not_applicable_everywhere(tmp_path, over):
    with pytest.raises(m.ManifestError):
        _with_module(tmp_path, _spec(**over))


# ---- modules and rows match one to one ------------------------------------------------------


def test_a_module_whose_fixture_has_no_row_is_rejected(tmp_path):
    _module(tmp_path, _spec(subcases=["EX-02.a"]), name="ex_02_x")
    with pytest.raises(m.ManifestError, match="without a manifest row"):
        _load(tmp_path, _write(tmp_path, _rows("EX-01")))


def test_a_module_not_named_for_a_fixture_is_rejected(tmp_path):
    _module(tmp_path, _spec(), name="anonymous")
    with pytest.raises(m.ManifestError, match="names no fixture"):
        _load(tmp_path, _write(tmp_path, _rows("EX-01")))


def test_two_modules_for_one_fixture_are_rejected(tmp_path):
    _module(tmp_path, _spec(), name="ex_01_x")
    _module(tmp_path, _spec(), name="ex_01_y")
    with pytest.raises(m.ManifestError, match="two modules"):
        _load(tmp_path, _write(tmp_path, _rows("EX-01")))


def test_helper_modules_are_not_fixtures(tmp_path):
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "_base.py").write_text("SPEC = 'not a fixture'\n")
    man = _load(tmp_path, _write(tmp_path, _rows("EX-01")))
    assert man.runnable() == []
