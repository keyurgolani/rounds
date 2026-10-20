"""The seed builders after the definitions rework (ROUNDS-00A-L02).

The builders no longer delete and recreate presentation rows. They leave
the committed v1 seed migrations (1700001200, 1700001400) in place and,
only when a compiled definition is past version 1, emit a new
presentation-only upsert migration: display fields only, each row at its
own version, in a new file per version bump. Take-home emits nothing while
every assignment is retired.
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


def _ai(slug: str, version: int, variant: str = "python") -> dict:
    return {"kind": "harness-revision", "track": "ai-coding", "slug": slug, "variant": variant,
            "content_version": version, "lifecycle": "active", "path": "x", "checksum": "c"}


def _migrations(tmp_path: Path) -> Path:
    path = tmp_path / "pb_migrations"
    path.mkdir()
    (path / "1700006200_definitions_expand.js").write_text("// applied\n")
    return path


def _rounds(tmp_path: Path, slugs: list[str]) -> Path:
    """Single-language rounds with one checkpoint that has a test command,
    a test glob, and a hidden test."""
    root = tmp_path / "rounds"
    for slug in slugs:
        d = root / slug
        (d / "starter").mkdir(parents=True)
        (d / "starter" / "main.py").write_text("x = 1\n")
        (d / "checkpoints" / "0" / "hidden_tests").mkdir(parents=True)
        (d / "checkpoints" / "0" / "hidden_tests" / "test_hidden.py").write_text("def test_h(): pass\n")
        (d / "manifest.json").write_text(json.dumps({
            "slug": slug, "title": slug.upper(), "language": "python",
            "checkpoints": [{"label": "One", "prompt": "Do it.", "ai_allowed": True,
                             "test_command": "pytest tests/test_visible.py", "tests_glob": "tests/*"}],
        }))
    return root


def _emitted(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.js") if "presentation" in p.name)


def _rows(path: Path, const: str) -> list[dict]:
    return json.loads(path.read_text().split(f"const {const} = ", 1)[1].split(";\n", 1)[0])


def test_the_committed_seed_migrations_no_longer_delete_rows():
    # The destructive delete+recreate is gone from both builders; the
    # committed 1700001200/1700001400 stay the historical v1 seed.
    ai = (ROOT / "backend" / "ai_coding" / "build_seed.py").read_text()
    th = (ROOT / "backend" / "take_home" / "build_seed.py").read_text()
    assert "deleteRecord" not in ai
    assert "deleteRecord" not in th


def test_ai_coding_emits_nothing_at_version_1(ai_builder, tmp_path, monkeypatch, capsys):
    manifest = _manifest(tmp_path, [_ai("hallucinated-http-client", 1)])
    migrations = _migrations(tmp_path)
    monkeypatch.setattr(ai_builder, "DEFINITIONS_MANIFEST", manifest)
    monkeypatch.setattr(ai_builder, "MIGRATIONS", migrations)
    ai_builder.main()
    assert _emitted(migrations) == []
    assert "nothing to emit" in capsys.readouterr().out


def test_ai_coding_emits_a_non_destructive_upsert_for_a_new_version(ai_builder, tmp_path, monkeypatch):
    manifest = _manifest(tmp_path, [_ai("hallucinated-http-client", 2), _ai("hallucinated-http-client", 2, "typescript")])
    migrations = _migrations(tmp_path)
    monkeypatch.setattr(ai_builder, "DEFINITIONS_MANIFEST", manifest)
    monkeypatch.setattr(ai_builder, "MIGRATIONS", migrations)
    ai_builder.main()
    (out,) = _emitted(migrations)
    # A new file, numbered after every migration already there.
    assert out.name.startswith("1700006201_ai_coding_presentation_")
    text = out.read_text()
    assert "deleteRecord" not in text
    assert "findFirstRecordByData" in text and "saveRecord" in text
    by_slug = {r["slug"]: r for r in _rows(out, "ROUNDS")}
    row = by_slug["hallucinated-http-client"]
    assert row["definition_version"] == 2
    # Display only: what runs and how it scores stay in the compiled revision.
    checkpoints = [cp for cps in row["checkpoints"].values() for cp in cps]
    assert checkpoints and all(set(cp) <= {"label", "prompt", "ai_allowed"} for cp in checkpoints)
    assert all(cp.get("label") for cp in checkpoints)
    for field in ("test_command", "hidden_files", "tests_glob"):
        assert field not in text, field


def test_ai_coding_stamps_each_round_with_its_own_version(ai_builder, tmp_path, monkeypatch):
    rounds = _rounds(tmp_path, ["alpha", "beta", "gamma"])
    manifest = _manifest(tmp_path, [_ai("alpha", 3), _ai("beta", 2), _ai("gamma", 1)])
    migrations = _migrations(tmp_path)
    monkeypatch.setattr(ai_builder, "ROOT", rounds)
    monkeypatch.setattr(ai_builder, "DEFINITIONS_MANIFEST", manifest)
    monkeypatch.setattr(ai_builder, "MIGRATIONS", migrations)
    ai_builder.main()
    (out,) = _emitted(migrations)
    rows = {r["slug"]: r for r in _rows(out, "ROUNDS")}
    # gamma is still the committed v1 seed, so it isn't touched.
    assert {slug: r["definition_version"] for slug, r in rows.items()} == {"alpha": 3, "beta": 2}
    assert rows["alpha"]["checkpoints"] == [{"label": "One", "prompt": "Do it.", "ai_allowed": True}]


def test_a_version_bump_gets_a_new_file_and_never_rewrites_one(ai_builder, tmp_path, monkeypatch, capsys):
    rounds = _rounds(tmp_path, ["alpha"])
    migrations = _migrations(tmp_path)
    monkeypatch.setattr(ai_builder, "ROOT", rounds)
    monkeypatch.setattr(ai_builder, "MIGRATIONS", migrations)
    monkeypatch.setattr(ai_builder, "DEFINITIONS_MANIFEST", _manifest(tmp_path, [_ai("alpha", 2)]))
    ai_builder.main()
    (first,) = _emitted(migrations)
    applied = first.read_bytes()
    # The same versions again: nothing new, and the first file is as it was.
    ai_builder.main()
    assert _emitted(migrations) == [first] and first.read_bytes() == applied
    assert "already there" in capsys.readouterr().out
    # The next bump: a second file after the first, the first untouched.
    monkeypatch.setattr(ai_builder, "DEFINITIONS_MANIFEST", _manifest(tmp_path, [_ai("alpha", 3)]))
    ai_builder.main()
    emitted = _emitted(migrations)
    assert len(emitted) == 2 and emitted[0] == first and first.read_bytes() == applied
    assert int(emitted[1].name.split("_", 1)[0]) > int(first.name.split("_", 1)[0])
    assert _rows(emitted[1], "ROUNDS")[0]["definition_version"] == 3


def test_ai_coding_presentation_migration_body_is_valid_js(ai_builder):
    body = ai_builder.presentation_migration(
        [{"definition_version": 2, "slug": "r", "title": "R", "checkpoints": {}, "rubric": {"items": []}}]
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
    migrations = _migrations(tmp_path)
    monkeypatch.setattr(th_builder, "DEFINITIONS_MANIFEST", manifest)
    monkeypatch.setattr(th_builder, "MIGRATIONS", migrations)
    th_builder.main()
    assert _emitted(migrations) == []
    assert "nothing to emit" in capsys.readouterr().out
    assert th_builder.live_assignments() == []


def test_take_home_presentation_carries_no_execution_fields(th_builder, tmp_path, monkeypatch):
    assignments = tmp_path / "assignments"
    d = assignments / "fresh-py"
    (d / "starter").mkdir(parents=True)
    (d / "starter" / "main.py").write_text("x = 1\n")
    (d / "harness").mkdir()
    (d / "harness" / "run.py").write_text("print('grade')\n")
    (d / "prompt.md").write_text("# Fresh\n")
    (d / "manifest.json").write_text(json.dumps({"slug": "fresh-py", "title": "Fresh", "language": "python",
                                                 "entrypoint": "python3 harness/run.py"}))
    manifest = _manifest(tmp_path, [{"kind": "harness-revision", "track": "take-home", "slug": "fresh-py",
                                     "variant": "python", "content_version": 2, "lifecycle": "active",
                                     "path": "x", "checksum": "c"}])
    migrations = _migrations(tmp_path)
    monkeypatch.setattr(th_builder, "ROOT", assignments)
    monkeypatch.setattr(th_builder, "DEFINITIONS_MANIFEST", manifest)
    monkeypatch.setattr(th_builder, "MIGRATIONS", migrations)
    th_builder.main()
    (out,) = _emitted(migrations)
    assert out.name.startswith("1700006201_take_home_presentation_")
    (row,) = _rows(out, "ASSIGNMENTS")
    assert row["definition_version"] == 2 and row["title"] == "Fresh"
    assert "entrypoint" not in row and "harness_files" not in row
    assert "harness/run.py" not in out.read_text()


def test_take_home_against_the_real_sources_emits_nothing():
    # Every assignment under backend/take_home/assignments/ is retired.
    th = importlib.import_module("take_home.build_seed")
    assert th.live_assignments() == []


def test_take_home_presentation_upsert_has_no_delete(th_builder):
    body = th_builder.presentation_migration(
        [{"slug": "a", "definition_version": 2, "title": "A", "rubric": {"items": []}}]
    )
    assert "deleteRecord" not in body and "findFirstRecordByData" in body
