"""Maximum Depth of Binary Tree — Easy. Trees / DFS / BFS.

The canonical 'first tree question'. Almost everyone reaches for the
3-line recursion. The real interview value is being able to also
sketch the iterative BFS level-count and explain when each is
preferable (deep skewed trees blow the recursion stack — switch to
BFS or an explicit stack).
"""
from builder.registry import register


PAYLOAD = {
    "title": "Maximum Depth of Binary Tree",
    "difficulty": "Easy",
    "description": (
        "Given the `root` of a binary tree, return its **maximum depth** — the number of nodes on the "
        "longest path from the root down to the farthest leaf.\n\n"
        "Trees are encoded as level-order lists with `null` for missing children (LeetCode style).\n\n"
        "**Example 1:**\n"
        "```\n"
        "Tree:    3\n"
        "        / \\\n"
        "       9  20\n"
        "          / \\\n"
        "         15  7\n"
        "```\n"
        "- Input: `root = [3, 9, 20, null, null, 15, 7]`\n"
        "- Output: `3`\n\n"
        "**Example 2:**\n"
        "- Input: `root = [1, null, 2]`\n"
        "- Output: `2`\n\n"
        "Empty tree returns `0`."
    ),
    "hints": [
        "Recursive definition: depth of an empty tree is 0; otherwise `1 + max(depth(left), depth(right))`. "
        "Three lines once you see it.",
        "Iterative BFS: walk level by level with a queue; the answer is the number of levels you process.",
        "Iterative DFS with an explicit stack of `(node, depth)` pairs — avoids recursion-depth limits on "
        "skewed trees with up to 10⁴ nodes.",
        "Don't confuse 'depth' (node count on the path) with 'height in edges' — they differ by 1. The "
        "problem asks for the node count.",
        "A leaf is a node where both children are `None`. The depth of a tree with only a root is 1, not 0.",
    ],
    "constraints": [
        "0 <= node count <= 10⁴",
        "-100 <= node value <= 100",
        "Tree may be highly skewed — a left- or right-only chain of 10⁴ nodes is allowed.",
    ],
    "starter_code": {
        "python": "def max_depth(root):\n    # `root` is a LeetCode-style level-order list with None for missing children.\n    # Your code here\n    pass",
        "javascript": "function maxDepth(root) {\n    // `root` is a level-order array with null for missing children.\n    // Your code here\n}",
        "java": "public int maxDepth(List<Integer> root) {\n    // `root` is a level-order list with null for missing children.\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[3, 9, 20, None, None, 15, 7], [1, None, 2], []]\n"
            "    for c in cases:\n"
            "        print(f\"max_depth({c}) = {max_depth(c)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[3, 9, 20, null, null, 15, 7], [1, null, 2], []].forEach(c =>\n"
            "    console.log(`maxDepth =`, maxDepth(c))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.maxDepth(java.util.Arrays.asList(3, 9, 20, null, null, 15, 7)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": []}, "expected": 0,
         "description": "Empty tree → depth 0", "tags": ["edge"]},
        {"input": {"root": [1]}, "expected": 1,
         "description": "Single node → depth 1 (not 0)", "tags": ["edge"]},
        {"input": {"root": [1, 2, None, 3]}, "expected": 3,
         "description": "Left-only chain of length 3", "tags": ["edge"]},
        {"input": {"root": [1, None, 2, None, 3]}, "expected": 3,
         "description": "Right-only chain of length 3", "tags": ["edge"]},
        {"input": {"root": [1, 2, 3]}, "expected": 2,
         "description": "Perfectly balanced 3-node tree", "tags": ["basic"]},
        {"input": {"root": [3, 9, 20, None, None, 15, 7]}, "expected": 3,
         "description": "Classic LeetCode example", "tags": ["basic"]},
        {"input": {"root": [1, 2, 3, 4, 5, None, 6, None, None, 7]}, "expected": 4,
         "description": "Asymmetric with scattered nulls; deepest leaf reached via 1→2→5→7",
         "tags": ["tricky"]},
        {"input": {"root": [5, 4, 8, 11, None, 13, 4, 7, 2, None, None, None, 1]}, "expected": 4,
         "description": "Mixed-shape tree with nulls inside the level-order list",
         "tags": ["tricky"]},
        {"input": {"root": list(range(1, 11))}, "expected": 4,
         "description": "Complete tree of 10 nodes → depth 4 (ceil(log2(11)))",
         "tags": ["basic"]},
        {"input": {"root": [1, 2, None, 3, None, 4, None, 5, None, 6, None, 7, None, 8, None, 9, None, 10]},
         "expected": 10,
         "description": "Left-only chain of 10 nodes — recursion-depth stress",
         "tags": ["large"]},
        {"input": {"root": [0, -1, 1, -2, None, None, 2]}, "expected": 3,
         "description": "Negative and zero values don't affect depth — only structure does",
         "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Recursive DFS (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(h) recursion stack — O(log n) balanced, O(n) skewed",
            "description": (
                "Direct translation of the recursive definition: empty tree has depth 0; otherwise "
                "1 + max of the two children's depths. Visits each node exactly once. Three lines of body."
            ),
            "code": {
                "python": (
                    "def max_depth(root):\n"
                    "    node = _from_level(root)\n"
                    "    def go(n):\n"
                    "        if n is None:\n"
                    "            return 0\n"
                    "        return 1 + max(go(n.left), go(n.right))\n"
                    "    return go(node)"
                ),
                "javascript": (
                    "function maxDepth(root) {\n"
                    "    const node = fromLevel(root);\n"
                    "    const go = (n) => n === null ? 0 : 1 + Math.max(go(n.left), go(n.right));\n"
                    "    return go(node);\n"
                    "}"
                ),
                "java": (
                    "public int maxDepth(List<Integer> root) {\n"
                    "    TreeNode node = fromLevel(root);\n"
                    "    return depth(node);\n"
                    "}\n"
                    "private int depth(TreeNode n) {\n"
                    "    if (n == null) return 0;\n"
                    "    return 1 + Math.max(depth(n.left), depth(n.right));\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative BFS Level Count",
            "time_complexity": "O(n)",
            "space_complexity": "O(w) — width of the widest level (up to n/2 for a complete tree)",
            "description": (
                "Walk the tree level by level using a queue. For each level, drain exactly the nodes "
                "currently in the queue and enqueue their non-null children. Increment a level counter "
                "each time you complete a level. Avoids recursion entirely — safer on deep skewed trees."
            ),
            "code": {
                "python": (
                    "def max_depth(root):\n"
                    "    node = _from_level(root)\n"
                    "    if node is None:\n"
                    "        return 0\n"
                    "    from collections import deque\n"
                    "    q = deque([node])\n"
                    "    levels = 0\n"
                    "    while q:\n"
                    "        for _ in range(len(q)):\n"
                    "            n = q.popleft()\n"
                    "            if n.left:  q.append(n.left)\n"
                    "            if n.right: q.append(n.right)\n"
                    "        levels += 1\n"
                    "    return levels"
                ),
                "javascript": (
                    "function maxDepth(root) {\n"
                    "    const node = fromLevel(root);\n"
                    "    if (!node) return 0;\n"
                    "    let q = [node], levels = 0;\n"
                    "    while (q.length) {\n"
                    "        const next = [];\n"
                    "        for (const n of q) {\n"
                    "            if (n.left) next.push(n.left);\n"
                    "            if (n.right) next.push(n.right);\n"
                    "        }\n"
                    "        q = next;\n"
                    "        levels += 1;\n"
                    "    }\n"
                    "    return levels;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative DFS with Explicit Stack",
            "time_complexity": "O(n)",
            "space_complexity": "O(h)",
            "description": (
                "Push `(node, depth)` pairs onto an explicit stack. Track the maximum depth observed. "
                "Useful when recursion limits are a concern but you prefer DFS over BFS (e.g., to keep "
                "memory bounded on a wide complete tree)."
            ),
            "code": {
                "python": (
                    "def max_depth(root):\n"
                    "    node = _from_level(root)\n"
                    "    if node is None:\n"
                    "        return 0\n"
                    "    stack = [(node, 1)]\n"
                    "    best = 0\n"
                    "    while stack:\n"
                    "        n, d = stack.pop()\n"
                    "        if d > best: best = d\n"
                    "        if n.left:  stack.append((n.left,  d + 1))\n"
                    "        if n.right: stack.append((n.right, d + 1))\n"
                    "    return best"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the recurrence: depth(empty) = 0; depth(n) = 1 + max(depth(left), depth(right)).",
        "2. Write the 3-line recursion first — it's the cleanest expression of the definition.",
        "3. Note the recursion-stack risk: a chain of 10⁴ nodes would blow Python's default 1000-frame limit. "
        "Mention BFS or iterative DFS as the safe alternative.",
        "4. BFS level-count is the natural iterative version — and it generalises directly to 'level order "
        "traversal' and 'right-side view' follow-ups.",
        "5. Edge cases: empty tree → 0; single node → 1; deeply skewed → linear depth.",
        "6. Don't conflate 'depth in nodes' with 'height in edges' — clarify if the prompt is ambiguous.",
    ],
    "tips": [
        "The 3-line recursion is the standard answer. Have the BFS version ready as the first follow-up.",
        "When asked 'minimum depth' (LeetCode 111), the recursion changes: a missing child must NOT be "
        "treated as depth 0 — that would let you 'cheat' through an internal node with one child.",
        "BFS level-count generalises: average per level (LC 637), right-side view (LC 199), zigzag (LC 103).",
        "If recursion depth is a concern, mention `sys.setrecursionlimit` exists but prefer the iterative "
        "rewrite — bumping the limit is a workaround, not a fix.",
        "Don't forget: a leaf is `left is None AND right is None`. A node with only a left child is NOT a "
        "leaf and the recursion must still descend through it.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Apple", "LinkedIn", "Bloomberg"],
    "topics": ["Tree", "DFS", "BFS", "Recursion"],
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


def REFERENCE(root):
    node = _from_level(root)

    def go(n):
        if n is None:
            return 0
        return 1 + max(go(n.left), go(n.right))

    return go(node)


register(PAYLOAD, REFERENCE)
