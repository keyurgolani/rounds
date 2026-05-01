"""Regular Expression Matching — Hard. 2D DP / Recursion + Memo.

A textbook 2D DP. The wrinkle is the `*` quantifier: it doesn't match
a character — it modifies the *previous* element. So the recurrence
splits on whether `p[j-1] == '*'`. Most candidates draft the recursive
version first, then memoize, then convert to a bottom-up table to
nail the indexing. Worth practising both directions because the
follow-up (Wildcard Matching, LC 44) shares the structure.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Regular Expression Matching",
    "difficulty": "Hard",
    "description": (
        "Given an input string `s` and a pattern `p`, implement regular expression matching with support "
        "for `.` and `*` where:\n\n"
        "- `.` Matches any single character.\n"
        "- `*` Matches zero or more of the preceding element.\n\n"
        "The matching should cover the **entire** input string (not partial).\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"aa\", p = \"a*\"`\n"
        "- Output: `true`\n"
        "- Explanation: `'*'` means zero or more of the preceding element, `'a'`. Therefore, by repeating "
        "`'a'` once, it becomes `\"aa\"`.\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"ab\", p = \".*\"`\n"
        "- Output: `true`\n"
        "- Explanation: `\".*\"` means \"zero or more (`*`) of any character (`.`)\"."
    ),
    "hints": [
        "Define `dp[i][j]` = does `s[:i]` match `p[:j]`? Base case: `dp[0][0] = True`. Final answer: `dp[m][n]`.",
        "If `p[j-1]` is a normal char or `.`: `dp[i][j] = dp[i-1][j-1] AND (p[j-1] == '.' OR p[j-1] == s[i-1])`.",
        "If `p[j-1] == '*'`: two choices. **Skip** the `X*` group entirely (zero occurrences) → `dp[i][j-2]`. "
        "**Or consume** one character from `s` if `p[j-2]` matches `s[i-1]` → `dp[i-1][j]`.",
        "Empty-string row matters: `dp[0][j]` is True only when the pattern can collapse to empty — that "
        "requires `p[j-1] == '*'` AND `dp[0][j-2]`. Compute this row first.",
        "Top-down recursive memo is often easier to write under pressure. Recurse on `(i, j)` from the "
        "*front* and check `j+1 < n AND p[j+1] == '*'` to decide branching. Memoize on `(i, j)`.",
    ],
    "constraints": [
        "1 <= s.length <= 20",
        "1 <= p.length <= 20",
        "`s` contains only lowercase English letters. `p` contains only lowercase English letters, `.`, and `*`. "
        "It is guaranteed that for each appearance of `*`, there will be a previous valid character to match.",
    ],
    "starter_code": {
        "python": "def is_match(s, p):\n    # Your code here\n    pass",
        "javascript": "function isMatch(s, p) {\n    // Your code here\n}",
        "java": "public boolean isMatch(String s, String p) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(\"aa\", \"a\"), (\"aa\", \"a*\"), (\"ab\", \".*\"), (\"aab\", \"c*a*b\")]\n"
            "    for s, p in cases:\n"
            "        print(f\"is_match({s!r}, {p!r}) = {is_match(s, p)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[\"aa\", \"a\"], [\"aa\", \"a*\"], [\"ab\", \".*\"], [\"aab\", \"c*a*b\"]].forEach(([s, p]) =>\n"
            "    console.log(`isMatch(${s}, ${p}) =`, isMatch(s, p))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution sol = new Solution();\n"
            "        System.out.println(sol.isMatch(\"aa\", \"a*\"));\n"
            "        System.out.println(sol.isMatch(\"ab\", \".*\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "aa", "p": "a"}, "expected": False,
         "description": "Pattern shorter than string — no match", "tags": ["basic"]},
        {"input": {"s": "aa", "p": "a*"}, "expected": True,
         "description": "`a*` matches one or more `a`'s", "tags": ["basic"]},
        {"input": {"s": "ab", "p": ".*"}, "expected": True,
         "description": "`.*` matches any sequence", "tags": ["basic"]},
        {"input": {"s": "aab", "p": "c*a*b"}, "expected": True,
         "description": "`c*` matches zero `c`'s, `a*` matches `aa`, `b` matches `b`", "tags": ["tricky"]},
        {"input": {"s": "mississippi", "p": "mis*is*p*."}, "expected": False,
         "description": "Pattern can't consume the trailing `i` — classic LC trap", "tags": ["tricky"]},
        {"input": {"s": "", "p": "a*"}, "expected": True,
         "description": "Empty string vs `a*` — zero occurrences", "tags": ["edge"]},
        {"input": {"s": "", "p": ""}, "expected": True,
         "description": "Both empty", "tags": ["edge"]},
        {"input": {"s": "a", "p": ".*..a*"}, "expected": False,
         "description": "Pattern requires at least 2 characters before optional `a*`", "tags": ["tricky"]},
        {"input": {"s": "aaa", "p": "a*a"}, "expected": True,
         "description": "Greedy `a*` must yield one `a` to the trailing literal", "tags": ["tricky"]},
        {"input": {"s": "ab", "p": ".*c"}, "expected": False,
         "description": "Trailing literal must be consumed", "tags": ["edge"]},
        {"input": {"s": "aaa", "p": "ab*a*c*a"}, "expected": True,
         "description": "Multiple `*` groups collapsing to zero — `a` + `a` + `a`", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Top-Down Recursion with Memoization",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Recurse from the front. At each `(i, j)`, peek at `p[j+1]`: if it is `*`, either skip the "
                "`X*` group (recurse on `(i, j+2)`) or, if the current characters match, consume one char "
                "(recurse on `(i+1, j)`). Otherwise require a single-character match and recurse on "
                "`(i+1, j+1)`. Memoize on `(i, j)`."
            ),
            "code": {
                "python": (
                    "def is_match(s, p):\n"
                    "    from functools import lru_cache\n"
                    "    m, n = len(s), len(p)\n"
                    "\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def dp(i, j):\n"
                    "        if j == n:\n"
                    "            return i == m\n"
                    "        first = i < m and p[j] in (s[i], '.')\n"
                    "        if j + 1 < n and p[j + 1] == '*':\n"
                    "            return dp(i, j + 2) or (first and dp(i + 1, j))\n"
                    "        return first and dp(i + 1, j + 1)\n"
                    "\n"
                    "    return dp(0, 0)"
                ),
                "javascript": (
                    "function isMatch(s, p) {\n"
                    "    const m = s.length, n = p.length;\n"
                    "    const memo = new Map();\n"
                    "    const dp = (i, j) => {\n"
                    "        const key = i * (n + 1) + j;\n"
                    "        if (memo.has(key)) return memo.get(key);\n"
                    "        let ans;\n"
                    "        if (j === n) ans = (i === m);\n"
                    "        else {\n"
                    "            const first = i < m && (p[j] === s[i] || p[j] === '.');\n"
                    "            if (j + 1 < n && p[j + 1] === '*') ans = dp(i, j + 2) || (first && dp(i + 1, j));\n"
                    "            else ans = first && dp(i + 1, j + 1);\n"
                    "        }\n"
                    "        memo.set(key, ans);\n"
                    "        return ans;\n"
                    "    };\n"
                    "    return dp(0, 0);\n"
                    "}"
                ),
                "java": (
                    "public boolean isMatch(String s, String p) {\n"
                    "    int m = s.length(), n = p.length();\n"
                    "    Boolean[][] memo = new Boolean[m + 1][n + 1];\n"
                    "    return dp(0, 0, s, p, memo);\n"
                    "}\n"
                    "\n"
                    "private boolean dp(int i, int j, String s, String p, Boolean[][] memo) {\n"
                    "    if (memo[i][j] != null) return memo[i][j];\n"
                    "    boolean ans;\n"
                    "    if (j == p.length()) ans = (i == s.length());\n"
                    "    else {\n"
                    "        boolean first = i < s.length() && (p.charAt(j) == s.charAt(i) || p.charAt(j) == '.');\n"
                    "        if (j + 1 < p.length() && p.charAt(j + 1) == '*')\n"
                    "            ans = dp(i, j + 2, s, p, memo) || (first && dp(i + 1, j, s, p, memo));\n"
                    "        else\n"
                    "            ans = first && dp(i + 1, j + 1, s, p, memo);\n"
                    "    }\n"
                    "    return memo[i][j] = ans;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Bottom-Up DP Table",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Define `dp[i][j]` = does `s[:i]` match `p[:j]`. Initialise `dp[0][0] = True`. Pre-fill the "
                "first row for patterns that can collapse to empty (`X*` runs). Then for each cell: if "
                "`p[j-1] == '*'`, take `dp[i][j-2]` (skip) OR `dp[i-1][j]` when `p[j-2]` matches `s[i-1]` "
                "(consume). Otherwise require `dp[i-1][j-1]` and a character match."
            ),
            "code": {
                "python": (
                    "def is_match(s, p):\n"
                    "    m, n = len(s), len(p)\n"
                    "    dp = [[False] * (n + 1) for _ in range(m + 1)]\n"
                    "    dp[0][0] = True\n"
                    "    for j in range(2, n + 1):\n"
                    "        if p[j - 1] == '*':\n"
                    "            dp[0][j] = dp[0][j - 2]\n"
                    "    for i in range(1, m + 1):\n"
                    "        for j in range(1, n + 1):\n"
                    "            if p[j - 1] == '*':\n"
                    "                dp[i][j] = dp[i][j - 2]\n"
                    "                if p[j - 2] == '.' or p[j - 2] == s[i - 1]:\n"
                    "                    dp[i][j] = dp[i][j] or dp[i - 1][j]\n"
                    "            else:\n"
                    "                if p[j - 1] == '.' or p[j - 1] == s[i - 1]:\n"
                    "                    dp[i][j] = dp[i - 1][j - 1]\n"
                    "    return dp[m][n]"
                ),
                "javascript": (
                    "function isMatch(s, p) {\n"
                    "    const m = s.length, n = p.length;\n"
                    "    const dp = Array.from({length: m + 1}, () => new Array(n + 1).fill(false));\n"
                    "    dp[0][0] = true;\n"
                    "    for (let j = 2; j <= n; j++) {\n"
                    "        if (p[j - 1] === '*') dp[0][j] = dp[0][j - 2];\n"
                    "    }\n"
                    "    for (let i = 1; i <= m; i++) {\n"
                    "        for (let j = 1; j <= n; j++) {\n"
                    "            if (p[j - 1] === '*') {\n"
                    "                dp[i][j] = dp[i][j - 2];\n"
                    "                if (p[j - 2] === '.' || p[j - 2] === s[i - 1])\n"
                    "                    dp[i][j] = dp[i][j] || dp[i - 1][j];\n"
                    "            } else if (p[j - 1] === '.' || p[j - 1] === s[i - 1]) {\n"
                    "                dp[i][j] = dp[i - 1][j - 1];\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[m][n];\n"
                    "}"
                ),
                "java": (
                    "public boolean isMatch(String s, String p) {\n"
                    "    int m = s.length(), n = p.length();\n"
                    "    boolean[][] dp = new boolean[m + 1][n + 1];\n"
                    "    dp[0][0] = true;\n"
                    "    for (int j = 2; j <= n; j++) {\n"
                    "        if (p.charAt(j - 1) == '*') dp[0][j] = dp[0][j - 2];\n"
                    "    }\n"
                    "    for (int i = 1; i <= m; i++) {\n"
                    "        for (int j = 1; j <= n; j++) {\n"
                    "            if (p.charAt(j - 1) == '*') {\n"
                    "                dp[i][j] = dp[i][j - 2];\n"
                    "                if (p.charAt(j - 2) == '.' || p.charAt(j - 2) == s.charAt(i - 1))\n"
                    "                    dp[i][j] = dp[i][j] || dp[i - 1][j];\n"
                    "            } else if (p.charAt(j - 1) == '.' || p.charAt(j - 1) == s.charAt(i - 1)) {\n"
                    "                dp[i][j] = dp[i - 1][j - 1];\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[m][n];\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Clarify scope: full-string match, not search. `*` modifies the *previous* element — it never stands alone.",
        "2. Try a small example by hand: `s='aab', p='c*a*b'`. Walk left-to-right and notice that `c*` collapses to empty.",
        "3. Define the subproblem: `dp[i][j]` = does `s[:i]` match `p[:j]`. Base `dp[0][0] = True`.",
        "4. Two transitions. Normal char / `.`: depends on `dp[i-1][j-1]` and a single-char match. `*`: skip the `X*` group entirely (`dp[i][j-2]`), or consume one `s` char when `p[j-2]` matches (`dp[i-1][j]`).",
        "5. Pre-fill `dp[0][j]` for patterns that can collapse to empty — only `X*` groups can.",
        "6. Choose top-down (recursion + memo) for clarity in interviews; bottom-up if the interviewer asks for an iterative solution.",
        "7. Edge cases: empty `s`, empty `p`, leading `*` (the constraints rule it out), patterns longer than the string.",
    ],
    "tips": [
        "The single most common bug is forgetting to initialise `dp[0][j]` for `X*X*X*` patterns. Walk through the empty-string row first.",
        "Don't confuse `*` with the regex `+`. Here `*` means **zero or more**, so `a*` matches the empty string.",
        "When peeking at `p[j+1] == '*'` in the top-down version, **always** bounds-check `j+1 < n` first.",
        "The recursion has overlapping subproblems — without memoization it's exponential on patterns like `a*a*a*a*a*a*b`. Always memoize.",
        "Follow-up — Wildcard Matching (LC 44): `?` is single char, `*` is *any sequence* (no preceding element). Different recurrence, similar 2D DP shape.",
        "If the interviewer asks for `O(n)` space, you can roll the DP table to two rows since `dp[i][*]` only depends on `dp[i-1][*]` and `dp[i][*]`.",
    ],
    "companies": ["Google", "Facebook", "Amazon", "Microsoft", "Uber", "Bloomberg"],
    "topics": ["String", "Dynamic Programming", "Recursion"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(m·n)",
}


def REFERENCE(s, p):
    m, n = len(s), len(p)
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True
    for j in range(2, n + 1):
        if p[j - 1] == '*':
            dp[0][j] = dp[0][j - 2]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if p[j - 1] == '*':
                dp[i][j] = dp[i][j - 2]
                if p[j - 2] == '.' or p[j - 2] == s[i - 1]:
                    dp[i][j] = dp[i][j] or dp[i - 1][j]
            else:
                if p[j - 1] == '.' or p[j - 1] == s[i - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
    return dp[m][n]


register(PAYLOAD, REFERENCE)
