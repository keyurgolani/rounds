"""Binary Tree Inorder Traversal — Easy. Tree / DFS / Stack.

LeetCode 94. The canonical 'can you write a tree traversal under stress'
question. Trivial in three lines of recursion; the interesting follow-ups
are the explicit-stack iterative version and Morris traversal (O(1) extra
space, mutates pointers temporarily).

The user function receives the `TreeNode root` directly and returns a flat
list of ints for the visit order.
"""
from builder.registry import register

from builder._shorthand import level_order_to_verbose, inflate_tree

def _inorder(node, out):
    if node is None:
        return
    _inorder(node["left"], out)
    out.append(node["val"])
    _inorder(node["right"], out)

PAYLOAD = {
    "title": "Binary Tree Inorder Traversal",
    "difficulty": "Easy",
    "description": (
        "Given the `root` of a binary tree, return the **inorder traversal** of its nodes' values.\n\n"
        "Inorder visits a node *between* its left and right subtrees: traverse left, visit root, traverse "
        "right. For a binary search tree, this yields the values in sorted order — a fact worth mentioning.\n\n"
        "The function receives the `TreeNode root` directly and returns a flat list of integers in visit order.\n\n"
        "**Example 1:**\n"
        "- Input: the tree shown below\n"
        "- Output: `[1,3,2]`\n"
        "- Explanation:\n"
        "```\n"
        "   1\n"
        "    \\\n"
        "     2\n"
        "    /\n"
        "   3\n"
        "```\n"
        "Visit left of 1 (none), visit 1, recurse right into 2 → visit left of 2 which is 3 → "
        "visit 2 → no right.\n\n"
        "**Example 2:**\n"
        "- Input: a balanced BST with root `4`, children `2` and `6`, and leaves `1,3,5,7`\n"
        "- Output: `[1,2,3,4,5,6,7]`\n"
        "- Explanation: This is a balanced BST, so inorder produces sorted output."
    ),
    "hints": [
        "The recursive definition writes itself: `inorder(left) ++ [root.val] ++ inorder(right)`. Three "
        "lines, base case `None → []`.",
        "Iterative version with an explicit stack: walk left as far as possible pushing every node, then "
        "pop, record, and pivot to the popped node's right child. Repeat until both stack and current pointer are empty.",
        "The iterative loop has the shape `while current or stack`. Inside, push-left until you hit None, "
        "then pop, record, move to `node.right`. That's the entire algorithm.",
        "Morris traversal achieves O(1) extra space by temporarily threading the rightmost node of each "
        "left subtree to point back at the current root. You restore the pointer on the second visit, so "
        "the tree ends up unmodified.",
        "Edge cases: empty tree → `[]`; single node → `[val]`; left-only chain visits leaves first; "
        "right-only chain visits root first.",
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
            "def inorder_traversal(root):\n"
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
            "function inorderTraversal(root) {\n"
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
            "public List<Integer> inorderTraversal(TreeNode root) {\n"
            "    // Your code here\n"
            "    return new ArrayList<>();\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    # Build a small tree manually:  1\n"
            "    #                              \\\n"
            "    #                               2\n"
            "    #                              /\n"
            "    #                             3\n"
            "    root = TreeNode(1, None, TreeNode(2, TreeNode(3)))\n"
            "    print(inorder_traversal(root))  # [1, 3, 2]"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const root = { val: 1, left: null,\n"
            "    right: { val: 2, left: { val: 3, left: null, right: null }, right: null } };\n"
            "console.log(inorderTraversal(root));  // [1, 3, 2]"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.*;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        TreeNode root = new TreeNode(1, null, new TreeNode(2, new TreeNode(3), null));\n"
            "        System.out.println(s.inorderTraversal(root));  // [1, 3, 2]\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": level_order_to_verbose([])}, "expected": [],
         "description": "Empty tree — empty traversal", "tags": ["edge"]},
        {"input": {"root": level_order_to_verbose([1])}, "expected": [1],
         "description": "Single node — visit produces just the root", "tags": ["edge"]},
        {"input": {"root": level_order_to_verbose([1, None, 2, 3])}, "expected": [1, 3, 2],
         "description": "Classic LeetCode example shape — right child with a left subtree", "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([1, 2])}, "expected": [2, 1],
         "description": "Two-node tree, only left child — leaf visited before root", "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([1, None, 2])}, "expected": [1, 2],
         "description": "Two-node tree, only right child — root visited before leaf", "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([4, 2, 6, 1, 3, 5, 7])}, "expected": [1, 2, 3, 4, 5, 6, 7],
         "description": "Balanced BST — inorder is the sorted sequence", "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([5, 4, None, 3, None, 2, None, 1])}, "expected": [1, 2, 3, 4, 5],
         "description": "Left-only chain (skewed) — leaves first, root last", "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([1, None, 2, None, 3, None, 4, None, 5])}, "expected": [1, 2, 3, 4, 5],
         "description": "Right-only chain (skewed) — root first, leaves last", "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([3, 1, 4, None, 2])}, "expected": [1, 2, 3, 4],
         "description": "BST with interior null — sorted output sanity-checks the traversal", "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([0, -3, 9, -10, None, 5])}, "expected": [-10, -3, 0, 5, 9],
         "description": "Negative values and an interior null", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Recursive (Cleanest)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h)",
            "description": (
                "Three-line recursion: traverse left, append root, traverse right. `h` is the tree height "
                "and bounds the call-stack depth — `O(log n)` for balanced trees, `O(n)` worst case."
            ),
            "code": {
                "python": (
                    "def inorder_traversal(root):\n"
                    "    out = []\n"
                    "    def go(node):\n"
                    "        if node is None:\n"
                    "            return\n"
                    "        go(node.left)\n"
                    "        out.append(node.val)\n"
                    "        go(node.right)\n"
                    "    go(root)\n"
                    "    return out"
                ),
                "javascript": (
                    "function inorderTraversal(root) {\n"
                    "    const out = [];\n"
                    "    const go = (node) => {\n"
                    "        if (node === null) return;\n"
                    "        go(node.left);\n"
                    "        out.push(node.val);\n"
                    "        go(node.right);\n"
                    "    };\n"
                    "    go(root);\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public List<Integer> inorderTraversal(TreeNode root) {\n"
                    "    List<Integer> out = new ArrayList<>();\n"
                    "    go(root, out);\n"
                    "    return out;\n"
                    "}\n"
                    "private void go(TreeNode node, List<Integer> out) {\n"
                    "    if (node == null) return;\n"
                    "    go(node.left, out);\n"
                    "    out.add(node.val);\n"
                    "    go(node.right, out);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative with Explicit Stack",
            "time_complexity": "O(n)",
            "space_complexity": "O(h)",
            "description": (
                "Replace the call stack with a manual one. Outer loop runs while `current` is non-null "
                "or the stack is non-empty: push-left until you hit null, then pop, record the value, "
                "and pivot to the popped node's right child. Same asymptotic space as recursion but no "
                "interpreter-stack risk on deep trees."
            ),
            "code": {
                "python": (
                    "def inorder_traversal(root):\n"
                    "    out, stack, cur = [], [], root\n"
                    "    while cur or stack:\n"
                    "        while cur:\n"
                    "            stack.append(cur)\n"
                    "            cur = cur.left\n"
                    "        cur = stack.pop()\n"
                    "        out.append(cur.val)\n"
                    "        cur = cur.right\n"
                    "    return out"
                ),
                "javascript": (
                    "function inorderTraversal(root) {\n"
                    "    const out = [];\n"
                    "    const stack = [];\n"
                    "    let cur = root;\n"
                    "    while (cur !== null || stack.length) {\n"
                    "        while (cur !== null) {\n"
                    "            stack.push(cur);\n"
                    "            cur = cur.left;\n"
                    "        }\n"
                    "        cur = stack.pop();\n"
                    "        out.push(cur.val);\n"
                    "        cur = cur.right;\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public List<Integer> inorderTraversal(TreeNode root) {\n"
                    "    List<Integer> out = new ArrayList<>();\n"
                    "    Deque<TreeNode> stack = new ArrayDeque<>();\n"
                    "    TreeNode cur = root;\n"
                    "    while (cur != null || !stack.isEmpty()) {\n"
                    "        while (cur != null) {\n"
                    "            stack.push(cur);\n"
                    "            cur = cur.left;\n"
                    "        }\n"
                    "        cur = stack.pop();\n"
                    "        out.add(cur.val);\n"
                    "        cur = cur.right;\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Morris Traversal (O(1) Space)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "For each node with a left child, find the rightmost node of its left subtree (the "
                "in-order predecessor) and thread its right pointer back to the current node. The first "
                "time we reach a node we descend left; on returning via the thread we record the value and "
                "tear the thread down before descending right. Each edge is traversed a constant number "
                "of times, so total work is O(n) and the only extra space is two pointers — but the trick "
                "is that the tree is *temporarily* mutated, which interviewers love to grill you on."
            ),
            "code": {
                "python": (
                    "def inorder_traversal(root):\n"
                    "    out, cur = [], root\n"
                    "    while cur:\n"
                    "        if cur.left is None:\n"
                    "            out.append(cur.val)\n"
                    "            cur = cur.right\n"
                    "        else:\n"
                    "            pred = cur.left\n"
                    "            while pred.right and pred.right is not cur:\n"
                    "                pred = pred.right\n"
                    "            if pred.right is None:\n"
                    "                pred.right = cur          # thread\n"
                    "                cur = cur.left\n"
                    "            else:\n"
                    "                pred.right = None         # un-thread\n"
                    "                out.append(cur.val)\n"
                    "                cur = cur.right\n"
                    "    return out"
                ),
                "javascript": (
                    "function inorderTraversal(root) {\n"
                    "    const out = [];\n"
                    "    let cur = root;\n"
                    "    while (cur !== null) {\n"
                    "        if (cur.left === null) {\n"
                    "            out.push(cur.val);\n"
                    "            cur = cur.right;\n"
                    "        } else {\n"
                    "            let pred = cur.left;\n"
                    "            while (pred.right !== null && pred.right !== cur) {\n"
                    "                pred = pred.right;\n"
                    "            }\n"
                    "            if (pred.right === null) {\n"
                    "                pred.right = cur;\n"
                    "                cur = cur.left;\n"
                    "            } else {\n"
                    "                pred.right = null;\n"
                    "                out.push(cur.val);\n"
                    "                cur = cur.right;\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public List<Integer> inorderTraversal(TreeNode root) {\n"
                    "    List<Integer> out = new ArrayList<>();\n"
                    "    TreeNode cur = root;\n"
                    "    while (cur != null) {\n"
                    "        if (cur.left == null) {\n"
                    "            out.add(cur.val);\n"
                    "            cur = cur.right;\n"
                    "        } else {\n"
                    "            TreeNode pred = cur.left;\n"
                    "            while (pred.right != null && pred.right != cur) {\n"
                    "                pred = pred.right;\n"
                    "            }\n"
                    "            if (pred.right == null) {\n"
                    "                pred.right = cur;\n"
                    "                cur = cur.left;\n"
                    "            } else {\n"
                    "                pred.right = null;\n"
                    "                out.add(cur.val);\n"
                    "                cur = cur.right;\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: inorder visits left subtree, then node, then right subtree. For a BST this yields sorted output — note that out loud.",
        "2. Default solution: recursion. Three lines plus a base case. Clear and obvious — start there.",
        "3. Interviewer pushback: 'do it iteratively'. Simulate the call stack with an explicit stack: push-left until null, pop & record, pivot right. Same O(h) space.",
        "4. Follow-up: 'O(1) space'. That's Morris traversal — thread the rightmost node of each left subtree back to its in-order successor, tear the thread on the way back.",
        "5. Edge cases: empty tree → [], single node → [val], skewed chains (left-only / right-only) test that the order logic is right rather than just 'visit everything'.",
        "6. Complexity: every node visited once → O(n) time. Space is O(h) for the recursive/iterative versions, O(1) for Morris.",
    ],
    "tips": [
        "Mention up front that inorder on a BST gives sorted output — interviewers like seeing that connection without prompting.",
        "When writing the iterative version, the structure `while cur or stack` with an inner `while cur` is the canonical shape. Write it from muscle memory; don't reinvent it under stress.",
        "Don't conflate the iterative inorder template with the iterative preorder template. Inorder pushes-then-records-on-pop; preorder records-on-push. Mixing them is a classic interview slip.",
        "Morris traversal *mutates* the tree mid-flight. Even though it restores everything by the end, in a multi-threaded context this is observable — call this out as a caveat if asked.",
        "If the interviewer asks how you'd do preorder or postorder iteratively, the same explicit-stack idea adapts: preorder is record-then-push-children; postorder is trickier (two stacks, or a 'visited' flag, or reverse a modified preorder).",
        "Watch the base case: returning `[]` (not `None`) for an empty tree matters — the function returns a list, not an Optional.",
    ],
    "companies": ["Microsoft", "Amazon", "Google", "Facebook", "Apple", "Bloomberg"],
    "topics": ["Stack", "Tree", "Depth-First Search", "Binary Tree"],
    "time_complexity": "O(n)",
    "space_complexity": "O(h)",
    "entry": {
        "kind": "tree",
        "name": "inorder_traversal",
        "params": [{"name": "root", "type": "node"}],
    },
}

def REFERENCE(root):
    """Take a level-order list, return the inorder traversal as a flat list of ints."""
    tree = inflate_tree(root)
    out = []
    _inorder(tree, out)
    return out

register(PAYLOAD, REFERENCE)
