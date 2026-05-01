"""Candy Distribution — Hard. Greedy / Two-Pass.

Each child gets >= 1 candy; higher-rated children get strictly more
than lower-rated neighbours. Minimise total candies. Two-pass greedy
sweeps the array left-to-right then right-to-left, taking the max."""
from builder.registry import register


PAYLOAD = {
    "title": "Candy Distribution",
    "difficulty": "Hard",
    "description": (
        "There are `n` children standing in a line, each with a rating in `ratings[i]`. You distribute "
        "candies subject to two rules:\n"
        "1. Each child gets **at least one** candy.\n"
        "2. Children with a **higher rating than their direct neighbour** must receive **more** candies than "
        "that neighbour.\n\n"
        "Return the minimum total candies you must distribute.\n\n"
        "**Example 1:**\n"
        "- Input: `ratings = [1, 0, 2]`\n"
        "- Output: `5` (distribute `[2, 1, 2]` — total 5)\n\n"
        "**Example 2:**\n"
        "- Input: `ratings = [1, 2, 2]`\n"
        "- Output: `4` (distribute `[1, 2, 1]` — note: the third child equals (not exceeds) the second, so "
        "rule 2 doesn't apply between them)"
    ),
    "hints": [
        "Brute force: iterate, fixing every violation by adding 1. Loops until stable. Correct, but O(n²) worst case.",
        "Two-pass greedy: pass 1 left-to-right (handle 'higher than left neighbour'), pass 2 right-to-left (handle 'higher than right neighbour'), take max at each index. O(n).",
        "Single-pass slope: walk once, tracking ascending and descending run lengths. Add up the triangular-number sums plus a correction for the peak. O(n) time, O(1) space.",
        "Critical detail: rule 2 applies only when STRICTLY greater — equal ratings impose no constraint.",
        "Edge cases: single child (1 candy), all equal ratings (n candies), strictly ascending, strictly descending, valley.",
    ],
    "constraints": [
        "1 <= n <= 10⁴",
        "0 <= ratings[i] <= 10⁴",
    ],
    "starter_code": {
        "python": "def candy(ratings):\n    # Your code here\n    pass",
        "javascript": "function candy(ratings) {\n    // Your code here\n}",
        "java": "public int candy(int[] ratings) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(candy([1, 0, 2]))   # 5\n"
            "    print(candy([1, 2, 2]))   # 4"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ratings": [1, 0, 2]}, "expected": 5,
         "description": "Valley shape", "tags": ["basic"]},
        {"input": {"ratings": [1, 2, 2]}, "expected": 4,
         "description": "Equal ratings — no constraint between equals", "tags": ["basic"]},
        {"input": {"ratings": [1]}, "expected": 1,
         "description": "Single child", "tags": ["edge"]},
        {"input": {"ratings": [5, 5, 5]}, "expected": 3,
         "description": "All equal — 1 each", "tags": ["edge"]},
        {"input": {"ratings": [1, 2, 3, 4, 5]}, "expected": 15,
         "description": "Strict ascending — 1+2+3+4+5", "tags": ["edge"]},
        {"input": {"ratings": [5, 4, 3, 2, 1]}, "expected": 15,
         "description": "Strict descending — same total by symmetry", "tags": ["edge"]},
        {"input": {"ratings": [1, 3, 2, 2, 1]}, "expected": 7,
         "description": "Peak at index 1, descending tail", "tags": ["tricky"]},
        {"input": {"ratings": [1, 2, 87, 87, 87, 2, 1]}, "expected": 13,
         "description": "Plateau in the middle, ascending and descending sides",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Two-Pass Greedy (Most Readable)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Pass 1 (left to right): if `ratings[i] > ratings[i-1]`, give `candies[i-1] + 1`, else 1. "
                "Pass 2 (right to left): if `ratings[i] > ratings[i+1]`, give `max(candies[i], "
                "candies[i+1] + 1)`. Sum. Each pass enforces one direction; the max ensures both rules are "
                "satisfied simultaneously."
            ),
            "code": {
                "python": (
                    "def candy(ratings):\n"
                    "    n = len(ratings)\n"
                    "    candies = [1] * n\n"
                    "    for i in range(1, n):\n"
                    "        if ratings[i] > ratings[i - 1]:\n"
                    "            candies[i] = candies[i - 1] + 1\n"
                    "    for i in range(n - 2, -1, -1):\n"
                    "        if ratings[i] > ratings[i + 1]:\n"
                    "            candies[i] = max(candies[i], candies[i + 1] + 1)\n"
                    "    return sum(candies)"
                ),
                "javascript": (
                    "function candy(ratings) {\n"
                    "    const n = ratings.length;\n"
                    "    const candies = new Array(n).fill(1);\n"
                    "    for (let i = 1; i < n; i++) if (ratings[i] > ratings[i-1]) candies[i] = candies[i-1] + 1;\n"
                    "    for (let i = n - 2; i >= 0; i--) if (ratings[i] > ratings[i+1]) candies[i] = Math.max(candies[i], candies[i+1] + 1);\n"
                    "    return candies.reduce((a, b) => a + b, 0);\n"
                    "}"
                ),
                "java": (
                    "public int candy(int[] ratings) {\n"
                    "    int n = ratings.length;\n"
                    "    int[] candies = new int[n];\n"
                    "    Arrays.fill(candies, 1);\n"
                    "    for (int i = 1; i < n; i++) if (ratings[i] > ratings[i-1]) candies[i] = candies[i-1] + 1;\n"
                    "    for (int i = n - 2; i >= 0; i--) if (ratings[i] > ratings[i+1]) candies[i] = Math.max(candies[i], candies[i+1] + 1);\n"
                    "    int sum = 0; for (int c : candies) sum += c; return sum;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Single-Pass Slope (O(1) space)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk once tracking ascending run length `up`, descending run length `down`, and `peak` "
                "height. On a flat or direction change, contribute the triangular sum 1+2+…+up + "
                "1+2+…+down minus an adjustment for the peak (counted once, not twice). Tightest possible "
                "but trickier to derive on the fly."
            ),
            "code": {
                "python": (
                    "def candy(ratings):\n"
                    "    n = len(ratings)\n"
                    "    if n <= 1:\n"
                    "        return n\n"
                    "    total = 1\n"
                    "    up = down = peak = 0\n"
                    "    for i in range(1, n):\n"
                    "        if ratings[i] > ratings[i - 1]:\n"
                    "            up += 1; down = 0; peak = up\n"
                    "            total += 1 + up\n"
                    "        elif ratings[i] == ratings[i - 1]:\n"
                    "            up = down = peak = 0\n"
                    "            total += 1\n"
                    "        else:\n"
                    "            up = 0; down += 1\n"
                    "            total += 1 + down - (1 if peak >= down else 0)\n"
                    "    return total"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Read both rules carefully — rule 2 fires only on STRICT inequality. Equal ratings are unconstrained.",
        "2. Realise a single pass can't see both neighbours simultaneously: a left-to-right pass alone misses 'higher than right neighbour'. Hence two passes.",
        "3. Pass 1: enforce 'higher than left neighbour'. Pass 2: enforce 'higher than right neighbour'. Take max at each index.",
        "4. Sum the per-child candies. O(n) time, O(n) space.",
        "5. To get O(1) space, fold the two passes into one with slope tracking. Optional optimisation.",
        "6. Edge cases: n=1, all equal, strict ascending, strict descending, plateaus, valleys.",
    ],
    "tips": [
        "Don't initialise candies to 0 — every child must get at least 1. Off-by-one waiting to happen.",
        "Equal ratings are unconstrained: if you accidentally enforce strict ordering, you'll overcount.",
        "If asked about cyclic neighbours (children in a circle), the two-pass approach generalises but you need a tiebreaker pass to handle the wrap-around.",
        "Common follow-up: 'allow equal candies for equal ratings.' That's the default of this problem; the trap is some candidates impose strict inequality unprompted.",
        "Common follow-up: 'minimise the maximum candy.' Different objective — switch to binary search on the max.",
    ],
    "companies": ["Amazon", "Google", "Microsoft"],
    "topics": ["Greedy", "Array", "Two Pointers"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(ratings):
    n = len(ratings)
    candies = [1] * n
    for i in range(1, n):
        if ratings[i] > ratings[i - 1]:
            candies[i] = candies[i - 1] + 1
    for i in range(n - 2, -1, -1):
        if ratings[i] > ratings[i + 1]:
            candies[i] = max(candies[i], candies[i + 1] + 1)
    return sum(candies)


register(PAYLOAD, REFERENCE)
