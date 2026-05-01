"""Foldable Binary Tree (Mirror Check) — Easy/Medium. Trees / Recursion.

A binary tree is foldable iff its left subtree is the structural mirror
of its right subtree. Note: structure-only mirror; node values are not
compared. The recursion compares (left.left, right.right) and
(left.right, right.left)."""
from builder.registry import register


PAYLOAD = {
    "title": "Foldable Binary Tree",
    "difficulty": "Medium",
    "description": (
        "Given a binary tree (NOT a BST), determine whether it is **foldable** — i.e. its left subtree is "
        "the structural mirror image of its right subtree. The values at the nodes are irrelevant; only the "
        "shape matters.\n\n"
        "Trees are encoded as level-order lists with `null` for missing children.\n\n"
        "**Example 1:**\n"
        "- Input: `[1, 2, 3]` (both children present)\n"
        "- Output: `true`\n\n"
        "**Example 2:**\n"
        "- Input: `[1, 2, 3, 4, null, null, 5]` (left.left and right.right present)\n"
        "- Output: `true`\n\n"
        "**Example 3:**\n"
        "- Input: `[1, 2, 3, 4, null, 5, null]` (left.left and right.left — not mirrored)\n"
        "- Output: `false`\n\n"
        "An empty tree is foldable. A single-node tree is foldable."
    ),
    "hints": [
        "Recursion compares the LEFT subtree against the MIRROR of the RIGHT subtree (or vice versa).",
        "The recursive predicate is: `mirror(a, b)` = `(a is None and b is None) OR (a and b and mirror(a.left, b.right) and mirror(a.right, b.left))`.",
        "Don't compare values — the problem is purely structural. Compare only nullness at each pair of nodes.",
        "An iterative variant uses two queues (or one queue with paired pushes) and walks the tree level by level.",
        "Edge cases: empty tree, single node, full tree, tree where only one child exists at the root.",
    ],
    "constraints": [
        "0 <= node count <= 10⁴",
    ],
    "starter_code": {
        "python": "def is_foldable(level_order):\n    # Your code here\n    pass",
        "javascript": "function isFoldable(levelOrder) {\n    // Your code here\n}",
        "java": "public boolean isFoldable(List<Integer> levelOrder) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(is_foldable([1, 2, 3, 4, None, None, 5]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"level_order": [1, 2, 3]}, "expected": True,
         "description": "Both children present at root", "tags": ["basic"]},
        {"input": {"level_order": [1, 2, 3, 4, None, None, 5]}, "expected": True,
         "description": "Mirrored grandchildren", "tags": ["basic"]},
        {"input": {"level_order": [1, 2, 3, 4, None, 5, None]}, "expected": False,
         "description": "Grandchildren on the same side — not mirrored", "tags": ["basic"]},
        {"input": {"level_order": []}, "expected": True,
         "description": "Empty tree — vacuously foldable", "tags": ["edge"]},
        {"input": {"level_order": [42]}, "expected": True,
         "description": "Single node", "tags": ["edge"]},
        {"input": {"level_order": [1, 2, None]}, "expected": False,
         "description": "Only left child at root", "tags": ["edge"]},
        {"input": {"level_order": [1, 2, 3, 4, 5, 6, 7]}, "expected": True,
         "description": "Full tree to depth 3", "tags": ["basic"]},
        {"input": {"level_order": [1, 2, 3, 4, 5, 6, None]}, "expected": False,
         "description": "Asymmetric leaf", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Recursive Mirror Check (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h) recursion stack",
            "description": (
                "Define `mirror(a, b)` returning whether the subtrees rooted at `a` and `b` are structural "
                "mirrors. Recurse pairwise: `a.left` ↔ `b.right` and `a.right` ↔ `b.left`. The tree is "
                "foldable iff `root` is null OR `mirror(root.left, root.right)`."
            ),
            "code": {
                "python": (
                    "def is_foldable(level_order):\n"
                    "    root = _from_level(level_order)\n"
                    "    if root is None:\n"
                    "        return True\n"
                    "    return _mirror(root.left, root.right)\n\n"
                    "def _mirror(a, b):\n"
                    "    if a is None and b is None:\n"
                    "        return True\n"
                    "    if a is None or b is None:\n"
                    "        return False\n"
                    "    return _mirror(a.left, b.right) and _mirror(a.right, b.left)"
                ),
                "javascript": (
                    "function isFoldable(levelOrder) {\n"
                    "    const root = fromLevel(levelOrder);\n"
                    "    if (!root) return true;\n"
                    "    const mirror = (a, b) => {\n"
                    "        if (!a && !b) return true;\n"
                    "        if (!a || !b) return false;\n"
                    "        return mirror(a.left, b.right) && mirror(a.right, b.left);\n"
                    "    };\n"
                    "    return mirror(root.left, root.right);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative with Pair Queue",
            "time_complexity": "O(n)",
            "space_complexity": "O(w) where w = max width of either side",
            "description": (
                "Push (left, right) pairs into a queue. On each iteration pop a pair, compare nullness, "
                "and push the diagonal grandchildren: (a.left, b.right) and (a.right, b.left). Same logic, "
                "no recursion — useful when tree depth could blow the stack."
            ),
            "code": {
                "python": (
                    "def is_foldable(level_order):\n"
                    "    root = _from_level(level_order)\n"
                    "    if root is None:\n"
                    "        return True\n"
                    "    from collections import deque\n"
                    "    q = deque([(root.left, root.right)])\n"
                    "    while q:\n"
                    "        a, b = q.popleft()\n"
                    "        if a is None and b is None:\n"
                    "            continue\n"
                    "        if a is None or b is None:\n"
                    "            return False\n"
                    "        q.append((a.left, b.right))\n"
                    "        q.append((a.right, b.left))\n"
                    "    return True"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Read carefully: foldable means STRUCTURAL mirror, not value-equal mirror. Don't compare values.",
        "2. The natural recursion: `mirror(left_subtree, right_subtree)`. Compare diagonally at each level.",
        "3. Base cases: both null → true (vacuously mirrored), one null → false (asymmetric).",
        "4. Empty tree is foldable. Single node is foldable. Don't return false on null root.",
        "5. Iterative variant: queue of pairs. Same logic without recursion depth concerns.",
        "6. Edge cases: empty tree, single node, asymmetric direct children, deep mirrored tree.",
    ],
    "tips": [
        "If asked 'is the tree symmetric (values too)?' (LeetCode 101), add `a.val == b.val` to the recursion. The structure check alone is NOT enough.",
        "In-order traversal will NOT detect this — equal traversals can come from non-foldable trees because position information is lost.",
        "Iterative version: pair tuples in a queue. Don't accidentally push (a, b) and (b, a) — that double-counts.",
        "Common follow-up: 'rotate the right subtree to mirror the left.' Walk the right subtree and swap left/right children at each node.",
        "Common follow-up: 'count how many subtrees are foldable.' Apply the predicate at every node, not just root.",
    ],
    "companies": ["Amazon", "Microsoft"],
    "topics": ["Tree", "Recursion", "DFS"],
    "time_complexity": "O(n)",
    "space_complexity": "O(h)",
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
    root = _from_level(level_order)
    if root is None:
        return True

    def mirror(a, b):
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        return mirror(a.left, b.right) and mirror(a.right, b.left)

    return mirror(root.left, root.right)


register(PAYLOAD, REFERENCE)
