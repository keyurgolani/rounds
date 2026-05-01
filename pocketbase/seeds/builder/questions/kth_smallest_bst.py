"""Kth Smallest Element in a BST — Medium. Tree / DFS / BST.

LeetCode 230. Classic exploitation of the BST in-order property: an
in-order traversal of a BST yields values in ascending order, so the
kth value popped off the in-order walk is exactly the answer. The
optimal version uses an explicit stack and stops the moment count == k,
giving O(h + k) time and O(h) space — strictly better than a full
traversal when k is small.

Input is a LeetCode level-order list (with `null` for missing nodes)
plus a 1-indexed integer k. Output is the kth-smallest node value.
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


def _kth_smallest(root, k):
    """Iterative in-order traversal that early-stops when the kth node is popped."""
    stack = []
    node = root
    count = 0
    while stack or node is not None:
        while node is not None:
            stack.append(node)
            node = node["left"]
        node = stack.pop()
        count += 1
        if count == k:
            return node["val"]
        node = node["right"]
    # Should not be reached for valid 1 <= k <= n.
    return -1


PAYLOAD = {
    "title": "Kth Smallest Element in a BST",
    "difficulty": "Medium",
    "description": (
        "Given the `root` of a binary search tree (BST) and an integer `k`, return the **kth smallest** "
        "value (1-indexed) among all node values in the tree.\n\n"
        "The input tree is given in LeetCode level-order serialization where `null` denotes a missing "
        "child.\n\n"
        "**Example 1:**\n"
        "- Input: `root = [3,1,4,null,2]`, `k = 1`\n"
        "- Output: `1`\n"
        "- Explanation:\n"
        "```\n"
        "       3\n"
        "      / \\\n"
        "     1   4\n"
        "      \\\n"
        "       2\n"
        "```\n"
        "In-order traversal yields `[1, 2, 3, 4]`. The 1st smallest is `1`.\n\n"
        "**Example 2:**\n"
        "- Input: `root = [5,3,6,2,4,null,null,1]`, `k = 3`\n"
        "- Output: `3`\n"
        "- Explanation:\n"
        "```\n"
        "         5\n"
        "        / \\\n"
        "       3   6\n"
        "      / \\\n"
        "     2   4\n"
        "    /\n"
        "   1\n"
        "```\n"
        "In-order traversal yields `[1, 2, 3, 4, 5, 6]`. The 3rd smallest is `3`."
    ),
    "hints": [
        "The defining property of a BST: an **in-order traversal** (left, root, right) visits nodes in strictly ascending order. So the kth value emitted by an in-order walk is the answer.",
        "The naive approach: do a full in-order traversal into a list, return `list[k-1]`. Works in `O(n)` time and `O(n)` space — fine but not optimal.",
        "Optimal: walk in-order **iteratively** using an explicit stack so you can stop the moment you've popped `k` nodes. Time becomes `O(h + k)` (height to descend + k pops), space `O(h)`.",
        "The iterative pattern: push left spine onto stack, pop, increment counter, if counter == k return; otherwise step into the right child and repeat.",
        "Recursive variant works too — pass `k` and a counter by reference (or use a closure / nonlocal). Same optimal complexity, but the explicit stack is clearer to reason about under interview pressure.",
        "Follow-up to expect: 'What if the BST is modified often (insertions/deletions) and you must find the kth smallest frequently?' → augment each node with a `size` field (size of its subtree). Then descend in `O(h)` per query and update sizes in `O(h)` per modification.",
    ],
    "constraints": [
        "The number of nodes in the tree is `n` and `1 <= k <= n <= 10^4`.",
        "0 <= Node.val <= 10^4",
        "The tree is a valid binary search tree.",
    ],
    "starter_code": {
        "python": (
            "# Definition for a binary tree node.\n"
            "# class TreeNode:\n"
            "#     def __init__(self, val=0, left=None, right=None):\n"
            "#         self.val = val\n"
            "#         self.left = left\n"
            "#         self.right = right\n"
            "def kth_smallest(root, k):\n"
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
            "function kthSmallest(root, k) {\n"
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
            "public int kthSmallest(TreeNode root, int k) {\n"
            "    // Your code here\n"
            "    return -1;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    #     3\n"
            "    #    / \\\n"
            "    #   1   4\n"
            "    #    \\\n"
            "    #     2\n"
            "    root = TreeNode(3, TreeNode(1, None, TreeNode(2)), TreeNode(4))\n"
            "    print(kth_smallest(root, 1))  # 1\n"
            "    print(kth_smallest(root, 3))  # 3"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const root = {\n"
            "    val: 3,\n"
            "    left: { val: 1, left: null, right: { val: 2, left: null, right: null } },\n"
            "    right: { val: 4, left: null, right: null }\n"
            "};\n"
            "console.log(kthSmallest(root, 1));  // 1\n"
            "console.log(kthSmallest(root, 3));  // 3"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        TreeNode root = new TreeNode(3,\n"
            "            new TreeNode(1, null, new TreeNode(2)),\n"
            "            new TreeNode(4));\n"
            "        System.out.println(s.kthSmallest(root, 1));  // 1\n"
            "        System.out.println(s.kthSmallest(root, 3));  // 3\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": [3, 1, 4, None, 2], "k": 1}, "expected": 1,
         "description": "Classic example, k=1 → minimum value", "tags": ["basic"]},
        {"input": {"root": [3, 1, 4, None, 2], "k": 2}, "expected": 2,
         "description": "Same tree, k=2 → second smallest is the in-order successor of the leftmost", "tags": ["basic"]},
        {"input": {"root": [5, 3, 6, 2, 4, None, None, 1], "k": 3}, "expected": 3,
         "description": "Classic LeetCode example, k=3 → middle of in-order [1,2,3,4,5,6]", "tags": ["basic"]},
        {"input": {"root": [1], "k": 1}, "expected": 1,
         "description": "Single-node tree, k=1 → only value", "tags": ["edge"]},
        {"input": {"root": [5, 4, None, 3, None, 2, None, 1], "k": 3}, "expected": 3,
         "description": "Left-only chain (BST descending into left children), k=mid", "tags": ["tricky"]},
        {"input": {"root": [1, None, 2, None, 3, None, 4, None, 5], "k": 3}, "expected": 3,
         "description": "Right-only chain (BST ascending into right children), k=mid", "tags": ["tricky"]},
        {"input": {"root": [4, 2, 6, 1, 3, 5, 7], "k": 4}, "expected": 4,
         "description": "Perfectly balanced BST of 7 nodes, k=4 → root value (median)", "tags": ["basic"]},
        {"input": {"root": [4, 2, 6, 1, 3, 5, 7], "k": 1}, "expected": 1,
         "description": "Balanced BST, k=1 → leftmost leaf (overall minimum)", "tags": ["edge"]},
        {"input": {"root": [4, 2, 6, 1, 3, 5, 7], "k": 7}, "expected": 7,
         "description": "Balanced BST, k=n → rightmost leaf (overall maximum)", "tags": ["edge"]},
        {"input": {"root": [5, 3, 6, 2, 4, None, None, 1], "k": 1}, "expected": 1,
         "description": "Lopsided BST, k=1 → deepest left descendant", "tags": ["tricky"]},
        {"input": {"root": [5, 3, 6, 2, 4, None, None, 1], "k": 6}, "expected": 6,
         "description": "Lopsided BST, k=n → rightmost node", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Iterative In-Order with Stack (Optimal)",
            "time_complexity": "O(h + k)",
            "space_complexity": "O(h)",
            "description": (
                "Walk the tree in-order using an explicit stack and stop as soon as `k` nodes have been "
                "popped. The outer loop pushes the entire left spine of the current subtree, pops the "
                "smallest unvisited node, increments the counter, and — if it isn't yet the kth — descends "
                "into that node's right subtree. Time is `O(h + k)`: `O(h)` to descend to the leftmost leaf, "
                "then `O(k)` pops. Space is the stack depth, bounded by the tree height `h`."
            ),
            "code": {
                "python": (
                    "def kth_smallest(root, k):\n"
                    "    stack = []\n"
                    "    node = root\n"
                    "    while stack or node is not None:\n"
                    "        while node is not None:\n"
                    "            stack.append(node)\n"
                    "            node = node.left\n"
                    "        node = stack.pop()\n"
                    "        k -= 1\n"
                    "        if k == 0:\n"
                    "            return node.val\n"
                    "        node = node.right\n"
                    "    return -1  # unreachable for valid input"
                ),
                "javascript": (
                    "function kthSmallest(root, k) {\n"
                    "    const stack = [];\n"
                    "    let node = root;\n"
                    "    while (stack.length || node !== null) {\n"
                    "        while (node !== null) {\n"
                    "            stack.push(node);\n"
                    "            node = node.left;\n"
                    "        }\n"
                    "        node = stack.pop();\n"
                    "        if (--k === 0) return node.val;\n"
                    "        node = node.right;\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
                "java": (
                    "public int kthSmallest(TreeNode root, int k) {\n"
                    "    Deque<TreeNode> stack = new ArrayDeque<>();\n"
                    "    TreeNode node = root;\n"
                    "    while (!stack.isEmpty() || node != null) {\n"
                    "        while (node != null) {\n"
                    "            stack.push(node);\n"
                    "            node = node.left;\n"
                    "        }\n"
                    "        node = stack.pop();\n"
                    "        if (--k == 0) return node.val;\n"
                    "        node = node.right;\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Recursive In-Order Collect-All",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Do a full recursive in-order traversal, appending every value to a list. Because in-order "
                "on a BST yields ascending values, `values[k - 1]` is the kth smallest. Conceptually the "
                "simplest approach and a great whiteboard answer when you want to demonstrate that you "
                "*understand the BST property* before optimising. Trades early termination for clarity: "
                "always touches all `n` nodes and uses `O(n)` extra space for the list."
            ),
            "code": {
                "python": (
                    "def kth_smallest(root, k):\n"
                    "    values = []\n"
                    "\n"
                    "    def inorder(node):\n"
                    "        if node is None:\n"
                    "            return\n"
                    "        inorder(node.left)\n"
                    "        values.append(node.val)\n"
                    "        inorder(node.right)\n"
                    "\n"
                    "    inorder(root)\n"
                    "    return values[k - 1]"
                ),
                "javascript": (
                    "function kthSmallest(root, k) {\n"
                    "    const values = [];\n"
                    "    const inorder = (node) => {\n"
                    "        if (node === null) return;\n"
                    "        inorder(node.left);\n"
                    "        values.push(node.val);\n"
                    "        inorder(node.right);\n"
                    "    };\n"
                    "    inorder(root);\n"
                    "    return values[k - 1];\n"
                    "}"
                ),
                "java": (
                    "public int kthSmallest(TreeNode root, int k) {\n"
                    "    List<Integer> values = new ArrayList<>();\n"
                    "    inorder(root, values);\n"
                    "    return values.get(k - 1);\n"
                    "}\n"
                    "\n"
                    "private void inorder(TreeNode node, List<Integer> values) {\n"
                    "    if (node == null) return;\n"
                    "    inorder(node.left, values);\n"
                    "    values.add(node.val);\n"
                    "    inorder(node.right, values);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: find the kth smallest value (1-indexed) in a BST. The BST property is the whole game.",
        "2. Recall the BST in-order property: traversing left → root → right yields values in ascending order. So the kth element of the in-order sequence is the answer.",
        "3. Brute force: collect every value with an in-order DFS, return `values[k-1]`. `O(n)` time, `O(n)` space. Easy to write.",
        "4. Optimise: replace the recursive walk with an explicit stack so we can break out of the loop as soon as `k` nodes have been popped. Time drops to `O(h + k)`, space to `O(h)`.",
        "5. The iterative pattern: descend the leftmost spine pushing each node, pop one (smallest unvisited), decrement `k`. If `k == 0` we're done; otherwise step into the popped node's right child and repeat the descent.",
        "6. Edge cases to mention: `k == 1` (just go leftmost), `k == n` (effectively rightmost), single-node tree, skewed trees where `h == n` (then the optimal bound is `O(n)` anyway).",
        "7. Follow-up: if the BST is modified frequently and the kth-smallest query is hot, augment each node with a subtree size. Then queries and updates both run in `O(h)`.",
    ],
    "tips": [
        "Lead with the BST in-order property — interviewers want to hear *why* in-order works before they see code. Saying 'in-order on a BST is sorted' demonstrates fluency.",
        "Don't write the full-collect O(n) version and stop. State it as the brute force, then immediately propose the iterative early-stop version. That progression is the signal of a strong candidate.",
        "Be careful with the 1-indexed vs 0-indexed pitfall. Decrement `k` after each pop and check `k == 0`, or use a separate `count` variable that you compare to `k`. Pick one and be consistent.",
        "The classic bug: forgetting to step into `node.right` after a pop, which causes the loop to spin or terminate early. The pattern `node = node.right` after the pop is mandatory.",
        "If asked the follow-up about frequent modifications, propose an order-statistic tree: each node stores `size = 1 + size(left) + size(right)`. Lookups and updates are both `O(h)`.",
        "Recursion depth on a skewed tree with `n = 10^4` can blow the default Python recursion limit (1000). Mention this if you go recursive; the iterative version sidesteps the issue.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Meta", "Bloomberg", "Apple", "Uber"],
    "topics": ["Tree", "Depth-First Search", "Binary Search Tree", "Binary Tree", "Stack"],
    "time_complexity": "O(h + k)",
    "space_complexity": "O(h)",
}


def REFERENCE(root, k):
    """Build the BST from the level-order list and return the kth-smallest value."""
    tree = _build(root)
    return _kth_smallest(tree, k)


register(PAYLOAD, REFERENCE)
