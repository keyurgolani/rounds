"""Escape Maze With One Wall Removal — Hard. BFS / State Space.

The twist over plain BFS is that reaching the same cell with the wall
break still unused is a strictly better state than reaching it after
breaking a wall. The visited set must distinguish `(row, col, used)`
rather than just `(row, col)`, or it incorrectly prunes better paths.
"""
from collections import deque

from builder.registry import register


PAYLOAD = {
    "title": "Escape Maze With One Wall Removal",
    "difficulty": "Hard",
    "description": (
        "Given a binary maze where `0` is open and `1` is a wall, return the shortest path length from the top-left "
        "cell to the bottom-right cell when you may remove at most one wall. Path length counts both the start and end cells."
    ),
    "hints": [
        "Use BFS because every step has the same cost.",
        "The state is not just `(row, col)`; it is `(row, col, removed_wall)` because reaching a cell with the wall break still available is better.",
        "When moving into an open cell, keep the same wall-removal state.",
        "When moving into a wall, proceed only if `removed_wall` is false, and mark it true for the next state.",
        "Return the distance when the destination state is reached first.",
    ],
    "constraints": [
        "1 <= maze.length, maze[0].length <= 50",
        "maze[0][0] == 0",
        "maze[-1][-1] == 0",
    ],
    "starter_code": {
        "python": "def shortest_escape_with_one_wall_removal(maze):\n    # Your code here\n    pass",
        "javascript": "function shortestEscapeWithOneWallRemoval(maze) {\n    // Your code here\n}",
        "java": "public int shortestEscapeWithOneWallRemoval(int[][] maze) {\n    // Your code here\n    return -1;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(shortest_escape_with_one_wall_removal([[0,1,1,0],[0,0,0,1],[1,1,0,0],[1,1,1,0]]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"maze": [[0, 1, 1, 0], [0, 0, 0, 1], [1, 1, 0, 0], [1, 1, 1, 0]]}, "expected": 7,
         "description": "Must navigate around walls", "tags": ["basic"]},
        {"input": {"maze": [[0, 0, 0, 0, 0, 0], [1, 1, 1, 1, 1, 0], [0, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 1], [0, 1, 1, 1, 1, 1], [0, 0, 0, 0, 0, 0]]}, "expected": 11,
         "description": "Long corridor sample", "tags": ["basic"]},
        {"input": {"maze": [[0]]}, "expected": 1,
         "description": "Start is destination", "tags": ["edge"]},
        {"input": {"maze": [[0, 1], [1, 0]]}, "expected": 3,
         "description": "Must remove one wall", "tags": ["edge"]},
        {"input": {"maze": [[0, 0], [0, 0]]}, "expected": 3,
         "description": "No wall removal needed", "tags": ["edge"]},
    ],
    "solutions": [{
        "title": "BFS With Wall-Removal State",
        "time_complexity": "O(R * C)",
        "space_complexity": "O(R * C)",
        "description": "Search over two layers per cell: one before using the wall removal and one after using it.",
        "code": {
            "python": (
                "from collections import deque\n\n"
                "def shortest_escape_with_one_wall_removal(maze):\n"
                "    rows, cols = len(maze), len(maze[0])\n"
                "    queue = deque([(0, 0, 0, 1)])\n"
                "    seen = {(0, 0, 0)}\n"
                "    while queue:\n"
                "        r, c, used, dist = queue.popleft()\n"
                "        if r == rows - 1 and c == cols - 1:\n"
                "            return dist\n"
                "        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n"
                "            nr, nc = r + dr, c + dc\n"
                "            if not (0 <= nr < rows and 0 <= nc < cols):\n"
                "                continue\n"
                "            next_used = used + maze[nr][nc]\n"
                "            state = (nr, nc, next_used)\n"
                "            if next_used <= 1 and state not in seen:\n"
                "                seen.add(state)\n"
                "                queue.append((nr, nc, next_used, dist + 1))\n"
                "    return -1"
            ),
            "javascript": (
                "function shortestEscapeWithOneWallRemoval(maze) {\n"
                "    const rows = maze.length, cols = maze[0].length;\n"
                "    const queue = [[0, 0, 0, 1]];\n"
                "    const seen = new Set(['0,0,0']);\n"
                "    while (queue.length) {\n"
                "        const [r, c, used, dist] = queue.shift();\n"
                "        if (r === rows - 1 && c === cols - 1) return dist;\n"
                "        for (const [dr, dc] of [[1,0],[-1,0],[0,1],[0,-1]]) {\n"
                "            const nr = r + dr, nc = c + dc;\n"
                "            if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;\n"
                "            const nu = used + maze[nr][nc];\n"
                "            const key = `${nr},${nc},${nu}`;\n"
                "            if (nu <= 1 && !seen.has(key)) { seen.add(key); queue.push([nr, nc, nu, dist + 1]); }\n"
                "        }\n"
                "    }\n"
                "    return -1;\n"
                "}"
            ),
        },
    }],
    "thought_process": [
        "1. Start with shortest path in a grid: BFS from the top-left cell.",
        "2. Add the twist: reaching the same cell before breaking a wall is a different and better state than reaching it after breaking one.",
        "3. Store visited states as `(row, col, used_break)` rather than just cells.",
        "4. Expand four directions. Open cells keep the state; wall cells consume the one break if available.",
        "5. The first destination state popped from BFS has the minimum path length.",
    ],
    "tips": [
        "Do not mark a cell globally visited; that incorrectly prunes paths that arrive with the wall break unused.",
        "The path length counts cells, so initialize the start distance to 1.",
        "An alternative is two BFS distance maps: from start and from end, then combine at each wall. The stateful BFS is shorter to code.",
    ],
    "companies": ["Google"],
    "topics": ["Matrix", "Graph", "BFS", "Shortest Path"],
    "time_complexity": "O(R * C)",
    "space_complexity": "O(R * C)",
}


def REFERENCE(maze):
    rows = len(maze)
    cols = len(maze[0])
    queue = deque([(0, 0, 0, 1)])
    seen = {(0, 0, 0)}
    while queue:
        r, c, used, dist = queue.popleft()
        if r == rows - 1 and c == cols - 1:
            return dist
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            next_used = used + maze[nr][nc]
            state = (nr, nc, next_used)
            if next_used <= 1 and state not in seen:
                seen.add(state)
                queue.append((nr, nc, next_used, dist + 1))
    return -1


register(PAYLOAD, REFERENCE)
