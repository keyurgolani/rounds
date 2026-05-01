"""Course Schedule — Medium. Cycle detection in a directed graph.

Classic 'can you topologically order the prerequisite graph?' question.
Build the directed graph (edge `b -> a` means 'b must precede a') and
ask whether it's a DAG. Two industry-standard ways to answer that:
Kahn's BFS (peel zero-in-degree nodes; if you peel all `n`, no cycle)
or DFS three-coloring (white/gray/black; a back-edge to a gray node
is a cycle). Either is O(V + E). The follow-up — Course Schedule II —
asks for the actual order, which Kahn gives you for free.
"""
from builder.registry import register
from collections import deque


PAYLOAD = {
    "title": "Course Schedule",
    "difficulty": "Medium",
    "description": (
        "There are `numCourses` courses you have to take, labeled from `0` to `numCourses - 1`. "
        "You are given an array `prerequisites` where `prerequisites[i] = [a, b]` indicates that you "
        "**must take course `b` first** if you want to take course `a`.\n\n"
        "Return `true` if you can finish all courses. Otherwise, return `false`.\n\n"
        "**Example 1:**\n"
        "- Input: `numCourses = 2, prerequisites = [[1,0]]`\n"
        "- Output: `true`\n"
        "- Explanation: Take course 0 first, then course 1.\n\n"
        "**Example 2:**\n"
        "- Input: `numCourses = 2, prerequisites = [[1,0],[0,1]]`\n"
        "- Output: `false`\n"
        "- Explanation: 0 requires 1, and 1 requires 0 — a cycle, impossible to finish."
    ),
    "hints": [
        "Model it as a directed graph: edge `b -> a` for each `[a, b]` pair. The question becomes: is this graph a DAG?",
        "Kahn's algorithm: repeatedly remove a node whose in-degree is 0 and decrement the in-degree of its successors. If you remove all `n` nodes, it's a DAG.",
        "DFS three-coloring: white = unvisited, gray = on current DFS stack, black = fully explored. Hitting a gray node during DFS = back-edge = cycle.",
        "Don't recompute the adjacency list inside the loop — build it once. O(V + E) overall.",
        "Edge cases: 0 courses (vacuously true), 1 course with no prereqs (true), self-loop `[a, a]` (false — that's a 1-cycle).",
    ],
    "constraints": [
        "1 <= numCourses <= 2000",
        "0 <= prerequisites.length <= 5000",
        "prerequisites[i].length == 2",
        "0 <= a, b < numCourses",
        "All [a, b] pairs are distinct.",
    ],
    "starter_code": {
        "python": "def can_finish(num_courses, prerequisites):\n    # Your code here\n    pass",
        "javascript": "function canFinish(numCourses, prerequisites) {\n    // Your code here\n}",
        "java": "public boolean canFinish(int numCourses, int[][] prerequisites) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(2, [[1,0]]), (2, [[1,0],[0,1]]), (5, [[1,0],[2,0],[3,1],[4,2]])]\n"
            "    for n, prereqs in cases:\n"
            "        print(f\"can_finish({n}, {prereqs}) = {can_finish(n, prereqs)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[2, [[1,0]]], [2, [[1,0],[0,1]]]].forEach(([n, p]) =>\n"
            "    console.log(`canFinish =`, canFinish(n, p))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.canFinish(2, new int[][]{{1,0}}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"num_courses": 2, "prerequisites": [[1, 0]]}, "expected": True,
         "description": "Single edge — trivially a DAG", "tags": ["basic"]},
        {"input": {"num_courses": 2, "prerequisites": [[1, 0], [0, 1]]}, "expected": False,
         "description": "Direct 2-cycle between courses 0 and 1", "tags": ["basic"]},
        {"input": {"num_courses": 1, "prerequisites": []}, "expected": True,
         "description": "One course, no prereqs", "tags": ["edge"]},
        {"input": {"num_courses": 5, "prerequisites": [[1, 0], [2, 0], [3, 1], [4, 2]]}, "expected": True,
         "description": "Tree-shaped DAG rooted at 0", "tags": ["basic"]},
        {"input": {"num_courses": 3, "prerequisites": [[0, 1], [1, 2], [2, 0]]}, "expected": False,
         "description": "3-cycle 0 -> 1 -> 2 -> 0", "tags": ["tricky"]},
        {"input": {"num_courses": 4, "prerequisites": [[2, 0], [2, 1], [3, 2]]}, "expected": True,
         "description": "Diamond-ish DAG — 2 has two parents, then 3 follows", "tags": ["basic"]},
        {"input": {"num_courses": 0, "prerequisites": []}, "expected": True,
         "description": "Zero courses — vacuously schedulable", "tags": ["edge"]},
        {"input": {"num_courses": 6, "prerequisites": [[1, 0], [2, 1], [3, 2], [4, 3], [5, 4]]}, "expected": True,
         "description": "Long chain 0 -> 1 -> 2 -> 3 -> 4 -> 5", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Kahn's Algorithm (BFS Topological Sort)",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V + E)",
            "description": (
                "Compute in-degrees, push every zero-in-degree node onto a queue, and pop nodes one at a "
                "time. For each popped node, decrement the in-degrees of its successors and push any that "
                "drop to zero. If the total number of popped nodes equals `numCourses`, every node was "
                "scheduled — no cycle. Otherwise, the un-popped nodes form a cycle."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "def can_finish(num_courses, prerequisites):\n"
                    "    graph = [[] for _ in range(num_courses)]\n"
                    "    in_degree = [0] * num_courses\n"
                    "    for a, b in prerequisites:\n"
                    "        graph[b].append(a)\n"
                    "        in_degree[a] += 1\n"
                    "    queue = deque(i for i in range(num_courses) if in_degree[i] == 0)\n"
                    "    processed = 0\n"
                    "    while queue:\n"
                    "        node = queue.popleft()\n"
                    "        processed += 1\n"
                    "        for nxt in graph[node]:\n"
                    "            in_degree[nxt] -= 1\n"
                    "            if in_degree[nxt] == 0:\n"
                    "                queue.append(nxt)\n"
                    "    return processed == num_courses"
                ),
                "javascript": (
                    "function canFinish(numCourses, prerequisites) {\n"
                    "    const graph = Array.from({length: numCourses}, () => []);\n"
                    "    const inDeg = new Array(numCourses).fill(0);\n"
                    "    for (const [a, b] of prerequisites) {\n"
                    "        graph[b].push(a);\n"
                    "        inDeg[a]++;\n"
                    "    }\n"
                    "    const queue = [];\n"
                    "    for (let i = 0; i < numCourses; i++) if (inDeg[i] === 0) queue.push(i);\n"
                    "    let processed = 0;\n"
                    "    while (queue.length) {\n"
                    "        const node = queue.shift();\n"
                    "        processed++;\n"
                    "        for (const nxt of graph[node]) {\n"
                    "            if (--inDeg[nxt] === 0) queue.push(nxt);\n"
                    "        }\n"
                    "    }\n"
                    "    return processed === numCourses;\n"
                    "}"
                ),
                "java": (
                    "public boolean canFinish(int numCourses, int[][] prerequisites) {\n"
                    "    List<List<Integer>> graph = new ArrayList<>();\n"
                    "    for (int i = 0; i < numCourses; i++) graph.add(new ArrayList<>());\n"
                    "    int[] inDeg = new int[numCourses];\n"
                    "    for (int[] p : prerequisites) {\n"
                    "        graph.get(p[1]).add(p[0]);\n"
                    "        inDeg[p[0]]++;\n"
                    "    }\n"
                    "    Deque<Integer> queue = new ArrayDeque<>();\n"
                    "    for (int i = 0; i < numCourses; i++) if (inDeg[i] == 0) queue.offer(i);\n"
                    "    int processed = 0;\n"
                    "    while (!queue.isEmpty()) {\n"
                    "        int node = queue.poll();\n"
                    "        processed++;\n"
                    "        for (int nxt : graph.get(node)) {\n"
                    "            if (--inDeg[nxt] == 0) queue.offer(nxt);\n"
                    "        }\n"
                    "    }\n"
                    "    return processed == numCourses;\n"
                    "}"
                ),
            },
        },
        {
            "title": "DFS with Three-Color Cycle Detection",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V + E)",
            "description": (
                "Color each node white (0), gray (1, on current DFS stack), or black (2, fully explored). "
                "Run DFS from every white node; if you encounter a gray neighbor, you've found a back-edge — "
                "a cycle. If every DFS finishes without seeing gray, the graph is a DAG."
            ),
            "code": {
                "python": (
                    "def can_finish(num_courses, prerequisites):\n"
                    "    graph = [[] for _ in range(num_courses)]\n"
                    "    for a, b in prerequisites:\n"
                    "        graph[b].append(a)\n"
                    "    WHITE, GRAY, BLACK = 0, 1, 2\n"
                    "    color = [WHITE] * num_courses\n\n"
                    "    def dfs(u):\n"
                    "        color[u] = GRAY\n"
                    "        for v in graph[u]:\n"
                    "            if color[v] == GRAY:\n"
                    "                return False\n"
                    "            if color[v] == WHITE and not dfs(v):\n"
                    "                return False\n"
                    "        color[u] = BLACK\n"
                    "        return True\n\n"
                    "    return all(color[i] != WHITE or dfs(i) for i in range(num_courses))"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the structure: each prerequisite is a directed edge. The question is 'is this graph a DAG?'",
        "2. Build the adjacency list once: for each `[a, b]`, add edge `b -> a`. (Pick a direction and stick with it.)",
        "3. Choose your tool — Kahn's BFS or DFS three-coloring. Both are O(V + E); Kahn's is easier to reason about and gives you the order for free if you ever need Course Schedule II.",
        "4. Kahn's: seed the queue with every zero-in-degree node, pop and decrement successors' in-degrees, count how many you popped. Cycle iff `popped < numCourses`.",
        "5. DFS: white/gray/black coloring. Hitting a gray neighbor mid-DFS is a back-edge, which is the textbook definition of a cycle in a directed graph.",
        "6. Edge cases: 0 courses (true), self-loop `[a, a]` (false — a 1-cycle), disconnected components (handled because both algorithms iterate over all nodes).",
    ],
    "tips": [
        "Edge direction matters and is easy to flip. `[a, b]` = 'b before a' = edge `b -> a`. Write a comment next to the line that builds the graph.",
        "DFS recursion can stack-overflow on long chains in languages with shallow stacks (Python's default is 1000). Either iterate or bump the limit explicitly — and if you iterate, you're basically writing Kahn's anyway.",
        "Two-color DFS (just visited / not visited) is **not** enough for directed cycle detection — you'd flag re-visits in DAGs as cycles. The three-color trick is what distinguishes a back-edge from a cross-edge or forward-edge.",
        "Common follow-up — Course Schedule II: return the actual order. Kahn's gives it directly: append each popped node to a list. (Reverse-postorder of the DFS works too.)",
        "Common follow-up — strongly-connected components (Tarjan / Kosaraju) when the interviewer wants you to *report which* courses are in the cycle, not just whether one exists.",
    ],
    "companies": ["Amazon", "Google", "Apple"],
    "topics": ["Graph", "Topological Sort", "BFS", "DFS"],
    "time_complexity": "O(V + E)",
    "space_complexity": "O(V + E)",
}


def REFERENCE(num_courses, prerequisites):
    graph = [[] for _ in range(num_courses)]
    in_degree = [0] * num_courses
    for a, b in prerequisites:
        graph[b].append(a)
        in_degree[a] += 1
    queue = deque(i for i in range(num_courses) if in_degree[i] == 0)
    processed = 0
    while queue:
        node = queue.popleft()
        processed += 1
        for nxt in graph[node]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)
    return processed == num_courses


register(PAYLOAD, REFERENCE)
