"""Invert Binary Tree — Easy. Tree / DFS / BFS.

LeetCode 226. The 'Max Howell could not solve on a whiteboard, so
Google didn't hire him' problem. Five-line recursion; useful as a
warm-up to confirm the candidate can write tree code without panic.

Input/output use LeetCode level-order with `null` for missing nodes,
which lines up with how most folks have already memorised the format.
"""
from collections import deque

from builder.registry import register


def _build(level):
    """Deserialize LeetCode level-order list (with None for missing) to a tree."""
    if not level:
        return None
    nodes = [None if v is None else {"val": v, "left": None, "right": None} for v in level]
    kids = nodes[1:][::-1]
    for node in nodes:
        if node is None:
            continue
        if kids:
            node["left"] = kids.pop()
        if kids:
            node["right"] = kids.pop()
    return nodes[0]


def _serialize(root):
    """Serialize tree back to LeetCode level-order list with None for missing.

    Trailing None entries are stripped (LeetCode convention)."""
    if root is None:
        return []
    out = []
    q = deque([root])
    while q:
        node = q.popleft()
        if node is None:
            out.append(None)
            continue
        out.append(node["val"])
        q.append(node["left"])
        q.append(node["right"])
    while out and out[-1] is None:
        out.pop()
    return out


def _invert(node):
    if node is None:
        return None
    node["left"], node["right"] = _invert(node["right"]), _invert(node["left"])
    return node


PAYLOAD = {
    "title": "Invert Binary Tree",
    "difficulty": "Easy",
    "description": (
        "Given the `root` of a binary tree, **invert** the tree (mirror it left-to-right) and return its "
        "root.\n\n"
        "The input/output use LeetCode level-order serialization where `null` denotes a missing child.\n\n"
        "**Example 1:**\n"
        "- Input: `root = [4,2,7,1,3,6,9]`\n"
        "- Output: `[4,7,2,9,6,3,1]`\n"
        "- Explanation:\n"
        "```\n"
        "       4                4\n"
        "      / \\              / \\\n"
        "     2   7    -->     7   2\n"
        "    / \\ / \\          / \\ / \\\n"
        "   1  3 6  9         9  6 3  1\n"
        "```\n\n"
        "**Example 2:**\n"
        "- Input: `root = [2,1,3]`\n"
        "- Output: `[2,3,1]`\n"
        "- Explanation:\n"
        "```\n"
        "     2            2\n"
        "    / \\          / \\\n"
        "   1   3   -->  3   1\n"
        "```"
    ),
    "hints": [
        "Recursion writes itself: invert the left subtree, invert the right subtree, then swap the two pointers.",
        "Order doesn't matter — you can swap *before* recursing or *after*. Both work because each call only touches its own subtree.",
        "Iterative version: BFS with a queue. Pop a node, swap its children, enqueue any non-null children. Same O(n) work, O(w) space.",
        "DFS iterative is also fine — use a stack instead of a queue. The order in which you visit nodes is irrelevant; only the local swap matters.",
        "Edge case: an empty tree (`root` is `None`). Return `None` immediately and you're done.",
    ],
    "constraints": [
        "The number of nodes in the tree is in the range `[0, 100]`.",
        "-100 <= Node.val <= 100",
    ],
    "starter_code": {
        "python": (
            "# Definition for a binary tree node.\n"
            "# class TreeNode:\n"
            "#     def __init__(self, val=0, left=None, right=None):\n"
            "#         self.val = val\n"
            "#         self.left = left\n"
            "#         self.right = right\n"
            "def invert_tree(root):\n"
            "    # Your code here\n"
            "    pass"
        ),
        "javascript": (
            "// Definition for a binary tree node.\n"
            "// function TreeNode(val, left, right) {\n"
            "//     this.val = (val === undefined ? 0 : val);\n"
            "//     this.left = (left === undefined ? null : left);\n"
            "//     this.right = (right === undefined ? null : right);\n"
            "// }\n"
            "function invertTree(root) {\n"
            "    // Your code here\n"
            "}"
        ),
        "java": (
            "/**\n"
            " * Definition for a binary tree node.\n"
            " * public class TreeNode {\n"
            " *     int val;\n"
            " *     TreeNode left;\n"
            " *     TreeNode right;\n"
            " *     TreeNode() {}\n"
            " *     TreeNode(int val) { this.val = val; }\n"
            " *     TreeNode(int val, TreeNode left, TreeNode right) {\n"
            " *         this.val = val;\n"
            " *         this.left = left;\n"
            " *         this.right = right;\n"
            " *     }\n"
            " * }\n"
            " */\n"
            "public TreeNode invertTree(TreeNode root) {\n"
            "    // Your code here\n"
            "    return root;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    # Build a small tree manually for a smoke test:  4\n"
            "    #                                              / \\\n"
            "    #                                             2   7\n"
            "    root = TreeNode(4, TreeNode(2), TreeNode(7))\n"
            "    inverted = invert_tree(root)\n"
            "    print(inverted.val, inverted.left.val, inverted.right.val)  # 4 7 2"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const root = { val: 4, left: { val: 2, left: null, right: null },\n"
            "                       right: { val: 7, left: null, right: null } };\n"
            "const inv = invertTree(root);\n"
            "console.log(inv.val, inv.left.val, inv.right.val);  // 4 7 2"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        TreeNode root = new TreeNode(4, new TreeNode(2), new TreeNode(7));\n"
            "        TreeNode inv = s.invertTree(root);\n"
            "        System.out.println(inv.val + \" \" + inv.left.val + \" \" + inv.right.val);\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": []}, "expected": [],
         "description": "Empty tree — nothing to invert", "tags": ["edge"]},
        {"input": {"root": [1]}, "expected": [1],
         "description": "Single node — invert is identity", "tags": ["edge"]},
        {"input": {"root": [1, 2]}, "expected": [1, None, 2],
         "description": "Two-node tree, only left child — becomes only-right", "tags": ["edge"]},
        {"input": {"root": [1, None, 2]}, "expected": [1, 2],
         "description": "Two-node tree, only right child — becomes only-left", "tags": ["edge"]},
        {"input": {"root": [4, 2, 7, 1, 3, 6, 9]}, "expected": [4, 7, 2, 9, 6, 3, 1],
         "description": "Classic LeetCode example — full balanced tree", "tags": ["basic"]},
        {"input": {"root": [2, 1, 3]}, "expected": [2, 3, 1],
         "description": "Three-node BST flipped to mirror BST", "tags": ["basic"]},
        {"input": {"root": [1, 2, 3, 4, 5, 6, 7]}, "expected": [1, 3, 2, 7, 6, 5, 4],
         "description": "Perfect binary tree, depth 3", "tags": ["basic"]},
        {"input": {"root": [1, 2, None, 3, None, 4, None, 5]},
         "expected": [1, None, 2, None, 3, None, 4, None, 5],
         "description": "Left-skewed chain becomes right-skewed chain", "tags": ["tricky"]},
        {"input": {"root": [1, None, 2, None, 3, None, 4, None, 5]},
         "expected": [1, 2, None, 3, None, 4, None, 5],
         "description": "Right-skewed chain becomes left-skewed chain", "tags": ["tricky"]},
        {"input": {"root": [5, 3, 8, 1, 4, None, 9]},
         "expected": [5, 8, 3, 9, None, 4, 1],
         "description": "Lopsided tree with a missing internal child — nulls must be placed correctly",
         "tags": ["tricky"]},
        {"input": {"root": [0, -1, 1, -2, None, None, 2]},
         "expected": [0, 1, -1, 2, None, None, -2],
         "description": "Negative values and interior null", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Recursive DFS (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h)",
            "description": (
                "Recurse into the left and right subtrees, then swap the two child pointers. Five lines. "
                "`h` is the tree height — `O(log n)` for balanced trees, `O(n)` worst case (skewed)."
            ),
            "code": {
                "python": (
                    "def invert_tree(root):\n"
                    "    if root is None:\n"
                    "        return None\n"
                    "    left = invert_tree(root.left)\n"
                    "    right = invert_tree(root.right)\n"
                    "    root.left, root.right = right, left\n"
                    "    return root"
                ),
                "javascript": (
                    "function invertTree(root) {\n"
                    "    if (root === null) return null;\n"
                    "    const left = invertTree(root.left);\n"
                    "    const right = invertTree(root.right);\n"
                    "    root.left = right;\n"
                    "    root.right = left;\n"
                    "    return root;\n"
                    "}"
                ),
                "java": (
                    "public TreeNode invertTree(TreeNode root) {\n"
                    "    if (root == null) return null;\n"
                    "    TreeNode left = invertTree(root.left);\n"
                    "    TreeNode right = invertTree(root.right);\n"
                    "    root.left = right;\n"
                    "    root.right = left;\n"
                    "    return root;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative BFS with Queue",
            "time_complexity": "O(n)",
            "space_complexity": "O(w)",
            "description": (
                "Walk the tree level-by-level. For each node popped from the queue, swap its left and right "
                "pointers, then enqueue both children (skipping null). `w` is the maximum width of the tree, "
                "which can be up to `n/2` for the bottom level of a complete tree."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "def invert_tree(root):\n"
                    "    if root is None:\n"
                    "        return None\n"
                    "    q = deque([root])\n"
                    "    while q:\n"
                    "        node = q.popleft()\n"
                    "        node.left, node.right = node.right, node.left\n"
                    "        if node.left:\n"
                    "            q.append(node.left)\n"
                    "        if node.right:\n"
                    "            q.append(node.right)\n"
                    "    return root"
                ),
                "javascript": (
                    "function invertTree(root) {\n"
                    "    if (root === null) return null;\n"
                    "    const q = [root];\n"
                    "    while (q.length) {\n"
                    "        const node = q.shift();\n"
                    "        [node.left, node.right] = [node.right, node.left];\n"
                    "        if (node.left) q.push(node.left);\n"
                    "        if (node.right) q.push(node.right);\n"
                    "    }\n"
                    "    return root;\n"
                    "}"
                ),
                "java": (
                    "public TreeNode invertTree(TreeNode root) {\n"
                    "    if (root == null) return null;\n"
                    "    Deque<TreeNode> q = new ArrayDeque<>();\n"
                    "    q.offer(root);\n"
                    "    while (!q.isEmpty()) {\n"
                    "        TreeNode node = q.poll();\n"
                    "        TreeNode tmp = node.left;\n"
                    "        node.left = node.right;\n"
                    "        node.right = tmp;\n"
                    "        if (node.left != null) q.offer(node.left);\n"
                    "        if (node.right != null) q.offer(node.right);\n"
                    "    }\n"
                    "    return root;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: 'invert' means mirror left-to-right at every level — equivalently, swap left and right children at every node.",
        "2. Recursion is the natural fit: invert(root) = swap(invert(left), invert(right)). Five lines.",
        "3. Order is irrelevant — pre-order (swap then recurse) and post-order (recurse then swap) both work because each call is self-contained.",
        "4. Iterative version: replace the call stack with an explicit queue (BFS) or stack (DFS). The work at each node is just the swap.",
        "5. Edge case: `root is None` → return `None`. Handles the empty-tree input cleanly.",
        "6. Complexity: every node is touched exactly once → `O(n)` time. Space is the recursion depth (`O(h)`) or the queue width (`O(w)`).",
    ],
    "tips": [
        "Don't forget the `root is None` base case — without it, accessing `root.left` on an empty tree throws.",
        "Pre-order vs post-order swap is a non-issue here. The interviewer may ask 'does order matter?' — the answer is no, and explaining *why* (each call is independent) is the win.",
        "If the interviewer asks for the iterative version, BFS with a queue is the cleanest. DFS with a stack is equivalent.",
        "Don't be tempted to write `root.left, root.right = invert(root.left), invert(root.right)` and call it a day — it works in Python because of tuple unpacking, but the equivalent in Java/C++ requires a temp variable.",
        "Follow-up to expect: 'How would you check if two trees are mirror images?' → recursive `is_mirror(a, b)` comparing `a.left` with `b.right` and vice versa.",
        "Another common follow-up: 'Symmetric tree' (LC 101) — same recursion, just no mutation. Mention it if you have time.",
    ],
    "companies": ["Google", "Amazon", "Microsoft", "Apple", "Bloomberg"],
    "topics": ["Tree", "Depth-First Search", "Breadth-First Search", "Binary Tree"],
    "time_complexity": "O(n)",
    "space_complexity": "O(h)",
}


def REFERENCE(root):
    """Take a level-order list, invert the tree, return the level-order list."""
    tree = _build(root)
    inverted = _invert(tree)
    return _serialize(inverted)


register(PAYLOAD, REFERENCE)
