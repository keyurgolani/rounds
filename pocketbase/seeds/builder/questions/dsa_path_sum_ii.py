"""Path Sum II — Medium. Trees / DFS / Backtracking.

Return all root-to-leaf paths whose values sum to a target. Standard
DFS + backtracking — append on entry, pop on exit, capture a copy on
each leaf hit."""
from builder.registry import register
from builder.registry import unordered_deep


PAYLOAD = {
    "title": "Binary Tree Path Sum II",
    "difficulty": "Medium",
    "description": (
        "Given the root of a binary tree and an integer `target_sum`, return all root-to-leaf paths where "
        "the sum of node values equals `target_sum`. Each path is returned as the list of values along it.\n\n"
        "Trees are encoded as level-order lists with `null` for missing children.\n\n"
        "**Example:**\n"
        "- Input: `[5, 4, 8, 11, null, 13, 4, 7, 2, null, null, 5, 1]`, `target_sum = 22`\n"
        "- Output: `[[5, 4, 11, 2], [5, 8, 4, 5]]`"
    ),
    "hints": [
        "DFS with backtracking. Append on entry, recurse, pop on exit.",
        "Trigger 'capture path' when you reach a leaf AND the running sum equals the target.",
        "A leaf is `node.left is None AND node.right is None` — not just `node is None`.",
        "Negative values are allowed; don't prune branches based on partial sum unless explicitly told values are non-negative.",
        "Edge cases: empty tree, single node (path is [root] iff root.val == target), no matching paths, all values zero with target zero.",
    ],
    "constraints": [
        "0 <= node count <= 5000",
        "Node values: -1000 to 1000",
        "Target: -10⁵ to 10⁵",
    ],
    "starter_code": {
        "python": "def path_sum(level_order, target_sum):\n    # Your code here\n    pass",
        "javascript": "function pathSum(levelOrder, targetSum) {\n    // Your code here\n}",
        "java": "public List<List<Integer>> pathSum(List<Integer> levelOrder, int targetSum) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(path_sum([5,4,8,11,None,13,4,7,2,None,None,5,1], 22))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"level_order": [5, 4, 8, 11, None, 13, 4, 7, 2, None, None, 5, 1],
                    "target_sum": 22},
         "expected": unordered_deep([[5, 4, 11, 2], [5, 8, 4, 5]]),
         "description": "Standard tree, two matching paths", "tags": ["basic"]},
        {"input": {"level_order": [], "target_sum": 0}, "expected": [],
         "description": "Empty tree", "tags": ["edge"]},
        {"input": {"level_order": [1, 2, 3], "target_sum": 5},
         "expected": unordered_deep([[1, 2, 2]]) if False else [[1, 4]] if False else [],
         "description": "Sentinel — overridden below", "tags": ["edge"]},
        {"input": {"level_order": [5], "target_sum": 5},
         "expected": [[5]],
         "description": "Single-node tree, root value matches target", "tags": ["edge"]},
        {"input": {"level_order": [5], "target_sum": 10}, "expected": [],
         "description": "Single-node, no match", "tags": ["edge"]},
        {"input": {"level_order": [-2, None, -3], "target_sum": -5},
         "expected": [[-2, -3]],
         "description": "Negative values", "tags": ["tricky"]},
        {"input": {"level_order": [0, 0, 0], "target_sum": 0},
         "expected": unordered_deep([[0, 0], [0, 0]]),
         "description": "Two paths, both sum to 0", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "DFS with Backtracking (Optimal)",
            "time_complexity": "O(n²) worst case (deep tree, every leaf hits)",
            "space_complexity": "O(h) for recursion + O(n²) worst-case output",
            "description": (
                "Recurse into each child, tracking the current path and remaining target. On reaching a "
                "leaf, if remaining is exactly the leaf's value, snapshot the path. Pop the leaf on the way "
                "out so the parent can recurse into siblings with a clean path."
            ),
            "code": {
                "python": (
                    "def path_sum(level_order, target_sum):\n"
                    "    root = _from_level(level_order)\n"
                    "    out = []\n"
                    "    if root is None:\n"
                    "        return out\n"
                    "    cur = []\n"
                    "    def go(n, remaining):\n"
                    "        if n is None:\n"
                    "            return\n"
                    "        cur.append(n.val)\n"
                    "        remaining -= n.val\n"
                    "        if n.left is None and n.right is None and remaining == 0:\n"
                    "            out.append(list(cur))\n"
                    "        else:\n"
                    "            go(n.left, remaining)\n"
                    "            go(n.right, remaining)\n"
                    "        cur.pop()\n"
                    "    go(root, target_sum)\n"
                    "    return out"
                ),
                "javascript": (
                    "function pathSum(levelOrder, targetSum) {\n"
                    "    const root = fromLevel(levelOrder);\n"
                    "    const out = [];\n"
                    "    if (!root) return out;\n"
                    "    const cur = [];\n"
                    "    const go = (n, rem) => {\n"
                    "        if (!n) return;\n"
                    "        cur.push(n.val); rem -= n.val;\n"
                    "        if (!n.left && !n.right && rem === 0) out.push([...cur]);\n"
                    "        else { go(n.left, rem); go(n.right, rem); }\n"
                    "        cur.pop();\n"
                    "    };\n"
                    "    go(root, targetSum);\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. DFS the tree, threading `remaining = target_sum - sum_so_far` through the recursion.",
        "2. Append on entry, pop on exit. Snapshot the path with `list(cur)` (not `cur` directly) when capturing.",
        "3. Leaf check is BOTH children null. A node with one child is internal, not a leaf.",
        "4. Allow negative values — partial sums can go up and down; don't prune unless told values are non-negative.",
        "5. Watch for the 'no path' case at root (root.val != target with no children) — should return [].",
        "6. Edge cases: empty tree, single-node match, single-node mismatch, paths with negatives, zero-sum paths in zero trees.",
    ],
    "tips": [
        "Not snapshotting the path — using `out.append(cur)` instead of `out.append(list(cur))` — gives you a list of references all pointing to the same final empty array. Common bug.",
        "If asked for 'any one path' (not all), short-circuit on first match.",
        "Common follow-up: 'count paths summing to k' (LeetCode 437) — paths can start anywhere, not just at root. Switch to a prefix-sum hash map keyed on running totals.",
        "Common follow-up: 'longest path summing to k.' Modify the comparison; track maximum length.",
        "DFS recursion depth: for skewed trees of 10⁴ nodes, you may need to bump Python's recursion limit or convert to iterative.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg", "Facebook"],
    "topics": ["Tree", "DFS", "Backtracking"],
    "time_complexity": "O(n²)",
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


def REFERENCE(level_order, target_sum):
    root = _from_level(level_order)
    out = []
    if root is None:
        return out
    cur = []

    def go(n, remaining):
        if n is None:
            return
        cur.append(n.val)
        remaining -= n.val
        if n.left is None and n.right is None and remaining == 0:
            out.append(list(cur))
        else:
            go(n.left, remaining)
            go(n.right, remaining)
        cur.pop()

    go(root, target_sum)
    return out


register(PAYLOAD, REFERENCE)
