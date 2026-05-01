"""Pacific Atlantic Water Flow — Medium. Graph / Multi-source DFS / BFS.

Classic 'flood fill from the boundary' question. The trick everyone
misses on the first pass: don't simulate water flowing *down* from
each cell — that's O((m·n)²). Instead, reverse the direction. Start
from each ocean's edge cells and walk INTO neighbours of *equal or
greater* height. Each ocean ends up with the set of cells that can
reach it. The intersection is the answer. O(m·n).
"""
from builder.registry import register
from collections import deque


PAYLOAD = {
    "title": "Pacific Atlantic Water Flow",
    "difficulty": "Medium",
    "description": (
        "There is an `m x n` rectangular island that borders both the **Pacific Ocean** and the "
        "**Atlantic Ocean**. The Pacific Ocean touches the island's left and top edges, and the Atlantic "
        "Ocean touches the island's right and bottom edges.\n\n"
        "The island is partitioned into a grid of square cells. You are given an `m x n` integer matrix "
        "`heights` where `heights[r][c]` represents the height above sea level of the cell at coordinate "
        "`(r, c)`.\n\n"
        "Rain water can flow to neighbouring cells directly north, south, east, and west if the neighbouring "
        "cell's height is **less than or equal to** the current cell's height. Water can flow from any cell "
        "adjacent to an ocean into the ocean.\n\n"
        "Return a 2D list of grid coordinates `result` where `result[i] = [r_i, c_i]` denotes that rain water "
        "falling on cell `(r_i, c_i)` can flow to **both** the Pacific and Atlantic oceans.\n\n"
        "**Example 1:**\n"
        "- Input:\n"
        "  ```\n"
        "  heights = [\n"
        "    [1,2,2,3,5],\n"
        "    [3,2,3,4,4],\n"
        "    [2,4,5,3,1],\n"
        "    [6,7,1,4,5],\n"
        "    [5,1,1,2,4]\n"
        "  ]\n"
        "  ```\n"
        "- Output: `[[0,4],[1,3],[1,4],[2,2],[3,0],[3,1],[4,0]]`\n\n"
        "**Example 2:**\n"
        "- Input: `heights = [[1]]`\n"
        "- Output: `[[0,0]]`\n"
        "- Explanation: A single cell trivially borders both oceans."
    ),
    "hints": [
        "Naive idea: from each cell, simulate water flowing downhill until it hits an ocean. That's O((m·n)²) "
        "in the worst case (one big plateau) and it re-walks the same paths over and over.",
        "Reverse the direction. Instead of 'can this cell reach the ocean?', ask 'can the ocean reach this "
        "cell, walking uphill or flat?'. Start the traversal at the ocean's edge cells and step to neighbours "
        "with height **greater than or equal to** the current cell.",
        "Run two independent traversals — one from the Pacific edges (top row + left column), one from the "
        "Atlantic edges (bottom row + right column). Each produces a set of reachable cells.",
        "The answer is the **intersection** of the two reachable sets. Walk every cell once at the end and "
        "collect those in both.",
        "DFS or BFS — either works. Use two `visited` matrices (one per ocean). Total work is O(m·n) because "
        "each cell is dequeued at most once per ocean.",
    ],
    "constraints": [
        "m == heights.length",
        "n == heights[r].length",
        "1 <= m, n <= 200",
        "0 <= heights[r][c] <= 10⁵",
    ],
    "starter_code": {
        "python": "def pacific_atlantic(heights):\n    # Your code here\n    pass",
        "javascript": "function pacificAtlantic(heights) {\n    // Your code here\n}",
        "java": "public List<List<Integer>> pacificAtlantic(int[][] heights) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[1,2,2,3,5],[3,2,3,4,4],[2,4,5,3,1],[6,7,1,4,5],[5,1,1,2,4]],\n"
            "        [[1]],\n"
            "        [[1,2,3]],\n"
            "    ]\n"
            "    for h in cases:\n"
            "        print(f\"pacific_atlantic -> {pacific_atlantic([row[:] for row in h])}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const cases = [\n"
            "    [[1,2,2,3,5],[3,2,3,4,4],[2,4,5,3,1],[6,7,1,4,5],[5,1,1,2,4]],\n"
            "    [[1]],\n"
            "];\n"
            "cases.forEach(h => console.log(`pacificAtlantic =`, pacificAtlantic(h.map(r => r.slice()))));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.*;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] h = {{1,2,2,3,5},{3,2,3,4,4},{2,4,5,3,1},{6,7,1,4,5},{5,1,1,2,4}};\n"
            "        System.out.println(s.pacificAtlantic(h));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"heights": [[1, 2, 2, 3, 5], [3, 2, 3, 4, 4], [2, 4, 5, 3, 1],
                               [6, 7, 1, 4, 5], [5, 1, 1, 2, 4]]},
         "expected": [[0, 4], [1, 3], [1, 4], [2, 2], [3, 0], [3, 1], [4, 0]],
         "description": "Classic LC 5x5 — seven cells reach both oceans",
         "matcher": {"$match": "unordered_deep", "value": [[0, 4], [1, 3], [1, 4], [2, 2], [3, 0], [3, 1], [4, 0]]},
         "tags": ["basic"]},
        {"input": {"heights": [[1]]}, "expected": [[0, 0]],
         "description": "Single cell — trivially borders both oceans",
         "matcher": {"$match": "unordered_deep", "value": [[0, 0]]},
         "tags": ["edge"]},
        {"input": {"heights": [[1, 2, 3]]}, "expected": [[0, 0], [0, 1], [0, 2]],
         "description": "Single row — every cell is on both edges",
         "matcher": {"$match": "unordered_deep", "value": [[0, 0], [0, 1], [0, 2]]},
         "tags": ["edge"]},
        {"input": {"heights": [[1], [2], [3]]}, "expected": [[0, 0], [1, 0], [2, 0]],
         "description": "Single column — every cell is on both edges",
         "matcher": {"$match": "unordered_deep", "value": [[0, 0], [1, 0], [2, 0]]},
         "tags": ["edge"]},
        {"input": {"heights": [[5, 5, 5], [5, 5, 5], [5, 5, 5]]},
         "expected": [[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]],
         "description": "All-equal plateau — water flows freely; every cell qualifies",
         "matcher": {"$match": "unordered_deep",
                     "value": [[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]]},
         "tags": ["tricky"]},
        {"input": {"heights": [[3, 3, 3], [3, 1, 3], [3, 3, 3]]},
         "expected": [[0, 0], [0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1], [2, 2]],
         "description": "Descending plateau — interior valley can't reach either ocean",
         "matcher": {"$match": "unordered_deep",
                     "value": [[0, 0], [0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1], [2, 2]]},
         "tags": ["tricky"]},
        {"input": {"heights": [[1, 2, 3], [8, 9, 4], [7, 6, 5]]},
         "expected": [[0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]],
         "description": "Spiral ascending — high ridge reaches both oceans",
         "matcher": {"$match": "unordered_deep",
                     "value": [[0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]]},
         "tags": ["tricky"]},
        {"input": {"heights": [[1, 1], [1, 1]]},
         "expected": [[0, 0], [0, 1], [1, 0], [1, 1]],
         "description": "Tiny 2x2 all-equal — every cell sits on a corner",
         "matcher": {"$match": "unordered_deep",
                     "value": [[0, 0], [0, 1], [1, 0], [1, 1]]},
         "tags": ["edge"]},
        {"input": {"heights": [[10, 10, 10], [10, 1, 10], [10, 10, 10]]},
         "expected": [[0, 0], [0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1], [2, 2]],
         "description": "Border ridge — only the trapped centre fails to reach both oceans",
         "matcher": {"$match": "unordered_deep",
                     "value": [[0, 0], [0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1], [2, 2]]},
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Reverse DFS from Edges (Optimal)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Start at each ocean's boundary cells and DFS *uphill* (to neighbours with height >= "
                "current). Mark every reachable cell in a per-ocean visited matrix. The answer is the "
                "intersection. Each cell is visited at most twice (once per ocean), so the total work is "
                "linear in the grid size."
            ),
            "code": {
                "python": (
                    "def pacific_atlantic(heights):\n"
                    "    if not heights or not heights[0]:\n"
                    "        return []\n"
                    "    m, n = len(heights), len(heights[0])\n"
                    "    pac = [[False] * n for _ in range(m)]\n"
                    "    atl = [[False] * n for _ in range(m)]\n"
                    "\n"
                    "    def dfs(r, c, visited):\n"
                    "        visited[r][c] = True\n"
                    "        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n"
                    "            nr, nc = r + dr, c + dc\n"
                    "            if (0 <= nr < m and 0 <= nc < n and not visited[nr][nc]\n"
                    "                    and heights[nr][nc] >= heights[r][c]):\n"
                    "                dfs(nr, nc, visited)\n"
                    "\n"
                    "    for c in range(n):\n"
                    "        dfs(0, c, pac)\n"
                    "        dfs(m - 1, c, atl)\n"
                    "    for r in range(m):\n"
                    "        dfs(r, 0, pac)\n"
                    "        dfs(r, n - 1, atl)\n"
                    "\n"
                    "    return [[r, c] for r in range(m) for c in range(n) if pac[r][c] and atl[r][c]]"
                ),
                "javascript": (
                    "function pacificAtlantic(heights) {\n"
                    "    if (!heights.length || !heights[0].length) return [];\n"
                    "    const m = heights.length, n = heights[0].length;\n"
                    "    const pac = Array.from({length: m}, () => Array(n).fill(false));\n"
                    "    const atl = Array.from({length: m}, () => Array(n).fill(false));\n"
                    "    const dfs = (r, c, visited) => {\n"
                    "        visited[r][c] = true;\n"
                    "        for (const [dr, dc] of [[1,0],[-1,0],[0,1],[0,-1]]) {\n"
                    "            const nr = r + dr, nc = c + dc;\n"
                    "            if (nr >= 0 && nr < m && nc >= 0 && nc < n\n"
                    "                && !visited[nr][nc] && heights[nr][nc] >= heights[r][c])\n"
                    "                dfs(nr, nc, visited);\n"
                    "        }\n"
                    "    };\n"
                    "    for (let c = 0; c < n; c++) { dfs(0, c, pac); dfs(m-1, c, atl); }\n"
                    "    for (let r = 0; r < m; r++) { dfs(r, 0, pac); dfs(r, n-1, atl); }\n"
                    "    const result = [];\n"
                    "    for (let r = 0; r < m; r++)\n"
                    "        for (let c = 0; c < n; c++)\n"
                    "            if (pac[r][c] && atl[r][c]) result.push([r, c]);\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public List<List<Integer>> pacificAtlantic(int[][] heights) {\n"
                    "    List<List<Integer>> result = new ArrayList<>();\n"
                    "    if (heights.length == 0 || heights[0].length == 0) return result;\n"
                    "    int m = heights.length, n = heights[0].length;\n"
                    "    boolean[][] pac = new boolean[m][n];\n"
                    "    boolean[][] atl = new boolean[m][n];\n"
                    "    for (int c = 0; c < n; c++) { dfs(heights, 0, c, pac, m, n); dfs(heights, m-1, c, atl, m, n); }\n"
                    "    for (int r = 0; r < m; r++) { dfs(heights, r, 0, pac, m, n); dfs(heights, r, n-1, atl, m, n); }\n"
                    "    for (int r = 0; r < m; r++)\n"
                    "        for (int c = 0; c < n; c++)\n"
                    "            if (pac[r][c] && atl[r][c]) result.add(Arrays.asList(r, c));\n"
                    "    return result;\n"
                    "}\n"
                    "private void dfs(int[][] h, int r, int c, boolean[][] v, int m, int n) {\n"
                    "    v[r][c] = true;\n"
                    "    int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};\n"
                    "    for (int[] d : dirs) {\n"
                    "        int nr = r + d[0], nc = c + d[1];\n"
                    "        if (nr >= 0 && nr < m && nc >= 0 && nc < n && !v[nr][nc] && h[nr][nc] >= h[r][c])\n"
                    "            dfs(h, nr, nc, v, m, n);\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Reverse BFS from Edges",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Same shape as the DFS solution, but expand each ocean with a queue. Useful when the grid "
                "is large enough that recursion-depth would be a concern (e.g. a 200x200 monotone grid in "
                "Python). Seed the queue with all of an ocean's edge cells, then BFS outward to higher-or-"
                "equal neighbours."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "def pacific_atlantic(heights):\n"
                    "    if not heights or not heights[0]:\n"
                    "        return []\n"
                    "    m, n = len(heights), len(heights[0])\n"
                    "\n"
                    "    def bfs(starts):\n"
                    "        visited = [[False] * n for _ in range(m)]\n"
                    "        q = deque()\n"
                    "        for r, c in starts:\n"
                    "            visited[r][c] = True\n"
                    "            q.append((r, c))\n"
                    "        while q:\n"
                    "            r, c = q.popleft()\n"
                    "            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n"
                    "                nr, nc = r + dr, c + dc\n"
                    "                if (0 <= nr < m and 0 <= nc < n and not visited[nr][nc]\n"
                    "                        and heights[nr][nc] >= heights[r][c]):\n"
                    "                    visited[nr][nc] = True\n"
                    "                    q.append((nr, nc))\n"
                    "        return visited\n"
                    "\n"
                    "    pac_starts = [(0, c) for c in range(n)] + [(r, 0) for r in range(m)]\n"
                    "    atl_starts = [(m - 1, c) for c in range(n)] + [(r, n - 1) for r in range(m)]\n"
                    "    pac, atl = bfs(pac_starts), bfs(atl_starts)\n"
                    "    return [[r, c] for r in range(m) for c in range(n) if pac[r][c] and atl[r][c]]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. The naive read of the problem says 'simulate water flowing downhill from each cell'. That's O((m·n)²) on a plateau and re-walks the same downhill paths from every starting point.",
        "2. Reverse the question. 'Cell X can reach the Pacific' iff 'starting from a Pacific edge cell, we can climb (height non-decreasing) to X'. Same relation, traversed in the opposite direction.",
        "3. Run two independent multi-source flood fills — one seeded with all Pacific edge cells (top row + left column), one with all Atlantic edge cells (bottom row + right column).",
        "4. Each flood fill produces a boolean matrix marking 'cells this ocean can reach'. Every cell is enqueued at most once per fill, so each fill is O(m·n).",
        "5. Final answer: walk the grid once and collect every (r, c) where both matrices are true.",
        "6. Edge cases: single row / single column / single cell — every cell is on both edges, so the answer is every cell. Falls out naturally because both flood fills mark everything.",
    ],
    "tips": [
        "Comparison is `>=`, NOT `>`. Equal-height neighbours allow flow in both directions; missing the equality drops valid plateau paths.",
        "Multi-source BFS/DFS: seed the queue/stack with *all* edge cells before starting the loop, not one corner at a time.",
        "Don't allocate a fresh visited matrix inside the recursive call — keep one per ocean and pass it in. Resetting per-cell would make the algorithm O(m²·n²).",
        "If you DFS recursively in Python on a 200x200 grid, bump `sys.setrecursionlimit` or switch to BFS — a worst-case monotone path is 40,000 frames deep.",
        "Surrounded Regions (LC 130) and Number of Enclaves (LC 1020) are the same 'flood fill from the boundary' pattern. Recognise the family.",
    ],
    "companies": ["Amazon", "Google", "Facebook", "Microsoft", "Apple"],
    "topics": ["Graph", "DFS", "BFS", "Matrix", "Array"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(m·n)",
}


def REFERENCE(heights):
    if not heights or not heights[0]:
        return []
    m, n = len(heights), len(heights[0])

    def bfs(starts):
        visited = [[False] * n for _ in range(m)]
        q = deque()
        for r, c in starts:
            if not visited[r][c]:
                visited[r][c] = True
                q.append((r, c))
        while q:
            r, c = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if (0 <= nr < m and 0 <= nc < n and not visited[nr][nc]
                        and heights[nr][nc] >= heights[r][c]):
                    visited[nr][nc] = True
                    q.append((nr, nc))
        return visited

    pac_starts = [(0, c) for c in range(n)] + [(r, 0) for r in range(m)]
    atl_starts = [(m - 1, c) for c in range(n)] + [(r, n - 1) for r in range(m)]
    pac = bfs(pac_starts)
    atl = bfs(atl_starts)
    return [[r, c] for r in range(m) for c in range(n) if pac[r][c] and atl[r][c]]


register(PAYLOAD, REFERENCE)
