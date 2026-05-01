"""Isomorphic Word Groups — Medium. String / Hash.

Group words such that each group consists of mutually-isomorphic
strings. Canonicalise each word to its 'pattern signature' and group
by it."""
from builder.registry import register
from builder.registry import unordered_deep


PAYLOAD = {
    "title": "Group Isomorphic Words",
    "difficulty": "Medium",
    "description": (
        "Two strings are **isomorphic** if you can replace each character in one with another (consistently "
        "across the string, distinct chars map to distinct chars) to obtain the other. Group an input "
        "list of words such that each group contains mutually-isomorphic words.\n\n"
        "Examples of isomorphic word pairs: `('aab', 'xxy')`, `('paper', 'title')`, `('foo', 'bar')` "
        "(both have signature `[0, 1, 1]`).\n\n"
        "**Output:** a list of groups (each group is a list of words). Group order is not specified; "
        "within-group order is not specified.\n\n"
        "**Example:**\n"
        "- Input: `['aab', 'xxy', 'xyy', 'abc', 'def']`\n"
        "- Output (one valid): `[['aab', 'xxy'], ['xyy'], ['abc', 'def']]`"
    ),
    "hints": [
        "Canonical signature: replace each character with the index of its first occurrence. `'aab' → [0, 0, 1]`. `'xxy' → [0, 0, 1]`. Same signature = isomorphic.",
        "Tuple-of-ints (or string) signature can be used as a hash-map key.",
        "Brute-force pairwise check is O(n² · L); signature-based grouping is O(n · L).",
        "Edge cases: empty list, single-character words (every length-1 word is in the same group), distinct-char words (every word with all-unique chars groups together regardless of letter).",
    ],
    "constraints": [
        "0 <= |words| <= 10⁴",
        "1 <= word.length <= 100",
        "Lowercase ASCII",
    ],
    "starter_code": {
        "python": "def group_isomorphic(words):\n    # Your code here\n    pass",
        "javascript": "function groupIsomorphic(words) {\n    // Your code here\n}",
        "java": "public List<List<String>> groupIsomorphic(List<String> words) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(group_isomorphic(['aab', 'xxy', 'xyy', 'abc', 'def']))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"words": ["aab", "xxy", "xyy", "abc", "def"]},
         "expected": unordered_deep([["aab", "xxy"], ["xyy"], ["abc", "def"]]),
         "description": "Three groups", "tags": ["basic"]},
        {"input": {"words": []}, "expected": [],
         "description": "Empty input", "tags": ["edge"]},
        {"input": {"words": ["a"]}, "expected": [["a"]],
         "description": "Single word", "tags": ["edge"]},
        {"input": {"words": ["ab", "cd", "ef"]},
         "expected": unordered_deep([["ab", "cd", "ef"]]),
         "description": "All distinct-char 2-letter words → same signature [0,1]",
         "tags": ["edge"]},
        {"input": {"words": ["paper", "title"]},
         "expected": unordered_deep([["paper", "title"]]),
         "description": "Classic isomorphic pair", "tags": ["basic"]},
        {"input": {"words": ["a", "bb"]},
         "expected": unordered_deep([["a"], ["bb"]]),
         "description": "Different lengths → different groups", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Pattern Signature Grouping (Optimal)",
            "time_complexity": "O(n · L)",
            "space_complexity": "O(n · L)",
            "description": (
                "For each word, compute its signature (each char → index of first occurrence). Group "
                "words by signature using a dict. Linear in total characters."
            ),
            "code": {
                "python": (
                    "from collections import defaultdict\n\n"
                    "def group_isomorphic(words):\n"
                    "    groups = defaultdict(list)\n"
                    "    for w in words:\n"
                    "        sig = _signature(w)\n"
                    "        groups[sig].append(w)\n"
                    "    return list(groups.values())\n\n"
                    "def _signature(s):\n"
                    "    seen = {}\n"
                    "    out = []\n"
                    "    for c in s:\n"
                    "        if c not in seen:\n"
                    "            seen[c] = len(seen)\n"
                    "        out.append(seen[c])\n"
                    "    return tuple(out)"
                ),
                "javascript": (
                    "function groupIsomorphic(words) {\n"
                    "    const groups = new Map();\n"
                    "    for (const w of words) {\n"
                    "        const seen = {};\n"
                    "        let n = 0;\n"
                    "        const sig = [];\n"
                    "        for (const c of w) {\n"
                    "            if (!(c in seen)) seen[c] = n++;\n"
                    "            sig.push(seen[c]);\n"
                    "        }\n"
                    "        const k = sig.join(',');\n"
                    "        if (!groups.has(k)) groups.set(k, []);\n"
                    "        groups.get(k).push(w);\n"
                    "    }\n"
                    "    return [...groups.values()];\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Reframe: 'is_isomorphic(a, b)' is symmetric and transitive — equivalence relation. Equivalence classes are the groups.",
        "2. Need a canonical representative per class. Pattern signature: each char → index of first occurrence.",
        "3. Group words by signature using a dict.",
        "4. O(n · L) — linear in total characters.",
        "5. Edge cases: empty input, single word, all-different-length words, all-distinct-char words (same signature).",
    ],
    "tips": [
        "The signature must be hashable. Tuple of ints in Python; comma-joined string in JS.",
        "Don't compute pairwise isomorphism — that's O(n² · L). The signature trick is the win.",
        "Common follow-up: 'are all words rotationally equivalent?' Different equivalence relation; canonical form is `min(rotation)`.",
        "Common follow-up: 'streaming words.' Same hash-map approach; emit groups on-demand.",
        "Common follow-up: 'count groups, not list them.' Same dict; return `len(groups)`.",
    ],
    "companies": ["Amazon", "Microsoft"],
    "topics": ["String", "Hash Table", "Equivalence Class"],
    "time_complexity": "O(n · L)",
    "space_complexity": "O(n · L)",
}


def REFERENCE(words):
    from collections import defaultdict
    groups = defaultdict(list)
    for w in words:
        seen = {}
        out = []
        for c in w:
            if c not in seen:
                seen[c] = len(seen)
            out.append(seen[c])
        groups[tuple(out)].append(w)
    return list(groups.values())


register(PAYLOAD, REFERENCE)
