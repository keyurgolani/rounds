"""City Traffic — Medium. Graph / Edge Weighting.

Given a city graph where each node has a population and edges to
neighbours, when one city holds an event, return the maximum traffic
flowing across any single edge."""
from builder.registry import register


PAYLOAD = {
    "title": "City Traffic — Max Edge Load During Event",
    "difficulty": "Medium",
    "description": (
        "You have a graph of cities with populations. When city `event` holds an event, EVERY person from "
        "EVERY OTHER city travels to `event`. People take the SHORTEST PATH (by hop count). Return the "
        "**maximum** number of people that pass through any single edge.\n\n"
        "Each edge in the graph is undirected; an edge `(A, B)` carries traffic equal to the total "
        "population of cities for which the shortest path to `event` goes through that edge.\n\n"
        "**Example (from the source):**\n"
        "```\n"
        "cities = {\n"
        "  'A': {'pop': 1000, 'neighbors': ['E']},\n"
        "  'B': {'pop': 2000, 'neighbors': ['E']},\n"
        "  'C': {'pop': 3000, 'neighbors': ['E']},\n"
        "  'D': {'pop': 4000, 'neighbors': ['E']},\n"
        "  'E': {'pop': 5000, 'neighbors': ['A','B','C','D']}\n"
        "}\n"
        "event = 'A'  # everyone travels to A\n"
        "# B/C/D/E all go A→E (no, the other way: B→E→A means E→A carries B's pop)\n"
        "# Edges to A: only E—A. All of B+C+D+E (=14000) flow through that edge.\n"
        "max_traffic(cities, 'A') = 14000\n"
        "```"
    ),
    "hints": [
        "Run BFS from `event`. Each non-event city is assigned to the edge it traverses to reach `event`.",
        "Walk from each city back along its parent pointer to `event`, accumulating that city's population on each edge.",
        "Equivalent: BFS gives a tree rooted at `event`. Each non-root node sends its population through the tree edge to its parent. Return max edge total.",
        "If multiple shortest paths exist, the problem is ambiguous — pin it down. The clean spec: each city's population goes through the tree formed by BFS-parent pointers.",
        "Edge cases: `event` with no neighbours (no traffic), graph not connected (unreachable cities contribute zero), single city (zero traffic).",
    ],
    "constraints": [
        "1 <= |cities| <= 10⁴",
    ],
    "starter_code": {
        "python": "def max_traffic(cities, event):\n    # Your code here\n    pass",
        "javascript": "function maxTraffic(cities, event) {\n    // Your code here\n}",
        "java": "public int maxTraffic(Map<String, Object> cities, String event) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cities = {'A': {'pop': 1000, 'neighbors': ['B']},\n"
            "              'B': {'pop': 2000, 'neighbors': ['A']}}\n"
            "    print(max_traffic(cities, 'A'))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"cities": {"A": {"pop": 1000, "neighbors": ["E"]},
                                "B": {"pop": 2000, "neighbors": ["E"]},
                                "C": {"pop": 3000, "neighbors": ["E"]},
                                "D": {"pop": 4000, "neighbors": ["E"]},
                                "E": {"pop": 5000, "neighbors": ["A", "B", "C", "D"]}},
                    "event": "A"},
         "expected": 14000,
         "description": "Star with E hub; A is event — E—A carries everyone else", "tags": ["basic"]},
        {"input": {"cities": {"A": {"pop": 1000, "neighbors": ["B"]},
                                "B": {"pop": 2000, "neighbors": ["A"]}},
                    "event": "A"},
         "expected": 2000,
         "description": "Two cities — single edge", "tags": ["basic"]},
        {"input": {"cities": {"A": {"pop": 1000, "neighbors": []}}, "event": "A"},
         "expected": 0,
         "description": "Single isolated city — no traffic", "tags": ["edge"]},
        {"input": {"cities": {"A": {"pop": 100, "neighbors": ["B"]},
                                "B": {"pop": 200, "neighbors": ["A", "C"]},
                                "C": {"pop": 300, "neighbors": ["B"]}},
                    "event": "A"},
         "expected": 500,
         "description": "Linear A—B—C, event at A. Edge A—B carries B + C = 500",
         "tags": ["basic"]},
        {"input": {"cities": {"A": {"pop": 100, "neighbors": ["B"]},
                                "B": {"pop": 200, "neighbors": ["A"]},
                                "C": {"pop": 300, "neighbors": []}},
                    "event": "A"},
         "expected": 200,
         "description": "Disconnected C — only B reaches A", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "BFS Tree + Subtree Sum (Optimal)",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
            "description": (
                "BFS from `event`, building a parent map. For each city, walk back along parent pointers, "
                "accumulating that city's population on each edge it traverses. Equivalent to: each "
                "BFS-tree edge carries the sum of populations of cities in the subtree below it. Return "
                "max edge total."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "def max_traffic(cities, event):\n"
                    "    if event not in cities:\n"
                    "        return 0\n"
                    "    parent = {event: None}\n"
                    "    q = deque([event])\n"
                    "    while q:\n"
                    "        u = q.popleft()\n"
                    "        for v in cities[u]['neighbors']:\n"
                    "            if v not in parent:\n"
                    "                parent[v] = u\n"
                    "                q.append(v)\n"
                    "    # For each non-event city, accumulate its pop along its path back to event\n"
                    "    edge_total = {}\n"
                    "    for c in cities:\n"
                    "        if c == event or c not in parent:\n"
                    "            continue\n"
                    "        cur = c\n"
                    "        pop = cities[c]['pop']\n"
                    "        while parent[cur] is not None:\n"
                    "            edge = (cur, parent[cur]) if cur < parent[cur] else (parent[cur], cur)\n"
                    "            edge_total[edge] = edge_total.get(edge, 0) + pop\n"
                    "            cur = parent[cur]\n"
                    "    return max(edge_total.values()) if edge_total else 0"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise: 'shortest paths in unweighted graph' = BFS from event.",
        "2. BFS produces a tree of parent pointers. Every city other than event sends its population through that tree.",
        "3. Per-city: walk parent pointers, accumulating its population on each edge.",
        "4. Max edge total is the answer.",
        "5. Disconnected cities don't contribute — their populations don't reach the event.",
        "6. Edge cases: isolated event, two-city, linear chain, disconnected graph.",
    ],
    "tips": [
        "Walk-each-city is O(V · path_length). For star graphs that's fine; for linear ones it's O(V²). Subtree-sum DFS is O(V + E).",
        "Multiple shortest paths: the problem usually wants you to PICK ONE per city (deterministically). Lock this with the interviewer.",
        "Common follow-up: 'people travel along ALL shortest paths, splitting equally.' Now edge weights become fractional sums — adapt.",
        "Common follow-up: 'minimise max edge load by routing some traffic the long way.' That's a flow problem.",
        "Common follow-up: 'multiple events.' Run multi-source BFS or sum independent BFSes.",
    ],
    "companies": ["Amazon", "Uber"],
    "topics": ["Graph", "BFS", "Shortest Path"],
    "time_complexity": "O(V + E)",
    "space_complexity": "O(V)",
}


def REFERENCE(cities, event):
    from collections import deque
    if event not in cities:
        return 0
    parent = {event: None}
    q = deque([event])
    while q:
        u = q.popleft()
        for v in cities[u]["neighbors"]:
            if v not in parent:
                parent[v] = u
                q.append(v)
    edge_total = {}
    for c in cities:
        if c == event or c not in parent:
            continue
        cur = c
        pop = cities[c]["pop"]
        while parent[cur] is not None:
            edge = (cur, parent[cur]) if cur < parent[cur] else (parent[cur], cur)
            edge_total[edge] = edge_total.get(edge, 0) + pop
            cur = parent[cur]
    return max(edge_total.values()) if edge_total else 0


register(PAYLOAD, REFERENCE)
