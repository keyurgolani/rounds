"""Surrounded Regions — Medium. Graph / DFS / BFS / Union-Find.

The 'reverse the question' classic. Don't try to detect surrounded
regions directly — that's painful. Instead, find every 'O' that's
*safe* (connected to a border 'O') and flip everything else. Same
DFS/BFS skeleton as Number of Islands, but the seed set is the
border instead of arbitrary cells.
"""
from builder.registry import register
from collections import deque
import copy


PAYLOAD = {
    "title": "Surrounded Regions",
    "difficulty": "Medium",
    "description": (
        "Given an `m x n` matrix `board` containing `'X'` and `'O'`, **capture all regions that are 4-"
        "directionally surrounded by `'X'`**.\n\n"
        "A region is **captured** by flipping all `'O'`s into `'X'`s in that surrounded region. A region "
        "is *not* surrounded if any of its `'O'` cells lies on the border of the board (or is connected to "
        "such a cell).\n\n"
        "You must modify the board **in-place**.\n\n"
        "**Example 1:**\n"
        "- Input:\n"
        "  ```\n"
        "  board = [\n"
        "    [\"X\",\"X\",\"X\",\"X\"],\n"
        "    [\"X\",\"O\",\"O\",\"X\"],\n"
        "    [\"X\",\"X\",\"O\",\"X\"],\n"
        "    [\"X\",\"O\",\"X\",\"X\"]\n"
        "  ]\n"
        "  ```\n"
        "- Output:\n"
        "  ```\n"
        "  [\n"
        "    [\"X\",\"X\",\"X\",\"X\"],\n"
        "    [\"X\",\"X\",\"X\",\"X\"],\n"
        "    [\"X\",\"X\",\"X\",\"X\"],\n"
        "    [\"X\",\"O\",\"X\",\"X\"]\n"
        "  ]\n"
        "  ```\n"
        "- Explanation: The interior region of three `'O'`s is fully surrounded and gets flipped. The "
        "single `'O'` on the bottom row is on the border, so it (and anything connected to it) survives.\n\n"
        "**Example 2:**\n"
        "- Input: `board = [[\"X\"]]`\n"
        "- Output: `[[\"X\"]]`\n"
        "- Explanation: A single `'X'` — nothing to flip."
    ),
    "hints": [
        "Detecting 'surrounded' directly is hard — a region might wind through the grid and you'd have to "
        "prove no cell touches the border. Reverse the question: find every 'O' that is *safe*, then flip "
        "everything else.",
        "An 'O' is safe iff it is connected (4-directionally) to a border 'O'. So seed your traversal from "
        "every 'O' on the four borders and flood-fill inward, marking each safe cell.",
        "Use a sentinel character (e.g. '#') to mark safe cells during the traversal. Final pass: '#' → 'O', "
        "everything else → 'X'. Avoids needing a separate visited set.",
        "Either DFS or BFS works for the flood. DFS is shorter; BFS avoids Python's recursion limit on a "
        "200x200 board completely filled with safe 'O's.",
        "Union-Find variant: create a virtual node `BORDER`. Union every border 'O' with `BORDER`, then "
        "union every adjacent pair of 'O' cells. Final pass: any 'O' whose root is *not* `BORDER` gets "
        "flipped to 'X'.",
    ],
    "constraints": [
        "m == board.length",
        "n == board[i].length",
        "1 <= m, n <= 200",
        "board[i][j] is 'X' or 'O'",
    ],
    "starter_code": {
        "python": "def solve(board):\n    # Modify board in-place\n    pass",
        "javascript": "function solve(board) {\n    // Modify board in-place\n}",
        "java": "public void solve(char[][] board) {\n    // Modify board in-place\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[\"X\",\"X\",\"X\",\"X\"],[\"X\",\"O\",\"O\",\"X\"],[\"X\",\"X\",\"O\",\"X\"],[\"X\",\"O\",\"X\",\"X\"]],\n"
            "        [[\"X\"]],\n"
            "        [[\"O\",\"O\"],[\"O\",\"O\"]],\n"
            "    ]\n"
            "    for b in cases:\n"
            "        board = [row[:] for row in b]\n"
            "        solve(board)\n"
            "        print(board)"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const cases = [\n"
            "    [[\"X\",\"X\",\"X\",\"X\"],[\"X\",\"O\",\"O\",\"X\"],[\"X\",\"X\",\"O\",\"X\"],[\"X\",\"O\",\"X\",\"X\"]],\n"
            "    [[\"O\",\"O\"],[\"O\",\"O\"]],\n"
            "];\n"
            "cases.forEach(b => {\n"
            "    const board = b.map(r => r.slice());\n"
            "    solve(board);\n"
            "    console.log(board);\n"
            "});"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        char[][] board = {{'X','X','X','X'},{'X','O','O','X'},{'X','X','O','X'},{'X','O','X','X'}};\n"
            "        s.solve(board);\n"
            "        for (char[] row : board) System.out.println(new String(row));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"board": [["X", "X", "X", "X"], ["X", "O", "O", "X"],
                              ["X", "X", "O", "X"], ["X", "O", "X", "X"]]},
         "expected": [["X", "X", "X", "X"], ["X", "X", "X", "X"],
                      ["X", "X", "X", "X"], ["X", "O", "X", "X"]],
         "description": "Classic LC example — interior region captured, border 'O' survives", "tags": ["basic"]},
        {"input": {"board": [["X"]]}, "expected": [["X"]],
         "description": "1x1 single 'X'", "tags": ["edge"]},
        {"input": {"board": [["O"]]}, "expected": [["O"]],
         "description": "1x1 single 'O' — entire cell is border, can't be surrounded", "tags": ["edge"]},
        {"input": {"board": [["X", "X", "X"], ["X", "X", "X"], ["X", "X", "X"]]},
         "expected": [["X", "X", "X"], ["X", "X", "X"], ["X", "X", "X"]],
         "description": "All 'X' — nothing to flip", "tags": ["edge"]},
        {"input": {"board": [["O", "O", "O"], ["O", "O", "O"], ["O", "O", "O"]]},
         "expected": [["O", "O", "O"], ["O", "O", "O"], ["O", "O", "O"]],
         "description": "All 'O' — every cell connects to the border", "tags": ["edge"]},
        {"input": {"board": [["X", "O", "X"], ["O", "O", "O"], ["X", "O", "X"]]},
         "expected": [["X", "O", "X"], ["O", "O", "O"], ["X", "O", "X"]],
         "description": "Plus-shaped region with all four arms touching the border — fully safe",
         "tags": ["tricky"]},
        {"input": {"board": [["X", "X", "X"], ["X", "O", "X"], ["X", "X", "X"]]},
         "expected": [["X", "X", "X"], ["X", "X", "X"], ["X", "X", "X"]],
         "description": "Single isolated 'O' fully surrounded — flipped", "tags": ["basic"]},
        {"input": {"board": [["X", "O", "X", "X"], ["O", "X", "O", "X"],
                              ["X", "O", "X", "O"], ["X", "X", "O", "X"]]},
         "expected": [["X", "O", "X", "X"], ["O", "X", "X", "X"],
                      ["X", "X", "X", "O"], ["X", "X", "O", "X"]],
         "description": "Multiple regions — border 'O's survive, interior singletons flipped",
         "tags": ["tricky"]},
        {"input": {"board": [["X", "X", "X", "X"], ["X", "O", "O", "X"],
                              ["X", "O", "O", "X"], ["X", "X", "X", "X"]]},
         "expected": [["X", "X", "X", "X"], ["X", "X", "X", "X"],
                      ["X", "X", "X", "X"], ["X", "X", "X", "X"]],
         "description": "2x2 interior block — fully captured", "tags": ["basic"]},
        {"input": {"board": [["O", "X", "X", "O"], ["X", "O", "O", "X"],
                              ["X", "O", "O", "X"], ["O", "X", "X", "O"]]},
         "expected": [["O", "X", "X", "O"], ["X", "X", "X", "X"],
                      ["X", "X", "X", "X"], ["O", "X", "X", "O"]],
         "description": "Corner 'O's safe; interior 2x2 'O' block surrounded and flipped",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "DFS from Borders (Optimal)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n) recursion worst case",
            "description": (
                "Reverse the question. Walk every cell on the four borders; whenever you see an 'O', DFS "
                "from it and mark every reachable 'O' as safe (use a sentinel like '#'). After the flood, "
                "do a single pass: '#' → 'O' (preserved), 'O' → 'X' (captured), 'X' stays. Each cell is "
                "visited at most a constant number of times."
            ),
            "code": {
                "python": (
                    "def solve(board):\n"
                    "    if not board or not board[0]:\n"
                    "        return\n"
                    "    m, n = len(board), len(board[0])\n"
                    "\n"
                    "    def dfs(r, c):\n"
                    "        if r < 0 or r >= m or c < 0 or c >= n or board[r][c] != 'O':\n"
                    "            return\n"
                    "        board[r][c] = '#'\n"
                    "        dfs(r + 1, c); dfs(r - 1, c); dfs(r, c + 1); dfs(r, c - 1)\n"
                    "\n"
                    "    for r in range(m):\n"
                    "        dfs(r, 0); dfs(r, n - 1)\n"
                    "    for c in range(n):\n"
                    "        dfs(0, c); dfs(m - 1, c)\n"
                    "\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            board[r][c] = 'O' if board[r][c] == '#' else 'X'"
                ),
                "javascript": (
                    "function solve(board) {\n"
                    "    if (!board.length || !board[0].length) return;\n"
                    "    const m = board.length, n = board[0].length;\n"
                    "    const dfs = (r, c) => {\n"
                    "        if (r < 0 || r >= m || c < 0 || c >= n || board[r][c] !== 'O') return;\n"
                    "        board[r][c] = '#';\n"
                    "        dfs(r+1,c); dfs(r-1,c); dfs(r,c+1); dfs(r,c-1);\n"
                    "    };\n"
                    "    for (let r = 0; r < m; r++) { dfs(r, 0); dfs(r, n-1); }\n"
                    "    for (let c = 0; c < n; c++) { dfs(0, c); dfs(m-1, c); }\n"
                    "    for (let r = 0; r < m; r++)\n"
                    "        for (let c = 0; c < n; c++)\n"
                    "            board[r][c] = board[r][c] === '#' ? 'O' : 'X';\n"
                    "}"
                ),
                "java": (
                    "public void solve(char[][] board) {\n"
                    "    if (board.length == 0 || board[0].length == 0) return;\n"
                    "    int m = board.length, n = board[0].length;\n"
                    "    for (int r = 0; r < m; r++) { dfs(board, r, 0, m, n); dfs(board, r, n-1, m, n); }\n"
                    "    for (int c = 0; c < n; c++) { dfs(board, 0, c, m, n); dfs(board, m-1, c, m, n); }\n"
                    "    for (int r = 0; r < m; r++)\n"
                    "        for (int c = 0; c < n; c++)\n"
                    "            board[r][c] = board[r][c] == '#' ? 'O' : 'X';\n"
                    "}\n"
                    "private void dfs(char[][] b, int r, int c, int m, int n) {\n"
                    "    if (r < 0 || r >= m || c < 0 || c >= n || b[r][c] != 'O') return;\n"
                    "    b[r][c] = '#';\n"
                    "    dfs(b,r+1,c,m,n); dfs(b,r-1,c,m,n); dfs(b,r,c+1,m,n); dfs(b,r,c-1,m,n);\n"
                    "}"
                ),
            },
        },
        {
            "title": "BFS from Borders",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m + n) for the queue in the worst case",
            "description": (
                "Same idea as DFS but with a queue. Seed it with every border 'O' (mark them '#' as you "
                "enqueue), then expand. Avoids Python's recursion limit on a 200x200 board where every "
                "cell is a connected 'O'."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "def solve(board):\n"
                    "    if not board or not board[0]:\n"
                    "        return\n"
                    "    m, n = len(board), len(board[0])\n"
                    "    q = deque()\n"
                    "    for r in range(m):\n"
                    "        for c in (0, n - 1):\n"
                    "            if board[r][c] == 'O':\n"
                    "                board[r][c] = '#'\n"
                    "                q.append((r, c))\n"
                    "    for c in range(n):\n"
                    "        for r in (0, m - 1):\n"
                    "            if board[r][c] == 'O':\n"
                    "                board[r][c] = '#'\n"
                    "                q.append((r, c))\n"
                    "    while q:\n"
                    "        i, j = q.popleft()\n"
                    "        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n"
                    "            ni, nj = i + di, j + dj\n"
                    "            if 0 <= ni < m and 0 <= nj < n and board[ni][nj] == 'O':\n"
                    "                board[ni][nj] = '#'\n"
                    "                q.append((ni, nj))\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            board[r][c] = 'O' if board[r][c] == '#' else 'X'"
                ),
            },
        },
        {
            "title": "Union-Find with Virtual Border Node",
            "time_complexity": "O(m·n·α(m·n))",
            "space_complexity": "O(m·n)",
            "description": (
                "Allocate one extra node BORDER at index m*n. Union every border 'O' with BORDER. Then "
                "for each interior 'O', union it with its 'O' neighbours (right and down suffice — left "
                "and up are processed earlier). Final pass: any 'O' whose root is BORDER stays 'O'; "
                "everything else becomes 'X'. Conceptually clean — every safe cell shares a single root — "
                "but constant factors are higher than DFS/BFS."
            ),
            "code": {
                "python": (
                    "def solve(board):\n"
                    "    if not board or not board[0]:\n"
                    "        return\n"
                    "    m, n = len(board), len(board[0])\n"
                    "    BORDER = m * n\n"
                    "    parent = list(range(m * n + 1))\n"
                    "\n"
                    "    def find(x):\n"
                    "        while parent[x] != x:\n"
                    "            parent[x] = parent[parent[x]]\n"
                    "            x = parent[x]\n"
                    "        return x\n"
                    "\n"
                    "    def union(a, b):\n"
                    "        ra, rb = find(a), find(b)\n"
                    "        if ra != rb:\n"
                    "            parent[ra] = rb\n"
                    "\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            if board[r][c] != 'O':\n"
                    "                continue\n"
                    "            idx = r * n + c\n"
                    "            if r == 0 or r == m - 1 or c == 0 or c == n - 1:\n"
                    "                union(idx, BORDER)\n"
                    "            if r + 1 < m and board[r + 1][c] == 'O':\n"
                    "                union(idx, (r + 1) * n + c)\n"
                    "            if c + 1 < n and board[r][c + 1] == 'O':\n"
                    "                union(idx, r * n + (c + 1))\n"
                    "\n"
                    "    border_root = find(BORDER)\n"
                    "    for r in range(m):\n"
                    "        for c in range(n):\n"
                    "            if board[r][c] == 'O' and find(r * n + c) != border_root:\n"
                    "                board[r][c] = 'X'"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Try the direct framing: 'detect surrounded regions and flip them'. Painful — you'd have to flood from each 'O' and prove no cell touches the border before flipping. Don't go down this road.",
        "2. Reverse it: identify every *safe* 'O' (connected to a border 'O'). Everything else is surrounded. This is much easier to compute.",
        "3. Seed the traversal from the four borders. Any 'O' on row 0, row m-1, col 0, or col n-1 starts a flood.",
        "4. Mark safe cells with a sentinel ('#') instead of using a separate visited set. Saves memory and lets the final pass be a single sweep.",
        "5. Final pass: '#' → 'O' (these were safe), 'O' → 'X' (these were surrounded), 'X' unchanged.",
        "6. Edge cases — 1x1 board, all 'X', all 'O', plus-shape touching all four borders — all fall out of the algorithm naturally.",
    ],
    "tips": [
        "The problem asks for an in-place modification. Don't return a new board — mutate the input. Interviewer is watching for this.",
        "Pick a sentinel that is *neither* 'X' nor 'O'. '#' or '*' or '1' all work. Don't reuse 'X' — you'd lose track of which 'X's were original vs newly flipped.",
        "Don't flood from interior 'O's looking for a border. That works but is O(m·n) per region in the worst case — degenerates to O(m²·n²) overall. Always seed from the border.",
        "Recursive DFS on a 200x200 grid filled with safe 'O's hits Python's default recursion limit (1000). Either bump it or use BFS.",
        "Closely related problems: Number of Islands (LC 200) is the same flood skeleton with a counter; Pacific Atlantic Water Flow (LC 417) also seeds from the border but with a conditional traversal; Number of Enclaves (LC 1020) is essentially this problem with a count instead of a flip.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Facebook", "Bloomberg"],
    "topics": ["Graph", "DFS", "BFS", "Union Find", "Matrix"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(m·n)",
}


def REFERENCE(board):
    board = copy.deepcopy(board)
    if not board or not board[0]:
        return board
    m, n = len(board), len(board[0])
    q = deque()
    for r in range(m):
        for c in (0, n - 1):
            if board[r][c] == 'O':
                board[r][c] = '#'
                q.append((r, c))
    for c in range(n):
        for r in (0, m - 1):
            if board[r][c] == 'O':
                board[r][c] = '#'
                q.append((r, c))
    while q:
        i, j = q.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ni, nj = i + di, j + dj
            if 0 <= ni < m and 0 <= nj < n and board[ni][nj] == 'O':
                board[ni][nj] = '#'
                q.append((ni, nj))
    for r in range(m):
        for c in range(n):
            board[r][c] = 'O' if board[r][c] == '#' else 'X'
    return board


register(PAYLOAD, REFERENCE)
