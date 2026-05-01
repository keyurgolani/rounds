"""Redundant Connection — Medium. Union-Find / Graph Cycle.

A canonical Union-Find (DSU) interview problem. The graph started life
as a tree on n nodes, then someone added one extra edge — find which
edge to delete to recover the tree. The phrase 'last edge that creates
a cycle' is the giveaway: process edges in order, union as you go, and
the first time you try to union two nodes already in the same component
you've found the answer. Path compression + union by rank gives near
O(n). The DFS alternative is O(n^2) worst case but worth knowing for
the variant where you must return *any* edge on the cycle, not the last
one in input order.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Redundant Connection",
    "difficulty": "Medium",
    "description": (
        "In this problem, a tree is an undirected graph that is connected and has no cycles.\n\n"
        "You are given a graph that started as a tree with `n` nodes labeled from `1` to `n`, with one "
        "additional edge added. The added edge has two **different** vertices chosen from `1` to `n`, and "
        "was not an edge that already existed.\n\n"
        "The graph is represented as an array `edges` of length `n` where `edges[i] = [a_i, b_i]` indicates "
        "an undirected edge connecting nodes `a_i` and `b_i`.\n\n"
        "Return **an edge that can be removed** so that the resulting graph is a tree of `n` nodes. If there "
        "are multiple answers, return the edge that occurs **last** in the input.\n\n"
        "**Example 1:**\n"
        "- Input: `edges = [[1,2],[1,3],[2,3]]`\n"
        "- Output: `[2,3]`\n"
        "- Explanation: Nodes 1, 2, 3 form a triangle. The edge `[2,3]` is the last one added that closes "
        "the cycle, so removing it yields a tree.\n\n"
        "**Example 2:**\n"
        "- Input: `edges = [[1,2],[2,3],[3,4],[1,4],[1,5]]`\n"
        "- Output: `[1,4]`\n"
        "- Explanation: The cycle is 1 - 2 - 3 - 4 - 1. The edge `[1,4]` is the last edge in the input that "
        "closes the cycle. The trailing edge `[1,5]` attaches a leaf and is not part of any cycle."
    ),
    "hints": [
        "The graph has exactly `n` nodes and `n` edges. A tree on `n` nodes has `n-1` edges, so there is exactly one cycle, and exactly one redundant edge to remove.",
        "Union-Find (DSU) is the textbook fit. Iterate edges in input order; for each `(u, v)`, if `find(u) == find(v)` they're already connected — this edge closes the cycle, return it. Otherwise `union(u, v)` and continue.",
        "Because you walk the input left-to-right and return on the first union that collapses, the edge you return is automatically the *last* one in the input that creates a cycle (any earlier cycle-creating edge would have been caught first — but the problem guarantees only one extra edge, so there's only one such collision).",
        "Path compression + union by rank/size keeps each operation at near-constant amortized cost: O(n · α(n)) total, where α is the inverse Ackermann function.",
        "Alternative without DSU: for each edge `(u, v)`, before adding it, run DFS/BFS from `u` over the edges added so far and check if `v` is already reachable. If yes, return `(u, v)`. O(n²) but conceptually simpler and useful prep for the harder follow-up *Redundant Connection II* (directed variant).",
    ],
    "constraints": [
        "n == edges.length",
        "3 <= n <= 1000",
        "Nodes are labeled from 1 to n (1-indexed); `edges[i] = [a_i, b_i]` with `1 <= a_i < b_i <= n` and no duplicate edges.",
    ],
    "starter_code": {
        "python": "def find_redundant_connection(edges):\n    # Your code here\n    pass",
        "javascript": "function findRedundantConnection(edges) {\n    // Your code here\n}",
        "java": "public int[] findRedundantConnection(int[][] edges) {\n    // Your code here\n    return new int[]{};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[[1,2],[1,3],[2,3]], [[1,2],[2,3],[3,4],[1,4],[1,5]]]\n"
            "    for edges in cases:\n"
            "        print(f\"find_redundant_connection({edges}) = {find_redundant_connection(edges)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,2],[1,3],[2,3]], [[1,2],[2,3],[3,4],[1,4],[1,5]]].forEach(edges =>\n"
            "    console.log(`findRedundantConnection =`, findRedundantConnection(edges))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[] ans = s.findRedundantConnection(new int[][]{{1,2},{1,3},{2,3}});\n"
            "        System.out.println(\"[\" + ans[0] + \",\" + ans[1] + \"]\");\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"edges": [[1, 2], [1, 3], [2, 3]]}, "expected": [2, 3],
         "description": "LC Example 1 — triangle on 3 nodes; last edge closes the cycle", "tags": ["basic"]},
        {"input": {"edges": [[1, 2], [2, 3], [3, 4], [1, 4], [1, 5]]}, "expected": [1, 4],
         "description": "LC Example 2 — 4-cycle plus a pendant leaf; redundant edge is interior",
         "tags": ["basic"]},
        {"input": {"edges": [[1, 2], [2, 3], [1, 3]]}, "expected": [1, 3],
         "description": "Cycle closes at the last edge — chain then back-edge", "tags": ["basic"]},
        {"input": {"edges": [[1, 2], [1, 2]]}, "expected": [1, 2],
         "description": "Two-node multi-edge — second copy is redundant (n=2 corner)", "tags": ["edge"]},
        {"input": {"edges": [[1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 1]]}, "expected": [6, 1],
         "description": "Long chain 1-2-3-4-5-6 with the closing back-edge last — single big cycle",
         "tags": ["tricky"]},
        {"input": {"edges": [[3, 4], [1, 2], [2, 4], [3, 5], [2, 5]]}, "expected": [2, 5],
         "description": "Edges given out of order; redundant edge is the last in input", "tags": ["tricky"]},
        {"input": {"edges": [[1, 2], [1, 3], [1, 4], [1, 5], [3, 5]]}, "expected": [3, 5],
         "description": "Star centered at 1 plus an extra rim edge — last edge is redundant",
         "tags": ["tricky"]},
        {"input": {"edges": [[1, 4], [3, 4], [1, 3], [1, 2], [4, 5]]}, "expected": [1, 3],
         "description": "Cycle forms early (edges 1-3); trailing edges are tree extensions",
         "tags": ["tricky"]},
        {"input": {"edges": [
            [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10],
            [10, 11], [11, 12], [12, 13], [13, 14], [14, 15], [15, 1]
        ]}, "expected": [15, 1],
         "description": "15-node ring — last edge closes a long cycle", "tags": ["large"]},
        {"input": {"edges": [
            [1, 2], [3, 4], [5, 6], [1, 3], [3, 5], [4, 6]
        ]}, "expected": [4, 6],
         "description": "Three pairs fused via bridges 1-3 and 3-5; the trailing 4-6 closes the cycle across already-merged components",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Union-Find with Path Compression and Union by Rank (Optimal)",
            "time_complexity": "O(n · α(n))",
            "space_complexity": "O(n)",
            "description": (
                "Maintain a DSU over the n nodes. Process edges in input order. For each `(u, v)`, if "
                "`find(u) == find(v)` the two endpoints are already in the same connected component, so "
                "adding this edge would close a cycle — return it. Otherwise `union(u, v)` and continue. "
                "Path compression on `find` plus union by rank on `union` gives near-constant amortized "
                "operations (inverse Ackermann)."
            ),
            "code": {
                "python": (
                    "def find_redundant_connection(edges):\n"
                    "    n = len(edges)\n"
                    "    parent = list(range(n + 1))\n"
                    "    rank = [0] * (n + 1)\n"
                    "\n"
                    "    def find(x):\n"
                    "        while parent[x] != x:\n"
                    "            parent[x] = parent[parent[x]]  # path compression (halving)\n"
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
                    "            return [u, v]\n"
                    "    return []"
                ),
                "javascript": (
                    "function findRedundantConnection(edges) {\n"
                    "    const n = edges.length;\n"
                    "    const parent = Array.from({length: n + 1}, (_, i) => i);\n"
                    "    const rank = new Array(n + 1).fill(0);\n"
                    "\n"
                    "    function find(x) {\n"
                    "        while (parent[x] !== x) {\n"
                    "            parent[x] = parent[parent[x]];\n"
                    "            x = parent[x];\n"
                    "        }\n"
                    "        return x;\n"
                    "    }\n"
                    "\n"
                    "    function union(a, b) {\n"
                    "        let ra = find(a), rb = find(b);\n"
                    "        if (ra === rb) return false;\n"
                    "        if (rank[ra] < rank[rb]) [ra, rb] = [rb, ra];\n"
                    "        parent[rb] = ra;\n"
                    "        if (rank[ra] === rank[rb]) rank[ra]++;\n"
                    "        return true;\n"
                    "    }\n"
                    "\n"
                    "    for (const [u, v] of edges) {\n"
                    "        if (!union(u, v)) return [u, v];\n"
                    "    }\n"
                    "    return [];\n"
                    "}"
                ),
                "java": (
                    "public int[] findRedundantConnection(int[][] edges) {\n"
                    "    int n = edges.length;\n"
                    "    int[] parent = new int[n + 1];\n"
                    "    int[] rank = new int[n + 1];\n"
                    "    for (int i = 0; i <= n; i++) parent[i] = i;\n"
                    "    for (int[] e : edges) {\n"
                    "        int ra = find(parent, e[0]);\n"
                    "        int rb = find(parent, e[1]);\n"
                    "        if (ra == rb) return e;\n"
                    "        if (rank[ra] < rank[rb]) { int t = ra; ra = rb; rb = t; }\n"
                    "        parent[rb] = ra;\n"
                    "        if (rank[ra] == rank[rb]) rank[ra]++;\n"
                    "    }\n"
                    "    return new int[]{};\n"
                    "}\n"
                    "\n"
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
            "title": "Incremental DFS Cycle Check (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(n)",
            "description": (
                "Build the adjacency list one edge at a time. Before adding edge `(u, v)`, run DFS from `u` "
                "over the edges added so far; if you can already reach `v`, this edge closes a cycle — "
                "return it. Otherwise add it and move on. Worst-case O(n²) — fine for n ≤ 1000, and the "
                "natural starting point if you don't recall DSU. Also generalises better to *Redundant "
                "Connection II* (the directed variant), where DSU alone isn't quite enough."
            ),
            "code": {
                "python": (
                    "def find_redundant_connection(edges):\n"
                    "    from collections import defaultdict\n"
                    "    graph = defaultdict(set)\n"
                    "\n"
                    "    def reachable(src, dst):\n"
                    "        seen = {src}\n"
                    "        stack = [src]\n"
                    "        while stack:\n"
                    "            node = stack.pop()\n"
                    "            if node == dst:\n"
                    "                return True\n"
                    "            for nxt in graph[node]:\n"
                    "                if nxt not in seen:\n"
                    "                    seen.add(nxt)\n"
                    "                    stack.append(nxt)\n"
                    "        return False\n"
                    "\n"
                    "    for u, v in edges:\n"
                    "        if u in graph and v in graph and reachable(u, v):\n"
                    "            return [u, v]\n"
                    "        graph[u].add(v)\n"
                    "        graph[v].add(u)\n"
                    "    return []"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the structure: n nodes, n edges, originally a tree → exactly one cycle, exactly one redundant edge. There is only one valid answer; the 'last in input' tiebreaker is mostly there to make the spec deterministic.",
        "2. Cycle detection in an *incremental* undirected graph is the textbook DSU use case. State Union-Find as the target before coding.",
        "3. Walk edges left-to-right. For each `(u, v)`: if `find(u) == find(v)`, the two endpoints are already connected through earlier edges, so this edge would create the cycle — return it.",
        "4. Otherwise `union(u, v)` and keep going. The first collision is the answer; you never see a second one (only one extra edge exists).",
        "5. Implement DSU with path compression on `find` and union by rank/size on `union` — both are one-liners, both are expected, and together they give near-O(1) amortized ops.",
        "6. Mention the DFS alternative (O(n²)) explicitly. It's slower but conceptually cleaner, and it's the right starting point for the harder *Redundant Connection II* follow-up.",
        "7. Edge cases worth saying out loud: a 2-node multi-edge (`[[1,2],[1,2]]`), the cycle closing on the very first non-tree edge, and the cycle closing on the last edge.",
    ],
    "tips": [
        "DSU is by far the cleanest answer here. If you have an interview prep list, this problem is *the* canonical justification for memorising a 10-line DSU template.",
        "Path compression alone (without union by rank) is already O(log n) amortized — fine for n ≤ 1000. Adding union by rank takes you to inverse Ackermann. Both are easy; do both.",
        "Iterative `find` with path halving (`parent[x] = parent[parent[x]]`) avoids Python recursion-limit issues and is the form most interviewers prefer.",
        "Size your `parent` array to `n + 1`, not `n` — nodes are 1-indexed in this problem. A common silent bug.",
        "Common follow-up: **Redundant Connection II** (LC 685) — same idea but the graph is *directed* and started as a rooted tree. DSU alone isn't enough; you have to also handle the case where some node ends up with two parents. Be ready to talk through the case split.",
        "If asked to return the *first* redundant edge instead of the last, the same DSU walk still works — you'd return on the first collision, which is exactly what this code already does. The 'last in input' phrasing is misleading: there's only one collision when only one edge is extra.",
        "If the interviewer pushes back and says 'no DSU', fall back to the incremental DFS approach. It's strictly worse asymptotically but still passes for n ≤ 1000, and it's the right springboard for the directed follow-up.",
    ],
    "companies": ["Google", "Amazon", "Microsoft", "Facebook", "Apple", "Bloomberg"],
    "topics": ["Union Find", "Graph", "Depth-First Search", "Breadth-First Search"],
    "time_complexity": "O(n · α(n))",
    "space_complexity": "O(n)",
}


def REFERENCE(edges):
    n = len(edges)
    parent = list(range(n + 1))
    rank = [0] * (n + 1)

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
            return [u, v]
    return []


register(PAYLOAD, REFERENCE)
