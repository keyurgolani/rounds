"""Best Time to Buy and Sell Stock — Easy. Sliding Window / DP.

The 'one pass tracking the minimum so far' classic. Often presented
as DP — and it *is* DP — but it collapses to two scalar variables, so
most candidates write it as a single linear scan. Worth knowing the
DP framing because the follow-ups (II, III, IV, with cooldown, with
fee) all stack on the same recurrence.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Best Time to Buy and Sell Stock",
    "difficulty": "Easy",
    "description": (
        "You are given an array `prices` where `prices[i]` is the price of a given stock on the i-th day.\n\n"
        "You want to maximize your profit by choosing **a single day to buy** one stock and choosing **a "
        "different day in the future to sell** that stock.\n\n"
        "Return the maximum profit you can achieve from this transaction. If you cannot achieve any profit, "
        "return `0`.\n\n"
        "**Example 1:**\n"
        "- Input: `prices = [7,1,5,3,6,4]`\n"
        "- Output: `5`\n"
        "- Explanation: Buy on day 2 (price = 1) and sell on day 5 (price = 6), profit = 6 - 1 = 5.\n\n"
        "**Example 2:**\n"
        "- Input: `prices = [7,6,4,3,1]`\n"
        "- Output: `0`\n"
        "- Explanation: In this case, no transactions are done and the max profit = 0."
    ),
    "hints": [
        "Brute force: every (buy, sell) pair → O(n²). State it; never submit it for n up to 10⁵.",
        "Reframe: for each day, the best profit if you sell *today* is `today's price − minimum price seen on or before today`.",
        "One pass: maintain `min_so_far` and `best_profit`. For each price, update `best_profit = max(best_profit, price - min_so_far)` then update `min_so_far`.",
        "If the array is monotonically decreasing, the answer is 0 (you'd never buy). The single-pass code naturally returns 0 because no `price - min_so_far` ever beats 0.",
        "DP framing (worth knowing for the follow-ups): `dp[i] = max(dp[i-1], prices[i] - min_price[i])`. Collapses to two scalars.",
    ],
    "constraints": [
        "1 <= prices.length <= 10⁵",
        "0 <= prices[i] <= 10⁴",
    ],
    "starter_code": {
        "python": "def max_profit(prices):\n    # Your code here\n    pass",
        "javascript": "function maxProfit(prices) {\n    // Your code here\n}",
        "java": "public int maxProfit(int[] prices) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[7,1,5,3,6,4], [7,6,4,3,1], [1,2]]\n"
            "    for prices in cases:\n"
            "        print(f\"max_profit({prices}) = {max_profit(prices)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[7,1,5,3,6,4], [7,6,4,3,1]].forEach(prices =>\n"
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
        {"input": {"prices": [7, 1, 5, 3, 6, 4]}, "expected": 5,
         "description": "Buy at 1, sell at 6", "tags": ["basic"]},
        {"input": {"prices": [7, 6, 4, 3, 1]}, "expected": 0,
         "description": "Monotonic decrease — never buy", "tags": ["basic"]},
        {"input": {"prices": [1, 2]}, "expected": 1,
         "description": "Two-day case — buy day 1, sell day 2", "tags": ["edge"]},
        {"input": {"prices": [2, 1]}, "expected": 0,
         "description": "Two-day decreasing — no profit", "tags": ["edge"]},
        {"input": {"prices": [5]}, "expected": 0,
         "description": "Single day — no transaction possible", "tags": ["edge"]},
        {"input": {"prices": [1, 2, 3, 4, 5]}, "expected": 4,
         "description": "Monotonic increase — buy day 1, sell day 5", "tags": ["tricky"]},
        {"input": {"prices": [3, 3, 3, 3]}, "expected": 0,
         "description": "Flat — no positive delta", "tags": ["edge"]},
        {"input": {"prices": [2, 4, 1]}, "expected": 2,
         "description": "Best window is the first two days, despite a deeper trough later",
         "tags": ["tricky"]},
        {"input": {"prices": [3, 2, 6, 5, 0, 3]}, "expected": 4,
         "description": "Two valleys, two peaks — only the (2 → 6) window wins", "tags": ["tricky"]},
        {"input": {"prices": list(range(10000))}, "expected": 9999,
         "description": "10K ascending — full-range trade", "tags": ["large"]},
        {"input": {"prices": list(range(10000, 0, -1))}, "expected": 0,
         "description": "10K strictly decreasing — never trade", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Single Pass (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Track the minimum price seen so far. For each new price, compute the profit if you sold "
                "today (price − min_so_far) and update the running best. Update min_so_far afterwards. "
                "One pass, two scalars."
            ),
            "code": {
                "python": (
                    "def max_profit(prices):\n"
                    "    min_so_far = float('inf')\n"
                    "    best = 0\n"
                    "    for p in prices:\n"
                    "        if p < min_so_far:\n"
                    "            min_so_far = p\n"
                    "        elif p - min_so_far > best:\n"
                    "            best = p - min_so_far\n"
                    "    return best"
                ),
                "javascript": (
                    "function maxProfit(prices) {\n"
                    "    let minSoFar = Infinity, best = 0;\n"
                    "    for (const p of prices) {\n"
                    "        if (p < minSoFar) minSoFar = p;\n"
                    "        else if (p - minSoFar > best) best = p - minSoFar;\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "public int maxProfit(int[] prices) {\n"
                    "    int minSoFar = Integer.MAX_VALUE, best = 0;\n"
                    "    for (int p : prices) {\n"
                    "        if (p < minSoFar) minSoFar = p;\n"
                    "        else if (p - minSoFar > best) best = p - minSoFar;\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "Try every (buy_day, sell_day) pair. Mention as the baseline; never submit for n up to 10⁵."
            ),
            "code": {
                "python": (
                    "def max_profit(prices):\n"
                    "    best = 0\n"
                    "    for i in range(len(prices)):\n"
                    "        for j in range(i + 1, len(prices)):\n"
                    "            best = max(best, prices[j] - prices[i])\n"
                    "    return best"
                ),
            },
        },
        {
            "title": "Kadane on Daily Deltas",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "View each day as a delta `prices[i] - prices[i-1]`. The maximum profit equals the maximum "
                "*subarray sum* of those deltas — Kadane's algorithm. Equivalent to the single-pass approach "
                "but worth recognising because it generalises to 'Maximum Subarray' questions."
            ),
            "code": {
                "python": (
                    "def max_profit(prices):\n"
                    "    best = current = 0\n"
                    "    for i in range(1, len(prices)):\n"
                    "        delta = prices[i] - prices[i - 1]\n"
                    "        current = max(0, current + delta)\n"
                    "        best = max(best, current)\n"
                    "    return best"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force is n². State it as the baseline.",
        "2. Reframe: for each day, what's the best profit if I sell *today*? That's `today − min_before_today`.",
        "3. Maintain `min_so_far` as you walk left-to-right; the running answer is `max(answer, price − min_so_far)`.",
        "4. Update order matters: compute the profit *before* updating `min_so_far` so you never sell on the same day you bought.",
        "5. If prices monotonically decrease, no positive profit is ever computed → answer stays 0. Correct by construction.",
        "6. Edge cases: single day (return 0), all-equal prices (return 0), monotonic increase (return last − first).",
    ],
    "tips": [
        "Initialising `min_so_far` to the first price (and starting the loop at index 1) is equivalent. Pick one and stick with it.",
        "Don't use `min(prices)` then `max(prices)` — that's wrong. The min must occur *before* the max in array order.",
        "Common follow-up — Stock II: 'unlimited transactions'. Sum every positive delta. Trivial in 3 lines.",
        "Common follow-up — Stock III/IV: 'k transactions max'. State-machine DP with `O(nk)` time.",
        "Common follow-up — with cooldown / with fee: same DP, extra states. The single-pass version stops working; you need the explicit state machine.",
    ],
    "companies": ["Amazon", "Facebook", "Microsoft", "Bloomberg", "Uber"],
    "topics": ["Array", "Dynamic Programming"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(prices):
    min_so_far = float('inf')
    best = 0
    for p in prices:
        if p < min_so_far:
            min_so_far = p
        elif p - min_so_far > best:
            best = p - min_so_far
    return best


register(PAYLOAD, REFERENCE)
