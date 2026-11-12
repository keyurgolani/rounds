"""/api/run and /api/evaluate with the request shapes they took before
definitions (admission/v1, ROUNDS-00A-L01).

A caller named a question by slug, and the entry and test cases came from
the stored question. Since ROUNDS-00A-L03 PR 4 both routes run definitions
only, as jobs, and the gates as shipped leave definitions at legacy, where
the execution keys act as off. So each older request below, from anyone,
answers 503 ``execution_disabled`` before the account check: no question
is read and nothing runs. test_definitions_enforce.py sends these shapes
at enforce, test_execution_scratch.py runs the jobs, and test_runner.py
covers what a run does."""
import pytest

PYTHON_TWO_SUM = (
    "def two_sum(nums, target):\n"
    "    seen = {}\n"
    "    for i, n in enumerate(nums):\n"
    "        if target - n in seen:\n"
    "            return [seen[target - n], i]\n"
    "        seen[n] = i\n"
)

FUNCTION_ENTRY = lambda name: {"kind": "function", "name": name}
CLASS_OPS_ENTRY = lambda cls: {"kind": "class_ops", "class": cls}

LRU_CODE = (
    "class Node:\n"
    "    def __init__(self, key=0, value=0):\n"
    "        self.key = key; self.value = value\n"
    "        self.next = None; self.previous = None\n"
    "class LRUCache:\n"
    "    def __init__(self, capacity):\n"
    "        self.capacity = capacity; self.cache = {}; self.order = []\n"
    "    def get(self, key):\n"
    "        if key not in self.cache: return -1\n"
    "        self.order.remove(key); self.order.append(key)\n"
    "        return self.cache[key]\n"
    "    def put(self, key, value):\n"
    "        if key in self.cache: self.order.remove(key)\n"
    "        self.cache[key] = value; self.order.append(key)\n"
    "        if len(self.cache) > self.capacity:\n"
    "            evict = self.order.pop(0); del self.cache[evict]\n"
)

# Each scenario: the stored question, then the request a caller sends.
SCENARIOS = {
    "run": (
        {"slug": "add-one", "entry": FUNCTION_ENTRY("solve"), "test_cases": []},
        "/api/run",
        {"question_slug": "add-one", "code": "def solve(x):\n    print('hi'); return x + 1", "language": "python", "input": {"x": 2}},
    ),
    "evaluate_all": (
        {
            "slug": "two-sum",
            "entry": FUNCTION_ENTRY("two_sum"),
            "test_cases": [
                {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1], "tags": ["basic"]},
                {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2], "tags": ["basic"]},
            ],
        },
        "/api/evaluate",
        {"question_slug": "two-sum", "code": PYTHON_TWO_SUM, "language": "python"},
    ),
    "evaluate_by_tag": (
        {
            "slug": "two-sum-tags",
            "entry": FUNCTION_ENTRY("two_sum"),
            "test_cases": [
                {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1], "tags": ["basic"]},
                {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2], "tags": ["edge"]},
            ],
        },
        "/api/evaluate",
        {"question_slug": "two-sum-tags", "code": PYTHON_TWO_SUM, "language": "python", "filter": {"tags": ["edge"]}},
    ),
    "evaluate_by_index": (
        {
            "slug": "two-sum-index",
            "entry": FUNCTION_ENTRY("two_sum"),
            "test_cases": [
                {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
                {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2]},
            ],
        },
        "/api/evaluate",
        {"question_slug": "two-sum-index", "code": PYTHON_TWO_SUM, "language": "python", "filter": {"indices": [0]}},
    ),
    "evaluate_class_ops": (
        {
            "slug": "counter",
            "entry": CLASS_OPS_ENTRY("Counter"),
            "test_cases": [{
                "input": {"ops": ["Counter", "inc", "inc"], "args": [[10], [2], [3]]},
                "expected": [None, 12, 15],
            }],
        },
        "/api/evaluate",
        {
            "question_slug": "counter",
            "code": (
                "class Counter:\n"
                "    def __init__(self, start): self.n = start\n"
                "    def inc(self, by): self.n += by; return self.n\n"
            ),
            "language": "python",
        },
    ),
    "evaluate_lru": (
        {
            "slug": "lru-cache",
            "entry": CLASS_OPS_ENTRY("LRUCache"),
            "test_cases": [{
                "input": {
                    "ops": ["LRUCache", "put", "put", "get", "put", "get", "get"],
                    "args": [[2], [1, 1], [2, 2], [1], [3, 3], [2], [3]],
                },
                "expected": [None, None, None, 1, None, -1, 3],
            }],
        },
        "/api/evaluate",
        {"question_slug": "lru-cache", "code": LRU_CODE, "language": "python"},
    ),
    "evaluate_failed_case": (
        {
            "slug": "two-sum-wrong",
            "entry": FUNCTION_ENTRY("two_sum"),
            "test_cases": [{"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]}],
        },
        "/api/evaluate",
        {"question_slug": "two-sum-wrong", "code": "def two_sum(nums, target): return [0, 0]", "language": "python"},
    ),
    "evaluate_unknown_kind": (
        {"slug": "quantum", "entry": {"kind": "quantum"}, "test_cases": []},
        "/api/evaluate",
        {"question_slug": "quantum", "code": "def f(): pass", "language": "python"},
    ),
    "run_missing_name": (
        {"slug": "nameless", "entry": {"kind": "function"}, "test_cases": []},
        "/api/run",
        {"question_slug": "nameless", "code": "def f(): pass", "language": "python", "input": {}},
    ),
}


# ---- expected-deny controls (#8) ---------------------------------------------


@pytest.fixture
def ran(monkeypatch):
    """Every run_one call the runner router makes."""
    from routers import runner as runner_router

    calls = []
    real = runner_router.run_one

    def spy(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    monkeypatch.setattr(runner_router, "run_one", spy)
    return calls


CALLERS = {"anonymous": {}, "a bearer pocketbase rejects": {"Authorization": "Bearer someone-else"}}


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_an_older_request_from_anyone_is_turned_off_before_anything_runs(client, signed_in, questions, ran,
                                                                          scenario):
    question, path, body = SCENARIOS[scenario]
    questions.add(**question)
    for headers in (*CALLERS.values(), signed_in):
        res = client.post(path, json=body, headers=headers)
        assert res.status_code == 503, res.text
        assert res.json()["code"] == "execution_disabled"
    assert ran == []
    assert questions.calls == []
