"""Symmetric Tree — Easy. Tree / DFS / BFS.

LeetCode 101. The textbook follow-up to Same Tree (LC 100): the same
paired-recursion skeleton, but the children are crossed — left-of-A
mirrors right-of-B, and right-of-A mirrors left-of-B. A clean check
that the candidate has internalised *why* the recursion in LC 100
works rather than memorising the literal pattern.

The user-facing function receives a TreeNode root; the build-time
reference still accepts raw array fixtures and returns a bool.
"""
from builder.registry import register

from builder._shorthand import level_order_to_verbose, inflate_tree

def _is_mirror(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if a["val"] != b["val"]:
        return False
    return _is_mirror(a["left"], b["right"]) and _is_mirror(a["right"], b["left"])

PAYLOAD = {
    "title": "Symmetric Tree",
    "difficulty": "Easy",
    "description": (
        "Given the `root` of a binary tree, check whether it is a **mirror of itself** — i.e., "
        "**symmetric** around its centre.\n\n"
        "**Example 1:**\n"
        "- Input: `root = [1,2,2,3,4,4,3]`\n"
        "- Output: `true`\n"
        "- Explanation: The left and right subtrees are mirror images of each other.\n"
        "```\n"
        "         1\n"
        "        / \\\n"
        "       2   2\n"
        "      / \\ / \\\n"
        "     3  4 4  3\n"
        "```\n\n"
        "**Example 2:**\n"
        "- Input: `root = [1,2,2,null,3,null,3]`\n"
        "- Output: `false`\n"
        "- Explanation: Both `3`s sit on the *right* side of their respective parents — that's a "
        "translation, not a reflection.\n"
        "```\n"
        "         1\n"
        "        / \\\n"
        "       2   2\n"
        "        \\   \\\n"
        "         3   3\n"
        "```"
    ),
    "hints": [
        "A tree is symmetric iff its left and right subtrees are *mirror images* of each other. "
        "Reduce the problem from one tree to a paired check on two subtrees.",
        "Define `mirror(a, b)`: True iff `a.val == b.val` AND `mirror(a.left, b.right)` AND "
        "`mirror(a.right, b.left)`. Note the *crossed* recursion — left pairs with right.",
        "Three base cases: both null → True; exactly one null → False; values differ → False. "
        "Same skeleton as Same Tree (LC 100), only the recursive children are swapped.",
        "Iterative version: BFS with a queue of *pairs*. Seed with `(root.left, root.right)`, then "
        "for each `(a, b)` popped, enqueue `(a.left, b.right)` and `(a.right, b.left)`.",
        "Edge case: an empty tree is vacuously symmetric — return True. A single node is also "
        "symmetric (no children to compare).",
    ],
    "constraints": [
        "The number of nodes in the tree is in the range `[0, 1000]`.",
        "-100 <= Node.val <= 100",
        "`root` is either `null` or the root of a valid binary tree.",
    ],
    "starter_code": {
        "python": (
            "# Definition for a binary tree node.\n"
            "# class TreeNode:\n"
            "#     def __init__(self, val=0, left=None, right=None):\n"
            "#         self.val = val\n"
            "#         self.left = left\n"
            "#         self.right = right\n"
            "def is_symmetric(root):\n"
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
            "function isSymmetric(root) {\n"
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
            "public boolean isSymmetric(TreeNode root) {\n"
            "    // Your code here\n"
            "    return false;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    # Symmetric:        1\n"
            "    #                  / \\\n"
            "    #                 2   2\n"
            "    #                / \\ / \\\n"
            "    #               3  4 4  3\n"
            "    root = TreeNode(1,\n"
            "                    TreeNode(2, TreeNode(3), TreeNode(4)),\n"
            "                    TreeNode(2, TreeNode(4), TreeNode(3)))\n"
            "    print(is_symmetric(root))  # True\n"
            "    # Asymmetric: [1,2,2,null,3,null,3]\n"
            "    root2 = TreeNode(1,\n"
            "                     TreeNode(2, None, TreeNode(3)),\n"
            "                     TreeNode(2, None, TreeNode(3)))\n"
            "    print(is_symmetric(root2))  # False"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const root = { val: 1,\n"
            "    left:  { val: 2, left: { val: 3, left: null, right: null },\n"
            "                     right:{ val: 4, left: null, right: null } },\n"
            "    right: { val: 2, left: { val: 4, left: null, right: null },\n"
            "                     right:{ val: 3, left: null, right: null } } };\n"
            "console.log(isSymmetric(root));  // true"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        TreeNode root = new TreeNode(1,\n"
            "            new TreeNode(2, new TreeNode(3), new TreeNode(4)),\n"
            "            new TreeNode(2, new TreeNode(4), new TreeNode(3)));\n"
            "        System.out.println(s.isSymmetric(root));  // true\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": level_order_to_verbose([])}, "expected": True,
         "description": "Empty tree — vacuously symmetric", "tags": ["edge"]},
        {"input": {"root": level_order_to_verbose([1])}, "expected": True,
         "description": "Single node — trivially symmetric", "tags": ["edge"]},
        {"input": {"root": level_order_to_verbose([1, 2, 2])}, "expected": True,
         "description": "Two children with equal values — symmetric", "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([1, 2, 3])}, "expected": False,
         "description": "Two children with different values — asymmetric at the top",
         "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([1, 2, 2, 3, 4, 4, 3])}, "expected": True,
         "description": "Classic LeetCode example — fully symmetric four-leaf tree",
         "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([1, 2, 2, None, 3, None, 3])}, "expected": False,
         "description": "Classic LeetCode counter-example — both 3s are right children, a "
                        "translation rather than a reflection",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([1, 2, 2, 3, 4, 4, 3, 5, 6, 7, 8, 8, 7, 6, 5])}, "expected": True,
         "description": "Perfect symmetric tree of depth 4", "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([1, 2, 2, 3, 4, 4, 5])}, "expected": False,
         "description": "Mirror shape but one corresponding leaf value differs", "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([1, 2])}, "expected": False,
         "description": "Only-left subtree — no right side to mirror", "tags": ["edge"]},
        {"input": {"root": level_order_to_verbose([1, 2, 2, None, 3, 3, None])}, "expected": True,
         "description": "Mirror shape with a single null at corresponding mirrored positions — "
                        "asymmetric *within* a child but symmetric *across* the root",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([1, 2, 2, 3, None, None, 3])}, "expected": True,
         "description": "Outer leaves present, inner positions null on both sides — symmetric",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([1, 2, 2, 3, None, 3, None])}, "expected": False,
         "description": "Same node values on each side, but the nulls land at non-mirrored "
                        "positions — structural mismatch",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Recursive Mirror Compare (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h)",
            "description": (
                "Define a helper `mirror(a, b)` that returns whether two subtrees are reflections "
                "of each other. The recursion crosses the children: `a.left` is paired with "
                "`b.right`, and `a.right` with `b.left`. Call it once on `(root.left, root.right)`. "
                "Every node is visited at most once, so time is `O(n)`. Space is the recursion "
                "depth — `O(log n)` for balanced trees, `O(n)` worst case (skewed)."
            ),
            "code": {
                "python": (
                    "def is_symmetric(root):\n"
                    "    def mirror(a, b):\n"
                    "        if a is None and b is None:\n"
                    "            return True\n"
                    "        if a is None or b is None:\n"
                    "            return False\n"
                    "        if a.val != b.val:\n"
                    "            return False\n"
                    "        return mirror(a.left, b.right) and mirror(a.right, b.left)\n"
                    "\n"
                    "    if root is None:\n"
                    "        return True\n"
                    "    return mirror(root.left, root.right)"
                ),
                "javascript": (
                    "function isSymmetric(root) {\n"
                    "    function mirror(a, b) {\n"
                    "        if (a === null && b === null) return true;\n"
                    "        if (a === null || b === null) return false;\n"
                    "        if (a.val !== b.val) return false;\n"
                    "        return mirror(a.left, b.right) && mirror(a.right, b.left);\n"
                    "    }\n"
                    "    if (root === null) return true;\n"
                    "    return mirror(root.left, root.right);\n"
                    "}"
                ),
                "java": (
                    "public boolean isSymmetric(TreeNode root) {\n"
                    "    if (root == null) return true;\n"
                    "    return mirror(root.left, root.right);\n"
                    "}\n"
                    "\n"
                    "private boolean mirror(TreeNode a, TreeNode b) {\n"
                    "    if (a == null && b == null) return true;\n"
                    "    if (a == null || b == null) return false;\n"
                    "    if (a.val != b.val) return false;\n"
                    "    return mirror(a.left, b.right) && mirror(a.right, b.left);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative BFS with Pair Queue",
            "time_complexity": "O(n)",
            "space_complexity": "O(w)",
            "description": (
                "Walk the two halves of the tree in lock-step using a queue of node *pairs*. Seed "
                "with `(root.left, root.right)`. For each popped pair, apply the three base checks "
                "(both null, exactly one null, value mismatch), then enqueue the *crossed* "
                "children: `(a.left, b.right)` and `(a.right, b.left)`. If the loop drains "
                "without returning False, the tree is symmetric. `w` is the maximum width of the "
                "tree — up to `n/2` for the bottom level of a complete tree. Useful when recursion "
                "depth is a concern."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "def is_symmetric(root):\n"
                    "    if root is None:\n"
                    "        return True\n"
                    "    queue = deque([(root.left, root.right)])\n"
                    "    while queue:\n"
                    "        a, b = queue.popleft()\n"
                    "        if a is None and b is None:\n"
                    "            continue\n"
                    "        if a is None or b is None:\n"
                    "            return False\n"
                    "        if a.val != b.val:\n"
                    "            return False\n"
                    "        queue.append((a.left, b.right))\n"
                    "        queue.append((a.right, b.left))\n"
                    "    return True"
                ),
                "javascript": (
                    "function isSymmetric(root) {\n"
                    "    if (root === null) return true;\n"
                    "    const queue = [[root.left, root.right]];\n"
                    "    while (queue.length) {\n"
                    "        const [a, b] = queue.shift();\n"
                    "        if (a === null && b === null) continue;\n"
                    "        if (a === null || b === null) return false;\n"
                    "        if (a.val !== b.val) return false;\n"
                    "        queue.push([a.left, b.right]);\n"
                    "        queue.push([a.right, b.left]);\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
                "java": (
                    "public boolean isSymmetric(TreeNode root) {\n"
                    "    if (root == null) return true;\n"
                    "    Deque<TreeNode[]> queue = new ArrayDeque<>();\n"
                    "    queue.offer(new TreeNode[]{root.left, root.right});\n"
                    "    while (!queue.isEmpty()) {\n"
                    "        TreeNode[] pair = queue.poll();\n"
                    "        TreeNode a = pair[0], b = pair[1];\n"
                    "        if (a == null && b == null) continue;\n"
                    "        if (a == null || b == null) return false;\n"
                    "        if (a.val != b.val) return false;\n"
                    "        queue.offer(new TreeNode[]{a.left, b.right});\n"
                    "        queue.offer(new TreeNode[]{a.right, b.left});\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: a tree is symmetric iff folding it down the middle lines up every node — both "
        "shape *and* value match across the centre line.",
        "2. One-tree question, but the answer falls out of a *two-tree* helper: `mirror(left, "
        "right)`. This is the LC 101 trick — convert a self-comparison into a paired comparison.",
        "3. Recursive structure: `mirror(a, b) = mirror(a.left, b.right) AND mirror(a.right, "
        "b.left)`. The crossed children are what makes it 'mirror' instead of 'same'.",
        "4. Three base cases: both null (True), one null (False), values differ (False). Identical "
        "to Same Tree (LC 100) — only the recursive call swaps the children.",
        "5. Iterative: a queue of pairs. Seed with `(root.left, root.right)`; pop, validate, push "
        "the crossed pairs. Same `O(n)` work, swaps recursion stack for an explicit queue.",
        "6. Edge case: empty tree → True (vacuously); single node → True (no children to compare). "
        "Both fall out of the base cases without special-casing.",
        "7. Complexity: every node is touched at most once → `O(n)` time. Space is `O(h)` for "
        "recursion or `O(w)` for the BFS queue.",
    ],
    "tips": [
        "The whole problem hinges on the *crossed* recursion — `a.left` with `b.right`, "
        "`a.right` with `b.left`. Get that wrong and you've written Same Tree, not Symmetric Tree.",
        "Don't try to compute symmetry directly on the single root — extract a two-argument "
        "helper. The two-argument framing is what makes the recursion express-able at all.",
        "Order of base cases matters: both-null first (True), then one-null (False), then value "
        "compare. Swap the first two and you'll mark every empty-vs-empty as asymmetric.",
        "An alternative iterative technique is to do an in-order traversal of the left subtree "
        "and a *reverse* in-order traversal of the right subtree and compare value-by-value — "
        "but it doesn't generalize to handling structural nulls cleanly. Stick with paired BFS.",
        "Don't be tempted to invert the right subtree and call `is_same_tree(left, inverted_right)`. "
        "It works but mutates the input — interviewers will dock you for the side effect.",
        "Common follow-up: 'Same Tree' (LC 100) — the same paired recursion *without* the cross. "
        "Mention the connection explicitly; it shows you understand the family of problems.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Bloomberg", "Apple", "LinkedIn"],
    "topics": ["Tree", "Depth-First Search", "Breadth-First Search", "Binary Tree"],
    "time_complexity": "O(n)",
    "space_complexity": "O(h)",
    "entry": {
        "kind": "tree",
        "name": "is_symmetric",
        "params": [
            {"name": "root", "type": "node"},
        ],
    },
}

def REFERENCE(root):
    """Take the raw array fixture and return whether the tree is symmetric."""
    tree = inflate_tree(root)
    if tree is None:
        return True
    return _is_mirror(tree["left"], tree["right"])

register(PAYLOAD, REFERENCE)
