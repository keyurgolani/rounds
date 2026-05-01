"""Graph Valid Tree — Medium. Union-Find / DFS / BFS.

A classic 'is this graph a tree?' question. The trick is recognising
the two-part definition: a tree on n nodes has *exactly* n-1 edges
AND is connected AND acyclic. With n-1 edges, connected ⇔ acyclic,
so you only need to verify one of the two — Union-Find naturally
detects cycles, DFS naturally detects connectedness. Either works;
both should be in your back pocket.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Graph Valid Tree",
    "difficulty": "Medium",
    "description": (
        "You have a graph of `n` nodes labeled from `0` to `n - 1`. You are given an integer `n` and a "
        "list of `edges` where `edges[i] = [u, v]` indicates an undirected edge between nodes `u` and `v`.\n\n"
        "Return `true` if the edges form a **valid tree**, and `false` otherwise.\n\n"
        "A valid tree is an undirected graph that is **connected** and contains **no cycles**.\n\n"
        "**Example 1:**\n"
        "- Input: `n = 5, edges = [[0,1],[0,2],[0,3],[1,4]]`\n"
        "- Output: `true`\n"
        "- Explanation: 4 edges, 5 nodes, connected, no cycle — valid tree.\n\n"
        "**Example 2:**\n"
        "- Input: `n = 5, edges = [[0,1],[1,2],[2,3],[1,3],[1,4]]`\n"
        "- Output: `false`\n"
        "- Explanation: Edge `[1,3]` closes a cycle with `[1,2]`/`[2,3]` — not a tree."
    ),
    "hints": [
        "A tree on `n` nodes has *exactly* `n - 1` edges. If `len(edges) != n - 1`, return false immediately — saves you from doing any graph work.",
        "Once `len(edges) == n - 1` holds, the graph is a tree iff it is **connected** *or*, equivalently, iff it is **acyclic**. Verify either one.",
        "Union-Find approach: union each edge's endpoints. If you ever try to union two nodes that already share a root, you've found a cycle → return false. After processing, if no cycle was found and edge count == n-1, it's a tree.",
        "DFS / BFS approach: build an adjacency list, run a traversal from node 0, track visited nodes. If you visit `n` distinct nodes without revisiting one through a non-parent edge, it's a tree.",
        "Watch the parent-edge case in DFS: in an undirected graph, the edge you came in on shows up as a 'back edge' to the parent. That's not a cycle — skip it.",
    ],
    "constraints": [
        "1 <= n <= 2000",
        "0 <= edges.length <= 5000",
        "edges[i].length == 2, 0 <= u_i, v_i < n, u_i != v_i, no duplicate edges",
    ],
    "starter_code": {
        "python": "def valid_tree(n, edges):\n    # Your code here\n    pass",
        "javascript": "function validTree(n, edges) {\n    // Your code here\n}",
        "java": "public boolean validTree(int n, int[][] edges) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        (5, [[0,1],[0,2],[0,3],[1,4]]),\n"
            "        (5, [[0,1],[1,2],[2,3],[1,3],[1,4]]),\n"
            "        (1, []),\n"
            "    ]\n"
            "    for n, edges in cases:\n"
            "        print(f\"valid_tree({n}, {edges}) = {valid_tree(n, edges)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[5, [[0,1],[0,2],[0,3],[1,4]]], [5, [[0,1],[1,2],[2,3],[1,3],[1,4]]]].forEach(([n, edges]) =>\n"
            "    console.log(`validTree =`, validTree(n, edges))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.validTree(5, new int[][]{{0,1},{0,2},{0,3},{1,4}}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"n": 5, "edges": [[0, 1], [0, 2], [0, 3], [1, 4]]}, "expected": True,
         "description": "LC example 1 — connected, n-1 edges, no cycle", "tags": ["basic"]},
        {"input": {"n": 5, "edges": [[0, 1], [1, 2], [2, 3], [1, 3], [1, 4]]}, "expected": False,
         "description": "LC example 2 — cycle on {1, 2, 3}", "tags": ["basic"]},
        {"input": {"n": 1, "edges": []}, "expected": True,
         "description": "Single node, no edges — trivially a tree", "tags": ["edge"]},
        {"input": {"n": 2, "edges": [[0, 1]]}, "expected": True,
         "description": "Two nodes with one edge — minimal tree", "tags": ["edge"]},
        {"input": {"n": 2, "edges": []}, "expected": False,
         "description": "Two nodes, no edges — disconnected", "tags": ["edge"]},
        {"input": {"n": 4, "edges": [[0, 1], [2, 3]]}, "expected": False,
         "description": "Too few edges — two disconnected components", "tags": ["tricky"]},
        {"input": {"n": 4, "edges": [[0, 1], [1, 2], [2, 3], [0, 3]]}, "expected": False,
         "description": "Too many edges — n edges form a cycle", "tags": ["tricky"]},
        {"input": {"n": 4, "edges": [[0, 1], [2, 3], [1, 2]]}, "expected": True,
         "description": "Linear chain 0-1-2-3 — valid tree", "tags": ["basic"]},
        {"input": {"n": 5, "edges": [[0, 1], [1, 2], [2, 0], [3, 4]]}, "expected": False,
         "description": "Cycle on subset {0,1,2} plus separate component — not a tree", "tags": ["tricky"]},
        {"input": {"n": 6, "edges": [[0, 1], [0, 2], [0, 3], [0, 4], [0, 5]]}, "expected": True,
         "description": "Star graph rooted at 0 — valid tree", "tags": ["basic"]},
        {"input": {"n": 3, "edges": [[0, 1], [1, 2], [0, 2]]}, "expected": False,
         "description": "Triangle — n edges, contains cycle", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Union-Find (Optimal)",
            "time_complexity": "O(E·α(n))",
            "space_complexity": "O(n)",
            "description": (
                "Edge-count short-circuit: if `len(edges) != n - 1`, return false. Otherwise, run Union-Find "
                "with path compression and union by rank. For each edge `(u, v)`, if `find(u) == find(v)` "
                "the edge would close a cycle → return false. If every edge unions two distinct components, "
                "the graph is acyclic; combined with the edge-count check, it's a tree. Inverse-Ackermann "
                "α(n) is effectively constant."
            ),
            "code": {
                "python": (
                    "def valid_tree(n, edges):\n"
                    "    if len(edges) != n - 1:\n"
                    "        return False\n"
                    "    parent = list(range(n))\n"
                    "    rank = [0] * n\n"
                    "\n"
                    "    def find(x):\n"
                    "        while parent[x] != x:\n"
                    "            parent[x] = parent[parent[x]]\n"
                    "            x = parent[x]\n"
                    "        return x\n"
                    "\n"
                    "    def union(a, b):\n"
                    "        ra, rb = find(a), find(b)\n"
                    "        if ra == rb:\n"
                    "            return False\n"
                    "        if rank[ra] < rank[rb]:\n"
                    "            ra, rb = rb, ra\n"
                    "        parent[rb] = ra\n"
                    "        if rank[ra] == rank[rb]:\n"
                    "            rank[ra] += 1\n"
                    "        return True\n"
                    "\n"
                    "    for u, v in edges:\n"
                    "        if not union(u, v):\n"
                    "            return False\n"
                    "    return True"
                ),
                "javascript": (
                    "function validTree(n, edges) {\n"
                    "    if (edges.length !== n - 1) return false;\n"
                    "    const parent = Array.from({length: n}, (_, i) => i);\n"
                    "    const rank = new Array(n).fill(0);\n"
                    "    const find = (x) => {\n"
                    "        while (parent[x] !== x) {\n"
                    "            parent[x] = parent[parent[x]];\n"
                    "            x = parent[x];\n"
                    "        }\n"
                    "        return x;\n"
                    "    };\n"
                    "    for (const [u, v] of edges) {\n"
                    "        const ru = find(u), rv = find(v);\n"
                    "        if (ru === rv) return false;\n"
                    "        if (rank[ru] < rank[rv]) parent[ru] = rv;\n"
                    "        else if (rank[ru] > rank[rv]) parent[rv] = ru;\n"
                    "        else { parent[rv] = ru; rank[ru]++; }\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
                "java": (
                    "public boolean validTree(int n, int[][] edges) {\n"
                    "    if (edges.length != n - 1) return false;\n"
                    "    int[] parent = new int[n];\n"
                    "    int[] rank = new int[n];\n"
                    "    for (int i = 0; i < n; i++) parent[i] = i;\n"
                    "    for (int[] e : edges) {\n"
                    "        int ru = find(parent, e[0]);\n"
                    "        int rv = find(parent, e[1]);\n"
                    "        if (ru == rv) return false;\n"
                    "        if (rank[ru] < rank[rv]) parent[ru] = rv;\n"
                    "        else if (rank[ru] > rank[rv]) parent[rv] = ru;\n"
                    "        else { parent[rv] = ru; rank[ru]++; }\n"
                    "    }\n"
                    "    return true;\n"
                    "}\n"
                    "private int find(int[] parent, int x) {\n"
                    "    while (parent[x] != x) {\n"
                    "        parent[x] = parent[parent[x]];\n"
                    "        x = parent[x];\n"
                    "    }\n"
                    "    return x;\n"
                    "}"
                ),
            },
        },
        {
            "title": "DFS Tree-Check",
            "time_complexity": "O(n + E)",
            "space_complexity": "O(n + E)",
            "description": (
                "Edge-count short-circuit, then a DFS from node 0 over an adjacency list. Pass the parent "
                "into each recursive call so the back-edge to the parent isn't mistaken for a cycle. After "
                "the DFS, the graph is a valid tree iff every node was visited (connected) — the n-1 edge "
                "count guarantees acyclicity given connectedness, but the explicit cycle check during DFS "
                "is robust either way."
            ),
            "code": {
                "python": (
                    "def valid_tree(n, edges):\n"
                    "    if len(edges) != n - 1:\n"
                    "        return False\n"
                    "    adj = [[] for _ in range(n)]\n"
                    "    for u, v in edges:\n"
                    "        adj[u].append(v)\n"
                    "        adj[v].append(u)\n"
                    "    visited = [False] * n\n"
                    "\n"
                    "    def dfs(node, parent):\n"
                    "        if visited[node]:\n"
                    "            return False\n"
                    "        visited[node] = True\n"
                    "        for nxt in adj[node]:\n"
                    "            if nxt == parent:\n"
                    "                continue\n"
                    "            if not dfs(nxt, node):\n"
                    "                return False\n"
                    "        return True\n"
                    "\n"
                    "    if not dfs(0, -1):\n"
                    "        return False\n"
                    "    return all(visited)"
                ),
                "javascript": (
                    "function validTree(n, edges) {\n"
                    "    if (edges.length !== n - 1) return false;\n"
                    "    const adj = Array.from({length: n}, () => []);\n"
                    "    for (const [u, v] of edges) { adj[u].push(v); adj[v].push(u); }\n"
                    "    const visited = new Array(n).fill(false);\n"
                    "    const dfs = (node, parent) => {\n"
                    "        if (visited[node]) return false;\n"
                    "        visited[node] = true;\n"
                    "        for (const nxt of adj[node]) {\n"
                    "            if (nxt === parent) continue;\n"
                    "            if (!dfs(nxt, node)) return false;\n"
                    "        }\n"
                    "        return true;\n"
                    "    };\n"
                    "    if (!dfs(0, -1)) return false;\n"
                    "    return visited.every(Boolean);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recall the tree definition: connected + acyclic. Equivalent on n nodes: connected + exactly n-1 edges, OR acyclic + exactly n-1 edges.",
        "2. First check `len(edges) == n - 1`. Cheap, eliminates most invalid inputs in one comparison.",
        "3. Decide: detect cycles (Union-Find is natural) or detect connectedness (DFS/BFS is natural). Either suffices once edge count is right.",
        "4. Union-Find: for each edge, union; if endpoints already share a root, that edge closes a cycle → not a tree.",
        "5. DFS: build adjacency list, traverse from node 0, pass parent down to ignore the back-edge. Confirm all n nodes were visited.",
        "6. Edge cases: n=1 with no edges is a valid tree. n=0 isn't usually in scope; check the constraint. Self-loops and duplicate edges aren't in this problem's constraints.",
    ],
    "tips": [
        "The `len(edges) == n - 1` short-circuit is the single most useful one-liner here — interviewers love when you state it before writing any graph code.",
        "Union by rank + path compression makes Union-Find effectively O(α(n)) per op. Without them you regress to O(log n) or worse — write both.",
        "In the DFS, the parent-edge skip is the part candidates forget. Without it, every visited child immediately reports a 'cycle'.",
        "Iterative DFS with an explicit stack avoids recursion-depth issues if n is large. The constraint here (n ≤ 2000) fits Python's default 1000-frame limit only loosely — mention it.",
        "BFS is interchangeable with DFS for this problem — connectedness doesn't care about traversal order. Pick whichever you write more reliably.",
        "A common follow-up is 'Number of Connected Components in an Undirected Graph' (LC 323) — same Union-Find scaffolding, just count distinct roots at the end.",
    ],
    "companies": ["Google", "Facebook", "Amazon", "Microsoft", "Bloomberg", "LinkedIn"],
    "topics": ["Graph", "Union-Find", "DFS", "BFS"],
    "time_complexity": "O(E·α(n))",
    "space_complexity": "O(n)",
}


def REFERENCE(n, edges):
    if len(edges) != n - 1:
        return False
    parent = list(range(n))
    rank = [0] * n

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1
        return True

    for u, v in edges:
        if not union(u, v):
            return False
    return True


register(PAYLOAD, REFERENCE)
