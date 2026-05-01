"""Set Matrix Zeroes — Medium. Matrix / In-Place Markers.

The classic 'do it in O(1) extra space' interview question. The naive
mark-with-extra-arrays solution is fine and worth stating; the elegant
trick is to reuse the matrix's own first row and first column as the
mark arrays, with a single extra boolean for the first row/col itself.
Order of operations is the only place this question bites — clear all
interior cells first, then the first row, then the first column.
"""
from copy import deepcopy

from builder.registry import register


PAYLOAD = {
    "title": "Set Matrix Zeroes",
    "difficulty": "Medium",
    "description": (
        "Given an `m x n` integer matrix `matrix`, if an element is `0`, set its entire row and column "
        "to `0`. You must do it **in-place**.\n\n"
        "Follow up: A straightforward solution using `O(m + n)` extra space is acceptable, but can you "
        "devise a constant-space solution?\n\n"
        "**Example 1:**\n"
        "- Input: `matrix = [[1,1,1],[1,0,1],[1,1,1]]`\n"
        "- Output: `[[1,0,1],[0,0,0],[1,0,1]]`\n"
        "- Explanation: The single `0` at position (1,1) zeroes out row 1 and column 1.\n\n"
        "**Example 2:**\n"
        "- Input: `matrix = [[0,1,2,0],[3,4,5,2],[1,3,1,5]]`\n"
        "- Output: `[[0,0,0,0],[0,4,5,0],[0,3,1,0]]`\n"
        "- Explanation: The two zeros at (0,0) and (0,3) zero out row 0 and columns 0 and 3."
    ),
    "hints": [
        "Brute force trap: if you set a row to 0 and then look for the next 0, you'll cascade and zero everything. You need to *first identify* all zero positions, then write.",
        "Easy version: keep two boolean arrays — `zero_rows[m]` and `zero_cols[n]`. Pass 1 marks them, pass 2 writes. O(m + n) extra space, very clean to code.",
        "O(1) extra space: reuse the matrix's own first row as `zero_cols` and first column as `zero_rows`. The cell at (0,0) is shared — that's why you need a separate flag.",
        "You must remember separately whether the first row and the first column originally contained any zero, *before* you start writing markers into them. Two booleans: `first_row_has_zero`, `first_col_has_zero`.",
        "Order of writes for the O(1) version: zero out the interior (i ≥ 1, j ≥ 1) using the markers first, *then* zero the first row if its flag is set, *then* zero the first column. Reverse this order and you destroy your markers.",
    ],
    "constraints": [
        "m == matrix.length",
        "n == matrix[0].length",
        "1 <= m, n <= 200",
        "-2³¹ <= matrix[i][j] <= 2³¹ - 1",
    ],
    "starter_code": {
        "python": (
            "def set_zeroes(matrix):\n"
            "    # Modify matrix in-place, then return it.\n"
            "    pass"
        ),
        "javascript": (
            "function setZeroes(matrix) {\n"
            "    // Modify matrix in-place, then return it.\n"
            "}"
        ),
        "java": (
            "public int[][] setZeroes(int[][] matrix) {\n"
            "    // Modify matrix in-place, then return it.\n"
            "    return matrix;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[1,1,1],[1,0,1],[1,1,1]],\n"
            "        [[0,1,2,0],[3,4,5,2],[1,3,1,5]],\n"
            "    ]\n"
            "    for m in cases:\n"
            "        print(set_zeroes(m))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\n"
            "    [[1,1,1],[1,0,1],[1,1,1]],\n"
            "    [[0,1,2,0],[3,4,5,2],[1,3,1,5]],\n"
            "].forEach(m => console.log(setZeroes(m)));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] m = {{1,1,1},{1,0,1},{1,1,1}};\n"
            "        s.setZeroes(m);\n"
            "        for (int[] row : m) {\n"
            "            for (int v : row) System.out.print(v + \" \");\n"
            "            System.out.println();\n"
            "        }\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"matrix": [[0]]}, "expected": [[0]],
         "description": "1x1 zero — stays zero", "tags": ["edge"]},
        {"input": {"matrix": [[7]]}, "expected": [[7]],
         "description": "1x1 non-zero — unchanged", "tags": ["edge"]},
        {"input": {"matrix": [[1, 1, 1], [1, 0, 1], [1, 1, 1]]},
         "expected": [[1, 0, 1], [0, 0, 0], [1, 0, 1]],
         "description": "Classic 3x3 with one interior zero", "tags": ["basic"]},
        {"input": {"matrix": [[0, 1, 2, 0], [3, 4, 5, 2], [1, 3, 1, 5]]},
         "expected": [[0, 0, 0, 0], [0, 4, 5, 0], [0, 3, 1, 0]],
         "description": "Classic 3x4 with two zeros on the first row", "tags": ["basic"]},
        {"input": {"matrix": [[0, 0], [0, 0]]},
         "expected": [[0, 0], [0, 0]],
         "description": "All zeros — already saturated", "tags": ["edge"]},
        {"input": {"matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]},
         "expected": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
         "description": "No zeros — matrix unchanged", "tags": ["edge"]},
        {"input": {"matrix": [[0, 2, 3], [4, 5, 6], [7, 8, 9]]},
         "expected": [[0, 0, 0], [0, 5, 6], [0, 8, 9]],
         "description": "Zero only at (0,0) — both first row and first col cleared", "tags": ["tricky"]},
        {"input": {"matrix": [[1, 2, 3], [0, 5, 6], [7, 8, 9]]},
         "expected": [[0, 2, 3], [0, 0, 0], [0, 8, 9]],
         "description": "Zero in first column (not first row) — column 0 cleared, row 1 cleared",
         "tags": ["tricky"]},
        {"input": {"matrix": [[1, 0, 3], [4, 5, 6], [7, 8, 9]]},
         "expected": [[0, 0, 0], [4, 0, 6], [7, 0, 9]],
         "description": "Zero in first row (not first col) — row 0 cleared, column 1 cleared",
         "tags": ["tricky"]},
        {"input": {"matrix": [[0, 1], [1, 0]]},
         "expected": [[0, 0], [0, 0]],
         "description": "Both first row and first column have a zero — every cell zeroes out",
         "tags": ["tricky"]},
        {"input": {"matrix": [[1, 2, 3, 4, 5]]},
         "expected": [[1, 2, 3, 4, 5]],
         "description": "Single row, no zero — unchanged", "tags": ["edge"]},
        {"input": {"matrix": [[1], [2], [0], [4]]},
         "expected": [[0], [0], [0], [0]],
         "description": "Single column with one zero — entire column cleared", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Markers in First Row & Column (Optimal, O(1) extra)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(1)",
            "description": (
                "Reuse the matrix's own first row as the column-marker array and first column as the "
                "row-marker array. Before writing any markers, capture two booleans: whether the first "
                "row originally had a zero and whether the first column originally had a zero. Then "
                "scan interior cells (i ≥ 1, j ≥ 1); for each zero, set `matrix[i][0] = 0` and "
                "`matrix[0][j] = 0`. Now zero the interior using the markers, *then* zero the first "
                "row if its flag is set, *then* zero the first column. Order matters — touching the "
                "first row/column before the interior would corrupt the markers."
            ),
            "code": {
                "python": (
                    "def set_zeroes(matrix):\n"
                    "    m, n = len(matrix), len(matrix[0])\n"
                    "    first_row_has_zero = any(matrix[0][j] == 0 for j in range(n))\n"
                    "    first_col_has_zero = any(matrix[i][0] == 0 for i in range(m))\n"
                    "    # Mark using first row and first column\n"
                    "    for i in range(1, m):\n"
                    "        for j in range(1, n):\n"
                    "            if matrix[i][j] == 0:\n"
                    "                matrix[i][0] = 0\n"
                    "                matrix[0][j] = 0\n"
                    "    # Zero interior cells based on markers\n"
                    "    for i in range(1, m):\n"
                    "        for j in range(1, n):\n"
                    "            if matrix[i][0] == 0 or matrix[0][j] == 0:\n"
                    "                matrix[i][j] = 0\n"
                    "    # Zero first row if needed\n"
                    "    if first_row_has_zero:\n"
                    "        for j in range(n):\n"
                    "            matrix[0][j] = 0\n"
                    "    # Zero first column if needed\n"
                    "    if first_col_has_zero:\n"
                    "        for i in range(m):\n"
                    "            matrix[i][0] = 0\n"
                    "    return matrix"
                ),
                "javascript": (
                    "function setZeroes(matrix) {\n"
                    "    const m = matrix.length, n = matrix[0].length;\n"
                    "    let firstRowZero = false, firstColZero = false;\n"
                    "    for (let j = 0; j < n; j++) if (matrix[0][j] === 0) firstRowZero = true;\n"
                    "    for (let i = 0; i < m; i++) if (matrix[i][0] === 0) firstColZero = true;\n"
                    "    for (let i = 1; i < m; i++) {\n"
                    "        for (let j = 1; j < n; j++) {\n"
                    "            if (matrix[i][j] === 0) {\n"
                    "                matrix[i][0] = 0;\n"
                    "                matrix[0][j] = 0;\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    for (let i = 1; i < m; i++) {\n"
                    "        for (let j = 1; j < n; j++) {\n"
                    "            if (matrix[i][0] === 0 || matrix[0][j] === 0) matrix[i][j] = 0;\n"
                    "        }\n"
                    "    }\n"
                    "    if (firstRowZero) for (let j = 0; j < n; j++) matrix[0][j] = 0;\n"
                    "    if (firstColZero) for (let i = 0; i < m; i++) matrix[i][0] = 0;\n"
                    "    return matrix;\n"
                    "}"
                ),
                "java": (
                    "public int[][] setZeroes(int[][] matrix) {\n"
                    "    int m = matrix.length, n = matrix[0].length;\n"
                    "    boolean firstRowZero = false, firstColZero = false;\n"
                    "    for (int j = 0; j < n; j++) if (matrix[0][j] == 0) firstRowZero = true;\n"
                    "    for (int i = 0; i < m; i++) if (matrix[i][0] == 0) firstColZero = true;\n"
                    "    for (int i = 1; i < m; i++) {\n"
                    "        for (int j = 1; j < n; j++) {\n"
                    "            if (matrix[i][j] == 0) {\n"
                    "                matrix[i][0] = 0;\n"
                    "                matrix[0][j] = 0;\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    for (int i = 1; i < m; i++) {\n"
                    "        for (int j = 1; j < n; j++) {\n"
                    "            if (matrix[i][0] == 0 || matrix[0][j] == 0) matrix[i][j] = 0;\n"
                    "        }\n"
                    "    }\n"
                    "    if (firstRowZero) for (int j = 0; j < n; j++) matrix[0][j] = 0;\n"
                    "    if (firstColZero) for (int i = 0; i < m; i++) matrix[i][0] = 0;\n"
                    "    return matrix;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Auxiliary Marker Arrays (O(m + n) extra)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m + n)",
            "description": (
                "Use two boolean arrays of length m and n to remember which rows and columns contain a "
                "zero. Pass 1 fills the markers; pass 2 writes zeros into any cell whose row or column "
                "is marked. Less clever than the O(1) approach but bullet-proof, easy to reason about, "
                "and a perfectly acceptable answer if the interviewer doesn't push for constant space."
            ),
            "code": {
                "python": (
                    "def set_zeroes(matrix):\n"
                    "    m, n = len(matrix), len(matrix[0])\n"
                    "    zero_rows = [False] * m\n"
                    "    zero_cols = [False] * n\n"
                    "    for i in range(m):\n"
                    "        for j in range(n):\n"
                    "            if matrix[i][j] == 0:\n"
                    "                zero_rows[i] = True\n"
                    "                zero_cols[j] = True\n"
                    "    for i in range(m):\n"
                    "        for j in range(n):\n"
                    "            if zero_rows[i] or zero_cols[j]:\n"
                    "                matrix[i][j] = 0\n"
                    "    return matrix"
                ),
                "javascript": (
                    "function setZeroes(matrix) {\n"
                    "    const m = matrix.length, n = matrix[0].length;\n"
                    "    const zeroRows = new Array(m).fill(false);\n"
                    "    const zeroCols = new Array(n).fill(false);\n"
                    "    for (let i = 0; i < m; i++)\n"
                    "        for (let j = 0; j < n; j++)\n"
                    "            if (matrix[i][j] === 0) { zeroRows[i] = true; zeroCols[j] = true; }\n"
                    "    for (let i = 0; i < m; i++)\n"
                    "        for (let j = 0; j < n; j++)\n"
                    "            if (zeroRows[i] || zeroCols[j]) matrix[i][j] = 0;\n"
                    "    return matrix;\n"
                    "}"
                ),
                "java": (
                    "public int[][] setZeroes(int[][] matrix) {\n"
                    "    int m = matrix.length, n = matrix[0].length;\n"
                    "    boolean[] zeroRows = new boolean[m];\n"
                    "    boolean[] zeroCols = new boolean[n];\n"
                    "    for (int i = 0; i < m; i++)\n"
                    "        for (int j = 0; j < n; j++)\n"
                    "            if (matrix[i][j] == 0) { zeroRows[i] = true; zeroCols[j] = true; }\n"
                    "    for (int i = 0; i < m; i++)\n"
                    "        for (int j = 0; j < n; j++)\n"
                    "            if (zeroRows[i] || zeroCols[j]) matrix[i][j] = 0;\n"
                    "    return matrix;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Realise the obvious cascading bug: if you zero a row the moment you find a zero, the freshly-written zeros trigger more zeroing. Two passes are mandatory.",
        "2. Easiest correct solution: two boolean arrays of length m and n. Pass 1 marks; pass 2 writes. O(m + n) space, O(m·n) time.",
        "3. Push for O(1) extra space. Observation: the matrix already contains m + n cells in its first row and first column — reuse them as the marker arrays.",
        "4. The cell at (0,0) is shared by both first-row and first-col, so you can't store both signals in it. Lift one of them out into a single boolean (or two — one per axis).",
        "5. Capture `first_row_has_zero` and `first_col_has_zero` *before* you write any markers, otherwise you can't tell a real original zero from a marker you wrote yourself.",
        "6. Write order matters: zero the interior using markers first (because the markers live in the first row/col), then clear the first row, then clear the first column.",
        "7. Sanity-check edges: 1×1, single-row, single-column, all-zero, no-zero, and the 'zero on the boundary' cases — they're where the off-by-one bugs live.",
    ],
    "tips": [
        "Capture the two 'first row/col has zero' flags *first*, before you mutate anything. Reordering this is the most common bug.",
        "Walk the interior with `i ∈ [1, m)` and `j ∈ [1, n)`. The boundary is reserved for markers and gets handled at the end.",
        "When clearing using markers, check both `matrix[i][0] == 0` *and* `matrix[0][j] == 0` — either one being a marker means the cell must zero.",
        "Don't try to encode both first-row and first-col signals into `matrix[0][0]` — the two signals are independent. Use two booleans.",
        "Common follow-up: 'what if the matrix can contain a sentinel value that's already zero by accident?' Same algorithm — `0` is your fixed marker; you handle the boundary with the booleans.",
        "If asked the brute force, say 'mark zero positions in a set, then write' — O(m·n) space — before stating the O(m+n) and O(1) optimisations.",
    ],
    "companies": ["Amazon", "Microsoft", "Facebook", "Bloomberg", "Adobe", "Oracle"],
    "topics": ["Array", "Hash Table", "Matrix"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(1)",
}


def REFERENCE(matrix):
    matrix = deepcopy(matrix)
    m, n = len(matrix), len(matrix[0])
    first_row_has_zero = any(matrix[0][j] == 0 for j in range(n))
    first_col_has_zero = any(matrix[i][0] == 0 for i in range(m))
    for i in range(1, m):
        for j in range(1, n):
            if matrix[i][j] == 0:
                matrix[i][0] = 0
                matrix[0][j] = 0
    for i in range(1, m):
        for j in range(1, n):
            if matrix[i][0] == 0 or matrix[0][j] == 0:
                matrix[i][j] = 0
    if first_row_has_zero:
        for j in range(n):
            matrix[0][j] = 0
    if first_col_has_zero:
        for i in range(m):
            matrix[i][0] = 0
    return matrix


register(PAYLOAD, REFERENCE)
