"""Tree → First-Child / Next-Sibling Events — Medium. Trees / DFS.

Convert an N-ary tree into a flat list of (id, first_child_id,
next_sibling_id) tuples. Tests recognition of the first-child /
next-sibling representation that's also how compilers store ASTs."""
from builder.registry import register


PAYLOAD = {
    "title": "Tree to First-Child / Next-Sibling Events",
    "difficulty": "Medium",
    "description": (
        "Given an N-ary tree as a `parent → ordered list of children` map and the root id, return a list "
        "of events `[id, first_child_id_or_null, next_sibling_id_or_null]` describing the tree in "
        "first-child / next-sibling form. Emit events in pre-order (DFS).\n\n"
        "**Example:**\n"
        "```\n"
        "tree = {'A': ['B', 'C', 'D'], 'B': ['E'], 'C': [], 'D': ['F', 'G']}, root = 'A'\n"
        "Pre-order: A, B, E, C, D, F, G\n"
        "Events:\n"
        "  ['A', 'B', null]    # A's first child is B; A has no sibling\n"
        "  ['B', 'E', 'C']     # B's first child is E; B's next sibling is C\n"
        "  ['E', null, null]   # leaf, last child\n"
        "  ['C', null, 'D']    # leaf, sibling D\n"
        "  ['D', 'F', null]    # has children, last sibling\n"
        "  ['F', null, 'G']\n"
        "  ['G', null, null]\n"
        "```\n"
        "This is the canonical 'first-child / next-sibling' representation — same shape compilers use to "
        "store ASTs in fixed-size cells without per-node child arrays."
    ),
    "hints": [
        "Pre-order DFS the tree. At each node emit `[id, first_child, next_sibling]`.",
        "`first_child` = `children[0]` if it has children else null.",
        "`next_sibling` = the next entry in the parent's children list, or null if this is the last child or the root.",
        "Pass the parent's child list and the current index down so each node knows its sibling position.",
        "Edge cases: empty tree, single node (root with no children), wide tree (many siblings), deep tree (long parent chain).",
    ],
    "constraints": [
        "0 <= |tree| <= 10⁴ nodes",
    ],
    "starter_code": {
        "python": "def tree_events(tree, root):\n    # Your code here\n    pass",
        "javascript": "function treeEvents(tree, root) {\n    // Your code here\n}",
        "java": "public List<Object[]> treeEvents(Map<String, List<String>> tree, String root) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    t = {'A': ['B','C','D'], 'B': ['E'], 'C': [], 'D': ['F','G']}\n"
            "    for ev in tree_events(t, 'A'): print(ev)"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"tree": {"A": ["B", "C", "D"], "B": ["E"], "C": [], "D": ["F", "G"]},
                    "root": "A"},
         "expected": [
             ["A", "B", None],
             ["B", "E", "C"],
             ["E", None, None],
             ["C", None, "D"],
             ["D", "F", None],
             ["F", None, "G"],
             ["G", None, None],
         ],
         "description": "Standard tree from problem statement", "tags": ["basic"]},
        {"input": {"tree": {}, "root": "X"}, "expected": [],
         "description": "Empty tree (root not in tree)", "tags": ["edge"]},
        {"input": {"tree": {"R": []}, "root": "R"},
         "expected": [["R", None, None]],
         "description": "Single root, no children", "tags": ["edge"]},
        {"input": {"tree": {"R": ["A", "B", "C"]}, "root": "R"},
         "expected": [
             ["R", "A", None],
             ["A", None, "B"],
             ["B", None, "C"],
             ["C", None, None],
         ],
         "description": "Root with three flat siblings", "tags": ["basic"]},
        {"input": {"tree": {"A": ["B"], "B": ["C"], "C": ["D"]}, "root": "A"},
         "expected": [
             ["A", "B", None],
             ["B", "C", None],
             ["C", "D", None],
             ["D", None, None],
         ],
         "description": "Deep linear tree", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "DFS with Sibling Index (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h) recursion + O(n) output",
            "description": (
                "Pre-order DFS. Pass each node its parent's children list and its own index in that list "
                "so it can compute its next sibling. The first child is the head of its own children list "
                "(or null). Recurse on children in order; each returns when its subtree is fully emitted."
            ),
            "code": {
                "python": (
                    "def tree_events(tree, root):\n"
                    "    out = []\n"
                    "    if root not in tree:\n"
                    "        return out\n"
                    "    def go(node, siblings, idx):\n"
                    "        first = tree.get(node, [])[0] if tree.get(node) else None\n"
                    "        nxt = siblings[idx + 1] if idx + 1 < len(siblings) else None\n"
                    "        out.append([node, first, nxt])\n"
                    "        children = tree.get(node, [])\n"
                    "        for i, c in enumerate(children):\n"
                    "            go(c, children, i)\n"
                    "    go(root, [root], 0)\n"
                    "    return out"
                ),
                "javascript": (
                    "function treeEvents(tree, root) {\n"
                    "    const out = [];\n"
                    "    if (!(root in tree)) return out;\n"
                    "    const go = (node, siblings, idx) => {\n"
                    "        const ch = tree[node] || [];\n"
                    "        const first = ch.length ? ch[0] : null;\n"
                    "        const nxt = idx + 1 < siblings.length ? siblings[idx + 1] : null;\n"
                    "        out.push([node, first, nxt]);\n"
                    "        for (let i = 0; i < ch.length; i++) go(ch[i], ch, i);\n"
                    "    };\n"
                    "    go(root, [root], 0);\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative with Stack",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Push (node, siblings, idx) onto a stack. Pop, emit, push children in reverse order so the "
                "first child comes off the top next. Same big-O, no recursion limit risk."
            ),
            "code": {
                "python": (
                    "def tree_events(tree, root):\n"
                    "    if root not in tree:\n"
                    "        return []\n"
                    "    out = []\n"
                    "    stack = [(root, [root], 0)]\n"
                    "    while stack:\n"
                    "        node, siblings, idx = stack.pop()\n"
                    "        children = tree.get(node, [])\n"
                    "        first = children[0] if children else None\n"
                    "        nxt = siblings[idx + 1] if idx + 1 < len(siblings) else None\n"
                    "        out.append([node, first, nxt])\n"
                    "        for i in range(len(children) - 1, -1, -1):\n"
                    "            stack.append((children[i], children, i))\n"
                    "    return out"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the output format: each node carries pointers to ITS first child AND its next sibling. That's the first-child / next-sibling representation — compact, fixed-size cells.",
        "2. Pre-order DFS gives the right emission sequence: parent before children, children left to right.",
        "3. Each recursive call needs to know the parent's children list AND its own index in it (to compute next sibling).",
        "4. First child = head of own children list, or null.",
        "5. Next sibling = next entry in parent's children list, or null if last/root.",
        "6. Edge cases: empty tree, single root, linear chain, very wide root.",
    ],
    "tips": [
        "If you forget to pass the sibling list down, you'll need to compute it from the parent → which means another lookup; just thread it through the call.",
        "BFS gives the wrong order for this problem (level-by-level, not pre-order). Don't mix them up.",
        "Common follow-up: 'reconstruct the tree from the events list.' Walk the events, dispatch by id; first_child links downward, next_sibling links across.",
        "Common follow-up: 'serialise to a flat array of (id, first_child_idx, next_sibling_idx) for fixed-size cells.' Same algorithm, just translate ids to indices on emission.",
        "This is the underlying representation used by many AST libraries — recognising it is itself a senior signal.",
    ],
    "companies": ["Amazon", "Microsoft"],
    "topics": ["Tree", "DFS", "N-ary Tree", "Design"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(tree, root):
    out = []
    if root not in tree:
        return out

    def go(node, siblings, idx):
        children = tree.get(node, [])
        first = children[0] if children else None
        nxt = siblings[idx + 1] if idx + 1 < len(siblings) else None
        out.append([node, first, nxt])
        for i, c in enumerate(children):
            go(c, children, i)

    go(root, [root], 0)
    return out


register(PAYLOAD, REFERENCE)
