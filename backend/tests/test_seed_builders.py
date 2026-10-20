"""The seed builders after the definitions rework (ROUNDS-00A-L02).

The builders no longer delete and recreate presentation rows. They leave
the committed v1 seed migrations (1700001200, 1700001400) in place and,
only when a compiled definition is past version 1, emit a new
presentation-only upsert migration. Take-home emits nothing while every
assignment is retired.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ai_builder():
    return importlib.import_module("ai_coding.build_seed")


@pytest.fixture
def th_builder():
    return importlib.import_module("take_home.build_seed")


def _manifest(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schema": "definitions-manifest/v1", "entries": entries}))
    return path


def test_the_committed_seed_migrations_no_longer_delete_rows():
    # The destructive delete+recreate is gone from both builders; the
    # committed 1700001200/1700001400 stay the historical v1 seed.
    ai = (ROOT / "backend" / "ai_coding" / "build_seed.py").read_text()
    th = (ROOT / "backend" / "take_home" / "build_seed.py").read_text()
    assert "deleteRecord" not in ai
    assert "deleteRecord" not in th


def test_ai_coding_emits_nothing_at_version_1(ai_builder, tmp_path, monkeypatch, capsys):
    manifest = _manifest(tmp_path, [
        {"kind": "harness-revision", "track": "ai-coding", "slug": "hallucinated-http-client",
         "variant": "python", "content_version": 1, "lifecycle": "active", "path": "x", "checksum": "c"},
    ])
    monkeypatch.setattr(ai_builder, "DEFINITIONS_MANIFEST", manifest)
    monkeypatch.setattr(ai_builder, "PRESENTATION_OUT", tmp_path / "out.js")
    ai_builder.main()
    assert not (tmp_path / "out.js").exists()
    assert "nothing to emit" in capsys.readouterr().out


def test_ai_coding_emits_a_non_destructive_upsert_for_a_new_version(ai_builder, tmp_path, monkeypatch):
    manifest = _manifest(tmp_path, [
        {"kind": "harness-revision", "track": "ai-coding", "slug": "hallucinated-http-client",
         "variant": "python", "content_version": 2, "lifecycle": "active", "path": "x", "checksum": "c"},
    ])
    out = tmp_path / "1700006300_ai_coding_presentation.js"
    monkeypatch.setattr(ai_builder, "DEFINITIONS_MANIFEST", manifest)
    monkeypatch.setattr(ai_builder, "PRESENTATION_OUT", out)
    ai_builder.main()
    text = out.read_text()
    assert "deleteRecord" not in text
    assert "findFirstRecordByData" in text and "saveRecord" in text
    rounds = json.loads(text.split("const ROUNDS = ", 1)[1].split(";\n", 1)[0])
    by_slug = {r["slug"]: r for r in rounds}
    assert by_slug["hallucinated-http-client"]["definition_version"] == 2
    assert "checkpoints" in by_slug["hallucinated-http-client"]


def test_ai_coding_presentation_migration_body_is_valid_js(ai_builder):
    body = ai_builder.presentation_migration(
        [{"slug": "r", "title": "R", "checkpoints": {}, "rubric": {"items": []}}], 2
    )
    assert body.lstrip().startswith("/// <reference")
    # The down step does nothing: forward-safe.
    assert "(_db) =>" in body


def test_take_home_emits_nothing_while_every_assignment_is_retired(th_builder, tmp_path, monkeypatch, capsys):
    manifest = _manifest(tmp_path, [
        {"kind": "harness-revision", "track": "take-home", "slug": s, "variant": "python",
         "content_version": 1, "lifecycle": "retired", "path": None, "checksum": None}
        for s in ("csv-summarize-py", "event-bus-ts", "kv-store-py")
    ])
    monkeypatch.setattr(th_builder, "DEFINITIONS_MANIFEST", manifest)
    monkeypatch.setattr(th_builder, "PRESENTATION_OUT", tmp_path / "out.js")
    th_builder.main()
    assert not (tmp_path / "out.js").exists()
    assert "nothing to emit" in capsys.readouterr().out
    assert th_builder.live_assignments() == []


def test_take_home_against_the_real_sources_emits_nothing():
    # Every assignment under backend/take_home/assignments/ is retired.
    th = importlib.import_module("take_home.build_seed")
    assert th.live_assignments() == []


def test_take_home_presentation_upsert_has_no_delete(th_builder):
    body = th_builder.presentation_migration(
        [{"slug": "a", "definition_version": 2, "title": "A", "rubric": {"items": []}}]
    )
    assert "deleteRecord" not in body and "findFirstRecordByData" in body
