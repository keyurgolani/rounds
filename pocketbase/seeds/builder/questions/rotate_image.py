"""Rotate Image — Medium. Matrix / In-Place Manipulation.

The classic 'rotate n×n matrix 90° clockwise' problem. Two canonical
solutions: (1) transpose then reverse each row — concise, O(1) extra
space, works because the composition equals a 90° rotation; (2) the
layer-by-layer 4-cycle, which is the 'rotate without ever knowing the
trick' approach — important to be able to derive from first principles
when the interviewer asks 'what if you couldn't transpose?'.
"""
from copy import deepcopy

from builder.registry import register


PAYLOAD = {
    "title": "Rotate Image",
    "difficulty": "Medium",
    "description": (
        "You are given an `n x n` 2D `matrix` representing an image. Rotate the image by **90 degrees "
        "(clockwise)**.\n\n"
        "You have to rotate the image **in-place**, which means you must modify the input 2D matrix "
        "directly. **Do not** allocate another 2D matrix and do the rotation. (For this test runner, "
        "return the rotated matrix.)\n\n"
        "**Example 1:**\n"
        "- Input: `matrix = [[1,2,3],[4,5,6],[7,8,9]]`\n"
        "- Output: `[[7,4,1],[8,5,2],[9,6,3]]`\n"
        "- Explanation: The top row `[1,2,3]` becomes the right column; the left column `[1,4,7]` "
        "becomes the top row reversed → `[7,4,1]`.\n\n"
        "**Example 2:**\n"
        "- Input: `matrix = [[5,1,9,11],[2,4,8,10],[13,3,6,7],[15,14,12,16]]`\n"
        "- Output: `[[15,13,2,5],[14,3,4,1],[12,6,8,9],[16,7,10,11]]`\n"
        "- Explanation: Each of the 4 concentric layers rotates independently; corners cycle in groups of 4."
    ),
    "hints": [
        "The cleanest in-place trick: **transpose** the matrix (swap `M[i][j]` with `M[j][i]` for `i < j`), then **reverse each row**. The composition equals a 90° clockwise rotation.",
        "Why transpose + reverse works: transpose maps `(i, j) → (j, i)` (reflection across the main diagonal); reversing each row maps `(j, i) → (j, n−1−i)`. That's exactly the 90° CW map `(i, j) → (j, n−1−i)`.",
        "Alternative: rotate **layer by layer**. Outer ring first, then the next ring in, etc. There are `n // 2` layers. For a layer of side `k`, you do `k − 1` 4-element cyclic rotations.",
        "The 4-element cycle: for the top-left index `(top, left + offset)`, the four positions that swap are `top-row`, `right-column`, `bottom-row`, `left-column`. Save one in a temp, shift the other three, drop the temp into the empty slot.",
        "Off-by-one watch: outer loop runs `i` from `0` to `n // 2` (exclusive). Inner loop runs `j` from `i` to `n − 1 − i` (exclusive). Get this wrong and you'll either skip cells or rotate them twice (which equals 180°).",
    ],
    "constraints": [
        "n == matrix.length == matrix[i].length",
        "1 <= n <= 20",
        "-1000 <= matrix[i][j] <= 1000",
    ],
    "starter_code": {
        "python": "def rotate(matrix):\n    # Rotate the matrix 90° clockwise in-place, then return it.\n    pass",
        "javascript": "function rotate(matrix) {\n    // Rotate the matrix 90° clockwise in-place, then return it.\n}",
        "java": "public int[][] rotate(int[][] matrix) {\n    // Rotate the matrix 90° clockwise in-place, then return it.\n    return matrix;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[1,2,3],[4,5,6],[7,8,9]],\n"
            "        [[5,1,9,11],[2,4,8,10],[13,3,6,7],[15,14,12,16]],\n"
            "    ]\n"
            "    for m in cases:\n"
            "        print(rotate([row[:] for row in m]))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\n"
            "    [[1,2,3],[4,5,6],[7,8,9]],\n"
            "    [[5,1,9,11],[2,4,8,10],[13,3,6,7],[15,14,12,16]],\n"
            "].forEach(m => console.log(rotate(m.map(r => r.slice()))));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] m = {{1,2,3},{4,5,6},{7,8,9}};\n"
            "        int[][] out = s.rotate(m);\n"
            "        for (int[] row : out) {\n"
            "            for (int v : row) System.out.print(v + \" \");\n"
            "            System.out.println();\n"
            "        }\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"matrix": [[1]]}, "expected": [[1]],
         "description": "1×1 — rotation is a no-op", "tags": ["edge"]},
        {"input": {"matrix": [[1, 2], [3, 4]]}, "expected": [[3, 1], [4, 2]],
         "description": "2×2 — smallest non-trivial case", "tags": ["edge"]},
        {"input": {"matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]},
         "expected": [[7, 4, 1], [8, 5, 2], [9, 6, 3]],
         "description": "3×3 classic LeetCode example 1", "tags": ["basic"]},
        {"input": {"matrix": [[5, 1, 9, 11], [2, 4, 8, 10], [13, 3, 6, 7], [15, 14, 12, 16]]},
         "expected": [[15, 13, 2, 5], [14, 3, 4, 1], [12, 6, 8, 9], [16, 7, 10, 11]],
         "description": "4×4 LeetCode example 2 — two concentric layers", "tags": ["basic"]},
        {"input": {"matrix": [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10], [11, 12, 13, 14, 15],
                              [16, 17, 18, 19, 20], [21, 22, 23, 24, 25]]},
         "expected": [[21, 16, 11, 6, 1], [22, 17, 12, 7, 2], [23, 18, 13, 8, 3],
                      [24, 19, 14, 9, 4], [25, 20, 15, 10, 5]],
         "description": "5×5 — odd side, center fixed point", "tags": ["basic"]},
        {"input": {"matrix": [[1, 1, 1], [2, 2, 2], [3, 3, 3]]},
         "expected": [[3, 2, 1], [3, 2, 1], [3, 2, 1]],
         "description": "3×3 with row-duplicates — verifies column ordering", "tags": ["tricky"]},
        {"input": {"matrix": [[-1, -2, -3], [-4, -5, -6], [-7, -8, -9]]},
         "expected": [[-7, -4, -1], [-8, -5, -2], [-9, -6, -3]],
         "description": "3×3 negatives — sign handling sanity", "tags": ["tricky"]},
        {"input": {"matrix": [[0, 0, 0], [0, 0, 0], [0, 0, 0]]},
         "expected": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
         "description": "3×3 all zeros — invariant under rotation", "tags": ["edge"]},
        {"input": {"matrix": [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12], [13, 14, 15, 16, 17, 18],
                              [19, 20, 21, 22, 23, 24], [25, 26, 27, 28, 29, 30],
                              [31, 32, 33, 34, 35, 36]]},
         "expected": [[31, 25, 19, 13, 7, 1], [32, 26, 20, 14, 8, 2], [33, 27, 21, 15, 9, 3],
                      [34, 28, 22, 16, 10, 4], [35, 29, 23, 17, 11, 5], [36, 30, 24, 18, 12, 6]],
         "description": "6×6 — three concentric layers, full layer-by-layer stress", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Transpose + Reverse Rows (Optimal)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "Transpose the matrix in place (swap `M[i][j]` with `M[j][i]` for `i < j`), then reverse "
                "each row. The composition `(i, j) → (j, i) → (j, n−1−i)` is exactly the 90° clockwise "
                "rotation map. Two clean passes, no off-by-one fiddling, no temp arrays."
            ),
            "code": {
                "python": (
                    "def rotate(matrix):\n"
                    "    n = len(matrix)\n"
                    "    # Transpose: reflect across the main diagonal.\n"
                    "    for i in range(n):\n"
                    "        for j in range(i + 1, n):\n"
                    "            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]\n"
                    "    # Reverse each row.\n"
                    "    for row in matrix:\n"
                    "        row.reverse()\n"
                    "    return matrix"
                ),
                "javascript": (
                    "function rotate(matrix) {\n"
                    "    const n = matrix.length;\n"
                    "    for (let i = 0; i < n; i++) {\n"
                    "        for (let j = i + 1; j < n; j++) {\n"
                    "            [matrix[i][j], matrix[j][i]] = [matrix[j][i], matrix[i][j]];\n"
                    "        }\n"
                    "    }\n"
                    "    for (const row of matrix) row.reverse();\n"
                    "    return matrix;\n"
                    "}"
                ),
                "java": (
                    "public int[][] rotate(int[][] matrix) {\n"
                    "    int n = matrix.length;\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        for (int j = i + 1; j < n; j++) {\n"
                    "            int t = matrix[i][j];\n"
                    "            matrix[i][j] = matrix[j][i];\n"
                    "            matrix[j][i] = t;\n"
                    "        }\n"
                    "    }\n"
                    "    for (int[] row : matrix) {\n"
                    "        for (int l = 0, r = n - 1; l < r; l++, r--) {\n"
                    "            int t = row[l]; row[l] = row[r]; row[r] = t;\n"
                    "        }\n"
                    "    }\n"
                    "    return matrix;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Layer-by-Layer 4-Cycle",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "Walk the matrix one concentric ring at a time. For each ring (layer `i` from `0` to "
                "`n // 2`), perform `n − 1 − 2i` four-way swaps that cycle one element through its top, "
                "right, bottom, and left mirror positions. This is the 'no-trick' derivation — useful when "
                "the interviewer asks you to rotate a matrix without using transpose, or asks you to "
                "rotate by 90° counter-clockwise (just flip the cycle direction)."
            ),
            "code": {
                "python": (
                    "def rotate(matrix):\n"
                    "    n = len(matrix)\n"
                    "    for i in range(n // 2):\n"
                    "        for j in range(i, n - 1 - i):\n"
                    "            # 4-way cycle: top-left ← bottom-left ← bottom-right ← top-right ← top-left\n"
                    "            tmp = matrix[i][j]\n"
                    "            matrix[i][j] = matrix[n - 1 - j][i]\n"
                    "            matrix[n - 1 - j][i] = matrix[n - 1 - i][n - 1 - j]\n"
                    "            matrix[n - 1 - i][n - 1 - j] = matrix[j][n - 1 - i]\n"
                    "            matrix[j][n - 1 - i] = tmp\n"
                    "    return matrix"
                ),
                "javascript": (
                    "function rotate(matrix) {\n"
                    "    const n = matrix.length;\n"
                    "    for (let i = 0; i < Math.floor(n / 2); i++) {\n"
                    "        for (let j = i; j < n - 1 - i; j++) {\n"
                    "            const tmp = matrix[i][j];\n"
                    "            matrix[i][j] = matrix[n - 1 - j][i];\n"
                    "            matrix[n - 1 - j][i] = matrix[n - 1 - i][n - 1 - j];\n"
                    "            matrix[n - 1 - i][n - 1 - j] = matrix[j][n - 1 - i];\n"
                    "            matrix[j][n - 1 - i] = tmp;\n"
                    "        }\n"
                    "    }\n"
                    "    return matrix;\n"
                    "}"
                ),
                "java": (
                    "public int[][] rotate(int[][] matrix) {\n"
                    "    int n = matrix.length;\n"
                    "    for (int i = 0; i < n / 2; i++) {\n"
                    "        for (int j = i; j < n - 1 - i; j++) {\n"
                    "            int tmp = matrix[i][j];\n"
                    "            matrix[i][j] = matrix[n - 1 - j][i];\n"
                    "            matrix[n - 1 - j][i] = matrix[n - 1 - i][n - 1 - j];\n"
                    "            matrix[n - 1 - i][n - 1 - j] = matrix[j][n - 1 - i];\n"
                    "            matrix[j][n - 1 - i] = tmp;\n"
                    "        }\n"
                    "    }\n"
                    "    return matrix;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Clarify: 90° clockwise, in-place, square matrix. Confirm 'in-place' means O(1) extra space (no second matrix).",
        "2. Brute force baseline: allocate `result[n][n]`, set `result[j][n−1−i] = matrix[i][j]`. O(n²) time, O(n²) space. State it, then improve.",
        "3. Spot the geometric identity: 90° CW = transpose ∘ reverse-each-row. That's the 'trick' answer — concise and bug-resistant.",
        "4. If forbidden from using the trick (or asked to derive it), fall back to layer-by-layer. Each ring is independent; within a ring, every cell is one of 4 cyclic positions.",
        "5. Index discipline for layer-by-layer: outer `i` in `[0, n // 2)`; inner `j` in `[i, n − 1 − i)`. The four indices in the cycle are `(i, j)`, `(n−1−j, i)`, `(n−1−i, n−1−j)`, `(j, n−1−i)`.",
        "6. Edge cases: 1×1 matrix (no cells to rotate, both methods naturally no-op); 2×2 (one 4-cycle); odd `n` (the center cell is its own image — both methods skip it correctly).",
        "7. Verify on the 4×4 LeetCode example by hand for at least the outer layer — it's the fastest way to catch an off-by-one.",
    ],
    "tips": [
        "Transpose + reverse-rows is the 'right' answer for an interview — short, hard to get wrong, easy to explain. Memorise the geometric reason so you don't sound like you're parroting a trick.",
        "If asked for 90° **counter-clockwise**: either (a) transpose then reverse each *column* (equivalently, reverse rows *first*, then transpose), or (b) reverse the 4-cycle direction.",
        "180° rotation = reverse each row, then reverse the order of rows. Or: rotate 90° twice. Equivalent.",
        "Don't forget the `j` range starts at `i + 1` for transpose (not `0`) — otherwise you swap each pair twice and end up with the original matrix.",
        "When debugging, print after the *transpose* step alone. If the transpose is wrong, the reverse won't save it. Decompose the failure.",
        "Common follow-up: 'rotate an `m × n` (non-square) matrix'. You can no longer rotate in-place — the output has different dimensions. Allocate `result[n][m]`.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Facebook", "Bloomberg", "Uber"],
    "topics": ["Array", "Math", "Matrix"],
    "time_complexity": "O(n²)",
    "space_complexity": "O(1)",
}


def REFERENCE(matrix):
    # Deepcopy so the test harness's input is never mutated across cases.
    m = deepcopy(matrix)
    n = len(m)
    # Transpose.
    for i in range(n):
        for j in range(i + 1, n):
            m[i][j], m[j][i] = m[j][i], m[i][j]
    # Reverse each row.
    for row in m:
        row.reverse()
    return m


register(PAYLOAD, REFERENCE)
