"""Longest Common Subsequence — Medium. 2D DP on two strings.

The canonical 'grid DP on two sequences' problem. Once you see the
recurrence — match means extend the diagonal, mismatch means take the
better of the two neighbours — every other string-alignment question
(edit distance, longest palindromic subsequence, shortest common
supersequence, diff/patch) is the same shape with the cell-update rule
swapped. Worth knowing the rolling-row optimisation cold; it halves the
memory and is a frequent follow-up.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Longest Common Subsequence",
    "difficulty": "Medium",
    "description": (
        "Given two strings `text1` and `text2`, return *the length of their longest **common "
        "subsequence***. If there is no common subsequence, return `0`.\n\n"
        "A **subsequence** of a string is a new string generated from the original string with some "
        "characters (can be none) deleted without changing the relative order of the remaining "
        "characters.\n\n"
        "- For example, `\"ace\"` is a subsequence of `\"abcde\"`.\n\n"
        "A **common subsequence** of two strings is a subsequence that is common to both strings.\n\n"
        "**Example 1:**\n"
        "- Input: `text1 = \"abcde\"`, `text2 = \"ace\"`\n"
        "- Output: `3`\n"
        "- Explanation: The longest common subsequence is `\"ace\"` and its length is 3.\n\n"
        "**Example 2:**\n"
        "- Input: `text1 = \"abc\"`, `text2 = \"abc\"`\n"
        "- Output: `3`\n"
        "- Explanation: The longest common subsequence is `\"abc\"` and its length is 3.\n\n"
        "**Example 3:**\n"
        "- Input: `text1 = \"abc\"`, `text2 = \"def\"`\n"
        "- Output: `0`\n"
        "- Explanation: There is no such common subsequence, so the result is 0."
    ),
    "hints": [
        "Brute force: enumerate every subsequence of `text1` (2^m of them) and check membership in `text2`. Exponential — state it, never run it.",
        "Define `dp[i][j]` = LCS length of `text1[:i]` and `text2[:j]`. Two cases: characters match → `dp[i-1][j-1] + 1`; mismatch → `max(dp[i-1][j], dp[i][j-1])`.",
        "Base cases fall out: `dp[0][j] = dp[i][0] = 0` (empty prefix has no common subsequence).",
        "Each cell only depends on the row above and the cell to its left. You only need *two rows* — or one row plus a single saved diagonal — so memory drops to O(min(m, n)).",
        "Always make the *shorter* string the inner dimension of the rolling array. Halves the constant factor when the inputs are very different lengths.",
    ],
    "constraints": [
        "1 <= text1.length, text2.length <= 1000",
        "text1 and text2 consist of only lowercase English characters.",
    ],
    "starter_code": {
        "python": "def longest_common_subsequence(text1, text2):\n    # Your code here\n    pass",
        "javascript": "function longestCommonSubsequence(text1, text2) {\n    // Your code here\n}",
        "java": "public int longestCommonSubsequence(String text1, String text2) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(\"abcde\", \"ace\"), (\"abc\", \"abc\"), (\"abc\", \"def\"), (\"\", \"abc\")]\n"
            "    for a, b in cases:\n"
            "        print(f\"longest_common_subsequence({a!r}, {b!r}) = \"\n"
            "              f\"{longest_common_subsequence(a, b)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[\"abcde\", \"ace\"], [\"abc\", \"abc\"], [\"abc\", \"def\"]].forEach(([a, b]) =>\n"
            "    console.log(`lcs(${a}, ${b}) =`, longestCommonSubsequence(a, b))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.longestCommonSubsequence(\"abcde\", \"ace\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"text1": "abcde", "text2": "ace"}, "expected": 3,
         "description": "Classic — LCS is \"ace\"", "tags": ["basic"]},
        {"input": {"text1": "abc", "text2": "abc"}, "expected": 3,
         "description": "Identical strings — LCS is the whole string", "tags": ["basic"]},
        {"input": {"text1": "abc", "text2": "def"}, "expected": 0,
         "description": "Disjoint alphabets — no common character", "tags": ["basic"]},
        {"input": {"text1": "", "text2": "abc"}, "expected": 0,
         "description": "Empty first string — base case", "tags": ["edge"]},
        {"input": {"text1": "abc", "text2": ""}, "expected": 0,
         "description": "Empty second string — base case", "tags": ["edge"]},
        {"input": {"text1": "ezupkr", "text2": "ubmrapg"}, "expected": 2,
         "description": "Tricky — LCS is \"ur\" (order matters; 'p' appears in both but breaks order)",
         "tags": ["tricky"]},
        {"input": {"text1": "bsbininm", "text2": "jmjkbkjkv"}, "expected": 1,
         "description": "Sparse overlap — only one character can be aligned", "tags": ["tricky"]},
        {"input": {"text1": "a" * 500 + "b" * 500, "text2": "a" * 500 + "c" * 500}, "expected": 500,
         "description": "1000 vs 1000 — only the leading 'a' block aligns", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "2D Bottom-Up DP (Canonical)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Build a `(m+1) × (n+1)` table where `dp[i][j]` is the LCS length of the first `i` "
                "characters of `text1` and the first `j` characters of `text2`. If the current pair "
                "matches, extend the diagonal (`dp[i-1][j-1] + 1`); otherwise inherit the better of "
                "(drop a char from text1, drop a char from text2). Answer is `dp[m][n]`."
            ),
            "code": {
                "python": (
                    "def longest_common_subsequence(text1, text2):\n"
                    "    m, n = len(text1), len(text2)\n"
                    "    dp = [[0] * (n + 1) for _ in range(m + 1)]\n"
                    "    for i in range(1, m + 1):\n"
                    "        for j in range(1, n + 1):\n"
                    "            if text1[i - 1] == text2[j - 1]:\n"
                    "                dp[i][j] = dp[i - 1][j - 1] + 1\n"
                    "            else:\n"
                    "                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])\n"
                    "    return dp[m][n]"
                ),
                "javascript": (
                    "function longestCommonSubsequence(text1, text2) {\n"
                    "    const m = text1.length, n = text2.length;\n"
                    "    const dp = Array.from({length: m + 1}, () => new Array(n + 1).fill(0));\n"
                    "    for (let i = 1; i <= m; i++) {\n"
                    "        for (let j = 1; j <= n; j++) {\n"
                    "            if (text1[i - 1] === text2[j - 1]) dp[i][j] = dp[i - 1][j - 1] + 1;\n"
                    "            else dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[m][n];\n"
                    "}"
                ),
                "java": (
                    "public int longestCommonSubsequence(String text1, String text2) {\n"
                    "    int m = text1.length(), n = text2.length();\n"
                    "    int[][] dp = new int[m + 1][n + 1];\n"
                    "    for (int i = 1; i <= m; i++) {\n"
                    "        for (int j = 1; j <= n; j++) {\n"
                    "            if (text1.charAt(i - 1) == text2.charAt(j - 1))\n"
                    "                dp[i][j] = dp[i - 1][j - 1] + 1;\n"
                    "            else\n"
                    "                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[m][n];\n"
                    "}"
                ),
            },
        },
        {
            "title": "1D Rolling DP (Space-Optimised)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(min(m, n))",
            "description": (
                "Each cell only needs the row above and the cell to its left, so a single 1D array of "
                "length `min(m, n) + 1` plus one scalar (`prev_diag`) suffices. Iterate the longer "
                "string outside, the shorter inside; before overwriting `dp[j]`, stash its old value "
                "to use as the diagonal on the next iteration."
            ),
            "code": {
                "python": (
                    "def longest_common_subsequence(text1, text2):\n"
                    "    if len(text1) < len(text2):\n"
                    "        text1, text2 = text2, text1\n"
                    "    n = len(text2)\n"
                    "    dp = [0] * (n + 1)\n"
                    "    for ch1 in text1:\n"
                    "        prev_diag = 0\n"
                    "        for j in range(1, n + 1):\n"
                    "            tmp = dp[j]\n"
                    "            if ch1 == text2[j - 1]:\n"
                    "                dp[j] = prev_diag + 1\n"
                    "            else:\n"
                    "                dp[j] = max(dp[j], dp[j - 1])\n"
                    "            prev_diag = tmp\n"
                    "    return dp[n]"
                ),
            },
        },
        {
            "title": "Top-Down Recursion + Memoisation",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Direct translation of the recurrence: `lcs(i, j) = 1 + lcs(i-1, j-1)` on match, else "
                "`max(lcs(i-1, j), lcs(i, j-1))`. Memoise on `(i, j)`. Same time complexity as the "
                "bottom-up table, but burns recursion depth — for the 1000×1000 constraint, raise the "
                "limit or prefer the iterative form."
            ),
            "code": {
                "python": (
                    "from functools import lru_cache\n"
                    "\n"
                    "def longest_common_subsequence(text1, text2):\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def lcs(i, j):\n"
                    "        if i == 0 or j == 0:\n"
                    "            return 0\n"
                    "        if text1[i - 1] == text2[j - 1]:\n"
                    "            return lcs(i - 1, j - 1) + 1\n"
                    "        return max(lcs(i - 1, j), lcs(i, j - 1))\n"
                    "    return lcs(len(text1), len(text2))"
                ),
            },
        },
        {
            "title": "Hirschberg's Algorithm (Reconstruction in Linear Space)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(min(m, n))",
            "description": (
                "Mention only — usually overkill for 'just the length'. If the interviewer asks you to "
                "*reconstruct* the actual LCS string in O(min(m, n)) space (not just its length), "
                "Hirschberg's divide-and-conquer recovers the alignment by computing forward and "
                "backward score rows on each half and recursing through the optimal split column. "
                "Time stays O(m·n); space drops to O(min(m, n))."
            ),
            "code": {
                "python": (
                    "# See Hirschberg 1975 for the full algorithm. Outline:\n"
                    "#   1. Split text1 in half.\n"
                    "#   2. Compute LCS-length row from the left over text2 against text1[:m/2].\n"
                    "#   3. Compute LCS-length row from the right over reverse(text2) against\n"
                    "#      reverse(text1[m/2:]).\n"
                    "#   4. Pick the split index k in text2 maximising left[k] + right[n - k].\n"
                    "#   5. Recurse on (text1[:m/2], text2[:k]) and (text1[m/2:], text2[k:]).\n"
                    "# Concatenate the two reconstructed subsequences."
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force is exponential (enumerate subsequences of one string, test membership in the other). State it, drop it immediately.",
        "2. Look for overlapping subproblems. The LCS of two prefixes only depends on shorter prefixes → DP on `(i, j) = (prefix length of text1, prefix length of text2)`.",
        "3. Recurrence: if `text1[i-1] == text2[j-1]`, that pair *must* be in some optimal LCS (proof: swap argument), so `dp[i][j] = dp[i-1][j-1] + 1`. Otherwise drop one character and take the better of the two: `max(dp[i-1][j], dp[i][j-1])`.",
        "4. Base cases: empty prefix on either side → 0. The `(m+1) × (n+1)` table size folds these in for free.",
        "5. Fill the table row-by-row (or column-by-column). Answer is the bottom-right cell `dp[m][n]`.",
        "6. Optimise: each row only reads the row above and the cell to its left. Roll to a 1D array of length `min(m, n) + 1` and stash the diagonal in a scalar before overwriting. Halves memory; same time.",
    ],
    "tips": [
        "LCS is the *foundation* of the diff algorithm. `git diff` and `diff -u` essentially compute the LCS of two files (line-granularity), then everything outside the LCS is an addition or deletion.",
        "Edit Distance (Levenshtein) is the same DP shape with three operations (insert / delete / substitute) instead of one. If you can write LCS, edit distance is a 5-minute extension.",
        "Longest Palindromic Subsequence on string `s` reduces to LCS of `s` and `reverse(s)`. State this as the bridge if the interviewer follows up.",
        "Common pitfall: confusing *subsequence* (order preserved, gaps allowed) with *substring* (contiguous). LCS allows gaps; longest common substring does not — different DP, different recurrence.",
        "Reconstructing the LCS itself (not just the length) walks back from `dp[m][n]`: on a match, prepend the char and step diagonally; on a mismatch, step toward the larger neighbour. O(m + n) walk after the O(m·n) fill.",
    ],
    "companies": ["Amazon", "Microsoft", "Adobe"],
    "topics": ["String", "Dynamic Programming"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(min(m, n))",
}


def REFERENCE(text1, text2):
    if len(text1) < len(text2):
        text1, text2 = text2, text1
    n = len(text2)
    dp = [0] * (n + 1)
    for ch1 in text1:
        prev_diag = 0
        for j in range(1, n + 1):
            tmp = dp[j]
            if ch1 == text2[j - 1]:
                dp[j] = prev_diag + 1
            else:
                dp[j] = max(dp[j], dp[j - 1])
            prev_diag = tmp
    return dp[n]


register(PAYLOAD, REFERENCE)
