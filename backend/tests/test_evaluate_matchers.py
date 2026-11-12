"""Matchers through /api/evaluate's older request shape (admission/v1,
ROUNDS-00A-L01).

Expected values, validators included, came only from the stored question.
Since ROUNDS-00A-L03 PR 4 the route runs definitions only, as jobs, and
at the shipped gates the execution keys act as off: each older request,
from anyone, answers 503 ``execution_disabled`` before the account check,
and no matcher or validator runs. test_matchers.py covers the matchers
themselves, and test_execution_scratch.py a definition's validators in a
job."""
import pytest

TWO_SUM_REVERSED = (
    "def two_sum(nums, target):\n"
    "    seen = {}\n"
    "    for i, n in enumerate(nums):\n"
    "        if target - n in seen:\n"
    "            return [i, seen[target - n]]\n"  # reversed order
    "        seen[n] = i\n"
)

TWO_SUM = (
    "def two_sum(nums, target):\n"
    "    seen = {}\n"
    "    for i, n in enumerate(nums):\n"
    "        if target - n in seen:\n"
    "            return [seen[target - n], i]\n"
    "        seen[n] = i\n"
)

VALID_PAIR = (
    "lambda inp, out: isinstance(out, list) and len(out) == 2 "
    "and out[0] != out[1] "
    "and inp['nums'][out[0]] + inp['nums'][out[1]] == inp['target']"
)

# Each scenario: the stored question, then the caller's code.
SCENARIOS = {
    "unordered": (
        {
            "slug": "two-sum-unordered",
            "entry": {"kind": "function", "name": "two_sum"},
            "test_cases": [{
                "input": {"nums": [2, 7, 11, 15], "target": 9},
                "expected": {"$match": "unordered", "value": [0, 1]},
                "description": "reversed-order solution still passes",
                "tags": ["basic"],
            }],
        },
        TWO_SUM_REVERSED,
    ),
    "any_of": (
        {
            "slug": "two-sum-any-of",
            "entry": {"kind": "function", "name": "two_sum"},
            "test_cases": [{
                "input": {"nums": [1, 5, 6, 9, 14], "target": 15},
                "expected": {"$match": "any_of", "values": [[0, 4], [2, 3]]},
                "description": "two valid pairs",
                "tags": ["tricky"],
            }],
        },
        "def two_sum(nums, target):\n    return [2, 3]\n",
    ),
    "validator": (
        {
            "slug": "two-sum-validator",
            "entry": {"kind": "function", "name": "two_sum"},
            "test_cases": [{
                "input": {"nums": [1, 5, 6, 9, 14], "target": 15},
                "expected": {"$match": "validator", "code": VALID_PAIR, "description": "any valid pair"},
                "description": "validator grades by predicate",
                "tags": ["tricky"],
            }],
        },
        TWO_SUM,
    ),
    "validator_error": (
        {
            "slug": "identity-validator-error",
            "entry": {"kind": "function", "name": "f"},
            "test_cases": [{
                "input": {"x": 1},
                "expected": {"$match": "validator", "code": "lambda inp, out: out[99]"},
                "description": "validator raises",
                "tags": [],
            }],
        },
        "def f(x):\n    return x\n",
    ),
    "runtime_error": (
        {
            "slug": "identity-runtime-error",
            "entry": {"kind": "function", "name": "f"},
            "test_cases": [{
                "input": {"x": 1},
                "expected": {"$match": "validator", "code": "lambda inp, out: out[99]"},
                "description": "runtime error must win over validator",
                "tags": [],
            }],
        },
        "def f(x):\n    raise ValueError('boom')\n",
    ),
}


def _evaluate(client, questions, headers, scenario):
    question, code = SCENARIOS[scenario]
    questions.add(**question)
    return client.post(
        "/api/evaluate",
        json={"question_slug": question["slug"], "code": code, "language": "python"},
        headers=headers,
    )


# ---- expected-deny controls (#8) ---------------------------------------------


@pytest.fixture
def matched(monkeypatch):
    """Every matcher call, validators included."""
    from routers import runner as runner_router

    calls = []
    real = runner_router.match

    def spy(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    monkeypatch.setattr(runner_router, "match", spy)
    return calls


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_an_older_evaluate_from_anyone_is_turned_off_before_any_matcher_runs(client, signed_in, questions, matched,
                                                                             scenario):
    for headers in ({}, signed_in):
        res = _evaluate(client, questions, headers, scenario)
        assert res.status_code == 503
        assert res.json()["code"] == "execution_disabled"
    assert matched == []
    assert questions.calls == []


def test_a_caller_supplied_validator_is_refused_before_anything_runs(client, signed_in, questions, matched):
    questions.add(**SCENARIOS["validator"][0])
    res = client.post(
        "/api/evaluate",
        json={
            "question_slug": "two-sum-validator",
            "code": TWO_SUM,
            "language": "python",
            "test_cases": [{"input": {}, "expected": {"$match": "validator", "code": "lambda inp, out: True"}}],
        },
        headers=signed_in,
    )
    assert res.status_code == 503
    assert res.json()["code"] == "execution_disabled"
    assert matched == []
    assert questions.calls == []
