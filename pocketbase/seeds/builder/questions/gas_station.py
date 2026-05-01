"""Gas Station — Medium. Greedy / Array.

The classic 'one-pass greedy' problem. Brute force is n² — try every
starting index and simulate. The trick is the two-line insight: if the
total gas is less than the total cost, no answer exists; otherwise the
unique answer is the index right after the last point where the running
tank goes negative. One pass, two accumulators.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Gas Station",
    "difficulty": "Medium",
    "description": (
        "There are `n` gas stations along a circular route, where the amount of gas at the i-th station is "
        "`gas[i]`.\n\n"
        "You have a car with an unlimited gas tank and it costs `cost[i]` of gas to travel from the i-th "
        "station to its next `(i + 1)`-th station. You begin the journey with an empty tank at one of the "
        "gas stations.\n\n"
        "Given two integer arrays `gas` and `cost`, return *the starting gas station's index* if you can "
        "travel around the circuit once in the clockwise direction, otherwise return `-1`. If there exists "
        "a solution, it is **guaranteed to be unique**.\n\n"
        "**Example 1:**\n"
        "- Input: `gas = [1,2,3,4,5]`, `cost = [3,4,5,1,2]`\n"
        "- Output: `3`\n"
        "- Explanation: Start at station 3 (index 3). Tank: 0 + 4 = 4. Travel to station 4 (cost 1): tank = "
        "3. Tank: 3 + 5 = 8. Travel to station 0 (cost 2): tank = 6. Tank: 6 + 1 = 7. Travel to station 1 "
        "(cost 3): tank = 4. Tank: 4 + 2 = 6. Travel to station 2 (cost 4): tank = 2. Tank: 2 + 3 = 5. "
        "Travel to station 3 (cost 5): tank = 0. Circuit complete.\n\n"
        "**Example 2:**\n"
        "- Input: `gas = [2,3,4]`, `cost = [3,4,3]`\n"
        "- Output: `-1`\n"
        "- Explanation: You can't start at station 0 or 1, as there is not enough gas to travel to the next "
        "station. Starting at station 2: tank = 4. Travel to station 0 (cost 3): tank = 1. Tank: 1 + 2 = 3. "
        "Travel to station 1 (cost 3): tank = 0. Tank: 0 + 3 = 3. Travel to station 2 (cost 4): not enough "
        "gas. Therefore, you can't travel around the circuit once no matter where you start."
    ),
    "hints": [
        "Brute force: try every starting index and simulate the full circuit. O(n²) — fine to state, never the final answer.",
        "Sum check: if `sum(gas) < sum(cost)`, no solution can possibly exist — return -1 immediately. The converse is also true: if total gas >= total cost, a valid start *must* exist (problem guarantee).",
        "Greedy single pass: maintain a running `tank` of `gas[i] - cost[i]`. Whenever `tank` drops below zero, you can't have started anywhere in `[start..i]` — reset `start = i + 1` and `tank = 0`.",
        "Why the reset works: if you couldn't reach station i+1 starting from `start`, no station between `start` and `i` could either (each intermediate start had even less fuel at the failing edge).",
        "Combine both ideas: one loop tracks `total` (for the feasibility check) and `tank` + `start` (for the candidate). At the end, return `start` if `total >= 0`, else `-1`.",
    ],
    "constraints": [
        "n == gas.length == cost.length",
        "1 <= n <= 10⁵",
        "0 <= gas[i], cost[i] <= 10⁴",
    ],
    "starter_code": {
        "python": "def can_complete_circuit(gas, cost):\n    # Your code here\n    pass",
        "javascript": "function canCompleteCircuit(gas, cost) {\n    // Your code here\n}",
        "java": "public int canCompleteCircuit(int[] gas, int[] cost) {\n    // Your code here\n    return -1;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([1,2,3,4,5], [3,4,5,1,2]), ([2,3,4], [3,4,3])]\n"
            "    for gas, cost in cases:\n"
            "        print(f\"can_complete_circuit({gas}, {cost}) = {can_complete_circuit(gas, cost)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,2,3,4,5], [3,4,5,1,2]], [[2,3,4], [3,4,3]]].forEach(([gas, cost]) =>\n"
            "    console.log(`canCompleteCircuit =`, canCompleteCircuit(gas, cost))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.canCompleteCircuit(new int[]{1,2,3,4,5}, new int[]{3,4,5,1,2}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"gas": [1, 2, 3, 4, 5], "cost": [3, 4, 5, 1, 2]}, "expected": 3,
         "description": "Classic LC example — start at index 3", "tags": ["basic"]},
        {"input": {"gas": [2, 3, 4], "cost": [3, 4, 3]}, "expected": -1,
         "description": "Total gas (9) < total cost (10) — impossible", "tags": ["basic"]},
        {"input": {"gas": [5, 1, 2, 3, 4], "cost": [4, 4, 1, 5, 1]}, "expected": 4,
         "description": "Start at the last index — wraps around immediately", "tags": ["tricky"]},
        {"input": {"gas": [3, 1, 1], "cost": [1, 2, 2]}, "expected": 0,
         "description": "Start at index 0 — first station has the surplus", "tags": ["basic"]},
        {"input": {"gas": [4, 5, 2, 6, 5, 3], "cost": [3, 2, 7, 3, 2, 9]}, "expected": -1,
         "description": "Total gas (25) < total cost (26) — fails by one", "tags": ["edge"]},
        {"input": {"gas": [5], "cost": [4]}, "expected": 0,
         "description": "Single station — surplus, trivially completes", "tags": ["edge"]},
        {"input": {"gas": [3], "cost": [4]}, "expected": -1,
         "description": "Single station — deficit, impossible", "tags": ["edge"]},
        {"input": {"gas": [2, 2, 2, 2], "cost": [2, 2, 2, 2]}, "expected": 0,
         "description": "Equal gas and cost everywhere — any start works, greedy picks 0", "tags": ["edge"]},
        {"input": {"gas": [1, 2, 3, 4, 5, 5, 70], "cost": [2, 3, 4, 3, 9, 6, 2]}, "expected": 6,
         "description": "Big surplus at the last station — must start there", "tags": ["tricky"]},
        {"input": {"gas": [6, 1, 4, 3, 5], "cost": [3, 8, 2, 4, 2]}, "expected": 2,
         "description": "Cycle wraps through index 0 from the middle start", "tags": ["tricky"]},
        {"input": {"gas": [0] * 9999 + [10000], "cost": [1] * 9999 + [1]}, "expected": 9999,
         "description": "10K stations — single fuel-up at the end carries the whole circuit", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "One-Pass Greedy (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk the array once tracking two sums: `total` (overall surplus, decides feasibility) and "
                "`tank` (running surplus from the current candidate start). Whenever `tank` goes negative, "
                "the current start (and every index in between) is invalid — reset `start = i + 1` and "
                "`tank = 0`. At the end, if `total >= 0` the answer is `start`; otherwise -1."
            ),
            "code": {
                "python": (
                    "def can_complete_circuit(gas, cost):\n"
                    "    total = tank = start = 0\n"
                    "    for i in range(len(gas)):\n"
                    "        diff = gas[i] - cost[i]\n"
                    "        total += diff\n"
                    "        tank += diff\n"
                    "        if tank < 0:\n"
                    "            start = i + 1\n"
                    "            tank = 0\n"
                    "    return start if total >= 0 else -1"
                ),
                "javascript": (
                    "function canCompleteCircuit(gas, cost) {\n"
                    "    let total = 0, tank = 0, start = 0;\n"
                    "    for (let i = 0; i < gas.length; i++) {\n"
                    "        const diff = gas[i] - cost[i];\n"
                    "        total += diff;\n"
                    "        tank += diff;\n"
                    "        if (tank < 0) {\n"
                    "            start = i + 1;\n"
                    "            tank = 0;\n"
                    "        }\n"
                    "    }\n"
                    "    return total >= 0 ? start : -1;\n"
                    "}"
                ),
                "java": (
                    "public int canCompleteCircuit(int[] gas, int[] cost) {\n"
                    "    int total = 0, tank = 0, start = 0;\n"
                    "    for (int i = 0; i < gas.length; i++) {\n"
                    "        int diff = gas[i] - cost[i];\n"
                    "        total += diff;\n"
                    "        tank += diff;\n"
                    "        if (tank < 0) {\n"
                    "            start = i + 1;\n"
                    "            tank = 0;\n"
                    "        }\n"
                    "    }\n"
                    "    return total >= 0 ? start : -1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force — Try Each Start",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "For each candidate start index, simulate the full circuit and check whether the tank ever "
                "goes negative. Return the first index that makes it. State this as the baseline; never "
                "submit for n up to 10⁵."
            ),
            "code": {
                "python": (
                    "def can_complete_circuit(gas, cost):\n"
                    "    n = len(gas)\n"
                    "    for start in range(n):\n"
                    "        tank = 0\n"
                    "        ok = True\n"
                    "        for k in range(n):\n"
                    "            i = (start + k) % n\n"
                    "            tank += gas[i] - cost[i]\n"
                    "            if tank < 0:\n"
                    "                ok = False\n"
                    "                break\n"
                    "        if ok:\n"
                    "            return start\n"
                    "    return -1"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force: simulate from every starting index. O(n²). State it as the baseline.",
        "2. Feasibility shortcut: if `sum(gas) < sum(cost)`, no full circuit is possible. Return -1.",
        "3. Conversely (problem guarantee): if `sum(gas) >= sum(cost)`, exactly one valid start exists.",
        "4. Greedy reset insight: if you start at `s` and run out of fuel reaching index `i+1`, then *no* index in `[s..i]` could have worked either — each later start would have had even less fuel at the failing edge.",
        "5. Therefore one pass suffices: walk left-to-right; whenever the running tank dips below zero, jump the candidate start to `i + 1` and reset the tank. At the end, the surviving `start` is the unique answer (assuming the totals check out).",
        "6. Edge cases: single station (compare gas[0] vs cost[0]), all-equal (any start works → start 0), giant surplus at the last index (must start there).",
    ],
    "tips": [
        "Two accumulators, one loop. Don't conflate `total` (global feasibility) with `tank` (local candidate). They diverge whenever you reset.",
        "The reset-to-`i+1` step is the heart of the algorithm. If you only remember one thing, remember *why* it's correct: every intermediate start has less fuel at the failing edge.",
        "You don't need a separate feasibility pre-pass. Tracking `total` inside the same loop saves one walk and is cleaner to write.",
        "If asked 'what if there could be multiple valid starts?' — the greedy still returns the smallest one that completes from-the-left; you'd need a different algorithm to enumerate all.",
        "Watch the off-by-one: when `tank < 0` at index i, the new start is `i + 1`, not `i`. Drawing one example on the whiteboard cements this.",
        "Beware integer overflow in Java for adversarial inputs — sums up to 10⁵ * 10⁴ = 10⁹ fit in `int` but only just; production code might use `long`.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Bloomberg", "Apple"],
    "topics": ["Array", "Greedy"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(gas, cost):
    total = tank = start = 0
    for i in range(len(gas)):
        diff = gas[i] - cost[i]
        total += diff
        tank += diff
        if tank < 0:
            start = i + 1
            tank = 0
    return start if total >= 0 else -1


register(PAYLOAD, REFERENCE)
