"""Subtree of Another Tree — Easy. Tree / DFS / String Matching.

LeetCode 572. The recursive sweet-spot: walk every node of `root`,
ask 'is the subtree rooted here identical to subRoot?' via the
classic isSameTree helper. O(m * n) and easy to write.

The slick follow-up trick: serialize both trees with a delimiter and
*null sentinels* (so [12] and [1, None, 2] don't collide), then ask
'is one a substring of the other?'. KMP turns it into O(m + n).
"""
from collections import deque

from builder.registry import register

from builder._shorthand import level_order_to_verbose, inflate_tree

def _same(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if a["val"] != b["val"]:
        return False
    return _same(a["left"], b["left"]) and _same(a["right"], b["right"])

def _is_subtree(root, sub):
    if sub is None:
        return True
    if root is None:
        return False
    if _same(root, sub):
        return True
    return _is_subtree(root["left"], sub) or _is_subtree(root["right"], sub)

PAYLOAD = {
    "title": "Subtree of Another Tree",
    "difficulty": "Easy",
    "description": (
        "Given the roots of two binary trees `root` and `subRoot`, return `true` if there is a subtree of "
        "`root` with the same structure and node values as `subRoot`, and `false` otherwise.\n\n"
        "A subtree of a binary tree `tree` is a tree consisting of a node in `tree` and all of this node's "
        "descendants. The tree `tree` could also be considered a subtree of itself.\n\n"
        "**Example 1:**\n"
        "- Input: `root = [3,4,5,1,2]`, `subRoot = [4,1,2]`\n"
        "- Output: `true`\n"
        "- Explanation:\n"
        "```\n"
        "      root              subRoot\n"
        "       3                   4\n"
        "      / \\                 / \\\n"
        "     4   5               1   2\n"
        "    / \\\n"
        "   1   2\n"
        "```\n"
        "The subtree rooted at the left child of `root` matches `subRoot` exactly.\n\n"
        "**Example 2:**\n"
        "- Input: `root = [3,4,5,1,2,null,null,null,null,0]`, `subRoot = [4,1,2]`\n"
        "- Output: `false`\n"
        "- Explanation:\n"
        "```\n"
        "         root             subRoot\n"
        "          3                  4\n"
        "         / \\                / \\\n"
        "        4   5              1   2\n"
        "       / \\\n"
        "      1   2\n"
        "         /\n"
        "        0\n"
        "```\n"
        "The candidate match has an extra node `0`, so the structures differ."
    ),
    "hints": [
        "The natural decomposition: walk every node of `root`; at each one ask 'is the subtree rooted here "
        "*identical* to `subRoot`?'. That sub-question is the classic `isSameTree` recursion.",
        "`isSameTree(a, b)` — both null → true; one null → false; values differ → false; otherwise recurse on "
        "both pairs of children. Keep this helper as a separate function — it'll be reused in many tree problems.",
        "Combine: `isSubtree(root, sub) = isSameTree(root, sub) or isSubtree(root.left, sub) or "
        "isSubtree(root.right, sub)`. Time is O(m·n) worst case (m = |root|, n = |sub|).",
        "Slick alternative: serialize each tree by pre-order DFS using a delimiter and a *null sentinel* "
        "(e.g. `,#`). Then `isSubtree` reduces to `subRootStr in rootStr`. The sentinel is critical — without "
        "it, [12] and [1,null,2] would both serialize to '12' and produce false positives.",
        "Substring check with Python's `in` is O(m·n) worst case, but using KMP brings it to O(m + n) — "
        "the standard 'I know a faster algorithm exists' answer for the follow-up.",
    ],
    "constraints": [
        "The number of nodes in `root` is in the range `[1, 2000]`.",
        "The number of nodes in `subRoot` is in the range `[1, 1000]`.",
        "-10⁴ <= Node.val <= 10⁴",
    ],
    "starter_code": {
        "python": (
            "# Definition for a binary tree node.\n"
            "# class TreeNode:\n"
            "#     def __init__(self, val=0, left=None, right=None):\n"
            "#         self.val = val\n"
            "#         self.left = left\n"
            "#         self.right = right\n"
            "def is_subtree(root, subRoot):\n"
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
            "function isSubtree(root, subRoot) {\n"
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
            "public boolean isSubtree(TreeNode root, TreeNode subRoot) {\n"
            "    // Your code here\n"
            "    return false;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    # root = [3,4,5,1,2], subRoot = [4,1,2]\n"
            "    root = TreeNode(3, TreeNode(4, TreeNode(1), TreeNode(2)), TreeNode(5))\n"
            "    sub = TreeNode(4, TreeNode(1), TreeNode(2))\n"
            "    print(is_subtree(root, sub))  # True"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const root = { val: 3,\n"
            "    left: { val: 4, left: { val: 1, left: null, right: null },\n"
            "                    right: { val: 2, left: null, right: null } },\n"
            "    right: { val: 5, left: null, right: null } };\n"
            "const sub = { val: 4, left: { val: 1, left: null, right: null },\n"
            "                       right: { val: 2, left: null, right: null } };\n"
            "console.log(isSubtree(root, sub));  // true"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        TreeNode root = new TreeNode(3,\n"
            "            new TreeNode(4, new TreeNode(1), new TreeNode(2)),\n"
            "            new TreeNode(5));\n"
            "        TreeNode sub = new TreeNode(4, new TreeNode(1), new TreeNode(2));\n"
            "        System.out.println(s.isSubtree(root, sub));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": level_order_to_verbose([3, 4, 5, 1, 2]), "subRoot": level_order_to_verbose([4, 1, 2])}, "expected": True,
         "description": "Classic LeetCode example — subRoot equals the left subtree of root", "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([3, 4, 5, 1, 2, None, None, None, None, 0]), "subRoot": level_order_to_verbose([4, 1, 2])}, "expected": False,
         "description": "Candidate match has an extra leaf — structure differs", "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([1, 1]), "subRoot": level_order_to_verbose([1])}, "expected": True,
         "description": "subRoot is a single leaf — matches any leaf in root", "tags": ["edge"]},
        {"input": {"root": level_order_to_verbose([1, 2, 3]), "subRoot": level_order_to_verbose([1, 2, 3])}, "expected": True,
         "description": "subRoot equals root — a tree is a subtree of itself", "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([]), "subRoot": level_order_to_verbose([1])}, "expected": False,
         "description": "Empty root with non-empty subRoot — cannot match", "tags": ["edge"]},
        {"input": {"root": level_order_to_verbose([1, 2, 3, 4, 5, 6, 7]), "subRoot": level_order_to_verbose([2, 4, 5])}, "expected": True,
         "description": "subRoot is the entire left subtree of a perfect tree", "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([1, 2, 3, 4, 5, 6, 7]), "subRoot": level_order_to_verbose([2, 4])}, "expected": False,
         "description": "Same root value but subRoot is missing the right child — structures differ",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([10, 4, 6, 30, None, None, None, None, 20]), "subRoot": level_order_to_verbose([4, 30])}, "expected": False,
         "description": "subRoot's 30 is a left child but root's 30 has its own left child 20 — mismatch deeper",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([1, 2, 3, None, 4, None, None, None, 5]), "subRoot": level_order_to_verbose([2, None, 4, None, 5])},
         "expected": True,
         "description": "subRoot is a deep right-leaning chain inside root", "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([12]), "subRoot": level_order_to_verbose([1, None, 2])}, "expected": False,
         "description": "Sentinel-discrimination case — naive serialization '12' would falsely match without "
                        "null sentinels",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([-1, -2, -3, -4, -5]), "subRoot": level_order_to_verbose([-2, -4, -5])}, "expected": True,
         "description": "Negative values — algorithm must compare values, not just absolute values",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose(list(range(1, 16))), "subRoot": level_order_to_verbose([3, 6, 7, 12, 13, 14, 15])}, "expected": True,
         "description": "Larger root (perfect tree of 15 nodes) — subRoot is the right subtree",
         "tags": ["large"]},
        {"input": {"root": level_order_to_verbose(list(range(1, 16))), "subRoot": level_order_to_verbose([3, 6, 7])}, "expected": False,
         "description": "Larger root — subRoot has the right values but root's subtree at 3 has more descendants",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "DFS + isSameTree (Canonical)",
            "time_complexity": "O(m * n)",
            "space_complexity": "O(max(h_root, h_sub))",
            "description": (
                "Walk every node in `root`. At each node, run `isSameTree(node, subRoot)`; if any call returns "
                "true, we're done. Otherwise recurse into the left and right children of `root`. Worst case "
                "we run the equality check from m starting points, each taking up to n work."
            ),
            "code": {
                "python": (
                    "def is_same_tree(a, b):\n"
                    "    if a is None and b is None:\n"
                    "        return True\n"
                    "    if a is None or b is None:\n"
                    "        return False\n"
                    "    if a.val != b.val:\n"
                    "        return False\n"
                    "    return is_same_tree(a.left, b.left) and is_same_tree(a.right, b.right)\n"
                    "\n"
                    "def is_subtree(root, subRoot):\n"
                    "    if subRoot is None:\n"
                    "        return True\n"
                    "    if root is None:\n"
                    "        return False\n"
                    "    if is_same_tree(root, subRoot):\n"
                    "        return True\n"
                    "    return is_subtree(root.left, subRoot) or is_subtree(root.right, subRoot)"
                ),
                "javascript": (
                    "function isSameTree(a, b) {\n"
                    "    if (a === null && b === null) return true;\n"
                    "    if (a === null || b === null) return false;\n"
                    "    if (a.val !== b.val) return false;\n"
                    "    return isSameTree(a.left, b.left) && isSameTree(a.right, b.right);\n"
                    "}\n"
                    "\n"
                    "function isSubtree(root, subRoot) {\n"
                    "    if (subRoot === null) return true;\n"
                    "    if (root === null) return false;\n"
                    "    if (isSameTree(root, subRoot)) return true;\n"
                    "    return isSubtree(root.left, subRoot) || isSubtree(root.right, subRoot);\n"
                    "}"
                ),
                "java": (
                    "private boolean isSameTree(TreeNode a, TreeNode b) {\n"
                    "    if (a == null && b == null) return true;\n"
                    "    if (a == null || b == null) return false;\n"
                    "    if (a.val != b.val) return false;\n"
                    "    return isSameTree(a.left, b.left) && isSameTree(a.right, b.right);\n"
                    "}\n"
                    "\n"
                    "public boolean isSubtree(TreeNode root, TreeNode subRoot) {\n"
                    "    if (subRoot == null) return true;\n"
                    "    if (root == null) return false;\n"
                    "    if (isSameTree(root, subRoot)) return true;\n"
                    "    return isSubtree(root.left, subRoot) || isSubtree(root.right, subRoot);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Serialize + Substring with Null Sentinels (Optimal with KMP)",
            "time_complexity": "O(m + n) with KMP, O(m * n) with naive `in`",
            "space_complexity": "O(m + n)",
            "description": (
                "Serialize each tree with a pre-order DFS, prepending a delimiter and using a null sentinel "
                "for missing children. Then `subRoot` is a subtree of `root` iff `serialize(subRoot)` is a "
                "*substring* of `serialize(root)`. The leading delimiter and null sentinels prevent false "
                "matches like `[12]` vs `[1, null, 2]`. Naive substring is still O(m·n), but plugging in KMP "
                "(or any linear string-matching algorithm) gives O(m + n)."
            ),
            "code": {
                "python": (
                    "def is_subtree(root, subRoot):\n"
                    "    def serialize(node):\n"
                    "        if node is None:\n"
                    "            return ',#'\n"
                    "        return ',' + str(node.val) + serialize(node.left) + serialize(node.right)\n"
                    "    return serialize(subRoot) in serialize(root)"
                ),
                "javascript": (
                    "function isSubtree(root, subRoot) {\n"
                    "    const serialize = (node) =>\n"
                    "        node === null ? ',#' : ',' + node.val + serialize(node.left) + serialize(node.right);\n"
                    "    return serialize(root).includes(serialize(subRoot));\n"
                    "}"
                ),
                "java": (
                    "public boolean isSubtree(TreeNode root, TreeNode subRoot) {\n"
                    "    return serialize(root).contains(serialize(subRoot));\n"
                    "}\n"
                    "private String serialize(TreeNode node) {\n"
                    "    if (node == null) return \",#\";\n"
                    "    return \",\" + node.val + serialize(node.left) + serialize(node.right);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: find any node in `root` whose subtree is structurally identical to `subRoot`.",
        "2. Decompose: 'is subtree of' = (walk every node) × (test identity at that node). The identity test is `isSameTree`.",
        "3. `isSameTree(a, b)` is the standard double-recursion: both null → true, one null → false, vals differ → false, else recurse on both child pairs.",
        "4. Outer recursion: try matching at `root`; if not, try the left subtree, else the right. Stop early on success.",
        "5. Complexity: O(m·n) worst case (m starting points, n equality work). Acceptable for the stated constraints (m ≤ 2000, n ≤ 1000).",
        "6. Follow-up — faster: serialize both trees with a delimiter + null sentinels and reduce to substring matching. KMP gives O(m + n).",
        "7. The sentinel is non-negotiable in the serialization approach: without it, `[12]` and `[1, null, 2]` collide. The leading delimiter prevents prefix-of-value collisions like `2` matching inside `12`.",
    ],
    "tips": [
        "Keep `isSameTree` as a separate helper. It's a reusable building block (LC 100) and makes the code easy to read.",
        "Don't forget `subRoot is None → True`. By the LeetCode definition the empty tree is a subtree of any tree, though the constraints in this problem guarantee `subRoot` has at least one node.",
        "Don't forget `root is None → False` (when `subRoot` is non-null). Falling through without this guard crashes on the recursive calls.",
        "When mentioning the serialization trick, *always* call out the null sentinel explicitly. Interviewers love this detail because it's the difference between a working solution and one that fails on `[12]` vs `[1,null,2]`.",
        "If the interviewer asks for sub-O(m·n), KMP on the serialized strings is the answer. For an even fancier alternative, mention Merkle hashing — hash each subtree by `(val, left_hash, right_hash)` and check membership in O(m + n) (with collision risk).",
        "Watch for negative values: when serializing, `,−1` and `,1` differ, so the leading delimiter handles sign. Don't use `+` as a delimiter — it appears in expressions but not in stringified ints, so `,` or `#` is safe.",
    ],
    "companies": ["Amazon", "Microsoft", "Facebook", "Google", "Apple"],
    "topics": ["Tree", "Depth-First Search", "Binary Tree", "String Matching", "Hash Function"],
    "time_complexity": "O(m * n)",
    "space_complexity": "O(max(h_root, h_sub))",
    "entry": {
        "kind": "tree",
        "name": "is_subtree",
        "params": [
            {"name": "root", "type": "node"},
            {"name": "subRoot", "type": "node"},
        ],
    },
}

def REFERENCE(root, subRoot):
    """Take two level-order lists, return whether subRoot is a subtree of root."""
    return _is_subtree(inflate_tree(root), inflate_tree(subRoot))

register(PAYLOAD, REFERENCE)
