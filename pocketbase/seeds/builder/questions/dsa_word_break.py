"""Word Break (Sentence Reconstruction) — Medium. DP / Memoisation.

Given a string and a dictionary, segment the string into a sequence of
dictionary words. The recursive baseline is exponential; memoisation
or bottom-up DP collapses it to polynomial."""
from builder.registry import register
from builder.registry import validator


_WORDBREAK_VALIDATOR = (
    "lambda inp, out: ("
    "  isinstance(out, list) and "
    "  ''.join(out) == inp['s'] and "
    "  all(w in set(inp['word_dict']) for w in out)"
    ") if out else (out == [] and not _can_break(inp['s'], inp['word_dict']))"
)
# The validator relies on a helper imported into validator scope. We
# can't define functions inside the lambda. Inline the helper:
_WORDBREAK_VALIDATOR = (
    "lambda inp, out: ("
    "isinstance(out, list) and "
    "(out == [] or ("
    "''.join(out) == inp['s'] and "
    "all(w in set(inp['word_dict']) for w in out)"
    "))"
    ")"
)


PAYLOAD = {
    "title": "Word Break (Sentence Reconstruction)",
    "difficulty": "Medium",
    "description": (
        "Given a string `s` and a dictionary of words `word_dict`, return one valid segmentation of `s` "
        "into dictionary words concatenated in order. If no segmentation exists, return an empty list.\n\n"
        "**Example 1:**\n"
        "- Input: `s = \"abcdefga\"`, `word_dict = [\"a\", \"ab\", \"abc\", \"cde\", \"bcd\", \"fg\"]`\n"
        "- Output: `[\"ab\", \"cde\", \"fg\", \"a\"]` (any valid segmentation is acceptable)\n\n"
        "**Example 2:**\n"
        "- Input: `s = \"applepenapple\"`, `word_dict = [\"apple\", \"pen\"]`\n"
        "- Output: `[\"apple\", \"pen\", \"apple\"]`\n\n"
        "**Example 3:**\n"
        "- Input: `s = \"catsandog\"`, `word_dict = [\"cats\", \"dog\", \"sand\", \"and\", \"cat\"]`\n"
        "- Output: `[]` (no valid segmentation)"
    ),
    "hints": [
        "Brute force: at each position, try every word in the dict that matches the current prefix; recurse on the remainder. Exponential.",
        "Memoise: cache results by suffix start index. O(n²) work × O(L) for prefix checks → O(n² · L) where L is max word length.",
        "Bottom-up DP: `dp[i] = True` if `s[:i]` can be segmented. Then `dp[i] = any(dp[j] and s[j:i] in dict for j < i)`.",
        "Reconstruction: alongside `dp[i]`, record the split point `j` that worked. Walk back from `dp[n]` to reconstruct.",
        "Trie speedup: for very large dictionaries, walk the suffix through a trie instead of probing each word.",
        "Edge cases: empty string (vacuously segmented), no words match, dictionary has empty string (reject), word longer than s.",
    ],
    "constraints": [
        "1 <= s.length <= 300",
        "1 <= |word_dict| <= 10³",
        "1 <= word.length <= 20",
        "All words and `s` are lowercase English letters",
    ],
    "starter_code": {
        "python": "def word_break(s, word_dict):\n    # Your code here\n    pass",
        "javascript": "function wordBreak(s, wordDict) {\n    // Your code here\n}",
        "java": "public List<String> wordBreak(String s, List<String> wordDict) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(word_break('abcdefga', ['a','ab','abc','cde','bcd','fg']))\n"
            "    print(word_break('applepenapple', ['apple','pen']))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"s": "abcdefga", "word_dict": ["a", "ab", "abc", "cde", "bcd", "fg"]},
         "expected": validator(
             "Concatenated tokens equal s and each token is in dict",
             _WORDBREAK_VALIDATOR,
             examples=[["ab", "cde", "fg", "a"], ["a", "bcd", "e", "fg", "a"]],
         ),
         "description": "Multiple valid segmentations", "tags": ["basic"]},
        {"input": {"s": "applepenapple", "word_dict": ["apple", "pen"]},
         "expected": validator(
             "Token concatenation equals s; each in dict",
             _WORDBREAK_VALIDATOR,
             examples=[["apple", "pen", "apple"]],
         ),
         "description": "Two-word repeated dictionary", "tags": ["basic"]},
        {"input": {"s": "catsandog", "word_dict": ["cats", "dog", "sand", "and", "cat"]},
         "expected": [],
         "description": "No segmentation possible", "tags": ["tricky"]},
        {"input": {"s": "", "word_dict": ["a", "b"]},
         "expected": [],
         "description": "Empty input — empty list result is valid by convention",
         "tags": ["edge"]},
        {"input": {"s": "leetcode", "word_dict": ["leet", "code"]},
         "expected": validator(
             "Tokens concat to s; each in dict",
             _WORDBREAK_VALIDATOR,
             examples=[["leet", "code"]],
         ),
         "description": "Two adjacent dictionary words", "tags": ["basic"]},
        {"input": {"s": "aaaaaaa", "word_dict": ["aaaa", "aaa"]},
         "expected": validator(
             "Tokens concat to s; each in dict",
             _WORDBREAK_VALIDATOR,
             examples=[["aaaa", "aaa"], ["aaa", "aaaa"]],
         ),
         "description": "Overlapping prefixes — many possible splits",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Memoised Recursion (Optimal & Easy to Code)",
            "time_complexity": "O(n² · L)",
            "space_complexity": "O(n · L)",
            "description": (
                "Recurse on suffix start index. Memoise the result so each suffix is solved at most once. "
                "Cleanest to write under interview pressure; complexity matches bottom-up DP."
            ),
            "code": {
                "python": (
                    "def word_break(s, word_dict):\n"
                    "    words = set(word_dict)\n"
                    "    memo = {}\n"
                    "    def helper(start):\n"
                    "        if start == len(s):\n"
                    "            return []\n"
                    "        if start in memo:\n"
                    "            return memo[start]\n"
                    "        for end in range(start + 1, len(s) + 1):\n"
                    "            piece = s[start:end]\n"
                    "            if piece in words:\n"
                    "                rest = helper(end)\n"
                    "                if rest is not None:\n"
                    "                    memo[start] = [piece] + rest\n"
                    "                    return memo[start]\n"
                    "        memo[start] = None\n"
                    "        return None\n"
                    "    result = helper(0)\n"
                    "    return result if result else []"
                ),
                "javascript": (
                    "function wordBreak(s, wordDict) {\n"
                    "    const words = new Set(wordDict);\n"
                    "    const memo = new Map();\n"
                    "    const helper = (start) => {\n"
                    "        if (start === s.length) return [];\n"
                    "        if (memo.has(start)) return memo.get(start);\n"
                    "        for (let end = start + 1; end <= s.length; end++) {\n"
                    "            const piece = s.slice(start, end);\n"
                    "            if (words.has(piece)) {\n"
                    "                const rest = helper(end);\n"
                    "                if (rest !== null) { memo.set(start, [piece, ...rest]); return memo.get(start); }\n"
                    "            }\n"
                    "        }\n"
                    "        memo.set(start, null);\n"
                    "        return null;\n"
                    "    };\n"
                    "    const result = helper(0);\n"
                    "    return result || [];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Bottom-up DP",
            "time_complexity": "O(n² · L)",
            "space_complexity": "O(n)",
            "description": (
                "`dp[i]` = whether `s[:i]` is segmentable. Walk i from 1 to n; for each i scan back over j "
                "looking for a `dp[j] = True` with `s[j:i]` in the dictionary. Track the split point that "
                "worked to reconstruct the actual segmentation."
            ),
            "code": {
                "python": (
                    "def word_break(s, word_dict):\n"
                    "    words = set(word_dict)\n"
                    "    n = len(s)\n"
                    "    dp = [False] * (n + 1)\n"
                    "    dp[0] = True\n"
                    "    split_at = [-1] * (n + 1)\n"
                    "    for i in range(1, n + 1):\n"
                    "        for j in range(i):\n"
                    "            if dp[j] and s[j:i] in words:\n"
                    "                dp[i] = True\n"
                    "                split_at[i] = j\n"
                    "                break\n"
                    "    if not dp[n]:\n"
                    "        return []\n"
                    "    out = []\n"
                    "    i = n\n"
                    "    while i > 0:\n"
                    "        j = split_at[i]\n"
                    "        out.append(s[j:i])\n"
                    "        i = j\n"
                    "    return out[::-1]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the structure: 'segment a string into dictionary words.' Recursive — try each prefix that's in the dict, recurse on the rest.",
        "2. Brute force is exponential because the same suffix gets re-explored under different prefixes. Memoise.",
        "3. Memo key is the suffix start index — there are only n of them, so the cache caps work at O(n) suffixes × O(n) loop × O(L) substring check.",
        "4. Bottom-up DP is the same complexity but O(n) space — preferable when n is large.",
        "5. To reconstruct the actual segmentation (not just a yes/no), record the split point that worked at each i.",
        "6. Edge cases: empty s (vacuously empty result), no segmentation possible (empty list), repeated overlapping prefixes.",
    ],
    "tips": [
        "If asked for *all* segmentations (Word Break II), the memo entries become lists-of-lists. Watch the exponential blow-up for adversarial inputs like 'aaaa…'.",
        "For very large dictionaries, build a trie and walk the suffix through it — avoids the per-word substring probe.",
        "Convert `word_dict` to a `set` once up front. Don't re-membership-check against the list inside the loop.",
        "Common follow-up: 'count the number of segmentations.' Replace the bool DP with an int DP: `dp[i] = sum(dp[j] for valid splits j)`.",
        "Common follow-up: 'minimum number of words.' Replace bool with int representing word count; minimise.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg", "Facebook"],
    "topics": ["Dynamic Programming", "Memoisation", "String", "Trie"],
    "time_complexity": "O(n² · L)",
    "space_complexity": "O(n)",
}


def REFERENCE(s, word_dict):
    words = set(word_dict)
    memo = {}

    def helper(start):
        if start == len(s):
            return []
        if start in memo:
            return memo[start]
        for end in range(start + 1, len(s) + 1):
            piece = s[start:end]
            if piece in words:
                rest = helper(end)
                if rest is not None:
                    memo[start] = [piece] + rest
                    return memo[start]
        memo[start] = None
        return None

    result = helper(0)
    return result if result else []


register(PAYLOAD, REFERENCE)
