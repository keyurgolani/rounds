"""Recently Listened Tracks — Medium. Logical & Maintainable / LRU.

Track a user's recently played songs. Same shape as LRU cache —
HashMap + Doubly Linked List for O(1) add and get."""
from builder.registry import register


PAYLOAD = {
    "title": "Recently Listened Tracks Widget",
    "difficulty": "Medium",
    "description": (
        "Implement a widget that tracks a user's recently listened tracks. Required operations:\n"
        "- `play(track_id)` — record a play. If the track was already in the list, move it to the front "
        "(most recent). If the list is at capacity and a new track plays, evict the least-recently played.\n"
        "- `recent()` — return the list of track IDs in most-recent-first order.\n"
        "- `count()` — number of tracks currently tracked.\n\n"
        "All operations must be **O(1) amortised** (apart from `recent()` which is O(N) by definition).\n\n"
        "Capacity is fixed at construction time.\n\n"
        "**Example:**\n"
        "```\n"
        "w = RecentTracks(3)\n"
        "w.play('A'); w.play('B'); w.play('C')\n"
        "w.recent()      # ['C', 'B', 'A']\n"
        "w.play('A')     # bump A to front\n"
        "w.recent()      # ['A', 'C', 'B']\n"
        "w.play('D')     # evict 'B' (LRU)\n"
        "w.recent()      # ['D', 'A', 'C']\n"
        "```"
    ),
    "hints": [
        "Same shape as LRU cache: HashMap (track_id → node) + Doubly Linked List (head = most recent).",
        "On `play(t)`: if `t` exists, unlink and re-insert at head; else, insert at head and possibly evict the tail.",
        "Capacity check before insert: if at capacity, pop the tail and remove from the map.",
        "`recent()` walks the list from head; `count()` is the map size.",
        "Edge cases: capacity 0 (always empty?), repeated play of the same track, play with empty cache.",
    ],
    "constraints": [
        "1 <= capacity <= 10⁵",
        "1 <= total operations <= 10⁵",
    ],
    "starter_code": {
        "python": (
            "class RecentTracks:\n"
            "    def __init__(self, capacity): pass\n"
            "    def play(self, track_id): pass\n"
            "    def recent(self): pass\n"
            "    def count(self): pass"
        ),
        "javascript": (
            "class RecentTracks {\n"
            "    constructor(capacity) {}\n"
            "    play(trackId) {}\n"
            "    recent() {}\n"
            "    count() {}\n"
            "}"
        ),
        "java": (
            "class RecentTracks {\n"
            "    public RecentTracks(int capacity) {}\n"
            "    public void play(String trackId) {}\n"
            "    public List<String> recent() { return new ArrayList<>(); }\n"
            "    public int count() { return 0; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    w = RecentTracks(3)\n"
            "    for t in ['A','B','C']: w.play(t)\n"
            "    print(w.recent())"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["RecentTracks", "play", "play", "play", "recent"],
                    "args": [[3], ["A"], ["B"], ["C"], []]},
         "expected": [None, None, None, None, ["C", "B", "A"]],
         "description": "Three plays in order", "tags": ["basic"]},
        {"input": {"ops": ["RecentTracks", "play", "play", "play", "play", "recent"],
                    "args": [[3], ["A"], ["B"], ["C"], ["A"], []]},
         "expected": [None, None, None, None, None, ["A", "C", "B"]],
         "description": "Re-play A bumps it to front", "tags": ["basic"]},
        {"input": {"ops": ["RecentTracks", "play", "play", "play", "play", "recent"],
                    "args": [[2], ["A"], ["B"], ["C"], ["D"], []]},
         "expected": [None, None, None, None, None, ["D", "C"]],
         "description": "Capacity 2 — A and B evicted", "tags": ["basic"]},
        {"input": {"ops": ["RecentTracks", "recent", "count"],
                    "args": [[5], [], []]},
         "expected": [None, [], 0],
         "description": "Empty cache", "tags": ["edge"]},
        {"input": {"ops": ["RecentTracks", "play", "play", "count"],
                    "args": [[5], ["A"], ["A"], []]},
         "expected": [None, None, None, 1],
         "description": "Re-play same track doesn't grow count", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "HashMap + Doubly Linked List (Optimal)",
            "time_complexity": "O(1) play, O(N) recent, O(1) count",
            "space_complexity": "O(N)",
            "description": (
                "Same data structure as the canonical LRU cache. Map points from track_id to its node in "
                "the doubly linked list. Head sentinel = most recent; tail sentinel = LRU. play unlinks "
                "and re-inserts at head."
            ),
            "code": {
                "python": (
                    "class _Node:\n"
                    "    __slots__ = ('val', 'prev', 'next')\n"
                    "    def __init__(self, val):\n"
                    "        self.val = val; self.prev = self.next = None\n\n"
                    "class RecentTracks:\n"
                    "    def __init__(self, capacity):\n"
                    "        self._cap = capacity\n"
                    "        self._map = {}\n"
                    "        self._head = _Node(None); self._tail = _Node(None)\n"
                    "        self._head.next = self._tail; self._tail.prev = self._head\n"
                    "    def _unlink(self, n):\n"
                    "        n.prev.next = n.next; n.next.prev = n.prev\n"
                    "    def _insert_front(self, n):\n"
                    "        n.next = self._head.next; n.prev = self._head\n"
                    "        self._head.next.prev = n; self._head.next = n\n"
                    "    def play(self, track_id):\n"
                    "        if track_id in self._map:\n"
                    "            n = self._map[track_id]\n"
                    "            self._unlink(n)\n"
                    "            self._insert_front(n)\n"
                    "        else:\n"
                    "            n = _Node(track_id)\n"
                    "            self._map[track_id] = n\n"
                    "            self._insert_front(n)\n"
                    "            if len(self._map) > self._cap:\n"
                    "                old = self._tail.prev\n"
                    "                self._unlink(old)\n"
                    "                del self._map[old.val]\n"
                    "    def recent(self):\n"
                    "        out = []\n"
                    "        cur = self._head.next\n"
                    "        while cur is not self._tail:\n"
                    "            out.append(cur.val)\n"
                    "            cur = cur.next\n"
                    "        return out\n"
                    "    def count(self):\n"
                    "        return len(self._map)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Read the requirements carefully — recently played, with eviction, with re-play bumping. That's LRU semantics with a cap.",
        "2. Same shape as the canonical LRU cache. Don't re-derive — name the pattern out loud.",
        "3. Map for O(1) lookup; doubly linked list for O(1) link/unlink; sentinels to remove edge-case branching.",
        "4. play: existing → unlink+insert front; new → insert front + maybe evict tail.",
        "5. recent: walk head→tail. count: map size.",
        "6. Edge cases: empty, single track repeated, cap exceeded, all unique fills capacity.",
    ],
    "tips": [
        "Python tip: a `collections.OrderedDict` reduces this to ~10 lines via `move_to_end` and `popitem(last=False)`. Show the underlying structure once for understanding, then offer this as the 'in production' answer.",
        "Sentinels (head and tail nodes that aren't 'real' data) eliminate null-checks at the boundaries.",
        "Don't forget to remove from the map when you evict the tail. It's a classic memory leak.",
        "Common follow-up: 'persist across sessions.' Serialize the linked list order; rehydrate on startup.",
        "Common follow-up: 'distributed cache.' Now you're building Redis with LRU eviction. Discuss consistency, replication.",
    ],
    "companies": ["Amazon", "Spotify", "Pandora"],
    "topics": ["Hash Table", "Linked List", "Design", "LRU Cache"],
    "time_complexity": "O(1) play",
    "space_complexity": "O(N)",
}


def REFERENCE(input):
    class _Node:
        __slots__ = ("val", "prev", "next")

        def __init__(self, val):
            self.val = val
            self.prev = self.next = None

    class RecentTracks:
        def __init__(self, capacity):
            self._cap = capacity
            self._map = {}
            self._head = _Node(None)
            self._tail = _Node(None)
            self._head.next = self._tail
            self._tail.prev = self._head

        def _unlink(self, n):
            n.prev.next = n.next
            n.next.prev = n.prev

        def _insert_front(self, n):
            n.next = self._head.next
            n.prev = self._head
            self._head.next.prev = n
            self._head.next = n

        def play(self, track_id):
            if track_id in self._map:
                n = self._map[track_id]
                self._unlink(n)
                self._insert_front(n)
            else:
                n = _Node(track_id)
                self._map[track_id] = n
                self._insert_front(n)
                if len(self._map) > self._cap:
                    old = self._tail.prev
                    self._unlink(old)
                    del self._map[old.val]

        def recent(self):
            out = []
            cur = self._head.next
            while cur is not self._tail:
                out.append(cur.val)
                cur = cur.next
            return out

        def count(self):
            return len(self._map)

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "RecentTracks":
            instance = RecentTracks(*a)
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "RecentTracks",
    "constructor": {"params": [{"name": "capacity", "type": "int"}]},
    "methods": [
        {"name": "play", "params": [{"name": "track_id", "type": "string"}], "returns": "any"},
        {"name": "recent", "params": [], "returns": "string[]"},
        {"name": "count", "params": [], "returns": "int"},
    ],
}


register(PAYLOAD, REFERENCE)
