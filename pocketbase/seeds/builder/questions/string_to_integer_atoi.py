"""String to Integer (atoi) — Medium. String / State Machine.

The classic 'parse one int from a messy string' question. Looks easy
until you list all the corner cases: leading whitespace, optional sign,
non-digit terminators, 32-bit overflow clamping, empty/sign-only input.
The cleanest framing is a deterministic finite automaton with four
states (start, signed, in_number, end) — once you draw the table the
code writes itself.
"""
from builder.registry import register


INT_MAX = 2**31 - 1   # 2147483647
INT_MIN = -(2**31)    # -2147483648


PAYLOAD = {
    "title": "String to Integer (atoi)",
    "difficulty": "Medium",
    "description": (
        "Implement the `myAtoi(s)` function, which converts a string to a 32-bit signed integer.\n\n"
        "The algorithm is:\n"
        "1. **Skip** any leading whitespace.\n"
        "2. Read an optional `+` or `-` sign. If neither is present, assume positive.\n"
        "3. Read in the next characters until a non-digit character is encountered or the end of the "
        "string is reached. The rest of the string is ignored.\n"
        "4. Convert the digits read into an integer. If no digits were read, the result is `0`.\n"
        "5. **Clamp** the result to the 32-bit signed integer range `[-2³¹, 2³¹ - 1]`. Values less "
        "than `-2147483648` become `-2147483648`; values greater than `2147483647` become `2147483647`.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"42\"`\n"
        "- Output: `42`\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"   -42\"`\n"
        "- Output: `-42`\n"
        "- Explanation: Leading whitespace is skipped, then `-` sets the sign.\n\n"
        "**Example 3:**\n"
        "- Input: `s = \"4193 with words\"`\n"
        "- Output: `4193`\n"
        "- Explanation: Reading stops at the space because it is not a digit."
    ),
    "hints": [
        "Think of it as a small state machine: `start` → `signed` → `in_number` → `end`. Each character "
        "either advances the state or terminates parsing.",
        "From `start`: whitespace stays in `start`; `+`/`-` moves to `signed`; a digit moves to "
        "`in_number`; anything else moves straight to `end` (return 0).",
        "Once in `in_number`, multiply running result by 10 and add the digit. As soon as you see a "
        "non-digit, stop — the rest of the string is irrelevant.",
        "Clamp on every digit, not just at the end. Before doing `result = result*10 + d`, check whether "
        "the new value would exceed `INT_MAX` (or fall below `INT_MIN`); if so, return the clamped bound.",
        "Edge cases that bite: empty string, only whitespace, only a sign (`\"+\"` or `\"-\"`), sign "
        "followed by non-digit, leading zeros, and overflow with the sign already applied.",
    ],
    "constraints": [
        "0 <= s.length <= 200",
        "s consists of English letters (lower-case and upper-case), digits (0-9), ' ', '+', '-', and '.'.",
        "Result must fit in a 32-bit signed integer; clamp otherwise.",
    ],
    "starter_code": {
        "python": "def my_atoi(s):\n    # Your code here\n    pass",
        "javascript": "function myAtoi(s) {\n    // Your code here\n}",
        "java": "public int myAtoi(String s) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\"42\", \"   -42\", \"4193 with words\", \"words and 987\", \"-91283472332\"]\n"
            "    for s in cases:\n"
            "        print(f\"my_atoi({s!r}) = {my_atoi(s)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\"42\", \"   -42\", \"4193 with words\", \"words and 987\"].forEach(s =>\n"
            "    console.log(`myAtoi(${JSON.stringify(s)}) =`, myAtoi(s))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.myAtoi(\"   -42\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "42"}, "expected": 42,
         "description": "Classic — pure digits", "tags": ["basic"]},
        {"input": {"s": "   -42"}, "expected": -42,
         "description": "LeetCode example 2 — leading whitespace + negative sign", "tags": ["basic"]},
        {"input": {"s": "4193 with words"}, "expected": 4193,
         "description": "LeetCode example 3 — digits then non-digit terminator", "tags": ["basic"]},
        {"input": {"s": "words and 987"}, "expected": 0,
         "description": "LeetCode example — first non-whitespace is a letter, return 0", "tags": ["basic"]},
        {"input": {"s": "91283472332"}, "expected": 2147483647,
         "description": "Positive overflow — clamp to INT_MAX", "tags": ["overflow"]},
        {"input": {"s": "-91283472332"}, "expected": -2147483648,
         "description": "Negative overflow — clamp to INT_MIN", "tags": ["overflow"]},
        {"input": {"s": ""}, "expected": 0,
         "description": "Empty string", "tags": ["edge"]},
        {"input": {"s": "+"}, "expected": 0,
         "description": "Only a sign — no digits follow, return 0", "tags": ["edge"]},
        {"input": {"s": "      "}, "expected": 0,
         "description": "Only whitespace", "tags": ["edge"]},
        {"input": {"s": "+0 123"}, "expected": 0,
         "description": "Sign with leading zero, then space — stop at the space", "tags": ["tricky"]},
        {"input": {"s": "  +2147483648"}, "expected": 2147483647,
         "description": "Exactly one over INT_MAX with explicit sign — clamp", "tags": ["overflow"]},
        {"input": {"s": "+-12"}, "expected": 0,
         "description": "Two signs in a row — second is not a digit, return 0", "tags": ["tricky"]},
        {"input": {"s": "  0000000000012345678"}, "expected": 12345678,
         "description": "Many leading zeros — strip and parse", "tags": ["tricky"]},
        {"input": {"s": "-2147483648"}, "expected": -2147483648,
         "description": "Exactly INT_MIN — fits, no clamp", "tags": ["edge"]},
        {"input": {"s": "2147483647"}, "expected": 2147483647,
         "description": "Exactly INT_MAX — fits, no clamp", "tags": ["edge"]},
        {"input": {"s": "3.14159"}, "expected": 3,
         "description": "Decimal point is a non-digit terminator", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Deterministic Finite Automaton (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Model the parse as a state machine with four states: `start` (skipping whitespace), "
                "`signed` (sign just consumed), `in_number` (accumulating digits), and `end` (done). "
                "For each character, look up the next state. Clamp after every digit so we never grow "
                "beyond 32-bit bounds."
            ),
            "code": {
                "python": (
                    "INT_MAX = 2**31 - 1\n"
                    "INT_MIN = -(2**31)\n"
                    "\n"
                    "def my_atoi(s):\n"
                    "    state = 'start'\n"
                    "    sign = 1\n"
                    "    result = 0\n"
                    "    for ch in s:\n"
                    "        if state == 'start':\n"
                    "            if ch == ' ':\n"
                    "                continue\n"
                    "            if ch == '+' or ch == '-':\n"
                    "                sign = -1 if ch == '-' else 1\n"
                    "                state = 'signed'\n"
                    "            elif ch.isdigit():\n"
                    "                result = int(ch)\n"
                    "                state = 'in_number'\n"
                    "            else:\n"
                    "                return 0\n"
                    "        elif state == 'signed':\n"
                    "            if ch.isdigit():\n"
                    "                result = int(ch)\n"
                    "                state = 'in_number'\n"
                    "            else:\n"
                    "                return 0\n"
                    "        elif state == 'in_number':\n"
                    "            if ch.isdigit():\n"
                    "                result = result * 10 + int(ch)\n"
                    "                # clamp\n"
                    "                if sign == 1 and result > INT_MAX:\n"
                    "                    return INT_MAX\n"
                    "                if sign == -1 and result > -INT_MIN:\n"
                    "                    return INT_MIN\n"
                    "            else:\n"
                    "                break\n"
                    "    return sign * result"
                ),
                "javascript": (
                    "const INT_MAX = 2 ** 31 - 1;\n"
                    "const INT_MIN = -(2 ** 31);\n"
                    "\n"
                    "function myAtoi(s) {\n"
                    "    let state = 'start', sign = 1, result = 0;\n"
                    "    for (const ch of s) {\n"
                    "        if (state === 'start') {\n"
                    "            if (ch === ' ') continue;\n"
                    "            if (ch === '+' || ch === '-') { sign = ch === '-' ? -1 : 1; state = 'signed'; }\n"
                    "            else if (ch >= '0' && ch <= '9') { result = +ch; state = 'in_number'; }\n"
                    "            else return 0;\n"
                    "        } else if (state === 'signed') {\n"
                    "            if (ch >= '0' && ch <= '9') { result = +ch; state = 'in_number'; }\n"
                    "            else return 0;\n"
                    "        } else {\n"
                    "            if (ch >= '0' && ch <= '9') {\n"
                    "                result = result * 10 + Number(ch);\n"
                    "                if (sign === 1 && result > INT_MAX) return INT_MAX;\n"
                    "                if (sign === -1 && result > -INT_MIN) return INT_MIN;\n"
                    "            } else break;\n"
                    "        }\n"
                    "    }\n"
                    "    return sign * result;\n"
                    "}"
                ),
                "java": (
                    "public int myAtoi(String s) {\n"
                    "    final int INT_MAX = Integer.MAX_VALUE;\n"
                    "    final int INT_MIN = Integer.MIN_VALUE;\n"
                    "    String state = \"start\";\n"
                    "    int sign = 1;\n"
                    "    long result = 0;\n"
                    "    for (char ch : s.toCharArray()) {\n"
                    "        if (state.equals(\"start\")) {\n"
                    "            if (ch == ' ') continue;\n"
                    "            if (ch == '+' || ch == '-') { sign = ch == '-' ? -1 : 1; state = \"signed\"; }\n"
                    "            else if (Character.isDigit(ch)) { result = ch - '0'; state = \"in_number\"; }\n"
                    "            else return 0;\n"
                    "        } else if (state.equals(\"signed\")) {\n"
                    "            if (Character.isDigit(ch)) { result = ch - '0'; state = \"in_number\"; }\n"
                    "            else return 0;\n"
                    "        } else {\n"
                    "            if (Character.isDigit(ch)) {\n"
                    "                result = result * 10 + (ch - '0');\n"
                    "                if (sign == 1 && result > INT_MAX) return INT_MAX;\n"
                    "                if (sign == -1 && -result < INT_MIN) return INT_MIN;\n"
                    "            } else break;\n"
                    "        }\n"
                    "    }\n"
                    "    return (int) (sign * result);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Char Walk (Index-based)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Equivalent algorithm written as three sequential phases over an explicit index `i`: "
                "(1) skip whitespace, (2) consume optional sign, (3) accumulate digits with overflow "
                "clamp. Reads more like a textbook description than the state machine; some interviewers "
                "prefer it because the phases are visually distinct."
            ),
            "code": {
                "python": (
                    "INT_MAX = 2**31 - 1\n"
                    "INT_MIN = -(2**31)\n"
                    "\n"
                    "def my_atoi(s):\n"
                    "    n = len(s)\n"
                    "    i = 0\n"
                    "    # 1. skip whitespace\n"
                    "    while i < n and s[i] == ' ':\n"
                    "        i += 1\n"
                    "    # 2. optional sign\n"
                    "    sign = 1\n"
                    "    if i < n and (s[i] == '+' or s[i] == '-'):\n"
                    "        sign = -1 if s[i] == '-' else 1\n"
                    "        i += 1\n"
                    "    # 3. digits with clamp\n"
                    "    result = 0\n"
                    "    while i < n and s[i].isdigit():\n"
                    "        result = result * 10 + int(s[i])\n"
                    "        if sign == 1 and result > INT_MAX:\n"
                    "            return INT_MAX\n"
                    "        if sign == -1 and result > -INT_MIN:\n"
                    "            return INT_MIN\n"
                    "        i += 1\n"
                    "    return sign * result"
                ),
                "javascript": (
                    "function myAtoi(s) {\n"
                    "    const INT_MAX = 2 ** 31 - 1, INT_MIN = -(2 ** 31);\n"
                    "    let i = 0, n = s.length;\n"
                    "    while (i < n && s[i] === ' ') i++;\n"
                    "    let sign = 1;\n"
                    "    if (i < n && (s[i] === '+' || s[i] === '-')) {\n"
                    "        sign = s[i] === '-' ? -1 : 1; i++;\n"
                    "    }\n"
                    "    let result = 0;\n"
                    "    while (i < n && s[i] >= '0' && s[i] <= '9') {\n"
                    "        result = result * 10 + Number(s[i]);\n"
                    "        if (sign === 1 && result > INT_MAX) return INT_MAX;\n"
                    "        if (sign === -1 && result > -INT_MIN) return INT_MIN;\n"
                    "        i++;\n"
                    "    }\n"
                    "    return sign * result;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. List the parsing rules out loud: skip whitespace, read optional sign, read digits, stop at "
        "the first non-digit, clamp to 32-bit. Naming the rules first prevents off-by-one mistakes.",
        "2. Decide on a structure: I prefer an explicit state machine (start → signed → in_number → end) "
        "because the transitions are easy to defend in interview.",
        "3. Walk the string once. Any character can only advance the state or terminate parsing.",
        "4. Clamp after every digit, not just at the end. This avoids relying on Python big-int / Java "
        "long tricks and ports cleanly to languages with fixed-width arithmetic.",
        "5. Edge cases — drive them out before coding: empty, only whitespace, only sign, sign+letter, "
        "leading zeros, exactly INT_MAX, exactly INT_MIN, one above each bound.",
        "6. Sanity: `\"+0 123\"` → 0 (the space terminates the digits, leading zeros stripped). "
        "`\"3.14\"` → 3 (the dot is just a non-digit). Verifying these by hand catches off-by-ones.",
    ],
    "tips": [
        "Don't use the language's built-in `int(s)` / `Integer.parseInt(s)` — it throws on the very "
        "inputs the question is testing. Interviewers will fail you on this.",
        "Clamp at every step, not at the end. `result > INT_MAX // 10` is a common pre-check before "
        "multiplying, but `result > INT_MAX` after the multiply works just as well in big-int languages.",
        "For the negative bound, compare against `-INT_MIN` (i.e., 2³¹) on the unsigned magnitude, then "
        "apply the sign at the end. Avoids asymmetric `INT_MIN == -INT_MIN` headaches.",
        "Two signs in a row (`\"+-12\"`, `\"--3\"`) → return 0. The state machine catches this naturally: "
        "after `signed`, the next char must be a digit.",
        "LeetCode used to allow whitespace-separated digits; current spec does not. Re-read the rules: "
        "once you stop reading digits, the rest of the string is ignored — it's never re-entered.",
        "Common follow-up — 'parse a float' or 'parse a signed hex literal'. Same DFA shape, just more "
        "states. Drawing the diagram first scales much better than nested ifs.",
    ],
    "companies": ["Amazon", "Microsoft", "Facebook", "Google", "Bloomberg", "Apple"],
    "topics": ["String", "State Machine"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(s):
    state = 'start'
    sign = 1
    result = 0
    for ch in s:
        if state == 'start':
            if ch == ' ':
                continue
            if ch == '+' or ch == '-':
                sign = -1 if ch == '-' else 1
                state = 'signed'
            elif ch.isdigit():
                result = int(ch)
                state = 'in_number'
            else:
                return 0
        elif state == 'signed':
            if ch.isdigit():
                result = int(ch)
                state = 'in_number'
            else:
                return 0
        elif state == 'in_number':
            if ch.isdigit():
                result = result * 10 + int(ch)
                if sign == 1 and result > INT_MAX:
                    return INT_MAX
                if sign == -1 and result > -INT_MIN:
                    return INT_MIN
            else:
                break
    return int(sign * result)


register(PAYLOAD, REFERENCE)
