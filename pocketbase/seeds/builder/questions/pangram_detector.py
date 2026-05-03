"""Pangram Detector — Easy. String, Set.

Collect normalized lowercase letters into a set and check for all
26. The subtle point is ignoring digits and punctuation — numbers
that look like letters (7 for T, 3 for E) do not count.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Pangram Detector",
    "difficulty": "Easy",
    "description": (
        "Return whether a sentence is a pangram: it must contain every letter from `a` through `z` at least once, "
        "case-insensitively. Ignore numbers, spaces, and punctuation."
    ),
    "hints": [
        "Normalize to lowercase so `A` and `a` count as the same letter.",
        "Track only alphabetic characters from `a` through `z`; ignore digits, spaces, underscores, and punctuation.",
        "A set size of 26 is enough to prove the sentence is a pangram.",
        "You can return early once all 26 letters have appeared.",
    ],
    "constraints": ["0 <= sentence.length <= 10^5"],
    "starter_code": {
        "python": "def is_pangram(sentence):\n    # Your code here\n    pass",
        "javascript": "function isPangram(sentence) {\n    // Your code here\n}",
        "java": "public boolean isPangram(String sentence) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": "# Test runner (read-only)\nif __name__ == \"__main__\":\n    print(is_pangram(\"the quick brown fox jumps over the lazy dog\"))",
        "javascript": "// Test runner (read-only)\nconsole.log(isPangram(\"the quick brown fox jumps over the lazy dog\"));",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"sentence": ""}, "expected": False, "description": "Empty sentence", "tags": ["edge"]},
        {"input": {"sentence": "abcdefghijklmnopqrstuvwxyz"}, "expected": True, "description": "Perfect lowercase pangram", "tags": ["basic"]},
        {"input": {"sentence": "the quick brown fox jumps over the lazy dog"}, "expected": True, "description": "Classic pangram", "tags": ["basic"]},
        {"input": {"sentence": "a quick movement of the enemy will jeopardize five gunboats"}, "expected": False, "description": "Missing x", "tags": ["basic"]},
        {"input": {"sentence": "the_quick_brown_fox_jumps_over_the_lazy_dog"}, "expected": True, "description": "Underscores ignored", "tags": ["edge"]},
        {"input": {"sentence": "the 1 quick brown fox jumps over the 2 lazy dogs"}, "expected": True, "description": "Numbers ignored", "tags": ["edge"]},
        {"input": {"sentence": "7h3 qu1ck brown fox jumps ov3r 7h3 lazy dog"}, "expected": False, "description": "Numbers do not substitute for letters", "tags": ["tricky"]},
        {"input": {"sentence": "\"Five quacking Zephyrs jolt my wax bed.\""}, "expected": True, "description": "Mixed case and punctuation", "tags": ["tricky"]},
    ],
    "solutions": [{
        "title": "Letter Set",
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "description": "Collect normalized letters into a set and check whether all 26 letters appear.",
        "code": {
            "python": "def is_pangram(sentence):\n    letters = {ch for ch in sentence.lower() if 'a' <= ch <= 'z'}\n    return len(letters) == 26",
            "javascript": "function isPangram(sentence) {\n    const letters = new Set();\n    for (const ch of sentence.toLowerCase()) {\n        if (ch >= 'a' && ch <= 'z') letters.add(ch);\n    }\n    return letters.size === 26;\n}",
        },
    }],
    "thought_process": [
        "1. Lowercase the sentence to make matching case-insensitive.",
        "2. Ignore non-letter characters instead of treating them as failures.",
        "3. Track unique letters in a set.",
        "4. Return true when the set has 26 letters; otherwise return false after the scan.",
    ],
    "tips": [
        "Do not use `isalnum`; digits should be ignored, not counted.",
        "Numbers that look like letters, such as `7` for `t` or `3` for `e`, do not count.",
        "If the interviewer asks about Unicode, clarify whether the alphabet is strictly English `a-z` or locale-aware.",
        "An array of 26 booleans works just as well as a set and gives fixed O(1) space.",
    ],
    "companies": [],
    "topics": ["String", "Set"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(sentence):
    letters = {ch for ch in sentence.lower() if "a" <= ch <= "z"}
    return len(letters) == 26


register(PAYLOAD, REFERENCE)
