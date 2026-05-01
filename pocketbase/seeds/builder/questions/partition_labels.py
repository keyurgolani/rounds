"""Partition Labels — Medium. Greedy / Two Pointers / Hash Map.

The classic 'expand a window until every character seen so far is fully
contained' greedy. The trick: precompute each letter's *last* index, then
sweep left-to-right extending the window's right edge to `max(last[c])`
for every character `c` seen. When `i` hits that edge, snap off a
partition. O(n) time, O(26) space — a beautiful one-pass greedy.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Partition Labels",
    "difficulty": "Medium",
    "description": (
        "You are given a string `s`. We want to partition the string into as many parts as possible so "
        "that each letter appears in at most one part.\n\n"
        "Note that the partition is done so that after concatenating all the parts in order, the "
        "resultant string should be `s`.\n\n"
        "Return a list of integers representing the size of these parts.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"ababcbacadefegdehijhklij\"`\n"
        "- Output: `[9,7,8]`\n"
        "- Explanation: The partition is `\"ababcbaca\"`, `\"defegde\"`, `\"hijhklij\"`. "
        "A partition like `\"ababcbacadefegde\"`, `\"hijhklij\"` is incorrect, because it splits `s` into "
        "fewer parts.\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"eccbbbbdec\"`\n"
        "- Output: `[10]`\n"
        "- Explanation: Every letter's first and last occurrence span the entire string, so the only "
        "valid partition is the whole string."
    ),
    "hints": [
        "Brute force: try every split point and check uniqueness — exponential. Don't.",
        "Key insight: a partition must extend at least to the *last* occurrence of every character it contains. Precompute `last[c]` for each character in one pass.",
        "Walk left-to-right. Maintain a running `end = max(end, last[s[i]])` — the furthest index any seen-so-far character demands.",
        "When `i == end`, every character in the current window is fully contained → emit `end - start + 1` and reset `start = i + 1`.",
        "Two passes total: one to build `last`, one to sweep. Constant extra space (26 lowercase letters).",
    ],
    "constraints": [
        "1 <= s.length <= 500",
        "s consists of lowercase English letters",
        "Each part's letters appear in no other part",
    ],
    "starter_code": {
        "python": "def partition_labels(s):\n    # Your code here\n    pass",
        "javascript": "function partitionLabels(s) {\n    // Your code here\n}",
        "java": "public List<Integer> partitionLabels(String s) {\n    // Your code here\n    return null;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\"ababcbacadefegdehijhklij\", \"eccbbbbdec\", \"abc\"]\n"
            "    for s in cases:\n"
            "        print(f\"partition_labels({s!r}) = {partition_labels(s)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\"ababcbacadefegdehijhklij\", \"eccbbbbdec\", \"abc\"].forEach(s =>\n"
            "    console.log(`partitionLabels(${JSON.stringify(s)}) =`, partitionLabels(s))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.List;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.partitionLabels(\"ababcbacadefegdehijhklij\"));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"s": "ababcbacadefegdehijhklij"}, "expected": [9, 7, 8],
         "description": "Classic LeetCode example — three partitions",
         "tags": ["basic"]},
        {"input": {"s": "eccbbbbdec"}, "expected": [10],
         "description": "Second LeetCode example — entire string is one partition",
         "tags": ["basic"]},
        {"input": {"s": "a"}, "expected": [1],
         "description": "Single character", "tags": ["edge"]},
        {"input": {"s": "aaaaaa"}, "expected": [6],
         "description": "All same character — one partition",
         "tags": ["edge"]},
        {"input": {"s": "abcdef"}, "expected": [1, 1, 1, 1, 1, 1],
         "description": "All distinct chars — every char is its own part",
         "tags": ["edge"]},
        {"input": {"s": "aabbcc"}, "expected": [2, 2, 2],
         "description": "Three non-overlapping pairs — three parts",
         "tags": ["basic"]},
        {"input": {"s": "abcabc"}, "expected": [6],
         "description": "Nested overlap — every letter spans the whole string",
         "tags": ["tricky"]},
        {"input": {"s": "abadcdc"}, "expected": [3, 4],
         "description": "First three chars share `a`; last four interleave `d` and `c`",
         "tags": ["tricky"]},
        {"input": {"s": "qiejxqfnqceocmy"}, "expected": [13, 1, 1],
         "description": "Long-overlap window followed by two singletons",
         "tags": ["tricky"]},
        {"input": {"s": "ab"}, "expected": [1, 1],
         "description": "Two distinct chars — two singletons",
         "tags": ["edge"]},
        {"input": {"s": "adcgbfebfbebbeicdgjgejbidccdicggefbbchedgfdihdgfihdjcehcfbhhgidhggfijfgbhgjidehbfccbhcdeibffiiideeaz"},
         "expected": [99, 1],
         "description": "Long string — first 99 chars chained by repeating `a`, lone `z` is its own part",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Last-Occurrence Map (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1) — at most 26 entries for lowercase English",
            "description": (
                "Two passes. First pass: record `last[c]` — the rightmost index where each character "
                "appears. Second pass: walk i = 0..n-1 keeping `start` (current partition's left edge) and "
                "`end` (current required right edge = max of last[s[j]] for all j ≤ i). When `i == end`, "
                "every character introduced so far is fully contained, so emit `end - start + 1` and reset "
                "`start = i + 1`."
            ),
            "code": {
                "python": (
                    "def partition_labels(s):\n"
                    "    last = {c: i for i, c in enumerate(s)}\n"
                    "    result = []\n"
                    "    start = end = 0\n"
                    "    for i, c in enumerate(s):\n"
                    "        if last[c] > end:\n"
                    "            end = last[c]\n"
                    "        if i == end:\n"
                    "            result.append(end - start + 1)\n"
                    "            start = i + 1\n"
                    "    return result"
                ),
                "javascript": (
                    "function partitionLabels(s) {\n"
                    "    const last = {};\n"
                    "    for (let i = 0; i < s.length; i++) last[s[i]] = i;\n"
                    "    const result = [];\n"
                    "    let start = 0, end = 0;\n"
                    "    for (let i = 0; i < s.length; i++) {\n"
                    "        if (last[s[i]] > end) end = last[s[i]];\n"
                    "        if (i === end) {\n"
                    "            result.push(end - start + 1);\n"
                    "            start = i + 1;\n"
                    "        }\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public List<Integer> partitionLabels(String s) {\n"
                    "    int[] last = new int[26];\n"
                    "    for (int i = 0; i < s.length(); i++) last[s.charAt(i) - 'a'] = i;\n"
                    "    List<Integer> result = new ArrayList<>();\n"
                    "    int start = 0, end = 0;\n"
                    "    for (int i = 0; i < s.length(); i++) {\n"
                    "        end = Math.max(end, last[s.charAt(i) - 'a']);\n"
                    "        if (i == end) {\n"
                    "            result.add(end - start + 1);\n"
                    "            start = i + 1;\n"
                    "        }\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(n³)",
            "space_complexity": "O(n)",
            "description": (
                "For every prefix `s[start..i]`, check whether any character inside this window also "
                "appears outside it (in `s[i+1..]`). If not, snap a partition and recurse on the suffix. "
                "Cubic in the worst case (n prefixes × O(n) membership scans × O(n) outside scan). "
                "State as a baseline; never submit."
            ),
            "code": {
                "python": (
                    "def partition_labels(s):\n"
                    "    result = []\n"
                    "    start = 0\n"
                    "    while start < len(s):\n"
                    "        for end in range(start, len(s)):\n"
                    "            inside = set(s[start:end + 1])\n"
                    "            outside = set(s[end + 1:])\n"
                    "            if inside.isdisjoint(outside):\n"
                    "                result.append(end - start + 1)\n"
                    "                start = end + 1\n"
                    "                break\n"
                    "    return result"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force is O(n³) — try every split, check disjointness. State it as baseline.",
        "2. Reframe: a partition ending at index `j` is valid iff no character in `s[start..j]` reappears after `j`. The earliest valid `j` for a given `start` is `max(last[s[k]] for k in start..j)` — but that's circular until you realise it stabilises as you walk i forward.",
        "3. Precompute `last[c]` in one pass. Now for any character we encounter, we instantly know how far the current partition must extend.",
        "4. Walk left to right with `end = max(end, last[s[i]])`. The window grows monotonically; when `i` finally catches up to `end`, the window is closed and we emit it.",
        "5. Reset `start = i + 1` and repeat. Two passes total, O(n) time, O(26) space.",
        "6. Edge cases: single char (returns `[1]`), all same char (returns `[n]`), all distinct (returns `[1] * n`).",
    ],
    "tips": [
        "The pattern 'precompute last index, sweep with running max' generalises: 'merge intervals defined by first/last occurrence' is the same algorithm.",
        "If the alphabet isn't lowercase ASCII, use a hash map instead of a 26-slot array — same logic.",
        "Don't try to do it in one pass. Two passes is correct and clean; clever 'one-pass' attempts get tangled in last-occurrence ambiguity.",
        "The condition is `i == end`, not `i >= end` (end only grows, and i increments by 1, so they meet exactly).",
        "Common follow-up: 'Partition Labels II' — same problem but on arbitrary integer arrays. Replace the 26-slot array with a `defaultdict(int)`.",
        "Related: 'Merge Intervals' — once you have `(first, last)` per character, merging overlapping intervals gives the same answer (longer code, same idea).",
    ],
    "companies": ["Amazon", "Google", "Facebook", "Microsoft", "Apple"],
    "topics": ["String", "Greedy", "Two Pointers", "Hash Table"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(s):
    last = {c: i for i, c in enumerate(s)}
    result = []
    start = end = 0
    for i, c in enumerate(s):
        if last[c] > end:
            end = last[c]
        if i == end:
            result.append(end - start + 1)
            start = i + 1
    return result


register(PAYLOAD, REFERENCE)
