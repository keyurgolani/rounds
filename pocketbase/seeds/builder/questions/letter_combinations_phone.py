"""Letter Combinations of a Phone Number — Medium. Backtracking / BFS.

The canonical 'enumerate the cartesian product' problem. Every digit
maps to 3 or 4 letters (T9 keypad), and the answer is every length-n
string you can form by picking one letter per digit. Two clean
templates: recursive backtracking, and iterative BFS that grows a
queue of partial strings. The empty-input edge case trips people up.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Letter Combinations of a Phone Number",
    "difficulty": "Medium",
    "description": (
        "Given a string `digits` containing digits from `2-9` inclusive, return all possible letter "
        "combinations that the number could represent. Return the answer in **any order**.\n\n"
        "A mapping of digits to letters (just like on the telephone buttons) is given below. Note that "
        "`1` does not map to any letters.\n\n"
        "- `2` → `abc`\n"
        "- `3` → `def`\n"
        "- `4` → `ghi`\n"
        "- `5` → `jkl`\n"
        "- `6` → `mno`\n"
        "- `7` → `pqrs`\n"
        "- `8` → `tuv`\n"
        "- `9` → `wxyz`\n\n"
        "**Example 1:**\n"
        "- Input: `digits = \"23\"`\n"
        "- Output: `[\"ad\",\"ae\",\"af\",\"bd\",\"be\",\"bf\",\"cd\",\"ce\",\"cf\"]`\n\n"
        "**Example 2:**\n"
        "- Input: `digits = \"\"`\n"
        "- Output: `[]`\n\n"
        "**Example 3:**\n"
        "- Input: `digits = \"2\"`\n"
        "- Output: `[\"a\",\"b\",\"c\"]`"
    ),
    "hints": [
        "Empty input is its own case — the answer is `[]`, not `[\"\"]`. Handle it before recursing.",
        "Think cartesian product: for digits of length n, the result has roughly 3^n to 4^n strings, each of length n.",
        "Backtracking: build a partial string, recurse on the next digit, undo on return. Standard DFS template.",
        "Iterative BFS: start with `[\"\"]`. For each digit, replace the current frontier with `frontier × letters_for_digit`.",
        "Keep the digit→letters mapping in a dict or a fixed array indexed by `int(digit) - 2`. Both are fine.",
    ],
    "constraints": [
        "0 <= digits.length <= 4",
        "digits[i] is a digit in the range ['2', '9'].",
    ],
    "starter_code": {
        "python": "def letter_combinations(digits):\n    # Your code here\n    pass",
        "javascript": "function letterCombinations(digits) {\n    // Your code here\n}",
        "java": "public List<String> letterCombinations(String digits) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\"23\", \"\", \"2\", \"7\"]\n"
            "    for digits in cases:\n"
            "        print(f\"letter_combinations({digits!r}) = {letter_combinations(digits)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\"23\", \"\", \"2\", \"7\"].forEach(digits =>\n"
            "    console.log(`letterCombinations(${JSON.stringify(digits)}) =`, letterCombinations(digits))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.letterCombinations(\"23\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"digits": "23"},
         "expected": {"$match": "unordered_deep",
                      "value": ["ad", "ae", "af", "bd", "be", "bf", "cd", "ce", "cf"]},
         "description": "Two digits — 3 × 3 = 9 combinations", "tags": ["basic"]},
        {"input": {"digits": ""},
         "expected": [],
         "description": "Empty input — return empty list (not `[\"\"]`)", "tags": ["edge"]},
        {"input": {"digits": "2"},
         "expected": {"$match": "unordered_deep", "value": ["a", "b", "c"]},
         "description": "Single 3-letter digit", "tags": ["basic"]},
        {"input": {"digits": "7"},
         "expected": {"$match": "unordered_deep", "value": ["p", "q", "r", "s"]},
         "description": "Single 4-letter digit (pqrs)", "tags": ["edge"]},
        {"input": {"digits": "9"},
         "expected": {"$match": "unordered_deep", "value": ["w", "x", "y", "z"]},
         "description": "Single 4-letter digit (wxyz)", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Backtracking (Recursive DFS)",
            "time_complexity": "O(4^n × n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk the digits left-to-right. At each position, for each letter the digit maps to, append "
                "the letter, recurse on the next position, then pop. When the path length equals the input "
                "length, snapshot the path into the result. Recursion depth = n, so the stack is O(n); the "
                "output dominates with up to 4^n strings of length n."
            ),
            "code": {
                "python": (
                    "def letter_combinations(digits):\n"
                    "    if not digits:\n"
                    "        return []\n"
                    "    mapping = {\n"
                    "        '2': 'abc', '3': 'def', '4': 'ghi', '5': 'jkl',\n"
                    "        '6': 'mno', '7': 'pqrs', '8': 'tuv', '9': 'wxyz',\n"
                    "    }\n"
                    "    result = []\n"
                    "    path = []\n"
                    "    def backtrack(i):\n"
                    "        if i == len(digits):\n"
                    "            result.append(''.join(path))\n"
                    "            return\n"
                    "        for ch in mapping[digits[i]]:\n"
                    "            path.append(ch)\n"
                    "            backtrack(i + 1)\n"
                    "            path.pop()\n"
                    "    backtrack(0)\n"
                    "    return result"
                ),
                "javascript": (
                    "function letterCombinations(digits) {\n"
                    "    if (!digits) return [];\n"
                    "    const mapping = {\n"
                    "        '2': 'abc', '3': 'def', '4': 'ghi', '5': 'jkl',\n"
                    "        '6': 'mno', '7': 'pqrs', '8': 'tuv', '9': 'wxyz',\n"
                    "    };\n"
                    "    const result = [];\n"
                    "    const path = [];\n"
                    "    const backtrack = (i) => {\n"
                    "        if (i === digits.length) {\n"
                    "            result.push(path.join(''));\n"
                    "            return;\n"
                    "        }\n"
                    "        for (const ch of mapping[digits[i]]) {\n"
                    "            path.push(ch);\n"
                    "            backtrack(i + 1);\n"
                    "            path.pop();\n"
                    "        }\n"
                    "    };\n"
                    "    backtrack(0);\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public List<String> letterCombinations(String digits) {\n"
                    "    List<String> result = new ArrayList<>();\n"
                    "    if (digits.isEmpty()) return result;\n"
                    "    String[] mapping = {\"\", \"\", \"abc\", \"def\", \"ghi\", \"jkl\",\n"
                    "                        \"mno\", \"pqrs\", \"tuv\", \"wxyz\"};\n"
                    "    StringBuilder path = new StringBuilder();\n"
                    "    backtrack(digits, 0, mapping, path, result);\n"
                    "    return result;\n"
                    "}\n"
                    "private void backtrack(String digits, int i, String[] mapping,\n"
                    "                       StringBuilder path, List<String> result) {\n"
                    "    if (i == digits.length()) {\n"
                    "        result.add(path.toString());\n"
                    "        return;\n"
                    "    }\n"
                    "    for (char ch : mapping[digits.charAt(i) - '0'].toCharArray()) {\n"
                    "        path.append(ch);\n"
                    "        backtrack(digits, i + 1, mapping, path, result);\n"
                    "        path.deleteCharAt(path.length() - 1);\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative BFS (Queue)",
            "time_complexity": "O(4^n × n)",
            "space_complexity": "O(4^n × n)",
            "description": (
                "Treat the partial strings as a frontier. Initialise the frontier as `[\"\"]`. For each "
                "digit, replace the frontier with the cartesian product of the current frontier and the "
                "digit's letters. After processing all digits, the frontier *is* the answer. Same "
                "asymptotic complexity as backtracking; some prefer it because it avoids recursion."
            ),
            "code": {
                "python": (
                    "def letter_combinations(digits):\n"
                    "    if not digits:\n"
                    "        return []\n"
                    "    mapping = {\n"
                    "        '2': 'abc', '3': 'def', '4': 'ghi', '5': 'jkl',\n"
                    "        '6': 'mno', '7': 'pqrs', '8': 'tuv', '9': 'wxyz',\n"
                    "    }\n"
                    "    frontier = ['']\n"
                    "    for d in digits:\n"
                    "        frontier = [prefix + ch for prefix in frontier for ch in mapping[d]]\n"
                    "    return frontier"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: this is a cartesian product over per-digit letter sets. Output size is the product of |letters(d)| for each digit d — between 3^n and 4^n.",
        "2. Edge case first: empty digits → return `[]`, not `[\"\"]`. Mis-handling this is the most common bug.",
        "3. Pick a representation for the mapping: a dict keyed by digit char, or a fixed array indexed by `int(d) - 2`. Either is fine; the dict reads more clearly.",
        "4. Backtracking template: maintain a `path` list, recurse with index `i`. At `i == len(digits)`, snapshot `''.join(path)` into the result.",
        "5. Iterative alternative: seed a frontier with `['']`, then for each digit grow the frontier via list comprehension `[p + c for p in frontier for c in letters(d)]`. Same complexity, no recursion.",
        "6. Complexity: O(4^n × n) time (4^n leaves, n work to materialise each string), O(n) extra space for backtracking (excluding the output) or O(4^n × n) for the BFS frontier.",
    ],
    "tips": [
        "Empty input → `[]` not `[\"\"]`. Pin this down before writing the recursion — many candidates accidentally produce a single empty string.",
        "Prune nothing — the problem asks for *all* combinations, so every leaf is valid. Don't add a 'skip' branch by mistake.",
        "Think of it as a generalised cartesian product. If the alphabet were `{0..9}` instead of `{a..z}`, the same template generates every n-digit number — useful framing for follow-ups.",
        "Constant-factor win: in Python, `''.join(path)` once per leaf beats string concatenation on every recursive call (which copies O(n) per level → O(n²) per leaf).",
        "For the BFS variant, keep the frontier as a list and reassign each iteration. A `deque` is unnecessary because you process the entire frontier per digit, not one element at a time.",
    ],
    "companies": ["Amazon", "Apple", "Microsoft"],
    "topics": ["String", "Backtracking", "Hash Table"],
    "time_complexity": "O(4^n × n)",
    "space_complexity": "O(n)",
}


def REFERENCE(digits):
    if not digits:
        return []
    mapping = {
        '2': 'abc', '3': 'def', '4': 'ghi', '5': 'jkl',
        '6': 'mno', '7': 'pqrs', '8': 'tuv', '9': 'wxyz',
    }
    result = []
    path = []

    def backtrack(i):
        if i == len(digits):
            result.append(''.join(path))
            return
        for ch in mapping[digits[i]]:
            path.append(ch)
            backtrack(i + 1)
            path.pop()

    backtrack(0)
    return result


register(PAYLOAD, REFERENCE)
