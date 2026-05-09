"""LeaderboardSystem — Medium. Heap / Hash Map / Design.

Maintain a top-K live leaderboard as player updates stream in.
Each update is a `(player_id, name, wins)` triple; an existing
player's row is overwritten (NOT additive — score is the latest
authoritative wins for that id). Queries ask for the current top
K by descending wins, ties broken by name ascending.

The design tension is the same one that shows up in every
streaming top-K: a min-heap of size K is the textbook answer for
'what are the top K right now', but updates that touch an
existing player force you to either invalidate stale heap entries
(lazy deletion with a token) or reheapify (O(N)). The class_ops
test sequences exercise both the steady-state stream and the
update-existing-player edge."""
from builder.registry import register


PAYLOAD = {
    "title": "Leaderboard System",
    "difficulty": "Medium",
    "description": (
        "Design a `LeaderboardSystem` that maintains a live top-K standings as player score updates "
        "stream in. Each player has a unique `player_id` (string), a `name` (string), and a non-"
        "negative integer `wins` count.\n\n"
        "**Operations:**\n"
        "- `record_player(player_id, name, wins)` — insert a player or update an existing one. "
        "The wins value passed in is the new authoritative wins for that player — it **replaces**, "
        "not adds.\n"
        "- `top(k)` — return the top `k` players as a list of `[name, wins]` pairs sorted by `wins` "
        "descending, ties broken by `name` ascending. If fewer than `k` players exist, return all "
        "of them. If `k <= 0`, return `[]`.\n\n"
        "**Notes:**\n"
        "- Player names are not unique — two different `player_id`s can share a name. The same "
        "`player_id` keeps a single row that's updated in place across calls.\n"
        "- The interview discussion typically extends this into the streaming-files framing: many "
        "files arrive over time, each containing player records. Implementation is file-format "
        "agnostic — assume someone else parsed them and is calling `record_player` for each row.\n\n"
        "**Example sequence:**\n"
        "```\n"
        "lb = LeaderboardSystem()\n"
        "lb.record_player(\"p1\", \"Alice\", 5)\n"
        "lb.record_player(\"p2\", \"Bob\", 3)\n"
        "lb.record_player(\"p3\", \"Cara\", 7)\n"
        "lb.top(2)               # [[\"Cara\", 7], [\"Alice\", 5]]\n"
        "lb.record_player(\"p2\", \"Bob\", 9)   # update Bob's wins\n"
        "lb.top(2)               # [[\"Bob\", 9], [\"Cara\", 7]]\n"
        "```"
    ),
    "hints": [
        "The simplest correct version: store `player_id → (name, wins)` in a dict. On `top(k)`, sort and slice. O(N log N) per query but trivially correct and fine when N is small.",
        "If the read-rate is high, maintain a min-heap of size K of (wins, name, player_id). On insert, if smaller than the min, drop it; else heappush, then heappop until size is K. O(log K) per write.",
        "The catch with the heap-of-K approach: if a player who's currently in the top-K gets their wins UPDATED, the heap holds a stale (wins, ...) entry. Three ways to handle: (a) lazy deletion via tokens (most popular), (b) eager removal which is O(K) on a binary heap, (c) Fibonacci or indexed heap.",
        "Lazy deletion: keep a 'tombstone' set keyed by player_id. When the heap top points at a tombstoned id, pop and discard. Cost: bounded by total updates between heap reads.",
        "Variable K (different `top(k)` calls request different k) breaks the heap-of-K trick — the structure depends on K. If K varies, fall back to maintaining a sorted structure (sorted list, balanced BST / skip list, or just sort on read).",
        "If you're operating at scale (many writers, many readers) the bottleneck moves to concurrency. Discuss: a single-writer-many-reader copy-on-write snapshot, or per-shard partitioning of player_id space with cross-shard merge on read.",
        "Real-world: the file-streaming framing is mostly distraction — the parser is somebody else's problem. The senior signal is in the consistency story: do `top(k)` and `record_player` interleave atomically, or can `top` see a half-applied update?",
    ],
    "constraints": [
        "1 <= total operations across the test sequence <= 10⁵",
        "1 <= len(player_id) <= 32; player_id is a printable ASCII string",
        "1 <= len(name) <= 64; name is a printable string (may contain spaces)",
        "0 <= wins <= 10⁹",
        "0 <= k <= 10⁵ (k larger than the player count just returns everyone sorted)",
        "Updates always replace; there is no decrement-only path (wins values can also go down on update)",
    ],
    "starter_code": {
        "python": (
            "class LeaderboardSystem:\n"
            "    def __init__(self): pass\n"
            "    def record_player(self, player_id, name, wins): pass\n"
            "    def top(self, k): pass"
        ),
        "javascript": (
            "class LeaderboardSystem {\n"
            "    constructor() {}\n"
            "    recordPlayer(playerId, name, wins) {}\n"
            "    top(k) {}\n"
            "}"
        ),
        "java": (
            "class LeaderboardSystem {\n"
            "    public LeaderboardSystem() {}\n"
            "    public void recordPlayer(String playerId, String name, long wins) {}\n"
            "    public java.util.List<Object[]> top(int k) { return java.util.Collections.emptyList(); }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    lb = LeaderboardSystem()\n"
            "    lb.record_player(\"p1\", \"Alice\", 5)\n"
            "    lb.record_player(\"p2\", \"Bob\", 3)\n"
            "    lb.record_player(\"p3\", \"Cara\", 7)\n"
            "    print(lb.top(2))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {
            "ops": ["LeaderboardSystem", "record_player", "record_player", "record_player", "top"],
            "args": [[], ["p1", "Alice", 5], ["p2", "Bob", 3], ["p3", "Cara", 7], [2]],
         },
         "expected": [None, None, None, None, [["Cara", 7], ["Alice", 5]]],
         "description": "Three players, top-2 by wins desc",
         "tags": ["basic"]},
        {"input": {
            "ops": ["LeaderboardSystem", "record_player", "record_player", "record_player",
                    "record_player", "top"],
            "args": [[], ["p1", "Alice", 5], ["p2", "Bob", 3], ["p3", "Cara", 7],
                     ["p2", "Bob", 9], [2]],
         },
         "expected": [None, None, None, None, None, [["Bob", 9], ["Cara", 7]]],
         "description": "Update existing player's wins — they jump to top",
         "tags": ["basic"]},
        {"input": {
            "ops": ["LeaderboardSystem", "top"],
            "args": [[], [3]],
         },
         "expected": [None, []],
         "description": "Empty leaderboard returns empty list",
         "tags": ["edge"]},
        {"input": {
            "ops": ["LeaderboardSystem", "record_player", "record_player", "record_player", "top"],
            "args": [[], ["p1", "Alice", 5], ["p2", "Bob", 3], ["p3", "Cara", 7], [10]],
         },
         "expected": [None, None, None, None, [["Cara", 7], ["Alice", 5], ["Bob", 3]]],
         "description": "k > player count → return all sorted",
         "tags": ["edge"]},
        {"input": {
            "ops": ["LeaderboardSystem", "record_player", "record_player", "record_player", "top"],
            "args": [[], ["p1", "Alice", 5], ["p2", "Bob", 5], ["p3", "Cara", 5], [3]],
         },
         "expected": [None, None, None, None, [["Alice", 5], ["Bob", 5], ["Cara", 5]]],
         "description": "Tied wins — break by name ascending",
         "tags": ["tricky"]},
        {"input": {
            "ops": ["LeaderboardSystem", "record_player", "record_player", "top"],
            "args": [[], ["p1", "Alice", 5], ["p1", "Alice Updated", 10], [1]],
         },
         "expected": [None, None, None, [["Alice Updated", 10]]],
         "description": "Same player_id with renamed display — name field updates too",
         "tags": ["tricky"]},
        {"input": {
            "ops": ["LeaderboardSystem", "record_player", "record_player", "top"],
            "args": [[], ["p1", "Alice", 7], ["p1", "Alice", 3], [1]],
         },
         "expected": [None, None, None, [["Alice", 3]]],
         "description": "Update can also LOWER wins — the latest call is authoritative",
         "tags": ["tricky"]},
        {"input": {
            "ops": ["LeaderboardSystem", "record_player", "top", "top"],
            "args": [[], ["p1", "Alice", 0], [1], [0]],
         },
         "expected": [None, None, [["Alice", 0]], []],
         "description": "Wins=0 is a valid score; k=0 returns []",
         "tags": ["edge"]},
        {"input": {
            "ops": ["LeaderboardSystem", "record_player", "record_player", "record_player",
                    "record_player", "record_player", "top"],
            "args": [[], ["p1", "A", 1], ["p2", "B", 2], ["p3", "C", 3], ["p4", "D", 4],
                     ["p5", "E", 5], [3]],
         },
         "expected": [None, None, None, None, None, None, [["E", 5], ["D", 4], ["C", 3]]],
         "description": "Five-player streaming, top-3",
         "tags": ["basic"]},
        {"input": {
            "ops": ["LeaderboardSystem", "record_player", "record_player", "record_player",
                    "top", "record_player", "top"],
            "args": [[], ["p1", "A", 10], ["p2", "B", 8], ["p3", "C", 5], [2],
                     ["p4", "D", 9], [3]],
         },
         "expected": [None, None, None, None, [["A", 10], ["B", 8]], None,
                       [["A", 10], ["D", 9], ["B", 8]]],
         "description": "Insert in middle of stream — top recomputes correctly",
         "tags": ["basic"]},
        {"input": {
            "ops": ["LeaderboardSystem", "record_player", "record_player", "record_player",
                    "record_player", "record_player", "top"],
            "args": [[], ["pA", "Zoe", 5], ["pB", "Yan", 5], ["pC", "Xin", 5],
                     ["pD", "Wes", 5], ["pE", "Vic", 5], [3]],
         },
         "expected": [None, None, None, None, None, None, [["Vic", 5], ["Wes", 5], ["Xin", 5]]],
         "description": "Five-way tie — name ASC across the entire result",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Hash Map + Sort-on-Read (Optimal for Variable K)",
            "time_complexity": "O(1) record_player; O(N log N + k) top",
            "space_complexity": "O(N)",
            "description": (
                "Store one row per player_id in a dict; sort on every `top()`. Because `k` can vary "
                "from query to query and updates can move any player anywhere in the order, "
                "maintaining a precomputed structure adds complexity without saving complexity in the "
                "average case. This is the production shape when N is in the thousands and queries "
                "are infrequent — measure before optimising. The dominant cost is the sort, "
                "O(N log N), which is fine until N is genuinely huge or queries are extremely hot."
            ),
            "code": {
                "python": (
                    "class LeaderboardSystem:\n"
                    "    def __init__(self):\n"
                    "        self._players = {}  # player_id → (name, wins)\n"
                    "    \n"
                    "    def record_player(self, player_id, name, wins):\n"
                    "        self._players[player_id] = (name, wins)\n"
                    "    \n"
                    "    def top(self, k):\n"
                    "        if k <= 0:\n"
                    "            return []\n"
                    "        # Sort by wins desc, then name asc.\n"
                    "        ranked = sorted(\n"
                    "            self._players.values(),\n"
                    "            key=lambda nw: (-nw[1], nw[0]),\n"
                    "        )\n"
                    "        return [list(nw) for nw in ranked[:k]]"
                ),
                "javascript": (
                    "class LeaderboardSystem {\n"
                    "    constructor() { this._players = new Map(); }\n"
                    "    recordPlayer(playerId, name, wins) {\n"
                    "        this._players.set(playerId, [name, wins]);\n"
                    "    }\n"
                    "    top(k) {\n"
                    "        if (k <= 0) return [];\n"
                    "        const ranked = [...this._players.values()].sort((a, b) => {\n"
                    "            if (a[1] !== b[1]) return b[1] - a[1];\n"
                    "            return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0;\n"
                    "        });\n"
                    "        return ranked.slice(0, k);\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Hash Map + Min-Heap of K (Fixed K, Hot Reads)",
            "time_complexity": "O(log K) record_player; O(K log K) top",
            "space_complexity": "O(N + K)",
            "description": (
                "Keep the player dict as before. Maintain a min-heap of size at most K of `(wins, "
                "name, player_id)`. On record_player: if the heap is smaller than K, push; else if "
                "the new wins exceeds the heap top, replace. To avoid stale entries from prior "
                "versions of the same player, tag each heap entry with a version counter and lazy-"
                "drop entries whose version disagrees with the dict on read. This wins when K is "
                "fixed, the read rate is high, and N is much larger than K. It loses when K varies "
                "across queries."
            ),
            "code": {
                "python": (
                    "import heapq\n"
                    "\n"
                    "class LeaderboardSystem:\n"
                    "    def __init__(self):\n"
                    "        self._players = {}    # player_id → (name, wins)\n"
                    "        self._version = {}    # player_id → monotonic version int\n"
                    "        self._heap = []       # entries of (wins, name, player_id, version)\n"
                    "    \n"
                    "    def record_player(self, player_id, name, wins):\n"
                    "        v = self._version.get(player_id, 0) + 1\n"
                    "        self._version[player_id] = v\n"
                    "        self._players[player_id] = (name, wins)\n"
                    "        heapq.heappush(self._heap, (wins, name, player_id, v))\n"
                    "    \n"
                    "    def top(self, k):\n"
                    "        if k <= 0: return []\n"
                    "        # Walk the heap, dropping stale entries; collect top-k by sort.\n"
                    "        # In a long-lived system you'd maintain a SIZE-K view incrementally\n"
                    "        # and snapshot it; for clarity here we just sort the live snapshot.\n"
                    "        live = []\n"
                    "        for wins, name, pid, v in self._heap:\n"
                    "            if self._version.get(pid) == v and self._players.get(pid) == (name, wins):\n"
                    "                live.append((name, wins))\n"
                    "        live.sort(key=lambda nw: (-nw[1], nw[0]))\n"
                    "        return [list(nw) for nw in live[:k]]"
                ),
            },
        },
        {
            "title": "Hash Map + Indexed Sorted Container (Fast Top-K, Variable K)",
            "time_complexity": "O(log N) record_player; O(k) top",
            "space_complexity": "O(N)",
            "description": (
                "If both writes and reads are hot AND k varies, neither plain sort nor heap-of-K wins. "
                "Use an order-statistic structure: in Python, a `SortedList` from `sortedcontainers`; "
                "in Java, a `TreeMap`; in C++, an order-statistic tree. Key the structure by "
                "`(-wins, name, player_id)` so the natural iteration order is descending wins / "
                "ascending name. Updates remove the old key and insert the new one — O(log N) each. "
                "Reads slice the first k entries — O(k). This is the structure most production "
                "leaderboards reach for. The shape below uses `bisect.insort` on a maintained sorted "
                "list of (-wins, name, player_id) tuples — same idea, no third-party dependency."
            ),
            "code": {
                "python": (
                    "import bisect\n"
                    "\n"
                    "class LeaderboardSystem:\n"
                    "    def __init__(self):\n"
                    "        self._players = {}    # player_id → (name, wins)\n"
                    "        self._sorted = []     # list of (-wins, name, player_id), kept sorted\n"
                    "    \n"
                    "    def record_player(self, player_id, name, wins):\n"
                    "        old = self._players.get(player_id)\n"
                    "        if old is not None:\n"
                    "            old_name, old_wins = old\n"
                    "            old_key = (-old_wins, old_name, player_id)\n"
                    "            i = bisect.bisect_left(self._sorted, old_key)\n"
                    "            if i < len(self._sorted) and self._sorted[i] == old_key:\n"
                    "                self._sorted.pop(i)\n"
                    "        self._players[player_id] = (name, wins)\n"
                    "        bisect.insort(self._sorted, (-wins, name, player_id))\n"
                    "    \n"
                    "    def top(self, k):\n"
                    "        if k <= 0:\n"
                    "            return []\n"
                    "        return [[name, -neg_wins] for neg_wins, name, _ in self._sorted[:k]]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate. Stream of (id, name, wins) updates; queries ask for top-K by wins desc, name asc tiebreak. Updates REPLACE the player row, they don't add to it.",
        "2. Smallest correct thing: dict for O(1) update + sort-on-read for queries. O(N log N) per query — fine for small N.",
        "3. If queries get hot: heap of size K. But K is variable here, which kills the simple heap-of-K trick. Note this and move on.",
        "4. Lazy deletion: when a player gets updated, the heap may hold a stale snapshot. Tag entries with a version; drop on read whenever the version doesn't match the dict. Trade memory + occasional sweep for fast writes.",
        "5. The senior reach: order-statistic structure (TreeMap / SortedList) keyed by `(-wins, name, id)` gives O(log N) writes and O(K) reads with no staleness ever. This is what production code uses.",
        "6. Tiebreak on name asc — pin this in the comparator, not the sort. The Python `sorted` with `key=lambda x: (-x[1], x[0])` is stable AND correct.",
        "7. Edge cases: k <= 0 → []. k > N → return all N. Empty leaderboard → []. Update with same wins (no-op semantically, but the version still bumps).",
        "8. Concurrency follow-up: if the file stream is multi-threaded, snapshot reads (copy-on-write) keep `top()` consistent. Otherwise an interleaved update mid-sort can produce a torn read.",
    ],
    "tips": [
        "Pin the tiebreak rule explicitly. 'Name ascending' is the most defensible default — alphabetical, deterministic, doesn't depend on insertion order.",
        "Update REPLACES wins. The 'wins can go down' test case catches solutions that maintain a max-tracker which assumes monotonic growth.",
        "Variable K is the hidden trap. Solutions that maintain a heap-of-K silently produce wrong answers when called with `top(K')` for K' > K.",
        "If the interviewer asks 'how big can N get?', the answer determines the data structure. <10⁴: sort on read. 10⁴–10⁶ with hot reads: order-statistic tree. >10⁶: shard by player_id and merge K-way on read.",
        "Common follow-up: 'now wins are EVENTS, not absolute counts.' Now record_player ADDS wins; the question becomes 'which structure tracks running totals AND maintains rank?' Answer: same data structure, just with += instead of =.",
        "Common follow-up: 'now we want top-K AND each player's rank.' Order-statistic tree gives both: rank = index of the player's key.",
        "Common follow-up: 'now there are 100 leaderboards (per-region, per-mode).' Same structure parameterised by leaderboard_id; per-id state in a map.",
        "The streaming-files framing is a red herring. Parse-and-call is somebody else's problem. Don't get distracted writing JSON / CSV / XML parsers in the interview.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Meta", "Bloomberg", "Netflix"],
    "topics": ["Hash Table", "Heap", "Sorting", "Design"],
    "time_complexity": "O(N log N) sort-on-read / O(log N) order-statistic",
    "space_complexity": "O(N)",
    "entry": {
        "kind": "class_ops",
        "class": "LeaderboardSystem",
        "constructor": {"params": []},
        "methods": [
            {"name": "record_player",
             "params": [{"name": "player_id", "type": "string"},
                        {"name": "name", "type": "string"},
                        {"name": "wins", "type": "int"}],
             "returns": "any"},
            {"name": "top",
             "params": [{"name": "k", "type": "int"}],
             "returns": "list"},
        ],
    },
}


def REFERENCE(input):
    class LeaderboardSystem:
        def __init__(self):
            self._players = {}

        def record_player(self, player_id, name, wins):
            self._players[player_id] = (name, wins)

        def top(self, k):
            if k <= 0:
                return []
            ranked = sorted(
                self._players.values(),
                key=lambda nw: (-nw[1], nw[0]),
            )
            return [list(nw) for nw in ranked[:k]]

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "LeaderboardSystem":
            instance = LeaderboardSystem()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


register(PAYLOAD, REFERENCE)
