"""Shortest Path Between Profiles in a Friend Graph — Medium. BFS.

Classic 'six degrees of Kevin Bacon' problem. Optimal answer is BFS;
DFS gets you a path but not necessarily the shortest. Senior bar:
mention bidirectional BFS as the O(M^(N/2)) follow-up."""
from builder.registry import register


PAYLOAD = {
    "title": "Shortest Path Between Profiles",
    "difficulty": "Medium",
    "description": (
        "Given a social graph as an adjacency list (`profile → list of friend profiles`) and two profile "
        "names `start` and `end`, return the shortest **friend chain** linking them as a list of profiles "
        "starting with `start` and ending with `end`. If no path exists, return an empty list.\n\n"
        "**Example:**\n"
        "```\n"
        "graph = {\n"
        "  'Gordon':  ['Shantel', 'Aaron'],\n"
        "  'Shantel': ['Gordon', 'Maria'],\n"
        "  'Maria':   ['Shantel', 'David'],\n"
        "  'David':   ['Maria', 'Stephen'],\n"
        "  'Stephen': ['David'],\n"
        "  'Aaron':   ['Gordon']\n"
        "}\n"
        "start='Gordon', end='Stephen'\n"
        "Output: ['Gordon', 'Shantel', 'Maria', 'David', 'Stephen']\n"
        "```"
    ),
    "hints": [
        "BFS finds the shortest path in an unweighted graph by construction. Each level explored = one extra hop.",
        "DFS can find *a* path but not necessarily the shortest — don't lead with it.",
        "Track visited nodes to avoid infinite loops in cyclic graphs.",
        "Reconstruct the path with a parent pointer (`came_from[node] = previous`) — popping it back at the end.",
        "Bidirectional BFS halves the search depth: O(M^(N/2)) vs O(M^N) for one-sided BFS. Worth mentioning at senior level.",
        "Edge cases: start == end (return [start]), end not reachable (return []), end not in graph at all.",
    ],
    "constraints": [
        "0 <= |graph| <= 10⁴",
        "Each node has 0 to 10³ neighbors",
        "Graph is undirected — friendship is symmetric",
    ],
    "starter_code": {
        "python": "def shortest_path(graph, start, end):\n    # Your code here\n    pass",
        "javascript": "function shortestPath(graph, start, end) {\n    // Your code here\n}",
        "java": "public List<String> shortestPath(Map<String, List<String>> graph, String start, String end) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    g = {'A': ['B', 'C'], 'B': ['A', 'D'], 'C': ['A'], 'D': ['B']}\n"
            "    print(shortest_path(g, 'A', 'D'))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"graph": {"Gordon": ["Shantel", "Aaron"], "Shantel": ["Gordon", "Maria"],
                              "Maria": ["Shantel", "David"], "David": ["Maria", "Stephen"],
                              "Stephen": ["David"], "Aaron": ["Gordon"]},
                    "start": "Gordon", "end": "Stephen"},
         "expected": ["Gordon", "Shantel", "Maria", "David", "Stephen"],
         "description": "Canonical chain through 4 hops", "tags": ["basic"]},
        {"input": {"graph": {"A": ["B"], "B": ["A"]}, "start": "A", "end": "A"},
         "expected": ["A"],
         "description": "Self-target — trivial path", "tags": ["edge"]},
        {"input": {"graph": {"A": ["B"], "B": ["A"], "C": []}, "start": "A", "end": "C"},
         "expected": [],
         "description": "Disconnected — no path", "tags": ["edge"]},
        {"input": {"graph": {"A": ["B", "C"], "B": ["A", "D"], "C": ["A", "D"], "D": ["B", "C"]},
                    "start": "A", "end": "D"},
         "expected": {"$match": "any_of", "values": [["A", "B", "D"], ["A", "C", "D"]]},
         "description": "Two equally-short paths — accept either", "tags": ["tricky"]},
        {"input": {"graph": {}, "start": "A", "end": "B"}, "expected": [],
         "description": "Empty graph", "tags": ["edge"]},
        {"input": {"graph": {"A": ["A"]}, "start": "A", "end": "A"}, "expected": ["A"],
         "description": "Self-loop, self-target", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "BFS with Parent Pointers (Optimal)",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
            "description": (
                "BFS from `start`, recording each newly-discovered node's predecessor. Stop the moment "
                "`end` is dequeued. Reconstruct the path by walking parent pointers from `end` back to "
                "`start`, then reverse."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "def shortest_path(graph, start, end):\n"
                    "    if start == end:\n"
                    "        return [start] if start in graph or not graph else [start]\n"
                    "    came_from = {start: None}\n"
                    "    q = deque([start])\n"
                    "    while q:\n"
                    "        node = q.popleft()\n"
                    "        for nbr in graph.get(node, []):\n"
                    "            if nbr in came_from:\n"
                    "                continue\n"
                    "            came_from[nbr] = node\n"
                    "            if nbr == end:\n"
                    "                # reconstruct\n"
                    "                path = []\n"
                    "                cur = end\n"
                    "                while cur is not None:\n"
                    "                    path.append(cur)\n"
                    "                    cur = came_from[cur]\n"
                    "                return path[::-1]\n"
                    "            q.append(nbr)\n"
                    "    return []"
                ),
                "javascript": (
                    "function shortestPath(graph, start, end) {\n"
                    "    if (start === end) return [start];\n"
                    "    const cameFrom = new Map([[start, null]]);\n"
                    "    const q = [start];\n"
                    "    while (q.length) {\n"
                    "        const node = q.shift();\n"
                    "        for (const nbr of (graph[node] || [])) {\n"
                    "            if (cameFrom.has(nbr)) continue;\n"
                    "            cameFrom.set(nbr, node);\n"
                    "            if (nbr === end) {\n"
                    "                const path = [];\n"
                    "                let cur = end;\n"
                    "                while (cur !== null) { path.push(cur); cur = cameFrom.get(cur); }\n"
                    "                return path.reverse();\n"
                    "            }\n"
                    "            q.push(nbr);\n"
                    "        }\n"
                    "    }\n"
                    "    return [];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Bidirectional BFS (Senior Follow-up)",
            "time_complexity": "O(b^(d/2)) with branching factor b, distance d",
            "space_complexity": "O(b^(d/2))",
            "description": (
                "Search from both ends simultaneously. The two frontiers meet in the middle, halving the "
                "exponent on the branching factor. The trick: switch to the smaller frontier each step "
                "(BFS-from-the-smaller-side). Mention this even if you don't implement it under time pressure."
            ),
            "code": {
                "python": (
                    "def shortest_path(graph, start, end):\n"
                    "    if start == end:\n"
                    "        return [start]\n"
                    "    fwd = {start: [start]}\n"
                    "    bwd = {end: [end]}\n"
                    "    while fwd and bwd:\n"
                    "        if len(fwd) <= len(bwd):\n"
                    "            fwd = _step(graph, fwd, bwd)\n"
                    "            for k in fwd:\n"
                    "                if k in bwd:\n"
                    "                    return fwd[k] + bwd[k][-2::-1]\n"
                    "        else:\n"
                    "            bwd = _step(graph, bwd, fwd)\n"
                    "            for k in bwd:\n"
                    "                if k in fwd:\n"
                    "                    return fwd[k] + bwd[k][-2::-1]\n"
                    "    return []\n\n"
                    "def _step(graph, frontier, other):\n"
                    "    nxt = {}\n"
                    "    for node, path in frontier.items():\n"
                    "        for nbr in graph.get(node, []):\n"
                    "            if nbr not in frontier and nbr not in nxt:\n"
                    "                nxt[nbr] = path + [nbr]\n"
                    "    return nxt"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: 'shortest path in an unweighted graph' → BFS, by construction.",
        "2. State that DFS can find *a* path but not necessarily *the shortest*. Don't lead with it.",
        "3. Walk the BFS: queue + visited set, layer by layer. Record predecessor at first discovery.",
        "4. Reconstruct the path by walking predecessors from `end` back to `start`, then reverse.",
        "5. Discuss bidirectional BFS as the senior-level upgrade: O(b^(d/2)) instead of O(b^d).",
        "6. Edge cases: same node (return [start]), no path (return []), node missing from graph.",
    ],
    "tips": [
        "Use a dict for `came_from` rather than appending growing path lists per queue entry — that avoids quadratic blowup.",
        "If memory is tight, store only the predecessor and reconstruct lazily; don't store the full path with each frontier entry.",
        "Bidirectional BFS shines when branching factor is high (social graphs are dense): 6 degrees becomes 3 from each side.",
        "Common follow-up: 'weighted edges (e.g. closeness scores).' Switch from BFS to Dijkstra's.",
        "Common follow-up: 'find all shortest paths.' Track multiple predecessors; reconstruction returns a list of lists.",
    ],
    "companies": ["Amazon", "Meta", "LinkedIn", "Microsoft"],
    "topics": ["Graph", "BFS", "Shortest Path"],
    "time_complexity": "O(V + E)",
    "space_complexity": "O(V)",
}


def REFERENCE(graph, start, end):
    from collections import deque
    if start == end:
        return [start]
    came_from = {start: None}
    q = deque([start])
    while q:
        node = q.popleft()
        for nbr in graph.get(node, []):
            if nbr in came_from:
                continue
            came_from[nbr] = node
            if nbr == end:
                path = []
                cur = end
                while cur is not None:
                    path.append(cur)
                    cur = came_from[cur]
                return path[::-1]
            q.append(nbr)
    return []


register(PAYLOAD, REFERENCE)
