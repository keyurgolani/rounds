"""Number of 1 Bits — Easy. Bit Manipulation.

The 'Hamming weight' / popcount classic. Two canonical solutions worth
knowing cold: the 32-bit shift loop (works in any language, predictable
O(32)), and Brian Kernighan's `n & (n-1)` trick (loops only over set
bits — strictly faster in practice). Builtins like `bin(n).count('1')`
or `Integer.bitCount` are fine to mention but interviewers usually want
to see the manual approach.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Number of 1 Bits",
    "difficulty": "Easy",
    "description": (
        "Write a function that takes a non-negative integer `n` and returns the number of `1` bits it has "
        "in its binary representation (also known as the **Hamming weight**).\n\n"
        "**Example 1:**\n"
        "- Input: `n = 11`\n"
        "- Output: `3`\n"
        "- Explanation: The binary representation of `11` is `1011`, which has three `1` bits.\n\n"
        "**Example 2:**\n"
        "- Input: `n = 128`\n"
        "- Output: `1`\n"
        "- Explanation: The binary representation of `128` is `10000000`, which has one `1` bit."
    ),
    "hints": [
        "Naive: shift right one bit at a time, count the LSB each step. Loop runs exactly 32 times for a 32-bit integer — predictable and language-agnostic.",
        "Brian Kernighan's trick: `n & (n - 1)` clears the lowest set bit. Loop until `n == 0`; the iteration count *is* the answer. O(set bits) instead of O(32).",
        "Why does `n & (n-1)` work? Subtracting 1 flips the lowest set bit to 0 and turns all the lower 0s into 1s; AND-ing with the original zeros all of those out — netting one fewer set bit.",
        "Language builtins: Python's `bin(n).count('1')`, Java's `Integer.bitCount(n)`, JS's `n.toString(2).split('1').length - 1`. Mention them, but interviewers usually want the manual loop.",
        "Be careful in languages with signed 32-bit ints (Java): use `>>>` (unsigned right shift), not `>>`, or the loop never terminates for negative inputs.",
    ],
    "constraints": [
        "0 <= n <= 2³¹ - 1 (treat the input as an unsigned 32-bit integer)",
        "The input is guaranteed to be a non-negative integer",
    ],
    "starter_code": {
        "python": "def hamming_weight(n):\n    # Your code here\n    pass",
        "javascript": "function hammingWeight(n) {\n    // Your code here\n}",
        "java": "public int hammingWeight(int n) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for n in [0, 1, 11, 128, 7]:\n"
            "        print(f\"hamming_weight({n}) = {hamming_weight(n)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[0, 1, 11, 128, 7].forEach(n =>\n"
            "    console.log(`hammingWeight(${n}) =`, hammingWeight(n))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        for (int n : new int[]{0, 1, 11, 128, 7}) {\n"
            "            System.out.println(\"hammingWeight(\" + n + \") = \" + s.hammingWeight(n));\n"
            "        }\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"n": 0}, "expected": 0,
         "description": "Zero — no set bits", "tags": ["edge"]},
        {"input": {"n": 1}, "expected": 1,
         "description": "Single LSB", "tags": ["edge"]},
        {"input": {"n": 11}, "expected": 3,
         "description": "0b1011 has three set bits (LeetCode example)", "tags": ["basic"]},
        {"input": {"n": 128}, "expected": 1,
         "description": "Power of two — 0b10000000, one set bit (LeetCode example)", "tags": ["basic"]},
        {"input": {"n": 2}, "expected": 1,
         "description": "0b10 — one set bit", "tags": ["edge"]},
        {"input": {"n": 7}, "expected": 3,
         "description": "0b111 — three contiguous set bits", "tags": ["basic"]},
        {"input": {"n": 65536}, "expected": 1,
         "description": "2^16 — one set bit at position 16", "tags": ["basic"]},
        {"input": {"n": 2147483647}, "expected": 31,
         "description": "2^31 - 1 — all 31 low bits set (Java Integer.MAX_VALUE)", "tags": ["large"]},
        {"input": {"n": 4294967293}, "expected": 31,
         "description": "0xFFFFFFFD — 32-bit all-ones with bit 1 cleared (LeetCode signed-edge case)", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Brian Kernighan — n & (n-1) (Optimal)",
            "time_complexity": "O(k) where k = number of set bits",
            "space_complexity": "O(1)",
            "description": (
                "Each iteration of `n &= n - 1` clears exactly one set bit (the lowest). The loop runs once "
                "per set bit, so total work is proportional to the popcount — strictly faster than a 32-step "
                "shift loop on sparse inputs. For a fully-set 32-bit integer it's the same 32 iterations."
            ),
            "code": {
                "python": (
                    "def hamming_weight(n):\n"
                    "    count = 0\n"
                    "    while n:\n"
                    "        n &= n - 1\n"
                    "        count += 1\n"
                    "    return count"
                ),
                "javascript": (
                    "function hammingWeight(n) {\n"
                    "    let count = 0;\n"
                    "    while (n !== 0) {\n"
                    "        n &= n - 1;\n"
                    "        count++;\n"
                    "    }\n"
                    "    return count;\n"
                    "}"
                ),
                "java": (
                    "public int hammingWeight(int n) {\n"
                    "    int count = 0;\n"
                    "    while (n != 0) {\n"
                    "        n &= n - 1;\n"
                    "        count++;\n"
                    "    }\n"
                    "    return count;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Bit Shift Loop (Baseline)",
            "time_complexity": "O(32)",
            "space_complexity": "O(1)",
            "description": (
                "Walk the 32 bits one at a time: AND with 1 to read the LSB, accumulate, then unsigned-shift "
                "right. Predictable iteration count regardless of popcount. Use `>>>` in Java/JS to avoid "
                "sign-extension on negative inputs."
            ),
            "code": {
                "python": (
                    "def hamming_weight(n):\n"
                    "    count = 0\n"
                    "    for _ in range(32):\n"
                    "        count += n & 1\n"
                    "        n >>= 1\n"
                    "    return count"
                ),
                "javascript": (
                    "function hammingWeight(n) {\n"
                    "    let count = 0;\n"
                    "    for (let i = 0; i < 32; i++) {\n"
                    "        count += n & 1;\n"
                    "        n >>>= 1;\n"
                    "    }\n"
                    "    return count;\n"
                    "}"
                ),
                "java": (
                    "public int hammingWeight(int n) {\n"
                    "    int count = 0;\n"
                    "    for (int i = 0; i < 32; i++) {\n"
                    "        count += n & 1;\n"
                    "        n >>>= 1;\n"
                    "    }\n"
                    "    return count;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Language Builtin (One-liner)",
            "time_complexity": "O(1) on most modern CPUs (POPCNT instruction)",
            "space_complexity": "O(1)",
            "description": (
                "Mention the builtin so the interviewer knows you know it: `bin(n).count('1')` in Python, "
                "`Integer.bitCount(n)` in Java, `n.toString(2).split('1').length - 1` in JS. Then write "
                "the manual version — they're almost always asking for the manual one."
            ),
            "code": {
                "python": (
                    "def hamming_weight(n):\n"
                    "    return bin(n).count('1')"
                ),
                "java": (
                    "public int hammingWeight(int n) {\n"
                    "    return Integer.bitCount(n);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: count the number of `1` bits in the binary expansion of `n`. This is 'popcount' / 'Hamming weight'.",
        "2. Baseline — shift loop: examine bit 0 (`n & 1`), accumulate, shift right, repeat 32 times. Easy to reason about, easy to bound.",
        "3. Optimisation — Brian Kernighan: `n & (n - 1)` clears the lowest set bit. Loop until zero; iteration count = answer. Faster on sparse inputs.",
        "4. Why it works: subtract 1 flips the lowest 1 to 0 and turns trailing 0s into 1s; AND with original zeros all those out → exactly one fewer set bit.",
        "5. Sign-bit gotcha (Java/JS): use unsigned right shift `>>>` so negative ints (or values with the high bit set) don't sign-extend and loop forever.",
        "6. Mention the builtin (`Integer.bitCount`, `bin().count('1')`, hardware POPCNT) but write the manual version unless told otherwise.",
    ],
    "tips": [
        "`n & (n - 1) == 0` (with n != 0) is the canonical 'is power of two' check — same trick, different question.",
        "In Python, integers are arbitrary-precision, so the 32-bit framing is a *convention* from the problem statement, not a language limit. Both solutions still work correctly.",
        "In Java, `int` is signed 32-bit. The high bit makes negative numbers; `>>` sign-extends and breaks the shift loop. Always `>>>` here.",
        "Common follow-up — 'Counting Bits' (LC 338): return an array of popcounts for `0..n`. DP recurrence: `dp[i] = dp[i >> 1] + (i & 1)` or `dp[i] = dp[i & (i-1)] + 1`.",
        "Common follow-up — 'Hamming Distance' (LC 461): popcount of `x ^ y`. Same algorithm, one extra XOR.",
        "Modern CPUs have a single-cycle POPCNT instruction; the language builtins compile to it. Worth knowing if you're asked about real-world performance.",
    ],
    "companies": ["Apple", "Microsoft", "Amazon", "Adobe", "Bloomberg"],
    "topics": ["Bit Manipulation", "Divide and Conquer"],
    "time_complexity": "O(k) where k = popcount (Kernighan); O(32) for the shift loop",
    "space_complexity": "O(1)",
}


def REFERENCE(n):
    count = 0
    while n:
        n &= n - 1
        count += 1
    return count


register(PAYLOAD, REFERENCE)
