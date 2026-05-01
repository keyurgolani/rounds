"""Number of Connected Components in an Undirected Graph — Medium. Union-Find / DFS / BFS.

LeetCode 323. The canonical 'count components' question. Three accepted
solutions: Union-Find (each edge unions two endpoints; final count =
distinct roots), DFS (mark visited, increment counter when launching a
fresh traversal), and BFS (same idea, queue-based). Union-Find with
path compression + union by rank is the answer for follow-ups that
add/remove edges online.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Number of Connected Components in an Undirected Graph",
    "difficulty": "Medium",
    "driver_kind": "function",
    "description": (
        "You have a graph of `n` nodes labeled from `0` to `n - 1`. You are given an integer `n` and an "
        "array `edges` where `edges[i] = [u, v]` indicates that there is an undirected edge between nodes "
        "`u` and `v` in the graph.\n\n"
        "Return *the number of connected components in the graph*.\n\n"
        "**Example 1:**\n"
        "- Input: `n = 5, edges = [[0,1],[1,2],[3,4]]`\n"
        "- Output: `2`\n"
        "- Explanation: Nodes `{0,1,2}` form one component and nodes `{3,4}` form another.\n\n"
        "**Example 2:**\n"
        "- Input: `n = 5, edges = [[0,1],[1,2],[2,3],[3,4]]`\n"
        "- Output: `1`\n"
        "- Explanation: All five nodes are reachable from each other through the chain of edges."
    ),
    "hints": [
        "Two well-known approaches: Union-Find (a.k.a. Disjoint Set Union) and graph traversal (DFS or BFS). Both run in near-linear time. Pick one and own it.",
        "Union-Find: start with `n` components and a `parent` array where `parent[i] = i`. For each edge `(u, v)`, if `find(u) != find(v)` union them and decrement the component counter. Final counter is the answer.",
        "Make Union-Find fast: **path compression** in `find` (point every node on the lookup path directly at the root) and **union by rank/size** in `union` (attach the smaller tree under the larger). Together this gives O(α(n)) per op — effectively O(1).",
        "DFS approach: build an adjacency list. Iterate `i` from `0` to `n-1`; when `i` is unvisited, run DFS from `i`, mark every reachable node visited, and increment the component counter. Time O(V + E).",
        "BFS approach: same skeleton as DFS but use a queue instead of recursion — useful when `n` is large enough that recursion would blow the stack.",
    ],
    "constraints": [
        "1 <= n <= 2000",
        "0 <= edges.length <= n * (n - 1) / 2",
        "There are no self-loops or repeated edges.",
    ],
    "starter_code": {
        "python": "def count_components(n, edges):\n    # Your code here\n    pass",
        "javascript": "function countComponents(n, edges) {\n    // Your code here\n}",
        "java": "public int countComponents(int n, int[][] edges) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(5, [[0,1],[1,2],[3,4]]), (5, [[0,1],[1,2],[2,3],[3,4]]), (4, [])]\n"
            "    for n, edges in cases:\n"
            "        print(f\"count_components({n}, {edges}) = {count_components(n, edges)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[5, [[0,1],[1,2],[3,4]]], [5, [[0,1],[1,2],[2,3],[3,4]]], [4, []]].forEach(([n, edges]) =>\n"
            "    console.log(`countComponents =`, countComponents(n, edges))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.countComponents(5, new int[][]{{0,1},{1,2},{3,4}}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"n": 5, "edges": [[0, 1], [1, 2], [3, 4]]}, "expected": 2,
         "description": "LeetCode example 1 — two components {0,1,2} and {3,4}", "tags": ["basic"]},
        {"input": {"n": 5, "edges": [[0, 1], [1, 2], [2, 3], [3, 4]]}, "expected": 1,
         "description": "LeetCode example 2 — chain through all five nodes", "tags": ["basic"]},
        {"input": {"n": 0, "edges": []}, "expected": 0,
         "description": "Empty graph — zero nodes, zero components", "tags": ["edge"]},
        {"input": {"n": 1, "edges": []}, "expected": 1,
         "description": "Single isolated node", "tags": ["edge"]},
        {"input": {"n": 5, "edges": []}, "expected": 5,
         "description": "Five isolated nodes — no edges means n components", "tags": ["edge"]},
        {"input": {"n": 4, "edges": [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]]}, "expected": 1,
         "description": "Complete graph K4 — single component", "tags": ["tricky"]},
        {"input": {"n": 6, "edges": [[0, 1], [0, 2], [0, 3], [0, 4], [0, 5]]}, "expected": 1,
         "description": "Star graph — all leaves connect to center node 0", "tags": ["tricky"]},
        {"input": {"n": 6, "edges": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5]]}, "expected": 1,
         "description": "Linear chain of six nodes", "tags": ["tricky"]},
        {"input": {"n": 7, "edges": [[0, 1], [2, 3], [4, 5]]}, "expected": 4,
         "description": "Three pairs plus one isolated node — four components", "tags": ["tricky"]},
        {"input": {"n": 8, "edges": [[0, 1], [1, 2], [3, 4], [5, 6], [6, 7]]}, "expected": 3,
         "description": "Three components of sizes 3, 2, 3", "tags": ["tricky"]},
        {"input": {"n": 10, "edges": [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]}, "expected": 5,
         "description": "Five disjoint pairs", "tags": ["tricky"]},
        {"input": {"n": 4, "edges": [[0, 1], [2, 3], [1, 2]]}, "expected": 1,
         "description": "Edges given out of order — union-find still merges correctly", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Union-Find with Path Compression and Union by Rank (Optimal)",
            "time_complexity": "O(E·α(n))",
            "space_complexity": "O(n)",
            "description": (
                "Initialise `parent[i] = i` and a counter `components = n`. For each edge `(u, v)`, find "
                "the roots of `u` and `v`. If they differ, union them (attach the shallower tree under the "
                "deeper one) and decrement `components`. Path compression flattens the tree on every "
                "`find`, so the amortised cost per operation is the inverse Ackermann function α(n) — "
                "essentially constant."
            ),
            "code": {
                "python": (
                    "def count_components(n, edges):\n"
                    "    parent = list(range(n))\n"
                    "    rank = [0] * n\n"
                    "    components = n\n"
                    "\n"
                    "    def find(x):\n"
                    "        while parent[x] != x:\n"
                    "            parent[x] = parent[parent[x]]  # path compression\n"
                    "            x = parent[x]\n"
                    "        return x\n"
                    "\n"
                    "    def union(a, b):\n"
                    "        nonlocal components\n"
                    "        ra, rb = find(a), find(b)\n"
                    "        if ra == rb:\n"
                    "            return\n"
                    "        if rank[ra] < rank[rb]:\n"
                    "            ra, rb = rb, ra\n"
                    "        parent[rb] = ra\n"
                    "        if rank[ra] == rank[rb]:\n"
                    "            rank[ra] += 1\n"
                    "        components -= 1\n"
                    "\n"
                    "    for u, v in edges:\n"
                    "        union(u, v)\n"
                    "    return components"
                ),
                "javascript": (
                    "function countComponents(n, edges) {\n"
                    "    const parent = Array.from({length: n}, (_, i) => i);\n"
                    "    const rank = new Array(n).fill(0);\n"
                    "    let components = n;\n"
                    "\n"
                    "    const find = (x) => {\n"
                    "        while (parent[x] !== x) {\n"
                    "            parent[x] = parent[parent[x]];\n"
                    "            x = parent[x];\n"
                    "        }\n"
                    "        return x;\n"
                    "    };\n"
                    "\n"
                    "    const union = (a, b) => {\n"
                    "        let ra = find(a), rb = find(b);\n"
                    "        if (ra === rb) return;\n"
                    "        if (rank[ra] < rank[rb]) [ra, rb] = [rb, ra];\n"
                    "        parent[rb] = ra;\n"
                    "        if (rank[ra] === rank[rb]) rank[ra]++;\n"
                    "        components--;\n"
                    "    };\n"
                    "\n"
                    "    for (const [u, v] of edges) union(u, v);\n"
                    "    return components;\n"
                    "}"
                ),
                "java": (
                    "public int countComponents(int n, int[][] edges) {\n"
                    "    int[] parent = new int[n];\n"
                    "    int[] rank = new int[n];\n"
                    "    for (int i = 0; i < n; i++) parent[i] = i;\n"
                    "    int components = n;\n"
                    "    for (int[] e : edges) {\n"
                    "        int ra = find(parent, e[0]);\n"
                    "        int rb = find(parent, e[1]);\n"
                    "        if (ra == rb) continue;\n"
                    "        if (rank[ra] < rank[rb]) { int t = ra; ra = rb; rb = t; }\n"
                    "        parent[rb] = ra;\n"
                    "        if (rank[ra] == rank[rb]) rank[ra]++;\n"
                    "        components--;\n"
                    "    }\n"
                    "    return components;\n"
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
            "title": "DFS on Adjacency List",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V + E)",
            "description": (
                "Build an adjacency list from the edge list. Walk `i` from `0` to `n-1`; whenever you "
                "find an unvisited node, run DFS from it (marking every reachable node) and bump the "
                "component counter. Each vertex and edge is touched at most twice, so the runtime is "
                "linear in the graph size."
            ),
            "code": {
                "python": (
                    "def count_components(n, edges):\n"
                    "    adj = [[] for _ in range(n)]\n"
                    "    for u, v in edges:\n"
                    "        adj[u].append(v)\n"
                    "        adj[v].append(u)\n"
                    "    visited = [False] * n\n"
                    "    count = 0\n"
                    "\n"
                    "    def dfs(node):\n"
                    "        stack = [node]\n"
                    "        while stack:\n"
                    "            cur = stack.pop()\n"
                    "            if visited[cur]:\n"
                    "                continue\n"
                    "            visited[cur] = True\n"
                    "            for nxt in adj[cur]:\n"
                    "                if not visited[nxt]:\n"
                    "                    stack.append(nxt)\n"
                    "\n"
                    "    for i in range(n):\n"
                    "        if not visited[i]:\n"
                    "            dfs(i)\n"
                    "            count += 1\n"
                    "    return count"
                ),
                "javascript": (
                    "function countComponents(n, edges) {\n"
                    "    const adj = Array.from({length: n}, () => []);\n"
                    "    for (const [u, v] of edges) { adj[u].push(v); adj[v].push(u); }\n"
                    "    const visited = new Array(n).fill(false);\n"
                    "    let count = 0;\n"
                    "    const dfs = (start) => {\n"
                    "        const stack = [start];\n"
                    "        while (stack.length) {\n"
                    "            const cur = stack.pop();\n"
                    "            if (visited[cur]) continue;\n"
                    "            visited[cur] = true;\n"
                    "            for (const nxt of adj[cur]) if (!visited[nxt]) stack.push(nxt);\n"
                    "        }\n"
                    "    };\n"
                    "    for (let i = 0; i < n; i++) {\n"
                    "        if (!visited[i]) { dfs(i); count++; }\n"
                    "    }\n"
                    "    return count;\n"
                    "}"
                ),
                "java": (
                    "public int countComponents(int n, int[][] edges) {\n"
                    "    List<List<Integer>> adj = new ArrayList<>();\n"
                    "    for (int i = 0; i < n; i++) adj.add(new ArrayList<>());\n"
                    "    for (int[] e : edges) { adj.get(e[0]).add(e[1]); adj.get(e[1]).add(e[0]); }\n"
                    "    boolean[] visited = new boolean[n];\n"
                    "    int count = 0;\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        if (!visited[i]) { dfs(i, adj, visited); count++; }\n"
                    "    }\n"
                    "    return count;\n"
                    "}\n"
                    "private void dfs(int start, List<List<Integer>> adj, boolean[] visited) {\n"
                    "    Deque<Integer> stack = new ArrayDeque<>();\n"
                    "    stack.push(start);\n"
                    "    while (!stack.isEmpty()) {\n"
                    "        int cur = stack.pop();\n"
                    "        if (visited[cur]) continue;\n"
                    "        visited[cur] = true;\n"
                    "        for (int nxt : adj.get(cur)) if (!visited[nxt]) stack.push(nxt);\n"
                    "    }\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the question as 'count connected components in an undirected graph' — a textbook DSU/DFS/BFS pattern.",
        "2. Pick a representation. Edges as a list are fine for Union-Find; for DFS/BFS you'll want an adjacency list.",
        "3. Union-Find framing: start with `n` components. Every edge that joins two *different* components reduces the count by one. Final answer is `n - successful_unions`.",
        "4. DFS framing: run a traversal from each unvisited node; every fresh launch corresponds to one new component.",
        "5. Always include path compression *and* union by rank (or size). Without both, pathological inputs degrade to O(n) per op.",
        "6. Sanity-check edges: zero edges → answer is `n`. A spanning tree (n-1 edges that connect everything) → answer is 1.",
        "7. Edge cases: `n = 0` (return 0), `n = 1` (return 1), self-loops would be no-ops in Union-Find but the problem guarantees none.",
    ],
    "tips": [
        "If the interviewer asks for online connectivity (edges streaming in, queries interleaved), Union-Find wins decisively — DFS would re-traverse on every query.",
        "Path compression alone or union-by-rank alone gives O(log n) amortised. Both together give O(α(n)). Mention this explicitly.",
        "If recursion depth is a concern (`n` up to 10⁵+), implement DFS iteratively with a stack — same complexity, no stack overflow.",
        "Common variant: 'Number of Provinces' (LC 547) is the same problem with an adjacency-matrix input. Same solution; just iterate the upper triangle.",
        "Common variant: 'Graph Valid Tree' (LC 261) — connected components = 1 *and* edges = n - 1. Union-Find handles both checks in one pass (detect a cycle when both endpoints share a root).",
        "Watch for duplicate edges in unconstrained variants. Union-Find is naturally idempotent on dupes; adjacency-list DFS doesn't care either, but it bloats the list.",
    ],
    "companies": ["Google", "Facebook", "Amazon", "Microsoft", "LinkedIn", "Pinterest"],
    "topics": ["Graph", "Union Find", "Depth-First Search", "Breadth-First Search"],
    "time_complexity": "O(E·α(n))",
    "space_complexity": "O(n)",
}


def REFERENCE(n, edges):
    parent = list(range(n))
    rank = [0] * n
    components = n

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        nonlocal components
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1
        components -= 1

    for u, v in edges:
        union(u, v)
    return components


register(PAYLOAD, REFERENCE)
