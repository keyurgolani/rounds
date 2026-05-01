"""Package Manager — Medium. Topological Sort.

Install packages in dependency order. Toposort the DAG; detect cycles.
The L&M signal is the interface — `Installer` plugin point is what
real package managers (apt, brew, pip) all factor."""
from builder.registry import register


PAYLOAD = {
    "title": "Package Manager Install Order",
    "difficulty": "Medium",
    "description": (
        "Given a map of packages to their direct dependencies and a target package, return a list of "
        "packages in installation order — every dependency must appear before any package that requires "
        "it. The target package is the LAST entry. If a cycle exists in the dependency graph, return an "
        "empty list.\n\n"
        "**Example:**\n"
        "```\n"
        "deps = {\n"
        "  'A': ['B', 'C'],\n"
        "  'B': ['D', 'E', 'F'],\n"
        "  'C': ['F'],\n"
        "  'F': ['G'],\n"
        "  'D': [], 'E': [], 'G': []\n"
        "}\n"
        "install_order(deps, 'A')\n"
        "# One valid output: ['G', 'F', 'D', 'E', 'B', 'C', 'A']\n"
        "# Any topological order ending with 'A' is acceptable.\n"
        "```\n\n"
        "If a transitive dependency is missing from the map, treat it as an unsatisfiable requirement and "
        "return an empty list."
    ),
    "hints": [
        "DFS post-order: visit dependencies first, then the package itself. Append on exit. Reverse-postorder gives a valid install sequence.",
        "Cycle detection: use the colour trick (white/grey/black). A grey-on-grey hit signals a cycle.",
        "Track visited so the same dependency isn't installed twice (diamond dependency).",
        "Missing-package detection: a referenced dependency not in the map → return empty.",
        "Multiple valid orderings: pick any. Don't enumerate.",
        "Edge cases: target with no deps, missing target, self-cycle, two-cycle, diamond dependency.",
    ],
    "constraints": [
        "0 <= |deps| <= 10⁴",
    ],
    "starter_code": {
        "python": "def install_order(deps, target):\n    # Your code here\n    pass",
        "javascript": "function installOrder(deps, target) {\n    // Your code here\n}",
        "java": "public List<String> installOrder(Map<String, List<String>> deps, String target) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    deps = {'A':['B','C'],'B':['D','E','F'],'C':['F'],'F':['G'],'D':[],'E':[],'G':[]}\n"
            "    print(install_order(deps, 'A'))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"deps": {"A": ["B", "C"], "B": ["D", "E", "F"], "C": ["F"],
                             "F": ["G"], "D": [], "E": [], "G": []},
                    "target": "A"},
         "expected": {"$match": "validator",
                       "description": "Topological order ending with 'A'",
                       "code": "lambda inp, out: ("
                               "isinstance(out, list) and "
                               "len(out) > 0 and out[-1] == 'A' and "
                               "len(set(out)) == len(out) and "
                               "all("
                               "all(out.index(d) < out.index(p) for d in inp['deps'].get(p, []))"
                               " for p in out"
                               ")"
                               ")"},
         "description": "Standard 7-package DAG", "tags": ["basic"]},
        {"input": {"deps": {"A": []}, "target": "A"}, "expected": ["A"],
         "description": "Single package, no deps", "tags": ["edge"]},
        {"input": {"deps": {}, "target": "X"}, "expected": [],
         "description": "Target not in map", "tags": ["edge"]},
        {"input": {"deps": {"A": ["B"], "B": ["A"]}, "target": "A"}, "expected": [],
         "description": "Two-cycle", "tags": ["edge"]},
        {"input": {"deps": {"A": ["A"]}, "target": "A"}, "expected": [],
         "description": "Self-cycle", "tags": ["edge"]},
        {"input": {"deps": {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []},
                    "target": "A"},
         "expected": {"$match": "validator",
                       "description": "Diamond — D appears once, before B and C",
                       "code": "lambda inp, out: ("
                               "isinstance(out, list) and "
                               "out[-1] == 'A' and "
                               "len(out) == 4 and "
                               "len(set(out)) == 4 and "
                               "out.index('D') < out.index('B') and "
                               "out.index('D') < out.index('C')"
                               ")"},
         "description": "Diamond dependency — D installed once",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "DFS Post-Order with Cycle Detection (Optimal)",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
            "description": (
                "Three-colour DFS: white (unvisited), grey (in progress), black (done). On entry, mark "
                "grey; recurse; on exit, mark black and append. Grey-on-grey hit → cycle → return empty. "
                "Reverse the post-order at the end (or build it in the right order — DFS post-order is "
                "ALREADY a valid install order if you append on exit)."
            ),
            "code": {
                "python": (
                    "def install_order(deps, target):\n"
                    "    if target not in deps:\n"
                    "        return []\n"
                    "    WHITE, GREY, BLACK = 0, 1, 2\n"
                    "    color = {}\n"
                    "    order = []\n"
                    "    cycle = [False]\n"
                    "    def dfs(p):\n"
                    "        if cycle[0]: return\n"
                    "        c = color.get(p, WHITE)\n"
                    "        if c == GREY:\n"
                    "            cycle[0] = True; return\n"
                    "        if c == BLACK: return\n"
                    "        if p not in deps:\n"
                    "            cycle[0] = True; return\n"
                    "        color[p] = GREY\n"
                    "        for d in deps[p]:\n"
                    "            dfs(d)\n"
                    "            if cycle[0]: return\n"
                    "        color[p] = BLACK\n"
                    "        order.append(p)\n"
                    "    dfs(target)\n"
                    "    return [] if cycle[0] else order"
                ),
                "javascript": (
                    "function installOrder(deps, target) {\n"
                    "    if (!(target in deps)) return [];\n"
                    "    const color = new Map();\n"
                    "    const order = [];\n"
                    "    let cycle = false;\n"
                    "    const dfs = (p) => {\n"
                    "        if (cycle) return;\n"
                    "        const c = color.get(p) || 0;\n"
                    "        if (c === 1) { cycle = true; return; }\n"
                    "        if (c === 2) return;\n"
                    "        if (!(p in deps)) { cycle = true; return; }\n"
                    "        color.set(p, 1);\n"
                    "        for (const d of deps[p]) { dfs(d); if (cycle) return; }\n"
                    "        color.set(p, 2);\n"
                    "        order.push(p);\n"
                    "    };\n"
                    "    dfs(target);\n"
                    "    return cycle ? [] : order;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Kahn's BFS",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
            "description": (
                "Restrict the graph to packages reachable from `target`. Compute indegrees within that "
                "subgraph. Kahn's BFS: dequeue indegree-0 nodes, append to output, decrement neighbours. "
                "If output size != reachable size → cycle."
            ),
            "code": {
                "python": (
                    "def install_order(deps, target):\n"
                    "    if target not in deps:\n"
                    "        return []\n"
                    "    # Restrict to reachable from target\n"
                    "    reachable = set()\n"
                    "    stack = [target]\n"
                    "    while stack:\n"
                    "        p = stack.pop()\n"
                    "        if p in reachable: continue\n"
                    "        if p not in deps: return []\n"
                    "        reachable.add(p)\n"
                    "        for d in deps[p]:\n"
                    "            stack.append(d)\n"
                    "    indeg = {p: 0 for p in reachable}\n"
                    "    for p in reachable:\n"
                    "        for d in deps[p]:\n"
                    "            if d in reachable:\n"
                    "                indeg[d] += 1  # NOTE: dependency edges point FROM consumer TO provider\n"
                    "    # Reverse: we want to install providers first\n"
                    "    # Re-do with edges flipped: provider -> consumer\n"
                    "    indeg = {p: 0 for p in reachable}\n"
                    "    rev_adj = {p: [] for p in reachable}\n"
                    "    for p in reachable:\n"
                    "        for d in deps[p]:\n"
                    "            rev_adj[d].append(p)\n"
                    "            indeg[p] += 1\n"
                    "    from collections import deque\n"
                    "    q = deque([p for p in reachable if indeg[p] == 0])\n"
                    "    out = []\n"
                    "    while q:\n"
                    "        p = q.popleft()\n"
                    "        out.append(p)\n"
                    "        for c in rev_adj[p]:\n"
                    "            indeg[c] -= 1\n"
                    "            if indeg[c] == 0:\n"
                    "                q.append(c)\n"
                    "    return out if len(out) == len(reachable) else []"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise: 'install in dependency order' = topological sort of a DAG.",
        "2. DFS post-order is the cleanest: append nodes as they finish — natural reverse-topological order.",
        "3. Cycle detection with the three-colour trick. Don't skip this; missing it is the canonical L4 failure.",
        "4. Diamond dependencies (B and C both need D): visited set ensures D installs once.",
        "5. Missing dependencies: a ref outside the map → unsatisfiable → empty result. Pin this with the interviewer.",
        "6. Multiple valid orderings: any one is acceptable.",
        "7. Edge cases: target not in map, self-cycle, two-cycle, diamond, deep chain.",
    ],
    "tips": [
        "DFS naturally yields reverse-post-order — appending on exit gives a valid install sequence WITHOUT a final reverse.",
        "Don't toposort the whole graph if the target only depends on a subset. Walk only the reachable subset.",
        "Common follow-up: 'parallelise installation.' Group nodes by their level in the toposort; install each level concurrently.",
        "Common follow-up: 'version constraints.' Now it's SAT. Mention `pubgrub` (Dart's resolver) or backtracking SAT-style approaches.",
        "Common follow-up: 'plugin point for the actual install.' Pass an `Installer` interface; the orchestrator only handles ordering.",
    ],
    "companies": ["Amazon", "Microsoft", "Google"],
    "topics": ["Graph", "Topological Sort", "DFS"],
    "time_complexity": "O(V + E)",
    "space_complexity": "O(V)",
}


def REFERENCE(deps, target):
    if target not in deps:
        return []
    WHITE, GREY, BLACK = 0, 1, 2
    color = {}
    order = []
    cycle = [False]

    def dfs(p):
        if cycle[0]:
            return
        c = color.get(p, WHITE)
        if c == GREY:
            cycle[0] = True
            return
        if c == BLACK:
            return
        if p not in deps:
            cycle[0] = True
            return
        color[p] = GREY
        for d in deps[p]:
            dfs(d)
            if cycle[0]:
                return
        color[p] = BLACK
        order.append(p)

    dfs(target)
    return [] if cycle[0] else order


register(PAYLOAD, REFERENCE)
