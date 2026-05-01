"""Reverse Integer — Medium. Math / Overflow Handling.

The classic 'reverse digits with %10 and //10' question whose entire
difficulty lies in the 32-bit overflow check. The mechanical part is a
two-line loop; the interesting part is detecting overflow *before* it
happens, since the problem assumes you cannot store 64-bit integers
(LeetCode's original constraint). Worth practising the pre-overflow
arithmetic — same trick shows up in 'String to Integer (atoi)' and
'Divide Two Integers'.
"""
from builder.registry import register


INT_MAX = 2**31 - 1   # 2147483647
INT_MIN = -(2**31)    # -2147483648


PAYLOAD = {
    "title": "Reverse Integer",
    "difficulty": "Medium",
    "description": (
        "Given a signed 32-bit integer `x`, return `x` with its digits reversed. If reversing `x` causes "
        "the value to go outside the signed 32-bit integer range `[-2^31, 2^31 - 1]`, then return `0`.\n\n"
        "**Assume the environment does not allow you to store 64-bit integers** (signed or unsigned).\n\n"
        "**Example 1:**\n"
        "- Input: `x = 123`\n"
        "- Output: `321`\n\n"
        "**Example 2:**\n"
        "- Input: `x = -123`\n"
        "- Output: `-321`\n\n"
        "**Example 3:**\n"
        "- Input: `x = 120`\n"
        "- Output: `21`\n"
        "- Explanation: Trailing zeros disappear after reversal."
    ),
    "hints": [
        "Extract digits one at a time using `digit = x % 10` and shrink with `x //= 10`. Build the result with "
        "`result = result * 10 + digit`. That's the entire mechanical loop.",
        "Sign handling: in Python, `%` and `//` round toward negative infinity, which gives you wrong digits "
        "for negative numbers. Either operate on `abs(x)` and re-apply the sign, or use truncated division.",
        "The whole challenge is the 32-bit overflow check. The naive 'reverse, then compare' breaks the rule "
        "that says you cannot store 64-bit integers — the intermediate `result * 10 + digit` can already be "
        "out of range.",
        "Pre-overflow check: before doing `result = result * 10 + digit`, ask 'would that exceed INT_MAX?'. "
        "If `result > INT_MAX // 10`, definitely overflow. If `result == INT_MAX // 10` and `digit > 7`, "
        "overflow (because INT_MAX = 2147483647 ends in 7). Mirror logic for INT_MIN with `-8`.",
        "Trailing zeros (e.g. 120) drop out automatically because `result * 10 + 0 = result`. No special case.",
    ],
    "constraints": [
        "-2^31 <= x <= 2^31 - 1",
        "Assume the environment cannot store 64-bit integers.",
        "Return 0 on overflow.",
    ],
    "starter_code": {
        "python": "def reverse(x):\n    # Your code here\n    pass",
        "javascript": "function reverse(x) {\n    // Your code here\n}",
        "java": "public int reverse(int x) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [123, -123, 120, 0, 1534236469]\n"
            "    for x in cases:\n"
            "        print(f\"reverse({x}) = {reverse(x)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[123, -123, 120, 0, 1534236469].forEach(x =>\n"
            "    console.log(`reverse(${x}) =`, reverse(x))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.reverse(123));\n"
            "        System.out.println(s.reverse(-123));\n"
            "        System.out.println(s.reverse(1534236469));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"x": 123}, "expected": 321,
         "description": "Basic positive — 123 → 321", "tags": ["basic"]},
        {"input": {"x": -123}, "expected": -321,
         "description": "Basic negative — sign preserved", "tags": ["basic"]},
        {"input": {"x": 120}, "expected": 21,
         "description": "Trailing zero collapses on reverse", "tags": ["basic"]},
        {"input": {"x": 0}, "expected": 0,
         "description": "Zero stays zero", "tags": ["edge"]},
        {"input": {"x": 7}, "expected": 7,
         "description": "Single digit — palindromic by definition", "tags": ["edge"]},
        {"input": {"x": -8}, "expected": -8,
         "description": "Single negative digit", "tags": ["edge"]},
        {"input": {"x": 1534236469}, "expected": 0,
         "description": "Reverse would be 9646324351 > INT_MAX → 0", "tags": ["overflow"]},
        {"input": {"x": -1534236469}, "expected": 0,
         "description": "Reverse would be -9646324351 < INT_MIN → 0", "tags": ["overflow"]},
        {"input": {"x": 1463847412}, "expected": 2147483641,
         "description": "Large but reverse fits — 2147483641 < INT_MAX", "tags": ["tricky"]},
        {"input": {"x": 1000000003}, "expected": 0,
         "description": "Reverse 3000000001 > INT_MAX → 0 (overflow)", "tags": ["overflow"]},
        {"input": {"x": 100}, "expected": 1,
         "description": "Multiple trailing zeros drop", "tags": ["edge"]},
        {"input": {"x": 2147483647}, "expected": 0,
         "description": "INT_MAX itself — reverse 7463847412 > INT_MAX → 0", "tags": ["overflow"]},
        {"input": {"x": -2147483648}, "expected": 0,
         "description": "INT_MIN itself — reverse -8463847412 < INT_MIN → 0", "tags": ["overflow"]},
    ],
    "solutions": [
        {
            "title": "Pre-Overflow Check (Optimal)",
            "time_complexity": "O(log₁₀ n)",
            "space_complexity": "O(1)",
            "description": (
                "Pop digits with `% 10` and `// 10`. Before each `result = result * 10 + digit` step, check "
                "whether the multiplication would push `result` past INT_MAX (or below INT_MIN). The boundary "
                "is `INT_MAX // 10 = 214748364`: if `result` exceeds that you overflow on the next push; if "
                "`result` equals that, overflow only when the incoming digit > 7 (since INT_MAX ends in 7). "
                "Mirror logic for INT_MIN with `-8`. Honours the no-64-bit-integer rule."
            ),
            "code": {
                "python": (
                    "def reverse(x):\n"
                    "    INT_MAX = 2**31 - 1     # 2147483647\n"
                    "    INT_MIN = -(2**31)      # -2147483648\n"
                    "    sign = -1 if x < 0 else 1\n"
                    "    x = abs(x)\n"
                    "    result = 0\n"
                    "    while x > 0:\n"
                    "        digit = x % 10\n"
                    "        x //= 10\n"
                    "        # Pre-overflow check (positive magnitude)\n"
                    "        if result > INT_MAX // 10 or (result == INT_MAX // 10 and digit > 7):\n"
                    "            return 0\n"
                    "        result = result * 10 + digit\n"
                    "    result *= sign\n"
                    "    if result < INT_MIN or result > INT_MAX:\n"
                    "        return 0\n"
                    "    return result"
                ),
                "javascript": (
                    "function reverse(x) {\n"
                    "    const INT_MAX = 2**31 - 1;\n"
                    "    const INT_MIN = -(2**31);\n"
                    "    const sign = x < 0 ? -1 : 1;\n"
                    "    x = Math.abs(x);\n"
                    "    let result = 0;\n"
                    "    while (x > 0) {\n"
                    "        const digit = x % 10;\n"
                    "        x = Math.floor(x / 10);\n"
                    "        if (result > Math.floor(INT_MAX / 10) ||\n"
                    "            (result === Math.floor(INT_MAX / 10) && digit > 7)) {\n"
                    "            return 0;\n"
                    "        }\n"
                    "        result = result * 10 + digit;\n"
                    "    }\n"
                    "    return result * sign;\n"
                    "}"
                ),
                "java": (
                    "public int reverse(int x) {\n"
                    "    int result = 0;\n"
                    "    while (x != 0) {\n"
                    "        int digit = x % 10;\n"
                    "        x /= 10;\n"
                    "        // Pre-overflow check (works for both signs)\n"
                    "        if (result > Integer.MAX_VALUE / 10 ||\n"
                    "            (result == Integer.MAX_VALUE / 10 && digit > 7)) return 0;\n"
                    "        if (result < Integer.MIN_VALUE / 10 ||\n"
                    "            (result == Integer.MIN_VALUE / 10 && digit < -8)) return 0;\n"
                    "        result = result * 10 + digit;\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Long Wrap and Check",
            "time_complexity": "O(log₁₀ n)",
            "space_complexity": "O(1)",
            "description": (
                "Pragmatic version when the language gives you a wider type for free: do the reverse in a "
                "64-bit accumulator, then compare against INT_MAX/INT_MIN at the end. Cleanest code; *fails "
                "the problem's stated constraint*, so flag that in the interview before writing it. Useful as "
                "a sanity-check baseline."
            ),
            "code": {
                "python": (
                    "def reverse(x):\n"
                    "    INT_MAX = 2**31 - 1\n"
                    "    INT_MIN = -(2**31)\n"
                    "    sign = -1 if x < 0 else 1\n"
                    "    rev = int(str(abs(x))[::-1]) * sign\n"
                    "    return rev if INT_MIN <= rev <= INT_MAX else 0"
                ),
                "javascript": (
                    "function reverse(x) {\n"
                    "    const sign = x < 0 ? -1 : 1;\n"
                    "    const rev = sign * parseInt(String(Math.abs(x)).split('').reverse().join(''), 10);\n"
                    "    return (rev < -(2**31) || rev > 2**31 - 1) ? 0 : rev;\n"
                    "}"
                ),
                "java": (
                    "public int reverse(int x) {\n"
                    "    long result = 0;\n"
                    "    while (x != 0) {\n"
                    "        result = result * 10 + x % 10;\n"
                    "        x /= 10;\n"
                    "    }\n"
                    "    if (result < Integer.MIN_VALUE || result > Integer.MAX_VALUE) return 0;\n"
                    "    return (int) result;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Mechanical part: `digit = x % 10`, `x //= 10`, `result = result * 10 + digit`. Three lines.",
        "2. Sign: factor it out up front (`sign = -1 if x < 0 else 1; x = abs(x)`) to dodge language-specific "
        "modulo semantics for negatives.",
        "3. The interesting question: how do you detect overflow *without* using a wider type? The naive "
        "'compute then compare' reads from a value the problem says you cannot store.",
        "4. Pre-overflow check: `result * 10 + digit > INT_MAX` rearranges to `result > INT_MAX // 10` OR "
        "(`result == INT_MAX // 10` AND `digit > INT_MAX % 10`). INT_MAX % 10 == 7.",
        "5. Mirror for INT_MIN (`% 10 == -8` in truncated semantics, hence the `-8` boundary).",
        "6. Trailing zeros need no special case — the loop drops them naturally.",
        "7. Edge cases to call out: 0, single digits, INT_MAX, INT_MIN, and any value whose reversal exceeds "
        "the bound (e.g. 1534236469).",
    ],
    "tips": [
        "INT_MAX = 2147483647 ends in 7; INT_MIN = -2147483648 ends in -8. Memorise these — the pre-overflow "
        "check uses 7 and 8 as the 'last digit' thresholds.",
        "In Python, prefer `abs(x)` then re-apply sign. Python's `%` rounds toward -∞, so `-123 % 10 == 7`, "
        "not `-3`. That breaks the digit-extraction loop if you forget.",
        "Java's `int` overflow is silent (wraps), so the pre-overflow check is the *only* correct approach in "
        "Java without using `long`. State this up front in the interview.",
        "JavaScript numbers are 64-bit floats — you have plenty of headroom, but the *problem* constrains you "
        "to 32-bit semantics, so still apply the check.",
        "Don't reverse via `int(str(x)[::-1])` in interview — it's clever but skips the algorithmic content "
        "the question is testing. Write the loop.",
        "Common mistake: applying the overflow check *after* the multiplication. By then you've already "
        "stored a value the problem says you cannot store. Check *before* you multiply.",
    ],
    "companies": ["Apple", "Amazon", "Bloomberg", "Microsoft", "Adobe"],
    "topics": ["Math"],
    "time_complexity": "O(log₁₀ n)",
    "space_complexity": "O(1)",
}


def REFERENCE(x):
    sign = -1 if x < 0 else 1
    n = abs(x)
    result = 0
    while n > 0:
        digit = n % 10
        n //= 10
        result = result * 10 + digit
    result *= sign
    if result < INT_MIN or result > INT_MAX:
        return 0
    return result


register(PAYLOAD, REFERENCE)
