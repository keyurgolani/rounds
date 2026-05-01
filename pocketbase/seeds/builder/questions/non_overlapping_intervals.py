"""Non-overlapping Intervals — Medium. Greedy / Interval Scheduling.

The classic 'activity selection' problem in disguise. The trick is the
flip: instead of asking 'how many to remove?', ask 'how many can I
*keep* such that they're all non-overlapping?' The answer is then
`n − keepable`. Sort by end time and greedily take the earliest-ending
interval that doesn't conflict with the last kept one. This is one of
the rare greedy proofs every interviewer expects you to recite.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Non-overlapping Intervals",
    "difficulty": "Medium",
    "description": (
        "Given an array of intervals `intervals` where `intervals[i] = [start_i, end_i]`, return the "
        "**minimum number of intervals you need to remove** so that the rest of the intervals are "
        "non-overlapping.\n\n"
        "Two intervals `[a, b]` and `[c, d]` are considered non-overlapping if they only touch at a single "
        "endpoint — i.e., `[1, 2]` and `[2, 3]` do **not** overlap.\n\n"
        "**Example 1:**\n"
        "- Input: `intervals = [[1,2],[2,3],[3,4],[1,3]]`\n"
        "- Output: `1`\n"
        "- Explanation: Remove `[1,3]` and the remaining intervals are non-overlapping.\n\n"
        "**Example 2:**\n"
        "- Input: `intervals = [[1,2],[1,2],[1,2]]`\n"
        "- Output: `2`\n"
        "- Explanation: You need to remove two of the `[1,2]` intervals to leave a single non-overlapping one."
    ),
    "hints": [
        "Reframe the question. 'Minimum to remove' is the same as 'maximum to keep'. The answer is `n − max_non_overlapping`.",
        "This is the classic **activity selection** problem. Greedy works.",
        "Sort intervals by their **end time** ascending. Walk through and greedily keep each interval whose start is `>=` the end of the last kept interval.",
        "Why sort by end (not start)? Picking the interval that ends earliest leaves the most room for future intervals. Sorting by start can pick a long interval that blocks many short ones.",
        "Touching at endpoints does **not** count as overlap: `[1,2]` and `[2,3]` are compatible. Use `start >= last_end`, not `>`.",
    ],
    "constraints": [
        "1 <= intervals.length <= 10⁵",
        "intervals[i].length == 2",
        "-5 * 10⁴ <= start_i < end_i <= 5 * 10⁴",
    ],
    "starter_code": {
        "python": "def erase_overlap_intervals(intervals):\n    # Your code here\n    pass",
        "javascript": "function eraseOverlapIntervals(intervals) {\n    // Your code here\n}",
        "java": "public int eraseOverlapIntervals(int[][] intervals) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[1,2],[2,3],[3,4],[1,3]],\n"
            "        [[1,2],[1,2],[1,2]],\n"
            "        [[1,2],[2,3]],\n"
            "    ]\n"
            "    for intervals in cases:\n"
            "        print(f\"erase_overlap_intervals({intervals}) = {erase_overlap_intervals(intervals)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,2],[2,3],[3,4],[1,3]], [[1,2],[1,2],[1,2]]].forEach(intervals =>\n"
            "    console.log(`eraseOverlapIntervals =`, eraseOverlapIntervals(intervals))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.eraseOverlapIntervals(new int[][]{{1,2},{2,3},{3,4},{1,3}}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"intervals": [[1, 2], [2, 3], [3, 4], [1, 3]]}, "expected": 1,
         "description": "Classic example — remove [1,3] only", "tags": ["basic"]},
        {"input": {"intervals": [[1, 2], [1, 2], [1, 2]]}, "expected": 2,
         "description": "All identical — keep one, remove n-1", "tags": ["basic"]},
        {"input": {"intervals": [[1, 2], [3, 4], [5, 6], [7, 8]]}, "expected": 0,
         "description": "All non-overlapping — remove nothing", "tags": ["basic"]},
        {"input": {"intervals": [[1, 2]]}, "expected": 0,
         "description": "Single interval — trivially non-overlapping", "tags": ["edge"]},
        {"input": {"intervals": [[1, 2], [2, 3]]}, "expected": 0,
         "description": "Touching at endpoint — does not count as overlap", "tags": ["edge"]},
        {"input": {"intervals": [[1, 100], [2, 3], [4, 5], [6, 7]]}, "expected": 1,
         "description": "Nested — one giant interval blocks three small; remove the giant",
         "tags": ["tricky"]},
        {"input": {"intervals": [[1, 5], [2, 6], [3, 7], [4, 8], [5, 9]]}, "expected": 3,
         "description": "Chain ABCDE — keep [1,5] and [5,9] (touch at 5); remove the other 3",
         "tags": ["tricky"]},
        {"input": {"intervals": [[7, 8], [5, 6], [3, 4], [1, 2]]}, "expected": 0,
         "description": "Reverse-sorted but already non-overlapping — sort handles it", "tags": ["tricky"]},
        {"input": {"intervals": [[1, 10], [2, 3], [3, 4], [4, 5], [5, 6]]}, "expected": 1,
         "description": "Mixed — long interval covers many shorts; drop the long one", "tags": ["tricky"]},
        {"input": {"intervals": [[-100, -50], [-60, -40], [-30, -10], [-20, 0]]}, "expected": 2,
         "description": "Negative coordinates — same logic", "tags": ["tricky"]},
        {"input": {"intervals": [[i, i + 2] for i in range(0, 1000)]}, "expected": 500,
         "description": "1000 sliding intervals of width 2 — keep every other one (500 kept)", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Greedy by End-Time (Optimal)",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(1)",
            "description": (
                "Sort intervals by end time ascending. Walk through and keep each interval whose start is "
                ">= the end of the last kept interval. The number to remove is `n - kept`. Picking the "
                "earliest-ending interval at every step is the textbook greedy choice — it leaves the most "
                "room for what's left. The exchange argument: if an optimal solution doesn't pick the "
                "earliest-ending interval, you can swap it in without making things worse."
            ),
            "code": {
                "python": (
                    "def erase_overlap_intervals(intervals):\n"
                    "    if not intervals:\n"
                    "        return 0\n"
                    "    intervals.sort(key=lambda x: x[1])\n"
                    "    kept = 1\n"
                    "    last_end = intervals[0][1]\n"
                    "    for start, end in intervals[1:]:\n"
                    "        if start >= last_end:\n"
                    "            kept += 1\n"
                    "            last_end = end\n"
                    "    return len(intervals) - kept"
                ),
                "javascript": (
                    "function eraseOverlapIntervals(intervals) {\n"
                    "    if (intervals.length === 0) return 0;\n"
                    "    intervals.sort((a, b) => a[1] - b[1]);\n"
                    "    let kept = 1;\n"
                    "    let lastEnd = intervals[0][1];\n"
                    "    for (let i = 1; i < intervals.length; i++) {\n"
                    "        const [start, end] = intervals[i];\n"
                    "        if (start >= lastEnd) {\n"
                    "            kept++;\n"
                    "            lastEnd = end;\n"
                    "        }\n"
                    "    }\n"
                    "    return intervals.length - kept;\n"
                    "}"
                ),
                "java": (
                    "public int eraseOverlapIntervals(int[][] intervals) {\n"
                    "    if (intervals.length == 0) return 0;\n"
                    "    Arrays.sort(intervals, (a, b) -> a[1] - b[1]);\n"
                    "    int kept = 1;\n"
                    "    int lastEnd = intervals[0][1];\n"
                    "    for (int i = 1; i < intervals.length; i++) {\n"
                    "        if (intervals[i][0] >= lastEnd) {\n"
                    "            kept++;\n"
                    "            lastEnd = intervals[i][1];\n"
                    "        }\n"
                    "    }\n"
                    "    return intervals.length - kept;\n"
                    "}"
                ),
            },
        },
        {
            "title": "DP — Longest Non-overlapping Chain",
            "time_complexity": "O(n²)",
            "space_complexity": "O(n)",
            "description": (
                "Sort by start time. Let `dp[i]` = the maximum number of non-overlapping intervals using "
                "intervals[0..i] with intervals[i] included. Transition: `dp[i] = 1 + max(dp[j])` for all "
                "`j < i` where `intervals[j].end <= intervals[i].start`. Answer is `n - max(dp)`. Same "
                "shape as Longest Increasing Subsequence — useful to recognise but quadratic."
            ),
            "code": {
                "python": (
                    "def erase_overlap_intervals(intervals):\n"
                    "    if not intervals:\n"
                    "        return 0\n"
                    "    intervals.sort(key=lambda x: x[0])\n"
                    "    n = len(intervals)\n"
                    "    dp = [1] * n\n"
                    "    for i in range(1, n):\n"
                    "        for j in range(i):\n"
                    "            if intervals[j][1] <= intervals[i][0]:\n"
                    "                dp[i] = max(dp[i], dp[j] + 1)\n"
                    "    return n - max(dp)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. The phrasing is 'minimum to remove' but the natural question is 'maximum to keep'. Flip it: answer = n − max_non_overlapping_subset.",
        "2. This is **interval scheduling / activity selection** — a textbook greedy.",
        "3. Greedy choice: sort by end time, repeatedly pick the interval that ends earliest among those compatible with what's already picked.",
        "4. Why end time and not start time? Picking the earliest-ending interval leaves the most remaining room. A start-sorted greedy can pick a long interval that swallows many shorts.",
        "5. Sweep: keep `last_end`. For each interval (in end-sorted order), if `start >= last_end`, take it and update `last_end`.",
        "6. Subtlety: touching at endpoints (`[1,2]` then `[2,3]`) is NOT overlap. Use `>=`, not `>`.",
        "7. Edge cases: empty list → 0, single interval → 0, all identical → n − 1.",
    ],
    "tips": [
        "Sort by end time, not start time. This is the most common bug — start-sorted greedy fails on cases like `[[1,100],[2,3],[4,5]]`.",
        "Use `start >= last_end` (touching is fine), not `start > last_end`. Read the problem statement carefully — every interval problem has its own overlap convention.",
        "Be ready to explain the exchange argument when the interviewer asks 'why does end-time greedy work?'. Swap any earlier-ending interval into an optimal solution; it can only help.",
        "If asked for the actual subset to keep (not the count), maintain the picked list during the sweep — same algorithm, just track the choices.",
        "Common follow-up — **Meeting Rooms II** (minimum rooms to host all meetings): different problem, but same sort-by-time toolkit. Min-heap of end times.",
        "Common follow-up — **Insert Interval / Merge Intervals**: sort by start, then sweep merging. Different sort key, different greedy.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Bloomberg", "Apple", "Facebook"],
    "topics": ["Array", "Greedy", "Dynamic Programming", "Sorting"],
    "time_complexity": "O(n log n)",
    "space_complexity": "O(1)",
}


def REFERENCE(intervals):
    if not intervals:
        return 0
    sorted_intervals = sorted(intervals, key=lambda x: x[1])
    kept = 1
    last_end = sorted_intervals[0][1]
    for start, end in sorted_intervals[1:]:
        if start >= last_end:
            kept += 1
            last_end = end
    return len(sorted_intervals) - kept


register(PAYLOAD, REFERENCE)
