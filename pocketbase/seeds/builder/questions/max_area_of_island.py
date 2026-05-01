"""Max Area of Island — Medium. Graph / DFS / BFS.

LC 695. Direct sibling of Number of Islands — same 4-directional flood
fill skeleton, but instead of incrementing a counter per component you
return the *size* of each component and track the maximum. The right
answer is just one DFS or BFS over the grid; everything else is variations
on how you mark visited cells (sink to 0 vs. visited set).
"""
from builder.registry import register
from collections import deque
from copy import deepcopy


PAYLOAD = {
    "title": "Max Area of Island",
    "difficulty": "Medium",
    "description": (
        "You are given an `m x n` binary matrix `grid`. An **island** is a group of `1`'s (representing land) "
        "connected **4-directionally** (horizontal or vertical). You may assume all four edges of the grid are "
        "surrounded by water.\n\n"
        "The **area** of an island is the number of cells with a value `1` in the island.\n\n"
        "Return the **maximum area** of an island in `grid`. If there is no island, return `0`.\n\n"
        "**Example 1:**\n"
        "- Input:\n"
        "  ```\n"
        "  grid = [\n"
        "    [0,0,1,0,0,0,0,1,0,0,0,0,0],\n"
        "    [0,0,0,0,0,0,0,1,1,1,0,0,0],\n"
        "    [0,1,1,0,1,0,0,0,0,0,0,0,0],\n"
        "    [0,1,0,0,1,1,0,0,1,0,1,0,0],\n"
        "    [0,1,0,0,1,1,0,0,1,1,1,0,0],\n"
        "    [0,0,0,0,0,0,0,0,0,0,1,0,0],\n"
        "    [0,0,0,0,0,0,0,1,1,1,0,0,0],\n"
        "    [0,0,0,0,0,0,0,1,1,0,0,0,0]\n"
        "  ]\n"
        "  ```\n"
        "- Output: `6`\n"
        "- Explanation: The largest island (the bottom-right cluster reaching up to the column-10 chain) has 6 cells.\n\n"
        "**Example 2:**\n"
        "- Input: `grid = [[0,0,0,0,0,0,0,0]]`\n"
        "- Output: `0`\n"
        "- Explanation: All water — no island, so the maximum area is 0."
    ),
    "hints": [
        "Same skeleton as Number of Islands: walk every cell, and when you hit an unvisited `1`, flood-fill the "
        "whole island. The twist: have the flood-fill **return the size** of the component instead of just "
        "marking it.",
        "DFS is the cleanest expression — `dfs(r, c)` returns `1 + dfs(neighbours)` and 0 when out of bounds or "
        "on water. Recursion handles the accumulation for free.",
        "Mark visited cells *as you enter them*, before recursing into neighbours — otherwise the same cell gets "
        "visited from multiple directions and the area is overcounted.",
        "Two valid marking strategies: (a) sink visited `1`s to `0` in place — saves O(m·n) memory but mutates "
        "the input; (b) keep a separate `visited` set/matrix — non-mutating but extra space.",
        "BFS variant: same idea, but pop a queue and accumulate a counter instead of recursing. Useful on huge "
        "grids where Python's recursion limit (~1000) bites — a single 1000x1000 island of all `1`s would blow "
        "the stack with naive DFS.",
    ],
    "constraints": [
        "m == grid.length",
        "n == grid[i].length",
        "1 <= m, n <= 50",
        "grid[i][j] is 0 or 1",
    ],
    "starter_code": {
        "python": "def max_area_of_island(grid):\n    # Your code here\n    pass",
        "javascript": "function maxAreaOfIsland(grid) {\n    // Your code here\n}",
        "java": "public int maxAreaOfIsland(int[][] grid) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[0,0,1,0,0],[0,1,1,1,0],[0,0,1,0,0]],\n"
            "        [[0,0,0,0],[0,0,0,0]],\n"
            "        [[1,1,1],[1,1,1]],\n"
            "    ]\n"
            "    for g in cases:\n"
            "        print(f\"max_area_of_island -> {max_area_of_island([row[:] for row in g])}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const cases = [\n"
            "    [[0,0,1,0,0],[0,1,1,1,0],[0,0,1,0,0]],\n"
            "    [[0,0,0,0],[0,0,0,0]],\n"
            "    [[1,1,1],[1,1,1]],\n"
            "];\n"
            "cases.forEach(g => console.log(`maxAreaOfIsland =`, maxAreaOfIsland(g.map(r => r.slice()))));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] grid = {{0,0,1,0,0},{0,1,1,1,0},{0,0,1,0,0}};\n"
            "        System.out.println(s.maxAreaOfIsland(grid));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"grid": [
            [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0],
            [0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0],
            [0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0],
        ]}, "expected": 6,
         "description": "Classic LeetCode example — best island has area 6", "tags": ["basic"]},
        {"input": {"grid": [[0, 0, 0, 0, 0, 0, 0, 0]]}, "expected": 0,
         "description": "All water — no island", "tags": ["edge"]},
        {"input": {"grid": [[1, 1, 1], [1, 1, 1], [1, 1, 1]]}, "expected": 9,
         "description": "All land — single island fills the grid", "tags": ["basic"]},
        {"input": {"grid": [
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0],
            [0, 0, 0, 1, 1],
            [0, 0, 0, 1, 1],
        ]}, "expected": 4,
         "description": "Multiple disjoint islands — pick the biggest (4 vs. 3)", "tags": ["basic"]},
        {"input": {"grid": [[1]]}, "expected": 1,
         "description": "Single-cell island", "tags": ["edge"]},
        {"input": {"grid": [[1, 1, 1, 1, 1, 1, 1, 1, 1, 1]]}, "expected": 10,
         "description": "Long thin horizontal island — full row", "tags": ["edge"]},
        {"input": {"grid": [
            [1, 1, 1, 1, 1],
            [1, 0, 0, 0, 1],
            [1, 0, 1, 0, 1],
            [1, 0, 0, 0, 1],
            [1, 1, 1, 1, 1],
        ]}, "expected": 16,
         "description": "Spiral / hollow ring — outer ring is one island of 16, isolated centre cell is its own",
         "tags": ["tricky"]},
        {"input": {"grid": [[1] * 50 for _ in range(50)]}, "expected": 2500,
         "description": "Large 50x50 grid of all 1s — single island of 2500", "tags": ["large"]},
        {"input": {"grid": [
            [1, 0, 1, 0, 1],
            [0, 1, 0, 1, 0],
            [1, 0, 1, 0, 1],
        ]}, "expected": 1,
         "description": "Checkerboard — diagonals don't connect, every island is size 1", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "DFS Recursive (Optimal)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Iterate every cell. When you find a `1`, recurse into the four neighbours, accumulating "
                "the size as you go. Sink each visited cell to `0` *before* recursing so you don't loop back. "
                "Track the global maximum. Each cell is visited at most once → O(m·n) time. Recursion depth is "
                "bounded by the size of the largest island, hence O(m·n) auxiliary space worst case."
            ),
            "code": {
                "python": (
                    "def max_area_of_island(grid):\n"
                    "    if not grid or not grid[0]:\n"
                    "        return 0\n"
                    "    m, n = len(grid), len(grid[0])\n"
                    "\n"
                    "    def dfs(r, c):\n"
                    "        if r < 0 or r >= m or c < 0 or c >= n or grid[r][c] != 1:\n"
                    "            return 0\n"
                    "        grid[r][c] = 0\n"
                    "        return 1 + dfs(r + 1, c) + dfs(r - 1, c) + dfs(r, c + 1) + dfs(r, c - 1)\n"
                    "\n"
                    "    best = 0\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            if grid[r][c] == 1:\n"
                    "                best = max(best, dfs(r, c))\n"
                    "    return best"
                ),
                "javascript": (
                    "function maxAreaOfIsland(grid) {\n"
                    "    if (!grid.length || !grid[0].length) return 0;\n"
                    "    const m = grid.length, n = grid[0].length;\n"
                    "    const dfs = (r, c) => {\n"
                    "        if (r < 0 || r >= m || c < 0 || c >= n || grid[r][c] !== 1) return 0;\n"
                    "        grid[r][c] = 0;\n"
                    "        return 1 + dfs(r+1,c) + dfs(r-1,c) + dfs(r,c+1) + dfs(r,c-1);\n"
                    "    };\n"
                    "    let best = 0;\n"
                    "    for (let r = 0; r < m; r++)\n"
                    "        for (let c = 0; c < n; c++)\n"
                    "            if (grid[r][c] === 1) best = Math.max(best, dfs(r, c));\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "public int maxAreaOfIsland(int[][] grid) {\n"
                    "    if (grid.length == 0 || grid[0].length == 0) return 0;\n"
                    "    int m = grid.length, n = grid[0].length, best = 0;\n"
                    "    for (int r = 0; r < m; r++)\n"
                    "        for (int c = 0; c < n; c++)\n"
                    "            if (grid[r][c] == 1) best = Math.max(best, dfs(grid, r, c, m, n));\n"
                    "    return best;\n"
                    "}\n"
                    "private int dfs(int[][] g, int r, int c, int m, int n) {\n"
                    "    if (r < 0 || r >= m || c < 0 || c >= n || g[r][c] != 1) return 0;\n"
                    "    g[r][c] = 0;\n"
                    "    return 1 + dfs(g,r+1,c,m,n) + dfs(g,r-1,c,m,n) + dfs(g,r,c+1,m,n) + dfs(g,r,c-1,m,n);\n"
                    "}"
                ),
            },
        },
        {
            "title": "BFS Iterative",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(min(m, n))",
            "description": (
                "Same flood fill, but expand each island with a queue. For each unvisited `1`, push it onto "
                "the queue, mark it as visited, and pop until empty — counting each pop. Update the global "
                "max. Avoids Python's recursion limit on a worst-case grid (e.g. a single huge island of "
                "all `1`s). Mark cells *as you enqueue them*, never as you dequeue — otherwise a cell can "
                "land in the queue multiple times and inflate the count."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "def max_area_of_island(grid):\n"
                    "    if not grid or not grid[0]:\n"
                    "        return 0\n"
                    "    m, n = len(grid), len(grid[0])\n"
                    "    best = 0\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            if grid[r][c] != 1:\n"
                    "                continue\n"
                    "            grid[r][c] = 0\n"
                    "            q = deque([(r, c)])\n"
                    "            area = 0\n"
                    "            while q:\n"
                    "                i, j = q.popleft()\n"
                    "                area += 1\n"
                    "                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n"
                    "                    ni, nj = i + di, j + dj\n"
                    "                    if 0 <= ni < m and 0 <= nj < n and grid[ni][nj] == 1:\n"
                    "                        grid[ni][nj] = 0\n"
                    "                        q.append((ni, nj))\n"
                    "            if area > best:\n"
                    "                best = area\n"
                    "    return best"
                ),
                "javascript": (
                    "function maxAreaOfIsland(grid) {\n"
                    "    if (!grid.length || !grid[0].length) return 0;\n"
                    "    const m = grid.length, n = grid[0].length;\n"
                    "    let best = 0;\n"
                    "    const dirs = [[1,0],[-1,0],[0,1],[0,-1]];\n"
                    "    for (let r = 0; r < m; r++) {\n"
                    "        for (let c = 0; c < n; c++) {\n"
                    "            if (grid[r][c] !== 1) continue;\n"
                    "            grid[r][c] = 0;\n"
                    "            const q = [[r, c]];\n"
                    "            let area = 0;\n"
                    "            while (q.length) {\n"
                    "                const [i, j] = q.shift();\n"
                    "                area++;\n"
                    "                for (const [di, dj] of dirs) {\n"
                    "                    const ni = i + di, nj = j + dj;\n"
                    "                    if (ni >= 0 && ni < m && nj >= 0 && nj < n && grid[ni][nj] === 1) {\n"
                    "                        grid[ni][nj] = 0;\n"
                    "                        q.push([ni, nj]);\n"
                    "                    }\n"
                    "                }\n"
                    "            }\n"
                    "            if (area > best) best = area;\n"
                    "        }\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: same connected-components problem as Number of Islands, only the answer changes from 'count' to 'max size'.",
        "2. The natural skeleton: outer double loop scans every cell; when it hits a `1`, flood-fill from there and ask the flood-fill to return the area it covered.",
        "3. Recursive DFS expresses this cleanly — `dfs` returns `1 + dfs(neighbours)` and `0` for out-of-bounds or water. The recursion does the accumulation automatically.",
        "4. Mark visited cells *before* recursing into neighbours, otherwise the same cell is counted from each direction it's entered.",
        "5. Discuss the marking trade-off: sinking `1` → `0` mutates the input but uses no extra memory; a `visited` matrix is non-destructive but doubles the space. Ask the interviewer.",
        "6. Track the running max across the outer loop. Edge cases (all water, empty grid, single cell) fall out for free as long as the bounds check is the first thing in `dfs`.",
        "7. If the grid can be huge (or a single island can fill it), prefer the iterative BFS variant to avoid blowing the recursion stack.",
    ],
    "tips": [
        "Diagonals do NOT connect — only up/down/left/right. Same gotcha as Number of Islands.",
        "Don't forget to mark the *starting* cell visited before you recurse — easy off-by-one that turns a connected island into an infinite loop.",
        "Sister problems: Number of Islands (LC 200) — count components instead of sizing them. Number of Distinct Islands (LC 694) — record canonical shape per component.",
        "Generalisation: Island Perimeter (LC 463) — same traversal, but accumulate edges-not-shared-with-another-1 instead of cells.",
        "Follow-up — 'Making A Large Island' (LC 827, hard): flip at most one `0` to `1`. Two-pass: first pass labels each island with an id and stores its size; second pass tries every `0` and sums the distinct neighbour-island sizes.",
        "If recursion depth is a concern (Python's default limit is ~1000), the iterative BFS gets you out of trouble without changing the algorithm.",
    ],
    "companies": ["Amazon", "Google", "Facebook", "Microsoft", "Apple"],
    "topics": ["Graph", "DFS", "BFS", "Union Find", "Matrix", "Array"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(m·n)",
}


def REFERENCE(grid):
    grid = deepcopy(grid)
    if not grid or not grid[0]:
        return 0
    m, n = len(grid), len(grid[0])
    best = 0
    for r in range(m):
        for c in range(n):
            if grid[r][c] != 1:
                continue
            grid[r][c] = 0
            q = deque([(r, c)])
            area = 0
            while q:
                i, j = q.popleft()
                area += 1
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ni, nj = i + di, j + dj
                    if 0 <= ni < m and 0 <= nj < n and grid[ni][nj] == 1:
                        grid[ni][nj] = 0
                        q.append((ni, nj))
            if area > best:
                best = area
    return best


register(PAYLOAD, REFERENCE)
