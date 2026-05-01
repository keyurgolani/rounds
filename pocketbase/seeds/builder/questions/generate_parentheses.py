"""Generate Parentheses — Medium. Backtracking / DP.

The Catalan-number poster child. Given n pairs, enumerate every
well-formed string of length 2n. The two clean templates are
backtracking with running open/close counts (the universal
interview answer) and a closure-decomposition DP that's worth
knowing because it makes the Catalan recurrence concrete:
C(n) = sum_{i=0..n-1} C(i) * C(n-1-i). The result count is the
n-th Catalan number — 1, 2, 5, 14, 42, 132, 429, 1430 for n in 1..8.
"""
from builder.registry import register, unordered_deep


PAYLOAD = {
    "title": "Generate Parentheses",
    "difficulty": "Medium",
    "description": (
        "Given `n` pairs of parentheses, write a function to generate **all combinations of well-formed "
        "parentheses**.\n\n"
        "Return the answer in **any order**.\n\n"
        "**Example 1:**\n"
        "- Input: `n = 3`\n"
        "- Output: `[\"((()))\",\"(()())\",\"(())()\",\"()(())\",\"()()()\"]`\n\n"
        "**Example 2:**\n"
        "- Input: `n = 1`\n"
        "- Output: `[\"()\"]`\n\n"
        "**Example 3:**\n"
        "- Input: `n = 2`\n"
        "- Output: `[\"(())\",\"()()\"]`"
    ),
    "hints": [
        "Brute force: enumerate every length-2n string over `{(, )}` (2^(2n) of them) and filter for validity. State it as a baseline; never code it.",
        "Backtracking invariant: at any partial prefix, `open_count >= close_count`. Maintain both counters; never add `)` unless `close < open`.",
        "Stop conditions: only emit when `open == n AND close == n`. Add `(` while `open < n`. Add `)` while `close < open`.",
        "The output count is the n-th Catalan number C(n) = (2n)! / ((n+1)! * n!). For n in 1..8 that's 1, 2, 5, 14, 42, 132, 429, 1430.",
        "DP / closure decomposition: every valid string of length 2n has a unique split `(A)B` where A is a valid string of i pairs and B a valid string of n-1-i pairs. Recurrence: f(n) = union over i in [0..n-1] of `'(' + a + ')' + b for a in f(i) for b in f(n-1-i)`.",
    ],
    "constraints": [
        "1 <= n <= 8",
    ],
    "starter_code": {
        "python": "def generate_parenthesis(n):\n    # Your code here\n    pass",
        "javascript": "function generateParenthesis(n) {\n    // Your code here\n}",
        "java": "public List<String> generateParenthesis(int n) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for n in [1, 2, 3, 4]:\n"
            "        print(f\"generate_parenthesis({n}) = {generate_parenthesis(n)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[1, 2, 3, 4].forEach(n =>\n"
            "    console.log(`generateParenthesis(${n}) =`, generateParenthesis(n))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.generateParenthesis(3));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"n": 1},
         "expected": ["()"],
         "description": "Single pair — only one valid combination", "tags": ["edge"]},
        {"input": {"n": 2},
         "expected": unordered_deep(["(())", "()()"]),
         "description": "Two pairs — Catalan(2) = 2 combinations", "tags": ["basic"]},
        {"input": {"n": 3},
         "expected": unordered_deep(["((()))", "(()())", "(())()", "()(())", "()()()"]),
         "description": "Three pairs — Catalan(3) = 5 combinations", "tags": ["basic"]},
        {"input": {"n": 4},
         "expected": unordered_deep([
             "(((())))", "((()()))", "((())())", "((()))()",
             "(()(()))", "(()()())", "(()())()", "(())(())",
             "(())()()", "()((()))", "()(()())", "()(())()",
             "()()(())", "()()()()",
         ]),
         "description": "Four pairs — Catalan(4) = 14 combinations", "tags": ["tricky"]},
        {"input": {"n": 5},
         "expected": unordered_deep([
             "((((()))))", "(((()())))", "(((())()))", "(((()))())", "(((())))()",
             "((()(())))", "((()()()))", "((()())())", "((()()))()", "((())(()))",
             "((())()())", "((())())()", "((()))(())", "((()))()()", "(()((())))",
             "(()(()()))", "(()(())())", "(()(()))()", "(()()(()))", "(()()()())",
             "(()()())()", "(()())(())", "(()())()()", "(())((()))", "(())(()())",
             "(())(())()", "(())()(())", "(())()()()", "()(((())))", "()((()()))",
             "()((())())", "()((()))()", "()(()(()))", "()(()()())", "()(()())()",
             "()(())(())", "()(())()()", "()()((()))", "()()(()())", "()()(())()",
             "()()()(())", "()()()()()",
         ]),
         "description": "Five pairs — Catalan(5) = 42 combinations (stress)", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Backtracking with Open/Close Counts (Optimal)",
            "time_complexity": "O(4^n / sqrt(n))",
            "space_complexity": "O(n)",
            "description": (
                "Walk a decision tree of length 2n. At each step you can append `(` (if `open < n`) or "
                "`)` (if `close < open`). The `close < open` guard is what keeps every visited prefix "
                "valid — no post-hoc filtering required. When `open == close == n`, snapshot the path. "
                "Time is bounded by the number of leaves, the n-th Catalan number, which grows like "
                "4^n / (n^1.5 * sqrt(pi)); space is O(n) for the recursion stack and the path."
            ),
            "code": {
                "python": (
                    "def generate_parenthesis(n):\n"
                    "    result = []\n"
                    "    path = []\n"
                    "    def backtrack(open_count, close_count):\n"
                    "        if open_count == n and close_count == n:\n"
                    "            result.append(''.join(path))\n"
                    "            return\n"
                    "        if open_count < n:\n"
                    "            path.append('(')\n"
                    "            backtrack(open_count + 1, close_count)\n"
                    "            path.pop()\n"
                    "        if close_count < open_count:\n"
                    "            path.append(')')\n"
                    "            backtrack(open_count, close_count + 1)\n"
                    "            path.pop()\n"
                    "    backtrack(0, 0)\n"
                    "    return result"
                ),
                "javascript": (
                    "function generateParenthesis(n) {\n"
                    "    const result = [];\n"
                    "    const path = [];\n"
                    "    const backtrack = (openCount, closeCount) => {\n"
                    "        if (openCount === n && closeCount === n) {\n"
                    "            result.push(path.join(''));\n"
                    "            return;\n"
                    "        }\n"
                    "        if (openCount < n) {\n"
                    "            path.push('(');\n"
                    "            backtrack(openCount + 1, closeCount);\n"
                    "            path.pop();\n"
                    "        }\n"
                    "        if (closeCount < openCount) {\n"
                    "            path.push(')');\n"
                    "            backtrack(openCount, closeCount + 1);\n"
                    "            path.pop();\n"
                    "        }\n"
                    "    };\n"
                    "    backtrack(0, 0);\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public List<String> generateParenthesis(int n) {\n"
                    "    List<String> result = new ArrayList<>();\n"
                    "    backtrack(result, new StringBuilder(), 0, 0, n);\n"
                    "    return result;\n"
                    "}\n"
                    "private void backtrack(List<String> result, StringBuilder path,\n"
                    "                       int open, int close, int n) {\n"
                    "    if (open == n && close == n) {\n"
                    "        result.add(path.toString());\n"
                    "        return;\n"
                    "    }\n"
                    "    if (open < n) {\n"
                    "        path.append('(');\n"
                    "        backtrack(result, path, open + 1, close, n);\n"
                    "        path.deleteCharAt(path.length() - 1);\n"
                    "    }\n"
                    "    if (close < open) {\n"
                    "        path.append(')');\n"
                    "        backtrack(result, path, open, close + 1, n);\n"
                    "        path.deleteCharAt(path.length() - 1);\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Closure Decomposition DP",
            "time_complexity": "O(4^n / sqrt(n))",
            "space_complexity": "O(4^n / sqrt(n))",
            "description": (
                "Every valid string of length 2n has a unique decomposition `(A)B` where A is a valid "
                "string of i pairs (`0 <= i <= n-1`) and B is a valid string of n-1-i pairs. Build "
                "`f[k]` bottom-up for k = 0..n: `f[0] = ['']`, `f[k] = ['(' + a + ')' + b for i in "
                "range(k) for a in f[i] for b in f[k-1-i]]`. The recurrence mirrors the Catalan "
                "recurrence C(n) = sum C(i) * C(n-1-i) — useful framing for follow-up combinatorial "
                "questions."
            ),
            "code": {
                "python": (
                    "def generate_parenthesis(n):\n"
                    "    f = [['']]\n"
                    "    for k in range(1, n + 1):\n"
                    "        layer = []\n"
                    "        for i in range(k):\n"
                    "            for a in f[i]:\n"
                    "                for b in f[k - 1 - i]:\n"
                    "                    layer.append('(' + a + ')' + b)\n"
                    "        f.append(layer)\n"
                    "    return f[n]"
                ),
                "javascript": (
                    "function generateParenthesis(n) {\n"
                    "    const f = [['']];\n"
                    "    for (let k = 1; k <= n; k++) {\n"
                    "        const layer = [];\n"
                    "        for (let i = 0; i < k; i++) {\n"
                    "            for (const a of f[i]) {\n"
                    "                for (const b of f[k - 1 - i]) {\n"
                    "                    layer.push('(' + a + ')' + b);\n"
                    "                }\n"
                    "            }\n"
                    "        }\n"
                    "        f.push(layer);\n"
                    "    }\n"
                    "    return f[n];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force Enumeration (Baseline)",
            "time_complexity": "O(2^(2n) * n)",
            "space_complexity": "O(n)",
            "description": (
                "Generate every length-2n string over `{(, )}` (there are 2^(2n) of them), then filter "
                "by checking the running prefix-balance never goes negative and ends at zero. State it "
                "to anchor the optimisation; never submit it — it does ~16x more work than the "
                "Catalan-bounded backtracking for n=8."
            ),
            "code": {
                "python": (
                    "def generate_parenthesis(n):\n"
                    "    def is_valid(s):\n"
                    "        bal = 0\n"
                    "        for ch in s:\n"
                    "            bal += 1 if ch == '(' else -1\n"
                    "            if bal < 0:\n"
                    "                return False\n"
                    "        return bal == 0\n"
                    "    result = []\n"
                    "    def gen(path):\n"
                    "        if len(path) == 2 * n:\n"
                    "            if is_valid(path):\n"
                    "                result.append(path)\n"
                    "            return\n"
                    "        gen(path + '(')\n"
                    "        gen(path + ')')\n"
                    "    gen('')\n"
                    "    return result"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force: enumerate every length-2n string over `{(, )}` and filter by validity. 2^(2n) candidates — exponential and wasteful since most are invalid. State it as the baseline.",
        "2. Key observation: a prefix is *extensible to a valid string* iff at every position `open >= close` and the totals are bounded by n. Track those two counters and you never visit a doomed branch.",
        "3. Backtracking template: at each step, try `(` (if `open < n`) and `)` (if `close < open`). When both counts hit n, the path is a complete valid string — snapshot it.",
        "4. Why no validity check at the leaves? Because the two guards above make every visited prefix a valid extensible prefix. The leaves are valid by construction.",
        "5. Complexity: leaves = C(n), the n-th Catalan number, which is asymptotically `4^n / (n^1.5 * sqrt(pi))`. Each leaf takes O(n) to materialise. So total work is O(4^n / sqrt(n)) — strictly better than the 4^n you'd get from naive backtracking without the `close < open` prune.",
        "6. Alternative framing — closure decomposition: every valid string is uniquely `(A)B` with A a valid string of i pairs and B a valid string of n-1-i pairs. That gives the Catalan recurrence directly and makes a clean bottom-up DP. Same asymptotic cost, useful framing for follow-ups.",
    ],
    "tips": [
        "The result count is the n-th Catalan number — 1, 2, 5, 14, 42, 132, 429, 1430 for n = 1..8. Mention it; interviewers love the connection.",
        "Both guards (`open < n` and `close < open`) are independent — they're not `else if`. You can take *either* branch (or both, in different recursive calls) at each step.",
        "Don't post-filter for validity. The two guards make every visited path valid — adding a check at the leaf is dead code that signals you don't trust your invariant.",
        "The `(A)B` decomposition is the same recurrence used for counting binary trees, triangulations of an (n+2)-gon, and Dyck paths — all Catalan structures. Recognising that family of problems is a useful interview superpower.",
        "Constant-factor: in Python prefer `path.append`/`path.pop` with a final `''.join(path)` over string concatenation, which copies the prefix at every recursive call and inflates the per-leaf cost from O(n) to O(n^2).",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Facebook"],
    "topics": ["String", "Backtracking", "Dynamic Programming"],
    "time_complexity": "O(4^n / sqrt(n))",
    "space_complexity": "O(n)",
}


def REFERENCE(n):
    result = []
    path = []

    def backtrack(open_count, close_count):
        if open_count == n and close_count == n:
            result.append(''.join(path))
            return
        if open_count < n:
            path.append('(')
            backtrack(open_count + 1, close_count)
            path.pop()
        if close_count < open_count:
            path.append(')')
            backtrack(open_count, close_count + 1)
            path.pop()

    backtrack(0, 0)
    return result


register(PAYLOAD, REFERENCE)
