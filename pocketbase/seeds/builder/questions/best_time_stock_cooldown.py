"""Best Time to Buy and Sell Stock with Cooldown — Medium. State-Machine DP.

The natural follow-up to Stock I/II once cooldown enters the picture: the
single-pass min-tracking trick stops working because today's decision now
depends on yesterday's *and* the day-before's state. The clean framing is a
three-state machine — held / sold-today / resting — with O(1) transitions.
Worth knowing because the same recurrence handles 'with fee', 'k transactions',
and most other LeetCode stock variants with one extra dimension.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Best Time to Buy and Sell Stock with Cooldown",
    "difficulty": "Medium",
    "description": (
        "You are given an array `prices` where `prices[i]` is the price of a given stock on the i-th day.\n\n"
        "Find the maximum profit you can achieve. You may complete as many transactions as you like (i.e., "
        "buy one and sell one share of the stock multiple times) with the following restrictions:\n\n"
        "- You may not engage in multiple transactions simultaneously (i.e., you must sell the stock before you buy again).\n"
        "- After you sell your stock, you cannot buy stock on the next day (**1-day cooldown**).\n\n"
        "**Example 1:**\n"
        "- Input: `prices = [1,2,3,0,2]`\n"
        "- Output: `3`\n"
        "- Explanation: transactions = [buy, sell, cooldown, buy, sell]. Profit = (2 - 1) + (2 - 0) = 3.\n\n"
        "**Example 2:**\n"
        "- Input: `prices = [1]`\n"
        "- Output: `0`\n"
        "- Explanation: Only one day — no transaction possible."
    ),
    "hints": [
        "Three states per day capture every situation: `held` (currently owning a share), `sold` (just sold *today* — cooldown begins tomorrow), `rest` (not holding and not in cooldown).",
        "Transitions: `held = max(held_prev, rest_prev - price)` (carry or buy from rest), `sold = held_prev + price` (sell today), `rest = max(rest_prev, sold_prev)` (idle or finish a cooldown).",
        "Initialise on day 0: `held = -prices[0]`, `sold = 0`, `rest = 0`. The answer is `max(sold, rest)` after the last day — never `held`, because you wouldn't end holding a share.",
        "Each new day's three values depend only on the previous day's three values → compress to three rolling scalars, O(1) extra space.",
        "Top-down alternative: `dfs(i, can_buy)` memoised on (day, holding-flag). Same O(n) time but O(n) recursion depth — useful for explaining the state, then collapse to the iterative version.",
    ],
    "constraints": [
        "1 <= prices.length <= 5000",
        "0 <= prices[i] <= 1000",
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
            "    cases = [[1,2,3,0,2], [1], [1,2,4], [6,1,3,2,4,7]]\n"
            "    for prices in cases:\n"
            "        print(f\"max_profit({prices}) = {max_profit(prices)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,2,3,0,2], [1], [1,2,4], [6,1,3,2,4,7]].forEach(prices =>\n"
            "    console.log(`maxProfit =`, maxProfit(prices))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.maxProfit(new int[]{1,2,3,0,2}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"prices": [1, 2, 3, 0, 2]}, "expected": 3,
         "description": "Classic LC sample — buy/sell/cooldown/buy/sell", "tags": ["basic"]},
        {"input": {"prices": [1]}, "expected": 0,
         "description": "Single price — no transaction possible", "tags": ["edge"]},
        {"input": {"prices": [5, 4, 3, 2, 1]}, "expected": 0,
         "description": "Strictly descending — never trade", "tags": ["basic"]},
        {"input": {"prices": [1, 2, 3, 4, 5]}, "expected": 4,
         "description": "Strictly ascending — single buy/sell beats fragmented trades because cooldown costs",
         "tags": ["tricky"]},
        {"input": {"prices": [1, 2]}, "expected": 1,
         "description": "Two days ascending — one trade", "tags": ["edge"]},
        {"input": {"prices": [2, 1]}, "expected": 0,
         "description": "Two days descending — no trade", "tags": ["edge"]},
        {"input": {"prices": [1, 4, 2, 7]}, "expected": 6,
         "description": "Alternating — best is single trade (1→7); cooldown blocks 1→4 then 2→7",
         "tags": ["tricky"]},
        {"input": {"prices": [6, 1, 3, 2, 4, 7]}, "expected": 6,
         "description": "Buy 1 sell 3 cooldown buy 2 sell 7 → 2 + 5 = 7? No: cooldown blocks buy at 2; optimal is buy 1 sell 7 = 6",
         "tags": ["tricky"]},
        {"input": {"prices": [3, 3, 3, 3, 3]}, "expected": 0,
         "description": "Flat — no positive delta", "tags": ["edge"]},
        {"input": {"prices": [2, 1, 4, 5, 2, 9, 7]}, "expected": 10,
         "description": "Multiple windows — buy 1 sell 4 cooldown buy 2 sell 9 = 3 + 7",
         "tags": ["tricky"]},
        {"input": {"prices": list(range(1, 1001))}, "expected": 999,
         "description": "1K ascending — one full-range trade", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "State-Machine DP (Optimal, O(1) space)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Three rolling scalars: `held` = best profit ending today still holding a share; "
                "`sold` = best profit ending today having *just sold*; `rest` = best profit ending today "
                "neither holding nor in cooldown. Each day's transitions read only the previous day's "
                "values, so we keep three numbers and walk left-to-right. Answer = `max(sold, rest)` at the end."
            ),
            "code": {
                "python": (
                    "def max_profit(prices):\n"
                    "    if not prices:\n"
                    "        return 0\n"
                    "    held = -prices[0]\n"
                    "    sold = 0\n"
                    "    rest = 0\n"
                    "    for i in range(1, len(prices)):\n"
                    "        prev_held, prev_sold, prev_rest = held, sold, rest\n"
                    "        held = max(prev_held, prev_rest - prices[i])\n"
                    "        sold = prev_held + prices[i]\n"
                    "        rest = max(prev_rest, prev_sold)\n"
                    "    return max(sold, rest)"
                ),
                "javascript": (
                    "function maxProfit(prices) {\n"
                    "    if (!prices.length) return 0;\n"
                    "    let held = -prices[0], sold = 0, rest = 0;\n"
                    "    for (let i = 1; i < prices.length; i++) {\n"
                    "        const ph = held, ps = sold, pr = rest;\n"
                    "        held = Math.max(ph, pr - prices[i]);\n"
                    "        sold = ph + prices[i];\n"
                    "        rest = Math.max(pr, ps);\n"
                    "    }\n"
                    "    return Math.max(sold, rest);\n"
                    "}"
                ),
                "java": (
                    "public int maxProfit(int[] prices) {\n"
                    "    if (prices.length == 0) return 0;\n"
                    "    int held = -prices[0], sold = 0, rest = 0;\n"
                    "    for (int i = 1; i < prices.length; i++) {\n"
                    "        int ph = held, ps = sold, pr = rest;\n"
                    "        held = Math.max(ph, pr - prices[i]);\n"
                    "        sold = ph + prices[i];\n"
                    "        rest = Math.max(pr, ps);\n"
                    "    }\n"
                    "    return Math.max(sold, rest);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Top-Down Recursion + Memoization",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Define `dfs(i, can_buy)` = max profit achievable starting from day `i` given whether you're "
                "allowed to buy. If `can_buy`: choose to buy (pay `prices[i]`, recurse with holding) or skip "
                "(recurse with `can_buy`). If holding: choose to sell (gain `prices[i]`, then *skip* day i+1 "
                "for cooldown by jumping to `i+2` with `can_buy=True`) or hold (recurse). Memoise on "
                "`(i, can_buy)` — 2n states, O(1) work each."
            ),
            "code": {
                "python": (
                    "def max_profit(prices):\n"
                    "    from functools import lru_cache\n"
                    "    n = len(prices)\n"
                    "\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def dfs(i, can_buy):\n"
                    "        if i >= n:\n"
                    "            return 0\n"
                    "        if can_buy:\n"
                    "            buy = dfs(i + 1, False) - prices[i]\n"
                    "            skip = dfs(i + 1, True)\n"
                    "            return max(buy, skip)\n"
                    "        else:\n"
                    "            sell = dfs(i + 2, True) + prices[i]  # +2 enforces cooldown\n"
                    "            hold = dfs(i + 1, False)\n"
                    "            return max(sell, hold)\n"
                    "\n"
                    "    return dfs(0, True)"
                ),
                "javascript": (
                    "function maxProfit(prices) {\n"
                    "    const n = prices.length;\n"
                    "    const memo = new Map();\n"
                    "    const key = (i, b) => i * 2 + (b ? 1 : 0);\n"
                    "    const dfs = (i, canBuy) => {\n"
                    "        if (i >= n) return 0;\n"
                    "        const k = key(i, canBuy);\n"
                    "        if (memo.has(k)) return memo.get(k);\n"
                    "        let best;\n"
                    "        if (canBuy) {\n"
                    "            best = Math.max(dfs(i + 1, false) - prices[i], dfs(i + 1, true));\n"
                    "        } else {\n"
                    "            best = Math.max(dfs(i + 2, true) + prices[i], dfs(i + 1, false));\n"
                    "        }\n"
                    "        memo.set(k, best);\n"
                    "        return best;\n"
                    "    };\n"
                    "    return dfs(0, true);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the family: Stock I (one trade), II (unlimited), with-cooldown is II + a 1-day gate after each sell. The single-pass trick from I dies — today depends on more than yesterday.",
        "2. Pick states: at the end of each day you're in exactly one of {holding a share, just sold today, resting (idle, not in cooldown)}. Three states is enough.",
        "3. Write transitions in plain English first: to be holding today either you were holding yesterday or you bought today (which requires resting yesterday — *not* having just sold). To have just sold today you were holding yesterday and sold. To be resting today you were either resting or just-sold yesterday (the cooldown completes by today).",
        "4. Translate to math: `held = max(held_prev, rest_prev - p)`, `sold = held_prev + p`, `rest = max(rest_prev, sold_prev)`.",
        "5. Initialise day 0: `held = -prices[0]` (bought), `sold = 0` (impossible to have-just-sold without owning first; profit anchored at 0), `rest = 0`.",
        "6. Final answer: `max(sold, rest)` — never `held`, since holding at the end means you bought and never realised the profit.",
        "7. Compress: each step uses only the previous step's three values → three scalars, O(1) extra space.",
        "8. Verify on `[1,2,3,0,2]`: walk through and confirm the answer is 3 before coding it up.",
    ],
    "tips": [
        "When asked for the recurrence on the whiteboard, name the states *first* (held / sold / rest) and only then write the transitions. Naming clarifies what 'previous state' means.",
        "A common bug: writing `held = max(held_prev, sold_prev - p)` — that lets you buy the day after a sell, violating the cooldown. The correct predecessor is `rest_prev`, not `sold_prev`.",
        "If you end up with `held = ...sold_prev - p...` you've forgotten the cooldown rule. Always sanity-check by tracing two consecutive days where you sold then immediately bought.",
        "Common follow-up — *Stock with Transaction Fee*: same shape but no cooldown, just subtract the fee on sell. Two states (`held`, `cash`) suffice.",
        "Common follow-up — *Stock III/IV (k transactions)*: add a transaction-count dimension, giving O(nk). The general state-machine framing scales cleanly.",
        "Don't reach for `lru_cache` in an interview unless the iterative version is harder to explain. Here the iterative O(1)-space version is shorter and cleaner — lead with it.",
    ],
    "companies": ["Amazon", "Google", "Bloomberg", "Microsoft", "Adobe"],
    "topics": ["Array", "Dynamic Programming", "State Machine"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(prices):
    if not prices:
        return 0
    held = -prices[0]
    sold = 0
    rest = 0
    for i in range(1, len(prices)):
        prev_held, prev_sold, prev_rest = held, sold, rest
        held = max(prev_held, prev_rest - prices[i])
        sold = prev_held + prices[i]
        rest = max(prev_rest, prev_sold)
    return max(sold, rest)


register(PAYLOAD, REFERENCE)
