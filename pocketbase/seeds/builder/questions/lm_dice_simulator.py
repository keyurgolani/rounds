"""Dice Rolling Simulator — Easy/Medium. Logical & Maintainable.

Roll N dice K times, compute mean, median, mode of the sums.
Deterministic random for testing (seed) is the L&M signal."""
from builder.registry import register


PAYLOAD = {
    "title": "Dice Rolling Simulator (Statistics)",
    "difficulty": "Medium",
    "description": (
        "Implement a dice-rolling simulator. Given:\n"
        "- `num_dice` — number of dice rolled per trial.\n"
        "- `num_rolls` — number of trials.\n"
        "- `sides` — sides per die (defaults to 6).\n"
        "- `seed` — random seed for deterministic testing.\n\n"
        "Return a dict containing the **mean**, **median**, and **mode** of the per-trial sums.\n\n"
        "**Test framing:** because output depends on the RNG, the harness fixes the seed and the reference "
        "implementation uses Python's `random.Random(seed)` so results are reproducible.\n\n"
        "**Example (seed = 0):**\n"
        "- `simulate(num_dice=2, num_rolls=4, sides=6, seed=0)`\n"
        "- Returns `{'mean': ..., 'median': ..., 'mode': ...}` (exact values depend on the RNG)."
    ),
    "hints": [
        "Mean = sum(sums) / num_rolls.",
        "Median = sorted middle (or average of two middles for even count).",
        "Mode = most-frequent sum; tie-break is unspecified in interview, so pick smallest or any (document).",
        "Inject the seed — don't read system time. Tests need determinism.",
        "Edge cases: num_rolls = 0 (undefined stats — return None or zeros), num_dice = 0 (sum is always 0), sides = 1 (sum is always num_dice).",
    ],
    "constraints": [
        "1 <= num_dice <= 100",
        "0 <= num_rolls <= 10⁵",
        "1 <= sides <= 100",
    ],
    "starter_code": {
        "python": "def simulate(num_dice, num_rolls, sides, seed):\n    # Your code here\n    pass",
        "javascript": "function simulate(numDice, numRolls, sides, seed) {\n    // Your code here\n}",
        "java": "public Map<String, Object> simulate(int numDice, int numRolls, int sides, long seed) {\n    // Your code here\n    return Map.of();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(simulate(2, 4, 6, 0))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"num_dice": 1, "num_rolls": 0, "sides": 6, "seed": 0},
         "expected": {"mean": None, "median": None, "mode": None},
         "description": "Zero rolls — undefined stats", "tags": ["edge"]},
        {"input": {"num_dice": 0, "num_rolls": 5, "sides": 6, "seed": 0},
         "expected": {"mean": 0, "median": 0, "mode": 0},
         "description": "Zero dice — every sum is 0", "tags": ["edge"]},
        {"input": {"num_dice": 1, "num_rolls": 1, "sides": 1, "seed": 0},
         "expected": {"mean": 1, "median": 1, "mode": 1},
         "description": "One die with one side — always 1", "tags": ["edge"]},
        {"input": {"num_dice": 1, "num_rolls": 5, "sides": 1, "seed": 42},
         "expected": {"mean": 1, "median": 1, "mode": 1},
         "description": "Five rolls of a 1-sided die", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Direct Simulation (Optimal)",
            "time_complexity": "O(num_rolls · num_dice)",
            "space_complexity": "O(num_rolls)",
            "description": (
                "Use a seeded RNG. For each trial, sum `num_dice` random rolls. Compute mean/median/mode "
                "from the resulting list of sums."
            ),
            "code": {
                "python": (
                    "import random\n"
                    "from collections import Counter\n\n"
                    "def simulate(num_dice, num_rolls, sides, seed):\n"
                    "    if num_rolls == 0:\n"
                    "        return {'mean': None, 'median': None, 'mode': None}\n"
                    "    rng = random.Random(seed)\n"
                    "    sums = []\n"
                    "    for _ in range(num_rolls):\n"
                    "        s = sum(rng.randint(1, sides) for _ in range(num_dice))\n"
                    "        sums.append(s)\n"
                    "    mean = sum(sums) / num_rolls\n"
                    "    sorted_sums = sorted(sums)\n"
                    "    n = len(sorted_sums)\n"
                    "    median = (sorted_sums[n // 2] if n % 2 == 1\n"
                    "              else (sorted_sums[n // 2 - 1] + sorted_sums[n // 2]) / 2)\n"
                    "    counts = Counter(sums)\n"
                    "    max_count = max(counts.values())\n"
                    "    mode = min(s for s, c in counts.items() if c == max_count)\n"
                    "    return {'mean': mean, 'median': median, 'mode': mode}"
                ),
            },
        },
        {
            "title": "Histogram (Better at Scale)",
            "time_complexity": "O(num_rolls · num_dice + range)",
            "space_complexity": "O(range)",
            "description": (
                "Sums are bounded: `[num_dice, num_dice · sides]`. Bucket each sum into a fixed-size array "
                "indexed by sum. Mean = weighted average; median = walk the cumulative distribution; mode "
                "= argmax of the buckets. O(range) post-processing instead of O(num_rolls log num_rolls)."
            ),
            "code": {
                "python": (
                    "# Sketch — preferred when num_rolls is huge but range is small.\n"
                    "import random\n"
                    "def simulate(num_dice, num_rolls, sides, seed):\n"
                    "    raise NotImplementedError(\n"
                    "        'Bucket sums into a histogram of size num_dice*(sides) + 1. Compute stats from histogram.'\n"
                    "    )"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Inject the seed — never use the system clock. Tests must be deterministic.",
        "2. Simulate: nested loop, sum each trial.",
        "3. Mean: total / count.",
        "4. Median: sort, take middle (or avg of two middles).",
        "5. Mode: Counter.most_common, with explicit tie-break.",
        "6. Edge cases: zero rolls (undefined stats), zero dice (all zeros), one-sided die (constant), tied modes.",
    ],
    "tips": [
        "Don't import `random` and forget to seed it — the global state is shared across tests and breaks determinism.",
        "If multiple modes tie, the standard library `statistics.mode` raises in Python <3.8 and picks the smallest in 3.8+. Pin behaviour explicitly.",
        "For very large num_rolls, a histogram beats sorted-list median by avoiding the O(N log N) sort.",
        "Common follow-up: 'add per-die-side weighting' (loaded dice). Replace `randint` with a weighted sampler.",
        "Common follow-up: 'streaming statistics — compute as rolls arrive.' Welford's algorithm for mean/variance; running sum of buckets for histogram-based median.",
    ],
    "companies": ["Amazon", "Bloomberg"],
    "topics": ["Math", "Statistics", "Randomness"],
    "time_complexity": "O(num_rolls · num_dice)",
    "space_complexity": "O(num_rolls)",
}


def REFERENCE(num_dice, num_rolls, sides, seed):
    import random
    from collections import Counter
    if num_rolls == 0:
        return {"mean": None, "median": None, "mode": None}
    rng = random.Random(seed)
    sums = []
    for _ in range(num_rolls):
        s = sum(rng.randint(1, sides) for _ in range(num_dice))
        sums.append(s)
    mean = sum(sums) / num_rolls
    if mean == int(mean):
        mean = int(mean)
    sorted_sums = sorted(sums)
    n = len(sorted_sums)
    if n % 2 == 1:
        median = sorted_sums[n // 2]
    else:
        median_avg = (sorted_sums[n // 2 - 1] + sorted_sums[n // 2]) / 2
        median = int(median_avg) if median_avg == int(median_avg) else median_avg
    counts = Counter(sums)
    max_count = max(counts.values())
    mode = min(s for s, c in counts.items() if c == max_count)
    return {"mean": mean, "median": median, "mode": mode}


register(PAYLOAD, REFERENCE)
