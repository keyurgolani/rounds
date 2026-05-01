"""Pow(x, n) — Medium. Math / Binary Exponentiation / Recursion.

The classic 'fast power' problem. Naive multiplication is O(n) and TLEs
for n up to ~2^31. The trick: use the binary representation of n to
square and multiply in O(log n). Two flavors — iterative (squaring x
while halving n via bit checks) and recursive (split n in half). Watch
the negative-n case and the INT_MIN edge: -INT_MIN overflows in C/Java
unless you widen to long first. In Python this is a non-issue, but
interviewers still want you to mention it.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Pow(x, n)",
    "difficulty": "Medium",
    "description": (
        "Implement `pow(x, n)`, which calculates `x` raised to the power `n` (i.e., `x^n`).\n\n"
        "**Example 1:**\n"
        "- Input: `x = 2.00000, n = 10`\n"
        "- Output: `1024.00000`\n\n"
        "**Example 2:**\n"
        "- Input: `x = 2.10000, n = 3`\n"
        "- Output: `9.26100`\n\n"
        "**Example 3:**\n"
        "- Input: `x = 2.00000, n = -2`\n"
        "- Output: `0.25000`\n"
        "- Explanation: `2^-2 = 1/2^2 = 1/4 = 0.25`."
    ),
    "hints": [
        "Naive `x * x * ... * x` is O(n). For `n` up to 2^31 this TLEs. State it as the baseline, then improve.",
        "Fast power (binary exponentiation): if `n` is even, `x^n = (x^(n/2))^2`; if `n` is odd, `x^n = x * x^(n-1)`. O(log n).",
        "Iterative form: walk the bits of `n` low-to-high, squaring `x` each step and multiplying it into the result whenever the current bit is 1.",
        "Negative `n`: compute `x^(-n)` and return `1 / result`. Equivalently, replace `x` with `1/x` and negate `n`.",
        "INT_MIN edge: in C/Java, `-n` overflows when `n == INT_MIN`. Widen to `long` (or convert to a 64-bit type) before negating. Python ints are arbitrary precision so this isn't a runtime issue, but mention it in interviews.",
    ],
    "constraints": [
        "-100.0 < x < 100.0",
        "-2^31 <= n <= 2^31 - 1",
        "n is an integer; either x is non-zero or n > 0.",
    ],
    "starter_code": {
        "python": "def my_pow(x, n):\n    # Your code here\n    pass",
        "javascript": "function myPow(x, n) {\n    // Your code here\n}",
        "java": "public double myPow(double x, int n) {\n    // Your code here\n    return 0.0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(2.0, 10), (2.1, 3), (2.0, -2), (1.0, 1000000)]\n"
            "    for x, n in cases:\n"
            "        print(f\"my_pow({x}, {n}) = {my_pow(x, n)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[2.0, 10], [2.1, 3], [2.0, -2]].forEach(([x, n]) =>\n"
            "    console.log(`myPow(${x}, ${n}) =`, myPow(x, n))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.myPow(2.0, 10));\n"
            "        System.out.println(s.myPow(2.1, 3));\n"
            "        System.out.println(s.myPow(2.0, -2));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"x": 2.0, "n": 10},
         "expected": {"$match": "approx", "value": 1024.0, "abs_tol": 1e-5},
         "description": "Classic 2^10 = 1024", "tags": ["basic"]},
        {"input": {"x": 2.1, "n": 3},
         "expected": {"$match": "approx", "value": 9.261, "abs_tol": 1e-5},
         "description": "Non-integer base, small odd exponent", "tags": ["basic"]},
        {"input": {"x": 2.0, "n": -2},
         "expected": {"$match": "approx", "value": 0.25, "abs_tol": 1e-5},
         "description": "Negative exponent — reciprocal", "tags": ["basic"]},
        {"input": {"x": 5.0, "n": 0},
         "expected": {"$match": "approx", "value": 1.0, "abs_tol": 1e-5},
         "description": "n = 0 — anything to the zero is 1", "tags": ["edge"]},
        {"input": {"x": 1.0, "n": 1000000},
         "expected": {"$match": "approx", "value": 1.0, "abs_tol": 1e-5},
         "description": "x = 1 with huge n — must stay 1, no precision drift", "tags": ["edge"]},
        {"input": {"x": -1.0, "n": 1000000},
         "expected": {"$match": "approx", "value": 1.0, "abs_tol": 1e-5},
         "description": "x = -1 with even n — 1", "tags": ["edge"]},
        {"input": {"x": -1.0, "n": 999999},
         "expected": {"$match": "approx", "value": -1.0, "abs_tol": 1e-5},
         "description": "x = -1 with odd n — -1", "tags": ["edge"]},
        {"input": {"x": 3.0, "n": 1},
         "expected": {"$match": "approx", "value": 3.0, "abs_tol": 1e-5},
         "description": "n = 1 — identity", "tags": ["edge"]},
        {"input": {"x": 1.00001, "n": 1000},
         "expected": {"$match": "approx", "value": 1.0100501670841672, "abs_tol": 1e-5},
         "description": "Very large n — must run in O(log n), not O(n)", "tags": ["large"]},
        {"input": {"x": 1.00000001, "n": -100000000},
         "expected": {"$match": "approx", "value": 0.36787945131749766, "abs_tol": 1e-5},
         "description": "Big negative n with x close to 1 — log-time compounding", "tags": ["large"]},
        {"input": {"x": 0.0, "n": 5},
         "expected": {"$match": "approx", "value": 0.0, "abs_tol": 1e-5},
         "description": "x = 0 with positive n — 0", "tags": ["edge"]},
        {"input": {"x": 2.0, "n": -3},
         "expected": {"$match": "approx", "value": 0.125, "abs_tol": 1e-5},
         "description": "Negative odd exponent — 1/8", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Iterative Binary Exponentiation",
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk the bits of `|n|` from low to high. Maintain a running `result = 1` and a "
                "running `base = x`. At each bit, if the bit is set, multiply `base` into `result`; "
                "then square `base` and shift `n` right. At the end, take the reciprocal if the "
                "original `n` was negative. Convert `n` to a wide integer first to dodge the "
                "`-INT_MIN` overflow in C/Java."
            ),
            "code": {
                "python": (
                    "def my_pow(x, n):\n"
                    "    if n < 0:\n"
                    "        x = 1 / x\n"
                    "        n = -n\n"
                    "    result = 1.0\n"
                    "    base = x\n"
                    "    while n > 0:\n"
                    "        if n & 1:\n"
                    "            result *= base\n"
                    "        base *= base\n"
                    "        n >>= 1\n"
                    "    return result"
                ),
                "javascript": (
                    "function myPow(x, n) {\n"
                    "    let N = n;\n"
                    "    if (N < 0) { x = 1 / x; N = -N; }\n"
                    "    let result = 1.0, base = x;\n"
                    "    while (N > 0) {\n"
                    "        if (N % 2 === 1) result *= base;\n"
                    "        base *= base;\n"
                    "        N = Math.floor(N / 2);\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public double myPow(double x, int n) {\n"
                    "    long N = n;  // widen to dodge -INT_MIN overflow\n"
                    "    if (N < 0) { x = 1 / x; N = -N; }\n"
                    "    double result = 1.0, base = x;\n"
                    "    while (N > 0) {\n"
                    "        if ((N & 1) == 1) result *= base;\n"
                    "        base *= base;\n"
                    "        N >>= 1;\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Recursive Binary Exponentiation",
            "time_complexity": "O(log n)",
            "space_complexity": "O(log n)",
            "description": (
                "Split the exponent in half each call: `x^n = x^(n/2) * x^(n/2)` for even `n`, "
                "and `x * x^(n-1)` for odd `n`. Compute the half once and multiply it by itself "
                "(don't recurse twice — that would be O(n)). Handle negative `n` by recursing on "
                "`-n` and inverting the result, with the INT_MIN widen-to-long caveat."
            ),
            "code": {
                "python": (
                    "def my_pow(x, n):\n"
                    "    def helper(x, n):\n"
                    "        if n == 0:\n"
                    "            return 1.0\n"
                    "        half = helper(x, n // 2)\n"
                    "        if n % 2 == 0:\n"
                    "            return half * half\n"
                    "        return half * half * x\n"
                    "    if n < 0:\n"
                    "        return 1 / helper(x, -n)\n"
                    "    return helper(x, n)"
                ),
                "javascript": (
                    "function myPow(x, n) {\n"
                    "    function helper(x, n) {\n"
                    "        if (n === 0) return 1.0;\n"
                    "        const half = helper(x, Math.floor(n / 2));\n"
                    "        return n % 2 === 0 ? half * half : half * half * x;\n"
                    "    }\n"
                    "    return n < 0 ? 1 / helper(x, -n) : helper(x, n);\n"
                    "}"
                ),
                "java": (
                    "public double myPow(double x, int n) {\n"
                    "    long N = n;\n"
                    "    return N < 0 ? 1.0 / helper(x, -N) : helper(x, N);\n"
                    "}\n"
                    "private double helper(double x, long n) {\n"
                    "    if (n == 0) return 1.0;\n"
                    "    double half = helper(x, n / 2);\n"
                    "    return (n % 2 == 0) ? half * half : half * half * x;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Naive: multiply x by itself n times — O(n). For n up to 2^31, this TLEs. State it as the baseline.",
        "2. Observation: x^n = (x^(n/2))^2 for even n, and x * x^(n-1) for odd n. Each step halves n → O(log n).",
        "3. Iterative form: walk bits of n. result starts at 1, base starts at x. If current bit is 1, multiply base into result. Always square base, shift n right.",
        "4. Negative n: compute the positive-exponent answer and take its reciprocal. Equivalently, set x = 1/x and negate n up front.",
        "5. INT_MIN edge: -INT_MIN overflows 32-bit signed int. In C/Java, widen n to long before negating. In Python, no-op — but mention it.",
        "6. Recursive form: same idea, divide-and-conquer. Compute half = pow(x, n/2) once and reuse — recursing twice degrades to O(n).",
    ],
    "tips": [
        "If you write `pow(x, n/2) * pow(x, n/2)` you've just made it O(n). Bind `half` to a variable and square it.",
        "Convert n to long *before* checking sign and negating. The `-INT_MIN` overflow is the most common bug interviewers look for.",
        "Both branches of the recursion need to bottom out at `n == 0 → 1.0`, not `n == 1`. Forgetting this gives wrong answers for x^0.",
        "Iterative is preferred in interviews — O(1) extra space and no stack-overflow risk for huge n. Recursive is cleaner but uses O(log n) stack.",
        "Built-ins (`Math.pow`, `**`, `Math.Pow`) are off-limits — interviewers want to see the algorithm. Mention you'd use the built-in in production.",
        "Floating-point precision: x = 1.0 with huge n must stay exactly 1.0. The fast-power code handles this naturally; naive repeated multiplication would too. Worth noting if asked about numerical stability.",
    ],
    "companies": ["Google", "Facebook", "Amazon", "Microsoft", "Bloomberg", "LinkedIn"],
    "topics": ["Math", "Recursion", "Binary Exponentiation", "Bit Manipulation"],
    "time_complexity": "O(log n)",
    "space_complexity": "O(1)",
}


def REFERENCE(x, n):
    if n < 0:
        x = 1 / x
        n = -n
    result = 1.0
    base = x
    while n > 0:
        if n & 1:
            result *= base
        base *= base
        n >>= 1
    return float(result)


register(PAYLOAD, REFERENCE)
