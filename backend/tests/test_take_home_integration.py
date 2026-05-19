"""Take-home seed shape guards: parse the seeded ASSIGNMENTS array and
assert every entry carries the fields the runner + frontend depend on,
and that rubric weights sum to one. Catches a regression where adding
a new assignment forgets a required field."""
from __future__ import annotations

import json
import pathlib
import re

import pytest

@pytest.fixture
def seeded_assignments() -> list[dict]:
    """Parse the seeded ASSIGNMENTS array out of the take-home seed
    migration JS. The array may be intentionally empty between catalog
    refreshes — when it is, the seed file carries a `// ...` comment
    explaining why. Strip JS line comments before json.loads so an
    explanatory-comment-only body still parses to []."""
    path = pathlib.Path(__file__).resolve().parents[2] / "pocketbase" / "pb_migrations" / "1700001400_take_home_seed.js"
    text = path.read_text(encoding="utf-8")
    m = re.search(r"const ASSIGNMENTS = (\[.*\]);\s*\n\s*migrate\(", text, re.DOTALL)
    assert m, "couldn't find ASSIGNMENTS array in seed migration"
    cleaned = re.sub(r"//[^\n]*", "", m.group(1))
    return json.loads(cleaned)


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


def test_seeded_take_home_rubric_weights_sum_to_one(seeded_assignments: list[dict]):
    """Catch a regression where adding/removing a rubric item leaves
    the weights miscalibrated."""
    for a in seeded_assignments:
        items = (a["rubric"] or {}).get("items") or []
        if not items:
            continue
        total = sum(float(it.get("weight", 0)) for it in items)
        assert abs(total - 1.0) < 1e-6, (
            f"rubric weights for {a['slug']!r} sum to {total!r}, expected 1.0"
        )
