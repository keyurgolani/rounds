"""Date Map (Floor Key Lookup) — Medium. BST / Binary Search.

Given timestamped key-value pairs, support get(key) returning the
value at the largest key <= the requested key. Sorted-list +
binary search is the canonical answer; treemap if mutations are common."""
from builder.registry import register


PAYLOAD = {
    "title": "Date Map (Floor Key Lookup)",
    "difficulty": "Medium",
    "description": (
        "Implement a `DateMap` data structure with two operations:\n"
        "- `set(key, value)` — store a key-value pair (keys are integers, e.g. UNIX timestamps).\n"
        "- `get(key)` — return the value associated with `key`. If no exact match, return the value "
        "associated with the **largest key smaller than or equal to** the requested key. If no such key "
        "exists, return `null` (Python: `None`).\n\n"
        "**Example sequence:**\n"
        "```\n"
        "m = DateMap()\n"
        "m.set(10, 'A')      # store at t=10\n"
        "m.set(20, 'B')      # store at t=20\n"
        "m.get(15)           # → 'A' (floor of 15 is 10)\n"
        "m.get(20)           # → 'B' (exact match)\n"
        "m.get(5)            # → null (nothing at or before 5)\n"
        "```"
    ),
    "hints": [
        "If keys are inserted in order (or rarely deleted), keep a sorted list and binary-search on `get`.",
        "If inserts are arbitrary, a TreeMap (Java)/SortedDict (Python `sortedcontainers`) gives O(log n) for both ops without manual maintenance.",
        "Pure dict + linear scan is O(n) per get — wrong choice for n = 10⁵.",
        "Updating the value at an existing key replaces (not appends).",
        "Edge cases: empty map, key smaller than every stored key, key larger than every stored key, exact-match hit.",
    ],
    "constraints": [
        "1 <= total operations <= 10⁵",
        "Keys: 32-bit integer range",
    ],
    "starter_code": {
        "python": (
            "class DateMap:\n"
            "    def __init__(self):\n"
            "        pass\n"
            "    def set(self, key, value):\n"
            "        pass\n"
            "    def get(self, key):\n"
            "        pass"
        ),
        "javascript": (
            "class DateMap {\n"
            "    constructor() { /* ... */ }\n"
            "    set(key, value) { /* ... */ }\n"
            "    get(key) { /* ... */ }\n"
            "}"
        ),
        "java": (
            "class DateMap {\n"
            "    public DateMap() {}\n"
            "    public void set(int key, String value) {}\n"
            "    public String get(int key) { return null; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    m = DateMap()\n"
            "    m.set(10, 'A')\n"
            "    m.set(20, 'B')\n"
            "    print(m.get(15))  # 'A'"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["DateMap", "set", "set", "get", "get", "get"],
                    "args": [[], [10, "A"], [20, "B"], [15], [20], [5]]},
         "expected": [None, None, None, "A", "B", None],
         "description": "Standard sequence", "tags": ["basic"]},
        {"input": {"ops": ["DateMap", "get"], "args": [[], [100]]},
         "expected": [None, None],
         "description": "Empty map — get returns None", "tags": ["edge"]},
        {"input": {"ops": ["DateMap", "set", "set", "get"],
                    "args": [[], [5, "old"], [5, "new"], [5]]},
         "expected": [None, None, None, "new"],
         "description": "Repeated set on same key replaces", "tags": ["edge"]},
        {"input": {"ops": ["DateMap", "set", "get", "get"],
                    "args": [[], [10, "A"], [10000], [-1]]},
         "expected": [None, None, "A", None],
         "description": "Above max returns latest; below min returns None", "tags": ["edge"]},
        {"input": {"ops": ["DateMap"] + ["set"] * 5 + ["get"] * 6,
                    "args": [[], [10, "v10"], [20, "v20"], [30, "v30"], [40, "v40"], [50, "v50"],
                             [10], [25], [50], [55], [9], [40]]},
         "expected": [None, None, None, None, None, None, "v10", "v20", "v50", "v50", None, "v40"],
         "description": "Mixed gets across the range", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Sorted List + Binary Search (Optimal)",
            "time_complexity": "O(log n) get, O(n) set worst-case (insertion shift)",
            "space_complexity": "O(n)",
            "description": (
                "Maintain a sorted list of keys plus a parallel dict `key → value`. `get` does bisect_right "
                "on the keys to find the floor. `set` inserts in sorted order if the key is new. For "
                "mostly-append insertion patterns (timestamps in order), this is amortised O(1) for set."
            ),
            "code": {
                "python": (
                    "from bisect import bisect_right, insort\n\n"
                    "class DateMap:\n"
                    "    def __init__(self):\n"
                    "        self._keys = []\n"
                    "        self._values = {}\n"
                    "    def set(self, key, value):\n"
                    "        if key not in self._values:\n"
                    "            insort(self._keys, key)\n"
                    "        self._values[key] = value\n"
                    "    def get(self, key):\n"
                    "        idx = bisect_right(self._keys, key) - 1\n"
                    "        if idx < 0:\n"
                    "            return None\n"
                    "        return self._values[self._keys[idx]]"
                ),
                "javascript": (
                    "class DateMap {\n"
                    "    constructor() { this.keys = []; this.values = new Map(); }\n"
                    "    set(key, value) {\n"
                    "        if (!this.values.has(key)) {\n"
                    "            // binary-search insertion point\n"
                    "            let lo = 0, hi = this.keys.length;\n"
                    "            while (lo < hi) { const mid = (lo + hi) >> 1; if (this.keys[mid] < key) lo = mid + 1; else hi = mid; }\n"
                    "            this.keys.splice(lo, 0, key);\n"
                    "        }\n"
                    "        this.values.set(key, value);\n"
                    "    }\n"
                    "    get(key) {\n"
                    "        let lo = 0, hi = this.keys.length;\n"
                    "        while (lo < hi) { const mid = (lo + hi) >> 1; if (this.keys[mid] <= key) lo = mid + 1; else hi = mid; }\n"
                    "        if (lo === 0) return null;\n"
                    "        return this.values.get(this.keys[lo - 1]);\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "TreeMap (Native Sorted Container)",
            "time_complexity": "O(log n) for both set and get",
            "space_complexity": "O(n)",
            "description": (
                "If your language has a built-in sorted/red-black-tree map (Java `TreeMap`, C++ `std::map`, "
                "Python `sortedcontainers.SortedDict`), use it. Java's `floorKey(k)` is exactly the API. "
                "Beats hand-rolled bisection on arbitrary insert order."
            ),
            "code": {
                "java": (
                    "class DateMap {\n"
                    "    private final TreeMap<Integer, String> map = new TreeMap<>();\n"
                    "    public void set(int key, String value) { map.put(key, value); }\n"
                    "    public String get(int key) {\n"
                    "        Map.Entry<Integer, String> e = map.floorEntry(key);\n"
                    "        return e == null ? null : e.getValue();\n"
                    "    }\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Spot the operation: 'largest key ≤ requested' is a floor lookup. Sorted structure required.",
        "2. State the brute force baseline (linear scan) and reject it for n = 10⁵.",
        "3. Pick the structure: TreeMap if available; sorted list + bisect otherwise.",
        "4. `set` decision: append-amortised if timestamps come in order, else true O(log n) with TreeMap.",
        "5. `get` is binary search for `bisect_right(keys, key) - 1` — that gives the floor index.",
        "6. Edge cases: empty map, key below all (return None), key above all (return latest), exact hit.",
    ],
    "tips": [
        "Java `TreeMap.floorEntry(k)` is the textbook API for this exact problem — name-drop it if you're in Java.",
        "Python's `sortedcontainers.SortedDict` has `irange()` and `bisect_left/right`; if your environment has it, prefer it over manual bisect.",
        "Don't use a plain dict + scan — that's O(n) per get and silently fails the constraint at scale.",
        "Common follow-up: 'ceiling instead of floor.' Use `bisect_left` and check the index directly (no -1).",
        "Common follow-up: 'range query: all values in [low, high].' Bisect both ends, slice the keys list.",
    ],
    "companies": ["Amazon", "Bloomberg", "LinkedIn"],
    "topics": ["Binary Search", "TreeMap", "Sorted Container", "Design"],
    "time_complexity": "O(log n)",
    "space_complexity": "O(n)",
}


def REFERENCE(input):
    """Class-ops driver: replay the operation sequence."""
    from bisect import bisect_right, insort

    class DateMap:
        def __init__(self):
            self._keys = []
            self._values = {}

        def set(self, key, value):
            if key not in self._values:
                insort(self._keys, key)
            self._values[key] = value

        def get(self, key):
            idx = bisect_right(self._keys, key) - 1
            if idx < 0:
                return None
            return self._values[self._keys[idx]]

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "DateMap":
            instance = DateMap()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


# Add the entry field for class_ops dispatch
PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "DateMap",
    "constructor": {"params": []},
    "methods": [
        {"name": "set", "params": [{"name": "key", "type": "int"}, {"name": "value", "type": "any"}],
         "returns": "any"},
        {"name": "get", "params": [{"name": "key", "type": "int"}], "returns": "any"},
    ],
}


register(PAYLOAD, REFERENCE)
