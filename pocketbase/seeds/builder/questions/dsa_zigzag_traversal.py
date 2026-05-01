"""Zigzag Tree Traversal — Medium. Trees / BFS.

Level-order traversal but flip direction every level. BFS with a deque
(or with a flag and final reversal) is the canonical answer."""
from builder.registry import register


PAYLOAD = {
    "title": "Binary Tree Zigzag Level Order Traversal",
    "difficulty": "Medium",
    "description": (
        "Given the root of a binary tree, return the **zigzag level-order traversal** of node values: "
        "level 0 left-to-right, level 1 right-to-left, level 2 left-to-right, and so on. Return as a list "
        "of lists, one per level.\n\n"
        "Trees are encoded as level-order lists with `null` for missing children.\n\n"
        "**Example:**\n"
        "- Input: `[3, 9, 20, null, null, 15, 7]`\n"
        "- Output: `[[3], [20, 9], [15, 7]]`"
    ),
    "hints": [
        "Standard BFS gives left-to-right per level. Reverse every other level.",
        "Cleanest: BFS with a flag, build each level as a list, reverse iff flag is set, flip flag.",
        "Avoid 'reverse the queue' approaches — they conflate the dequeue order with the output order.",
        "DFS with an explicit `level` parameter also works: append to `output[level]` if even, prepend (or push to a deque's front) if odd.",
        "Edge cases: empty tree (return []), single node ([[val]]), deeply skewed tree.",
    ],
    "constraints": [
        "0 <= node count <= 10⁴",
    ],
    "starter_code": {
        "python": "def zigzag_level_order(level_order):\n    # Your code here\n    pass",
        "javascript": "function zigzagLevelOrder(levelOrder) {\n    // Your code here\n}",
        "java": "public List<List<Integer>> zigzagLevelOrder(List<Integer> levelOrder) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(zigzag_level_order([3, 9, 20, None, None, 15, 7]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"level_order": [3, 9, 20, None, None, 15, 7]},
         "expected": [[3], [20, 9], [15, 7]],
         "description": "Standard 3-level tree", "tags": ["basic"]},
        {"input": {"level_order": []}, "expected": [],
         "description": "Empty tree", "tags": ["edge"]},
        {"input": {"level_order": [1]}, "expected": [[1]],
         "description": "Single node", "tags": ["edge"]},
        {"input": {"level_order": [1, 2, 3, 4, 5, 6, 7]},
         "expected": [[1], [3, 2], [4, 5, 6, 7]],
         "description": "Full tree to depth 3", "tags": ["basic"]},
        {"input": {"level_order": [1, 2, None, 3, None, 4]},
         "expected": [[1], [2], [3], [4]],
         "description": "Left-skewed tree (single node per level)", "tags": ["edge"]},
        {"input": {"level_order": [1, None, 2, None, 3, None, 4]},
         "expected": [[1], [2], [3], [4]],
         "description": "Right-skewed tree", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "BFS with Direction Flag (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Standard level-order BFS, processing the queue level by level. Build each level's value "
                "list left-to-right, then reverse it iff the flag says so. Toggle the flag, append, repeat."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "def zigzag_level_order(level_order):\n"
                    "    root = _from_level(level_order)\n"
                    "    if root is None:\n"
                    "        return []\n"
                    "    out = []\n"
                    "    q = deque([root])\n"
                    "    flip = False\n"
                    "    while q:\n"
                    "        level = []\n"
                    "        for _ in range(len(q)):\n"
                    "            n = q.popleft()\n"
                    "            level.append(n.val)\n"
                    "            if n.left: q.append(n.left)\n"
                    "            if n.right: q.append(n.right)\n"
                    "        out.append(level[::-1] if flip else level)\n"
                    "        flip = not flip\n"
                    "    return out"
                ),
                "javascript": (
                    "function zigzagLevelOrder(levelOrder) {\n"
                    "    const root = fromLevel(levelOrder);\n"
                    "    if (!root) return [];\n"
                    "    const out = [];\n"
                    "    let q = [root];\n"
                    "    let flip = false;\n"
                    "    while (q.length) {\n"
                    "        const level = [];\n"
                    "        const next = [];\n"
                    "        for (const n of q) {\n"
                    "            level.push(n.val);\n"
                    "            if (n.left) next.push(n.left);\n"
                    "            if (n.right) next.push(n.right);\n"
                    "        }\n"
                    "        out.push(flip ? level.reverse() : level);\n"
                    "        flip = !flip;\n"
                    "        q = next;\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "DFS with Level Indexing",
            "time_complexity": "O(n)",
            "space_complexity": "O(n) + O(h) recursion",
            "description": (
                "DFS in pre-order, passing the current depth. For each node, append (or prepend) its value "
                "to `output[depth]` based on the depth's parity. Conceptually elegant; loses to BFS on cache "
                "behaviour for very wide trees."
            ),
            "code": {
                "python": (
                    "def zigzag_level_order(level_order):\n"
                    "    root = _from_level(level_order)\n"
                    "    if root is None:\n"
                    "        return []\n"
                    "    out = []\n"
                    "    def go(n, depth):\n"
                    "        if n is None: return\n"
                    "        if len(out) <= depth:\n"
                    "            out.append([])\n"
                    "        if depth % 2 == 0:\n"
                    "            out[depth].append(n.val)\n"
                    "        else:\n"
                    "            out[depth].insert(0, n.val)\n"
                    "        go(n.left, depth + 1)\n"
                    "        go(n.right, depth + 1)\n"
                    "    go(root, 0)\n"
                    "    return out"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise: level-order traversal with alternating direction. BFS is the natural fit.",
        "2. Process the queue level by level using the size-snapshot trick: 'for _ in range(len(queue)): pop'.",
        "3. Build each level's list left-to-right; reverse it if we're on an odd-indexed level.",
        "4. Children always pushed left-then-right into the queue — direction flipping happens at output time, not at traversal time.",
        "5. DFS variant: depth-indexed appends/prepends. Equivalent, slightly less natural.",
        "6. Edge cases: empty tree, single node, skewed trees (each level has 1 node).",
    ],
    "tips": [
        "Don't try to reverse the queue itself — the queue's order is the next level's input, not the current level's output.",
        "Python: `level[::-1]` allocates a new list. For very wide levels, build a deque and `appendleft` directly to skip the reverse.",
        "For odd levels with DFS, `list.insert(0, …)` is O(L). On wide levels, append + reverse at the end is faster.",
        "Common follow-up: 'spiral order' is the same problem with the opposite phase — start with right-to-left at the root.",
        "Common follow-up: 'level-order of an N-ary tree.' Same BFS, iterate children directly instead of left/right.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Bloomberg"],
    "topics": ["Tree", "BFS", "Level-Order"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


class _TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


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


def REFERENCE(level_order):
    from collections import deque
    root = _from_level(level_order)
    if root is None:
        return []
    out = []
    q = deque([root])
    flip = False
    while q:
        level = []
        for _ in range(len(q)):
            n = q.popleft()
            level.append(n.val)
            if n.left:
                q.append(n.left)
            if n.right:
                q.append(n.right)
        out.append(level[::-1] if flip else level)
        flip = not flip
    return out


register(PAYLOAD, REFERENCE)
