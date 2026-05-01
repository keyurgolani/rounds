"""Word Search — Medium. Backtracking / DFS on a grid.

The canonical 'DFS on a grid with a visited set' problem. Easy to write
once you've internalised the four-direction recursion pattern, but the
two failure modes — forgetting to unmark on backtrack, or starting DFS
from every cell instead of just the matching ones — are interview
landmines. The follow-up (Word Search II) jumps in difficulty: a Trie
of all words turns repeated grid scans into a single shared traversal.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Word Search",
    "difficulty": "Medium",
    "description": (
        "Given an `m x n` grid of characters `board` and a string `word`, return `true` if `word` "
        "exists in the grid.\n\n"
        "The word can be constructed from letters of sequentially adjacent cells, where adjacent cells "
        "are horizontally or vertically neighboring. **The same letter cell may not be used more than "
        "once.**\n\n"
        "**Example 1:**\n"
        "- Input: `board = [[\"A\",\"B\",\"C\",\"E\"],[\"S\",\"F\",\"C\",\"S\"],[\"A\",\"D\",\"E\",\"E\"]]`, "
        "`word = \"ABCCED\"`\n"
        "- Output: `true`\n\n"
        "**Example 2:**\n"
        "- Input: same board, `word = \"SEE\"`\n"
        "- Output: `true`\n\n"
        "**Example 3:**\n"
        "- Input: same board, `word = \"ABCB\"`\n"
        "- Output: `false` (would require reusing the `B` cell)."
    ),
    "hints": [
        "From each cell whose letter matches `word[0]`, launch a DFS that walks neighbours in 4 directions.",
        "Track visited cells. The cleanest trick: temporarily overwrite `board[r][c]` with a sentinel (e.g. `'#'`) during the recursive call, then restore it on the way out. No extra set needed.",
        "Prune aggressively: bounds-check, letter-match, and visited-check at the top of the recursive function — return False immediately if any fails.",
        "Base case: when the index `i == len(word)`, you've matched every character. Return True.",
        "Don't forget to restore the cell on backtrack. A bug here only surfaces on certain inputs (the same letter appearing on two valid paths) and is painful to debug live.",
    ],
    "constraints": [
        "m == board.length",
        "n == board[i].length",
        "1 <= m, n <= 6",
        "1 <= word.length <= 15",
        "board and word consist of only lowercase and uppercase English letters.",
    ],
    "starter_code": {
        "python": "def exist(board, word):\n    # Your code here\n    pass",
        "javascript": "function exist(board, word) {\n    // Your code here\n}",
        "java": "public boolean exist(char[][] board, String word) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    board = [[\"A\",\"B\",\"C\",\"E\"],[\"S\",\"F\",\"C\",\"S\"],[\"A\",\"D\",\"E\",\"E\"]]\n"
            "    for w in [\"ABCCED\", \"SEE\", \"ABCB\"]:\n"
            "        print(f\"exist(board, {w!r}) = {exist(board, w)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const board = [[\"A\",\"B\",\"C\",\"E\"],[\"S\",\"F\",\"C\",\"S\"],[\"A\",\"D\",\"E\",\"E\"]];\n"
            "[\"ABCCED\", \"SEE\", \"ABCB\"].forEach(w =>\n"
            "    console.log(`exist(board, ${JSON.stringify(w)}) =`, exist(board, w))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        char[][] board = {{'A','B','C','E'},{'S','F','C','S'},{'A','D','E','E'}};\n"
            "        System.out.println(s.exist(board, \"ABCCED\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"board": [["A", "B", "C", "E"], ["S", "F", "C", "S"], ["A", "D", "E", "E"]],
                   "word": "ABCCED"}, "expected": True,
         "description": "Classic LC example — word snakes through the grid", "tags": ["basic"]},
        {"input": {"board": [["A", "B", "C", "E"], ["S", "F", "C", "S"], ["A", "D", "E", "E"]],
                   "word": "SEE"}, "expected": True,
         "description": "Short word starting mid-grid", "tags": ["basic"]},
        {"input": {"board": [["A", "B", "C", "E"], ["S", "F", "C", "S"], ["A", "D", "E", "E"]],
                   "word": "ABCB"}, "expected": False,
         "description": "Would require reusing the same `B` cell — must return False",
         "tags": ["tricky"]},
        {"input": {"board": [["A"]], "word": "A"}, "expected": True,
         "description": "1x1 grid matching a single-character word", "tags": ["edge"]},
        {"input": {"board": [["A"]], "word": "B"}, "expected": False,
         "description": "1x1 grid, no match", "tags": ["edge"]},
        {"input": {"board": [["a"]], "word": "ab"}, "expected": False,
         "description": "Word longer than the entire board — impossible", "tags": ["edge"]},
        {"input": {"board": [["A", "B"], ["C", "D"]], "word": "ABDC"}, "expected": True,
         "description": "Word forms a square loop — adjacency without revisit", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "DFS Backtracking with In-Place Visited Mark",
            "time_complexity": "O(m · n · 4^L) where L = len(word)",
            "space_complexity": "O(L) recursion depth",
            "description": (
                "From every cell, attempt to grow the match. The recursive helper takes (r, c, i) and "
                "returns True iff `word[i:]` can start at cell (r, c). Mark the cell visited by overwriting "
                "with a sentinel before recursing in 4 directions; restore the original character on the "
                "way out so the board is unchanged for the caller."
            ),
            "code": {
                "python": (
                    "def exist(board, word):\n"
                    "    rows, cols = len(board), len(board[0])\n"
                    "\n"
                    "    def dfs(r, c, i):\n"
                    "        if i == len(word):\n"
                    "            return True\n"
                    "        if r < 0 or r >= rows or c < 0 or c >= cols or board[r][c] != word[i]:\n"
                    "            return False\n"
                    "        saved = board[r][c]\n"
                    "        board[r][c] = '#'\n"
                    "        found = (dfs(r + 1, c, i + 1) or dfs(r - 1, c, i + 1)\n"
                    "                 or dfs(r, c + 1, i + 1) or dfs(r, c - 1, i + 1))\n"
                    "        board[r][c] = saved\n"
                    "        return found\n"
                    "\n"
                    "    for r in range(rows):\n"
                    "        for c in range(cols):\n"
                    "            if dfs(r, c, 0):\n"
                    "                return True\n"
                    "    return False"
                ),
                "javascript": (
                    "function exist(board, word) {\n"
                    "    const rows = board.length, cols = board[0].length;\n"
                    "    const dfs = (r, c, i) => {\n"
                    "        if (i === word.length) return true;\n"
                    "        if (r < 0 || r >= rows || c < 0 || c >= cols || board[r][c] !== word[i]) return false;\n"
                    "        const saved = board[r][c];\n"
                    "        board[r][c] = '#';\n"
                    "        const found = dfs(r + 1, c, i + 1) || dfs(r - 1, c, i + 1)\n"
                    "                   || dfs(r, c + 1, i + 1) || dfs(r, c - 1, i + 1);\n"
                    "        board[r][c] = saved;\n"
                    "        return found;\n"
                    "    };\n"
                    "    for (let r = 0; r < rows; r++)\n"
                    "        for (let c = 0; c < cols; c++)\n"
                    "            if (dfs(r, c, 0)) return true;\n"
                    "    return false;\n"
                    "}"
                ),
                "java": (
                    "public boolean exist(char[][] board, String word) {\n"
                    "    int rows = board.length, cols = board[0].length;\n"
                    "    for (int r = 0; r < rows; r++)\n"
                    "        for (int c = 0; c < cols; c++)\n"
                    "            if (dfs(board, word, r, c, 0)) return true;\n"
                    "    return false;\n"
                    "}\n"
                    "\n"
                    "private boolean dfs(char[][] board, String word, int r, int c, int i) {\n"
                    "    if (i == word.length()) return true;\n"
                    "    if (r < 0 || r >= board.length || c < 0 || c >= board[0].length\n"
                    "        || board[r][c] != word.charAt(i)) return false;\n"
                    "    char saved = board[r][c];\n"
                    "    board[r][c] = '#';\n"
                    "    boolean found = dfs(board, word, r + 1, c, i + 1) || dfs(board, word, r - 1, c, i + 1)\n"
                    "                 || dfs(board, word, r, c + 1, i + 1) || dfs(board, word, r, c - 1, i + 1);\n"
                    "    board[r][c] = saved;\n"
                    "    return found;\n"
                    "}"
                ),
            },
        },
        {
            "title": "DFS with Explicit Visited Set",
            "time_complexity": "O(m · n · 4^L)",
            "space_complexity": "O(L) for the visited set + recursion",
            "description": (
                "Same algorithm, but track visited cells in a `set` instead of mutating the board. Slightly "
                "more memory, but leaves the input pristine — preferable when the board is shared or when "
                "you want to avoid argument mutation as a matter of style."
            ),
            "code": {
                "python": (
                    "def exist(board, word):\n"
                    "    rows, cols = len(board), len(board[0])\n"
                    "    visited = set()\n"
                    "\n"
                    "    def dfs(r, c, i):\n"
                    "        if i == len(word):\n"
                    "            return True\n"
                    "        if (r < 0 or r >= rows or c < 0 or c >= cols\n"
                    "                or (r, c) in visited or board[r][c] != word[i]):\n"
                    "            return False\n"
                    "        visited.add((r, c))\n"
                    "        found = (dfs(r + 1, c, i + 1) or dfs(r - 1, c, i + 1)\n"
                    "                 or dfs(r, c + 1, i + 1) or dfs(r, c - 1, i + 1))\n"
                    "        visited.remove((r, c))\n"
                    "        return found\n"
                    "\n"
                    "    for r in range(rows):\n"
                    "        for c in range(cols):\n"
                    "            if dfs(r, c, 0):\n"
                    "                return True\n"
                    "    return False"
                ),
            },
        },
        {
            "title": "DFS with Frequency-Count Pruning",
            "time_complexity": "O(m · n · 4^L) worst case, much better in practice",
            "space_complexity": "O(L)",
            "description": (
                "Two cheap pre-checks before the DFS even starts: (1) every letter of `word` must appear at "
                "least as many times in `board` as in `word`, otherwise return False immediately; (2) if the "
                "last letter of `word` is rarer than the first letter in the board, reverse `word` — DFS "
                "starts from fewer cells. Same complexity, dramatic constant-factor wins on adversarial inputs."
            ),
            "code": {
                "python": (
                    "from collections import Counter\n"
                    "\n"
                    "def exist(board, word):\n"
                    "    rows, cols = len(board), len(board[0])\n"
                    "    board_counts = Counter(ch for row in board for ch in row)\n"
                    "    word_counts = Counter(word)\n"
                    "    for ch, cnt in word_counts.items():\n"
                    "        if board_counts[ch] < cnt:\n"
                    "            return False\n"
                    "    if board_counts[word[-1]] < board_counts[word[0]]:\n"
                    "        word = word[::-1]\n"
                    "\n"
                    "    def dfs(r, c, i):\n"
                    "        if i == len(word):\n"
                    "            return True\n"
                    "        if r < 0 or r >= rows or c < 0 or c >= cols or board[r][c] != word[i]:\n"
                    "            return False\n"
                    "        saved = board[r][c]\n"
                    "        board[r][c] = '#'\n"
                    "        found = (dfs(r + 1, c, i + 1) or dfs(r - 1, c, i + 1)\n"
                    "                 or dfs(r, c + 1, i + 1) or dfs(r, c - 1, i + 1))\n"
                    "        board[r][c] = saved\n"
                    "        return found\n"
                    "\n"
                    "    for r in range(rows):\n"
                    "        for c in range(cols):\n"
                    "            if dfs(r, c, 0):\n"
                    "                return True\n"
                    "    return False"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: 'find a path in a grid with no revisits' is a textbook DFS + backtracking problem. Don't overthink it.",
        "2. Define the recursion: `dfs(r, c, i)` returns True iff we can match `word[i:]` starting at (r, c). Base case: `i == len(word)`.",
        "3. Prune at the top of `dfs`: out of bounds, already visited, or letter mismatch — bail early. Cheap checks first.",
        "4. Mark visited *before* recursing, restore *after*. The clean trick is overwriting `board[r][c]` with a sentinel like `'#'`; equivalent and cheaper than maintaining a `set`.",
        "5. Outer loop: launch DFS from every cell. Most launches die at the first letter check, which is fine.",
        "6. Edge cases: word longer than the entire board (impossible), 1×1 board, repeated letters that tempt cell reuse — make sure your visited logic catches them.",
    ],
    "tips": [
        "The `board[r][c] = '#'` sentinel trick is cleaner than a visited set — but it mutates the input. State the trade-off and ask the interviewer if they care.",
        "Frequency-count pruning + reversing `word` when the last letter is rarer is a 5-line addition that turns the worst LC tests from TLE-adjacent to instant. Worth knowing.",
        "Time complexity is `O(m·n·4^L)` worst case — the `4^L` because each step has up to 4 unvisited neighbours. The visited mark prevents true exponential blow-up in practice.",
        "Iterative DFS with an explicit stack works but is awkward because you also need to know when to *unmark* — recursion handles the unmark naturally on stack unwind.",
        "Word Search II (LC 212) is the natural follow-up: many words to search at once. Build a Trie of all words and DFS once per cell, walking the Trie in lockstep with the grid. Single shared traversal beats running this algorithm `k` times.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg", "Facebook"],
    "topics": ["Matrix", "Backtracking", "DFS"],
    "time_complexity": "O(m · n · 4^L)",
    "space_complexity": "O(L)",
}


def REFERENCE(board, word):
    # Deep-copy the board so we never mutate the caller's input.
    board = [row[:] for row in board]
    rows, cols = len(board), len(board[0])

    def dfs(r, c, i):
        if i == len(word):
            return True
        if r < 0 or r >= rows or c < 0 or c >= cols or board[r][c] != word[i]:
            return False
        saved = board[r][c]
        board[r][c] = '#'
        found = (dfs(r + 1, c, i + 1) or dfs(r - 1, c, i + 1)
                 or dfs(r, c + 1, i + 1) or dfs(r, c - 1, i + 1))
        board[r][c] = saved
        return found

    for r in range(rows):
        for c in range(cols):
            if dfs(r, c, 0):
                return True
    return False


register(PAYLOAD, REFERENCE)
