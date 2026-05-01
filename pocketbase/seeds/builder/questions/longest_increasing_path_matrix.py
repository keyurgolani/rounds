"""Longest Increasing Path in a Matrix — Hard. DFS + Memoization / Topo Sort.

A grid problem that is secretly a DAG problem. Strict increase guarantees
acyclicity, so you don't need a `visited` set — just memoize. The textbook
DFS-with-memo answer is O(m·n). The topological-sort BFS variant is the
'longest path in a DAG' interview classic and worth knowing because
follow-ups (cycles allowed, weighted edges) bend toward it.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Longest Increasing Path in a Matrix",
    "difficulty": "Hard",
    "description": (
        "Given an `m x n` integers `matrix`, return the length of the **longest strictly increasing path** "
        "in `matrix`.\n\n"
        "From each cell, you can move in four directions: left, right, up, or down. You **may not** move "
        "diagonally or move outside the boundary (i.e., wrap-around is not allowed).\n\n"
        "**Example 1:**\n"
        "- Input: `matrix = [[9,9,4],[6,6,8],[2,1,1]]`\n"
        "- Output: `4`\n"
        "- Explanation: The longest increasing path is `[1, 2, 6, 9]`.\n"
        "  ```\n"
        "  9 9 4\n"
        "  6 6 8\n"
        "  2 1 1\n"
        "  ```\n"
        "  Start at the `1` in the bottom row, go up to `2`, up to `6`, up to `9`. Length = 4.\n\n"
        "**Example 2:**\n"
        "- Input: `matrix = [[3,4,5],[3,2,6],[2,2,1]]`\n"
        "- Output: `4`\n"
        "- Explanation: The longest increasing path is `[3, 4, 5, 6]`.\n"
        "  ```\n"
        "  3 4 5\n"
        "  3 2 6\n"
        "  2 2 1\n"
        "  ```\n"
        "  Diagonal moves are not allowed — `3 → 4 → 5 → 6` walks across the top row then drops to (1,2)."
    ),
    "hints": [
        "Brute-force DFS from every cell explores all paths exponentially. The key insight: from a given "
        "cell, the longest increasing path *starting there* depends only on the cell — not on how you got "
        "there. So memoize it.",
        "Strictly increasing means the implicit graph (cell → larger neighbor) is a **DAG**. No cycles are "
        "possible. You don't need a `visited` set in your DFS — the strictness already prevents revisits.",
        "DFS + memo: `dp[r][c] = 1 + max(dp[nr][nc] for each neighbor with matrix[nr][nc] > matrix[r][c])`. "
        "Default `1` (the cell itself). Answer is `max(dp)` over all cells. Time and space O(m·n).",
        "Alternative — topological sort: treat each cell as a node, edges go from smaller to larger. "
        "Compute in-degree (# smaller neighbors) and BFS from in-degree-0 cells (local minima). The number "
        "of BFS layers is the answer. This is the 'longest path in a DAG' template.",
        "Both approaches are O(m·n) time and space. DFS+memo is shorter to write; topo-sort uses no "
        "recursion (no stack-overflow risk on huge grids) and generalises to weighted DAG longest-path.",
    ],
    "constraints": [
        "m == matrix.length",
        "n == matrix[i].length",
        "1 <= m, n <= 200",
        "0 <= matrix[i][j] <= 2³¹ - 1",
    ],
    "starter_code": {
        "python": (
            "def longest_increasing_path(matrix):\n"
            "    # Your code here\n"
            "    pass"
        ),
        "javascript": (
            "function longestIncreasingPath(matrix) {\n"
            "    // Your code here\n"
            "}"
        ),
        "java": (
            "public int longestIncreasingPath(int[][] matrix) {\n"
            "    // Your code here\n"
            "    return 0;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[9,9,4],[6,6,8],[2,1,1]],\n"
            "        [[3,4,5],[3,2,6],[2,2,1]],\n"
            "        [[1]],\n"
            "    ]\n"
            "    for m in cases:\n"
            "        print(f\"longest_increasing_path({m}) = {longest_increasing_path(m)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\n"
            "    [[9,9,4],[6,6,8],[2,1,1]],\n"
            "    [[3,4,5],[3,2,6],[2,2,1]],\n"
            "].forEach(m =>\n"
            "    console.log(`longestIncreasingPath =`, longestIncreasingPath(m))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] m = {{9,9,4},{6,6,8},{2,1,1}};\n"
            "        System.out.println(s.longestIncreasingPath(m));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"matrix": [[9, 9, 4], [6, 6, 8], [2, 1, 1]]}, "expected": 4,
         "description": "Classic LC example — path 1 → 2 → 6 → 9", "tags": ["basic"]},
        {"input": {"matrix": [[3, 4, 5], [3, 2, 6], [2, 2, 1]]}, "expected": 4,
         "description": "Second LC example — path 3 → 4 → 5 → 6 (no diagonals)", "tags": ["basic"]},
        {"input": {"matrix": [[1]]}, "expected": 1,
         "description": "Single cell — trivial path of length 1", "tags": ["edge"]},
        {"input": {"matrix": [[7, 7, 7], [7, 7, 7], [7, 7, 7]]}, "expected": 1,
         "description": "All-equal — strict increase forbids any move; length 1", "tags": ["edge"]},
        {"input": {"matrix": [[1, 2, 3, 4, 5]]}, "expected": 5,
         "description": "Single ascending row — full row is the path", "tags": ["basic"]},
        {"input": {"matrix": [[1], [2], [3], [4], [5]]}, "expected": 5,
         "description": "Single ascending column — full column is the path", "tags": ["basic"]},
        {"input": {"matrix": [
            [1, 2, 3, 4],
            [12, 13, 14, 5],
            [11, 16, 15, 6],
            [10, 9, 8, 7],
        ]}, "expected": 16,
         "description": "Spiral pattern — entire grid is one increasing path of length 16",
         "tags": ["tricky"]},
        {"input": {"matrix": [[5, 4, 3], [4, 3, 2], [3, 2, 1]]}, "expected": 5,
         "description": "Decreasing toward bottom-right — path 1 → 2 → 3 → 4 → 5", "tags": ["tricky"]},
        {"input": {"matrix": [[1, 2], [4, 3]]}, "expected": 4,
         "description": "2x2 — path 1 → 2 → 3 → 4 walks around the cells", "tags": ["basic"]},
        {"input": {"matrix": [[0]]}, "expected": 1,
         "description": "1x1 with zero — length 1", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "DFS + Memoization (Optimal)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "From each cell, recursively compute the longest increasing path starting there. "
                "Cache the result so each cell is solved once. Strict increase rules out cycles, so no "
                "`visited` set is needed. Answer is the max over all cells."
            ),
            "code": {
                "python": (
                    "def longest_increasing_path(matrix):\n"
                    "    if not matrix or not matrix[0]:\n"
                    "        return 0\n"
                    "    m, n = len(matrix), len(matrix[0])\n"
                    "    memo = [[0] * n for _ in range(m)]\n"
                    "    DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))\n"
                    "\n"
                    "    def dfs(r, c):\n"
                    "        if memo[r][c]:\n"
                    "            return memo[r][c]\n"
                    "        best = 1\n"
                    "        for dr, dc in DIRS:\n"
                    "            nr, nc = r + dr, c + dc\n"
                    "            if 0 <= nr < m and 0 <= nc < n and matrix[nr][nc] > matrix[r][c]:\n"
                    "                best = max(best, 1 + dfs(nr, nc))\n"
                    "        memo[r][c] = best\n"
                    "        return best\n"
                    "\n"
                    "    return max(dfs(r, c) for r in range(m) for c in range(n))"
                ),
                "javascript": (
                    "function longestIncreasingPath(matrix) {\n"
                    "    if (!matrix.length || !matrix[0].length) return 0;\n"
                    "    const m = matrix.length, n = matrix[0].length;\n"
                    "    const memo = Array.from({length: m}, () => new Array(n).fill(0));\n"
                    "    const DIRS = [[1,0],[-1,0],[0,1],[0,-1]];\n"
                    "    const dfs = (r, c) => {\n"
                    "        if (memo[r][c]) return memo[r][c];\n"
                    "        let best = 1;\n"
                    "        for (const [dr, dc] of DIRS) {\n"
                    "            const nr = r + dr, nc = c + dc;\n"
                    "            if (nr >= 0 && nr < m && nc >= 0 && nc < n && matrix[nr][nc] > matrix[r][c]) {\n"
                    "                best = Math.max(best, 1 + dfs(nr, nc));\n"
                    "            }\n"
                    "        }\n"
                    "        memo[r][c] = best;\n"
                    "        return best;\n"
                    "    };\n"
                    "    let ans = 0;\n"
                    "    for (let r = 0; r < m; r++)\n"
                    "        for (let c = 0; c < n; c++)\n"
                    "            ans = Math.max(ans, dfs(r, c));\n"
                    "    return ans;\n"
                    "}"
                ),
                "java": (
                    "public int longestIncreasingPath(int[][] matrix) {\n"
                    "    if (matrix.length == 0 || matrix[0].length == 0) return 0;\n"
                    "    int m = matrix.length, n = matrix[0].length;\n"
                    "    int[][] memo = new int[m][n];\n"
                    "    int ans = 0;\n"
                    "    for (int r = 0; r < m; r++)\n"
                    "        for (int c = 0; c < n; c++)\n"
                    "            ans = Math.max(ans, dfs(matrix, r, c, memo));\n"
                    "    return ans;\n"
                    "}\n"
                    "\n"
                    "private static final int[][] DIRS = {{1,0},{-1,0},{0,1},{0,-1}};\n"
                    "\n"
                    "private int dfs(int[][] mat, int r, int c, int[][] memo) {\n"
                    "    if (memo[r][c] != 0) return memo[r][c];\n"
                    "    int best = 1;\n"
                    "    for (int[] d : DIRS) {\n"
                    "        int nr = r + d[0], nc = c + d[1];\n"
                    "        if (nr >= 0 && nr < mat.length && nc >= 0 && nc < mat[0].length\n"
                    "                && mat[nr][nc] > mat[r][c]) {\n"
                    "            best = Math.max(best, 1 + dfs(mat, nr, nc, memo));\n"
                    "        }\n"
                    "    }\n"
                    "    memo[r][c] = best;\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Topological Sort (BFS / Kahn's)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Build the implicit DAG: each cell has an incoming edge from each *smaller* neighbor. "
                "Compute in-degree per cell and seed a BFS queue with all in-degree-0 cells (local minima). "
                "Each BFS layer peels off one level; the number of layers equals the longest path length. "
                "No recursion — useful when the grid is large enough to risk stack overflow."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "def longest_increasing_path(matrix):\n"
                    "    if not matrix or not matrix[0]:\n"
                    "        return 0\n"
                    "    m, n = len(matrix), len(matrix[0])\n"
                    "    DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))\n"
                    "    indeg = [[0] * n for _ in range(m)]\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            for dr, dc in DIRS:\n"
                    "                nr, nc = r + dr, c + dc\n"
                    "                if 0 <= nr < m and 0 <= nc < n and matrix[nr][nc] < matrix[r][c]:\n"
                    "                    indeg[r][c] += 1\n"
                    "    q = deque((r, c) for r in range(m) for c in range(n) if indeg[r][c] == 0)\n"
                    "    layers = 0\n"
                    "    while q:\n"
                    "        layers += 1\n"
                    "        for _ in range(len(q)):\n"
                    "            r, c = q.popleft()\n"
                    "            for dr, dc in DIRS:\n"
                    "                nr, nc = r + dr, c + dc\n"
                    "                if 0 <= nr < m and 0 <= nc < n and matrix[nr][nc] > matrix[r][c]:\n"
                    "                    indeg[nr][nc] -= 1\n"
                    "                    if indeg[nr][nc] == 0:\n"
                    "                        q.append((nr, nc))\n"
                    "    return layers"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the brute-force DFS from every cell is exponential. The fix is memoization — but only "
        "if the subproblem is well-defined.",
        "2. Subproblem: `longest_path_starting_at(r, c)`. This depends only on `(r, c)` and the matrix, not "
        "on path history. Therefore memoizable.",
        "3. Strict increase ⇒ DAG. No cycles ⇒ no `visited` set. This is the trick — candidates often add a "
        "redundant `visited` and confuse themselves.",
        "4. Recurrence: `dp[r][c] = 1 + max(dp[nr][nc])` over neighbors with strictly greater value. Default "
        "1 (the cell alone). Answer: `max(dp)` over all cells.",
        "5. Complexity: each cell is solved once, O(1) work per cell (4 neighbors). Total O(m·n) time and "
        "O(m·n) space for the memo table and recursion stack.",
        "6. Alternative framing — topological sort: longest path in a DAG. Compute in-degree, BFS from "
        "in-degree-0 cells, count layers. Same O(m·n), no recursion.",
        "7. Edge cases: 1x1 (return 1), all-equal grid (return 1 — strict increase blocks all moves), "
        "single ascending row/column (return length).",
    ],
    "tips": [
        "Don't add a `visited` set. Strict increase already guarantees acyclicity. Adding `visited` is "
        "wrong (it makes the answer order-dependent) and signals to the interviewer you didn't see why.",
        "The memo table doubles as the answer aggregator — the final answer is `max(memo[r][c])` once "
        "every cell has been DFS'd. No need for a separate global.",
        "If you're worried about Python's recursion limit on a 200×200 grid (worst case 40000-deep "
        "recursion), bump `sys.setrecursionlimit` or switch to the topological-sort BFS variant.",
        "Common follow-up: 'allow equal values' — now it's no longer a DAG; you need Tarjan SCC or "
        "explicit `visited` because cycles are possible.",
        "Common follow-up: 'return the path itself, not just the length' — store the parent pointer "
        "alongside the DP value, then reconstruct from the argmax cell.",
        "Common follow-up: 'count the number of longest increasing paths' — second DP table tracking "
        "the count, updated alongside the length.",
    ],
    "companies": ["Google", "Amazon", "Facebook", "Microsoft", "Apple", "Bloomberg"],
    "topics": ["Dynamic Programming", "Depth-First Search", "Breadth-First Search", "Graph",
               "Topological Sort", "Memoization", "Matrix"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(m·n)",
}


def REFERENCE(matrix):
    if not matrix or not matrix[0]:
        return 0
    m, n = len(matrix), len(matrix[0])
    memo = [[0] * n for _ in range(m)]
    DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))

    def dfs(r, c):
        if memo[r][c]:
            return memo[r][c]
        best = 1
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < m and 0 <= nc < n and matrix[nr][nc] > matrix[r][c]:
                v = 1 + dfs(nr, nc)
                if v > best:
                    best = v
        memo[r][c] = best
        return best

    return max(dfs(r, c) for r in range(m) for c in range(n))


register(PAYLOAD, REFERENCE)
