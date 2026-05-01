"""Palindrome Substring Pairs — Hard. String / Hashing.

Count pairs of substrings (s[i..j], s[k..l]) that are reverses of each
other. Brute force is O(n^6). Smart counting groups substrings by
canonical representation; hashing or rolling hashes get to O(n²)."""
from builder.registry import register


PAYLOAD = {
    "title": "Count Palindrome Pairs Among Substrings",
    "difficulty": "Hard",
    "description": (
        "Given a string `s`, count the number of **ordered pairs** of substrings `(a, b)` of `s` such that "
        "`a` is the reverse of `b` (and `a != b` as substrings — different positions in `s`). Each substring "
        "is identified by its (start, end) position; the same substring text at different positions counts "
        "as a distinct entity.\n\n"
        "**Example:**\n"
        "- Input: `s = 'abba'`\n"
        "- Output: `4`\n"
        "- The four pairs are:\n"
        "  - `(s[0:1] = 'a', s[3:4] = 'a')` — same letter, palindrome of length 1\n"
        "  - `(s[1:2] = 'b', s[2:3] = 'b')`\n"
        "  - `(s[0:2] = 'ab', s[2:4] = 'ba')`\n"
        "  - `(s[0:3] = 'abb', s[1:4] = 'bba')`\n\n"
        "Each pair is counted once (unordered)."
    ),
    "hints": [
        "Brute force: enumerate all O(n²) substrings on each side, compare reverses → O(n^6) including string ops. State and reject.",
        "Group substrings by a canonical 'length + sorted-multiset' key — but that overcounts (e.g. 'abc' and 'cab' have the same multiset, aren't reverses).",
        "Correct grouping: hash the substring `s[i..j]` and the reverse `s[j..i]` together. Pairs match iff one is the reverse of the other; so for each substring t, count substrings whose text equals reversed(t) at a different position.",
        "Build a frequency map `text → count_of_positions`. For each substring t, the pair count contribution is `freq[reversed(t)]`. Sum and divide by 2 to undo double counting.",
        "Substring extraction is O(L) — the practical bound is O(n²) (number of substrings) × O(n) for substring + reverse + hash = O(n³). Rolling hashes get this to O(n²) but the constant is large.",
        "Edge cases: empty string (0), single char (0 — needs distinct positions), all identical chars.",
    ],
    "constraints": [
        "1 <= |s| <= 1000",
        "Lowercase ASCII",
    ],
    "starter_code": {
        "python": "def palindrome_pairs(s):\n    # Your code here\n    pass",
        "javascript": "function palindromePairs(s) {\n    // Your code here\n}",
        "java": "public int palindromePairs(String s) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(palindrome_pairs('abba'))   # 4"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"s": "abba"}, "expected": 4,
         "description": "Standard example", "tags": ["basic"]},
        {"input": {"s": "aaa"}, "expected": 4,
         "description": "Three single-char 'a-a' pairs + one 'aa-aa' pair across overlapping positions",
         "tags": ["basic"]},
        {"input": {"s": ""}, "expected": 0,
         "description": "Empty string", "tags": ["edge"]},
        {"input": {"s": "a"}, "expected": 0,
         "description": "Single char — no distinct-position pair possible", "tags": ["edge"]},
        {"input": {"s": "abcd"}, "expected": 0,
         "description": "All distinct chars — no palindrome pairs", "tags": ["edge"]},
        {"input": {"s": "abab"}, "expected": 4,
         "description": "Two 'a's, two 'b's, plus 'ab' / 'ba' overlapping pairs",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Hash Map of Substrings (Practical)",
            "time_complexity": "O(n³)",
            "space_complexity": "O(n²)",
            "description": (
                "Enumerate every substring (i, j) and store it in a frequency map keyed by text. For each "
                "substring t, look up `freq[reversed(t)]` and add to the running total. Divide by 2 at the "
                "end to avoid double-counting (each pair is found from both sides). Watch for self-pairs "
                "(t == reversed(t) at the SAME position) — those don't count."
            ),
            "code": {
                "python": (
                    "from collections import defaultdict\n\n"
                    "def palindrome_pairs(s):\n"
                    "    n = len(s)\n"
                    "    pos_by_text = defaultdict(list)\n"
                    "    for i in range(n):\n"
                    "        for j in range(i + 1, n + 1):\n"
                    "            pos_by_text[s[i:j]].append((i, j))\n"
                    "    total = 0\n"
                    "    for text, positions in pos_by_text.items():\n"
                    "        rev = text[::-1]\n"
                    "        if rev not in pos_by_text:\n"
                    "            continue\n"
                    "        rev_positions = pos_by_text[rev]\n"
                    "        for p in positions:\n"
                    "            for q in rev_positions:\n"
                    "                if p != q:\n"
                    "                    total += 1\n"
                    "    return total // 2"
                ),
            },
        },
        {
            "title": "Rolling Hash (Optimal)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(n²)",
            "description": (
                "Precompute polynomial rolling hashes of `s` and reversed-`s`. Each substring hash is "
                "O(1) lookup once the prefix-hash array is built. Compare hashes of (i, j) and the "
                "corresponding reversed range; equal hashes (with double-hash to avoid collisions) means "
                "the substrings are reverses of each other."
            ),
            "code": {
                "python": (
                    "# Sketch — full implementation requires double hashing for collision safety.\n"
                    "def palindrome_pairs(s):\n"
                    "    raise NotImplementedError(\n"
                    "        'Use polynomial rolling hashes on s and rev(s).\\n'\n"
                    "        'For each substring (i,j) of length L, the hash of s[i:j] and '\n"
                    "        'the hash of rev(s)[i_rev:j_rev] match when one is the reverse of the other.\\n'\n"
                    "        'Pair counting then requires a 2D lookup; the implementation is finicky.'\n"
                    "    )"
                ),
            },
        },
    ],
    "thought_process": [
        "1. State the naive enumeration: O(n²) substrings on the left × O(n²) on the right × O(n) compare = O(n^5) at best. Reject for n = 1000.",
        "2. Reformulate: 'pair (a, b) with a == reversed(b)' is equivalent to 'for each substring a, count substrings whose text equals reversed(a)'.",
        "3. Build a frequency map keyed on substring text. Then per-substring lookup is O(L).",
        "4. Watch the double-counting: pair (a, b) is found once from a's perspective and once from b's. Divide by 2.",
        "5. Self-position exclusion: don't count the same position pair as a 'pair'.",
        "6. For tighter bounds, polynomial rolling hashes drop substring extraction to O(1) — bringing the total to O(n²).",
    ],
    "tips": [
        "Watch off-by-one: substring `s[i:j]` is valid for `0 <= i < j <= n`. The (i, j) end is exclusive.",
        "If memory is tight, you can avoid materialising every substring by hashing them directly into the frequency map.",
        "Single-char palindromes are a degenerate case worth thinking about — every pair of identical letters at distinct positions counts.",
        "Common follow-up: 'count distinct palindrome pair *texts*' — different problem; group by canonical text, not position.",
        "Common follow-up: 'longest palindrome formable from any pair concatenation' — see Manacher's algorithm.",
    ],
    "companies": ["Amazon", "Google"],
    "topics": ["String", "Hash Table", "Rolling Hash"],
    "time_complexity": "O(n³) practical, O(n²) with rolling hash",
    "space_complexity": "O(n²)",
}


def REFERENCE(s):
    from collections import defaultdict
    n = len(s)
    pos_by_text = defaultdict(list)
    for i in range(n):
        for j in range(i + 1, n + 1):
            pos_by_text[s[i:j]].append((i, j))
    total = 0
    for text, positions in pos_by_text.items():
        rev = text[::-1]
        if rev not in pos_by_text:
            continue
        rev_positions = pos_by_text[rev]
        for p in positions:
            for q in rev_positions:
                if p != q:
                    total += 1
    return total // 2


register(PAYLOAD, REFERENCE)
