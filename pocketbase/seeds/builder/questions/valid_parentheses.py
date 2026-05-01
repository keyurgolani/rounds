"""Valid Parentheses — Easy. Stack / String.

The canonical 'first stack problem'. The trick everyone learns: a stack
turns 'most recent opener' lookups into O(1). Push openers, pop on
closers and verify the match. Two failure modes hide in plain sight —
a closer with no opener, and openers left on the stack at the end —
and both are easy to miss if you only look at the matching step.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Valid Parentheses",
    "difficulty": "Easy",
    "description": (
        "Given a string `s` containing just the characters `'('`, `')'`, `'{'`, `'}'`, `'['` and `']'`, "
        "determine if the input string is valid.\n\n"
        "An input string is valid if:\n"
        "1. Open brackets are closed by the same type of brackets.\n"
        "2. Open brackets are closed in the correct order.\n"
        "3. Every closing bracket has a corresponding opening bracket of the same type.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"()\"`\n"
        "- Output: `True`\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"()[]{}\"`\n"
        "- Output: `True`\n\n"
        "**Example 3:**\n"
        "- Input: `s = \"(]\"`\n"
        "- Output: `False`\n\n"
        "**Example 4:**\n"
        "- Input: `s = \"([)]\"`\n"
        "- Output: `False` — the brackets interleave, so they're not properly nested.\n\n"
        "**Example 5:**\n"
        "- Input: `s = \"{[]}\"`\n"
        "- Output: `True`"
    ),
    "hints": [
        "The 'most recent opener must match the next closer' phrasing screams LIFO — that's a stack.",
        "Walk the string once. Push openers onto a stack. On a closer, pop the top and check the pair matches.",
        "Two failure modes: (a) closer arrives but the stack is empty, (b) the popped opener doesn't match the closer.",
        "After the walk, the stack must be empty. A non-empty stack means unmatched openers (e.g. `\"(\"`).",
        "A length-odd string can never be valid — useful early-exit micro-optimisation, not required.",
    ],
    "constraints": [
        "1 <= s.length <= 10⁴",
        "s consists of parentheses only `'()[]{}'`.",
    ],
    "starter_code": {
        "python": "def is_valid(s):\n    # Your code here\n    pass",
        "javascript": "function isValid(s) {\n    // Your code here\n}",
        "java": "public boolean isValid(String s) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\"()\", \"()[]{}\", \"(]\", \"([)]\", \"{[]}\"]\n"
            "    for s in cases:\n"
            "        print(f\"is_valid({s!r}) = {is_valid(s)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\"()\", \"()[]{}\", \"(]\", \"([)]\", \"{[]}\"].forEach(s =>\n"
            "    console.log(`isValid(${JSON.stringify(s)}) =`, isValid(s))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.isValid(\"()[]{}\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "()"}, "expected": True,
         "description": "Single matched pair", "tags": ["basic"]},
        {"input": {"s": "()[]{}"}, "expected": True,
         "description": "Three sibling pairs in sequence", "tags": ["basic"]},
        {"input": {"s": "(]"}, "expected": False,
         "description": "Mismatched bracket types", "tags": ["basic"]},
        {"input": {"s": "([)]"}, "expected": False,
         "description": "Interleaved is not properly nested", "tags": ["tricky"]},
        {"input": {"s": "{[]}"}, "expected": True,
         "description": "Properly nested mixed brackets", "tags": ["basic"]},
        {"input": {"s": ""}, "expected": True,
         "description": "Empty string is vacuously valid", "tags": ["edge"]},
        {"input": {"s": "("}, "expected": False,
         "description": "Single unmatched opener — stack non-empty at end", "tags": ["edge"]},
        {"input": {"s": ")"}, "expected": False,
         "description": "Closer with no opener — pop on empty stack", "tags": ["edge"]},
        {"input": {"s": "(((((((("}, "expected": False,
         "description": "All openers, no closers — stack non-empty at end", "tags": ["edge"]},
        {"input": {"s": "{[(]}"}, "expected": False,
         "description": "Inner mismatch — '(' popped to match ']'", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Stack (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk the string once. For each opener, push it onto a stack. For each closer, check the "
                "stack is non-empty and that the top matches the expected partner; if either check fails, "
                "the string is invalid. After the walk, the stack must be empty — any leftover openers "
                "are unmatched. A small dict mapping closer → opener keeps the match check to one lookup."
            ),
            "code": {
                "python": (
                    "def is_valid(s):\n"
                    "    pairs = {')': '(', ']': '[', '}': '{'}\n"
                    "    stack = []\n"
                    "    for ch in s:\n"
                    "        if ch in pairs:\n"
                    "            if not stack or stack.pop() != pairs[ch]:\n"
                    "                return False\n"
                    "        else:\n"
                    "            stack.append(ch)\n"
                    "    return not stack"
                ),
                "javascript": (
                    "function isValid(s) {\n"
                    "    const pairs = {')': '(', ']': '[', '}': '{'};\n"
                    "    const stack = [];\n"
                    "    for (const ch of s) {\n"
                    "        if (ch in pairs) {\n"
                    "            if (stack.pop() !== pairs[ch]) return false;\n"
                    "        } else {\n"
                    "            stack.push(ch);\n"
                    "        }\n"
                    "    }\n"
                    "    return stack.length === 0;\n"
                    "}"
                ),
                "java": (
                    "public boolean isValid(String s) {\n"
                    "    Deque<Character> stack = new ArrayDeque<>();\n"
                    "    for (char ch : s.toCharArray()) {\n"
                    "        if (ch == '(' || ch == '[' || ch == '{') {\n"
                    "            stack.push(ch);\n"
                    "        } else {\n"
                    "            if (stack.isEmpty()) return false;\n"
                    "            char top = stack.pop();\n"
                    "            if ((ch == ')' && top != '(') ||\n"
                    "                (ch == ']' && top != '[') ||\n"
                    "                (ch == '}' && top != '{')) return false;\n"
                    "        }\n"
                    "    }\n"
                    "    return stack.isEmpty();\n"
                    "}"
                ),
            },
        },
        {
            "title": "Repeated Replacement (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(n)",
            "description": (
                "Repeatedly remove every `\"()\"`, `\"[]\"`, and `\"{}\"` from the string until no more "
                "removals happen. If the result is empty, the string was valid. Conceptually clean and "
                "easy to explain in an interview, but each pass is O(n) and you may need O(n) passes — "
                "so the total is O(n²). Mention as the baseline; submit the stack solution."
            ),
            "code": {
                "python": (
                    "def is_valid(s):\n"
                    "    prev = None\n"
                    "    while prev != s:\n"
                    "        prev = s\n"
                    "        s = s.replace('()', '').replace('[]', '').replace('{}', '')\n"
                    "    return s == ''"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate the rule: every closer must match the *most recent* still-open opener. 'Most recent' is the LIFO signal — reach for a stack.",
        "2. Walk left-to-right. Openers get pushed; closers consume the top of the stack.",
        "3. On a closer, two things must be true: the stack is non-empty, AND the top is the matching opener. If either fails, return False immediately.",
        "4. Encode the matching rule once — a dict `{')': '(', ']': '[', '}': '{'}` keeps the body branch-free.",
        "5. After the walk, an empty stack means everything got matched. A non-empty stack means leftover openers (`\"(\"`, `\"((\"` etc.) → return False.",
        "6. Edge cases: empty string (return True — vacuous), single closer (pop-on-empty), single opener (non-empty stack at end), interleaved like `\"([)]\"` (top mismatch).",
    ],
    "tips": [
        "The two failure modes are symmetric — closer-without-opener (stack empty when you try to pop) and opener-without-closer (stack non-empty at the end). Don't forget the second check; many candidates do.",
        "Use a dict from closer → opener, not opener → closer. You're popping when you see a closer, so you want to look up the *expected* opener in O(1).",
        "In Python, `stack.pop()` on an empty list raises IndexError — guard with `if not stack` before popping, or wrap in try/except. Most interviewers prefer the explicit check.",
        "In Java, prefer `ArrayDeque` over `Stack` — `Stack` extends `Vector` and is synchronized (slow). The interview-correct stack is `Deque<Character> stack = new ArrayDeque<>();`.",
        "An odd-length string cannot be valid — you can early-return False at the start. It's a micro-optimisation, but worth mentioning to show you're thinking about pruning.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Bloomberg", "Facebook"],
    "topics": ["Stack", "String"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(s):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for ch in s:
        if ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
        else:
            stack.append(ch)
    return not stack


register(PAYLOAD, REFERENCE)
