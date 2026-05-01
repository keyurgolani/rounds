"""Best Time to Buy and Sell Stock II — Medium. Greedy / DP.

The unconstrained variant of Stock I — unlimited transactions. The
greedy 'sum every positive delta' fits in three lines and is provably
optimal. Worth knowing the state-machine DP framing because the
follow-ups (III with k=2, IV with general k, with cooldown, with fee)
all stack on the same recurrence.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Best Time to Buy and Sell Stock II",
    "difficulty": "Medium",
    "description": (
        "You are given an integer array `prices` where `prices[i]` is the price of a given stock on the i-th day.\n\n"
        "On each day, you may decide to **buy and/or sell** the stock. You can only hold **at most one share** of "
        "the stock at any time. However, you can buy it then immediately sell it on the **same day**.\n\n"
        "Find and return the **maximum profit** you can achieve.\n\n"
        "**Example 1:**\n"
        "- Input: `prices = [7,1,5,3,6,4]`\n"
        "- Output: `7`\n"
        "- Explanation: Buy on day 2 (price = 1) and sell on day 3 (price = 5), profit = 4. Then buy on day 4 "
        "(price = 3) and sell on day 5 (price = 6), profit = 3. Total = 7.\n\n"
        "**Example 2:**\n"
        "- Input: `prices = [1,2,3,4,5]`\n"
        "- Output: `4`\n"
        "- Explanation: Buy on day 1, sell on day 5. Equivalent to summing every daily delta.\n\n"
        "**Example 3:**\n"
        "- Input: `prices = [7,6,4,3,1]`\n"
        "- Output: `0`\n"
        "- Explanation: Monotonic decrease — never trade."
    ),
    "hints": [
        "Unlike Stock I, you can transact as many times as you like. The constraint is just 'sell before you buy again'.",
        "Greedy insight: any uphill segment `a → b → c` with `a < b < c` is equivalent to two trades `(a→b) + (b→c)`. So **every positive daily delta contributes independently** to the answer.",
        "Three-line solution: `sum(max(0, prices[i] - prices[i-1]) for i in range(1, len(prices)))`.",
        "DP state machine — useful for the follow-ups: track `cash` (no stock) and `hold` (has stock). Transitions: `cash = max(cash, hold + price)`, `hold = max(hold, cash - price)`.",
        "Peak-valley framing: find every (valley, peak) pair and sum `peak − valley`. Provably equivalent to the greedy delta sum.",
    ],
    "constraints": [
        "1 <= prices.length <= 3 * 10⁴",
        "0 <= prices[i] <= 10⁴",
    ],
    "starter_code": {
        "python": "def max_profit_ii(prices):\n    # Your code here\n    pass",
        "javascript": "function maxProfit(prices) {\n    // Your code here\n}",
        "java": "public int maxProfit(int[] prices) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[7,1,5,3,6,4], [1,2,3,4,5], [7,6,4,3,1]]\n"
            "    for prices in cases:\n"
            "        print(f\"max_profit_ii({prices}) = {max_profit_ii(prices)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[7,1,5,3,6,4], [1,2,3,4,5], [7,6,4,3,1]].forEach(prices =>\n"
            "    console.log(`maxProfit =`, maxProfit(prices))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.maxProfit(new int[]{7,1,5,3,6,4}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"prices": [7, 1, 5, 3, 6, 4]}, "expected": 7,
         "description": "Two windows: (1→5) + (3→6) = 4 + 3", "tags": ["basic"]},
        {"input": {"prices": [1, 2, 3, 4, 5]}, "expected": 4,
         "description": "Monotonic increase — equivalent to single trade buy day 1, sell day 5", "tags": ["basic"]},
        {"input": {"prices": [7, 6, 4, 3, 1]}, "expected": 0,
         "description": "Monotonic decrease — never trade", "tags": ["basic"]},
        {"input": {"prices": [1]}, "expected": 0,
         "description": "Single day — no transaction possible", "tags": ["edge"]},
        {"input": {"prices": []}, "expected": 0,
         "description": "Empty input — no transaction possible", "tags": ["edge"]},
        {"input": {"prices": [3, 3, 3]}, "expected": 0,
         "description": "Flat — no positive delta", "tags": ["edge"]},
        {"input": {"prices": [2, 1, 2, 0, 1]}, "expected": 2,
         "description": "Two valleys: (1→2) + (0→1) = 1 + 1", "tags": ["tricky"]},
        {"input": {"prices": [1, 7, 2, 8, 3, 9]}, "expected": 18,
         "description": "Three peaks alternating with valleys — sum every uphill", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Greedy — Sum Positive Deltas (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk left-to-right; whenever today's price is higher than yesterday's, pocket the difference. "
                "Equivalent to buying at every local minimum and selling at every local maximum. Three lines, "
                "provably optimal."
            ),
            "code": {
                "python": (
                    "def max_profit_ii(prices):\n"
                    "    profit = 0\n"
                    "    for i in range(1, len(prices)):\n"
                    "        if prices[i] > prices[i - 1]:\n"
                    "            profit += prices[i] - prices[i - 1]\n"
                    "    return profit"
                ),
                "javascript": (
                    "function maxProfit(prices) {\n"
                    "    let profit = 0;\n"
                    "    for (let i = 1; i < prices.length; i++) {\n"
                    "        if (prices[i] > prices[i - 1]) profit += prices[i] - prices[i - 1];\n"
                    "    }\n"
                    "    return profit;\n"
                    "}"
                ),
                "java": (
                    "public int maxProfit(int[] prices) {\n"
                    "    int profit = 0;\n"
                    "    for (int i = 1; i < prices.length; i++) {\n"
                    "        if (prices[i] > prices[i - 1]) profit += prices[i] - prices[i - 1];\n"
                    "    }\n"
                    "    return profit;\n"
                    "}"
                ),
            },
        },
        {
            "title": "DP State Machine (Hold / Cash)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Track two states: `cash` (max profit while holding no stock) and `hold` (max profit while "
                "holding one share). Transitions per day: sell → `cash = max(cash, hold + price)`; buy → "
                "`hold = max(hold, cash - price)`. More verbose than the greedy, but generalises directly to "
                "the cooldown / fee / k-transactions follow-ups."
            ),
            "code": {
                "python": (
                    "def max_profit_ii(prices):\n"
                    "    cash, hold = 0, float('-inf')\n"
                    "    for p in prices:\n"
                    "        cash = max(cash, hold + p)\n"
                    "        hold = max(hold, cash - p)\n"
                    "    return cash"
                ),
            },
        },
        {
            "title": "Peak-Valley Walk",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Scan for each (valley, peak) pair: descend to the next local minimum, then ascend to the next "
                "local maximum, and add `peak − valley` to the profit. Equivalent to the greedy delta sum — "
                "useful as a verbal explanation in interviews."
            ),
            "code": {
                "python": (
                    "def max_profit_ii(prices):\n"
                    "    profit = 0\n"
                    "    i = 0\n"
                    "    n = len(prices)\n"
                    "    while i < n - 1:\n"
                    "        while i < n - 1 and prices[i + 1] <= prices[i]:\n"
                    "            i += 1\n"
                    "        valley = prices[i]\n"
                    "        while i < n - 1 and prices[i + 1] >= prices[i]:\n"
                    "            i += 1\n"
                    "        profit += prices[i] - valley\n"
                    "    return profit"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Note the difference from Stock I: unlimited transactions, only constraint is 'sell before buying again'.",
        "2. Brute force enumerates every subset of (buy, sell) pairs — exponential. Skip and head straight to greedy.",
        "3. Key observation: any uphill `a → b → c` with `a < b < c` decomposes into `(a→b) + (b→c)`, so capturing every positive daily delta is at least as good as any single longer trade across that segment.",
        "4. Conversely, any negative delta would lose money — skip it. Therefore `sum of max(0, prices[i] - prices[i-1])` is provably optimal.",
        "5. Edge cases: empty array (0), single price (0), flat prices (0), monotonic decrease (0).",
        "6. For the follow-ups (cooldown, fee, k transactions), the greedy stops working — fall back to the explicit cash/hold state-machine DP.",
    ],
    "tips": [
        "This is the *unconstrained* variant. Stock III caps you at k=2 transactions; Stock IV at general k; the cooldown variant adds a 1-day idle after every sell; the fee variant subtracts a fixed cost per transaction.",
        "Don't over-think it: 'buy at every valley, sell at every peak' is the exact same answer as 'sum every positive delta'. Pick whichever framing you can defend on a whiteboard.",
        "Same-day buy-and-sell is a no-op (zero profit) — the constraint that lets it happen is what makes the greedy work.",
        "If the interviewer adds a transaction fee, the greedy breaks — switch to the DP state machine and subtract `fee` on the sell transition.",
        "The state-machine DP is the unifying framework for the entire stock series. Memorise the two-state transitions and you can derive every variant on the spot.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg"],
    "topics": ["Array", "Greedy", "Dynamic Programming"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(prices):
    profit = 0
    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1]:
            profit += prices[i] - prices[i - 1]
    return profit


register(PAYLOAD, REFERENCE)
