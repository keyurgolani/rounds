"""Target Sum — Medium. Dynamic Programming / Subset Sum.

A classic 'expression sign assignment' problem that looks like brute-force
2^n at first glance, but reduces *cleanly* to subset sum: pick a subset P
whose elements get '+' and let N be the rest (which get '-'). Then
sum(P) - sum(N) = target and sum(P) + sum(N) = total, so
sum(P) = (total + target) / 2. Counting subsets with that exact sum is the
canonical 0/1 knapsack count. The reduction is the whole interview.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Target Sum",
    "difficulty": "Medium",
    "description": (
        "You are given an integer array `nums` and an integer `target`.\n\n"
        "You want to build an **expression** out of `nums` by adding one of the symbols `'+'` and `'-'` "
        "before each integer in `nums` and then concatenating all the integers.\n\n"
        "- For example, if `nums = [2, 1]`, you can add a `'+'` before `2` and a `'-'` before `1` and "
        "concatenate them to build the expression `\"+2-1\"`.\n\n"
        "Return the number of different expressions that you can build, which evaluates to `target`.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,1,1,1,1], target = 3`\n"
        "- Output: `5`\n"
        "- Explanation: There are 5 ways to assign symbols to make the sum equal to 3:\n"
        "  `-1+1+1+1+1 = 3`, `+1-1+1+1+1 = 3`, `+1+1-1+1+1 = 3`, `+1+1+1-1+1 = 3`, `+1+1+1+1-1 = 3`.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [1], target = 1`\n"
        "- Output: `1`"
    ),
    "hints": [
        "Brute force: try `+`/`-` for each element → 2^n expressions. Fine for n ≤ 20, dies above.",
        "Reduction: split `nums` into a positive set P and a negative set N. Then `sum(P) - sum(N) = target` and `sum(P) + sum(N) = total`. Solve: `sum(P) = (total + target) / 2`.",
        "If `total + target` is negative or odd, **no valid assignment exists** — return 0 immediately.",
        "Now it's a count-subsets-with-sum-S problem. Classic 0/1 knapsack count: `dp[s] = dp[s] + dp[s - num]` iterated over `s` descending so each item is used once.",
        "Zeros are special: each zero contributes a factor of 2 (you can flip its sign for free). The DP handles this automatically — a zero doubles every existing count.",
    ],
    "constraints": [
        "1 <= nums.length <= 20",
        "0 <= nums[i] <= 1000",
        "0 <= sum(nums[i]) <= 1000",
        "-1000 <= target <= 1000",
    ],
    "starter_code": {
        "python": "def find_target_sum_ways(nums, target):\n    # Your code here\n    pass",
        "javascript": "function findTargetSumWays(nums, target) {\n    // Your code here\n}",
        "java": "public int findTargetSumWays(int[] nums, int target) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([1,1,1,1,1], 3), ([1], 1), ([1,2,1], 0)]\n"
            "    for nums, target in cases:\n"
            "        print(f\"find_target_sum_ways({nums}, {target}) = {find_target_sum_ways(nums, target)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,1,1,1,1], 3], [[1], 1], [[1,2,1], 0]].forEach(([nums, target]) =>\n"
            "    console.log(`findTargetSumWays =`, findTargetSumWays(nums, target))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.findTargetSumWays(new int[]{1,1,1,1,1}, 3));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 1, 1, 1, 1], "target": 3}, "expected": 5,
         "description": "Canonical LeetCode example — 5 ways to flip one of the five 1s",
         "tags": ["basic"]},
        {"input": {"nums": [1], "target": 1}, "expected": 1,
         "description": "Single element, achievable with `+1`", "tags": ["edge"]},
        {"input": {"nums": [1], "target": 2}, "expected": 0,
         "description": "Single element, target unreachable", "tags": ["edge"]},
        {"input": {"nums": [], "target": 0}, "expected": 1,
         "description": "Empty expression equals target 0 — exactly one way (the empty assignment)",
         "tags": ["edge"]},
        {"input": {"nums": [1, 2, 1], "target": 0}, "expected": 2,
         "description": "Two valid sign assignments: `+1-2+1` and `-1+2-1`", "tags": ["basic"]},
        {"input": {"nums": [0, 0, 0, 0, 0, 0, 0, 0, 1], "target": 1}, "expected": 256,
         "description": "Eight zeros each freely +/-, plus a fixed `+1` → 2^8 = 256 ways",
         "tags": ["tricky"]},
        {"input": {"nums": [100], "target": 100}, "expected": 1,
         "description": "Single element matches target exactly", "tags": ["edge"]},
        {"input": {"nums": [1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000], "target": 0},
         "expected": 252,
         "description": "Ten 1000s, target 0 — choose 5 of 10 to be positive: C(10,5) = 252",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Subset-Sum Reduction (1D DP — Optimal)",
            "time_complexity": "O(n * S) where S = (total + target) / 2",
            "space_complexity": "O(S)",
            "description": (
                "Reduce to subset sum: count subsets P with sum `(total + target) / 2`. "
                "If `total + target` is negative or odd, the answer is 0. "
                "Then run the classic 0/1 knapsack count with a 1D table iterated from S downwards."
            ),
            "code": {
                "python": (
                    "def find_target_sum_ways(nums, target):\n"
                    "    total = sum(nums)\n"
                    "    s = total + target\n"
                    "    if s < 0 or s % 2 != 0:\n"
                    "        return 0\n"
                    "    s //= 2\n"
                    "    dp = [0] * (s + 1)\n"
                    "    dp[0] = 1\n"
                    "    for num in nums:\n"
                    "        for j in range(s, num - 1, -1):\n"
                    "            dp[j] += dp[j - num]\n"
                    "    return dp[s]"
                ),
                "javascript": (
                    "function findTargetSumWays(nums, target) {\n"
                    "    const total = nums.reduce((a, b) => a + b, 0);\n"
                    "    const s = total + target;\n"
                    "    if (s < 0 || s % 2 !== 0) return 0;\n"
                    "    const half = s / 2;\n"
                    "    const dp = new Array(half + 1).fill(0);\n"
                    "    dp[0] = 1;\n"
                    "    for (const num of nums) {\n"
                    "        for (let j = half; j >= num; j--) dp[j] += dp[j - num];\n"
                    "    }\n"
                    "    return dp[half];\n"
                    "}"
                ),
                "java": (
                    "public int findTargetSumWays(int[] nums, int target) {\n"
                    "    int total = 0;\n"
                    "    for (int n : nums) total += n;\n"
                    "    int s = total + target;\n"
                    "    if (s < 0 || s % 2 != 0) return 0;\n"
                    "    s /= 2;\n"
                    "    int[] dp = new int[s + 1];\n"
                    "    dp[0] = 1;\n"
                    "    for (int num : nums) {\n"
                    "        for (int j = s; j >= num; j--) dp[j] += dp[j - num];\n"
                    "    }\n"
                    "    return dp[s];\n"
                    "}"
                ),
            },
        },
        {
            "title": "2D DP on (index, running sum) — Direct",
            "time_complexity": "O(n * total)",
            "space_complexity": "O(n * total)",
            "description": (
                "Skip the algebra trick and run the recurrence straight: "
                "`dp[i][s] = dp[i-1][s - nums[i]] + dp[i-1][s + nums[i]]`. "
                "Offset `s` by `total` to keep indices non-negative. Slightly heavier on memory but "
                "the most literal translation of the problem."
            ),
            "code": {
                "python": (
                    "def find_target_sum_ways(nums, target):\n"
                    "    total = sum(nums)\n"
                    "    if abs(target) > total:\n"
                    "        return 0\n"
                    "    # offset so indices [0 .. 2*total] map to sums [-total .. +total]\n"
                    "    width = 2 * total + 1\n"
                    "    dp = [0] * width\n"
                    "    dp[total] = 1  # empty prefix sums to 0\n"
                    "    for num in nums:\n"
                    "        nxt = [0] * width\n"
                    "        for s in range(width):\n"
                    "            if dp[s] == 0:\n"
                    "                continue\n"
                    "            if s + num < width:\n"
                    "                nxt[s + num] += dp[s]\n"
                    "            if s - num >= 0:\n"
                    "                nxt[s - num] += dp[s]\n"
                    "        dp = nxt\n"
                    "    return dp[total + target] if abs(target) <= total else 0"
                ),
            },
        },
        {
            "title": "Recursion + Memoisation",
            "time_complexity": "O(n * total)",
            "space_complexity": "O(n * total)",
            "description": (
                "Top-down counterpart: at each index choose `+nums[i]` or `-nums[i]` and recurse. "
                "Memoise on `(index, remaining_target)`. Cleanest to write under interview pressure if "
                "the subset-sum reduction doesn't surface."
            ),
            "code": {
                "python": (
                    "def find_target_sum_ways(nums, target):\n"
                    "    from functools import lru_cache\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def go(i, remaining):\n"
                    "        if i == len(nums):\n"
                    "            return 1 if remaining == 0 else 0\n"
                    "        return go(i + 1, remaining - nums[i]) + go(i + 1, remaining + nums[i])\n"
                    "    return go(0, target)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force is 2^n: try `+` and `-` for each element. Fine to mention for n ≤ 20, but useless as a stepping stone unless you need a baseline.",
        "2. Look for structure. Split `nums` into the positives P (the ones with `+`) and the negatives N (the ones with `-`). Every assignment is exactly one such split.",
        "3. By construction, `sum(P) - sum(N) = target` and `sum(P) + sum(N) = total`. Add the equations: `2 * sum(P) = total + target`, so `sum(P) = (total + target) / 2`.",
        "4. Feasibility check: if `total + target` is negative or odd, no integer subset sum P exists → return 0. This collapses the 'impossible target' family in one line.",
        "5. Now the problem is **count subsets of `nums` summing to S**. That's the canonical 0/1 knapsack count. 1D DP: `dp[j] += dp[j - num]` iterating `j` from `S` down to `num`.",
        "6. Zeros: each zero contributes a factor of 2 because flipping its sign is free. The DP handles this for you — when `num == 0`, the inner loop doubles every `dp[j]`. No special case needed.",
    ],
    "tips": [
        "Watch the parity gate: `(total + target) % 2 != 0` returns 0 instantly. Many candidates miss this and let the DP try to index a fractional sum.",
        "Don't forget the negativity gate: if `total + target < 0`, the subset sum is negative and the DP should never run. Handle before allocating the table.",
        "Zeros multiply: an array with k zeros has its answer multiplied by 2^k vs. the same array with zeros removed. Useful as a sanity check.",
        "When iterating the 1D table, iterate `j` from S **downwards** to `num`. Iterating upwards turns the 0/1 knapsack into the unbounded variant and overcounts.",
        "If `abs(target) > total`, the target is unreachable regardless of signs — return 0 (the parity gate also catches this, but the explicit check is clearer in interviews).",
    ],
    "companies": ["Amazon", "Facebook"],
    "topics": ["Array", "Dynamic Programming"],
    "time_complexity": "O(n * (total + target))",
    "space_complexity": "O(total + target)",
}


def REFERENCE(nums, target):
    total = sum(nums)
    s = total + target
    if s < 0 or s % 2 != 0:
        return 0
    s //= 2
    dp = [0] * (s + 1)
    dp[0] = 1
    for num in nums:
        for j in range(s, num - 1, -1):
            dp[j] += dp[j - num]
    return dp[s]


register(PAYLOAD, REFERENCE)
