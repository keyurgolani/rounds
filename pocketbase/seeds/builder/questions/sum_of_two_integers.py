"""Sum of Two Integers — Medium. Bit Manipulation.

Compute a + b without using `+` or `-`. The bit-twiddling classic: XOR
gives sum-without-carry, AND-then-shift gives the carry, iterate until
carry is zero. The Python wrinkle is that Python ints are arbitrary
precision, so you have to mask to 32 bits and reinterpret the sign
manually — otherwise negative numbers loop forever.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Sum of Two Integers",
    "difficulty": "Medium",
    "description": (
        "Given two integers `a` and `b`, return the sum of the two integers **without using the operators "
        "`+` and `-`**.\n\n"
        "You must implement the addition using bitwise operations only.\n\n"
        "**Example 1:**\n"
        "- Input: `a = 1, b = 2`\n"
        "- Output: `3`\n"
        "- Explanation: `1 + 2 = 3`, computed via XOR (sum-without-carry) and AND-shift (carry) until carry is 0.\n\n"
        "**Example 2:**\n"
        "- Input: `a = 2, b = 3`\n"
        "- Output: `5`\n"
        "- Explanation: `2 + 3 = 5`, same bit-manipulation procedure."
    ),
    "hints": [
        "`a XOR b` produces the sum of `a` and `b` *ignoring carries* — bit-by-bit half-adder output.",
        "`(a AND b) << 1` produces the *carry bits*, shifted into the next column where they belong.",
        "Loop: while there is still a carry, set `a = a XOR b` and `b = (a AND b) << 1` (compute carry from the previous a,b first). Stop when `b == 0`. Then `a` holds the answer.",
        "In Python, ints are arbitrary precision — the carry never naturally falls off the top, so negatives loop forever. Mask every step with `0xFFFFFFFF` to simulate a 32-bit register.",
        "After the loop, reinterpret the 32-bit result as signed: if the sign bit (`a & 0x80000000`) is set, return `~(a ^ 0xFFFFFFFF)` (i.e. flip the low 32 bits and negate via Python's two's-complement bitwise NOT).",
    ],
    "constraints": [
        "-1000 <= a, b <= 1000",
        "Result fits in a 32-bit signed integer.",
        "You may not use the `+` or `-` operators.",
    ],
    "starter_code": {
        "python": "def get_sum(a, b):\n    # Your code here\n    pass",
        "javascript": "function getSum(a, b) {\n    // Your code here\n}",
        "java": "public int getSum(int a, int b) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(1, 2), (2, 3), (-1, 1), (0, 0), (-2, -3)]\n"
            "    for a, b in cases:\n"
            "        print(f\"get_sum({a}, {b}) = {get_sum(a, b)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,2],[2,3],[-1,1],[0,0],[-2,-3]].forEach(([a,b]) =>\n"
            "    console.log(`getSum(${a}, ${b}) =`, getSum(a, b))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.getSum(1, 2));\n"
            "        System.out.println(s.getSum(-1, 1));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"a": 1, "b": 2}, "expected": 3,
         "description": "LeetCode example 1 — small positives", "tags": ["basic"]},
        {"input": {"a": 2, "b": 3}, "expected": 5,
         "description": "LeetCode example 2 — small positives", "tags": ["basic"]},
        {"input": {"a": -1, "b": 1}, "expected": 0,
         "description": "Opposite signs cancel — exercises 32-bit mask path", "tags": ["edge"]},
        {"input": {"a": 0, "b": 0}, "expected": 0,
         "description": "Zero + zero — loop exits immediately (b is already 0)", "tags": ["edge"]},
        {"input": {"a": -2, "b": -3}, "expected": -5,
         "description": "Both negative — sign bit must be reinterpreted from the masked register",
         "tags": ["tricky"]},
        {"input": {"a": 1000, "b": 1000}, "expected": 2000,
         "description": "Constraint maximum sum", "tags": ["edge"]},
        {"input": {"a": -1000, "b": -1000}, "expected": -2000,
         "description": "Constraint minimum sum — most negative case in range", "tags": ["edge"]},
        {"input": {"a": 7, "b": -3}, "expected": 4,
         "description": "Mixed signs, positive result", "tags": ["tricky"]},
        {"input": {"a": -7, "b": 3}, "expected": -4,
         "description": "Mixed signs, negative result", "tags": ["tricky"]},
        {"input": {"a": 100, "b": 0}, "expected": 100,
         "description": "Identity — adding 0 returns the other operand", "tags": ["edge"]},
        {"input": {"a": 999, "b": 1}, "expected": 1000,
         "description": "Carry ripples across multiple bits (999 + 1 → 1000 in binary too)",
         "tags": ["tricky"]},
        {"input": {"a": 123, "b": 456}, "expected": 579,
         "description": "Generic positive sum with intermediate carries", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Bit-Manipulation Loop with 32-bit Mask (Optimal)",
            "time_complexity": "O(1)",
            "space_complexity": "O(1)",
            "description": (
                "Half-adder logic in a loop. `a XOR b` is the sum without carries; `(a AND b) << 1` is the "
                "carry. Repeat until the carry is zero. In Python, ints are unbounded, so we mask with "
                "`0xFFFFFFFF` to simulate a 32-bit register and then reinterpret the sign bit at the end. "
                "The loop runs at most 32 times — constant time."
            ),
            "code": {
                "python": (
                    "def get_sum(a, b):\n"
                    "    MASK = 0xFFFFFFFF\n"
                    "    SIGN = 0x80000000\n"
                    "    while b & MASK:\n"
                    "        carry = ((a & b) << 1) & MASK\n"
                    "        a = (a ^ b) & MASK\n"
                    "        b = carry\n"
                    "    a &= MASK\n"
                    "    # Reinterpret as signed 32-bit\n"
                    "    return a if a < SIGN else ~(a ^ MASK)"
                ),
                "javascript": (
                    "function getSum(a, b) {\n"
                    "    // JS bitwise ops are 32-bit signed — no masking needed.\n"
                    "    while (b !== 0) {\n"
                    "        const carry = (a & b) << 1;\n"
                    "        a = a ^ b;\n"
                    "        b = carry;\n"
                    "    }\n"
                    "    return a;\n"
                    "}"
                ),
                "java": (
                    "public int getSum(int a, int b) {\n"
                    "    while (b != 0) {\n"
                    "        int carry = (a & b) << 1;\n"
                    "        a = a ^ b;\n"
                    "        b = carry;\n"
                    "    }\n"
                    "    return a;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brain-Teaser using sum() (Baseline)",
            "time_complexity": "O(1)",
            "space_complexity": "O(1)",
            "description": (
                "Strictly speaking, the problem only forbids `+` and `-` — it does not forbid `sum()`. "
                "Python's built-in `sum` produces the answer in one call. Mention this only as a "
                "lateral-thinking aside; in an interview the bit-manipulation solution is what is being "
                "tested. Useful as a sanity check / reference oracle."
            ),
            "code": {
                "python": (
                    "def get_sum(a, b):\n"
                    "    return sum([a, b])"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate the rule: no `+`, no `-`. So we have to *build* addition out of bitwise primitives.",
        "2. Recall the half-adder: for one bit, `sum = a XOR b` and `carry = a AND b`. Generalises to ints if you shift the carry one position left.",
        "3. The carry has to be added back in — but we can't use `+`. Recurse: feed `(a XOR b)` and `(a AND b) << 1` back into the same procedure. Stop when there is no carry left.",
        "4. Convergence: each iteration shifts the carry left by one bit, so after at most 32 iterations the carry falls off a 32-bit register. The loop is O(1).",
        "5. Python wrinkle: ints are arbitrary precision. The carry never falls off the top → infinite loop on negatives. Fix: mask both operands with `0xFFFFFFFF` every step.",
        "6. Sign reinterpretation: after the loop, `a` is in `[0, 2³²)`. If the high bit (`0x80000000`) is set, the answer is negative — convert via Python's `~(a ^ 0xFFFFFFFF)` (flip low 32 bits, then bitwise NOT to get the negative value).",
        "7. Edge cases to verify: `0 + 0` (loop exits immediately), opposite signs (`-1 + 1 = 0`, mask + sign reinterpret), both negative (`-2 + -3 = -5`).",
    ],
    "tips": [
        "Order matters in the loop body: compute the carry from the *current* `a` and `b` *before* you overwrite `a` with `a ^ b`. Otherwise you compute the carry from the wrong operand.",
        "JavaScript and Java do this naturally — their `&`, `^`, `<<` operators are already 32-bit. Only Python needs the explicit mask. Mention the language difference if asked.",
        "The mask trick generalises: any 'simulate a fixed-width register in Python' problem (two's-complement subtraction, integer overflow, etc.) uses the same `& 0xFFFFFFFF` then sign-bit-check pattern.",
        "If the interviewer asks 'why does the loop terminate?', the answer is: each iteration the carry shifts left by one bit, so within 32 iterations the carry is shifted out of the masked register and becomes 0.",
        "Common follow-up — subtraction without `+`/`-`: `a - b == a + (-b)`, and `-b == ~b + 1`. The `+ 1` is itself a `get_sum(~b, 1)` call.",
        "Don't try to be cute with `sum([a, b])` in a real interview unless the interviewer signals they're testing lateral thinking. The expected answer is the bit-manipulation loop.",
    ],
    "companies": ["Google", "Apple", "Facebook", "Amazon", "Microsoft"],
    "topics": ["Math", "Bit Manipulation"],
    "time_complexity": "O(1)",
    "space_complexity": "O(1)",
}


def REFERENCE(a, b):
    # Ground-truth oracle: regular addition is fine here. The constraint
    # against `+`/`-` applies to the candidate's submission, not to the
    # reference used by the grader.
    return a + b


register(PAYLOAD, REFERENCE)
