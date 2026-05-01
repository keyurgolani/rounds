"""Decode Ways — Medium. 1D Dynamic Programming.

A 'Fibonacci with skip rules' DP. Walk left-to-right, and at each
position decide whether the current digit decodes alone (must be
non-zero) and/or pairs with the previous digit (must form 10..26).
The answer is a sum of one or two prior subproblems — exactly the
shape of Fibonacci, but with a zero/range guard at every step.

Common stumbling block: leading zeros and embedded zeros. '0' on its
own has no letter; a zero only survives as the second half of '10'
or '20'. Most off-by-one bugs in this problem trace back to a zero
being silently 'decoded' as a single character.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Decode Ways",
    "difficulty": "Medium",
    "description": (
        "A message containing letters from `A-Z` can be encoded into numbers using the following mapping:\n"
        "`'A' -> \"1\"`, `'B' -> \"2\"`, ..., `'Z' -> \"26\"`.\n\n"
        "To decode an encoded message, all the digits must be grouped then mapped back into letters using the "
        "reverse of the mapping above (there may be multiple ways). For example, `\"11106\"` can be mapped into "
        "`\"AAJF\"` (with the grouping `(1 1 10 6)`) or `\"KJF\"` (with the grouping `(11 10 6)`). Note that the "
        "grouping `(1 11 06)` is invalid because `\"06\"` cannot be mapped into `'F'` since `\"6\"` is different "
        "from `\"06\"`.\n\n"
        "Given a string `s` containing only digits, return the **number of ways** to decode it. The test cases "
        "are generated so that the answer fits in a 32-bit integer.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"12\"`\n"
        "- Output: `2`\n"
        "- Explanation: `\"12\"` could be decoded as `\"AB\"` (1 2) or `\"L\"` (12).\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"226\"`\n"
        "- Output: `3`\n"
        "- Explanation: `\"226\"` could be decoded as `\"BZ\"` (2 26), `\"VF\"` (22 6), or `\"BBF\"` (2 2 6).\n\n"
        "**Example 3:**\n"
        "- Input: `s = \"06\"`\n"
        "- Output: `0`\n"
        "- Explanation: `\"06\"` cannot be mapped to `\"F\"` because of the leading zero (`\"6\"` is different "
        "from `\"06\"`)."
    ),
    "hints": [
        "Think one position at a time. Standing at index `i`, ask: how did I get here? Either I decoded the last single digit `s[i-1]`, or I decoded the last two digits `s[i-2..i-1]` together.",
        "That gives the recurrence `dp[i] = dp[i-1] (if s[i-1] != '0') + dp[i-2] (if 10 <= int(s[i-2..i-1]) <= 26)`. It looks exactly like Fibonacci, with two boolean guards.",
        "Base case: `dp[0] = 1` (the empty prefix has one decoding — the empty message). `dp[1] = 1` if `s[0] != '0'` else `0`.",
        "Zeros are the trap. A zero never decodes alone, and it only survives when paired as `10` or `20`. Anything else (`00`, `30`, `40`, …, `90`) makes the whole string undecodable from that point.",
        "You only ever look back two positions, so collapse the array into two scalars `prev1`, `prev2` for O(1) space.",
    ],
    "constraints": [
        "1 <= s.length <= 100",
        "s contains only digits and may contain leading zero(s).",
    ],
    "starter_code": {
        "python": "def num_decodings(s):\n    # Your code here\n    pass",
        "javascript": "function numDecodings(s) {\n    // Your code here\n}",
        "java": "public int numDecodings(String s) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\"12\", \"226\", \"06\", \"11106\"]\n"
            "    for s in cases:\n"
            "        print(f\"num_decodings({s!r}) = {num_decodings(s)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\"12\", \"226\", \"06\", \"11106\"].forEach(s =>\n"
            "    console.log(`numDecodings(${JSON.stringify(s)}) =`, numDecodings(s))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.numDecodings(\"226\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "12"}, "expected": 2,
         "description": "Two decodings: 'AB' or 'L'", "tags": ["basic"]},
        {"input": {"s": "226"}, "expected": 3,
         "description": "Three decodings: 'BZ', 'VF', 'BBF'", "tags": ["basic"]},
        {"input": {"s": "06"}, "expected": 0,
         "description": "Leading zero — invalid encoding", "tags": ["edge"]},
        {"input": {"s": "10"}, "expected": 1,
         "description": "Only 'J' — the zero must pair", "tags": ["edge"]},
        {"input": {"s": "27"}, "expected": 1,
         "description": "27 > 26 so only the (2)(7) split is valid", "tags": ["tricky"]},
        {"input": {"s": "0"}, "expected": 0,
         "description": "Single zero — no letter maps to 0", "tags": ["edge"]},
        {"input": {"s": "1"}, "expected": 1,
         "description": "Single non-zero digit — one decoding", "tags": ["edge"]},
        {"input": {"s": "11106"}, "expected": 2,
         "description": "Two decodings: 'AAJF' (1 1 10 6) or 'KJF' (11 10 6)", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Bottom-Up DP — Two Scalars (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk left-to-right. Keep `prev2` = decodings of `s[:i-1]` and `prev1` = decodings of `s[:i]`. "
                "At each step, the new count is the sum of two contributions: `prev1` if the current digit is "
                "non-zero (decode it alone), and `prev2` if the current digit pairs with the previous one to "
                "form 10..26. Then slide the window."
            ),
            "code": {
                "python": (
                    "def num_decodings(s):\n"
                    "    if not s or s[0] == '0':\n"
                    "        return 0\n"
                    "    prev2, prev1 = 1, 1  # dp[0], dp[1]\n"
                    "    for i in range(2, len(s) + 1):\n"
                    "        cur = 0\n"
                    "        if s[i - 1] != '0':\n"
                    "            cur += prev1\n"
                    "        two = int(s[i - 2:i])\n"
                    "        if 10 <= two <= 26:\n"
                    "            cur += prev2\n"
                    "        prev2, prev1 = prev1, cur\n"
                    "    return prev1"
                ),
                "javascript": (
                    "function numDecodings(s) {\n"
                    "    if (!s || s[0] === '0') return 0;\n"
                    "    let prev2 = 1, prev1 = 1;\n"
                    "    for (let i = 2; i <= s.length; i++) {\n"
                    "        let cur = 0;\n"
                    "        if (s[i - 1] !== '0') cur += prev1;\n"
                    "        const two = parseInt(s.slice(i - 2, i), 10);\n"
                    "        if (two >= 10 && two <= 26) cur += prev2;\n"
                    "        prev2 = prev1;\n"
                    "        prev1 = cur;\n"
                    "    }\n"
                    "    return prev1;\n"
                    "}"
                ),
                "java": (
                    "public int numDecodings(String s) {\n"
                    "    if (s == null || s.isEmpty() || s.charAt(0) == '0') return 0;\n"
                    "    int prev2 = 1, prev1 = 1;\n"
                    "    for (int i = 2; i <= s.length(); i++) {\n"
                    "        int cur = 0;\n"
                    "        if (s.charAt(i - 1) != '0') cur += prev1;\n"
                    "        int two = Integer.parseInt(s.substring(i - 2, i));\n"
                    "        if (two >= 10 && two <= 26) cur += prev2;\n"
                    "        prev2 = prev1;\n"
                    "        prev1 = cur;\n"
                    "    }\n"
                    "    return prev1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Top-Down Recursion with Memoisation",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Same recurrence, expressed top-down. `decode(i)` returns the number of ways to decode `s[i:]`. "
                "If `s[i] == '0'` return 0. Otherwise return `decode(i+1) + (decode(i+2) if s[i:i+2] forms "
                "10..26 else 0)`. Cache by `i`. Useful when explaining the recursion tree on the whiteboard "
                "before collapsing to bottom-up."
            ),
            "code": {
                "python": (
                    "def num_decodings(s):\n"
                    "    from functools import lru_cache\n"
                    "    n = len(s)\n"
                    "\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def decode(i):\n"
                    "        if i == n:\n"
                    "            return 1\n"
                    "        if s[i] == '0':\n"
                    "            return 0\n"
                    "        ways = decode(i + 1)\n"
                    "        if i + 1 < n and 10 <= int(s[i:i + 2]) <= 26:\n"
                    "            ways += decode(i + 2)\n"
                    "        return ways\n"
                    "\n"
                    "    return decode(0)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: each position is either decoded as a single digit (1..9) or as a pair with the previous digit (10..26). Count the ways.",
        "2. Try a tiny example by hand. For '226': splits are (2)(2)(6), (22)(6), (2)(26) → 3. The structure 'last step was 1 char or 2 chars' is exactly the Fibonacci recurrence.",
        "3. Recurrence: `dp[i] = dp[i-1]` (if `s[i-1] != '0'`, decode last char alone) `+ dp[i-2]` (if `s[i-2..i-1]` forms 10..26, decode last two together).",
        "4. Base cases: `dp[0] = 1` (empty prefix has the empty decoding); `dp[1] = 1` if `s[0] != '0'` else `0`. A leading zero kills the entire string.",
        "5. Zero handling is the crux. `'0'` never decodes alone, so the single-digit branch contributes nothing when `s[i-1] == '0'`. It survives only when paired as `'10'` or `'20'`; any other zero (`'30'`, `'00'`, …) zeroes the entire suffix.",
        "6. Space optimisation: only `dp[i-1]` and `dp[i-2]` are ever needed → keep two scalars, slide forward, return the last one. O(n) time, O(1) space.",
    ],
    "tips": [
        "Most bugs are zero bugs. Walk through `'10'`, `'100'`, `'101'`, `'301'` mentally before submitting — they cover all the failure modes.",
        "Don't stringify and re-parse if the language makes it cheap to compare digits directly. In Python `int(s[i-2:i])` is fine; in C++/Java prefer `(s[i-2]-'0')*10 + (s[i-1]-'0')`.",
        "When asked for the actual decodings (not the count), switch to backtracking — DP only counts, it doesn't enumerate. The follow-up is a different problem with exponential output.",
        "LeetCode 639 'Decode Ways II' adds a `'*'` wildcard that stands for any digit 1..9. Same recurrence shape, but each transition multiplies by the count of digits the wildcard can represent (1, 2, 9, …) and you must take the result modulo 10⁹+7.",
        "If asked about constraints up to 10⁵ or larger, the O(1)-space iterative version is the only acceptable answer — recursion will blow the stack.",
    ],
    "companies": ["Amazon", "Microsoft", "Facebook"],
    "topics": ["String", "Dynamic Programming"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(s):
    if not s or s[0] == '0':
        return 0
    prev2, prev1 = 1, 1
    for i in range(2, len(s) + 1):
        cur = 0
        if s[i - 1] != '0':
            cur += prev1
        two = int(s[i - 2:i])
        if 10 <= two <= 26:
            cur += prev2
        prev2, prev1 = prev1, cur
    return prev1


register(PAYLOAD, REFERENCE)
