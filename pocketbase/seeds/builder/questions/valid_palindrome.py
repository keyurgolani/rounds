"""Valid Palindrome — Easy. Two Pointers / Strings.

The 'easy' part is the algorithm. The interview part is the input
preprocessing: case-folding, alphanumeric filtering, and whether you
do it eagerly (O(n) extra space) or lazily inside the two-pointer
walk (O(1) extra space). The latter is what separates a passing
answer from a clean one.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Valid Palindrome",
    "difficulty": "Easy",
    "description": (
        "A phrase is a **palindrome** if, after converting all uppercase letters into lowercase letters "
        "and removing all non-alphanumeric characters, it reads the same forward and backward. "
        "Alphanumeric characters include letters and numbers.\n\n"
        "Given a string `s`, return `true` if it is a palindrome, or `false` otherwise.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"A man, a plan, a canal: Panama\"`\n"
        "- Output: `true`\n"
        "- Explanation: `\"amanaplanacanalpanama\"` is a palindrome.\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"race a car\"`\n"
        "- Output: `false`\n"
        "- Explanation: `\"raceacar\"` is not a palindrome.\n\n"
        "**Example 3:**\n"
        "- Input: `s = \" \"`\n"
        "- Output: `true`\n"
        "- Explanation: After removing non-alphanumeric characters, `s` is an empty string. An empty string reads the same forward and backward, so it is a palindrome."
    ),
    "hints": [
        "Decompose the problem: 'normalise' (lowercase + strip non-alphanumeric) then 'check palindrome'.",
        "Easiest implementation: build the cleaned string, then compare to its reverse. O(n) time, O(n) space.",
        "Better: two pointers from each end. Skip non-alphanumeric characters in place, compare lowercased letters. O(n) time, O(1) space.",
        "Edge case: empty string and pure-punctuation strings are palindromes by definition (the cleaned string is empty).",
        "Built-ins help: Python's `str.isalnum()` and `str.lower()` cover both checks.",
    ],
    "constraints": [
        "1 <= s.length <= 2 * 10⁵",
        "`s` consists only of printable ASCII characters",
    ],
    "starter_code": {
        "python": "def is_palindrome(s):\n    # Your code here\n    pass",
        "javascript": "function isPalindrome(s) {\n    // Your code here\n}",
        "java": "public boolean isPalindrome(String s) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        \"A man, a plan, a canal: Panama\",\n"
            "        \"race a car\",\n"
            "        \" \",\n"
            "    ]\n"
            "    for s in cases:\n"
            "        print(f\"is_palindrome({s!r}) = {is_palindrome(s)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "['A man, a plan, a canal: Panama', 'race a car', ' '].forEach(s =>\n"
            "    console.log(`isPalindrome(${JSON.stringify(s)}) =`, isPalindrome(s))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.isPalindrome(\"A man, a plan, a canal: Panama\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "A man, a plan, a canal: Panama"}, "expected": True,
         "description": "Classic example — punctuation and case", "tags": ["basic"]},
        {"input": {"s": "race a car"}, "expected": False,
         "description": "Almost a palindrome, fails on the 'e' vs 'c'", "tags": ["basic"]},
        {"input": {"s": " "}, "expected": True,
         "description": "Whitespace only — cleaned form is empty", "tags": ["edge"]},
        {"input": {"s": ""}, "expected": True,
         "description": "Empty string is a palindrome by convention", "tags": ["edge"]},
        {"input": {"s": "a"}, "expected": True,
         "description": "Single character", "tags": ["edge"]},
        {"input": {"s": "0P"}, "expected": False,
         "description": "Digit vs letter — case folding doesn't help",
         "tags": ["tricky"]},
        {"input": {"s": "Was it a car or a cat I saw?"}, "expected": True,
         "description": "Long phrase with mixed punctuation", "tags": ["basic"]},
        {"input": {"s": "12321"}, "expected": True,
         "description": "Digits only — palindrome", "tags": ["basic"]},
        {"input": {"s": "12345"}, "expected": False,
         "description": "Digits only — not a palindrome", "tags": ["edge"]},
        {"input": {"s": "Able was I, ere I saw Elba."}, "expected": True,
         "description": "Famous English-language palindrome", "tags": ["tricky"]},
        {"input": {"s": "x" * 100000 + "y" + "x" * 100000}, "expected": True,
         "description": "200K characters — two-pointer must run in O(n)", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Two Pointers (Optimal — O(1) space)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk pointers from both ends. Skip past non-alphanumeric characters on each side, then "
                "compare lowercased letters. Stop when the pointers cross. No auxiliary string allocation."
            ),
            "code": {
                "python": (
                    "def is_palindrome(s):\n"
                    "    i, j = 0, len(s) - 1\n"
                    "    while i < j:\n"
                    "        while i < j and not s[i].isalnum():\n"
                    "            i += 1\n"
                    "        while i < j and not s[j].isalnum():\n"
                    "            j -= 1\n"
                    "        if s[i].lower() != s[j].lower():\n"
                    "            return False\n"
                    "        i += 1\n"
                    "        j -= 1\n"
                    "    return True"
                ),
                "javascript": (
                    "function isPalindrome(s) {\n"
                    "    const isAlnum = (c) => /[a-z0-9]/i.test(c);\n"
                    "    let i = 0, j = s.length - 1;\n"
                    "    while (i < j) {\n"
                    "        while (i < j && !isAlnum(s[i])) i++;\n"
                    "        while (i < j && !isAlnum(s[j])) j--;\n"
                    "        if (s[i].toLowerCase() !== s[j].toLowerCase()) return false;\n"
                    "        i++; j--;\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
                "java": (
                    "public boolean isPalindrome(String s) {\n"
                    "    int i = 0, j = s.length() - 1;\n"
                    "    while (i < j) {\n"
                    "        while (i < j && !Character.isLetterOrDigit(s.charAt(i))) i++;\n"
                    "        while (i < j && !Character.isLetterOrDigit(s.charAt(j))) j--;\n"
                    "        if (Character.toLowerCase(s.charAt(i)) != Character.toLowerCase(s.charAt(j))) return false;\n"
                    "        i++; j--;\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Filter + Reverse Compare",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Strip non-alphanumerics, lowercase, then compare to the reverse. Two lines in Python. Spends "
                "O(n) extra space on the cleaned string but is the easiest version to whiteboard and explain "
                "to a non-technical interviewer."
            ),
            "code": {
                "python": (
                    "def is_palindrome(s):\n"
                    "    cleaned = ''.join(ch.lower() for ch in s if ch.isalnum())\n"
                    "    return cleaned == cleaned[::-1]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Decompose: normalise (lowercase, strip non-alphanumeric), then check palindrome.",
        "2. Brute version: build cleaned string, compare to its reverse. Easy, O(n) extra memory.",
        "3. Optimise space: do the normalisation lazily inside a two-pointer walk; skip non-alphanumerics in place.",
        "4. Lowercase comparison only at the moment of comparison — don't allocate a new string.",
        "5. Watch the alphanumeric definition: digits count too. `'0P'` looks palindrome-ish but isn't (0 ≠ p).",
        "6. Edge cases: empty, pure-whitespace, single character, pure digits.",
    ],
    "tips": [
        "Confirm the alphanumeric rule before coding. Some variants only consider letters; some are case-sensitive.",
        "`str.isalnum()` is your best friend in Python — it already handles 'a'-'z', 'A'-'Z', '0'-'9'.",
        "Don't write `s = re.sub(r'[^a-z0-9]', '', s.lower())` and then `s == s[::-1]` without acknowledging the O(n) extra space — for a 200K input it matters.",
        "Common follow-up: 'What if you can delete at most one character? Is it still a palindrome?' → Two pointers, on first mismatch try skipping left or right and recurse.",
        "Common follow-up: 'What if the string is Unicode?' → `str.casefold()` handles full-Unicode case folding (e.g. 'ß' → 'ss'); `str.lower()` doesn't.",
    ],
    "companies": ["Microsoft", "Facebook", "Amazon", "Apple", "Bloomberg"],
    "topics": ["Two Pointers", "String"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(s):
    i, j = 0, len(s) - 1
    while i < j:
        while i < j and not s[i].isalnum():
            i += 1
        while i < j and not s[j].isalnum():
            j -= 1
        if s[i].lower() != s[j].lower():
            return False
        i += 1
        j -= 1
    return True


register(PAYLOAD, REFERENCE)
