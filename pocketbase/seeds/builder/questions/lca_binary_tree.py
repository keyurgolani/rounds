"""Lowest Common Ancestor of a Binary Tree — Medium. Tree / DFS.

LeetCode 236. Classic recursion question. The trick is realising that
when both subtrees of a node return non-null, the current node is the
LCA — no extra bookkeeping needed.

Input/output use LeetCode level-order with `null` for missing nodes.
The reference returns the integer value of the LCA (not a node object)
so it serializes cleanly through JSON.
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


def _lca(node, p, q):
    """Return the LCA node (dict) of values p and q, or None."""
    if node is None:
        return None
    if node["val"] == p or node["val"] == q:
        return node
    left = _lca(node["left"], p, q)
    right = _lca(node["right"], p, q)
    if left and right:
        return node
    return left if left else right


PAYLOAD = {
    "title": "Lowest Common Ancestor of a Binary Tree",
    "difficulty": "Medium",
    "description": (
        "Given the `root` of a binary tree (not necessarily a BST) and two node values `p` and `q`, "
        "return the **value** of their lowest common ancestor (LCA).\n\n"
        "The LCA of `p` and `q` is the **deepest** node in the tree that has both `p` and `q` as descendants "
        "(where a node is allowed to be a descendant of itself).\n\n"
        "The input uses LeetCode level-order serialization where `null` denotes a missing child. "
        "All values in the tree are unique, and both `p` and `q` are guaranteed to exist in the tree.\n\n"
        "**Example 1:**\n"
        "- Input: `root = [3,5,1,6,2,0,8,null,null,7,4]`, `p = 5`, `q = 1`\n"
        "- Output: `3`\n"
        "- Explanation: The LCA of nodes `5` and `1` is `3`.\n"
        "```\n"
        "         3\n"
        "        / \\\n"
        "       5   1\n"
        "      / \\ / \\\n"
        "     6  2 0  8\n"
        "       / \\\n"
        "      7   4\n"
        "```\n\n"
        "**Example 2:**\n"
        "- Input: `root = [3,5,1,6,2,0,8,null,null,7,4]`, `p = 5`, `q = 4`\n"
        "- Output: `5`\n"
        "- Explanation: A node can be a descendant of itself — `5` is an ancestor of `4` and of itself, "
        "so the LCA is `5`."
    ),
    "hints": [
        "Post-order recursion is the elegant solution: at each node, recurse left and right, then decide based on what came back.",
        "Base cases: if the current node is `None`, return `None`. If the current node matches `p` or `q`, return the current node — no need to look deeper on this path.",
        "After recursing: if **both** left and right returned non-null, then `p` and `q` live in different subtrees, so the **current** node is the LCA. Otherwise propagate the non-null side upward.",
        "Iterative approach: do a DFS to build a parent-pointer map, then walk upward from `p` collecting ancestors into a set, then walk upward from `q` until you hit one that's in the set.",
        "Path-find approach: find the root-to-`p` path and the root-to-`q` path as lists, then walk them in lockstep — the last node where they agree is the LCA. Uses O(n) extra space but is easy to reason about.",
    ],
    "constraints": [
        "The number of nodes in the tree is in the range `[2, 10^5]`.",
        "-10^9 <= Node.val <= 10^9",
        "All `Node.val` are **unique**, and `p != q`. Both `p` and `q` are guaranteed to exist in the tree.",
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
            "    # Return the integer value of the LCA of nodes with values p and q.\n"
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
            "    // Return the integer value of the LCA of nodes with values p and q.\n"
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
            "public int lowestCommonAncestor(TreeNode root, int p, int q) {\n"
            "    // Return the integer value of the LCA of nodes with values p and q.\n"
            "    return -1;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    #       3\n"
            "    #      / \\\n"
            "    #     5   1\n"
            "    root = TreeNode(3, TreeNode(5), TreeNode(1))\n"
            "    print(lowest_common_ancestor(root, 5, 1))  # 3"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const root = { val: 3,\n"
            "               left: { val: 5, left: null, right: null },\n"
            "               right: { val: 1, left: null, right: null } };\n"
            "console.log(lowestCommonAncestor(root, 5, 1));  // 3"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        TreeNode root = new TreeNode(3);\n"
            "        root.left = new TreeNode(5);\n"
            "        root.right = new TreeNode(1);\n"
            "        System.out.println(s.lowestCommonAncestor(root, 5, 1));  // 3\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": [3, 5, 1, 6, 2, 0, 8, None, None, 7, 4], "p": 5, "q": 1}, "expected": 3,
         "description": "Classic LeetCode example — p and q in opposite subtrees, LCA is the root",
         "tags": ["basic"]},
        {"input": {"root": [3, 5, 1, 6, 2, 0, 8, None, None, 7, 4], "p": 5, "q": 4}, "expected": 5,
         "description": "Ancestor case — p (5) is itself the ancestor of q (4)",
         "tags": ["tricky"]},
        {"input": {"root": [1, 2], "p": 1, "q": 2}, "expected": 1,
         "description": "Two-node tree — root is the ancestor of its only child",
         "tags": ["edge"]},
        {"input": {"root": [1, 2, None, 3, None, 4], "p": 3, "q": 4}, "expected": 3,
         "description": "Left-only chain — LCA is the upper of the two nodes (3 is ancestor of 4)",
         "tags": ["edge"]},
        {"input": {"root": [1, None, 2, None, 3, None, 4], "p": 2, "q": 4}, "expected": 2,
         "description": "Right-only chain — LCA is the upper of the two nodes (2 is ancestor of 4)",
         "tags": ["edge"]},
        {"input": {"root": [3, 5, 1, 6, 2, 0, 8, None, None, 7, 4], "p": 6, "q": 8}, "expected": 3,
         "description": "Deep leaves in opposite subtrees — LCA is the root",
         "tags": ["basic"]},
        {"input": {"root": [3, 5, 1, 6, 2, 0, 8, None, None, 7, 4], "p": 7, "q": 4}, "expected": 2,
         "description": "Cousins-only case — both leaves share the same parent (2)",
         "tags": ["basic"]},
        {"input": {"root": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], "p": 8, "q": 15},
         "expected": 1,
         "description": "Deeper full tree — leaves at opposite ends, LCA is the root",
         "tags": ["basic"]},
        {"input": {"root": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], "p": 8, "q": 11},
         "expected": 2,
         "description": "Deeper full tree — both leaves under node 2",
         "tags": ["basic"]},
        {"input": {"root": [10, 5, 15, 3, 7, None, 18, 1, None, None, 9], "p": 1, "q": 9}, "expected": 5,
         "description": "Lopsided tree — LCA is an internal node with both targets in its subtree",
         "tags": ["tricky"]},
        {"input": {"root": [1, 2, 3], "p": 2, "q": 3}, "expected": 1,
         "description": "Three-node tree — siblings under root",
         "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Recursive DFS Post-Order (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h)",
            "description": (
                "Walk the tree post-order. If the current node is `None` or matches `p` or `q`, return it. "
                "Otherwise recurse into both children. If **both** sides returned non-null, the current "
                "node is the split point — it's the LCA. If only one side returned non-null, propagate it "
                "upward. `h` is the tree height — `O(log n)` for balanced trees, `O(n)` worst-case skewed."
            ),
            "code": {
                "python": (
                    "def lowest_common_ancestor(root, p, q):\n"
                    "    def dfs(node):\n"
                    "        if node is None or node.val == p or node.val == q:\n"
                    "            return node\n"
                    "        left = dfs(node.left)\n"
                    "        right = dfs(node.right)\n"
                    "        if left and right:\n"
                    "            return node\n"
                    "        return left if left else right\n"
                    "    return dfs(root).val"
                ),
                "javascript": (
                    "function lowestCommonAncestor(root, p, q) {\n"
                    "    function dfs(node) {\n"
                    "        if (node === null || node.val === p || node.val === q) return node;\n"
                    "        const left = dfs(node.left);\n"
                    "        const right = dfs(node.right);\n"
                    "        if (left && right) return node;\n"
                    "        return left ? left : right;\n"
                    "    }\n"
                    "    return dfs(root).val;\n"
                    "}"
                ),
                "java": (
                    "public int lowestCommonAncestor(TreeNode root, int p, int q) {\n"
                    "    return dfs(root, p, q).val;\n"
                    "}\n"
                    "private TreeNode dfs(TreeNode node, int p, int q) {\n"
                    "    if (node == null || node.val == p || node.val == q) return node;\n"
                    "    TreeNode left = dfs(node.left, p, q);\n"
                    "    TreeNode right = dfs(node.right, p, q);\n"
                    "    if (left != null && right != null) return node;\n"
                    "    return left != null ? left : right;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative Parent-Pointer Map",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "First DFS the tree once to record each node's parent in a hash map. Then walk upward from "
                "`p`, putting every ancestor (including `p`) into a set. Finally walk upward from `q` and "
                "return the first ancestor that's already in the set — that's the LCA. Linear time, but "
                "uses linear extra space for the parent map."
            ),
            "code": {
                "python": (
                    "def lowest_common_ancestor(root, p, q):\n"
                    "    parent = {root: None}\n"
                    "    p_node = q_node = None\n"
                    "    stack = [root]\n"
                    "    while stack and (p_node is None or q_node is None):\n"
                    "        node = stack.pop()\n"
                    "        if node.val == p:\n"
                    "            p_node = node\n"
                    "        if node.val == q:\n"
                    "            q_node = node\n"
                    "        if node.left:\n"
                    "            parent[node.left] = node\n"
                    "            stack.append(node.left)\n"
                    "        if node.right:\n"
                    "            parent[node.right] = node\n"
                    "            stack.append(node.right)\n"
                    "    ancestors = set()\n"
                    "    cur = p_node\n"
                    "    while cur is not None:\n"
                    "        ancestors.add(id(cur))\n"
                    "        cur = parent[cur]\n"
                    "    cur = q_node\n"
                    "    while id(cur) not in ancestors:\n"
                    "        cur = parent[cur]\n"
                    "    return cur.val"
                ),
                "javascript": (
                    "function lowestCommonAncestor(root, p, q) {\n"
                    "    const parent = new Map();\n"
                    "    parent.set(root, null);\n"
                    "    let pNode = null, qNode = null;\n"
                    "    const stack = [root];\n"
                    "    while (stack.length && (pNode === null || qNode === null)) {\n"
                    "        const node = stack.pop();\n"
                    "        if (node.val === p) pNode = node;\n"
                    "        if (node.val === q) qNode = node;\n"
                    "        if (node.left)  { parent.set(node.left, node);  stack.push(node.left); }\n"
                    "        if (node.right) { parent.set(node.right, node); stack.push(node.right); }\n"
                    "    }\n"
                    "    const ancestors = new Set();\n"
                    "    let cur = pNode;\n"
                    "    while (cur !== null) { ancestors.add(cur); cur = parent.get(cur); }\n"
                    "    cur = qNode;\n"
                    "    while (!ancestors.has(cur)) cur = parent.get(cur);\n"
                    "    return cur.val;\n"
                    "}"
                ),
                "java": (
                    "public int lowestCommonAncestor(TreeNode root, int p, int q) {\n"
                    "    Map<TreeNode, TreeNode> parent = new HashMap<>();\n"
                    "    parent.put(root, null);\n"
                    "    Deque<TreeNode> stack = new ArrayDeque<>();\n"
                    "    stack.push(root);\n"
                    "    TreeNode pNode = null, qNode = null;\n"
                    "    while (!stack.isEmpty() && (pNode == null || qNode == null)) {\n"
                    "        TreeNode node = stack.pop();\n"
                    "        if (node.val == p) pNode = node;\n"
                    "        if (node.val == q) qNode = node;\n"
                    "        if (node.left != null)  { parent.put(node.left, node);  stack.push(node.left); }\n"
                    "        if (node.right != null) { parent.put(node.right, node); stack.push(node.right); }\n"
                    "    }\n"
                    "    Set<TreeNode> ancestors = new HashSet<>();\n"
                    "    for (TreeNode cur = pNode; cur != null; cur = parent.get(cur)) ancestors.add(cur);\n"
                    "    TreeNode cur = qNode;\n"
                    "    while (!ancestors.contains(cur)) cur = parent.get(cur);\n"
                    "    return cur.val;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: LCA = deepest node that has both p and q in its subtree. A node is its own descendant.",
        "2. Key insight: at every node, ask 'is p somewhere below me?' and 'is q somewhere below me?'. The deepest node where both answers are yes is the LCA.",
        "3. Post-order recursion encodes this naturally. Bubble up either p, q, or null from each subtree.",
        "4. The split-point rule: if the left recursion bubbled up something AND the right recursion bubbled up something, then p and q live in different subtrees → I'm the LCA.",
        "5. Otherwise only one side has a hit (or neither) — propagate that side upward. The hit will eventually meet the other on the way up to the LCA.",
        "6. Ancestor case (p is ancestor of q): the recursion stops at p as soon as it sees `node.val == p`, and the q-hit bubbles up underneath, but we never recurse below p. The first node above whose 'other side' returns non-null becomes the LCA — but actually p itself bubbles up alone, and that's the answer.",
        "7. Complexity: every node is visited at most once → O(n) time. Recursion depth is the tree height → O(h) space.",
        "8. Alternative: parent-pointer map + ancestor-set walk. Linear time, linear space. Useful when you need to answer many LCA queries on the same tree.",
    ],
    "tips": [
        "Don't overthink the ancestor case (one node is the ancestor of the other). The post-order recursion handles it for free — when you hit p, you return p without descending further, and that p propagates up to become the answer.",
        "The two recursive calls must happen *before* the decision. A common bug is short-circuiting on the left result — you'd miss the case where p is on the left and q is on the right.",
        "If the interviewer says 'the tree is a BST' (LeetCode 235), there's a much simpler O(h) solution that doesn't need to look at the whole tree — walk down comparing values to p and q.",
        "Follow-up: 'what if you have many LCA queries on the same tree?' → preprocess with Euler-tour + sparse-table RMQ for O(1) per query, or use Tarjan's offline LCA. Mention this only if asked.",
        "Be careful with the iterative parent-map version: in Python, dict keys must be hashable, but tree nodes (dicts here, custom classes in interview) compare by identity — use `id(node)` or a class with default `__hash__`.",
        "Edge cases worth mentioning out loud: p == q (problem says p != q, but worth flagging); p is the root; tree of size 2.",
    ],
    "companies": ["Facebook", "Amazon", "Google", "Microsoft", "Apple", "LinkedIn", "Bloomberg"],
    "topics": ["Tree", "Depth-First Search", "Binary Tree"],
    "time_complexity": "O(n)",
    "space_complexity": "O(h)",
}


def REFERENCE(root, p, q):
    """Build the tree, find the LCA node, return its integer value."""
    tree = _build(root)
    ancestor = _lca(tree, p, q)
    return ancestor["val"]


register(PAYLOAD, REFERENCE)
