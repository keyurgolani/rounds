"""Construct Binary Tree from Preorder and Inorder Traversal — Medium. Tree / DFS / Hash Map.

LeetCode 105. Classic recursion problem: the first element of preorder is
always the current subtree's root; locating it inside inorder gives the
exact split between the left and right subtrees. Repeat recursively. The
O(n) optimum uses a value→index hashmap on `inorder` to avoid the inner
linear scan.

Input is two integer arrays with unique values; output is the tree as a
LeetCode level-order list with `null` for missing nodes (trailing nulls
stripped).
"""
from collections import deque

from builder.registry import register


def _serialize(root):
    """Serialize tree (dict-shaped) back to LeetCode level-order list with None for missing.

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


def _build(preorder, inorder):
    """Reference construction: O(n) recursive build using a value→index map on inorder."""
    if not preorder or not inorder:
        return None
    idx = {v: i for i, v in enumerate(inorder)}
    pre_iter = iter(preorder)

    def helper(lo, hi):
        if lo > hi:
            return None
        val = next(pre_iter)
        node = {"val": val, "left": None, "right": None}
        mid = idx[val]
        node["left"] = helper(lo, mid - 1)
        node["right"] = helper(mid + 1, hi)
        return node

    return helper(0, len(inorder) - 1)


PAYLOAD = {
    "title": "Construct Binary Tree from Preorder and Inorder Traversal",
    "difficulty": "Medium",
    "description": (
        "Given two integer arrays `preorder` and `inorder` where `preorder` is the **preorder traversal** "
        "of a binary tree and `inorder` is the **inorder traversal** of the same tree, construct and "
        "return the binary tree.\n\n"
        "All values in the tree are **unique**. The output is the tree serialized as a LeetCode "
        "level-order list using `null` for missing nodes (trailing nulls stripped).\n\n"
        "**Example 1:**\n"
        "- Input: `preorder = [3,9,20,15,7]`, `inorder = [9,3,15,20,7]`\n"
        "- Output: `[3,9,20,null,null,15,7]`\n"
        "- Explanation:\n"
        "```\n"
        "      3\n"
        "     / \\\n"
        "    9   20\n"
        "       /  \\\n"
        "      15   7\n"
        "```\n\n"
        "**Example 2:**\n"
        "- Input: `preorder = [-1]`, `inorder = [-1]`\n"
        "- Output: `[-1]`\n"
        "- Explanation: A single node tree."
    ),
    "hints": [
        "The very first element of `preorder` is always the root of the current subtree — preorder visits root before its children.",
        "Find that root inside `inorder`. Everything to its left belongs to the left subtree; everything to its right belongs to the right subtree.",
        "The size of the left subtree (call it `k`) tells you how to slice `preorder` too: indices `[1..k]` are the left preorder, `[k+1..]` are the right preorder.",
        "Repeated linear search inside `inorder` makes the algorithm O(n²). Build a `value → index` hashmap once up front so each lookup is O(1) — this turns the whole solution into O(n) time.",
        "Use a moving pointer (or an iterator) over `preorder` instead of slicing — slicing copies arrays and silently inflates space complexity to O(n²).",
    ],
    "constraints": [
        "1 <= preorder.length <= 3000  (the empty case `[]`,`[]` is also accepted by this problem and returns an empty tree).",
        "inorder.length == preorder.length",
        "All values in `preorder` and `inorder` are **unique**, and each value in `preorder` also appears in `inorder`.",
    ],
    "starter_code": {
        "python": (
            "# Definition for a binary tree node.\n"
            "# class TreeNode:\n"
            "#     def __init__(self, val=0, left=None, right=None):\n"
            "#         self.val = val\n"
            "#         self.left = left\n"
            "#         self.right = right\n"
            "def build_tree(preorder, inorder):\n"
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
            "function buildTree(preorder, inorder) {\n"
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
            "public TreeNode buildTree(int[] preorder, int[] inorder) {\n"
            "    // Your code here\n"
            "    return null;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    root = build_tree([3, 9, 20, 15, 7], [9, 3, 15, 20, 7])\n"
            "    # Expected root.val == 3, root.left.val == 9, root.right.val == 20\n"
            "    print(root.val, root.left.val, root.right.val)  # 3 9 20"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const root = buildTree([3, 9, 20, 15, 7], [9, 3, 15, 20, 7]);\n"
            "console.log(root.val, root.left.val, root.right.val);  // 3 9 20"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        TreeNode root = s.buildTree(new int[]{3, 9, 20, 15, 7}, new int[]{9, 3, 15, 20, 7});\n"
            "        System.out.println(root.val + \" \" + root.left.val + \" \" + root.right.val);\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"preorder": [], "inorder": []}, "expected": [],
         "description": "Empty tree — both arrays empty", "tags": ["edge"]},
        {"input": {"preorder": [1], "inorder": [1]}, "expected": [1],
         "description": "Single node", "tags": ["edge"]},
        {"input": {"preorder": [3, 9, 20, 15, 7], "inorder": [9, 3, 15, 20, 7]},
         "expected": [3, 9, 20, None, None, 15, 7],
         "description": "Classic LeetCode example — left leaf and right subtree", "tags": ["basic"]},
        {"input": {"preorder": [1, 2, 3, 4], "inorder": [4, 3, 2, 1]},
         "expected": [1, 2, None, 3, None, 4],
         "description": "Left-only chain (every node has only a left child)", "tags": ["tricky"]},
        {"input": {"preorder": [1, 2, 3, 4], "inorder": [1, 2, 3, 4]},
         "expected": [1, None, 2, None, 3, None, 4],
         "description": "Right-only chain (every node has only a right child)", "tags": ["tricky"]},
        {"input": {"preorder": [4, 2, 1, 3, 6, 5, 7], "inorder": [1, 2, 3, 4, 5, 6, 7]},
         "expected": [4, 2, 6, 1, 3, 5, 7],
         "description": "Perfect balanced BST of depth 3", "tags": ["basic"]},
        {"input": {"preorder": [10, 5, 1, 7, 40, 50], "inorder": [1, 5, 7, 10, 40, 50]},
         "expected": [10, 5, 40, 1, 7, None, 50],
         "description": "Lopsided BST — right subtree is itself right-skewed", "tags": ["tricky"]},
        {"input": {"preorder": [-1, -2, -3], "inorder": [-3, -2, -1]}, "expected": [-1, -2, None, -3],
         "description": "Negative values, left-skewed", "tags": ["edge"]},
        {"input": {"preorder": [8, 3, 1, 6, 4, 7, 10, 14, 13],
                   "inorder": [1, 3, 4, 6, 7, 8, 10, 13, 14]},
         "expected": [8, 3, 10, 1, 6, None, 14, None, None, 4, 7, 13],
         "description": "Larger tree with mixed left/right subtrees", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Recursive with HashMap (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Pre-compute a `value → index` map on `inorder` so locating the root inside `inorder` is "
                "O(1). Walk `preorder` left-to-right with a single moving pointer (or iterator). For each "
                "subtree defined by an inorder window `[lo, hi]`: take the next preorder element as the "
                "root, find its inorder index `mid`, recurse on `[lo, mid-1]` for the left subtree, then "
                "on `[mid+1, hi]` for the right. Each node is constructed exactly once → O(n) time. The "
                "hashmap and recursion stack are both O(n) worst case."
            ),
            "code": {
                "python": (
                    "def build_tree(preorder, inorder):\n"
                    "    if not preorder:\n"
                    "        return None\n"
                    "    idx = {v: i for i, v in enumerate(inorder)}\n"
                    "    pre_iter = iter(preorder)\n"
                    "\n"
                    "    def helper(lo, hi):\n"
                    "        if lo > hi:\n"
                    "            return None\n"
                    "        val = next(pre_iter)\n"
                    "        node = TreeNode(val)\n"
                    "        mid = idx[val]\n"
                    "        node.left = helper(lo, mid - 1)\n"
                    "        node.right = helper(mid + 1, hi)\n"
                    "        return node\n"
                    "\n"
                    "    return helper(0, len(inorder) - 1)"
                ),
                "javascript": (
                    "function buildTree(preorder, inorder) {\n"
                    "    if (preorder.length === 0) return null;\n"
                    "    const idx = new Map();\n"
                    "    inorder.forEach((v, i) => idx.set(v, i));\n"
                    "    let p = 0;\n"
                    "\n"
                    "    function helper(lo, hi) {\n"
                    "        if (lo > hi) return null;\n"
                    "        const val = preorder[p++];\n"
                    "        const node = new TreeNode(val);\n"
                    "        const mid = idx.get(val);\n"
                    "        node.left = helper(lo, mid - 1);\n"
                    "        node.right = helper(mid + 1, hi);\n"
                    "        return node;\n"
                    "    }\n"
                    "    return helper(0, inorder.length - 1);\n"
                    "}"
                ),
                "java": (
                    "import java.util.HashMap;\n"
                    "import java.util.Map;\n"
                    "\n"
                    "public class Solution {\n"
                    "    private int p = 0;\n"
                    "    private int[] preorder;\n"
                    "    private Map<Integer, Integer> idx;\n"
                    "\n"
                    "    public TreeNode buildTree(int[] preorder, int[] inorder) {\n"
                    "        if (preorder.length == 0) return null;\n"
                    "        this.preorder = preorder;\n"
                    "        this.idx = new HashMap<>();\n"
                    "        for (int i = 0; i < inorder.length; i++) idx.put(inorder[i], i);\n"
                    "        return helper(0, inorder.length - 1);\n"
                    "    }\n"
                    "\n"
                    "    private TreeNode helper(int lo, int hi) {\n"
                    "        if (lo > hi) return null;\n"
                    "        int val = preorder[p++];\n"
                    "        TreeNode node = new TreeNode(val);\n"
                    "        int mid = idx.get(val);\n"
                    "        node.left = helper(lo, mid - 1);\n"
                    "        node.right = helper(mid + 1, hi);\n"
                    "        return node;\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Recursive with Linear Search (Brute Force)",
            "time_complexity": "O(n^2)",
            "space_complexity": "O(n)",
            "description": (
                "Same shape of recursion, but locate the root in `inorder` with a linear scan instead of "
                "a hashmap. Worst case (skewed tree) does an O(n) scan at every level → O(n²) overall. "
                "Slicing the arrays at each call (often seen in tutorials) also bloats space to O(n²); "
                "passing `(lo, hi)` indices keeps space at O(n) for the recursion stack."
            ),
            "code": {
                "python": (
                    "def build_tree(preorder, inorder):\n"
                    "    if not preorder:\n"
                    "        return None\n"
                    "    pre_iter = iter(preorder)\n"
                    "\n"
                    "    def helper(lo, hi):\n"
                    "        if lo > hi:\n"
                    "            return None\n"
                    "        val = next(pre_iter)\n"
                    "        node = TreeNode(val)\n"
                    "        mid = lo\n"
                    "        while inorder[mid] != val:\n"
                    "            mid += 1\n"
                    "        node.left = helper(lo, mid - 1)\n"
                    "        node.right = helper(mid + 1, hi)\n"
                    "        return node\n"
                    "\n"
                    "    return helper(0, len(inorder) - 1)"
                ),
                "javascript": (
                    "function buildTree(preorder, inorder) {\n"
                    "    if (preorder.length === 0) return null;\n"
                    "    let p = 0;\n"
                    "\n"
                    "    function helper(lo, hi) {\n"
                    "        if (lo > hi) return null;\n"
                    "        const val = preorder[p++];\n"
                    "        const node = new TreeNode(val);\n"
                    "        let mid = lo;\n"
                    "        while (inorder[mid] !== val) mid++;\n"
                    "        node.left = helper(lo, mid - 1);\n"
                    "        node.right = helper(mid + 1, hi);\n"
                    "        return node;\n"
                    "    }\n"
                    "    return helper(0, inorder.length - 1);\n"
                    "}"
                ),
                "java": (
                    "public class Solution {\n"
                    "    private int p = 0;\n"
                    "    private int[] preorder;\n"
                    "    private int[] inorder;\n"
                    "\n"
                    "    public TreeNode buildTree(int[] preorder, int[] inorder) {\n"
                    "        if (preorder.length == 0) return null;\n"
                    "        this.preorder = preorder;\n"
                    "        this.inorder = inorder;\n"
                    "        return helper(0, inorder.length - 1);\n"
                    "    }\n"
                    "\n"
                    "    private TreeNode helper(int lo, int hi) {\n"
                    "        if (lo > hi) return null;\n"
                    "        int val = preorder[p++];\n"
                    "        TreeNode node = new TreeNode(val);\n"
                    "        int mid = lo;\n"
                    "        while (inorder[mid] != val) mid++;\n"
                    "        node.left = helper(lo, mid - 1);\n"
                    "        node.right = helper(mid + 1, hi);\n"
                    "        return node;\n"
                    "    }\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: rebuild a binary tree given its preorder and inorder traversals; values are unique.",
        "2. Key insight #1: preorder visits root → left → right, so `preorder[0]` is the root of the whole tree (and recursively, of every subtree).",
        "3. Key insight #2: inorder visits left → root → right, so once you know the root's value, its position in `inorder` cleanly partitions inorder into the left subtree's inorder and the right subtree's inorder.",
        "4. Recurse: take the next element of `preorder` as the current root, split `inorder` around it, then build left and right subtrees from the corresponding slices.",
        "5. Optimization: avoid the O(n) scan to locate the root in `inorder` by pre-building a `value → index` map. This turns O(n²) into O(n).",
        "6. Avoid slicing the arrays at every recursion — pass `(lo, hi)` index ranges instead. Slicing makes space complexity O(n²).",
        "7. Use a single shared pointer/iterator over `preorder` so each node is consumed exactly once in DFS order.",
        "8. Edge cases: empty arrays → empty tree; single element → leaf.",
    ],
    "tips": [
        "State the two invariants out loud before coding: 'preorder[0] is the root' and 'inorder splits into left | root | right'. The recursion almost writes itself.",
        "Don't slice the input arrays — it's O(n) per call and silently turns the algorithm into O(n²) time and O(n²) space. Pass indices.",
        "Build the inorder index map *once* before recursing. Building it inside the helper (a common bug) defeats the optimization.",
        "Use a single moving pointer over `preorder` (an iterator in Python, an instance variable in Java/JS). Recomputing the preorder index from the subtree size is error-prone.",
        "Sister problem: 'Construct Binary Tree from Inorder and Postorder' (LC 106). Same idea, but consume postorder from the *back* and recurse right subtree first.",
        "Common follow-up: 'Could you do it without inorder?' — only possible if the tree is a BST (LC 1008) or full (LC 889).",
        "Sanity-check on input: the problem promises unique values. If duplicates were allowed, the inorder index would be ambiguous and the problem would be unsolvable from these two traversals alone.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Bloomberg", "Facebook", "Apple"],
    "topics": ["Tree", "Array", "Hash Table", "Divide and Conquer", "Binary Tree", "Depth-First Search"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(preorder, inorder):
    """Build the tree from preorder + inorder, return its level-order list with nulls."""
    tree = _build(list(preorder), list(inorder))
    return _serialize(tree)


register(PAYLOAD, REFERENCE)
