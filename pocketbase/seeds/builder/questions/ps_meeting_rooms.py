"""Minimum Meeting Rooms — Medium. Sweep / Heap.

Given meeting intervals, return the minimum number of rooms needed.
Sweep-line or heap of end times — both are O(n log n)."""
from builder.registry import register


PAYLOAD = {
    "title": "Minimum Meeting Rooms",
    "difficulty": "Medium",
    "description": (
        "Given an array of meeting intervals `[start, end]`, return the **minimum number of conference "
        "rooms** required to host all meetings without conflicts. Two meetings touching at the boundary "
        "(e.g. one ending at 10 and another starting at 10) can share a room.\n\n"
        "**Example 1:**\n"
        "- Input: `intervals = [[0, 30], [5, 10], [15, 20]]`\n"
        "- Output: `2`\n\n"
        "**Example 2:**\n"
        "- Input: `intervals = [[7, 10], [2, 4]]`\n"
        "- Output: `1`"
    ),
    "hints": [
        "Sweep-line: split each meeting into events `(start, +1)` and `(end, -1)`. Sort; on tie, ends come BEFORE starts (so touching meetings share a room).",
        "Heap-of-end-times: sort meetings by start. For each meeting, evict ends that are <= current start (room frees up); push current end. Heap size at the end = answer.",
        "Brute force: timeline-marker counting per minute. Reject for large time ranges.",
        "Edge cases: empty input (0 rooms), single meeting (1 room), all overlapping, all disjoint, touching at endpoints.",
    ],
    "constraints": [
        "0 <= |intervals| <= 10⁵",
        "0 <= start < end <= 10⁹",
    ],
    "starter_code": {
        "python": "def min_meeting_rooms(intervals):\n    # Your code here\n    pass",
        "javascript": "function minMeetingRooms(intervals) {\n    // Your code here\n}",
        "java": "public int minMeetingRooms(int[][] intervals) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(min_meeting_rooms([[0, 30], [5, 10], [15, 20]]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"intervals": [[0, 30], [5, 10], [15, 20]]}, "expected": 2,
         "description": "Three meetings, max overlap of 2", "tags": ["basic"]},
        {"input": {"intervals": [[7, 10], [2, 4]]}, "expected": 1,
         "description": "Disjoint", "tags": ["basic"]},
        {"input": {"intervals": []}, "expected": 0,
         "description": "Empty", "tags": ["edge"]},
        {"input": {"intervals": [[1, 5]]}, "expected": 1,
         "description": "Single meeting", "tags": ["edge"]},
        {"input": {"intervals": [[1, 5], [5, 10]]}, "expected": 1,
         "description": "Touching at endpoint — share room", "tags": ["tricky"]},
        {"input": {"intervals": [[0, 10], [0, 10], [0, 10]]}, "expected": 3,
         "description": "Three identical — three rooms", "tags": ["edge"]},
        {"input": {"intervals": [[i, i + 5] for i in range(0, 100, 5)]}, "expected": 1,
         "description": "Back-to-back, sharing one room", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Min-Heap of End Times (Optimal)",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "Sort by start. Min-heap of currently-active room end times. For each meeting, pop all "
                "ends <= current start (those rooms free up). Push current end. Heap size after "
                "processing all meetings = max concurrent = rooms needed."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "def min_meeting_rooms(intervals):\n"
                    "    if not intervals:\n"
                    "        return 0\n"
                    "    sorted_intervals = sorted(intervals)\n"
                    "    heap = []\n"
                    "    best = 0\n"
                    "    for start, end in sorted_intervals:\n"
                    "        while heap and heap[0] <= start:\n"
                    "            heapq.heappop(heap)\n"
                    "        heapq.heappush(heap, end)\n"
                    "        best = max(best, len(heap))\n"
                    "    return best"
                ),
                "javascript": (
                    "function minMeetingRooms(intervals) {\n"
                    "    if (!intervals.length) return 0;\n"
                    "    const sorted = [...intervals].sort((a, b) => a[0] - b[0]);\n"
                    "    // Inline min-heap on end times\n"
                    "    const heap = [];\n"
                    "    const swap = (i, j) => { [heap[i], heap[j]] = [heap[j], heap[i]]; };\n"
                    "    const up = i => { while (i > 0) { const p = (i-1)>>1; if (heap[p] <= heap[i]) break; swap(i, p); i = p; } };\n"
                    "    const down = i => { const n = heap.length; while (true) { const l = 2*i+1, r = 2*i+2; let s = i; if (l < n && heap[l] < heap[s]) s = l; if (r < n && heap[r] < heap[s]) s = r; if (s === i) break; swap(i, s); i = s; } };\n"
                    "    let best = 0;\n"
                    "    for (const [start, end] of sorted) {\n"
                    "        while (heap.length && heap[0] <= start) { swap(0, heap.length - 1); heap.pop(); down(0); }\n"
                    "        heap.push(end); up(heap.length - 1);\n"
                    "        if (heap.length > best) best = heap.length;\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "public int minMeetingRooms(int[][] intervals) {\n"
                    "    if (intervals.length == 0) return 0;\n"
                    "    Arrays.sort(intervals, (a, b) -> a[0] - b[0]);\n"
                    "    PriorityQueue<Integer> heap = new PriorityQueue<>();\n"
                    "    int best = 0;\n"
                    "    for (int[] m : intervals) {\n"
                    "        while (!heap.isEmpty() && heap.peek() <= m[0]) heap.poll();\n"
                    "        heap.offer(m[1]);\n"
                    "        best = Math.max(best, heap.size());\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sweep Line",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "Convert intervals to events. Sort. Walk events, tracking running count and max. The "
                "tie-break rule (ends before starts) ensures touching meetings share a room."
            ),
            "code": {
                "python": (
                    "def min_meeting_rooms(intervals):\n"
                    "    if not intervals:\n"
                    "        return 0\n"
                    "    events = []\n"
                    "    for s, e in intervals:\n"
                    "        events.append((s, 1))\n"
                    "        events.append((e, -1))\n"
                    "    events.sort(key=lambda x: (x[0], x[1]))  # -1 before +1 on ties\n"
                    "    cur = best = 0\n"
                    "    for _, d in events:\n"
                    "        cur += d\n"
                    "        best = max(best, cur)\n"
                    "    return best"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: 'maximum overlap of intervals' — sweep-line / heap.",
        "2. Sort by start. Heap holds end-times of currently-active rooms.",
        "3. For each meeting: pop ends ≤ current start (those rooms have freed up). Push current end. Track heap-size max.",
        "4. Sweep variant: events for starts and ends. Tie-break ends before starts so touching meetings share.",
        "5. Edge cases: empty, single, all-overlapping, all-disjoint, touching.",
    ],
    "tips": [
        "Tie-break matters: '<= start' (heap) or 'ends before starts' (sweep) gives the touching-shares-room behaviour.",
        "The 'rooms' answer equals max concurrent — same algorithm as 'max concurrent tasks'.",
        "Common follow-up: 'assign each meeting to a specific room.' Same heap, but record which room you popped.",
        "Common follow-up: 'meeting types (priority).' Multiple heaps (one per type) or augment with priority field.",
        "Common follow-up: 'optimise total cost across rooms.' That's combinatorial — interval scheduling / weighted interval scheduling.",
    ],
    "companies": ["Amazon", "Bloomberg", "Facebook", "Google"],
    "topics": ["Sweep Line", "Heap", "Sorting", "Greedy"],
    "time_complexity": "O(n log n)",
    "space_complexity": "O(n)",
}


def REFERENCE(intervals):
    import heapq
    if not intervals:
        return 0
    sorted_intervals = sorted(intervals)
    heap = []
    best = 0
    for start, end in sorted_intervals:
        while heap and heap[0] <= start:
            heapq.heappop(heap)
        heapq.heappush(heap, end)
        best = max(best, len(heap))
    return best


register(PAYLOAD, REFERENCE)
