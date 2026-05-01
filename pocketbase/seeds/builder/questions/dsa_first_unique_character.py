"""First Unique Character in Stream — Easy. Hashing / Counting.

The two-pass count + scan classic. Worth practicing because the
follow-ups (true streaming with eviction, distinct-element queries on
the run, fixed-alphabet vs unbounded) all build on the same skeleton."""
from builder.registry import register


PAYLOAD = {
    "title": "First Unique Character in Stream",
    "difficulty": "Easy",
    "description": (
        "Given an input string `s` (or arbitrary-length stream of characters), return the **first character "
        "that does not repeat anywhere in the input**. If every character repeats, return an empty string.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"leetcode\"`\n"
        "- Output: `\"l\"`\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"loveleetcode\"`\n"
        "- Output: `\"v\"`\n\n"
        "**Example 3:**\n"
        "- Input: `s = \"aabb\"`\n"
        "- Output: `\"\"`"
    ),
    "hints": [
        "Brute force: for each character, scan the rest of the string for a duplicate. O(n²). Mention it; never submit.",
        "Two-pass: count every character (pass 1), then walk again and return the first one whose count is 1 (pass 2). O(n).",
        "If the alphabet is bounded (e.g. lowercase ASCII), use a fixed-size int[26] instead of a hash map — same big-O, much smaller constants.",
        "Streaming variant: maintain a doubly linked list of candidates plus a `char → node` map. Increment on arrival, evict from the list when count exceeds 1. Head of list = current first-unique.",
        "Edge cases: empty string, all-distinct, all-identical, single character.",
    ],
    "constraints": [
        "1 <= s.length <= 10⁵",
        "Characters are ASCII (lowercase letters in the canonical version)",
    ],
    "starter_code": {
        "python": "def first_unique_character(s):\n    # Your code here\n    pass",
        "javascript": "function firstUniqueCharacter(s) {\n    // Your code here\n}",
        "java": "public char firstUniqueCharacter(String s) {\n    // Your code here\n    return ' ';\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for s in [\"leetcode\", \"loveleetcode\", \"aabb\", \"z\"]:\n"
            "        print(f\"first_unique_character({s!r}) = {first_unique_character(s)!r}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\"leetcode\", \"loveleetcode\", \"aabb\"].forEach(s =>\n"
            "    console.log(`firstUniqueCharacter(${s}) =`, firstUniqueCharacter(s))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        for (String t : new String[]{\"leetcode\", \"loveleetcode\", \"aabb\"})\n"
            "            System.out.println(s.firstUniqueCharacter(t));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "leetcode"}, "expected": "l",
         "description": "First char is unique", "tags": ["basic"]},
        {"input": {"s": "loveleetcode"}, "expected": "v",
         "description": "First unique is mid-string", "tags": ["basic"]},
        {"input": {"s": "aabb"}, "expected": "",
         "description": "All chars repeat — empty result", "tags": ["edge"]},
        {"input": {"s": "z"}, "expected": "z",
         "description": "Single char — trivially unique", "tags": ["edge"]},
        {"input": {"s": "aabbccddeefg"}, "expected": "f",
         "description": "Long prefix of doubled pairs, unique near the end", "tags": ["tricky"]},
        {"input": {"s": "aaaaaa"}, "expected": "",
         "description": "Single repeated character", "tags": ["edge"]},
        {"input": {"s": "abcdef"}, "expected": "a",
         "description": "All distinct — first wins", "tags": ["basic"]},
        {"input": {"s": "abacabad"}, "expected": "c",
         "description": "Multiple uniques; pick the earliest", "tags": ["tricky"]},
        {"input": {"s": "a" * 50000 + "b" + "a" * 49999}, "expected": "b",
         "description": "100K chars; one unique 'b' in the middle", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Two-Pass Count (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(k) where k = alphabet size (≤26 for lowercase ASCII)",
            "description": (
                "Pass 1: count every character. Pass 2: walk the string again and return the first character "
                "whose count is exactly 1. Two linear scans, fixed-size auxiliary table."
            ),
            "code": {
                "python": (
                    "from collections import Counter\n\n"
                    "def first_unique_character(s):\n"
                    "    counts = Counter(s)\n"
                    "    for c in s:\n"
                    "        if counts[c] == 1:\n"
                    "            return c\n"
                    "    return \"\""
                ),
                "javascript": (
                    "function firstUniqueCharacter(s) {\n"
                    "    const counts = new Map();\n"
                    "    for (const c of s) counts.set(c, (counts.get(c) || 0) + 1);\n"
                    "    for (const c of s) if (counts.get(c) === 1) return c;\n"
                    "    return \"\";\n"
                    "}"
                ),
                "java": (
                    "public char firstUniqueCharacter(String s) {\n"
                    "    int[] counts = new int[128];\n"
                    "    for (int i = 0; i < s.length(); i++) counts[s.charAt(i)]++;\n"
                    "    for (int i = 0; i < s.length(); i++) if (counts[s.charAt(i)] == 1) return s.charAt(i);\n"
                    "    return ' ';\n"
                    "}"
                ),
            },
        },
        {
            "title": "Streaming with Linked List + Map",
            "time_complexity": "O(1) per arriving char (amortised)",
            "space_complexity": "O(k)",
            "description": (
                "True online variant. Maintain a doubly linked list of candidate characters in arrival order "
                "plus a `char → node` map. On each new char: if not seen, append to list; if seen exactly once, "
                "unlink and mark 'rejected'; if rejected, ignore. Head of list = current first-unique. Lets "
                "you answer the query at any prefix in O(1)."
            ),
            "code": {
                "python": (
                    "class FirstUniqueStream:\n"
                    "    def __init__(self):\n"
                    "        self.nodes = {}\n"
                    "        self.rejected = set()\n"
                    "        self.head = self.tail = None\n"
                    "    def add(self, c):\n"
                    "        if c in self.rejected:\n"
                    "            return\n"
                    "        if c in self.nodes:\n"
                    "            n = self.nodes.pop(c)\n"
                    "            if n.prev: n.prev.next = n.next\n"
                    "            else: self.head = n.next\n"
                    "            if n.next: n.next.prev = n.prev\n"
                    "            else: self.tail = n.prev\n"
                    "            self.rejected.add(c)\n"
                    "        else:\n"
                    "            n = type('N', (), {'val': c, 'prev': self.tail, 'next': None})()\n"
                    "            if self.tail: self.tail.next = n\n"
                    "            self.tail = n\n"
                    "            if not self.head: self.head = n\n"
                    "            self.nodes[c] = n\n"
                    "    def first_unique(self):\n"
                    "        return self.head.val if self.head else \"\""
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "For each character, scan the rest of the string for a duplicate. State as the baseline; "
                "never submit for n up to 10⁵."
            ),
            "code": {
                "python": (
                    "def first_unique_character(s):\n"
                    "    for i, c in enumerate(s):\n"
                    "        if c not in s[:i] and c not in s[i+1:]:\n"
                    "            return c\n"
                    "    return \"\""
                ),
            },
        },
    ],
    "thought_process": [
        "1. State the brute force out loud: 'I could scan for each char's duplicates in O(n²).' Then move on.",
        "2. Reframe: 'I just need each character's frequency, then the first one with frequency 1.' That's count + scan.",
        "3. Pick the structure: if alphabet is bounded, fixed array beats hash map on constants. Mention both.",
        "4. Walk through pass 1 (count), pass 2 (find first unique). Two clean loops.",
        "5. If asked about streaming: switch to linked-list-of-candidates. Head is your answer at any moment.",
        "6. Edge cases: empty string, all-distinct (return first), all-identical (return empty).",
    ],
    "tips": [
        "If the input is restricted to lowercase ASCII, use `int[26]` not `HashMap<Character, Integer>` — order-of-magnitude faster on constants.",
        "Don't forget to define what to return when nothing is unique. Empty string vs `None`/sentinel — pin this down with the interviewer.",
        "Common follow-up: 'now make it streaming so I can ask `firstUnique()` at any point.' → linked list + map.",
        "Common follow-up: 'now allow eviction from the stream.' → reference-count and prune the linked list when a char's count drops to 1 from 2.",
        "Java gotcha: `getOrDefault(c, 0) + 1` is the idiomatic count update; don't use `merge` here unless the team prefers it.",
    ],
    "companies": ["Amazon", "Bloomberg", "Microsoft", "Goldman Sachs"],
    "topics": ["String", "Hash Table", "Counting", "Queue"],
    "time_complexity": "O(n)",
    "space_complexity": "O(k)",
}


def REFERENCE(s):
    from collections import Counter
    counts = Counter(s)
    for c in s:
        if counts[c] == 1:
            return c
    return ""


register(PAYLOAD, REFERENCE)
