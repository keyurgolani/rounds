"""Code runner endpoints — the only HTTP surface the Python backend
owns now that content and user data live in PocketBase.

Both routes are admitted (``app.admission``). The caller names a
question by slug and sends only code and input; the entry, test cases,
and expected values load from ``coding_questions`` with the caller's
token, and validators come only from that stored data.

TODO(ROUNDS-00A-L02): #2's server-owned Test Definitions replace the
caller-token lookup, and validators leave the API process.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app import admission
from app.errors import TypedError
from app.limits import EVALUATE_MAX_CASES
from app.pb_auth import pb_get
from matchers import match
from runner import run_one
from schemas import (
    CodeEvaluateRequest,
    CodeEvaluateResult,
    CodeRunRequest,
    CodeRunResult,
    Entry,
    EvaluateCaseResult,
)

router = APIRouter(prefix="/api", tags=["runner"])

DEFAULT_TIMEOUT_S = 3
LARGE_TAG_TIMEOUT_S = 10
# The most one evaluate can run: every case it may select, each large.
EVALUATE_MAX_WALL_S = EVALUATE_MAX_CASES * LARGE_TAG_TIMEOUT_S


async def _load_question(request: Request, slug: str) -> tuple[dict, list[dict]]:
    """Step 8: the question's stored entry and test cases."""
    user = admission.account(request)
    question = await admission.first_item(pb_get, user["token"], "coding_questions", slug)
    try:
        entry = Entry.model_validate(question.get("entry") or {})
    except ValidationError:
        raise TypedError("invalid_request", "This question can't run here.") from None
    if entry.kind == "custom":
        # Stored custom drivers stay off until #2's harness runs them.
        raise TypedError("invalid_request", "This question can't run here.")
    cases = question.get("test_cases") or []
    if not isinstance(cases, list):
        raise TypedError("invalid_request", "This question can't run here.")
    return entry.model_dump(), [tc for tc in cases if isinstance(tc, dict)]


@router.post("/run", response_model=CodeRunResult)
async def run_code(request: Request, req: CodeRunRequest):
    await admission.begin(request, req, wall_seconds=DEFAULT_TIMEOUT_S)
    entry, _cases = await _load_question(request, req.question_slug)
    async with admission.allocate() as slot:
        outcome = await run_in_threadpool(
            run_one,
            req.code,
            req.language,
            entry,
            req.input,
            timeout_s=DEFAULT_TIMEOUT_S,
            sandbox=slot,
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


def _evaluate(code, language, entry_dict, selected, slot) -> CodeEvaluateResult:
    results = []
    passed = 0
    failed = 0
    for i, tc in selected:
        outcome = run_one(
            code,
            language,
            entry_dict,
            tc.get("input", {}),
            timeout_s=_timeout_for(tc),
            sandbox=slot,
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


@router.post("/evaluate", response_model=CodeEvaluateResult)
async def evaluate_code(request: Request, req: CodeEvaluateRequest):
    # Admitted on one case's time, up to every case it may select; the
    # charge settles once the cases load.
    await admission.begin(request, req, wall_seconds=DEFAULT_TIMEOUT_S, max_wall_seconds=EVALUATE_MAX_WALL_S)
    entry_dict, cases = await _load_question(request, req.question_slug)
    selected = _select_cases(cases, req.filter)
    if len(selected) > EVALUATE_MAX_CASES:
        raise TypedError("limit_exceeded")
    await admission.settle(request, sum(_timeout_for(tc) for _index, tc in selected))
    async with admission.allocate() as slot:
        return await run_in_threadpool(_evaluate, req.code, req.language, entry_dict, selected, slot)
