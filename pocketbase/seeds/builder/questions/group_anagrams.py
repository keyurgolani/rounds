"""Group Anagrams — Medium. Strings / Hashing.

The signature problem for "what's the right key for this hash map?"
Sorting each word gives one canonical key (O(n*k log k)); a 26-int
char-count tuple gives another (O(n*k)). Discussing both is what
separates a passable answer from a strong one.
"""
from builder.registry import register


# Validator: input groups must partition `inp['strs']` by anagram
# equivalence. Both axes of freedom (group order, within-group order)
# are canonicalised by sorting both sides as `sorted(sorted(g) for g in ...)`.
# Reuses safe builtins only — see backend/matchers.py::_SAFE_BUILTINS.
_GROUPS_VALIDATOR = (
    "lambda inp, out: ("
    "isinstance(out, list) and "
    "all(isinstance(g, list) for g in out) and "
    "sorted(sorted(g) for g in out) == sorted("
    "sorted([s for s in inp['strs'] if ''.join(sorted(s)) == k]) "
    "for k in set(''.join(sorted(s)) for s in inp['strs'])"
    ")"
    ")"
)


PAYLOAD = {
    "title": "Group Anagrams",
    "difficulty": "Medium",
    "description": (
        "Given an array of strings `strs`, group the anagrams together. "
        "You can return the answer in **any order**.\n\n"
        "**Example 1:**\n"
        "- Input: `strs = [\"eat\",\"tea\",\"tan\",\"ate\",\"nat\",\"bat\"]`\n"
        "- Output: `[[\"bat\"],[\"nat\",\"tan\"],[\"ate\",\"eat\",\"tea\"]]`\n\n"
        "**Example 2:**\n"
        "- Input: `strs = [\"\"]`\n"
        "- Output: `[[\"\"]]`\n\n"
        "**Example 3:**\n"
        "- Input: `strs = [\"a\"]`\n"
        "- Output: `[[\"a\"]]`\n\n"
        "Note: the order of groups in your output doesn't matter, and the order of words "
        "within each group doesn't matter either."
    ),
    "hints": [
        "All anagrams share something: a canonical form. Find one, group by it.",
        "Easiest canonical form: the sorted string. `'eat' → 'aet'`, `'tea' → 'aet'`. Same key → same group.",
        "Use a hash map: key = canonical form, value = list of strings that map to that key.",
        "Faster canonical form: a 26-element character-count tuple. Building it is O(k) per string vs O(k log k) for the sort.",
        "Stop when you've walked the input once. The hash map's `.values()` is your answer (in any order).",
    ],
    "constraints": [
        "1 <= strs.length <= 10⁴",
        "0 <= strs[i].length <= 100",
        "`strs[i]` consists of lowercase English letters",
    ],
    "starter_code": {
        "python": "def group_anagrams(strs):\n    # Your code here\n    pass",
        "javascript": "function groupAnagrams(strs) {\n    // Your code here\n}",
        "java": "public List<List<String>> groupAnagrams(String[] strs) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [\"eat\",\"tea\",\"tan\",\"ate\",\"nat\",\"bat\"],\n"
            "        [\"\"],\n"
            "        [\"a\"],\n"
            "    ]\n"
            "    for strs in cases:\n"
            "        print(group_anagrams(strs))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "console.log(groupAnagrams([\"eat\",\"tea\",\"tan\",\"ate\",\"nat\",\"bat\"]));\n"
            "console.log(groupAnagrams([\"\"]));\n"
            "console.log(groupAnagrams([\"a\"]));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.groupAnagrams(new String[]{\"eat\",\"tea\",\"tan\",\"ate\",\"nat\",\"bat\"}));\n"
            "    }\n"
            "}"
        ),
    },
    # The grading shape: partition the input by anagram-equivalence
    # class. Order of groups and order within each group is free, so
    # we use a validator that compares both sides as a sorted set of
    # sorted groups, which canonicalises both axes of freedom at once.
    "test_cases": [
        {
            "input": {"strs": ["eat", "tea", "tan", "ate", "nat", "bat"]},
            "expected": {
                "$match": "validator",
                "description": "groups must partition the input by anagram equivalence; group order and within-group order are free",
                "code": _GROUPS_VALIDATOR,
                "examples": [
                    [["bat"], ["nat", "tan"], ["ate", "eat", "tea"]],
                    [["eat", "tea", "ate"], ["tan", "nat"], ["bat"]],
                ],
            },
            "description": "Six words, three anagram groups",
            "tags": ["basic"],
        },
        {
            "input": {"strs": [""]},
            "expected": [[""]],
            "description": "Single empty string", "tags": ["edge"],
        },
        {
            "input": {"strs": ["a"]},
            "expected": [["a"]],
            "description": "Single one-letter word", "tags": ["edge"],
        },
        {
            "input": {"strs": ["abc", "bca", "cab", "xyz", "zyx"]},
            "expected": {
                "$match": "validator",
                "description": "groups must partition by anagram equivalence",
                "code": _GROUPS_VALIDATOR,
                "examples": [[["abc", "bca", "cab"], ["xyz", "zyx"]]],
            },
            "description": "Two groups of three and two", "tags": ["basic"],
        },
        {
            "input": {"strs": ["", "", ""]},
            "expected": [["", "", ""]],
            "description": "All empties collapse to one group", "tags": ["edge", "tricky"],
        },
        {
            "input": {"strs": ["abc", "def", "ghi"]},
            "expected": {
                "$match": "validator",
                "description": "every word distinct → each group has exactly one element",
                "code": _GROUPS_VALIDATOR,
                "examples": [[["abc"], ["def"], ["ghi"]]],
            },
            "description": "All distinct — every group has one element", "tags": ["tricky"],
        },
        {
            "input": {"strs": ["aaa", "aaa", "aaa"]},
            "expected": [["aaa", "aaa", "aaa"]],
            "description": "All identical strings collapse to one group", "tags": ["edge"],
        },
        {
            "input": {
                "strs": ["listen", "silent", "enlist", "tinsel", "stone", "tones",
                         "notes", "onset", "seton", "rat", "tar", "art"],
            },
            "expected": {
                "$match": "validator",
                "description": "12 words, three anagram families",
                "code": _GROUPS_VALIDATOR,
                "examples": [[
                    ["listen", "silent", "enlist", "tinsel"],
                    ["stone", "tones", "notes", "onset", "seton"],
                    ["rat", "tar", "art"],
                ]],
            },
            "description": "Three real-world anagram families", "tags": ["basic"],
        },
        {
            "input": {"strs": ["ab", "ba"] * 500},
            "expected": {
                "$match": "validator",
                "description": "1000 strings, all in one anagram group",
                "code": _GROUPS_VALIDATOR,
                "examples": [[["ab", "ba"] * 500]],
            },
            "description": "1000 strings, single group", "tags": ["large"],
        },
        {
            "input": {"strs": [chr(ord('a') + i % 26) + chr(ord('a') + (i + 1) % 26) for i in range(1000)]},
            "expected": {
                "$match": "validator",
                "description": "1000 generated 2-letter strings; verify groups partition the input correctly",
                "code": _GROUPS_VALIDATOR,
                "examples": [[["ab", "ba"]]],
            },
            "description": "1000 generated 2-letter strings", "tags": ["large"],
        },
    ],
    "solutions": [
        {
            "title": "Char-Count Tuple Key (Optimal)",
            "time_complexity": "O(n * k) where n is the number of strings and k is the max length",
            "space_complexity": "O(n * k) for the resulting groups",
            "description": (
                "For each string, build a 26-element tuple of character counts. Tuples are hashable "
                "and unique up to permutation, so anagrams collide on the same key. Avoids the per-string "
                "sort, dropping a log k factor."
            ),
            "code": {
                "python": (
                    "from collections import defaultdict\n\n"
                    "def group_anagrams(strs):\n"
                    "    groups = defaultdict(list)\n"
                    "    for s in strs:\n"
                    "        key = [0] * 26\n"
                    "        for ch in s:\n"
                    "            key[ord(ch) - ord('a')] += 1\n"
                    "        groups[tuple(key)].append(s)\n"
                    "    return list(groups.values())"
                ),
                "javascript": (
                    "function groupAnagrams(strs) {\n"
                    "    const groups = new Map();\n"
                    "    for (const s of strs) {\n"
                    "        const counts = new Array(26).fill(0);\n"
                    "        for (const ch of s) counts[ch.charCodeAt(0) - 97]++;\n"
                    "        const key = counts.join(',');\n"
                    "        if (!groups.has(key)) groups.set(key, []);\n"
                    "        groups.get(key).push(s);\n"
                    "    }\n"
                    "    return [...groups.values()];\n"
                    "}"
                ),
                "java": (
                    "public List<List<String>> groupAnagrams(String[] strs) {\n"
                    "    Map<String, List<String>> groups = new HashMap<>();\n"
                    "    for (String s : strs) {\n"
                    "        int[] counts = new int[26];\n"
                    "        for (char c : s.toCharArray()) counts[c - 'a']++;\n"
                    "        String key = Arrays.toString(counts);\n"
                    "        groups.computeIfAbsent(key, k -> new ArrayList<>()).add(s);\n"
                    "    }\n"
                    "    return new ArrayList<>(groups.values());\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sorted-String Key",
            "time_complexity": "O(n * k log k)",
            "space_complexity": "O(n * k)",
            "description": (
                "Use the sorted form of each string as its key. Slightly slower because of the per-string "
                "sort, but the implementation is one line shorter and easier to defend on a whiteboard."
            ),
            "code": {
                "python": (
                    "from collections import defaultdict\n\n"
                    "def group_anagrams(strs):\n"
                    "    groups = defaultdict(list)\n"
                    "    for s in strs:\n"
                    "        groups[''.join(sorted(s))].append(s)\n"
                    "    return list(groups.values())"
                ),
                "javascript": (
                    "function groupAnagrams(strs) {\n"
                    "    const groups = new Map();\n"
                    "    for (const s of strs) {\n"
                    "        const key = [...s].sort().join('');\n"
                    "        if (!groups.has(key)) groups.set(key, []);\n"
                    "        groups.get(key).push(s);\n"
                    "    }\n"
                    "    return [...groups.values()];\n"
                    "}"
                ),
                "java": (
                    "public List<List<String>> groupAnagrams(String[] strs) {\n"
                    "    Map<String, List<String>> groups = new HashMap<>();\n"
                    "    for (String s : strs) {\n"
                    "        char[] chars = s.toCharArray();\n"
                    "        Arrays.sort(chars);\n"
                    "        String key = new String(chars);\n"
                    "        groups.computeIfAbsent(key, k -> new ArrayList<>()).add(s);\n"
                    "    }\n"
                    "    return new ArrayList<>(groups.values());\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Reframe the problem: 'group by anagram equivalence' means 'group by some canonical form that's identical for all anagrams.'",
        "2. Two natural canonical forms: sorted string (intuitive) or 26-element character-count tuple (faster).",
        "3. Bucket: hash map keyed by canonical form, value is the list of original strings that map there.",
        "4. Walk the input once. Output `groups.values()` — order is unconstrained per the problem statement.",
        "5. Justify the key choice: sorted is O(k log k) per string and easy to whiteboard; tuple is O(k) but has the 'lowercase ASCII only' assumption.",
        "6. Edge cases: empty input, empty strings (one-element key), all-identical strings (single big group), all-distinct strings (every group is size 1).",
    ],
    "tips": [
        "'Group by canonical form' is a recurring pattern — same trick works for 'group equivalent expressions' or 'group rotations'. Recognise it.",
        "When the alphabet is fixed and small, the count-tuple key is faster *and* easier to extend (you can stop at the first non-zero count for 'is this empty' shortcuts).",
        "If asked about Unicode: the count-tuple no longer works (alphabet unbounded). Switch to a `dict` keyed by sorted code points, or a frozen `Counter`.",
        "Java cheat: `Arrays.toString(int[])` is a usable hash key — it's stable and fast — but for large alphabets prefer `String.valueOf` of a character array.",
        "If the interviewer adds 'preserve input order within each group', you're already covered — the loop appends in input order. Mention this proactively.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Meta", "Uber"],
    "topics": ["Hash Table", "String", "Sorting"],
    "time_complexity": "O(n * k)",
    "space_complexity": "O(n * k)",
}


def REFERENCE(strs):
    from collections import defaultdict
    groups = defaultdict(list)
    for s in strs:
        key = [0] * 26
        for ch in s:
            key[ord(ch) - ord('a')] += 1
        groups[tuple(key)].append(s)
    return list(groups.values())


register(PAYLOAD, REFERENCE)
