"""Merge Sorted Notifications — Easy. Two Pointers / Linked List.

Merge two sorted lists by timestamp. Domain dressing for the
classic merge-two-sorted-lists problem. Two pointers, O(n + m)."""
from builder.registry import register


PAYLOAD = {
    "title": "Merge Sorted Notification Lists",
    "difficulty": "Easy",
    "description": (
        "A workspace client receives two streams of notifications, each already sorted in ascending order "
        "by timestamp. Merge them into a single sorted list, preserving stable order across equal "
        "timestamps (entries from list A come before equal-timestamp entries from list B).\n\n"
        "Each notification is a tuple `(timestamp, payload)`.\n\n"
        "**Example:**\n"
        "- Input: `a = [(1, 'login'), (5, 'msg')]`, `b = [(3, 'mention'), (5, 'reply')]`\n"
        "- Output: `[(1, 'login'), (3, 'mention'), (5, 'msg'), (5, 'reply')]`\n\n"
        "(Stable: at timestamp 5, the entry from `a` comes first.)"
    ),
    "hints": [
        "Two pointers: `i` into `a`, `j` into `b`. Advance whichever has the smaller timestamp; on tie, advance `a` first to preserve stability.",
        "When one input is exhausted, append the rest of the other.",
        "Don't sort the concatenation — that's O((n+m) log(n+m)) and throws away the existing sortedness.",
        "Heap version generalises to k > 2 streams (the k-way merge).",
        "Edge cases: one or both empty, all-tied timestamps, single-element inputs, very different lengths.",
    ],
    "constraints": [
        "0 <= |a|, |b| <= 10⁵",
        "timestamps are integers",
    ],
    "starter_code": {
        "python": "def merge_notifications(a, b):\n    # Your code here\n    pass",
        "javascript": "function mergeNotifications(a, b) {\n    // Your code here\n}",
        "java": "public List<Object[]> mergeNotifications(List<Object[]> a, List<Object[]> b) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    a = [(1, 'login'), (5, 'msg')]\n"
            "    b = [(3, 'mention'), (5, 'reply')]\n"
            "    print(merge_notifications(a, b))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"a": [[1, "login"], [5, "msg"]],
                    "b": [[3, "mention"], [5, "reply"]]},
         "expected": [[1, "login"], [3, "mention"], [5, "msg"], [5, "reply"]],
         "description": "Stable tie-break at t=5", "tags": ["basic"]},
        {"input": {"a": [], "b": [[1, "x"]]}, "expected": [[1, "x"]],
         "description": "First list empty", "tags": ["edge"]},
        {"input": {"a": [[1, "x"]], "b": []}, "expected": [[1, "x"]],
         "description": "Second list empty", "tags": ["edge"]},
        {"input": {"a": [], "b": []}, "expected": [],
         "description": "Both empty", "tags": ["edge"]},
        {"input": {"a": [[1, "a"], [2, "a"], [3, "a"]],
                    "b": [[1, "b"], [2, "b"], [3, "b"]]},
         "expected": [[1, "a"], [1, "b"], [2, "a"], [2, "b"], [3, "a"], [3, "b"]],
         "description": "Every timestamp tied — stability across all", "tags": ["tricky"]},
        {"input": {"a": [[1, "a"]], "b": [[100, "z"]]},
         "expected": [[1, "a"], [100, "z"]],
         "description": "Disjoint ranges, single elements each", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Two Pointers (Optimal)",
            "time_complexity": "O(n + m)",
            "space_complexity": "O(n + m)",
            "description": (
                "Walk both lists with two pointers. Append the smaller-timestamp head; on tie, prefer "
                "list `a` to preserve stability. When one list is exhausted, extend with the remainder of "
                "the other. Linear time, linear extra space (or O(1) if you can mutate one of the inputs)."
            ),
            "code": {
                "python": (
                    "def merge_notifications(a, b):\n"
                    "    i = j = 0\n"
                    "    out = []\n"
                    "    while i < len(a) and j < len(b):\n"
                    "        if a[i][0] <= b[j][0]:\n"
                    "            out.append(a[i]); i += 1\n"
                    "        else:\n"
                    "            out.append(b[j]); j += 1\n"
                    "    out.extend(a[i:])\n"
                    "    out.extend(b[j:])\n"
                    "    return out"
                ),
                "javascript": (
                    "function mergeNotifications(a, b) {\n"
                    "    let i = 0, j = 0;\n"
                    "    const out = [];\n"
                    "    while (i < a.length && j < b.length) {\n"
                    "        if (a[i][0] <= b[j][0]) out.push(a[i++]);\n"
                    "        else out.push(b[j++]);\n"
                    "    }\n"
                    "    while (i < a.length) out.push(a[i++]);\n"
                    "    while (j < b.length) out.push(b[j++]);\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public List<Object[]> mergeNotifications(List<Object[]> a, List<Object[]> b) {\n"
                    "    int i = 0, j = 0;\n"
                    "    List<Object[]> out = new ArrayList<>();\n"
                    "    while (i < a.size() && j < b.size()) {\n"
                    "        if ((Long)a.get(i)[0] <= (Long)b.get(j)[0]) out.add(a.get(i++));\n"
                    "        else out.add(b.get(j++));\n"
                    "    }\n"
                    "    while (i < a.size()) out.add(a.get(i++));\n"
                    "    while (j < b.size()) out.add(b.get(j++));\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Two sorted inputs → two-pointer merge. Don't reach for sort.",
        "2. Tie-break rule: `a[i][0] <= b[j][0]` advances `a` (stability).",
        "3. Drain remaining elements of whichever list isn't exhausted.",
        "4. For k > 2 sources, generalise to a min-heap (k-way merge).",
        "5. Edge cases: empty inputs, all-tied timestamps, very uneven lengths.",
    ],
    "tips": [
        "`<=` not `<` for stability. Easy to flip and break the tie order.",
        "Don't `out.append(a[i:])` — that nests a list inside out. Use `extend`.",
        "If the inputs are linked lists, splice nodes rather than allocating; O(1) extra space.",
        "Common follow-up: 'merge k streams' — heap of k pointers. Same pattern, log k per pop.",
        "Common follow-up: 'streaming inputs.' Heap of stream heads still works; you just refill from the source on pop.",
    ],
    "companies": ["Amazon", "LinkedIn", "Microsoft"],
    "topics": ["Two Pointers", "Merge", "Linked List"],
    "time_complexity": "O(n + m)",
    "space_complexity": "O(n + m)",
}


def REFERENCE(a, b):
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i][0] <= b[j][0]:
            out.append(a[i])
            i += 1
        else:
            out.append(b[j])
            j += 1
    out.extend(a[i:])
    out.extend(b[j:])
    return out


register(PAYLOAD, REFERENCE)
