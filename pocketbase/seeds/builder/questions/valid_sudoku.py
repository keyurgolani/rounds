"""Valid Sudoku — Medium. Hash Set / Matrix.

The classic 'three sets per dimension' problem. The trick everyone
remembers afterwards is the box index formula: `(r // 3) * 3 + (c // 3)`.
Worth knowing the encoded-key variant too — collapses three sets into
one and reads cleanly in interviews.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Valid Sudoku",
    "difficulty": "Medium",
    "description": (
        "Determine if a 9x9 Sudoku **board** is valid. Only the filled cells need to be validated according to "
        "the following rules:\n\n"
        "1. Each row must contain the digits `1-9` without repetition.\n"
        "2. Each column must contain the digits `1-9` without repetition.\n"
        "3. Each of the nine 3x3 sub-boxes of the grid must contain the digits `1-9` without repetition.\n\n"
        "Empty cells are indicated by the character `'.'`. Note: a valid board (per above rules) is not "
        "necessarily solvable — only the filled cells are validated.\n\n"
        "**Example 1:**\n"
        "- Input:\n"
        "```\n"
        "board = [\n"
        "  [\"5\",\"3\",\".\",\".\",\"7\",\".\",\".\",\".\",\".\"],\n"
        "  [\"6\",\".\",\".\",\"1\",\"9\",\"5\",\".\",\".\",\".\"],\n"
        "  [\".\",\"9\",\"8\",\".\",\".\",\".\",\".\",\"6\",\".\"],\n"
        "  [\"8\",\".\",\".\",\".\",\"6\",\".\",\".\",\".\",\"3\"],\n"
        "  [\"4\",\".\",\".\",\"8\",\".\",\"3\",\".\",\".\",\"1\"],\n"
        "  [\"7\",\".\",\".\",\".\",\"2\",\".\",\".\",\".\",\"6\"],\n"
        "  [\".\",\"6\",\".\",\".\",\".\",\".\",\"2\",\"8\",\".\"],\n"
        "  [\".\",\".\",\".\",\"4\",\"1\",\"9\",\".\",\".\",\"5\"],\n"
        "  [\".\",\".\",\".\",\".\",\"8\",\".\",\".\",\"7\",\"9\"]\n"
        "]\n"
        "```\n"
        "- Output: `true`\n\n"
        "**Example 2:**\n"
        "- Input: same board as Example 1, but the top-left cell `5` is replaced with `8`.\n"
        "- Output: `false`\n"
        "- Explanation: There are now two `8`s in the left column (and in the top-left 3x3 box), so the board "
        "is invalid even though every row remains fine."
    ),
    "hints": [
        "Brute force: for every filled cell, scan its row, column, and box for duplicates → O(81 * 27) = constant, "
        "but verbose and easy to get wrong. Prefer hash sets.",
        "Maintain three arrays of nine sets: `rows[9]`, `cols[9]`, `boxes[9]`. One pass over the 81 cells.",
        "Box index formula: for cell `(r, c)`, `box = (r // 3) * 3 + (c // 3)`. Memorise this — it shows up in "
        "Sudoku Solver, Word Search variants, and any 3x3 grid problem.",
        "On each filled cell, check membership in all three sets *before* inserting. If any contains the digit, "
        "return `false`. Otherwise insert into all three.",
        "One-set variant: encode each observation as a string like `f\"{d} in row {r}\"`, `f\"{d} in col {c}\"`, "
        "`f\"{d} in box {b}\"` and add all three to a single set. If `add` would duplicate, the board is invalid.",
    ],
    "constraints": [
        "board.length == 9",
        "board[i].length == 9",
        "board[i][j] is a digit '1'-'9' or '.'",
    ],
    "starter_code": {
        "python": "def is_valid_sudoku(board):\n    # Your code here\n    pass",
        "javascript": "function isValidSudoku(board) {\n    // Your code here\n}",
        "java": "public boolean isValidSudoku(char[][] board) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    board = [\n"
            "        [\"5\",\"3\",\".\",\".\",\"7\",\".\",\".\",\".\",\".\"],\n"
            "        [\"6\",\".\",\".\",\"1\",\"9\",\"5\",\".\",\".\",\".\"],\n"
            "        [\".\",\"9\",\"8\",\".\",\".\",\".\",\".\",\"6\",\".\"],\n"
            "        [\"8\",\".\",\".\",\".\",\"6\",\".\",\".\",\".\",\"3\"],\n"
            "        [\"4\",\".\",\".\",\"8\",\".\",\"3\",\".\",\".\",\"1\"],\n"
            "        [\"7\",\".\",\".\",\".\",\"2\",\".\",\".\",\".\",\"6\"],\n"
            "        [\".\",\"6\",\".\",\".\",\".\",\".\",\"2\",\"8\",\".\"],\n"
            "        [\".\",\".\",\".\",\"4\",\"1\",\"9\",\".\",\".\",\"5\"],\n"
            "        [\".\",\".\",\".\",\".\",\"8\",\".\",\".\",\"7\",\"9\"]\n"
            "    ]\n"
            "    print(is_valid_sudoku(board))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const board = [\n"
            "    [\"5\",\"3\",\".\",\".\",\"7\",\".\",\".\",\".\",\".\"],\n"
            "    [\"6\",\".\",\".\",\"1\",\"9\",\"5\",\".\",\".\",\".\"],\n"
            "    [\".\",\"9\",\"8\",\".\",\".\",\".\",\".\",\"6\",\".\"],\n"
            "    [\"8\",\".\",\".\",\".\",\"6\",\".\",\".\",\".\",\"3\"],\n"
            "    [\"4\",\".\",\".\",\"8\",\".\",\"3\",\".\",\".\",\"1\"],\n"
            "    [\"7\",\".\",\".\",\".\",\"2\",\".\",\".\",\".\",\"6\"],\n"
            "    [\".\",\"6\",\".\",\".\",\".\",\".\",\"2\",\"8\",\".\"],\n"
            "    [\".\",\".\",\".\",\"4\",\"1\",\"9\",\".\",\".\",\"5\"],\n"
            "    [\".\",\".\",\".\",\".\",\"8\",\".\",\".\",\"7\",\"9\"]\n"
            "];\n"
            "console.log(isValidSudoku(board));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        char[][] board = {\n"
            "            {'5','3','.','.','7','.','.','.','.'},\n"
            "            {'6','.','.','1','9','5','.','.','.'},\n"
            "            {'.','9','8','.','.','.','.','6','.'},\n"
            "            {'8','.','.','.','6','.','.','.','3'},\n"
            "            {'4','.','.','8','.','3','.','.','1'},\n"
            "            {'7','.','.','.','2','.','.','.','6'},\n"
            "            {'.','6','.','.','.','.','2','8','.'},\n"
            "            {'.','.','.','4','1','9','.','.','5'},\n"
            "            {'.','.','.','.','8','.','.','7','9'}\n"
            "        };\n"
            "        System.out.println(new Solution().isValidSudoku(board));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {
            "input": {"board": [
                ["5","3",".",".","7",".",".",".","."],
                ["6",".",".","1","9","5",".",".","."],
                [".","9","8",".",".",".",".","6","."],
                ["8",".",".",".","6",".",".",".","3"],
                ["4",".",".","8",".","3",".",".","1"],
                ["7",".",".",".","2",".",".",".","6"],
                [".","6",".",".",".",".","2","8","."],
                [".",".",".","4","1","9",".",".","5"],
                [".",".",".",".","8",".",".","7","9"],
            ]},
            "expected": True,
            "description": "Classic LeetCode valid partial board",
            "tags": ["basic"],
        },
        {
            "input": {"board": [
                ["8","3",".",".","7",".",".",".","."],
                ["6",".",".","1","9","5",".",".","."],
                [".","9","8",".",".",".",".","6","."],
                ["8",".",".",".","6",".",".",".","3"],
                ["4",".",".","8",".","3",".",".","1"],
                ["7",".",".",".","2",".",".",".","6"],
                [".","6",".",".",".",".","2","8","."],
                [".",".",".","4","1","9",".",".","5"],
                [".",".",".",".","8",".",".","7","9"],
            ]},
            "expected": False,
            "description": "Classic LC invalid — duplicate 8 in left column (and top-left 3x3 box)",
            "tags": ["basic"],
        },
        {
            "input": {"board": [["." for _ in range(9)] for _ in range(9)]},
            "expected": True,
            "description": "Empty board — vacuously valid",
            "tags": ["edge"],
        },
        {
            "input": {"board": [
                ["5",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
            ]},
            "expected": True,
            "description": "Single cell filled — trivially valid",
            "tags": ["edge"],
        },
        {
            "input": {"board": [
                ["5","3",".",".","7",".",".","3","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
            ]},
            "expected": False,
            "description": "Row violation — duplicate 3 in row 0",
            "tags": ["basic"],
        },
        {
            "input": {"board": [
                ["5",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                ["5",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
            ]},
            "expected": False,
            "description": "Column violation — duplicate 5 in column 0 (different boxes)",
            "tags": ["tricky"],
        },
        {
            "input": {"board": [
                ["5",".",".",".",".",".",".",".","."],
                [".",".","5",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
                [".",".",".",".",".",".",".",".","."],
            ]},
            "expected": False,
            "description": "Box violation — duplicate 5 in top-left 3x3 box (different row/col)",
            "tags": ["tricky"],
        },
        {
            "input": {"board": [
                ["5","3","4","6","7","8","9","1","2"],
                ["6","7","2","1","9","5","3","4","8"],
                ["1","9","8","3","4","2","5","6","7"],
                ["8","5","9","7","6","1","4","2","3"],
                ["4","2","6","8","5","3","7","9","1"],
                ["7","1","3","9","2","4","8","5","6"],
                ["9","6","1","5","3","7","2","8","4"],
                ["2","8","7","4","1","9","6","3","5"],
                ["3","4","5","2","8","6","1","7","9"],
            ]},
            "expected": True,
            "description": "Fully solved valid Sudoku",
            "tags": ["large"],
        },
    ],
    "solutions": [
        {
            "title": "Sets per Row / Column / Box (Optimal)",
            "time_complexity": "O(1)",
            "space_complexity": "O(1)",
            "description": (
                "Maintain three arrays of nine sets — one set per row, per column, per 3x3 box. Walk all 81 cells "
                "once. For each filled cell `(r, c)` with digit `d`, compute `b = (r // 3) * 3 + (c // 3)` and "
                "check `d` against `rows[r]`, `cols[c]`, `boxes[b]` before inserting. Constant size grid → "
                "constant time and space."
            ),
            "code": {
                "python": (
                    "def is_valid_sudoku(board):\n"
                    "    rows = [set() for _ in range(9)]\n"
                    "    cols = [set() for _ in range(9)]\n"
                    "    boxes = [set() for _ in range(9)]\n"
                    "    for r in range(9):\n"
                    "        for c in range(9):\n"
                    "            d = board[r][c]\n"
                    "            if d == '.':\n"
                    "                continue\n"
                    "            b = (r // 3) * 3 + (c // 3)\n"
                    "            if d in rows[r] or d in cols[c] or d in boxes[b]:\n"
                    "                return False\n"
                    "            rows[r].add(d)\n"
                    "            cols[c].add(d)\n"
                    "            boxes[b].add(d)\n"
                    "    return True"
                ),
                "javascript": (
                    "function isValidSudoku(board) {\n"
                    "    const rows = Array.from({length: 9}, () => new Set());\n"
                    "    const cols = Array.from({length: 9}, () => new Set());\n"
                    "    const boxes = Array.from({length: 9}, () => new Set());\n"
                    "    for (let r = 0; r < 9; r++) {\n"
                    "        for (let c = 0; c < 9; c++) {\n"
                    "            const d = board[r][c];\n"
                    "            if (d === '.') continue;\n"
                    "            const b = Math.floor(r / 3) * 3 + Math.floor(c / 3);\n"
                    "            if (rows[r].has(d) || cols[c].has(d) || boxes[b].has(d)) return false;\n"
                    "            rows[r].add(d); cols[c].add(d); boxes[b].add(d);\n"
                    "        }\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
                "java": (
                    "public boolean isValidSudoku(char[][] board) {\n"
                    "    Set<Character>[] rows = new HashSet[9];\n"
                    "    Set<Character>[] cols = new HashSet[9];\n"
                    "    Set<Character>[] boxes = new HashSet[9];\n"
                    "    for (int i = 0; i < 9; i++) {\n"
                    "        rows[i] = new HashSet<>();\n"
                    "        cols[i] = new HashSet<>();\n"
                    "        boxes[i] = new HashSet<>();\n"
                    "    }\n"
                    "    for (int r = 0; r < 9; r++) {\n"
                    "        for (int c = 0; c < 9; c++) {\n"
                    "            char d = board[r][c];\n"
                    "            if (d == '.') continue;\n"
                    "            int b = (r / 3) * 3 + (c / 3);\n"
                    "            if (!rows[r].add(d) || !cols[c].add(d) || !boxes[b].add(d)) return false;\n"
                    "        }\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Encoded-Key Single Set",
            "time_complexity": "O(1)",
            "space_complexity": "O(1)",
            "description": (
                "Collapse the three sets into one by encoding each observation as a unique key: digit `d` at row "
                "`r` becomes `(d, 'r', r)`, at column `c` becomes `(d, 'c', c)`, in box `b` becomes "
                "`(d, 'b', b)`. Add all three keys for each filled cell. If `add` ever finds an existing key, "
                "the board is invalid. Reads cleanly in interviews."
            ),
            "code": {
                "python": (
                    "def is_valid_sudoku(board):\n"
                    "    seen = set()\n"
                    "    for r in range(9):\n"
                    "        for c in range(9):\n"
                    "            d = board[r][c]\n"
                    "            if d == '.':\n"
                    "                continue\n"
                    "            b = (r // 3) * 3 + (c // 3)\n"
                    "            keys = ((d, 'r', r), (d, 'c', c), (d, 'b', b))\n"
                    "            for k in keys:\n"
                    "                if k in seen:\n"
                    "                    return False\n"
                    "                seen.add(k)\n"
                    "    return True"
                ),
                "javascript": (
                    "function isValidSudoku(board) {\n"
                    "    const seen = new Set();\n"
                    "    for (let r = 0; r < 9; r++) {\n"
                    "        for (let c = 0; c < 9; c++) {\n"
                    "            const d = board[r][c];\n"
                    "            if (d === '.') continue;\n"
                    "            const b = Math.floor(r / 3) * 3 + Math.floor(c / 3);\n"
                    "            const keys = [`${d} r${r}`, `${d} c${c}`, `${d} b${b}`];\n"
                    "            for (const k of keys) {\n"
                    "                if (seen.has(k)) return false;\n"
                    "                seen.add(k);\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: only validate filled cells; we are not asked to solve.",
        "2. Three independent constraints — rows, cols, 3x3 boxes. Each digit must be unique within each.",
        "3. The natural data structure is three arrays of nine sets. Walk the board once.",
        "4. Box index: think of boxes laid out 3x3 themselves. `(r // 3, c // 3)` gives box coordinates; flatten "
        "with `(r // 3) * 3 + (c // 3)`.",
        "5. Check membership *before* inserting — otherwise every cell would 'collide with itself'.",
        "6. Variant: encode each (digit, dimension, index) as a single key in one set. Same logic, fewer "
        "containers, slightly more allocation.",
        "7. Edge cases: empty board (vacuously valid), single filled cell (valid), full solved board (valid).",
    ],
    "tips": [
        "Memorise the box index formula: `(r // 3) * 3 + (c // 3)`. It generalises — for an `n*n` board with "
        "`k*k` sub-boxes, use `(r // k) * k + (c // k)`.",
        "Don't forget to skip `'.'` cells — checking them as if they were a digit will give false positives.",
        "If asked the follow-up 'now solve the board', the same three-sets structure becomes your "
        "constraint store for backtracking (LC 37 — Sudoku Solver).",
        "Bit-mask variant: each row/col/box is a 9-bit integer. `mask & (1 << (d - 1))` checks; `mask |= (1 << "
        "(d - 1))` sets. Tightest constants but obscures intent for an interviewer who hasn't seen it.",
        "Watch out for off-by-one in the box index — `r * 3 + c` (without integer division) is the cell index, "
        "*not* the box index. Easy slip under pressure.",
        "Single-pass is essential: iterating three times (once per dimension) is correct but wastes work and "
        "loses you points on 'can you do it in one pass?'.",
    ],
    "companies": ["Apple", "Amazon", "Microsoft", "Uber", "Snapchat"],
    "topics": ["Array", "Hash Table", "Matrix"],
    "time_complexity": "O(1)",
    "space_complexity": "O(1)",
}


def REFERENCE(board):
    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]
    for r in range(9):
        for c in range(9):
            d = board[r][c]
            if d == '.':
                continue
            b = (r // 3) * 3 + (c // 3)
            if d in rows[r] or d in cols[c] or d in boxes[b]:
                return False
            rows[r].add(d)
            cols[c].add(d)
            boxes[b].add(d)
    return True


register(PAYLOAD, REFERENCE)
