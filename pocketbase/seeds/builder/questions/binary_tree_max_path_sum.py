"""Binary Tree Maximum Path Sum — Hard. Trees / DFS.

LeetCode 124. Same recursive shape as Diameter of Binary Tree (LC 543),
but instead of returning a *height* and tracking longest length, we return
the maximum **gain** a subtree can contribute to a path that descends from
its root, and we track a global maximum for paths that *bend* at any node.

Key twist over diameter: subtree contributions can be negative, so they
must be clamped to zero (i.e. "skip that branch") before being combined.
The bent-path candidate at a node is `node.val + max(0, leftGain) +
max(0, rightGain)`; the value returned upward is `node.val + max(0,
max(leftGain, rightGain))`, because a path going through an ancestor can
only extend one side.

Input is the binary tree root; output is an int (the maximum path sum).
"""
from builder.registry import register

from builder._shorthand import level_order_to_verbose, inflate_tree
PAYLOAD = {
    "title": "Binary Tree Maximum Path Sum",
    "difficulty": "Hard",
    "description": (
        "A **path** in a binary tree is a sequence of nodes where each pair of adjacent nodes is "
        "connected by an edge. A node may appear in the path **at most once**, and the path does "
        "**not** need to pass through the root.\n\n"
        "The **path sum** is the sum of the node values along the path.\n\n"
        "Given the `root` of a binary tree, return the **maximum path sum** of any non-empty path.\n\n"
        "**Example 1:**\n"
        "```\n"
        "Tree:    1\n"
        "        / \\\n"
        "       2   3\n"
        "```\n"
        "- Input: `root = [1,2,3]`\n"
        "- Output: `6`\n"
        "- Explanation: the optimal path is `2 -> 1 -> 3`, summing to `2 + 1 + 3 = 6`.\n\n"
        "**Example 2:**\n"
        "```\n"
        "Tree:    -10\n"
        "         /  \\\n"
        "        9   20\n"
        "            / \\\n"
        "           15  7\n"
        "```\n"
        "- Input: `root = [-10,9,20,null,null,15,7]`\n"
        "- Output: `42`\n"
        "- Explanation: the optimal path is `15 -> 20 -> 7`, summing to `15 + 20 + 7 = 42`. The "
        "root `-10` is skipped because including it would lower the total."
    ),
    "hints": [
        "DFS each node and return the **maximum gain** a path starting at that node and going **down** "
        "one side can contribute: `node.val + max(0, max(leftGain, rightGain))`. The `max(0, ...)` is "
        "what lets you discard a negative branch.",
        "Update a **global maximum** at every node with the value of a path that **bends at this node**: "
        "`node.val + max(0, leftGain) + max(0, rightGain)`. This is the only place you combine both sides.",
        "Clamp negative subtree contributions to `0` before adding — choosing 'don't extend into that "
        "branch' is always at least as good as extending into a negative one.",
        "Initialise the global max to `-infinity` (not `0`). All-negative trees have a negative answer, "
        "and the path must contain at least one node.",
        "Same recursive shape as Diameter of Binary Tree (LC 543) — single post-order DFS, return one "
        "thing upward, update a side-effect maximum. Time `O(n)`, space `O(h)` for the recursion stack.",
    ],
    "constraints": [
        "The number of nodes in the tree is in the range `[1, 3 * 10^4]`.",
        "-1000 <= Node.val <= 1000",
        "Negative node values are allowed; the path must contain at least one node.",
    ],
    "starter_code": {
        "python": (
            "# Definition for a binary tree node.\n"
            "# class TreeNode:\n"
            "#     def __init__(self, val=0, left=None, right=None):\n"
            "#         self.val = val\n"
            "#         self.left = left\n"
            "#         self.right = right\n"
            "# Return the maximum path sum (any non-empty path) as an int.\n"
            "#\n"
            "# Hint: a recursive helper that returns the max downward gain from a node\n"
            "# while updating a shared `best` (e.g. `best = [-float('inf')]`) is the cleanest pattern.\n"
            "def max_path_sum(root):\n"
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
            "// Return the maximum path sum as a number.\n"
            "//\n"
            "// Hint: capture a `best` variable in a closure, recurse and return\n"
            "// the max downward gain from each node while updating `best`.\n"
            "function maxPathSum(root) {\n"
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
            "// Return the maximum path sum as an int.\n"
            "//\n"
            "// Hint: an instance field `int best = Integer.MIN_VALUE` lets a recursive\n"
            "// helper update a shared maximum while returning each subtree's max gain upward.\n"
            "public int maxPathSum(TreeNode root) {\n"
            "    // Your code here\n"
            "    return 0;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[1, 2, 3], [-10, 9, 20, None, None, 15, 7], [-3], [1]]\n"
            "    for c in cases:\n"
            "        print(f\"max_path_sum({c}) = {max_path_sum(c)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1, 2, 3], [-10, 9, 20, null, null, 15, 7], [-3], [1]].forEach(c =>\n"
            "    console.log(`maxPathSum =`, maxPathSum(c))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.maxPathSum(java.util.Arrays.asList(-10, 9, 20, null, null, 15, 7)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": level_order_to_verbose([1])}, "expected": 1,
         "description": "Single node — path is just that node", "tags": ["edge"]},
        {"input": {"root": level_order_to_verbose([-3])}, "expected": -3,
         "description": "Single negative node — path must contain at least one node, so answer is -3",
         "tags": ["edge"]},
        {"input": {"root": level_order_to_verbose([1, 2, 3])}, "expected": 6,
         "description": "Classic small example — path 2→1→3 sums to 6", "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([-10, 9, 20, None, None, 15, 7])}, "expected": 42,
         "description": "Classic LeetCode example — path 15→20→7 = 42; root -10 is skipped",
         "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([-2, -1, -3])}, "expected": -1,
         "description": "All-negative tree — best is the single largest node (-1)",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([1, 2, None, 3, None, 4, None, 5])}, "expected": 15,
         "description": "Left-skewed positive chain of 5 → take the whole chain = 1+2+3+4+5 = 15",
         "tags": ["basic"]},
        {"input": {"root": level_order_to_verbose([-1, 2, 3, -4, 5, -6, 7])}, "expected": 16,
         "description": "Mixed signs — best path bends at root: 5→2→-1→3→7 = 16 (negative branches "
                        "-4 and -6 are skipped)",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([5, 4, 8, 11, None, 13, 4, 7, 2, None, None, None, 1])}, "expected": 48,
         "description": "Deep imbalance — path 7→11→4→5→8→13 = 48",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([10, 2, 10, 20, 1, None, -25, None, None, None, None, 3, 4])}, "expected": 42,
         "description": "Best path does NOT pass through root — 20→2→10→1 = 33? Actually 20→2→10 = 32, "
                        "best is 20+2+10+10 = 42 going through root",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([2, -1, -2])}, "expected": 2,
         "description": "Root positive, both children negative — best is just the root alone",
         "tags": ["tricky"]},
        {"input": {"root": level_order_to_verbose([-3, 1, 2, -1, None, None, 3])}, "expected": 5,
         "description": "Best path lives in a subtree, root not on it — path 1→-3→2→3 = 3? "
                        "Actually best non-root path 3+2 = 5 (or 1 alone = 1); answer is 5",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "DFS Gain with Global Max (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h) recursion stack — O(log n) balanced, O(n) skewed",
            "description": (
                "A single post-order DFS. The helper returns the **maximum gain** a path can earn by "
                "starting at the current node and descending into **one** subtree: "
                "`node.val + max(0, max(leftGain, rightGain))`. The `max(0, ...)` clamps negative "
                "branches to zero — extending into a negative branch is never better than stopping.\n\n"
                "Independently, while computing that gain, update a shared `best` with the value of a "
                "path that **bends at this node** (uses both children): "
                "`node.val + max(0, leftGain) + max(0, rightGain)`. This is the only place both subtrees "
                "are combined, since a path through an ancestor can extend only one side.\n\n"
                "Initialise `best` to `-infinity` so all-negative trees return their largest single node."
            ),
            "code": {
                "python": (
                    "def max_path_sum(root):\n"
                    "    best = [float('-inf')]\n"
                    "    def gain(n):\n"
                    "        if n is None:\n"
                    "            return 0\n"
                    "        l = max(0, gain(n.left))\n"
                    "        r = max(0, gain(n.right))\n"
                    "        bend = n.val + l + r\n"
                    "        if bend > best[0]:\n"
                    "            best[0] = bend\n"
                    "        return n.val + max(l, r)\n"
                    "    gain(root)\n"
                    "    return best[0]"
                ),
                "javascript": (
                    "function maxPathSum(root) {\n"
                    "    let best = -Infinity;\n"
                    "    const gain = (n) => {\n"
                    "        if (n === null) return 0;\n"
                    "        const l = Math.max(0, gain(n.left));\n"
                    "        const r = Math.max(0, gain(n.right));\n"
                    "        const bend = n.val + l + r;\n"
                    "        if (bend > best) best = bend;\n"
                    "        return n.val + Math.max(l, r);\n"
                    "    };\n"
                    "    gain(root);\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "class Solution {\n"
                    "    private int best = Integer.MIN_VALUE;\n"
                    "    public int maxPathSum(TreeNode root) {\n"
                    "        gain(root);\n"
                    "        return best;\n"
                    "    }\n"
                    "    private int gain(TreeNode n) {\n"
                    "        if (n == null) return 0;\n"
                    "        int l = Math.max(0, gain(n.left));\n"
                    "        int r = Math.max(0, gain(n.right));\n"
                    "        int bend = n.val + l + r;\n"
                    "        if (bend > best) best = bend;\n"
                    "        return n.val + Math.max(l, r);\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force — Enumerate Every Path",
            "time_complexity": "O(n^2) average, O(n^3) worst-case",
            "space_complexity": "O(h)",
            "description": (
                "For each node, treat it as the **bend point** of the path and explore every "
                "downward path into the left subtree and every downward path into the right "
                "subtree, summing all combinations. Recompute the per-node 'best downward path' "
                "at each visited node. Correct but redundant — the same subtree work happens "
                "from every ancestor. Useful as a contrast to motivate the one-pass optimal "
                "version: collapsing 'find best downward path' and 'update bent-path max' into a "
                "single post-order recursion drops the cost to O(n)."
            ),
            "code": {
                "python": (
                    "def max_path_sum(root):\n"
                    "    best = [float('-inf')]\n"
                    "    def best_down(n):\n"
                    "        if n is None:\n"
                    "            return 0\n"
                    "        l = max(0, best_down(n.left))\n"
                    "        r = max(0, best_down(n.right))\n"
                    "        return n.val + max(l, r)\n"
                    "    def visit(n):\n"
                    "        if n is None:\n"
                    "            return\n"
                    "        l = max(0, best_down(n.left))\n"
                    "        r = max(0, best_down(n.right))\n"
                    "        bend = n.val + l + r\n"
                    "        if bend > best[0]:\n"
                    "            best[0] = bend\n"
                    "        visit(n.left)\n"
                    "        visit(n.right)\n"
                    "    visit(root)\n"
                    "    return best[0]"
                ),
                "javascript": (
                    "function maxPathSum(root) {\n"
                    "    let best = -Infinity;\n"
                    "    const bestDown = (n) => {\n"
                    "        if (n === null) return 0;\n"
                    "        const l = Math.max(0, bestDown(n.left));\n"
                    "        const r = Math.max(0, bestDown(n.right));\n"
                    "        return n.val + Math.max(l, r);\n"
                    "    };\n"
                    "    const visit = (n) => {\n"
                    "        if (n === null) return;\n"
                    "        const l = Math.max(0, bestDown(n.left));\n"
                    "        const r = Math.max(0, bestDown(n.right));\n"
                    "        const bend = n.val + l + r;\n"
                    "        if (bend > best) best = bend;\n"
                    "        visit(n.left);\n"
                    "        visit(n.right);\n"
                    "    };\n"
                    "    visit(root);\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "class Solution {\n"
                    "    private int best = Integer.MIN_VALUE;\n"
                    "    public int maxPathSum(TreeNode root) {\n"
                    "        visit(root);\n"
                    "        return best;\n"
                    "    }\n"
                    "    private int bestDown(TreeNode n) {\n"
                    "        if (n == null) return 0;\n"
                    "        int l = Math.max(0, bestDown(n.left));\n"
                    "        int r = Math.max(0, bestDown(n.right));\n"
                    "        return n.val + Math.max(l, r);\n"
                    "    }\n"
                    "    private void visit(TreeNode n) {\n"
                    "        if (n == null) return;\n"
                    "        int l = Math.max(0, bestDown(n.left));\n"
                    "        int r = Math.max(0, bestDown(n.right));\n"
                    "        int bend = n.val + l + r;\n"
                    "        if (bend > best) best = bend;\n"
                    "        visit(n.left);\n"
                    "        visit(n.right);\n"
                    "    }\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: a path is any simple sequence of edge-connected nodes (it can start and end "
        "anywhere); we want the maximum sum of node values along such a path.",
        "2. Key observation: every path has a unique highest node — the **bend** — where it "
        "(optionally) goes down into the left subtree and (optionally) into the right subtree. So "
        "iterate over all candidate bend nodes and take the best.",
        "3. At a bend node `n`, the best path bending there is `n.val + max(0, leftGain) + "
        "max(0, rightGain)` where `gain(x)` is the best path that starts at `x` and goes downward "
        "into one subtree only.",
        "4. Negative branches are always discardable — `max(0, gain)` says 'don't extend into this "
        "side if it costs you'. This is the only difference from the diameter recurrence.",
        "5. The recursion returns `n.val + max(0, max(leftGain, rightGain))` upward — a path "
        "extending through an ancestor can use only **one** of `n`'s sides, so we hand back the "
        "larger one (or just `n.val` if both are negative).",
        "6. Initialise the global `best` to `-infinity`. The path must contain at least one node, so "
        "an all-negative tree returns the largest single value, not zero.",
        "7. Complexity: every node is visited once and does O(1) work → `O(n)` time, `O(h)` space "
        "for the recursion stack. For 30000 skewed nodes mention iterative post-order with an "
        "explicit stack as a recursion-depth safety follow-up.",
    ],
    "tips": [
        "Two distinct quantities — keep them separate. `gain(n)` = best one-sided downward path "
        "from `n` (returned upward). `bend(n)` = best path bending at `n` (compared against the "
        "global `best`). Conflating the two is the most common mistake.",
        "`max(0, leftGain)` and `max(0, rightGain)` — the clamping is what makes the algorithm "
        "correct for negative values. If you forget it, a strongly-positive subtree may be dragged "
        "down by a negative neighbour.",
        "Init `best = -infinity`, NOT `0`. With nodes constrained to `[-1000, 1000]`, an "
        "all-negative input means the answer is negative and a `0` initial value silently lies.",
        "Don't return the global `best` from the recursive helper — return the gain. The global is "
        "updated as a side effect. Mixing them up produces correct-looking code that's wrong.",
        "Common follow-up: 'now also return the path itself, not just the sum' — track parent "
        "pointers (or parallel `best_node` plus reconstruction) at the moment you update `best`.",
        "Same recursion shape as Diameter of Binary Tree (LC 543), House Robber III (LC 337), and "
        "Longest Univalue Path (LC 687). All four are 'one DFS, return one thing, update a global'. "
        "If you've internalised the pattern, mention it explicitly in the interview.",
    ],
    "companies": ["Facebook", "Amazon", "Google", "Microsoft", "Apple", "Bloomberg", "Uber"],
    "topics": ["Tree", "Depth-First Search", "Binary Tree", "Recursion", "Dynamic Programming"],
    "time_complexity": "O(n)",
    "space_complexity": "O(h)",
    "entry": {
        "kind": "tree",
        "name": "max_path_sum",
        "params": [{"name": "root", "type": "node"}],
    },
}

def REFERENCE(root):
    """Return the maximum path sum over any non-empty path in the tree."""
    node = inflate_tree(root)
    best = [float("-inf")]

    def gain(n):
        if n is None:
            return 0
        l = max(0, gain(n.left))
        r = max(0, gain(n.right))
        bend = n.val + l + r
        if bend > best[0]:
            best[0] = bend
        return n.val + max(l, r)

    gain(node)
    return best[0]

register(PAYLOAD, REFERENCE)
