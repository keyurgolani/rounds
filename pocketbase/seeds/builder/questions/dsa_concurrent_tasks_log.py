"""Max Concurrent Tasks from Log — Medium. Sweep Line / Sorting.

Given a log of (start, end) intervals, return the maximum number of
concurrent intervals at any moment. Sweep line: sort all start/end
events, walk in order, increment on start, decrement on end."""
from builder.registry import register


PAYLOAD = {
    "title": "Max Concurrent Tasks from Server Log",
    "difficulty": "Medium",
    "description": (
        "Given a log of server tasks where each entry is `[start, end]` (with `start <= end`), return the "
        "**maximum number of tasks running concurrently** at any moment.\n\n"
        "**Example:**\n"
        "- Input: `tasks = [[1,5],[2,7],[3,4],[6,8]]`\n"
        "- Output: `3` (between t=3 and t=4 inclusive, three tasks are running)\n\n"
        "Treat the intervals as inclusive on both ends. If a task ends at `t` and another starts at `t`, "
        "they are concurrent at that moment."
    ),
    "hints": [
        "Brute force: for each integer time `t`, count tasks whose interval covers `t`. O(N · max_t). Wrong scale beyond tiny inputs.",
        "Sweep line: split each task into two events `(start, +1)` and `(end + 1, -1)` (the `+1` makes the end exclusive). Sort and walk, tracking a running count and its max.",
        "Tie-breaking: if a task ends and another starts at the same instant and you want them concurrent, sort starts BEFORE ends (use the standard `(time, +1)` < `(time, -1)` ordering).",
        "Heap variant: sort by start; for each task pop expired ends from a min-heap, push current end, max-track heap size.",
        "Edge cases: empty input, single task (max = 1), all overlapping (max = N), no overlaps (max = 1).",
    ],
    "constraints": [
        "0 <= |tasks| <= 10⁵",
        "0 <= start <= end <= 10⁹",
    ],
    "starter_code": {
        "python": "def max_concurrent(tasks):\n    # Your code here\n    pass",
        "javascript": "function maxConcurrent(tasks) {\n    // Your code here\n}",
        "java": "public int maxConcurrent(int[][] tasks) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(max_concurrent([[1,5],[2,7],[3,4],[6,8]]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"tasks": [[1, 5], [2, 7], [3, 4], [6, 8]]}, "expected": 3,
         "description": "Three tasks overlap between t=3 and t=4", "tags": ["basic"]},
        {"input": {"tasks": []}, "expected": 0,
         "description": "Empty log", "tags": ["edge"]},
        {"input": {"tasks": [[1, 10]]}, "expected": 1,
         "description": "Single task", "tags": ["edge"]},
        {"input": {"tasks": [[1, 2], [3, 4], [5, 6]]}, "expected": 1,
         "description": "Disjoint intervals", "tags": ["edge"]},
        {"input": {"tasks": [[1, 10], [1, 10], [1, 10]]}, "expected": 3,
         "description": "All identical", "tags": ["edge"]},
        {"input": {"tasks": [[1, 5], [5, 10]]}, "expected": 2,
         "description": "Touching at endpoint — inclusive overlap", "tags": ["tricky"]},
        {"input": {"tasks": [[i, i + 100] for i in range(1000)]}, "expected": 101,
         "description": "1000 sliding windows of width 100 — max concurrency at intersection",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Sweep-Line Events (Optimal)",
            "time_complexity": "O(N log N)",
            "space_complexity": "O(N)",
            "description": (
                "Convert each `[start, end]` into two events: `(start, +1)` and `(end + 1, -1)` (the +1 "
                "makes ends exclusive and ensures starts at the same instant as ends produce concurrency). "
                "Sort events; walk in order tracking a running count and its max."
            ),
            "code": {
                "python": (
                    "def max_concurrent(tasks):\n"
                    "    if not tasks:\n"
                    "        return 0\n"
                    "    events = []\n"
                    "    for s, e in tasks:\n"
                    "        events.append((s, 1))\n"
                    "        events.append((e + 1, -1))\n"
                    "    events.sort()\n"
                    "    cur = best = 0\n"
                    "    for _, d in events:\n"
                    "        cur += d\n"
                    "        best = max(best, cur)\n"
                    "    return best"
                ),
                "javascript": (
                    "function maxConcurrent(tasks) {\n"
                    "    if (!tasks.length) return 0;\n"
                    "    const events = [];\n"
                    "    for (const [s, e] of tasks) { events.push([s, 1]); events.push([e + 1, -1]); }\n"
                    "    events.sort((a, b) => a[0] - b[0] || a[1] - b[1]);\n"
                    "    let cur = 0, best = 0;\n"
                    "    for (const [, d] of events) { cur += d; if (cur > best) best = cur; }\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "public int maxConcurrent(int[][] tasks) {\n"
                    "    if (tasks.length == 0) return 0;\n"
                    "    int[][] ev = new int[tasks.length * 2][2];\n"
                    "    int k = 0;\n"
                    "    for (int[] t : tasks) { ev[k++] = new int[]{t[0], 1}; ev[k++] = new int[]{t[1] + 1, -1}; }\n"
                    "    Arrays.sort(ev, (a, b) -> a[0] != b[0] ? a[0] - b[0] : a[1] - b[1]);\n"
                    "    int cur = 0, best = 0;\n"
                    "    for (int[] e : ev) { cur += e[1]; if (cur > best) best = cur; }\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Min-Heap of End Times",
            "time_complexity": "O(N log N)",
            "space_complexity": "O(N)",
            "description": (
                "Sort tasks by start. For each task, pop all expired ends from a min-heap (ends < current "
                "start). Push current end. Heap size at this moment = concurrent tasks. Track the max. "
                "Same complexity as sweep-line but a different framing — useful when you need to know "
                "WHICH tasks overlap, not just how many."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "def max_concurrent(tasks):\n"
                    "    if not tasks:\n"
                    "        return 0\n"
                    "    sorted_tasks = sorted(tasks)\n"
                    "    heap = []\n"
                    "    best = 0\n"
                    "    for s, e in sorted_tasks:\n"
                    "        while heap and heap[0] < s:\n"
                    "            heapq.heappop(heap)\n"
                    "        heapq.heappush(heap, e)\n"
                    "        best = max(best, len(heap))\n"
                    "    return best"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: 'maximum overlap of intervals' — sweep line.",
        "2. Skip per-time-step counting (O(N · T)). Sort the events, walk the sorted stream.",
        "3. Map intervals to events: start → +1, end+1 → -1. The +1 makes ends exclusive — touching at endpoints counts as concurrent.",
        "4. Sort. Walk. Track running sum. Track max running sum.",
        "5. Heap variant if you need to know which tasks overlap, not just how many.",
        "6. Edge cases: empty input, single task, disjoint, all identical, touching at endpoint.",
    ],
    "tips": [
        "Tie-breaking matters. If '0 ends and 1 starts at t=5' must NOT count as concurrent, sort `-1` before `+1`. With `+1` first you get inclusive overlap (the version this problem asks for).",
        "Don't mutate the input. Sort a copy or build the events list separately.",
        "For 64-bit timestamps and very large N, use the sweep line — the heap version has more memory pressure.",
        "Common follow-up: 'at what time is the max reached?' Track the time alongside the max during the walk.",
        "Common follow-up: 'rooms / agents / lanes required' (LeetCode 'Meeting Rooms II') — same algorithm, same answer.",
    ],
    "companies": ["Amazon", "Bloomberg", "Microsoft"],
    "topics": ["Sweep Line", "Sorting", "Heap"],
    "time_complexity": "O(N log N)",
    "space_complexity": "O(N)",
}


def REFERENCE(tasks):
    if not tasks:
        return 0
    events = []
    for s, e in tasks:
        events.append((s, 1))
        events.append((e + 1, -1))
    events.sort()
    cur = best = 0
    for _, d in events:
        cur += d
        best = max(best, cur)
    return best


register(PAYLOAD, REFERENCE)
