"""Cheapest Flights Within K Stops — Medium. Shortest Path with Constraints.

The 'shortest path with a hop budget' classic. The trap is reaching for
plain Dijkstra: it minimises cost but ignores stops, and a costlier path
with fewer stops can dominate a cheaper one that's already over budget.
The clean answer is Bellman-Ford with exactly k+1 relaxation rounds —
each round extends the frontier by one edge, so after k+1 rounds you've
considered every path with at most k+1 edges (= k stops). Modified
Dijkstra carrying (cost, stops) state also works and is often faster on
sparse graphs, but Bellman-Ford is the cleanest interview answer.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Cheapest Flights Within K Stops",
    "difficulty": "Medium",
    "description": (
        "There are `n` cities connected by some number of flights. You are given an array `flights` "
        "where `flights[i] = [u_i, v_i, price_i]` indicates that there is a flight from city `u_i` to "
        "city `v_i` with cost `price_i`.\n\n"
        "You are also given three integers `src`, `dst`, and `k`. Return **the cheapest price** from "
        "`src` to `dst` with **at most `k` stops**. If there is no such route, return `-1`.\n\n"
        "Note: 'k stops' means the path can use at most `k + 1` edges (a direct flight uses 0 stops).\n\n"
        "**Example 1:**\n"
        "- Input: `n = 3, flights = [[0,1,100],[1,2,100],[0,2,500]], src = 0, dst = 2, k = 1`\n"
        "- Output: `200`\n"
        "- Explanation: The cheapest path from 0 to 2 with at most 1 stop is 0 -> 1 -> 2 with cost 200. "
        "The direct flight 0 -> 2 costs 500.\n\n"
        "**Example 2:**\n"
        "- Input: `n = 3, flights = [[0,1,100],[1,2,100],[0,2,500]], src = 0, dst = 2, k = 0`\n"
        "- Output: `500`\n"
        "- Explanation: With 0 stops allowed, only the direct flight 0 -> 2 is valid (cost 500). The "
        "two-leg path uses 1 stop, which is over budget."
    ),
    "hints": [
        "'At most k stops' = 'at most k+1 edges'. Convert the budget once and never confuse stops with edges again.",
        "Bellman-Ford fits perfectly: run exactly k+1 relaxation rounds. Each round extends every reachable city by one more edge, so after k+1 rounds you've considered every ≤(k+1)-edge path. O(k·E) time.",
        "Critical Bellman-Ford detail: relax from a *snapshot* of the previous round's distances, not the live array. Otherwise one round can chain multiple edges and you'll undercount stops.",
        "Plain Dijkstra is wrong: a path may be cheaper but already over the stop budget, while a costlier path has stops to spare. Fix it by carrying `(cost, stops_used)` in the priority queue and only popping a state if it improves either dimension.",
        "BFS layered by edge-count also works: process the frontier k+1 times, relaxing all edges per layer. Same shape as Bellman-Ford, just framed as a graph traversal.",
    ],
    "constraints": [
        "1 <= n <= 100, 0 <= flights.length <= n*(n-1), 1 <= price_i <= 10⁴",
        "0 <= src, dst < n, src != dst, 0 <= k <= n-1",
        "There will not be any multiple flights between two cities (per LC; tests cover the multi-edge case anyway).",
    ],
    "starter_code": {
        "python": (
            "def find_cheapest_price(n, flights, src, dst, k):\n"
            "    # Your code here\n"
            "    pass"
        ),
        "javascript": (
            "function findCheapestPrice(n, flights, src, dst, k) {\n"
            "    // Your code here\n"
            "}"
        ),
        "java": (
            "public int findCheapestPrice(int n, int[][] flights, int src, int dst, int k) {\n"
            "    // Your code here\n"
            "    return -1;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        (3, [[0,1,100],[1,2,100],[0,2,500]], 0, 2, 1),\n"
            "        (3, [[0,1,100],[1,2,100],[0,2,500]], 0, 2, 0),\n"
            "    ]\n"
            "    for n, flights, src, dst, k in cases:\n"
            "        print(f\"find_cheapest_price = {find_cheapest_price(n, flights, src, dst, k)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\n"
            "    [3, [[0,1,100],[1,2,100],[0,2,500]], 0, 2, 1],\n"
            "    [3, [[0,1,100],[1,2,100],[0,2,500]], 0, 2, 0],\n"
            "].forEach(([n, flights, src, dst, k]) =>\n"
            "    console.log('findCheapestPrice =', findCheapestPrice(n, flights, src, dst, k))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] flights = {{0,1,100},{1,2,100},{0,2,500}};\n"
            "        System.out.println(s.findCheapestPrice(3, flights, 0, 2, 1));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"n": 3, "flights": [[0, 1, 100], [1, 2, 100], [0, 2, 500]],
                   "src": 0, "dst": 2, "k": 1},
         "expected": 200,
         "description": "Classic LC: 0->1->2 (200) beats direct 0->2 (500) when 1 stop allowed",
         "tags": ["basic"]},
        {"input": {"n": 3, "flights": [[0, 1, 100], [1, 2, 100], [0, 2, 500]],
                   "src": 0, "dst": 2, "k": 0},
         "expected": 500,
         "description": "k=0 forces the direct flight even though it's costlier",
         "tags": ["basic"]},
        {"input": {"n": 4, "flights": [[0, 1, 100], [1, 2, 100], [2, 3, 100]],
                   "src": 0, "dst": 3, "k": 1},
         "expected": -1,
         "description": "Unreachable within budget — needs 2 stops, only 1 allowed",
         "tags": ["edge"]},
        {"input": {"n": 3, "flights": [[0, 1, 100], [1, 2, 100]],
                   "src": 0, "dst": 0, "k": 5},
         "expected": 0,
         "description": "src == dst — zero cost, zero edges",
         "tags": ["edge"]},
        {"input": {"n": 2, "flights": [[0, 1, 42]],
                   "src": 0, "dst": 1, "k": 0},
         "expected": 42,
         "description": "Single direct flight with k=0",
         "tags": ["edge"]},
        {"input": {"n": 4, "flights": [[0, 1, 1], [1, 2, 1], [2, 0, 1], [2, 3, 100]],
                   "src": 0, "dst": 3, "k": 5},
         "expected": 102,
         "description": "Cycle in the graph — must not loop forever; answer is 0->1->2->3",
         "tags": ["tricky"]},
        {"input": {"n": 3, "flights": [[0, 1, 200], [0, 1, 50], [1, 2, 10]],
                   "src": 0, "dst": 2, "k": 1},
         "expected": 60,
         "description": "Multi-edge same src->dst — must pick the cheaper parallel edge",
         "tags": ["tricky"]},
        {"input": {"n": 5, "flights": [[0, 1, 5], [1, 2, 5], [0, 2, 100],
                                       [2, 3, 5], [3, 4, 5], [2, 4, 1]],
                   "src": 0, "dst": 4, "k": 2},
         "expected": 11,
         "description": "Two stops let you take 0->1->2->4 (11) instead of going via 3",
         "tags": ["tricky"]},
        {"input": {"n": 5, "flights": [[0, 1, 5], [1, 2, 5], [2, 3, 5],
                                       [3, 4, 5], [0, 4, 100]],
                   "src": 0, "dst": 4, "k": 2},
         "expected": 100,
         "description": "Cheap chain needs 3 stops; budget forces the 100-cost direct",
         "tags": ["tricky"]},
        {"input": {"n": 4, "flights": [[0, 1, 100], [1, 2, 100], [0, 2, 500],
                                       [0, 3, 1], [3, 2, 1]],
                   "src": 0, "dst": 2, "k": 1},
         "expected": 2,
         "description": "Better 2-edge path via city 3 — Dijkstra trap if it commits to 1->2 too early",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Bellman-Ford with k+1 Relaxation Rounds (Optimal)",
            "time_complexity": "O(k·E)",
            "space_complexity": "O(n)",
            "description": (
                "k stops = at most k+1 edges. Run Bellman-Ford for exactly k+1 rounds, each round "
                "relaxing every flight from a *snapshot* of the previous round's distances. The "
                "snapshot is critical — relaxing in place would let one round chain multiple edges "
                "and silently spend stops we don't have. After k+1 rounds, `dist[dst]` is the cheapest "
                "≤(k+1)-edge cost or infinity."
            ),
            "code": {
                "python": (
                    "def find_cheapest_price(n, flights, src, dst, k):\n"
                    "    INF = float('inf')\n"
                    "    dist = [INF] * n\n"
                    "    dist[src] = 0\n"
                    "    for _ in range(k + 1):\n"
                    "        snapshot = dist[:]\n"
                    "        for u, v, w in flights:\n"
                    "            if snapshot[u] + w < dist[v]:\n"
                    "                dist[v] = snapshot[u] + w\n"
                    "    return dist[dst] if dist[dst] != INF else -1"
                ),
                "javascript": (
                    "function findCheapestPrice(n, flights, src, dst, k) {\n"
                    "    const INF = Infinity;\n"
                    "    let dist = new Array(n).fill(INF);\n"
                    "    dist[src] = 0;\n"
                    "    for (let i = 0; i <= k; i++) {\n"
                    "        const snap = dist.slice();\n"
                    "        for (const [u, v, w] of flights) {\n"
                    "            if (snap[u] + w < dist[v]) dist[v] = snap[u] + w;\n"
                    "        }\n"
                    "    }\n"
                    "    return dist[dst] === INF ? -1 : dist[dst];\n"
                    "}"
                ),
                "java": (
                    "public int findCheapestPrice(int n, int[][] flights, int src, int dst, int k) {\n"
                    "    int INF = Integer.MAX_VALUE;\n"
                    "    int[] dist = new int[n];\n"
                    "    java.util.Arrays.fill(dist, INF);\n"
                    "    dist[src] = 0;\n"
                    "    for (int i = 0; i <= k; i++) {\n"
                    "        int[] snap = dist.clone();\n"
                    "        for (int[] f : flights) {\n"
                    "            int u = f[0], v = f[1], w = f[2];\n"
                    "            if (snap[u] != INF && snap[u] + w < dist[v]) dist[v] = snap[u] + w;\n"
                    "        }\n"
                    "    }\n"
                    "    return dist[dst] == INF ? -1 : dist[dst];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Modified Dijkstra (cost, stops) State",
            "time_complexity": "O(E·log(E))",
            "space_complexity": "O(n + E)",
            "description": (
                "Run Dijkstra but carry `(cost_so_far, node, edges_used)` in the priority queue. "
                "Pop the cheapest state first; the first time we pop `dst` we return its cost. Skip "
                "expanding a state whose `edges_used` already equals `k+1`. Crucially we do NOT keep "
                "a single `visited` set — the same node can re-enter the queue with fewer stops, and "
                "that variant might still produce the answer. Track `min_edges_to[node]` and only "
                "skip states that are dominated on both dimensions."
            ),
            "code": {
                "python": (
                    "def find_cheapest_price(n, flights, src, dst, k):\n"
                    "    import heapq\n"
                    "    graph = [[] for _ in range(n)]\n"
                    "    for u, v, w in flights:\n"
                    "        graph[u].append((v, w))\n"
                    "    # min edges used to reach a node so far; prune dominated states\n"
                    "    best_edges = [float('inf')] * n\n"
                    "    pq = [(0, src, 0)]  # (cost, node, edges_used)\n"
                    "    while pq:\n"
                    "        cost, u, edges = heapq.heappop(pq)\n"
                    "        if u == dst:\n"
                    "            return cost\n"
                    "        if edges >= best_edges[u] or edges > k:\n"
                    "            continue\n"
                    "        best_edges[u] = edges\n"
                    "        for v, w in graph[u]:\n"
                    "            heapq.heappush(pq, (cost + w, v, edges + 1))\n"
                    "    return -1"
                ),
                "javascript": (
                    "function findCheapestPrice(n, flights, src, dst, k) {\n"
                    "    const graph = Array.from({length: n}, () => []);\n"
                    "    for (const [u, v, w] of flights) graph[u].push([v, w]);\n"
                    "    const bestEdges = new Array(n).fill(Infinity);\n"
                    "    // Tiny binary heap\n"
                    "    const pq = [[0, src, 0]];\n"
                    "    const cmp = (a, b) => a[0] - b[0];\n"
                    "    while (pq.length) {\n"
                    "        pq.sort(cmp);\n"
                    "        const [cost, u, edges] = pq.shift();\n"
                    "        if (u === dst) return cost;\n"
                    "        if (edges >= bestEdges[u] || edges > k) continue;\n"
                    "        bestEdges[u] = edges;\n"
                    "        for (const [v, w] of graph[u]) pq.push([cost + w, v, edges + 1]);\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "BFS Layered by Edge Count",
            "time_complexity": "O(k·E)",
            "space_complexity": "O(n)",
            "description": (
                "Frame Bellman-Ford as a BFS: a frontier of (node, cost) pairs, advanced one edge per "
                "layer for k+1 layers. Each layer relaxes every flight from the previous layer's best "
                "cost. Mechanically identical to Bellman-Ford with snapshots — useful framing if the "
                "interviewer is expecting a 'graph traversal' answer rather than 'DP relaxation'."
            ),
            "code": {
                "python": (
                    "def find_cheapest_price(n, flights, src, dst, k):\n"
                    "    INF = float('inf')\n"
                    "    cost = [INF] * n\n"
                    "    cost[src] = 0\n"
                    "    for _ in range(k + 1):\n"
                    "        nxt = cost[:]\n"
                    "        for u, v, w in flights:\n"
                    "            if cost[u] + w < nxt[v]:\n"
                    "                nxt[v] = cost[u] + w\n"
                    "        cost = nxt\n"
                    "    return cost[dst] if cost[dst] != INF else -1"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Translate the budget: 'at most k stops' = 'at most k+1 edges'. Now the question is a path-length-bounded shortest path.",
        "2. Reach for plain Dijkstra and immediately notice the bug: cheaper-with-too-many-stops can shadow costlier-with-stops-to-spare. The classic counter-example is exactly the 5-edge case.",
        "3. Switch to Bellman-Ford: relax all edges k+1 times. After round r, `dist[v]` holds the cheapest cost to reach v using ≤r edges. Done.",
        "4. The snapshot detail: relax from `dist_prev`, write to `dist`. Without a snapshot, edges relaxed earlier in the same round bleed into later relaxations and you accidentally chain multiple edges per round.",
        "5. Modified Dijkstra is the alternative: state is (cost, node, edges_used). It's faster on sparse graphs because it terminates as soon as `dst` is popped, but the bookkeeping (no naive visited set, only skip states dominated on both axes) is the part that catches people in interviews.",
        "6. Edge cases: src == dst (return 0), no flights, unreachable within budget (return -1), cycles (Bellman-Ford handles them naturally — the snapshot prevents stop-count cheating).",
    ],
    "tips": [
        "If you write Bellman-Ford in place without a snapshot, the test 'cheap chain needs 3 stops; budget forces the 100-cost direct' will fail — your single round will silently traverse the whole chain.",
        "Don't stop the loop early when nothing relaxes — that's the unbounded-shortest-path optimisation, but you specifically need exactly k+1 rounds because more rounds can find more-edges paths that are cheaper but valid.",
        "For the Dijkstra variant, never use a plain `visited` set keyed only on node. The correct prune is: skip if `edges_used >= best_edges_seen_for_this_node`. Otherwise you discard valid lower-stop revisits.",
        "Common follow-up: 'k stops with edge weights summed' is the same problem. 'k stops minimising hop count' degenerates to BFS — drop the priority queue.",
        "Watch for integer overflow in Java if you sum costs naively before checking INF. Guard with `snap[u] != INF` before adding.",
        "Adjacency list helps Dijkstra (`O(E log E)`) but is unnecessary for Bellman-Ford — iterating the raw `flights` list each round is the cleanest code.",
    ],
    "companies": ["Amazon", "Google", "Meta", "Bloomberg", "Uber", "Apple"],
    "topics": ["Graph", "Dynamic Programming", "Shortest Path", "Bellman-Ford", "Dijkstra", "BFS"],
    "time_complexity": "O(k·E)",
    "space_complexity": "O(n)",
}


def REFERENCE(n, flights, src, dst, k):
    if src == dst:
        return 0
    INF = float('inf')
    dist = [INF] * n
    dist[src] = 0
    for _ in range(k + 1):
        snapshot = dist[:]
        for u, v, w in flights:
            if snapshot[u] != INF and snapshot[u] + w < dist[v]:
                dist[v] = snapshot[u] + w
    return dist[dst] if dist[dst] != INF else -1


register(PAYLOAD, REFERENCE)
