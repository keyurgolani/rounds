"""Counting Bits — Easy. Dynamic Programming / Bit Manipulation.

LeetCode 338. The naive answer is 'count bits per number' (Brian
Kernighan or builtin popcount), giving O(n log n) overall. The
'expected' optimal is the linear DP recurrence
`ans[i] = ans[i >> 1] + (i & 1)` — every number is its right shift
plus its lowest bit. Worth knowing the alternate recurrence
`ans[i] = ans[i & (i - 1)] + 1` because it shows up in interviews
as 'remove the lowest set bit'.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Counting Bits",
    "difficulty": "Easy",
    "description": (
        "Given an integer `n`, return an array `ans` of length `n + 1` such that for each `i` "
        "(`0 <= i <= n`), `ans[i]` is the **number of 1's** in the binary representation of `i`.\n\n"
        "**Example 1:**\n"
        "- Input: `n = 2`\n"
        "- Output: `[0,1,1]`\n"
        "- Explanation: `0 = 0b0` (0 ones), `1 = 0b1` (1 one), `2 = 0b10` (1 one).\n\n"
        "**Example 2:**\n"
        "- Input: `n = 5`\n"
        "- Output: `[0,1,1,2,1,2]`\n"
        "- Explanation: `0 → 0`, `1 → 1`, `2 → 10`, `3 → 11`, `4 → 100`, `5 → 101`. "
        "Bit counts: `0,1,1,2,1,2`.\n\n"
        "**Follow-up:** Can you do it in `O(n)` time and a single pass, *without* using a built-in "
        "popcount function?"
    ),
    "hints": [
        "Brute force: for each `i` from 0 to `n`, count its bits with Brian Kernighan (`while x: x &= x - 1; cnt++`). O(n log n) total — fine, but not the 'expected' answer.",
        "Key DP observation: `i >> 1` drops the lowest bit. So `popcount(i) = popcount(i >> 1) + (i & 1)`. Each entry is computed from one already-computed entry — O(1) per element, O(n) total.",
        "Alternate recurrence: `ans[i] = ans[i & (i - 1)] + 1`. `i & (i - 1)` clears the lowest set bit, so the answer is 'one more than the answer for i with that bit removed'. Equally O(n).",
        "Both recurrences need `ans[0] = 0` as the base case. Allocate an array of length `n + 1` up front.",
        "Don't reach for `bin(i).count('1')` or `Integer.bitCount(i)` — interviewers asking this question want the recurrence. State the builtin as an option, then write the DP.",
    ],
    "constraints": [
        "0 <= n <= 10⁵",
        "The returned array has length exactly `n + 1`.",
        "`ans[0]` is always 0.",
    ],
    "starter_code": {
        "python": "def count_bits(n):\n    # Your code here\n    pass",
        "javascript": "function countBits(n) {\n    // Your code here\n}",
        "java": "public int[] countBits(int n) {\n    // Your code here\n    return new int[0];\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for n in [0, 2, 5, 8]:\n"
            "        print(f\"count_bits({n}) = {count_bits(n)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[0, 2, 5, 8].forEach(n =>\n"
            "    console.log(`countBits(${n}) =`, countBits(n))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.Arrays;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(Arrays.toString(s.countBits(5)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"n": 0}, "expected": [0],
         "description": "Smallest input — only ans[0] = 0", "tags": ["edge"]},
        {"input": {"n": 1}, "expected": [0, 1],
         "description": "Two elements — 0 and 1", "tags": ["edge"]},
        {"input": {"n": 2}, "expected": [0, 1, 1],
         "description": "Example 1 from prompt", "tags": ["basic"]},
        {"input": {"n": 5}, "expected": [0, 1, 1, 2, 1, 2],
         "description": "Example 2 from prompt", "tags": ["basic"]},
        {"input": {"n": 8}, "expected": [0, 1, 1, 2, 1, 2, 2, 3, 1],
         "description": "Power-of-two boundary — ans[8] resets to 1", "tags": ["basic"]},
        {"input": {"n": 15}, "expected": [0, 1, 1, 2, 1, 2, 2, 3, 1, 2, 2, 3, 2, 3, 3, 4],
         "description": "All 4-bit values — ans[15] = 4 (0b1111)", "tags": ["tricky"]},
        {"input": {"n": 16}, "expected": [0, 1, 1, 2, 1, 2, 2, 3, 1, 2, 2, 3, 2, 3, 3, 4, 1],
         "description": "Crosses into 5-bit numbers — ans[16] = 1 (0b10000)", "tags": ["tricky"]},
        {"input": {"n": 31},
         "expected": [0, 1, 1, 2, 1, 2, 2, 3, 1, 2, 2, 3, 2, 3, 3, 4,
                      1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5],
         "description": "All 5-bit values — ans[31] = 5 (0b11111)", "tags": ["tricky"]},
        {"input": {"n": 1000}, "expected": None,
         "description": "Large input sanity — verified against reference", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "DP — Right Shift Recurrence (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "For any positive integer `i`, `i >> 1` is `i` with its lowest bit dropped. So the "
                "number of ones in `i` is the number of ones in `i >> 1` plus the lowest bit `i & 1`. "
                "Build the array left-to-right; each entry is O(1) work."
            ),
            "code": {
                "python": (
                    "def count_bits(n):\n"
                    "    ans = [0] * (n + 1)\n"
                    "    for i in range(1, n + 1):\n"
                    "        ans[i] = ans[i >> 1] + (i & 1)\n"
                    "    return ans"
                ),
                "javascript": (
                    "function countBits(n) {\n"
                    "    const ans = new Array(n + 1).fill(0);\n"
                    "    for (let i = 1; i <= n; i++) {\n"
                    "        ans[i] = ans[i >> 1] + (i & 1);\n"
                    "    }\n"
                    "    return ans;\n"
                    "}"
                ),
                "java": (
                    "public int[] countBits(int n) {\n"
                    "    int[] ans = new int[n + 1];\n"
                    "    for (int i = 1; i <= n; i++) {\n"
                    "        ans[i] = ans[i >> 1] + (i & 1);\n"
                    "    }\n"
                    "    return ans;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brian Kernighan + Memo (Lowest-Bit Recurrence)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "`i & (i - 1)` clears the lowest set bit of `i`. So `popcount(i) = popcount(i & (i - 1)) + 1`. "
                "Because `i & (i - 1) < i`, the dependency is always already computed — fill left-to-right. "
                "Conceptually equivalent to the right-shift recurrence; mention both because interviewers "
                "sometimes specifically ask for the Kernighan framing."
            ),
            "code": {
                "python": (
                    "def count_bits(n):\n"
                    "    ans = [0] * (n + 1)\n"
                    "    for i in range(1, n + 1):\n"
                    "        ans[i] = ans[i & (i - 1)] + 1\n"
                    "    return ans"
                ),
                "javascript": (
                    "function countBits(n) {\n"
                    "    const ans = new Array(n + 1).fill(0);\n"
                    "    for (let i = 1; i <= n; i++) {\n"
                    "        ans[i] = ans[i & (i - 1)] + 1;\n"
                    "    }\n"
                    "    return ans;\n"
                    "}"
                ),
                "java": (
                    "public int[] countBits(int n) {\n"
                    "    int[] ans = new int[n + 1];\n"
                    "    for (int i = 1; i <= n; i++) {\n"
                    "        ans[i] = ans[i & (i - 1)] + 1;\n"
                    "    }\n"
                    "    return ans;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force — Hamming Weight Per Number",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "For each `i` from 0 to `n`, count its bits independently using Brian Kernighan's loop "
                "(`while x: x &= x - 1; cnt += 1`). Each number takes O(popcount) ≤ O(log n) time. "
                "State this as the baseline before producing the linear DP."
            ),
            "code": {
                "python": (
                    "def count_bits(n):\n"
                    "    def popcount(x):\n"
                    "        c = 0\n"
                    "        while x:\n"
                    "            x &= x - 1\n"
                    "            c += 1\n"
                    "        return c\n"
                    "    return [popcount(i) for i in range(n + 1)]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force: count bits per number with Brian Kernighan → O(n log n). State it; usable, but the question is famous for having an O(n) DP.",
        "2. Look for structure between consecutive answers. `i` in binary is `(i >> 1)` shifted left, with the lowest bit appended. So `popcount(i) = popcount(i >> 1) + (i & 1)`.",
        "3. That's an O(1) transition with one already-computed dependency (`i >> 1 < i`). Fill the array left-to-right — O(n) total.",
        "4. Alternate framing: `i & (i - 1)` clears the lowest set bit. So `popcount(i) = popcount(i & (i - 1)) + 1`. Same structure, same complexity.",
        "5. Base case: `ans[0] = 0`. The array has length `n + 1`, not `n`.",
        "6. Edge case: `n = 0` — return `[0]`. The loop body doesn't execute; the zero-initialised array is already correct.",
    ],
    "tips": [
        "Don't conflate `n` (the input integer) with `len(ans)` — the array has length `n + 1`. Off-by-one bugs are the most common mistake on this question.",
        "`bin(i).count('1')` (Python) or `Integer.bitCount(i)` (Java) is a one-liner — *mention* it as 'the language gives me popcount', then write the DP. Skipping straight to the builtin annoys interviewers.",
        "The two recurrences (`ans[i >> 1] + (i & 1)` vs. `ans[i & (i - 1)] + 1`) are equally good. Pick whichever you can derive on the whiteboard most naturally.",
        "Common follow-up — 'do it in O(1) extra space (excluding the output array)'. Both DPs already do; just make sure you're not allocating auxiliary structures.",
        "Common follow-up — 'Number of 1 Bits' (LC 191): popcount of a single integer. Same Brian Kernighan loop, no array needed.",
        "Watch for unsigned-vs-signed in Java/C++: `>>>` is the unsigned right shift in Java; `>>` is fine here because `i` is non-negative, but mention the distinction if asked about negative inputs.",
    ],
    "companies": ["Amazon", "Apple", "Microsoft", "Google", "Facebook"],
    "topics": ["Dynamic Programming", "Bit Manipulation"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(n):
    ans = [0] * (n + 1)
    for i in range(1, n + 1):
        ans[i] = ans[i >> 1] + (i & 1)
    return ans


# Backfill the n=1000 expected output from REFERENCE so the test case is concrete.
for _case in PAYLOAD["test_cases"]:
    if _case["expected"] is None:
        _case["expected"] = REFERENCE(_case["input"]["n"])


register(PAYLOAD, REFERENCE)
