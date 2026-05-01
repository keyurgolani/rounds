"""Clone Graph — Medium. Graph / DFS / BFS / HashMap.

The canonical 'deep copy with cycles' question. The trap is the cycle:
a naive recursive copy on a graph with a cycle blows the stack. The
fix — a `visited`/`old_to_new` dictionary that maps each original node
to its already-cloned counterpart — is the same trick that powers
'Copy List with Random Pointer' (LC 138). DFS or BFS, doesn't matter,
as long as you clone the node *first* and *then* recurse for neighbours.
"""
from builder.registry import register
from collections import deque


PAYLOAD = {
    "title": "Clone Graph",
    "difficulty": "Medium",
    "description": (
        "Given a reference of a node in a **connected** undirected graph, return a **deep copy** (clone) of "
        "the graph.\n\n"
        "Each node in the graph contains a value (`int`) and a list (`List[Node]`) of its neighbors.\n\n"
        "**Test format (this judge):** the graph is provided as an **adjacency list**: "
        "`adjList[i]` is the list of neighbors of the node with value `i + 1` (nodes are 1-indexed). "
        "Your function takes the adjacency list of the input graph and returns the adjacency list of the "
        "**cloned** graph. For a correct deep copy, the returned adjacency list equals the input.\n\n"
        "**Example 1:**\n"
        "- Input: `adjList = [[2,4],[1,3],[2,4],[1,3]]`\n"
        "- Output: `[[2,4],[1,3],[2,4],[1,3]]`\n"
        "- Explanation: A 4-cycle. Node 1's neighbors are 2 and 4. Node 2's are 1 and 3. Etc.\n\n"
        "**Example 2:**\n"
        "- Input: `adjList = [[]]`\n"
        "- Output: `[[]]`\n"
        "- Explanation: A single node with no neighbors.\n\n"
        "**Example 3:**\n"
        "- Input: `adjList = []`\n"
        "- Output: `[]`\n"
        "- Explanation: The empty graph — no node passed in."
    ),
    "hints": [
        "The graph has cycles. A naive recursive clone (`clone(node) = Node(node.val, [clone(n) for n in "
        "node.neighbors])`) recurses forever.",
        "Break the cycle with a hash map: `old_to_new[original_node] = cloned_node`. Before recursing into a "
        "neighbor, check the map — if the neighbor is already cloned, reuse it.",
        "Critical ordering: create the clone and put it in the map *first*, then walk the neighbors. If you "
        "recurse first, you'll re-enter the same node before its entry exists and loop forever.",
        "DFS (recursion or explicit stack) and BFS (queue) both work. BFS uses an explicit queue and avoids "
        "Python's recursion limit on long chains; DFS reads more naturally.",
        "Both approaches run in O(V + E): each node is created once and each edge is walked twice (once from "
        "each endpoint). Auxiliary space is O(V) for the map.",
    ],
    "constraints": [
        "The number of nodes in the graph is in the range [0, 100].",
        "1 <= Node.val <= 100. Values are unique — `Node.val == 1, 2, ..., n`.",
        "The graph is connected and undirected; there are no self-loops or repeated edges.",
    ],
    "starter_code": {
        "python": (
            "# Definition for a Node.\n"
            "# class Node:\n"
            "#     def __init__(self, val=0, neighbors=None):\n"
            "#         self.val = val\n"
            "#         self.neighbors = neighbors if neighbors is not None else []\n"
            "\n"
            "def clone_graph(adj_list):\n"
            "    # Build the input graph from adj_list, deep-copy it,\n"
            "    # then return the adjacency list of the clone.\n"
            "    # Your code here\n"
            "    pass"
        ),
        "javascript": (
            "// Definition for a Node.\n"
            "// function Node(val, neighbors) {\n"
            "//     this.val = val === undefined ? 0 : val;\n"
            "//     this.neighbors = neighbors === undefined ? [] : neighbors;\n"
            "// }\n"
            "\n"
            "function cloneGraph(adjList) {\n"
            "    // Your code here\n"
            "}"
        ),
        "java": (
            "// Definition for a Node.\n"
            "// class Node {\n"
            "//     public int val;\n"
            "//     public List<Node> neighbors;\n"
            "//     public Node(int _val) { val = _val; neighbors = new ArrayList<>(); }\n"
            "// }\n"
            "\n"
            "public List<List<Integer>> cloneGraph(List<List<Integer>> adjList) {\n"
            "    // Your code here\n"
            "    return new ArrayList<>();\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[[2,4],[1,3],[2,4],[1,3]], [[]], []]\n"
            "    for adj in cases:\n"
            "        print(f\"clone_graph({adj}) = {clone_graph(adj)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[2,4],[1,3],[2,4],[1,3]], [[]], []].forEach(adj =>\n"
            "    console.log(`cloneGraph =`, cloneGraph(adj))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.*;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        List<List<Integer>> adj = Arrays.asList(\n"
            "            Arrays.asList(2,4), Arrays.asList(1,3),\n"
            "            Arrays.asList(2,4), Arrays.asList(1,3)\n"
            "        );\n"
            "        System.out.println(s.cloneGraph(adj));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"adj_list": []}, "expected": [],
         "description": "Empty graph — no node to clone", "tags": ["edge"]},
        {"input": {"adj_list": [[]]}, "expected": [[]],
         "description": "Single node, no neighbors", "tags": ["edge"]},
        {"input": {"adj_list": [[2], [1]]}, "expected": [[2], [1]],
         "description": "Two nodes connected by a single edge", "tags": ["basic"]},
        {"input": {"adj_list": [[2, 4], [1, 3], [2, 4], [1, 3]]},
         "expected": [[2, 4], [1, 3], [2, 4], [1, 3]],
         "description": "Classic LC example — 4-cycle", "tags": ["basic"]},
        {"input": {"adj_list": [[2, 3, 4, 5], [1], [1], [1], [1]]},
         "expected": [[2, 3, 4, 5], [1], [1], [1], [1]],
         "description": "Star graph — node 1 in the center, 4 leaves", "tags": ["basic"]},
        {"input": {"adj_list": [[2], [1, 3], [2, 4], [3, 5], [4]]},
         "expected": [[2], [1, 3], [2, 4], [3, 5], [4]],
         "description": "Chain (path graph) of 5 nodes", "tags": ["tricky"]},
        {"input": {"adj_list": [[2, 3, 4], [1, 3, 4], [1, 2, 4], [1, 2, 3]]},
         "expected": [[2, 3, 4], [1, 3, 4], [1, 2, 4], [1, 2, 3]],
         "description": "Fully connected K4 — every pair adjacent", "tags": ["tricky"]},
        {"input": {"adj_list": [[4, 5, 6], [4, 5, 6], [4, 5, 6], [1, 2, 3], [1, 2, 3], [1, 2, 3]]},
         "expected": [[4, 5, 6], [4, 5, 6], [4, 5, 6], [1, 2, 3], [1, 2, 3], [1, 2, 3]],
         "description": "Complete bipartite K3,3", "tags": ["tricky"]},
        {"input": {"adj_list": [[2], [1, 3], [2]]}, "expected": [[2], [1, 3], [2]],
         "description": "Three-node path — minimal branching chain", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "DFS Recursion with HashMap (Optimal)",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
            "description": (
                "Maintain `old_to_new`: a map from original node → cloned node. To clone a node: if it's "
                "already in the map, return the stored clone (this breaks cycles). Otherwise, create the "
                "clone, store it in the map *immediately*, then recursively clone each neighbor and append "
                "the result to the clone's neighbor list. The 'create-and-store-first' ordering is what "
                "makes the recursion terminate."
            ),
            "code": {
                "python": (
                    "class Node:\n"
                    "    def __init__(self, val=0, neighbors=None):\n"
                    "        self.val = val\n"
                    "        self.neighbors = neighbors if neighbors is not None else []\n"
                    "\n"
                    "def clone_graph_node(node):\n"
                    "    if node is None:\n"
                    "        return None\n"
                    "    old_to_new = {}\n"
                    "\n"
                    "    def dfs(n):\n"
                    "        if n in old_to_new:\n"
                    "            return old_to_new[n]\n"
                    "        clone = Node(n.val)\n"
                    "        old_to_new[n] = clone           # store BEFORE recursing\n"
                    "        for nei in n.neighbors:\n"
                    "            clone.neighbors.append(dfs(nei))\n"
                    "        return clone\n"
                    "\n"
                    "    return dfs(node)"
                ),
                "javascript": (
                    "// class Node { constructor(val, neighbors) { this.val = val; this.neighbors = neighbors || []; } }\n"
                    "function cloneGraphNode(node) {\n"
                    "    if (!node) return null;\n"
                    "    const oldToNew = new Map();\n"
                    "    const dfs = (n) => {\n"
                    "        if (oldToNew.has(n)) return oldToNew.get(n);\n"
                    "        const clone = new Node(n.val, []);\n"
                    "        oldToNew.set(n, clone);\n"
                    "        for (const nei of n.neighbors) clone.neighbors.push(dfs(nei));\n"
                    "        return clone;\n"
                    "    };\n"
                    "    return dfs(node);\n"
                    "}"
                ),
                "java": (
                    "public Node cloneGraph(Node node) {\n"
                    "    if (node == null) return null;\n"
                    "    Map<Node, Node> oldToNew = new HashMap<>();\n"
                    "    return dfs(node, oldToNew);\n"
                    "}\n"
                    "private Node dfs(Node n, Map<Node, Node> map) {\n"
                    "    if (map.containsKey(n)) return map.get(n);\n"
                    "    Node clone = new Node(n.val);\n"
                    "    map.put(n, clone);              // store BEFORE recursing\n"
                    "    for (Node nei : n.neighbors) clone.neighbors.add(dfs(nei, map));\n"
                    "    return clone;\n"
                    "}"
                ),
            },
        },
        {
            "title": "BFS with HashMap (Iterative)",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
            "description": (
                "Same map, no recursion. Clone the start node, push the original onto a queue. While the "
                "queue is non-empty: pop an original `cur`; for each neighbor of `cur`, if it's not yet "
                "cloned, clone it, store it in the map, and enqueue it; then append the clone of the "
                "neighbor to `map[cur].neighbors`. Avoids Python's recursion limit on long chains and is "
                "the safer default in interview code."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "class Node:\n"
                    "    def __init__(self, val=0, neighbors=None):\n"
                    "        self.val = val\n"
                    "        self.neighbors = neighbors if neighbors is not None else []\n"
                    "\n"
                    "def clone_graph_node(node):\n"
                    "    if node is None:\n"
                    "        return None\n"
                    "    old_to_new = {node: Node(node.val)}\n"
                    "    q = deque([node])\n"
                    "    while q:\n"
                    "        cur = q.popleft()\n"
                    "        for nei in cur.neighbors:\n"
                    "            if nei not in old_to_new:\n"
                    "                old_to_new[nei] = Node(nei.val)\n"
                    "                q.append(nei)\n"
                    "            old_to_new[cur].neighbors.append(old_to_new[nei])\n"
                    "    return old_to_new[node]"
                ),
                "javascript": (
                    "function cloneGraphNode(node) {\n"
                    "    if (!node) return null;\n"
                    "    const map = new Map();\n"
                    "    map.set(node, new Node(node.val, []));\n"
                    "    const q = [node];\n"
                    "    while (q.length) {\n"
                    "        const cur = q.shift();\n"
                    "        for (const nei of cur.neighbors) {\n"
                    "            if (!map.has(nei)) {\n"
                    "                map.set(nei, new Node(nei.val, []));\n"
                    "                q.push(nei);\n"
                    "            }\n"
                    "            map.get(cur).neighbors.push(map.get(nei));\n"
                    "        }\n"
                    "    }\n"
                    "    return map.get(node);\n"
                    "}"
                ),
                "java": (
                    "public Node cloneGraph(Node node) {\n"
                    "    if (node == null) return null;\n"
                    "    Map<Node, Node> map = new HashMap<>();\n"
                    "    map.put(node, new Node(node.val));\n"
                    "    Deque<Node> q = new ArrayDeque<>();\n"
                    "    q.offer(node);\n"
                    "    while (!q.isEmpty()) {\n"
                    "        Node cur = q.poll();\n"
                    "        for (Node nei : cur.neighbors) {\n"
                    "            if (!map.containsKey(nei)) {\n"
                    "                map.put(nei, new Node(nei.val));\n"
                    "                q.offer(nei);\n"
                    "            }\n"
                    "            map.get(cur).neighbors.add(map.get(nei));\n"
                    "        }\n"
                    "    }\n"
                    "    return map.get(node);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the trap: cycles. A naive recursive clone (`Node(val, [clone(n) for n in neighbors])`) recurses forever on the smallest 2-node cycle.",
        "2. The fix is the standard 'deep copy with shared structure' trick: a hash map from original → clone. Same idea as 'Copy List with Random Pointer'.",
        "3. Ordering is the load-bearing detail: create the clone and store it in the map BEFORE walking neighbors. If you recurse first, you re-enter the same node before its map entry exists.",
        "4. DFS is the cleanest write-up; BFS avoids recursion-depth issues on long chains and is the safer choice on systems with low stack limits.",
        "5. Edge cases: null/empty graph (return null/None), single node with no neighbors (one map entry, no recursion), self-loops (problem rules them out, but if allowed: handled correctly because the map check fires before re-recursion).",
        "6. Complexity: each node is cloned once, each edge is walked twice (from each endpoint) → O(V + E). Map holds V entries → O(V) space.",
    ],
    "tips": [
        "Insert the clone into the map *before* recursing into neighbors. Forgetting this is the #1 way to write infinite-recursion code on this problem.",
        "On the LC harness the input arrives as an adjacency list and the output is checked the same way — but inside your function you're operating on real Node objects. Don't confuse the two representations.",
        "DFS vs BFS: same complexity, same correctness. Pick BFS when the graph might be a long chain (Python recursion limit ~1000) or when the interviewer asks for an iterative solution.",
        "Closely related: 'Copy List with Random Pointer' (LC 138) — same hash-map trick on a linked list with arbitrary back-references. Mention it if asked for variants.",
        "Variant — 'Clone Binary Tree with Random Pointer' (LC 1485) and 'Clone N-ary Tree' (LC 1490) reuse the exact pattern. The skill transfers; the data structure changes.",
        "If the interviewer says 'clone in O(1) extra space', they're hinting at the LC 138 interleave-and-split trick. That trick does NOT generalise to graphs — be ready to explain why.",
    ],
    "companies": ["Facebook", "Google", "Amazon", "Microsoft", "Bloomberg", "Uber"],
    "topics": ["Graph", "DFS", "BFS", "Hash Table"],
    "time_complexity": "O(V + E)",
    "space_complexity": "O(V)",
}


class _Node:
    __slots__ = ("val", "neighbors")

    def __init__(self, val):
        self.val = val
        self.neighbors = []


def REFERENCE(adj_list):
    """Build a real Node graph from `adj_list`, deep-copy it via BFS+map,
    then serialise the clone back to an adjacency list. For a correct
    deep copy the returned list equals `adj_list`.
    """
    if not adj_list:
        return []

    n = len(adj_list)
    nodes = [_Node(i + 1) for i in range(n)]
    for i, nbrs in enumerate(adj_list):
        nodes[i].neighbors = [nodes[j - 1] for j in nbrs]

    start = nodes[0]
    old_to_new = {start: _Node(start.val)}
    q = deque([start])
    while q:
        cur = q.popleft()
        for nei in cur.neighbors:
            if nei not in old_to_new:
                old_to_new[nei] = _Node(nei.val)
                q.append(nei)
            old_to_new[cur].neighbors.append(old_to_new[nei])

    cloned_by_val = {clone.val: clone for clone in old_to_new.values()}
    result = []
    for i in range(1, n + 1):
        clone = cloned_by_val[i]
        result.append([nei.val for nei in clone.neighbors])
    return result


register(PAYLOAD, REFERENCE)
