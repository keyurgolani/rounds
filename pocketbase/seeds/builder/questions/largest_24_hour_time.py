"""Largest 24-Hour Time From Digits — Easy. Permutation / Brute Force.

Four digits means at most 24 arrangements. Exhaustive search over
those permutations is both the simplest and fastest approach. The
problem tests boundary validation (hours < 24, minutes < 60) and
careful formatting with leading zeroes.
"""
from itertools import permutations

from builder.registry import register


PAYLOAD = {
    "title": "Largest 24-Hour Time From Digits",
    "difficulty": "Easy",
    "description": (
        "Given four digits, arrange all of them to make the latest valid 24-hour time in `HH:MM` format. "
        "If no valid time can be formed, return `NOT POSSIBLE`."
    ),
    "hints": [
        "There are only 24 permutations, so brute force is both simple and optimal enough.",
        "A time is valid when `0 <= hours < 24` and `0 <= minutes < 60`.",
        "Compare valid times by total minutes since midnight.",
        "Format the answer with leading zeroes for both hours and minutes.",
    ],
    "constraints": ["digits.length == 4", "0 <= digits[i] <= 9"],
    "starter_code": {
        "python": "def largest_24_hour_time(digits):\n    # Your code here\n    pass",
        "javascript": "function largest24HourTime(digits) {\n    // Your code here\n}",
        "java": "public String largest24HourTime(int[] digits) {\n    // Your code here\n    return \"NOT POSSIBLE\";\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(largest_24_hour_time([1, 2, 3, 4]))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "console.log(largest24HourTime([1, 2, 3, 4]));"
        ),
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"digits": [1, 2, 3, 4]}, "expected": "23:41",
         "description": "Several valid permutations", "tags": ["basic"]},
        {"input": {"digits": [0, 0, 0, 0]}, "expected": "00:00",
         "description": "Midnight", "tags": ["edge"]},
        {"input": {"digits": [2, 4, 0, 0]}, "expected": "20:40",
         "description": "24 is not a valid hour", "tags": ["tricky"]},
        {"input": {"digits": [5, 5, 5, 5]}, "expected": "NOT POSSIBLE",
         "description": "No valid hour", "tags": ["edge"]},
        {"input": {"digits": [0, 6, 0, 0]}, "expected": "06:00",
         "description": "Leading zero hour", "tags": ["edge"]},
    ],
    "solutions": [{
        "title": "Enumerate All Permutations",
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "description": "Try every ordering of the four digits and keep the valid time with the largest minute count.",
        "code": {
            "python": (
                "from itertools import permutations\n\n"
                "def largest_24_hour_time(digits):\n"
                "    best = -1\n"
                "    for a, b, c, d in permutations(digits):\n"
                "        hours = a * 10 + b\n"
                "        minutes = c * 10 + d\n"
                "        if hours < 24 and minutes < 60:\n"
                "            best = max(best, hours * 60 + minutes)\n"
                "    if best == -1:\n"
                "        return 'NOT POSSIBLE'\n"
                "    return f'{best // 60:02d}:{best % 60:02d}'"
            ),
            "javascript": (
                "function largest24HourTime(digits) {\n"
                "    let best = -1;\n"
                "    const perms = (arr) => arr.length <= 1 ? [arr] : arr.flatMap((v, i) => perms([...arr.slice(0, i), ...arr.slice(i + 1)]).map(p => [v, ...p]));\n"
                "    for (const [a, b, c, d] of perms(digits)) {\n"
                "        const h = a * 10 + b, m = c * 10 + d;\n"
                "        if (h < 24 && m < 60) best = Math.max(best, h * 60 + m);\n"
                "    }\n"
                "    return best === -1 ? 'NOT POSSIBLE' : String(Math.floor(best / 60)).padStart(2, '0') + ':' + String(best % 60).padStart(2, '0');\n"
                "}"
            ),
        },
    }],
    "thought_process": [
        "1. Point out that four digits means at most 24 arrangements, so exhaustive search is clean.",
        "2. For each ordering, split the first two digits into hours and the last two into minutes.",
        "3. Reject invalid hours and minutes.",
        "4. Track the maximum total minutes and format the final answer with leading zeroes.",
    ],
    "tips": [
        "Do not accept `24:00`; 24 is outside the valid hour range.",
        "Duplicate digits can produce duplicate permutations. That is fine because the search space is constant.",
        "Returning `6:00` instead of `06:00` is a formatting bug, not an algorithm bug.",
    ],
    "companies": [],
    "topics": ["Array", "Permutation", "Brute Force"],
    "time_complexity": "O(1)",
    "space_complexity": "O(1)",
}


def REFERENCE(digits):
    best = -1
    for a, b, c, d in permutations(digits):
        hours = a * 10 + b
        minutes = c * 10 + d
        if hours < 24 and minutes < 60:
            best = max(best, hours * 60 + minutes)
    if best == -1:
        return "NOT POSSIBLE"
    return f"{best // 60:02d}:{best % 60:02d}"


register(PAYLOAD, REFERENCE)
