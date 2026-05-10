"""Find All Anagrams in a String — Medium. Sliding Window / Hashing.

The canonical fixed-size sliding window with character-frequency
matching. Two common implementations: comparing 26-element counters
(O(|s|·26)) and maintaining a `matches` counter that increments/
decrements as characters enter/leave the window (O(|s|+|p|)). Worth
knowing both — interviewers often push from the first to the second.
"""
from builder.registry import register, unordered_deep


PAYLOAD = {
    "title": "Find All Anagrams in a String",
    "difficulty": "Medium",
    "description": (
        "Given two strings `s` and `p`, return an array of **all the start indices** of `p`'s anagrams in "
        "`s`. You may return the answer in any order.\n\n"
        "An **anagram** is a rearrangement of all the letters of a string. Two strings are anagrams iff they "
        "are the same length and have identical character frequencies.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"cbaebabacd\", p = \"abc\"`\n"
        "- Output: `[0, 6]`\n"
        "- Explanation: The substring starting at index `0` is `\"cba\"`, which is an anagram of `\"abc\"`. "
        "The substring starting at index `6` is `\"bac\"`, which is also an anagram of `\"abc\"`.\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"abab\", p = \"ab\"`\n"
        "- Output: `[0, 1, 2]`\n"
        "- Explanation: The substrings starting at indices `0` (`\"ab\"`), `1` (`\"ba\"`), and `2` (`\"ab\"`) "
        "are all anagrams of `\"ab\"`."
    ),
    "hints": [
        "Brute force: for every window of length `|p|` in `s`, sort it and compare to sorted `p` → "
        "O(|s|·|p|·log|p|). State it; never submit it.",
        "Anagrams have identical character frequencies. Reduce the problem to: 'find every length-|p| "
        "window of `s` whose char-count matches `p`'s char-count'.",
        "Sliding window of fixed size `|p|`. Slide one character at a time: add the entering char, remove "
        "the leaving char. Compare the window's counter to `p`'s counter at each step.",
        "Comparing two 26-length arrays is O(26) per step → O(|s|·26) overall. Acceptable, but you can do "
        "better with a `matches` counter that tracks how many of the 26 letter-buckets currently agree.",
        "Edge case first: if `|p| > |s|`, return `[]` immediately. Also: only lowercase English letters per "
        "the constraints, so a fixed-size 26-array beats a hashmap.",
    ],
    "constraints": [
        "1 <= s.length, p.length <= 3 * 10⁴",
        "s and p consist of lowercase English letters.",
    ],
    "starter_code": {
        "python": "def find_anagrams(s, p):\n    # Your code here\n    pass",
        "javascript": "function findAnagrams(s, p) {\n    // Your code here\n}",
        "java": "public List<Integer> findAnagrams(String s, String p) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(\"cbaebabacd\", \"abc\"), (\"abab\", \"ab\"), (\"af\", \"be\")]\n"
            "    for s, p in cases:\n"
            "        print(f\"find_anagrams({s!r}, {p!r}) = {find_anagrams(s, p)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[\"cbaebabacd\", \"abc\"], [\"abab\", \"ab\"]].forEach(([s, p]) =>\n"
            "    console.log(`findAnagrams(${s}, ${p}) =`, findAnagrams(s, p))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.*;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution sol = new Solution();\n"
            "        System.out.println(sol.findAnagrams(\"cbaebabacd\", \"abc\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "cbaebabacd", "p": "abc"}, "expected": unordered_deep([0, 6]),
         "description": "Classic LeetCode example — two anagram windows", "tags": ["basic"]},
        {"input": {"s": "abab", "p": "ab"}, "expected": unordered_deep([0, 1, 2]),
         "description": "Overlapping anagram windows at every index", "tags": ["basic"]},
        {"input": {"s": "ab", "p": "abcd"}, "expected": [],
         "description": "|p| > |s| — no window possible", "tags": ["edge"]},
        {"input": {"s": "abc", "p": "bca"}, "expected": [0],
         "description": "|p| == |s| and they match — single window at index 0", "tags": ["edge"]},
        {"input": {"s": "abc", "p": "def"}, "expected": [],
         "description": "|p| == |s| but no shared letters — no match", "tags": ["edge"]},
        {"input": {"s": "aaaaaaaaaa", "p": "aaa"},
         "expected": unordered_deep([0, 1, 2, 3, 4, 5, 6, 7]),
         "description": "All chars the same — every starting index up to |s|-|p| qualifies",
         "tags": ["tricky"]},
        {"input": {"s": "aaa", "p": "aa"}, "expected": unordered_deep([0, 1]),
         "description": "All positions match — short overlap", "tags": ["tricky"]},
        {"input": {"s": "baa", "p": "aa"}, "expected": [1],
         "description": "Duplicates in p — must require both 'a's, not just one", "tags": ["tricky"]},
        {"input": {"s": "abacbabc", "p": "abc"}, "expected": unordered_deep([1, 2, 3, 5]),
         "description": "Multiple overlapping anagrams scattered through s", "tags": ["tricky"]},
        {"input": {"s": "a", "p": "a"}, "expected": [0],
         "description": "Single-char match", "tags": ["edge"]},
        {"input": {"s": "a", "p": "b"}, "expected": [],
         "description": "Single-char mismatch", "tags": ["edge"]},
        {"input": {"s": "z" * 30000, "p": "z" * 100},
         "expected": unordered_deep(list(range(30000 - 100 + 1))),
         "description": "Long s, every window matches — stress test for the linear solution",
         "tags": ["large"]},
        {"input": {"s": "x" * 29999 + "y", "p": "xy"}, "expected": [29998],
         "description": "Long s with exactly one match at the very end", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Sliding Window with Counter Comparison",
            "time_complexity": "O(|s| · 26)",
            "space_complexity": "O(1)",
            "description": (
                "Maintain two fixed-size counters of length 26 — one for `p`, one for the current window in "
                "`s`. Slide the window across `s`: for each new index, increment the entering character's "
                "bucket and decrement the leaving character's. After each slide, compare the two counters. "
                "Comparison is O(26), so total work is O(|s| · 26). Simple, easy to get right under pressure."
            ),
            "code": {
                "python": (
                    "def find_anagrams(s, p):\n"
                    "    if len(p) > len(s):\n"
                    "        return []\n"
                    "    p_count = [0] * 26\n"
                    "    w_count = [0] * 26\n"
                    "    for ch in p:\n"
                    "        p_count[ord(ch) - 97] += 1\n"
                    "    res = []\n"
                    "    for i, ch in enumerate(s):\n"
                    "        w_count[ord(ch) - 97] += 1\n"
                    "        if i >= len(p):\n"
                    "            w_count[ord(s[i - len(p)]) - 97] -= 1\n"
                    "        if w_count == p_count:\n"
                    "            res.append(i - len(p) + 1)\n"
                    "    return res"
                ),
                "javascript": (
                    "function findAnagrams(s, p) {\n"
                    "    if (p.length > s.length) return [];\n"
                    "    const pCount = new Array(26).fill(0);\n"
                    "    const wCount = new Array(26).fill(0);\n"
                    "    for (const ch of p) pCount[ch.charCodeAt(0) - 97]++;\n"
                    "    const res = [];\n"
                    "    for (let i = 0; i < s.length; i++) {\n"
                    "        wCount[s.charCodeAt(i) - 97]++;\n"
                    "        if (i >= p.length) wCount[s.charCodeAt(i - p.length) - 97]--;\n"
                    "        if (wCount.every((v, k) => v === pCount[k])) {\n"
                    "            res.push(i - p.length + 1);\n"
                    "        }\n"
                    "    }\n"
                    "    return res;\n"
                    "}"
                ),
                "java": (
                    "public List<Integer> findAnagrams(String s, String p) {\n"
                    "    List<Integer> res = new ArrayList<>();\n"
                    "    if (p.length() > s.length()) return res;\n"
                    "    int[] pCount = new int[26];\n"
                    "    int[] wCount = new int[26];\n"
                    "    for (char c : p.toCharArray()) pCount[c - 'a']++;\n"
                    "    for (int i = 0; i < s.length(); i++) {\n"
                    "        wCount[s.charAt(i) - 'a']++;\n"
                    "        if (i >= p.length()) wCount[s.charAt(i - p.length()) - 'a']--;\n"
                    "        if (Arrays.equals(wCount, pCount)) res.add(i - p.length() + 1);\n"
                    "    }\n"
                    "    return res;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sliding Window with Match-Counter",
            "time_complexity": "O(|s| + |p|)",
            "space_complexity": "O(1)",
            "description": (
                "Track a single integer `matches` — the number of letters (out of 26) whose window-count "
                "currently equals `p`'s count. When a character enters or leaves the window, update its "
                "bucket and adjust `matches` based on whether it just hit equality or just left equality. "
                "When `matches == 26`, the window is an anagram. Total work is O(|s| + |p|) with O(1) per "
                "step regardless of alphabet size constants."
            ),
            "code": {
                "python": (
                    "def find_anagrams(s, p):\n"
                    "    if len(p) > len(s):\n"
                    "        return []\n"
                    "    p_count = [0] * 26\n"
                    "    w_count = [0] * 26\n"
                    "    for ch in p:\n"
                    "        p_count[ord(ch) - 97] += 1\n"
                    "    matches = sum(1 for i in range(26) if p_count[i] == 0)\n"
                    "    res = []\n"
                    "    for i, ch in enumerate(s):\n"
                    "        idx = ord(ch) - 97\n"
                    "        w_count[idx] += 1\n"
                    "        if w_count[idx] == p_count[idx]:\n"
                    "            matches += 1\n"
                    "        elif w_count[idx] == p_count[idx] + 1:\n"
                    "            matches -= 1\n"
                    "        if i >= len(p):\n"
                    "            out = ord(s[i - len(p)]) - 97\n"
                    "            w_count[out] -= 1\n"
                    "            if w_count[out] == p_count[out]:\n"
                    "                matches += 1\n"
                    "            elif w_count[out] == p_count[out] - 1:\n"
                    "                matches -= 1\n"
                    "        if matches == 26:\n"
                    "            res.append(i - len(p) + 1)\n"
                    "    return res"
                ),
                "javascript": (
                    "function findAnagrams(s, p) {\n"
                    "    if (p.length > s.length) return [];\n"
                    "    const pCount = new Array(26).fill(0);\n"
                    "    const wCount = new Array(26).fill(0);\n"
                    "    for (const ch of p) pCount[ch.charCodeAt(0) - 97]++;\n"
                    "    let matches = 0;\n"
                    "    for (let k = 0; k < 26; k++) if (pCount[k] === 0) matches++;\n"
                    "    const res = [];\n"
                    "    for (let i = 0; i < s.length; i++) {\n"
                    "        const idx = s.charCodeAt(i) - 97;\n"
                    "        wCount[idx]++;\n"
                    "        if (wCount[idx] === pCount[idx]) matches++;\n"
                    "        else if (wCount[idx] === pCount[idx] + 1) matches--;\n"
                    "        if (i >= p.length) {\n"
                    "            const out = s.charCodeAt(i - p.length) - 97;\n"
                    "            wCount[out]--;\n"
                    "            if (wCount[out] === pCount[out]) matches++;\n"
                    "            else if (wCount[out] === pCount[out] - 1) matches--;\n"
                    "        }\n"
                    "        if (matches === 26) res.push(i - p.length + 1);\n"
                    "    }\n"
                    "    return res;\n"
                    "}"
                ),
                "java": (
                    "public List<Integer> findAnagrams(String s, String p) {\n"
                    "    List<Integer> res = new ArrayList<>();\n"
                    "    if (p.length() > s.length()) return res;\n"
                    "    int[] pCount = new int[26];\n"
                    "    int[] wCount = new int[26];\n"
                    "    for (char c : p.toCharArray()) pCount[c - 'a']++;\n"
                    "    int matches = 0;\n"
                    "    for (int k = 0; k < 26; k++) if (pCount[k] == 0) matches++;\n"
                    "    for (int i = 0; i < s.length(); i++) {\n"
                    "        int idx = s.charAt(i) - 'a';\n"
                    "        wCount[idx]++;\n"
                    "        if (wCount[idx] == pCount[idx]) matches++;\n"
                    "        else if (wCount[idx] == pCount[idx] + 1) matches--;\n"
                    "        if (i >= p.length()) {\n"
                    "            int out = s.charAt(i - p.length()) - 'a';\n"
                    "            wCount[out]--;\n"
                    "            if (wCount[out] == pCount[out]) matches++;\n"
                    "            else if (wCount[out] == pCount[out] - 1) matches--;\n"
                    "        }\n"
                    "        if (matches == 26) res.add(i - p.length() + 1);\n"
                    "    }\n"
                    "    return res;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. State the brute force: every window → sort → compare. O(|s|·|p|·log|p|). Don't submit it.",
        "2. Observation: anagrams have identical char frequencies. Reduce the problem to 'find windows whose count vector equals p's count vector'.",
        "3. Window size is fixed = |p|. Use a sliding window: when index `i` enters, increment its bucket; when index `i - |p|` leaves, decrement.",
        "4. Compare the two 26-length vectors at each step — O(26) per slide → O(|s|·26) overall. This is the easy version to get right.",
        "5. Optimisation: maintain an integer `matches` tracking how many of the 26 buckets currently agree with p's. Update `matches` in O(1) per char enter/leave by checking the before/after relationship to p's bucket. When `matches == 26`, we have an anagram.",
        "6. Edge case: if `|p| > |s|`, return `[]` immediately — there are no windows to check.",
    ],
    "tips": [
        "Use a 26-int array, not a hashmap — the constraint says lowercase English letters, so fixed-size beats `defaultdict(int)` on both speed and simplicity.",
        "When the window grows to size `|p|`, that's when you start emitting indices. Don't off-by-one this; the first valid start index is `i - |p| + 1` once `i >= |p| - 1`.",
        "For the match-counter optimisation, the trick is: a bucket only just achieved equality if it now equals `p_count[idx]` (and was just one off before). Use `==` checks against `p_count[idx]` and `p_count[idx] ± 1`.",
        "Common bug: forgetting to handle the symmetric case for the *leaving* character. When a char leaves, its bucket can also gain or lose equality with p's bucket.",
        "Mention that the same template handles 'Permutation in String' (LC 567) — return on first match instead of collecting all.",
    ],
    "companies": ["Amazon", "Facebook", "Microsoft", "Google", "Bloomberg"],
    "topics": ["Hash Table", "String", "Sliding Window"],
    "time_complexity": "O(|s| + |p|)",
    "space_complexity": "O(1)",
}


def REFERENCE(s, p):
    if len(p) > len(s):
        return []
    p_count = [0] * 26
    w_count = [0] * 26
    for ch in p:
        p_count[ord(ch) - 97] += 1
    matches = sum(1 for i in range(26) if p_count[i] == 0)
    res = []
    for i, ch in enumerate(s):
        idx = ord(ch) - 97
        w_count[idx] += 1
        if w_count[idx] == p_count[idx]:
            matches += 1
        elif w_count[idx] == p_count[idx] + 1:
            matches -= 1
        if i >= len(p):
            out = ord(s[i - len(p)]) - 97
            w_count[out] -= 1
            if w_count[out] == p_count[out]:
                matches += 1
            elif w_count[out] == p_count[out] - 1:
                matches -= 1
        if matches == 26:
            res.append(i - len(p) + 1)
    return sorted(res)


register(PAYLOAD, REFERENCE)
