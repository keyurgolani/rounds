"""Weighted Matrix Minimum Cost Path — Medium. DP / Dijkstra.

Find the minimum cost path through a weighted matrix from (0,0) to
(m-1,n-1). DP works if movement is restricted to right/down; Dijkstra
generalises to four-direction movement with non-negative weights."""
from builder.registry import register


PAYLOAD = {
    "title": "Weighted Matrix Minimum Cost Path",
    "difficulty": "Medium",
    "description": (
        "Given an `m × n` matrix of non-negative integer weights, find the minimum cost from `(0, 0)` to "
        "`(m-1, n-1)`. You may move only **right** or **down** at each step. The cost of a path is the "
        "sum of all cells visited (including start and end).\n\n"
        "**Example:**\n"
        "- Input: `grid = [[1, 3, 1], [1, 5, 1], [4, 2, 1]]`\n"
        "- Output: `7` (path: 1 → 3 → 1 → 1 → 1 → 1)"
    ),
    "hints": [
        "DP: `dp[i][j] = grid[i][j] + min(dp[i-1][j], dp[i][j-1])`. First row/column have only one predecessor.",
        "Space-optimised DP: only the previous row matters → O(n) extra space.",
        "If movement were 4-directional with non-negative weights, switch to Dijkstra (O((m·n) log(m·n))).",
        "If weights could be negative, Bellman-Ford or skip the problem (negative cycles cause unbounded paths).",
        "Edge cases: 1x1 grid (return grid[0][0]), single row, single column, larger weights.",
    ],
    "constraints": [
        "1 <= m, n <= 10²",
        "0 <= grid[i][j] <= 10⁵",
    ],
    "starter_code": {
        "python": "def min_path_cost(grid):\n    # Your code here\n    pass",
        "javascript": "function minPathCost(grid) {\n    // Your code here\n}",
        "java": "public int minPathCost(int[][] grid) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(min_path_cost([[1,3,1],[1,5,1],[4,2,1]]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"grid": [[1, 3, 1], [1, 5, 1], [4, 2, 1]]}, "expected": 7,
         "description": "Standard 3x3", "tags": ["basic"]},
        {"input": {"grid": [[42]]}, "expected": 42,
         "description": "1x1 — just the cell", "tags": ["edge"]},
        {"input": {"grid": [[1, 2, 3]]}, "expected": 6,
         "description": "Single row — sum every cell", "tags": ["edge"]},
        {"input": {"grid": [[1], [2], [3]]}, "expected": 6,
         "description": "Single column — sum every cell", "tags": ["edge"]},
        {"input": {"grid": [[0, 0], [0, 0]]}, "expected": 0,
         "description": "All zeros", "tags": ["edge"]},
        {"input": {"grid": [[5, 4, 2, 1], [1, 7, 9, 3], [4, 1, 8, 5]]},
         "expected": 20,
         "description": "Multi-step optimal — verify against DP table", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Bottom-Up DP (Optimal)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n) (or O(n) optimised)",
            "description": (
                "Fill `dp[i][j]` = `grid[i][j] + min(dp[i-1][j], dp[i][j-1])`. First row and column have "
                "only one predecessor. Answer is `dp[m-1][n-1]`. Easy to implement, easy to extend to "
                "constrained variants (forbidden cells, max steps)."
            ),
            "code": {
                "python": (
                    "def min_path_cost(grid):\n"
                    "    m, n = len(grid), len(grid[0])\n"
                    "    dp = [[0] * n for _ in range(m)]\n"
                    "    dp[0][0] = grid[0][0]\n"
                    "    for j in range(1, n):\n"
                    "        dp[0][j] = dp[0][j - 1] + grid[0][j]\n"
                    "    for i in range(1, m):\n"
                    "        dp[i][0] = dp[i - 1][0] + grid[i][0]\n"
                    "    for i in range(1, m):\n"
                    "        for j in range(1, n):\n"
                    "            dp[i][j] = grid[i][j] + min(dp[i - 1][j], dp[i][j - 1])\n"
                    "    return dp[m - 1][n - 1]"
                ),
                "javascript": (
                    "function minPathCost(grid) {\n"
                    "    const m = grid.length, n = grid[0].length;\n"
                    "    const dp = Array.from({length: m}, () => new Array(n).fill(0));\n"
                    "    dp[0][0] = grid[0][0];\n"
                    "    for (let j = 1; j < n; j++) dp[0][j] = dp[0][j-1] + grid[0][j];\n"
                    "    for (let i = 1; i < m; i++) dp[i][0] = dp[i-1][0] + grid[i][0];\n"
                    "    for (let i = 1; i < m; i++)\n"
                    "        for (let j = 1; j < n; j++)\n"
                    "            dp[i][j] = grid[i][j] + Math.min(dp[i-1][j], dp[i][j-1]);\n"
                    "    return dp[m-1][n-1];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Space-Optimised DP",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(n)",
            "description": (
                "Only the previous row matters at any moment. Roll the DP table to a single row of length "
                "n. Updates in place: `row[j] = grid[i][j] + min(row[j], row[j-1])` (the unmutated `row[j]` "
                "is the value from the previous row at column j; `row[j-1]` is already updated for the "
                "current row)."
            ),
            "code": {
                "python": (
                    "def min_path_cost(grid):\n"
                    "    m, n = len(grid), len(grid[0])\n"
                    "    row = [0] * n\n"
                    "    row[0] = grid[0][0]\n"
                    "    for j in range(1, n):\n"
                    "        row[j] = row[j - 1] + grid[0][j]\n"
                    "    for i in range(1, m):\n"
                    "        row[0] += grid[i][0]\n"
                    "        for j in range(1, n):\n"
                    "            row[j] = grid[i][j] + min(row[j], row[j - 1])\n"
                    "    return row[n - 1]"
                ),
            },
        },
        {
            "title": "Dijkstra (Generalised — 4-direction movement)",
            "time_complexity": "O(m·n · log(m·n))",
            "space_complexity": "O(m·n)",
            "description": (
                "If movement is unconstrained (4-direction or 8-direction), the DP recurrence breaks "
                "because there's no longer a monotonic visit order. Switch to Dijkstra: priority queue of "
                "`(cost, cell)`, expand the cheapest, relax neighbours. Works for any non-negative weights."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "def min_path_cost_dijkstra(grid):\n"
                    "    m, n = len(grid), len(grid[0])\n"
                    "    INF = float('inf')\n"
                    "    dist = [[INF] * n for _ in range(m)]\n"
                    "    dist[0][0] = grid[0][0]\n"
                    "    heap = [(grid[0][0], 0, 0)]\n"
                    "    while heap:\n"
                    "        d, i, j = heapq.heappop(heap)\n"
                    "        if d > dist[i][j]: continue\n"
                    "        if (i, j) == (m - 1, n - 1):\n"
                    "            return d\n"
                    "        for di, dj in ((1, 0), (0, 1), (-1, 0), (0, -1)):\n"
                    "            ni, nj = i + di, j + dj\n"
                    "            if 0 <= ni < m and 0 <= nj < n:\n"
                    "                nd = d + grid[ni][nj]\n"
                    "                if nd < dist[ni][nj]:\n"
                    "                    dist[ni][nj] = nd\n"
                    "                    heapq.heappush(heap, (nd, ni, nj))\n"
                    "    return dist[m - 1][n - 1]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise: shortest path in a DAG of cells (right + down only). DP fits perfectly.",
        "2. State: `dp[i][j]` = min cost to reach (i, j). Transition: `min` of the two predecessors plus current cell.",
        "3. First row and column have only one predecessor — handle separately.",
        "4. Space-optimise to O(n) by rolling the DP table to a single row.",
        "5. If movement generalises to 4 directions, the DP order breaks. Use Dijkstra.",
        "6. Negative weights → Bellman-Ford or specify the problem rules out negative cycles.",
    ],
    "tips": [
        "DP only works because movement is monotonic (right + down). Don't try DP with 4-direction movement.",
        "Space-optimised DP is a frequent follow-up — practise the in-place roll.",
        "If the problem says 'don't mutate the input grid', allocate the DP table separately.",
        "Common follow-up: 'minimise + return the path.' Track parent pointers per cell, walk back from (m-1, n-1).",
        "Common follow-up: 'k-th shortest path.' Yen's algorithm or path enumeration with priority queues.",
    ],
    "companies": ["Amazon", "Bloomberg", "Microsoft", "Apple"],
    "topics": ["Dynamic Programming", "Matrix", "Dijkstra"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(m·n)",
}


def REFERENCE(grid):
    m, n = len(grid), len(grid[0])
    dp = [[0] * n for _ in range(m)]
    dp[0][0] = grid[0][0]
    for j in range(1, n):
        dp[0][j] = dp[0][j - 1] + grid[0][j]
    for i in range(1, m):
        dp[i][0] = dp[i - 1][0] + grid[i][0]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = grid[i][j] + min(dp[i - 1][j], dp[i][j - 1])
    return dp[m - 1][n - 1]


register(PAYLOAD, REFERENCE)
