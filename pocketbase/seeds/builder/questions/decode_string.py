"""Decode String — Medium. Stack / Recursion / Parsing.

The canonical 'nested bracket expansion' problem. Two clean
solutions: an iterative stack that pushes (count, prevString) on
'[' and pops on ']', and a recursive descent parser that walks the
string with an index pointer. Both are O(n) in the *output* size;
neither has a way around producing the expanded string.

Watch-outs candidates miss: multi-digit counts (parse the whole
integer, not a single char), and the fact that the count applies
to whatever is *inside* the brackets — including nested expansions
that have already been built.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Decode String",
    "difficulty": "Medium",
    "description": (
        "Given an encoded string, return its decoded form.\n\n"
        "The encoding rule is `k[encoded_string]`, where the `encoded_string` inside the square brackets "
        "is repeated exactly `k` times. `k` is guaranteed to be a positive integer.\n\n"
        "You may assume the input is always valid: no extra white spaces, well-formed brackets, and digits "
        "appear only as repeat counts (never inside the encoded string itself). The original data does not "
        "contain digits — digits exist only as repeat counts.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"3[a]2[bc]\"`\n"
        "- Output: `\"aaabcbc\"`\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"3[a2[c]]\"`\n"
        "- Output: `\"accaccacc\"`\n"
        "- Explanation: the inner `2[c]` expands to `\"cc\"`, giving `\"acc\"`, then the outer `3[...]` repeats it.\n\n"
        "**Example 3:**\n"
        "- Input: `s = \"2[abc]3[cd]ef\"`\n"
        "- Output: `\"abcabccdcdcdef\"`"
    ),
    "hints": [
        "Think 'parentheses with a multiplier'. Whenever you see `[`, you're entering a new scope; whenever "
        "you see `]`, you finish a scope and multiply.",
        "Stack approach: keep two stacks (or one stack of pairs). On `[`, push the current `(count, "
        "current_string)` and reset both. On `]`, pop `(prev_count, prev_string)` and set `current = "
        "prev_string + current * prev_count`.",
        "Multi-digit counts: when you see a digit, keep reading until the next non-digit — `100[leetcode]` "
        "needs the integer `100`, not just `1`.",
        "Recursive alternative: write `decode(i)` that consumes characters starting at index `i` and returns "
        "`(decoded_chunk, next_index)`. Recurse on `[`, return on `]` or end-of-string. Use a mutable index "
        "(list/object/nonlocal) to share progress across calls.",
        "Both approaches are O(n) in the *output* length, not the input length — the output can be ~10⁵× "
        "larger than the input (e.g. `100[leetcode]`). Use a list/StringBuilder, not repeated `+=`.",
    ],
    "constraints": [
        "1 <= s.length <= 30",
        "`s` consists of lowercase English letters, digits, and square brackets `[]`",
        "`s` is guaranteed to be a valid input; all integers `k` satisfy `1 <= k <= 300`",
    ],
    "starter_code": {
        "python": "def decode_string(s):\n    # Your code here\n    pass",
        "javascript": "function decodeString(s) {\n    // Your code here\n}",
        "java": "public String decodeString(String s) {\n    // Your code here\n    return \"\";\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\"3[a]2[bc]\", \"3[a2[c]]\", \"2[abc]3[cd]ef\", \"abcd\"]\n"
            "    for s in cases:\n"
            "        print(f\"decode_string({s!r}) = {decode_string(s)!r}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\"3[a]2[bc]\", \"3[a2[c]]\", \"2[abc]3[cd]ef\", \"abcd\"].forEach(s =>\n"
            "    console.log(`decodeString(${JSON.stringify(s)}) =`, decodeString(s))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.decodeString(\"3[a]2[bc]\"));\n"
            "        System.out.println(s.decodeString(\"3[a2[c]]\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "3[a]2[bc]"}, "expected": "aaabcbc",
         "description": "Classic two-segment example", "tags": ["basic"]},
        {"input": {"s": "3[a2[c]]"}, "expected": "accaccacc",
         "description": "Nested — inner `2[c]` expands first, then outer `3[...]`", "tags": ["basic"]},
        {"input": {"s": "2[abc]3[cd]ef"}, "expected": "abcabccdcdcdef",
         "description": "LeetCode example — trailing literal `ef` after the brackets", "tags": ["basic"]},
        {"input": {"s": "abcd"}, "expected": "abcd",
         "description": "No brackets — input passes through unchanged", "tags": ["edge"]},
        {"input": {"s": "1[a]"}, "expected": "a",
         "description": "Count of 1 — bracket is a no-op", "tags": ["edge"]},
        {"input": {"s": "100[leetcode]"}, "expected": "leetcode" * 100,
         "description": "Multi-digit count — must parse `100` as one integer", "tags": ["tricky"]},
        {"input": {"s": "3[ab]4[cd]"}, "expected": "abababcdcdcdcd",
         "description": "Two consecutive bracket groups, no literal between them", "tags": ["basic"]},
        {"input": {"s": "2[2[2[a]]]"}, "expected": "a" * 8,
         "description": "Triple-nested — 2*2*2 = 8 copies of `a`", "tags": ["tricky"]},
        {"input": {"s": "10[a]"}, "expected": "a" * 10,
         "description": "Two-digit count edge case", "tags": ["edge"]},
        {"input": {"s": "3[a]2[b4[F]c]"}, "expected": "aaabFFFFcbFFFFc",
         "description": "Mixed nesting with literals on both sides of the inner bracket", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Stack-Based Iterative",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk the string once. Maintain a stack of `(count, prev_string)` frames plus a 'current "
                "string being built' and a 'current count being parsed'. On a digit, accumulate into the "
                "count. On `[`, push the frame and reset. On `]`, pop and set `current = prev_string + "
                "current * prev_count`. On a letter, append to current. Note: complexity is O(total output "
                "length); the input bound n=30 is misleading because the output can blow up via large counts."
            ),
            "code": {
                "python": (
                    "def decode_string(s):\n"
                    "    stack = []\n"
                    "    current = []\n"
                    "    count = 0\n"
                    "    for ch in s:\n"
                    "        if ch.isdigit():\n"
                    "            count = count * 10 + int(ch)\n"
                    "        elif ch == '[':\n"
                    "            stack.append((count, current))\n"
                    "            current = []\n"
                    "            count = 0\n"
                    "        elif ch == ']':\n"
                    "            prev_count, prev = stack.pop()\n"
                    "            prev.extend(current * prev_count)\n"
                    "            current = prev\n"
                    "        else:\n"
                    "            current.append(ch)\n"
                    "    return ''.join(current)"
                ),
                "javascript": (
                    "function decodeString(s) {\n"
                    "    const stack = [];\n"
                    "    let current = '';\n"
                    "    let count = 0;\n"
                    "    for (const ch of s) {\n"
                    "        if (ch >= '0' && ch <= '9') {\n"
                    "            count = count * 10 + (ch.charCodeAt(0) - 48);\n"
                    "        } else if (ch === '[') {\n"
                    "            stack.push([count, current]);\n"
                    "            current = '';\n"
                    "            count = 0;\n"
                    "        } else if (ch === ']') {\n"
                    "            const [prevCount, prev] = stack.pop();\n"
                    "            current = prev + current.repeat(prevCount);\n"
                    "        } else {\n"
                    "            current += ch;\n"
                    "        }\n"
                    "    }\n"
                    "    return current;\n"
                    "}"
                ),
                "java": (
                    "public String decodeString(String s) {\n"
                    "    Deque<Integer> countStack = new ArrayDeque<>();\n"
                    "    Deque<StringBuilder> strStack = new ArrayDeque<>();\n"
                    "    StringBuilder current = new StringBuilder();\n"
                    "    int count = 0;\n"
                    "    for (char ch : s.toCharArray()) {\n"
                    "        if (Character.isDigit(ch)) {\n"
                    "            count = count * 10 + (ch - '0');\n"
                    "        } else if (ch == '[') {\n"
                    "            countStack.push(count);\n"
                    "            strStack.push(current);\n"
                    "            current = new StringBuilder();\n"
                    "            count = 0;\n"
                    "        } else if (ch == ']') {\n"
                    "            int k = countStack.pop();\n"
                    "            StringBuilder prev = strStack.pop();\n"
                    "            for (int i = 0; i < k; i++) prev.append(current);\n"
                    "            current = prev;\n"
                    "        } else {\n"
                    "            current.append(ch);\n"
                    "        }\n"
                    "    }\n"
                    "    return current.toString();\n"
                    "}"
                ),
            },
        },
        {
            "title": "Recursive Parser with Index Pointer",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Treat the grammar directly: each call to `decode` consumes characters until it hits `]` "
                "(end of its scope) or end-of-string. On a digit, read the full integer; then expect `[`, "
                "recurse, expect `]`, and repeat the recursed result `count` times. Use a shared index "
                "(list cell or class field) so the caller knows where to resume."
            ),
            "code": {
                "python": (
                    "def decode_string(s):\n"
                    "    i = [0]\n"
                    "    def parse():\n"
                    "        out = []\n"
                    "        while i[0] < len(s) and s[i[0]] != ']':\n"
                    "            if s[i[0]].isdigit():\n"
                    "                k = 0\n"
                    "                while s[i[0]].isdigit():\n"
                    "                    k = k * 10 + int(s[i[0]])\n"
                    "                    i[0] += 1\n"
                    "                i[0] += 1  # skip '['\n"
                    "                inner = parse()\n"
                    "                i[0] += 1  # skip ']'\n"
                    "                out.append(inner * k)\n"
                    "            else:\n"
                    "                out.append(s[i[0]])\n"
                    "                i[0] += 1\n"
                    "        return ''.join(out)\n"
                    "    return parse()"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the grammar: `S := (letter | k[S])*`. Two natural implementations — explicit stack or recursion.",
        "2. State to track per scope: the count prefix and the string built so far inside the current bracket.",
        "3. Stack approach: on `[`, snapshot `(count, current)` and reset; on `]`, pop and multiply.",
        "4. Watch out for multi-digit counts — accumulate `count = count * 10 + digit` until the next non-digit.",
        "5. Don't materialise via `current += ch` in a tight loop in Python — append to a list and `''.join` at the end. In Java, use `StringBuilder`.",
        "6. Recursive variant reads better but needs a mutable index across calls (Python: `[i]`; Java: a class field; JS: closure variable).",
        "7. Walk through `3[a2[c]]` on paper: stack accumulates `(3, '')`, then `(2, 'a')`, pops back to `'acc'`, then to `'accaccacc'`.",
    ],
    "tips": [
        "Multi-digit counts are the most common bug. `100[a]` must produce 100 copies, not 1 followed by `00[a]` chaos.",
        "If you write the recursive version, decide upfront how the index is shared. A list cell `i = [0]` in Python is the cleanest hack; in Java/JS use a class member or closure.",
        "Avoid `O(n²)` string concatenation. Use a list/StringBuilder and join once per scope close.",
        "Edge case: input with no brackets at all — your code should pass it through unchanged.",
        "Edge case: count of 1 (`1[a]`) is legal — no special handling needed if your code is generic.",
        "Follow-up — 'Number of Atoms' (LC 726): same pattern but counts apply to chemical formulas. Same stack template, different alphabet.",
        "Follow-up — 'Basic Calculator' (LC 224/227): same nested-scope-with-stack idea, but `(` `)` instead of `[` `]` and arithmetic instead of repetition.",
    ],
    "companies": ["Google", "Amazon", "Facebook", "Microsoft", "Bloomberg", "Apple"],
    "topics": ["String", "Stack", "Recursion"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(s):
    stack = []
    current = []
    count = 0
    for ch in s:
        if ch.isdigit():
            count = count * 10 + int(ch)
        elif ch == '[':
            stack.append((count, current))
            current = []
            count = 0
        elif ch == ']':
            prev_count, prev = stack.pop()
            prev.extend(current * prev_count)
            current = prev
        else:
            current.append(ch)
    return ''.join(current)


register(PAYLOAD, REFERENCE)
