"""Minimum Window Substring — Hard. Sliding Window.

The canonical 'expand-then-shrink' sliding window over a frequency
counter. The trick is the `formed` / `required` accounting: you only
shrink while the window is *still valid*, and you only update the
answer at the moment a character's count first matches what `t`
needs. Once you internalise the have/need pattern, every variant
('Permutation in String', 'Find All Anagrams', 'Smallest Subarray
Covering K Distinct') falls out of the same template.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Minimum Window Substring",
    "difficulty": "Hard",
    "description": (
        "Given two strings `s` and `t`, return **the minimum window substring of `s`** such that every "
        "character in `t` (including duplicates) is included in the window. If there is no such substring, "
        "return the empty string `\"\"`.\n\n"
        "If multiple windows of the same minimum length exist, return the **leftmost** one.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"ADOBECODEBANC\"`, `t = \"ABC\"`\n"
        "- Output: `\"BANC\"`\n"
        "- Explanation: The substring `\"BANC\"` contains `'A'`, `'B'`, and `'C'` from `t`.\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"a\"`, `t = \"a\"`\n"
        "- Output: `\"a\"`\n"
        "- Explanation: The entire string `s` is the minimum window.\n\n"
        "**Example 3:**\n"
        "- Input: `s = \"a\"`, `t = \"aa\"`\n"
        "- Output: `\"\"`\n"
        "- Explanation: Both `'a'`s from `t` must appear in the window. Since `s` only has one `'a'`, no "
        "valid window exists."
    ),
    "hints": [
        "Sliding window: expand the right edge until the window contains everything `t` needs, then shrink "
        "the left edge as far as possible while keeping the window valid. Repeat.",
        "Maintain a `need` counter (frequency of each char in `t`) and a `have` counter (frequency of each "
        "char currently inside the window).",
        "Track a scalar `formed` = how many distinct characters in the window currently meet their required "
        "count. The window is valid exactly when `formed == len(need)`. Avoid comparing the two counters "
        "directly on every step — that's O(alphabet) per move.",
        "Only update the best answer *while the window is valid*, after each successful shrink. Record "
        "`(window_length, left_index)` and reconstruct the substring at the end.",
        "Characters not in `t` are still added to `have`, but they never affect `formed` — so the window "
        "naturally drags them along until they fall off the left.",
    ],
    "constraints": [
        "1 <= s.length, t.length <= 10⁵",
        "`s` and `t` consist of uppercase and lowercase English letters.",
        "Return the leftmost minimum window if there are ties.",
    ],
    "starter_code": {
        "python": "def min_window(s, t):\n    # Your code here\n    pass",
        "javascript": "function minWindow(s, t) {\n    // Your code here\n}",
        "java": "public String minWindow(String s, String t) {\n    // Your code here\n    return \"\";\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(\"ADOBECODEBANC\", \"ABC\"), (\"a\", \"a\"), (\"a\", \"aa\")]\n"
            "    for s, t in cases:\n"
            "        print(f\"min_window({s!r}, {t!r}) = {min_window(s, t)!r}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[\"ADOBECODEBANC\", \"ABC\"], [\"a\", \"a\"], [\"a\", \"aa\"]].forEach(([s, t]) =>\n"
            "    console.log(`minWindow(${JSON.stringify(s)}, ${JSON.stringify(t)}) =`, minWindow(s, t))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.minWindow(\"ADOBECODEBANC\", \"ABC\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "ADOBECODEBANC", "t": "ABC"}, "expected": "BANC",
         "description": "Classic example — minimum window is at the tail", "tags": ["basic"]},
        {"input": {"s": "a", "t": "a"}, "expected": "a",
         "description": "Single-char `t` matches single-char `s`", "tags": ["edge"]},
        {"input": {"s": "ABC", "t": "ABC"}, "expected": "ABC",
         "description": "`t` equals `s` — entire string is the window", "tags": ["edge"]},
        {"input": {"s": "a", "t": "aa"}, "expected": "",
         "description": "`t` longer than `s` — impossible", "tags": ["edge"]},
        {"input": {"s": "aa", "t": "aa"}, "expected": "aa",
         "description": "Duplicates in `t` — must include both `'a'`s", "tags": ["tricky"]},
        {"input": {"s": "aaflslflsldkalskaaa", "t": "aaa"}, "expected": "aaa",
         "description": "Three `'a'`s required — only the trailing `'aaa'` cluster works", "tags": ["tricky"]},
        {"input": {"s": "ABAB", "t": "AB"}, "expected": "AB",
         "description": "Multiple windows of equal length — leftmost wins", "tags": ["tricky"]},
        {"input": {"s": "xyz", "t": "a"}, "expected": "",
         "description": "No matching character — empty result", "tags": ["edge"]},
        {"input": {"s": "ABCxxxx", "t": "ABC"}, "expected": "ABC",
         "description": "Window sits at the start", "tags": ["basic"]},
        {"input": {"s": "xxxxABC", "t": "ABC"}, "expected": "ABC",
         "description": "Window sits at the end", "tags": ["basic"]},
        {"input": {"s": "cabwefgewcwaefgcf", "t": "cae"}, "expected": "cwae",
         "description": "Window spans non-contiguous matches with filler chars", "tags": ["tricky"]},
        {"input": {"s": "ab", "t": "b"}, "expected": "b",
         "description": "Single-char target at end of two-char string", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Sliding Window with Have/Need Counters (Optimal)",
            "time_complexity": "O(|s| + |t|)",
            "space_complexity": "O(|s| + |t|)",
            "description": (
                "Build a `need` counter from `t`. Walk a right pointer through `s`, incrementing `have[c]`. "
                "When `have[c]` reaches `need[c]` for some required char, increment a scalar `formed`. Once "
                "`formed == len(need)`, the window is valid — shrink from the left as far as possible, "
                "decrementing `have` and `formed` as required characters fall below their threshold. Each "
                "time the window is valid, record its length and left index if it beats the best so far. "
                "Both pointers only move forward → linear time."
            ),
            "code": {
                "python": (
                    "def min_window(s, t):\n"
                    "    if not t or len(t) > len(s):\n"
                    "        return \"\"\n"
                    "    need = {}\n"
                    "    for c in t:\n"
                    "        need[c] = need.get(c, 0) + 1\n"
                    "    required = len(need)\n"
                    "    have = {}\n"
                    "    formed = 0\n"
                    "    best_len = float('inf')\n"
                    "    best_left = 0\n"
                    "    left = 0\n"
                    "    for right, c in enumerate(s):\n"
                    "        have[c] = have.get(c, 0) + 1\n"
                    "        if c in need and have[c] == need[c]:\n"
                    "            formed += 1\n"
                    "        while formed == required:\n"
                    "            if right - left + 1 < best_len:\n"
                    "                best_len = right - left + 1\n"
                    "                best_left = left\n"
                    "            lc = s[left]\n"
                    "            have[lc] -= 1\n"
                    "            if lc in need and have[lc] < need[lc]:\n"
                    "                formed -= 1\n"
                    "            left += 1\n"
                    "    return \"\" if best_len == float('inf') else s[best_left:best_left + best_len]"
                ),
                "javascript": (
                    "function minWindow(s, t) {\n"
                    "    if (!t || t.length > s.length) return \"\";\n"
                    "    const need = new Map();\n"
                    "    for (const c of t) need.set(c, (need.get(c) || 0) + 1);\n"
                    "    const required = need.size;\n"
                    "    const have = new Map();\n"
                    "    let formed = 0, left = 0, bestLen = Infinity, bestLeft = 0;\n"
                    "    for (let right = 0; right < s.length; right++) {\n"
                    "        const c = s[right];\n"
                    "        have.set(c, (have.get(c) || 0) + 1);\n"
                    "        if (need.has(c) && have.get(c) === need.get(c)) formed++;\n"
                    "        while (formed === required) {\n"
                    "            if (right - left + 1 < bestLen) {\n"
                    "                bestLen = right - left + 1;\n"
                    "                bestLeft = left;\n"
                    "            }\n"
                    "            const lc = s[left];\n"
                    "            have.set(lc, have.get(lc) - 1);\n"
                    "            if (need.has(lc) && have.get(lc) < need.get(lc)) formed--;\n"
                    "            left++;\n"
                    "        }\n"
                    "    }\n"
                    "    return bestLen === Infinity ? \"\" : s.substring(bestLeft, bestLeft + bestLen);\n"
                    "}"
                ),
                "java": (
                    "public String minWindow(String s, String t) {\n"
                    "    if (t.isEmpty() || t.length() > s.length()) return \"\";\n"
                    "    Map<Character, Integer> need = new HashMap<>();\n"
                    "    for (char c : t.toCharArray()) need.merge(c, 1, Integer::sum);\n"
                    "    int required = need.size();\n"
                    "    Map<Character, Integer> have = new HashMap<>();\n"
                    "    int formed = 0, left = 0, bestLen = Integer.MAX_VALUE, bestLeft = 0;\n"
                    "    for (int right = 0; right < s.length(); right++) {\n"
                    "        char c = s.charAt(right);\n"
                    "        have.merge(c, 1, Integer::sum);\n"
                    "        if (need.containsKey(c) && have.get(c).equals(need.get(c))) formed++;\n"
                    "        while (formed == required) {\n"
                    "            if (right - left + 1 < bestLen) {\n"
                    "                bestLen = right - left + 1;\n"
                    "                bestLeft = left;\n"
                    "            }\n"
                    "            char lc = s.charAt(left);\n"
                    "            have.merge(lc, -1, Integer::sum);\n"
                    "            if (need.containsKey(lc) && have.get(lc) < need.get(lc)) formed--;\n"
                    "            left++;\n"
                    "        }\n"
                    "    }\n"
                    "    return bestLen == Integer.MAX_VALUE ? \"\" : s.substring(bestLeft, bestLeft + bestLen);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(|s|² · |t|)",
            "space_complexity": "O(|t|)",
            "description": (
                "Enumerate every substring `s[i:j+1]` and check whether it contains every character of `t` "
                "with sufficient multiplicity. Track the leftmost minimum-length match. State this as the "
                "baseline; never submit it for |s| up to 10⁵."
            ),
            "code": {
                "python": (
                    "def min_window(s, t):\n"
                    "    if not t or len(t) > len(s):\n"
                    "        return \"\"\n"
                    "    need = {}\n"
                    "    for c in t:\n"
                    "        need[c] = need.get(c, 0) + 1\n"
                    "    best = \"\"\n"
                    "    for i in range(len(s)):\n"
                    "        for j in range(i, len(s)):\n"
                    "            window = s[i:j + 1]\n"
                    "            counts = {}\n"
                    "            for c in window:\n"
                    "                counts[c] = counts.get(c, 0) + 1\n"
                    "            if all(counts.get(c, 0) >= n for c, n in need.items()):\n"
                    "                if not best or len(window) < len(best):\n"
                    "                    best = window\n"
                    "                break\n"
                    "    return best"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force is O(n²·|t|). State it as the baseline; never submit for n up to 10⁵.",
        "2. Reframe as a sliding window: any minimum window has a definite left and right edge — both can "
        "march monotonically rightward.",
        "3. Build `need[c]` from `t`. As you expand `right`, increment `have[c]`. The window is valid when, "
        "for every required char, `have[c] >= need[c]`.",
        "4. Avoid re-comparing the whole counter each step. Track a scalar `formed` = number of distinct "
        "required chars currently satisfied. Increment when `have[c]` *first* equals `need[c]`; decrement "
        "when it drops below.",
        "5. While valid, shrink from the left and update the best (length, left_index). Stop shrinking the "
        "moment `formed` drops below `required`.",
        "6. Edge cases: empty `t` → return `\"\"` (or whatever the spec says — in this problem `t` is non-empty); "
        "`|t| > |s|` → impossible; `t` chars never appear in `s` → loop never makes the window valid → "
        "`best_len` stays at `inf` → return `\"\"`.",
        "7. Tie-breaking: 'leftmost minimum' falls out for free if you only update the answer with strict "
        "`<` (not `<=`) on length.",
    ],
    "tips": [
        "The strict `<` on length comparison is what gives you the *leftmost* minimum window. Using `<=` "
        "would give the rightmost — a subtle but common bug.",
        "Increment `formed` only when `have[c]` becomes *equal to* `need[c]`, not *greater than or equal*. "
        "Otherwise you'll over-count duplicates and falsely declare the window valid.",
        "Symmetric mistake on shrink: decrement `formed` only when `have[c]` *drops below* `need[c]` — not "
        "when it merely decreases.",
        "Characters of `s` that aren't in `t` still get counted in `have`. That's fine; they never "
        "influence `formed` because the `c in need` guard filters them out.",
        "Common follow-ups: 'Permutation in String' (window of fixed size = |t|), 'Find All Anagrams in a "
        "String' (collect all valid window starts), 'Longest Substring with At Most K Distinct Characters' "
        "(expand-shrink with a different validity predicate). All share this template.",
        "Don't reconstruct the substring inside the loop — store `(best_len, best_left)` and slice once at "
        "the end. Slicing is O(window) and called once.",
    ],
    "companies": ["Facebook", "Amazon", "Google", "Microsoft", "LinkedIn", "Uber"],
    "topics": ["Hash Table", "String", "Sliding Window"],
    "time_complexity": "O(|s| + |t|)",
    "space_complexity": "O(|s| + |t|)",
}


def REFERENCE(s, t):
    if not t or len(t) > len(s):
        return ""
    need = {}
    for c in t:
        need[c] = need.get(c, 0) + 1
    required = len(need)
    have = {}
    formed = 0
    best_len = float('inf')
    best_left = 0
    left = 0
    for right, c in enumerate(s):
        have[c] = have.get(c, 0) + 1
        if c in need and have[c] == need[c]:
            formed += 1
        while formed == required:
            if right - left + 1 < best_len:
                best_len = right - left + 1
                best_left = left
            lc = s[left]
            have[lc] -= 1
            if lc in need and have[lc] < need[lc]:
                formed -= 1
            left += 1
    return "" if best_len == float('inf') else s[best_left:best_left + best_len]


register(PAYLOAD, REFERENCE)
