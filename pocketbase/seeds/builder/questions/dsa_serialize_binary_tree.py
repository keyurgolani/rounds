"""Serialize/Deserialize Binary Tree — Hard. Trees / Recursion.

Convert a binary tree to a string and back. Trick: nulls must be part
of the serialised representation, otherwise deserialisation is
ambiguous. Pre-order with explicit nulls is the canonical solution."""
from builder.registry import register


PAYLOAD = {
    "title": "Serialize and Deserialize Binary Tree",
    "difficulty": "Hard",
    "description": (
        "Design two functions: `serialize(root)` returns a string representation of a binary tree, and "
        "`deserialize(s)` reconstructs the tree from that string. The tree is an arbitrary binary tree (not "
        "a BST) — node values can repeat and have no ordering.\n\n"
        "For testing purposes, encode trees as a level-order list with `null` for missing children "
        "(LeetCode-style):\n"
        "- `[1, 2, 3, null, null, 4, 5]` represents:\n"
        "```\n"
        "    1\n"
        "   / \\\n"
        "  2   3\n"
        "     / \\\n"
        "    4   5\n"
        "```\n\n"
        "Your `serialize` should accept a level-order list and return a *string* representation. "
        "`deserialize` should take that string and return the equivalent level-order list (after a clean "
        "round-trip)."
    ),
    "hints": [
        "Pre-order DFS with explicit `null` markers serialises every binary tree uniquely.",
        "Different trees can produce the same in-order or post-order traversal — `null` markers in pre-order break the ambiguity.",
        "BFS / level-order serialisation also works (this is what LeetCode shows visually). Pick one and stick with it.",
        "Without null markers, you'd need TWO traversals (in-order + pre-order) to reconstruct uniquely — wasteful.",
        "Edge cases: empty tree (single null marker), single node, very skewed tree, very wide tree, duplicate values.",
    ],
    "constraints": [
        "0 <= node count <= 10⁴",
        "Node values are integers in a 32-bit range",
    ],
    "starter_code": {
        "python": (
            "def round_trip(level_order):\n"
            "    # serialize then deserialize; should return the input level_order (trimmed of trailing nulls)\n"
            "    pass"
        ),
        "javascript": "function roundTrip(levelOrder) {\n    // Your code here\n}",
        "java": "public List<Integer> roundTrip(List<Integer> levelOrder) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(round_trip([1, 2, 3, None, None, 4, 5]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"level_order": [1, 2, 3, None, None, 4, 5]},
         "expected": [1, 2, 3, None, None, 4, 5],
         "description": "Standard tree from problem statement", "tags": ["basic"]},
        {"input": {"level_order": []}, "expected": [],
         "description": "Empty tree", "tags": ["edge"]},
        {"input": {"level_order": [42]}, "expected": [42],
         "description": "Single node", "tags": ["edge"]},
        {"input": {"level_order": [1, 2, None, 3, None, 4]},
         "expected": [1, 2, None, 3, None, 4],
         "description": "Left-skewed tree", "tags": ["edge"]},
        {"input": {"level_order": [1, None, 2, None, 3]},
         "expected": [1, None, 2, None, 3],
         "description": "Right-skewed tree", "tags": ["edge"]},
        {"input": {"level_order": [5, 5, 5, 5, 5]},
         "expected": [5, 5, 5, 5, 5],
         "description": "Duplicate values", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Pre-order DFS with Null Markers (Canonical)",
            "time_complexity": "O(n) for both serialize and deserialize",
            "space_complexity": "O(n) for the output string + O(h) recursion",
            "description": (
                "Serialise: pre-order DFS, emitting node values (or 'N' for null) separated by commas. "
                "Deserialise: split on commas, walk the tokens with an iterator, recursively pulling the "
                "next token as the current node's value. Null tokens become null subtrees. The recursion "
                "matches the serialisation order naturally."
            ),
            "code": {
                "python": (
                    "class TreeNode:\n"
                    "    def __init__(self, val=0, left=None, right=None):\n"
                    "        self.val, self.left, self.right = val, left, right\n\n"
                    "def serialize(root):\n"
                    "    parts = []\n"
                    "    def go(n):\n"
                    "        if n is None:\n"
                    "            parts.append('N')\n"
                    "            return\n"
                    "        parts.append(str(n.val))\n"
                    "        go(n.left)\n"
                    "        go(n.right)\n"
                    "    go(root)\n"
                    "    return ','.join(parts)\n\n"
                    "def deserialize(s):\n"
                    "    it = iter(s.split(','))\n"
                    "    def go():\n"
                    "        tok = next(it)\n"
                    "        if tok == 'N':\n"
                    "            return None\n"
                    "        n = TreeNode(int(tok))\n"
                    "        n.left = go()\n"
                    "        n.right = go()\n"
                    "        return n\n"
                    "    return go()\n\n"
                    "def round_trip(level_order):\n"
                    "    root = _from_level(level_order)\n"
                    "    s = serialize(root)\n"
                    "    root2 = deserialize(s)\n"
                    "    return _to_level(root2)\n\n"
                    "def _from_level(arr):\n"
                    "    from collections import deque\n"
                    "    if not arr:\n"
                    "        return None\n"
                    "    root = TreeNode(arr[0])\n"
                    "    q = deque([root])\n"
                    "    i = 1\n"
                    "    while q and i < len(arr):\n"
                    "        n = q.popleft()\n"
                    "        if i < len(arr) and arr[i] is not None:\n"
                    "            n.left = TreeNode(arr[i]); q.append(n.left)\n"
                    "        i += 1\n"
                    "        if i < len(arr) and arr[i] is not None:\n"
                    "            n.right = TreeNode(arr[i]); q.append(n.right)\n"
                    "        i += 1\n"
                    "    return root\n\n"
                    "def _to_level(root):\n"
                    "    if root is None: return []\n"
                    "    from collections import deque\n"
                    "    out = []\n"
                    "    q = deque([root])\n"
                    "    while q:\n"
                    "        n = q.popleft()\n"
                    "        if n is None:\n"
                    "            out.append(None)\n"
                    "            continue\n"
                    "        out.append(n.val)\n"
                    "        q.append(n.left)\n"
                    "        q.append(n.right)\n"
                    "    while out and out[-1] is None:\n"
                    "        out.pop()\n"
                    "    return out"
                ),
            },
        },
        {
            "title": "Level-order BFS Serialization",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "BFS the tree, emitting values level by level (LeetCode's display format). Trailing nulls "
                "can be trimmed. Reads visually but consumes more space than pre-order on dense trees."
            ),
            "code": {
                "python": (
                    "# Sketch — produces the LeetCode-visible format directly.\n"
                    "def serialize(root):\n"
                    "    from collections import deque\n"
                    "    if not root:\n"
                    "        return ''\n"
                    "    out = []\n"
                    "    q = deque([root])\n"
                    "    while q:\n"
                    "        n = q.popleft()\n"
                    "        if n is None:\n"
                    "            out.append('N')\n"
                    "            continue\n"
                    "        out.append(str(n.val))\n"
                    "        q.append(n.left)\n"
                    "        q.append(n.right)\n"
                    "    while out and out[-1] == 'N':\n"
                    "        out.pop()\n"
                    "    return ','.join(out)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Establish the requirement: must round-trip exactly. Different trees with same shape but different children-positions must serialise differently.",
        "2. State the trap: in-order alone is ambiguous (e.g. `[1, 2]` could be left or right child). Need null markers OR two traversals.",
        "3. Pick pre-order with null markers — minimal extra code, unambiguous reconstruction.",
        "4. Serialize: recursive DFS pre-order, append 'N' for null. Deserialize: iterate tokens, recurse.",
        "5. Discuss trade-offs: pre-order is compact but unreadable; level-order is human-readable but less compact on skewed trees.",
        "6. Edge cases: empty tree, single node, skewed trees, duplicate values.",
    ],
    "tips": [
        "Pick a delimiter that can't appear in your value space. For arbitrary integers, comma is fine; for arbitrary strings, prefix with a length marker.",
        "If the value space is bounded (e.g. small ints), you can pack the serialisation into a byte stream for the absolutely most compact representation.",
        "Common follow-up: 'serialize a BST.' BSTs don't need null markers — just pre-order is enough since the value bounds the structure.",
        "Common follow-up: 'serialize an N-ary tree.' Same idea, but each node emits its child count first.",
        "Round-trip property is the canonical test: `deserialize(serialize(t)) == t` structurally.",
    ],
    "companies": ["Amazon", "Microsoft", "LinkedIn", "Bloomberg", "Facebook"],
    "topics": ["Tree", "DFS", "BFS", "Serialization", "Design"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


class _TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def _serialize(root):
    parts = []

    def go(n):
        if n is None:
            parts.append("N")
            return
        parts.append(str(n.val))
        go(n.left)
        go(n.right)

    go(root)
    return ",".join(parts)


def _deserialize(s):
    if not s:
        return None
    it = iter(s.split(","))

    def go():
        tok = next(it)
        if tok == "N":
            return None
        n = _TreeNode(int(tok))
        n.left = go()
        n.right = go()
        return n

    return go()


def _from_level(arr):
    from collections import deque
    if not arr:
        return None
    root = _TreeNode(arr[0])
    q = deque([root])
    i = 1
    while q and i < len(arr):
        n = q.popleft()
        if i < len(arr) and arr[i] is not None:
            n.left = _TreeNode(arr[i]); q.append(n.left)
        i += 1
        if i < len(arr) and arr[i] is not None:
            n.right = _TreeNode(arr[i]); q.append(n.right)
        i += 1
    return root


def _to_level(root):
    if root is None:
        return []
    from collections import deque
    out = []
    q = deque([root])
    while q:
        n = q.popleft()
        if n is None:
            out.append(None)
            continue
        out.append(n.val)
        q.append(n.left)
        q.append(n.right)
    while out and out[-1] is None:
        out.pop()
    return out


def REFERENCE(level_order):
    root = _from_level(level_order)
    s = _serialize(root)
    root2 = _deserialize(s)
    return _to_level(root2)


register(PAYLOAD, REFERENCE)
