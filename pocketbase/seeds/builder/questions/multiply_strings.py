"""Multiply Strings — Medium. Math / Simulation.

The 'big-int from scratch' classic. The interviewer is testing whether
you can simulate grade-school multiplication: digit-by-digit products,
correct index alignment, and carry propagation. The shortcut of
`str(int(num1) * int(num2))` is explicitly disallowed — the entire point
is to prove you can do arbitrary-precision arithmetic without leaning on
the language's big-int. The schoolbook O(m·n) algorithm is the expected
answer; FFT-based multiplication is the worth-mentioning upgrade for
genuinely huge inputs.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Multiply Strings",
    "difficulty": "Medium",
    "description": (
        "Given two non-negative integers `num1` and `num2` represented as strings, return the product "
        "of `num1` and `num2`, **also represented as a string**.\n\n"
        "**Note:** You must not use any built-in big-integer library or convert the inputs to integer "
        "directly (no `int(num1) * int(num2)` or equivalent language shortcut).\n\n"
        "**Example 1:**\n"
        "- Input: `num1 = \"2\", num2 = \"3\"`\n"
        "- Output: `\"6\"`\n\n"
        "**Example 2:**\n"
        "- Input: `num1 = \"123\", num2 = \"456\"`\n"
        "- Output: `\"56088\"`\n"
        "- Explanation: 123 × 456 = 56088. Schoolbook multiplication, digit by digit, with carry."
    ),
    "hints": [
        "Short-circuit: if either input is `\"0\"`, return `\"0\"` immediately. This avoids leading-zero bugs at the end.",
        "The product of an m-digit and an n-digit number has at most `m + n` digits. Allocate an integer buffer of size `m + n` filled with zeros.",
        "Index alignment: the digit `num1[i]` × `num2[j]` contributes to positions `i + j` (carry) and `i + j + 1` (units) of the result buffer when both strings are processed left-to-right (most-significant first).",
        "Carry handling: after writing `partial = result[i+j+1] + num1[i] * num2[j]`, set `result[i+j+1] = partial % 10` and add `partial // 10` to `result[i+j]`. Don't forget that the carry can be > 9 because `result[i+j]` already accumulates from earlier passes — but the recurrence still works because every position is touched again before being read as final.",
        "After the double loop, strip leading zeros from the buffer before joining to a string. Skip indices while `result[k] == 0`, then join the rest. If you stripped everything (only possible when an input was `\"0\"`, which you already short-circuited), return `\"0\"`.",
    ],
    "constraints": [
        "1 <= num1.length, num2.length <= 200",
        "`num1` and `num2` consist of digits only.",
        "Both `num1` and `num2` do not contain any leading zero, except the number 0 itself.",
    ],
    "starter_code": {
        "python": "def multiply(num1, num2):\n    # Your code here\n    pass",
        "javascript": "function multiply(num1, num2) {\n    // Your code here\n}",
        "java": "public String multiply(String num1, String num2) {\n    // Your code here\n    return \"\";\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(\"2\", \"3\"), (\"123\", \"456\"), (\"0\", \"99999\"), (\"9\", \"9\")]\n"
            "    for a, b in cases:\n"
            "        print(f\"multiply({a!r}, {b!r}) = {multiply(a, b)!r}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[\"2\",\"3\"], [\"123\",\"456\"], [\"0\",\"99999\"], [\"9\",\"9\"]].forEach(([a, b]) =>\n"
            "    console.log(`multiply(${a}, ${b}) =`, multiply(a, b))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.multiply(\"123\", \"456\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"num1": "2", "num2": "3"}, "expected": "6",
         "description": "Classic LC example — single digit × single digit", "tags": ["basic"]},
        {"input": {"num1": "123", "num2": "456"}, "expected": "56088",
         "description": "Classic LC example — three digits × three digits", "tags": ["basic"]},
        {"input": {"num1": "0", "num2": "99999"}, "expected": "0",
         "description": "Left operand is zero — short-circuit", "tags": ["edge"]},
        {"input": {"num1": "12345", "num2": "0"}, "expected": "0",
         "description": "Right operand is zero — short-circuit", "tags": ["edge"]},
        {"input": {"num1": "9", "num2": "9"}, "expected": "81",
         "description": "Both single digits — carry produces a two-digit result", "tags": ["edge"]},
        {"input": {"num1": "1", "num2": "1"}, "expected": "1",
         "description": "Identity — 1 × 1", "tags": ["edge"]},
        {"input": {"num1": "999", "num2": "1"}, "expected": "999",
         "description": "Identity — multiplying by 1 returns the other operand verbatim", "tags": ["edge"]},
        {"input": {"num1": "100", "num2": "10"}, "expected": "1000",
         "description": "Trailing zeros — buffer would have many leading zeros to strip", "tags": ["tricky"]},
        {"input": {"num1": "20", "num2": "5"}, "expected": "100",
         "description": "Result has trailing zeros + leading-zero edge in the buffer",
         "tags": ["tricky"]},
        {"input": {"num1": "999", "num2": "999"}, "expected": "998001",
         "description": "Maximal carry chain for three-digit operands", "tags": ["tricky"]},
        {"input": {"num1": "12345678901234567890", "num2": "98765432109876543210"},
         "expected": "1219326311370217952237463801111263526900",
         "description": "20-digit × 20-digit — exceeds 64-bit integer range", "tags": ["large"]},
        {"input": {
            "num1": "99999999999999999999999999999999999999999999999999",
            "num2": "99999999999999999999999999999999999999999999999999",
         },
         "expected": (
             "9999999999999999999999999999999999999999999999999"
             "8"
             "0000000000000000000000000000000000000000000000000"
             "1"
         ),
         "description": "50-digit × 50-digit (all 9s) — squares to a 100-digit (10^50 − 1)² result",
         "tags": ["large"]},
        {"input": {
            "num1": "12345678901234567890123456789012345678901234567890",
            "num2": "12345678901234567890123456789012345678901234567890",
         },
         "expected": (
             "152415787532388367504953515625666819450083828736206317051"
             "2230652054766307721216410828earlier".replace("earlier", "")  # placeholder, replaced below
         ),
         "description": "Square of a 50-digit number", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Schoolbook Digit Multiplication (Optimal in Practice)",
            "time_complexity": "O(m·n)",
            "space_complexity": "O(m+n)",
            "description": (
                "Allocate a buffer of length m+n (zero-filled). For each pair of digits "
                "`(num1[i], num2[j])`, compute `partial = num1[i] * num2[j] + result[i+j+1]`, "
                "write the units digit at `result[i+j+1]`, and *add* the carry into `result[i+j]`. "
                "Because each cell is revisited (it can be incremented by carries from later "
                "iterations), the loop ends with all cells in [0,9] and one final pass is enough "
                "to drop leading zeros. Short-circuit when either input is `\"0\"` to keep "
                "the leading-zero stripping simple."
            ),
            "code": {
                "python": (
                    "def multiply(num1, num2):\n"
                    "    if num1 == \"0\" or num2 == \"0\":\n"
                    "        return \"0\"\n"
                    "    m, n = len(num1), len(num2)\n"
                    "    result = [0] * (m + n)\n"
                    "    for i in range(m - 1, -1, -1):\n"
                    "        a = ord(num1[i]) - ord('0')\n"
                    "        for j in range(n - 1, -1, -1):\n"
                    "            b = ord(num2[j]) - ord('0')\n"
                    "            total = a * b + result[i + j + 1]\n"
                    "            result[i + j + 1] = total % 10\n"
                    "            result[i + j] += total // 10\n"
                    "    # Strip leading zeros\n"
                    "    k = 0\n"
                    "    while k < len(result) - 1 and result[k] == 0:\n"
                    "        k += 1\n"
                    "    return ''.join(str(d) for d in result[k:])"
                ),
                "javascript": (
                    "function multiply(num1, num2) {\n"
                    "    if (num1 === \"0\" || num2 === \"0\") return \"0\";\n"
                    "    const m = num1.length, n = num2.length;\n"
                    "    const result = new Array(m + n).fill(0);\n"
                    "    for (let i = m - 1; i >= 0; i--) {\n"
                    "        const a = num1.charCodeAt(i) - 48;\n"
                    "        for (let j = n - 1; j >= 0; j--) {\n"
                    "            const b = num2.charCodeAt(j) - 48;\n"
                    "            const total = a * b + result[i + j + 1];\n"
                    "            result[i + j + 1] = total % 10;\n"
                    "            result[i + j] += Math.floor(total / 10);\n"
                    "        }\n"
                    "    }\n"
                    "    let k = 0;\n"
                    "    while (k < result.length - 1 && result[k] === 0) k++;\n"
                    "    return result.slice(k).join('');\n"
                    "}"
                ),
                "java": (
                    "public String multiply(String num1, String num2) {\n"
                    "    if (num1.equals(\"0\") || num2.equals(\"0\")) return \"0\";\n"
                    "    int m = num1.length(), n = num2.length();\n"
                    "    int[] result = new int[m + n];\n"
                    "    for (int i = m - 1; i >= 0; i--) {\n"
                    "        int a = num1.charAt(i) - '0';\n"
                    "        for (int j = n - 1; j >= 0; j--) {\n"
                    "            int b = num2.charAt(j) - '0';\n"
                    "            int total = a * b + result[i + j + 1];\n"
                    "            result[i + j + 1] = total % 10;\n"
                    "            result[i + j] += total / 10;\n"
                    "        }\n"
                    "    }\n"
                    "    StringBuilder sb = new StringBuilder();\n"
                    "    int k = 0;\n"
                    "    while (k < result.length - 1 && result[k] == 0) k++;\n"
                    "    for (; k < result.length; k++) sb.append(result[k]);\n"
                    "    return sb.toString();\n"
                    "}"
                ),
            },
        },
        {
            "title": "FFT-Based Multiplication (Asymptotically Faster)",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "Treat each number as a polynomial whose coefficients are its digits, evaluate both "
                "via FFT, multiply pointwise in the frequency domain, inverse-FFT, then propagate "
                "carries. Beats schoolbook for very large inputs (thousands of digits) but loses to "
                "it on the LeetCode constraint (≤ 200 digits) due to the constant factor. Mention "
                "as the asymptotically optimal approach; do not write it as your first answer. "
                "Beware: floating-point FFT introduces rounding error — for exact integer "
                "multiplication you typically use NTT (number-theoretic transform) over a prime "
                "modulus, not complex FFT."
            ),
            "code": {
                "python": (
                    "def multiply(num1, num2):\n"
                    "    if num1 == \"0\" or num2 == \"0\":\n"
                    "        return \"0\"\n"
                    "    import cmath\n"
                    "    a = [ord(c) - ord('0') for c in reversed(num1)]\n"
                    "    b = [ord(c) - ord('0') for c in reversed(num2)]\n"
                    "    size = 1\n"
                    "    while size < len(a) + len(b):\n"
                    "        size *= 2\n"
                    "    a += [0] * (size - len(a))\n"
                    "    b += [0] * (size - len(b))\n"
                    "    def fft(x, invert=False):\n"
                    "        n = len(x)\n"
                    "        if n == 1:\n"
                    "            return\n"
                    "        # iterative bit-reversal FFT (sketch — production code uses NTT)\n"
                    "        j = 0\n"
                    "        for i in range(1, n):\n"
                    "            bit = n >> 1\n"
                    "            while j & bit:\n"
                    "                j ^= bit\n"
                    "                bit >>= 1\n"
                    "            j ^= bit\n"
                    "            if i < j:\n"
                    "                x[i], x[j] = x[j], x[i]\n"
                    "        length = 2\n"
                    "        while length <= n:\n"
                    "            ang = 2 * cmath.pi / length * (-1 if invert else 1)\n"
                    "            wlen = cmath.exp(1j * ang)\n"
                    "            for i in range(0, n, length):\n"
                    "                w = 1\n"
                    "                for k in range(length // 2):\n"
                    "                    u = x[i + k]\n"
                    "                    v = x[i + k + length // 2] * w\n"
                    "                    x[i + k] = u + v\n"
                    "                    x[i + k + length // 2] = u - v\n"
                    "                    w *= wlen\n"
                    "            length <<= 1\n"
                    "        if invert:\n"
                    "            for i in range(n):\n"
                    "                x[i] /= n\n"
                    "    fa = [complex(v) for v in a]\n"
                    "    fb = [complex(v) for v in b]\n"
                    "    fft(fa)\n"
                    "    fft(fb)\n"
                    "    for i in range(size):\n"
                    "        fa[i] *= fb[i]\n"
                    "    fft(fa, invert=True)\n"
                    "    digits = [round(c.real) for c in fa]\n"
                    "    carry = 0\n"
                    "    for i in range(len(digits)):\n"
                    "        digits[i] += carry\n"
                    "        carry, digits[i] = digits[i] // 10, digits[i] % 10\n"
                    "    while carry:\n"
                    "        digits.append(carry % 10)\n"
                    "        carry //= 10\n"
                    "    while len(digits) > 1 and digits[-1] == 0:\n"
                    "        digits.pop()\n"
                    "    return ''.join(str(d) for d in reversed(digits))"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate the constraint: no `int()`. The whole problem is simulating grade-school multiplication on digit arrays.",
        "2. Short-circuit zero. If either operand is `\"0\"`, return `\"0\"`. This eliminates the only case where the answer should *be* a leading zero, so the rest of the code can strip leading zeros aggressively.",
        "3. Bound the result size: an m-digit number times an n-digit number has at most m+n digits (e.g., 99 × 99 = 9801 — four digits, m+n = 4). Allocate an integer buffer of size m+n.",
        "4. Pick an indexing convention. Most-significant first (left = high-order) is natural because the input strings are already in that order. Then `num1[i] * num2[j]` lands at result indices `(i+j, i+j+1)` — the carry goes left, the units digit stays right.",
        "5. Carry handling: after writing the units digit, *add* the carry into `result[i+j]`. That cell may exceed 9 mid-loop, but it'll be visited again in a later iteration before being read for its own carry, so the recurrence stays consistent.",
        "6. Strip leading zeros at the end. The buffer is m+n long; the actual answer may be m+n-1 digits (e.g., 12 × 12 = 144 in a buffer of size 4 → `[0,1,4,4]`).",
        "7. Mention FFT as the asymptotically faster approach if the interviewer asks about scaling beyond a few hundred digits.",
    ],
    "tips": [
        "Convert digits with `ord(c) - ord('0')` (or `c - '0'`) — don't allocate a new int via `int(c)` in a hot loop, and definitely don't do `int(num1)`, which is the explicit forbidden shortcut.",
        "Iterate both indices from right (least-significant) to left. It mirrors how you do it on paper and makes the carry direction obvious.",
        "Don't pre-multiply by 10^k to align partial products into a list and sum them — that re-implements the same arithmetic at higher constant factor and is more bug-prone.",
        "Trace the loop on `\"99\" × \"99\"` once on a whiteboard before submitting. If your buffer ends `[9,8,0,1]`, you're done. If it ends with carries > 9 anywhere, your carry-add step is wrong.",
        "On the LeetCode constraint (≤ 200 digits), schoolbook is faster than FFT in practice. Don't over-engineer; bring up FFT only as a follow-up if the interviewer probes for asymptotic improvements.",
        "Watch for the leading-zero bug: `\"0\" * \"123\"` should return `\"0\"`, not `\"\"`. The short-circuit handles it; if you skip the short-circuit, your strip-leading-zeros loop must keep at least one digit.",
    ],
    "companies": ["Facebook", "Microsoft", "Apple", "Twitter", "ByteDance", "Amazon"],
    "topics": ["Math", "String", "Simulation"],
    "time_complexity": "O(m·n)",
    "space_complexity": "O(m+n)",
}


# Compute the square-of-50-digit test case expected value programmatically
# (still no language shortcut at solve-time — this is harness setup, not the
# candidate's solution). The reference implementation below proves correctness.
def _schoolbook(a: str, b: str) -> str:
    if a == "0" or b == "0":
        return "0"
    m, n = len(a), len(b)
    result = [0] * (m + n)
    for i in range(m - 1, -1, -1):
        da = ord(a[i]) - ord('0')
        for j in range(n - 1, -1, -1):
            db = ord(b[j]) - ord('0')
            total = da * db + result[i + j + 1]
            result[i + j + 1] = total % 10
            result[i + j] += total // 10
    k = 0
    while k < len(result) - 1 and result[k] == 0:
        k += 1
    return ''.join(str(d) for d in result[k:])


# Patch the placeholder square-of-50-digits expected value
_big = "12345678901234567890123456789012345678901234567890"
for _tc in PAYLOAD["test_cases"]:
    if _tc["input"].get("num1") == _big and _tc["input"].get("num2") == _big:
        _tc["expected"] = _schoolbook(_big, _big)
        break


def REFERENCE(num1, num2):
    if num1 == "0" or num2 == "0":
        return "0"
    m, n = len(num1), len(num2)
    result = [0] * (m + n)
    for i in range(m - 1, -1, -1):
        a = ord(num1[i]) - ord('0')
        for j in range(n - 1, -1, -1):
            b = ord(num2[j]) - ord('0')
            total = a * b + result[i + j + 1]
            result[i + j + 1] = total % 10
            result[i + j] += total // 10
    k = 0
    while k < len(result) - 1 and result[k] == 0:
        k += 1
    return ''.join(str(d) for d in result[k:])


register(PAYLOAD, REFERENCE)
