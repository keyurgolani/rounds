"""Zigzag String Conversion — Medium. String, Simulation.

Write characters into row buckets while bouncing the row pointer up
and down. The identity cases (one row or rows >= length) return the
string unchanged — forgetting them breaks the pointer logic.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Zigzag String Conversion",
    "difficulty": "Medium",
    "description": (
        "Convert a string into a zigzag pattern with `num_rows`, then read the rows from top to bottom.\n\n"
        "For `s = \"PAYPALISHIRING\"` and `num_rows = 3`, the rows read as `PAHNAPLSIIGYIR`."
    ),
    "hints": [
        "First handle identity cases: one row or at least as many rows as characters returns the original string.",
        "The simplest correct model is row simulation: append each character to the current row and move the row pointer down or up.",
        "Flip direction at row `0` and row `num_rows - 1`; do the flip before the next pointer move.",
        "The arithmetic cycle length is `2 * num_rows - 2`, but simulation is usually easier to code correctly in an interview.",
        "Memory is O(n) because the output itself has n characters; the row array only adds O(num_rows) buckets.",
    ],
    "constraints": [
        "0 <= s.length <= 10^4",
        "1 <= num_rows <= 10^4",
    ],
    "starter_code": {
        "python": "def zigzag_convert(s, num_rows):\n    # Your code here\n    pass",
        "javascript": "function zigzagConvert(s, numRows) {\n    // Your code here\n}",
        "java": "public String zigzagConvert(String s, int numRows) {\n    // Your code here\n    return \"\";\n}",
    },
    "boilerplate_code": {
        "python": "# Test runner (read-only)\nif __name__ == \"__main__\":\n    print(zigzag_convert(\"PAYPALISHIRING\", 3))",
        "javascript": "// Test runner (read-only)\nconsole.log(zigzagConvert(\"PAYPALISHIRING\", 3));",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"s": "PAYPALISHIRING", "num_rows": 3}, "expected": "PAHNAPLSIIGYIR", "description": "Three rows", "tags": ["basic"]},
        {"input": {"s": "PAYPALISHIRING", "num_rows": 4}, "expected": "PINALSIGYAHRPI", "description": "Four rows", "tags": ["basic"]},
        {"input": {"s": "A", "num_rows": 1}, "expected": "A", "description": "Single character", "tags": ["edge"]},
        {"input": {"s": "AB", "num_rows": 1}, "expected": "AB", "description": "Single row", "tags": ["edge"]},
        {"input": {"s": "AB", "num_rows": 5}, "expected": "AB", "description": "Rows exceed length", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Row Simulation",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": "Append each character to the current row and flip direction at the top and bottom rows.",
            "code": {
                "python": (
                    "def zigzag_convert(s, num_rows):\n"
                    "    if num_rows == 1 or num_rows >= len(s):\n"
                    "        return s\n"
                    "    rows = [''] * num_rows\n"
                    "    row, step = 0, 1\n"
                    "    for ch in s:\n"
                    "        rows[row] += ch\n"
                    "        if row == 0:\n"
                    "            step = 1\n"
                    "        elif row == num_rows - 1:\n"
                    "            step = -1\n"
                    "        row += step\n"
                    "    return ''.join(rows)"
                ),
                "javascript": (
                    "function zigzagConvert(s, numRows) {\n"
                    "    if (numRows === 1 || numRows >= s.length) return s;\n"
                    "    const rows = Array.from({ length: numRows }, () => '');\n"
                    "    let row = 0, step = 1;\n"
                    "    for (const ch of s) {\n"
                    "        rows[row] += ch;\n"
                    "        if (row === 0) step = 1;\n"
                    "        else if (row === numRows - 1) step = -1;\n"
                    "        row += step;\n"
                    "    }\n"
                    "    return rows.join('');\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Draw the `PAYPALISHIRING` example for 3 rows so the row order is visible.",
        "2. State the identity cases up front to avoid pointer logic that breaks on `num_rows == 1`.",
        "3. Maintain `row` and `step`; append each character to `rows[row]`.",
        "4. At the first and last rows, flip `step` so the next character moves in the opposite direction.",
        "5. Join rows in order. The zigzag geometry is only an intermediate representation; the output is row-major.",
    ],
    "tips": [
        "The most common bug is updating `row` before checking whether you are at a boundary.",
        "Avoid a 2D grid full of blanks; row buckets produce the same output without wasted space.",
        "For `num_rows = 2`, the direction flips every character. Include this as a mental test case.",
        "If asked for a math-only version, use cycle length `2r - 2` and collect vertical plus diagonal positions per row.",
    ],
    "companies": ["Adobe", "Amazon", "Apple", "Bloomberg", "Meta", "Google", "Microsoft", "PayPal"],
    "topics": ["String", "Simulation"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(s, num_rows):
    if num_rows == 1 or num_rows >= len(s):
        return s
    rows = [""] * num_rows
    row = 0
    step = 1
    for ch in s:
        rows[row] += ch
        if row == 0:
            step = 1
        elif row == num_rows - 1:
            step = -1
        row += step
    return "".join(rows)


register(PAYLOAD, REFERENCE)
