"""Matchers for grading code-runner output against an expected value.

`match(expected, output, input) -> (passed, error)`.

`expected` is either a literal (treated as `exact`) or a tagged dict:
    {"$match": "<kind>", ...kind-specific fields}

`error` is non-None only when a matcher could not run (e.g. validator
raised). Plain pass/fail returns `error=None` — the user's output is
already shown alongside the rendered expected, so the diff is self-evident.
"""
from __future__ import annotations

import json
from typing import Any, Callable

MatchResult = tuple[bool, str | None]
Matcher = Callable[[dict, Any, Any], MatchResult]

_SAFE_BUILTINS = {
    "len": len, "range": range, "sum": sum, "set": set, "sorted": sorted,
    "all": all, "any": any, "abs": abs, "min": min, "max": max,
    "enumerate": enumerate, "zip": zip, "map": map, "filter": filter,
    "isinstance": isinstance,
    "list": list, "tuple": tuple, "dict": dict, "str": str,
    "int": int, "float": float, "bool": bool,
    "True": True, "False": False, "None": None,
}
_VALIDATOR_GLOBALS = {"__builtins__": _SAFE_BUILTINS}


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
    try:
        predicate = eval(code, _VALIDATOR_GLOBALS, {})
    except Exception as e:
        return (False, f"Validator error: {e}")
    try:
        result = predicate(input, output)
    except Exception as e:
        return (False, f"Validator error: {e}")
    return (bool(result), None)


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
