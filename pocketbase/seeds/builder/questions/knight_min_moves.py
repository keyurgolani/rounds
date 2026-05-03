"""Knight Minimum Moves on Chessboard — Medium. BFS / Shortest Path.

An 8x8 board has only 64 nodes, so BFS over knight-move edges is
constant work. The problem is a clean test of BFS fundamentals:
queue discipline, visited-set management, and early termination.
"""
from collections import deque

from builder.registry import register


PAYLOAD = {
    "title": "Knight Minimum Moves on Chessboard",
    "difficulty": "Medium",
    "description": (
        "Given two squares `src` and `dest` on an 8x8 chessboard, numbered from `0` to `63`, return the minimum "
        "number of knight moves from `src` to `dest`. Square `0` is the top-left cell; square `63` is the bottom-right cell."
    ),
    "hints": [
        "This is an unweighted shortest-path problem on a small graph, so BFS is the safest approach.",
        "Convert each square number to `(row, col)` with `divmod(square, 8)`.",
        "Generate the eight legal knight offsets and ignore moves that leave the board.",
        "Return as soon as the destination is dequeued or discovered at the next distance.",
    ],
    "constraints": ["0 <= src, dest < 64"],
    "starter_code": {
        "python": "def knight_min_moves(src, dest):\n    # Your code here\n    pass",
        "javascript": "function knightMinMoves(src, dest) {\n    // Your code here\n}",
        "java": "public int knightMinMoves(int src, int dest) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(knight_min_moves(19, 36))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "console.log(knightMinMoves(19, 36));"
        ),
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"src": 19, "dest": 36}, "expected": 1,
         "description": "One-hop reachability", "tags": ["basic"]},
        {"input": {"src": 0, "dest": 1}, "expected": 3,
         "description": "Adjacent squares take three knight moves", "tags": ["tricky"]},
        {"input": {"src": 0, "dest": 0}, "expected": 0,
         "description": "Already at destination", "tags": ["edge"]},
        {"input": {"src": 0, "dest": 63}, "expected": 6,
         "description": "Opposite corners", "tags": ["edge"]},
        {"input": {"src": 7, "dest": 56}, "expected": 6,
         "description": "Other opposite corners", "tags": ["edge"]},
    ],
    "solutions": [{
        "title": "Breadth-First Search",
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "description": "The board has only 64 nodes. BFS guarantees the first time we reach `dest` is the shortest path.",
        "code": {
            "python": (
                "from collections import deque\n\n"
                "def knight_min_moves(src, dest):\n"
                "    if src == dest:\n"
                "        return 0\n"
                "    moves = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]\n"
                "    sr, sc = divmod(src, 8)\n"
                "    dr, dc = divmod(dest, 8)\n"
                "    queue = deque([(sr, sc, 0)])\n"
                "    seen = {(sr, sc)}\n"
                "    while queue:\n"
                "        r, c, dist = queue.popleft()\n"
                "        for rr, cc in moves:\n"
                "            nr, nc = r + rr, c + cc\n"
                "            if not (0 <= nr < 8 and 0 <= nc < 8) or (nr, nc) in seen:\n"
                "                continue\n"
                "            if (nr, nc) == (dr, dc):\n"
                "                return dist + 1\n"
                "            seen.add((nr, nc))\n"
                "            queue.append((nr, nc, dist + 1))"
            ),
            "javascript": (
                "function knightMinMoves(src, dest) {\n"
                "    if (src === dest) return 0;\n"
                "    const moves = [[1,2],[2,1],[2,-1],[1,-2],[-1,-2],[-2,-1],[-2,1],[-1,2]];\n"
                "    const [sr, sc] = [Math.floor(src / 8), src % 8];\n"
                "    const [dr, dc] = [Math.floor(dest / 8), dest % 8];\n"
                "    const queue = [[sr, sc, 0]];\n"
                "    const seen = new Set([sr * 8 + sc]);\n"
                "    while (queue.length) {\n"
                "        const [r, c, dist] = queue.shift();\n"
                "        for (const [rr, cc] of moves) {\n"
                "            const nr = r + rr, nc = c + cc;\n"
                "            if (nr < 0 || nr >= 8 || nc < 0 || nc >= 8) continue;\n"
                "            if (nr === dr && nc === dc) return dist + 1;\n"
                "            const key = nr * 8 + nc;\n"
                "            if (seen.has(key)) continue;\n"
                "            seen.add(key);\n"
                "            queue.push([nr, nc, dist + 1]);\n"
                "        }\n"
                "    }\n"
                "}"
            ),
        },
    }],
    "thought_process": [
        "1. Model each board square as a graph node with edges for legal knight moves.",
        "2. Because each move has equal cost, use BFS rather than Dijkstra or a formula.",
        "3. Convert square numbers to coordinates and generate legal neighbors with the eight offsets.",
        "4. Track visited squares so the search does not cycle.",
        "5. Return the BFS level when the destination is reached.",
    ],
    "tips": [
        "A formula solution exists, but BFS is simpler and less error-prone for an 8x8 board.",
        "Check `src == dest` before enqueuing neighbors.",
        "Be consistent about row/column numbering; `divmod(square, 8)` gives `(row, col)` for this numbering.",
    ],
    "companies": ["Google"],
    "topics": ["Graph", "BFS", "Shortest Path"],
    "time_complexity": "O(1)",
    "space_complexity": "O(1)",
}


def REFERENCE(src, dest):
    if src == dest:
        return 0
    moves = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
    sr, sc = divmod(src, 8)
    dr, dc = divmod(dest, 8)
    queue = deque([(sr, sc, 0)])
    seen = {(sr, sc)}
    while queue:
        r, c, dist = queue.popleft()
        for rr, cc in moves:
            nr, nc = r + rr, c + cc
            if not (0 <= nr < 8 and 0 <= nc < 8) or (nr, nc) in seen:
                continue
            if (nr, nc) == (dr, dc):
                return dist + 1
            seen.add((nr, nc))
            queue.append((nr, nc, dist + 1))
    raise ValueError("unreachable")


register(PAYLOAD, REFERENCE)
