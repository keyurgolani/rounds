"""Hamming Distance Between DNA Strands — Easy. String, Counting.

Walk two equal-length strands in lockstep and count mismatches.
The pitfall is confusing this with set difference — order and
repeated positions matter.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Hamming Distance Between DNA Strands",
    "difficulty": "Easy",
    "description": (
        "Given two equal-length DNA strands, return the number of positions where their nucleotides differ."
    ),
    "hints": [
        "Compare the strands position by position.",
        "Increment the count only when the characters differ.",
        "The distance between identical strands is zero, including two empty strands.",
        "The original Exercism exercise raises on unequal lengths; these app tests use equal-length strands.",
    ],
    "constraints": ["0 <= left.length = right.length <= 10^5"],
    "starter_code": {
        "python": "def hamming_distance(left, right):\n    # Your code here\n    pass",
        "javascript": "function hammingDistance(left, right) {\n    // Your code here\n}",
        "java": "public int hammingDistance(String left, String right) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": "# Test runner (read-only)\nif __name__ == \"__main__\":\n    print(hamming_distance(\"GATACA\", \"GCATAA\"))",
        "javascript": "// Test runner (read-only)\nconsole.log(hammingDistance(\"GATACA\", \"GCATAA\"));",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"left": "", "right": ""}, "expected": 0, "description": "Empty strands", "tags": ["edge"]},
        {"input": {"left": "A", "right": "A"}, "expected": 0, "description": "Identical one-character strands", "tags": ["basic"]},
        {"input": {"left": "A", "right": "G"}, "expected": 1, "description": "Single mismatch", "tags": ["basic"]},
        {"input": {"left": "AG", "right": "CT"}, "expected": 2, "description": "Complete distance", "tags": ["basic"]},
        {"input": {"left": "ACCAGGG", "right": "ACTATGG"}, "expected": 2, "description": "Small distance in longer strands", "tags": ["basic"]},
        {"input": {"left": "GATACA", "right": "GCATAA"}, "expected": 4, "description": "Large distance", "tags": ["tricky"]},
    ],
    "solutions": [{
        "title": "Zip and Count Mismatches",
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "description": "Walk both strings together and count positions where the characters differ.",
        "code": {
            "python": "def hamming_distance(left, right):\n    return sum(a != b for a, b in zip(left, right))",
            "javascript": "function hammingDistance(left, right) {\n    let count = 0;\n    for (let i = 0; i < left.length; i++) if (left[i] !== right[i]) count++;\n    return count;\n}",
        },
    }],
    "thought_process": [
        "1. Confirm the equal-length precondition; otherwise the term Hamming distance is undefined.",
        "2. Iterate through paired characters with an index or `zip`.",
        "3. Count positions where the pair differs.",
        "4. Return the count after scanning all positions.",
    ],
    "tips": [
        "If unequal lengths are allowed, validate before the loop and reject early.",
        "Do not use set difference; repeated positions and order matter.",
        "This DNA-strand exercise is different from the bitwise LeetCode Hamming Distance problem, although both count differing positions.",
    ],
    "companies": [],
    "topics": ["String", "Counting"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(left, right):
    return sum(a != b for a, b in zip(left, right))


register(PAYLOAD, REFERENCE)
