"""SetWithExpiry — Medium. Logical & Maintainable / Code Review.

A set whose entries auto-expire. Implement add(key, ttl), contains(key)
with lazy purging. The senior signal is the testability discussion:
inject a clock so 'expiry' isn't gated on real time."""
from builder.registry import register


PAYLOAD = {
    "title": "Set With Expiry",
    "difficulty": "Medium",
    "description": (
        "Implement a `SetWithExpiry` data structure with these operations:\n"
        "- `add(key, ttl_ms)` — insert `key` with time-to-live `ttl_ms` milliseconds.\n"
        "- `contains(key)` — return whether `key` is currently present (i.e. inserted and not yet expired).\n"
        "- `tick(now_ms)` — advance the virtual clock to `now_ms`. Used by tests to make time deterministic.\n\n"
        "**Test framing:** rather than relying on real wall-clock, the harness uses an injected clock — "
        "every test sequence starts at `now = 0` and advances the clock via `tick`.\n\n"
        "**Example sequence:**\n"
        "```\n"
        "s = SetWithExpiry()\n"
        "s.add('a', 100)        # 'a' lives until t=100\n"
        "s.contains('a')        # True\n"
        "s.tick(50)\n"
        "s.contains('a')        # True\n"
        "s.tick(150)\n"
        "s.contains('a')        # False (expired)\n"
        "```"
    ),
    "hints": [
        "Store `key → expiry_time`. `contains` returns True iff the key is present AND `expiry_time > now`.",
        "Lazy purge: do nothing on `tick`; check expiry on access. O(1) ops, but stale entries linger in memory.",
        "Eager purge: on `tick`, drop everything expired before now. O(expired) work; bounded memory.",
        "Hybrid: lazy on access + a min-heap keyed on expiry, popped opportunistically on `add`.",
        "Concurrency (the canonical bar-raising thread): real production needs synchronisation around the map and the clock.",
        "Test gotcha: the buggy version of this problem — the one used in the code-review framing — purges only on `add` and lets `contains` return stale `True`. Surface that.",
    ],
    "constraints": [
        "1 <= total operations <= 10⁵",
    ],
    "starter_code": {
        "python": (
            "class SetWithExpiry:\n"
            "    def __init__(self): pass\n"
            "    def add(self, key, ttl_ms): pass\n"
            "    def contains(self, key): pass\n"
            "    def tick(self, now_ms): pass"
        ),
        "javascript": (
            "class SetWithExpiry {\n"
            "    constructor() {}\n"
            "    add(key, ttlMs) {}\n"
            "    contains(key) {}\n"
            "    tick(nowMs) {}\n"
            "}"
        ),
        "java": (
            "class SetWithExpiry {\n"
            "    public SetWithExpiry() {}\n"
            "    public void add(String key, long ttlMs) {}\n"
            "    public boolean contains(String key) { return false; }\n"
            "    public void tick(long nowMs) {}\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    s = SetWithExpiry()\n"
            "    s.add('a', 100)\n"
            "    print(s.contains('a'))\n"
            "    s.tick(150)\n"
            "    print(s.contains('a'))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["SetWithExpiry", "add", "contains", "tick", "contains", "tick", "contains"],
                    "args": [[], ["a", 100], ["a"], [50], ["a"], [150], ["a"]]},
         "expected": [None, None, True, None, True, None, False],
         "description": "Add, half-life check, expiry", "tags": ["basic"]},
        {"input": {"ops": ["SetWithExpiry", "contains"],
                    "args": [[], ["x"]]},
         "expected": [None, False],
         "description": "Contains on missing key", "tags": ["edge"]},
        {"input": {"ops": ["SetWithExpiry", "add", "add", "contains"],
                    "args": [[], ["k", 50], ["k", 200], ["k"]]},
         "expected": [None, None, None, True],
         "description": "Re-add extends TTL (or refreshes — pick one and document)",
         "tags": ["tricky"]},
        {"input": {"ops": ["SetWithExpiry", "add", "tick", "add", "contains", "contains"],
                    "args": [[], ["a", 50], [100], ["b", 50], ["a"], ["b"]]},
         "expected": [None, None, None, None, False, True],
         "description": "Mixed add/expire/add — old expired, new alive",
         "tags": ["basic"]},
        {"input": {"ops": ["SetWithExpiry", "add", "tick", "contains"],
                    "args": [[], ["a", 0], [0], ["a"]]},
         "expected": [None, None, None, False],
         "description": "TTL=0 is already expired", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Hash Map + Lazy Purge (Optimal Read Path)",
            "time_complexity": "O(1) for add and contains (amortised)",
            "space_complexity": "O(N) for live + expired-but-not-purged",
            "description": (
                "Store `key → expiry_ms`. `add` writes `now + ttl`. `contains` checks both presence and "
                "`expiry > now`; if expired, evict in place and return False. The map can hold expired "
                "entries that are never read again — a slow leak unless an eager sweep is added."
            ),
            "code": {
                "python": (
                    "class SetWithExpiry:\n"
                    "    def __init__(self):\n"
                    "        self._exp = {}\n"
                    "        self._now = 0\n"
                    "    def add(self, key, ttl_ms):\n"
                    "        self._exp[key] = self._now + ttl_ms\n"
                    "    def contains(self, key):\n"
                    "        e = self._exp.get(key)\n"
                    "        if e is None:\n"
                    "            return False\n"
                    "        if e <= self._now:\n"
                    "            del self._exp[key]\n"
                    "            return False\n"
                    "        return True\n"
                    "    def tick(self, now_ms):\n"
                    "        self._now = now_ms"
                ),
                "javascript": (
                    "class SetWithExpiry {\n"
                    "    constructor() { this.exp = new Map(); this.now = 0; }\n"
                    "    add(key, ttlMs) { this.exp.set(key, this.now + ttlMs); }\n"
                    "    contains(key) {\n"
                    "        const e = this.exp.get(key);\n"
                    "        if (e === undefined) return false;\n"
                    "        if (e <= this.now) { this.exp.delete(key); return false; }\n"
                    "        return true;\n"
                    "    }\n"
                    "    tick(nowMs) { this.now = nowMs; }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Hash Map + Min-Heap (Eager Purge)",
            "time_complexity": "O(log N) per op",
            "space_complexity": "O(N)",
            "description": (
                "Pair the map with a min-heap of `(expiry, key)`. On `tick` (or any operation), pop the "
                "heap top while it's expired and purge from the map. Bounded memory at the cost of O(log N) "
                "per op. This is the production shape — almost every cache library uses it."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "class SetWithExpiry:\n"
                    "    def __init__(self):\n"
                    "        self._exp = {}\n"
                    "        self._heap = []\n"
                    "        self._now = 0\n"
                    "    def _sweep(self):\n"
                    "        while self._heap and self._heap[0][0] <= self._now:\n"
                    "            t, k = heapq.heappop(self._heap)\n"
                    "            if self._exp.get(k) == t:\n"
                    "                del self._exp[k]\n"
                    "    def add(self, key, ttl_ms):\n"
                    "        e = self._now + ttl_ms\n"
                    "        self._exp[key] = e\n"
                    "        heapq.heappush(self._heap, (e, key))\n"
                    "    def contains(self, key):\n"
                    "        self._sweep()\n"
                    "        return key in self._exp\n"
                    "    def tick(self, now_ms):\n"
                    "        self._now = now_ms\n"
                    "        self._sweep()"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Map `key → expiry_time`. The 'set' is just 'has a non-expired entry'.",
        "2. Decide lazy vs eager. Lazy is fast on the hot path; eager bounds memory.",
        "3. Hybrid is what production uses: lazy on read + heap-driven sweep on add/tick.",
        "4. Inject a clock. Don't call `time.time()` directly — that makes tests time-flaky and orthogonally couples behaviour to wall-clock.",
        "5. Document the re-add semantics: does it extend the TTL or refresh? Pick one explicitly.",
        "6. Edge cases: TTL = 0 (immediately expired), missing key, repeated adds, expired key still in map.",
    ],
    "tips": [
        "The most common bug in this problem is `contains` returning True for an expired entry that hasn't been swept. The lazy check on read is the fix.",
        "Heap entries can become stale (the entry was overwritten by a fresh `add`). Validate the heap top against the current map entry before deleting.",
        "Concurrency: synchronise on the map for correctness; consider a striped lock for throughput.",
        "Common follow-up: 'how would you test this?' Inject the clock; advance manually. Avoid `sleep` in tests — flaky and slow.",
        "Common follow-up: 'distribute it.' Now you're building Redis with TTLs. Discuss replication, eviction policies, time skew across nodes.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg"],
    "topics": ["Hash Table", "Heap", "Design", "Concurrency"],
    "time_complexity": "O(1) lazy / O(log N) eager",
    "space_complexity": "O(N)",
}


def REFERENCE(input):
    class SetWithExpiry:
        def __init__(self):
            self._exp = {}
            self._now = 0

        def add(self, key, ttl_ms):
            self._exp[key] = self._now + ttl_ms

        def contains(self, key):
            e = self._exp.get(key)
            if e is None:
                return False
            if e <= self._now:
                del self._exp[key]
                return False
            return True

        def tick(self, now_ms):
            self._now = now_ms

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "SetWithExpiry":
            instance = SetWithExpiry()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "SetWithExpiry",
    "constructor": {"params": []},
    "methods": [
        {"name": "add", "params": [{"name": "key", "type": "string"},
                                    {"name": "ttl_ms", "type": "int"}], "returns": "any"},
        {"name": "contains", "params": [{"name": "key", "type": "string"}], "returns": "bool"},
        {"name": "tick", "params": [{"name": "now_ms", "type": "int"}], "returns": "any"},
    ],
}


register(PAYLOAD, REFERENCE)
