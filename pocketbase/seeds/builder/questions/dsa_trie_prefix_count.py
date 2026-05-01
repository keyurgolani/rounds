"""Trie Prefix Count — Easy/Medium. Trie / String.

Build a trie from a list of words; given a prefix, return how many of
the original words begin with that prefix. The classic 'count entries
in a Trie subtree' question."""
from builder.registry import register


PAYLOAD = {
    "title": "Trie Prefix Word Count",
    "difficulty": "Medium",
    "description": (
        "Given a list of words and a list of prefix queries, return the **number of words** matching each "
        "prefix. A word matches a prefix `p` iff `word` starts with `p` (or equals `p`).\n\n"
        "**Example:**\n"
        "- Input: `words = ['apple','bell','ant','bed','annotate','best','ape','bad','application','apples']`, "
        "`queries = ['a','ap','app','be']`\n"
        "- Output: `[6, 4, 3, 3]`\n\n"
        "Build the trie once, query many times — that's the win over per-query string scans."
    ),
    "hints": [
        "Build a trie. At each node, store a `count` field tallying how many words pass through this node.",
        "On insert, increment `count` at every node along the path.",
        "On query, descend by each prefix character. The count at the final node = answer. If you fall off, the answer is 0.",
        "Brute force: for each query, scan all words and count startswith — O(W·L·Q). Trie is O((W·L) build + L·Q query).",
        "Edge cases: empty prefix (returns total word count), prefix not present (returns 0), prefix equal to a word (counts that word too — still a 'starts with' match).",
    ],
    "constraints": [
        "1 <= |words| <= 10⁴",
        "1 <= |queries| <= 10⁴",
        "1 <= word.length, prefix.length <= 50",
        "Lowercase ASCII",
    ],
    "starter_code": {
        "python": "def prefix_counts(words, queries):\n    # Your code here\n    pass",
        "javascript": "function prefixCounts(words, queries) {\n    // Your code here\n}",
        "java": "public int[] prefixCounts(String[] words, String[] queries) {\n    // Your code here\n    return new int[]{};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    w = ['apple','bell','ant','bed','annotate','best','ape','bad','application','apples']\n"
            "    print(prefix_counts(w, ['a','ap','app','be']))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"words": ["apple", "bell", "ant", "bed", "annotate", "best", "ape", "bad",
                              "application", "apples"],
                    "queries": ["a", "ap", "app", "be"]},
         "expected": [6, 4, 3, 3],
         "description": "Mixed prefix lengths", "tags": ["basic"]},
        {"input": {"words": [], "queries": ["a", "b"]}, "expected": [0, 0],
         "description": "Empty word list", "tags": ["edge"]},
        {"input": {"words": ["a", "b", "c"], "queries": [""]}, "expected": [3],
         "description": "Empty prefix matches everything", "tags": ["edge"]},
        {"input": {"words": ["abc"], "queries": ["abc", "abcd", "ab", ""]},
         "expected": [1, 0, 1, 1],
         "description": "Prefix == word, prefix > word, prefix < word, empty",
         "tags": ["tricky"]},
        {"input": {"words": ["apple"] * 5, "queries": ["app"]}, "expected": [5],
         "description": "Duplicate words count separately", "tags": ["edge"]},
        {"input": {"words": ["xyz"], "queries": ["a"]}, "expected": [0],
         "description": "Prefix not present", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Trie with Subtree Counts (Optimal)",
            "time_complexity": "O(W·L) build + O(L) per query",
            "space_complexity": "O(W·L)",
            "description": (
                "Each trie node holds a `count` of words passing through. Inserts walk the trie character "
                "by character, creating nodes as needed and incrementing each node's count. Queries descend "
                "by the prefix and read the count at the final node (0 if any node along the way is missing). "
                "Beats per-query scans for large word lists or many queries."
            ),
            "code": {
                "python": (
                    "class _Node:\n"
                    "    __slots__ = ('children', 'count')\n"
                    "    def __init__(self):\n"
                    "        self.children = {}\n"
                    "        self.count = 0\n\n"
                    "def prefix_counts(words, queries):\n"
                    "    root = _Node()\n"
                    "    for w in words:\n"
                    "        node = root\n"
                    "        for ch in w:\n"
                    "            if ch not in node.children:\n"
                    "                node.children[ch] = _Node()\n"
                    "            node = node.children[ch]\n"
                    "            node.count += 1\n"
                    "    out = []\n"
                    "    for p in queries:\n"
                    "        node = root\n"
                    "        if p == '':\n"
                    "            out.append(len(words))\n"
                    "            continue\n"
                    "        ok = True\n"
                    "        for ch in p:\n"
                    "            if ch not in node.children:\n"
                    "                ok = False; break\n"
                    "            node = node.children[ch]\n"
                    "        out.append(node.count if ok else 0)\n"
                    "    return out"
                ),
                "javascript": (
                    "function prefixCounts(words, queries) {\n"
                    "    const root = { children: {}, count: 0 };\n"
                    "    for (const w of words) {\n"
                    "        let node = root;\n"
                    "        for (const ch of w) {\n"
                    "            if (!node.children[ch]) node.children[ch] = { children: {}, count: 0 };\n"
                    "            node = node.children[ch];\n"
                    "            node.count++;\n"
                    "        }\n"
                    "    }\n"
                    "    const out = [];\n"
                    "    for (const p of queries) {\n"
                    "        if (p === '') { out.push(words.length); continue; }\n"
                    "        let node = root, ok = true;\n"
                    "        for (const ch of p) {\n"
                    "            if (!node.children[ch]) { ok = false; break; }\n"
                    "            node = node.children[ch];\n"
                    "        }\n"
                    "        out.push(ok ? node.count : 0);\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sort + Binary Search",
            "time_complexity": "O(W·L·log W) build, O(L·log W) per query",
            "space_complexity": "O(W) (besides the input)",
            "description": (
                "Sort the words; for each query bisect for the lower bound of the prefix and the upper "
                "bound of `prefix + 'high-char'`. Difference is the count. Wins when you can't afford the "
                "trie's pointer overhead and queries are infrequent."
            ),
            "code": {
                "python": (
                    "from bisect import bisect_left, bisect_right\n\n"
                    "def prefix_counts(words, queries):\n"
                    "    sw = sorted(words)\n"
                    "    out = []\n"
                    "    for p in queries:\n"
                    "        if p == '':\n"
                    "            out.append(len(sw)); continue\n"
                    "        lo = bisect_left(sw, p)\n"
                    "        hi = bisect_left(sw, p + chr(0x10FFFF))\n"
                    "        out.append(hi - lo)\n"
                    "    return out"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(Q·W·L)",
            "space_complexity": "O(1)",
            "description": (
                "For each query, scan the word list and count startswith matches. Mention as the baseline; "
                "submit only if word and query counts are tiny."
            ),
            "code": {
                "python": (
                    "def prefix_counts(words, queries):\n"
                    "    return [sum(1 for w in words if w.startswith(p)) for p in queries]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: 'count words with given prefix' is a trie classic.",
        "2. State the brute-force baseline (per-query scan) and reject for repeated queries on a fixed dictionary.",
        "3. Trie build: walk each word, creating nodes as needed, increment count on every node visited.",
        "4. Trie query: walk the prefix; the count at the terminating node is the answer.",
        "5. Empty prefix matches every word — handle it explicitly or initialise root.count to len(words).",
        "6. Edge cases: empty word list, empty prefix, prefix longer than every word, duplicate words (count each).",
    ],
    "tips": [
        "Don't forget to count duplicates separately — if the input has 5 copies of 'apple', a query for 'app' returns 5.",
        "For very large alphabets (Unicode), use a dict-of-children rather than fixed-size arrays.",
        "If queries are streamed but words are batched, build the trie once and query repeatedly.",
        "Common follow-up: 'list all words with the prefix.' DFS the subtree below the matched node and yield each terminal.",
        "Common follow-up: 'count distinct words with prefix.' Track a per-word terminator flag; subtract duplicates.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Apple"],
    "topics": ["Trie", "String", "Hash Table"],
    "time_complexity": "O(W·L) build, O(L) per query",
    "space_complexity": "O(W·L)",
}


def REFERENCE(words, queries):
    class _Node:
        __slots__ = ("children", "count")

        def __init__(self):
            self.children = {}
            self.count = 0

    root = _Node()
    for w in words:
        node = root
        for ch in w:
            if ch not in node.children:
                node.children[ch] = _Node()
            node = node.children[ch]
            node.count += 1
    out = []
    for p in queries:
        if p == "":
            out.append(len(words))
            continue
        node = root
        ok = True
        for ch in p:
            if ch not in node.children:
                ok = False
                break
            node = node.children[ch]
        out.append(node.count if ok else 0)
    return out


register(PAYLOAD, REFERENCE)
