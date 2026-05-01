"""Interleaving String — Medium. 2D Dynamic Programming.

The classic 'is s3 a shuffle that preserves order from s1 and s2'
problem. The naive recursive shuffle search is exponential; the trick
is recognising that the *only* state that matters is `(i, j)` — how
many characters consumed from s1 and s2 — because k = i + j is
determined. That collapses the search space to O(m·n) and unlocks the
2D DP. Worth knowing the rolling-row optimisation for follow-ups.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Interleaving String",
    "difficulty": "Medium",
    "description": (
        "Given strings `s1`, `s2`, and `s3`, return `True` if `s3` is formed by an **interleaving** of "
        "`s1` and `s2`.\n\n"
        "An interleaving of two strings `s` and `t` is a configuration where `s` and `t` are divided into "
        "non-empty substrings such that:\n"
        "- `s = s_1 + s_2 + ... + s_n`\n"
        "- `t = t_1 + t_2 + ... + t_m`\n"
        "- `|n - m| <= 1`\n"
        "- The interleaving is `s_1 + t_1 + s_2 + t_2 + ...` or `t_1 + s_1 + t_2 + s_2 + ...`\n\n"
        "The order of characters within each of `s1` and `s2` must be preserved.\n\n"
        "**Example 1:**\n"
        "- Input: `s1 = \"aabcc\"`, `s2 = \"dbbca\"`, `s3 = \"aadbbcbcac\"`\n"
        "- Output: `True`\n"
        "- Explanation: One valid split is `\"aa\" + \"dbbc\" + \"bc\" + \"a\" + \"c\"` interleaving "
        "`(aa)(dbbc)(bc)(a)(c)`.\n\n"
        "**Example 2:**\n"
        "- Input: `s1 = \"aabcc\"`, `s2 = \"dbbca\"`, `s3 = \"aadbbbaccc\"`\n"
        "- Output: `False`\n"
        "- Explanation: No way to interleave `s1` and `s2` to get `s3`."
    ),
    "hints": [
        "Quick reject: if `len(s1) + len(s2) != len(s3)`, return `False` immediately. No interleaving can change the total length.",
        "When you greedily try the next character, you face a fork: either it came from `s1` or from `s2`. Both branches may match — you can't decide locally. That's the recursion.",
        "Key insight: the only state that matters is `(i, j)` — how many characters consumed from `s1` and `s2`. Because `k = i + j`, you don't need a third index. Memoise on `(i, j)` → O(m·n) states.",
        "Bottom-up 2D DP: `dp[i][j]` = can `s3[0..i+j-1]` be formed from `s1[0..i-1]` and `s2[0..j-1]`. Recurrence: `dp[i][j] = (dp[i-1][j] and s1[i-1]==s3[i+j-1]) or (dp[i][j-1] and s2[j-1]==s3[i+j-1])`.",
        "Space optimisation: each row of `dp` only depends on the previous row and the cell to the left → collapse to a 1D array of length `len(s2)+1`. O(n) extra space.",
    ],
    "constraints": [
        "0 <= s1.length, s2.length <= 100",
        "0 <= s3.length <= 200",
        "s1, s2, and s3 consist of lowercase English letters",
    ],
    "starter_code": {
        "python": "def is_interleave(s1, s2, s3):\n    # Your code here\n    pass",
        "javascript": "function isInterleave(s1, s2, s3) {\n    // Your code here\n}",
        "java": "public boolean isInterleave(String s1, String s2, String s3) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        (\"aabcc\", \"dbbca\", \"aadbbcbcac\"),\n"
            "        (\"aabcc\", \"dbbca\", \"aadbbbaccc\"),\n"
            "        (\"\", \"\", \"\"),\n"
            "    ]\n"
            "    for s1, s2, s3 in cases:\n"
            "        print(f\"is_interleave({s1!r}, {s2!r}, {s3!r}) = {is_interleave(s1, s2, s3)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\n"
            "    [\"aabcc\", \"dbbca\", \"aadbbcbcac\"],\n"
            "    [\"aabcc\", \"dbbca\", \"aadbbbaccc\"],\n"
            "].forEach(([s1, s2, s3]) =>\n"
            "    console.log(`isInterleave =`, isInterleave(s1, s2, s3))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.isInterleave(\"aabcc\", \"dbbca\", \"aadbbcbcac\"));\n"
            "        System.out.println(s.isInterleave(\"aabcc\", \"dbbca\", \"aadbbbaccc\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s1": "aabcc", "s2": "dbbca", "s3": "aadbbcbcac"}, "expected": True,
         "description": "Classic LC example — valid interleaving", "tags": ["basic"]},
        {"input": {"s1": "aabcc", "s2": "dbbca", "s3": "aadbbbaccc"}, "expected": False,
         "description": "Same s1/s2, scrambled s3 — no valid weave", "tags": ["basic"]},
        {"input": {"s1": "", "s2": "", "s3": ""}, "expected": True,
         "description": "All empty — trivially True", "tags": ["edge"]},
        {"input": {"s1": "", "s2": "abc", "s3": "abc"}, "expected": True,
         "description": "s1 empty — s3 must equal s2", "tags": ["edge"]},
        {"input": {"s1": "abc", "s2": "", "s3": "abc"}, "expected": True,
         "description": "s2 empty — s3 must equal s1", "tags": ["edge"]},
        {"input": {"s1": "abc", "s2": "", "s3": "acb"}, "expected": False,
         "description": "s2 empty but s3 reorders s1 — order must be preserved", "tags": ["edge"]},
        {"input": {"s1": "a", "s2": "b", "s3": "ab"}, "expected": True,
         "description": "Tiny case — straight concatenation", "tags": ["edge"]},
        {"input": {"s1": "a", "s2": "b", "s3": "ba"}, "expected": True,
         "description": "Tiny case — reverse concatenation", "tags": ["edge"]},
        {"input": {"s1": "ab", "s2": "cd", "s3": "abcde"}, "expected": False,
         "description": "Length mismatch (5 vs 4) — instant False", "tags": ["edge"]},
        {"input": {"s1": "ab", "s2": "cd", "s3": "acbd"}, "expected": True,
         "description": "Perfect alternation a-c-b-d", "tags": ["basic"]},
        {"input": {"s1": "aa", "s2": "ab", "s3": "aaba"}, "expected": True,
         "description": "Tricky branching — at index 1 both s1 and s2 offer 'a'; greedy fails", "tags": ["tricky"]},
        {"input": {"s1": "aa", "s2": "ab", "s3": "abaa"}, "expected": True,
         "description": "Tricky branching — must pick s2's 'a' first then 'b'", "tags": ["tricky"]},
        {"input": {"s1": "aabc", "s2": "abad", "s3": "aabadabc"}, "expected": True,
         "description": "Repeated 'a's force the DP to explore both sides", "tags": ["tricky"]},
        {"input": {"s1": "a" * 50, "s2": "b" * 50, "s3": "a" * 50 + "b" * 50}, "expected": True,
         "description": "Stress — 100-char interleave, all-a then all-b", "tags": ["large"]},
        {"input": {"s1": "a" * 50, "s2": "b" * 50, "s3": ("ab") * 50}, "expected": True,
         "description": "Stress — 100-char strict alternation", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "2D Bottom-Up DP (Optimal)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "Let `dp[i][j]` be `True` iff `s3[0..i+j-1]` can be formed by interleaving `s1[0..i-1]` "
                "and `s2[0..j-1]`. Base: `dp[0][0] = True`. Transition: `dp[i][j]` is True if either "
                "(`dp[i-1][j]` and `s1[i-1] == s3[i+j-1]`) — last char came from s1 — or "
                "(`dp[i][j-1]` and `s2[j-1] == s3[i+j-1]`) — last char came from s2. Answer: `dp[m][n]`."
            ),
            "code": {
                "python": (
                    "def is_interleave(s1, s2, s3):\n"
                    "    m, n = len(s1), len(s2)\n"
                    "    if m + n != len(s3):\n"
                    "        return False\n"
                    "    dp = [[False] * (n + 1) for _ in range(m + 1)]\n"
                    "    dp[0][0] = True\n"
                    "    for i in range(m + 1):\n"
                    "        for j in range(n + 1):\n"
                    "            if i > 0 and s1[i - 1] == s3[i + j - 1]:\n"
                    "                dp[i][j] = dp[i][j] or dp[i - 1][j]\n"
                    "            if j > 0 and s2[j - 1] == s3[i + j - 1]:\n"
                    "                dp[i][j] = dp[i][j] or dp[i][j - 1]\n"
                    "    return dp[m][n]"
                ),
                "javascript": (
                    "function isInterleave(s1, s2, s3) {\n"
                    "    const m = s1.length, n = s2.length;\n"
                    "    if (m + n !== s3.length) return false;\n"
                    "    const dp = Array.from({length: m + 1}, () => new Array(n + 1).fill(false));\n"
                    "    dp[0][0] = true;\n"
                    "    for (let i = 0; i <= m; i++) {\n"
                    "        for (let j = 0; j <= n; j++) {\n"
                    "            if (i > 0 && s1[i - 1] === s3[i + j - 1])\n"
                    "                dp[i][j] = dp[i][j] || dp[i - 1][j];\n"
                    "            if (j > 0 && s2[j - 1] === s3[i + j - 1])\n"
                    "                dp[i][j] = dp[i][j] || dp[i][j - 1];\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[m][n];\n"
                    "}"
                ),
                "java": (
                    "public boolean isInterleave(String s1, String s2, String s3) {\n"
                    "    int m = s1.length(), n = s2.length();\n"
                    "    if (m + n != s3.length()) return false;\n"
                    "    boolean[][] dp = new boolean[m + 1][n + 1];\n"
                    "    dp[0][0] = true;\n"
                    "    for (int i = 0; i <= m; i++) {\n"
                    "        for (int j = 0; j <= n; j++) {\n"
                    "            if (i > 0 && s1.charAt(i - 1) == s3.charAt(i + j - 1))\n"
                    "                dp[i][j] = dp[i][j] || dp[i - 1][j];\n"
                    "            if (j > 0 && s2.charAt(j - 1) == s3.charAt(i + j - 1))\n"
                    "                dp[i][j] = dp[i][j] || dp[i][j - 1];\n"
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
            "space_complexity": "O(n)",
            "description": (
                "Each row of the 2D table only depends on the previous row (for the s1 transition) and "
                "the cell to the left in the same row (for the s2 transition). Collapse to a single row "
                "of length `len(s2)+1`. Iterate `i` from 0 to m; the `i=0` row is initialised by walking "
                "s2 against the prefix of s3."
            ),
            "code": {
                "python": (
                    "def is_interleave(s1, s2, s3):\n"
                    "    m, n = len(s1), len(s2)\n"
                    "    if m + n != len(s3):\n"
                    "        return False\n"
                    "    dp = [False] * (n + 1)\n"
                    "    dp[0] = True\n"
                    "    for j in range(1, n + 1):\n"
                    "        dp[j] = dp[j - 1] and s2[j - 1] == s3[j - 1]\n"
                    "    for i in range(1, m + 1):\n"
                    "        dp[0] = dp[0] and s1[i - 1] == s3[i - 1]\n"
                    "        for j in range(1, n + 1):\n"
                    "            dp[j] = (dp[j] and s1[i - 1] == s3[i + j - 1]) or \\\n"
                    "                    (dp[j - 1] and s2[j - 1] == s3[i + j - 1])\n"
                    "    return dp[n]"
                ),
                "javascript": (
                    "function isInterleave(s1, s2, s3) {\n"
                    "    const m = s1.length, n = s2.length;\n"
                    "    if (m + n !== s3.length) return false;\n"
                    "    const dp = new Array(n + 1).fill(false);\n"
                    "    dp[0] = true;\n"
                    "    for (let j = 1; j <= n; j++)\n"
                    "        dp[j] = dp[j - 1] && s2[j - 1] === s3[j - 1];\n"
                    "    for (let i = 1; i <= m; i++) {\n"
                    "        dp[0] = dp[0] && s1[i - 1] === s3[i - 1];\n"
                    "        for (let j = 1; j <= n; j++) {\n"
                    "            dp[j] = (dp[j] && s1[i - 1] === s3[i + j - 1]) ||\n"
                    "                    (dp[j - 1] && s2[j - 1] === s3[i + j - 1]);\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[n];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Top-Down Recursion + Memo",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m·n)",
            "description": (
                "The natural recursion: at state `(i, j)` consume `s3[i+j]` from either s1 or s2 if the "
                "character matches. Memoise on `(i, j)` since `k = i + j` is implicit. Often easier to "
                "*derive* in an interview than the bottom-up table — write it first, then convert."
            ),
            "code": {
                "python": (
                    "def is_interleave(s1, s2, s3):\n"
                    "    m, n = len(s1), len(s2)\n"
                    "    if m + n != len(s3):\n"
                    "        return False\n"
                    "    from functools import lru_cache\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def go(i, j):\n"
                    "        if i == m and j == n:\n"
                    "            return True\n"
                    "        k = i + j\n"
                    "        if i < m and s1[i] == s3[k] and go(i + 1, j):\n"
                    "            return True\n"
                    "        if j < n and s2[j] == s3[k] and go(i, j + 1):\n"
                    "            return True\n"
                    "        return False\n"
                    "    return go(0, 0)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Length sanity: `|s1| + |s2|` must equal `|s3|`. Reject otherwise — saves the entire DP.",
        "2. Try the greedy/two-pointer instinct: walk all three strings, advance whichever matches. Find a counter-example fast (e.g. `s1='aa', s2='ab', s3='aaba'`) — both s1 and s2 can supply the 'a', greedy picks wrong.",
        "3. So you must try *both* branches at every fork — that's recursion. State = (i, j) = chars consumed from s1, s2. k = i + j is implied.",
        "4. Memoise on (i, j): O(m·n) states, each branch is O(1) → O(m·n) total. Now you have a working solution.",
        "5. Convert to bottom-up: `dp[i][j]` = can `s3[0..i+j-1]` be built from `s1[0..i-1]` + `s2[0..j-1]`. Base `dp[0][0] = True`. Transition takes the OR over the two branches.",
        "6. Space optimisation: each row only reads from the previous row (same j) and the left cell (j-1). One row suffices → O(n) space.",
        "7. Edge cases: both empty → True; one empty → s3 must equal the other; length mismatch → False.",
    ],
    "tips": [
        "Don't fall into the greedy two-pointer trap. The interviewer is probably steering you there to see if you spot the branching.",
        "The dimension reduction `(i, j, k) → (i, j)` because `k = i + j` is the move that earns the points. State it explicitly when you write the recursion.",
        "When you write the bottom-up table, initialise the first row and column by walking the matching prefix — easier than special-casing `i == 0` / `j == 0` in the inner loop.",
        "The 1D rolling-row optimisation looks scary because the cell `dp[j]` plays two roles (old `dp[i-1][j]` before update, new `dp[i][j]` after). The recurrence is set up so reading-then-writing in left-to-right order is safe.",
        "Common follow-up: 'reconstruct the interleaving' — store parent pointers in the DP and walk back from `dp[m][n]`. Same time, same space.",
        "Common follow-up: 'three strings interleaving s1, s2, s3 → s4'. Same idea, 3D DP `dp[i][j][k]`. The state-collapse trick still applies (`l = i + j + k`).",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Bloomberg", "Apple"],
    "topics": ["String", "Dynamic Programming"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(n)",
}


def REFERENCE(s1, s2, s3):
    m, n = len(s1), len(s2)
    if m + n != len(s3):
        return False
    dp = [False] * (n + 1)
    dp[0] = True
    for j in range(1, n + 1):
        dp[j] = dp[j - 1] and s2[j - 1] == s3[j - 1]
    for i in range(1, m + 1):
        dp[0] = dp[0] and s1[i - 1] == s3[i - 1]
        for j in range(1, n + 1):
            dp[j] = (dp[j] and s1[i - 1] == s3[i + j - 1]) or \
                    (dp[j - 1] and s2[j - 1] == s3[i + j - 1])
    return dp[n]


register(PAYLOAD, REFERENCE)
