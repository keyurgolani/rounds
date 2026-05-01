"""Stock Buy/Sell with Indices — Easy/Medium. Single Pass.

Buy/sell once for max profit. Return the (buy_index, sell_index) pair.
Same algorithm as Best Time to Buy and Sell Stock — track the min so
far and the best profit pair found."""
from builder.registry import register


PAYLOAD = {
    "title": "Stock Buy/Sell — Best Pair of Days",
    "difficulty": "Medium",
    "description": (
        "Given a list of historic stock prices `prices`, return the indices `(buy_day, sell_day)` "
        "maximising profit, with the constraint `buy_day < sell_day`. If no profitable transaction "
        "exists, return `[-1, -1]`.\n\n"
        "If multiple pairs achieve the same maximum profit, return the EARLIEST `buy_day`; among ties on "
        "buy_day, the earliest `sell_day`.\n\n"
        "**Example:**\n"
        "- Input: `prices = [7, 1, 5, 3, 6, 4]`\n"
        "- Output: `[1, 4]` (buy on day 1 at 1, sell on day 4 at 6, profit 5)"
    ),
    "hints": [
        "Brute force: every (buy, sell) pair, O(n²). State; reject.",
        "Single pass: track `min_price_index_so_far`. For each `i`, profit if sold today is `prices[i] - prices[min_idx]`. Update best pair.",
        "Tie-break: keep the earliest buy day on ties; only update best when strictly greater profit.",
        "If the array is monotonic decreasing, no profit is possible — return [-1, -1].",
        "Edge cases: empty, single element, all-equal, all-decreasing.",
    ],
    "constraints": [
        "0 <= |prices| <= 10⁵",
        "0 <= prices[i] <= 10⁵",
    ],
    "starter_code": {
        "python": "def best_buy_sell(prices):\n    # Your code here\n    pass",
        "javascript": "function bestBuySell(prices) {\n    // Your code here\n}",
        "java": "public int[] bestBuySell(int[] prices) {\n    // Your code here\n    return new int[]{-1, -1};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(best_buy_sell([7, 1, 5, 3, 6, 4]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"prices": [7, 1, 5, 3, 6, 4]}, "expected": [1, 4],
         "description": "Standard example", "tags": ["basic"]},
        {"input": {"prices": [7, 6, 4, 3, 1]}, "expected": [-1, -1],
         "description": "Monotonic decrease — no profit", "tags": ["edge"]},
        {"input": {"prices": []}, "expected": [-1, -1],
         "description": "Empty input", "tags": ["edge"]},
        {"input": {"prices": [5]}, "expected": [-1, -1],
         "description": "Single element — no transaction possible", "tags": ["edge"]},
        {"input": {"prices": [1, 2, 3, 4, 5]}, "expected": [0, 4],
         "description": "Monotonic increase — full window", "tags": ["edge"]},
        {"input": {"prices": [3, 3, 3]}, "expected": [-1, -1],
         "description": "All equal — zero profit (no positive transaction)",
         "tags": ["edge"]},
        {"input": {"prices": [2, 4, 1, 3]}, "expected": [0, 1],
         "description": "Two valleys, but the early window has the largest delta",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Single Pass with Min-Index (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk once. Maintain `min_idx` (index of minimum price seen so far). For each i, compute "
                "the profit if sold on day i (relative to min_idx). Update best pair on strict improvement. "
                "Update min_idx only when a strictly smaller price appears."
            ),
            "code": {
                "python": (
                    "def best_buy_sell(prices):\n"
                    "    if len(prices) < 2:\n"
                    "        return [-1, -1]\n"
                    "    min_idx = 0\n"
                    "    best = [-1, -1]\n"
                    "    best_profit = 0\n"
                    "    for i in range(1, len(prices)):\n"
                    "        if prices[i] < prices[min_idx]:\n"
                    "            min_idx = i\n"
                    "        else:\n"
                    "            profit = prices[i] - prices[min_idx]\n"
                    "            if profit > best_profit:\n"
                    "                best_profit = profit\n"
                    "                best = [min_idx, i]\n"
                    "    return best"
                ),
                "javascript": (
                    "function bestBuySell(prices) {\n"
                    "    if (prices.length < 2) return [-1, -1];\n"
                    "    let minIdx = 0;\n"
                    "    let best = [-1, -1], bestProfit = 0;\n"
                    "    for (let i = 1; i < prices.length; i++) {\n"
                    "        if (prices[i] < prices[minIdx]) minIdx = i;\n"
                    "        else {\n"
                    "            const profit = prices[i] - prices[minIdx];\n"
                    "            if (profit > bestProfit) { bestProfit = profit; best = [minIdx, i]; }\n"
                    "        }\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. State the brute-force baseline (every pair, O(n²)). Reject for large n.",
        "2. Single pass: 'for each day, what's the most I could sell at today's price?' That's `today - min(before today)`.",
        "3. Track min_idx, not min_value, so we can return indices.",
        "4. Update min_idx only on a STRICTLY smaller price (preserves earliest-buy tie-break).",
        "5. Update best pair only on STRICTLY larger profit (preserves earliest-buy on profit ties).",
        "6. Edge cases: <2 prices, monotonic decrease, all-equal, ascending.",
    ],
    "tips": [
        "Strict inequalities for both updates — that's the tie-break invariant.",
        "If the question requires return value (just profit, not indices), this collapses to the canonical 'Best Time to Buy and Sell Stock' problem.",
        "Common follow-up: 'multiple transactions, no overlap.' Sum every positive delta — Stock II.",
        "Common follow-up: 'k transactions max.' DP with O(nk) states.",
        "Common follow-up: 'with cooldown / fee.' DP with extra state.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg"],
    "topics": ["Array", "Single Pass", "Greedy"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(prices):
    if len(prices) < 2:
        return [-1, -1]
    min_idx = 0
    best = [-1, -1]
    best_profit = 0
    for i in range(1, len(prices)):
        if prices[i] < prices[min_idx]:
            min_idx = i
        else:
            profit = prices[i] - prices[min_idx]
            if profit > best_profit:
                best_profit = profit
                best = [min_idx, i]
    return best


register(PAYLOAD, REFERENCE)
