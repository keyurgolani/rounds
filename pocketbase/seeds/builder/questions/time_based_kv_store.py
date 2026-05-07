"""Time Based Key-Value Store — Medium. LeetCode 981.

Design TimeMap supporting set(key, value, timestamp) and get(key, timestamp)
which returns the value with the largest timestamp_prev <= timestamp.
Timestamps for set are strictly increasing per key, so per-key append is O(1)
and get is a binary search."""
from builder.registry import register


PAYLOAD = {
    "title": "Time Based Key-Value Store",
    "difficulty": "Medium",
    "description": (
        "Design a time-based key-value data structure that can store multiple values for the same "
        "key at different timestamps and retrieve the key's value at a certain timestamp.\n\n"
        "Implement the `TimeMap` class:\n"
        "- `TimeMap()` — initializes the object.\n"
        "- `void set(String key, String value, int timestamp)` — stores the key `key` with the value "
        "`value` at the given time `timestamp`.\n"
        "- `String get(String key, int timestamp)` — returns a value such that `set` was previously "
        "called with `timestamp_prev <= timestamp`. If there are multiple such values, it returns the "
        "value associated with the **largest** `timestamp_prev`. If there are no values, it returns `\"\"`.\n\n"
        "All timestamps for `set` on a given key are **strictly increasing**.\n\n"
        "**Example 1:**\n"
        "```\n"
        "Input:\n"
        "  ops  = [\"TimeMap\", \"set\", \"get\",      \"get\",      \"set\", \"get\",      \"get\"]\n"
        "  args = [[],         [\"foo\",\"bar\",1], [\"foo\",1], [\"foo\",3], [\"foo\",\"bar2\",4], [\"foo\",4], [\"foo\",5]]\n"
        "Output: [null, null, \"bar\", \"bar\", null, \"bar2\", \"bar2\"]\n"
        "```\n\n"
        "**Example 2:**\n"
        "```\n"
        "TimeMap tm = new TimeMap();\n"
        "tm.set(\"love\", \"high\", 10);\n"
        "tm.set(\"love\", \"low\",  20);\n"
        "tm.get(\"love\", 5);   // \"\"      (nothing before t=10)\n"
        "tm.get(\"love\", 10);  // \"high\"  (exact match)\n"
        "tm.get(\"love\", 15);  // \"high\"  (floor)\n"
        "tm.get(\"love\", 20);  // \"low\"   (exact match)\n"
        "tm.get(\"love\", 25);  // \"low\"   (latest)\n"
        "```"
    ),
    "hints": [
        "Bucket the data per key: `dict[key] -> list of (timestamp, value)`. Different keys never interact, so they can be searched independently.",
        "Because `set` timestamps are strictly increasing per key, you can simply append to that key's list in O(1) — the list stays sorted for free.",
        "For `get`, do a binary search on the per-key list for the largest timestamp `<= t`. In Python, `bisect_right(times, t) - 1` gives that index.",
        "If `bisect_right` returns 0, no timestamp is small enough — return the empty string `\"\"`.",
        "Alternative: use a TreeMap (Java) / SortedDict (Python) per key and call `floorKey(t)`. Same asymptotics, less manual code, but typically larger constant factor.",
    ],
    "constraints": [
        "1 <= key.length, value.length <= 100",
        "1 <= timestamp <= 10^7",
        "All timestamps `timestamp` of `set` are strictly increasing for a given key. At most 2*10^5 calls in total.",
    ],
    "starter_code": {
        "python": (
            "class TimeMap:\n"
            "    def __init__(self):\n"
            "        pass\n"
            "    def set(self, key, value, timestamp):\n"
            "        pass\n"
            "    def get(self, key, timestamp):\n"
            "        pass"
        ),
        "javascript": (
            "class TimeMap {\n"
            "    constructor() { /* ... */ }\n"
            "    set(key, value, timestamp) { /* ... */ }\n"
            "    get(key, timestamp) { /* ... */ }\n"
            "}"
        ),
        "java": (
            "class TimeMap {\n"
            "    public TimeMap() {}\n"
            "    public void set(String key, String value, int timestamp) {}\n"
            "    public String get(String key, int timestamp) { return \"\"; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    tm = TimeMap()\n"
            "    tm.set('foo', 'bar', 1)\n"
            "    print(tm.get('foo', 1))   # 'bar'\n"
            "    print(tm.get('foo', 3))   # 'bar'\n"
            "    tm.set('foo', 'bar2', 4)\n"
            "    print(tm.get('foo', 4))   # 'bar2'\n"
            "    print(tm.get('foo', 5))   # 'bar2'"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {
            "input": {
                "ops": ["TimeMap", "set", "get", "get", "set", "get", "get"],
                "args": [[], ["foo", "bar", 1], ["foo", 1], ["foo", 3],
                          ["foo", "bar2", 4], ["foo", 4], ["foo", 5]],
            },
            "expected": [None, None, "bar", "bar", None, "bar2", "bar2"],
            "description": "Classic LeetCode 981 example sequence",
            "tags": ["basic"],
        },
        {
            "input": {"ops": ["TimeMap", "get"], "args": [[], ["foo", 1]]},
            "expected": [None, ""],
            "description": "Get on empty map returns empty string",
            "tags": ["edge"],
        },
        {
            "input": {
                "ops": ["TimeMap", "set", "get", "get"],
                "args": [[], ["k", "v", 5], ["k", 4], ["k", 5]],
            },
            "expected": [None, None, "", "v"],
            "description": "Get before any matching timestamp returns \"\"; exact match works",
            "tags": ["edge"],
        },
        {
            "input": {
                "ops": ["TimeMap", "set", "set", "get", "get", "get"],
                "args": [[], ["a", "first", 10], ["a", "second", 20],
                          ["a", 14], ["a", 19], ["a", 20]],
            },
            "expected": [None, None, None, "first", "first", "second"],
            "description": "Get strictly between two sets; boundary at second timestamp",
            "tags": ["basic"],
        },
        {
            "input": {
                "ops": ["TimeMap", "set", "set", "set", "set",
                        "get", "get", "get", "get", "get"],
                "args": [[], ["x", "x1", 1], ["x", "x2", 5],
                          ["y", "y1", 2], ["y", "y2", 8],
                          ["x", 4], ["x", 7], ["y", 1], ["y", 5], ["y", 100]],
            },
            "expected": [None, None, None, None, None,
                          "x1", "x2", "", "y1", "y2"],
            "description": "Multiple keys do not interfere",
            "tags": ["basic"],
        },
        {
            "input": {
                "ops": ["TimeMap", "set", "get", "get"],
                "args": [[], ["k", "v", 100], ["k", 100], ["k", 99]],
            },
            "expected": [None, None, "v", ""],
            "description": "Boundary: equal timestamp matches; one less misses",
            "tags": ["edge"],
        },
        {
            "input": {
                "ops": ["TimeMap"]
                        + ["set"] * 6
                        + ["get"] * 8,
                "args": [[],
                         ["k", "v1", 1], ["k", "v2", 2], ["k", "v3", 4],
                         ["k", "v4", 8], ["k", "v5", 16], ["k", "v6", 32],
                         ["k", 0], ["k", 1], ["k", 3], ["k", 7],
                         ["k", 15], ["k", 31], ["k", 32], ["k", 1000]],
            },
            "expected": [None, None, None, None, None, None, None,
                          "", "v1", "v2", "v3", "v4", "v5", "v6", "v6"],
            "description": "Long sequence: floor lookups across a doubling timeline",
            "tags": ["stress"],
        },
        {
            "input": {
                "ops": ["TimeMap", "set", "set", "get", "get", "get"],
                "args": [[], ["love", "high", 10], ["love", "low", 20],
                          ["love", 5], ["love", 10], ["love", 25]],
            },
            "expected": [None, None, None, "", "high", "low"],
            "description": "Below min, exact match, above max",
            "tags": ["edge"],
        },
    ],
    "solutions": [
        {
            "title": "Per-Key Sorted List + Binary Search (Optimal)",
            "time_complexity": "O(1) set, O(log n) get (n = entries for that key)",
            "space_complexity": "O(N) total entries across all keys",
            "description": (
                "Maintain `store: dict[key] -> (times[], values[])`. Because `set` is called with strictly "
                "increasing timestamps per key, each `set` is a plain append — O(1) and the list stays "
                "sorted automatically. `get` does `bisect_right(times, t) - 1` to find the largest "
                "`timestamp_prev <= t`; if the index is negative, return `\"\"`."
            ),
            "code": {
                "python": (
                    "from bisect import bisect_right\n"
                    "from collections import defaultdict\n\n"
                    "class TimeMap:\n"
                    "    def __init__(self):\n"
                    "        self.store = defaultdict(lambda: ([], []))\n"
                    "    def set(self, key, value, timestamp):\n"
                    "        times, values = self.store[key]\n"
                    "        times.append(timestamp)\n"
                    "        values.append(value)\n"
                    "    def get(self, key, timestamp):\n"
                    "        if key not in self.store:\n"
                    "            return \"\"\n"
                    "        times, values = self.store[key]\n"
                    "        idx = bisect_right(times, timestamp) - 1\n"
                    "        return values[idx] if idx >= 0 else \"\""
                ),
                "javascript": (
                    "class TimeMap {\n"
                    "    constructor() { this.store = new Map(); }\n"
                    "    set(key, value, timestamp) {\n"
                    "        if (!this.store.has(key)) this.store.set(key, { times: [], values: [] });\n"
                    "        const e = this.store.get(key);\n"
                    "        e.times.push(timestamp);\n"
                    "        e.values.push(value);\n"
                    "    }\n"
                    "    get(key, timestamp) {\n"
                    "        if (!this.store.has(key)) return \"\";\n"
                    "        const { times, values } = this.store.get(key);\n"
                    "        let lo = 0, hi = times.length;\n"
                    "        while (lo < hi) {\n"
                    "            const mid = (lo + hi) >> 1;\n"
                    "            if (times[mid] <= timestamp) lo = mid + 1; else hi = mid;\n"
                    "        }\n"
                    "        return lo === 0 ? \"\" : values[lo - 1];\n"
                    "    }\n"
                    "}"
                ),
                "java": (
                    "class TimeMap {\n"
                    "    private final Map<String, List<int[]>> times = new HashMap<>();\n"
                    "    private final Map<String, List<String>> values = new HashMap<>();\n"
                    "    public TimeMap() {}\n"
                    "    public void set(String key, String value, int timestamp) {\n"
                    "        times.computeIfAbsent(key, k -> new ArrayList<>()).add(new int[]{timestamp});\n"
                    "        values.computeIfAbsent(key, k -> new ArrayList<>()).add(value);\n"
                    "    }\n"
                    "    public String get(String key, int timestamp) {\n"
                    "        List<int[]> ts = times.get(key);\n"
                    "        if (ts == null) return \"\";\n"
                    "        int lo = 0, hi = ts.size();\n"
                    "        while (lo < hi) {\n"
                    "            int mid = (lo + hi) >>> 1;\n"
                    "            if (ts.get(mid)[0] <= timestamp) lo = mid + 1; else hi = mid;\n"
                    "        }\n"
                    "        return lo == 0 ? \"\" : values.get(key).get(lo - 1);\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Per-Key Sorted Map (TreeMap / SortedDict)",
            "time_complexity": "O(log n) for both set and get",
            "space_complexity": "O(N) total entries across all keys",
            "description": (
                "If the language ships a balanced sorted map (Java `TreeMap`, C++ `std::map`, Python "
                "`sortedcontainers.SortedDict`), use one per key and call `floorKey(timestamp)`. This is "
                "the cleanest formulation and works even if timestamps weren't strictly increasing — the "
                "tree handles arbitrary insertion order."
            ),
            "code": {
                "java": (
                    "class TimeMap {\n"
                    "    private final Map<String, TreeMap<Integer, String>> store = new HashMap<>();\n"
                    "    public TimeMap() {}\n"
                    "    public void set(String key, String value, int timestamp) {\n"
                    "        store.computeIfAbsent(key, k -> new TreeMap<>()).put(timestamp, value);\n"
                    "    }\n"
                    "    public String get(String key, int timestamp) {\n"
                    "        TreeMap<Integer, String> tm = store.get(key);\n"
                    "        if (tm == null) return \"\";\n"
                    "        Map.Entry<Integer, String> e = tm.floorEntry(timestamp);\n"
                    "        return e == null ? \"\" : e.getValue();\n"
                    "    }\n"
                    "}"
                ),
                "python": (
                    "from bisect import bisect_right\n"
                    "from collections import defaultdict\n\n"
                    "class TimeMap:\n"
                    "    def __init__(self):\n"
                    "        self.times = defaultdict(list)\n"
                    "        self.values = defaultdict(list)\n"
                    "    def set(self, key, value, timestamp):\n"
                    "        self.times[key].append(timestamp)\n"
                    "        self.values[key].append(value)\n"
                    "    def get(self, key, timestamp):\n"
                    "        if key not in self.times:\n"
                    "            return \"\"\n"
                    "        idx = bisect_right(self.times[key], timestamp) - 1\n"
                    "        if idx < 0:\n"
                    "            return \"\"\n"
                    "        return self.values[key][idx]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: 'largest timestamp_prev <= t' is a floor-key query — sorted structure required.",
        "2. Notice the per-key isolation: different keys never compete, so bucket them into `dict[key] -> per-key store`.",
        "3. Exploit the strictly-increasing-per-key constraint: `set` becomes O(1) append, no insertion shift.",
        "4. For `get`, binary-search the per-key timestamp list with `bisect_right(times, t) - 1`.",
        "5. Handle the two empty cases: key absent → `\"\"`; key present but no timestamp ≤ t → `\"\"`.",
        "6. If timestamps could be unordered (variant), swap to TreeMap/SortedDict — same API, O(log n) set.",
    ],
    "tips": [
        "`bisect_right(arr, t) - 1` is the canonical floor-index idiom. Don't mix it up with `bisect_left`, which gives ceiling-style behaviour and breaks on exact matches.",
        "Java `TreeMap.floorEntry(t)` is the textbook one-liner — name-drop it in interviews.",
        "Don't forget the empty-string return: the contract says `\"\"`, not `null`. Tests catch this.",
        "Per-key isolation matters: a single global sorted list of (timestamp, key, value) makes get O(n) — wrong.",
        "Common follow-up: 'what if timestamps aren't strictly increasing?' Switch to SortedDict / TreeMap so set is also O(log n).",
        "Common follow-up: 'support delete.' TreeMap handles this directly; sorted list needs a tombstone or shift.",
    ],
    "companies": ["Google", "Amazon", "Meta", "Bloomberg", "Microsoft"],
    "topics": ["Binary Search", "Hash Table", "Design", "Sorted Container", "TreeMap"],
    "time_complexity": "O(1) set, O(log n) get",
    "space_complexity": "O(N)",
}


def REFERENCE(input):
    """Class-ops driver: replay the operation sequence."""
    from bisect import bisect_right
    from collections import defaultdict

    class TimeMap:
        def __init__(self):
            self.store = defaultdict(lambda: ([], []))

        def set(self, key, value, timestamp):
            times, values = self.store[key]
            times.append(timestamp)
            values.append(value)

        def get(self, key, timestamp):
            if key not in self.store:
                return ""
            times, values = self.store[key]
            idx = bisect_right(times, timestamp) - 1
            return values[idx] if idx >= 0 else ""

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "TimeMap":
            instance = TimeMap()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


# Add the entry field for class_ops dispatch
PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "TimeMap",
    "constructor": {"params": []},
    "methods": [
        {"name": "set",
         "params": [
             {"name": "key", "type": "string"},
             {"name": "value", "type": "string"},
             {"name": "timestamp", "type": "int"},
         ],
         "returns": "any"},
        {"name": "get",
         "params": [
             {"name": "key", "type": "string"},
             {"name": "timestamp", "type": "int"},
         ],
         "returns": "string"},
    ],
}


register(PAYLOAD, REFERENCE)
