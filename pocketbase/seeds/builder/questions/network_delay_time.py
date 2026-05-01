"""Network Delay Time — Medium. Single-Source Shortest Path (Dijkstra).

The canonical Dijkstra interview problem dressed as a 'signal propagation'
narrative. The trick: the answer isn't a single shortest path — it's the
*maximum* of all shortest paths from the source, because the signal must
reach every node. Bellman-Ford works too (and would be required if weights
could be negative), but with non-negative weights Dijkstra wins on time.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Network Delay Time",
    "difficulty": "Medium",
    "description": (
        "You are given a network of `n` nodes labeled from `1` to `n`. You are also given `times`, "
        "a list of travel times as directed edges `times[i] = [u_i, v_i, w_i]`, where `u_i` is the "
        "source node, `v_i` is the target node, and `w_i` is the time it takes for a signal to "
        "travel from source to target.\n\n"
        "We will send a signal from a given node `k`. Return the **minimum time** it takes for all "
        "the `n` nodes to receive the signal. If it is impossible for all the `n` nodes to receive "
        "the signal, return `-1`.\n\n"
        "**Example 1:**\n"
        "- Input: `times = [[2,1,1],[2,3,1],[3,4,1]]`, `n = 4`, `k = 2`\n"
        "- Output: `2`\n"
        "- Explanation: From node 2, distances are: 2→1 (1), 2→3 (1), 2→3→4 (2). The slowest "
        "node to receive the signal is node 4 at time 2.\n\n"
        "**Example 2:**\n"
        "- Input: `times = [[1,2,1]]`, `n = 2`, `k = 2`\n"
        "- Output: `-1`\n"
        "- Explanation: Node 1 is unreachable from node 2 (the only edge points the wrong way)."
    ),
    "hints": [
        "This is single-source shortest path on a weighted directed graph. The answer is "
        "`max(dist[i] for i in 1..n)` — the time the *last* node receives the signal.",
        "Weights are non-negative, so Dijkstra's algorithm applies. Use a min-heap keyed on "
        "(distance, node); always expand the closest unfinalised node first.",
        "Build an adjacency list from `times` once: `adj[u] = [(v, w), ...]`. Don't rescan the "
        "edge list on every relaxation — that's the O(V·E) Bellman-Ford regression.",
        "If any node's distance remains infinity after Dijkstra terminates, that node is "
        "unreachable from `k` → return -1.",
        "If weights *could* be negative, Dijkstra breaks (a closer node might be reached via a "
        "longer-but-cheaper detour later). Bellman-Ford O(V·E) is the correct fallback. Not "
        "needed here, but worth naming aloud — interviewers love the comparison.",
    ],
    "constraints": [
        "1 <= n <= 100",
        "1 <= times.length <= 6000",
        "0 <= w_i <= 100 (weights are non-negative)",
    ],
    "starter_code": {
        "python": "def network_delay_time(times, n, k):\n    # Your code here\n    pass",
        "javascript": "function networkDelayTime(times, n, k) {\n    // Your code here\n}",
        "java": "public int networkDelayTime(int[][] times, int n, int k) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        ([[2,1,1],[2,3,1],[3,4,1]], 4, 2),\n"
            "        ([[1,2,1]], 2, 2),\n"
            "        ([], 1, 1),\n"
            "    ]\n"
            "    for times, n, k in cases:\n"
            "        print(f\"network_delay_time({times}, {n}, {k}) = {network_delay_time(times, n, k)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\n"
            "    [[[2,1,1],[2,3,1],[3,4,1]], 4, 2],\n"
            "    [[[1,2,1]], 2, 2],\n"
            "].forEach(([times, n, k]) =>\n"
            "    console.log(`networkDelayTime =`, networkDelayTime(times, n, k))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] times = {{2,1,1},{2,3,1},{3,4,1}};\n"
            "        System.out.println(s.networkDelayTime(times, 4, 2));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"times": [[2, 1, 1], [2, 3, 1], [3, 4, 1]], "n": 4, "k": 2}, "expected": 2,
         "description": "Classic LC example — branch + chain, last node arrives at time 2",
         "tags": ["basic"]},
        {"input": {"times": [[1, 2, 1]], "n": 2, "k": 2}, "expected": -1,
         "description": "Edge points the wrong way — node 1 unreachable from k=2",
         "tags": ["edge", "unreachable"]},
        {"input": {"times": [], "n": 1, "k": 1}, "expected": 0,
         "description": "Single node, no edges — source already has the signal at time 0",
         "tags": ["edge"]},
        {"input": {"times": [[1, 2, 5]], "n": 2, "k": 1}, "expected": 5,
         "description": "Two nodes, one edge — answer is the edge weight",
         "tags": ["basic"]},
        {"input": {"times": [[1, 2, 1], [2, 3, 1], [3, 4, 1], [4, 5, 1]], "n": 5, "k": 1},
         "expected": 4,
         "description": "Linear chain of 5 — slowest node is the tail at distance 4",
         "tags": ["basic"]},
        {"input": {"times": [[1, 2, 3], [1, 3, 3], [1, 4, 3], [1, 5, 3]], "n": 5, "k": 1},
         "expected": 3,
         "description": "Star graph — every leaf reached in one hop of weight 3",
         "tags": ["basic"]},
        {"input": {"times": [[1, 2, 10], [1, 3, 1], [3, 2, 2]], "n": 3, "k": 1}, "expected": 3,
         "description": "Multi-edge — direct (10) loses to indirect (1+2=3); Dijkstra must relax",
         "tags": ["tricky"]},
        {"input": {"times": [[1, 2, 1], [2, 3, 1], [3, 1, 1], [1, 4, 5]], "n": 4, "k": 1},
         "expected": 5,
         "description": "Cycle 1→2→3→1 plus dangling edge to 4 — cycle must not loop forever",
         "tags": ["tricky", "cycle"]},
        {"input": {"times": [[1, 2, 1], [3, 4, 1]], "n": 4, "k": 1}, "expected": -1,
         "description": "Disconnected graph — nodes 3 and 4 unreachable from k=1",
         "tags": ["edge", "unreachable"]},
        {"input": {"times": [[1, 2, 0], [2, 3, 0]], "n": 3, "k": 1}, "expected": 0,
         "description": "Zero-weight edges — instantaneous propagation, answer is 0",
         "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Dijkstra with Min-Heap (Optimal)",
            "time_complexity": "O((V + E) log V)",
            "space_complexity": "O(V + E)",
            "description": (
                "Build an adjacency list. Maintain `dist[i] = shortest known distance from k to i`, "
                "initialised to infinity except `dist[k] = 0`. Push `(0, k)` onto a min-heap. "
                "Repeatedly pop the closest unfinalised node, skip if its popped distance is stale, "
                "otherwise relax all outgoing edges and push improved neighbours. After the heap "
                "drains, the answer is `max(dist)` — or -1 if any entry is still infinity."
            ),
            "code": {
                "python": (
                    "import heapq\n"
                    "from collections import defaultdict\n"
                    "\n"
                    "def network_delay_time(times, n, k):\n"
                    "    adj = defaultdict(list)\n"
                    "    for u, v, w in times:\n"
                    "        adj[u].append((v, w))\n"
                    "    dist = {i: float('inf') for i in range(1, n + 1)}\n"
                    "    dist[k] = 0\n"
                    "    heap = [(0, k)]\n"
                    "    while heap:\n"
                    "        d, u = heapq.heappop(heap)\n"
                    "        if d > dist[u]:\n"
                    "            continue\n"
                    "        for v, w in adj[u]:\n"
                    "            nd = d + w\n"
                    "            if nd < dist[v]:\n"
                    "                dist[v] = nd\n"
                    "                heapq.heappush(heap, (nd, v))\n"
                    "    ans = max(dist.values())\n"
                    "    return -1 if ans == float('inf') else ans"
                ),
                "javascript": (
                    "function networkDelayTime(times, n, k) {\n"
                    "    const adj = new Map();\n"
                    "    for (const [u, v, w] of times) {\n"
                    "        if (!adj.has(u)) adj.set(u, []);\n"
                    "        adj.get(u).push([v, w]);\n"
                    "    }\n"
                    "    const dist = new Array(n + 1).fill(Infinity);\n"
                    "    dist[k] = 0;\n"
                    "    // Simple heap via sorted array (fine for n <= 100)\n"
                    "    const heap = [[0, k]];\n"
                    "    while (heap.length) {\n"
                    "        heap.sort((a, b) => a[0] - b[0]);\n"
                    "        const [d, u] = heap.shift();\n"
                    "        if (d > dist[u]) continue;\n"
                    "        for (const [v, w] of (adj.get(u) || [])) {\n"
                    "            const nd = d + w;\n"
                    "            if (nd < dist[v]) {\n"
                    "                dist[v] = nd;\n"
                    "                heap.push([nd, v]);\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    let ans = 0;\n"
                    "    for (let i = 1; i <= n; i++) ans = Math.max(ans, dist[i]);\n"
                    "    return ans === Infinity ? -1 : ans;\n"
                    "}"
                ),
                "java": (
                    "import java.util.*;\n"
                    "\n"
                    "public int networkDelayTime(int[][] times, int n, int k) {\n"
                    "    Map<Integer, List<int[]>> adj = new HashMap<>();\n"
                    "    for (int[] t : times) {\n"
                    "        adj.computeIfAbsent(t[0], x -> new ArrayList<>()).add(new int[]{t[1], t[2]});\n"
                    "    }\n"
                    "    int[] dist = new int[n + 1];\n"
                    "    Arrays.fill(dist, Integer.MAX_VALUE);\n"
                    "    dist[k] = 0;\n"
                    "    PriorityQueue<int[]> heap = new PriorityQueue<>((a, b) -> a[0] - b[0]);\n"
                    "    heap.offer(new int[]{0, k});\n"
                    "    while (!heap.isEmpty()) {\n"
                    "        int[] cur = heap.poll();\n"
                    "        int d = cur[0], u = cur[1];\n"
                    "        if (d > dist[u]) continue;\n"
                    "        for (int[] e : adj.getOrDefault(u, Collections.emptyList())) {\n"
                    "            int v = e[0], w = e[1];\n"
                    "            if (d + w < dist[v]) {\n"
                    "                dist[v] = d + w;\n"
                    "                heap.offer(new int[]{dist[v], v});\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    int ans = 0;\n"
                    "    for (int i = 1; i <= n; i++) {\n"
                    "        if (dist[i] == Integer.MAX_VALUE) return -1;\n"
                    "        ans = Math.max(ans, dist[i]);\n"
                    "    }\n"
                    "    return ans;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Bellman-Ford (Contrast)",
            "time_complexity": "O(V * E)",
            "space_complexity": "O(V)",
            "description": (
                "Relax every edge V-1 times. Slower than Dijkstra here (no heap, no priority), but "
                "this is the algorithm you'd switch to if weights could be negative. Worth knowing "
                "because the interviewer's follow-up is often 'what if some edges are negative?' — "
                "and the answer is Bellman-Ford (with one more pass to detect negative cycles)."
            ),
            "code": {
                "python": (
                    "def network_delay_time(times, n, k):\n"
                    "    dist = [float('inf')] * (n + 1)\n"
                    "    dist[k] = 0\n"
                    "    for _ in range(n - 1):\n"
                    "        updated = False\n"
                    "        for u, v, w in times:\n"
                    "            if dist[u] + w < dist[v]:\n"
                    "                dist[v] = dist[u] + w\n"
                    "                updated = True\n"
                    "        if not updated:\n"
                    "            break\n"
                    "    ans = max(dist[1:])\n"
                    "    return -1 if ans == float('inf') else ans"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: directed graph, non-negative weights, single source, want shortest "
        "distance to *every* node. That's textbook Dijkstra.",
        "2. Reframe the answer: the signal reaches each node at its shortest-path distance from k. "
        "All nodes have received the signal once the slowest node receives it → answer = max(dist).",
        "3. Build adjacency list once (O(E)). Don't iterate `times` per relaxation.",
        "4. Min-heap discipline: pop, check `if d > dist[u]: continue` to skip stale entries (lazy "
        "deletion). Relax outgoing edges, push improved neighbours.",
        "5. Termination: heap drains. Walk dist[1..n] — if any is infinity, return -1; else return max.",
        "6. Follow-up readiness: if weights could be negative, switch to Bellman-Ford O(V·E) and "
        "add a Vth pass to detect negative cycles.",
    ],
    "tips": [
        "Use 1-indexed `dist` to match the problem's 1..n labelling — saves a pile of off-by-one bugs.",
        "Lazy deletion (skip stale heap entries with `if d > dist[u]: continue`) is simpler than "
        "decrease-key and equally correct for Dijkstra.",
        "Don't forget `dist[k] = 0` — the source receives the signal at time 0, not infinity.",
        "Zero-weight edges are legal and don't break Dijkstra. Negative weights would.",
        "If the interviewer asks about Floyd-Warshall: that's O(V³) all-pairs shortest path — "
        "overkill here (we only need single-source) but the right tool if you needed every pair.",
        "SPFA (Shortest Path Faster Algorithm) is a queue-based Bellman-Ford optimisation — "
        "name-drop only if you've actually implemented it; otherwise Dijkstra + Bellman-Ford covers it.",
    ],
    "companies": ["Amazon", "Google", "Facebook", "Uber", "LinkedIn", "Bloomberg"],
    "topics": ["Graph", "Shortest Path", "Dijkstra", "Heap (Priority Queue)", "Bellman-Ford"],
    "time_complexity": "O((V + E) log V)",
    "space_complexity": "O(V + E)",
}


def REFERENCE(times, n, k):
    import heapq
    from collections import defaultdict
    adj = defaultdict(list)
    for u, v, w in times:
        adj[u].append((v, w))
    dist = {i: float('inf') for i in range(1, n + 1)}
    dist[k] = 0
    heap = [(0, k)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    ans = max(dist.values())
    return -1 if ans == float('inf') else ans


register(PAYLOAD, REFERENCE)
