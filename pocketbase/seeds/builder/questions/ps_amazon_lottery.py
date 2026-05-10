"""Amazon Lottery — Medium. Weighted Random Selection.

Pick K winners from a list of orders weighted by purchase price. Build
a prefix-sum array; binary-search a random number into it. O(N) build,
O(log N) per pick."""
from builder.registry import register


PAYLOAD = {
    "title": "Amazon Lottery (Weighted Random Selection)",
    "difficulty": "Medium",
    "description": (
        "Customers enter a lottery by making a purchase. Each order is `(customer_id, price)`. The "
        "probability of winning is proportional to price (a `$10` purchase is 10× more likely to win than "
        "`$1`).\n\n"
        "Implement `pick_winners(orders, k, seed)` returning a list of `k` distinct customer ids drawn "
        "WITHOUT replacement, weighted by their TOTAL purchase price across all their orders. Use "
        "`random.Random(seed)` for determinism.\n\n"
        "If a customer has multiple orders, sum their prices.\n\n"
        "If `k > number of distinct customers`, return all customers in any deterministic order.\n\n"
        "**Test framing:** seed-bound RNG ensures the harness gets reproducible results."
    ),
    "hints": [
        "Aggregate per-customer total spend.",
        "Weighted random selection: build a prefix-sum array of weights. Pick a random number in `[0, total)`. Binary-search to find the index whose prefix range contains it.",
        "Without replacement: after each pick, remove the chosen customer's weight (set to 0) and rebuild prefix sums — or use the alias method, or just reject duplicates.",
        "Brute force: build a list with each customer appearing `weight` times. Random.choice. Memory-bounded but conceptually correct.",
        "Edge cases: zero customers, k=0, k > distinct customers, single customer, all-zero weights (treat as uniform).",
    ],
    "constraints": [
        "0 <= |orders| <= 10⁴",
        "0 <= price <= 10⁵",
        "1 <= k <= 10⁴",
    ],
    "starter_code": {
        "python": "def pick_winners(orders, k, seed):\n    # Your code here\n    pass",
        "javascript": "function pickWinners(orders, k, seed) {\n    // Your code here\n}",
        "java": "public List<String> pickWinners(List<Object[]> orders, int k, long seed) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(pick_winners([('a', 10), ('b', 1), ('c', 1)], 1, 0))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"orders": [["a", 100]], "k": 1, "seed": 0},
         "expected": {"$match": "validator",
                       "description": "Single customer always wins regardless of RNG",
                       "code": "lambda inp, out: out == ['a']"},
         "description": "Single customer wins by default", "tags": ["edge"]},
        {"input": {"orders": [], "k": 1, "seed": 0}, "expected": [],
         "description": "Empty orders", "tags": ["edge"]},
        {"input": {"orders": [["a", 0], ["b", 0]], "k": 1, "seed": 0},
         "expected": {"$match": "any_of", "values": [["a"], ["b"]]},
         "description": "All-zero weights — treat as uniform", "tags": ["edge"]},
        {"input": {"orders": [["a", 100], ["b", 100], ["c", 100]], "k": 5, "seed": 0},
         "expected": {"$match": "validator",
                       "description": "All distinct customers returned",
                       "code": "lambda inp, out: ("
                               "isinstance(out, list) and "
                               "set(out) == {'a', 'b', 'c'} and "
                               "len(out) == 3"
                               ")"},
         "description": "k > distinct customers — return all", "tags": ["edge"]},
        {"input": {"orders": [["a", 1000], ["b", 1]], "k": 2, "seed": 0},
         "expected": {"$match": "validator",
                       "description": "Both customers picked, distinct",
                       "code": "lambda inp, out: ("
                               "isinstance(out, list) and len(out) == 2 and "
                               "set(out) == {'a', 'b'}"
                               ")"},
         "description": "k=2 from 2 customers — both win", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Prefix Sum + Binary Search (Optimal)",
            "time_complexity": "O(N + k log N)",
            "space_complexity": "O(N)",
            "description": (
                "Aggregate per-customer total. Build a prefix-sum array of weights and a parallel id "
                "array. For each pick, draw a random number in `[0, total_remaining)`, binary-search the "
                "prefix sum, take the corresponding id, and rebuild the prefix sums excluding that id "
                "(or use the alias method for true O(1) sampling)."
            ),
            "code": {
                "python": (
                    "import random\n"
                    "from collections import defaultdict\n"
                    "from bisect import bisect_left\n\n"
                    "def pick_winners(orders, k, seed):\n"
                    "    weights = defaultdict(int)\n"
                    "    for cid, price in orders:\n"
                    "        weights[cid] += price\n"
                    "    customers = list(weights.keys())\n"
                    "    if not customers:\n"
                    "        return []\n"
                    "    rng = random.Random(seed)\n"
                    "    if k >= len(customers):\n"
                    "        # Return everyone in deterministic (insertion) order\n"
                    "        return customers\n"
                    "    if all(weights[c] == 0 for c in customers):\n"
                    "        # Uniform fallback\n"
                    "        return rng.sample(customers, k)\n"
                    "    chosen = []\n"
                    "    used = set()\n"
                    "    for _ in range(k):\n"
                    "        avail = [c for c in customers if c not in used]\n"
                    "        prefix = []\n"
                    "        s = 0\n"
                    "        for c in avail:\n"
                    "            s += weights[c]\n"
                    "            prefix.append(s)\n"
                    "        if s == 0:\n"
                    "            # All remaining have zero weight; uniform among them\n"
                    "            pick = rng.choice(avail)\n"
                    "        else:\n"
                    "            r = rng.random() * s\n"
                    "            idx = bisect_left(prefix, r)\n"
                    "            if idx == len(prefix): idx -= 1\n"
                    "            pick = avail[idx]\n"
                    "        chosen.append(pick)\n"
                    "        used.add(pick)\n"
                    "    return chosen"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Aggregate per-customer total weight (a customer with multiple orders pools).",
        "2. Without replacement: each pick reduces the pool. Naive approach rebuilds the prefix sums — O(k · N).",
        "3. Better: alias method or Walker's tables for O(1) sampling — but won't naturally support without-replacement.",
        "4. Brute force: each customer appears `weight` times; random sample. Memory-heavy.",
        "5. Use a seeded RNG; never the global one.",
        "6. Edge cases: empty, k > distinct, all-zero weights, single customer.",
    ],
    "tips": [
        "Without replacement is the trap. Easy to write 'k draws from prefix sum' that returns the same customer repeatedly.",
        "The alias method gives O(1) sampling but assumes with-replacement; tooling for without is more complex.",
        "Cents-as-int prices avoid float drift in the prefix sum; if you can guarantee integer prices, prefer that.",
        "Common follow-up: 'non-linear weighting (e.g. quadratic).' Same algorithm — substitute the weight function.",
        "Common follow-up: 'streaming / can't fit all orders in memory.' Reservoir sampling, or rolling weight aggregation with periodic compaction.",
    ],
    "companies": ["Amazon", "Lyft", "DoorDash"],
    "topics": ["Randomness", "Prefix Sum", "Binary Search"],
    "time_complexity": "O(N + k · N) naive without-replacement",
    "space_complexity": "O(N)",
}


def REFERENCE(orders, k, seed):
    import random
    from collections import defaultdict
    from bisect import bisect_left

    weights = defaultdict(int)
    for cid, price in orders:
        weights[cid] += price
    customers = list(weights.keys())
    if not customers:
        return []
    rng = random.Random(seed)
    if k >= len(customers):
        return customers
    if all(weights[c] == 0 for c in customers):
        return rng.sample(customers, k)
    chosen = []
    used = set()
    for _ in range(k):
        avail = [c for c in customers if c not in used]
        prefix = []
        s = 0
        for c in avail:
            s += weights[c]
            prefix.append(s)
        if s == 0:
            pick = rng.choice(avail)
        else:
            r = rng.random() * s
            idx = bisect_left(prefix, r)
            if idx == len(prefix):
                idx -= 1
            pick = avail[idx]
        chosen.append(pick)
        used.add(pick)
    return chosen


register(PAYLOAD, REFERENCE)
