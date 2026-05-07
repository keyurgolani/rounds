"""Meta-validation: run every question's REFERENCE function and every
sample solution against every test case via the backend runner + matchers.

Catches incorrect test cases, broken solutions, and driver regressions
at development time.

Run from repo root:
    python3 -m pytest backend/tests/test_question_validation.py -v

Skip the (slower) subprocess solution tests:
    python3 -m pytest backend/tests/test_question_validation.py -v -k "test_reference"
"""
from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SEEDS_DIR = REPO_ROOT / "pocketbase" / "seeds"
BACKEND_DIR = REPO_ROOT / "backend"

# ---- Import question modules (populates QUESTIONS registry) ----

sys.path.insert(0, str(SEEDS_DIR))
try:
    from builder import questions as _qpkg

    for _info in pkgutil.iter_modules(_qpkg.__path__):
        if _info.name.startswith("_"):
            continue
        importlib.import_module(f"builder.questions.{_info.name}")

    from builder.registry import QUESTIONS
finally:
    sys.path.pop(0)

# ---- Import backend modules ----

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from matchers import match  # type: ignore
from runner import run_one  # type: ignore


# ---- Helpers ----


def _qid(q) -> str:
    module = inspect.getmodule(q.reference_python)
    if module:
        return module.__name__.split(".")[-1]
    return q.payload.get("title", "unknown").lower().replace(" ", "_")[:40]


def _invoke_reference(reference, test_input: Any) -> Any:
    """Mirror build.py dispatch logic for calling REFERENCE functions."""
    if (
        isinstance(test_input, dict)
        and "ops" in test_input
        and "args" in test_input
    ):
        try:
            return reference(test_input)
        except TypeError:
            return reference(test_input["ops"], test_input["args"])
    if isinstance(test_input, dict):
        return reference(**test_input)
    if isinstance(test_input, list):
        return reference(*test_input)
    return reference(test_input)


# ---- Parametrize data builders ----


def _ref_cases():
    cases = []
    for q in QUESTIONS:
        qid = _qid(q)
        skip = q.skip_validation_indices
        for ti, tc in enumerate(q.payload.get("test_cases", [])):
            if ti in skip:
                continue
            cases.append(pytest.param(q, ti, id=f"{qid}::ref::case{ti}"))
    return cases


def _sol_cases():
    cases = []
    for q in QUESTIONS:
        qid = _qid(q)
        skip = q.skip_validation_indices
        entry = q.payload.get("entry")
        if not entry:
            continue
        for si, solution in enumerate(q.payload.get("solutions", [])):
            code = solution.get("code", {}).get("python")
            if not code:
                continue
            for ti, tc in enumerate(q.payload.get("test_cases", [])):
                if ti in skip:
                    continue
                cases.append(
                    pytest.param(
                        entry,
                        code,
                        ti,
                        tc,
                        id=f"{qid}::sol{si}::py::case{ti}",
                    )
                )
    return cases


# ---- Tests ----


@pytest.mark.parametrize("question,case_idx", _ref_cases())
def test_reference_oracle(question, case_idx):
    """REFERENCE function must produce the expected output for each test case."""
    tc = question.payload["test_cases"][case_idx]
    inp = deepcopy(tc.get("input"))
    expected = tc.get("expected")

    try:
        out = _invoke_reference(question.reference_python, inp)
    except Exception as e:
        pytest.fail(f"REFERENCE raised {type(e).__name__}: {e}")

    out = json.loads(json.dumps(out))

    passed, err = match(expected, out, tc.get("input"))
    assert passed, (
        f"Expected {expected!r}, got {out!r}"
        + (f" — {err}" if err else "")
    )


@pytest.mark.parametrize("entry,code,case_idx,tc", _sol_cases())
def test_solution_code(entry, code, case_idx, tc):
    """Each sample solution must produce the expected output for each test case."""
    timeout = 10 if "large" in (tc.get("tags") or []) else 5
    outcome = run_one(code, "python", entry, tc.get("input"), timeout_s=timeout)

    if outcome.error:
        pytest.fail(f"Runtime error: {outcome.error}")

    passed, err = match(tc.get("expected"), outcome.return_value, tc.get("input"))
    assert passed, (
        f"Expected {tc.get('expected')!r}, got {outcome.return_value!r}"
        + (f" — {err}" if err else "")
    )
