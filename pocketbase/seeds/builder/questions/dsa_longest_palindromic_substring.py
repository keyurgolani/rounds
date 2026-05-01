"""Longest Palindromic Substring — Medium. String / Expand Around Center.

Return the longest palindromic substring of s. Expand-around-center is
the canonical O(n²) solution; Manacher's is the O(n) follow-up."""
from builder.registry import register
from builder.registry import validator


_LONGEST_PAL_VALIDATOR = (
    "lambda inp, out: ("
    "isinstance(out, str) and "
    "out == out[::-1] and "
    "out in inp['s']"
    ")"
)


PAYLOAD = {
    "title": "Longest Palindromic Substring",
    "difficulty": "Medium",
    "description": (
        "Given a string `s`, return the **longest palindromic substring** of `s`. If multiple substrings "
        "of the same maximum length exist, returning any is acceptable.\n\n"
        "**Example 1:**\n"
        "- Input: `s = 'babad'`\n"
        "- Output: `'bab'` (or `'aba'`)\n\n"
        "**Example 2:**\n"
        "- Input: `s = 'cbbd'`\n"
        "- Output: `'bb'`\n\n"
        "**Example 3:**\n"
        "- Input: `s = ''`\n"
        "- Output: `''`"
    ),
    "hints": [
        "Brute force: enumerate every (i, j) substring, check palindrome. O(n^3). Reject for n > a few hundred.",
        "Expand around center: every palindrome has a center (one char for odd length, between two for even). Try each of 2n-1 centers; expand while characters match. O(n²) time, O(1) space.",
        "DP: `dp[i][j] = True` iff `s[i:j+1]` is palindrome. Base: dp[i][i] = True; transition: dp[i][j] = (s[i] == s[j]) and dp[i+1][j-1]. O(n²) time, O(n²) space.",
        "Manacher's algorithm: O(n) time using the symmetry of palindromes around an active center. Hard to derive under pressure but worth name-dropping.",
        "Edge cases: empty string, single char, all identical chars (whole string), all distinct chars (any single char).",
    ],
    "constraints": [
        "0 <= |s| <= 1000",
        "ASCII",
    ],
    "starter_code": {
        "python": "def longest_palindrome(s):\n    # Your code here\n    pass",
        "javascript": "function longestPalindrome(s) {\n    // Your code here\n}",
        "java": "public String longestPalindrome(String s) {\n    // Your code here\n    return \"\";\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for s in ['babad', 'cbbd', '', 'a', 'forgeeksskeegfor']:\n"
            "        print(f\"longest_palindrome({s!r}) = {longest_palindrome(s)!r}\")"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"s": "babad"},
         "expected": validator("Palindrome substring of s of max length",
                                _LONGEST_PAL_VALIDATOR, examples=["bab", "aba"]),
         "description": "Two valid answers", "tags": ["basic"]},
        {"input": {"s": "cbbd"}, "expected": "bb",
         "description": "Even-length palindrome", "tags": ["basic"]},
        {"input": {"s": ""}, "expected": "",
         "description": "Empty string", "tags": ["edge"]},
        {"input": {"s": "a"}, "expected": "a",
         "description": "Single char", "tags": ["edge"]},
        {"input": {"s": "forgeeksskeegfor"}, "expected": "geeksskeeg",
         "description": "Long even-length palindrome embedded mid-string", "tags": ["tricky"]},
        {"input": {"s": "aaaa"}, "expected": "aaaa",
         "description": "All identical — entire string", "tags": ["edge"]},
        {"input": {"s": "abc"},
         "expected": validator("Single char palindrome",
                                _LONGEST_PAL_VALIDATOR, examples=["a", "b", "c"]),
         "description": "All distinct — any single char", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Expand Around Center (Optimal in Practice)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "For each of the 2n-1 possible centers (n single chars for odd lengths, n-1 inter-char "
                "positions for even lengths), expand outwards while characters match. Track the best "
                "(longest) span seen. Constant extra space."
            ),
            "code": {
                "python": (
                    "def longest_palindrome(s):\n"
                    "    if not s:\n"
                    "        return ''\n"
                    "    best_start = 0\n"
                    "    best_len = 1\n"
                    "    def expand(l, r):\n"
                    "        while l >= 0 and r < len(s) and s[l] == s[r]:\n"
                    "            l -= 1; r += 1\n"
                    "        return l + 1, r - 1\n"
                    "    for i in range(len(s)):\n"
                    "        # odd-length center\n"
                    "        l, r = expand(i, i)\n"
                    "        if r - l + 1 > best_len:\n"
                    "            best_start, best_len = l, r - l + 1\n"
                    "        # even-length center\n"
                    "        l, r = expand(i, i + 1)\n"
                    "        if r - l + 1 > best_len:\n"
                    "            best_start, best_len = l, r - l + 1\n"
                    "    return s[best_start:best_start + best_len]"
                ),
                "javascript": (
                    "function longestPalindrome(s) {\n"
                    "    if (!s) return '';\n"
                    "    let bs = 0, bl = 1;\n"
                    "    const expand = (l, r) => {\n"
                    "        while (l >= 0 && r < s.length && s[l] === s[r]) { l--; r++; }\n"
                    "        return [l + 1, r - 1];\n"
                    "    };\n"
                    "    for (let i = 0; i < s.length; i++) {\n"
                    "        let [l, r] = expand(i, i);\n"
                    "        if (r - l + 1 > bl) { bs = l; bl = r - l + 1; }\n"
                    "        [l, r] = expand(i, i + 1);\n"
                    "        if (r - l + 1 > bl) { bs = l; bl = r - l + 1; }\n"
                    "    }\n"
                    "    return s.slice(bs, bs + bl);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Dynamic Programming",
            "time_complexity": "O(n²)",
            "space_complexity": "O(n²)",
            "description": (
                "`dp[i][j]` = `True` if `s[i:j+1]` is a palindrome. Fill by increasing length. O(n²) extra "
                "space — loses to expand-around-center on memory but is sometimes preferred when you also "
                "need 'is s[i:j+1] palindrome?' queries downstream."
            ),
            "code": {
                "python": (
                    "def longest_palindrome(s):\n"
                    "    n = len(s)\n"
                    "    if n == 0:\n"
                    "        return ''\n"
                    "    dp = [[False] * n for _ in range(n)]\n"
                    "    best_start, best_len = 0, 1\n"
                    "    for i in range(n):\n"
                    "        dp[i][i] = True\n"
                    "    for length in range(2, n + 1):\n"
                    "        for i in range(n - length + 1):\n"
                    "            j = i + length - 1\n"
                    "            if s[i] == s[j] and (length == 2 or dp[i+1][j-1]):\n"
                    "                dp[i][j] = True\n"
                    "                if length > best_len:\n"
                    "                    best_start, best_len = i, length\n"
                    "    return s[best_start:best_start + best_len]"
                ),
            },
        },
        {
            "title": "Manacher's Algorithm (O(n))",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Insert sentinels between characters to unify odd/even cases. Track an 'active' palindrome's "
                "center and right boundary; for each position, mirror-reflect to seed a known palindrome "
                "length, then extend. Hard to write under interview pressure; mention it for credit."
            ),
            "code": {
                "python": (
                    "def longest_palindrome(s):\n"
                    "    if not s:\n"
                    "        return ''\n"
                    "    t = '#' + '#'.join(s) + '#'\n"
                    "    n = len(t)\n"
                    "    p = [0] * n\n"
                    "    c = r = 0\n"
                    "    for i in range(n):\n"
                    "        mirror = 2 * c - i\n"
                    "        if i < r:\n"
                    "            p[i] = min(r - i, p[mirror])\n"
                    "        while i + p[i] + 1 < n and i - p[i] - 1 >= 0 and t[i + p[i] + 1] == t[i - p[i] - 1]:\n"
                    "            p[i] += 1\n"
                    "        if i + p[i] > r:\n"
                    "            c, r = i, i + p[i]\n"
                    "    max_i = max(range(n), key=lambda i: p[i])\n"
                    "    start = (max_i - p[max_i]) // 2\n"
                    "    return s[start:start + p[max_i]]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force is O(n^3). Reject.",
        "2. Reframe: every palindrome has a center. There are 2n-1 of them (n char centers + n-1 between-char centers). For each, expand while characters match.",
        "3. Expand-around-center: O(n²), O(1) space — clean to write.",
        "4. DP variant: O(n²), O(n²) space. Useful only if you also need 'is range palindrome?' queries.",
        "5. Manacher's: O(n) — name-drop, implement only if you have it memorised cold.",
        "6. Edge cases: empty (return ''), single char, all identical, all distinct, even-length palindrome.",
    ],
    "tips": [
        "Don't forget the even-length case. Trying only odd centers misses 'cbbd' → 'bb'.",
        "The 'sentinel' trick (inserting '#' between chars) reduces the two cases to one but isn't necessary if you handle them explicitly.",
        "If the string can be very long (10^5 plus), Manacher is the only reasonable choice. For n=10^3, expand-around-center is fine.",
        "Common follow-up: 'longest palindromic SUBSEQUENCE' (not substring) — different problem, classic O(n²) DP on subsequence.",
        "Common follow-up: 'count palindromic substrings' (LeetCode 647) — modify expand-around-center to count expansions.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Apple"],
    "topics": ["String", "Dynamic Programming", "Two Pointers"],
    "time_complexity": "O(n²)",
    "space_complexity": "O(1)",
}


def REFERENCE(s):
    if not s:
        return ""
    best_start = 0
    best_len = 1

    def expand(l, r):
        while l >= 0 and r < len(s) and s[l] == s[r]:
            l -= 1
            r += 1
        return l + 1, r - 1

    for i in range(len(s)):
        l, r = expand(i, i)
        if r - l + 1 > best_len:
            best_start, best_len = l, r - l + 1
        l, r = expand(i, i + 1)
        if r - l + 1 > best_len:
            best_start, best_len = l, r - l + 1
    return s[best_start:best_start + best_len]


register(PAYLOAD, REFERENCE)
