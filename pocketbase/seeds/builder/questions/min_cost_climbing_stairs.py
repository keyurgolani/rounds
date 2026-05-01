"""Min Cost Climbing Stairs — Easy. Dynamic Programming.

The natural follow-up to Climbing Stairs: same 1-or-2-step recurrence,
but now each stair carries a cost and we minimise instead of count.
The clean way to frame it: `dp[i]` = minimum cost to *stand on* step i,
with `dp[i] = cost[i] + min(dp[i-1], dp[i-2])`. The answer is the
cheaper of the last two stairs (since either can be the final launch
pad to the top). Collapses to two scalars in O(1) space.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Min Cost Climbing Stairs",
    "difficulty": "Easy",
    "description": (
        "You are given an integer array `cost` where `cost[i]` is the cost of stepping on the i-th stair "
        "of a staircase. Once you pay the cost, you can either climb **one** or **two** steps.\n\n"
        "You can either start from the stair at index `0`, or the stair at index `1`.\n\n"
        "Return the **minimum cost** to reach the top of the floor (i.e., the position just past the last "
        "stair, index `n`).\n\n"
        "**Example 1:**\n"
        "- Input: `cost = [10, 15, 20]`\n"
        "- Output: `15`\n"
        "- Explanation: Start at index 1, pay 15, and step two stairs to reach the top. Total = 15.\n\n"
        "**Example 2:**\n"
        "- Input: `cost = [1, 100, 1, 1, 1, 100, 1, 1, 100, 1]`\n"
        "- Output: `6`\n"
        "- Explanation: Start at index 0. Path of indices: 0 → 2 → 4 → 6 → 7 → 9 → top. "
        "Costs paid: 1 + 1 + 1 + 1 + 1 + 1 = 6."
    ),
    "hints": [
        "Define `dp[i]` = minimum cost to *stand on* stair `i`. The recurrence is "
        "`dp[i] = cost[i] + min(dp[i-1], dp[i-2])` — you arrive at `i` from either of the two stairs below it.",
        "Base cases: you may start from index 0 or 1 free of charge, so `dp[0] = cost[0]` and `dp[1] = cost[1]`.",
        "The 'top' is the position past the last stair, which you can reach from either of the last two "
        "stairs. So the answer is `min(dp[n-1], dp[n-2])`.",
        "Only the previous two `dp` values are ever read — drop the array and keep two scalars for O(1) space.",
        "Top-down memoised recursion is equivalent: `cost_to_reach(i) = cost[i] + min(cost_to_reach(i-1), "
        "cost_to_reach(i-2))`. Same O(n) time, O(n) recursion stack.",
    ],
    "constraints": [
        "2 <= cost.length <= 1000",
        "0 <= cost[i] <= 999",
    ],
    "starter_code": {
        "python": "def min_cost_climbing_stairs(cost):\n    # Your code here\n    pass",
        "javascript": "function minCostClimbingStairs(cost) {\n    // Your code here\n}",
        "java": "public int minCostClimbingStairs(int[] cost) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[10, 15, 20], [1, 100, 1, 1, 1, 100, 1, 1, 100, 1], [10, 15]]\n"
            "    for cost in cases:\n"
            "        print(f\"min_cost_climbing_stairs({cost}) = {min_cost_climbing_stairs(cost)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[10, 15, 20], [1, 100, 1, 1, 1, 100, 1, 1, 100, 1]].forEach(cost =>\n"
            "    console.log(`minCostClimbingStairs =`, minCostClimbingStairs(cost))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.minCostClimbingStairs(new int[]{10, 15, 20}));\n"
            "        System.out.println(s.minCostClimbingStairs(new int[]{1,100,1,1,1,100,1,1,100,1}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"cost": [10, 15, 20]}, "expected": 15,
         "description": "Classic LC example — start at index 1, jump 2 to top", "tags": ["basic"]},
        {"input": {"cost": [1, 100, 1, 1, 1, 100, 1, 1, 100, 1]}, "expected": 6,
         "description": "Classic LC example — weave around the 100s, pay six 1s", "tags": ["basic"]},
        {"input": {"cost": [10, 15]}, "expected": 10,
         "description": "n=2 — start at index 0, step two to the top, pay 10", "tags": ["edge"]},
        {"input": {"cost": [15, 10]}, "expected": 10,
         "description": "n=2 reversed — start at index 1, step two to the top, pay 10", "tags": ["edge"]},
        {"input": {"cost": [0, 0, 0, 0]}, "expected": 0,
         "description": "All zeros — minimum cost is 0", "tags": ["edge"]},
        {"input": {"cost": [5, 5, 5, 5, 5, 5]}, "expected": 15,
         "description": "All same — every other stair, three steps × 5", "tags": ["basic"]},
        {"input": {"cost": [1, 100, 1, 100, 1, 100, 1]}, "expected": 4,
         "description": "Alternating high/low — hop only the 1s, pay four of them", "tags": ["tricky"]},
        {"input": {"cost": [100, 1, 100, 1, 100, 1, 100]}, "expected": 3,
         "description": "Alternating starting high — start at index 1, hop the 1s, pay three", "tags": ["tricky"]},
        {"input": {"cost": [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]}, "expected": 25,
         "description": "Descending costs — start at index 1, hop by 2s: 9 + 7 + 5 + 3 + 1 = 25",
         "tags": ["tricky"]},
        {"input": {"cost": [0] * 1000}, "expected": 0,
         "description": "Large n, all zeros — verifies the loop doesn't accumulate spurious cost", "tags": ["large"]},
        {"input": {"cost": [1] * 1000}, "expected": 500,
         "description": "Large n, all ones — optimal pays every other stair, 500 total", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Bottom-Up DP, O(1) Space (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk left-to-right carrying only the previous two `dp` values. `prev2` is the cost to stand "
                "on stair `i-2`, `prev1` the cost to stand on stair `i-1`. The current value is "
                "`cost[i] + min(prev1, prev2)`. After the scan, the answer is `min(prev1, prev2)` — the "
                "cheaper launch pad to the top. Two scalars, no array. This is what to write in the room."
            ),
            "code": {
                "python": (
                    "def min_cost_climbing_stairs(cost):\n"
                    "    prev2, prev1 = cost[0], cost[1]\n"
                    "    for i in range(2, len(cost)):\n"
                    "        prev2, prev1 = prev1, cost[i] + min(prev1, prev2)\n"
                    "    return min(prev1, prev2)"
                ),
                "javascript": (
                    "function minCostClimbingStairs(cost) {\n"
                    "    let prev2 = cost[0], prev1 = cost[1];\n"
                    "    for (let i = 2; i < cost.length; i++) {\n"
                    "        const curr = cost[i] + Math.min(prev1, prev2);\n"
                    "        prev2 = prev1;\n"
                    "        prev1 = curr;\n"
                    "    }\n"
                    "    return Math.min(prev1, prev2);\n"
                    "}"
                ),
                "java": (
                    "public int minCostClimbingStairs(int[] cost) {\n"
                    "    int prev2 = cost[0], prev1 = cost[1];\n"
                    "    for (int i = 2; i < cost.length; i++) {\n"
                    "        int curr = cost[i] + Math.min(prev1, prev2);\n"
                    "        prev2 = prev1;\n"
                    "        prev1 = curr;\n"
                    "    }\n"
                    "    return Math.min(prev1, prev2);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Top-Down Memoised Recursion",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Express the recurrence directly: `cost_to_reach(i) = cost[i] + min(cost_to_reach(i-1), "
                "cost_to_reach(i-2))`, with `cost_to_reach(0) = cost[0]` and `cost_to_reach(1) = cost[1]`. "
                "Cache results to avoid the exponential blow-up. Same asymptotic time as the iterative "
                "version, but O(n) auxiliary space from the call stack and memo table. Useful as a "
                "stepping-stone explanation."
            ),
            "code": {
                "python": (
                    "from functools import lru_cache\n\n"
                    "def min_cost_climbing_stairs(cost):\n"
                    "    n = len(cost)\n\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def reach(i):\n"
                    "        if i < 2:\n"
                    "            return cost[i]\n"
                    "        return cost[i] + min(reach(i - 1), reach(i - 2))\n\n"
                    "    return min(reach(n - 1), reach(n - 2))"
                ),
                "javascript": (
                    "function minCostClimbingStairs(cost) {\n"
                    "    const memo = new Map();\n"
                    "    const reach = (i) => {\n"
                    "        if (i < 2) return cost[i];\n"
                    "        if (memo.has(i)) return memo.get(i);\n"
                    "        const v = cost[i] + Math.min(reach(i - 1), reach(i - 2));\n"
                    "        memo.set(i, v);\n"
                    "        return v;\n"
                    "    };\n"
                    "    const n = cost.length;\n"
                    "    return Math.min(reach(n - 1), reach(n - 2));\n"
                    "}"
                ),
                "java": (
                    "public int minCostClimbingStairs(int[] cost) {\n"
                    "    int n = cost.length;\n"
                    "    Integer[] memo = new Integer[n];\n"
                    "    return Math.min(reach(cost, n - 1, memo), reach(cost, n - 2, memo));\n"
                    "}\n\n"
                    "private int reach(int[] cost, int i, Integer[] memo) {\n"
                    "    if (i < 2) return cost[i];\n"
                    "    if (memo[i] != null) return memo[i];\n"
                    "    memo[i] = cost[i] + Math.min(reach(cost, i - 1, memo), reach(cost, i - 2, memo));\n"
                    "    return memo[i];\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Read the problem carefully: each stair has a cost, you pay it when you step on it, you can start "
        "free at index 0 or 1, and the goal is the position *past* the last stair. Walk the second example "
        "by hand to confirm: 1 → 1 → 1 → 1 → 1 → 1 = 6.",
        "2. Define the subproblem: `dp[i]` = minimum cost to *stand on* stair `i`. (Defining it as 'cost to "
        "reach the position just past `i`' also works but is clumsier; pick one and stick with it.)",
        "3. Derive the recurrence: to stand on stair `i` you must have stood on either `i-1` or `i-2`, then "
        "paid `cost[i]`. So `dp[i] = cost[i] + min(dp[i-1], dp[i-2])`.",
        "4. Base cases: starting at index 0 or 1 is free, so the cost of standing on them is just their own "
        "cost: `dp[0] = cost[0]`, `dp[1] = cost[1]`.",
        "5. Final answer: the top is past the last stair, reachable from either of the last two stairs, so "
        "return `min(dp[n-1], dp[n-2])`.",
        "6. Optimise space: the recurrence only reads the previous two values, so collapse to two scalars. "
        "This is the clean O(n) time / O(1) space solution to write in the interview.",
    ],
    "tips": [
        "Pick your `dp[i]` definition carefully and write it on the board. The two natural choices ("
        "'cost to stand on i' vs. 'cost to reach the slot past i') give equivalent answers but different "
        "indexing — flipping mid-derivation is the #1 way candidates introduce off-by-one bugs.",
        "The 'top' is *past* the last stair, not the last stair itself. That's why the answer is "
        "`min(dp[n-1], dp[n-2])` and not just `dp[n-1]` — you can launch from either of the last two.",
        "Don't pay `cost[i]` twice. The recurrence adds `cost[i]` exactly once per stair, when you step on it.",
        "Recognise the family: this is Climbing Stairs with weights. The same 1-or-2-step graph, but you're "
        "running shortest-path instead of counting paths. House Robber is the next variant — same DP shape, "
        "different recurrence (`max(dp[i-1], cost[i] + dp[i-2])`).",
        "Generalisation — 'k step sizes from set S, minimise total cost': becomes "
        "`dp[i] = cost[i] + min(dp[i-s] for s in S)`. Same DP, O(n·|S|) time. Mention as a follow-up.",
        "Constraint check: `n >= 2` is guaranteed, so you don't need to special-case empty or singleton "
        "arrays. State this when picking your base cases.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Apple"],
    "topics": ["Dynamic Programming", "Array"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(cost):
    prev2, prev1 = cost[0], cost[1]
    for i in range(2, len(cost)):
        prev2, prev1 = prev1, cost[i] + min(prev1, prev2)
    return min(prev1, prev2)


register(PAYLOAD, REFERENCE)
