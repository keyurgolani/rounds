"""Valid Anagram — Easy. Strings / Hashing.

Tiny on the surface, deep underneath. The follow-up about Unicode is
the part most candidates blow: a 26-int counter array is great for
ASCII letters but breaks the moment the input includes 'é' or '日'.
Be ready to switch to a hash map when asked.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Valid Anagram",
    "difficulty": "Easy",
    "description": (
        "Given two strings `s` and `t`, return `true` if `t` is an anagram of `s`, "
        "and `false` otherwise.\n\n"
        "An **anagram** is a word or phrase formed by rearranging the letters of a "
        "different word or phrase, typically using all the original letters exactly once.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"anagram\", t = \"nagaram\"`\n"
        "- Output: `true`\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"rat\", t = \"car\"`\n"
        "- Output: `false`\n\n"
        "**Follow-up:** What if the inputs contain Unicode characters? How would you adapt your solution?"
    ),
    "hints": [
        "Different lengths → instantly `false`. Check this first; it's a free O(1) early exit.",
        "Sort both strings and compare — O(n log n) time, O(n) space (Python's `sorted` returns a new list). Easy to explain in a phone screen.",
        "Counter approach: tally character frequencies in `s`, decrement them as you walk `t`. If anything ends non-zero, return `false`. O(n) time.",
        "Optimisation for ASCII-only inputs: a 26-element int array is faster than a hash map (no hashing, fits in cache).",
        "Unicode follow-up: a fixed-size array breaks. Switch to a `dict`/`HashMap`. Be explicit about why during the interview.",
    ],
    "constraints": [
        "1 <= s.length, t.length <= 5 * 10⁴",
        "`s` and `t` consist of lowercase English letters",
    ],
    "starter_code": {
        "python": "def is_anagram(s, t):\n    # Your code here\n    pass",
        "javascript": "function isAnagram(s, t) {\n    // Your code here\n}",
        "java": "public boolean isAnagram(String s, String t) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(\"anagram\", \"nagaram\"), (\"rat\", \"car\"), (\"a\", \"a\")]\n"
            "    for s, t in cases:\n"
            "        print(f\"is_anagram({s!r}, {t!r}) = {is_anagram(s, t)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[['anagram','nagaram'], ['rat','car'], ['a','a']].forEach(([s,t]) =>\n"
            "    console.log(`isAnagram(${JSON.stringify(s)}, ${JSON.stringify(t)}) =`, isAnagram(s, t))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        String[][] cases = {{\"anagram\",\"nagaram\"}, {\"rat\",\"car\"}};\n"
            "        for (String[] c : cases) System.out.println(s.isAnagram(c[0], c[1]));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "anagram", "t": "nagaram"}, "expected": True,
         "description": "Classic anagram pair", "tags": ["basic"]},
        {"input": {"s": "rat", "t": "car"}, "expected": False,
         "description": "Same length, different letters", "tags": ["basic"]},
        {"input": {"s": "a", "t": "a"}, "expected": True,
         "description": "Identical single character", "tags": ["basic"]},
        {"input": {"s": "ab", "t": "a"}, "expected": False,
         "description": "Different lengths — early exit", "tags": ["edge"]},
        {"input": {"s": "", "t": ""}, "expected": True,
         "description": "Two empty strings (allowed by some variants — verify with interviewer)",
         "tags": ["edge"]},
        {"input": {"s": "aacc", "t": "ccac"}, "expected": False,
         "description": "Same letters, different multiplicity", "tags": ["tricky"]},
        {"input": {"s": "abcdefghijklmnop", "t": "ponmlkjihgfedcba"}, "expected": True,
         "description": "Reverse — every letter once", "tags": ["tricky"]},
        {"input": {"s": "listen", "t": "silent"}, "expected": True,
         "description": "Famous English-pair anagram", "tags": ["basic"]},
        {"input": {"s": "a" * 25000 + "b" * 25000, "t": "b" * 25000 + "a" * 25000}, "expected": True,
         "description": "50K characters — counter approach must outpace sort",
         "tags": ["large"]},
        {"input": {"s": "a" * 25000 + "b" * 25000, "t": "b" * 25000 + "a" * 24999 + "c"}, "expected": False,
         "description": "50K characters with a single mismatch", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Counter / Frequency Map (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(k) where k is the alphabet size (26 for lowercase ASCII)",
            "description": (
                "Length-mismatch shortcut, then count characters in `s` and decrement on `t`. "
                "If any count is non-zero at the end, the strings differ. Faster and simpler than sort, "
                "and the same shape extends to Unicode by swapping the array for a hash map."
            ),
            "code": {
                "python": (
                    "from collections import Counter\n\n"
                    "def is_anagram(s, t):\n"
                    "    if len(s) != len(t):\n"
                    "        return False\n"
                    "    return Counter(s) == Counter(t)"
                ),
                "javascript": (
                    "function isAnagram(s, t) {\n"
                    "    if (s.length !== t.length) return false;\n"
                    "    const counts = new Array(26).fill(0);\n"
                    "    const A = 'a'.charCodeAt(0);\n"
                    "    for (let i = 0; i < s.length; i++) {\n"
                    "        counts[s.charCodeAt(i) - A]++;\n"
                    "        counts[t.charCodeAt(i) - A]--;\n"
                    "    }\n"
                    "    return counts.every((c) => c === 0);\n"
                    "}"
                ),
                "java": (
                    "public boolean isAnagram(String s, String t) {\n"
                    "    if (s.length() != t.length()) return false;\n"
                    "    int[] counts = new int[26];\n"
                    "    for (int i = 0; i < s.length(); i++) {\n"
                    "        counts[s.charAt(i) - 'a']++;\n"
                    "        counts[t.charAt(i) - 'a']--;\n"
                    "    }\n"
                    "    for (int c : counts) if (c != 0) return false;\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sort + Compare",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n) (Python's `sorted` returns a new list)",
            "description": (
                "Sort both strings and compare. Two lines, easy to remember, slower than counting. "
                "Useful when you don't trust your counter implementation under interview pressure."
            ),
            "code": {
                "python": (
                    "def is_anagram(s, t):\n"
                    "    return sorted(s) == sorted(t)"
                ),
                "javascript": (
                    "function isAnagram(s, t) {\n"
                    "    if (s.length !== t.length) return false;\n"
                    "    return [...s].sort().join('') === [...t].sort().join('');\n"
                    "}"
                ),
                "java": (
                    "public boolean isAnagram(String s, String t) {\n"
                    "    if (s.length() != t.length()) return false;\n"
                    "    char[] a = s.toCharArray();\n"
                    "    char[] b = t.toCharArray();\n"
                    "    Arrays.sort(a);\n"
                    "    Arrays.sort(b);\n"
                    "    return Arrays.equals(a, b);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Hash Map (Unicode-safe)",
            "time_complexity": "O(n)",
            "space_complexity": "O(k) where k is the number of distinct code points",
            "description": (
                "Same idea as the counter but uses a hash map keyed by character. Handles arbitrary "
                "Unicode (combining marks, surrogate pairs aside) without resizing assumptions. "
                "Mention this when the interviewer asks the Unicode follow-up."
            ),
            "code": {
                "python": (
                    "def is_anagram(s, t):\n"
                    "    if len(s) != len(t):\n"
                    "        return False\n"
                    "    counts = {}\n"
                    "    for ch in s:\n"
                    "        counts[ch] = counts.get(ch, 0) + 1\n"
                    "    for ch in t:\n"
                    "        if counts.get(ch, 0) == 0:\n"
                    "            return False\n"
                    "        counts[ch] -= 1\n"
                    "    return True"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Length check first: if `len(s) != len(t)`, they can't be anagrams. Free O(1) prune.",
        "2. Reframe: 'anagram' means identical multiset of characters. The question is really 'do these two multisets match?'",
        "3. Two natural data structures: sorted sequence (multisets equal iff sorted forms equal) or frequency map (multisets equal iff counts equal).",
        "4. Pick by complexity: counter wins (O(n)) over sort (O(n log n)) once n grows.",
        "5. Pre-empt the Unicode follow-up: 26-int array breaks; HashMap survives.",
    ],
    "tips": [
        "`Counter(s) == Counter(t)` is the cleanest Python — but say 'I'm comparing frequency maps' so the interviewer hears the algorithm, not the syntax sugar.",
        "If the constraint says 'lowercase English letters', use the 26-int array — it's faster and the interviewer expects you to notice the constraint.",
        "Common follow-up: 'What if you can't allocate any extra space?' → You can't beat O(n log n) without it. State that explicitly.",
        "Common follow-up: 'What if the strings are streamed and you can only read each once?' → Two pointers + counter; you can no longer sort.",
        "Don't forget that case sensitivity and whitespace handling are interview-specific. Ask before assuming.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Apple", "Bloomberg"],
    "topics": ["Hash Table", "String", "Sorting"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1) (fixed alphabet)",
}


def REFERENCE(s, t):
    if len(s) != len(t):
        return False
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    for ch in t:
        if counts.get(ch, 0) == 0:
            return False
        counts[ch] -= 1
    return True


register(PAYLOAD, REFERENCE)
