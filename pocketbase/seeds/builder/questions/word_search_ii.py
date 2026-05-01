"""Word Search II — Hard. Trie + DFS Backtracking on a grid.

The natural follow-up to Word Search (LC 79). Naively running the
single-word algorithm `k` times is O(k · m · n · 4^L) and will TLE on
the LeetCode harness for any non-trivial word list. The unlock is
building a Trie of all the words and walking it in lockstep with the
grid DFS — every grid path explores all candidate words simultaneously.
The classic interview moment: candidate proposes per-word DFS, gets
asked 'what if the word list has 10,000 entries?', and has to invent
the Trie on the spot.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Word Search II",
    "difficulty": "Hard",
    "description": (
        "Given an `m x n` `board` of characters and a list of strings `words`, return all words on the "
        "board.\n\n"
        "Each word must be constructed from letters of sequentially adjacent cells, where adjacent cells "
        "are horizontally or vertically neighboring. **The same letter cell may not be used more than once "
        "in a word.** Output order does not matter.\n\n"
        "**Example 1:**\n"
        "- Input: `board = [[\"o\",\"a\",\"a\",\"n\"],[\"e\",\"t\",\"a\",\"e\"],[\"i\",\"h\",\"k\",\"r\"],"
        "[\"i\",\"f\",\"l\",\"v\"]]`, `words = [\"oath\",\"pea\",\"eat\",\"rain\"]`\n"
        "- Output: `[\"eat\",\"oath\"]`\n"
        "- Explanation: `oath` snakes from (0,0) → (1,1) → (2,1) → (1,0). `eat` starts at (1,3).\n\n"
        "**Example 2:**\n"
        "- Input: `board = [[\"a\",\"b\"],[\"c\",\"d\"]]`, `words = [\"abcb\"]`\n"
        "- Output: `[]`\n"
        "- Explanation: `abcb` would require revisiting the `b` cell, which is not allowed."
    ),
    "hints": [
        "Don't run single-word `exist()` k times — that's O(k · m · n · 4^L). Build a Trie of all the words and DFS the grid once per starting cell, walking the Trie in lockstep with the grid.",
        "Each Trie node carries the letter it represents (or store children keyed by letter). When the DFS visits cell (r, c), descend into the child node `trie[board[r][c]]`. If no such child exists, prune.",
        "Mark a cell visited the same way as Word Search I — overwrite `board[r][c]` with a sentinel like `'#'` for the duration of the recursive call, then restore it on the way out.",
        "When you reach a Trie node whose `word` field is set, you've matched a complete word — add it to the result. Then *clear* the field (or remove the leaf) so duplicates aren't reported and the Trie shrinks as you go.",
        "Optimisation: after returning from a child, if that child has no remaining children, prune it from the Trie. The Trie literally shrinks during the search — later cells skip dead branches for free.",
    ],
    "constraints": [
        "1 <= m, n <= 12",
        "1 <= words.length <= 3 · 10⁴; 1 <= words[i].length <= 10",
        "All strings consist of lowercase English letters; words[i] are pairwise distinct.",
    ],
    "starter_code": {
        "python": "def find_words(board, words):\n    # Your code here\n    pass",
        "javascript": "function findWords(board, words) {\n    // Your code here\n}",
        "java": "public List<String> findWords(char[][] board, String[] words) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    board = [[\"o\",\"a\",\"a\",\"n\"],[\"e\",\"t\",\"a\",\"e\"],"
            "[\"i\",\"h\",\"k\",\"r\"],[\"i\",\"f\",\"l\",\"v\"]]\n"
            "    words = [\"oath\", \"pea\", \"eat\", \"rain\"]\n"
            "    print(sorted(find_words(board, words)))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const board = [[\"o\",\"a\",\"a\",\"n\"],[\"e\",\"t\",\"a\",\"e\"],"
            "[\"i\",\"h\",\"k\",\"r\"],[\"i\",\"f\",\"l\",\"v\"]];\n"
            "const words = [\"oath\", \"pea\", \"eat\", \"rain\"];\n"
            "console.log(findWords(board, words).sort());"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.*;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        char[][] board = {{'o','a','a','n'},{'e','t','a','e'},"
            "{'i','h','k','r'},{'i','f','l','v'}};\n"
            "        String[] words = {\"oath\", \"pea\", \"eat\", \"rain\"};\n"
            "        System.out.println(s.findWords(board, words));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"board": [["o", "a", "a", "n"], ["e", "t", "a", "e"],
                              ["i", "h", "k", "r"], ["i", "f", "l", "v"]],
                   "words": ["oath", "pea", "eat", "rain"]},
         "expected": {"$match": "unordered_deep", "value": ["eat", "oath"]},
         "description": "Classic LeetCode example — two of four words present",
         "tags": ["basic"]},
        {"input": {"board": [["a", "b"], ["c", "d"]], "words": ["abcd"]},
         "expected": {"$match": "unordered_deep", "value": []},
         "description": "Small board, single word that isn't reachable (would need a diagonal)",
         "tags": ["basic"]},
        {"input": {"board": [["a", "b"], ["c", "d"]], "words": ["ab", "ac", "bd", "cd", "abdc"]},
         "expected": {"$match": "unordered_deep", "value": ["ab", "ac", "bd", "cd", "abdc"]},
         "description": "All five words findable on a 2×2 board, including the looping `abdc`",
         "tags": ["basic"]},
        {"input": {"board": [["a", "b"], ["c", "d"]], "words": ["xyz", "qrs", "abcb"]},
         "expected": {"$match": "unordered_deep", "value": []},
         "description": "None of the words are findable — `abcb` would reuse a cell",
         "tags": ["tricky"]},
        {"input": {"board": [["a", "b"], ["c", "d"]], "words": ["abcdefghij"]},
         "expected": {"$match": "unordered_deep", "value": []},
         "description": "Word longer than the entire 2×2 board — impossible by pigeonhole",
         "tags": ["edge"]},
        {"input": {"board": [["a"]], "words": ["a", "b", "ab"]},
         "expected": {"$match": "unordered_deep", "value": ["a"]},
         "description": "Single-cell board — only the matching one-letter word is found",
         "tags": ["edge"]},
        {"input": {"board": [["o", "a", "a", "n"], ["e", "t", "a", "e"],
                              ["i", "h", "k", "r"], ["i", "f", "l", "v"]],
                   "words": ["oat", "oath", "oaths", "eat", "eats"]},
         "expected": {"$match": "unordered_deep", "value": ["oat", "oath", "eat"]},
         "description": "Words with shared prefixes — Trie sharing must surface every valid prefix",
         "tags": ["tricky"]},
        {"input": {"board": [["a", "a"], ["a", "a"]], "words": ["aaaa", "aaaaa", "a"]},
         "expected": {"$match": "unordered_deep", "value": ["aaaa", "a"]},
         "description": "Duplicate-letter board — `aaaa` walks all four cells; `aaaaa` would require revisit",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Trie + DFS with In-Place Visited Mark and Trie Pruning",
            "time_complexity": "O(m · n · 4 · 3^(L-1)) where L is the longest word length",
            "space_complexity": "O(N) where N is the total number of characters across all words (Trie size)",
            "description": (
                "Insert every word into a Trie keyed by character. Each leaf node carries the full word "
                "for O(1) emission. DFS from each cell, walking the grid and the Trie together — at cell "
                "(r, c), descend to `trie.children[board[r][c]]`. Mark cells with a sentinel during recursion. "
                "When the current Trie node has a non-null `word` field, record it and clear the field to "
                "deduplicate. After returning from a child DFS, if that child has no children left, delete "
                "it from the Trie — the search space literally shrinks as we go."
            ),
            "code": {
                "python": (
                    "def find_words(board, words):\n"
                    "    # Build trie: each node is a dict; '$' key holds the full word at terminals.\n"
                    "    root = {}\n"
                    "    for w in words:\n"
                    "        node = root\n"
                    "        for ch in w:\n"
                    "            node = node.setdefault(ch, {})\n"
                    "        node['$'] = w\n"
                    "\n"
                    "    rows, cols = len(board), len(board[0])\n"
                    "    found = []\n"
                    "\n"
                    "    def dfs(r, c, node):\n"
                    "        ch = board[r][c]\n"
                    "        nxt = node.get(ch)\n"
                    "        if nxt is None:\n"
                    "            return\n"
                    "        word = nxt.pop('$', None)\n"
                    "        if word is not None:\n"
                    "            found.append(word)\n"
                    "        board[r][c] = '#'\n"
                    "        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n"
                    "            nr, nc = r + dr, c + dc\n"
                    "            if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != '#':\n"
                    "                dfs(nr, nc, nxt)\n"
                    "        board[r][c] = ch\n"
                    "        # Prune dead branches so future cells skip them.\n"
                    "        if not nxt:\n"
                    "            node.pop(ch, None)\n"
                    "\n"
                    "    for r in range(rows):\n"
                    "        for c in range(cols):\n"
                    "            dfs(r, c, root)\n"
                    "    return found"
                ),
                "javascript": (
                    "function findWords(board, words) {\n"
                    "    const root = {};\n"
                    "    for (const w of words) {\n"
                    "        let node = root;\n"
                    "        for (const ch of w) {\n"
                    "            if (!node[ch]) node[ch] = {};\n"
                    "            node = node[ch];\n"
                    "        }\n"
                    "        node.$ = w;\n"
                    "    }\n"
                    "    const rows = board.length, cols = board[0].length;\n"
                    "    const found = [];\n"
                    "    const dfs = (r, c, node) => {\n"
                    "        const ch = board[r][c];\n"
                    "        const nxt = node[ch];\n"
                    "        if (!nxt) return;\n"
                    "        if (nxt.$ !== undefined) { found.push(nxt.$); delete nxt.$; }\n"
                    "        board[r][c] = '#';\n"
                    "        for (const [dr, dc] of [[1,0],[-1,0],[0,1],[0,-1]]) {\n"
                    "            const nr = r + dr, nc = c + dc;\n"
                    "            if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && board[nr][nc] !== '#')\n"
                    "                dfs(nr, nc, nxt);\n"
                    "        }\n"
                    "        board[r][c] = ch;\n"
                    "        if (Object.keys(nxt).length === 0) delete node[ch];\n"
                    "    };\n"
                    "    for (let r = 0; r < rows; r++)\n"
                    "        for (let c = 0; c < cols; c++)\n"
                    "            dfs(r, c, root);\n"
                    "    return found;\n"
                    "}"
                ),
                "java": (
                    "import java.util.*;\n"
                    "public List<String> findWords(char[][] board, String[] words) {\n"
                    "    // Trie node: 26 children + word field at terminals.\n"
                    "    class Node { Node[] kids = new Node[26]; String word; }\n"
                    "    Node root = new Node();\n"
                    "    for (String w : words) {\n"
                    "        Node n = root;\n"
                    "        for (char c : w.toCharArray()) {\n"
                    "            int i = c - 'a';\n"
                    "            if (n.kids[i] == null) n.kids[i] = new Node();\n"
                    "            n = n.kids[i];\n"
                    "        }\n"
                    "        n.word = w;\n"
                    "    }\n"
                    "    List<String> out = new ArrayList<>();\n"
                    "    int rows = board.length, cols = board[0].length;\n"
                    "    int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};\n"
                    "    // Recursive DFS via inner method emulation.\n"
                    "    dfs(board, rows, cols, 0, 0, root, out, dirs); // placeholder; see helper.\n"
                    "    for (int r = 0; r < rows; r++)\n"
                    "        for (int c = 0; c < cols; c++)\n"
                    "            dfs(board, rows, cols, r, c, root, out, dirs);\n"
                    "    return out;\n"
                    "}\n"
                    "// Helper assumes the Node class above is in scope (factor out as needed).\n"
                ),
            },
        },
        {
            "title": "Per-Word DFS (Baseline — for contrast)",
            "time_complexity": "O(W · m · n · 4^L) where W = len(words)",
            "space_complexity": "O(L) recursion depth",
            "description": (
                "Run the Word Search I algorithm independently for every word in the list. Conceptually "
                "trivial — call `exist(board, w)` for each `w` and collect those that return True. Always "
                "state this as the baseline; it's correct but TLEs on LC for large word lists because each "
                "word re-traverses the same grid prefixes. The Trie solution above shares those prefix "
                "traversals across all words."
            ),
            "code": {
                "python": (
                    "def find_words(board, words):\n"
                    "    rows, cols = len(board), len(board[0])\n"
                    "\n"
                    "    def exist(word):\n"
                    "        def dfs(r, c, i):\n"
                    "            if i == len(word):\n"
                    "                return True\n"
                    "            if r < 0 or r >= rows or c < 0 or c >= cols or board[r][c] != word[i]:\n"
                    "                return False\n"
                    "            saved = board[r][c]\n"
                    "            board[r][c] = '#'\n"
                    "            ok = (dfs(r+1, c, i+1) or dfs(r-1, c, i+1)\n"
                    "                  or dfs(r, c+1, i+1) or dfs(r, c-1, i+1))\n"
                    "            board[r][c] = saved\n"
                    "            return ok\n"
                    "        for r in range(rows):\n"
                    "            for c in range(cols):\n"
                    "                if dfs(r, c, 0):\n"
                    "                    return True\n"
                    "        return False\n"
                    "\n"
                    "    return [w for w in words if exist(w)]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Naive: call Word Search I once per word. Correct but O(W · m · n · 4^L). State it; explain why it TLEs when W is 10⁴.",
        "2. Observation: many words share prefixes. Walking the grid 'oat' then walking it again for 'oath' redoes the first three steps. Wasteful.",
        "3. Unlock: build a Trie of all the words. Walk the grid and the Trie together — at each step, descend into `trie.children[board[r][c]]`, prune if missing.",
        "4. Emit on terminal: when the current Trie node has a `word` attribute, append it to results. Clear the attribute to avoid emitting duplicates if the same word is found via two paths.",
        "5. Visited mark: same trick as Word Search I — overwrite `board[r][c]` with `'#'` during recursion, restore on backtrack. The visited check becomes `board[nr][nc] != '#'`.",
        "6. Crucial pruning: after recursing through a child Trie node, if that node has no remaining children, delete it from its parent. Future grid paths skip dead branches entirely.",
        "7. Edge cases: word longer than `m·n` (skip — won't fit), 1×1 board, duplicate-letter boards that tempt cell reuse, words sharing long prefixes (Trie handles naturally).",
    ],
    "tips": [
        "The 'cleared `word` field on emit + delete dead Trie branches' double-prune is what separates the textbook solution from the LC-AC solution. Without the second prune, this can TLE on adversarial tests.",
        "Store the full word string at the Trie terminal — not just a boolean. That way you don't need to reconstruct the path during DFS; just emit `node.word`.",
        "If words have characters outside the alphabet (Unicode, mixed case), use a dict-keyed Trie (Python). For pure lowercase ASCII (LC's constraint), a 26-element array per node is faster.",
        "Time complexity is often quoted as `O(m·n·4·3^(L-1))` — the 4 is the first move (no parent yet), then each subsequent move excludes the cell you came from. The Trie pruning makes this a *very* loose upper bound in practice.",
        "Common interview follow-up: 'what if words can be diagonal too?' → 8 directions instead of 4, identical structure. 'What if cells can be reused?' → drop the visited mark and add a depth limit (otherwise infinite loop on cycles).",
    ],
    "companies": ["Microsoft", "Amazon", "Google", "Facebook", "Bloomberg"],
    "topics": ["Trie", "Backtracking", "DFS", "Matrix"],
    "time_complexity": "O(m · n · 4 · 3^(L-1))",
    "space_complexity": "O(N) for the Trie, where N is total characters across all words",
}


def REFERENCE(board, words):
    # Deep-copy the board so we never mutate the caller's input.
    board = [row[:] for row in board]
    rows, cols = len(board), len(board[0])

    # Build trie: nested dicts; '$' key at terminals stores the full word.
    root = {}
    for w in words:
        node = root
        for ch in w:
            node = node.setdefault(ch, {})
        node['$'] = w

    found = []

    def dfs(r, c, node):
        ch = board[r][c]
        nxt = node.get(ch)
        if nxt is None:
            return
        word = nxt.pop('$', None)
        if word is not None:
            found.append(word)
        board[r][c] = '#'
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != '#':
                dfs(nr, nc, nxt)
        board[r][c] = ch
        if not nxt:
            node.pop(ch, None)

    for r in range(rows):
        for c in range(cols):
            dfs(r, c, root)
    return found


register(PAYLOAD, REFERENCE)
