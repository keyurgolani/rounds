"""Org Chart Total Reports — Easy/Medium. Trees / DFS / Memoisation.

Given an org chart as parent→[children] map, return total reports
(direct + indirect) for an employee. Recursive DFS is the obvious
answer; memoisation is the ladder up. DAGs (multi-parent) are the
senior follow-up."""
from builder.registry import register


PAYLOAD = {
    "title": "Org Chart — Total Reports",
    "difficulty": "Medium",
    "description": (
        "Given an organisation chart as a `manager → [direct reports]` adjacency map and an `employee` "
        "name, return the **total number of reports** (direct + indirect, all the way down the hierarchy) "
        "under that employee. The employee themselves is NOT included in the count.\n\n"
        "**Example:**\n"
        "```\n"
        "org = {\n"
        "  'CEO':   ['VP1', 'VP2'],\n"
        "  'VP1':   ['M1'],\n"
        "  'M1':    ['E1', 'E2'],\n"
        "  'VP2':   ['M2', 'M3'],\n"
        "  'M2':    [],\n"
        "  'M3':    ['E3']\n"
        "}\n"
        "total_reports(org, 'CEO') = 7\n"
        "total_reports(org, 'M1')  = 2\n"
        "total_reports(org, 'M2')  = 0\n"
        "```"
    ),
    "hints": [
        "Recursive DFS: count = sum(count(child) for child in directs) + len(directs).",
        "If the same employee is queried repeatedly, memoise — each subtree's total is invariant.",
        "The structure is a tree (one parent per employee) in the strict org-chart sense. If matrix-managed, it's a DAG — track visited to avoid double-counting.",
        "Iterative variant: BFS/DFS with a stack/queue, increment a counter per pop. Same complexity, no recursion.",
        "Edge cases: employee not in the map (return 0), employee with no reports (return 0), missing children (treat as no reports).",
    ],
    "constraints": [
        "0 <= |org| <= 10⁵ employees",
        "Each employee has 0 to 10³ direct reports",
    ],
    "starter_code": {
        "python": "def total_reports(org, employee):\n    # Your code here\n    pass",
        "javascript": "function totalReports(org, employee) {\n    // Your code here\n}",
        "java": "public int totalReports(Map<String, List<String>> org, String employee) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    org = {'CEO':['VP1','VP2'],'VP1':['M1'],'M1':['E1','E2'],'VP2':['M2','M3'],'M3':['E3']}\n"
            "    print(total_reports(org, 'CEO'))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"org": {"CEO": ["VP1", "VP2"], "VP1": ["M1"], "M1": ["E1", "E2"],
                            "VP2": ["M2", "M3"], "M3": ["E3"]},
                    "employee": "CEO"},
         "expected": 8,
         "description": "Full chart — 2 VPs + 3 managers + 3 ICs", "tags": ["basic"]},
        {"input": {"org": {"CEO": ["VP1", "VP2"], "VP1": ["M1"], "M1": ["E1", "E2"],
                            "VP2": ["M2", "M3"], "M3": ["E3"]},
                    "employee": "M1"},
         "expected": 2,
         "description": "Mid-level manager", "tags": ["basic"]},
        {"input": {"org": {"CEO": ["VP1", "VP2"], "VP1": ["M1"], "M1": ["E1", "E2"],
                            "VP2": ["M2", "M3"], "M3": ["E3"]},
                    "employee": "M2"},
         "expected": 0,
         "description": "Manager with no reports yet", "tags": ["edge"]},
        {"input": {"org": {"CEO": []}, "employee": "CEO"}, "expected": 0,
         "description": "Solo employee", "tags": ["edge"]},
        {"input": {"org": {}, "employee": "anyone"}, "expected": 0,
         "description": "Empty org", "tags": ["edge"]},
        {"input": {"org": {"A": ["B"], "B": ["C"], "C": ["D"], "D": []}, "employee": "A"},
         "expected": 3,
         "description": "Linear chain — 3 indirect reports", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Recursive DFS with Memoisation (Optimal)",
            "time_complexity": "O(V + E) per query, O(1) per query if memoised across calls",
            "space_complexity": "O(V) for memo + O(h) recursion",
            "description": (
                "DFS the subtree rooted at the employee. Sum the size of each child's subtree plus the "
                "child itself. Memoise per-employee so repeated queries on overlapping subtrees don't "
                "recompute."
            ),
            "code": {
                "python": (
                    "def total_reports(org, employee):\n"
                    "    memo = {}\n"
                    "    def go(name):\n"
                    "        if name in memo:\n"
                    "            return memo[name]\n"
                    "        directs = org.get(name, [])\n"
                    "        total = len(directs)\n"
                    "        for child in directs:\n"
                    "            total += go(child)\n"
                    "        memo[name] = total\n"
                    "        return total\n"
                    "    return go(employee) if employee in org else 0"
                ),
                "javascript": (
                    "function totalReports(org, employee) {\n"
                    "    if (!(employee in org)) return 0;\n"
                    "    const memo = new Map();\n"
                    "    const go = (name) => {\n"
                    "        if (memo.has(name)) return memo.get(name);\n"
                    "        const directs = org[name] || [];\n"
                    "        let total = directs.length;\n"
                    "        for (const c of directs) total += go(c);\n"
                    "        memo.set(name, total);\n"
                    "        return total;\n"
                    "    };\n"
                    "    return go(employee);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative BFS",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
            "description": (
                "Explicit queue. Pop, count direct reports, enqueue them. Counter at the end is the total. "
                "Useful when recursion depth is a concern (very deep org charts)."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "def total_reports(org, employee):\n"
                    "    if employee not in org:\n"
                    "        return 0\n"
                    "    q = deque(org.get(employee, []))\n"
                    "    count = 0\n"
                    "    while q:\n"
                    "        n = q.popleft()\n"
                    "        count += 1\n"
                    "        for c in org.get(n, []):\n"
                    "            q.append(c)\n"
                    "    return count"
                ),
            },
        },
        {
            "title": "DAG Variant (Multi-Parent / Matrix Org)",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)",
            "description": (
                "If an employee can have multiple managers (matrix org / dotted-line reporting), the chart "
                "becomes a DAG. Use a visited set to avoid double-counting employees reachable through "
                "multiple paths. Otherwise the algorithm is identical to the tree DFS."
            ),
            "code": {
                "python": (
                    "def total_reports(org, employee):\n"
                    "    visited = set()\n"
                    "    def go(name):\n"
                    "        for child in org.get(name, []):\n"
                    "            if child in visited:\n"
                    "                continue\n"
                    "            visited.add(child)\n"
                    "            go(child)\n"
                    "    go(employee)\n"
                    "    return len(visited)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise: walk the subtree, count nodes excluding the root.",
        "2. Recursive DFS is the natural shape: count(node) = len(directs) + sum(count(child) for child in directs).",
        "3. Memoise on employee — repeated queries don't recompute. Same memo can be reused across calls.",
        "4. If the chart is a DAG (matrix org), add a visited set to prevent double-counting.",
        "5. Iterative variant if the chart is very deep (recursion limit risk).",
        "6. Edge cases: employee not in map (return 0), no reports (return 0), empty org, linear chain.",
    ],
    "tips": [
        "Don't include the employee themselves in the count — this is a 'reports under me' query, not 'me + my org'.",
        "Memo invalidates on any chart mutation. If the org changes, drop the cache or use a versioned key.",
        "For the matrix-org follow-up, decide explicitly: are dotted-line reports counted? Confirm with the interviewer.",
        "Common follow-up: 'queries at scale.' Precompute the count for every employee in one DFS — O(V) total instead of O(V) per query.",
        "Common follow-up: 'common-level-N manager.' Track depth from root for each employee; pair-wise queries become 'find LCA at level N.'",
    ],
    "companies": ["Amazon", "LinkedIn", "Microsoft"],
    "topics": ["Tree", "DFS", "Memoisation", "Hash Table"],
    "time_complexity": "O(V + E)",
    "space_complexity": "O(V)",
}


def REFERENCE(org, employee):
    if employee not in org:
        return 0
    memo = {}

    def go(name):
        if name in memo:
            return memo[name]
        directs = org.get(name, [])
        total = len(directs)
        for child in directs:
            total += go(child)
        memo[name] = total
        return total

    return go(employee)


register(PAYLOAD, REFERENCE)
