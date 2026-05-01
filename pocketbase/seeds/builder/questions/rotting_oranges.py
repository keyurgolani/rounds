"""Rotting Oranges — Medium. Multi-Source BFS on a Grid.

The canonical 'spread from multiple sources, count levels' question.
Single-source BFS gives you shortest path from one node; multi-source
BFS — seed the queue with *every* initial source — gives you the
shortest distance from the *nearest* source for each cell, in one
pass. Same O(m*n) cost. Recognising the pattern unlocks Walls and
Gates (LC 286), 01 Matrix (LC 542), and As Far From Land As Possible
(LC 1162).
"""
from builder.registry import register
from collections import deque


PAYLOAD = {
    "title": "Rotting Oranges",
    "difficulty": "Medium",
    "description": (
        "You are given an `m x n` `grid` where each cell can have one of three values:\n\n"
        "- `0` representing an empty cell,\n"
        "- `1` representing a fresh orange, or\n"
        "- `2` representing a rotten orange.\n\n"
        "Every minute, any fresh orange that is **4-directionally adjacent** to a rotten orange becomes "
        "rotten.\n\n"
        "Return the **minimum number of minutes** that must elapse until no cell has a fresh orange. "
        "If this is impossible, return `-1`.\n\n"
        "**Example 1:**\n"
        "- Input: `grid = [[2,1,1],[1,1,0],[0,1,1]]`\n"
        "- Output: `4`\n"
        "- Explanation: The rot spreads outward from `(0,0)` and reaches the bottom-right fresh orange "
        "after 4 minutes.\n\n"
        "**Example 2:**\n"
        "- Input: `grid = [[2,1,1],[0,1,1],[1,0,1]]`\n"
        "- Output: `-1`\n"
        "- Explanation: The fresh orange at `(2,0)` is isolated by empty cells — it can never rot.\n\n"
        "**Example 3:**\n"
        "- Input: `grid = [[0,2]]`\n"
        "- Output: `0`\n"
        "- Explanation: There are no fresh oranges, so no time elapses."
    ),
    "hints": [
        "This is a shortest-distance-on-a-grid problem in disguise. Each minute is one BFS layer; you "
        "want the *last* layer reached.",
        "Multi-source BFS: seed the queue with **every** initial rotten orange, all at distance 0. "
        "Then expand layer by layer. The total elapsed minutes equal the BFS depth at termination.",
        "Track the count of fresh oranges up front. Decrement it every time you rot a new one. If "
        "fresh > 0 after BFS finishes, some orange was unreachable — return -1.",
        "Process the queue *one layer at a time* (snapshot the queue size before each minute) so you "
        "can increment the minute counter after each layer flushes.",
        "Edge case: zero fresh oranges at the start → answer is 0, regardless of how many rotten "
        "oranges there are. Handle this before kicking off BFS, or your minute counter will overshoot.",
    ],
    "constraints": [
        "m == grid.length",
        "n == grid[i].length",
        "1 <= m, n <= 10",
        "grid[i][j] is 0, 1, or 2",
    ],
    "starter_code": {
        "python": "def oranges_rotting(grid):\n    # Your code here\n    pass",
        "javascript": "function orangesRotting(grid) {\n    // Your code here\n}",
        "java": "public int orangesRotting(int[][] grid) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[2,1,1],[1,1,0],[0,1,1]],\n"
            "        [[2,1,1],[0,1,1],[1,0,1]],\n"
            "        [[0,2]],\n"
            "    ]\n"
            "    for g in cases:\n"
            "        print(f\"oranges_rotting -> {oranges_rotting([row[:] for row in g])}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const cases = [\n"
            "    [[2,1,1],[1,1,0],[0,1,1]],\n"
            "    [[2,1,1],[0,1,1],[1,0,1]],\n"
            "    [[0,2]],\n"
            "];\n"
            "cases.forEach(g => console.log(`orangesRotting =`, orangesRotting(g.map(r => r.slice()))));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] grid = {{2,1,1},{1,1,0},{0,1,1}};\n"
            "        System.out.println(s.orangesRotting(grid));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"grid": [[2, 1, 1], [1, 1, 0], [0, 1, 1]]}, "expected": 4,
         "description": "Classic LC example — single rotten source spreads to fill the grid in 4 minutes",
         "tags": ["basic"]},
        {"input": {"grid": [[2, 1, 1], [0, 1, 1], [1, 0, 1]]}, "expected": -1,
         "description": "Isolated fresh orange at (2,0) — impossible to rot", "tags": ["basic"]},
        {"input": {"grid": [[0, 2]]}, "expected": 0,
         "description": "No fresh oranges — zero minutes elapse", "tags": ["edge"]},
        {"input": {"grid": [[0, 0, 0], [0, 0, 0]]}, "expected": 0,
         "description": "All empty — no fresh, no rotten, answer is 0", "tags": ["edge"]},
        {"input": {"grid": [[2, 2, 2], [2, 2, 2]]}, "expected": 0,
         "description": "All rotten — no fresh remain, answer is 0", "tags": ["edge"]},
        {"input": {"grid": [[1]]}, "expected": -1,
         "description": "Single fresh orange, no rotten — impossible", "tags": ["edge"]},
        {"input": {"grid": [[2]]}, "expected": 0,
         "description": "Single rotten orange — no work to do", "tags": ["edge"]},
        {"input": {"grid": [[0]]}, "expected": 0,
         "description": "Single empty cell", "tags": ["edge"]},
        {"input": {"grid": [[2, 1, 1, 1, 1]]}, "expected": 4,
         "description": "Single row — rot propagates left-to-right one cell per minute",
         "tags": ["tricky"]},
        {"input": {"grid": [[2, 1, 1, 1, 2]]}, "expected": 2,
         "description": "Two rotten sources at the ends — meet in the middle in 2 minutes",
         "tags": ["tricky"]},
        {"input": {"grid": [[1, 1, 1], [1, 1, 1], [1, 1, 2]]}, "expected": 4,
         "description": "Single rotten at corner — diagonal-distance 4 to opposite corner",
         "tags": ["tricky"]},
        {"input": {"grid": [[2, 1, 1], [1, 1, 1], [0, 1, 2]]}, "expected": 2,
         "description": "Two rotten corners on a 3x3 with one blocker — meet at distance 2",
         "tags": ["tricky"]},
        {"input": {"grid": [[1] * 10 for _ in range(10)][:9] + [[1] * 9 + [2]]}, "expected": 18,
         "description": "10x10 mostly fresh — single rotten at bottom-right, Manhattan reach is 9+9=18",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Multi-Source BFS (Optimal)",
            "time_complexity": "O(m*n)",
            "space_complexity": "O(m*n)",
            "description": (
                "Seed the BFS queue with every initially-rotten cell at distance 0, and count the "
                "fresh cells up front. Process the queue one layer at a time: snapshot `len(queue)`, "
                "drain exactly that many, and increment the minute counter after each layer. For each "
                "popped cell, rot its 4 neighbours that are still fresh, decrement the fresh counter, "
                "and enqueue them. Terminate when the queue is empty. If `fresh == 0`, return the "
                "minute counter; otherwise some orange was unreachable, return -1.\n\n"
                "Why multi-source works: BFS from a single source gives shortest distance from that "
                "source. BFS from a *set* of sources gives shortest distance from the *nearest* source "
                "for every cell — exactly what 'minimum minutes for the last fresh orange to rot' asks."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "def oranges_rotting(grid):\n"
                    "    if not grid or not grid[0]:\n"
                    "        return 0\n"
                    "    m, n = len(grid), len(grid[0])\n"
                    "    q = deque()\n"
                    "    fresh = 0\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            if grid[r][c] == 2:\n"
                    "                q.append((r, c))\n"
                    "            elif grid[r][c] == 1:\n"
                    "                fresh += 1\n"
                    "    if fresh == 0:\n"
                    "        return 0\n"
                    "    minutes = 0\n"
                    "    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))\n"
                    "    while q and fresh > 0:\n"
                    "        for _ in range(len(q)):\n"
                    "            r, c = q.popleft()\n"
                    "            for dr, dc in dirs:\n"
                    "                nr, nc = r + dr, c + dc\n"
                    "                if 0 <= nr < m and 0 <= nc < n and grid[nr][nc] == 1:\n"
                    "                    grid[nr][nc] = 2\n"
                    "                    fresh -= 1\n"
                    "                    q.append((nr, nc))\n"
                    "        minutes += 1\n"
                    "    return minutes if fresh == 0 else -1"
                ),
                "javascript": (
                    "function orangesRotting(grid) {\n"
                    "    if (!grid.length || !grid[0].length) return 0;\n"
                    "    const m = grid.length, n = grid[0].length;\n"
                    "    const q = [];\n"
                    "    let fresh = 0;\n"
                    "    for (let r = 0; r < m; r++)\n"
                    "        for (let c = 0; c < n; c++) {\n"
                    "            if (grid[r][c] === 2) q.push([r, c]);\n"
                    "            else if (grid[r][c] === 1) fresh++;\n"
                    "        }\n"
                    "    if (fresh === 0) return 0;\n"
                    "    const dirs = [[1,0],[-1,0],[0,1],[0,-1]];\n"
                    "    let minutes = 0, head = 0;\n"
                    "    while (head < q.length && fresh > 0) {\n"
                    "        const layerEnd = q.length;\n"
                    "        while (head < layerEnd) {\n"
                    "            const [r, c] = q[head++];\n"
                    "            for (const [dr, dc] of dirs) {\n"
                    "                const nr = r + dr, nc = c + dc;\n"
                    "                if (nr >= 0 && nr < m && nc >= 0 && nc < n && grid[nr][nc] === 1) {\n"
                    "                    grid[nr][nc] = 2;\n"
                    "                    fresh--;\n"
                    "                    q.push([nr, nc]);\n"
                    "                }\n"
                    "            }\n"
                    "        }\n"
                    "        minutes++;\n"
                    "    }\n"
                    "    return fresh === 0 ? minutes : -1;\n"
                    "}"
                ),
                "java": (
                    "public int orangesRotting(int[][] grid) {\n"
                    "    int m = grid.length, n = grid[0].length, fresh = 0;\n"
                    "    Deque<int[]> q = new ArrayDeque<>();\n"
                    "    for (int r = 0; r < m; r++)\n"
                    "        for (int c = 0; c < n; c++) {\n"
                    "            if (grid[r][c] == 2) q.offer(new int[]{r, c});\n"
                    "            else if (grid[r][c] == 1) fresh++;\n"
                    "        }\n"
                    "    if (fresh == 0) return 0;\n"
                    "    int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};\n"
                    "    int minutes = 0;\n"
                    "    while (!q.isEmpty() && fresh > 0) {\n"
                    "        int size = q.size();\n"
                    "        for (int i = 0; i < size; i++) {\n"
                    "            int[] cell = q.poll();\n"
                    "            for (int[] d : dirs) {\n"
                    "                int nr = cell[0] + d[0], nc = cell[1] + d[1];\n"
                    "                if (nr >= 0 && nr < m && nc >= 0 && nc < n && grid[nr][nc] == 1) {\n"
                    "                    grid[nr][nc] = 2;\n"
                    "                    fresh--;\n"
                    "                    q.offer(new int[]{nr, nc});\n"
                    "                }\n"
                    "            }\n"
                    "        }\n"
                    "        minutes++;\n"
                    "    }\n"
                    "    return fresh == 0 ? minutes : -1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative Simulation",
            "time_complexity": "O((m*n)^2)",
            "space_complexity": "O(1)",
            "description": (
                "Loop until nothing changes. Each pass scans the whole grid, marking every fresh "
                "neighbour of a *previously* rotten cell as 'rotting this minute' (use a placeholder "
                "value to avoid the cascade-within-a-tick bug), then converts placeholders to rotten "
                "after the scan and increments the minute counter. Stop when a pass produces no "
                "change. After the loop, scan once more for any remaining fresh oranges → return -1 "
                "if found.\n\n"
                "Worst case the rot front advances one cell per pass and each pass is O(m*n), so "
                "total is O((m*n)^2). Fine for the LC constraint of m,n <= 10, but BFS is the right "
                "answer to write. Worth knowing because it doesn't need a queue and it's the "
                "intuitive 'simulate the problem statement' baseline."
            ),
            "code": {
                "python": (
                    "def oranges_rotting(grid):\n"
                    "    if not grid or not grid[0]:\n"
                    "        return 0\n"
                    "    m, n = len(grid), len(grid[0])\n"
                    "    minutes = 0\n"
                    "    while True:\n"
                    "        changed = False\n"
                    "        # Mark cells that will rot this tick with a placeholder (3).\n"
                    "        for r in range(m):\n"
                    "            for c in range(n):\n"
                    "                if grid[r][c] != 2:\n"
                    "                    continue\n"
                    "                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n"
                    "                    nr, nc = r + dr, c + dc\n"
                    "                    if 0 <= nr < m and 0 <= nc < n and grid[nr][nc] == 1:\n"
                    "                        grid[nr][nc] = 3\n"
                    "                        changed = True\n"
                    "        if not changed:\n"
                    "            break\n"
                    "        # Promote placeholders to rotten.\n"
                    "        for r in range(m):\n"
                    "            for c in range(n):\n"
                    "                if grid[r][c] == 3:\n"
                    "                    grid[r][c] = 2\n"
                    "        minutes += 1\n"
                    "    # Any fresh remaining → impossible.\n"
                    "    for row in grid:\n"
                    "        if 1 in row:\n"
                    "            return -1\n"
                    "    return minutes"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Translate the story to graph terms: cells are nodes, 4-adjacency is edges, rotten cells are sources, fresh cells are targets. The answer is `max over fresh cells of (shortest distance to nearest source)` — or -1 if any fresh cell is unreachable.",
        "2. Multi-source BFS computes that `max-of-min-distances` in one O(m*n) pass — seed the queue with every source, expand layer by layer, the final layer count is the answer.",
        "3. Counting fresh oranges up front gives a clean termination check: after BFS, if `fresh > 0`, some target was unreachable → return -1. No second pass needed.",
        "4. The 'one layer at a time' loop pattern is the trick most candidates fumble: snapshot `len(queue)` before each minute and drain exactly that many. Mixing layers within the same minute counter inflates the answer.",
        "5. Increment `minutes` AFTER processing a layer that actually rotted something. The clean way: skip the loop entirely when `fresh == 0` at the start, then increment unconditionally per layer.",
        "6. Edge cases that bite: zero fresh (return 0 even if there are rotten), zero rotten with fresh present (return -1), single cell grids (handle via the up-front `fresh` check).",
    ],
    "tips": [
        "The 'snapshot len(queue) per layer' pattern is standard for any BFS that needs to track depth/level. Memorise it — Word Ladder, Binary Tree Level Order, Shortest Bridge all use it.",
        "Walls and Gates (LC 286) and 01 Matrix (LC 542) are the same algorithm with different framing — multi-source BFS to fill 'distance to nearest X'. Recognising the family saves time.",
        "If asked 'what if the grid is huge and mostly empty?' — same BFS, but you only enqueue rotten oranges, so cost is O(rotten + reachable_fresh), which is just O(non_zero_cells).",
        "Don't use a separate `visited` set — overwriting fresh (1) → rotten (2) is the natural 'visited' marker because you'll never revisit a rotten cell. Saves O(m*n) memory.",
        "If the interviewer asks for in-place without mutating the input, copy the grid up front — `grid = [row[:] for row in grid]`. Don't try to be clever with bitmasks on a 3-state cell.",
        "Common bug: incrementing `minutes` even when the layer rotted nothing (the queue contained only rotten cells from the *initial* seed and they had no fresh neighbours). The `fresh > 0` guard in the while condition prevents this.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Facebook", "Apple", "Bloomberg"],
    "topics": ["Graph", "BFS", "Matrix", "Array"],
    "time_complexity": "O(m*n)",
    "space_complexity": "O(m*n)",
}


def REFERENCE(grid):
    grid = [row[:] for row in grid]
    if not grid or not grid[0]:
        return 0
    m, n = len(grid), len(grid[0])
    q = deque()
    fresh = 0
    for r in range(m):
        for c in range(n):
            if grid[r][c] == 2:
                q.append((r, c))
            elif grid[r][c] == 1:
                fresh += 1
    if fresh == 0:
        return 0
    minutes = 0
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
    while q and fresh > 0:
        for _ in range(len(q)):
            r, c = q.popleft()
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < m and 0 <= nc < n and grid[nr][nc] == 1:
                    grid[nr][nc] = 2
                    fresh -= 1
                    q.append((nr, nc))
        minutes += 1
    return minutes if fresh == 0 else -1


register(PAYLOAD, REFERENCE)
