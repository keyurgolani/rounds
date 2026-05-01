TWO_SUM_REVERSED = (
    "def two_sum(nums, target):\n"
    "    seen = {}\n"
    "    for i, n in enumerate(nums):\n"
    "        if target - n in seen:\n"
    "            return [i, seen[target - n]]\n"  # reversed order
    "        seen[n] = i\n"
)


def test_evaluate_unordered_accepts_reversed_order(client):
    res = client.post("/api/evaluate", json={
        "code": TWO_SUM_REVERSED,
        "language": "python",
        "entry": {"kind": "function", "name": "two_sum"},
        "test_cases": [
            {
                "input": {"nums": [2, 7, 11, 15], "target": 9},
                "expected": {"$match": "unordered", "value": [0, 1]},
                "description": "reversed-order solution still passes",
                "tags": ["basic"],
            },
        ],
    })
    data = res.json()
    assert data["passed"] == 1 and data["failed"] == 0


def test_evaluate_any_of_accepts_alternative_pair(client):
    code = (
        "def two_sum(nums, target):\n"
        "    return [2, 3]\n"
    )
    res = client.post("/api/evaluate", json={
        "code": code,
        "language": "python",
        "entry": {"kind": "function", "name": "two_sum"},
        "test_cases": [
            {
                "input": {"nums": [1, 5, 6, 9, 14], "target": 15},
                "expected": {"$match": "any_of", "values": [[0, 4], [2, 3]]},
                "description": "two valid pairs",
                "tags": ["tricky"],
            },
        ],
    })
    data = res.json()
    assert data["passed"] == 1


def test_evaluate_validator_passes_for_valid_two_sum(client):
    code = (
        "def two_sum(nums, target):\n"
        "    seen = {}\n"
        "    for i, n in enumerate(nums):\n"
        "        if target - n in seen:\n"
        "            return [seen[target - n], i]\n"
        "        seen[n] = i\n"
    )
    validator_code = (
        "lambda inp, out: isinstance(out, list) and len(out) == 2 "
        "and out[0] != out[1] "
        "and inp['nums'][out[0]] + inp['nums'][out[1]] == inp['target']"
    )
    res = client.post("/api/evaluate", json={
        "code": code,
        "language": "python",
        "entry": {"kind": "function", "name": "two_sum"},
        "test_cases": [
            {
                "input": {"nums": [1, 5, 6, 9, 14], "target": 15},
                "expected": {"$match": "validator", "code": validator_code,
                              "description": "any valid pair"},
                "description": "validator grades by predicate",
                "tags": ["tricky"],
            },
        ],
    })
    data = res.json()
    assert data["passed"] == 1


def test_evaluate_validator_error_propagates_to_case_error(client):
    code = "def f(x):\n    return x\n"
    res = client.post("/api/evaluate", json={
        "code": code,
        "language": "python",
        "entry": {"kind": "function", "name": "f"},
        "test_cases": [
            {
                "input": {"x": 1},
                "expected": {"$match": "validator", "code": "lambda inp, out: out[99]"},
                "description": "validator raises",
                "tags": [],
            },
        ],
    })
    data = res.json()
    assert data["passed"] == 0 and data["failed"] == 1
    assert data["results"][0]["error"] is not None
    assert "Validator error" in data["results"][0]["error"]


def test_evaluate_runtime_error_skips_matcher_and_surfaces_execution_error(client):
    # When user code raises, the matcher must not run — otherwise a derived
    # validator failure could mask the real runtime cause.
    code = "def f(x):\n    raise ValueError('boom')\n"
    res = client.post("/api/evaluate", json={
        "code": code,
        "language": "python",
        "entry": {"kind": "function", "name": "f"},
        "test_cases": [
            {
                "input": {"x": 1},
                "expected": {"$match": "validator", "code": "lambda inp, out: out[99]"},
                "description": "runtime error must win over validator",
                "tags": [],
            },
        ],
    })
    data = res.json()
    assert data["failed"] == 1
    err = data["results"][0]["error"] or ""
    assert "boom" in err
    assert "Validator error" not in err
