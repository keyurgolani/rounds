"""Reverse Bits — Easy. Bit Manipulation.

The classic 32-bit reversal. Two flavours worth knowing: the loop-32-times
shift-and-OR (clean, obvious, O(32) but really O(1) since the width is
fixed), and the divide-and-conquer mask swap (true O(1) with a constant
number of ops). For repeated calls in tight loops, byte-cache lookup
beats both. LeetCode follow-up explicitly asks the cache question.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Reverse Bits",
    "difficulty": "Easy",
    "description": (
        "Reverse the bits of a given **32-bit unsigned integer**.\n\n"
        "Note: in some languages (such as Java) there is no unsigned integer type; the input and output "
        "will be given as a signed integer type and should not affect your implementation, since the "
        "internal binary representation is the same whether it is signed or unsigned.\n\n"
        "**Example 1:**\n"
        "- Input: `n = 43261596` (binary `00000010100101000001111010011100`)\n"
        "- Output: `964176192` (binary `00111001011110000010100101000000`)\n"
        "- Explanation: The input represents the unsigned integer 43261596; its reversal is 964176192.\n\n"
        "**Example 2:**\n"
        "- Input: `n = 4294967293` (binary `11111111111111111111111111111101`)\n"
        "- Output: `3221225471` (binary `10111111111111111111111111111111`)\n"
        "- Explanation: The input represents the unsigned integer 4294967293; its reversal is 3221225471.\n\n"
        "**Follow-up:** If this function is called many times, how would you optimize it?"
    ),
    "hints": [
        "Loop exactly 32 times. Each iteration: shift the result left by 1, OR in the lowest bit of `n`, then shift `n` right by 1. Total cost is O(32) = O(1) on a fixed-width word.",
        "Mask out the low bit with `n & 1`; never test `n != 0` as the loop guard — you must process all 32 positions even when the high bits are zero.",
        "Divide and conquer: swap adjacent bit-pairs (mask `0x55555555` / `0xAAAAAAAA`), then nibbles (`0x33...` / `0xCC...`), then bytes-within-shorts (`0x0F...` / `0xF0...`), then bytes (`0x00FF00FF` / `0xFF00FF00`), then halves (`<<16` / `>>16`). Five constant-shift steps.",
        "For repeated calls (the LC follow-up): split `n` into 4 bytes, look each up in a precomputed `byte_reverse[256]` table, then concatenate them in reversed byte order. ~4 lookups per call.",
        "Watch the language: in Python integers are unbounded — mask the result with `0xFFFFFFFF` at the end. In Java, use the unsigned right shift `>>>`, never `>>`.",
    ],
    "constraints": [
        "The input must be a binary string of length 32.",
        "0 <= n <= 2³¹ − 1 (treat the bit pattern as unsigned 32-bit).",
        "Output must fit in a 32-bit unsigned integer.",
    ],
    "starter_code": {
        "python": "def reverse_bits(n):\n    # Your code here\n    pass",
        "javascript": "function reverseBits(n) {\n    // Your code here\n}",
        "java": "// Treat n as an unsigned 32-bit integer\npublic int reverseBits(int n) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [43261596, 4294967293, 0, 1]\n"
            "    for n in cases:\n"
            "        print(f\"reverse_bits({n}) = {reverse_bits(n)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "// Note: JS bitwise ops are 32-bit signed; use `>>> 0` to view as unsigned.\n"
            "[43261596, 4294967293, 0, 1].forEach(n =>\n"
            "    console.log(`reverseBits(${n}) =`, reverseBits(n) >>> 0)\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        // Use Integer.toUnsignedLong() if you want to print as unsigned.\n"
            "        System.out.println(Integer.toUnsignedLong(s.reverseBits(43261596)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"n": 0}, "expected": 0,
         "description": "All zeros — reverses to all zeros", "tags": ["edge"]},
        {"input": {"n": 1}, "expected": 2147483648,
         "description": "Lowest bit set → highest bit set (2³¹)", "tags": ["edge"]},
        {"input": {"n": 2}, "expected": 1073741824,
         "description": "Bit 1 → bit 30 (2³⁰)", "tags": ["edge"]},
        {"input": {"n": 2147483648}, "expected": 1,
         "description": "Highest bit set → lowest bit set", "tags": ["edge"]},
        {"input": {"n": 43261596}, "expected": 964176192,
         "description": "LeetCode example 1 — classic reversal", "tags": ["basic"]},
        {"input": {"n": 4294967293}, "expected": 3221225471,
         "description": "LeetCode example 2 — only bit 1 is zero", "tags": ["basic"]},
        {"input": {"n": 4294967295}, "expected": 4294967295,
         "description": "All ones — palindrome under reversal", "tags": ["edge"]},
        {"input": {"n": 2863311530}, "expected": 1431655765,
         "description": "Alternating 1010...10 → 0101...01 (0xAAAAAAAA → 0x55555555)", "tags": ["tricky"]},
        {"input": {"n": 1431655765}, "expected": 2863311530,
         "description": "Alternating 0101...01 → 1010...10 (0x55555555 → 0xAAAAAAAA)", "tags": ["tricky"]},
        {"input": {"n": 65535}, "expected": 4294901760,
         "description": "Low 16 bits set → high 16 bits set (0x0000FFFF → 0xFFFF0000)", "tags": ["tricky"]},
        {"input": {"n": 16}, "expected": 134217728,
         "description": "Mid-range single bit (bit 4 → bit 27)", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Iterative 32-bit Loop (Optimal)",
            "time_complexity": "O(1)",
            "space_complexity": "O(1)",
            "description": (
                "Loop exactly 32 times. Each iteration shifts `result` left by one, ORs in the current "
                "low bit of `n`, then shifts `n` right by one. The fixed iteration count makes this O(1) "
                "for the 32-bit problem. Clean to write under interview pressure."
            ),
            "code": {
                "python": (
                    "def reverse_bits(n):\n"
                    "    result = 0\n"
                    "    for _ in range(32):\n"
                    "        result = (result << 1) | (n & 1)\n"
                    "        n >>= 1\n"
                    "    return result & 0xFFFFFFFF"
                ),
                "javascript": (
                    "function reverseBits(n) {\n"
                    "    let result = 0;\n"
                    "    for (let i = 0; i < 32; i++) {\n"
                    "        result = (result << 1) | (n & 1);\n"
                    "        n >>>= 1;\n"
                    "    }\n"
                    "    return result >>> 0;\n"
                    "}"
                ),
                "java": (
                    "public int reverseBits(int n) {\n"
                    "    int result = 0;\n"
                    "    for (int i = 0; i < 32; i++) {\n"
                    "        result = (result << 1) | (n & 1);\n"
                    "        n >>>= 1;\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Bit-Pair Swap (Divide and Conquer)",
            "time_complexity": "O(1)",
            "space_complexity": "O(1)",
            "description": (
                "Five constant-shift mask swaps: pairs, nibbles, bytes-within-shorts, bytes, halves. "
                "Truly O(1) with a small fixed instruction count — no loop. The same trick the bit-twiddling "
                "hacks page uses for `bswap`-style reversal. Worth knowing because interviewers love it."
            ),
            "code": {
                "python": (
                    "def reverse_bits(n):\n"
                    "    n = ((n & 0x55555555) << 1) | ((n & 0xAAAAAAAA) >> 1)  # swap pairs\n"
                    "    n = ((n & 0x33333333) << 2) | ((n & 0xCCCCCCCC) >> 2)  # swap nibbles\n"
                    "    n = ((n & 0x0F0F0F0F) << 4) | ((n & 0xF0F0F0F0) >> 4)  # swap bytes within shorts\n"
                    "    n = ((n & 0x00FF00FF) << 8) | ((n & 0xFF00FF00) >> 8)  # swap bytes\n"
                    "    n = ((n & 0x0000FFFF) << 16) | ((n & 0xFFFF0000) >> 16)  # swap halves\n"
                    "    return n & 0xFFFFFFFF"
                ),
                "javascript": (
                    "function reverseBits(n) {\n"
                    "    n = ((n & 0x55555555) << 1) | ((n >>> 1) & 0x55555555);\n"
                    "    n = ((n & 0x33333333) << 2) | ((n >>> 2) & 0x33333333);\n"
                    "    n = ((n & 0x0F0F0F0F) << 4) | ((n >>> 4) & 0x0F0F0F0F);\n"
                    "    n = ((n & 0x00FF00FF) << 8) | ((n >>> 8) & 0x00FF00FF);\n"
                    "    n = (n << 16) | (n >>> 16);\n"
                    "    return n >>> 0;\n"
                    "}"
                ),
                "java": (
                    "public int reverseBits(int n) {\n"
                    "    n = ((n & 0x55555555) << 1) | ((n >>> 1) & 0x55555555);\n"
                    "    n = ((n & 0x33333333) << 2) | ((n >>> 2) & 0x33333333);\n"
                    "    n = ((n & 0x0F0F0F0F) << 4) | ((n >>> 4) & 0x0F0F0F0F);\n"
                    "    n = ((n & 0x00FF00FF) << 8) | ((n >>> 8) & 0x00FF00FF);\n"
                    "    n = (n << 16) | (n >>> 16);\n"
                    "    return n;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Byte-Cache Lookup (Repeated Calls)",
            "time_complexity": "O(1)",
            "space_complexity": "O(256)",
            "description": (
                "The LeetCode follow-up: 'if called many times, how would you optimize?' Precompute an "
                "8-bit reverse table once. Then each call is four table lookups + three shifts. Beats "
                "the loop in tight loops because it amortizes the per-bit work across 256 cached entries."
            ),
            "code": {
                "python": (
                    "_CACHE = [int(f'{i:08b}'[::-1], 2) for i in range(256)]\n"
                    "\n"
                    "def reverse_bits(n):\n"
                    "    return (\n"
                    "        (_CACHE[n & 0xFF] << 24)\n"
                    "        | (_CACHE[(n >> 8) & 0xFF] << 16)\n"
                    "        | (_CACHE[(n >> 16) & 0xFF] << 8)\n"
                    "        | _CACHE[(n >> 24) & 0xFF]\n"
                    "    )"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate the problem: walk bit 0 → bit 31 of input, write each into bit 31 → bit 0 of output.",
        "2. Naive: build a 32-char binary string, reverse it, parse it back. Works but wasteful — interview signal is poor.",
        "3. The O(32) loop is the canonical answer. Loop 32 times — never `while n` — because trailing zeros in the input become leading zeros in the output and must be processed.",
        "4. In Python, integers are arbitrary precision — mask with `0xFFFFFFFF` at the end so the result fits in 32 bits. In Java/JS, use the unsigned right shift (`>>>`).",
        "5. Divide-and-conquer is the show-off answer: swap pairs, nibbles, bytes-within-shorts, bytes, halves. Five fixed mask-and-shift steps; truly constant ops.",
        "6. Follow-up — repeated calls: cache 8-bit reversals in a 256-entry table; reduce per call to 4 lookups and 3 shifts.",
    ],
    "tips": [
        "Loop a *fixed* 32 times. `while n != 0` is a common bug — it stops early and leaves trailing bits unset.",
        "Python's integers are unbounded — finish with `result & 0xFFFFFFFF` to truncate to 32 bits.",
        "JavaScript bitwise ops coerce to 32-bit *signed*. Use the unsigned right shift `>>>` when extracting bits and `>>> 0` to convert the final result to its unsigned interpretation for printing.",
        "Java has no unsigned int — `>>>` is the unsigned right shift; `>>` is sign-extending and will corrupt the high bit.",
        "The five-mask divide-and-conquer trick is the same pattern as `popcount` — both walk pair → nibble → byte → short → int. Recognising the family helps you reproduce either under pressure.",
        "For the follow-up: split into bytes, not nibbles. A 256-entry table fits in L1 cache; a 16-entry nibble table is too small to amortize the per-call cost.",
    ],
    "companies": ["Apple", "Amazon", "Microsoft", "Airbnb", "Bloomberg"],
    "topics": ["Bit Manipulation", "Divide and Conquer"],
    "time_complexity": "O(1)",
    "space_complexity": "O(1)",
}


def REFERENCE(n):
    result = 0
    for _ in range(32):
        result = (result << 1) | (n & 1)
        n >>= 1
    return result & 0xFFFFFFFF


register(PAYLOAD, REFERENCE)
