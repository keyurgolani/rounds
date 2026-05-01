"""Balanced Binary Tree — Easy. Tree / DFS / Recursion.

LeetCode 110. The classic 'where do you put the work?' question. The
naive recurrence — `is_balanced(root) = |h(L) - h(R)| <= 1 and
is_balanced(L) and is_balanced(R)` — is correct but O(n log n) at
best and O(n²) on a skewed tree because each `is_balanced` call
re-walks the subtree to compute height.

The optimal version folds height and balance into a single post-order
return: a node returns its height, or a sentinel (-1) signalling 'an
unbalanced subtree was found below me, propagate failure'. One pass,
O(n) time, O(h) stack.
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


def _check(node):
    """Post-order: return height, or -1 if the subtree rooted here is unbalanced."""
    if node is None:
        return 0
    lh = _check(node["left"])
    if lh == -1:
        return -1
    rh = _check(node["right"])
    if rh == -1:
        return -1
    if abs(lh - rh) > 1:
        return -1
    return 1 + max(lh, rh)


PAYLOAD = {
    "title": "Balanced Binary Tree",
    "difficulty": "Easy",
    "description": (
        "Given the `root` of a binary tree, determine if it is **height-balanced**: for every node in the "
        "tree, the heights of its left and right subtrees differ by at most 1.\n\n"
        "The input uses LeetCode level-order serialization where `null` denotes a missing child. The empty "
        "tree is considered balanced.\n\n"
        "**Example 1:**\n"
        "```\n"
        "Tree:    3\n"
        "        / \\\n"
        "       9  20\n"
        "          / \\\n"
        "         15  7\n"
        "```\n"
        "- Input: `root = [3, 9, 20, null, null, 15, 7]`\n"
        "- Output: `true`\n"
        "- Explanation: At every node the two subtree heights differ by at most 1.\n\n"
        "**Example 2:**\n"
        "```\n"
        "Tree:        1\n"
        "            / \\\n"
        "           2   2\n"
        "          / \\\n"
        "         3   3\n"
        "        / \\\n"
        "       4   4\n"
        "```\n"
        "- Input: `root = [1, 2, 2, 3, 3, null, null, 4, 4]`\n"
        "- Output: `false`\n"
        "- Explanation: The left subtree of the root has height 3 while the right subtree has height 1 — "
        "they differ by 2."
    ),
    "hints": [
        "Definition is recursive — but the obvious translation `is_balanced(L) && is_balanced(R) && "
        "|h(L)-h(R)| <= 1` re-walks each subtree to compute height. That's O(n log n) on a balanced tree "
        "and O(n²) on a skewed one. Can you do better?",
        "Fold the two questions ('how tall am I?' and 'am I balanced?') into a single post-order return: "
        "compute the child heights first, then decide.",
        "Use a sentinel — return `-1` to mean 'an imbalance was detected in my subtree, abort'. As soon as "
        "any child reports `-1`, propagate it upward without doing more work.",
        "When neither child returned `-1`, check `abs(lh - rh) <= 1`. If yes, return `1 + max(lh, rh)`. If "
        "no, return `-1`. The final answer is `_check(root) != -1`.",
        "Edge case: an empty tree is balanced by definition. Return `true`. A single node is also balanced "
        "(both subtrees have height 0, differ by 0).",
    ],
    "constraints": [
        "The number of nodes in the tree is in the range `[0, 5000]`.",
        "-10⁴ <= Node.val <= 10⁴",
        "The tree may be highly skewed — recursion depth can reach the node count.",
    ],
    "starter_code": {
        "python": (
            "# Definition for a binary tree node.\n"
            "# class TreeNode:\n"
            "#     def __init__(self, val=0, left=None, right=None):\n"
            "#         self.val = val\n"
            "#         self.left = left\n"
            "#         self.right = right\n"
            "def is_balanced(root):\n"
            "    # `root` is a LeetCode-style level-order list with None for missing children.\n"
            "    # Return True if the tree is height-balanced, else False.\n"
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
            "function isBalanced(root) {\n"
            "    // `root` is a level-order array with null for missing children.\n"
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
            "public boolean isBalanced(java.util.List<Integer> root) {\n"
            "    // `root` is a level-order list with null for missing children.\n"
            "    // Your code here\n"
            "    return false;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [3, 9, 20, None, None, 15, 7],\n"
            "        [1, 2, 2, 3, 3, None, None, 4, 4],\n"
            "        [],\n"
            "    ]\n"
            "    for c in cases:\n"
            "        print(f\"is_balanced({c}) = {is_balanced(c)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[3, 9, 20, null, null, 15, 7], [1, 2, 2, 3, 3, null, null, 4, 4], []].forEach(c =>\n"
            "    console.log(`isBalanced =`, isBalanced(c))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.isBalanced(java.util.Arrays.asList(3, 9, 20, null, null, 15, 7)));\n"
            "        System.out.println(s.isBalanced(java.util.Arrays.asList(1, 2, 2, 3, 3, null, null, 4, 4)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": []}, "expected": True,
         "description": "Empty tree is balanced by definition", "tags": ["edge"]},
        {"input": {"root": [1]}, "expected": True,
         "description": "Single node — both subtrees empty, heights differ by 0", "tags": ["edge"]},
        {"input": {"root": [1, 2, 3]}, "expected": True,
         "description": "Perfect 3-node tree — left and right are leaves", "tags": ["basic"]},
        {"input": {"root": [1, 2, 3, 4, 5, 6, 7]}, "expected": True,
         "description": "Perfect 7-node tree of depth 3 — fully balanced", "tags": ["basic"]},
        {"input": {"root": [3, 9, 20, None, None, 15, 7]}, "expected": True,
         "description": "Classic LeetCode example — balanced", "tags": ["basic"]},
        {"input": {"root": [1, 2, None, 3]}, "expected": False,
         "description": "Left-skewed chain of length 3 — root has heights 2 vs 0",
         "tags": ["basic"]},
        {"input": {"root": [1, 2, 2, 3, 3, None, None, 4, 4]}, "expected": False,
         "description": "Classic LeetCode unbalanced example — left subtree taller by 2",
         "tags": ["basic"]},
        {"input": {"root": [1, 2, 2, 3, None, None, 3, 4, None, None, 4]}, "expected": False,
         "description": "Imbalance on one side only — outer leaves 4 push left and right too deep",
         "tags": ["tricky"]},
        {"input": {"root": [1, 2, 2, 3, 3, None, None, 4, 4]},
         "expected": False,
         "description": "Subtle deep imbalance — extra layer only on one side of one subtree",
         "tags": ["tricky"]},
        {"input": {"root": [1, None, 2, None, 3]}, "expected": False,
         "description": "Right-skewed chain of length 3 — symmetric failure of the left-skew case",
         "tags": ["edge"]},
        {"input": {"root": [1, 2, 2, 3, 3, 3, 3]}, "expected": True,
         "description": "Complete tree of depth 3 with duplicate values — balanced",
         "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Post-Order DFS with -1 Sentinel (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h) recursion stack — O(log n) balanced, O(n) skewed",
            "description": (
                "Single post-order traversal. Each call returns the height of its subtree, or `-1` to "
                "signal that an imbalance was detected somewhere below. The parent short-circuits as soon "
                "as a child returns `-1`. Each node is visited exactly once, so the total work is O(n) — "
                "the trick that beats the naive O(n log n) / O(n²) recompute."
            ),
            "code": {
                "python": (
                    "def is_balanced(root):\n"
                    "    node = _from_level(root)\n"
                    "    def check(n):\n"
                    "        if n is None:\n"
                    "            return 0\n"
                    "        lh = check(n.left)\n"
                    "        if lh == -1:\n"
                    "            return -1\n"
                    "        rh = check(n.right)\n"
                    "        if rh == -1:\n"
                    "            return -1\n"
                    "        if abs(lh - rh) > 1:\n"
                    "            return -1\n"
                    "        return 1 + max(lh, rh)\n"
                    "    return check(node) != -1"
                ),
                "javascript": (
                    "function isBalanced(root) {\n"
                    "    const node = fromLevel(root);\n"
                    "    const check = (n) => {\n"
                    "        if (n === null) return 0;\n"
                    "        const lh = check(n.left);\n"
                    "        if (lh === -1) return -1;\n"
                    "        const rh = check(n.right);\n"
                    "        if (rh === -1) return -1;\n"
                    "        if (Math.abs(lh - rh) > 1) return -1;\n"
                    "        return 1 + Math.max(lh, rh);\n"
                    "    };\n"
                    "    return check(node) !== -1;\n"
                    "}"
                ),
                "java": (
                    "public boolean isBalanced(java.util.List<Integer> root) {\n"
                    "    TreeNode node = fromLevel(root);\n"
                    "    return check(node) != -1;\n"
                    "}\n"
                    "private int check(TreeNode n) {\n"
                    "    if (n == null) return 0;\n"
                    "    int lh = check(n.left);\n"
                    "    if (lh == -1) return -1;\n"
                    "    int rh = check(n.right);\n"
                    "    if (rh == -1) return -1;\n"
                    "    if (Math.abs(lh - rh) > 1) return -1;\n"
                    "    return 1 + Math.max(lh, rh);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Naive Top-Down (Recompute Height per Node)",
            "time_complexity": "O(n log n) balanced, O(n²) skewed",
            "space_complexity": "O(h)",
            "description": (
                "Direct translation of the definition: a tree is balanced iff `|h(L) - h(R)| <= 1` AND "
                "both subtrees are themselves balanced. The pitfall is that `height(n)` is called at every "
                "node, and each call re-walks the subtree — so each node is touched once per ancestor on "
                "its path to the root. For balanced trees that's O(log n) ancestors → O(n log n) total; "
                "for a degenerate skewed tree it's O(n²)."
            ),
            "code": {
                "python": (
                    "def is_balanced(root):\n"
                    "    node = _from_level(root)\n"
                    "    def height(n):\n"
                    "        if n is None:\n"
                    "            return 0\n"
                    "        return 1 + max(height(n.left), height(n.right))\n"
                    "    def check(n):\n"
                    "        if n is None:\n"
                    "            return True\n"
                    "        if abs(height(n.left) - height(n.right)) > 1:\n"
                    "            return False\n"
                    "        return check(n.left) and check(n.right)\n"
                    "    return check(node)"
                ),
                "javascript": (
                    "function isBalanced(root) {\n"
                    "    const node = fromLevel(root);\n"
                    "    const height = (n) => n === null ? 0 : 1 + Math.max(height(n.left), height(n.right));\n"
                    "    const check = (n) => {\n"
                    "        if (n === null) return true;\n"
                    "        if (Math.abs(height(n.left) - height(n.right)) > 1) return false;\n"
                    "        return check(n.left) && check(n.right);\n"
                    "    };\n"
                    "    return check(node);\n"
                    "}"
                ),
                "java": (
                    "public boolean isBalanced(java.util.List<Integer> root) {\n"
                    "    TreeNode node = fromLevel(root);\n"
                    "    return check(node);\n"
                    "}\n"
                    "private int height(TreeNode n) {\n"
                    "    if (n == null) return 0;\n"
                    "    return 1 + Math.max(height(n.left), height(n.right));\n"
                    "}\n"
                    "private boolean check(TreeNode n) {\n"
                    "    if (n == null) return true;\n"
                    "    if (Math.abs(height(n.left) - height(n.right)) > 1) return false;\n"
                    "    return check(n.left) && check(n.right);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate the definition: balanced means |h(L) - h(R)| <= 1 at *every* node — not just the root.",
        "2. First instinct: write `is_balanced(n) = |h(L) - h(R)| <= 1 AND is_balanced(L) AND "
        "is_balanced(R)`. Correct, but `h()` is called separately and re-walks subtrees.",
        "3. Cost analysis of the naive version: at depth d, height() costs O(n / 2^d) (subtree size). "
        "Summed over all nodes: O(n log n) for balanced, O(n²) for skewed.",
        "4. Insight: the moment we know the height of a subtree, we already know if *it* is balanced. So "
        "fold the two questions into one post-order return.",
        "5. Encode the balance check in the return value: a healthy subtree returns its height; an "
        "unhealthy one returns a sentinel (`-1`). Parent short-circuits on `-1`.",
        "6. Final answer: `check(root) != -1`. Each node visited once → O(n) time, O(h) stack.",
        "7. Edge cases: empty tree → balanced (return True). Single node → balanced (heights 0 and 0).",
    ],
    "tips": [
        "Lead with the naive version if it helps you think — but flag the O(n log n) / O(n²) cost yourself "
        "before the interviewer points it out. That earns more credit than pretending you didn't notice.",
        "The `-1` sentinel only works because heights are non-negative. If the problem allowed negative "
        "heights for some reason, you'd need a tuple `(height, ok)` or a thrown exception instead.",
        "Don't compute `height(left)` and `height(right)` and then *separately* recurse — that's the trap. "
        "The whole point of the optimal version is that one post-order pass answers both questions.",
        "Common follow-up: 'now make the tree balanced.' That's a different problem (LC 1382 — convert "
        "BST to balanced BST via in-order list and rebuild). Mention it if asked.",
        "Another classic follow-up: 'is this an AVL tree?' AVL adds the BST ordering invariant on top of "
        "the height-balance condition. Same recursion, plus a min/max check per node.",
        "Watch the definition: 'differ by at most 1' means `<= 1`, not `< 1`. Off-by-one here will fail "
        "the LeetCode `[3,9,20,null,null,15,7]` case.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Apple", "Bloomberg", "Adobe"],
    "topics": ["Tree", "Depth-First Search", "Binary Tree", "Recursion"],
    "time_complexity": "O(n)",
    "space_complexity": "O(h)",
}


class _TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def _from_level(arr):
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
    """Take a level-order list, return True iff the tree is height-balanced."""
    tree = _build(root)
    return _check(tree) != -1


register(PAYLOAD, REFERENCE)
