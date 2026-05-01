"""Distinct Subsequences — Hard. 2D DP on two strings.

The canonical 'count subsequence matches' DP. Same skeleton as Edit
Distance / LCS but the recurrence counts paths instead of optimising
length. The trap: it's *subsequences*, not substrings — characters can
be skipped in s but order is preserved. The 1D rolling variant is the
standard interview optimisation; iterate j *backwards* to keep the
previous row's value alive.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Distinct Subsequences",
    "difficulty": "Hard",
    "description": (
        "Given two strings `s` and `t`, return the **number of distinct subsequences** of `s` which equal `t`.\n\n"
        "A subsequence of a string is a new string formed from the original string by deleting some "
        "(can be none) of the characters without disturbing the relative positions of the remaining characters. "
        "(For example, `\"ACE\"` is a subsequence of `\"ABCDE\"` while `\"AEC\"` is not.)\n\n"
        "The test cases are guaranteed to fit in a 32-bit signed integer.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"rabbbit\", t = \"rabbit\"`\n"
        "- Output: `3`\n"
        "- Explanation: There are 3 ways you can generate `\"rabbit\"` from `\"rabbbit\"` by deleting one of "
        "the three `b`'s (positions 2, 3, or 4 in `s`).\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"babgbag\", t = \"bag\"`\n"
        "- Output: `5`\n"
        "- Explanation: The 5 distinct subsequences of `s` equal to `\"bag\"` come from picking different "
        "combinations of `b`, `a`, `g` indices: (0,1,2), (0,1,6), (0,4,6), (3,4,6), (0,1,5)... 5 in total."
    ),
    "hints": [
        "Define `dp[i][j]` = number of distinct subsequences of `s[0..i-1]` that equal `t[0..j-1]`. The answer is `dp[m][n]`.",
        "Base cases: `dp[i][0] = 1` for all `i` (empty `t` matches the empty subsequence — exactly one way). `dp[0][j] = 0` for `j > 0` (empty `s` cannot form non-empty `t`).",
        "Recurrence — when `s[i-1] == t[j-1]`: you can either *use* `s[i-1]` to match `t[j-1]` (`dp[i-1][j-1]` ways) or *skip* `s[i-1]` (`dp[i-1][j]` ways). Sum them: `dp[i][j] = dp[i-1][j-1] + dp[i-1][j]`.",
        "When `s[i-1] != t[j-1]`: you must skip `s[i-1]`, so `dp[i][j] = dp[i-1][j]`.",
        "Space optimisation: each row only depends on the previous row, so use a 1D array of size `n+1`. **Iterate `j` from right to left** so `dp[j-1]` still holds the previous row's value when you read it.",
    ],
    "constraints": [
        "1 <= s.length, t.length <= 1000",
        "s and t consist of English letters",
        "Answer is guaranteed to fit in a 32-bit signed integer",
    ],
    "starter_code": {
        "python": "def num_distinct(s, t):\n    # Your code here\n    pass",
        "javascript": "function numDistinct(s, t) {\n    // Your code here\n}",
        "java": "public int numDistinct(String s, String t) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(\"rabbbit\", \"rabbit\"), (\"babgbag\", \"bag\"), (\"abc\", \"\")]\n"
            "    for s, t in cases:\n"
            "        print(f\"num_distinct({s!r}, {t!r}) = {num_distinct(s, t)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[\"rabbbit\", \"rabbit\"], [\"babgbag\", \"bag\"]].forEach(([s, t]) =>\n"
            "    console.log(`numDistinct(${s}, ${t}) =`, numDistinct(s, t))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution sol = new Solution();\n"
            "        System.out.println(sol.numDistinct(\"rabbbit\", \"rabbit\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "rabbbit", "t": "rabbit"}, "expected": 3,
         "description": "Classic LC example — 3 ways via the three b's", "tags": ["basic"]},
        {"input": {"s": "babgbag", "t": "bag"}, "expected": 5,
         "description": "Classic LC example — 5 distinct (b,a,g) index triples", "tags": ["basic"]},
        {"input": {"s": "abc", "t": ""}, "expected": 1,
         "description": "Empty t — exactly one way (delete everything)", "tags": ["edge"]},
        {"input": {"s": "ab", "t": "abc"}, "expected": 0,
         "description": "t longer than s — impossible", "tags": ["edge"]},
        {"input": {"s": "abc", "t": "abc"}, "expected": 1,
         "description": "Identical strings — only one subsequence equals t", "tags": ["edge"]},
        {"input": {"s": "aaaa", "t": "aa"}, "expected": 6,
         "description": "Choose 2 of 4 identical chars — C(4,2) = 6", "tags": ["tricky"]},
        {"input": {"s": "aaaaa", "t": "a"}, "expected": 5,
         "description": "Five identical chars, pick one — 5 ways", "tags": ["tricky"]},
        {"input": {"s": "", "t": ""}, "expected": 1,
         "description": "Both empty — one way (the empty subsequence)", "tags": ["edge"]},
        {"input": {"s": "abcabc", "t": "abc"}, "expected": 4,
         "description": "Multiple overlapping matches", "tags": ["tricky"]},
        {"input": {"s": "xyz", "t": "a"}, "expected": 0,
         "description": "No character of t appears in s", "tags": ["edge"]},
        {"input": {"s": "a" * 100, "t": "a" * 10}, "expected": 17310309456440,
         "description": "C(100, 10) — large binomial; tests big integer correctness", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "2D DP (Optimal, Clearest)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Build `dp[i][j]` = number of subsequences of `s[0..i-1]` equal to `t[0..j-1]`. "
                "Initialise the first column to 1 (empty `t` is always matchable). For each cell, if "
                "`s[i-1] == t[j-1]` add `dp[i-1][j-1] + dp[i-1][j]`; otherwise inherit `dp[i-1][j]`. "
                "Return `dp[m][n]`."
            ),
            "code": {
                "python": (
                    "def num_distinct(s, t):\n"
                    "    m, n = len(s), len(t)\n"
                    "    dp = [[0] * (n + 1) for _ in range(m + 1)]\n"
                    "    for i in range(m + 1):\n"
                    "        dp[i][0] = 1\n"
                    "    for i in range(1, m + 1):\n"
                    "        for j in range(1, n + 1):\n"
                    "            if s[i - 1] == t[j - 1]:\n"
                    "                dp[i][j] = dp[i - 1][j - 1] + dp[i - 1][j]\n"
                    "            else:\n"
                    "                dp[i][j] = dp[i - 1][j]\n"
                    "    return dp[m][n]"
                ),
                "javascript": (
                    "function numDistinct(s, t) {\n"
                    "    const m = s.length, n = t.length;\n"
                    "    const dp = Array.from({length: m + 1}, () => new Array(n + 1).fill(0));\n"
                    "    for (let i = 0; i <= m; i++) dp[i][0] = 1;\n"
                    "    for (let i = 1; i <= m; i++) {\n"
                    "        for (let j = 1; j <= n; j++) {\n"
                    "            if (s[i - 1] === t[j - 1]) {\n"
                    "                dp[i][j] = dp[i - 1][j - 1] + dp[i - 1][j];\n"
                    "            } else {\n"
                    "                dp[i][j] = dp[i - 1][j];\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[m][n];\n"
                    "}"
                ),
                "java": (
                    "public int numDistinct(String s, String t) {\n"
                    "    int m = s.length(), n = t.length();\n"
                    "    long[][] dp = new long[m + 1][n + 1];\n"
                    "    for (int i = 0; i <= m; i++) dp[i][0] = 1;\n"
                    "    for (int i = 1; i <= m; i++) {\n"
                    "        for (int j = 1; j <= n; j++) {\n"
                    "            if (s.charAt(i - 1) == t.charAt(j - 1)) {\n"
                    "                dp[i][j] = dp[i - 1][j - 1] + dp[i - 1][j];\n"
                    "            } else {\n"
                    "                dp[i][j] = dp[i - 1][j];\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return (int) dp[m][n];\n"
                    "}"
                ),
            },
        },
        {
            "title": "1D DP Rolling Array (Space-Optimised)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(n)",
            "description": (
                "Each row only reads the row directly above, so collapse to a single array of size `n+1`. "
                "**Critical detail**: iterate `j` from `n` down to `1`. Reading `dp[j-1]` before overwriting it "
                "preserves the 'previous row, previous column' value (`dp[i-1][j-1]`). Going left-to-right "
                "would clobber it."
            ),
            "code": {
                "python": (
                    "def num_distinct(s, t):\n"
                    "    m, n = len(s), len(t)\n"
                    "    dp = [0] * (n + 1)\n"
                    "    dp[0] = 1\n"
                    "    for i in range(1, m + 1):\n"
                    "        # iterate right-to-left so dp[j-1] still holds the prev-row value\n"
                    "        for j in range(n, 0, -1):\n"
                    "            if s[i - 1] == t[j - 1]:\n"
                    "                dp[j] = dp[j - 1] + dp[j]\n"
                    "            # else: dp[j] unchanged (= dp[i-1][j])\n"
                    "    return dp[n]"
                ),
                "javascript": (
                    "function numDistinct(s, t) {\n"
                    "    const m = s.length, n = t.length;\n"
                    "    const dp = new Array(n + 1).fill(0);\n"
                    "    dp[0] = 1;\n"
                    "    for (let i = 1; i <= m; i++) {\n"
                    "        for (let j = n; j >= 1; j--) {\n"
                    "            if (s[i - 1] === t[j - 1]) {\n"
                    "                dp[j] = dp[j - 1] + dp[j];\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[n];\n"
                    "}"
                ),
                "java": (
                    "public int numDistinct(String s, String t) {\n"
                    "    int m = s.length(), n = t.length();\n"
                    "    long[] dp = new long[n + 1];\n"
                    "    dp[0] = 1;\n"
                    "    for (int i = 1; i <= m; i++) {\n"
                    "        for (int j = n; j >= 1; j--) {\n"
                    "            if (s.charAt(i - 1) == t.charAt(j - 1)) {\n"
                    "                dp[j] = dp[j - 1] + dp[j];\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return (int) dp[n];\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the pattern: counting matches between two strings → 2D DP with index pair as state.",
        "2. Define state precisely: `dp[i][j]` = number of distinct subsequences of `s[0..i-1]` equal to `t[0..j-1]`. Be explicit about prefix lengths vs indices — this is where most bugs hide.",
        "3. Base cases. `dp[i][0] = 1` (empty target — delete every char of s, one valid subsequence). `dp[0][j > 0] = 0` (can't form non-empty t from empty s).",
        "4. Recurrence by case on the last characters. If `s[i-1] == t[j-1]` you have a *choice*: use it (consume both → `dp[i-1][j-1]`) or don't (skip s[i-1] → `dp[i-1][j]`). Sum because both choices yield distinct subsequences.",
        "5. If `s[i-1] != t[j-1]` you have no choice — skip s[i-1]: `dp[i][j] = dp[i-1][j]`.",
        "6. Optimise space: each row depends only on the previous row → 1D array. Iterate j right-to-left so `dp[j-1]` still holds prev row's column j-1.",
        "7. Verify with the two LC examples by hand: 'rabbbit'→'rabbit' = 3, 'babgbag'→'bag' = 5.",
    ],
    "tips": [
        "The 'use it or skip it' choice when characters match is the heart of the recurrence — internalise it; it shows up in LCS, Edit Distance, Wildcard Matching, Regex Matching.",
        "Right-to-left iteration in the 1D version is *not* optional. Going left-to-right overwrites `dp[j-1]` before you read it as the prev-row value — silent wrong answer.",
        "When `s[i-1] != t[j-1]` in the 1D version, `dp[j]` stays the same — explicitly *do nothing*. Don't write `dp[j] = dp[j]`; that's a noop but makes the code noisier.",
        "In Java, accumulate in `long[]` even though the final answer fits in 32-bit. Intermediate `dp[i][j]` values can exceed `Integer.MAX_VALUE` for adversarial inputs (LC's test cases avoid this, but defensive code does it anyway).",
        "Common follow-up — Edit Distance (LC 72): same shape, recurrence becomes `min(insert, delete, replace) + 1`. Wildcard / Regex Matching are the same family with extra branches for `*` and `?`.",
        "Memoised top-down recursion `solve(i, j)` with `@lru_cache` is also acceptable in interviews and often easier to derive — translate to bottom-up only if asked for the space-optimised version.",
    ],
    "companies": ["Google", "Amazon", "Microsoft", "Bloomberg", "Apple"],
    "topics": ["String", "Dynamic Programming"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(n)",
}


def REFERENCE(s, t):
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = 1
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + dp[i - 1][j]
            else:
                dp[i][j] = dp[i - 1][j]
    return dp[m][n]


register(PAYLOAD, REFERENCE)
