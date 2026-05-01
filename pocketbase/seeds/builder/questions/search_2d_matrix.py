"""Search a 2D Matrix — Medium. Binary Search.

The matrix is *globally* sorted in row-major order: rows are ascending
and the first int of each row is greater than the last int of the row
above. That global property means you can flatten conceptually and run
a single binary search in O(log(m·n)) — the classic optimal. The
staircase walk from the top-right corner gives O(m+n) and generalises
to LC 240 (rows/cols sorted but not globally), so it's worth knowing
both framings.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Search a 2D Matrix",
    "difficulty": "Medium",
    "description": (
        "You are given an `m x n` integer matrix `matrix` with the following two properties:\n\n"
        "- Each row is sorted in non-decreasing order.\n"
        "- The first integer of each row is greater than the last integer of the previous row.\n\n"
        "Given an integer `target`, return `True` if `target` is in `matrix`, or `False` otherwise.\n\n"
        "You must write a solution in `O(log(m * n))` time complexity.\n\n"
        "**Example 1:**\n"
        "- Input: `matrix = [[1,3,5,7],[10,11,16,20],[23,30,34,60]]`, `target = 3`\n"
        "- Output: `True`\n"
        "- Explanation: `3` appears in the first row.\n\n"
        "**Example 2:**\n"
        "- Input: `matrix = [[1,3,5,7],[10,11,16,20],[23,30,34,60]]`, `target = 13`\n"
        "- Output: `False`\n"
        "- Explanation: `13` would fall between rows 1 and 2 but is not present."
    ),
    "hints": [
        "The two properties together mean the matrix, read row by row, is one big sorted array. Treat it as 1D.",
        "Map a flat index `idx` in `[0, m*n)` to a (row, col) pair via `row = idx // n`, `col = idx % n`. That's the only trick you need to run a single binary search.",
        "Standard binary search bounds: `lo = 0`, `hi = m*n - 1`. Compare `matrix[mid // n][mid % n]` to `target`.",
        "Alternative: 'staircase' from the top-right corner. If current > target go left; if current < target go down; equal is a hit. O(m + n) — slower asymptotically but generalises to LC 240 where rows/cols are only locally sorted.",
        "Two-step binary search (first locate the row by its first/last element, then binary-search within the row) is also O(log m + log n) = O(log(m·n)). Cleaner for some, but the flat-index version is one loop.",
    ],
    "constraints": [
        "m == matrix.length, n == matrix[0].length",
        "1 <= m, n <= 100",
        "-10^4 <= matrix[i][j], target <= 10^4",
    ],
    "starter_code": {
        "python": "def search_matrix(matrix, target):\n    # Your code here\n    pass",
        "javascript": "function searchMatrix(matrix, target) {\n    // Your code here\n}",
        "java": "public boolean searchMatrix(int[][] matrix, int target) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    m = [[1,3,5,7],[10,11,16,20],[23,30,34,60]]\n"
            "    for t in [3, 13, 60, 0]:\n"
            "        print(f\"search_matrix(m, {t}) = {search_matrix(m, t)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const m = [[1,3,5,7],[10,11,16,20],[23,30,34,60]];\n"
            "[3, 13, 60, 0].forEach(t =>\n"
            "    console.log(`searchMatrix(m, ${t}) =`, searchMatrix(m, t))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] m = {{1,3,5,7},{10,11,16,20},{23,30,34,60}};\n"
            "        System.out.println(s.searchMatrix(m, 3));\n"
            "        System.out.println(s.searchMatrix(m, 13));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"matrix": [[1, 3, 5, 7], [10, 11, 16, 20], [23, 30, 34, 60]], "target": 3},
         "expected": True,
         "description": "Classic LC example — target in first row", "tags": ["basic"]},
        {"input": {"matrix": [[1, 3, 5, 7], [10, 11, 16, 20], [23, 30, 34, 60]], "target": 13},
         "expected": False,
         "description": "Classic LC example — target falls between rows", "tags": ["basic"]},
        {"input": {"matrix": [[5]], "target": 5}, "expected": True,
         "description": "1×1 hit", "tags": ["edge"]},
        {"input": {"matrix": [[5]], "target": 4}, "expected": False,
         "description": "1×1 miss", "tags": ["edge"]},
        {"input": {"matrix": [[1, 2, 3, 4, 5, 6, 7, 8]], "target": 6}, "expected": True,
         "description": "1×n single-row matrix — straight binary search", "tags": ["edge"]},
        {"input": {"matrix": [[1, 2, 3, 4, 5, 6, 7, 8]], "target": 9}, "expected": False,
         "description": "1×n miss above", "tags": ["edge"]},
        {"input": {"matrix": [[1], [3], [5], [7], [9]], "target": 7}, "expected": True,
         "description": "m×1 single-column matrix — index/col arithmetic still works", "tags": ["edge"]},
        {"input": {"matrix": [[1], [3], [5], [7], [9]], "target": 4}, "expected": False,
         "description": "m×1 miss between rows", "tags": ["edge"]},
        {"input": {"matrix": [[1, 3, 5, 7], [10, 11, 16, 20], [23, 30, 34, 60]], "target": 0},
         "expected": False,
         "description": "Target below all elements", "tags": ["edge"]},
        {"input": {"matrix": [[1, 3, 5, 7], [10, 11, 16, 20], [23, 30, 34, 60]], "target": 100},
         "expected": False,
         "description": "Target above all elements", "tags": ["edge"]},
        {"input": {"matrix": [[1, 3, 5, 7], [10, 11, 16, 20], [23, 30, 34, 60]], "target": 1},
         "expected": True,
         "description": "Target at top-left corner", "tags": ["tricky"]},
        {"input": {"matrix": [[1, 3, 5, 7], [10, 11, 16, 20], [23, 30, 34, 60]], "target": 60},
         "expected": True,
         "description": "Target at bottom-right corner", "tags": ["tricky"]},
        {"input": {"matrix": [[-10, -5, 0], [3, 7, 9], [11, 13, 15]], "target": -5},
         "expected": True,
         "description": "Negative values present", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "1D Binary Search via Flat Index (Optimal)",
            "time_complexity": "O(log(m * n))",
            "space_complexity": "O(1)",
            "description": (
                "Treat the matrix as a virtual sorted array of length `m*n`. Binary-search on the flat index "
                "and convert to (row, col) on the fly via `row = mid // n`, `col = mid % n`. One loop, one "
                "comparison, optimal."
            ),
            "code": {
                "python": (
                    "def search_matrix(matrix, target):\n"
                    "    if not matrix or not matrix[0]:\n"
                    "        return False\n"
                    "    m, n = len(matrix), len(matrix[0])\n"
                    "    lo, hi = 0, m * n - 1\n"
                    "    while lo <= hi:\n"
                    "        mid = (lo + hi) // 2\n"
                    "        val = matrix[mid // n][mid % n]\n"
                    "        if val == target:\n"
                    "            return True\n"
                    "        if val < target:\n"
                    "            lo = mid + 1\n"
                    "        else:\n"
                    "            hi = mid - 1\n"
                    "    return False"
                ),
                "javascript": (
                    "function searchMatrix(matrix, target) {\n"
                    "    if (!matrix.length || !matrix[0].length) return false;\n"
                    "    const m = matrix.length, n = matrix[0].length;\n"
                    "    let lo = 0, hi = m * n - 1;\n"
                    "    while (lo <= hi) {\n"
                    "        const mid = (lo + hi) >> 1;\n"
                    "        const val = matrix[Math.floor(mid / n)][mid % n];\n"
                    "        if (val === target) return true;\n"
                    "        if (val < target) lo = mid + 1;\n"
                    "        else hi = mid - 1;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
                "java": (
                    "public boolean searchMatrix(int[][] matrix, int target) {\n"
                    "    if (matrix.length == 0 || matrix[0].length == 0) return false;\n"
                    "    int m = matrix.length, n = matrix[0].length;\n"
                    "    int lo = 0, hi = m * n - 1;\n"
                    "    while (lo <= hi) {\n"
                    "        int mid = (lo + hi) >>> 1;\n"
                    "        int val = matrix[mid / n][mid % n];\n"
                    "        if (val == target) return true;\n"
                    "        if (val < target) lo = mid + 1;\n"
                    "        else hi = mid - 1;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Staircase from Top-Right",
            "time_complexity": "O(m + n)",
            "space_complexity": "O(1)",
            "description": (
                "Start at the top-right corner. If the current cell equals `target`, done. If it's bigger, "
                "the entire current column below is also bigger — move left. If it's smaller, the entire "
                "current row to the left is also smaller — move down. Each step eliminates a row or a column, "
                "so we visit at most `m + n` cells. Slower than binary search here but the same code solves "
                "LC 240 (rows and columns sorted but not globally) where binary search no longer applies."
            ),
            "code": {
                "python": (
                    "def search_matrix(matrix, target):\n"
                    "    if not matrix or not matrix[0]:\n"
                    "        return False\n"
                    "    m, n = len(matrix), len(matrix[0])\n"
                    "    r, c = 0, n - 1\n"
                    "    while r < m and c >= 0:\n"
                    "        val = matrix[r][c]\n"
                    "        if val == target:\n"
                    "            return True\n"
                    "        if val > target:\n"
                    "            c -= 1\n"
                    "        else:\n"
                    "            r += 1\n"
                    "    return False"
                ),
                "javascript": (
                    "function searchMatrix(matrix, target) {\n"
                    "    if (!matrix.length || !matrix[0].length) return false;\n"
                    "    const m = matrix.length, n = matrix[0].length;\n"
                    "    let r = 0, c = n - 1;\n"
                    "    while (r < m && c >= 0) {\n"
                    "        const val = matrix[r][c];\n"
                    "        if (val === target) return true;\n"
                    "        if (val > target) c--;\n"
                    "        else r++;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
                "java": (
                    "public boolean searchMatrix(int[][] matrix, int target) {\n"
                    "    if (matrix.length == 0 || matrix[0].length == 0) return false;\n"
                    "    int m = matrix.length, n = matrix[0].length;\n"
                    "    int r = 0, c = n - 1;\n"
                    "    while (r < m && c >= 0) {\n"
                    "        int val = matrix[r][c];\n"
                    "        if (val == target) return true;\n"
                    "        if (val > target) c--;\n"
                    "        else r++;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Note both properties together: the matrix read row-major is a single sorted sequence of length m*n.",
        "2. That immediately suggests binary search over [0, m*n − 1] with the index→(row, col) mapping `r = idx // n, c = idx % n`.",
        "3. The mapping is the only trick. Code is identical to a 1D binary search after that.",
        "4. Sanity-check overflow: in Java prefer `(lo + hi) >>> 1` over `(lo + hi) / 2` — here m*n <= 10⁴, so it doesn't matter, but the habit transfers.",
        "5. Staircase from top-right is the alternative. Each step prunes a row or column → O(m + n). Use it if the interviewer asks about LC 240 next; the same code works there.",
        "6. Empty-matrix and empty-row guards belong at the top — `matrix[0]` would throw otherwise.",
    ],
    "tips": [
        "If asked to do it without `//` and `%`: do two binary searches — one to find the candidate row by comparing `target` to each row's first element, then one within that row. Same big-O.",
        "Don't write a linear scan after locating the row. Both halves should be log; otherwise you're at O(m + log n) and the interviewer will press.",
        "Watch off-by-one on `hi = m*n - 1`. Using `hi = m*n` (exclusive) with `lo < hi` is also fine — pick one convention and be consistent.",
        "LC 240 ('Search a 2D Matrix II') drops the global-sort property — only rows and columns are individually sorted. The flat-index binary search BREAKS there; the staircase still works. Many candidates conflate the two.",
        "If the interviewer says 'matrix may be huge, don't materialise the flattened array' — point out that the flat-index search never builds it; it only computes (r, c) from the index.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Apple", "Bloomberg", "Facebook"],
    "topics": ["Array", "Binary Search", "Matrix"],
    "time_complexity": "O(log(m * n))",
    "space_complexity": "O(1)",
}


def REFERENCE(matrix, target):
    if not matrix or not matrix[0]:
        return False
    m, n = len(matrix), len(matrix[0])
    lo, hi = 0, m * n - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        val = matrix[mid // n][mid % n]
        if val == target:
            return True
        if val < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return False


register(PAYLOAD, REFERENCE)
