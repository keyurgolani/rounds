"""Edit Distance — Hard. Classic 2D Dynamic Programming.

The textbook Levenshtein recurrence: at each cell `dp[i][j]` you choose
the cheapest of insert / delete / replace, or take the diagonal for free
when the characters already match. Once you've internalised this, half
of the 'two-string DP' family (Distinct Subsequences, Interleaving String,
Regex Matching, Wildcard Matching) becomes pattern recognition.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Edit Distance",
    "difficulty": "Hard",
    "description": (
        "Given two strings `word1` and `word2`, return the **minimum number of operations** required to "
        "convert `word1` into `word2`.\n\n"
        "You have the following three operations permitted on a word:\n"
        "- Insert a character\n"
        "- Delete a character\n"
        "- Replace a character\n\n"
        "**Example 1:**\n"
        "- Input: `word1 = \"horse\", word2 = \"ros\"`\n"
        "- Output: `3`\n"
        "- Explanation: horse → rorse (replace 'h' with 'r') → rose (delete 'r') → ros (delete 'e').\n\n"
        "**Example 2:**\n"
        "- Input: `word1 = \"intention\", word2 = \"execution\"`\n"
        "- Output: `5`\n"
        "- Explanation: intention → inention (delete 't') → enention (replace 'i' with 'e') → "
        "exention (replace 'n' with 'x') → exection (replace 'n' with 'c') → execution (insert 'u')."
    ),
    "hints": [
        "Define `dp[i][j]` = edit distance between `word1[:i]` and `word2[:j]`. The answer is `dp[m][n]`.",
        "Base cases: `dp[0][j] = j` (insert all of word2) and `dp[i][0] = i` (delete all of word1).",
        "If `word1[i-1] == word2[j-1]`, no operation needed: `dp[i][j] = dp[i-1][j-1]`.",
        "Otherwise: `dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])` — delete, insert, replace.",
        "Space optimisation: only the previous row is needed, so a 1D array of length `min(m, n) + 1` suffices.",
    ],
    "constraints": [
        "0 <= word1.length, word2.length <= 500",
        "word1 and word2 consist of lowercase English letters.",
    ],
    "starter_code": {
        "python": "def min_distance(word1, word2):\n    # Your code here\n    pass",
        "javascript": "function minDistance(word1, word2) {\n    // Your code here\n}",
        "java": "public int minDistance(String word1, String word2) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(\"horse\", \"ros\"), (\"intention\", \"execution\"), (\"\", \"abc\")]\n"
            "    for w1, w2 in cases:\n"
            "        print(f\"min_distance({w1!r}, {w2!r}) = {min_distance(w1, w2)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[\"horse\", \"ros\"], [\"intention\", \"execution\"]].forEach(([a, b]) =>\n"
            "    console.log(`minDistance(${a}, ${b}) =`, minDistance(a, b))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.minDistance(\"horse\", \"ros\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"word1": "horse", "word2": "ros"}, "expected": 3,
         "description": "Classic example — replace + two deletes", "tags": ["basic"]},
        {"input": {"word1": "intention", "word2": "execution"}, "expected": 5,
         "description": "Longer pair — one delete, three replaces, one insert", "tags": ["basic"]},
        {"input": {"word1": "", "word2": ""}, "expected": 0,
         "description": "Both empty — no operations", "tags": ["edge"]},
        {"input": {"word1": "abc", "word2": ""}, "expected": 3,
         "description": "Delete all of word1", "tags": ["edge"]},
        {"input": {"word1": "", "word2": "abc"}, "expected": 3,
         "description": "Insert all of word2", "tags": ["edge"]},
        {"input": {"word1": "abc", "word2": "abc"}, "expected": 0,
         "description": "Already equal — no edits", "tags": ["edge"]},
        {"input": {"word1": "a", "word2": "b"}, "expected": 1,
         "description": "Single replace", "tags": ["edge"]},
        {"input": {"word1": "kitten", "word2": "sitting"}, "expected": 3,
         "description": "Wikipedia Levenshtein example — two replaces, one insert", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "2D Dynamic Programming (Standard)",
            "time_complexity": "O(m * n)",
            "space_complexity": "O(m * n)",
            "description": (
                "Build a `(m+1) x (n+1)` table where `dp[i][j]` is the edit distance between the first "
                "`i` chars of `word1` and the first `j` chars of `word2`. Initialise the borders, then fill "
                "row by row using the four-way recurrence: match (diagonal copy) or 1 + min(insert, delete, "
                "replace). Answer sits at `dp[m][n]`."
            ),
            "code": {
                "python": (
                    "def min_distance(word1, word2):\n"
                    "    m, n = len(word1), len(word2)\n"
                    "    dp = [[0] * (n + 1) for _ in range(m + 1)]\n"
                    "    for i in range(m + 1):\n"
                    "        dp[i][0] = i\n"
                    "    for j in range(n + 1):\n"
                    "        dp[0][j] = j\n"
                    "    for i in range(1, m + 1):\n"
                    "        for j in range(1, n + 1):\n"
                    "            if word1[i - 1] == word2[j - 1]:\n"
                    "                dp[i][j] = dp[i - 1][j - 1]\n"
                    "            else:\n"
                    "                dp[i][j] = 1 + min(\n"
                    "                    dp[i - 1][j],     # delete\n"
                    "                    dp[i][j - 1],     # insert\n"
                    "                    dp[i - 1][j - 1], # replace\n"
                    "                )\n"
                    "    return dp[m][n]"
                ),
                "javascript": (
                    "function minDistance(word1, word2) {\n"
                    "    const m = word1.length, n = word2.length;\n"
                    "    const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));\n"
                    "    for (let i = 0; i <= m; i++) dp[i][0] = i;\n"
                    "    for (let j = 0; j <= n; j++) dp[0][j] = j;\n"
                    "    for (let i = 1; i <= m; i++) {\n"
                    "        for (let j = 1; j <= n; j++) {\n"
                    "            if (word1[i - 1] === word2[j - 1]) {\n"
                    "                dp[i][j] = dp[i - 1][j - 1];\n"
                    "            } else {\n"
                    "                dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[m][n];\n"
                    "}"
                ),
                "java": (
                    "public int minDistance(String word1, String word2) {\n"
                    "    int m = word1.length(), n = word2.length();\n"
                    "    int[][] dp = new int[m + 1][n + 1];\n"
                    "    for (int i = 0; i <= m; i++) dp[i][0] = i;\n"
                    "    for (int j = 0; j <= n; j++) dp[0][j] = j;\n"
                    "    for (int i = 1; i <= m; i++) {\n"
                    "        for (int j = 1; j <= n; j++) {\n"
                    "            if (word1.charAt(i - 1) == word2.charAt(j - 1)) {\n"
                    "                dp[i][j] = dp[i - 1][j - 1];\n"
                    "            } else {\n"
                    "                dp[i][j] = 1 + Math.min(dp[i - 1][j - 1],\n"
                    "                                       Math.min(dp[i - 1][j], dp[i][j - 1]));\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[m][n];\n"
                    "}"
                ),
            },
        },
        {
            "title": "1D Rolling DP (Space-Optimised)",
            "time_complexity": "O(m * n)",
            "space_complexity": "O(min(m, n))",
            "description": (
                "Only the previous row is needed to compute the next, so collapse the 2D table to a single "
                "array. Track the diagonal value (`dp[i-1][j-1]`) in a scalar before overwriting it. Always "
                "iterate over the shorter dimension as the inner axis so the rolling array is `min(m, n) + 1`."
            ),
            "code": {
                "python": (
                    "def min_distance(word1, word2):\n"
                    "    if len(word1) < len(word2):\n"
                    "        word1, word2 = word2, word1\n"
                    "    m, n = len(word1), len(word2)\n"
                    "    prev = list(range(n + 1))\n"
                    "    for i in range(1, m + 1):\n"
                    "        curr = [i] + [0] * n\n"
                    "        for j in range(1, n + 1):\n"
                    "            if word1[i - 1] == word2[j - 1]:\n"
                    "                curr[j] = prev[j - 1]\n"
                    "            else:\n"
                    "                curr[j] = 1 + min(prev[j], curr[j - 1], prev[j - 1])\n"
                    "        prev = curr\n"
                    "    return prev[n]"
                ),
            },
        },
        {
            "title": "Recursion + Memoisation",
            "time_complexity": "O(m * n)",
            "space_complexity": "O(m * n)",
            "description": (
                "Top-down mirror of the recurrence. `solve(i, j)` returns the edit distance between the "
                "first `i` chars of `word1` and the first `j` chars of `word2`. Memoise on `(i, j)`. Useful "
                "when you want to derive the recurrence interactively in an interview before flipping it "
                "to bottom-up."
            ),
            "code": {
                "python": (
                    "from functools import lru_cache\n"
                    "\n"
                    "def min_distance(word1, word2):\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def solve(i, j):\n"
                    "        if i == 0:\n"
                    "            return j\n"
                    "        if j == 0:\n"
                    "            return i\n"
                    "        if word1[i - 1] == word2[j - 1]:\n"
                    "            return solve(i - 1, j - 1)\n"
                    "        return 1 + min(solve(i - 1, j), solve(i, j - 1), solve(i - 1, j - 1))\n"
                    "    return solve(len(word1), len(word2))"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Frame the subproblem: `dp[i][j]` is the edit distance between `word1[:i]` and `word2[:j]`. The full answer is `dp[m][n]`.",
        "2. Base cases write themselves: turning an empty prefix into a length-`j` prefix needs exactly `j` inserts, and vice versa for deletes.",
        "3. If the two ends match, neither character costs anything — fall through to `dp[i-1][j-1]`.",
        "4. Otherwise, you must spend one operation. Three choices, each shrinks the problem by one character: delete (`dp[i-1][j]`), insert (`dp[i][j-1]`), replace (`dp[i-1][j-1]`).",
        "5. Walk \"horse\" → \"ros\" by hand: row 0 is [0,1,2,3]; column 0 is [0,1,2,3,4,5]; the table fills monotonically and `dp[5][3] = 3`. Confirms the recurrence.",
        "6. Iterate row-major bottom-up — every cell only needs values to the left, above, and up-left, so a single forward sweep suffices.",
        "7. Once correct, optimise: the previous row is the only thing the next row reads, so you can collapse to a 1D rolling array of size `min(m, n) + 1`.",
    ],
    "tips": [
        "Weighted edits: if insert / delete / replace have different costs (or even per-character costs), the same recurrence works — just swap the `+ 1` for the operation-specific cost.",
        "LCS connection: when only insertions and deletions are allowed (no replace), the answer becomes `m + n - 2 * LCS(word1, word2)`. Useful framing if an interviewer drops the replace operation.",
        "Reconstructing the actual edit sequence: walk the DP table backwards from `(m, n)`, choosing the predecessor that produced the current cell. O(m + n) extra work after the fill.",
        "Damerau–Levenshtein adds a fourth operation (transpose adjacent characters). The recurrence gains one more case: `dp[i][j] = min(..., dp[i-2][j-2] + 1)` when the last two chars swap.",
        "Watch the index off-by-one: `dp[i][j]` reasons about `word1[:i]`, so the character comparison is `word1[i-1] == word2[j-1]`. A classic interview slip.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "LinkedIn"],
    "topics": ["String", "Dynamic Programming"],
    "time_complexity": "O(m * n)",
    "space_complexity": "O(m * n)",
}


def REFERENCE(word1, word2):
    m, n = len(word1), len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],
                    dp[i][j - 1],
                    dp[i - 1][j - 1],
                )
    return dp[m][n]


register(PAYLOAD, REFERENCE)
