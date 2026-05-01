"""Build & validate the consolidated `more_coding.json` seed file.

Workflow:
  1. Import every module under `builder/questions/` (each registers a
     `Question` with the canonical PocketBase payload + a Python
     reference solution).
  2. Validate: invoke each reference solution against every test case
     and run the result through `backend/matchers.match()`. Any
     mismatch aborts the build with a precise diagnostic — catches
     typos, off-by-one validators, missing edge cases, etc.
   3. Emit `pocketbase/seeds/more_coding.json`. The fresh-release data
      seed migration consumes this artifact.

Run from the repo root:
    python -m pocketbase.seeds.builder.build

Or directly:
    cd pocketbase/seeds && python -m builder.build
"""
from __future__ import annotations

import importlib
import json
import pkgutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
SEEDS_DIR = REPO_ROOT / "pocketbase" / "seeds"
OUT_FILE = SEEDS_DIR / "more_coding.json"
BACKEND_DIR = REPO_ROOT / "backend"


def _load_matcher():
    """Import the live runtime matcher — the same one the production
    code runner uses — so build-time validation can't drift from
    runtime grading."""
    sys.path.insert(0, str(BACKEND_DIR))
    from matchers import match  # type: ignore

    sys.path.pop(0)
    return match


def _discover_modules() -> list[Any]:
    from builder import questions as _qpkg  # type: ignore

    mods = []
    for info in pkgutil.iter_modules(_qpkg.__path__):
        if info.name.startswith("_"):
            continue
        mods.append(importlib.import_module(f"builder.questions.{info.name}"))
    return mods


def _invoke_reference(reference, test_input: Any) -> Any:
    """Mirror the dispatch logic in `backend/runner.py::_run_python`."""
    if (
        isinstance(test_input, dict)
        and "ops" in test_input
        and "args" in test_input
    ):
        # Class-based sequence — reference must accept the dict and
        # replay the op sequence. Most class problems define a tiny
        # driver lambda; some accept (ops, args) directly. Try both.
        try:
            return reference(test_input)
        except TypeError:
            return reference(test_input["ops"], test_input["args"])
    if isinstance(test_input, dict):
        return reference(**test_input)
    if isinstance(test_input, list):
        return reference(*test_input)
    return reference(test_input)


def main() -> int:
    match = _load_matcher()
    sys.path.insert(0, str(SEEDS_DIR))
    try:
        _discover_modules()
        from builder.registry import QUESTIONS  # type: ignore
    finally:
        sys.path.pop(0)

    if not QUESTIONS:
        print("No questions registered.")
        return 1

    failures: list[str] = []

    for q in QUESTIONS:
        title = q.payload.get("title", "<untitled>")
        cases = q.payload.get("test_cases") or []
        for idx, tc in enumerate(cases):
            if idx in q.skip_validation_indices:
                continue
            inp = deepcopy(tc.get("input"))
            expected = tc.get("expected")
            try:
                out = _invoke_reference(q.reference_python, inp)
            except Exception as e:  # pragma: no cover - surfaced as failure
                failures.append(
                    f"  [{title}] case {idx} ({tc.get('description','')}): "
                    f"reference raised {type(e).__name__}: {e}"
                )
                continue
            # Round-trip through JSON to mirror what the runner returns
            # to the matcher (e.g. tuples become lists).
            try:
                out = json.loads(json.dumps(out))
            except (TypeError, ValueError) as e:
                failures.append(
                    f"  [{title}] case {idx}: reference returned non-JSON "
                    f"value: {type(e).__name__}: {e}"
                )
                continue
            passed, err = match(expected, out, tc.get("input"))
            if not passed:
                failures.append(
                    f"  [{title}] case {idx} ({tc.get('description','')}): "
                    f"reference output={out!r} did not match expected={expected!r}"
                    + (f" — matcher error: {err}" if err else "")
                )

    if failures:
        print(f"\nBuild aborted — {len(failures)} validation failure(s):")
        for f in failures:
            print(f)
        return 2

    payload = {"coding_questions": [q.payload for q in QUESTIONS]}
    OUT_FILE.write_text(json.dumps(payload, indent=2))
    print(
        f"Wrote {OUT_FILE.relative_to(REPO_ROOT)} "
        f"({len(QUESTIONS)} question(s), {OUT_FILE.stat().st_size:,} bytes)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
