"""Koko Eating Bananas — Medium. Binary Search on the Answer.

The canonical 'binary search on the answer' question. The candidate's
job is to recognise that the *answer* (eating speed k) lives on a
monotone predicate — `hours(k) <= h` flips from False to True exactly
once as k grows — and to binary-search the answer space [1, max(piles)]
rather than the input array. Same template as Capacity to Ship Packages
in D Days (LC 1011), Split Array Largest Sum (LC 410), and Find K-th
Smallest Pair Distance (LC 719). Worth drilling because the predicate
shape repeats across a dozen interview questions.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Koko Eating Bananas",
    "difficulty": "Medium",
    "description": (
        "Koko loves to eat bananas. There are `n` piles of bananas, the i-th pile has `piles[i]` bananas. "
        "The guards have gone and will come back in `h` hours.\n\n"
        "Koko can decide her bananas-per-hour eating speed of `k`. Each hour, she chooses some pile of "
        "bananas and eats `k` bananas from that pile. If the pile has less than `k` bananas, she eats all "
        "of them instead and **will not eat any more bananas during that hour**.\n\n"
        "Koko likes to eat slowly but still wants to finish eating all the bananas before the guards return.\n\n"
        "Return the **minimum integer** `k` such that she can eat all the bananas within `h` hours.\n\n"
        "**Example 1:**\n"
        "- Input: `piles = [3,6,7,11], h = 8`\n"
        "- Output: `4`\n\n"
        "**Example 2:**\n"
        "- Input: `piles = [30,11,23,4,20], h = 5`\n"
        "- Output: `30`\n"
        "- Explanation: With h equal to the number of piles, she must finish each pile in exactly one hour, "
        "so k must be at least `max(piles)`.\n\n"
        "**Example 3:**\n"
        "- Input: `piles = [30,11,23,4,20], h = 6`\n"
        "- Output: `23`"
    ),
    "hints": [
        "What's the search space? k must be at least 1 (eating zero never finishes) and at most `max(piles)` "
        "(any larger and she still finishes each pile in exactly 1 hour — wasted speed).",
        "Define a predicate: `can_finish(k)` = 'eating at speed k, total hours used ≤ h'. As k grows, hours "
        "monotonically *decrease* — so the predicate is False then True exactly once. Perfect for binary search.",
        "Hours for one pile at speed k is `ceil(pile / k)`. Compute as `(pile + k - 1) // k` to stay in integer "
        "arithmetic — `math.ceil(pile / k)` is fine but float division on 10⁹-sized inputs is a smell.",
        "Standard 'find leftmost True' binary search: while `lo < hi`, `mid = (lo + hi) // 2`; if "
        "`can_finish(mid)`, set `hi = mid`, else `lo = mid + 1`. Return `lo`.",
        "Brute force linear scan from k=1 upward works for small `max(piles)` but is O(max_pile · n). With "
        "`max(piles)` up to 10⁹ it's hopeless — state it as the baseline, then upgrade.",
    ],
    "constraints": [
        "1 <= piles.length <= 10⁴",
        "piles.length <= h <= 10⁹",
        "1 <= piles[i] <= 10⁹",
    ],
    "starter_code": {
        "python": "def min_eating_speed(piles, h):\n    # Your code here\n    pass",
        "javascript": "function minEatingSpeed(piles, h) {\n    // Your code here\n}",
        "java": "public int minEatingSpeed(int[] piles, int h) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([3,6,7,11], 8), ([30,11,23,4,20], 5), ([30,11,23,4,20], 6)]\n"
            "    for piles, h in cases:\n"
            "        print(f\"min_eating_speed({piles}, {h}) = {min_eating_speed(piles, h)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[3,6,7,11], 8], [[30,11,23,4,20], 5], [[30,11,23,4,20], 6]].forEach(([piles, h]) =>\n"
            "    console.log(`minEatingSpeed =`, minEatingSpeed(piles, h))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.minEatingSpeed(new int[]{3,6,7,11}, 8));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"piles": [3, 6, 7, 11], "h": 8}, "expected": 4,
         "description": "Canonical example — k=4 finishes in 2+2+2+3=9? No: ceil(3/4)+ceil(6/4)+ceil(7/4)+ceil(11/4)=1+2+2+3=8",
         "tags": ["basic"]},
        {"input": {"piles": [30, 11, 23, 4, 20], "h": 5}, "expected": 30,
         "description": "h equals pile count — must finish the largest pile in one hour", "tags": ["edge"]},
        {"input": {"piles": [30, 11, 23, 4, 20], "h": 6}, "expected": 23,
         "description": "One extra hour of slack — speed drops to 23", "tags": ["basic"]},
        {"input": {"piles": [1], "h": 1}, "expected": 1,
         "description": "Single pile, one hour — k=1 suffices", "tags": ["edge"]},
        {"input": {"piles": [1000000000], "h": 2}, "expected": 500000000,
         "description": "Max single pile, 2 hours — half-speed answer; tests integer overflow / large search space",
         "tags": ["large"]},
        {"input": {"piles": [5, 5, 5, 5], "h": 4}, "expected": 5,
         "description": "h equals pile count, all equal — answer is the pile size", "tags": ["edge"]},
        {"input": {"piles": [2, 2], "h": 10}, "expected": 1,
         "description": "Plenty of slack — minimum speed of 1 finishes in 4 hours", "tags": ["edge"]},
        {"input": {"piles": [805306368, 805306368, 805306368], "h": 1000000000}, "expected": 3,
         "description": "Three near-max piles, 10⁹ hours — speed of 3 finishes; tests big-h corner",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Binary Search on the Answer (Optimal)",
            "time_complexity": "O(n log(max_pile))",
            "space_complexity": "O(1)",
            "description": (
                "Binary search the eating speed k in `[1, max(piles)]`. The predicate `hours(k) <= h` is "
                "monotone in k — slower → more hours, faster → fewer hours — so we 'find leftmost True'. "
                "Hours per pile is `ceil(pile / k) = (pile + k - 1) // k`."
            ),
            "code": {
                "python": (
                    "def min_eating_speed(piles, h):\n"
                    "    def hours(k):\n"
                    "        return sum((p + k - 1) // k for p in piles)\n"
                    "    lo, hi = 1, max(piles)\n"
                    "    while lo < hi:\n"
                    "        mid = (lo + hi) // 2\n"
                    "        if hours(mid) <= h:\n"
                    "            hi = mid\n"
                    "        else:\n"
                    "            lo = mid + 1\n"
                    "    return lo"
                ),
                "javascript": (
                    "function minEatingSpeed(piles, h) {\n"
                    "    const hours = (k) => piles.reduce((s, p) => s + Math.ceil(p / k), 0);\n"
                    "    let lo = 1, hi = Math.max(...piles);\n"
                    "    while (lo < hi) {\n"
                    "        const mid = (lo + hi) >> 1;\n"
                    "        if (hours(mid) <= h) hi = mid;\n"
                    "        else lo = mid + 1;\n"
                    "    }\n"
                    "    return lo;\n"
                    "}"
                ),
                "java": (
                    "public int minEatingSpeed(int[] piles, int h) {\n"
                    "    int lo = 1, hi = 0;\n"
                    "    for (int p : piles) hi = Math.max(hi, p);\n"
                    "    while (lo < hi) {\n"
                    "        int mid = lo + (hi - lo) / 2;\n"
                    "        long hours = 0;\n"
                    "        for (int p : piles) hours += (p + mid - 1) / mid;\n"
                    "        if (hours <= h) hi = mid;\n"
                    "        else lo = mid + 1;\n"
                    "    }\n"
                    "    return lo;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force Linear Scan (Baseline)",
            "time_complexity": "O(max_pile · n)",
            "space_complexity": "O(1)",
            "description": (
                "Try every k starting from 1 and return the first that finishes in ≤ h hours. Correct, but "
                "with `max(piles)` up to 10⁹ this is hopeless — state it as the baseline you'd never submit."
            ),
            "code": {
                "python": (
                    "def min_eating_speed(piles, h):\n"
                    "    def hours(k):\n"
                    "        return sum((p + k - 1) // k for p in piles)\n"
                    "    k = 1\n"
                    "    while hours(k) > h:\n"
                    "        k += 1\n"
                    "    return k"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise this as 'binary search on the answer', not on the input. The array is unsorted and order doesn't matter — what matters is the *speed* k, which lives on a monotone predicate.",
        "2. Bound the search space: k must be ≥ 1 (no zero) and ≤ max(piles) (anything larger still takes one hour per pile — wasted).",
        "3. Define the predicate: at speed k, total hours = sum of ceil(piles[i] / k). The predicate `hours(k) <= h` is monotone in k.",
        "4. Apply 'find leftmost True' binary search: collapse the boundary towards the smallest k that satisfies the predicate.",
        "5. Implementation detail: use integer ceiling `(p + k - 1) // k` rather than `math.ceil(p / k)` to avoid float pitfalls on 10⁹-scale inputs.",
        "6. Edge cases: single pile (lo == hi == that pile when h=1), h equals pile count (answer is max(piles)), h huge (answer is 1).",
    ],
    "tips": [
        "This is the same template as **Capacity to Ship Packages in D Days (LC 1011)**, **Split Array Largest Sum (LC 410)**, and **Find K-th Smallest Pair Distance (LC 719)**. Recognising the pattern is the interview signal.",
        "Use integer ceiling division `(p + k - 1) // k` over `math.ceil(p / k)` — float division on 10⁹-scale inputs is a code-smell and can lose precision in some languages.",
        "'Find leftmost True' is the predicate-based binary search invariant: while `lo < hi`, set `hi = mid` on True, `lo = mid + 1` on False; return `lo`. Memorise it; it's the safest template.",
        "Watch the upper bound: `hi = max(piles)`, *not* `sum(piles)` and *not* 10⁹. Justifying the tight bound shows you understand the problem.",
        "Watch for integer overflow in Java/C++: `hours` can exceed Integer.MAX_VALUE for large inputs. Use `long` for the hour accumulator.",
    ],
    "companies": ["Amazon", "Facebook", "Google"],
    "topics": ["Array", "Binary Search"],
    "time_complexity": "O(n log(max_pile))",
    "space_complexity": "O(1)",
}


def REFERENCE(piles, h):
    def hours(k):
        return sum((p + k - 1) // k for p in piles)
    lo, hi = 1, max(piles)
    while lo < hi:
        mid = (lo + hi) // 2
        if hours(mid) <= h:
            hi = mid
        else:
            lo = mid + 1
    return lo


register(PAYLOAD, REFERENCE)
