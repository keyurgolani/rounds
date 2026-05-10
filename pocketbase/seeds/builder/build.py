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

Pass --no-smoke (or set ROUNDS_SMOKE=0) to skip the per-solution
smoke step for faster iteration during authoring. The smoke step
runs every in-scope problem's first Python solution through the
live runner and validates against expected outputs.
"""
from __future__ import annotations

import importlib
import inspect
import json
import os
import pkgutil
import re
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


# ---- Platform-coupling lint ----------------------------------------------
# Three smells that bog learners down with platform-internal details:
#   (a) Reference imports a seeded RNG and a test asserts a literal list/dict
#       — the test would only pass for one specific shuffle permutation.
#   (b) Description claims "any order" / "no particular order" but the test
#       expected is an ordered literal list — penalises learners whose
#       traversal differs.
#   (c) Float values appear in expected without `$match: approx` — exact-
#       equality on floats is brittle by default.
# Warn-only: each smell prints a one-liner; the build never aborts on lint.

_RNG_PATTERNS = (
    re.compile(r"\bimport\s+random\b"),
    re.compile(r"\bfrom\s+random\b"),
    re.compile(r"\bRandom\s*\("),
)
_ANY_ORDER_PATTERNS = (
    re.compile(r"any\s+order", re.IGNORECASE),
    re.compile(r"no\s+particular\s+order", re.IGNORECASE),
)


def _ref_uses_random(reference) -> bool:
    """True if the reference's defining module imports/uses random."""
    try:
        mod = inspect.getmodule(reference)
        src = inspect.getsource(mod) if mod else ""
    except (OSError, TypeError):
        src = ""
    return any(p.search(src) for p in _RNG_PATTERNS)


def _is_match_tag(v: Any) -> bool:
    return isinstance(v, dict) and isinstance(v.get("$match"), str)


def _has_float(v: Any) -> bool:
    """True iff `v` contains a float value that is *not* exactly representable
    in IEEE-754 by simple inspection. Floats that are integer-valued (e.g.
    `3.0`, `-1.0`) or half-integers (e.g. `1.5`, `-2.5`, `50.5`) are exact in
    binary, so exact-equality is fine and shouldn't trip the lint. This
    suppresses noise on median-style problems where the expected is always
    `n / 2` for some integer `n`."""
    if isinstance(v, bool):
        return False
    if isinstance(v, float):
        # Exactly representable: integer-valued or half-integer (n / 2 with
        # int n). `2 * v` lands on an integer with no rounding for those.
        try:
            doubled = v * 2
            if doubled == int(doubled):
                return False
        except (OverflowError, ValueError):
            pass
        return True
    if isinstance(v, list):
        return any(_has_float(x) for x in v)
    if isinstance(v, dict):
        return any(_has_float(x) for x in v.values())
    return False


def _could_encode_random_data(v: Any) -> bool:
    """True if `v` contains a string, float, or non-empty nested container —
    i.e. content that might be a shuffle/draw artifact. False for literals
    composed only of None/int/bool/empty containers, which are deterministic
    regardless of the RNG (e.g. `[None, 52]`, `[1]`, `{"mean": 0}`)."""
    if isinstance(v, str):
        return True
    if isinstance(v, float):
        return True
    if isinstance(v, list):
        return bool(v) and any(_could_encode_random_data(x) for x in v)
    if isinstance(v, dict):
        return bool(v) and any(_could_encode_random_data(x) for x in v.values())
    return False


def _lint_question(q) -> list[str]:
    payload = q.payload
    title = payload.get("title", "<untitled>")
    desc = payload.get("description", "") or ""
    cases = payload.get("test_cases") or []

    rng = _ref_uses_random(q.reference_python)
    any_order = any(p.search(desc) for p in _ANY_ORDER_PATTERNS)

    warnings: list[str] = []
    for idx, tc in enumerate(cases):
        expected = tc.get("expected")
        if _is_match_tag(expected):
            continue  # already using a tagged matcher — author opted out

        loc = f"  [{title}] case {idx} ({tc.get('description','')})"

        # (a) RNG-coupled literal list/dict — only warn when the literal
        # could plausibly encode shuffle/draw output. Trivially-deterministic
        # literals like `[None, 52]` or `{"mean": 0}` are skipped.
        if rng and _could_encode_random_data(expected):
            warnings.append(
                f"{loc}: reference uses `random` and `expected` is a literal "
                f"{type(expected).__name__}; consider `$match: validator` so the "
                f"test asserts behavioural properties, not a specific permutation."
            )

        # (b) "Any order" claim with an ordered literal of length > 1.
        if any_order and isinstance(expected, list) and len(expected) > 1:
            warnings.append(
                f"{loc}: description allows any order but `expected` is an ordered "
                f"literal list; consider `$match: unordered_deep`."
            )

        # (c) Float in literal expected without approx tolerance.
        if _has_float(expected):
            warnings.append(
                f"{loc}: `expected` contains float value(s) without "
                f"`$match: approx`; floating-point exact-equality is brittle."
            )
    return warnings


def _smoke_run_python_solution(question, match_fn, run_one) -> list[str]:
    """Exercise EVERY published Python solution against EVERY test case
    through the live runner subprocess. This catches: shape-conversion
    bugs in the runtime drivers (the kind we hit during the verbose-only
    migration), drift between a question's REFERENCE oracle and its
    published solutions, syntax errors in solution snippets, and
    matcher mismatches between build-time and runtime.

    Returns a list of failure strings; empty on full pass."""
    payload = question.payload
    entry = payload.get("entry")
    if not entry:
        return []
    solutions = payload.get("solutions") or []
    if not solutions:
        return []
    test_cases = payload.get("test_cases") or []
    if not test_cases:
        return []

    failures: list[str] = []
    title = payload.get("title", "<untitled>")

    for sol_idx, sol in enumerate(solutions):
        py_code = (sol.get("code") or {}).get("python")
        if not py_code:
            continue
        sol_label = sol.get("title") or f"solution #{sol_idx}"
        for tc_idx, tc in enumerate(test_cases):
            if tc_idx in question.skip_validation_indices:
                continue
            outcome = run_one(py_code, "python", entry, tc.get("input"))
            if outcome.error:
                failures.append(
                    f"  [{title}] [{sol_label}] case {tc_idx} ({tc.get('description', '')}): "
                    f"runner error: {outcome.error}"
                )
                continue
            passed, err = match_fn(tc.get("expected"), outcome.return_value, tc.get("input"))
            if not passed:
                failures.append(
                    f"  [{title}] [{sol_label}] case {tc_idx} ({tc.get('description', '')}): "
                    f"solution returned {outcome.return_value!r}, "
                    f"expected {tc.get('expected')!r}"
                    + (f" — matcher error: {err}" if err else "")
                )
    return failures


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
    lint_warnings: list[str] = []

    for q in QUESTIONS:
        lint_warnings.extend(_lint_question(q))

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

    smoke_enabled = (
        "--no-smoke" not in sys.argv
        and os.environ.get("ROUNDS_SMOKE", "1").lower() not in {"0", "false", "no", ""}
    )
    if smoke_enabled:
        # Smoke runs every (solution × test case) for every question
        # through the live runner subprocess. Each invocation forks a
        # Python (or Node) interpreter, so without a worker pool the
        # full sweep is dominated by interpreter startup. Parallelism
        # below is bounded by CPU count so the build doesn't hog the
        # box on dev laptops; override with ROUNDS_SMOKE_WORKERS.
        sys.path.insert(0, str(BACKEND_DIR))
        try:
            from runner import run_one  # type: ignore
        finally:
            sys.path.pop(0)

        from concurrent.futures import ThreadPoolExecutor

        try:
            workers = int(os.environ.get("ROUNDS_SMOKE_WORKERS", "0")) or (os.cpu_count() or 4)
        except ValueError:
            workers = os.cpu_count() or 4
        workers = max(1, min(workers, 32))

        print(f"Smoke testing every solution × every test case ({workers} workers)…")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for fail_list in pool.map(
                lambda q: _smoke_run_python_solution(q, match, run_one),
                QUESTIONS,
            ):
                failures.extend(fail_list)
    else:
        print("(smoke step skipped)")

    if lint_warnings:
        print(
            f"\nLint: {len(lint_warnings)} platform-coupling warning(s) "
            f"(non-fatal — see docs in this file):"
        )
        for w in lint_warnings:
            print(w)

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
