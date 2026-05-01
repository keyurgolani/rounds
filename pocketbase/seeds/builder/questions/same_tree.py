"""Same Tree — Easy. Tree / DFS / BFS.

LeetCode 100. The canonical pair-traversal problem: walk both trees in
lock-step, returning False the moment shape or value disagrees. Often
used as a lead-in to Symmetric Tree (LC 101) and Subtree of Another
Tree (LC 572) — they all share the same paired-recursion skeleton.

Input/output use LeetCode level-order with `null` for missing nodes.
The reference takes two such lists and returns a bool.
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


def _is_same(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if a["val"] != b["val"]:
        return False
    return _is_same(a["left"], b["left"]) and _is_same(a["right"], b["right"])


PAYLOAD = {
    "title": "Same Tree",
    "difficulty": "Easy",
    "description": (
        "Given the roots of two binary trees `p` and `q`, write a function to check if they are the "
        "**same** — i.e., they are **structurally identical** AND the corresponding nodes hold the "
        "**same values**.\n\n"
        "The inputs are LeetCode level-order serializations where `null` denotes a missing child.\n\n"
        "**Example 1:**\n"
        "- Input: `p = [1,2,3]`, `q = [1,2,3]`\n"
        "- Output: `true`\n"
        "- Explanation: Both trees have the same shape and the same values at every position.\n\n"
        "**Example 2:**\n"
        "- Input: `p = [1,2]`, `q = [1,null,2]`\n"
        "- Output: `false`\n"
        "- Explanation: Same node values, but the `2` is a *left* child in `p` and a *right* child in "
        "`q` — different structure.\n\n"
        "**Example 3:**\n"
        "- Input: `p = [1,2,1]`, `q = [1,1,2]`\n"
        "- Output: `false`\n"
        "- Explanation: Identical shape, but the values at the children differ."
    ),
    "hints": [
        "Recurse on both trees in parallel. Two trees are 'same' iff their roots match AND their left "
        "subtrees are same AND their right subtrees are same.",
        "Three base cases at every call: both null → True; exactly one null → False; values differ → "
        "False. Only after surviving those do you recurse.",
        "Iterative version: BFS with a queue of *pairs*. Push `(p, q)` to start; for each pair popped, "
        "validate and enqueue `(p.left, q.left)` and `(p.right, q.right)`.",
        "Don't forget the structural mismatch case — `[1,2]` vs `[1,null,2]` have the same node values "
        "but are not the same tree. The 'one is null, the other isn't' check catches it.",
        "Edge case: both trees empty → True. The base case handles it without any special-casing at "
        "the top.",
    ],
    "constraints": [
        "The number of nodes in both trees is in the range `[0, 100]`.",
        "-10⁴ <= Node.val <= 10⁴",
        "Both inputs are valid LeetCode level-order serializations.",
    ],
    "starter_code": {
        "python": (
            "# Definition for a binary tree node.\n"
            "# class TreeNode:\n"
            "#     def __init__(self, val=0, left=None, right=None):\n"
            "#         self.val = val\n"
            "#         self.left = left\n"
            "#         self.right = right\n"
            "def is_same_tree(p, q):\n"
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
            "function isSameTree(p, q) {\n"
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
            "public boolean isSameTree(TreeNode p, TreeNode q) {\n"
            "    // Your code here\n"
            "    return false;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    # p = q = [1, 2, 3]\n"
            "    p = TreeNode(1, TreeNode(2), TreeNode(3))\n"
            "    q = TreeNode(1, TreeNode(2), TreeNode(3))\n"
            "    print(is_same_tree(p, q))  # True\n"
            "    # p = [1, 2], q = [1, null, 2]\n"
            "    p2 = TreeNode(1, TreeNode(2), None)\n"
            "    q2 = TreeNode(1, None, TreeNode(2))\n"
            "    print(is_same_tree(p2, q2))  # False"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const p = { val: 1, left: { val: 2, left: null, right: null },\n"
            "                    right: { val: 3, left: null, right: null } };\n"
            "const q = { val: 1, left: { val: 2, left: null, right: null },\n"
            "                    right: { val: 3, left: null, right: null } };\n"
            "console.log(isSameTree(p, q));  // true"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        TreeNode p = new TreeNode(1, new TreeNode(2), new TreeNode(3));\n"
            "        TreeNode q = new TreeNode(1, new TreeNode(2), new TreeNode(3));\n"
            "        System.out.println(s.isSameTree(p, q));  // true\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"p": [], "q": []}, "expected": True,
         "description": "Both trees empty — vacuously same", "tags": ["edge"]},
        {"input": {"p": [1], "q": []}, "expected": False,
         "description": "One empty, one single-node — different structure", "tags": ["edge"]},
        {"input": {"p": [], "q": [1]}, "expected": False,
         "description": "Mirror of the previous case — null vs non-null at root", "tags": ["edge"]},
        {"input": {"p": [1], "q": [1]}, "expected": True,
         "description": "Single matching node", "tags": ["edge"]},
        {"input": {"p": [1], "q": [2]}, "expected": False,
         "description": "Single node, different value", "tags": ["edge"]},
        {"input": {"p": [1, 2], "q": [1, None, 2]}, "expected": False,
         "description": "Same values but different shape — left vs right child",
         "tags": ["tricky"]},
        {"input": {"p": [1, 2, 3], "q": [1, 2, 3]}, "expected": True,
         "description": "Classic LeetCode example — identical small tree", "tags": ["basic"]},
        {"input": {"p": [1, 2, 1], "q": [1, 1, 2]}, "expected": False,
         "description": "Identical shape, swapped child values", "tags": ["basic"]},
        {"input": {"p": [1, 2, 3, 4, 5], "q": [1, 2, 3, 4, 5]}, "expected": True,
         "description": "Deeper identical tree", "tags": ["basic"]},
        {"input": {"p": [1, 2, 3, 4, 5], "q": [1, 2, 3, 4, 6]}, "expected": False,
         "description": "Deeper trees, single leaf value differs", "tags": ["tricky"]},
        {"input": {"p": [1, 2, 3, 4, 5], "q": [1, 2, 3, 4]}, "expected": False,
         "description": "One tree missing a leaf — structural mismatch", "tags": ["tricky"]},
        {"input": {"p": [-1, -2, -3], "q": [-1, -2, -3]}, "expected": True,
         "description": "Negative values, identical", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Recursive DFS (Optimal)",
            "time_complexity": "O(min(m, n))",
            "space_complexity": "O(min(h_p, h_q))",
            "description": (
                "Compare both roots, then recurse on the corresponding left and right children. The "
                "instant either tree runs out — or the values disagree — short-circuit to False. "
                "Time is linear in the *smaller* of the two trees because divergence ends the walk. "
                "Space is the recursion depth, bounded by the shallower tree's height."
            ),
            "code": {
                "python": (
                    "def is_same_tree(p, q):\n"
                    "    if p is None and q is None:\n"
                    "        return True\n"
                    "    if p is None or q is None:\n"
                    "        return False\n"
                    "    if p.val != q.val:\n"
                    "        return False\n"
                    "    return is_same_tree(p.left, q.left) and is_same_tree(p.right, q.right)"
                ),
                "javascript": (
                    "function isSameTree(p, q) {\n"
                    "    if (p === null && q === null) return true;\n"
                    "    if (p === null || q === null) return false;\n"
                    "    if (p.val !== q.val) return false;\n"
                    "    return isSameTree(p.left, q.left) && isSameTree(p.right, q.right);\n"
                    "}"
                ),
                "java": (
                    "public boolean isSameTree(TreeNode p, TreeNode q) {\n"
                    "    if (p == null && q == null) return true;\n"
                    "    if (p == null || q == null) return false;\n"
                    "    if (p.val != q.val) return false;\n"
                    "    return isSameTree(p.left, q.left) && isSameTree(p.right, q.right);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative BFS with Pair Queue",
            "time_complexity": "O(min(m, n))",
            "space_complexity": "O(min(w_p, w_q))",
            "description": (
                "Walk both trees in lock-step using a queue of node *pairs*. Pop a `(a, b)` pair, "
                "apply the three base checks (both null, one null, value mismatch), then push "
                "`(a.left, b.left)` and `(a.right, b.right)`. If the loop drains without returning "
                "False, the trees are the same. Avoids recursion-stack risk on skewed inputs."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "def is_same_tree(p, q):\n"
                    "    queue = deque([(p, q)])\n"
                    "    while queue:\n"
                    "        a, b = queue.popleft()\n"
                    "        if a is None and b is None:\n"
                    "            continue\n"
                    "        if a is None or b is None:\n"
                    "            return False\n"
                    "        if a.val != b.val:\n"
                    "            return False\n"
                    "        queue.append((a.left, b.left))\n"
                    "        queue.append((a.right, b.right))\n"
                    "    return True"
                ),
                "javascript": (
                    "function isSameTree(p, q) {\n"
                    "    const queue = [[p, q]];\n"
                    "    while (queue.length) {\n"
                    "        const [a, b] = queue.shift();\n"
                    "        if (a === null && b === null) continue;\n"
                    "        if (a === null || b === null) return false;\n"
                    "        if (a.val !== b.val) return false;\n"
                    "        queue.push([a.left, b.left]);\n"
                    "        queue.push([a.right, b.right]);\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
                "java": (
                    "public boolean isSameTree(TreeNode p, TreeNode q) {\n"
                    "    Deque<TreeNode[]> queue = new ArrayDeque<>();\n"
                    "    queue.offer(new TreeNode[]{p, q});\n"
                    "    while (!queue.isEmpty()) {\n"
                    "        TreeNode[] pair = queue.poll();\n"
                    "        TreeNode a = pair[0], b = pair[1];\n"
                    "        if (a == null && b == null) continue;\n"
                    "        if (a == null || b == null) return false;\n"
                    "        if (a.val != b.val) return false;\n"
                    "        queue.offer(new TreeNode[]{a.left, b.left});\n"
                    "        queue.offer(new TreeNode[]{a.right, b.right});\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: 'same' means *both* shape and values match at every position. Either alone is "
        "insufficient — `[1,2]` vs `[1,null,2]` shows shape matters; `[1,2,1]` vs `[1,1,2]` shows "
        "values matter.",
        "2. Recursive structure is forced by the definition: `same(p, q)` iff roots match AND "
        "`same(p.left, q.left)` AND `same(p.right, q.right)`. Three base cases handle the leaves.",
        "3. The base cases must be in the right order: both-null first (success), then one-null "
        "(structural mismatch), then value compare. Skipping the second case is the classic "
        "off-by-one bug.",
        "4. Iterative version: replace the implicit recursion with a queue of pairs. The work per "
        "step is identical; only the traversal order changes (BFS vs DFS).",
        "5. Complexity: short-circuits the moment shape or value diverges, so it's `O(min(m, n))` "
        "in the worst case — the smaller tree determines the maximum work.",
        "6. Edge cases worth calling out: both empty (True), exactly one empty (False), single nodes "
        "with same/different value, deeper structural-only divergence.",
    ],
    "tips": [
        "Order of base cases matters. `both null → True` must come *before* `one null → False`; "
        "swap them and you'll wrongly mark two empty trees as different.",
        "Don't compare by serializing both trees and string-matching — it works but it's wasteful "
        "(`O(n + m)` time and space) and sidesteps the actual recursion the interviewer wants to see.",
        "Common follow-up — Symmetric Tree (LC 101): `is_mirror(a, b)` compares `a.left` with "
        "`b.right` and vice versa. Same skeleton, mirrored children. Mention it.",
        "Common follow-up — Subtree of Another Tree (LC 572): walk one tree and call `is_same_tree` "
        "at every node. Naive `O(m·n)`; tighten to `O(m + n)` with serialize + KMP or with hashing.",
        "Iterative BFS over pairs is also useful as the answer to 'what if the tree depth blows the "
        "Python recursion limit?' — it doesn't change the asymptotics, but it does sidestep "
        "`RecursionError` on adversarial skewed trees.",
        "If the interviewer asks 'what if values can be NaN or floats?' — the equality check becomes "
        "the only line you'd touch. The structure of the recursion is unchanged.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Bloomberg", "Apple"],
    "topics": ["Tree", "Depth-First Search", "Breadth-First Search", "Binary Tree"],
    "time_complexity": "O(min(m, n))",
    "space_complexity": "O(min(h_p, h_q))",
}


def REFERENCE(p, q):
    """Take two LeetCode level-order lists, return whether the trees are identical."""
    return _is_same(_build(p), _build(q))


register(PAYLOAD, REFERENCE)
