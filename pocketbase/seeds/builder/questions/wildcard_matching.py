"""Wildcard Matching — Hard. Dynamic Programming / Greedy.

Pattern matching with `?` (any single char) and `*` (any sequence,
including empty). The 2D DP is the standard answer; the greedy
two-pointer with star backtracking achieves O(m+n) average and is
the version interviewers love when you've already written the DP.
Different from Regular Expression Matching (LC 10) — `*` here is
free-standing, not a quantifier on the previous char.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Wildcard Matching",
    "difficulty": "Hard",
    "description": (
        "Given an input string `s` and a pattern `p`, implement wildcard pattern matching with support for "
        "`?` and `*` where:\n\n"
        "- `?` matches any single character.\n"
        "- `*` matches any sequence of characters (including the empty sequence).\n\n"
        "The matching should cover the **entire** input string (not partial).\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"adceb\"`, `p = \"*a*b\"`\n"
        "- Output: `true`\n"
        "- Explanation: The first `*` matches the empty sequence, while the second `*` matches the substring `\"dce\"`.\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"acdcb\"`, `p = \"a*c?b\"`\n"
        "- Output: `false`\n"
        "- Explanation: After matching `a`, `*` can absorb any prefix, but `c?b` cannot align with the remaining suffix."
    ),
    "hints": [
        "Think 2D DP: `dp[i][j]` = does `s[:i]` match `p[:j]`? Base case: `dp[0][0] = True`, and `dp[0][j]` is True only while `p[:j]` is all `*`.",
        "Transition: if `p[j-1]` is a letter or `?`, `dp[i][j] = dp[i-1][j-1]` (with letter equality for letters). If `p[j-1]` is `*`, `dp[i][j] = dp[i-1][j] OR dp[i][j-1]` — match one more char of `s`, or match zero chars and skip the `*`.",
        "`*` matching zero chars is the easy-to-miss case. That's why `dp[i][j-1]` is in the OR.",
        "Greedy two-pointer with backtrack: walk `s` and `p` together. On a mismatch, if you saw a `*` earlier, *rewind* the `s` pointer to one past where the `*` matched and let the `*` absorb one more character. O(m+n) average, O(m·n) worst case (pathological patterns).",
        "Preprocessing trick: collapse consecutive `*` in `p` into a single `*`. Doesn't change semantics and can dramatically speed up pathological inputs.",
    ],
    "constraints": [
        "0 <= s.length, p.length <= 2000",
        "`s` contains only lowercase English letters.",
        "`p` contains only lowercase English letters, `?`, or `*`.",
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
            "    cases = [(\"aa\", \"a\"), (\"aa\", \"*\"), (\"cb\", \"?a\"), (\"adceb\", \"*a*b\"), (\"acdcb\", \"a*c?b\")]\n"
            "    for s, p in cases:\n"
            "        print(f\"is_match({s!r}, {p!r}) = {is_match(s, p)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[\"aa\",\"a\"],[\"aa\",\"*\"],[\"cb\",\"?a\"],[\"adceb\",\"*a*b\"],[\"acdcb\",\"a*c?b\"]].forEach(([s,p]) =>\n"
            "    console.log(`isMatch(${JSON.stringify(s)}, ${JSON.stringify(p)}) =`, isMatch(s, p))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution sol = new Solution();\n"
            "        System.out.println(sol.isMatch(\"adceb\", \"*a*b\"));\n"
            "        System.out.println(sol.isMatch(\"acdcb\", \"a*c?b\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "aa", "p": "a"}, "expected": False,
         "description": "Pattern shorter than string with no wildcards", "tags": ["basic"]},
        {"input": {"s": "aa", "p": "*"}, "expected": True,
         "description": "Single `*` matches everything", "tags": ["basic"]},
        {"input": {"s": "cb", "p": "?a"}, "expected": False,
         "description": "`?` matches any single char but next letter mismatches", "tags": ["basic"]},
        {"input": {"s": "adceb", "p": "*a*b"}, "expected": True,
         "description": "First `*` matches empty, second absorbs `dce`", "tags": ["basic"]},
        {"input": {"s": "acdcb", "p": "a*c?b"}, "expected": False,
         "description": "Suffix `c?b` cannot align after `*` absorbs", "tags": ["basic"]},
        {"input": {"s": "", "p": ""}, "expected": True,
         "description": "Both empty — vacuously matches", "tags": ["edge"]},
        {"input": {"s": "", "p": "*"}, "expected": True,
         "description": "Empty string matches single `*` (zero chars)", "tags": ["edge"]},
        {"input": {"s": "", "p": "***"}, "expected": True,
         "description": "Empty string matches consecutive stars", "tags": ["edge"]},
        {"input": {"s": "abc", "p": ""}, "expected": False,
         "description": "Non-empty string can't match empty pattern", "tags": ["edge"]},
        {"input": {"s": "abc", "p": "***"}, "expected": True,
         "description": "Consecutive stars equivalent to a single `*`", "tags": ["tricky"]},
        {"input": {"s": "abcd", "p": "*?*?*"}, "expected": True,
         "description": "Mixed `*` and `?` — at least 2 chars required", "tags": ["tricky"]},
        {"input": {"s": "ab", "p": "*?*?*"}, "expected": True,
         "description": "Two chars, two `?` separated by stars — fits exactly", "tags": ["tricky"]},
        {"input": {"s": "a", "p": "*?*?*"}, "expected": False,
         "description": "Only one char — cannot satisfy two `?`", "tags": ["tricky"]},
        {"input": {"s": "abcabczzzde", "p": "*abc???de*"}, "expected": True,
         "description": "Star backtracking — pattern must align tail with `de`", "tags": ["tricky"]},
        {"input": {"s": "mississippi", "p": "m??*ss*?i*pi"}, "expected": False,
         "description": "Trailing `pi` cannot align — classic LC failure case", "tags": ["tricky"]},
        {"input": {"s": "a" * 1000 + "b", "p": "*" * 100 + "b"}, "expected": True,
         "description": "Many consecutive stars + suffix — needs star collapse for speed", "tags": ["large"]},
        {"input": {"s": "a" * 500, "p": "*a*a*a*a*"}, "expected": True,
         "description": "Pattern with multiple stars on a long uniform string", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "2D Dynamic Programming (Optimal Clarity)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Let `dp[i][j]` = does `s[:i]` match `p[:j]`. Base case `dp[0][0] = True`. For row 0, "
                "`dp[0][j] = dp[0][j-1] AND p[j-1] == '*'` — empty string only matches a prefix of all stars. "
                "For each cell: if `p[j-1]` is a letter or `?`, inherit from `dp[i-1][j-1]` (with letter equality "
                "for letters). If `p[j-1]` is `*`, the cell is True iff `dp[i-1][j]` (star absorbs one more "
                "char of s) OR `dp[i][j-1]` (star matches zero chars). Easy to reason about; can collapse to "
                "two rows for O(min(m,n)) space."
            ),
            "code": {
                "python": (
                    "def is_match(s, p):\n"
                    "    m, n = len(s), len(p)\n"
                    "    dp = [[False] * (n + 1) for _ in range(m + 1)]\n"
                    "    dp[0][0] = True\n"
                    "    for j in range(1, n + 1):\n"
                    "        if p[j - 1] == '*':\n"
                    "            dp[0][j] = dp[0][j - 1]\n"
                    "    for i in range(1, m + 1):\n"
                    "        for j in range(1, n + 1):\n"
                    "            if p[j - 1] == '*':\n"
                    "                dp[i][j] = dp[i - 1][j] or dp[i][j - 1]\n"
                    "            elif p[j - 1] == '?' or p[j - 1] == s[i - 1]:\n"
                    "                dp[i][j] = dp[i - 1][j - 1]\n"
                    "    return dp[m][n]"
                ),
                "javascript": (
                    "function isMatch(s, p) {\n"
                    "    const m = s.length, n = p.length;\n"
                    "    const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(false));\n"
                    "    dp[0][0] = true;\n"
                    "    for (let j = 1; j <= n; j++) {\n"
                    "        if (p[j - 1] === '*') dp[0][j] = dp[0][j - 1];\n"
                    "    }\n"
                    "    for (let i = 1; i <= m; i++) {\n"
                    "        for (let j = 1; j <= n; j++) {\n"
                    "            if (p[j - 1] === '*') {\n"
                    "                dp[i][j] = dp[i - 1][j] || dp[i][j - 1];\n"
                    "            } else if (p[j - 1] === '?' || p[j - 1] === s[i - 1]) {\n"
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
                    "    for (int j = 1; j <= n; j++) {\n"
                    "        if (p.charAt(j - 1) == '*') dp[0][j] = dp[0][j - 1];\n"
                    "    }\n"
                    "    for (int i = 1; i <= m; i++) {\n"
                    "        for (int j = 1; j <= n; j++) {\n"
                    "            char pc = p.charAt(j - 1);\n"
                    "            if (pc == '*') {\n"
                    "                dp[i][j] = dp[i - 1][j] || dp[i][j - 1];\n"
                    "            } else if (pc == '?' || pc == s.charAt(i - 1)) {\n"
                    "                dp[i][j] = dp[i - 1][j - 1];\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[m][n];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Greedy Two-Pointer with Star Backtrack",
            "time_complexity": "O(m + n) average, O(m·n) worst",
            "space_complexity": "O(1)",
            "description": (
                "Walk two pointers `i` over `s` and `j` over `p`. On a letter / `?` match, advance both. "
                "On `*`, record `star = j` and `match = i`, then advance only `j` (assume `*` matches zero "
                "for now). On a mismatch with no star seen: return False. On a mismatch *after* a star: "
                "rewind `j = star + 1`, increment `match`, and set `i = match` — i.e. let the most recent "
                "`*` absorb one more character. At the end, skip trailing `*` in `p`; success iff `j` "
                "reached the end of `p`."
            ),
            "code": {
                "python": (
                    "def is_match(s, p):\n"
                    "    i = j = 0\n"
                    "    star = -1\n"
                    "    match = 0\n"
                    "    while i < len(s):\n"
                    "        if j < len(p) and (p[j] == '?' or p[j] == s[i]):\n"
                    "            i += 1\n"
                    "            j += 1\n"
                    "        elif j < len(p) and p[j] == '*':\n"
                    "            star = j\n"
                    "            match = i\n"
                    "            j += 1\n"
                    "        elif star != -1:\n"
                    "            j = star + 1\n"
                    "            match += 1\n"
                    "            i = match\n"
                    "        else:\n"
                    "            return False\n"
                    "    while j < len(p) and p[j] == '*':\n"
                    "        j += 1\n"
                    "    return j == len(p)"
                ),
                "javascript": (
                    "function isMatch(s, p) {\n"
                    "    let i = 0, j = 0, star = -1, match = 0;\n"
                    "    while (i < s.length) {\n"
                    "        if (j < p.length && (p[j] === '?' || p[j] === s[i])) {\n"
                    "            i++; j++;\n"
                    "        } else if (j < p.length && p[j] === '*') {\n"
                    "            star = j; match = i; j++;\n"
                    "        } else if (star !== -1) {\n"
                    "            j = star + 1; match++; i = match;\n"
                    "        } else {\n"
                    "            return false;\n"
                    "        }\n"
                    "    }\n"
                    "    while (j < p.length && p[j] === '*') j++;\n"
                    "    return j === p.length;\n"
                    "}"
                ),
                "java": (
                    "public boolean isMatch(String s, String p) {\n"
                    "    int i = 0, j = 0, star = -1, match = 0;\n"
                    "    while (i < s.length()) {\n"
                    "        if (j < p.length() && (p.charAt(j) == '?' || p.charAt(j) == s.charAt(i))) {\n"
                    "            i++; j++;\n"
                    "        } else if (j < p.length() && p.charAt(j) == '*') {\n"
                    "            star = j; match = i; j++;\n"
                    "        } else if (star != -1) {\n"
                    "            j = star + 1; match++; i = match;\n"
                    "        } else {\n"
                    "            return false;\n"
                    "        }\n"
                    "    }\n"
                    "    while (j < p.length() && p.charAt(j) == '*') j++;\n"
                    "    return j == p.length();\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Start with the recursion: at each step, either consume one char (letter / `?`) or branch on `*` — match zero, or match one and stay on `*`.",
        "2. Memoize on `(i, j)` to get O(m·n). State this first; it's the natural answer.",
        "3. Convert top-down memo to bottom-up DP. Watch the base row: `dp[0][j]` is True only for an all-stars prefix.",
        "4. The `*` transition is the heart: `dp[i][j] = dp[i-1][j] OR dp[i][j-1]`. The first term is 'star absorbs one more char of s'; the second is 'star matches zero chars'. Miss either and you'll fail edge cases.",
        "5. Greedy two-pointer is the level-up. Most patterns have few stars, so you rarely backtrack — average O(m+n). Worst case (alternating mismatches after a star) is still O(m·n), same as DP.",
        "6. Edge cases: both empty (True), `s` empty + `p` all stars (True), `p` empty + `s` non-empty (False), consecutive stars (collapse for speed).",
    ],
    "tips": [
        "Confusing this with Regex Matching (LC 10) is a common stumble. Here `*` is free-standing — it doesn't quantify the previous char. Different recurrence.",
        "Collapse consecutive `*` in `p` upfront: `p = re.sub(r'\\*+', '*', p)` (Python). Same answer, much faster on adversarial inputs.",
        "For O(min(m,n)) space, roll the DP into two rows. Don't bother in interviews unless asked — clarity wins.",
        "When writing the greedy version, the rewind step `i = match; match += 1; j = star + 1` is order-sensitive. Increment `match` before reassigning `i`, or you'll loop forever.",
        "If the interviewer asks about complexity of the greedy: average is O(m+n), but pathological patterns like `*a*a*a*...b` against `aaaa...a` push to O(m·n). Both are correct answers depending on framing.",
        "Sanity check your DP: `is_match('', '')` must be True and `is_match('a', '')` must be False. If you got those wrong, your base row is broken.",
    ],
    "companies": ["Google", "Facebook", "Microsoft", "Amazon", "Two Sigma", "Snapchat"],
    "topics": ["String", "Dynamic Programming", "Greedy", "Recursion"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(m·n)",
}


def REFERENCE(s, p):
    i = j = 0
    star = -1
    match = 0
    while i < len(s):
        if j < len(p) and (p[j] == '?' or p[j] == s[i]):
            i += 1
            j += 1
        elif j < len(p) and p[j] == '*':
            star = j
            match = i
            j += 1
        elif star != -1:
            j = star + 1
            match += 1
            i = match
        else:
            return False
    while j < len(p) and p[j] == '*':
        j += 1
    return j == len(p)


register(PAYLOAD, REFERENCE)
