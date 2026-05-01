"""Palindromic Substrings — Medium. String / DP / Two Pointers.

The expand-around-centers classic. Brute force is O(n³) (every substring,
each checked for palindromicity). The clean O(n²) trick is to fix a
*center* and expand outwards as long as the characters match — every
expansion step discovers exactly one new palindrome. There are 2n−1
centers (n single-char centers for odd-length palindromes, n−1 between-
char centers for even-length ones), so the total work is O(n²) time and
O(1) extra space.

Worth knowing the DP framing too: dp[i][j] = (s[i] == s[j]) and dp[i+1][j-1].
Same complexity in time, worse in space, but the recurrence is the
conceptual anchor for the related 'Longest Palindromic Substring' and
'Palindrome Partitioning' questions. Manacher's gets you O(n) but is
overkill for an interview unless explicitly asked.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Palindromic Substrings",
    "difficulty": "Medium",
    "description": (
        "Given a string `s`, return the number of **palindromic substrings** in it.\n\n"
        "A string is a palindrome when it reads the same backward as forward. A substring is a "
        "contiguous sequence of characters within the string. Different substrings count separately "
        "even if they consist of the same characters.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"abc\"`\n"
        "- Output: `3`\n"
        "- Explanation: Three palindromic strings: `\"a\"`, `\"b\"`, `\"c\"`.\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"aaa\"`\n"
        "- Output: `6`\n"
        "- Explanation: Six palindromic strings: `\"a\"`, `\"a\"`, `\"a\"`, `\"aa\"`, `\"aa\"`, `\"aaa\"`."
    ),
    "hints": [
        "Brute force: enumerate every substring (O(n²) of them) and check each for palindromicity (O(n)) → O(n³). State it; do better.",
        "Key insight: every palindrome has a *center*. There are 2n−1 centers — n single-character centers (odd length) and n−1 between-character centers (even length).",
        "For each center, expand outward while `s[left] == s[right]`. Each successful expansion step *is* a new palindrome — count it.",
        "DP framing: `dp[i][j]` is True iff `s[i..j]` is a palindrome. Recurrence: `dp[i][j] = (s[i] == s[j]) and (j - i < 2 or dp[i+1][j-1])`. Sum the True cells.",
        "Manacher's algorithm gets O(n) by reusing palindrome information across centers, but it's almost never expected in an interview unless you're asked specifically.",
    ],
    "constraints": [
        "0 <= s.length <= 1000",
        "s consists of lowercase English letters.",
    ],
    "starter_code": {
        "python": "def count_substrings(s):\n    # Your code here\n    pass",
        "javascript": "function countSubstrings(s) {\n    // Your code here\n}",
        "java": "public int countSubstrings(String s) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\"abc\", \"aaa\", \"racecar\", \"abccba\"]\n"
            "    for s in cases:\n"
            "        print(f\"count_substrings({s!r}) = {count_substrings(s)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\"abc\", \"aaa\", \"racecar\", \"abccba\"].forEach(s =>\n"
            "    console.log(`countSubstrings(${JSON.stringify(s)}) =`, countSubstrings(s))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution sol = new Solution();\n"
            "        System.out.println(sol.countSubstrings(\"aaa\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "abc"}, "expected": 3,
         "description": "All distinct chars — only single-char palindromes", "tags": ["basic"]},
        {"input": {"s": "aaa"}, "expected": 6,
         "description": "All same — 3 single + 2 doubles + 1 triple", "tags": ["basic"]},
        {"input": {"s": ""}, "expected": 0,
         "description": "Empty string — no palindromes", "tags": ["edge"]},
        {"input": {"s": "a"}, "expected": 1,
         "description": "Single char — itself", "tags": ["edge"]},
        {"input": {"s": "racecar"}, "expected": 10,
         "description": "Classic odd-length palindrome with nested palindromes", "tags": ["tricky"]},
        {"input": {"s": "abccba"}, "expected": 9,
         "description": "Even-length palindrome — exercises between-char centers", "tags": ["tricky"]},
        {"input": {"s": "abba"}, "expected": 6,
         "description": "Small even-length palindrome — 4 singles + \"bb\" + \"abba\"", "tags": ["tricky"]},
        {"input": {"s": "aaaa"}, "expected": 10,
         "description": "Four equal chars — 4 + 3 + 2 + 1 palindromes", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Expand Around Centers (Optimal in practice)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "Iterate over every possible palindrome center — there are 2n−1 of them. For each center, "
                "expand outward as long as the surrounding characters match; each successful expansion is a "
                "new palindrome. Constant extra space, no DP table required."
            ),
            "code": {
                "python": (
                    "def count_substrings(s):\n"
                    "    def expand(left, right):\n"
                    "        count = 0\n"
                    "        while left >= 0 and right < len(s) and s[left] == s[right]:\n"
                    "            count += 1\n"
                    "            left -= 1\n"
                    "            right += 1\n"
                    "        return count\n"
                    "\n"
                    "    total = 0\n"
                    "    for i in range(len(s)):\n"
                    "        total += expand(i, i)      # odd-length center\n"
                    "        total += expand(i, i + 1)  # even-length center\n"
                    "    return total"
                ),
                "javascript": (
                    "function countSubstrings(s) {\n"
                    "    const expand = (left, right) => {\n"
                    "        let count = 0;\n"
                    "        while (left >= 0 && right < s.length && s[left] === s[right]) {\n"
                    "            count++;\n"
                    "            left--;\n"
                    "            right++;\n"
                    "        }\n"
                    "        return count;\n"
                    "    };\n"
                    "    let total = 0;\n"
                    "    for (let i = 0; i < s.length; i++) {\n"
                    "        total += expand(i, i);\n"
                    "        total += expand(i, i + 1);\n"
                    "    }\n"
                    "    return total;\n"
                    "}"
                ),
                "java": (
                    "public int countSubstrings(String s) {\n"
                    "    int total = 0;\n"
                    "    for (int i = 0; i < s.length(); i++) {\n"
                    "        total += expand(s, i, i);\n"
                    "        total += expand(s, i, i + 1);\n"
                    "    }\n"
                    "    return total;\n"
                    "}\n"
                    "\n"
                    "private int expand(String s, int left, int right) {\n"
                    "    int count = 0;\n"
                    "    while (left >= 0 && right < s.length() && s.charAt(left) == s.charAt(right)) {\n"
                    "        count++;\n"
                    "        left--;\n"
                    "        right++;\n"
                    "    }\n"
                    "    return count;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Dynamic Programming Table",
            "time_complexity": "O(n²)",
            "space_complexity": "O(n²)",
            "description": (
                "Build a 2D table where `dp[i][j]` is True iff `s[i..j]` is a palindrome. The recurrence is "
                "`dp[i][j] = (s[i] == s[j]) and (j - i < 2 or dp[i+1][j-1])`. Fill in order of increasing "
                "substring length and count the True cells. Same time as expand-around-centers but worse "
                "space — useful as the conceptual bridge to 'Longest Palindromic Substring' and "
                "'Palindrome Partitioning'."
            ),
            "code": {
                "python": (
                    "def count_substrings(s):\n"
                    "    n = len(s)\n"
                    "    if n == 0:\n"
                    "        return 0\n"
                    "    dp = [[False] * n for _ in range(n)]\n"
                    "    total = 0\n"
                    "    for length in range(1, n + 1):\n"
                    "        for i in range(n - length + 1):\n"
                    "            j = i + length - 1\n"
                    "            if s[i] == s[j] and (length < 3 or dp[i + 1][j - 1]):\n"
                    "                dp[i][j] = True\n"
                    "                total += 1\n"
                    "    return total"
                ),
            },
        },
        {
            "title": "Manacher's Algorithm",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Linear-time palindrome counting by transforming the string with sentinels (e.g. "
                "`^#a#b#a#$`) so every palindrome is odd-length, then maintaining an array `p[i]` of "
                "palindrome radii. By exploiting symmetry around the rightmost-known palindrome's center, "
                "each radius is computed in amortised O(1). The total count is `sum((p[i] + 1) // 2)`. "
                "Rarely required in interviews — name-drop only if asked for sub-quadratic."
            ),
            "code": {
                "python": (
                    "def count_substrings(s):\n"
                    "    if not s:\n"
                    "        return 0\n"
                    "    t = '^#' + '#'.join(s) + '#$'\n"
                    "    n = len(t)\n"
                    "    p = [0] * n\n"
                    "    center = right = 0\n"
                    "    for i in range(1, n - 1):\n"
                    "        mirror = 2 * center - i\n"
                    "        if i < right:\n"
                    "            p[i] = min(right - i, p[mirror])\n"
                    "        while t[i + p[i] + 1] == t[i - p[i] - 1]:\n"
                    "            p[i] += 1\n"
                    "        if i + p[i] > right:\n"
                    "            center, right = i, i + p[i]\n"
                    "    return sum((r + 1) // 2 for r in p)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force baseline: enumerate every substring (O(n²)) and check each for palindromicity (O(n)) → O(n³). State it, then improve.",
        "2. Observation: every palindrome has a *center*. Counting palindromes is equivalent to counting (center, radius) pairs.",
        "3. Centers come in two flavours: between two characters (even length) and on a character (odd length). For a string of length n, that's exactly 2n−1 centers.",
        "4. For each center, expand outward as long as `s[left] == s[right]`. Each successful step *is* a new distinct palindrome — increment a counter.",
        "5. Total work: each character can appear in at most O(n) palindromes (it can be at most n positions away from any center it belongs to), so the total expansion work is O(n²).",
        "6. Edge cases: empty string returns 0; single character returns 1; all-equal strings of length n return n*(n+1)/2 — a useful sanity check.",
    ],
    "tips": [
        "Connection to **Longest Palindromic Substring**: same expand-around-centers framework, but track the longest palindrome instead of counting. One algorithm, two questions.",
        "Why DP and expand-around-centers share O(n²): both visit the same conceptual (i, j) substring grid. DP fills it explicitly in a 2D array; expand-around-centers traverses it diagonally without storing it. Same work, different space.",
        "The 2n−1 centers count trips up many candidates — say it out loud when explaining your approach to avoid undercounting even-length palindromes.",
        "Don't conflate 'distinct palindromic substrings' with 'palindromic substring occurrences'. This problem counts *occurrences* — `\"aaa\"` has six, not three. If interviewer asks for distinct, you need a set or a more advanced structure (suffix automaton / Eertree).",
        "Manacher's is a flex, not a requirement. State the O(n²) approach confidently; only bring up Manacher if asked for better-than-quadratic.",
    ],
    "companies": ["Amazon", "Google", "Facebook"],
    "topics": ["String", "Dynamic Programming", "Two Pointers"],
    "time_complexity": "O(n²)",
    "space_complexity": "O(1)",
}


def REFERENCE(s):
    def expand(left, right):
        count = 0
        while left >= 0 and right < len(s) and s[left] == s[right]:
            count += 1
            left -= 1
            right += 1
        return count

    total = 0
    for i in range(len(s)):
        total += expand(i, i)
        total += expand(i, i + 1)
    return total


register(PAYLOAD, REFERENCE)
