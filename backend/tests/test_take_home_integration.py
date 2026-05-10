"""Take-home end-to-end: parse the seeded migration, run each
assignment's harness against its starter files via the real runner.
Locks in the build_seed → migration → runner pipeline."""
from __future__ import annotations

import json
import pathlib
import re

import pytest

from take_home.runner import run_assignment


@pytest.fixture
def seeded_assignments() -> list[dict]:
    """Parse the seeded ASSIGNMENTS array out of the take-home seed
    migration JS."""
    path = pathlib.Path(__file__).resolve().parents[2] / "pocketbase" / "pb_migrations" / "1700001400_take_home_seed.js"
    text = path.read_text(encoding="utf-8")
    m = re.search(r"const ASSIGNMENTS = (\[.*\]);\s*\n\s*migrate\(", text, re.DOTALL)
    assert m, "couldn't find ASSIGNMENTS array in seed migration"
    return json.loads(m.group(1))


def _run(assignment: dict, timeout_s: int = 30):
    """Materialize starter + harness into a single dict and run."""
    files: dict[str, str] = {}
    for f in assignment.get("starter_files") or []:
        files[f["path"]] = f["contents"]
    for f in assignment.get("harness_files") or []:
        files[f["path"]] = f["contents"]
    return run_assignment(files, assignment["entrypoint"], timeout_s=timeout_s)


def test_seeded_kv_store_py_runs_and_emits_six_criteria(seeded_assignments: list[dict]):
    a = next(x for x in seeded_assignments if x["slug"] == "kv-store-py")
    r = _run(a)
    assert r.error is None, f"runner errored: {r.error}\nstderr: {r.stderr}"
    assert len(r.criteria) == 6
    # Stub: 5 functional checks fail; code_quality heuristic passes →
    # score ~= 0.1. Assert a generous range.
    assert 0.0 <= r.score <= 0.2, f"unexpected score: {r.score}"


def test_seeded_csv_summarize_py_runs_and_emits_six_criteria(seeded_assignments: list[dict]):
    a = next(x for x in seeded_assignments if x["slug"] == "csv-summarize-py")
    r = _run(a)
    assert r.error is None, f"runner errored: {r.error}\nstderr: {r.stderr}"
    assert len(r.criteria) == 6
    # Stub raises NotImplementedError + code_quality fails (no csv/json
    # imports). Score = 0.0.
    assert r.score == 0.0


def test_seeded_event_bus_ts_runs_and_emits_six_criteria(seeded_assignments: list[dict]):
    a = next(x for x in seeded_assignments if x["slug"] == "event-bus-ts")
    r = _run(a)
    assert r.error is None, f"runner errored: {r.error}\nstderr: {r.stderr}"
    assert len(r.criteria) == 6
    # Stub throws on every method; no Map storage → all fail.
    assert r.score == 0.0


def test_all_seeded_assignments_have_required_fields(seeded_assignments: list[dict]):
    """Sanity: every seeded assignment must have the fields the runner
    + frontend rely on. A new assignment with a missing entrypoint
    would otherwise fail silently."""
    required = {"slug", "title", "language", "entrypoint", "starter_files", "harness_files", "rubric"}
    for a in seeded_assignments:
        missing = required - set(a.keys())
        assert not missing, f"assignment {a.get('slug')!r} missing fields: {missing}"
        # Every starter and harness file is a dict with path + contents.
        for f in a["starter_files"]:
            assert isinstance(f, dict) and "path" in f and "contents" in f
        for f in a["harness_files"]:
            assert isinstance(f, dict) and "path" in f and "contents" in f
        # Rubric items have id/label/weight/prompt.
        for it in (a["rubric"].get("items") or []):
            for key in ("id", "label", "weight", "prompt"):
                assert key in it, f"{a['slug']} rubric item missing {key!r}: {it}"
