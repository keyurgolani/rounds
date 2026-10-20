"""Matchers for grading code-runner output against an expected value.

`match(expected, output, input) -> (passed, error)`.

`expected` is either a literal (treated as `exact`) or a tagged dict:
    {"$match": "<kind>", ...kind-specific fields}

`error` is non-None only when a matcher could not run (e.g. validator
raised). Plain pass/fail returns `error=None` — the user's output is
already shown alongside the rendered expected, so the diff is self-evident.

A `validator` predicate never runs here: `app.validators` hands it to the
validator process, `python3 -I` with an empty environment
(ROUNDS-00A-L02). Inside `validator_batch(items)`, every validator case
in `items` has already been checked in one process, and `match` reads
those answers instead of starting a process per case.
"""
from __future__ import annotations

import contextvars
import json
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Sequence

from app import validators

MatchResult = tuple[bool, str | None]
Matcher = Callable[[dict, Any, Any], MatchResult]

_batch: contextvars.ContextVar[dict[str, MatchResult] | None] = contextvars.ContextVar(
    "rounds_validator_batch", default=None
)


def _is_validator(expected: Any) -> bool:
    return isinstance(expected, dict) and expected.get("$match") == "validator"


def _batch_key(code: str, input: Any, output: Any) -> str:
    return json.dumps([code, input, output], sort_keys=True)


@contextmanager
def validator_batch(items: Sequence[tuple[Any, Any, Any]]) -> Iterator[None]:
    """Checks the validator cases among ``(expected, output, input)``
    items in one validator process; ``match`` inside the block uses them."""
    pending = [
        (expected["code"], input, output)
        for expected, output, input in items
        if _is_validator(expected) and isinstance(expected.get("code"), str)
    ]
    answers = validators.run([validators.Check(code, input, output) for code, input, output in pending])
    token = _batch.set({_batch_key(*item): answer for item, answer in zip(pending, answers)})
    try:
        yield
    finally:
        _batch.reset(token)


def match(expected: Any, output: Any, input: Any) -> MatchResult:
    if isinstance(expected, dict) and isinstance(expected.get("$match"), str):
        kind = expected["$match"]
        fn = _MATCHERS.get(kind)
        if fn is None:
            return (False, f"Unknown matcher: {kind}")
        return fn(expected, output, input)
    return (output == expected, None)


def _exact(m: dict, output: Any, input: Any) -> MatchResult:
    return (output == m.get("value"), None)


def _unordered(m: dict, output: Any, input: Any) -> MatchResult:
    value = m.get("value")
    if not isinstance(output, list) or not isinstance(value, list):
        return (False, None)
    try:
        a = sorted(json.dumps(x, sort_keys=True) for x in output)
        b = sorted(json.dumps(x, sort_keys=True) for x in value)
    except TypeError:
        return (False, None)
    return (a == b, None)


def _unordered_deep(m: dict, output: Any, input: Any) -> MatchResult:
    value = m.get("value")
    return (_deep_multiset_equal(output, value), None)


def _deep_multiset_equal(a: Any, b: Any) -> bool:
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        unmatched = list(b)
        for x in a:
            for i, y in enumerate(unmatched):
                if _deep_multiset_equal(x, y):
                    unmatched.pop(i)
                    break
            else:
                return False
        return not unmatched
    return a == b


def _any_of(m: dict, output: Any, input: Any) -> MatchResult:
    values = m.get("values")
    if not isinstance(values, list) or not values:
        return (False, None)
    for v in values:
        if output == v:
            return (True, None)
    return (False, None)


def _contains(m: dict, output: Any, input: Any) -> MatchResult:
    value = m.get("value")
    if isinstance(output, str) and isinstance(value, str):
        return (value in output, None)
    if isinstance(output, list):
        if isinstance(value, list):
            return (all(v in output for v in value), None)
        return (value in output, None)
    return (False, None)


def _subset_of(m: dict, output: Any, input: Any) -> MatchResult:
    value = m.get("value")
    if not isinstance(output, list) or not isinstance(value, list):
        return (False, None)
    return (all(x in value for x in output), None)


def _superset_of(m: dict, output: Any, input: Any) -> MatchResult:
    value = m.get("value")
    if not isinstance(output, list) or not isinstance(value, list):
        return (False, None)
    return (all(v in output for v in value), None)


def _approx(m: dict, output: Any, input: Any) -> MatchResult:
    value = m.get("value")
    abs_tol = m.get("abs_tol") or 0
    rel_tol = m.get("rel_tol") or 0
    return (_approx_equal(output, value, abs_tol, rel_tol), None)


def _approx_equal(a: Any, b: Any, abs_tol: float, rel_tol: float) -> bool:
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(_approx_equal(x, y, abs_tol, rel_tol) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, bool) or isinstance(b, bool):
            return a == b
        return abs(a - b) <= max(abs_tol, rel_tol * max(abs(a), abs(b)))
    return False


def _validator(m: dict, output: Any, input: Any) -> MatchResult:
    code = m.get("code")
    if not isinstance(code, str):
        return (False, "Validator error: missing 'code' string")
    answers = _batch.get()
    if answers is not None:
        answer = answers.get(_batch_key(code, input, output))
        if answer is not None:
            return answer
    return validators.check_one(code, input, output)


_MATCHERS: dict[str, Matcher] = {
    "exact": _exact,
    "unordered": _unordered,
    "unordered_deep": _unordered_deep,
    "any_of": _any_of,
    "contains": _contains,
    "subset_of": _subset_of,
    "superset_of": _superset_of,
    "approx": _approx,
    "validator": _validator,
}
