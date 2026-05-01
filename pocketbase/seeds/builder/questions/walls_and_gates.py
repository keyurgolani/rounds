"""Walls and Gates — Medium. Multi-Source BFS on a Grid.

The canonical 'distance to nearest source' grid problem. Multi-source
BFS — seed the queue with *every* gate at distance 0 — fills each
empty room with the shortest distance to its nearest gate in a single
O(m*n) pass. Same algorithmic family as Rotting Oranges (LC 994) and
01 Matrix (LC 542). The wrong instinct is BFS/DFS *from each room*,
which is O((m*n)^2). The right instinct is BFS *from all sources at
once*.
"""
from builder.registry import register
from collections import deque
from copy import deepcopy


INF = 2147483647


PAYLOAD = {
    "title": "Walls and Gates",
    "difficulty": "Medium",
    "description": (
        "You are given an `m x n` grid `rooms` initialized with these three possible values:\n\n"
        "- `-1` — A wall or an obstacle.\n"
        "- `0` — A gate.\n"
        "- `2147483647` — Infinity (`INF`) representing an empty room. (Note: `2^31 - 1` is used so we "
        "can safely add small distances without overflow.)\n\n"
        "Fill each empty room with the **distance to its nearest gate**. If it is impossible to reach a "
        "gate, the room should remain filled with `INF`. Modify the grid **in-place**.\n\n"
        "**Example 1:**\n"
        "- Input: `rooms = [[2147483647,-1,0,2147483647],[2147483647,2147483647,2147483647,-1],"
        "[2147483647,-1,2147483647,-1],[0,-1,2147483647,2147483647]]`\n"
        "- Output: `[[3,-1,0,1],[2,2,1,-1],[1,-1,2,-1],[0,-1,3,4]]`\n"
        "- Explanation: Each empty room shows the Manhattan-style shortest path through non-wall cells "
        "to the nearest gate.\n\n"
        "**Example 2:**\n"
        "- Input: `rooms = [[-1]]`\n"
        "- Output: `[[-1]]`\n"
        "- Explanation: A single wall — nothing to fill."
    ),
    "hints": [
        "Single-source BFS gives the shortest distance from one starting cell. You want the shortest "
        "distance from the *nearest* gate for every empty room. Run BFS from **all** gates at once.",
        "Multi-source BFS: seed the queue with every cell whose value is `0` (every gate), all at "
        "distance 0. Then expand layer by layer — the first time you reach an empty room, that's the "
        "shortest distance to *some* gate, which (by BFS layering) is the nearest gate.",
        "Use the grid itself as the 'visited' marker. An empty room is `INF`; once you've assigned its "
        "distance you've also overwritten `INF`, so a future neighbour check `grid[nr][nc] == INF` "
        "naturally skips already-visited rooms. No extra `visited` set needed.",
        "Alternative: BFS or DFS from *each* empty room outward to find its nearest gate. That's "
        "O((m*n)^2) — fine to mention as the brute force, never the answer for an interview.",
        "Walls are obstacles, not sources. Skip them entirely when expanding — never enqueue a `-1`.",
    ],
    "constraints": [
        "m == rooms.length",
        "n == rooms[i].length",
        "1 <= m, n <= 250",
        "rooms[i][j] is -1, 0, or 2147483647",
    ],
    "starter_code": {
        "python": "def walls_and_gates(rooms):\n    # Modify rooms in-place\n    pass",
        "javascript": "function wallsAndGates(rooms) {\n    // Modify rooms in-place\n}",
        "java": "public void wallsAndGates(int[][] rooms) {\n    // Modify rooms in-place\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "INF = 2147483647\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[INF,-1,0,INF],[INF,INF,INF,-1],[INF,-1,INF,-1],[0,-1,INF,INF]],\n"
            "        [[0]],\n"
            "        [[-1]],\n"
            "    ]\n"
            "    for g in cases:\n"
            "        grid = [row[:] for row in g]\n"
            "        walls_and_gates(grid)\n"
            "        print(f\"walls_and_gates -> {grid}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const INF = 2147483647;\n"
            "const cases = [\n"
            "    [[INF,-1,0,INF],[INF,INF,INF,-1],[INF,-1,INF,-1],[0,-1,INF,INF]],\n"
            "    [[0]],\n"
            "    [[-1]],\n"
            "];\n"
            "cases.forEach(g => {\n"
            "    const grid = g.map(r => r.slice());\n"
            "    wallsAndGates(grid);\n"
            "    console.log('wallsAndGates =', grid);\n"
            "});"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int INF = Integer.MAX_VALUE;\n"
            "        int[][] rooms = {{INF,-1,0,INF},{INF,INF,INF,-1},{INF,-1,INF,-1},{0,-1,INF,INF}};\n"
            "        s.wallsAndGates(rooms);\n"
            "        for (int[] row : rooms) {\n"
            "            for (int v : row) System.out.print(v + \" \");\n"
            "            System.out.println();\n"
            "        }\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {
            "input": {"rooms": [
                [INF, -1, 0, INF],
                [INF, INF, INF, -1],
                [INF, -1, INF, -1],
                [0, -1, INF, INF],
            ]},
            "expected": [
                [3, -1, 0, 1],
                [2, 2, 1, -1],
                [1, -1, 2, -1],
                [0, -1, 3, 4],
            ],
            "description": "Classic LC example — two gates, walls, and reachable empties",
            "tags": ["basic"],
        },
        {
            "input": {"rooms": [[INF, INF], [INF, INF]]},
            "expected": [[INF, INF], [INF, INF]],
            "description": "No gates anywhere — every room stays INF",
            "tags": ["edge"],
        },
        {
            "input": {"rooms": [[-1, -1, INF], [-1, INF, -1], [INF, -1, -1]]},
            "expected": [[-1, -1, INF], [-1, INF, -1], [INF, -1, -1]],
            "description": "Only walls and INF — no gates, every empty room remains INF",
            "tags": ["edge"],
        },
        {
            "input": {"rooms": [[0]]},
            "expected": [[0]],
            "description": "Single gate — already complete",
            "tags": ["edge"],
        },
        {
            "input": {"rooms": [
                [0, INF, INF],
                [INF, INF, INF],
                [INF, INF, INF],
            ]},
            "expected": [
                [0, 1, 2],
                [1, 2, 3],
                [2, 3, 4],
            ],
            "description": "Single gate at corner — distances spread Manhattan-style across open grid",
            "tags": ["basic"],
        },
        {
            "input": {"rooms": [
                [0, -1, INF],
                [-1, -1, INF],
                [INF, INF, INF],
            ]},
            "expected": [
                [0, -1, INF],
                [-1, -1, INF],
                [INF, INF, INF],
            ],
            "description": "Empty rooms walled off from the only gate — they remain INF",
            "tags": ["tricky"],
        },
        {
            "input": {"rooms": [
                [0, INF, INF, INF, 0],
                [INF, INF, INF, INF, INF],
                [INF, INF, -1, INF, INF],
                [INF, INF, INF, INF, INF],
                [0, INF, INF, INF, 0],
            ]},
            "expected": [
                [0, 1, 2, 1, 0],
                [1, 2, 3, 2, 1],
                [2, 3, -1, 3, 2],
                [1, 2, 3, 2, 1],
                [0, 1, 2, 1, 0],
            ],
            "description": "Larger grid with four corner gates and a single interior wall — distances "
                           "compete from all four corners",
            "tags": ["large"],
        },
        {
            "input": {"rooms": [[0, INF, INF, 0]]},
            "expected": [[0, 1, 1, 0]],
            "description": "Single row — two gates meet in the middle",
            "tags": ["tricky"],
        },
        {
            "input": {"rooms": [[INF], [-1], [0], [-1], [INF]]},
            "expected": [[INF], [-1], [0], [-1], [INF]],
            "description": "Vertical strip — gate sandwiched by walls, both INF cells unreachable",
            "tags": ["tricky"],
        },
    ],
    "solutions": [
        {
            "title": "Multi-Source BFS (Optimal)",
            "time_complexity": "O(m*n)",
            "space_complexity": "O(m*n)",
            "description": (
                "Seed a single queue with **every** gate at distance 0. Then run standard BFS: pop a "
                "cell, look at its 4 neighbours, and for any neighbour that is still `INF`, write "
                "`grid[r][c] + 1` and enqueue it. Walls (`-1`) and already-filled cells "
                "(value < INF) are skipped naturally because we only descend into `INF` cells.\n\n"
                "Why it's correct: BFS expands in layers of equal distance from the source set. The "
                "first time any cell is reached, the layer index is its shortest distance to the "
                "*nearest* source. Writing the distance and using it as the visited marker is safe "
                "because we never revisit a non-INF cell.\n\n"
                "Why it's O(m*n): every cell is enqueued at most once (the moment it stops being "
                "INF), and each dequeue does O(1) work for 4 neighbours."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "INF = 2147483647\n"
                    "\n"
                    "def walls_and_gates(rooms):\n"
                    "    if not rooms or not rooms[0]:\n"
                    "        return\n"
                    "    m, n = len(rooms), len(rooms[0])\n"
                    "    q = deque()\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            if rooms[r][c] == 0:\n"
                    "                q.append((r, c))\n"
                    "    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))\n"
                    "    while q:\n"
                    "        r, c = q.popleft()\n"
                    "        for dr, dc in dirs:\n"
                    "            nr, nc = r + dr, c + dc\n"
                    "            if 0 <= nr < m and 0 <= nc < n and rooms[nr][nc] == INF:\n"
                    "                rooms[nr][nc] = rooms[r][c] + 1\n"
                    "                q.append((nr, nc))"
                ),
                "javascript": (
                    "function wallsAndGates(rooms) {\n"
                    "    const INF = 2147483647;\n"
                    "    if (!rooms.length || !rooms[0].length) return;\n"
                    "    const m = rooms.length, n = rooms[0].length;\n"
                    "    const q = [];\n"
                    "    for (let r = 0; r < m; r++)\n"
                    "        for (let c = 0; c < n; c++)\n"
                    "            if (rooms[r][c] === 0) q.push([r, c]);\n"
                    "    const dirs = [[1,0],[-1,0],[0,1],[0,-1]];\n"
                    "    let head = 0;\n"
                    "    while (head < q.length) {\n"
                    "        const [r, c] = q[head++];\n"
                    "        for (const [dr, dc] of dirs) {\n"
                    "            const nr = r + dr, nc = c + dc;\n"
                    "            if (nr >= 0 && nr < m && nc >= 0 && nc < n && rooms[nr][nc] === INF) {\n"
                    "                rooms[nr][nc] = rooms[r][c] + 1;\n"
                    "                q.push([nr, nc]);\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "}"
                ),
                "java": (
                    "public void wallsAndGates(int[][] rooms) {\n"
                    "    int INF = Integer.MAX_VALUE;\n"
                    "    if (rooms.length == 0 || rooms[0].length == 0) return;\n"
                    "    int m = rooms.length, n = rooms[0].length;\n"
                    "    Deque<int[]> q = new ArrayDeque<>();\n"
                    "    for (int r = 0; r < m; r++)\n"
                    "        for (int c = 0; c < n; c++)\n"
                    "            if (rooms[r][c] == 0) q.offer(new int[]{r, c});\n"
                    "    int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};\n"
                    "    while (!q.isEmpty()) {\n"
                    "        int[] cell = q.poll();\n"
                    "        int r = cell[0], c = cell[1];\n"
                    "        for (int[] d : dirs) {\n"
                    "            int nr = r + d[0], nc = c + d[1];\n"
                    "            if (nr >= 0 && nr < m && nc >= 0 && nc < n && rooms[nr][nc] == INF) {\n"
                    "                rooms[nr][nc] = rooms[r][c] + 1;\n"
                    "                q.offer(new int[]{nr, nc});\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "DFS From Every Gate",
            "time_complexity": "O(m*n)",
            "space_complexity": "O(m*n)",
            "description": (
                "Walk DFS outward from every gate, passing the current distance. At each cell, if the "
                "incoming distance is shorter than the value stored there, overwrite and recurse to "
                "the 4 neighbours with `distance + 1`. The visited skip is implicit: once a cell holds "
                "a value smaller-or-equal to the new candidate, we stop descending — that prunes the "
                "exponential branching.\n\n"
                "This *looks* like 'DFS from each room' (the bad O((m*n)^2) approach) but it's the "
                "opposite: DFS from each *gate*, with monotonic-improvement pruning. Total work is "
                "still O(m*n) amortised because each cell is finalised at most once per direction it "
                "improves from, and the values strictly decrease toward their final distance.\n\n"
                "Strictly worse than BFS in practice — DFS doesn't guarantee monotonic distance "
                "ordering, so cells get rewritten as shorter paths arrive. BFS is the right answer; "
                "DFS is worth knowing as a 'why is BFS the natural fit here' contrast."
            ),
            "code": {
                "python": (
                    "INF = 2147483647\n"
                    "\n"
                    "def walls_and_gates(rooms):\n"
                    "    if not rooms or not rooms[0]:\n"
                    "        return\n"
                    "    m, n = len(rooms), len(rooms[0])\n"
                    "\n"
                    "    def dfs(r, c, d):\n"
                    "        if r < 0 or r >= m or c < 0 or c >= n or rooms[r][c] < d:\n"
                    "            return\n"
                    "        rooms[r][c] = d\n"
                    "        dfs(r + 1, c, d + 1)\n"
                    "        dfs(r - 1, c, d + 1)\n"
                    "        dfs(r, c + 1, d + 1)\n"
                    "        dfs(r, c - 1, d + 1)\n"
                    "\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            if rooms[r][c] == 0:\n"
                    "                dfs(r, c, 0)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the family: 'distance to nearest X for every cell' on a 4-connected grid → multi-source BFS. Same shape as Rotting Oranges (LC 994), 01 Matrix (LC 542), As Far From Land (LC 1162).",
        "2. The naive instinct is 'BFS from each empty room outward to find its nearest gate'. That's O((m*n)^2) — 62.5M ops on a 250x250 grid. State it, then discard.",
        "3. Flip the direction: BFS *from the gates* outward instead of *to* the gates. One BFS, all gates seeded simultaneously at distance 0.",
        "4. Multi-source BFS guarantees: when you first reach a cell, you've reached it via the shortest path from *some* source — and because all sources started together at distance 0, that's the *nearest* source.",
        "5. Use the grid value itself as the visited marker. Empty rooms are `INF`; only descend into cells that are still `INF`. Walls (`-1`) are skipped because they're not `INF`. Already-assigned rooms have a value < INF and are skipped too.",
        "6. Unreachable empties (walled off) stay `INF` automatically — BFS just never visits them. No special handling needed.",
        "7. Edge cases: no gates (every empty stays INF), all walls (return immediately, nothing changes), single gate, single cell.",
    ],
    "tips": [
        "Recognising the multi-source BFS pattern is the whole interview. Once you see 'distance to nearest X', the algorithm writes itself.",
        "Don't allocate a separate `dist` matrix and then copy back at the end. Mutating `rooms` directly is the natural approach because INF doubles as 'unvisited'.",
        "If the interviewer disallows mutating the input, deep-copy `rooms = [row[:] for row in rooms]` and mutate the copy. Don't try to track distances in a separate map keyed by `(r,c)` — that's a 4x memory blowup for no benefit.",
        "If asked 'what about diagonals?' — change the `dirs` tuple to 8 entries. The algorithm is unchanged. The distance metric becomes Chebyshev instead of Manhattan-through-walls.",
        "Common bug: enqueuing walls or already-visited cells. The single guard `rooms[nr][nc] == INF` handles both — skip everything else.",
        "Common follow-up — 'what if some rooms have variable cost (like a weight)?' That's no longer BFS; you need Dijkstra. State the upgrade explicitly: priority queue keyed by distance, relax on extraction.",
        "If the grid is sparse (few empties, few gates), the BFS cost is O(reachable empties + gates), not the full m*n. Mention as an extension if asked about huge grids.",
    ],
    "companies": ["Facebook", "Google", "Amazon", "Microsoft", "Uber", "Bloomberg"],
    "topics": ["Graph", "BFS", "Matrix", "Array"],
    "time_complexity": "O(m*n)",
    "space_complexity": "O(m*n)",
}


def REFERENCE(rooms):
    rooms = deepcopy(rooms)
    if not rooms or not rooms[0]:
        return rooms
    m, n = len(rooms), len(rooms[0])
    q = deque()
    for r in range(m):
        for c in range(n):
            if rooms[r][c] == 0:
                q.append((r, c))
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
    while q:
        r, c = q.popleft()
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < m and 0 <= nc < n and rooms[nr][nc] == INF:
                rooms[nr][nc] = rooms[r][c] + 1
                q.append((nr, nc))
    return rooms


register(PAYLOAD, REFERENCE)
