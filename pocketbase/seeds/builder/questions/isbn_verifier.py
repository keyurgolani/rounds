"""ISBN-10 Verifier — Medium. String, Math, Validation.

Strip dashes, reject wrong length, then compute the weighted sum
with weights 10 down to 1. The two classic bugs are allowing X
anywhere and stripping all non-digits instead of just dashes.
"""
from builder.registry import register


PAYLOAD = {
    "title": "ISBN-10 Verifier",
    "difficulty": "Medium",
    "description": (
        "Verify whether a string is a valid ISBN-10. Ignore dashes. The first nine characters must be digits; "
        "the last character may be a digit or `X`, where `X` means 10. The weighted sum must be divisible by 11."
    ),
    "hints": [
        "Remove dashes before validation; other punctuation is not ignored.",
        "After cleanup, there must be exactly 10 characters.",
        "Only the final character may be `X`, and it represents value 10.",
        "Compute `sum(value * weight)` for weights 10 down to 1 and check modulo 11.",
        "Reject bad length or invalid characters before calculating the checksum.",
    ],
    "constraints": ["0 <= isbn.length <= 32"],
    "starter_code": {
        "python": "def is_valid_isbn10(isbn):\n    # Your code here\n    pass",
        "javascript": "function isValidIsbn10(isbn) {\n    // Your code here\n}",
        "java": "public boolean isValidIsbn10(String isbn) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": "# Test runner (read-only)\nif __name__ == \"__main__\":\n    print(is_valid_isbn10(\"3-598-21508-8\"))",
        "javascript": "// Test runner (read-only)\nconsole.log(isValidIsbn10(\"3-598-21508-8\"));",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"isbn": "3-598-21508-8"}, "expected": True, "description": "Valid ISBN with dashes", "tags": ["basic"]},
        {"input": {"isbn": "3-598-21508-9"}, "expected": False, "description": "Invalid check digit", "tags": ["basic"]},
        {"input": {"isbn": "3-598-21507-X"}, "expected": True, "description": "Valid X check digit", "tags": ["basic"]},
        {"input": {"isbn": "3-598-21507-A"}, "expected": False, "description": "Invalid check digit character", "tags": ["edge"]},
        {"input": {"isbn": "3-598-2X507-9"}, "expected": False, "description": "X before the check digit", "tags": ["edge"]},
        {"input": {"isbn": "3598215088"}, "expected": True, "description": "Valid without dashes", "tags": ["basic"]},
        {"input": {"isbn": "359821507"}, "expected": False, "description": "Too short", "tags": ["edge"]},
        {"input": {"isbn": ""}, "expected": False, "description": "Empty input", "tags": ["edge"]},
    ],
    "solutions": [{
        "title": "Normalize and Weighted Sum",
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "description": "Strip dashes, validate the normalized characters, then apply the ISBN-10 modulo rule.",
        "code": {
            "python": (
                "def is_valid_isbn10(isbn):\n"
                "    chars = isbn.replace('-', '')\n"
                "    if len(chars) != 10:\n"
                "        return False\n"
                "    total = 0\n"
                "    for i, ch in enumerate(chars):\n"
                "        if ch == 'X' and i == 9:\n"
                "            value = 10\n"
                "        elif ch.isdigit():\n"
                "            value = int(ch)\n"
                "        else:\n"
                "            return False\n"
                "        total += value * (10 - i)\n"
                "    return total % 11 == 0"
            ),
            "javascript": (
                "function isValidIsbn10(isbn) {\n"
                "    const chars = isbn.replaceAll('-', '');\n"
                "    if (chars.length !== 10) return false;\n"
                "    let total = 0;\n"
                "    for (let i = 0; i < chars.length; i++) {\n"
                "        const ch = chars[i];\n"
                "        let value;\n"
                "        if (ch === 'X' && i === 9) value = 10;\n"
                "        else if (/^[0-9]$/.test(ch)) value = Number(ch);\n"
                "        else return false;\n"
                "        total += value * (10 - i);\n"
                "    }\n"
                "    return total % 11 === 0;\n"
                "}"
            ),
        },
    }],
    "thought_process": [
        "1. Normalize only by removing dashes; keep every other character meaningful.",
        "2. Reject the wrong length immediately.",
        "3. Walk the 10 normalized characters with weights 10 down to 1.",
        "4. Convert a final `X` to 10 and reject `X` anywhere else.",
        "5. Return whether the weighted sum is divisible by 11.",
    ],
    "tips": [
        "The most common bug is allowing `X` anywhere instead of only in the final position.",
        "A second common bug is stripping all non-digits; that incorrectly accepts inputs with letters or extra punctuation.",
        "Use `3-598-21508-8` as a valid check and `3-598-21508-9` as the one-digit invalid check.",
        "If asked about ISBN-13, say it uses a different 13-digit weighted checksum, so do not mix the rules.",
    ],
    "companies": [],
    "topics": ["String", "Math", "Validation"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(isbn):
    chars = isbn.replace("-", "")
    if len(chars) != 10:
        return False
    total = 0
    for i, ch in enumerate(chars):
        if ch == "X" and i == 9:
            value = 10
        elif ch.isdigit():
            value = int(ch)
        else:
            return False
        total += value * (10 - i)
    return total % 11 == 0


register(PAYLOAD, REFERENCE)
