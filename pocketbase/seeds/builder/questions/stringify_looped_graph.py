"""Stringify Looped Graph — Medium. Graph Traversal / Validation.

Walk a single-cycle graph and emit the traversal order as a string.
The senior signal is on the *follow-up*: the input is no longer
guaranteed to be a clean cycle — flag every malformed shape (degree ≠ 2,
disconnected components, branches, dangling leaves) and reject. The
key insight: a clean n-cycle is exactly an n-node graph where every
node has degree 2 and one DFS from any node visits every node before
returning to start."""
from builder.registry import register


PAYLOAD = {
    "title": "Stringify Looped Graph",
    "difficulty": "Medium",
    "description": (
        "Given an adjacency-list representation of an undirected graph, return a string formed by "
        "concatenating node labels in the order you encounter them while walking the cycle.\n\n"
        "**Input shape:** a dict like\n"
        "```\n"
        "{\n"
        "  \"A\": [\"B\", \"D\"],\n"
        "  \"B\": [\"C\", \"A\"],\n"
        "  \"C\": [\"D\", \"B\"],\n"
        "  \"D\": [\"A\", \"C\"]\n"
        "}\n"
        "```\n"
        "which represents the cycle\n"
        "```\n"
        "A - B\n"
        "|   |\n"
        "D - C\n"
        "```\n\n"
        "Start from the **first key in iteration order** of the input dict. At each step pick the "
        "neighbour you haven't just come from. Return the concatenation of node labels in visit order. "
        "For the example above, return `\"ABCD\"`.\n\n"
        "**Edge cases for the basic problem:**\n"
        "- Empty / `None` input → return `\"\"`.\n"
        "- One-node graph → return that single label.\n"
        "- Two-node graph (`A ↔ B`) → return both labels concatenated.\n\n"
        "**Follow-up — robustness:** drop the guarantee that the input is a clean cycle. The function "
        "must now also detect and reject malformed inputs: any node whose degree isn't exactly 2 (for "
        "graphs with 3+ nodes), graphs with disconnected components, branches, or dangling leaves. "
        "Return `None` for any malformed input."
    ),
    "hints": [
        "A clean n-cycle (n ≥ 3) is uniquely characterised by two facts: every node has degree 2, AND a single walk from any node visits every node before returning to the start. If either fails, it isn't a clean cycle.",
        "Three-state walk: track `prev`, `current`, `next`. At each step, `next = neighbour of current that isn't prev`. With degree exactly 2 this is unambiguous: pick whichever of the two neighbours isn't `prev`.",
        "First step is the only awkward one — you have no `prev` yet. Just pick either neighbour as the first step. The traversal direction is arbitrary so this is fine.",
        "Termination: the walk ends when `next == start`. Don't append the start node twice.",
        "For the validity follow-up: track the visited set. After the walk, if `len(visited) != len(graph)`, you have disconnected components or branches — reject. Combined with the per-node degree-2 check at every step, this catches every malformed shape.",
        "Don't forget the small-n edge cases (`n = 0, 1, 2`). They don't satisfy the degree-2 invariant trivially — handle them as special cases up front rather than letting the loop misbehave.",
        "Dict iteration order in Python 3.7+ is insertion-ordered. If the interviewer cares, ask whether they want canonical (lexicographic) ordering or insertion-order; the answer affects which valid rotation you return.",
    ],
    "constraints": [
        "0 <= number of nodes <= 26 (single-letter labels in tests, but solution should handle arbitrary string keys)",
        "Each node's neighbour list contains 0 to (n - 1) labels; no self-loops in test inputs.",
        "For VALID inputs: every node has degree 0 (single-node graph), 1 (two-node graph), or 2 (3+ node cycle).",
        "Labels are strings; they'd typically be single characters in interview discussion but assume arbitrary strings in code.",
    ],
    "starter_code": {
        "python": (
            "def stringify_looped_graph(graph):\n"
            "    # Your code here\n"
            "    pass"
        ),
        "javascript": (
            "function stringifyLoopedGraph(graph) {\n"
            "    // Your code here\n"
            "}"
        ),
        "java": (
            "public String stringifyLoopedGraph(java.util.Map<String, java.util.List<String>> graph) {\n"
            "    // Your code here\n"
            "    return \"\";\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(stringify_looped_graph({\n"
            "        \"A\": [\"B\", \"D\"], \"B\": [\"C\", \"A\"],\n"
            "        \"C\": [\"D\", \"B\"], \"D\": [\"A\", \"C\"]\n"
            "    }))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "console.log(stringifyLoopedGraph({\n"
            "    A: ['B', 'D'], B: ['C', 'A'], C: ['D', 'B'], D: ['A', 'C']\n"
            "}));"
        ),
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"graph": None},
         "expected": "",
         "description": "None input → empty string",
         "tags": ["edge"]},
        {"input": {"graph": {}},
         "expected": "",
         "description": "Empty graph → empty string",
         "tags": ["edge"]},
        {"input": {"graph": {"A": []}},
         "expected": "A",
         "description": "Single-node graph",
         "tags": ["edge"]},
        {"input": {"graph": {"A": ["B"], "B": ["A"]}},
         "expected": "AB",
         "description": "Two-node graph A↔B",
         "tags": ["basic"]},
        {"input": {"graph": {"A": ["B", "C"], "B": ["C", "A"], "C": ["A", "B"]}},
         "expected": "ABC",
         "description": "Triangle ABC — all three pairwise adjacent",
         "tags": ["basic"]},
        {"input": {"graph": {"A": ["B", "D"], "B": ["C", "A"], "C": ["D", "B"], "D": ["A", "C"]}},
         "expected": "ABCD",
         "description": "Square cycle — the canonical example",
         "tags": ["basic"]},
        {"input": {"graph": {
            "A": ["B", "I"], "B": ["C", "A"], "C": ["B", "D"], "D": ["E", "C"], "E": ["D", "F"],
            "F": ["E", "G"], "G": ["H", "F"], "H": ["I", "G"], "I": ["A", "H"]}},
         "expected": "ABCDEFGHI",
         "description": "Nine-node cycle traced by following neighbour[0] when not prev",
         "tags": ["basic"]},
        {"input": {"graph": {"A": ["B", "D"], "B": ["C", "A"], "C": ["B"], "D": ["A"]}},
         "expected": None,
         "description": "Invalid — degree-1 nodes (C and D) on a 4-node graph",
         "tags": ["edge"]},
        {"input": {"graph": {
            "A": ["B", "D"], "B": ["C", "A", "E"], "C": ["B", "D", "F"], "D": ["A", "C"],
            "E": ["B", "F"], "F": ["E", "C"]}},
         "expected": None,
         "description": "Invalid — B and C have degree 3 (the 'two squares glued' shape)",
         "tags": ["tricky"]},
        {"input": {"graph": {
            "A": ["B", "D"], "B": ["C", "A", "E"], "C": ["B", "D"], "D": ["A", "C"], "E": ["B"]}},
         "expected": None,
         "description": "Invalid — B has degree 3 plus a dangling leaf E",
         "tags": ["tricky"]},
        {"input": {"graph": {
            "A": ["B"], "B": ["A", "C"], "C": ["B", "D"], "D": ["C"]}},
         "expected": None,
         "description": "Invalid — open path (a chain, not a cycle)",
         "tags": ["edge"]},
        {"input": {"graph": {
            "A": ["B", "C"], "B": ["A", "C"], "C": ["A", "B"],
            "X": ["Y", "Z"], "Y": ["X", "Z"], "Z": ["X", "Y"]}},
         "expected": None,
         "description": "Invalid — two disconnected triangles (degrees fine, components wrong)",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Walk + Validate (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n) for the visited set + result buffer",
            "description": (
                "Three-state walk: keep `prev`, `current`, `next`. Start from the first dict key with "
                "`prev = None`. At each step, the next node is the neighbour of `current` that isn't "
                "`prev` — for a degree-2 node this is unique. Stop when `next == start`. Validate as "
                "we go (degree must be exactly 2 once we're past the trivial cases) and at the end "
                "(visited set must equal the full node set, otherwise components are missing). Trivial "
                "small-n cases (0, 1, 2 nodes) get short-circuited up front since they don't satisfy "
                "the degree-2 invariant."
            ),
            "code": {
                "python": (
                    "def stringify_looped_graph(graph):\n"
                    "    if not graph:\n"
                    "        return \"\"\n"
                    "    keys = list(graph.keys())\n"
                    "    n = len(keys)\n"
                    "    if n == 1:\n"
                    "        return keys[0]\n"
                    "    if n == 2:\n"
                    "        a, b = keys\n"
                    "        # Two-node 'cycle' is just A↔B; require mutual edge.\n"
                    "        if graph[a] != [b] and graph[a] != [b, b]: return None\n"
                    "        if graph[b] != [a] and graph[b] != [a, a]: return None\n"
                    "        return a + b\n"
                    "    \n"
                    "    start = keys[0]\n"
                    "    current = start\n"
                    "    prev = None\n"
                    "    result = []\n"
                    "    visited = set()\n"
                    "    \n"
                    "    while True:\n"
                    "        if current in visited:\n"
                    "            return None  # revisit before completion → branch / disconnect\n"
                    "        visited.add(current)\n"
                    "        result.append(current)\n"
                    "        conns = graph.get(current, [])\n"
                    "        if len(conns) != 2:\n"
                    "            return None\n"
                    "        nxt = conns[0] if conns[0] != prev else conns[1]\n"
                    "        if nxt not in graph:\n"
                    "            return None  # neighbour not in node set → malformed\n"
                    "        prev = current\n"
                    "        current = nxt\n"
                    "        if current == start:\n"
                    "            break\n"
                    "    \n"
                    "    if len(visited) != n:\n"
                    "        return None  # disconnected components\n"
                    "    return \"\".join(result)"
                ),
                "javascript": (
                    "function stringifyLoopedGraph(graph) {\n"
                    "    if (!graph) return '';\n"
                    "    const keys = Object.keys(graph);\n"
                    "    const n = keys.length;\n"
                    "    if (n === 0) return '';\n"
                    "    if (n === 1) return keys[0];\n"
                    "    if (n === 2) {\n"
                    "        const [a, b] = keys;\n"
                    "        if (!graph[a].includes(b) || !graph[b].includes(a)) return null;\n"
                    "        return a + b;\n"
                    "    }\n"
                    "    \n"
                    "    const start = keys[0];\n"
                    "    let current = start;\n"
                    "    let prev = null;\n"
                    "    const result = [];\n"
                    "    const visited = new Set();\n"
                    "    \n"
                    "    while (true) {\n"
                    "        if (visited.has(current)) return null;\n"
                    "        visited.add(current);\n"
                    "        result.push(current);\n"
                    "        const conns = graph[current] || [];\n"
                    "        if (conns.length !== 2) return null;\n"
                    "        const nxt = conns[0] !== prev ? conns[0] : conns[1];\n"
                    "        if (!(nxt in graph)) return null;\n"
                    "        prev = current;\n"
                    "        current = nxt;\n"
                    "        if (current === start) break;\n"
                    "    }\n"
                    "    \n"
                    "    if (visited.size !== n) return null;\n"
                    "    return result.join('');\n"
                    "}"
                ),
            },
        },
        {
            "title": "Validate-First, Walk-Second",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Some interviewers prefer a clean separation: a single pre-pass that checks every "
                "structural invariant, then a separate walk that's allowed to assume the input is "
                "well-formed. Pre-pass: every node has degree exactly 2 (for n ≥ 3); every neighbour "
                "is a known node; every edge is symmetric (`B in graph[A]` iff `A in graph[B]`). "
                "Then a single DFS validates connectivity. If both pass, the walk is just a clean "
                "linear traversal. Same complexity, slightly more readable; trades one extra pass "
                "for code that splits cleanly into 'parse' and 'process'."
            ),
            "code": {
                "python": (
                    "def stringify_looped_graph(graph):\n"
                    "    if not graph: return \"\"\n"
                    "    keys = list(graph.keys())\n"
                    "    n = len(keys)\n"
                    "    if n == 1: return keys[0]\n"
                    "    if n == 2:\n"
                    "        a, b = keys\n"
                    "        if b not in graph.get(a, []) or a not in graph.get(b, []): return None\n"
                    "        return a + b\n"
                    "    \n"
                    "    # Pre-pass: degree, known-neighbour, symmetry.\n"
                    "    for node, conns in graph.items():\n"
                    "        if len(conns) != 2:\n"
                    "            return None\n"
                    "        for nb in conns:\n"
                    "            if nb not in graph or node not in graph[nb]:\n"
                    "                return None\n"
                    "    \n"
                    "    # Walk — guaranteed safe by pre-pass.\n"
                    "    start = keys[0]\n"
                    "    prev, current = None, start\n"
                    "    result = []\n"
                    "    while True:\n"
                    "        result.append(current)\n"
                    "        conns = graph[current]\n"
                    "        nxt = conns[0] if conns[0] != prev else conns[1]\n"
                    "        prev, current = current, nxt\n"
                    "        if current == start:\n"
                    "            break\n"
                    "    \n"
                    "    if len(result) != n:\n"
                    "        return None  # multiple disjoint cycles\n"
                    "    return \"\".join(result)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate. Input is an adjacency list of an UNDIRECTED graph claimed to be a single cycle. Output is a string of node labels in walk order.",
        "2. Edge cases up front: empty/None → \"\". One node → that label. Two nodes → both labels (it's the only valid 2-cycle in this convention).",
        "3. Three-state walk for n ≥ 3: track `prev`, `current`, pick `next` = the neighbour that isn't `prev`. With degree exactly 2 this is unique; that's the whole reason the cycle is walkable in O(n).",
        "4. Termination: when `next == start`, stop. Don't include start twice.",
        "5. Follow-up flips this from 'walk a cycle' to 'detect that it isn't a cycle.' Check at every step that current has degree 2 and the next neighbour exists in the graph. Then check at the end that the visited set equals the full node set.",
        "6. The 'two glued cycles' test case (B and C have degree 3) is caught by the degree-2 check at the first step where we reach B or C.",
        "7. The 'disjoint two triangles' test case is the subtle one. Each node has degree 2, the walk completes, but only half the nodes are visited. Catch it with the visited-count check at the end.",
        "8. The chain-not-cycle case (`A-B-C-D`) catches via degree: A and D have degree 1, not 2. The very first step hitting A returns None.",
    ],
    "tips": [
        "Pick a starting node deterministically (first key in iteration order) so tests are reproducible. Otherwise valid traversals form an equivalence class of 2n rotations.",
        "Don't forget the n ≤ 2 cases. They're the off-by-one of this problem — the degree-2 invariant doesn't apply.",
        "The validity follow-up is what separates a pass from a strong pass. Walking is easy; rejecting malformed input correctly is the senior signal.",
        "Check symmetry of edges in the pre-pass version — `B in graph[A]` should imply `A in graph[B]`. The walk-and-validate version catches asymmetric edges incidentally (the walk steers off-cycle and triggers a degree check), but pre-pass makes it explicit.",
        "Common follow-up: 'now allow self-loops.' A node with `[X, X]` should be treated as having one logical neighbour. Decide whether to filter or special-case in the next-step rule.",
        "Common follow-up: 'now allow multiple cycles.' Run the walk-from-unvisited loop until visited covers the graph; concatenate cycles separated by a delimiter.",
        "Common follow-up: 'detect & describe — what shape is this if it's not a clean cycle?' Classify into branch / chain / disconnected / multi-cycle by counting degree-1, degree-3+, and connected component count.",
    ],
    "companies": ["Google", "Microsoft", "Bloomberg", "Amazon", "Meta"],
    "topics": ["Graph", "Hash Table", "DFS", "Validation"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
    "entry": {
        "kind": "function",
        "name": "stringify_looped_graph",
        "params": [
            {"name": "graph", "type": "dict"},
        ],
    },
}


def REFERENCE(graph):
    if not graph:
        return ""
    keys = list(graph.keys())
    n = len(keys)
    if n == 1:
        return keys[0]
    if n == 2:
        a, b = keys
        if b not in graph.get(a, []) or a not in graph.get(b, []):
            return None
        return a + b

    start = keys[0]
    current = start
    prev = None
    result = []
    visited = set()

    while True:
        if current in visited:
            return None
        visited.add(current)
        result.append(current)
        conns = graph.get(current, [])
        if len(conns) != 2:
            return None
        nxt = conns[0] if conns[0] != prev else conns[1]
        if nxt not in graph:
            return None
        prev = current
        current = nxt
        if current == start:
            break

    if len(visited) != n:
        return None
    return "".join(result)


register(PAYLOAD, REFERENCE)
