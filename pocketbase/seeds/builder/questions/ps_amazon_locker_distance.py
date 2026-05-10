"""Amazon Locker Distance — Medium. Multi-Source BFS.

Distance from each cell to the nearest locker. Naive: BFS from each
cell or each locker. Optimal: multi-source BFS from all lockers
simultaneously. O(M·N)."""
from builder.registry import register


PAYLOAD = {
    "title": "Amazon Locker Distance (Multi-Source BFS)",
    "difficulty": "Medium",
    "description": (
        "Given a city as an `m × n` grid and a list of locker positions, return a 2D array of "
        "**Manhattan distances** to the nearest locker. Movement is 4-directional, and each step "
        "between neighbouring cells counts as 1 unit.\n\n"
        "Lockers are given as `[row, col]` pairs. Use the same `[row, col]` convention in the "
        "output grid.\n\n"
        "If there are no lockers, every cell's distance is `-1`.\n\n"
        "**Example**\n\n"
        "Input:\n"
        "```\n"
        "m = 3, n = 4, lockers = [[0, 0], [2, 3]]\n"
        "```\n"
        "Output:\n"
        "```\n"
        "[[0, 1, 2, 2],\n"
        " [1, 2, 2, 1],\n"
        " [2, 2, 1, 0]]\n"
        "```\n\n"
        "Lockers sit at the top-left `[0, 0]` and bottom-right `[2, 3]` corners; each cell holds the "
        "minimum Manhattan distance to either locker."
    ),
    "hints": [
        "Brute force: BFS from each cell to find the nearest locker. O(M²N²). Reject for any non-trivial grid.",
        "Better brute force: BFS from each locker, take min. O(L · M · N). Still wasteful.",
        "Optimal: SEED the BFS queue with ALL lockers simultaneously, distance 0. Walk outwards level by level. Each cell's first-discovery distance is the shortest. O(M·N).",
        "This is the same trick as 'rotting oranges' / '01 matrix' — multi-source BFS.",
        "Edge cases: no lockers (all -1), every cell is a locker (all 0), single-row / single-column grid.",
    ],
    "constraints": [
        "1 <= m, n <= 1000",
        "0 <= |lockers| <= m·n",
    ],
    "starter_code": {
        "python": "def locker_distance(m, n, lockers):\n    # Your code here\n    pass",
        "javascript": "function lockerDistance(m, n, lockers) {\n    // Your code here\n}",
        "java": "public int[][] lockerDistance(int m, int n, int[][] lockers) {\n    // Your code here\n    return new int[][]{};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(locker_distance(3, 4, [[0, 0], [2, 3]]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"m": 3, "n": 4, "lockers": [[0, 0], [2, 3]]},
         "expected": [[0, 1, 2, 2], [1, 2, 2, 1], [2, 2, 1, 0]],
         "description": "Two lockers at opposite corners — multi-source BFS picks min",
         "tags": ["basic"]},
        {"input": {"m": 2, "n": 2, "lockers": []},
         "expected": [[-1, -1], [-1, -1]],
         "description": "No lockers — every cell is -1", "tags": ["edge"]},
        {"input": {"m": 1, "n": 5, "lockers": [[0, 2]]},
         "expected": [[2, 1, 0, 1, 2]],
         "description": "Single row, locker in middle", "tags": ["edge"]},
        {"input": {"m": 3, "n": 3, "lockers": [[0, 0], [0, 1], [0, 2],
                                                  [1, 0], [1, 1], [1, 2],
                                                  [2, 0], [2, 1], [2, 2]]},
         "expected": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
         "description": "Every cell is a locker", "tags": ["edge"]},
        {"input": {"m": 1, "n": 1, "lockers": [[0, 0]]},
         "expected": [[0]],
         "description": "1x1 grid, locker present", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Multi-Source BFS (Optimal)",
            "time_complexity": "O(m · n)",
            "space_complexity": "O(m · n)",
            "description": (
                "Initialise a 2D distance array to -1. Push every locker into the BFS queue with "
                "distance 0. Pop, for each unvisited neighbour set distance = current + 1 and enqueue. "
                "All lockers expand outwards in lockstep, so the first time a cell is reached it's via "
                "the shortest path."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "def locker_distance(m, n, lockers):\n"
                    "    dist = [[-1] * n for _ in range(m)]\n"
                    "    q = deque()\n"
                    "    for r, c in lockers:\n"
                    "        if dist[r][c] == -1:\n"
                    "            dist[r][c] = 0\n"
                    "            q.append((r, c))\n"
                    "    while q:\n"
                    "        r, c = q.popleft()\n"
                    "        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n"
                    "            nr, nc = r + dr, c + dc\n"
                    "            if 0 <= nr < m and 0 <= nc < n and dist[nr][nc] == -1:\n"
                    "                dist[nr][nc] = dist[r][c] + 1\n"
                    "                q.append((nr, nc))\n"
                    "    return dist"
                ),
                "javascript": (
                    "function lockerDistance(m, n, lockers) {\n"
                    "    const dist = Array.from({length: m}, () => new Array(n).fill(-1));\n"
                    "    const q = [];\n"
                    "    for (const [r, c] of lockers) {\n"
                    "        if (dist[r][c] === -1) { dist[r][c] = 0; q.push([r, c]); }\n"
                    "    }\n"
                    "    let head = 0;\n"
                    "    while (head < q.length) {\n"
                    "        const [r, c] = q[head++];\n"
                    "        for (const [dr, dc] of [[1,0],[-1,0],[0,1],[0,-1]]) {\n"
                    "            const nr = r + dr, nc = c + dc;\n"
                    "            if (nr >= 0 && nr < m && nc >= 0 && nc < n && dist[nr][nc] === -1) {\n"
                    "                dist[nr][nc] = dist[r][c] + 1;\n"
                    "                q.push([nr, nc]);\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return dist;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. State the brute-force O(L · M · N): BFS from each locker, take min. Mention; reject.",
        "2. Reframe: 'distance to nearest locker' is solved by ONE BFS with the queue seeded by all lockers.",
        "3. Multi-source BFS: every locker starts at distance 0; the wavefront expands together.",
        "4. First-discovery distance is shortest by BFS invariant.",
        "5. Edge cases: no lockers (all -1), all cells lockers (all 0), 1xN strip.",
        "6. Follow-ups: add a locker in O(M·N) by re-running multi-source BFS from the affected region; remove a locker by re-running.",
    ],
    "tips": [
        "Don't BFS from each cell — that's M²N² and times out.",
        "Don't BFS from each locker independently and take min — that's L·M·N. Multi-source is just one BFS.",
        "Initialise distance grid to -1 (sentinel) so you can check visited and unreachable in one test.",
        "Common follow-up: 'add a locker.' Re-run BFS from just that locker; only update cells where the new distance is smaller.",
        "Common follow-up: 'remove a locker.' Cells whose nearest was that locker need recomputation. In the worst case rerun the whole multi-source BFS.",
    ],
    "companies": ["Amazon", "Microsoft", "Google"],
    "topics": ["Graph", "BFS", "Multi-Source BFS", "Grid"],
    "time_complexity": "O(m · n)",
    "space_complexity": "O(m · n)",
}


def REFERENCE(m, n, lockers):
    from collections import deque
    dist = [[-1] * n for _ in range(m)]
    q = deque()
    for r, c in lockers:
        if dist[r][c] == -1:
            dist[r][c] = 0
            q.append((r, c))
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < m and 0 <= nc < n and dist[nr][nc] == -1:
                dist[nr][nc] = dist[r][c] + 1
                q.append((nr, nc))
    return dist


register(PAYLOAD, REFERENCE)
