"""Runtime smoke test: shells out to backend/runner.py for one
representative test case per question. Catches escaping issues
(`\\n` inside generated code, etc.) that pure-Python build-time
validation can't see because it never round-trips through the
subprocess JSON layer.

Run from `pocketbase/seeds/`:
    python3 -m builder.runtime_smoke
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SEEDS_DIR = REPO_ROOT / "pocketbase" / "seeds"
BACKEND_DIR = REPO_ROOT / "backend"


def _function_name(code: str, lang: str) -> str:
    """Mirror the frontend's `extractFunctionName` heuristic so we
    pick the same entry point the runtime would."""
    if lang == "python":
        m = re.search(r"class\s+(\w+)", code)
        if m:
            return m.group(1)
        m = re.search(r"def\s+(\w+)\s*\(", code)
        return m.group(1) if m else "solution"
    if lang == "javascript":
        m = re.search(r"function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=|class\s+(\w+)", code)
        if m:
            return m.group(1) or m.group(2) or m.group(3)
        return "solution"
    return "solution"


def main() -> int:
    sys.path.insert(0, str(BACKEND_DIR))
    from matchers import match  # type: ignore
    from runner import run_one  # type: ignore

    payload = json.loads((SEEDS_DIR / "more_coding.json").read_text())
    questions = payload["coding_questions"]

    failures: list[str] = []
    for q in questions:
        title = q["title"]
        ref_solution = q["solutions"][0]
        py_code = ref_solution["code"]["python"]
        fn_name = _function_name(py_code, "python")
        # Pick one test case per question — the smoke test is a sanity
        # check on the full pipeline, not exhaustive (build.py already
        # exhaustively validates against `match()`).
        tc = q["test_cases"][0]
        outcome = run_one(py_code, "python", fn_name, tc["input"], timeout_s=8)
        if outcome.error is not None:
            failures.append(
                f"  [{title}] runtime error: {outcome.error[:200]}"
            )
            continue
        passed, err = match(tc["expected"], outcome.return_value, tc["input"])
        if not passed:
            failures.append(
                f"  [{title}] runtime returned {outcome.return_value!r}, "
                f"matcher rejected (expected={tc['expected']!r}, err={err})"
            )

    if failures:
        print(f"\nRuntime smoke aborted — {len(failures)} failure(s):")
        for f in failures:
            print(f)
        return 2
    print(f"Runtime smoke OK — {len(questions)} questions exercised end-to-end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
