"""Best Time to Buy and Sell Stock with Transaction Fee — Medium. DP / Greedy.

Stock II's 'unlimited transactions' problem with a per-transaction fee. The
clean framing is a two-state DP: at any moment you're either holding a share
(`hold`) or not (`cash`). The recurrence collapses to two scalars, O(1) space.
A greedy interpretation also works — track an effective buy price and 'sell'
whenever the current price beats it by more than the fee — but the DP framing
generalises to the rest of the stock-question family.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Best Time to Buy and Sell Stock with Transaction Fee",
    "difficulty": "Medium",
    "description": (
        "You are given an array `prices` where `prices[i]` is the price of a given stock on the i-th day, "
        "and an integer `fee` representing a transaction fee.\n\n"
        "Find the **maximum profit** you can achieve. You may complete as many transactions as you like, "
        "but you need to **pay the transaction fee for each transaction** (a buy followed by a sell counts "
        "as one transaction).\n\n"
        "**Note:** You may not engage in multiple transactions simultaneously (i.e., you must sell the "
        "stock before you buy again).\n\n"
        "**Example 1:**\n"
        "- Input: `prices = [1,3,2,8,4,9]`, `fee = 2`\n"
        "- Output: `8`\n"
        "- Explanation: The maximum profit can be achieved by:\n"
        "  - Buying at `prices[0] = 1`\n"
        "  - Selling at `prices[3] = 8`, profit = 8 - 1 - 2 = 5\n"
        "  - Buying at `prices[4] = 4`\n"
        "  - Selling at `prices[5] = 9`, profit = 9 - 4 - 2 = 3\n"
        "  - Total profit = 5 + 3 = 8.\n\n"
        "**Example 2:**\n"
        "- Input: `prices = [1,3,7,5,10,3]`, `fee = 3`\n"
        "- Output: `6`\n"
        "- Explanation: Buy at 1, sell at 10 → profit = 10 - 1 - 3 = 6. A second transaction never beats the fee."
    ),
    "hints": [
        "Two states per day: `cash` (no share held) and `hold` (one share held). Track the maximum profit "
        "achievable in each state as you walk left-to-right.",
        "Transitions: `hold = max(hold, cash - price)` (keep holding, or buy today). "
        "`cash = max(cash, hold + price - fee)` (stay in cash, or sell today and pay the fee).",
        "Initial values: `cash = 0`, `hold = -prices[0]`. The answer at the end is `cash` — you'd never "
        "want to finish still holding a share.",
        "Greedy alternative: track an effective buy price `buy = prices[0]`. Whenever `price > buy + fee`, "
        "realise profit `price - buy - fee` and reset `buy = price - fee` (so consecutive higher prices "
        "extend the same trade without re-paying the fee).",
        "Edge cases: monotonic descent → 0 profit. A single price → 0 profit. `fee` larger than any "
        "achievable gain → 0 profit. The DP handles all of these by construction.",
    ],
    "constraints": [
        "1 <= prices.length <= 5 * 10⁴",
        "1 <= prices[i] < 5 * 10⁴",
        "0 <= fee < 5 * 10⁴",
    ],
    "starter_code": {
        "python": "def max_profit(prices, fee):\n    # Your code here\n    pass",
        "javascript": "function maxProfit(prices, fee) {\n    // Your code here\n}",
        "java": "public int maxProfit(int[] prices, int fee) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([1,3,2,8,4,9], 2), ([1,3,7,5,10,3], 3), ([5,4,3,2,1], 1)]\n"
            "    for prices, fee in cases:\n"
            "        print(f\"max_profit({prices}, fee={fee}) = {max_profit(prices, fee)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,3,2,8,4,9], 2], [[1,3,7,5,10,3], 3]].forEach(([prices, fee]) =>\n"
            "    console.log(`maxProfit =`, maxProfit(prices, fee))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.maxProfit(new int[]{1,3,2,8,4,9}, 2));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"prices": [1, 3, 2, 8, 4, 9], "fee": 2}, "expected": 8,
         "description": "Classic LC example — two profitable transactions net of fee", "tags": ["basic"]},
        {"input": {"prices": [1, 3, 7, 5, 10, 3], "fee": 3}, "expected": 6,
         "description": "One big trade beats two small ones once fee is paid", "tags": ["basic"]},
        {"input": {"prices": [5, 4, 3, 2, 1], "fee": 1}, "expected": 0,
         "description": "Monotonic descent — no profitable trade", "tags": ["edge"]},
        {"input": {"prices": [1, 2], "fee": 5}, "expected": 0,
         "description": "Fee larger than the only possible gain", "tags": ["edge"]},
        {"input": {"prices": [7]}, "expected": 0,
         "description": "Single price — no transaction possible (fee defaulted)", "tags": ["edge"]},
        {"input": {"prices": [10, 1, 1, 1, 1, 10], "fee": 3}, "expected": 6,
         "description": "Buy the trough, sell the peak; fee leaves 6 profit", "tags": ["tricky"]},
        {"input": {"prices": [1, 5, 2, 8], "fee": 0}, "expected": 10,
         "description": "Zero fee — equivalent to Stock II, sum of positive deltas", "tags": ["tricky"]},
        {"input": {"prices": [3, 3, 3, 3, 3], "fee": 1}, "expected": 0,
         "description": "Flat prices — never trade", "tags": ["edge"]},
        {"input": {"prices": [1, 100], "fee": 50}, "expected": 49,
         "description": "Big swing, big fee — single transaction nets 49", "tags": ["basic"]},
        {"input": {"prices": [4, 1, 8, 2, 9, 3, 10], "fee": 1}, "expected": 18,
         "description": "Three peaks, three troughs — three transactions, 7+6+5 = 18", "tags": ["tricky"]},
        {"input": {"prices": list(range(1, 1001)), "fee": 0}, "expected": 999,
         "description": "Ascending with zero fee — full-range trade", "tags": ["large"]},
        {"input": {"prices": list(range(1000, 0, -1)), "fee": 1}, "expected": 0,
         "description": "1K strictly descending — never trade", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Two-State Rolling DP (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "At each day track two scalars: `cash` (max profit holding no share) and `hold` (max profit "
                "while holding a share). Transitions: `hold = max(hold, cash - price)` and "
                "`cash = max(cash, hold + price - fee)`. The final answer is `cash`, since ending in `hold` "
                "always loses the unrealised cost. One pass, O(1) memory."
            ),
            "code": {
                "python": (
                    "def max_profit(prices, fee=0):\n"
                    "    if not prices:\n"
                    "        return 0\n"
                    "    cash, hold = 0, -prices[0]\n"
                    "    for p in prices[1:]:\n"
                    "        cash = max(cash, hold + p - fee)\n"
                    "        hold = max(hold, cash - p)\n"
                    "    return cash"
                ),
                "javascript": (
                    "function maxProfit(prices, fee = 0) {\n"
                    "    if (!prices.length) return 0;\n"
                    "    let cash = 0, hold = -prices[0];\n"
                    "    for (let i = 1; i < prices.length; i++) {\n"
                    "        const p = prices[i];\n"
                    "        cash = Math.max(cash, hold + p - fee);\n"
                    "        hold = Math.max(hold, cash - p);\n"
                    "    }\n"
                    "    return cash;\n"
                    "}"
                ),
                "java": (
                    "public int maxProfit(int[] prices, int fee) {\n"
                    "    if (prices.length == 0) return 0;\n"
                    "    int cash = 0, hold = -prices[0];\n"
                    "    for (int i = 1; i < prices.length; i++) {\n"
                    "        int p = prices[i];\n"
                    "        cash = Math.max(cash, hold + p - fee);\n"
                    "        hold = Math.max(hold, cash - p);\n"
                    "    }\n"
                    "    return cash;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Greedy with Effective Buy Price",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Maintain an *effective* buy price `buy`. When today's price exceeds `buy + fee`, you'd "
                "lock in profit `price - buy - fee` and reset `buy = price - fee`. The reset trick lets "
                "consecutive higher prices extend the same trade without re-paying the fee — a fresh "
                "buy at `price - fee` would yield the same future profits as continuing the current hold. "
                "When today's price falls below `buy`, update `buy = price` (cheaper entry available)."
            ),
            "code": {
                "python": (
                    "def max_profit(prices, fee=0):\n"
                    "    if not prices:\n"
                    "        return 0\n"
                    "    profit = 0\n"
                    "    buy = prices[0]\n"
                    "    for p in prices[1:]:\n"
                    "        if p < buy:\n"
                    "            buy = p\n"
                    "        elif p > buy + fee:\n"
                    "            profit += p - buy - fee\n"
                    "            buy = p - fee  # extend the trade without re-paying the fee\n"
                    "    return profit"
                ),
                "javascript": (
                    "function maxProfit(prices, fee = 0) {\n"
                    "    if (!prices.length) return 0;\n"
                    "    let profit = 0, buy = prices[0];\n"
                    "    for (let i = 1; i < prices.length; i++) {\n"
                    "        const p = prices[i];\n"
                    "        if (p < buy) buy = p;\n"
                    "        else if (p > buy + fee) {\n"
                    "            profit += p - buy - fee;\n"
                    "            buy = p - fee;\n"
                    "        }\n"
                    "    }\n"
                    "    return profit;\n"
                    "}"
                ),
                "java": (
                    "public int maxProfit(int[] prices, int fee) {\n"
                    "    if (prices.length == 0) return 0;\n"
                    "    int profit = 0, buy = prices[0];\n"
                    "    for (int i = 1; i < prices.length; i++) {\n"
                    "        int p = prices[i];\n"
                    "        if (p < buy) buy = p;\n"
                    "        else if (p > buy + fee) {\n"
                    "            profit += p - buy - fee;\n"
                    "            buy = p - fee;\n"
                    "        }\n"
                    "    }\n"
                    "    return profit;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Without the fee this is Stock II — sum every positive delta. The fee breaks that, because tiny "
        "up-ticks no longer pay for themselves.",
        "2. Reframe with two states per day: `cash` (no share) and `hold` (one share). Walk left-to-right, "
        "updating both.",
        "3. Transitions follow from 'what could I have done yesterday?': stay, or flip state by paying "
        "(buy) or earning (sell − fee).",
        "4. Final answer is `cash` — finishing in `hold` means an unsold share, always weakly worse.",
        "5. Greedy alternative: when `price > buy + fee`, take the profit and reset `buy = price − fee`. "
        "The reset is the subtle bit — it lets higher subsequent prices extend the same trade.",
        "6. Edge cases (descending series, fee dominates, single price) all return 0 by construction in "
        "either approach.",
    ],
    "tips": [
        "Update order matters in the DP: compute `cash` from the *old* `hold`, then update `hold` from the "
        "*new* `cash` — or use temporaries. Either is fine; just be consistent.",
        "The greedy reset `buy = price - fee` is the moral equivalent of 'I haven't actually closed the "
        "position yet, I'm only locking in profit.' Be ready to explain that in interview.",
        "When `fee = 0`, both solutions degenerate to Stock II and the answer is the sum of positive "
        "consecutive deltas. Good sanity check.",
        "Common follow-up — Stock with cooldown (LC 309): same DP shape, a third state (`cooldown`) is added.",
        "Common follow-up — at most k transactions (LC 188): the state machine becomes 2D over (day, "
        "transactions used). O(nk) time.",
        "Don't try to apply the simple 'sum positive deltas' from Stock II — once a fee exists, small "
        "up-ticks become net losses. The DP/greedy is required.",
    ],
    "companies": ["Amazon", "Bloomberg", "Google", "Facebook", "Microsoft"],
    "topics": ["Array", "Dynamic Programming", "Greedy"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(prices, fee=0):
    if not prices:
        return 0
    cash, hold = 0, -prices[0]
    for p in prices[1:]:
        cash = max(cash, hold + p - fee)
        hold = max(hold, cash - p)
    return cash


register(PAYLOAD, REFERENCE)
