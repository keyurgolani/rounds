"""LFU Cache — Hard. LeetCode 460. Design with O(1) get/put.

Maintain key→(value, freq) plus freq→ordered set of keys (LRU within each freq
bucket). Track minFreq to evict in O(1). The classic two-level structure that
combines hashing with an OrderedDict (or DLL of DLLs) per frequency."""
from builder.registry import register


PAYLOAD = {
    "title": "LFU Cache",
    "difficulty": "Hard",
    "description": (
        "Design and implement a data structure for a **Least Frequently Used (LFU) cache**.\n\n"
        "Implement the `LFUCache` class:\n"
        "- `LFUCache(int capacity)` — initialise the object with the given positive `capacity`.\n"
        "- `int get(int key)` — return the value of the key if it exists, otherwise return `-1`.\n"
        "- `void put(int key, int value)` — update the value of the key if present, otherwise insert "
        "the key-value pair. When the cache is at capacity, **evict the least frequently used key** "
        "before inserting. If multiple keys have the same lowest use frequency, evict the **least "
        "recently used** among them.\n\n"
        "A key's **use frequency** is the count of `get` and `put` calls applied to it since its insertion. "
        "When a key is updated or read, its frequency increases by 1.\n\n"
        "Both `get` and `put` must run in **average O(1)** time.\n\n"
        "**Example sequence (capacity = 2):**\n"
        "```\n"
        "ops:  [LFUCache, put, put, get, put, get, get, put, get, get, get]\n"
        "args: [[2],      [1,1],[2,2],[1], [3,3],[2], [3], [4,4],[1], [3], [4]]\n"
        "out:  [None,     None, None, 1,   None, -1,  3,   None, -1,  3,   4]\n"
        "\n"
        "After put(1,1), put(2,2):  cache = {1:1, 2:2}\n"
        "get(1) = 1                 freq: {1:2, 2:1}\n"
        "put(3,3): capacity full; key 2 has lowest freq → evict 2.\n"
        "                            cache = {1:1, 3:3}, freq: {1:2, 3:1}\n"
        "get(2) = -1 (was evicted)\n"
        "get(3) = 3                 freq: {1:2, 3:2}\n"
        "put(4,4): full; keys 1 and 3 both have freq 2 → tie, evict LRU among them.\n"
        "          1 was used most recently before this put? No: get(3) was last touch.\n"
        "          So 1 is LRU among the freq-2 bucket → evict 1.\n"
        "                            cache = {3:3, 4:4}, freq: {3:2, 4:1}\n"
        "get(1) = -1, get(3) = 3, get(4) = 4\n"
        "```"
    ),
    "hints": [
        "Maintain `key → (value, freq)` so a hit can fetch both pieces of state in O(1).",
        "Maintain `freq → ordered collection of keys at that frequency`. The order within each bucket "
        "is insertion/access order so you can evict the least recently used in O(1).",
        "Track `minFreq` — the smallest non-empty frequency. On eviction, pop the LRU key from "
        "`buckets[minFreq]`. Update `minFreq` only when the bucket empties AND the operation could raise it "
        "(i.e. on `put` of a brand-new key, reset `minFreq = 1`).",
        "Python: `collections.OrderedDict` per bucket gives O(1) `popitem(last=False)` for LRU eviction "
        "and O(1) `move_to_end` for promote-on-access.",
        "Edge case: capacity 0. Every `put` is a no-op and every `get` returns -1. Special-case it in "
        "the constructor — do NOT enter the eviction code with capacity 0.",
    ],
    "constraints": [
        "0 <= capacity <= 10⁴",
        "0 <= key, value <= 10⁹",
        "At most 2 * 10⁵ calls to get and put combined",
    ],
    "starter_code": {
        "python": (
            "class LFUCache:\n"
            "    def __init__(self, capacity: int):\n"
            "        pass\n"
            "    def get(self, key: int) -> int:\n"
            "        pass\n"
            "    def put(self, key: int, value: int) -> None:\n"
            "        pass"
        ),
        "javascript": (
            "class LFUCache {\n"
            "    constructor(capacity) { /* ... */ }\n"
            "    get(key) { /* return number */ }\n"
            "    put(key, value) { /* ... */ }\n"
            "}"
        ),
        "java": (
            "class LFUCache {\n"
            "    public LFUCache(int capacity) {}\n"
            "    public int get(int key) { return -1; }\n"
            "    public void put(int key, int value) {}\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    c = LFUCache(2)\n"
            "    c.put(1, 1)\n"
            "    c.put(2, 2)\n"
            "    print(c.get(1))   # 1\n"
            "    c.put(3, 3)       # evicts key 2\n"
            "    print(c.get(2))   # -1"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["LFUCache", "put", "put", "get", "put", "get", "get", "put", "get", "get", "get"],
                    "args": [[2], [1, 1], [2, 2], [1], [3, 3], [2], [3], [4, 4], [1], [3], [4]]},
         "expected": [None, None, None, 1, None, -1, 3, None, -1, 3, 4],
         "description": "LeetCode 460 classic example", "tags": ["basic"]},
        {"input": {"ops": ["LFUCache", "put", "get"], "args": [[0], [0, 0], [0]]},
         "expected": [None, None, -1],
         "description": "Capacity 0 — every put is a no-op, every get returns -1", "tags": ["edge"]},
        {"input": {"ops": ["LFUCache", "put", "get", "put", "get", "get"],
                    "args": [[1], [1, 1], [1], [2, 2], [1], [2]]},
         "expected": [None, None, 1, None, -1, 2],
         "description": "Capacity 1 — every put after the first evicts", "tags": ["edge"]},
        {"input": {"ops": ["LFUCache"] + ["put"] * 5,
                    "args": [[3], [1, 1], [2, 2], [3, 3], [4, 4], [5, 5]]},
         "expected": [None, None, None, None, None, None],
         "description": "Many puts no gets — frequencies all equal, LRU breaks ties", "tags": ["basic"]},
        {"input": {"ops": ["LFUCache", "get", "put", "get", "get"],
                    "args": [[2], [99], [1, 1], [99], [1]]},
         "expected": [None, -1, None, -1, 1],
         "description": "Missing key returns -1; absent gets do not affect frequencies", "tags": ["edge"]},
        {"input": {"ops": ["LFUCache", "put", "put", "get", "get", "put", "get", "get"],
                    "args": [[2], [1, 10], [2, 20], [1], [1], [3, 30], [2], [1]]},
         "expected": [None, None, None, 10, 10, None, -1, 10],
         "description": "Eviction by frequency — key 2 with freq 1 is evicted, key 1 (freq 3) survives",
         "tags": ["basic"]},
        {"input": {"ops": ["LFUCache", "put", "put", "put", "get", "put", "get", "get", "get"],
                    "args": [[3], [1, 1], [2, 2], [3, 3], [2], [4, 4], [1], [3], [4]]},
         "expected": [None, None, None, None, 2, None, -1, 3, 4],
         "description": "Tie-break LRU — keys 1 and 3 both have freq 1 after the get(2); 1 is older",
         "tags": ["basic"]},
        {"input": {"ops": ["LFUCache", "put", "put", "put", "put", "get", "get", "get", "get",
                            "put", "get", "get", "get", "get", "get"],
                    "args": [[3], [1, 1], [2, 2], [3, 3], [4, 4], [4], [3], [2], [1],
                             [5, 5], [1], [2], [3], [4], [5]]},
         "expected": [None, None, None, None, None, 4, 3, 2, -1, None, -1, 2, 3, -1, 5],
         "description": "Large mixed — put(4) evicts key 1 (lowest freq, LRU). After gets 4,3,2 the "
                        "freq-2 bucket holds {4,3,2} in touch-order. put(5) evicts the LRU of the lowest "
                        "non-empty freq bucket: minFreq is now 2 (bucket 1 emptied), and key 4 is the LRU "
                        "of bucket 2. So key 4 is evicted; final cache = {2,3,5}.",
         "tags": ["large", "mixed"]},
    ],
    "solutions": [
        {
            "title": "HashMap + Per-Frequency OrderedDict (O(1) optimal)",
            "time_complexity": "O(1) average for both get and put",
            "space_complexity": "O(capacity)",
            "description": (
                "Two hash maps plus a `minFreq` counter:\n"
                "- `key_to_val[key] = (value, freq)`\n"
                "- `freq_to_keys[freq] = OrderedDict()` — keys at that frequency, ordered by recency. "
                "The first inserted is the least recently used.\n\n"
                "**get(key)**: miss → -1. Hit → bump freq: remove key from old bucket, add to bucket "
                "`freq+1` (at the recent end). If old bucket empties and equals `minFreq`, increment "
                "`minFreq`. Return value.\n\n"
                "**put(key, value)**: if key exists, update value and bump freq (same as get). "
                "Else if size == capacity, evict `freq_to_keys[minFreq].popitem(last=False)` (LRU within "
                "the lowest-freq bucket). Insert new key at freq=1 and reset `minFreq = 1`."
            ),
            "code": {
                "python": (
                    "from collections import OrderedDict, defaultdict\n\n"
                    "class LFUCache:\n"
                    "    def __init__(self, capacity: int):\n"
                    "        self.cap = capacity\n"
                    "        self.size = 0\n"
                    "        self.min_freq = 0\n"
                    "        self.key_to_val = {}      # key -> (value, freq)\n"
                    "        self.freq_to_keys = defaultdict(OrderedDict)  # freq -> OrderedDict(key -> None)\n"
                    "\n"
                    "    def _bump(self, key):\n"
                    "        value, freq = self.key_to_val[key]\n"
                    "        del self.freq_to_keys[freq][key]\n"
                    "        if not self.freq_to_keys[freq]:\n"
                    "            del self.freq_to_keys[freq]\n"
                    "            if self.min_freq == freq:\n"
                    "                self.min_freq += 1\n"
                    "        self.key_to_val[key] = (value, freq + 1)\n"
                    "        self.freq_to_keys[freq + 1][key] = None\n"
                    "\n"
                    "    def get(self, key: int) -> int:\n"
                    "        if key not in self.key_to_val:\n"
                    "            return -1\n"
                    "        self._bump(key)\n"
                    "        return self.key_to_val[key][0]\n"
                    "\n"
                    "    def put(self, key: int, value: int) -> None:\n"
                    "        if self.cap == 0:\n"
                    "            return\n"
                    "        if key in self.key_to_val:\n"
                    "            _, freq = self.key_to_val[key]\n"
                    "            self.key_to_val[key] = (value, freq)\n"
                    "            self._bump(key)\n"
                    "            return\n"
                    "        if self.size == self.cap:\n"
                    "            evict_key, _ = self.freq_to_keys[self.min_freq].popitem(last=False)\n"
                    "            if not self.freq_to_keys[self.min_freq]:\n"
                    "                del self.freq_to_keys[self.min_freq]\n"
                    "            del self.key_to_val[evict_key]\n"
                    "            self.size -= 1\n"
                    "        self.key_to_val[key] = (value, 1)\n"
                    "        self.freq_to_keys[1][key] = None\n"
                    "        self.min_freq = 1\n"
                    "        self.size += 1"
                ),
                "javascript": (
                    "class LFUCache {\n"
                    "    constructor(capacity) {\n"
                    "        this.cap = capacity;\n"
                    "        this.size = 0;\n"
                    "        this.minFreq = 0;\n"
                    "        this.keyToVal = new Map();   // key -> [value, freq]\n"
                    "        this.freqToKeys = new Map(); // freq -> Map(key -> true) (insertion-ordered)\n"
                    "    }\n"
                    "    _bump(key) {\n"
                    "        const [value, freq] = this.keyToVal.get(key);\n"
                    "        const bucket = this.freqToKeys.get(freq);\n"
                    "        bucket.delete(key);\n"
                    "        if (bucket.size === 0) {\n"
                    "            this.freqToKeys.delete(freq);\n"
                    "            if (this.minFreq === freq) this.minFreq += 1;\n"
                    "        }\n"
                    "        this.keyToVal.set(key, [value, freq + 1]);\n"
                    "        if (!this.freqToKeys.has(freq + 1)) this.freqToKeys.set(freq + 1, new Map());\n"
                    "        this.freqToKeys.get(freq + 1).set(key, true);\n"
                    "    }\n"
                    "    get(key) {\n"
                    "        if (!this.keyToVal.has(key)) return -1;\n"
                    "        this._bump(key);\n"
                    "        return this.keyToVal.get(key)[0];\n"
                    "    }\n"
                    "    put(key, value) {\n"
                    "        if (this.cap === 0) return;\n"
                    "        if (this.keyToVal.has(key)) {\n"
                    "            const [, freq] = this.keyToVal.get(key);\n"
                    "            this.keyToVal.set(key, [value, freq]);\n"
                    "            this._bump(key);\n"
                    "            return;\n"
                    "        }\n"
                    "        if (this.size === this.cap) {\n"
                    "            const bucket = this.freqToKeys.get(this.minFreq);\n"
                    "            const evictKey = bucket.keys().next().value;\n"
                    "            bucket.delete(evictKey);\n"
                    "            if (bucket.size === 0) this.freqToKeys.delete(this.minFreq);\n"
                    "            this.keyToVal.delete(evictKey);\n"
                    "            this.size -= 1;\n"
                    "        }\n"
                    "        this.keyToVal.set(key, [value, 1]);\n"
                    "        if (!this.freqToKeys.has(1)) this.freqToKeys.set(1, new Map());\n"
                    "        this.freqToKeys.get(1).set(key, true);\n"
                    "        this.minFreq = 1;\n"
                    "        this.size += 1;\n"
                    "    }\n"
                    "}"
                ),
                "java": (
                    "class LFUCache {\n"
                    "    private final int cap;\n"
                    "    private int size = 0, minFreq = 0;\n"
                    "    private final Map<Integer, int[]> keyToVal = new HashMap<>();   // key -> {value, freq}\n"
                    "    private final Map<Integer, LinkedHashSet<Integer>> freqToKeys = new HashMap<>();\n"
                    "    public LFUCache(int capacity) { this.cap = capacity; }\n"
                    "    private void bump(int key) {\n"
                    "        int[] vf = keyToVal.get(key);\n"
                    "        LinkedHashSet<Integer> bucket = freqToKeys.get(vf[1]);\n"
                    "        bucket.remove(key);\n"
                    "        if (bucket.isEmpty()) {\n"
                    "            freqToKeys.remove(vf[1]);\n"
                    "            if (minFreq == vf[1]) minFreq++;\n"
                    "        }\n"
                    "        vf[1]++;\n"
                    "        freqToKeys.computeIfAbsent(vf[1], k -> new LinkedHashSet<>()).add(key);\n"
                    "    }\n"
                    "    public int get(int key) {\n"
                    "        if (!keyToVal.containsKey(key)) return -1;\n"
                    "        bump(key);\n"
                    "        return keyToVal.get(key)[0];\n"
                    "    }\n"
                    "    public void put(int key, int value) {\n"
                    "        if (cap == 0) return;\n"
                    "        if (keyToVal.containsKey(key)) {\n"
                    "            keyToVal.get(key)[0] = value;\n"
                    "            bump(key);\n"
                    "            return;\n"
                    "        }\n"
                    "        if (size == cap) {\n"
                    "            LinkedHashSet<Integer> bucket = freqToKeys.get(minFreq);\n"
                    "            int evict = bucket.iterator().next();\n"
                    "            bucket.remove(evict);\n"
                    "            if (bucket.isEmpty()) freqToKeys.remove(minFreq);\n"
                    "            keyToVal.remove(evict);\n"
                    "            size--;\n"
                    "        }\n"
                    "        keyToVal.put(key, new int[]{value, 1});\n"
                    "        freqToKeys.computeIfAbsent(1, k -> new LinkedHashSet<>()).add(key);\n"
                    "        minFreq = 1;\n"
                    "        size++;\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Doubly-Linked-List of Doubly-Linked-Lists",
            "time_complexity": "O(1) for both get and put",
            "space_complexity": "O(capacity)",
            "description": (
                "Replace the per-frequency `OrderedDict` with a hand-rolled doubly-linked list, and "
                "chain the buckets themselves into an outer doubly-linked list ordered by frequency. "
                "Each node knows its bucket; each bucket knows its frequency. On a hit, move the node "
                "from its bucket to the bucket with `freq + 1` (creating it adjacent if missing). "
                "Eviction is `head_bucket.tail.prev` (the LRU of the lowest-freq bucket).\n\n"
                "Why bother? In languages without an ordered-dict primitive (or where you want "
                "guaranteed O(1) without hash-map amortisation), this is the canonical structure. "
                "The Python OrderedDict version above is what most interviewers accept; the DLL-of-DLLs "
                "is the answer when the interviewer asks 'now do it without OrderedDict'."
            ),
            "code": {
                "python": (
                    "class _Node:\n"
                    "    __slots__ = ('key', 'val', 'freq', 'prev', 'next')\n"
                    "    def __init__(self, key=0, val=0, freq=1):\n"
                    "        self.key, self.val, self.freq = key, val, freq\n"
                    "        self.prev = self.next = None\n"
                    "\n"
                    "class _DLL:\n"
                    "    def __init__(self):\n"
                    "        self.head, self.tail = _Node(), _Node()\n"
                    "        self.head.next = self.tail\n"
                    "        self.tail.prev = self.head\n"
                    "        self.size = 0\n"
                    "    def push_front(self, n):\n"
                    "        n.prev, n.next = self.head, self.head.next\n"
                    "        self.head.next.prev = n\n"
                    "        self.head.next = n\n"
                    "        self.size += 1\n"
                    "    def remove(self, n):\n"
                    "        n.prev.next = n.next; n.next.prev = n.prev\n"
                    "        self.size -= 1\n"
                    "    def pop_back(self):\n"
                    "        if self.size == 0: return None\n"
                    "        n = self.tail.prev; self.remove(n); return n\n"
                    "\n"
                    "class LFUCache:\n"
                    "    def __init__(self, capacity: int):\n"
                    "        self.cap = capacity\n"
                    "        self.size = 0\n"
                    "        self.min_freq = 0\n"
                    "        self.nodes = {}      # key -> _Node\n"
                    "        self.buckets = {}    # freq -> _DLL\n"
                    "    def _touch(self, n):\n"
                    "        bucket = self.buckets[n.freq]\n"
                    "        bucket.remove(n)\n"
                    "        if bucket.size == 0:\n"
                    "            del self.buckets[n.freq]\n"
                    "            if self.min_freq == n.freq:\n"
                    "                self.min_freq += 1\n"
                    "        n.freq += 1\n"
                    "        if n.freq not in self.buckets:\n"
                    "            self.buckets[n.freq] = _DLL()\n"
                    "        self.buckets[n.freq].push_front(n)\n"
                    "    def get(self, key: int) -> int:\n"
                    "        if key not in self.nodes: return -1\n"
                    "        n = self.nodes[key]; self._touch(n); return n.val\n"
                    "    def put(self, key: int, value: int) -> None:\n"
                    "        if self.cap == 0: return\n"
                    "        if key in self.nodes:\n"
                    "            n = self.nodes[key]; n.val = value; self._touch(n); return\n"
                    "        if self.size == self.cap:\n"
                    "            bucket = self.buckets[self.min_freq]\n"
                    "            evict = bucket.pop_back()\n"
                    "            if bucket.size == 0: del self.buckets[self.min_freq]\n"
                    "            del self.nodes[evict.key]\n"
                    "            self.size -= 1\n"
                    "        n = _Node(key, value, 1)\n"
                    "        self.nodes[key] = n\n"
                    "        if 1 not in self.buckets: self.buckets[1] = _DLL()\n"
                    "        self.buckets[1].push_front(n)\n"
                    "        self.min_freq = 1\n"
                    "        self.size += 1"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Re-read the eviction rule: lowest frequency, tie-break LRU. Two orderings to maintain at once.",
        "2. Frequency lookup needs to be O(1): a hash map `key → (value, freq)` is forced.",
        "3. Eviction must be O(1): we cannot scan for the min-freq key. Track `minFreq` and bucket keys by frequency.",
        "4. Within a bucket, eviction must pick the LRU. So each bucket is itself an ordered structure — OrderedDict (or DLL).",
        "5. On every access, the key's freq increases by 1. So 'access' = remove from old bucket, append to new bucket. O(1).",
        "6. `minFreq` only changes in two situations: new key inserted (set to 1), or current min-bucket emptied by an access (increment).",
        "7. Capacity 0 is its own branch — never enter the eviction code path with empty structures.",
        "8. Update path of `put` on existing key reuses the access bump — write `_bump` once, call from both `get` and update-`put`.",
    ],
    "tips": [
        "Most candidates conflate LRU and LFU. State explicitly: 'LRU evicts by recency; LFU evicts by frequency, then by recency as tiebreaker.' Interviewers love the precision.",
        "Python's `OrderedDict.popitem(last=False)` is the textbook one-liner for 'pop the LRU'. Mention it; it makes the bucket ordering trivial.",
        "Bug magnet: forgetting to update `minFreq` when the old bucket empties on a `_bump`. Walk the interviewer through that branch deliberately.",
        "Bug magnet: capacity 0. Add the early-return in `put` and call it out — interviewers throw it at you as a follow-up if you don't.",
        "Follow-up: 'what if frequency is bounded?' — a frequency array indexed by freq beats the hash map. Mention it as a constant-factor optimisation, not a complexity change.",
    ],
    "companies": ["Amazon", "Google", "Meta", "Microsoft", "Bloomberg", "Apple"],
    "topics": ["Hash Table", "Linked List", "Doubly-Linked List", "Design", "OrderedDict"],
    "time_complexity": "O(1)",
    "space_complexity": "O(capacity)",
}


def REFERENCE(input):
    """Class-ops driver: replay the operation sequence and return per-op results."""
    from collections import OrderedDict, defaultdict

    class LFUCache:
        def __init__(self, capacity):
            self.cap = capacity
            self.size = 0
            self.min_freq = 0
            self.key_to_val = {}
            self.freq_to_keys = defaultdict(OrderedDict)

        def _bump(self, key):
            value, freq = self.key_to_val[key]
            del self.freq_to_keys[freq][key]
            if not self.freq_to_keys[freq]:
                del self.freq_to_keys[freq]
                if self.min_freq == freq:
                    self.min_freq += 1
            self.key_to_val[key] = (value, freq + 1)
            self.freq_to_keys[freq + 1][key] = None

        def get(self, key):
            if key not in self.key_to_val:
                return -1
            self._bump(key)
            return self.key_to_val[key][0]

        def put(self, key, value):
            if self.cap == 0:
                return None
            if key in self.key_to_val:
                _, freq = self.key_to_val[key]
                self.key_to_val[key] = (value, freq)
                self._bump(key)
                return None
            if self.size == self.cap:
                evict_key, _ = self.freq_to_keys[self.min_freq].popitem(last=False)
                if not self.freq_to_keys[self.min_freq]:
                    del self.freq_to_keys[self.min_freq]
                del self.key_to_val[evict_key]
                self.size -= 1
            self.key_to_val[key] = (value, 1)
            self.freq_to_keys[1][key] = None
            self.min_freq = 1
            self.size += 1
            return None

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "LFUCache":
            instance = LFUCache(*a)
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


# Add the entry field for class_ops dispatch
PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "LFUCache",
    "constructor": {"params": [{"name": "capacity", "type": "int"}]},
    "methods": [
        {"name": "get", "params": [{"name": "key", "type": "int"}], "returns": "int"},
        {"name": "put", "params": [{"name": "key", "type": "int"}, {"name": "value", "type": "int"}],
         "returns": "any"},
    ],
}


register(PAYLOAD, REFERENCE)
