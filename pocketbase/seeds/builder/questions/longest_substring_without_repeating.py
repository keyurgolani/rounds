"""Longest Substring Without Repeating Characters — Medium. Sliding Window.

The canonical sliding-window question. Two-pointer scan with a hash map of
`char → most recent index`; whenever the right pointer lands on a character
already in the window, jump the left pointer to one past its previous index.
The classic gotcha is moving the left pointer *backwards* when the previous
occurrence sits outside the current window — `max(left, last_seen[c] + 1)`
guards against it. Generalises directly to 'longest substring with at most
K distinct characters' and a family of related window problems.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Longest Substring Without Repeating Characters",
    "difficulty": "Medium",
    "description": (
        "Given a string `s`, return the length of the longest substring of `s` containing no repeated "
        "characters.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"abcabcbb\"`\n"
        "- Output: `3`\n"
        "- Explanation: The answer is `\"abc\"`, with the length of 3.\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"bbbbb\"`\n"
        "- Output: `1`\n"
        "- Explanation: The answer is `\"b\"`, with the length of 1.\n\n"
        "**Example 3:**\n"
        "- Input: `s = \"pwwkew\"`\n"
        "- Output: `3`\n"
        "- Explanation: The answer is `\"wke\"`, with the length of 3. Note that `\"pwke\"` is a "
        "*subsequence*, not a substring."
    ),
    "hints": [
        "Brute force: enumerate every substring and check uniqueness with a set → O(n³) (or O(n²) if you reuse the set across the inner loop). State it; never submit it.",
        "Sliding window: keep a window [left, right] containing only distinct characters. Expand by moving `right` one step at a time.",
        "When `s[right]` is already in the window, you need to move `left` forward — but only forward. A hash map of `char → last index` lets you jump in O(1).",
        "Critical: `left = max(left, last_seen[c] + 1)`. Without the `max`, a stale entry whose index is *behind* `left` would drag `left` backwards and corrupt the window.",
        "Generalises: 'longest substring with at most K distinct characters' uses the same skeleton — replace 'no duplicates' with a frequency map and shrink while `len(freq) > K`.",
    ],
    "constraints": [
        "0 <= s.length <= 5 * 10⁴",
        "s consists of English letters, digits, symbols and spaces.",
    ],
    "starter_code": {
        "python": "def length_of_longest_substring(s):\n    # Your code here\n    pass",
        "javascript": "function lengthOfLongestSubstring(s) {\n    // Your code here\n}",
        "java": "public int lengthOfLongestSubstring(String s) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\"abcabcbb\", \"bbbbb\", \"pwwkew\", \"\", \"dvdf\", \"tmmzuxt\"]\n"
            "    for s in cases:\n"
            "        print(f\"length_of_longest_substring({s!r}) = {length_of_longest_substring(s)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\"abcabcbb\", \"bbbbb\", \"pwwkew\", \"\", \"dvdf\", \"tmmzuxt\"].forEach(s =>\n"
            "    console.log(`lengthOfLongestSubstring(${JSON.stringify(s)}) =`, lengthOfLongestSubstring(s))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.lengthOfLongestSubstring(\"abcabcbb\"));\n"
            "        System.out.println(s.lengthOfLongestSubstring(\"tmmzuxt\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "abcabcbb"}, "expected": 3,
         "description": "Classic case — answer is \"abc\"", "tags": ["basic"]},
        {"input": {"s": "bbbbb"}, "expected": 1,
         "description": "All identical — best window is a single character", "tags": ["basic"]},
        {"input": {"s": "pwwkew"}, "expected": 3,
         "description": "Best window is \"wke\" — \"pwke\" is a subsequence, not substring", "tags": ["basic"]},
        {"input": {"s": ""}, "expected": 0,
         "description": "Empty string — return 0", "tags": ["edge"]},
        {"input": {"s": "a"}, "expected": 1,
         "description": "Single character", "tags": ["edge"]},
        {"input": {"s": "abcdefg"}, "expected": 7,
         "description": "All distinct — entire string is the answer", "tags": ["tricky"]},
        {"input": {"s": "dvdf"}, "expected": 3,
         "description": "Stale-index gotcha — at right='d', last_seen['d']=0 sits behind left=2; must NOT move left back", "tags": ["tricky"]},
        {"input": {"s": "tmmzuxt"}, "expected": 5,
         "description": "Stale-index gotcha — final 't' has last_seen=0 but the window starts at index 2; answer is \"mzuxt\"", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Sliding Window with Last-Seen Index Map (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(min(n, |Σ|))",
            "description": (
                "Walk `right` left-to-right. Maintain a hash map `last_seen[c] = i` for every character "
                "currently or previously seen. On each step, if `s[right]` was seen at an index ≥ `left`, "
                "jump `left` to `last_seen[s[right]] + 1`. Use `max(left, last_seen[c] + 1)` so a stale "
                "entry behind the window can never drag `left` backwards. Update the answer with "
                "`right - left + 1` after each step."
            ),
            "code": {
                "python": (
                    "def length_of_longest_substring(s):\n"
                    "    last_seen = {}\n"
                    "    left = 0\n"
                    "    best = 0\n"
                    "    for right, c in enumerate(s):\n"
                    "        if c in last_seen:\n"
                    "            left = max(left, last_seen[c] + 1)\n"
                    "        last_seen[c] = right\n"
                    "        best = max(best, right - left + 1)\n"
                    "    return best"
                ),
                "javascript": (
                    "function lengthOfLongestSubstring(s) {\n"
                    "    const lastSeen = new Map();\n"
                    "    let left = 0, best = 0;\n"
                    "    for (let right = 0; right < s.length; right++) {\n"
                    "        const c = s[right];\n"
                    "        if (lastSeen.has(c)) {\n"
                    "            left = Math.max(left, lastSeen.get(c) + 1);\n"
                    "        }\n"
                    "        lastSeen.set(c, right);\n"
                    "        best = Math.max(best, right - left + 1);\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "public int lengthOfLongestSubstring(String s) {\n"
                    "    java.util.Map<Character, Integer> lastSeen = new java.util.HashMap<>();\n"
                    "    int left = 0, best = 0;\n"
                    "    for (int right = 0; right < s.length(); right++) {\n"
                    "        char c = s.charAt(right);\n"
                    "        if (lastSeen.containsKey(c)) {\n"
                    "            left = Math.max(left, lastSeen.get(c) + 1);\n"
                    "        }\n"
                    "        lastSeen.put(c, right);\n"
                    "        best = Math.max(best, right - left + 1);\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sliding Window with Set (Shrink-While-Duplicate)",
            "time_complexity": "O(n)",
            "space_complexity": "O(min(n, |Σ|))",
            "description": (
                "Cleaner alternative when you don't want to think about stale indices. Maintain a set of "
                "characters currently in the window. Expand `right`; while `s[right]` is already in the "
                "set, remove `s[left]` and advance `left`. Then add `s[right]` and update the answer. "
                "Each character enters and leaves the set at most once → still O(n)."
            ),
            "code": {
                "python": (
                    "def length_of_longest_substring(s):\n"
                    "    window = set()\n"
                    "    left = 0\n"
                    "    best = 0\n"
                    "    for right, c in enumerate(s):\n"
                    "        while c in window:\n"
                    "            window.remove(s[left])\n"
                    "            left += 1\n"
                    "        window.add(c)\n"
                    "        best = max(best, right - left + 1)\n"
                    "    return best"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(min(n, |Σ|))",
            "description": (
                "For each starting index `i`, walk forward with a set until a duplicate appears; track the "
                "longest distinct run. Mention as the baseline — never submit for n up to 5·10⁴."
            ),
            "code": {
                "python": (
                    "def length_of_longest_substring(s):\n"
                    "    best = 0\n"
                    "    for i in range(len(s)):\n"
                    "        seen = set()\n"
                    "        for j in range(i, len(s)):\n"
                    "            if s[j] in seen:\n"
                    "                break\n"
                    "            seen.add(s[j])\n"
                    "        best = max(best, len(seen))\n"
                    "    return best"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force is O(n²): for every start, walk until a duplicate. State it as the baseline so the interviewer hears it before you optimise.",
        "2. Observation: when you extend the window and hit a duplicate, you don't need to restart from `i+1`. You only need to skip past the previous occurrence of the duplicate.",
        "3. Two pointers `left` and `right`. The window `s[left..right]` always has distinct characters. Track the answer as `right - left + 1` after each successful extension.",
        "4. To jump `left` in O(1) on a duplicate, store `char → most recent index` in a hash map. On seeing `s[right] = c`, candidate new `left` is `last_seen[c] + 1`.",
        "5. Critical: use `left = max(left, last_seen[c] + 1)`, NOT a bare assignment. If `last_seen[c]` is behind the current `left` (i.e. it was already evicted in spirit), assigning would move `left` BACKWARDS and re-admit duplicates. Trace `\"dvdf\"` and `\"tmmzuxt\"` to see this fire.",
        "6. After each step, update `last_seen[c] = right` and `best = max(best, right - left + 1)`. Single pass; each character is touched O(1) times.",
    ],
    "tips": [
        "The defining bug in this problem is moving `left` backwards. Always write `left = max(left, last_seen[c] + 1)` — never a plain assignment. Test against `\"dvdf\"` and `\"tmmzuxt\"`; both fail without the `max`.",
        "Two clean variants: (a) last-seen-index map with O(1) jump, or (b) set with a `while` loop that shrinks one step at a time. Pick one consistently; mixing them is where bugs creep in.",
        "Don't confuse substring with subsequence. `\"pwwkew\"` answer is 3 (`\"wke\"`), not 4 (`\"pwke\"` — that's a subsequence).",
        "Direct generalisation: 'Longest Substring with At Most K Distinct Characters' (LeetCode 340) — same skeleton, replace the duplicate check with a frequency map and shrink while `len(freq) > K`. Worth solving right after this one.",
        "If the alphabet is small and known (e.g. ASCII), swap the hash map for a fixed-size int array (`int[128]`). Same complexity, lower constant — sometimes asked as a follow-up optimisation.",
    ],
    "companies": ["Amazon", "Microsoft", "Facebook", "Apple", "Bloomberg"],
    "topics": ["String", "Sliding Window", "Hash Table"],
    "time_complexity": "O(n)",
    "space_complexity": "O(min(n, |Σ|))",
}


def REFERENCE(s):
    last_seen = {}
    left = 0
    best = 0
    for right, c in enumerate(s):
        if c in last_seen:
            left = max(left, last_seen[c] + 1)
        last_seen[c] = right
        best = max(best, right - left + 1)
    return best


register(PAYLOAD, REFERENCE)
