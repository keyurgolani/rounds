"""Zeitgeist Top-N — Medium. Sliding Window / Heap.

Track top-N most popular items over a sliding time window from a
stream of (customer, item, timestamp) events."""
from builder.registry import register


PAYLOAD = {
    "title": "Zeitgeist — Top N Most Popular Items",
    "difficulty": "Medium",
    "description": (
        "Implement a service that processes purchase events and returns the most-popular items over a "
        "sliding time window. Required operations:\n"
        "- `__init__(window_seconds, n)` — track the top-N items over the most recent `window_seconds`.\n"
        "- `process(customer_id, item_id, timestamp)` — record a purchase.\n"
        "- `top()` — return the top-N item ids by purchase count within the window, ties broken by item id "
        "(lexicographic ascending). The list may be shorter than N if fewer distinct items have been "
        "purchased.\n"
        "- `now(timestamp)` — advance the virtual clock so older events can be evicted from the window. "
        "Tests use this for determinism.\n\n"
        "Eviction rule: when `top()` or `now()` is called, expire any event with `timestamp < now - "
        "window_seconds`. Counts decrement accordingly.\n\n"
        "**Example:**\n"
        "```\n"
        "z = Zeitgeist(window_seconds=60, n=2)\n"
        "z.process('c1', 'A', 0)\n"
        "z.process('c2', 'A', 5)\n"
        "z.process('c3', 'B', 10)\n"
        "z.now(15)\n"
        "z.top()                  # ['A', 'B']\n"
        "z.now(70)                # only events at t >= 10 remain\n"
        "z.top()                  # ['B'] (and 'A' at t=5 also remains)\n"
        "```"
    ),
    "hints": [
        "Maintain a deque of `(timestamp, item)` events in arrival order. On eviction, pop from the front while too old.",
        "Maintain a `count: item → frequency` map. On enqueue, increment; on evict, decrement; remove zero entries.",
        "Top-N from the count map: sort by (count desc, item asc), take first N.",
        "If N << number of items and the window is large, a sorted structure (TreeSet keyed by (-count, item)) gives O(log K) updates and O(N) reads.",
        "Edge cases: empty service, all events in window, all events expired, fewer than N distinct items.",
    ],
    "constraints": [
        "1 <= window_seconds <= 86400",
        "1 <= total operations <= 10⁵",
    ],
    "starter_code": {
        "python": (
            "class Zeitgeist:\n"
            "    def __init__(self, window_seconds, n): pass\n"
            "    def process(self, customer_id, item_id, timestamp): pass\n"
            "    def now(self, timestamp): pass\n"
            "    def top(self): pass"
        ),
        "javascript": (
            "class Zeitgeist {\n"
            "    constructor(windowSeconds, n) {}\n"
            "    process(customerId, itemId, timestamp) {}\n"
            "    now(timestamp) {}\n"
            "    top() {}\n"
            "}"
        ),
        "java": (
            "class Zeitgeist {\n"
            "    public Zeitgeist(int windowSeconds, int n) {}\n"
            "    public void process(String c, String item, long t) {}\n"
            "    public void now(long t) {}\n"
            "    public List<String> top() { return new ArrayList<>(); }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    z = Zeitgeist(60, 2)\n"
            "    for c, i, t in [('c1','A',0),('c2','A',5),('c3','B',10)]: z.process(c, i, t)\n"
            "    z.now(15); print(z.top())"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["Zeitgeist", "process", "process", "process", "now", "top"],
                    "args": [[60, 2], ["c1", "A", 0], ["c2", "A", 5], ["c3", "B", 10],
                             [15], []]},
         "expected": [None, None, None, None, None, ["A", "B"]],
         "description": "Top-2 within 60s window", "tags": ["basic"]},
        {"input": {"ops": ["Zeitgeist", "top"], "args": [[60, 5], []]},
         "expected": [None, []],
         "description": "Empty service", "tags": ["edge"]},
        {"input": {"ops": ["Zeitgeist", "process", "process", "now", "top"],
                    "args": [[10, 2], ["c1", "X", 0], ["c2", "Y", 5], [100], []]},
         "expected": [None, None, None, None, []],
         "description": "All events expired by the time top is called",
         "tags": ["edge"]},
        {"input": {"ops": ["Zeitgeist", "process", "process", "now", "top"],
                    "args": [[60, 5], ["c1", "A", 0], ["c2", "B", 5], [10], []]},
         "expected": [None, None, None, None, ["A", "B"]],
         "description": "Tie at count 1 — alphabetic order", "tags": ["tricky"]},
        {"input": {"ops": ["Zeitgeist", "process", "process", "process", "now", "top"],
                    "args": [[60, 1], ["c1", "B", 0], ["c2", "A", 5], ["c3", "A", 10],
                             [15], []]},
         "expected": [None, None, None, None, None, ["A"]],
         "description": "N=1; A wins on count", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Deque + Count Map (Optimal)",
            "time_complexity": "O(K log K) per top() worst case (sort)",
            "space_complexity": "O(W) where W = events in window",
            "description": (
                "Deque of `(timestamp, item)` events. Count map for O(1) frequency lookup. On now() (or "
                "top()), evict events older than `current - window`, decrementing counts. top() sorts the "
                "non-zero entries and returns the first N."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "class Zeitgeist:\n"
                    "    def __init__(self, window_seconds, n):\n"
                    "        self._window = window_seconds\n"
                    "        self._n = n\n"
                    "        self._events = deque()\n"
                    "        self._count = {}\n"
                    "        self._now = 0\n"
                    "    def process(self, customer_id, item_id, timestamp):\n"
                    "        self._now = max(self._now, timestamp)\n"
                    "        self._events.append((timestamp, item_id))\n"
                    "        self._count[item_id] = self._count.get(item_id, 0) + 1\n"
                    "    def now(self, timestamp):\n"
                    "        self._now = timestamp\n"
                    "        self._evict()\n"
                    "    def _evict(self):\n"
                    "        threshold = self._now - self._window\n"
                    "        while self._events and self._events[0][0] < threshold:\n"
                    "            _, item = self._events.popleft()\n"
                    "            self._count[item] -= 1\n"
                    "            if self._count[item] == 0:\n"
                    "                del self._count[item]\n"
                    "    def top(self):\n"
                    "        self._evict()\n"
                    "        ranked = sorted(self._count.items(), key=lambda kv: (-kv[1], kv[0]))\n"
                    "        return [item for item, _ in ranked[:self._n]]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Stream + sliding window → deque of events plus count map.",
        "2. process: append + bump count.",
        "3. now: advance virtual clock + evict.",
        "4. top: evict + sort + take N. Sort cost dominates if many distinct items; tree-based for hotter paths.",
        "5. Tie-break is alphabetic; implement explicitly so it's deterministic.",
        "6. Edge cases: empty, all expired, fewer than N distinct items, ties.",
    ],
    "tips": [
        "Don't forget to delete count entries that hit zero — otherwise they'll show up in top().",
        "Eviction lazily on read keeps writes O(1) — good when read is much rarer than write.",
        "Common follow-up: 'concurrency / sharded counters.' Hash-shard by item_id; periodic merge for top-N.",
        "Common follow-up: 'approximation for billions of events.' Count-min sketch + heavy-hitters algorithm (Misra-Gries).",
        "Common follow-up: 'continuous top-N updates.' Maintain a min-heap of size N keyed on count; replace when count surpasses heap min.",
    ],
    "companies": ["Amazon", "Twitter", "Google"],
    "topics": ["Sliding Window", "Hash Table", "Heap", "Streaming"],
    "time_complexity": "O(1) process, O(K log K) top",
    "space_complexity": "O(W)",
}


def REFERENCE(input):
    from collections import deque

    class Zeitgeist:
        def __init__(self, window_seconds, n):
            self._window = window_seconds
            self._n = n
            self._events = deque()
            self._count = {}
            self._now = 0

        def process(self, customer_id, item_id, timestamp):
            self._now = max(self._now, timestamp)
            self._events.append((timestamp, item_id))
            self._count[item_id] = self._count.get(item_id, 0) + 1

        def now(self, timestamp):
            self._now = timestamp
            self._evict()

        def _evict(self):
            threshold = self._now - self._window
            while self._events and self._events[0][0] < threshold:
                _, item = self._events.popleft()
                self._count[item] -= 1
                if self._count[item] == 0:
                    del self._count[item]

        def top(self):
            self._evict()
            ranked = sorted(self._count.items(), key=lambda kv: (-kv[1], kv[0]))
            return [item for item, _ in ranked[:self._n]]

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "Zeitgeist":
            instance = Zeitgeist(*a)
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "Zeitgeist",
    "constructor": {"params": [
        {"name": "window_seconds", "type": "int"},
        {"name": "n", "type": "int"},
    ]},
    "methods": [
        {"name": "process", "params": [
            {"name": "customer_id", "type": "string"},
            {"name": "item_id", "type": "string"},
            {"name": "timestamp", "type": "int"},
        ], "returns": "any"},
        {"name": "now", "params": [{"name": "timestamp", "type": "int"}], "returns": "any"},
        {"name": "top", "params": [], "returns": "string[]"},
    ],
}


register(PAYLOAD, REFERENCE)
