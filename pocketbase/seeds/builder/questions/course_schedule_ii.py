"""Course Schedule II — Medium. Graph / Topological Sort.

Course Schedule's older sibling: instead of a yes/no answer, return *one*
valid topological ordering of the courses (or `[]` if the prerequisite
graph contains a cycle). Same DAG-detection bones as LC 207, but the
output is the order itself — which means the validator has to accept
*any* legal ordering, not a single fixed one. Kahn's BFS gives you the
order for free as you peel off zero-indegree nodes; DFS post-order
reverse works too but needs an extra cycle-detection colour.
"""
from collections import deque

from builder.registry import register


PAYLOAD = {
    "title": "Course Schedule II",
    "difficulty": "Medium",
    "description": (
        "There are a total of `numCourses` courses you have to take, labeled from `0` to `numCourses - 1`. "
        "You are given an array `prerequisites` where `prerequisites[i] = [a_i, b_i]` indicates that you "
        "**must take course `b_i` first** if you want to take course `a_i`.\n\n"
        "Return *the ordering of courses you should take to finish all courses*. If there are many valid "
        "answers, return **any** of them. If it is impossible to finish all courses, return an **empty array**.\n\n"
        "**Example 1:**\n"
        "- Input: `numCourses = 2, prerequisites = [[1,0]]`\n"
        "- Output: `[0,1]`\n"
        "- Explanation: There are a total of 2 courses to take. To take course 1 you should have finished course 0. So the correct course order is `[0,1]`.\n\n"
        "**Example 2:**\n"
        "- Input: `numCourses = 4, prerequisites = [[1,0],[2,0],[3,1],[3,2]]`\n"
        "- Output: `[0,2,1,3]`\n"
        "- Explanation: One valid ordering is `[0,1,2,3]`. Another is `[0,2,1,3]`.\n\n"
        "**Example 3:**\n"
        "- Input: `numCourses = 1, prerequisites = []`\n"
        "- Output: `[0]`"
    ),
    "hints": [
        "Same DAG framing as Course Schedule — but instead of returning `True`/`False`, you return the order.",
        "Kahn's BFS does this naturally: every time you dequeue a zero-indegree node, append it to the answer.",
        "If at the end your answer doesn't contain all `numCourses` nodes, the graph had a cycle — return `[]`.",
        "DFS post-order reverse also works: finish-time order, reversed, is a valid topological sort. You'll need a 3-colour visited array to detect back edges.",
        "Multiple orderings can be valid. Don't compare your output to a single 'expected' list — check the topological constraints instead.",
    ],
    "constraints": [
        "1 <= numCourses <= 2000",
        "0 <= prerequisites.length <= numCourses * (numCourses - 1)",
        "prerequisites[i].length == 2",
        "0 <= a_i, b_i < numCourses",
        "All the pairs `[a_i, b_i]` are distinct.",
    ],
    "starter_code": {
        "python": "def find_order(num_courses, prerequisites):\n    # Your code here\n    pass",
        "javascript": "function findOrder(numCourses, prerequisites) {\n    // Your code here\n}",
        "java": "public int[] findOrder(int numCourses, int[][] prerequisites) {\n    // Your code here\n    return new int[0];\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [(2, [[1,0]]), (4, [[1,0],[2,0],[3,1],[3,2]]), (2, [[1,0],[0,1]])]\n"
            "    for n, prereqs in cases:\n"
            "        print(f\"find_order({n}, {prereqs}) = {find_order(n, prereqs)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[2, [[1,0]]], [4, [[1,0],[2,0],[3,1],[3,2]]]].forEach(([n, p]) =>\n"
            "    console.log(`findOrder =`, findOrder(n, p))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[] order = s.findOrder(4, new int[][]{{1,0},{2,0},{3,1},{3,2}});\n"
            "        for (int c : order) System.out.print(c + \" \");\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"num_courses": 2, "prerequisites": [[1, 0]]},
         "expected": {"$match": "validator",
                      "description": "Valid topological order",
                      "code": "lambda inp, out: (isinstance(out, list) and (len(out) == 0 or (len(out) == inp['num_courses'] and all(out.index(b) < out.index(a) for a, b in inp['prerequisites']))))"},
         "description": "Two courses, single edge — only [0,1] is valid", "tags": ["basic"]},
        {"input": {"num_courses": 4, "prerequisites": [[1, 0], [2, 0], [3, 1], [3, 2]]},
         "expected": {"$match": "validator",
                      "description": "Valid topological order",
                      "code": "lambda inp, out: (isinstance(out, list) and (len(out) == 0 or (len(out) == inp['num_courses'] and all(out.index(b) < out.index(a) for a, b in inp['prerequisites']))))"},
         "description": "Diamond DAG — multiple valid orderings (e.g. [0,1,2,3] or [0,2,1,3])", "tags": ["basic"]},
        {"input": {"num_courses": 1, "prerequisites": []},
         "expected": [0],
         "description": "Single course, no prereqs — uniquely [0]", "tags": ["edge"]},
        {"input": {"num_courses": 0, "prerequisites": []},
         "expected": [],
         "description": "Zero courses — empty order", "tags": ["edge"]},
        {"input": {"num_courses": 2, "prerequisites": [[1, 0], [0, 1]]},
         "expected": [],
         "description": "Two-node cycle — impossible, return []", "tags": ["edge"]},
        {"input": {"num_courses": 3, "prerequisites": [[0, 1], [1, 2], [2, 0]]},
         "expected": [],
         "description": "Three-node cycle — impossible, return []", "tags": ["tricky"]},
        {"input": {"num_courses": 6, "prerequisites": [[1, 0], [2, 1], [3, 2], [4, 3], [5, 4]]},
         "expected": [0, 1, 2, 3, 4, 5],
         "description": "Linear chain — uniquely ordered", "tags": ["tricky"]},
        {"input": {"num_courses": 5, "prerequisites": []},
         "expected": {"$match": "validator",
                      "description": "Valid topological order",
                      "code": "lambda inp, out: (isinstance(out, list) and (len(out) == 0 or (len(out) == inp['num_courses'] and all(out.index(b) < out.index(a) for a, b in inp['prerequisites']))))"},
         "description": "Five disconnected courses — any permutation is valid", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Kahn's Algorithm (BFS, Optimal)",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V + E)",
            "description": (
                "Compute in-degree for every node. Seed a queue with all zero-indegree nodes. Pop, append "
                "to the order, and decrement the in-degree of each neighbour; when a neighbour hits zero, "
                "enqueue it. If the final order has fewer than `num_courses` entries, the graph had a "
                "cycle — return `[]`. Otherwise return the order."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "def find_order(num_courses, prerequisites):\n"
                    "    graph = [[] for _ in range(num_courses)]\n"
                    "    indegree = [0] * num_courses\n"
                    "    for a, b in prerequisites:\n"
                    "        graph[b].append(a)\n"
                    "        indegree[a] += 1\n"
                    "    queue = deque(i for i in range(num_courses) if indegree[i] == 0)\n"
                    "    order = []\n"
                    "    while queue:\n"
                    "        node = queue.popleft()\n"
                    "        order.append(node)\n"
                    "        for nb in graph[node]:\n"
                    "            indegree[nb] -= 1\n"
                    "            if indegree[nb] == 0:\n"
                    "                queue.append(nb)\n"
                    "    return order if len(order) == num_courses else []"
                ),
                "javascript": (
                    "function findOrder(numCourses, prerequisites) {\n"
                    "    const graph = Array.from({length: numCourses}, () => []);\n"
                    "    const indegree = new Array(numCourses).fill(0);\n"
                    "    for (const [a, b] of prerequisites) {\n"
                    "        graph[b].push(a);\n"
                    "        indegree[a]++;\n"
                    "    }\n"
                    "    const queue = [];\n"
                    "    for (let i = 0; i < numCourses; i++) if (indegree[i] === 0) queue.push(i);\n"
                    "    const order = [];\n"
                    "    while (queue.length) {\n"
                    "        const node = queue.shift();\n"
                    "        order.push(node);\n"
                    "        for (const nb of graph[node]) {\n"
                    "            if (--indegree[nb] === 0) queue.push(nb);\n"
                    "        }\n"
                    "    }\n"
                    "    return order.length === numCourses ? order : [];\n"
                    "}"
                ),
                "java": (
                    "public int[] findOrder(int numCourses, int[][] prerequisites) {\n"
                    "    List<List<Integer>> graph = new ArrayList<>();\n"
                    "    for (int i = 0; i < numCourses; i++) graph.add(new ArrayList<>());\n"
                    "    int[] indegree = new int[numCourses];\n"
                    "    for (int[] p : prerequisites) {\n"
                    "        graph.get(p[1]).add(p[0]);\n"
                    "        indegree[p[0]]++;\n"
                    "    }\n"
                    "    Deque<Integer> queue = new ArrayDeque<>();\n"
                    "    for (int i = 0; i < numCourses; i++) if (indegree[i] == 0) queue.add(i);\n"
                    "    int[] order = new int[numCourses];\n"
                    "    int idx = 0;\n"
                    "    while (!queue.isEmpty()) {\n"
                    "        int node = queue.poll();\n"
                    "        order[idx++] = node;\n"
                    "        for (int nb : graph.get(node)) {\n"
                    "            if (--indegree[nb] == 0) queue.add(nb);\n"
                    "        }\n"
                    "    }\n"
                    "    return idx == numCourses ? order : new int[0];\n"
                    "}"
                ),
            },
        },
        {
            "title": "DFS Post-Order Reverse",
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V + E)",
            "description": (
                "Run DFS from every unvisited node. Use a 3-colour visited array (0 = unseen, 1 = in current "
                "stack, 2 = finished). If you hit a node with colour 1, you've found a back edge — cycle, "
                "return `[]`. Otherwise, push each node onto an output list when its DFS finishes; the "
                "*reverse* of that list is a valid topological order."
            ),
            "code": {
                "python": (
                    "def find_order(num_courses, prerequisites):\n"
                    "    graph = [[] for _ in range(num_courses)]\n"
                    "    for a, b in prerequisites:\n"
                    "        graph[b].append(a)\n"
                    "    color = [0] * num_courses  # 0 = white, 1 = gray, 2 = black\n"
                    "    order = []\n\n"
                    "    def dfs(u):\n"
                    "        if color[u] == 1:\n"
                    "            return False  # cycle\n"
                    "        if color[u] == 2:\n"
                    "            return True\n"
                    "        color[u] = 1\n"
                    "        for v in graph[u]:\n"
                    "            if not dfs(v):\n"
                    "                return False\n"
                    "        color[u] = 2\n"
                    "        order.append(u)\n"
                    "        return True\n\n"
                    "    for i in range(num_courses):\n"
                    "        if not dfs(i):\n"
                    "            return []\n"
                    "    return order[::-1]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the problem as a topological sort on a DAG: edge `b → a` means 'b must precede a'. If the graph has a cycle, no valid order exists.",
        "2. Two standard approaches: Kahn's BFS (peel zero-indegree nodes layer by layer) and DFS post-order reverse (use a 3-colour visited array to catch back edges).",
        "3. Kahn's gives the order for free: every dequeue is the next course you can take. After the loop, if you've emitted fewer than `num_courses` nodes, a cycle blocked some — return `[]`.",
        "4. Build the graph as adjacency-list `b → a` (not `a → b`) so Kahn's 'process prerequisites first' direction matches naturally.",
        "5. Edge cases worth stating up front: `num_courses = 0` → `[]`; no prerequisites → any permutation (commonly `[0, 1, …, n-1]` from the seed order); single self-loop → cycle.",
        "6. Both approaches are O(V + E) time and space. Kahn's is iterative (no recursion-depth concerns at V = 2000); DFS is recursive but cleaner if you're already comfortable with the colour trick.",
    ],
    "tips": [
        "Multiple valid orderings exist — don't hard-code an 'expected' list when testing. Instead, verify the output: it must contain every course exactly once *and* respect every prerequisite edge.",
        "Off-by-one trap: the cycle check is `len(order) == num_courses`, not `len(order) > 0`. A partial order (some courses unreachable due to a cycle elsewhere) still has nonzero length.",
        "Edge direction matters. `[a, b]` in the input means 'b before a', so add `b → a` to the adjacency list. Reversing it gives a backwards-but-valid-looking order that fails on cycles you'd otherwise catch.",
        "If the interviewer asks for the *lexicographically smallest* valid order, swap the queue for a min-heap in Kahn's — same algorithm, O((V + E) log V).",
        "Real-world hook: this is the 'parallel build scheduler' problem. The BFS *layer* (all nodes dequeued before their successors are enqueued) is exactly the set of tasks that can run concurrently in that wave.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Facebook"],
    "topics": ["Graph", "Topological Sort", "BFS", "DFS"],
    "time_complexity": "O(V + E)",
    "space_complexity": "O(V + E)",
}


def REFERENCE(num_courses, prerequisites):
    graph = [[] for _ in range(num_courses)]
    indegree = [0] * num_courses
    for a, b in prerequisites:
        graph[b].append(a)
        indegree[a] += 1
    queue = deque(i for i in range(num_courses) if indegree[i] == 0)
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nb in graph[node]:
            indegree[nb] -= 1
            if indegree[nb] == 0:
                queue.append(nb)
    return order if len(order) == num_courses else []


register(PAYLOAD, REFERENCE)
