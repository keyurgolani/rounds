"""Validate Binary Search Tree — Medium. Tree / DFS / BST.

LeetCode 98. The canonical 'do you actually understand BSTs?' question.
The trap: candidates who only check `node.left.val < node.val < node.right.val`
locally and miss that the BST property is a *global* invariant — every node
in the entire left subtree must be smaller, not just the immediate child.

Input/output use LeetCode level-order with `null` for missing nodes.
The reference returns a bool.
"""
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


def _is_valid_bst(node, low, high):
    if node is None:
        return True
    if node["val"] <= low or node["val"] >= high:
        return False
    return (_is_valid_bst(node["left"], low, node["val"])
            and _is_valid_bst(node["right"], node["val"], high))


PAYLOAD = {
    "title": "Validate Binary Search Tree",
    "difficulty": "Medium",
    "description": (
        "Given the `root` of a binary tree, determine if it is a **valid binary search tree (BST)**.\n\n"
        "A valid BST is defined as follows:\n"
        "- The left subtree of a node contains only nodes with keys **strictly less than** the node's key.\n"
        "- The right subtree of a node contains only nodes with keys **strictly greater than** the node's key.\n"
        "- Both the left and right subtrees must also be binary search trees.\n\n"
        "The input uses LeetCode level-order serialization where `null` denotes a missing child.\n\n"
        "**Example 1:**\n"
        "- Input: `root = [2,1,3]`\n"
        "- Output: `true`\n"
        "- Explanation:\n"
        "```\n"
        "     2\n"
        "    / \\\n"
        "   1   3\n"
        "```\n"
        "  Every left descendant is `< 2` and every right descendant is `> 2`.\n\n"
        "**Example 2:**\n"
        "- Input: `root = [5,1,4,null,null,3,6]`\n"
        "- Output: `false`\n"
        "- Explanation:\n"
        "```\n"
        "       5\n"
        "      / \\\n"
        "     1   4\n"
        "        / \\\n"
        "       3   6\n"
        "```\n"
        "  The node with value `4` is in the right subtree of `5`, which is fine — but its left child `3` is also "
        "in the right subtree of `5`, and `3 < 5` violates the BST property. The local parent-child checks "
        "(`3 < 4` and `6 > 4`) all pass, but the *global* invariant fails."
    ),
    "hints": [
        "The BST property is GLOBAL, not local. Just checking `left.val < node.val < right.val` at each node is wrong — every node in the left subtree must be < node, not just the immediate left child.",
        "Recurse with bounds: each node receives a `(low, high)` window it must lie strictly inside. Going left tightens the upper bound to `node.val`; going right tightens the lower bound to `node.val`.",
        "Alternative: an in-order traversal of a valid BST yields values in *strictly* increasing order. Walk in-order while tracking the previous value — if `prev >= curr` at any point, return false.",
        "Watch the strict inequality. Duplicate values are NOT allowed (`<=` or `>=` against the bound is a failure). This is a common off-by-one: `<` vs `<=`.",
        "Use sentinel bounds of `-infinity` / `+infinity` (or `None`) at the root so the constraint `INT_MIN <= val <= INT_MAX` doesn't make a legitimate INT_MIN/INT_MAX node fail. Don't hardcode `-2^31` and `2^31-1` as initial bounds.",
    ],
    "constraints": [
        "The number of nodes in the tree is in the range `[0, 10^4]`.",
        "-2^31 <= Node.val <= 2^31 - 1 — the bounds matter; don't use `INT_MIN`/`INT_MAX` as sentinels.",
        "Strict inequality: duplicate values are NOT a valid BST.",
    ],
    "starter_code": {
        "python": (
            "# Definition for a binary tree node.\n"
            "# class TreeNode:\n"
            "#     def __init__(self, val=0, left=None, right=None):\n"
            "#         self.val = val\n"
            "#         self.left = left\n"
            "#         self.right = right\n"
            "def is_valid_bst(root):\n"
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
            "function isValidBST(root) {\n"
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
            "public boolean isValidBST(TreeNode root) {\n"
            "    // Your code here\n"
            "    return false;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    # Build a small BST manually for a smoke test:  2\n"
            "    #                                              / \\\n"
            "    #                                             1   3\n"
            "    root = TreeNode(2, TreeNode(1), TreeNode(3))\n"
            "    print(is_valid_bst(root))  # True"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const root = { val: 2, left: { val: 1, left: null, right: null },\n"
            "                       right: { val: 3, left: null, right: null } };\n"
            "console.log(isValidBST(root));  // true"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        TreeNode root = new TreeNode(2, new TreeNode(1), new TreeNode(3));\n"
            "        System.out.println(s.isValidBST(root));  // true\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": []}, "expected": True,
         "description": "Empty tree — vacuously a valid BST", "tags": ["edge"]},
        {"input": {"root": [1]}, "expected": True,
         "description": "Single node — trivially a valid BST", "tags": ["edge"]},
        {"input": {"root": [2, 1, 3]}, "expected": True,
         "description": "Classic valid 3-node BST: left < root < right", "tags": ["basic"]},
        {"input": {"root": [5, 1, 4, None, None, 3, 6]}, "expected": False,
         "description": "Classic invalid: 4's left child 3 violates the global BST property (3 < 5 but is in 5's right subtree)",
         "tags": ["tricky"]},
        {"input": {"root": [5, 4, 6, None, None, 3, 7]}, "expected": False,
         "description": "Just-parent-check trap: 6's left child 3 looks fine locally (3 < 6) but 3 < 5 in 5's right subtree fails the global invariant",
         "tags": ["tricky"]},
        {"input": {"root": [10, 5, 15, 3, 7, 12, 20, 1, 4, 6, 8, 11, 13, 17, 25]}, "expected": True,
         "description": "Long valid BST — full balanced tree, all bounds satisfied", "tags": ["basic"]},
        {"input": {"root": [10, 5, 15, 3, 7, 12, 20, 1, 4, 6, 8, 11, 13, 9, 25]}, "expected": False,
         "description": "Long invalid BST — node 9 is the left child of 20 (deep in the right subtree of 10), but 9 < 15 violates the global bound for 15's subtree",
         "tags": ["tricky"]},
        {"input": {"root": [2, 1, 2]}, "expected": False,
         "description": "Duplicate value with the root — strict inequality means this is invalid", "tags": ["tricky"]},
        {"input": {"root": [2, 2, 3]}, "expected": False,
         "description": "Duplicate value with the left child — strict inequality fails", "tags": ["edge"]},
        {"input": {"root": [-2147483648]}, "expected": True,
         "description": "INT_MIN as a single-node tree — sentinel bound `-infinity` must be looser than INT_MIN",
         "tags": ["edge"]},
        {"input": {"root": [2147483647]}, "expected": True,
         "description": "INT_MAX as a single-node tree — sentinel bound `+infinity` must be looser than INT_MAX",
         "tags": ["edge"]},
        {"input": {"root": [-2147483648, None, 2147483647]}, "expected": True,
         "description": "INT_MIN root with INT_MAX right child — full integer range, both boundaries used",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Bounds-Pass DFS (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h)",
            "description": (
                "Recurse with an explicit `(low, high)` window. The root starts with `(-inf, +inf)`. When you "
                "descend left, the upper bound becomes the current node's value; when you descend right, the "
                "lower bound becomes the current node's value. At every node, check `low < node.val < high` "
                "(strict). This enforces the BST property *globally*, not just locally. `h` is the tree height — "
                "`O(log n)` for balanced trees, `O(n)` worst case (skewed)."
            ),
            "code": {
                "python": (
                    "def is_valid_bst(root):\n"
                    "    def dfs(node, low, high):\n"
                    "        if node is None:\n"
                    "            return True\n"
                    "        if node.val <= low or node.val >= high:\n"
                    "            return False\n"
                    "        return dfs(node.left, low, node.val) and dfs(node.right, node.val, high)\n"
                    "    return dfs(root, float('-inf'), float('inf'))"
                ),
                "javascript": (
                    "function isValidBST(root) {\n"
                    "    function dfs(node, low, high) {\n"
                    "        if (node === null) return true;\n"
                    "        if (node.val <= low || node.val >= high) return false;\n"
                    "        return dfs(node.left, low, node.val) && dfs(node.right, node.val, high);\n"
                    "    }\n"
                    "    return dfs(root, -Infinity, Infinity);\n"
                    "}"
                ),
                "java": (
                    "public boolean isValidBST(TreeNode root) {\n"
                    "    return dfs(root, null, null);\n"
                    "}\n"
                    "\n"
                    "private boolean dfs(TreeNode node, Integer low, Integer high) {\n"
                    "    if (node == null) return true;\n"
                    "    if ((low != null && node.val <= low) || (high != null && node.val >= high)) return false;\n"
                    "    return dfs(node.left, low, node.val) && dfs(node.right, node.val, high);\n"
                    "}"
                ),
            },
        },
        {
            "title": "In-Order Traversal with Prev Tracker",
            "time_complexity": "O(n)",
            "space_complexity": "O(h)",
            "description": (
                "An in-order traversal of a valid BST visits nodes in *strictly* increasing order. Walk in-order "
                "and keep a single `prev` pointer; if you ever encounter `prev >= curr`, the tree is not a BST. "
                "This is conceptually clean and avoids reasoning about bounds. The same `O(h)` space comes from "
                "the recursion stack (or an explicit stack for the iterative variant)."
            ),
            "code": {
                "python": (
                    "def is_valid_bst(root):\n"
                    "    prev = [float('-inf')]\n"
                    "    def inorder(node):\n"
                    "        if node is None:\n"
                    "            return True\n"
                    "        if not inorder(node.left):\n"
                    "            return False\n"
                    "        if node.val <= prev[0]:\n"
                    "            return False\n"
                    "        prev[0] = node.val\n"
                    "        return inorder(node.right)\n"
                    "    return inorder(root)"
                ),
                "javascript": (
                    "function isValidBST(root) {\n"
                    "    let prev = -Infinity;\n"
                    "    function inorder(node) {\n"
                    "        if (node === null) return true;\n"
                    "        if (!inorder(node.left)) return false;\n"
                    "        if (node.val <= prev) return false;\n"
                    "        prev = node.val;\n"
                    "        return inorder(node.right);\n"
                    "    }\n"
                    "    return inorder(root);\n"
                    "}"
                ),
                "java": (
                    "private Integer prev = null;\n"
                    "\n"
                    "public boolean isValidBST(TreeNode root) {\n"
                    "    prev = null;\n"
                    "    return inorder(root);\n"
                    "}\n"
                    "\n"
                    "private boolean inorder(TreeNode node) {\n"
                    "    if (node == null) return true;\n"
                    "    if (!inorder(node.left)) return false;\n"
                    "    if (prev != null && node.val <= prev) return false;\n"
                    "    prev = node.val;\n"
                    "    return inorder(node.right);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate the BST property carefully: 'every node in the LEFT SUBTREE is strictly less than the node, and every node in the RIGHT SUBTREE is strictly greater'. The word 'subtree' is the trap — it's not just the immediate child.",
        "2. Counter-example to test understanding: `[5,1,4,null,null,3,6]`. Locally `3 < 4 < 6`, but `3` is in `5`'s right subtree and `3 < 5`, so it's invalid. A naive parent-vs-child check fails this.",
        "3. Solution 1 — bounds-pass DFS: thread `(low, high)` through the recursion. Going left shrinks `high` to `node.val`; going right grows `low` to `node.val`. At each node, assert `low < val < high`.",
        "4. Solution 2 — in-order traversal: a BST in-order produces a strictly increasing sequence. Track the previous value and check monotonicity. Same complexity, different framing.",
        "5. Strict inequality is mandatory — duplicates fail. Use `<=`/`>=` against the bound, not `<`/`>`.",
        "6. Initial bounds: use `-inf`/`+inf` (or `None` sentinels in Java) so legitimate INT_MIN/INT_MAX nodes pass. Hardcoding `-2^31` will break the test for an INT_MIN root.",
        "7. Complexity: every node is visited once → `O(n)` time. Space is the recursion depth `O(h)`, which is `O(log n)` balanced and `O(n)` skewed.",
    ],
    "tips": [
        "The single biggest mistake is the local-only check: `node.left.val < node.val < node.right.val`. State out loud that the BST property is global, not local — interviewers love hearing this distinction.",
        "Pick the bounds-pass approach as your primary; it's more obviously correct and easier to explain. Mention in-order traversal as a follow-up — interviewers often nudge toward it.",
        "Use `-inf`/`+inf` (Python) or `Long.MIN_VALUE`/`Long.MAX_VALUE` (Java) as sentinels — never `Integer.MIN_VALUE`/`Integer.MAX_VALUE`, because a legitimate INT_MIN node would fail the strict comparison.",
        "Remember strict inequality. Duplicates are NOT allowed in this problem's definition (LeetCode is explicit). If the interviewer asks 'what if duplicates are allowed?', adjust to `<=` on one side only — never both, or the property breaks.",
        "Iterative in-order with an explicit stack is a great follow-up if asked to avoid recursion. Push left spine, pop, check against `prev`, then push right child's left spine.",
        "Edge cases to verify: empty tree (true), single node (true), two-node trees in both orientations, INT_MIN/INT_MAX, duplicate values.",
        "Common follow-ups: 'recover BST' (LC 99 — two nodes swapped, find them via in-order), 'kth smallest in BST' (in-order, stop at k), 'BST iterator' (LC 173 — lazy in-order).",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Meta", "Bloomberg", "Apple", "Adobe"],
    "topics": ["Tree", "Depth-First Search", "Binary Search Tree", "Binary Tree"],
    "time_complexity": "O(n)",
    "space_complexity": "O(h)",
}


def REFERENCE(root):
    """Take a level-order list, return whether the represented tree is a valid BST."""
    tree = _build(root)
    return _is_valid_bst(tree, float("-inf"), float("inf"))


register(PAYLOAD, REFERENCE)
