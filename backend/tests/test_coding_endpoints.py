PYTHON_TWO_SUM = (
    "def two_sum(nums, target):\n"
    "    seen = {}\n"
    "    for i, n in enumerate(nums):\n"
    "        if target - n in seen:\n"
    "            return [seen[target - n], i]\n"
    "        seen[n] = i\n"
)


def test_run_returns_stdout_and_return_value(client):
    code = "def solve(x):\n    print('hi'); return x + 1"
    res = client.post("/api/run", json={
        "code": code,
        "language": "python",
        "function_name": "solve",
        "input": {"x": 2},
    })
    assert res.status_code == 200
    data = res.json()
    assert data["stdout"].strip() == "hi"
    assert data["return_value"] == 3
    assert data["error"] is None


def test_run_rejects_non_object_input(client):
    res = client.post("/api/run", json={
        "code": "def solve(x): return x",
        "language": "python",
        "function_name": "solve",
        "input": [1, 2, 3],  # not an object
    })
    assert res.status_code == 422


def test_evaluate_no_filter_runs_all(client):
    res = client.post("/api/evaluate", json={
        "code": PYTHON_TWO_SUM,
        "language": "python",
        "function_name": "two_sum",
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1], "description": "a", "tags": ["basic"]},
            {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2], "description": "b", "tags": ["basic"]},
        ],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] == 2 and data["failed"] == 0
    assert [r["index"] for r in data["results"]] == [0, 1]


def test_evaluate_filter_by_tag(client):
    res = client.post("/api/evaluate", json={
        "code": PYTHON_TWO_SUM,
        "language": "python",
        "function_name": "two_sum",
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1], "description": "a", "tags": ["basic"]},
            {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2], "description": "b", "tags": ["edge"]},
            {"input": {"nums": [3, 3], "target": 6}, "expected": [0, 1], "description": "c", "tags": ["basic", "tricky"]},
        ],
        "filter": {"tags": ["edge"]},
    })
    data = res.json()
    assert [r["index"] for r in data["results"]] == [1]


def test_evaluate_filter_by_indices(client):
    res = client.post("/api/evaluate", json={
        "code": PYTHON_TWO_SUM,
        "language": "python",
        "function_name": "two_sum",
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1], "description": "a", "tags": ["basic"]},
            {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2], "description": "b", "tags": ["edge"]},
        ],
        "filter": {"indices": [0]},
    })
    data = res.json()
    assert [r["index"] for r in data["results"]] == [0]


def test_evaluate_filter_tags_and_indices_intersect(client):
    """Both fields supplied → intersection semantics."""
    res = client.post("/api/evaluate", json={
        "code": PYTHON_TWO_SUM,
        "language": "python",
        "function_name": "two_sum",
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1], "description": "a", "tags": ["basic"]},
            {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2], "description": "b", "tags": ["edge"]},
            {"input": {"nums": [3, 3], "target": 6}, "expected": [0, 1], "description": "c", "tags": ["basic"]},
        ],
        "filter": {"tags": ["basic"], "indices": [2]},
    })
    data = res.json()
    assert [r["index"] for r in data["results"]] == [2]


def test_evaluate_records_failed_case(client):
    code = "def two_sum(nums, target): return [0, 0]"  # wrong answer
    res = client.post("/api/evaluate", json={
        "code": code,
        "language": "python",
        "function_name": "two_sum",
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1], "description": "a", "tags": ["basic"]},
        ],
    })
    data = res.json()
    assert data["passed"] == 0 and data["failed"] == 1
    assert data["results"][0]["output"] == [0, 0]


def test_execute_alias_still_works(client):
    """Legacy endpoint continues to work (thin wrapper over evaluate)."""
    res = client.post("/api/execute", json={
        "code": PYTHON_TWO_SUM,
        "language": "python",
        "function_name": "two_sum",
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
        ],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] == 1


def test_evaluate_class_based(client):
    """LRU-style class test — ops + args parallel arrays."""
    code = (
        "class Counter:\n"
        "    def __init__(self, start): self.n = start\n"
        "    def inc(self, by): self.n += by; return self.n\n"
    )
    res = client.post("/api/evaluate", json={
        "code": code,
        "language": "python",
        "function_name": "Counter",
        "test_cases": [
            {
                "input": {"ops": ["Counter", "inc", "inc"], "args": [[10], [2], [3]]},
                "expected": [None, 12, 15],
                "description": "counter sequence",
                "tags": ["basic"],
            },
        ],
    })
    data = res.json()
    assert data["passed"] == 1
