"""/api/run and /api/evaluate (admission/v1, ROUNDS-00A-L01).

Signed-in callers name a question by slug; the entry and test cases come
from the stored question. Each request also runs anonymously as an
expected-deny control: 401 ``unauthenticated``, and nothing runs."""
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


def _post(client, questions, headers, scenario):
    question, path, body = SCENARIOS[scenario]
    questions.add(**question)
    return client.post(path, json=body, headers=headers)


def test_run_returns_stdout_and_return_value(client, signed_in, questions):
    res = _post(client, questions, signed_in, "run")
    assert res.status_code == 200
    data = res.json()
    assert data["stdout"].strip() == "hi"
    assert data["return_value"] == 3
    assert data["error"] is None


def test_evaluate_no_filter_runs_all(client, signed_in, questions):
    res = _post(client, questions, signed_in, "evaluate_all")
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] == 2 and data["failed"] == 0


def test_evaluate_filter_by_tag(client, signed_in, questions):
    res = _post(client, questions, signed_in, "evaluate_by_tag")
    assert [r["index"] for r in res.json()["results"]] == [1]


def test_evaluate_filter_by_indices(client, signed_in, questions):
    res = _post(client, questions, signed_in, "evaluate_by_index")
    assert [r["index"] for r in res.json()["results"]] == [0]


def test_evaluate_class_ops_counter(client, signed_in, questions):
    res = _post(client, questions, signed_in, "evaluate_class_ops")
    assert res.json()["passed"] == 1


def test_evaluate_lru_with_helper_node_class_regression(client, signed_in, questions):
    """Original LRU bug: Node helper class caused dispatch to misroute.
    With explicit entry.class = LRUCache, helper classes are invisible
    to dispatch."""
    res = _post(client, questions, signed_in, "evaluate_lru")
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] == 1, data["results"]


def test_evaluate_records_failed_case(client, signed_in, questions):
    res = _post(client, questions, signed_in, "evaluate_failed_case")
    data = res.json()
    assert data["passed"] == 0 and data["failed"] == 1
    assert data["results"][0]["output"] == [0, 0]


def test_evaluate_returns_400_on_unknown_kind(client, signed_in, questions):
    # The stored entry's kind isn't one the runner knows, so nothing runs.
    # (The name predates the check; the answer has always been 422.)
    res = _post(client, questions, signed_in, "evaluate_unknown_kind")
    assert res.status_code == 422
    assert res.json()["code"] == "invalid_request"


def test_run_returns_validate_error_on_missing_name(client, signed_in, questions):
    res = _post(client, questions, signed_in, "run_missing_name")
    data = res.json()
    assert data["error"] and "missing 'name'" in data["error"]


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


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_anonymous_request_is_denied_before_anything_runs(client, questions, ran, scenario):
    res = _post(client, questions, {}, scenario)
    assert res.status_code == 401
    assert res.json()["code"] == "unauthenticated"
    assert ran == []
    assert questions.calls == []


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_a_bearer_pocketbase_rejects_is_denied_before_anything_runs(client, signed_in, questions, ran, scenario):
    res = _post(client, questions, {"Authorization": "Bearer someone-else"}, scenario)
    assert res.status_code == 401
    assert ran == []
    assert questions.calls == []


def test_the_signed_in_run_reads_the_question_with_the_callers_token(client, signed_in, questions, ran):
    res = _post(client, questions, signed_in, "run")
    assert res.status_code == 200
    ((token, path, params),) = questions.calls
    assert token == signed_in["Authorization"].split(" ", 1)[1]
    assert params == {"filter": "slug='add-one'", "perPage": 1}
    assert len(ran) == 1
