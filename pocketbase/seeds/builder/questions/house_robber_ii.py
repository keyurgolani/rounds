"""House Robber II — Medium. Circular variant of House Robber.

The twist: houses are arranged in a circle, so house 0 and house n-1 are
adjacent. The trick is to recognise that *at most one* of those two can
be robbed, never both. So reduce to two linear House Robber subproblems —
nums[0..n-2] (skip the last) and nums[1..n-1] (skip the first) — and take
the larger answer. Each pass uses the same O(1) rolling DP as the linear
version.
"""
from builder.registry import register


PAYLOAD = {
    "title": "House Robber II",
    "difficulty": "Medium",
    "description": (
        "You are a professional robber planning to rob houses along a street. Each house has a certain amount "
        "of money stashed. All houses at this place are **arranged in a circle**, which means that the first "
        "house is the neighbor of the last one. Meanwhile, **adjacent houses have a security system connected**, "
        "and it will automatically contact the police if two adjacent houses were broken into on the same night.\n\n"
        "Given an integer array `nums` representing the amount of money of each house, return the **maximum "
        "amount of money you can rob tonight without alerting the police**.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [2,3,2]`\n"
        "- Output: `3`\n"
        "- Explanation: You cannot rob house 0 (money = 2) and then rob house 2 (money = 2), because they are "
        "adjacent in the circle. The best you can do is rob house 1 alone for 3.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [1,2,3,1]`\n"
        "- Output: `4`\n"
        "- Explanation: Rob house 1 (money = 2) and then rob house 3 (money = 1)? No — those total 3. Rob "
        "house 0 (money = 1) and house 2 (money = 3) → total = 4. House 0 and house 3 are circularly "
        "adjacent, so we cannot pick both."
    ),
    "hints": [
        "The circular constraint means house 0 and house n-1 are now neighbours. At most one of them can be robbed — never both.",
        "Split into two independent linear subproblems: rob within `nums[0..n-2]` (skip the last house) and rob within `nums[1..n-1]` (skip the first house). Return the max.",
        "Each subproblem is just plain House Robber. Reuse the rolling-pair DP: `prev2, prev1 = prev1, max(prev1, prev2 + n)`.",
        "Don't forget the small-input edge cases: if `len(nums) <= 1` return `nums[0] if nums else 0`; if `len(nums) == 2` return `max(nums)`. The two-range split is degenerate there.",
        "Both passes can run in O(1) extra space, so the whole algorithm stays O(n) time and O(1) space — same asymptotic profile as House Robber I.",
    ],
    "constraints": [
        "1 <= nums.length <= 100",
        "0 <= nums[i] <= 1000",
        "Houses are arranged in a circle: index 0 and index n-1 are adjacent.",
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
            "    cases = [[2,3,2], [1,2,3,1], [1,2,3], [5], [3,3], [200,3,140,20,10]]\n"
            "    for nums in cases:\n"
            "        print(f\"rob({nums}) = {rob(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[2,3,2], [1,2,3,1], [1,2,3], [200,3,140,20,10]].forEach(nums =>\n"
            "    console.log(`rob =`, rob(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.rob(new int[]{1,2,3,1}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [2, 3, 2]}, "expected": 3,
         "description": "LC example 1 — circular adjacency forbids robbing both ends; pick the middle",
         "tags": ["basic"]},
        {"input": {"nums": [1, 2, 3, 1]}, "expected": 4,
         "description": "LC example 2 — rob houses 0 and 2 (1 + 3); ends are circularly adjacent",
         "tags": ["basic"]},
        {"input": {"nums": [1, 2, 3]}, "expected": 3,
         "description": "LC example 3 — three houses, all circularly adjacent; rob only the largest",
         "tags": ["basic"]},
        {"input": {"nums": [5]}, "expected": 5,
         "description": "Single house — rob it; circular wrap is trivial",
         "tags": ["edge"]},
        {"input": {"nums": [3, 3]}, "expected": 3,
         "description": "Two houses — circularly adjacent; pick one",
         "tags": ["edge"]},
        {"input": {"nums": [0, 0, 0, 0]}, "expected": 0,
         "description": "All zeros — nothing to gain regardless of choice",
         "tags": ["edge"]},
        {"input": {"nums": [4, 4, 4, 4, 4]}, "expected": 8,
         "description": "All equal, n=5 — best is two non-adjacent picks (4 + 4)",
         "tags": ["edge"]},
        {"input": {"nums": [200, 3, 140, 20, 10]}, "expected": 340,
         "description": "Circular trap: greedy 200 + 140 + 10 looks tempting, but 200 and 10 wrap-collide; correct is 200 + 140 = 340 via skipping the last",
         "tags": ["tricky"]},
        {"input": {"nums": [1, 3, 1, 3, 100]}, "expected": 103,
         "description": "Big payoff at the end forces skipping index 0; rob indices 1 and 4 (3 + 100)",
         "tags": ["tricky"]},
        {"input": {"nums": [6, 7, 1, 30, 8, 2, 4]}, "expected": 41,
         "description": "Mid-array peak; circular split picks 7 + 30 + 4 = 41 (skipping index 0)",
         "tags": ["tricky"]},
        {"input": {"nums": [n % 17 + 1 for n in range(100)]}, "expected": 463,
         "description": "Large array (n=100) with a periodic pattern; verifies O(n) scaling",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Two-Range Rolling DP (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "The circular constraint means at most one of `nums[0]` and `nums[n-1]` can be robbed. So the "
                "answer is the max of two linear House Robber subproblems: one over `nums[0..n-2]` (skip the "
                "last) and one over `nums[1..n-1]` (skip the first). Each subproblem runs in O(n) with two "
                "scalars, so the overall cost stays O(n) time / O(1) space."
            ),
            "code": {
                "python": (
                    "def rob(nums):\n"
                    "    n = len(nums)\n"
                    "    if n == 0:\n"
                    "        return 0\n"
                    "    if n == 1:\n"
                    "        return nums[0]\n"
                    "    if n == 2:\n"
                    "        return max(nums)\n"
                    "\n"
                    "    def rob_linear(arr):\n"
                    "        prev2, prev1 = 0, 0\n"
                    "        for x in arr:\n"
                    "            prev2, prev1 = prev1, max(prev1, prev2 + x)\n"
                    "        return prev1\n"
                    "\n"
                    "    return max(rob_linear(nums[:-1]), rob_linear(nums[1:]))"
                ),
                "javascript": (
                    "function rob(nums) {\n"
                    "    const n = nums.length;\n"
                    "    if (n === 0) return 0;\n"
                    "    if (n === 1) return nums[0];\n"
                    "    if (n === 2) return Math.max(nums[0], nums[1]);\n"
                    "\n"
                    "    const robLinear = (lo, hi) => {\n"
                    "        let prev2 = 0, prev1 = 0;\n"
                    "        for (let i = lo; i <= hi; i++) {\n"
                    "            const curr = Math.max(prev1, prev2 + nums[i]);\n"
                    "            prev2 = prev1;\n"
                    "            prev1 = curr;\n"
                    "        }\n"
                    "        return prev1;\n"
                    "    };\n"
                    "\n"
                    "    return Math.max(robLinear(0, n - 2), robLinear(1, n - 1));\n"
                    "}"
                ),
                "java": (
                    "public int rob(int[] nums) {\n"
                    "    int n = nums.length;\n"
                    "    if (n == 0) return 0;\n"
                    "    if (n == 1) return nums[0];\n"
                    "    if (n == 2) return Math.max(nums[0], nums[1]);\n"
                    "    return Math.max(robLinear(nums, 0, n - 2), robLinear(nums, 1, n - 1));\n"
                    "}\n"
                    "\n"
                    "private int robLinear(int[] nums, int lo, int hi) {\n"
                    "    int prev2 = 0, prev1 = 0;\n"
                    "    for (int i = lo; i <= hi; i++) {\n"
                    "        int curr = Math.max(prev1, prev2 + nums[i]);\n"
                    "        prev2 = prev1;\n"
                    "        prev1 = curr;\n"
                    "    }\n"
                    "    return prev1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Top-Down Recursion + Memoisation",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Same two-range decomposition, expressed top-down. Define `f(i, end)` = max money robbable from "
                "index `i` up to (but not past) `end`. Then `f(i, end) = max(f(i+1, end), nums[i] + f(i+2, end))`. "
                "Memoise on `(i, end)` (or run two separate memo tables). Run it with `end = n-1` (skip last) "
                "and `end = n` starting from `i = 1` (skip first); take the max. Same asymptotic cost as the "
                "iterative DP, plus call-stack overhead — bottom-up is usually preferred."
            ),
            "code": {
                "python": (
                    "def rob(nums):\n"
                    "    n = len(nums)\n"
                    "    if n == 0:\n"
                    "        return 0\n"
                    "    if n == 1:\n"
                    "        return nums[0]\n"
                    "    if n == 2:\n"
                    "        return max(nums)\n"
                    "\n"
                    "    from functools import lru_cache\n"
                    "\n"
                    "    def best(start, end):\n"
                    "        # max robbable from indices [start, end) inclusive of start, exclusive of end\n"
                    "        @lru_cache(maxsize=None)\n"
                    "        def f(i):\n"
                    "            if i >= end:\n"
                    "                return 0\n"
                    "            return max(f(i + 1), nums[i] + f(i + 2))\n"
                    "        return f(start)\n"
                    "\n"
                    "    return max(best(0, n - 1), best(1, n))"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force: enumerate every subset of non-adjacent houses respecting the circular wrap → 2ⁿ. State it; never submit it.",
        "2. Key observation: in a circle, robbing both index 0 and index n-1 is forbidden, so at most one of them ends up in the chosen set.",
        "3. Reduce to two linear House Robber instances: case A excludes the last house (`nums[0..n-2]`), case B excludes the first (`nums[1..n-1]`). Either case A robs index 0 or it doesn't; either case B robs index n-1 or it doesn't — but never both.",
        "4. Each case is the standard House Robber recurrence: `dp[i] = max(dp[i-1], dp[i-2] + nums[i])`. Collapse to two scalars per pass.",
        "5. The final answer is `max(rob_linear(case A), rob_linear(case B))`. Two passes, O(n) each → O(n) total, O(1) extra space.",
        "6. Don't skip the small-input guard: `n == 1` returns `nums[0]`, `n == 2` returns `max(nums)`. Otherwise `nums[:-1]` and `nums[1:]` would each shrink to a single element and the two passes would both be defensible but redundant.",
    ],
    "tips": [
        "Spot the reduction immediately: 'circular' ⇒ 'at most one endpoint' ⇒ 'two linear runs'. Articulate that out loud — interviewers want the insight, not just the code.",
        "Don't write a special-case wrap-around DP. Two clean linear passes is shorter, faster, and harder to bug than a single circular DP with conditional logic.",
        "Watch out for `n == 1` and `n == 2`: `nums[:-1]` and `nums[1:]` are empty/singleton there, and your handling must still return the right value. A small explicit guard at the top is cheaper than carefully reasoning about it.",
        "Common follow-up — **House Robber III** (LC 337): houses form a binary tree. Same 'rob or skip' recurrence, but at each node return a pair `(rob_this, skip_this)` and combine children.",
        "Common follow-up — **Delete and Earn** (LC 740): bucket values by amount, then it's literally House Robber on the bucket array. Recognising the reduction is the whole trick.",
        "If asked to *return the houses robbed* (not just the max), keep a parent/choice pointer per pass and reconstruct — same idea as classical DP path recovery.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Apple", "LinkedIn"],
    "topics": ["Array", "Dynamic Programming"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    n = len(nums)
    if n == 0:
        return 0
    if n == 1:
        return nums[0]
    if n == 2:
        return max(nums)

    def rob_linear(arr):
        prev2, prev1 = 0, 0
        for x in arr:
            prev2, prev1 = prev1, max(prev1, prev2 + x)
        return prev1

    return max(rob_linear(nums[:-1]), rob_linear(nums[1:]))


register(PAYLOAD, REFERENCE)
