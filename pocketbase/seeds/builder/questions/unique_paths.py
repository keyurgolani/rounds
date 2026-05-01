"""Unique Paths — Medium. DP / Combinatorics.

The canonical 'count lattice paths in a grid' question. Two completely
different solutions land at the same answer: bottom-up DP (the textbook
recurrence `dp[i][j] = dp[i-1][j] + dp[i][j-1]`) and the closed-form
binomial coefficient `C(m+n-2, m-1)`. Knowing both signals comfort
moving between algorithmic and mathematical framings — and the
combinatorial trick saves you from recomputing big DP tables.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Unique Paths",
    "difficulty": "Medium",
    "description": (
        "There is a robot on an `m x n` grid. The robot is initially located at the **top-left corner** "
        "(i.e., `grid[0][0]`). The robot tries to move to the **bottom-right corner** "
        "(i.e., `grid[m-1][n-1]`). The robot can only move either **down** or **right** at any point in time.\n\n"
        "Given the two integers `m` and `n`, return *the number of possible unique paths that the robot "
        "can take to reach the bottom-right corner*.\n\n"
        "**Example 1:**\n"
        "- Input: `m = 3, n = 7`\n"
        "- Output: `28`\n\n"
        "**Example 2:**\n"
        "- Input: `m = 3, n = 2`\n"
        "- Output: `3`\n"
        "- Explanation: From the top-left corner, there are a total of 3 ways to reach the bottom-right "
        "corner: 1) Right -> Down -> Down  2) Down -> Down -> Right  3) Down -> Right -> Down"
    ),
    "hints": [
        "Brute-force recursion: `paths(i, j) = paths(i-1, j) + paths(i, j-1)`. Exponential without memoisation — state it, then memoise.",
        "Bottom-up DP: fill an `m × n` table where `dp[i][j]` = ways to reach cell `(i, j)`. The first row and first column are all 1 (only one way: keep going right / keep going down).",
        "You only need the previous row to compute the current row → drop to a 1D rolling array of size `min(m, n)`.",
        "Closed form: every path makes exactly `m-1` down moves and `n-1` right moves in some order. The count is `C(m+n-2, m-1)` — pick which of the total `m+n-2` steps are 'down'.",
        "For the closed form, iterate to keep the running product an integer: `result *= (n - 1 + i); result //= i` for `i = 1..m-1`. Avoids large factorials.",
    ],
    "constraints": [
        "1 <= m, n <= 100",
        "The answer is guaranteed to be less than or equal to 2 * 10⁹.",
    ],
    "starter_code": {
        "python": "def unique_paths(m, n):\n    # Your code here\n    pass",
        "javascript": "function uniquePaths(m, n) {\n    // Your code here\n}",
        "java": "public int uniquePaths(int m, int n) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(3, 7), (3, 2), (1, 1), (7, 3)]\n"
            "    for m, n in cases:\n"
            "        print(f\"unique_paths({m}, {n}) = {unique_paths(m, n)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[3,7], [3,2], [1,1], [7,3]].forEach(([m,n]) =>\n"
            "    console.log(`uniquePaths(${m}, ${n}) =`, uniquePaths(m, n))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.uniquePaths(3, 7));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"m": 3, "n": 7}, "expected": 28,
         "description": "Classic 3x7 grid", "tags": ["basic"]},
        {"input": {"m": 3, "n": 2}, "expected": 3,
         "description": "Small 3x2 — three orderings of D, D, R", "tags": ["basic"]},
        {"input": {"m": 1, "n": 1}, "expected": 1,
         "description": "Degenerate 1x1 — already at the destination", "tags": ["edge"]},
        {"input": {"m": 1, "n": 5}, "expected": 1,
         "description": "Single row — only one path (all right)", "tags": ["edge"]},
        {"input": {"m": 5, "n": 1}, "expected": 1,
         "description": "Single column — only one path (all down)", "tags": ["edge"]},
        {"input": {"m": 7, "n": 3}, "expected": 28,
         "description": "Symmetry — swapping m and n yields the same count", "tags": ["tricky"]},
        {"input": {"m": 10, "n": 10}, "expected": 48620,
         "description": "10x10 — central binomial coefficient C(18, 9)", "tags": ["large"]},
        {"input": {"m": 23, "n": 12}, "expected": 193536720,
         "description": "Near upper bound — exercises big-integer / overflow edges", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Combinatorial Closed-Form (Optimal)",
            "time_complexity": "O(min(m, n))",
            "space_complexity": "O(1)",
            "description": (
                "Every path is a sequence of exactly `m-1` down moves and `n-1` right moves. The total number "
                "of such sequences is the binomial coefficient `C(m+n-2, m-1)`. Compute it with a running "
                "product to keep all intermediate values integral and avoid overflow on large factorials."
            ),
            "code": {
                "python": (
                    "from math import comb\n"
                    "\n"
                    "def unique_paths(m, n):\n"
                    "    return comb(m + n - 2, m - 1)"
                ),
                "javascript": (
                    "function uniquePaths(m, n) {\n"
                    "    // Iterate over the smaller dimension for fewer steps.\n"
                    "    if (m > n) [m, n] = [n, m];\n"
                    "    let result = 1;\n"
                    "    for (let i = 1; i < m; i++) {\n"
                    "        result = result * (n - 1 + i) / i;\n"
                    "    }\n"
                    "    return Math.round(result);\n"
                    "}"
                ),
                "java": (
                    "public int uniquePaths(int m, int n) {\n"
                    "    if (m > n) { int t = m; m = n; n = t; }\n"
                    "    long result = 1;\n"
                    "    for (int i = 1; i < m; i++) {\n"
                    "        result = result * (n - 1 + i) / i;\n"
                    "    }\n"
                    "    return (int) result;\n"
                    "}"
                ),
            },
        },
        {
            "title": "1D Rolling DP",
            "time_complexity": "O(m * n)",
            "space_complexity": "O(min(m, n))",
            "description": (
                "Each cell only depends on the cell directly above and the cell directly to the left. Keep a "
                "single row of size `min(m, n)` and update it in place: `dp[j] += dp[j-1]`. After `m-1` "
                "passes (one per row beyond the first), `dp[-1]` holds the answer."
            ),
            "code": {
                "python": (
                    "def unique_paths(m, n):\n"
                    "    if m > n:\n"
                    "        m, n = n, m  # iterate fewer rows over a longer 1D array\n"
                    "    dp = [1] * n\n"
                    "    for _ in range(m - 1):\n"
                    "        for j in range(1, n):\n"
                    "            dp[j] += dp[j - 1]\n"
                    "    return dp[-1]"
                ),
            },
        },
        {
            "title": "2D Bottom-Up DP",
            "time_complexity": "O(m * n)",
            "space_complexity": "O(m * n)",
            "description": (
                "Allocate an `m x n` table. The first row and first column are all 1 (one way to reach any "
                "edge cell). For interior cells, `dp[i][j] = dp[i-1][j] + dp[i][j-1]`. Return `dp[m-1][n-1]`. "
                "The most readable solution; mention this before optimising the space."
            ),
            "code": {
                "python": (
                    "def unique_paths(m, n):\n"
                    "    dp = [[1] * n for _ in range(m)]\n"
                    "    for i in range(1, m):\n"
                    "        for j in range(1, n):\n"
                    "            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]\n"
                    "    return dp[m - 1][n - 1]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the move structure: from `(i, j)` you can only have arrived from `(i-1, j)` or `(i, j-1)`. That is the recurrence.",
        "2. Naïve recursion `paths(i, j) = paths(i-1, j) + paths(i, j-1)` is exponential — same subproblems revisited along every diagonal. Memoise or go bottom-up.",
        "3. Bottom-up 2D DP: first row and first column are all 1; interior cells sum the cell above and the cell to the left. O(m·n) time, O(m·n) space.",
        "4. Optimise space: each cell only needs the previous row, so collapse to a 1D rolling array of length `min(m, n)`. O(m·n) time, O(min(m, n)) space.",
        "5. Reframe combinatorially: every path is exactly `m-1` downs and `n-1` rights in some order → answer is `C(m+n-2, m-1)`. O(min(m, n)) time, O(1) space.",
        "6. Edge cases: `m == 1` or `n == 1` → exactly one path. Symmetry: swapping `m` and `n` doesn't change the count (binomial symmetry).",
    ],
    "tips": [
        "If the interviewer pushes for the 'best you can do', go straight to the binomial. State `C(m+n-2, m-1)` and explain why.",
        "When computing `C(a, b)` by hand, iterate `b` from `1..k` with `result = result * (a - k + i) / i` to keep every intermediate value an integer.",
        "Beware floating-point: in JavaScript / Java, the closed form needs careful integer division order or `long` to avoid precision loss.",
        "Common follow-up — Unique Paths II (LC 63): same grid, but some cells are obstacles. Same DP, just zero-out blocked cells.",
        "Common follow-up — Minimum Path Sum (LC 64): each cell has a weight; minimise the path sum instead of counting. Same recurrence shape, `min` instead of `+`.",
    ],
    "companies": ["Amazon", "Bloomberg", "Mathworks"],
    "topics": ["Math", "Dynamic Programming", "Combinatorics"],
    "time_complexity": "O(min(m, n))",
    "space_complexity": "O(1)",
}


def REFERENCE(m, n):
    from math import comb
    return comb(m + n - 2, m - 1)


register(PAYLOAD, REFERENCE)
