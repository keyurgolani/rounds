"""Lowest Common Ancestor of a BST — Easy. Tree / BST / DFS.

LeetCode 235. The BST property collapses a general LCA problem (LC 236)
into a single descent: at each node, compare both target values to the
current node's value. If both are smaller, go left; both larger, go
right; otherwise the current node is the split point — and therefore
the LCA.

Inputs use LeetCode level-order with `null` for missing nodes; `p` and
`q` are passed as values (not node references) for serialization
sanity. The reference returns the LCA's value as an int.
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


def _lca(root, p, q):
    cur = root
    while cur is not None:
        if p < cur["val"] and q < cur["val"]:
            cur = cur["left"]
        elif p > cur["val"] and q > cur["val"]:
            cur = cur["right"]
        else:
            return cur["val"]
    return None


PAYLOAD = {
    "title": "Lowest Common Ancestor of a BST",
    "difficulty": "Easy",
    "description": (
        "Given a **binary search tree** (BST) and two values `p` and `q` that exist in the tree, return the "
        "**lowest common ancestor** (LCA) of the two nodes. The LCA is defined as the *lowest* node in the "
        "tree that has both `p` and `q` as descendants (where a node is allowed to be a descendant of "
        "itself).\n\n"
        "The input/output use LeetCode level-order serialization where `null` denotes a missing child.\n\n"
        "**Example 1:**\n"
        "- Input: `root = [6,2,8,0,4,7,9,null,null,3,5]`, `p = 2`, `q = 8`\n"
        "- Output: `6`\n"
        "- Explanation:\n"
        "```\n"
        "         6              <- LCA(2, 8) = 6\n"
        "        / \\\n"
        "       2   8\n"
        "      / \\ / \\\n"
        "     0  4 7  9\n"
        "       / \\\n"
        "      3   5\n"
        "```\n"
        "  `2` is in the left subtree of `6` and `8` is in the right subtree, so `6` is the split point.\n\n"
        "**Example 2:**\n"
        "- Input: `root = [6,2,8,0,4,7,9,null,null,3,5]`, `p = 2`, `q = 4`\n"
        "- Output: `2`\n"
        "- Explanation: a node may be a descendant of itself — `4` lies in the left subtree of `2`, so the "
        "LCA is `2` itself.\n"
        "```\n"
        "         6\n"
        "        / \\\n"
        "       2   8         <- LCA(2, 4) = 2 (one is the ancestor of the other)\n"
        "      / \\\n"
        "     0  4\n"
        "       / \\\n"
        "      3   5\n"
        "```"
    ),
    "hints": [
        "Use the BST invariant: every value in the left subtree is less than the node, and every value in "
        "the right subtree is greater. The two target values either *split* at some node or one is an "
        "ancestor of the other.",
        "If both `p` and `q` are **less than** the current node's value, the LCA must be in the left "
        "subtree — descend left.",
        "If both `p` and `q` are **greater than** the current node's value, the LCA must be in the right "
        "subtree — descend right.",
        "Otherwise (`p` and `q` straddle the current value, or one equals it), the current node *is* the "
        "LCA — return it immediately.",
        "Iterative beats recursive here: the descent is tail-recursive, so a `while` loop gives `O(1)` "
        "auxiliary space versus `O(h)` for the call stack. Both are `O(h)` time.",
    ],
    "constraints": [
        "The number of nodes is in the range `[2, 10^5]`.",
        "All `Node.val` are unique.",
        "Both `p` and `q` exist in the BST and `p != q`.",
    ],
    "starter_code": {
        "python": (
            "# Definition for a binary tree node.\n"
            "# class TreeNode:\n"
            "#     def __init__(self, val=0, left=None, right=None):\n"
            "#         self.val = val\n"
            "#         self.left = left\n"
            "#         self.right = right\n"
            "def lowest_common_ancestor(root, p, q):\n"
            "    # Your code here. Return the LCA node (or its value).\n"
            "    pass"
        ),
        "javascript": (
            "// Definition for a binary tree node.\n"
            "// function TreeNode(val, left, right) {\n"
            "//     this.val = (val === undefined ? 0 : val);\n"
            "//     this.left = (left === undefined ? null : left);\n"
            "//     this.right = (right === undefined ? null : right);\n"
            "// }\n"
            "function lowestCommonAncestor(root, p, q) {\n"
            "    // Your code here. Return the LCA node.\n"
            "}"
        ),
        "java": (
            "/**\n"
            " * Definition for a binary tree node.\n"
            " * public class TreeNode {\n"
            " *     int val;\n"
            " *     TreeNode left;\n"
            " *     TreeNode right;\n"
            " *     TreeNode(int x) { val = x; }\n"
            " * }\n"
            " */\n"
            "public TreeNode lowestCommonAncestor(TreeNode root, TreeNode p, TreeNode q) {\n"
            "    // Your code here\n"
            "    return null;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    #         6\n"
            "    #        / \\\n"
            "    #       2   8\n"
            "    root = TreeNode(6, TreeNode(2), TreeNode(8))\n"
            "    p, q = root.left, root.right\n"
            "    lca = lowest_common_ancestor(root, p, q)\n"
            "    print(lca.val)  # 6"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const root = { val: 6,\n"
            "    left:  { val: 2, left: null, right: null },\n"
            "    right: { val: 8, left: null, right: null } };\n"
            "const lca = lowestCommonAncestor(root, root.left, root.right);\n"
            "console.log(lca.val);  // 6"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        TreeNode root = new TreeNode(6);\n"
            "        root.left = new TreeNode(2);\n"
            "        root.right = new TreeNode(8);\n"
            "        TreeNode lca = s.lowestCommonAncestor(root, root.left, root.right);\n"
            "        System.out.println(lca.val);  // 6\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": [6, 2, 8, 0, 4, 7, 9, None, None, 3, 5], "p": 2, "q": 8}, "expected": 6,
         "description": "Classic LeetCode example — p and q split at the root", "tags": ["basic"]},
        {"input": {"root": [6, 2, 8, 0, 4, 7, 9, None, None, 3, 5], "p": 2, "q": 4}, "expected": 2,
         "description": "One target is an ancestor of the other — LCA is the ancestor itself",
         "tags": ["basic"]},
        {"input": {"root": [6, 2, 8, 0, 4, 7, 9, None, None, 3, 5], "p": 3, "q": 5}, "expected": 4,
         "description": "Both targets are deep — split happens at node 4", "tags": ["basic"]},
        {"input": {"root": [6, 2, 8, 0, 4, 7, 9, None, None, 3, 5], "p": 7, "q": 9}, "expected": 8,
         "description": "Both targets in the right subtree — LCA is 8", "tags": ["basic"]},
        {"input": {"root": [6, 2, 8, 0, 4, 7, 9, None, None, 3, 5], "p": 0, "q": 9}, "expected": 6,
         "description": "Min and max leaves — LCA is the root", "tags": ["basic"]},
        {"input": {"root": [2, 1], "p": 1, "q": 2}, "expected": 2,
         "description": "Two-node tree — root is the ancestor of its child", "tags": ["edge"]},
        {"input": {"root": [2, 1, 3], "p": 1, "q": 3}, "expected": 2,
         "description": "Three-node tree — split at the root", "tags": ["edge"]},
        {"input": {"root": [5, 4, None, 3, None, 2, None, 1], "p": 1, "q": 4}, "expected": 4,
         "description": "Left-only chain — LCA is the higher of the two on the chain", "tags": ["edge"]},
        {"input": {"root": [1, None, 2, None, 3, None, 4, None, 5], "p": 3, "q": 5}, "expected": 3,
         "description": "Right-only chain — LCA is the higher of the two on the chain", "tags": ["edge"]},
        {"input": {"root": [20, 10, 30, 5, 15, 25, 35, None, None, 12, 17], "p": 12, "q": 17},
         "expected": 15,
         "description": "Deeper BST — split happens at depth 2", "tags": ["tricky"]},
        {"input": {"root": [20, 10, 30, 5, 15, 25, 35, None, None, 12, 17], "p": 5, "q": 35},
         "expected": 20,
         "description": "Targets on opposite extremes — LCA is the root", "tags": ["tricky"]},
        {"input": {"root": [20, 10, 30, 5, 15, 25, 35, None, None, 12, 17], "p": 10, "q": 12},
         "expected": 10,
         "description": "Root of a subtree is itself one of the targets", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Iterative BST-Walk (Optimal)",
            "time_complexity": "O(h)",
            "space_complexity": "O(1)",
            "description": (
                "Walk down from the root. At each node, if both `p` and `q` are smaller, descend left; if "
                "both are larger, descend right; otherwise we've found the split point — that's the LCA. "
                "No recursion stack, so auxiliary space is `O(1)`. `h` is the tree height: `O(log n)` "
                "balanced, `O(n)` worst case."
            ),
            "code": {
                "python": (
                    "def lowest_common_ancestor(root, p, q):\n"
                    "    pv, qv = p.val, q.val\n"
                    "    cur = root\n"
                    "    while cur is not None:\n"
                    "        if pv < cur.val and qv < cur.val:\n"
                    "            cur = cur.left\n"
                    "        elif pv > cur.val and qv > cur.val:\n"
                    "            cur = cur.right\n"
                    "        else:\n"
                    "            return cur\n"
                    "    return None"
                ),
                "javascript": (
                    "function lowestCommonAncestor(root, p, q) {\n"
                    "    let cur = root;\n"
                    "    while (cur !== null) {\n"
                    "        if (p.val < cur.val && q.val < cur.val) {\n"
                    "            cur = cur.left;\n"
                    "        } else if (p.val > cur.val && q.val > cur.val) {\n"
                    "            cur = cur.right;\n"
                    "        } else {\n"
                    "            return cur;\n"
                    "        }\n"
                    "    }\n"
                    "    return null;\n"
                    "}"
                ),
                "java": (
                    "public TreeNode lowestCommonAncestor(TreeNode root, TreeNode p, TreeNode q) {\n"
                    "    TreeNode cur = root;\n"
                    "    while (cur != null) {\n"
                    "        if (p.val < cur.val && q.val < cur.val) {\n"
                    "            cur = cur.left;\n"
                    "        } else if (p.val > cur.val && q.val > cur.val) {\n"
                    "            cur = cur.right;\n"
                    "        } else {\n"
                    "            return cur;\n"
                    "        }\n"
                    "    }\n"
                    "    return null;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Recursive BST-Walk",
            "time_complexity": "O(h)",
            "space_complexity": "O(h)",
            "description": (
                "Same idea expressed recursively: if both values are smaller than the current node, recurse "
                "left; if both larger, recurse right; otherwise the current node is the split point. The "
                "extra `O(h)` space is the recursion stack. Slightly cleaner code but strictly worse on "
                "memory than the iterative version."
            ),
            "code": {
                "python": (
                    "def lowest_common_ancestor(root, p, q):\n"
                    "    if p.val < root.val and q.val < root.val:\n"
                    "        return lowest_common_ancestor(root.left, p, q)\n"
                    "    if p.val > root.val and q.val > root.val:\n"
                    "        return lowest_common_ancestor(root.right, p, q)\n"
                    "    return root"
                ),
                "javascript": (
                    "function lowestCommonAncestor(root, p, q) {\n"
                    "    if (p.val < root.val && q.val < root.val) {\n"
                    "        return lowestCommonAncestor(root.left, p, q);\n"
                    "    }\n"
                    "    if (p.val > root.val && q.val > root.val) {\n"
                    "        return lowestCommonAncestor(root.right, p, q);\n"
                    "    }\n"
                    "    return root;\n"
                    "}"
                ),
                "java": (
                    "public TreeNode lowestCommonAncestor(TreeNode root, TreeNode p, TreeNode q) {\n"
                    "    if (p.val < root.val && q.val < root.val) {\n"
                    "        return lowestCommonAncestor(root.left, p, q);\n"
                    "    }\n"
                    "    if (p.val > root.val && q.val > root.val) {\n"
                    "        return lowestCommonAncestor(root.right, p, q);\n"
                    "    }\n"
                    "    return root;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: find the *deepest* node that has both `p` and `q` somewhere in its subtree (a node "
        "counts as its own descendant).",
        "2. The general LCA problem (LC 236) needs a post-order DFS — but this is a BST, and that extra "
        "structure is the whole hint.",
        "3. BST property: at any node `n`, everything in `left(n)` is `< n.val`, everything in `right(n)` "
        "is `> n.val`. So `p` and `q` end up in the same subtree only when both are `< n.val` or both are "
        "`> n.val`.",
        "4. Therefore the LCA is exactly the first node where `p` and `q` are *not* both on the same side "
        "— i.e., they straddle the value, or one of them equals it.",
        "5. Implementation: descend from root, comparing both target values to the current node. Three "
        "cases: both smaller (go left), both larger (go right), otherwise return current.",
        "6. Iterative is preferable to recursive: same `O(h)` time, but `O(1)` extra space instead of "
        "`O(h)` for the call stack. The descent is tail-recursive, so the iterative form is mechanical.",
        "7. Worst-case height for a skewed BST is `O(n)`, so the bound is `O(h)` (`O(log n)` balanced, "
        "`O(n)` skewed) — be precise about this in the interview.",
    ],
    "tips": [
        "Lead with the BST invariant out loud — interviewers want to hear *why* this is easier than the "
        "general LCA problem. The split-point intuition (`p < n < q` or vice versa) is the core insight.",
        "Prefer the iterative version. It's the same number of lines and saves the `O(h)` stack — there's "
        "no reason to recurse on a tail call.",
        "Don't normalize `p` and `q` (e.g., swap so `p < q`). It's unnecessary: the both-less / both-greater "
        "tests work either way.",
        "Watch the `<= / <` boundary. The condition is **strict** inequality on both sides; the moment "
        "`cur.val` equals one of the targets, that node *is* the LCA (since the target is its own "
        "descendant).",
        "Common follow-up: 'What if it's a general binary tree (not a BST)?' That's LC 236 — switch to a "
        "post-order DFS that returns `p`, `q`, or both. Mentioning this earns points.",
        "Another follow-up: 'What if `p` or `q` may not exist?' Add a guard pass to verify both are "
        "present, or fold the check into a single traversal that returns a found-flag tuple.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Facebook", "Apple", "LinkedIn"],
    "topics": ["Tree", "Binary Search Tree", "Depth-First Search", "Binary Tree"],
    "time_complexity": "O(h)",
    "space_complexity": "O(1)",
}


def REFERENCE(root, p, q):
    """Build the BST from the level-order list and return the LCA's value."""
    tree = _build(root)
    return _lca(tree, p, q)


register(PAYLOAD, REFERENCE)
