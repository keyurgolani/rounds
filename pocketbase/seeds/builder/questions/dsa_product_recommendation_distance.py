"""Product Recommendation Distance — Easy. BFS.

Distance in hops between two product nodes in a directed recommendation
graph. Same shape as 'Bacon number': BFS, count layers, return the layer
at which the destination first appears."""
from builder.registry import register


PAYLOAD = {
    "title": "Product Recommendation Distance",
    "difficulty": "Easy",
    "description": (
        "Given a product recommendation graph as an adjacency list (`product → list of recommended "
        "products`), and two products `origin` and `dest`, return the **number of hops** from `origin` to "
        "`dest`. If there's no path, return `-1`. If `origin == dest`, return `0`.\n\n"
        "**Example:**\n"
        "- Input: `graph = {'A': ['B', 'C'], 'B': ['D'], 'C': ['D'], 'D': []}`, `origin = 'A'`, `dest = 'D'`\n"
        "- Output: `2` (A → B → D, or A → C → D)"
    ),
    "hints": [
        "BFS on an unweighted graph gives shortest hop count by construction.",
        "Track visited nodes to avoid revisiting and to terminate on cycles.",
        "Track depth alongside the queue: either store `(node, depth)` tuples or process the queue level by level.",
        "Stop the moment `dest` is dequeued — don't keep BFSing.",
        "Edge cases: `origin == dest` (return 0), `dest` not reachable (return -1), `origin` not in graph (treat as unreachable).",
    ],
    "constraints": [
        "0 <= |graph| <= 10⁴",
        "Each node has 0 to 10³ neighbors",
    ],
    "starter_code": {
        "python": "def recommendation_distance(graph, origin, dest):\n    # Your code here\n    pass",
        "javascript": "function recommendationDistance(graph, origin, dest) {\n    // Your code here\n}",
        "java": "public int recommendationDistance(Map<String, List<String>> graph, String origin, String dest) {\n    // Your code here\n    return -1;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    g = {'A': ['B', 'C'], 'B': ['D'], 'C': ['D'], 'D': []}\n"
            "    print(recommendation_distance(g, 'A', 'D'))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"graph": {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []},
                    "origin": "A", "dest": "D"},
         "expected": 2,
         "description": "Two-hop diamond — both paths length 2", "tags": ["basic"]},
        {"input": {"graph": {"A": ["B"], "B": []}, "origin": "A", "dest": "A"},
         "expected": 0,
         "description": "Same node — distance 0", "tags": ["edge"]},
        {"input": {"graph": {"A": [], "B": []}, "origin": "A", "dest": "B"},
         "expected": -1,
         "description": "Disconnected", "tags": ["edge"]},
        {"input": {"graph": {"A": ["A"]}, "origin": "A", "dest": "A"},
         "expected": 0,
         "description": "Self-loop, self-target", "tags": ["edge"]},
        {"input": {"graph": {"A": ["B"], "B": ["A"]}, "origin": "A", "dest": "B"},
         "expected": 1,
         "description": "Cycle — must terminate via visited set", "tags": ["tricky"]},
        {"input": {"graph": {f"P{i}": [f"P{i+1}"] for i in range(99)} | {"P99": []},
                    "origin": "P0", "dest": "P99"},
         "expected": 99,
         "description": "Long chain — 99 hops", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "BFS with Depth Counter (Optimal)",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
            "description": (
                "Standard BFS. Push the origin with depth 0; each layer increments depth. Return the depth "
                "the first time you dequeue `dest`. Use a visited set to avoid revisiting and to handle "
                "cycles. Return -1 if the queue empties without finding `dest`."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "def recommendation_distance(graph, origin, dest):\n"
                    "    if origin == dest:\n"
                    "        return 0\n"
                    "    visited = {origin}\n"
                    "    q = deque([(origin, 0)])\n"
                    "    while q:\n"
                    "        node, d = q.popleft()\n"
                    "        for nbr in graph.get(node, []):\n"
                    "            if nbr in visited:\n"
                    "                continue\n"
                    "            if nbr == dest:\n"
                    "                return d + 1\n"
                    "            visited.add(nbr)\n"
                    "            q.append((nbr, d + 1))\n"
                    "    return -1"
                ),
                "javascript": (
                    "function recommendationDistance(graph, origin, dest) {\n"
                    "    if (origin === dest) return 0;\n"
                    "    const visited = new Set([origin]);\n"
                    "    const q = [[origin, 0]];\n"
                    "    while (q.length) {\n"
                    "        const [node, d] = q.shift();\n"
                    "        for (const nbr of (graph[node] || [])) {\n"
                    "            if (visited.has(nbr)) continue;\n"
                    "            if (nbr === dest) return d + 1;\n"
                    "            visited.add(nbr);\n"
                    "            q.push([nbr, d + 1]);\n"
                    "        }\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "DFS (Avoid)",
            "time_complexity": "O(V + E) for shortest path requires exhausting all paths",
            "space_complexity": "O(V) recursion + O(V) visited",
            "description": (
                "DFS *can* solve this, but you have to keep exploring even after finding a path because "
                "shorter ones might lie elsewhere — defeating the linear bound. BFS is strictly better here. "
                "Mention DFS only to dismiss it."
            ),
            "code": {
                "python": (
                    "# Sketch — don't actually use DFS for shortest distance.\n"
                    "def recommendation_distance(graph, origin, dest):\n"
                    "    raise NotImplementedError('Use BFS — DFS over-explores.')"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: 'shortest path in unweighted graph' → BFS.",
        "2. State that DFS works but doesn't get you the shortest path with a single traversal — BFS does.",
        "3. Walk through BFS: queue + visited set, increment depth each layer.",
        "4. Stop the moment you find `dest` — don't keep exploring.",
        "5. Edge cases: origin == dest (return 0), no path (return -1), cycles (visited set handles them).",
        "6. Mention bidirectional BFS for very deep / very wide graphs as the senior follow-up.",
    ],
    "tips": [
        "Don't use a list and `pop(0)` — that's O(n) per pop. Use `collections.deque` (Python) / `LinkedList` (Java).",
        "JS lacks a deque; for small graphs `Array.shift()` is fine, for performance use a circular buffer or index-based dequeue.",
        "Common follow-up: 'return the actual path, not just distance.' Track parent pointers and reconstruct.",
        "Common follow-up: 'count all paths of length k.' Switch to DFS with a depth cap and counter.",
        "Common follow-up: 'graph too large to fit in memory.' Use a remote/sharded adjacency lookup; BFS still works, just with paged neighbour fetches.",
    ],
    "companies": ["Amazon", "Meta", "LinkedIn", "Microsoft"],
    "topics": ["Graph", "BFS"],
    "time_complexity": "O(V + E)",
    "space_complexity": "O(V)",
}


def REFERENCE(graph, origin, dest):
    from collections import deque
    if origin == dest:
        return 0
    visited = {origin}
    q = deque([(origin, 0)])
    while q:
        node, d = q.popleft()
        for nbr in graph.get(node, []):
            if nbr in visited:
                continue
            if nbr == dest:
                return d + 1
            visited.add(nbr)
            q.append((nbr, d + 1))
    return -1


register(PAYLOAD, REFERENCE)
