"""Evaluate Reverse Polish Notation — Medium. Stack.

Postfix expression evaluation with a stack. The classic 'why stacks
exist' problem: each operand pushes, each operator pops two, applies,
and pushes the result. The only real trap is C-style truncation
toward zero for division — Python's `//` is floor division, which
rounds the wrong way for negative quotients. Use `int(a / b)` instead.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Evaluate Reverse Polish Notation",
    "difficulty": "Medium",
    "description": (
        "You are given an array of strings `tokens` that represents an arithmetic expression in "
        "[Reverse Polish Notation](https://en.wikipedia.org/wiki/Reverse_Polish_notation) (postfix).\n\n"
        "Evaluate the expression and return an integer representing its value.\n\n"
        "**Operators**: `+`, `-`, `*`, `/`. Each operand may be an integer or another expression. "
        "Division between two integers always **truncates toward zero** (i.e. drops the fractional "
        "part — note this differs from Python's `//` for negatives).\n\n"
        "It is guaranteed that the given RPN expression is always valid; the answer and all "
        "intermediate calculations fit in a 32-bit signed integer.\n\n"
        "**Example 1:**\n"
        "- Input: `tokens = [\"2\",\"1\",\"+\",\"3\",\"*\"]`\n"
        "- Output: `9`\n"
        "- Explanation: `((2 + 1) * 3) = 9`.\n\n"
        "**Example 2:**\n"
        "- Input: `tokens = [\"10\",\"6\",\"9\",\"3\",\"+\",\"-11\",\"*\",\"/\",\"*\",\"17\",\"+\",\"5\",\"+\"]`\n"
        "- Output: `22`\n"
        "- Explanation: `((10 * (6 / ((9 + 3) * -11))) + 17) + 5 = 22`."
    ),
    "hints": [
        "Use a stack of integers. Walk left-to-right through the tokens.",
        "If the token is a number, push it. If it's an operator, pop the top two values — the *second* pop is the left operand — apply, and push the result.",
        "Division must truncate toward zero, not floor. In Python, `int(a / b)` gives truncation; `a // b` gives floor (wrong for negative quotients like `-7 / 2`).",
        "Negative numbers appear as tokens (e.g. `\"-11\"`). A simple `t in {'+','-','*','/'}` check distinguishes operators from numeric tokens — don't rely on `isdigit()` which rejects the leading minus.",
        "After processing all tokens, exactly one value remains on the stack — return it.",
    ],
    "constraints": [
        "1 <= tokens.length <= 10⁴",
        "Each token is either an operator in `{'+', '-', '*', '/'}` or an integer in the range `[-200, 200]`.",
        "The expression is always a valid RPN expression and intermediate results fit in a 32-bit signed integer.",
    ],
    "starter_code": {
        "python": "def eval_rpn(tokens):\n    # Your code here\n    pass",
        "javascript": "function evalRPN(tokens) {\n    // Your code here\n}",
        "java": "public int evalRPN(String[] tokens) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [\"2\",\"1\",\"+\",\"3\",\"*\"],\n"
            "        [\"4\",\"13\",\"5\",\"/\",\"+\"],\n"
            "        [\"10\",\"6\",\"9\",\"3\",\"+\",\"-11\",\"*\",\"/\",\"*\",\"17\",\"+\",\"5\",\"+\"],\n"
            "    ]\n"
            "    for tokens in cases:\n"
            "        print(f\"eval_rpn({tokens}) = {eval_rpn(tokens)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\n"
            "    [\"2\",\"1\",\"+\",\"3\",\"*\"],\n"
            "    [\"4\",\"13\",\"5\",\"/\",\"+\"],\n"
            "].forEach(tokens =>\n"
            "    console.log(`evalRPN =`, evalRPN(tokens))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.evalRPN(new String[]{\"2\",\"1\",\"+\",\"3\",\"*\"}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"tokens": ["2", "1", "+"]}, "expected": 3,
         "description": "Simplest two-operand addition", "tags": ["basic"]},
        {"input": {"tokens": ["2", "1", "+", "3", "*"]}, "expected": 9,
         "description": "(2 + 1) * 3 — example 1", "tags": ["basic"]},
        {"input": {"tokens": ["4", "13", "5", "/", "+"]}, "expected": 6,
         "description": "4 + (13 / 5) = 4 + 2 = 6", "tags": ["basic"]},
        {"input": {"tokens": ["10", "6", "9", "3", "+", "-11", "*", "/", "*", "17", "+", "5", "+"]},
         "expected": 22,
         "description": "Full LeetCode example with negative token and nested division",
         "tags": ["complex"]},
        {"input": {"tokens": ["42"]}, "expected": 42,
         "description": "Single number — no operators applied", "tags": ["edge"]},
        {"input": {"tokens": ["-5"]}, "expected": -5,
         "description": "Single negative number", "tags": ["edge"]},
        {"input": {"tokens": ["3", "5", "-"]}, "expected": -2,
         "description": "Subtraction yielding negative result (3 - 5)", "tags": ["edge"]},
        {"input": {"tokens": ["7", "-3", "/"]}, "expected": -2,
         "description": "Division truncates toward zero — 7 / -3 = -2 (NOT -3 from floor)",
         "tags": ["tricky"]},
        {"input": {"tokens": ["-7", "3", "/"]}, "expected": -2,
         "description": "Truncation again — -7 / 3 = -2 (floor would give -3)", "tags": ["tricky"]},
        {"input": {"tokens": ["5", "5", "-"]}, "expected": 0,
         "description": "Zero result from subtraction", "tags": ["edge"]},
        {"input": {"tokens": ["2", "3", "*", "4", "5", "*", "+"]}, "expected": 26,
         "description": "Mixed operators — (2*3) + (4*5) = 6 + 20", "tags": ["basic"]},
        {"input": {"tokens": ["1", "2", "+", "3", "+", "4", "+", "5", "+"]}, "expected": 15,
         "description": "Deeply nested left-associative addition", "tags": ["tricky"]},
        {"input": {"tokens": ["100", "200", "+", "2", "/", "5", "*", "7", "+"]}, "expected": 757,
         "description": "Mixed operators with division — ((100+200)/2)*5 + 7", "tags": ["complex"]},
    ],
    "solutions": [
        {
            "title": "Stack-Based (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk the tokens once. Numbers go onto a stack; operators pop two values (right "
                "operand first, then left), apply the op, and push the result. After the walk the "
                "stack holds exactly one value. Use `int(a / b)` for division to truncate toward zero."
            ),
            "code": {
                "python": (
                    "def eval_rpn(tokens):\n"
                    "    stack = []\n"
                    "    ops = {'+', '-', '*', '/'}\n"
                    "    for t in tokens:\n"
                    "        if t in ops:\n"
                    "            b = stack.pop()\n"
                    "            a = stack.pop()\n"
                    "            if t == '+':\n"
                    "                stack.append(a + b)\n"
                    "            elif t == '-':\n"
                    "                stack.append(a - b)\n"
                    "            elif t == '*':\n"
                    "                stack.append(a * b)\n"
                    "            else:\n"
                    "                stack.append(int(a / b))  # truncate toward zero\n"
                    "        else:\n"
                    "            stack.append(int(t))\n"
                    "    return stack[0]"
                ),
                "javascript": (
                    "function evalRPN(tokens) {\n"
                    "    const stack = [];\n"
                    "    const ops = new Set(['+', '-', '*', '/']);\n"
                    "    for (const t of tokens) {\n"
                    "        if (ops.has(t)) {\n"
                    "            const b = stack.pop();\n"
                    "            const a = stack.pop();\n"
                    "            let r;\n"
                    "            if (t === '+') r = a + b;\n"
                    "            else if (t === '-') r = a - b;\n"
                    "            else if (t === '*') r = a * b;\n"
                    "            else r = Math.trunc(a / b);  // truncate toward zero\n"
                    "            stack.push(r);\n"
                    "        } else {\n"
                    "            stack.push(parseInt(t, 10));\n"
                    "        }\n"
                    "    }\n"
                    "    return stack[0];\n"
                    "}"
                ),
                "java": (
                    "public int evalRPN(String[] tokens) {\n"
                    "    Deque<Integer> stack = new ArrayDeque<>();\n"
                    "    for (String t : tokens) {\n"
                    "        switch (t) {\n"
                    "            case \"+\": case \"-\": case \"*\": case \"/\": {\n"
                    "                int b = stack.pop();\n"
                    "                int a = stack.pop();\n"
                    "                int r = 0;\n"
                    "                if (t.equals(\"+\")) r = a + b;\n"
                    "                else if (t.equals(\"-\")) r = a - b;\n"
                    "                else if (t.equals(\"*\")) r = a * b;\n"
                    "                else r = a / b;  // Java int division truncates toward zero\n"
                    "                stack.push(r);\n"
                    "                break;\n"
                    "            }\n"
                    "            default:\n"
                    "                stack.push(Integer.parseInt(t));\n"
                    "        }\n"
                    "    }\n"
                    "    return stack.pop();\n"
                    "}"
                ),
            },
        },
        {
            "title": "In-Place Using the Tokens Array as Stack",
            "time_complexity": "O(n)",
            "space_complexity": "O(1) extra",
            "description": (
                "Reuse the input list as the stack via a write index. As we scan, integers and "
                "operator results are written back into the array's prefix; on an operator we read "
                "the two slots below the write head and overwrite. Saves the auxiliary stack at the "
                "cost of mutating the input — mention the trade-off in an interview."
            ),
            "code": {
                "python": (
                    "def eval_rpn(tokens):\n"
                    "    ops = {'+', '-', '*', '/'}\n"
                    "    top = 0  # next free slot — also stack size\n"
                    "    buf = [0] * len(tokens)\n"
                    "    for t in tokens:\n"
                    "        if t in ops:\n"
                    "            b = buf[top - 1]\n"
                    "            a = buf[top - 2]\n"
                    "            top -= 2\n"
                    "            if t == '+':\n"
                    "                buf[top] = a + b\n"
                    "            elif t == '-':\n"
                    "                buf[top] = a - b\n"
                    "            elif t == '*':\n"
                    "                buf[top] = a * b\n"
                    "            else:\n"
                    "                buf[top] = int(a / b)\n"
                    "            top += 1\n"
                    "        else:\n"
                    "            buf[top] = int(t)\n"
                    "            top += 1\n"
                    "    return buf[0]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the structure: postfix means operators come *after* their operands → screams 'stack'.",
        "2. Push numbers; on each operator pop two and push the result. Order matters — the *second* pop is the left operand.",
        "3. Distinguish operators from numbers carefully. Negative tokens like `-11` mean `isdigit()` is wrong; use a set membership check on the operator symbols instead.",
        "4. Division: the spec says truncate toward zero. Python's `//` floors (rounds toward -∞), so `-7 // 2 == -4`, but the problem wants `-3`. Use `int(a / b)` for the right semantics. Java/JS integer division already truncates.",
        "5. Validity is guaranteed, so no need to check stack size before popping or for division by zero. State this assumption explicitly in interview.",
        "6. Final answer is the single remaining stack element.",
    ],
    "tips": [
        "The single biggest gotcha is `//` vs truncation. Memorise: `-7 // 2 == -4` (floor) but the answer expected is `-3` (truncate). Always reach for `int(a / b)` in Python for this problem.",
        "Pop order: right operand first. Easy to flip and pass `+`/`*` cases (commutative) while silently failing on `-` and `/`.",
        "Don't use `t.lstrip('-').isdigit()` and similar gymnastics — a 4-element set of operator symbols is clearer.",
        "Follow-up — generalize: support more operators (`%`, `**`) by mapping symbol → callable. `ops = {'+': operator.add, ...}` collapses the if-chain.",
        "Follow-up — convert *infix* to RPN: that's the **Shunting-Yard** algorithm. Worth knowing as the sister problem.",
        "If asked about overflow: the constraint guarantees 32-bit safety, but in Java explicitly use `int`/`long` based on the stated bound.",
    ],
    "companies": ["Amazon", "LinkedIn", "Microsoft", "Bloomberg", "Two Sigma"],
    "topics": ["Stack", "Array", "Math"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(tokens):
    stack = []
    ops = {'+', '-', '*', '/'}
    for t in tokens:
        if t in ops:
            b = stack.pop()
            a = stack.pop()
            if t == '+':
                stack.append(a + b)
            elif t == '-':
                stack.append(a - b)
            elif t == '*':
                stack.append(a * b)
            else:
                # Truncate toward zero — NOT floor division
                stack.append(int(a / b))
        else:
            stack.append(int(t))
    return stack[0]


register(PAYLOAD, REFERENCE)
