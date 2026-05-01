"""Max Root-to-Leaf Path Sum — Easy/Medium. Trees / DFS.

DFS the tree, tracking the path with the highest sum. Return the
path itself, not just the sum — many candidates miss this distinction."""
from builder.registry import register


PAYLOAD = {
    "title": "Maximum Root-to-Leaf Path Sum",
    "difficulty": "Medium",
    "description": (
        "Given the root of a binary tree where every node has an integer value, find the **complete "
        "root-to-leaf path** with the highest sum. Return the values along the path in order from root to "
        "leaf.\n\n"
        "Trees are encoded as level-order lists with `null` for missing children.\n\n"
        "**Example:**\n"
        "```\n"
        "Tree:    3\n"
        "        / \\\n"
        "       8   4\n"
        "      / \\   \\\n"
        "     2   1   6\n"
        "```\n"
        "- Input: `[3, 8, 4, 2, 1, null, 6]`\n"
        "- Output: `[3, 4, 6]` (sum 13)\n\n"
        "If the tree is empty, return `[]`. If multiple paths tie, returning any is acceptable."
    ),
    "hints": [
        "DFS the tree. At each leaf, you have a candidate path; remember the best so far.",
        "Pass the current path down recursively — append on entry, pop on exit (backtracking).",
        "Or: at each node, return `(best_subtree_sum, best_subtree_path)` and pick whichever child returned the larger sum.",
        "Negative values: don't assume sums are non-negative. The 'best path' can still be negative — pick the least-negative.",
        "Edge cases: empty tree, single node (root is the path), all-negative values, multiple equally-best paths.",
    ],
    "constraints": [
        "0 <= node count <= 10⁴",
        "Node values: -10⁴ to 10⁴",
    ],
    "starter_code": {
        "python": "def max_path(level_order):\n    # Your code here\n    pass",
        "javascript": "function maxPath(levelOrder) {\n    // Your code here\n}",
        "java": "public List<Integer> maxPath(List<Integer> levelOrder) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(max_path([3, 8, 4, 2, 1, None, 6]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"level_order": [3, 8, 4, 2, 1, None, 6]},
         "expected": {"$match": "any_of", "values": [[3, 8, 2], [3, 4, 6]]},
         "description": "Two paths tie at sum 13 — either is acceptable", "tags": ["basic"]},
        {"input": {"level_order": []}, "expected": [],
         "description": "Empty tree", "tags": ["edge"]},
        {"input": {"level_order": [42]}, "expected": [42],
         "description": "Single root node — that's the path", "tags": ["edge"]},
        {"input": {"level_order": [-1, -2, -3]}, "expected": [-1, -2],
         "description": "All-negative values; pick the path with the least-negative sum",
         "tags": ["tricky"]},
        {"input": {"level_order": [1, 2, 3]},
         "expected": {"$match": "any_of", "values": [[1, 2], [1, 3]]},
         "description": "Two leaves both reachable; tie", "tags": ["tricky"]},
        {"input": {"level_order": [10, None, 5, None, 3]},
         "expected": [10, 5, 3],
         "description": "Right-skewed tree", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "DFS with Backtracking (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h) recursion + O(h) path",
            "description": (
                "DFS in pre-order. Maintain a current path list and a current sum. On each leaf, compare "
                "against the running best. Append the value on entry, pop on exit (backtracking) so the "
                "list is reused. Single linear pass."
            ),
            "code": {
                "python": (
                    "def max_path(level_order):\n"
                    "    root = _from_level(level_order)\n"
                    "    if root is None:\n"
                    "        return []\n"
                    "    best = {'sum': float('-inf'), 'path': []}\n"
                    "    cur = []\n"
                    "    def go(n, s):\n"
                    "        if n is None:\n"
                    "            return\n"
                    "        cur.append(n.val)\n"
                    "        s += n.val\n"
                    "        if n.left is None and n.right is None:\n"
                    "            if s > best['sum']:\n"
                    "                best['sum'] = s\n"
                    "                best['path'] = list(cur)\n"
                    "        else:\n"
                    "            go(n.left, s)\n"
                    "            go(n.right, s)\n"
                    "        cur.pop()\n"
                    "    go(root, 0)\n"
                    "    return best['path']"
                ),
                "javascript": (
                    "function maxPath(levelOrder) {\n"
                    "    const root = fromLevel(levelOrder);\n"
                    "    if (!root) return [];\n"
                    "    let best = { sum: -Infinity, path: [] };\n"
                    "    const cur = [];\n"
                    "    const go = (n, s) => {\n"
                    "        if (!n) return;\n"
                    "        cur.push(n.val);\n"
                    "        s += n.val;\n"
                    "        if (!n.left && !n.right) {\n"
                    "            if (s > best.sum) best = { sum: s, path: [...cur] };\n"
                    "        } else { go(n.left, s); go(n.right, s); }\n"
                    "        cur.pop();\n"
                    "    };\n"
                    "    go(root, 0);\n"
                    "    return best.path;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Returning Tuples Up the Recursion",
            "time_complexity": "O(n) (with O(h) path copies, can be O(n·h) on skewed trees)",
            "space_complexity": "O(h)",
            "description": (
                "Each recursive call returns `(best_subtree_sum, best_subtree_path)`. The parent picks the "
                "larger child and prepends itself. Cleaner functional style; risk is that copying the path "
                "on every step is O(h) extra work per merge."
            ),
            "code": {
                "python": (
                    "def max_path(level_order):\n"
                    "    root = _from_level(level_order)\n"
                    "    if root is None:\n"
                    "        return []\n"
                    "    def go(n):\n"
                    "        if n is None:\n"
                    "            return float('-inf'), []\n"
                    "        if n.left is None and n.right is None:\n"
                    "            return n.val, [n.val]\n"
                    "        ls, lp = go(n.left)\n"
                    "        rs, rp = go(n.right)\n"
                    "        if ls >= rs:\n"
                    "            return ls + n.val, [n.val] + lp\n"
                    "        return rs + n.val, [n.val] + rp\n"
                    "    return go(root)[1]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise: DFS, track running sum and path, snapshot whenever you reach a leaf.",
        "2. Decide on the recursion shape: backtracking (one shared mutable list) or tuple-returning (clean but copies).",
        "3. Don't assume non-negative values — `max` against `float('-inf')` to handle all-negative trees.",
        "4. The leaf condition is `n.left is None and n.right is None`; checking `n is None` only flags missing children, not leaves.",
        "5. Multiple ties: the problem usually accepts any; clarify with the interviewer.",
        "6. Edge cases: empty tree, single node, all-negative, skewed trees, ties.",
    ],
    "tips": [
        "Don't append in-recursion when both children are non-null and you forgot to backtrack — silent off-by-one bug.",
        "Iterative version: explicit stack of `(node, current_path)`. Avoids recursion depth limits but copies more.",
        "Common follow-up: 'max path between any two nodes' (LeetCode 124). Different problem — track per-node 'best gain extending to me' and update a global maximum.",
        "Common follow-up: 'count paths summing to k' (LeetCode 437). Prefix-sum hash map per traversal.",
        "Edge: a leaf is `left is None AND right is None`. A node with only a left child is NOT a leaf — make sure your traversal still recurses through it.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Bloomberg"],
    "topics": ["Tree", "DFS", "Backtracking"],
    "time_complexity": "O(n)",
    "space_complexity": "O(h)",
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


def REFERENCE(level_order):
    root = _from_level(level_order)
    if root is None:
        return []
    best = {"sum": float("-inf"), "path": []}
    cur = []

    def go(n, s):
        if n is None:
            return
        cur.append(n.val)
        s += n.val
        if n.left is None and n.right is None:
            if s > best["sum"]:
                best["sum"] = s
                best["path"] = list(cur)
        else:
            go(n.left, s)
            go(n.right, s)
        cur.pop()

    go(root, 0)
    return best["path"]


register(PAYLOAD, REFERENCE)
