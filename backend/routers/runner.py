"""Code runner endpoints — the only HTTP surface the Python backend
owns now that content and user data live in PocketBase.

Both routes are admitted (``app.admission``). What they run comes from
the server, never the request:

- ``ROUNDS_GATE_EXECUTION_DEFINITIONS=legacy``: the caller names a
  question by slug and sends code and input; the entry, test cases, and
  expected values load from ``coding_questions`` with the caller's token.
- ``enforce``: the caller names a compiled test definition
  (``app.execution``); the entry, cases, and expected values come from
  its verified file, and validator predicates from the coding-validators
  revision it pins. The response carries the definition's receipt.

Validators run in the validator process (``app.validators``), never in
this one.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app import admission, definitions, execution
from app.errors import TypedError
from app.limits import EVALUATE_MAX_CASES
from app.pb_auth import pb_get
from matchers import match, validator_batch
from runner import run_one
from schemas import (
    CodeEvaluateRequest,
    CodeEvaluateResult,
    CodeRunRequest,
    CodeRunResult,
    DefinitionEvaluateRequest,
    DefinitionRunRequest,
    Entry,
    EvaluateCaseResult,
)

router = APIRouter(prefix="/api", tags=["runner"])

DEFAULT_TIMEOUT_S = 3
LARGE_TAG_TIMEOUT_S = 10
# The most one evaluate can run: every case it may select, each large.
EVALUATE_MAX_WALL_S = EVALUATE_MAX_CASES * LARGE_TAG_TIMEOUT_S
# A definition case's time class, in seconds.
TIME_CLASS_S = {"standard": DEFAULT_TIMEOUT_S, "large": LARGE_TAG_TIMEOUT_S}


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
async def run_code(request: Request):
    req = await execution.parse(request, CodeRunRequest, DefinitionRunRequest)
    if isinstance(req, DefinitionRunRequest):
        return await _run_definition(request, req)
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
    outcomes = [
        run_one(
            code,
            language,
            entry_dict,
            tc.get("input", {}),
            timeout_s=_timeout_for(tc),
            sandbox=slot,
        )
        for _i, tc in selected
    ]
    returned = [
        (tc.get("expected"), outcome.return_value, tc.get("input", {}))
        for (_i, tc), outcome in zip(selected, outcomes)
        if outcome.error is None
    ]
    results = []
    passed = 0
    failed = 0
    # The validator cases among them run in one validator process.
    with validator_batch(returned):
        checked = [
            (False, None) if outcome.error is not None
            else match(tc.get("expected"), outcome.return_value, tc.get("input", {}))
            for (_i, tc), outcome in zip(selected, outcomes)
        ]
    for (i, tc), outcome, (case_passed, matcher_error) in zip(selected, outcomes, checked):
        expected = tc.get("expected")
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
async def evaluate_code(request: Request):
    req = await execution.parse(request, CodeEvaluateRequest, DefinitionEvaluateRequest)
    if isinstance(req, DefinitionEvaluateRequest):
        return await _evaluate_definition(request, req)
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


# ---------------------------------------------------------------------------
# ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce
# ---------------------------------------------------------------------------


async def _run_definition(request: Request, req: DefinitionRunRequest) -> CodeRunResult:
    await admission.begin(request, req, wall_seconds=DEFAULT_TIMEOUT_S)
    resolved = execution.resolve(request, req.definition, "coding")
    document = resolved.document
    async with admission.allocate() as slot:
        outcome = await run_in_threadpool(
            run_one,
            req.code,
            document["variant"],
            document["entry"],
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
        definition=resolved.receipt(),
    )


def _select_definition_cases(request: Request, resolved: definitions.Resolved,
                             req: DefinitionEvaluateRequest) -> list[tuple[int, dict]]:
    """The definition's cases the request names, by id and tag, in their
    order. An id the version doesn't have is 422 ``case_unknown``."""
    cases = list(enumerate(resolved.document["cases"]))
    if req.case_ids is not None:
        known = {case["case_id"] for _i, case in cases}
        if any(case_id not in known for case_id in req.case_ids):
            raise execution.rejected(request, resolved, "case_unknown")
        wanted = set(req.case_ids)
        cases = [(i, case) for i, case in cases if case["case_id"] in wanted]
    if req.tags is not None:
        tags = set(req.tags)
        cases = [(i, case) for i, case in cases if tags & set(case.get("tags") or [])]
    return cases


def _predicates(resolved: definitions.Resolved) -> dict[str, str]:
    """The validator predicates the definition pins, by validator id."""
    ref = resolved.document.get("validators")
    if not ref:
        return {}
    revision = definitions.store().validators(ref["slug"], ref["content_version"], ref["checksum"])
    return {item["validator_id"]: item["predicate"] for item in revision["validators"]}


def _matcher(expected: dict[str, Any], predicates: dict[str, str]) -> Any:
    """A definition's expected value in the matcher form ``match`` reads."""
    if "literal" in expected:
        return {"$match": "exact", "value": expected["literal"]}
    if "validator_id" in expected:
        return {"$match": "validator", "code": predicates.get(expected["validator_id"])}
    spec = dict(expected)
    return {"$match": spec.pop("matcher"), **spec}


def _shown(expected: dict[str, Any]) -> Any:
    """What a result shows as expected: the literal itself, or the
    matcher without a validator's predicate."""
    if "literal" in expected:
        return expected["literal"]
    if "validator_id" in expected:
        return {"$match": "validator"}
    spec = dict(expected)
    return {"$match": spec.pop("matcher"), **spec}


def _evaluate_definition_cases(code, variant, entry, selected, predicates, slot) -> CodeEvaluateResult:
    outcomes = [
        run_one(code, variant, entry, case["input"], timeout_s=TIME_CLASS_S[case["time_class"]], sandbox=slot)
        for _i, case in selected
    ]
    matchers = [_matcher(case["expected"], predicates) for _i, case in selected]
    returned = [
        (matcher, outcome.return_value, case["input"])
        for (_i, case), outcome, matcher in zip(selected, outcomes, matchers)
        if outcome.error is None
    ]
    results = []
    passed = failed = 0
    with validator_batch(returned):
        checked = [
            (False, None) if outcome.error is not None else match(matcher, outcome.return_value, case["input"])
            for (_i, case), outcome, matcher in zip(selected, outcomes, matchers)
        ]
    for (i, case), outcome, (case_passed, matcher_error) in zip(selected, outcomes, checked):
        visible = case.get("visibility") == "visible"
        results.append(
            EvaluateCaseResult(
                index=i,
                case_id=case["case_id"],
                passed=case_passed,
                description=(case.get("description") or "") if visible else "",
                tags=list(case.get("tags") or []),
                output=outcome.return_value if visible else None,
                expected=_shown(case["expected"]) if visible else None,
                error=(outcome.error or matcher_error) if visible else None,
                duration_ms=outcome.duration_ms,
            )
        )
        if case_passed:
            passed += 1
        else:
            failed += 1
    return CodeEvaluateResult(passed=passed, failed=failed, results=results)


async def _evaluate_definition(request: Request, req: DefinitionEvaluateRequest) -> CodeEvaluateResult:
    # Admitted on one case's time, up to every case it may select; the
    # charge settles once the definition names the cases.
    await admission.begin(request, req, wall_seconds=DEFAULT_TIMEOUT_S, max_wall_seconds=EVALUATE_MAX_WALL_S)
    resolved = execution.resolve(request, req.definition, "coding")
    selected = _select_definition_cases(request, resolved, req)
    if len(selected) > EVALUATE_MAX_CASES:
        raise TypedError("limit_exceeded")
    predicates = _predicates(resolved)
    await admission.settle(request, sum(TIME_CLASS_S[case["time_class"]] for _i, case in selected))
    document = resolved.document
    async with admission.allocate() as slot:
        result = await run_in_threadpool(
            _evaluate_definition_cases, req.code, document["variant"], document["entry"], selected, predicates, slot
        )
    result.definition = resolved.receipt()
    return result
