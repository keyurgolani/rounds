"""Binary Tree Level Order Traversal — Medium. Tree / BFS / DFS.

LeetCode 102. The canonical BFS-with-explicit-level-boundary problem.
The trick is snapshotting `len(queue)` at the start of each iteration —
that count *is* the size of the current level, and you drain exactly
that many nodes before incrementing the depth counter.

A neat alternative (and a good follow-up to talk through) is recursive
DFS that carries the current depth and appends into `result[depth]` —
the recursion implicitly handles the level grouping with no queue at
all.

The user-facing function receives a `TreeNode` root and returns a
`list[list[int]]`.
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


PAYLOAD = {
    "title": "Binary Tree Level Order Traversal",
    "difficulty": "Medium",
    "description": (
        "Given the `root` of a binary tree, return its **level order traversal** — that is, the values "
        "of the nodes grouped by depth, with each level's values listed left-to-right.\n\n"
        "The output is a list of lists; each inner list is one level.\n\n"
        "**Example 1:**\n"
        "```\n"
        "Tree:    3\n"
        "        / \\\n"
        "       9  20\n"
        "          / \\\n"
        "         15  7\n"
        "```\n"
        "- Input: `root` points to the tree shown above\n"
        "- Output: `[[3], [9, 20], [15, 7]]`\n\n"
        "**Example 2:**\n"
        "- Input: `root` points to a single node with value `1`\n"
        "- Output: `[[1]]`\n\n"
        "An empty tree returns `[]` (no levels at all)."
    ),
    "hints": [
        "BFS is the natural fit. Use a queue and process the tree level-by-level — but you need a way to "
        "tell *where one level ends and the next begins*.",
        "The canonical trick: at the start of each outer loop iteration, snapshot `size = len(queue)`. "
        "Drain exactly that many nodes (they form one level), enqueue their children, then loop. The "
        "snapshot freezes the level boundary before children get added.",
        "Alternative (no queue): recursive DFS carrying a `depth` parameter. Lazily extend the result list "
        "with a new sublist when `depth == len(result)`, then `result[depth].append(node.val)`. The DFS "
        "order ensures left children are visited before right at every depth.",
        "Edge case: empty tree → return `[]`, not `[[]]`. Don't enqueue a `None` root.",
        "Don't try to do this with a single flat queue and a 'sentinel' — it works but it's needlessly "
        "fiddly. The size-snapshot pattern is shorter and harder to get wrong.",
    ],
    "constraints": [
        "The number of nodes in the tree is in the range `[0, 2000]`.",
        "-1000 <= Node.val <= 1000",
    ],
    "starter_code": {
        "python": (
            "# Definition for a binary tree node.\n"
            "# class TreeNode:\n"
            "#     def __init__(self, val=0, left=None, right=None):\n"
            "#         self.val = val\n"
            "#         self.left = left\n"
            "#         self.right = right\n"
            "# Return a list of lists; each inner list is one level, left-to-right.\n"
            "def level_order(root):\n"
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
            "// Return an array of arrays; each inner array is one level, left-to-right.\n"
            "function levelOrder(root) {\n"
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
            "// Return List<List<Integer>>; each inner list is one level.\n"
            "public List<List<Integer>> levelOrder(TreeNode root) {\n"
            "    // Your code here\n"
            "    return new ArrayList<>();\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    root = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))\n"
            "    print(level_order(root))\n"
            "    print(level_order(None))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const root = new TreeNode(3, new TreeNode(9), new TreeNode(20, new TreeNode(15), new TreeNode(7)));\n"
            "console.log(JSON.stringify(levelOrder(root)));\n"
            "console.log(JSON.stringify(levelOrder(null)));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        TreeNode root = new TreeNode(3, new TreeNode(9), new TreeNode(20, new TreeNode(15), new TreeNode(7)));\n"
            "        System.out.println(s.levelOrder(root));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"root": []}, "expected": [],
         "description": "Empty tree → empty list of levels", "tags": ["edge"]},
        {"input": {"root": [1]}, "expected": [[1]],
         "description": "Single node → one level with one value", "tags": ["edge"]},
        {"input": {"root": [3, 9, 20, None, None, 15, 7]}, "expected": [[3], [9, 20], [15, 7]],
         "description": "Classic LeetCode example — three levels, missing children at level 2",
         "tags": ["basic"]},
        {"input": {"root": [1, 2, None, 3, None, 4, None, 5]},
         "expected": [[1], [2], [3], [4], [5]],
         "description": "Left-only chain — each level holds exactly one node", "tags": ["edge"]},
        {"input": {"root": [1, None, 2, None, 3, None, 4, None, 5]},
         "expected": [[1], [2], [3], [4], [5]],
         "description": "Right-only chain — each level holds exactly one node", "tags": ["edge"]},
        {"input": {"root": [1, 2, 3, 4, 5, 6, 7]},
         "expected": [[1], [2, 3], [4, 5, 6, 7]],
         "description": "Perfect binary tree of 7 nodes — three full levels", "tags": ["basic"]},
        {"input": {"root": [1, 2, 3, 4, None, None, 5, 6, None, None, 7]},
         "expected": [[1], [2, 3], [4, 5], [6, 7]],
         "description": "Tree with scattered nulls — left/right children skip around at each level",
         "tags": ["tricky"]},
        {"input": {"root": [1, 2, 3, 4, 5, None, 6, None, None, 7]},
         "expected": [[1], [2, 3], [4, 5, 6], [7]],
         "description": "Asymmetric tree — deepest leaf reached via 1→2→5→7 only",
         "tags": ["tricky"]},
        {"input": {"root": [5, 4, 8, 11, None, 13, 4, 7, 2, None, None, None, 1]},
         "expected": [[5], [4, 8], [11, 13, 4], [7, 2, 1]],
         "description": "Mixed-shape tree with interior nulls — order at each level must be left-to-right",
         "tags": ["tricky"]},
        {"input": {"root": [0, -1, 1, -2, None, None, 2]},
         "expected": [[0], [-1, 1], [-2, 2]],
         "description": "Negative and zero values are preserved exactly", "tags": ["edge"]},
        {"input": {"root": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150]},
         "expected": [[10], [20, 30], [40, 50, 60, 70], [80, 90, 100, 110, 120, 130, 140, 150]],
         "description": "Perfect 4-level tree of 15 nodes — wide bottom level",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "BFS with Queue and Length Snapshot (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(w) — width of the widest level (up to n/2 for a complete tree)",
            "description": (
                "Standard BFS: enqueue the root, then on each outer iteration snapshot `size = len(queue)`. "
                "Pop exactly `size` nodes — those are the current level — collecting their values into a "
                "fresh sublist while enqueueing their non-null children for the next level. Append the "
                "sublist to the result. Visits every node once."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "def level_order(root):\n"
                    "    if root is None:\n"
                    "        return []\n"
                    "    result = []\n"
                    "    q = deque([root])\n"
                    "    while q:\n"
                    "        size = len(q)\n"
                    "        level = []\n"
                    "        for _ in range(size):\n"
                    "            n = q.popleft()\n"
                    "            level.append(n.val)\n"
                    "            if n.left:  q.append(n.left)\n"
                    "            if n.right: q.append(n.right)\n"
                    "        result.append(level)\n"
                    "    return result"
                ),
                "javascript": (
                    "function levelOrder(root) {\n"
                    "    if (!root) return [];\n"
                    "    const result = [];\n"
                    "    let q = [root];\n"
                    "    while (q.length) {\n"
                    "        const next = [];\n"
                    "        const level = [];\n"
                    "        for (const n of q) {\n"
                    "            level.push(n.val);\n"
                    "            if (n.left)  next.push(n.left);\n"
                    "            if (n.right) next.push(n.right);\n"
                    "        }\n"
                    "        result.push(level);\n"
                    "        q = next;\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public List<List<Integer>> levelOrder(TreeNode root) {\n"
                    "    List<List<Integer>> result = new ArrayList<>();\n"
                    "    if (root == null) return result;\n"
                    "    Deque<TreeNode> q = new ArrayDeque<>();\n"
                    "    q.offer(root);\n"
                    "    while (!q.isEmpty()) {\n"
                    "        int size = q.size();\n"
                    "        List<Integer> level = new ArrayList<>(size);\n"
                    "        for (int i = 0; i < size; i++) {\n"
                    "            TreeNode n = q.poll();\n"
                    "            level.add(n.val);\n"
                    "            if (n.left  != null) q.offer(n.left);\n"
                    "            if (n.right != null) q.offer(n.right);\n"
                    "        }\n"
                    "        result.add(level);\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Recursive DFS with Depth Index",
            "time_complexity": "O(n)",
            "space_complexity": "O(h) recursion stack — O(log n) balanced, O(n) skewed",
            "description": (
                "Walk the tree DFS pre-order, carrying the current `depth`. On the way down, if "
                "`depth == len(result)` we've reached a new level — append a fresh sublist. Then "
                "append the node's value to `result[depth]` and recurse into left and right (in that "
                "order, so values land left-to-right). No queue needed; recursion depth = tree height."
            ),
            "code": {
                "python": (
                    "def level_order(root):\n"
                    "    result = []\n"
                    "    def go(n, depth):\n"
                    "        if n is None:\n"
                    "            return\n"
                    "        if depth == len(result):\n"
                    "            result.append([])\n"
                    "        result[depth].append(n.val)\n"
                    "        go(n.left, depth + 1)\n"
                    "        go(n.right, depth + 1)\n"
                    "    go(root, 0)\n"
                    "    return result"
                ),
                "javascript": (
                    "function levelOrder(root) {\n"
                    "    const result = [];\n"
                    "    const go = (n, depth) => {\n"
                    "        if (n === null) return;\n"
                    "        if (depth === result.length) result.push([]);\n"
                    "        result[depth].push(n.val);\n"
                    "        go(n.left,  depth + 1);\n"
                    "        go(n.right, depth + 1);\n"
                    "    };\n"
                    "    go(root, 0);\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public List<List<Integer>> levelOrder(TreeNode root) {\n"
                    "    List<List<Integer>> result = new ArrayList<>();\n"
                    "    dfs(root, 0, result);\n"
                    "    return result;\n"
                    "}\n"
                    "private void dfs(TreeNode n, int depth, List<List<Integer>> result) {\n"
                    "    if (n == null) return;\n"
                    "    if (depth == result.size()) result.add(new ArrayList<>());\n"
                    "    result.get(depth).add(n.val);\n"
                    "    dfs(n.left,  depth + 1, result);\n"
                    "    dfs(n.right, depth + 1, result);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: for each depth d, list the values of nodes at that depth, ordered left-to-right. "
        "Output is a list of these per-level lists.",
        "2. BFS is the obvious tool — it's already a level-by-level walk. The only wrinkle is knowing "
        "where one level ends and the next begins, since a single shared queue mixes generations.",
        "3. Solve the boundary problem with a length snapshot: at the top of each outer iteration, "
        "`size = len(queue)` freezes the count of *current-level* nodes before we start enqueueing "
        "children. Drain exactly that many, then loop.",
        "4. Alternative without a queue: recursive DFS with a `depth` argument. Each call appends into "
        "`result[depth]`, lazily creating that sublist on first visit. DFS pre-order with left-before-"
        "right ensures the per-level ordering is correct.",
        "5. Edge cases: empty tree → `[]` (NOT `[[]]`); single node → `[[v]]`; deeply skewed tree → "
        "many levels of one node each. The DFS version blows the recursion stack on a 2000-deep skew, "
        "so prefer BFS when the bound is unknown.",
        "6. Complexity: every node is touched once → O(n) time. BFS space is O(w) (max level width); "
        "DFS space is O(h) (recursion depth). Both can be Θ(n) in the worst case.",
    ],
    "tips": [
        "The length snapshot — `size = len(q)` at the top of the outer loop — is the move. Without it, "
        "newly-enqueued children get folded into the current level's count and the boundaries collapse.",
        "Don't enqueue None. The shape of the tree is encoded in which children exist, not in null "
        "placeholders inside the BFS queue.",
        "Empty tree returns `[]`, not `[[]]`. Get this right before you write anything else — it's a "
        "common 'one wrong test case' bug.",
        "If the interviewer asks for the recursive variant, the depth-indexed-result trick is elegant "
        "and short. Mention it even if you go BFS first — it shows you see both shapes of the problem.",
        "Common follow-ups: zigzag level order (LC 103) — alternate level direction; bottom-up level "
        "order (LC 107) — reverse the result; right-side view (LC 199) — last value of each level. All "
        "are tiny modifications of the same BFS skeleton.",
        "On very skewed trees with up to 2000 nodes, recursive DFS may approach Python's default 1000-"
        "frame limit. The BFS version is safer; mention this if asked about robustness.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Meta", "Apple", "Bloomberg", "LinkedIn"],
    "topics": ["Tree", "Breadth-First Search", "Binary Tree", "Queue"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
    "entry": {
        "kind": "tree",
        "name": "level_order",
        "params": [
            {"name": "root", "type": "node"},
        ],
        "input_shape": "tree_level_order",
    },
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
    """Take a level-order list, return list-of-lists level-order traversal."""
    node = _from_level(root)
    if node is None:
        return []
    result = []
    q = deque([node])
    while q:
        size = len(q)
        level = []
        for _ in range(size):
            n = q.popleft()
            level.append(n.val)
            if n.left:
                q.append(n.left)
            if n.right:
                q.append(n.right)
        result.append(level)
    return result


register(PAYLOAD, REFERENCE)
