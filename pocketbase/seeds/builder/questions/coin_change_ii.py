"""Coin Change II — Medium. Unbounded Knapsack / DP.

The number-of-ways twin to Coin Change (LC 322, which asks for the *minimum*
count). Same data, totally different recurrence: here we count distinct
combinations, and the loop order matters more than anything else in the
problem. Outer-coin / inner-amount counts combinations; outer-amount /
inner-coin counts permutations and silently produces the wrong answer.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Coin Change II",
    "difficulty": "Medium",
    "description": (
        "You are given an integer `amount` representing a total amount of money and an array `coins` "
        "representing coins of different denominations. You have an **unlimited** supply of each kind "
        "of coin.\n\n"
        "Return the number of **distinct combinations** that make up that amount. If that amount cannot "
        "be made up by any combination of the coins, return `0`.\n\n"
        "The answer is guaranteed to fit into a signed 32-bit integer.\n\n"
        "**Example 1:**\n"
        "- Input: `amount = 5, coins = [1,2,5]`\n"
        "- Output: `4`\n"
        "- Explanation: There are four ways: `5=5`, `5=2+2+1`, `5=2+1+1+1`, `5=1+1+1+1+1`.\n\n"
        "**Example 2:**\n"
        "- Input: `amount = 3, coins = [2]`\n"
        "- Output: `0`\n"
        "- Explanation: The amount of 3 cannot be made up using only coins of 2.\n\n"
        "**Example 3:**\n"
        "- Input: `amount = 10, coins = [10]`\n"
        "- Output: `1`"
    ),
    "hints": [
        "Classic unbounded knapsack: each coin has unlimited supply, and we want to count combinations summing to `amount`.",
        "Define `dp[i] = number of ways to make amount i`. Base case: `dp[0] = 1` (the empty combination — choose no coins).",
        "Transition: for each coin `c`, every way to make `i - c` becomes a way to make `i` by appending one more `c`. So `dp[i] += dp[i - c]`.",
        "Loop order is the *whole* trick. Outer loop over coins, inner loop over amounts → counts combinations. Outer loop over amounts, inner over coins → counts ordered sequences (permutations) and over-counts.",
        "Don't confuse this with LC 322 (Coin Change), which asks for the *fewest* coins, not the number of ways. Different recurrence — `min` instead of sum.",
    ],
    "constraints": [
        "1 <= coins.length <= 300",
        "1 <= coins[i] <= 5000",
        "All values of coins are unique",
        "0 <= amount <= 5000",
    ],
    "starter_code": {
        "python": "def change(amount, coins):\n    # Your code here\n    pass",
        "javascript": "function change(amount, coins) {\n    // Your code here\n}",
        "java": "public int change(int amount, int[] coins) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(5, [1,2,5]), (3, [2]), (10, [10]), (0, [1,2,5])]\n"
            "    for amount, coins in cases:\n"
            "        print(f\"change({amount}, {coins}) = {change(amount, coins)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[5, [1,2,5]], [3, [2]], [10, [10]], [0, [1,2,5]]].forEach(([a, c]) =>\n"
            "    console.log(`change(${a}, ${JSON.stringify(c)}) =`, change(a, c))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.change(5, new int[]{1,2,5}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"amount": 5, "coins": [1, 2, 5]}, "expected": 4,
         "description": "Canonical LC example — four combinations", "tags": ["basic"]},
        {"input": {"amount": 3, "coins": [2]}, "expected": 0,
         "description": "Unreachable amount — only even denominations can't make 3", "tags": ["basic"]},
        {"input": {"amount": 10, "coins": [10]}, "expected": 1,
         "description": "Exact single-coin match", "tags": ["edge"]},
        {"input": {"amount": 0, "coins": [1, 2, 5]}, "expected": 1,
         "description": "Zero amount — the empty combination counts as one way", "tags": ["edge"]},
        {"input": {"amount": 4, "coins": [1, 2, 3]}, "expected": 4,
         "description": "Combinations: 1+1+1+1, 1+1+2, 2+2, 1+3", "tags": ["basic"]},
        {"input": {"amount": 10, "coins": [1]}, "expected": 1,
         "description": "Single denomination — exactly one combination (ten 1s)", "tags": ["edge"]},
        {"input": {"amount": 500, "coins": [1, 2, 5]}, "expected": 12701,
         "description": "Larger amount — exact count via DP", "tags": ["large"]},
        {"input": {"amount": 5000, "coins": [2, 5, 10, 1]}, "expected": 209460251,
         "description": "Stress test — order of coins doesn't affect the answer", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Bottom-Up DP — Coin-Outer, Amount-Inner (Optimal)",
            "time_complexity": "O(amount * len(coins))",
            "space_complexity": "O(amount)",
            "description": (
                "Define `dp[i]` = number of ways to make amount `i`. Initialise `dp[0] = 1` (the empty "
                "combination). For each coin `c`, iterate amounts `a` from `c` upwards and add "
                "`dp[a - c]` to `dp[a]`. Putting coins on the *outside* fixes a canonical order in which "
                "denominations are 'introduced' — every combination is counted exactly once because the "
                "DP only ever extends a partial sum with the *current or later* coin, never an earlier "
                "one. Order-of-use is irrelevant because the DP doesn't track it."
            ),
            "code": {
                "python": (
                    "def change(amount, coins):\n"
                    "    dp = [0] * (amount + 1)\n"
                    "    dp[0] = 1\n"
                    "    for c in coins:\n"
                    "        for a in range(c, amount + 1):\n"
                    "            dp[a] += dp[a - c]\n"
                    "    return dp[amount]"
                ),
                "javascript": (
                    "function change(amount, coins) {\n"
                    "    const dp = new Array(amount + 1).fill(0);\n"
                    "    dp[0] = 1;\n"
                    "    for (const c of coins) {\n"
                    "        for (let a = c; a <= amount; a++) {\n"
                    "            dp[a] += dp[a - c];\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[amount];\n"
                    "}"
                ),
                "java": (
                    "public int change(int amount, int[] coins) {\n"
                    "    int[] dp = new int[amount + 1];\n"
                    "    dp[0] = 1;\n"
                    "    for (int c : coins) {\n"
                    "        for (int a = c; a <= amount; a++) {\n"
                    "            dp[a] += dp[a - c];\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[amount];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Wrong Loop Order — Counts Permutations, NOT Combinations",
            "time_complexity": "O(amount * len(coins))",
            "space_complexity": "O(amount)",
            "description": (
                "If you swap the loops — amount on the outside, coins on the inside — the recurrence "
                "becomes 'number of ordered sequences of coins summing to `i`'. For amount=5 with "
                "coins=[1,2,5], this yields 9 (every ordering of 1+2+2 is counted separately) instead "
                "of the correct 4. Use this only as a counter-example when explaining why the canonical "
                "order matters; never submit it. (The same recurrence with this loop order is the "
                "*correct* answer to LC 377 'Combination Sum IV', which asks for ordered sequences — "
                "easy to mix the two up under interview pressure.)"
            ),
            "code": {
                "python": (
                    "def change_wrong(amount, coins):\n"
                    "    # WRONG for LC 518 — counts permutations.\n"
                    "    dp = [0] * (amount + 1)\n"
                    "    dp[0] = 1\n"
                    "    for a in range(1, amount + 1):\n"
                    "        for c in coins:\n"
                    "            if a - c >= 0:\n"
                    "                dp[a] += dp[a - c]\n"
                    "    return dp[amount]  # change_wrong(5, [1,2,5]) == 9, not 4"
                ),
            },
        },
        {
            "title": "2D DP (Pedagogical)",
            "time_complexity": "O(amount * len(coins))",
            "space_complexity": "O(amount * len(coins))",
            "description": (
                "Define `dp[i][a]` = number of ways to make `a` using only the first `i` coin types. "
                "Recurrence: `dp[i][a] = dp[i-1][a]` (don't use coin i) `+ dp[i][a - coins[i-1]]` "
                "(use one more coin i — note same row, since unlimited supply). The 1D version above "
                "is the in-place collapse of this table. Worth deriving once on paper to internalise "
                "*why* coin-outer / amount-inner is correct: each row introduces one more coin type, "
                "and within a row every combination uses only coins seen so far in canonical order."
            ),
            "code": {
                "python": (
                    "def change(amount, coins):\n"
                    "    n = len(coins)\n"
                    "    dp = [[0] * (amount + 1) for _ in range(n + 1)]\n"
                    "    for i in range(n + 1):\n"
                    "        dp[i][0] = 1\n"
                    "    for i in range(1, n + 1):\n"
                    "        for a in range(amount + 1):\n"
                    "            dp[i][a] = dp[i - 1][a]\n"
                    "            if a >= coins[i - 1]:\n"
                    "                dp[i][a] += dp[i][a - coins[i - 1]]\n"
                    "    return dp[n][amount]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the problem shape: counting combinations under an unbounded knapsack. Each coin has unlimited supply, so this is *not* 0/1 knapsack — we can reuse a coin many times.",
        "2. Define the state. `dp[i] = number of ways to make amount i`. Base case `dp[0] = 1` is non-obvious but essential: there's exactly one way to make 0 — pick nothing. That base case is what every combination ultimately decomposes to.",
        "3. Recurrence: for each coin `c`, every way to reach `i - c` extends to a way to reach `i` by appending one `c`. So `dp[i] += dp[i - c]`. The += matters — the contributions from different coins accumulate.",
        "4. Loop order is *the* subtle bit. Outer-coin, inner-amount: when we process coin `c`, we add ways using *that coin or earlier coins only*. Combinations are counted in a canonical 'coins introduced left-to-right' order, so each multiset is counted exactly once.",
        "5. Why amount-outer / coin-inner over-counts: with that order, when we update `dp[a]` we include contributions from *all* coins, treating `1+2` and `2+1` as distinct paths to amount 3. That's the recurrence for LC 377 (ordered sequences), not LC 518.",
        "6. Edge cases: `amount = 0` → return 1 (empty combination). Unreachable amount (e.g. amount=3, coins=[2]) → returns 0 because no recurrence ever lands on it. Single-coin exact match → 1. Final answer fits in 32-bit int per the problem constraints.",
    ],
    "tips": [
        "Don't confuse with LC 322 'Coin Change' — that asks for the *minimum* number of coins to make `amount`. Same data, completely different recurrence (`min` over `1 + dp[i - c]`).",
        "Don't confuse with LC 377 'Combination Sum IV' either — same DP shape but with amount-outer / coin-inner, because that problem *wants* permutations counted distinctly.",
        "This is unbounded knapsack, not 0/1 knapsack. The tell: in the inner loop we iterate `a` from `c` *upwards* (so `dp[a - c]` already includes coin `c`'s contributions), not downwards. Iterating downwards would convert it to 0/1 — each coin used at most once.",
        "If asked to enumerate the actual combinations rather than just count them, switch to backtracking — DP gives you the count cheaply, but reconstructing combinations from the table is fiddlier than just doing a recursive search with sorted coins to enforce canonical order.",
        "32-bit-int guarantee in the constraints lets you ignore overflow in Java/C++. Without it you'd want `long` or modular arithmetic — counts grow roughly like a polynomial in `amount` of degree `len(coins) - 1`.",
    ],
    "companies": ["Amazon", "Bloomberg"],
    "topics": ["Array", "Dynamic Programming"],
    "time_complexity": "O(amount * len(coins))",
    "space_complexity": "O(amount)",
}


def REFERENCE(amount, coins):
    dp = [0] * (amount + 1)
    dp[0] = 1
    for c in coins:
        for a in range(c, amount + 1):
            dp[a] += dp[a - c]
    return dp[amount]


register(PAYLOAD, REFERENCE)
