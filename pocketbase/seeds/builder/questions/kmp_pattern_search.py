"""KMP Pattern Search — Medium. String, KMP, Pattern Matching.

Build the longest-prefix-suffix table once, then scan text in a
single pass. The key insight is falling back to lps[j-1] on
mismatch instead of restarting from zero — overlapping matches
like "ababa"/"aba" catch the common reset-to-zero bug.
"""
from builder.registry import register


PAYLOAD = {
    "title": "KMP Pattern Search",
    "difficulty": "Medium",
    "description": (
        "Implement Knuth-Morris-Pratt substring search. Given `text` and `pattern`, return every start "
        "index where `pattern` appears in `text`.\n\n"
        "The KMP prefix table lets you avoid re-checking characters after a partial match fails."
    ),
    "hints": [
        "Start with the naive baseline: try matching the pattern at every text index, which can repeat work after partial matches fail.",
        "Build `lps[i]`, the length of the longest proper prefix of `pattern[:i + 1]` that is also a suffix.",
        "When a mismatch occurs after matching `j` characters, fall back to `lps[j - 1]` instead of restarting at zero.",
        "After recording a match, fall back to `lps[j - 1]` so overlapping matches are included.",
        "Keep the `text` pointer moving forward; only the `pattern` pointer jumps backward.",
    ],
    "constraints": [
        "0 <= text.length <= 10^5",
        "0 <= pattern.length <= 10^5",
        "Return an empty list when `pattern` is empty.",
    ],
    "starter_code": {
        "python": "def kmp_search(text, pattern):\n    # Your code here\n    pass",
        "javascript": "function kmpSearch(text, pattern) {\n    // Your code here\n}",
        "java": "public List<Integer> kmpSearch(String text, String pattern) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": "# Test runner (read-only)\nif __name__ == \"__main__\":\n    print(kmp_search(\"ababa\", \"aba\"))",
        "javascript": "// Test runner (read-only)\nconsole.log(kmpSearch(\"ababa\", \"aba\"));",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"text": "ababa", "pattern": "aba"}, "expected": [0, 2], "description": "Overlapping matches", "tags": ["basic", "tricky"]},
        {"input": {"text": "aaaaa", "pattern": "aa"}, "expected": [0, 1, 2, 3], "description": "Dense overlap", "tags": ["tricky"]},
        {"input": {"text": "hello world", "pattern": "world"}, "expected": [6], "description": "Single match near the end", "tags": ["basic"]},
        {"input": {"text": "abcdef", "pattern": "gh"}, "expected": [], "description": "No match", "tags": ["edge"]},
        {"input": {"text": "abc", "pattern": ""}, "expected": [], "description": "Empty pattern", "tags": ["edge"]},
        {"input": {"text": "", "pattern": "a"}, "expected": [], "description": "Empty text", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "KMP Prefix Table",
            "time_complexity": "O(n + m)",
            "space_complexity": "O(m)",
            "description": "Precompute fallback positions for the pattern, then scan the text once.",
            "code": {
                "python": (
                    "def kmp_search(text, pattern):\n"
                    "    if not pattern:\n"
                    "        return []\n"
                    "    lps = [0] * len(pattern)\n"
                    "    j = 0\n"
                    "    for i in range(1, len(pattern)):\n"
                    "        while j > 0 and pattern[i] != pattern[j]:\n"
                    "            j = lps[j - 1]\n"
                    "        if pattern[i] == pattern[j]:\n"
                    "            j += 1\n"
                    "            lps[i] = j\n"
                    "    out = []\n"
                    "    j = 0\n"
                    "    for i, ch in enumerate(text):\n"
                    "        while j > 0 and ch != pattern[j]:\n"
                    "            j = lps[j - 1]\n"
                    "        if ch == pattern[j]:\n"
                    "            j += 1\n"
                    "            if j == len(pattern):\n"
                    "                out.append(i - j + 1)\n"
                    "                j = lps[j - 1]\n"
                    "    return out"
                ),
                "javascript": (
                    "function kmpSearch(text, pattern) {\n"
                    "    if (pattern.length === 0) return [];\n"
                    "    const lps = Array(pattern.length).fill(0);\n"
                    "    let j = 0;\n"
                    "    for (let i = 1; i < pattern.length; i++) {\n"
                    "        while (j > 0 && pattern[i] !== pattern[j]) j = lps[j - 1];\n"
                    "        if (pattern[i] === pattern[j]) lps[i] = ++j;\n"
                    "    }\n"
                    "    const out = [];\n"
                    "    j = 0;\n"
                    "    for (let i = 0; i < text.length; i++) {\n"
                    "        while (j > 0 && text[i] !== pattern[j]) j = lps[j - 1];\n"
                    "        if (text[i] === pattern[j] && ++j === pattern.length) {\n"
                    "            out.push(i - j + 1);\n"
                    "            j = lps[j - 1];\n"
                    "        }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. State the naive baseline and why it repeats comparisons after a partial match.",
        "2. Define the prefix table in plain language: where can the pattern resume if the current candidate fails?",
        "3. Build `lps` with the same fallback idea used during the search.",
        "4. Scan text once. On match, advance both logical pointers; on mismatch, move only the pattern pointer using `lps`.",
        "5. After a full match, append `i - len(pattern) + 1` and fall back instead of clearing state, so overlaps work.",
    ],
    "tips": [
        "The overlap case `text=ababa`, `pattern=aba` catches the common reset-to-zero bug.",
        "Use `aaaaa` / `aa` to test dense overlaps and `abcdef` / `gh` to test no-match behavior.",
        "Define empty-pattern behavior before coding; this app expects an empty result.",
        "Do not increment the text index inside a mismatch fallback loop; that skips potential matches.",
        "If the interviewer asks where KMP is useful, cite streaming search, plagiarism checks, DNA/string matching, and log scanning.",
    ],
    "companies": [],
    "topics": ["String", "KMP", "Pattern Matching"],
    "time_complexity": "O(n + m)",
    "space_complexity": "O(m)",
}


def REFERENCE(text, pattern):
    if not pattern:
        return []
    lps = [0] * len(pattern)
    j = 0
    for i in range(1, len(pattern)):
        while j > 0 and pattern[i] != pattern[j]:
            j = lps[j - 1]
        if pattern[i] == pattern[j]:
            j += 1
            lps[i] = j
    out = []
    j = 0
    for i, ch in enumerate(text):
        while j > 0 and ch != pattern[j]:
            j = lps[j - 1]
        if ch == pattern[j]:
            j += 1
            if j == len(pattern):
                out.append(i - j + 1)
                j = lps[j - 1]
    return out


register(PAYLOAD, REFERENCE)
