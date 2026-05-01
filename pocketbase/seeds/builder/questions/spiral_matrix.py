"""Spiral Matrix — Medium. Matrix / Simulation.

The classic 'walk a matrix in spiral order' problem. Two clean approaches:
shrink boundaries (top/bottom/left/right) after each side is consumed, or
walk with a direction vector and a visited matrix. The boundary-shrink
version is the interview-grade answer — O(1) extra space and no off-by-one
trickery if you commit to half-open ranges. Watch for the two terminating
sides on uneven matrices: the last row or column can be re-walked if you
forget the boundary check.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Spiral Matrix",
    "difficulty": "Medium",
    "description": (
        "Given an `m x n` matrix, return all elements of the matrix in **spiral order** — starting at the "
        "top-left corner and walking clockwise (right, down, left, up), spiralling inward.\n\n"
        "**Example 1:**\n"
        "- Input: `matrix = [[1,2,3],[4,5,6],[7,8,9]]`\n"
        "- Output: `[1,2,3,6,9,8,7,4,5]`\n"
        "- Explanation: Walk the top row left-to-right (1,2,3), the right column top-to-bottom (6,9), the "
        "bottom row right-to-left (8,7), the left column bottom-to-top (4), then the inner cell (5).\n\n"
        "**Example 2:**\n"
        "- Input: `matrix = [[1,2,3,4],[5,6,7,8],[9,10,11,12]]`\n"
        "- Output: `[1,2,3,4,8,12,11,10,9,5,6,7]`\n"
        "- Explanation: 3×4 grid. Outer layer first (1,2,3,4,8,12,11,10,9,5), then the inner row (6,7). "
        "Note the inner 'layer' is a single horizontal strip — not a full ring."
    ),
    "hints": [
        "Maintain four boundaries: `top`, `bottom`, `left`, `right`. Initialise them to `0, m-1, 0, n-1`. "
        "After you finish consuming a side, shrink the corresponding boundary by 1.",
        "Walk one side at a time: top row left→right, then right column top→bottom, then bottom row "
        "right→left, then left column bottom→top. Repeat until `top > bottom` or `left > right`.",
        "Critical guard: after consuming the top row and the right column, you must check `top <= bottom` "
        "*and* `left <= right` before walking the bottom row / left column. Otherwise a single remaining row "
        "or column will be walked twice (in opposite directions), producing duplicate output.",
        "Alternative — direction vectors: keep `(dr, dc)` cycling through `[(0,1),(1,0),(0,-1),(-1,0)]`. "
        "Move while the next cell is in-bounds and unvisited; otherwise rotate. Uses `O(m·n)` extra space "
        "for the visited matrix.",
        "Total cells = `m * n`. You can use that as the loop's stopping condition instead of comparing "
        "boundaries — collect until `len(result) == m * n` and break.",
    ],
    "constraints": [
        "m == matrix.length",
        "n == matrix[i].length",
        "1 <= m, n <= 10, -100 <= matrix[i][j] <= 100",
    ],
    "starter_code": {
        "python": "def spiral_order(matrix):\n    # Your code here\n    pass",
        "javascript": "function spiralOrder(matrix) {\n    // Your code here\n}",
        "java": "public List<Integer> spiralOrder(int[][] matrix) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[1,2,3],[4,5,6],[7,8,9]],\n"
            "        [[1,2,3,4],[5,6,7,8],[9,10,11,12]],\n"
            "        [[1]],\n"
            "    ]\n"
            "    for m in cases:\n"
            "        print(f\"spiral_order({m}) = {spiral_order(m)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,2,3],[4,5,6],[7,8,9]], [[1,2,3,4],[5,6,7,8],[9,10,11,12]]].forEach(m =>\n"
            "    console.log(`spiralOrder =`, spiralOrder(m))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] m = {{1,2,3},{4,5,6},{7,8,9}};\n"
            "        System.out.println(s.spiralOrder(m));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]},
         "expected": [1, 2, 3, 6, 9, 8, 7, 4, 5],
         "description": "Classic 3x3 — outer ring then center", "tags": ["basic"]},
        {"input": {"matrix": [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]},
         "expected": [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7],
         "description": "3x4 — inner layer is a horizontal strip", "tags": ["basic"]},
        {"input": {"matrix": [[1, 2, 3, 4, 5]]},
         "expected": [1, 2, 3, 4, 5],
         "description": "1xn — single row, just left-to-right", "tags": ["edge"]},
        {"input": {"matrix": [[1], [2], [3], [4]]},
         "expected": [1, 2, 3, 4],
         "description": "mx1 — single column, top-to-bottom", "tags": ["edge"]},
        {"input": {"matrix": [[42]]},
         "expected": [42],
         "description": "1x1 — single element", "tags": ["edge"]},
        {"input": {"matrix": [[1, 2], [3, 4]]},
         "expected": [1, 2, 4, 3],
         "description": "2x2 — single ring, no center", "tags": ["edge"]},
        {"input": {"matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]]},
         "expected": [1, 2, 3, 6, 9, 12, 11, 10, 7, 4, 5, 8],
         "description": "4x3 — taller than wide; inner layer is a vertical strip", "tags": ["tricky"]},
        {"input": {"matrix": [
            [1, 2, 3, 4, 5],
            [16, 17, 18, 19, 6],
            [15, 24, 25, 20, 7],
            [14, 23, 22, 21, 8],
            [13, 12, 11, 10, 9],
        ]},
         "expected": list(range(1, 26)),
         "description": "5x5 — three concentric layers, output is 1..25", "tags": ["tricky"]},
        {"input": {"matrix": [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]},
         "expected": [1, 2, 4, 6, 8, 10, 9, 7, 5, 3],
         "description": "5x2 — uneven, very tall; checks left/right shrink path", "tags": ["tricky"]},
        {"input": {"matrix": [[-1, -2, -3], [-4, -5, -6], [-7, -8, -9]]},
         "expected": [-1, -2, -3, -6, -9, -8, -7, -4, -5],
         "description": "3x3 with negatives — values don't affect order", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Boundary-Shrink Walk (Optimal)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(1)",
            "description": (
                "Maintain `top`, `bottom`, `left`, `right`. Each iteration: walk top row L→R then top++, "
                "walk right column T→B then right--, then *if* `top <= bottom` walk bottom row R→L and "
                "bottom--, then *if* `left <= right` walk left column B→T and left++. The two guards are "
                "essential — without them, a single remaining row or column gets walked twice on uneven "
                "matrices. Excludes the visited matrix, so O(1) extra space (output not counted)."
            ),
            "code": {
                "python": (
                    "def spiral_order(matrix):\n"
                    "    if not matrix or not matrix[0]:\n"
                    "        return []\n"
                    "    top, bottom = 0, len(matrix) - 1\n"
                    "    left, right = 0, len(matrix[0]) - 1\n"
                    "    out = []\n"
                    "    while top <= bottom and left <= right:\n"
                    "        for c in range(left, right + 1):\n"
                    "            out.append(matrix[top][c])\n"
                    "        top += 1\n"
                    "        for r in range(top, bottom + 1):\n"
                    "            out.append(matrix[r][right])\n"
                    "        right -= 1\n"
                    "        if top <= bottom:\n"
                    "            for c in range(right, left - 1, -1):\n"
                    "                out.append(matrix[bottom][c])\n"
                    "            bottom -= 1\n"
                    "        if left <= right:\n"
                    "            for r in range(bottom, top - 1, -1):\n"
                    "                out.append(matrix[r][left])\n"
                    "            left += 1\n"
                    "    return out"
                ),
                "javascript": (
                    "function spiralOrder(matrix) {\n"
                    "    if (!matrix.length || !matrix[0].length) return [];\n"
                    "    let top = 0, bottom = matrix.length - 1;\n"
                    "    let left = 0, right = matrix[0].length - 1;\n"
                    "    const out = [];\n"
                    "    while (top <= bottom && left <= right) {\n"
                    "        for (let c = left; c <= right; c++) out.push(matrix[top][c]);\n"
                    "        top++;\n"
                    "        for (let r = top; r <= bottom; r++) out.push(matrix[r][right]);\n"
                    "        right--;\n"
                    "        if (top <= bottom) {\n"
                    "            for (let c = right; c >= left; c--) out.push(matrix[bottom][c]);\n"
                    "            bottom--;\n"
                    "        }\n"
                    "        if (left <= right) {\n"
                    "            for (let r = bottom; r >= top; r--) out.push(matrix[r][left]);\n"
                    "            left++;\n"
                    "        }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public List<Integer> spiralOrder(int[][] matrix) {\n"
                    "    List<Integer> out = new ArrayList<>();\n"
                    "    if (matrix.length == 0 || matrix[0].length == 0) return out;\n"
                    "    int top = 0, bottom = matrix.length - 1;\n"
                    "    int left = 0, right = matrix[0].length - 1;\n"
                    "    while (top <= bottom && left <= right) {\n"
                    "        for (int c = left; c <= right; c++) out.add(matrix[top][c]);\n"
                    "        top++;\n"
                    "        for (int r = top; r <= bottom; r++) out.add(matrix[r][right]);\n"
                    "        right--;\n"
                    "        if (top <= bottom) {\n"
                    "            for (int c = right; c >= left; c--) out.add(matrix[bottom][c]);\n"
                    "            bottom--;\n"
                    "        }\n"
                    "        if (left <= right) {\n"
                    "            for (int r = bottom; r >= top; r--) out.add(matrix[r][left]);\n"
                    "            left++;\n"
                    "        }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Direction Vector with Visited Matrix",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Store directions in a fixed cycle: `(0,1) → (1,0) → (0,-1) → (-1,0)`. Walk forward "
                "while the next cell is in-bounds and unvisited; when blocked, rotate to the next "
                "direction. Stop after collecting `m·n` cells. Conceptually clean, but pays O(m·n) "
                "extra space for the visited grid. Mention as the more general pattern (it generalises "
                "to spirals on irregular shapes / mazes)."
            ),
            "code": {
                "python": (
                    "def spiral_order(matrix):\n"
                    "    if not matrix or not matrix[0]:\n"
                    "        return []\n"
                    "    m, n = len(matrix), len(matrix[0])\n"
                    "    seen = [[False] * n for _ in range(m)]\n"
                    "    dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]\n"
                    "    r = c = di = 0\n"
                    "    out = []\n"
                    "    for _ in range(m * n):\n"
                    "        out.append(matrix[r][c])\n"
                    "        seen[r][c] = True\n"
                    "        nr, nc = r + dirs[di][0], c + dirs[di][1]\n"
                    "        if 0 <= nr < m and 0 <= nc < n and not seen[nr][nc]:\n"
                    "            r, c = nr, nc\n"
                    "        else:\n"
                    "            di = (di + 1) % 4\n"
                    "            r, c = r + dirs[di][0], c + dirs[di][1]\n"
                    "    return out"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: produce all m·n cells, walking clockwise from top-left, spiralling inward.",
        "2. Brute idea: keep a `visited` grid and a direction; rotate when the next step is OOB or visited. Works, but O(m·n) extra space.",
        "3. Optimal idea: the spiral consumes whole sides at a time. Track `top`, `bottom`, `left`, `right`; after each side, shrink the matching boundary.",
        "4. Loop: top-row L→R; right-col T→B; bottom-row R→L; left-col B→T. Repeat while `top <= bottom and left <= right`.",
        "5. Trap: on uneven matrices the inner 'layer' may be a single row or column. Without the `top <= bottom` and `left <= right` guards before the bottom-row and left-column passes, you walk that strip twice in opposite directions and emit duplicates.",
        "6. Edge cases: 1×1 (output is the single cell), 1×n (just the top row), m×1 (just the right column — the left-column pass is correctly guarded out).",
    ],
    "tips": [
        "Half-open vs closed ranges: pick one and stick with it. The reference uses inclusive bounds (`<=`) everywhere — mixing is how off-by-ones happen.",
        "If you forget the two inner guards, run the 1×n and m×1 cases by hand. They surface the duplicate-walk bug instantly.",
        "Stopping condition: `len(out) == m * n` is an equally good (and arguably clearer) loop condition. Use whichever you can write without bugs under interview pressure.",
        "Generate Spiral (LeetCode 59) is the inverse — write 1..n² in spiral order. Same skeleton; just assign values instead of reading them.",
        "Spiral Matrix III (LC 885) starts off-grid and needs the direction-vector formulation — the boundary-shrink trick doesn't generalise. Worth knowing the pattern.",
        "If the interviewer asks for O(1) auxiliary space, the boundary-shrink solution is the answer. The visited-matrix version costs O(m·n) and is harder to defend.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Apple", "Bloomberg", "Uber"],
    "topics": ["Array", "Matrix", "Simulation"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(1)",
}


def REFERENCE(matrix):
    if not matrix or not matrix[0]:
        return []
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1
    out = []
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            out.append(matrix[top][c])
        top += 1
        for r in range(top, bottom + 1):
            out.append(matrix[r][right])
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1):
                out.append(matrix[bottom][c])
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):
                out.append(matrix[r][left])
            left += 1
    return out


register(PAYLOAD, REFERENCE)
