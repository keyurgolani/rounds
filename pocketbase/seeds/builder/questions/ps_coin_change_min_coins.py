"""Coin Change (Min Coins) — Medium. Dynamic Programming.

Given denominations and a target amount, return the minimum number of
coins. DP O(amount × |denominations|). Greedy fails for arbitrary
denominations."""
from builder.registry import register


PAYLOAD = {
    "title": "Coin Change — Minimum Coins for Amount",
    "difficulty": "Medium",
    "description": (
        "Given an array of coin `denominations` (positive integers, repeats allowed without specified "
        "quantity) and an integer `amount`, return the **fewest number of coins** that sum exactly to "
        "`amount`. If it's impossible, return `-1`.\n\n"
        "You may use each denomination an unlimited number of times.\n\n"
        "**Example 1:**\n"
        "- Input: `denominations = [1, 2, 5]`, `amount = 11`\n"
        "- Output: `3` (5 + 5 + 1)\n\n"
        "**Example 2:**\n"
        "- Input: `denominations = [2]`, `amount = 3`\n"
        "- Output: `-1`\n\n"
        "**Example 3:**\n"
        "- Input: `denominations = [1]`, `amount = 0`\n"
        "- Output: `0`"
    ),
    "hints": [
        "Greedy is correct for canonical sets like US coins, but FAILS in general (counter: `denoms = [4, 3, 1]`, `amount = 6`; greedy gives 4+1+1=3, optimal is 3+3=2).",
        "Bottom-up DP: `dp[a] = min(dp[a - d] + 1 for d in denoms if d <= a)`. Initialise dp[0] = 0, dp[1..amount] = infinity.",
        "Top-down DP with memoisation works too — same complexity, recursion adds stack overhead.",
        "Skip explicit reconstruction unless asked — the count is the answer.",
        "Edge cases: amount = 0 (return 0), no solution (return -1), denomination = 1 (always solvable).",
    ],
    "constraints": [
        "0 <= amount <= 10⁴",
        "1 <= |denominations| <= 12",
        "1 <= denomination <= 2³¹ - 1",
    ],
    "starter_code": {
        "python": "def coin_change(denominations, amount):\n    # Your code here\n    pass",
        "javascript": "function coinChange(denominations, amount) {\n    // Your code here\n}",
        "java": "public int coinChange(int[] denominations, int amount) {\n    // Your code here\n    return -1;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(coin_change([1, 2, 5], 11))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"denominations": [1, 2, 5], "amount": 11}, "expected": 3,
         "description": "5 + 5 + 1", "tags": ["basic"]},
        {"input": {"denominations": [2], "amount": 3}, "expected": -1,
         "description": "Impossible", "tags": ["edge"]},
        {"input": {"denominations": [1], "amount": 0}, "expected": 0,
         "description": "Zero amount", "tags": ["edge"]},
        {"input": {"denominations": [4, 3, 1], "amount": 6}, "expected": 2,
         "description": "Greedy fails: 4+1+1=3 but optimal is 3+3=2",
         "tags": ["tricky"]},
        {"input": {"denominations": [25, 10, 5, 1], "amount": 30}, "expected": 2,
         "description": "Canonical US coins", "tags": ["basic"]},
        {"input": {"denominations": [2, 5, 10, 1], "amount": 27}, "expected": 4,
         "description": "Multiple denominations needed", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Bottom-Up DP (Optimal)",
            "time_complexity": "O(amount × |denominations|)",
            "space_complexity": "O(amount)",
            "description": (
                "`dp[a]` = min coins to reach amount a; ∞ if unreachable. dp[0] = 0. For each amount from "
                "1 to target, try every denomination ≤ a. Final answer is dp[amount] or -1."
            ),
            "code": {
                "python": (
                    "def coin_change(denominations, amount):\n"
                    "    INF = float('inf')\n"
                    "    dp = [INF] * (amount + 1)\n"
                    "    dp[0] = 0\n"
                    "    for a in range(1, amount + 1):\n"
                    "        for d in denominations:\n"
                    "            if d <= a and dp[a - d] + 1 < dp[a]:\n"
                    "                dp[a] = dp[a - d] + 1\n"
                    "    return dp[amount] if dp[amount] != INF else -1"
                ),
                "javascript": (
                    "function coinChange(denominations, amount) {\n"
                    "    const INF = Infinity;\n"
                    "    const dp = new Array(amount + 1).fill(INF);\n"
                    "    dp[0] = 0;\n"
                    "    for (let a = 1; a <= amount; a++) {\n"
                    "        for (const d of denominations) {\n"
                    "            if (d <= a && dp[a - d] + 1 < dp[a]) dp[a] = dp[a - d] + 1;\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[amount] === INF ? -1 : dp[amount];\n"
                    "}"
                ),
                "java": (
                    "public int coinChange(int[] denominations, int amount) {\n"
                    "    int[] dp = new int[amount + 1];\n"
                    "    Arrays.fill(dp, amount + 1);\n"
                    "    dp[0] = 0;\n"
                    "    for (int a = 1; a <= amount; a++)\n"
                    "        for (int d : denominations)\n"
                    "            if (d <= a) dp[a] = Math.min(dp[a], dp[a - d] + 1);\n"
                    "    return dp[amount] > amount ? -1 : dp[amount];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Top-Down DP (Memoised Recursion)",
            "time_complexity": "Same",
            "space_complexity": "Same + recursion stack",
            "description": (
                "Recurse: `f(a) = 1 + min(f(a - d) for d in denoms if d <= a)`. Memoise by amount. "
                "Cleaner to derive on a whiteboard but loses to bottom-up on stack discipline."
            ),
            "code": {
                "python": (
                    "def coin_change(denominations, amount):\n"
                    "    memo = {0: 0}\n"
                    "    def f(a):\n"
                    "        if a in memo: return memo[a]\n"
                    "        best = float('inf')\n"
                    "        for d in denominations:\n"
                    "            if d <= a:\n"
                    "                sub = f(a - d)\n"
                    "                if sub != -1 and sub + 1 < best:\n"
                    "                    best = sub + 1\n"
                    "        memo[a] = -1 if best == float('inf') else best\n"
                    "        return memo[a]\n"
                    "    return f(amount)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. State the greedy temptation. Provide a counter-example where greedy fails. That's the unlock.",
        "2. Reframe: for each amount a, the min coins is `1 + min(f(a - d) for d ≤ a)`. Recursive.",
        "3. Memoise on `a` — there are only `amount + 1` distinct subproblems.",
        "4. Bottom-up walks 0..amount; top-down recurses. Same complexity, prefer bottom-up under stress.",
        "5. Edge cases: amount = 0 (0 coins), unreachable (-1), denomination 1 always solvable.",
        "6. Reconstruction: track which denomination achieved each dp[a] for a path. Rarely required but simple to add.",
    ],
    "tips": [
        "If asked for the actual coins (not just the count), record the denomination chosen at each dp[a]. Walk back from dp[amount].",
        "If denominations include 1, the answer is always at most amount — but the DP doesn't know that and will compute it correctly anyway.",
        "Common follow-up: 'count the number of ways to make amount.' Different problem — different DP recurrence (sum over denominations instead of min).",
        "Common follow-up: 'minimise different denominations used.' Add a 'last denom used' state — exponential without compression, polynomial with.",
        "Common follow-up: 'unbounded knapsack with values.' Same DP shape with prices → values.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Apple"],
    "topics": ["Dynamic Programming", "Array", "BFS"],
    "time_complexity": "O(amount × |denominations|)",
    "space_complexity": "O(amount)",
}


def REFERENCE(denominations, amount):
    INF = float("inf")
    dp = [INF] * (amount + 1)
    dp[0] = 0
    for a in range(1, amount + 1):
        for d in denominations:
            if d <= a and dp[a - d] + 1 < dp[a]:
                dp[a] = dp[a - d] + 1
    return dp[amount] if dp[amount] != INF else -1


register(PAYLOAD, REFERENCE)
