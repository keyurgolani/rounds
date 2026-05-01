"""Number of Islands — Medium. Graph / DFS / BFS / Union-Find.

The canonical 'flood fill on a grid' question. Every connected
component of '1's is one island. Three respectable solutions: DFS
sinking, BFS queue, and Union-Find. Pick one based on what the
follow-up is — Number of Islands II (streaming additions) is the
Union-Find sweet spot; everything else is cleanest as DFS.
"""
from builder.registry import register
from collections import deque


PAYLOAD = {
    "title": "Number of Islands",
    "difficulty": "Medium",
    "description": (
        "Given an `m x n` 2D binary grid `grid` which represents a map of `'1'`s (land) and `'0'`s (water), "
        "return the **number of islands**.\n\n"
        "An **island** is surrounded by water and is formed by connecting adjacent lands horizontally or "
        "vertically. You may assume all four edges of the grid are surrounded by water.\n\n"
        "**Example 1:**\n"
        "- Input:\n"
        "  ```\n"
        "  grid = [\n"
        "    [\"1\",\"1\",\"1\",\"1\",\"0\"],\n"
        "    [\"1\",\"1\",\"0\",\"1\",\"0\"],\n"
        "    [\"1\",\"1\",\"0\",\"0\",\"0\"],\n"
        "    [\"0\",\"0\",\"0\",\"0\",\"0\"]\n"
        "  ]\n"
        "  ```\n"
        "- Output: `1`\n\n"
        "**Example 2:**\n"
        "- Input:\n"
        "  ```\n"
        "  grid = [\n"
        "    [\"1\",\"1\",\"0\",\"0\",\"0\"],\n"
        "    [\"1\",\"1\",\"0\",\"0\",\"0\"],\n"
        "    [\"0\",\"0\",\"1\",\"0\",\"0\"],\n"
        "    [\"0\",\"0\",\"0\",\"1\",\"1\"]\n"
        "  ]\n"
        "  ```\n"
        "- Output: `3`"
    ),
    "hints": [
        "Each island is a connected component of '1' cells under 4-directional adjacency. So the question is: "
        "how many connected components are there?",
        "Iterate over every cell. When you hit a '1' that hasn't been visited, you've found a new island — "
        "increment the counter, then traverse and mark the entire island so you never count it again.",
        "Two natural traversals: DFS (recursion or stack) and BFS (queue). Either is O(m·n).",
        "Marking trick: instead of a separate `visited` set, overwrite the '1's you visit to '0' (sink the "
        "island). Saves O(m·n) auxiliary space — but mutates the input.",
        "Union-Find variant: union every '1' with its right/down '1' neighbour. The answer is (number of '1' "
        "cells) − (successful unions). Or just: count distinct roots among '1' cells.",
    ],
    "constraints": [
        "m == grid.length",
        "n == grid[i].length",
        "1 <= m, n <= 300",
        "grid[i][j] is '0' or '1'",
    ],
    "starter_code": {
        "python": "def num_islands(grid):\n    # Your code here\n    pass",
        "javascript": "function numIslands(grid) {\n    // Your code here\n}",
        "java": "public int numIslands(char[][] grid) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[\"1\",\"1\",\"0\"],[\"0\",\"1\",\"0\"],[\"0\",\"0\",\"1\"]],\n"
            "        [[\"1\",\"1\",\"1\",\"1\",\"0\"],[\"1\",\"1\",\"0\",\"1\",\"0\"],[\"1\",\"1\",\"0\",\"0\",\"0\"],[\"0\",\"0\",\"0\",\"0\",\"0\"]],\n"
            "        [[\"0\",\"0\",\"0\"]],\n"
            "    ]\n"
            "    for g in cases:\n"
            "        print(f\"num_islands -> {num_islands([row[:] for row in g])}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const cases = [\n"
            "    [[\"1\",\"1\",\"0\"],[\"0\",\"1\",\"0\"],[\"0\",\"0\",\"1\"]],\n"
            "    [[\"1\",\"1\",\"1\",\"1\",\"0\"],[\"1\",\"1\",\"0\",\"1\",\"0\"],[\"1\",\"1\",\"0\",\"0\",\"0\"],[\"0\",\"0\",\"0\",\"0\",\"0\"]],\n"
            "];\n"
            "cases.forEach(g => console.log(`numIslands =`, numIslands(g.map(r => r.slice()))));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        char[][] grid = {{'1','1','0'},{'0','1','0'},{'0','0','1'}};\n"
            "        System.out.println(s.numIslands(grid));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"grid": [["1", "1", "0"], ["0", "1", "0"], ["0", "0", "1"]]}, "expected": 2,
         "description": "Two islands — diagonal touch does NOT connect", "tags": ["basic"]},
        {"input": {"grid": [["1", "1", "1", "1", "0"], ["1", "1", "0", "1", "0"],
                            ["1", "1", "0", "0", "0"], ["0", "0", "0", "0", "0"]]}, "expected": 1,
         "description": "Single L-shaped island", "tags": ["basic"]},
        {"input": {"grid": [["1", "1", "0", "0", "0"], ["1", "1", "0", "0", "0"],
                            ["0", "0", "1", "0", "0"], ["0", "0", "0", "1", "1"]]}, "expected": 3,
         "description": "Three disjoint islands", "tags": ["basic"]},
        {"input": {"grid": [["0", "0", "0"]]}, "expected": 0,
         "description": "All water — no islands", "tags": ["edge"]},
        {"input": {"grid": []}, "expected": 0,
         "description": "Empty grid", "tags": ["edge"]},
        {"input": {"grid": [["1"]]}, "expected": 1,
         "description": "Single land cell", "tags": ["edge"]},
        {"input": {"grid": [["1", "0", "1", "0", "1"]]}, "expected": 3,
         "description": "Single row — alternating land/water", "tags": ["edge"]},
        {"input": {"grid": [["1", "1", "1"], ["1", "1", "1"], ["1", "1", "1"]]}, "expected": 1,
         "description": "Solid land — one giant island", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "DFS with Sinking (Optimal)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n) recursion worst case",
            "description": (
                "Walk every cell. When you hit a '1', increment the counter and DFS from that cell, "
                "overwriting each visited '1' to '0' (sinking the island). The next outer-loop pass over "
                "those cells skips them because they're now '0'. Mutates the grid — make a copy if the "
                "caller cares."
            ),
            "code": {
                "python": (
                    "def num_islands(grid):\n"
                    "    if not grid or not grid[0]:\n"
                    "        return 0\n"
                    "    m, n = len(grid), len(grid[0])\n"
                    "\n"
                    "    def dfs(r, c):\n"
                    "        if r < 0 or r >= m or c < 0 or c >= n or grid[r][c] != '1':\n"
                    "            return\n"
                    "        grid[r][c] = '0'\n"
                    "        dfs(r + 1, c); dfs(r - 1, c); dfs(r, c + 1); dfs(r, c - 1)\n"
                    "\n"
                    "    count = 0\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            if grid[r][c] == '1':\n"
                    "                count += 1\n"
                    "                dfs(r, c)\n"
                    "    return count"
                ),
                "javascript": (
                    "function numIslands(grid) {\n"
                    "    if (!grid.length || !grid[0].length) return 0;\n"
                    "    const m = grid.length, n = grid[0].length;\n"
                    "    const dfs = (r, c) => {\n"
                    "        if (r < 0 || r >= m || c < 0 || c >= n || grid[r][c] !== '1') return;\n"
                    "        grid[r][c] = '0';\n"
                    "        dfs(r+1,c); dfs(r-1,c); dfs(r,c+1); dfs(r,c-1);\n"
                    "    };\n"
                    "    let count = 0;\n"
                    "    for (let r = 0; r < m; r++)\n"
                    "        for (let c = 0; c < n; c++)\n"
                    "            if (grid[r][c] === '1') { count++; dfs(r, c); }\n"
                    "    return count;\n"
                    "}"
                ),
                "java": (
                    "public int numIslands(char[][] grid) {\n"
                    "    if (grid.length == 0 || grid[0].length == 0) return 0;\n"
                    "    int m = grid.length, n = grid[0].length, count = 0;\n"
                    "    for (int r = 0; r < m; r++)\n"
                    "        for (int c = 0; c < n; c++)\n"
                    "            if (grid[r][c] == '1') { count++; dfs(grid, r, c, m, n); }\n"
                    "    return count;\n"
                    "}\n"
                    "private void dfs(char[][] g, int r, int c, int m, int n) {\n"
                    "    if (r < 0 || r >= m || c < 0 || c >= n || g[r][c] != '1') return;\n"
                    "    g[r][c] = '0';\n"
                    "    dfs(g,r+1,c,m,n); dfs(g,r-1,c,m,n); dfs(g,r,c+1,m,n); dfs(g,r,c-1,m,n);\n"
                    "}"
                ),
            },
        },
        {
            "title": "BFS (Iterative)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(min(m, n)) for the queue",
            "description": (
                "Same shape as DFS, but expand each island with a queue instead of recursion. Avoids "
                "Python's recursion limit on a 300x300 grid of all '1's. Mark cells as visited *when "
                "you enqueue them*, not when you dequeue — otherwise the same cell gets enqueued multiple "
                "times and the queue blows up."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "def num_islands(grid):\n"
                    "    if not grid or not grid[0]:\n"
                    "        return 0\n"
                    "    m, n = len(grid), len(grid[0])\n"
                    "    count = 0\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            if grid[r][c] != '1':\n"
                    "                continue\n"
                    "            count += 1\n"
                    "            grid[r][c] = '0'\n"
                    "            q = deque([(r, c)])\n"
                    "            while q:\n"
                    "                i, j = q.popleft()\n"
                    "                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n"
                    "                    ni, nj = i + di, j + dj\n"
                    "                    if 0 <= ni < m and 0 <= nj < n and grid[ni][nj] == '1':\n"
                    "                        grid[ni][nj] = '0'\n"
                    "                        q.append((ni, nj))\n"
                    "    return count"
                ),
            },
        },
        {
            "title": "Union-Find",
            "time_complexity": "O(m·n·α(m·n))",
            "space_complexity": "O(m·n)",
            "description": (
                "Treat each '1' cell as a node. Union it with its right and down '1' neighbours (left "
                "and up are redundant — they were processed earlier). The answer is the number of distinct "
                "roots among '1' cells. Same asymptotic cost as DFS/BFS but the natural shape for the "
                "streaming follow-up (Number of Islands II): each addLand becomes a constant-time union."
            ),
            "code": {
                "python": (
                    "def num_islands(grid):\n"
                    "    if not grid or not grid[0]:\n"
                    "        return 0\n"
                    "    m, n = len(grid), len(grid[0])\n"
                    "    parent = list(range(m * n))\n"
                    "    rank = [0] * (m * n)\n"
                    "    count = sum(row.count('1') for row in grid)\n"
                    "\n"
                    "    def find(x):\n"
                    "        while parent[x] != x:\n"
                    "            parent[x] = parent[parent[x]]\n"
                    "            x = parent[x]\n"
                    "        return x\n"
                    "\n"
                    "    def union(a, b):\n"
                    "        nonlocal count\n"
                    "        ra, rb = find(a), find(b)\n"
                    "        if ra == rb:\n"
                    "            return\n"
                    "        if rank[ra] < rank[rb]:\n"
                    "            ra, rb = rb, ra\n"
                    "        parent[rb] = ra\n"
                    "        if rank[ra] == rank[rb]:\n"
                    "            rank[ra] += 1\n"
                    "        count -= 1\n"
                    "\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            if grid[r][c] != '1':\n"
                    "                continue\n"
                    "            idx = r * n + c\n"
                    "            if r + 1 < m and grid[r + 1][c] == '1':\n"
                    "                union(idx, (r + 1) * n + c)\n"
                    "            if c + 1 < n and grid[r][c + 1] == '1':\n"
                    "                union(idx, r * n + (c + 1))\n"
                    "    return count"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: count connected components in an undirected graph where nodes are '1' cells and edges are 4-directional adjacency.",
        "2. Outer loop scans every cell. When we land on an unvisited '1', that's the start of a new island — increment the counter.",
        "3. From that starting cell, traverse the entire island (DFS or BFS), marking every visited '1' so the outer loop skips them.",
        "4. Marking choice: a separate `visited` set is clean but costs O(m·n) memory; sinking by overwriting '1' → '0' is in-place but mutates the input — ask the interviewer whether mutation is acceptable.",
        "5. Bounds check first in the recursive DFS — if you check after recursing, you'll IndexError at the grid edges.",
        "6. Edge cases: empty grid, single cell, all water, all land. Each falls out naturally if the bounds and emptiness checks come first.",
    ],
    "tips": [
        "Diagonal cells are NOT connected — only up/down/left/right. Easy to miss; the interviewer is watching.",
        "Number of Islands II (streaming addLand operations): Union-Find is the only sane approach. Each addLand → at most 4 unions, O(α) amortised.",
        "Max Area of Island (LC 695): same traversal, but return the size of each component and track the max instead of incrementing a counter.",
        "Number of Distinct Islands (LC 694): same traversal, but record the *shape* of each island as a normalised path/coordinate signature and count distinct signatures.",
        "Surrounded Regions (LC 130) and Pacific Atlantic Water Flow (LC 417) are 'flood fill from the boundary' variants — same DFS/BFS skeleton, different starting set.",
    ],
    "companies": ["Amazon", "Google", "Facebook", "Microsoft", "Apple"],
    "topics": ["Graph", "DFS", "BFS", "Union Find", "Matrix"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(m·n)",
}


def REFERENCE(grid):
    grid = [row[:] for row in grid]
    if not grid or not grid[0]:
        return 0
    m, n = len(grid), len(grid[0])
    count = 0
    for r in range(m):
        for c in range(n):
            if grid[r][c] != '1':
                continue
            count += 1
            grid[r][c] = '0'
            q = deque([(r, c)])
            while q:
                i, j = q.popleft()
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ni, nj = i + di, j + dj
                    if 0 <= ni < m and 0 <= nj < n and grid[ni][nj] == '1':
                        grid[ni][nj] = '0'
                        q.append((ni, nj))
    return count


register(PAYLOAD, REFERENCE)
