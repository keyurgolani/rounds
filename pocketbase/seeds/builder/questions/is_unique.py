"""Is Unique — Easy. String / Hash Set.

The entry-level string uniqueness check. Three solutions worth knowing:
set-based (simplest), boolean array (constant space for ASCII), and
the no-extra-structure follow-up (sort or pairwise). The pigeonhole
principle shortcut for ASCII input is the detail interviewers look for.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Is Unique",
    "difficulty": "Easy",
    "description": (
        "Given a string, determine whether all characters in the string are unique. Return `True` if no "
        "character appears more than once, otherwise return `False`.\n\n"
        "Follow-up: solve it without using an additional data structure."
    ),
    "hints": [
        "The direct solution is to insert characters into a set and fail when you see a repeat.",
        "If the character set is fixed ASCII, any string longer than 128 characters cannot be unique.",
        "For ASCII input, a boolean array of length 128 gives O(1) bounded auxiliary space.",
        "Without extra data structures, compare each pair or sort first; those trade time or mutation for space.",
    ],
    "constraints": ["0 <= s.length <= 10^5", "Assume standard ASCII unless stated otherwise"],
    "starter_code": {
        "python": "def is_unique(s):\n    # Your code here\n    pass",
        "javascript": "function isUnique(s) {\n    // Your code here\n}",
        "java": "public boolean isUnique(String s) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(is_unique(\"abcd\"))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "console.log(isUnique(\"abcd\"));"
        ),
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"s": "abcd"}, "expected": True,
         "description": "All letters are unique", "tags": ["basic"]},
        {"input": {"s": "acvklzckvnzxcvzlxcvkzxcvn"}, "expected": False,
         "description": "Repeated characters", "tags": ["basic"]},
        {"input": {"s": ""}, "expected": True,
         "description": "Empty string has no duplicates", "tags": ["edge"]},
        {"input": {"s": "a"}, "expected": True,
         "description": "Single character", "tags": ["edge"]},
        {"input": {"s": "Aa"}, "expected": True,
         "description": "Case-sensitive characters", "tags": ["tricky"]},
        {"input": {"s": "abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"}, "expected": True,
         "description": "Long unique ASCII string", "tags": ["large"]},
        {"input": {"s": "a" * 129}, "expected": False,
         "description": "Longer than ASCII alphabet with repeats", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Seen Set",
            "time_complexity": "O(n)",
            "space_complexity": "O(min(n, charset))",
            "description": "Track each character as it appears. A second sighting proves the string is not unique.",
            "code": {
                "python": (
                    "def is_unique(s):\n"
                    "    seen = set()\n"
                    "    for ch in s:\n"
                    "        if ch in seen:\n"
                    "            return False\n"
                    "        seen.add(ch)\n"
                    "    return True"
                ),
                "javascript": (
                    "function isUnique(s) {\n"
                    "    const seen = new Set();\n"
                    "    for (const ch of s) {\n"
                    "        if (seen.has(ch)) return false;\n"
                    "        seen.add(ch);\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
        {
            "title": "ASCII Boolean Lookup",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": "If input is ASCII, short-circuit strings longer than 128 and use a fixed-size lookup table.",
            "code": {
                "python": (
                    "def is_unique(s):\n"
                    "    if len(s) > 128:\n"
                    "        return False\n"
                    "    seen = [False] * 128\n"
                    "    for ch in s:\n"
                    "        idx = ord(ch)\n"
                    "        if seen[idx]:\n"
                    "            return False\n"
                    "        seen[idx] = True\n"
                    "    return True"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Clarify the character set. ASCII, Unicode, and case-insensitive variants change the bounds.",
        "2. With a set, every repeat is detected when encountered, so the scan can return early.",
        "3. With fixed ASCII, length greater than 128 is an immediate `False` by the pigeonhole principle.",
        "4. For the no-extra-structure follow-up, discuss the O(n^2) pairwise scan or O(n log n) sort-and-scan option.",
    ],
    "tips": [
        "Do not claim O(1) space for a generic set unless the character set is explicitly bounded.",
        "Ask whether uppercase and lowercase are distinct; this problem treats them as distinct.",
        "The bit-vector version is a common follow-up for lowercase `a`-`z` only.",
    ],
    "companies": [],
    "topics": ["String", "Hash Set", "Array"],
    "time_complexity": "O(n)",
    "space_complexity": "O(min(n, charset))",
}


def REFERENCE(s):
    if len(s) > 128:
        return False
    seen = [False] * 128
    for ch in s:
        idx = ord(ch)
        if idx >= 128:
            return len(set(s)) == len(s)
        if seen[idx]:
            return False
        seen[idx] = True
    return True


register(PAYLOAD, REFERENCE)
