"""Binary Tree Right Side View — Medium. Trees / BFS.

Standing on the right side of a binary tree, return values of nodes
visible top to bottom. Last node of each level (BFS) or first DFS hit
at each depth — both are O(n)."""
from builder.registry import register


PAYLOAD = {
    "title": "Binary Tree Right Side View",
    "difficulty": "Medium",
    "description": (
        "Given the root of a binary tree, imagine yourself standing on the right side. Return the **values "
        "of the nodes you can see**, ordered from top to bottom.\n\n"
        "Trees are encoded as level-order lists with `null` for missing children.\n\n"
        "**Example 1:**\n"
        "- Input: `[1, 2, 3, null, 5, null, 4]`\n"
        "- Output: `[1, 3, 4]`\n\n"
        "**Example 2:**\n"
        "- Input: `[1, null, 3]`\n"
        "- Output: `[1, 3]`\n\n"
        "**Example 3:**\n"
        "- Input: `[]`\n"
        "- Output: `[]`"
    ),
    "hints": [
        "BFS level by level. Take the LAST node dequeued at each level — that's the rightmost visible at that level.",
        "DFS variant: go right first. The first time you reach a new depth, that node is visible. Use a depth counter.",
        "Both are O(n). BFS is more intuitive; right-first DFS is one fewer state variable.",
        "Edge cases: empty tree, single node, left-skewed tree (every left node is the rightmost at its level), right-skewed tree, full tree.",
    ],
    "constraints": [
        "0 <= node count <= 10⁴",
    ],
    "starter_code": {
        "python": "def right_side_view(level_order):\n    # Your code here\n    pass",
        "javascript": "function rightSideView(levelOrder) {\n    // Your code here\n}",
        "java": "public List<Integer> rightSideView(List<Integer> levelOrder) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(right_side_view([1, 2, 3, None, 5, None, 4]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"level_order": [1, 2, 3, None, 5, None, 4]},
         "expected": [1, 3, 4],
         "description": "Standard tree from problem", "tags": ["basic"]},
        {"input": {"level_order": [1, None, 3]}, "expected": [1, 3],
         "description": "Right-only branches", "tags": ["edge"]},
        {"input": {"level_order": []}, "expected": [],
         "description": "Empty tree", "tags": ["edge"]},
        {"input": {"level_order": [1]}, "expected": [1],
         "description": "Single node", "tags": ["edge"]},
        {"input": {"level_order": [1, 2, None, 3, None, 4]},
         "expected": [1, 2, 3, 4],
         "description": "Left-skewed — every level has only the left child, which IS the rightmost",
         "tags": ["tricky"]},
        {"input": {"level_order": [1, 2, 3, 4, 5, 6, 7]},
         "expected": [1, 3, 7],
         "description": "Full tree to depth 3", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "BFS — Last Node Per Level (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Standard level-order BFS using the size-snapshot trick. For each level, append the value "
                "of the LAST node dequeued (the rightmost). Children always pushed left-then-right; order "
                "within the queue corresponds to position within the level."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "def right_side_view(level_order):\n"
                    "    root = _from_level(level_order)\n"
                    "    if root is None:\n"
                    "        return []\n"
                    "    out = []\n"
                    "    q = deque([root])\n"
                    "    while q:\n"
                    "        size = len(q)\n"
                    "        for i in range(size):\n"
                    "            n = q.popleft()\n"
                    "            if i == size - 1:\n"
                    "                out.append(n.val)\n"
                    "            if n.left: q.append(n.left)\n"
                    "            if n.right: q.append(n.right)\n"
                    "    return out"
                ),
                "javascript": (
                    "function rightSideView(levelOrder) {\n"
                    "    const root = fromLevel(levelOrder);\n"
                    "    if (!root) return [];\n"
                    "    const out = [];\n"
                    "    let q = [root];\n"
                    "    while (q.length) {\n"
                    "        const next = [];\n"
                    "        for (let i = 0; i < q.length; i++) {\n"
                    "            const n = q[i];\n"
                    "            if (i === q.length - 1) out.push(n.val);\n"
                    "            if (n.left) next.push(n.left);\n"
                    "            if (n.right) next.push(n.right);\n"
                    "        }\n"
                    "        q = next;\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "DFS — Right-First With Depth",
            "time_complexity": "O(n)",
            "space_complexity": "O(h)",
            "description": (
                "Recurse going RIGHT before LEFT. Track current depth. The first time you reach a new "
                "depth, the node is visible. Same idea as BFS but in fewer lines."
            ),
            "code": {
                "python": (
                    "def right_side_view(level_order):\n"
                    "    root = _from_level(level_order)\n"
                    "    out = []\n"
                    "    def go(n, d):\n"
                    "        if n is None:\n"
                    "            return\n"
                    "        if d == len(out):\n"
                    "            out.append(n.val)\n"
                    "        go(n.right, d + 1)\n"
                    "        go(n.left, d + 1)\n"
                    "    go(root, 0)\n"
                    "    return out"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise: 'visible from the right' = first node hit at each depth when entering from the right.",
        "2. BFS: process levels using the size-snapshot trick; capture the last dequeued at each level.",
        "3. DFS: recurse right first; the FIRST time you reach a new depth, that node is visible.",
        "4. Watch the left-skewed case — a left-only chain is still 'visible' from the right because it's the only node at each level.",
        "5. Edge cases: empty tree, single node, left-skewed, right-skewed, full tree.",
        "6. Both approaches are O(n); pick whichever feels more natural.",
    ],
    "tips": [
        "BFS size-snapshot: `for i in range(len(q))` — capture the size before iterating because pushes happen inside the loop.",
        "Going right-first in DFS isn't just an optimisation — it's the correctness condition. Going left-first would capture the leftmost at each level instead.",
        "Don't try to walk only the right edge of the tree — left-skewed trees fail that approach (no right children).",
        "Common follow-up: 'left side view.' Same algorithms, swap the visible-node selection (first instead of last in BFS, left-first in DFS).",
        "Common follow-up: 'top view' or 'bottom view.' Different problem — track horizontal distance from root with BFS.",
    ],
    "companies": ["Amazon", "Microsoft", "ByteDance"],
    "topics": ["Tree", "BFS", "DFS"],
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
    while q:
        size = len(q)
        for i in range(size):
            n = q.popleft()
            if i == size - 1:
                out.append(n.val)
            if n.left:
                q.append(n.left)
            if n.right:
                q.append(n.right)
    return out


register(PAYLOAD, REFERENCE)
