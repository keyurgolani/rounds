"""Count Negatives in a Sorted Matrix — Easy. Matrix / Staircase Walk.

Both rows and columns are sorted descending, so a staircase walk from
the bottom-left corner eliminates one row or one column per step.
The key insight is that a negative cell's entire rightward suffix in
that row is also negative.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Count Negatives in a Sorted Matrix",
    "difficulty": "Easy",
    "description": (
        "Given a matrix sorted in non-increasing order across each row and each column, return the number of negative values."
    ),
    "hints": [
        "Brute force checks every cell, which is O(R*C).",
        "Because rows and columns are sorted descending, the bottom-left or top-right corner lets you eliminate a row or column each step.",
        "From the bottom-left corner: if the value is negative, everything to its right in that row is also negative.",
        "If the bottom-left value is non-negative, move right to find smaller values.",
    ],
    "constraints": [
        "0 <= matrix.length, matrix[0].length <= 10^4",
        "Rows and columns are sorted in non-increasing order",
    ],
    "starter_code": {
        "python": "def count_negatives(matrix):\n    # Your code here\n    pass",
        "javascript": "function countNegatives(matrix) {\n    // Your code here\n}",
        "java": "public int countNegatives(int[][] matrix) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(count_negatives([[4,3,2,-1],[3,2,1,-1],[1,1,-1,-2],[-1,-1,-2,-3]]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"matrix": [[4, 3, 2, -1], [3, 2, 1, -1], [1, 1, -1, -2], [-1, -1, -2, -3]]}, "expected": 8,
         "description": "Canonical sorted matrix", "tags": ["basic"]},
        {"input": {"matrix": [[3, 2], [1, 0]]}, "expected": 0,
         "description": "No negatives", "tags": ["edge"]},
        {"input": {"matrix": [[-1]]}, "expected": 1,
         "description": "Single negative", "tags": ["edge"]},
        {"input": {"matrix": []}, "expected": 0,
         "description": "Empty matrix", "tags": ["edge"]},
        {"input": {"matrix": [[5, 1, -1], [4, -1, -2], [-1, -2, -3]]}, "expected": 6,
         "description": "Staircase boundary", "tags": ["tricky"]},
    ],
    "solutions": [{
        "title": "Staircase Walk",
        "time_complexity": "O(R + C)",
        "space_complexity": "O(1)",
        "description": "Walk from the bottom-left corner and eliminate one row or column at each step.",
        "code": {
            "python": (
                "def count_negatives(matrix):\n"
                "    if not matrix or not matrix[0]:\n"
                "        return 0\n"
                "    rows, cols = len(matrix), len(matrix[0])\n"
                "    r, c = rows - 1, 0\n"
                "    count = 0\n"
                "    while r >= 0 and c < cols:\n"
                "        if matrix[r][c] < 0:\n"
                "            count += cols - c\n"
                "            r -= 1\n"
                "        else:\n"
                "            c += 1\n"
                "    return count"
            ),
            "javascript": (
                "function countNegatives(matrix) {\n"
                "    if (!matrix.length || !matrix[0].length) return 0;\n"
                "    const rows = matrix.length, cols = matrix[0].length;\n"
                "    let r = rows - 1, c = 0, count = 0;\n"
                "    while (r >= 0 && c < cols) {\n"
                "        if (matrix[r][c] < 0) { count += cols - c; r--; }\n"
                "        else c++;\n"
                "    }\n"
                "    return count;\n"
                "}"
            ),
        },
    }],
    "thought_process": [
        "1. Confirm both rows and columns are sorted descending.",
        "2. Start at bottom-left, where moving right gets smaller and moving up gets larger.",
        "3. If the current value is negative, count all cells to its right in that row and move up.",
        "4. If it is non-negative, move right to find smaller values.",
    ],
    "tips": [
        "This is the same staircase idea as searching a sorted 2D matrix, but the action on a negative cell is to count a suffix.",
        "Do not use this O(R+C) walk unless both dimensions are sorted; row-only sorting needs per-row binary search.",
        "Handle empty input before reading `matrix[0]`.",
    ],
    "companies": [],
    "topics": ["Matrix", "Binary Search", "Two Pointers"],
    "time_complexity": "O(R + C)",
    "space_complexity": "O(1)",
}


def REFERENCE(matrix):
    if not matrix or not matrix[0]:
        return 0
    rows, cols = len(matrix), len(matrix[0])
    r, c = rows - 1, 0
    count = 0
    while r >= 0 and c < cols:
        if matrix[r][c] < 0:
            count += cols - c
            r -= 1
        else:
            c += 1
    return count


register(PAYLOAD, REFERENCE)
