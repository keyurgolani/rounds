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


def test_run_returns_stdout_and_return_value(client):
    code = "def solve(x):\n    print('hi'); return x + 1"
    res = client.post("/api/run", json={
        "code": code,
        "language": "python",
        "entry": FUNCTION_ENTRY("solve"),
        "input": {"x": 2},
    })
    assert res.status_code == 200
    data = res.json()
    assert data["stdout"].strip() == "hi"
    assert data["return_value"] == 3
    assert data["error"] is None


def test_evaluate_no_filter_runs_all(client):
    res = client.post("/api/evaluate", json={
        "code": PYTHON_TWO_SUM,
        "language": "python",
        "entry": FUNCTION_ENTRY("two_sum"),
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1], "tags": ["basic"]},
            {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2], "tags": ["basic"]},
        ],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] == 2 and data["failed"] == 0


def test_evaluate_filter_by_tag(client):
    res = client.post("/api/evaluate", json={
        "code": PYTHON_TWO_SUM,
        "language": "python",
        "entry": FUNCTION_ENTRY("two_sum"),
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1], "tags": ["basic"]},
            {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2], "tags": ["edge"]},
        ],
        "filter": {"tags": ["edge"]},
    })
    assert [r["index"] for r in res.json()["results"]] == [1]


def test_evaluate_filter_by_indices(client):
    res = client.post("/api/evaluate", json={
        "code": PYTHON_TWO_SUM,
        "language": "python",
        "entry": FUNCTION_ENTRY("two_sum"),
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
            {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2]},
        ],
        "filter": {"indices": [0]},
    })
    assert [r["index"] for r in res.json()["results"]] == [0]


def test_evaluate_class_ops_counter(client):
    code = (
        "class Counter:\n"
        "    def __init__(self, start): self.n = start\n"
        "    def inc(self, by): self.n += by; return self.n\n"
    )
    res = client.post("/api/evaluate", json={
        "code": code,
        "language": "python",
        "entry": CLASS_OPS_ENTRY("Counter"),
        "test_cases": [{
            "input": {"ops": ["Counter", "inc", "inc"], "args": [[10], [2], [3]]},
            "expected": [None, 12, 15],
        }],
    })
    assert res.json()["passed"] == 1


def test_evaluate_lru_with_helper_node_class_regression(client):
    """Original LRU bug: Node helper class caused dispatch to misroute.
    With explicit entry.class = LRUCache, helper classes are invisible
    to dispatch."""
    code = (
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
    res = client.post("/api/evaluate", json={
        "code": code,
        "language": "python",
        "entry": CLASS_OPS_ENTRY("LRUCache"),
        "test_cases": [{
            "input": {
                "ops": ["LRUCache", "put", "put", "get", "put", "get", "get"],
                "args": [[2], [1, 1], [2, 2], [1], [3, 3], [2], [3]],
            },
            "expected": [None, None, None, 1, None, -1, 3],
        }],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] == 1, data["results"]


def test_evaluate_records_failed_case(client):
    code = "def two_sum(nums, target): return [0, 0]"  # wrong answer
    res = client.post("/api/evaluate", json={
        "code": code,
        "language": "python",
        "entry": FUNCTION_ENTRY("two_sum"),
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
        ],
    })
    data = res.json()
    assert data["passed"] == 0 and data["failed"] == 1
    assert data["results"][0]["output"] == [0, 0]


def test_evaluate_returns_400_on_unknown_kind(client):
    res = client.post("/api/evaluate", json={
        "code": "def f(): pass",
        "language": "python",
        "entry": {"kind": "quantum"},
        "test_cases": [],
    })
    # Pydantic validation rejects the unknown kind at the API boundary.
    assert res.status_code == 422


def test_run_returns_validate_error_on_missing_name(client):
    res = client.post("/api/run", json={
        "code": "def f(): pass",
        "language": "python",
        "entry": {"kind": "function"},  # name missing
        "input": {},
    })
    data = res.json()
    assert data["error"] and "missing 'name'" in data["error"]
