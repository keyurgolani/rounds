"""Check Permutation — Easy. String / Hash Table.

Determining whether two strings are permutations of each other.
The canonical solutions are character counting (optimal O(n)),
sorting (simpler but O(n log n)), and the length short-circuit
that makes both faster in practice. The main pitfall is confusing
a set check with a multiset check.
"""
from collections import Counter

from builder.registry import register


PAYLOAD = {
    "title": "Check Permutation",
    "difficulty": "Easy",
    "description": (
        "Given two strings, decide whether one string is a permutation of the other. A permutation must contain "
        "exactly the same characters with exactly the same counts."
    ),
    "hints": [
        "If the strings have different lengths, they cannot be permutations.",
        "Sorting both strings makes equal character multisets line up at the same indices.",
        "A character-count map gives O(n) time by incrementing for one string and decrementing for the other.",
        "Be precise about spaces and case; this version treats every character literally.",
    ],
    "constraints": ["0 <= s1.length, s2.length <= 10^5", "Characters are case-sensitive"],
    "starter_code": {
        "python": "def check_permutation(s1, s2):\n    # Your code here\n    pass",
        "javascript": "function checkPermutation(s1, s2) {\n    // Your code here\n}",
        "java": "public boolean checkPermutation(String s1, String s2) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(check_permutation(\"abcd\", \"bacd\"))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "console.log(checkPermutation(\"abcd\", \"bacd\"));"
        ),
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"s1": "abcd", "s2": "bacd"}, "expected": True,
         "description": "Simple permutation", "tags": ["basic"]},
        {"input": {"s1": "3563476", "s2": "7334566"}, "expected": True,
         "description": "Repeated digits with same counts", "tags": ["basic"]},
        {"input": {"s1": "abcd", "s2": "d2cba"}, "expected": False,
         "description": "Extra different character", "tags": ["basic"]},
        {"input": {"s1": "ba", "s2": "Ab"}, "expected": False,
         "description": "Case-sensitive mismatch", "tags": ["tricky"]},
        {"input": {"s1": "anne", "s2": "annea"}, "expected": False,
         "description": "Different lengths", "tags": ["edge"]},
        {"input": {"s1": "", "s2": ""}, "expected": True,
         "description": "Two empty strings", "tags": ["edge"]},
        {"input": {"s1": "IAMLORDVOLDEMORT", "s2": "TOMMARVOLORIDDLE"}, "expected": True,
         "description": "Same multiset with different order", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Character Counts",
            "time_complexity": "O(n)",
            "space_complexity": "O(min(n, charset))",
            "description": "Count characters in the first string, then subtract using the second. Any missing or overused character fails.",
            "code": {
                "python": (
                    "from collections import Counter\n\n"
                    "def check_permutation(s1, s2):\n"
                    "    if len(s1) != len(s2):\n"
                    "        return False\n"
                    "    return Counter(s1) == Counter(s2)"
                ),
                "javascript": (
                    "function checkPermutation(s1, s2) {\n"
                    "    if (s1.length !== s2.length) return false;\n"
                    "    const counts = new Map();\n"
                    "    for (const ch of s1) counts.set(ch, (counts.get(ch) || 0) + 1);\n"
                    "    for (const ch of s2) {\n"
                    "        const next = (counts.get(ch) || 0) - 1;\n"
                    "        if (next < 0) return false;\n"
                    "        counts.set(ch, next);\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sort and Compare",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": "Sorting canonicalizes the order, so permutations become identical sorted strings.",
            "code": {
                "python": (
                    "def check_permutation(s1, s2):\n"
                    "    return len(s1) == len(s2) and sorted(s1) == sorted(s2)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Length mismatch is the cheapest rejection and avoids wasted work.",
        "2. A permutation means equal character counts, not just the same set of characters.",
        "3. Sorting is easy to explain but costs O(n log n). Counting is the optimal O(n) approach.",
        "4. Edge cases are usually policy questions: case, whitespace, and Unicode normalization.",
    ],
    "tips": [
        "A set comparison is wrong: `aab` and `abb` have the same set but different counts.",
        "Do not normalize case or strip spaces unless the interviewer explicitly asks for it.",
        "For fixed ASCII, use an integer array instead of a hash map if you want deterministic constant space.",
    ],
    "companies": [],
    "topics": ["String", "Hash Table", "Sorting"],
    "time_complexity": "O(n)",
    "space_complexity": "O(min(n, charset))",
}


def REFERENCE(s1, s2):
    return len(s1) == len(s2) and Counter(s1) == Counter(s2)


register(PAYLOAD, REFERENCE)
