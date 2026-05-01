"""Code runner endpoints — the only HTTP surface the Python backend
owns now that content and user data live in PocketBase."""
from fastapi import APIRouter

from matchers import match
from runner import run_one
from schemas import (
    CodeEvaluateRequest,
    CodeEvaluateResult,
    CodeRunRequest,
    CodeRunResult,
    EvaluateCaseResult,
)

router = APIRouter(prefix="/api", tags=["runner"])

DEFAULT_TIMEOUT_S = 3
LARGE_TAG_TIMEOUT_S = 10


@router.post("/run", response_model=CodeRunResult)
def run_code(req: CodeRunRequest):
    outcome = run_one(
        req.code,
        req.language,
        req.entry.model_dump(),
        req.input,
        timeout_s=DEFAULT_TIMEOUT_S,
    )
    return CodeRunResult(
        stdout=outcome.stdout,
        stderr=outcome.stderr,
        return_value=outcome.return_value,
        error=outcome.error,
        duration_ms=outcome.duration_ms,
        truncated=outcome.truncated,
    )


def _select_cases(test_cases, flt):
    selected = []
    for i, tc in enumerate(test_cases):
        if flt and flt.indices is not None and i not in flt.indices:
            continue
        if flt and flt.tags is not None:
            case_tags = set(tc.get("tags") or [])
            if not case_tags & set(flt.tags):
                continue
        selected.append((i, tc))
    return selected


def _timeout_for(tc) -> int:
    tags = tc.get("tags") or []
    return LARGE_TAG_TIMEOUT_S if "large" in tags else DEFAULT_TIMEOUT_S


@router.post("/evaluate", response_model=CodeEvaluateResult)
def evaluate_code(req: CodeEvaluateRequest):
    selected = _select_cases(req.test_cases, req.filter)
    entry_dict = req.entry.model_dump()
    results = []
    passed = 0
    failed = 0
    for i, tc in selected:
        outcome = run_one(
            req.code,
            req.language,
            entry_dict,
            tc.get("input", {}),
            timeout_s=_timeout_for(tc),
        )
        expected = tc.get("expected")
        if outcome.error is not None:
            case_passed, matcher_error = False, None
        else:
            case_passed, matcher_error = match(expected, outcome.return_value, tc.get("input", {}))
        results.append(
            EvaluateCaseResult(
                index=i,
                passed=case_passed,
                description=tc.get("description") or "",
                tags=list(tc.get("tags") or []),
                output=outcome.return_value,
                expected=expected,
                error=outcome.error or matcher_error,
                duration_ms=outcome.duration_ms,
            )
        )
        if case_passed:
            passed += 1
        else:
            failed += 1
    return CodeEvaluateResult(passed=passed, failed=failed, results=results)
