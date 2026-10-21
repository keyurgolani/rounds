"""Self-test: the take-home definition only the corpus stack has
(conformance/overlay.py), and that every definition the fixtures' bodies
name is active there, so no body stops at a retired definition."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from conformance import overlay
from corpus._requests import AI_CODING, CODING, TAKE_HOME, bodies

DEFINITIONS = overlay.repo_root() / "backend" / "definitions"
REAL = json.loads((DEFINITIONS / "manifest.json").read_bytes())
COMPOSE = Path(__file__).resolve().parents[1] / "compose.yml"


def test_the_corpus_manifest_is_the_real_one_plus_one_take_home_entry():
    manifest, document = overlay.overlay()
    assert {k: v for k, v in manifest.items() if k != "entries"} == {k: v for k, v in REAL.items() if k != "entries"}
    assert manifest["entries"][: len(REAL["entries"])] == REAL["entries"]
    (added,) = manifest["entries"][len(REAL["entries"]):]
    assert added == {
        "kind": "harness-revision",
        "track": "take-home",
        "slug": overlay.SLUG,
        "variant": overlay.VARIANT,
        "content_version": overlay.VERSION,
        "lifecycle": "active",
        "path": overlay.PATH,
        "checksum": "sha256:" + hashlib.sha256(document).hexdigest(),
    }


def test_the_corpus_definition_is_an_active_revision_keyed_as_a_take_home():
    _, document = overlay.overlay()
    doc = json.loads(document)
    source = json.loads((DEFINITIONS / overlay.SOURCE).read_bytes())
    assert [e["lifecycle"] for e in REAL["entries"] if e.get("path") == overlay.SOURCE] == ["active"]
    unchanged = set(source) - set(overlay.REKEYED)
    assert {k: doc[k] for k in unchanged} == {k: source[k] for k in unchanged}
    assert {k: doc[k] for k in overlay.REKEYED} == overlay.REKEYED
    # A take-home at enforce runs only a revision that reports on fd 3.
    assert doc["result_protocol"] == "fd3"
    # The take-home bodies send only paths the revision takes.
    for route in ("/api/take-home/run", "/api/take-home/submit"):
        assert set(bodies()[("POST", route)]["files"]) <= set(doc["candidate_paths"])


def test_every_definition_the_bodies_name_is_active_on_the_corpus_stack():
    manifest, _ = overlay.overlay()
    active = {(e["track"], e["slug"], e["variant"], e["content_version"])
              for e in manifest["entries"] if e["lifecycle"] == "active"}
    for ref in (CODING, AI_CODING, TAKE_HOME):
        assert (ref["track"], ref["slug"], ref["variant"], ref["version"]) in active, ref
    named = {json.dumps(b["definition"], sort_keys=True) for b in bodies().values() if "definition" in b}
    assert named == {json.dumps(r, sort_keys=True) for r in (CODING, AI_CODING, TAKE_HOME)}


def test_the_fixtures_bodies_need_no_checkout(monkeypatch):
    # The corpus driver's image carries only tests/conformance.
    import importlib

    import corpus._requests as requests_module

    def no_checkout():
        raise RuntimeError("no checkout here")

    monkeypatch.setattr(overlay, "repo_root", no_checkout)
    importlib.reload(requests_module)
    assert requests_module.bodies()[("POST", "/api/take-home/run")]["definition"] == TAKE_HOME


def test_the_branch_has_no_active_take_home_definition_of_its_own():
    # Why the corpus adds one. Once a real one is active, name it in
    # corpus/_requests.py and drop the overlay.
    assert not [e for e in REAL["entries"] if e["track"] == "take-home" and e["lifecycle"] == "active"]


def test_write_lays_out_the_files_compose_mounts(tmp_path):
    overlay.write(tmp_path)
    compose = COMPOSE.read_text()
    for rel in ("manifest.json", overlay.PATH):
        assert (tmp_path / rel).is_file(), rel
        assert f"}}/{rel}:/app/definitions/{rel}:ro" in compose, rel
    written = json.loads((tmp_path / "manifest.json").read_text())
    stored = (tmp_path / overlay.PATH).read_bytes()
    assert written["entries"][-1]["checksum"] == "sha256:" + hashlib.sha256(stored).hexdigest()


def test_it_refuses_to_shadow_a_real_definition(tmp_path):
    root = tmp_path
    (root / "backend" / "definitions").mkdir(parents=True)
    taken = {"kind": "harness-revision", "track": "take-home", "slug": overlay.SLUG, "variant": "python",
             "content_version": 1, "lifecycle": "active", "path": overlay.PATH, "checksum": "sha256:" + "0" * 64}
    (root / "backend" / "definitions" / "manifest.json").write_text(
        json.dumps({"schema": "definitions-manifest/v1", "entries": [taken]}))
    with pytest.raises(ValueError, match="already a real definition"):
        overlay.overlay(root)
