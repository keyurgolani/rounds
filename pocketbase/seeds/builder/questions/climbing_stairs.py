"""Climbing Stairs — Easy. Dynamic Programming / Math.

The canonical 'Fibonacci in disguise' interview problem. Most candidates
write the recursive form first, then optimise to two scalars. The real
value of the question is the follow-up ladder: arbitrary step sizes
(1D unbounded knapsack), matrix exponentiation for huge n, and the
closed-form Binet derivation. Worth knowing all three even if you only
implement the O(1)-space iterative DP in the room.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Climbing Stairs",
    "difficulty": "Easy",
    "description": (
        "You are climbing a staircase. It takes `n` steps to reach the top.\n\n"
        "Each time you can either climb **1** or **2** steps. In how many distinct ways can you climb to "
        "the top?\n\n"
        "**Example 1:**\n"
        "- Input: `n = 2`\n"
        "- Output: `2`\n"
        "- Explanation: Two ways — `1 + 1`, `2`.\n\n"
        "**Example 2:**\n"
        "- Input: `n = 3`\n"
        "- Output: `3`\n"
        "- Explanation: Three ways — `1 + 1 + 1`, `1 + 2`, `2 + 1`.\n\n"
        "**Example 3:**\n"
        "- Input: `n = 5`\n"
        "- Output: `8`\n"
        "- Explanation: The count follows the Fibonacci sequence: 1, 2, 3, 5, 8, 13, ..."
    ),
    "hints": [
        "To reach step `n`, your last move was either a 1-step (from `n-1`) or a 2-step (from `n-2`). "
        "So `ways(n) = ways(n-1) + ways(n-2)`.",
        "That recurrence is exactly the Fibonacci sequence — shifted by one. `ways(1) = 1`, `ways(2) = 2`, "
        "`ways(3) = 3`, `ways(4) = 5`, ...",
        "Naive recursion is O(2ⁿ) — exponential due to repeated subproblems. Memoise to collapse to O(n).",
        "You only need the previous two values, never the whole table → bottom-up iteration with two scalars, "
        "O(1) space.",
        "For very large `n`, matrix exponentiation `[[1,1],[1,0]]^n` solves it in O(log n) multiplications.",
    ],
    "constraints": [
        "1 <= n <= 45",
    ],
    "starter_code": {
        "python": "def climb_stairs(n):\n    # Your code here\n    pass",
        "javascript": "function climbStairs(n) {\n    // Your code here\n}",
        "java": "public int climbStairs(int n) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for n in [1, 2, 3, 5, 10, 45]:\n"
            "        print(f\"climb_stairs({n}) = {climb_stairs(n)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[1, 2, 3, 5, 10, 45].forEach(n =>\n"
            "    console.log(`climbStairs(${n}) =`, climbStairs(n))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        for (int n : new int[]{1, 2, 3, 5, 10, 45}) {\n"
            "            System.out.println(\"climbStairs(\" + n + \") = \" + s.climbStairs(n));\n"
            "        }\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"n": 1}, "expected": 1,
         "description": "One step — only one way", "tags": ["edge"]},
        {"input": {"n": 2}, "expected": 2,
         "description": "Two ways — 1+1 or 2", "tags": ["basic"]},
        {"input": {"n": 3}, "expected": 3,
         "description": "Three ways — 1+1+1, 1+2, 2+1", "tags": ["basic"]},
        {"input": {"n": 4}, "expected": 5,
         "description": "Fibonacci continues — 5 distinct paths", "tags": ["basic"]},
        {"input": {"n": 5}, "expected": 8,
         "description": "8 distinct paths", "tags": ["basic"]},
        {"input": {"n": 10}, "expected": 89,
         "description": "Mid-range — 89 ways", "tags": ["tricky"]},
        {"input": {"n": 20}, "expected": 10946,
         "description": "Larger n — exponential growth visible", "tags": ["tricky"]},
        {"input": {"n": 45}, "expected": 1836311903,
         "description": "Upper bound — verifies the full Fibonacci ramp without int overflow", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Iterative DP, O(1) Space (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk from step 1 up to step n, carrying only the previous two values. `prev2` holds "
                "`ways(i-2)`, `prev1` holds `ways(i-1)`, and the next value is their sum. Two scalars, "
                "no array. This is the answer to write in the interview."
            ),
            "code": {
                "python": (
                    "def climb_stairs(n):\n"
                    "    if n <= 2:\n"
                    "        return n\n"
                    "    prev2, prev1 = 1, 2\n"
                    "    for _ in range(3, n + 1):\n"
                    "        prev2, prev1 = prev1, prev1 + prev2\n"
                    "    return prev1"
                ),
                "javascript": (
                    "function climbStairs(n) {\n"
                    "    if (n <= 2) return n;\n"
                    "    let prev2 = 1, prev1 = 2;\n"
                    "    for (let i = 3; i <= n; i++) {\n"
                    "        const curr = prev1 + prev2;\n"
                    "        prev2 = prev1;\n"
                    "        prev1 = curr;\n"
                    "    }\n"
                    "    return prev1;\n"
                    "}"
                ),
                "java": (
                    "public int climbStairs(int n) {\n"
                    "    if (n <= 2) return n;\n"
                    "    int prev2 = 1, prev1 = 2;\n"
                    "    for (int i = 3; i <= n; i++) {\n"
                    "        int curr = prev1 + prev2;\n"
                    "        prev2 = prev1;\n"
                    "        prev1 = curr;\n"
                    "    }\n"
                    "    return prev1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Top-Down Memoised Recursion",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Express the recurrence directly and cache results. Same asymptotic complexity as the "
                "iterative version but a larger constant (call-stack overhead, dict lookups) and O(n) "
                "auxiliary space. Useful as a stepping stone when explaining the derivation."
            ),
            "code": {
                "python": (
                    "from functools import lru_cache\n\n"
                    "def climb_stairs(n):\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def ways(i):\n"
                    "        if i <= 2:\n"
                    "            return i\n"
                    "        return ways(i - 1) + ways(i - 2)\n"
                    "    return ways(n)"
                ),
                "javascript": (
                    "function climbStairs(n) {\n"
                    "    const memo = new Map();\n"
                    "    const ways = (i) => {\n"
                    "        if (i <= 2) return i;\n"
                    "        if (memo.has(i)) return memo.get(i);\n"
                    "        const v = ways(i - 1) + ways(i - 2);\n"
                    "        memo.set(i, v);\n"
                    "        return v;\n"
                    "    };\n"
                    "    return ways(n);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Matrix Exponentiation (Sub-linear)",
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
            "description": (
                "The Fibonacci recurrence has the matrix form `[F(k+1), F(k)] = [[1,1],[1,0]] · [F(k), F(k-1)]`. "
                "Raising the 2×2 matrix to the n-th power via fast exponentiation gives the answer in "
                "O(log n) multiplications. Overkill for n ≤ 45, but the right answer when n is enormous."
            ),
            "code": {
                "python": (
                    "def climb_stairs(n):\n"
                    "    def mat_mul(a, b):\n"
                    "        return [\n"
                    "            [a[0][0]*b[0][0] + a[0][1]*b[1][0], a[0][0]*b[0][1] + a[0][1]*b[1][1]],\n"
                    "            [a[1][0]*b[0][0] + a[1][1]*b[1][0], a[1][0]*b[0][1] + a[1][1]*b[1][1]],\n"
                    "        ]\n\n"
                    "    def mat_pow(m, p):\n"
                    "        result = [[1, 0], [0, 1]]  # identity\n"
                    "        while p:\n"
                    "            if p & 1:\n"
                    "                result = mat_mul(result, m)\n"
                    "            m = mat_mul(m, m)\n"
                    "            p >>= 1\n"
                    "        return result\n\n"
                    "    # ways(n) corresponds to F(n+1) in standard indexing.\n"
                    "    return mat_pow([[1, 1], [1, 0]], n)[0][0]"
                ),
            },
        },
        {
            "title": "Closed-Form (Binet's Formula) — Mention Only",
            "time_complexity": "O(1)",
            "space_complexity": "O(1)",
            "description": (
                "Binet's formula: `F(n) = (φⁿ − ψⁿ) / √5`, where `φ = (1+√5)/2` and `ψ = (1−√5)/2`. "
                "Mathematically O(1), but in practice IEEE-754 floating-point loses precision around "
                "n ≈ 70 and gives wrong integers thereafter. Worth naming in the interview to show you "
                "know it; do **not** submit it."
            ),
            "code": {
                "python": (
                    "# Illustrative only — float precision breaks for large n.\n"
                    "import math\n\n"
                    "def climb_stairs(n):\n"
                    "    sqrt5 = math.sqrt(5)\n"
                    "    phi = (1 + sqrt5) / 2\n"
                    "    psi = (1 - sqrt5) / 2\n"
                    "    # ways(n) == F(n+1)\n"
                    "    return round((phi ** (n + 1) - psi ** (n + 1)) / sqrt5)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Read carefully: each move is 1 or 2 steps, count *distinct* sequences. Start with small cases by hand: "
        "n=1 → 1, n=2 → 2, n=3 → 3, n=4 → 5. The pattern is screaming Fibonacci.",
        "2. Define the subproblem: `ways(i)` = number of distinct sequences that land exactly on step `i`. "
        "We want `ways(n)`.",
        "3. Derive the recurrence: the last move into step `i` is either a 1-step (came from `i-1`) or a "
        "2-step (came from `i-2`), and these two sets are disjoint. So `ways(i) = ways(i-1) + ways(i-2)`.",
        "4. Establish base cases: `ways(1) = 1` (just '1'), `ways(2) = 2` ('1+1' or '2'). Everything else "
        "follows from the recurrence.",
        "5. Naive recursion is O(2ⁿ) — every call branches twice and subproblems repeat. Memoise (top-down) "
        "or build bottom-up to collapse to O(n) time.",
        "6. Optimise space: only the last two values are ever read, so drop the array and keep two scalars. "
        "Mention matrix exponentiation as the O(log n) variant for very large n, and Binet's formula as a "
        "theoretical O(1) (with a precision caveat).",
    ],
    "tips": [
        "Recognise this as Fibonacci shifted by one: `ways(n) = F(n+1)`. The instant you spot it, the "
        "recurrence and base cases write themselves.",
        "Generalisation — 'each turn you can take any of k step sizes from set S': becomes 1D unbounded "
        "knapsack, `ways(i) = Σ ways(i - s) for s in S`. Same DP, different inner loop, O(n·|S|).",
        "For very large `n` (e.g., 10⁹), use matrix exponentiation on `[[1,1],[1,0]]` to get O(log n). "
        "Mention it even if you don't implement it — interviewers love this follow-up.",
        "Don't compute `2**n` by accident: the answer is *not* 2ⁿ. That's the count of all 1/2 sequences "
        "of length ≤ n, including ones that overshoot or undershoot. The constraint is *landing exactly on n*.",
        "If asked about overflow: at n=45 the answer fits in a 32-bit signed int (1,836,311,903 < 2³¹−1). "
        "Beyond that you'd need 64-bit or big integers — Python is fine, Java/JS need `long`/BigInt.",
    ],
    "companies": ["Amazon", "Adobe", "Apple"],
    "topics": ["Dynamic Programming", "Math", "Memoization"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(n):
    if n <= 2:
        return n
    prev2, prev1 = 1, 2
    for _ in range(3, n + 1):
        prev2, prev1 = prev1, prev1 + prev2
    return prev1


register(PAYLOAD, REFERENCE)
