"""Diameter of Binary Tree — Easy. Trees / DFS.

LeetCode 543. The trick: at each node compute the *height* of its left and
right subtrees and update a global maximum with `left + right` (the path
that turns at this node). Returning the height upward while updating a
side-effect maximum keeps the whole thing O(n). Naive solution recomputes
height at every node — O(n^2) — and is a useful contrast.

Input is the binary tree root; output is the diameter measured in *edges*.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Diameter of Binary Tree",
    "difficulty": "Easy",
    "description": (
        "Given the `root` of a binary tree, return the **length of the diameter** of the tree.\n\n"
        "The diameter is the **length of the longest path between any two nodes** in the tree. "
        "This path may or may not pass through the root.\n\n"
        "The **length** of a path is the **number of edges** between its endpoints (so a single "
        "node has diameter `0`, two connected nodes have diameter `1`).\n\n"
        "**Example 1:**\n"
        "```\n"
        "Tree:    1\n"
        "        / \\\n"
        "       2   3\n"
        "      / \\\n"
        "     4   5\n"
        "```\n"
        "- Input: `root` is the tree shown above\n"
        "- Output: `3`\n"
        "- Explanation: the longest path is `4 -> 2 -> 1 -> 3` (or `5 -> 2 -> 1 -> 3`), which has "
        "**3 edges**.\n\n"
        "**Example 2:**\n"
        "```\n"
        "Tree:    1\n"
        "        /\n"
        "       2\n"
        "```\n"
        "- Input: `root` is the tree shown above\n"
        "- Output: `1`\n"
        "- Explanation: the only path of nonzero length is `2 -> 1`, which has **1 edge**.\n\n"
        "Empty tree returns `0`."
    ),
    "hints": [
        "The longest path through a node `n` has length `height(n.left) + height(n.right)` (in edges) — "
        "because you climb to `n` from one subtree and descend into the other.",
        "Walk every node and track the maximum of that quantity across all nodes. The overall diameter is the "
        "best `left_height + right_height` seen anywhere in the tree.",
        "Don't forget that the longest path may not pass through the root — it can turn at any internal node. "
        "That's why you must check at every node, not just the top.",
        "Use a single DFS that returns the **height** of each subtree (in edges: `0` for a leaf, `-1` for a "
        "missing child if you prefer that convention; or `0` for `None` and `1 + max(...)` for nodes if you "
        "use 'height in nodes'). Update a shared `best` (e.g., `self.best` or a list/cell) as a side effect.",
        "Avoid the O(n^2) trap: computing `height` independently at every node walks each subtree multiple "
        "times. A single post-order pass computes the height once per node and updates the global at the same "
        "time.",
    ],
    "constraints": [
        "The number of nodes in the tree is in the range `[0, 10^4]`.",
        "-100 <= Node.val <= 100",
        "The diameter is measured in **edges**, not nodes.",
    ],
    "starter_code": {
        "python": (
            "# `root` is a TreeNode (or None).\n"
            "# Return the diameter (number of edges on the longest path) as an int.\n"
            "#\n"
            "# Hint: a class with `self.best = 0` (or a list cell) lets a recursive helper\n"
            "# update a shared maximum while returning each subtree's height upward.\n"
            "def diameter_of_binary_tree(root):\n"
            "    # Your code here\n"
            "    pass"
        ),
        "javascript": (
            "// `root` is a TreeNode (or null).\n"
            "// Return the diameter (number of edges on the longest path) as a number.\n"
            "//\n"
            "// Hint: capture a `best` variable in a closure (or use an outer `let best = 0`)\n"
            "// and have the recursive helper update it while returning the subtree height.\n"
            "function diameterOfBinaryTree(root) {\n"
            "    // Your code here\n"
            "}"
        ),
        "java": (
            "// `root` is a TreeNode (or null).\n"
            "// Return the diameter (number of edges on the longest path) as an int.\n"
            "//\n"
            "// Hint: an instance field `int best = 0` lets a recursive helper\n"
            "// update a shared maximum while returning each subtree's height upward.\n"
            "public int diameterOfBinaryTree(TreeNode root) {\n"
            "    // Your code here\n"
            "    return 0;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    # The platform supplies TreeNode roots when running submissions.\n"
            "    pass"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "// The platform supplies TreeNode roots when running submissions."
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        // The platform supplies TreeNode roots when running submissions.\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": []}, "expected": 0,
         "description": "Empty tree → diameter 0", "tags": ["edge"]},
        {"input": {"root": [1]}, "expected": 0,
         "description": "Single node — no edges → diameter 0", "tags": ["edge"]},
        {"input": {"root": [1, 2]}, "expected": 1,
         "description": "Two nodes — one edge → diameter 1", "tags": ["edge"]},
        {"input": {"root": [1, 2, 3, 4, 5]}, "expected": 3,
         "description": "Classic LeetCode example — path 4→2→1→3 has 3 edges", "tags": ["basic"]},
        {"input": {"root": [1, 2, None, 3, None, 4, None, 5]}, "expected": 4,
         "description": "Left-skewed chain of 5 nodes → 4 edges", "tags": ["edge"]},
        {"input": {"root": [1, None, 2, None, 3, None, 4, None, 5]}, "expected": 4,
         "description": "Right-skewed chain of 5 nodes → 4 edges", "tags": ["edge"]},
        {"input": {"root": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}, "expected": 6,
         "description": "Perfect balanced tree of depth 4 (15 nodes) → 6 edges (3 down + 3 up through root)",
         "tags": ["basic"]},
        {"input": {"root": [1, 2, 3, 4, 5, None, None, 6, None, None, 7, 8]}, "expected": 5,
         "description": "Diameter does not pass through root — longest path lives inside the left subtree "
                        "(6→4→2→5→7 or similar)",
         "tags": ["tricky"]},
        {"input": {"root": [1, 2, 3, None, 4, None, 5, 6, None, None, 7]}, "expected": 6,
         "description": "Tree with nulls scattered — longest path crosses root via deepest leaves on each side",
         "tags": ["tricky"]},
        {"input": {"root": [1, 2, 3, 4, 5, 6, 7]}, "expected": 4,
         "description": "Perfect binary tree of depth 3 (7 nodes) → 4 edges through the root",
         "tags": ["basic"]},
        {"input": {"root": [0, -1, 1, -2, None, None, 2, -3, None, None, 3]}, "expected": 6,
         "description": "Negative values don't affect structure; deep left + deep right through root → 6 edges",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "DFS Height with Side-Effect Max (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h) recursion stack — O(log n) balanced, O(n) skewed",
            "description": (
                "A single post-order DFS. The helper returns the **height** of the subtree it just walked. "
                "While computing that height, it also updates a shared `best` with `left_height + "
                "right_height` — the length (in edges) of the longest path that bends at the current node. "
                "Each node is visited exactly once, so total work is O(n)."
            ),
            "code": {
                "python": (
                    "def diameter_of_binary_tree(root):\n"
                    "    best = [0]\n"
                    "    def height(n):\n"
                    "        if n is None:\n"
                    "            return 0\n"
                    "        l = height(n.left)\n"
                    "        r = height(n.right)\n"
                    "        if l + r > best[0]:\n"
                    "            best[0] = l + r\n"
                    "        return 1 + max(l, r)\n"
                    "    height(root)\n"
                    "    return best[0]"
                ),
                "javascript": (
                    "function diameterOfBinaryTree(root) {\n"
                    "    let best = 0;\n"
                    "    const height = (n) => {\n"
                    "        if (n === null) return 0;\n"
                    "        const l = height(n.left);\n"
                    "        const r = height(n.right);\n"
                    "        if (l + r > best) best = l + r;\n"
                    "        return 1 + Math.max(l, r);\n"
                    "    };\n"
                    "    height(root);\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "class Solution {\n"
                    "    private int best = 0;\n"
                    "    public int diameterOfBinaryTree(TreeNode root) {\n"
                    "        height(root);\n"
                    "        return best;\n"
                    "    }\n"
                    "    private int height(TreeNode n) {\n"
                    "        if (n == null) return 0;\n"
                    "        int l = height(n.left);\n"
                    "        int r = height(n.right);\n"
                    "        if (l + r > best) best = l + r;\n"
                    "        return 1 + Math.max(l, r);\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Naive Per-Node Height Recomputation",
            "time_complexity": "O(n^2)",
            "space_complexity": "O(h)",
            "description": (
                "Walk every node; at each one, compute `height(left) + height(right)` from scratch and "
                "track the max. Correct but quadratic — `height` re-traverses the same subtrees from "
                "every ancestor. Worth knowing as a baseline so you can articulate why the optimal "
                "version (one DFS that returns height **and** updates the max) is asymptotically better."
            ),
            "code": {
                "python": (
                    "def diameter_of_binary_tree(root):\n"
                    "    def height(n):\n"
                    "        if n is None:\n"
                    "            return 0\n"
                    "        return 1 + max(height(n.left), height(n.right))\n"
                    "    best = 0\n"
                    "    def visit(n):\n"
                    "        nonlocal best\n"
                    "        if n is None:\n"
                    "            return\n"
                    "        local = height(n.left) + height(n.right)\n"
                    "        if local > best:\n"
                    "            best = local\n"
                    "        visit(n.left)\n"
                    "        visit(n.right)\n"
                    "    visit(root)\n"
                    "    return best"
                ),
                "javascript": (
                    "function diameterOfBinaryTree(root) {\n"
                    "    const height = (n) => n === null ? 0 : 1 + Math.max(height(n.left), height(n.right));\n"
                    "    let best = 0;\n"
                    "    const visit = (n) => {\n"
                    "        if (n === null) return;\n"
                    "        const local = height(n.left) + height(n.right);\n"
                    "        if (local > best) best = local;\n"
                    "        visit(n.left);\n"
                    "        visit(n.right);\n"
                    "    };\n"
                    "    visit(root);\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "class Solution {\n"
                    "    public int diameterOfBinaryTree(TreeNode root) {\n"
                    "        if (root == null) return 0;\n"
                    "        int local = height(root.left) + height(root.right);\n"
                    "        int leftBest  = diameterOfBinaryTree(root.left);\n"
                    "        int rightBest = diameterOfBinaryTree(root.right);\n"
                    "        return Math.max(local, Math.max(leftBest, rightBest));\n"
                    "    }\n"
                    "    private int height(TreeNode n) {\n"
                    "        if (n == null) return 0;\n"
                    "        return 1 + Math.max(height(n.left), height(n.right));\n"
                    "    }\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: longest path in edges between any two nodes; the path may turn at any node, not "
        "necessarily the root.",
        "2. Key insight: at every node `n`, the longest path that **bends at `n`** has length "
        "`height(left) + height(right)` (edges). The overall answer is the max of that across all nodes.",
        "3. Naive: compute `height` at every node and track a max → O(n^2) because every subtree is "
        "walked once per ancestor.",
        "4. Optimal: one post-order DFS. The recursive call returns the height of the subtree it walked; "
        "while it's there, update a shared `best` with `left + right`. One visit per node → O(n).",
        "5. Edge cases: empty tree → 0; single node → 0; two-node tree → 1. The 'edges, not nodes' wording "
        "is the most-missed detail — clarify with the interviewer if unsure.",
        "6. Complexity: O(n) time, O(h) recursion stack. For 10^4 skewed nodes mention an iterative "
        "post-order with an explicit stack as a safety follow-up.",
    ],
    "tips": [
        "Edges, not nodes — re-read the prompt. A two-node tree has diameter 1, not 2. This trips up "
        "more candidates than the algorithm itself.",
        "The diameter does NOT have to pass through the root. The skinny-spine-with-bushy-subtree case "
        "(test case 'diameter does not pass through root') is the standard interviewer trap.",
        "If you reach for a global variable in Python, `self.best` (in a class), `nonlocal best`, or a "
        "single-element list `best = [0]` all work. Pick whichever you'll explain most fluently.",
        "When asked for complexity, walk through *why* the naive version is O(n^2): each `height` call "
        "is O(size_of_subtree), and you call it at every node. The optimal version folds those two passes "
        "into one.",
        "Common follow-up: 'Diameter of an N-ary tree' (LC 1522) — same idea, but at each node you take "
        "the **two largest** child heights and sum them.",
        "Another common follow-up: 'Binary tree maximum path sum' (LC 124) — same recursive shape, but "
        "you track sum-of-values instead of height, and clamp negative subtree contributions to 0.",
    ],
    "companies": ["Facebook", "Amazon", "Google", "Microsoft", "Apple", "Bloomberg"],
    "topics": ["Tree", "Depth-First Search", "Binary Tree", "Recursion"],
    "time_complexity": "O(n)",
    "space_complexity": "O(h)",
    "entry": {
        "kind": "tree",
        "name": "diameter_of_binary_tree",
        "params": [
            {"name": "root", "type": "node"},
        ],
        "input_shape": "tree_level_order",
    },
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


def REFERENCE(root):
    """Return the diameter of the tree (number of edges on the longest path)."""
    node = _from_level(root)
    best = [0]

    def height(n):
        if n is None:
            return 0
        l = height(n.left)
        r = height(n.right)
        if l + r > best[0]:
            best[0] = l + r
        return 1 + max(l, r)

    height(node)
    return best[0]


register(PAYLOAD, REFERENCE)
