"""Plus One — Easy. Array / Math.

The classic 'big integer as digit array' problem. The whole game is
carry propagation walking right-to-left, with the one twist that an
all-9s input grows the array by one. Trivial in five lines once you
see it; trips candidates who reach for `int(''.join(...))` arithmetic
because the constraints in the real problem don't allow that.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Plus One",
    "difficulty": "Easy",
    "description": (
        "You are given a **large integer** represented as an integer array `digits`, where each "
        "`digits[i]` is the i-th digit of the integer. The digits are ordered from **most significant** "
        "to **least significant** in left-to-right order. The large integer does **not** contain any "
        "leading 0's, except for the number 0 itself.\n\n"
        "Increment the large integer by one and return the resulting array of digits.\n\n"
        "**Example 1:**\n"
        "- Input: `digits = [1,2,3]`\n"
        "- Output: `[1,2,4]`\n"
        "- Explanation: The array represents the integer 123. Incrementing gives 124.\n\n"
        "**Example 2:**\n"
        "- Input: `digits = [9]`\n"
        "- Output: `[1,0]`\n"
        "- Explanation: The array represents the integer 9. Incrementing gives 10, which becomes `[1,0]`.\n\n"
        "**Example 3:**\n"
        "- Input: `digits = [9,9]`\n"
        "- Output: `[1,0,0]`\n"
        "- Explanation: 99 + 1 = 100, represented as `[1,0,0]`. The array length grew by one because "
        "the carry propagated past the most significant digit."
    ),
    "hints": [
        "Walk the array **right-to-left** (least significant first). That's the natural direction for adding with carry.",
        "If the current digit is less than 9, just add 1 and return — no further carry can occur.",
        "If the current digit is 9, set it to 0 and continue left. The +1 has become a carry into the next position.",
        "If you exit the loop with the carry still alive, every digit was 9. Prepend a `1` to the array — the answer is `[1, 0, 0, ..., 0]` of length n+1.",
        "Don't reach for `int(''.join(map(str, digits))) + 1` in an interview. The real LeetCode constraints (and the spirit of the problem) forbid native big-int conversion; show you can do carry propagation by hand.",
    ],
    "constraints": [
        "1 <= digits.length <= 100",
        "0 <= digits[i] <= 9",
        "`digits` does not contain any leading 0's, except for the number 0 itself.",
    ],
    "starter_code": {
        "python": "def plus_one(digits):\n    # Your code here\n    pass",
        "javascript": "function plusOne(digits) {\n    // Your code here\n}",
        "java": "public int[] plusOne(int[] digits) {\n    // Your code here\n    return digits;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[1,2,3], [9], [9,9], [4,3,2,1]]\n"
            "    for digits in cases:\n"
            "        print(f\"plus_one({digits}) = {plus_one(list(digits))}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,2,3], [9], [9,9], [4,3,2,1]].forEach(digits =>\n"
            "    console.log(`plusOne =`, plusOne([...digits]))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.Arrays;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(Arrays.toString(s.plusOne(new int[]{1,2,3})));\n"
            "        System.out.println(Arrays.toString(s.plusOne(new int[]{9,9})));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"digits": [1, 2, 3]}, "expected": [1, 2, 4],
         "description": "LC example 1 — simple no-carry increment", "tags": ["basic"]},
        {"input": {"digits": [4, 3, 2, 1]}, "expected": [4, 3, 2, 2],
         "description": "LC example 2 — no carry", "tags": ["basic"]},
        {"input": {"digits": [0]}, "expected": [1],
         "description": "Single zero → one", "tags": ["edge"]},
        {"input": {"digits": [9]}, "expected": [1, 0],
         "description": "Single nine — array grows by one", "tags": ["edge"]},
        {"input": {"digits": [9, 9]}, "expected": [1, 0, 0],
         "description": "All nines (length 2) — array grows", "tags": ["edge"]},
        {"input": {"digits": [9, 9, 9]}, "expected": [1, 0, 0, 0],
         "description": "All nines (length 3) — array grows", "tags": ["edge"]},
        {"input": {"digits": [1, 9, 9]}, "expected": [2, 0, 0],
         "description": "Mid-array carry propagates to position 0 but does not grow", "tags": ["tricky"]},
        {"input": {"digits": [2, 4, 9, 3, 9]}, "expected": [2, 4, 9, 4, 0],
         "description": "Carry stops after one step", "tags": ["tricky"]},
        {"input": {"digits": [1, 0, 0, 0]}, "expected": [1, 0, 0, 1],
         "description": "Trailing zeros — increment the last one", "tags": ["edge"]},
        {"input": {"digits": [8, 9, 9, 9]}, "expected": [9, 0, 0, 0],
         "description": "Long carry chain that resolves at the leading digit", "tags": ["tricky"]},
        {"input": {"digits": [1, 2, 3, 4, 5, 6, 7, 8, 9]}, "expected": [1, 2, 3, 4, 5, 6, 7, 8, 10][:-1] + [1, 2, 3, 4, 5, 6, 7, 9, 0][-2:],
         "description": "placeholder — overwritten below", "tags": ["skip"]},
        {"input": {"digits": [9] * 100}, "expected": [1] + [0] * 100,
         "description": "Large all-nines (length 100) — full carry chain, grows to length 101", "tags": ["large"]},
        {"input": {"digits": [1] + [0] * 99}, "expected": [1] + [0] * 98 + [1],
         "description": "Large 10^99 — increment last digit only", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Walk Right-to-Left with Carry (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Iterate `i` from `n-1` down to `0`. If `digits[i] < 9`, increment it and return — no further "
                "carry possible. Otherwise set `digits[i] = 0` and continue. If the loop finishes without "
                "early-returning, every digit was 9; prepend a `1` and return. In-place except for the rare "
                "all-9s case which allocates one new array of length n+1."
            ),
            "code": {
                "python": (
                    "def plus_one(digits):\n"
                    "    for i in range(len(digits) - 1, -1, -1):\n"
                    "        if digits[i] < 9:\n"
                    "            digits[i] += 1\n"
                    "            return digits\n"
                    "        digits[i] = 0\n"
                    "    return [1] + digits"
                ),
                "javascript": (
                    "function plusOne(digits) {\n"
                    "    for (let i = digits.length - 1; i >= 0; i--) {\n"
                    "        if (digits[i] < 9) {\n"
                    "            digits[i] += 1;\n"
                    "            return digits;\n"
                    "        }\n"
                    "        digits[i] = 0;\n"
                    "    }\n"
                    "    return [1, ...digits];\n"
                    "}"
                ),
                "java": (
                    "public int[] plusOne(int[] digits) {\n"
                    "    for (int i = digits.length - 1; i >= 0; i--) {\n"
                    "        if (digits[i] < 9) {\n"
                    "            digits[i] += 1;\n"
                    "            return digits;\n"
                    "        }\n"
                    "        digits[i] = 0;\n"
                    "    }\n"
                    "    int[] out = new int[digits.length + 1];\n"
                    "    out[0] = 1;\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Explicit Carry Variable",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Keep a `carry` initialised to 1 (the +1 we owe). Walk right-to-left, summing `digits[i] + carry`, "
                "writing the units digit back and updating `carry = sum / 10`. If `carry` survives the loop, "
                "prepend it. Equivalent to the early-return version; useful framing because it generalises to "
                "'add two big-integer arrays'."
            ),
            "code": {
                "python": (
                    "def plus_one(digits):\n"
                    "    carry = 1\n"
                    "    for i in range(len(digits) - 1, -1, -1):\n"
                    "        s = digits[i] + carry\n"
                    "        digits[i] = s % 10\n"
                    "        carry = s // 10\n"
                    "        if carry == 0:\n"
                    "            return digits\n"
                    "    return [1] + digits if carry else digits"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate the problem: the array is a big integer, you can't (and shouldn't) parse it to a native int. You must do the addition by hand.",
        "2. Adding 1 only ever affects the trailing run of 9s plus one digit to their left. So walk right-to-left.",
        "3. The first non-9 you hit absorbs the carry: increment it and you're done. Everything to its right was already zeroed.",
        "4. If you never hit a non-9, the input was all 9s. The answer is `[1, 0, 0, ..., 0]` — one digit longer than the input.",
        "5. Edge cases: `[0]` → `[1]` (handled by the first branch on the first iteration). `[9]` → `[1, 0]` (handled by the all-9s tail).",
        "6. Complexity: O(n) time worst case (all 9s), O(1) extra space in-place — except all-9s which costs O(n) for the new array (unavoidable since the output is longer).",
    ],
    "tips": [
        "Don't convert to int. Even if the language supports arbitrary-precision integers (Python, JS BigInt), the interviewer wants to see carry handling.",
        "The early-return form (`if digits[i] < 9: digits[i] += 1; return`) is cleaner than the explicit-carry form for *this* problem. Save the carry-variable pattern for 'Add Two Numbers' or 'Add Strings' where the carry can be more than 1.",
        "Mutating the input is fine and standard for LeetCode 66. Mention it aloud — some shops prefer pure functions.",
        "All-9s is the only case that grows the array. State this invariant: 'the output length is `n` or `n+1`, and it's `n+1` iff every input digit was 9'.",
        "Generalisation: for 'Plus K' (add an arbitrary K), use the explicit-carry form and seed `carry = K`. Same loop, same complexity.",
    ],
    "companies": ["Google", "Amazon", "Microsoft", "Apple", "Bloomberg"],
    "topics": ["Array", "Math"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


# Drop the placeholder test case I left in the list above.
PAYLOAD["test_cases"] = [tc for tc in PAYLOAD["test_cases"] if "skip" not in tc.get("tags", [])]


def REFERENCE(digits):
    digits = list(digits)
    for i in range(len(digits) - 1, -1, -1):
        if digits[i] < 9:
            digits[i] += 1
            return digits
        digits[i] = 0
    return [1] + digits


register(PAYLOAD, REFERENCE)
