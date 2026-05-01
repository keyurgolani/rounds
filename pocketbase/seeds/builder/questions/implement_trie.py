"""Implement Trie (Prefix Tree) — Medium. Tree / Design.

Classic LeetCode 208. Support insert, exact-match search, and
startsWith prefix lookup. Each node holds children (dict or fixed
26-array) plus an isEnd flag — the flag is what distinguishes a
search hit from a mere prefix match."""
from builder.registry import register


PAYLOAD = {
    "title": "Implement Trie (Prefix Tree)",
    "difficulty": "Medium",
    "description": (
        "A **trie** (pronounced 'try'), or **prefix tree**, is a tree data structure used to "
        "efficiently store and retrieve keys in a dataset of strings. It has many applications: "
        "autocomplete, spell check, IP routing, and longest-common-prefix queries.\n\n"
        "Implement the `Trie` class with three operations:\n"
        "- `Trie()` — constructs an empty trie.\n"
        "- `insert(word)` — inserts the string `word` into the trie.\n"
        "- `search(word)` — returns `true` if `word` is in the trie (i.e. was previously inserted), and `false` otherwise.\n"
        "- `startsWith(prefix)` — returns `true` if there is any previously inserted word that has `prefix` as a prefix, and `false` otherwise.\n\n"
        "**Example:**\n"
        "```\n"
        "Trie trie = new Trie();\n"
        "trie.insert(\"apple\");\n"
        "trie.search(\"apple\");     // returns true\n"
        "trie.search(\"app\");       // returns false (\"app\" was never inserted as a full word)\n"
        "trie.startsWith(\"app\");   // returns true (\"apple\" starts with \"app\")\n"
        "trie.insert(\"app\");\n"
        "trie.search(\"app\");       // returns true (now \"app\" is a full word too)\n"
        "```\n\n"
        "The key distinction: `search` requires a stored word that **ends** at the queried position "
        "(i.e. the terminal node's `isEnd` flag is set). `startsWith` only needs the path to exist."
    ),
    "hints": [
        "Each trie node stores its children — use a dict `{char: TrieNode}` for simplicity, or a fixed-size array `TrieNode[26]` for lowercase ASCII (lower constant factor, cache-friendlier).",
        "Each node also needs an `isEnd` (a.k.a. `isWord`) boolean. Without it, you can't distinguish 'apple' was inserted but 'app' was not.",
        "`insert(word)`: walk from root, creating missing children as you go; mark `isEnd = True` on the final node.",
        "`startsWith(prefix)`: walk the prefix; if any character is missing, return False. If you finish the walk, return True — `isEnd` does not matter.",
        "`search(word)`: same walk as `startsWith`, but at the end you must also check `node.isEnd`. That's the one-line difference between the two methods.",
    ],
    "constraints": [
        "1 <= word.length, prefix.length <= 2000",
        "`word` and `prefix` consist only of lowercase English letters.",
        "At most 3 * 10⁴ calls in total to `insert`, `search`, and `startsWith`.",
    ],
    "starter_code": {
        "python": (
            "class Trie:\n"
            "    def __init__(self):\n"
            "        pass\n"
            "    def insert(self, word):\n"
            "        pass\n"
            "    def search(self, word):\n"
            "        pass\n"
            "    def startsWith(self, prefix):\n"
            "        pass"
        ),
        "javascript": (
            "class Trie {\n"
            "    constructor() { /* ... */ }\n"
            "    insert(word) { /* ... */ }\n"
            "    search(word) { /* ... */ }\n"
            "    startsWith(prefix) { /* ... */ }\n"
            "}"
        ),
        "java": (
            "class Trie {\n"
            "    public Trie() {}\n"
            "    public void insert(String word) {}\n"
            "    public boolean search(String word) { return false; }\n"
            "    public boolean startsWith(String prefix) { return false; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    t = Trie()\n"
            "    t.insert(\"apple\")\n"
            "    print(t.search(\"apple\"))      # True\n"
            "    print(t.search(\"app\"))        # False\n"
            "    print(t.startsWith(\"app\"))    # True\n"
            "    t.insert(\"app\")\n"
            "    print(t.search(\"app\"))        # True"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["Trie", "insert", "search", "search", "startsWith", "insert", "search"],
                    "args": [[], ["apple"], ["apple"], ["app"], ["app"], ["app"], ["app"]]},
         "expected": [None, None, True, False, True, None, True],
         "description": "Classic LeetCode 208 sequence — prefix vs full-word distinction",
         "tags": ["basic", "leetcode"]},
        {"input": {"ops": ["Trie", "insert", "insert", "insert", "search", "search", "search", "startsWith"],
                    "args": [[], ["cat"], ["car"], ["cart"], ["cat"], ["car"], ["cart"], ["ca"]]},
         "expected": [None, None, None, None, True, True, True, True],
         "description": "Multiple words sharing a common prefix",
         "tags": ["basic"]},
        {"input": {"ops": ["Trie", "search", "startsWith"],
                    "args": [[], ["anything"], ["a"]]},
         "expected": [None, False, False],
         "description": "Empty trie — every search and startsWith returns False",
         "tags": ["edge"]},
        {"input": {"ops": ["Trie", "insert", "search", "search", "startsWith", "startsWith"],
                    "args": [[], ["hello"], ["hell"], ["helloo"], ["hell"], ["helloo"]]},
         "expected": [None, None, False, False, True, False],
         "description": "Prefix match without full-word; over-long prefix fails",
         "tags": ["edge"]},
        {"input": {"ops": ["Trie", "insert", "search", "startsWith"],
                    "args": [[], ["a"], ["a"], ["a"]]},
         "expected": [None, None, True, True],
         "description": "Single-character word",
         "tags": ["edge"]},
        {"input": {"ops": ["Trie", "insert", "search", "startsWith", "search"],
                    "args": [[], ["abcdefghijklmnopqrstuvwxyz"],
                              ["abcdefghijklmnopqrstuvwxyz"],
                              ["abcdefghijklmnop"],
                              ["abcdefghijklmnop"]]},
         "expected": [None, None, True, True, False],
         "description": "Long word — every prefix matches startsWith but not search",
         "tags": ["edge", "long"]},
        {"input": {"ops": ["Trie", "insert", "insert", "search", "search", "search", "startsWith", "startsWith"],
                    "args": [[], ["dog"], ["dogs"], ["dog"], ["dogs"], ["do"], ["do"], ["dogss"]]},
         "expected": [None, None, None, True, True, False, True, False],
         "description": "Word that is a prefix of another inserted word",
         "tags": ["basic"]},
        {"input": {"ops": ["Trie", "insert", "insert", "insert", "insert", "startsWith",
                            "search", "search", "search", "search"],
                    "args": [[], ["bat"], ["bath"], ["batch"], ["bathe"], ["ba"],
                              ["bat"], ["bath"], ["bathe"], ["batche"]]},
         "expected": [None, None, None, None, None, True, True, True, True, False],
         "description": "Family of overlapping words; one over-long search fails",
         "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Dict-of-Children Trie (Pythonic, Optimal)",
            "time_complexity": "O(L) per operation, where L is the length of the word/prefix",
            "space_complexity": "O(total characters inserted) — one node per unique path letter",
            "description": (
                "Each node holds a `children` dict mapping a single character to its child node, "
                "plus an `isEnd` flag. `insert` walks-or-creates; `search` and `startsWith` share "
                "the same walk and differ only in whether they require `isEnd` at the terminal node. "
                "Using a dict keeps the implementation alphabet-agnostic (works for unicode out of the box)."
            ),
            "code": {
                "python": (
                    "class TrieNode:\n"
                    "    __slots__ = (\"children\", \"is_end\")\n"
                    "    def __init__(self):\n"
                    "        self.children = {}\n"
                    "        self.is_end = False\n\n"
                    "class Trie:\n"
                    "    def __init__(self):\n"
                    "        self.root = TrieNode()\n\n"
                    "    def insert(self, word):\n"
                    "        node = self.root\n"
                    "        for ch in word:\n"
                    "            if ch not in node.children:\n"
                    "                node.children[ch] = TrieNode()\n"
                    "            node = node.children[ch]\n"
                    "        node.is_end = True\n\n"
                    "    def _walk(self, s):\n"
                    "        node = self.root\n"
                    "        for ch in s:\n"
                    "            nxt = node.children.get(ch)\n"
                    "            if nxt is None:\n"
                    "                return None\n"
                    "            node = nxt\n"
                    "        return node\n\n"
                    "    def search(self, word):\n"
                    "        node = self._walk(word)\n"
                    "        return node is not None and node.is_end\n\n"
                    "    def startsWith(self, prefix):\n"
                    "        return self._walk(prefix) is not None"
                ),
                "javascript": (
                    "class TrieNode {\n"
                    "    constructor() { this.children = new Map(); this.isEnd = false; }\n"
                    "}\n\n"
                    "class Trie {\n"
                    "    constructor() { this.root = new TrieNode(); }\n"
                    "    insert(word) {\n"
                    "        let node = this.root;\n"
                    "        for (const ch of word) {\n"
                    "            if (!node.children.has(ch)) node.children.set(ch, new TrieNode());\n"
                    "            node = node.children.get(ch);\n"
                    "        }\n"
                    "        node.isEnd = true;\n"
                    "    }\n"
                    "    _walk(s) {\n"
                    "        let node = this.root;\n"
                    "        for (const ch of s) {\n"
                    "            const nxt = node.children.get(ch);\n"
                    "            if (!nxt) return null;\n"
                    "            node = nxt;\n"
                    "        }\n"
                    "        return node;\n"
                    "    }\n"
                    "    search(word) { const n = this._walk(word); return !!n && n.isEnd; }\n"
                    "    startsWith(prefix) { return this._walk(prefix) !== null; }\n"
                    "}"
                ),
                "java": (
                    "class Trie {\n"
                    "    private static class Node {\n"
                    "        Map<Character, Node> children = new HashMap<>();\n"
                    "        boolean isEnd;\n"
                    "    }\n"
                    "    private final Node root = new Node();\n"
                    "    public void insert(String word) {\n"
                    "        Node node = root;\n"
                    "        for (char ch : word.toCharArray()) {\n"
                    "            node = node.children.computeIfAbsent(ch, k -> new Node());\n"
                    "        }\n"
                    "        node.isEnd = true;\n"
                    "    }\n"
                    "    private Node walk(String s) {\n"
                    "        Node node = root;\n"
                    "        for (char ch : s.toCharArray()) {\n"
                    "            node = node.children.get(ch);\n"
                    "            if (node == null) return null;\n"
                    "        }\n"
                    "        return node;\n"
                    "    }\n"
                    "    public boolean search(String word) {\n"
                    "        Node n = walk(word); return n != null && n.isEnd;\n"
                    "    }\n"
                    "    public boolean startsWith(String prefix) {\n"
                    "        return walk(prefix) != null;\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Array(26)-Children Trie (Lower Constant for ASCII)",
            "time_complexity": "O(L) per operation",
            "space_complexity": "O(26 * total nodes) — fixed branch factor",
            "description": (
                "When the alphabet is fixed (lowercase a-z), replace the dict with a `TrieNode[26]` "
                "array indexed by `ch - 'a'`. This avoids hashing on every step and is what most "
                "competitive solutions use in Java/C++. Trades higher per-node memory for faster "
                "cache-friendly traversal — typically 2-3x faster on benchmarks at the cost of "
                "alphabet flexibility."
            ),
            "code": {
                "python": (
                    "class TrieNode:\n"
                    "    __slots__ = (\"children\", \"is_end\")\n"
                    "    def __init__(self):\n"
                    "        self.children = [None] * 26\n"
                    "        self.is_end = False\n\n"
                    "class Trie:\n"
                    "    def __init__(self):\n"
                    "        self.root = TrieNode()\n\n"
                    "    def insert(self, word):\n"
                    "        node = self.root\n"
                    "        for ch in word:\n"
                    "            i = ord(ch) - 97\n"
                    "            if node.children[i] is None:\n"
                    "                node.children[i] = TrieNode()\n"
                    "            node = node.children[i]\n"
                    "        node.is_end = True\n\n"
                    "    def _walk(self, s):\n"
                    "        node = self.root\n"
                    "        for ch in s:\n"
                    "            nxt = node.children[ord(ch) - 97]\n"
                    "            if nxt is None:\n"
                    "                return None\n"
                    "            node = nxt\n"
                    "        return node\n\n"
                    "    def search(self, word):\n"
                    "        node = self._walk(word)\n"
                    "        return node is not None and node.is_end\n\n"
                    "    def startsWith(self, prefix):\n"
                    "        return self._walk(prefix) is not None"
                ),
                "java": (
                    "class Trie {\n"
                    "    private static class Node {\n"
                    "        Node[] children = new Node[26];\n"
                    "        boolean isEnd;\n"
                    "    }\n"
                    "    private final Node root = new Node();\n"
                    "    public void insert(String word) {\n"
                    "        Node node = root;\n"
                    "        for (char ch : word.toCharArray()) {\n"
                    "            int i = ch - 'a';\n"
                    "            if (node.children[i] == null) node.children[i] = new Node();\n"
                    "            node = node.children[i];\n"
                    "        }\n"
                    "        node.isEnd = true;\n"
                    "    }\n"
                    "    private Node walk(String s) {\n"
                    "        Node node = root;\n"
                    "        for (char ch : s.toCharArray()) {\n"
                    "            node = node.children[ch - 'a'];\n"
                    "            if (node == null) return null;\n"
                    "        }\n"
                    "        return node;\n"
                    "    }\n"
                    "    public boolean search(String word) {\n"
                    "        Node n = walk(word); return n != null && n.isEnd;\n"
                    "    }\n"
                    "    public boolean startsWith(String prefix) {\n"
                    "        return walk(prefix) != null;\n"
                    "    }\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Spot the structure: prefix queries on a growing dictionary → trie. Hash-set of words can't answer 'any word with this prefix' in O(L).",
        "2. Define the node: children + isEnd flag. The flag is non-negotiable; without it 'apple' inserted would falsely match search('app').",
        "3. Pick the children container: dict for flexibility (unicode, sparse), array[26] for speed on lowercase a-z. Both are O(L).",
        "4. Insert is walk-or-create. Search and startsWith share the same walk; factor it into a `_walk` helper that returns the terminal node or None.",
        "5. The differentiator: `search` requires `node.isEnd`, `startsWith` does not. Literally one boolean check apart.",
        "6. Edge cases to mention: empty trie, single-char word, word that is a prefix of another inserted word (e.g. insert 'app' after 'apple' — both must search True afterwards).",
    ],
    "tips": [
        "The interview gotcha is forgetting `isEnd`. If your search() returns True for any prefix walk, you don't have a trie — you have a prefix index.",
        "Prefer `dict` in Python for clarity in interviews; mention array[26] as the optimization if the alphabet is fixed.",
        "Use `__slots__` on TrieNode in Python — saves ~40% memory on large dictionaries (matters at 30k inserts).",
        "Common follow-up: `delete(word)`. Walk to the end, unset isEnd, then bubble back up freeing nodes whose children are empty AND whose isEnd is False.",
        "Common follow-up: '212. Word Search II' — DFS the board with a trie of target words to prune branches that don't lead anywhere. Pretty much the canonical use case.",
        "Common follow-up: 'autocomplete: return all words with prefix X.' Walk to the prefix node, then DFS collecting strings whose isEnd is True.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Facebook", "Apple", "Bloomberg", "Uber"],
    "topics": ["Trie", "Tree", "Design", "Hash Table", "String"],
    "time_complexity": "O(L) per operation, where L is the length of the word or prefix",
    "space_complexity": "O(total characters inserted)",
}


def REFERENCE(input):
    """Class-ops driver: replay the trie operation sequence."""

    class TrieNode:
        __slots__ = ("children", "is_end")

        def __init__(self):
            self.children = {}
            self.is_end = False

    class Trie:
        def __init__(self):
            self.root = TrieNode()

        def insert(self, word):
            node = self.root
            for ch in word:
                if ch not in node.children:
                    node.children[ch] = TrieNode()
                node = node.children[ch]
            node.is_end = True

        def _walk(self, s):
            node = self.root
            for ch in s:
                nxt = node.children.get(ch)
                if nxt is None:
                    return None
                node = nxt
            return node

        def search(self, word):
            node = self._walk(word)
            return node is not None and node.is_end

        def startsWith(self, prefix):
            return self._walk(prefix) is not None

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "Trie":
            instance = Trie()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


# Add the entry field for class_ops dispatch
PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "Trie",
    "constructor": {"params": []},
    "methods": [
        {"name": "insert", "params": [{"name": "word", "type": "str"}], "returns": "any"},
        {"name": "search", "params": [{"name": "word", "type": "str"}], "returns": "bool"},
        {"name": "startsWith", "params": [{"name": "prefix", "type": "str"}], "returns": "bool"},
    ],
}


register(PAYLOAD, REFERENCE)
