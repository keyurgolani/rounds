"""Change Machine — Easy/Medium. Greedy / Strategy.

Make change for an amount. Greedy works for canonical denominations
(US/EUR); DP for arbitrary denominations. Bar-raise: handle finite
inventory per denomination."""
from builder.registry import register


PAYLOAD = {
    "title": "Change Machine (Coin Inventory)",
    "difficulty": "Medium",
    "description": (
        "Implement a change machine. Given:\n"
        "- A denomination map `inventory: {denomination_value: count}` (e.g. `{25: 5, 10: 3, 1: 100}`).\n"
        "- An amount `amount` (in the same units).\n\n"
        "Return a `{denomination: count_used}` dict that exactly makes `amount` using only available "
        "coins. If exact change isn't possible (insufficient inventory or unsuitable denominations), "
        "return an empty dict.\n\n"
        "**Example 1 — sufficient inventory:**\n"
        "- Input: `inventory = {25: 5, 10: 3, 1: 100}, amount = 32`\n"
        "- Output: `{25: 1, 1: 7}`\n\n"
        "**Example 2 — insufficient inventory:**\n"
        "- Input: `inventory = {25: 1, 10: 0, 1: 0}, amount = 30`\n"
        "- Output: `{}`"
    ),
    "hints": [
        "Greedy (descending denominations, take as many as possible) is correct ONLY for canonical sets like US coins. With arbitrary denominations, greedy can fail (`amount=6, denoms={4, 3, 1}` → greedy picks 4+1+1, but 3+3 uses fewer; with limited inventory of 1s, greedy can fail outright).",
        "DP: `dp[a] = min coins to make amount a` with backtracking pointers. Handles arbitrary denominations correctly. With finite inventory, treat each coin as a bounded knapsack item.",
        "For US coins specifically (1, 5, 10, 25, 50, 100), greedy is provably optimal — but the inventory constraint can still force a fallback.",
        "Track 'remaining inventory' as you commit; rolling back on failure is just restoration.",
        "Edge cases: zero amount (empty result, success), no inventory, unsuitable denominations (e.g. only 5s for amount 3), fractional cents.",
    ],
    "constraints": [
        "0 <= amount <= 10⁴",
        "Denominations are positive integers",
        "0 <= inventory[d] <= 10⁵",
    ],
    "starter_code": {
        "python": "def make_change(inventory, amount):\n    # Your code here\n    pass",
        "javascript": "function makeChange(inventory, amount) {\n    // Your code here\n}",
        "java": "public Map<Integer, Integer> makeChange(Map<Integer, Integer> inventory, int amount) {\n    // Your code here\n    return new HashMap<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(make_change({25: 5, 10: 3, 1: 100}, 32))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"inventory": {25: 5, 10: 3, 1: 100}, "amount": 32},
         "expected": {"25": 1, "1": 7},
         "description": "Greedy works on US-canonical denominations", "tags": ["basic"]},
        {"input": {"inventory": {1: 10}, "amount": 0},
         "expected": {},
         "description": "Zero amount returns empty (success)", "tags": ["edge"]},
        {"input": {"inventory": {25: 1, 10: 0, 1: 0}, "amount": 30},
         "expected": {},
         "description": "Insufficient inventory", "tags": ["edge"]},
        {"input": {"inventory": {5: 3}, "amount": 7},
         "expected": {},
         "description": "No way to make exact change with given denominations",
         "tags": ["edge"]},
        {"input": {"inventory": {10: 5, 5: 5, 1: 5}, "amount": 30},
         "expected": {"10": 3},
         "description": "Greedy picks 3 tens — correct", "tags": ["basic"]},
        {"input": {"inventory": {10: 5, 5: 5, 1: 5}, "amount": 17},
         "expected": {"10": 1, "5": 1, "1": 2},
         "description": "Three denominations consumed", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Greedy with Inventory Check (US-Canonical)",
            "time_complexity": "O(D · A) worst case",
            "space_complexity": "O(D)",
            "description": (
                "Sort denominations descending. For each, take as many as `min(remaining_amount // denom, "
                "inventory[denom])`. If you finish at amount = 0, success. Correct for canonical "
                "denominations (US: 1/5/10/25/50/100, EUR: 1/2/5/10/20/50/100/200). Document the "
                "assumption."
            ),
            "code": {
                "python": (
                    "def make_change(inventory, amount):\n"
                    "    if amount == 0:\n"
                    "        return {}\n"
                    "    out = {}\n"
                    "    remaining = amount\n"
                    "    for denom in sorted(inventory.keys(), reverse=True):\n"
                    "        if remaining == 0:\n"
                    "            break\n"
                    "        avail = inventory[denom]\n"
                    "        use = min(remaining // denom, avail)\n"
                    "        if use > 0:\n"
                    "            out[denom] = use\n"
                    "            remaining -= use * denom\n"
                    "    if remaining != 0:\n"
                    "        return {}\n"
                    "    return out"
                ),
                "javascript": (
                    "function makeChange(inventory, amount) {\n"
                    "    if (amount === 0) return {};\n"
                    "    const denoms = Object.keys(inventory).map(Number).sort((a, b) => b - a);\n"
                    "    const out = {};\n"
                    "    let rem = amount;\n"
                    "    for (const d of denoms) {\n"
                    "        if (rem === 0) break;\n"
                    "        const use = Math.min(Math.floor(rem / d), inventory[d]);\n"
                    "        if (use > 0) { out[d] = use; rem -= use * d; }\n"
                    "    }\n"
                    "    return rem === 0 ? out : {};\n"
                    "}"
                ),
            },
        },
        {
            "title": "DP for Arbitrary Denominations",
            "time_complexity": "O(D · A · max_count)",
            "space_complexity": "O(A)",
            "description": (
                "Bounded knapsack: `dp[a] = min coins to make amount a` with bookkeeping for the "
                "denomination used at each step. Walk amounts 1 to A; for each denomination, try using "
                "k ∈ [0, min(amount/denom, inventory[denom])] coins. Reconstruct by tracking the chosen "
                "denomination per amount."
            ),
            "code": {
                "python": (
                    "def make_change(inventory, amount):\n"
                    "    if amount == 0:\n"
                    "        return {}\n"
                    "    INF = float('inf')\n"
                    "    dp = [INF] * (amount + 1)\n"
                    "    dp[0] = 0\n"
                    "    used = [None] * (amount + 1)\n"
                    "    denoms = sorted(inventory.keys())\n"
                    "    for a in range(1, amount + 1):\n"
                    "        for d in denoms:\n"
                    "            if d <= a and dp[a - d] != INF and dp[a - d] + 1 < dp[a]:\n"
                    "                dp[a] = dp[a - d] + 1\n"
                    "                used[a] = d\n"
                    "    if dp[amount] == INF:\n"
                    "        return {}\n"
                    "    # Reconstruct + check inventory\n"
                    "    out = {}\n"
                    "    a = amount\n"
                    "    while a > 0:\n"
                    "        d = used[a]\n"
                    "        out[d] = out.get(d, 0) + 1\n"
                    "        a -= d\n"
                    "    for d, c in out.items():\n"
                    "        if c > inventory[d]:\n"
                    "            return {}  # exceeds inventory; would need full bounded-knapsack\n"
                    "    return out"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Establish the denomination set. If it's US-canonical, greedy is provably optimal.",
        "2. Sort descending. For each denomination, take as many as possible without exceeding inventory.",
        "3. If you finish exactly at zero, success. Otherwise, return empty (no solution).",
        "4. For arbitrary denominations, switch to DP — greedy can give a non-optimal answer or fail outright.",
        "5. With finite inventory, even arbitrary-denomination DP needs bookkeeping per denomination — bounded knapsack territory.",
        "6. Edge cases: zero amount (success, empty), no inventory, denomination set that can't make the target, fractional cents.",
    ],
    "tips": [
        "Be explicit about which denominations you're assuming. If the question says 'US coins' you can lean on greedy; if it says 'arbitrary denominations' you cannot.",
        "Don't conflate 'no exact change possible' (real failure) with 'no inventory left'. Both return empty but the diagnostic is different.",
        "For internationalisation: cents-as-integers avoids float headaches. Don't represent amounts as floats.",
        "Common follow-up: 'minimise the number of coins ALSO subject to inventory.' That's bounded knapsack — still polynomial but uglier.",
        "Common follow-up: 'thread-safe.' Synchronise inventory access; consider optimistic CAS for high-throughput vending machines.",
    ],
    "companies": ["Amazon", "Bloomberg", "Bank of America"],
    "topics": ["Greedy", "Dynamic Programming", "Hash Table"],
    "time_complexity": "O(D)",
    "space_complexity": "O(D)",
}


def REFERENCE(inventory, amount):
    if amount == 0:
        return {}
    out = {}
    remaining = amount
    for denom in sorted(inventory.keys(), reverse=True):
        if remaining == 0:
            break
        avail = inventory[denom]
        use = min(remaining // denom, avail)
        if use > 0:
            out[denom] = use
            remaining -= use * denom
    if remaining != 0:
        return {}
    return out


register(PAYLOAD, REFERENCE)
