"""House Robber — Medium. Classic 1D Dynamic Programming.

The canonical 'pick or skip' DP. Each house's decision is local: take it
and skip the previous, or skip it and inherit the previous best. The full
table is unnecessary — only the last two values matter, so the standard
solution collapses to two scalars (O(1) space). Worth knowing because
House Robber II (circular) and III (binary tree) reuse the same recurrence
with a structural twist.
"""
from builder.registry import register


PAYLOAD = {
    "title": "House Robber",
    "difficulty": "Medium",
    "description": (
        "You are a professional robber planning to rob houses along a street. Each house has a certain amount "
        "of money stashed, the only constraint stopping you from robbing each of them is that **adjacent houses "
        "have security systems connected** and it will automatically contact the police if two adjacent houses "
        "were broken into on the same night.\n\n"
        "Given an integer array `nums` representing the amount of money of each house, return the **maximum "
        "amount of money you can rob tonight without alerting the police**.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,2,3,1]`\n"
        "- Output: `4`\n"
        "- Explanation: Rob house 1 (money = 1) and then rob house 3 (money = 3). Total = 1 + 3 = 4.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [2,7,9,3,1]`\n"
        "- Output: `12`\n"
        "- Explanation: Rob house 1 (money = 2), rob house 3 (money = 9), and rob house 5 (money = 1). "
        "Total = 2 + 9 + 1 = 12."
    ),
    "hints": [
        "At each house, you have two choices: rob it (and skip the previous one) or skip it (and inherit the previous best). That's the entire recurrence.",
        "Define `dp[i]` = maximum money robbable from the first `i+1` houses. Then `dp[i] = max(dp[i-1], dp[i-2] + nums[i])`.",
        "Base cases: `dp[0] = nums[0]`, `dp[1] = max(nums[0], nums[1])`. Empty array → 0.",
        "Only the last two values of `dp` are ever needed — collapse to two scalars `prev2` and `prev1` for O(1) space.",
        "Don't be greedy and just take every other house. `[2,1,1,2]` defeats that: the answer is `2 + 2 = 4`, which means skipping *two* houses in the middle.",
    ],
    "constraints": [
        "0 <= nums.length <= 100",
        "0 <= nums[i] <= 400",
    ],
    "starter_code": {
        "python": "def rob(nums):\n    # Your code here\n    pass",
        "javascript": "function rob(nums) {\n    // Your code here\n}",
        "java": "public int rob(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[1,2,3,1], [2,7,9,3,1], [], [5], [2,1,1,2]]\n"
            "    for nums in cases:\n"
            "        print(f\"rob({nums}) = {rob(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,2,3,1], [2,7,9,3,1], [2,1,1,2]].forEach(nums =>\n"
            "    console.log(`rob =`, rob(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.rob(new int[]{2,7,9,3,1}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 2, 3, 1]}, "expected": 4,
         "description": "Rob houses 0 and 2 → 1 + 3", "tags": ["basic"]},
        {"input": {"nums": [2, 7, 9, 3, 1]}, "expected": 12,
         "description": "Rob houses 0, 2, 4 → 2 + 9 + 1", "tags": ["basic"]},
        {"input": {"nums": []}, "expected": 0,
         "description": "Empty street — nothing to rob", "tags": ["edge"]},
        {"input": {"nums": [5]}, "expected": 5,
         "description": "Single house — rob it", "tags": ["edge"]},
        {"input": {"nums": [2, 1]}, "expected": 2,
         "description": "Two houses — pick the larger", "tags": ["edge"]},
        {"input": {"nums": [2, 1, 1, 2]}, "expected": 4,
         "description": "Skipping two adjacent houses can beat strict alternation",
         "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}, "expected": 30,
         "description": "Ascending — pick every other one starting from index 1 (2+4+6+8+10)",
         "tags": ["tricky"]},
        {"input": {"nums": [100, 1, 1, 100]}, "expected": 200,
         "description": "Big values at the ends; skip the cheap middle pair",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Two-Scalar DP (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk left-to-right tracking only the two most recent DP values. At each house, the new best is "
                "`max(prev1, prev2 + nums[i])` — either skip this house (inherit `prev1`) or take it (add to "
                "`prev2`, the best two houses back). Shift the window forward and continue."
            ),
            "code": {
                "python": (
                    "def rob(nums):\n"
                    "    prev2, prev1 = 0, 0\n"
                    "    for n in nums:\n"
                    "        prev2, prev1 = prev1, max(prev1, prev2 + n)\n"
                    "    return prev1"
                ),
                "javascript": (
                    "function rob(nums) {\n"
                    "    let prev2 = 0, prev1 = 0;\n"
                    "    for (const n of nums) {\n"
                    "        const curr = Math.max(prev1, prev2 + n);\n"
                    "        prev2 = prev1;\n"
                    "        prev1 = curr;\n"
                    "    }\n"
                    "    return prev1;\n"
                    "}"
                ),
                "java": (
                    "public int rob(int[] nums) {\n"
                    "    int prev2 = 0, prev1 = 0;\n"
                    "    for (int n : nums) {\n"
                    "        int curr = Math.max(prev1, prev2 + n);\n"
                    "        prev2 = prev1;\n"
                    "        prev1 = curr;\n"
                    "    }\n"
                    "    return prev1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Full DP Table",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Same recurrence, but allocate the full `dp` array. Useful as a stepping stone when explaining "
                "the solution — you can point at `dp[i]` and reconstruct the choice. Functionally identical to "
                "the two-scalar version, just heavier on memory."
            ),
            "code": {
                "python": (
                    "def rob(nums):\n"
                    "    if not nums:\n"
                    "        return 0\n"
                    "    if len(nums) == 1:\n"
                    "        return nums[0]\n"
                    "    dp = [0] * len(nums)\n"
                    "    dp[0] = nums[0]\n"
                    "    dp[1] = max(nums[0], nums[1])\n"
                    "    for i in range(2, len(nums)):\n"
                    "        dp[i] = max(dp[i - 1], dp[i - 2] + nums[i])\n"
                    "    return dp[-1]"
                ),
            },
        },
        {
            "title": "Top-Down Recursion + Memoisation",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Define `f(i)` = max money robbable from index `i` onward. Then `f(i) = max(f(i+1), nums[i] + "
                "f(i+2))`. Cache results to avoid the exponential branching. Same complexity as the bottom-up "
                "DP, plus call-stack overhead — bottom-up is usually preferred."
            ),
            "code": {
                "python": (
                    "def rob(nums):\n"
                    "    from functools import lru_cache\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def f(i):\n"
                    "        if i >= len(nums):\n"
                    "            return 0\n"
                    "        return max(f(i + 1), nums[i] + f(i + 2))\n"
                    "    return f(0)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force: try every subset of non-adjacent houses → 2ⁿ. State it; never submit it.",
        "2. Reframe as a per-house decision: at house `i`, you either rob it (and skip `i-1`) or skip it (and inherit the best up to `i-1`).",
        "3. That gives the recurrence `dp[i] = max(dp[i-1], dp[i-2] + nums[i])` with base cases `dp[0] = nums[0]`, `dp[1] = max(nums[0], nums[1])`.",
        "4. Notice `dp[i]` only ever reads `dp[i-1]` and `dp[i-2]`. Drop the array; keep two scalars `prev2` and `prev1`.",
        "5. Trace `[2,7,9,3,1]`: prev2/prev1 evolve 0,2 → 2,7 → 7,11 → 11,11 → 11,12 → answer 12. Matches 2+9+1.",
        "6. Edge cases: empty (return 0), single house (return nums[0]) — both handled cleanly by initialising `prev2 = prev1 = 0`.",
    ],
    "tips": [
        "Don't fall for 'just pick every other house'. `[2,1,1,2]` breaks it — the answer skips two adjacent houses.",
        "The two-scalar version is so compact that interviewers expect it. If you write the full DP table first, immediately follow up with 'and we can collapse this to O(1) space'.",
        "Common follow-up — **House Robber II** (LC 213): houses are arranged in a *circle*, so the first and last are adjacent. Solve it as max of two linear runs: `nums[0:n-1]` and `nums[1:n]`.",
        "Common follow-up — **House Robber III** (LC 337): houses form a binary tree. The same 'rob or skip' recurrence, but at each node return a pair `(rob_this, skip_this)` and combine children.",
        "Common follow-up — **Delete and Earn** (LC 740): bucket values by amount, then it's literally House Robber on the bucket array. Recognising the reduction is the whole trick.",
    ],
    "companies": ["Amazon", "LinkedIn", "Cisco"],
    "topics": ["Array", "Dynamic Programming"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    prev2, prev1 = 0, 0
    for n in nums:
        prev2, prev1 = prev1, max(prev1, prev2 + n)
    return prev1


register(PAYLOAD, REFERENCE)
