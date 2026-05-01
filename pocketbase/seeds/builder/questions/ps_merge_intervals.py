"""Merge Intervals — Medium. Sorting / Sweep.

Sort by start, walk and merge overlapping intervals. The textbook
problem; included here for completeness against the source bank."""
from builder.registry import register


PAYLOAD = {
    "title": "Merge Overlapping Intervals",
    "difficulty": "Medium",
    "description": (
        "Given an array of intervals `[start, end]`, merge all overlapping or touching intervals and "
        "return the result.\n\n"
        "**Example 1:**\n"
        "- Input: `intervals = [[1,3],[2,6],[8,10],[15,18]]`\n"
        "- Output: `[[1,6],[8,10],[15,18]]`\n\n"
        "**Example 2:**\n"
        "- Input: `intervals = [[1,4],[4,5]]`\n"
        "- Output: `[[1,5]]` (touching at endpoint — merge)"
    ),
    "hints": [
        "Sort intervals by start. After sorting, overlapping intervals are adjacent.",
        "Walk once. For each interval, either merge with the running 'current' (if start <= current.end) or push current and start anew.",
        "Touching at endpoints: `[1, 4]` and `[4, 5]` overlap by definition here. Use `<=` not `<` for the overlap check.",
        "Edge cases: empty input, single interval, all overlapping, all disjoint, contained intervals.",
    ],
    "constraints": [
        "0 <= |intervals| <= 10⁴",
        "0 <= start <= end <= 10⁹",
    ],
    "starter_code": {
        "python": "def merge_intervals(intervals):\n    # Your code here\n    pass",
        "javascript": "function mergeIntervals(intervals) {\n    // Your code here\n}",
        "java": "public int[][] mergeIntervals(int[][] intervals) {\n    // Your code here\n    return new int[][]{};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(merge_intervals([[1,3],[2,6],[8,10],[15,18]]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"intervals": [[1, 3], [2, 6], [8, 10], [15, 18]]},
         "expected": [[1, 6], [8, 10], [15, 18]],
         "description": "Standard example", "tags": ["basic"]},
        {"input": {"intervals": [[1, 4], [4, 5]]}, "expected": [[1, 5]],
         "description": "Touching merges", "tags": ["basic"]},
        {"input": {"intervals": []}, "expected": [],
         "description": "Empty input", "tags": ["edge"]},
        {"input": {"intervals": [[5, 10]]}, "expected": [[5, 10]],
         "description": "Single interval", "tags": ["edge"]},
        {"input": {"intervals": [[1, 4], [0, 4]]}, "expected": [[0, 4]],
         "description": "Out-of-order, identical end", "tags": ["edge"]},
        {"input": {"intervals": [[1, 100], [2, 5], [10, 20]]}, "expected": [[1, 100]],
         "description": "Two intervals contained inside the first", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Sort + Linear Scan (Optimal)",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n) for the output",
            "description": (
                "Sort by start. Iterate; for each interval, if `start <= current_end`, extend "
                "`current_end = max(current_end, end)`. Otherwise push the current interval and start a "
                "new one."
            ),
            "code": {
                "python": (
                    "def merge_intervals(intervals):\n"
                    "    if not intervals:\n"
                    "        return []\n"
                    "    intervals = sorted(intervals)\n"
                    "    out = [list(intervals[0])]\n"
                    "    for s, e in intervals[1:]:\n"
                    "        if s <= out[-1][1]:\n"
                    "            out[-1][1] = max(out[-1][1], e)\n"
                    "        else:\n"
                    "            out.append([s, e])\n"
                    "    return out"
                ),
                "javascript": (
                    "function mergeIntervals(intervals) {\n"
                    "    if (!intervals.length) return [];\n"
                    "    const sorted = [...intervals].sort((a, b) => a[0] - b[0]);\n"
                    "    const out = [sorted[0].slice()];\n"
                    "    for (let i = 1; i < sorted.length; i++) {\n"
                    "        const [s, e] = sorted[i];\n"
                    "        if (s <= out[out.length - 1][1]) out[out.length - 1][1] = Math.max(out[out.length - 1][1], e);\n"
                    "        else out.push([s, e]);\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Sort by start. After sorting, overlapping intervals are adjacent.",
        "2. Walk once. For each interval: extend the current merged interval if it overlaps; else push current + start new.",
        "3. `start <= current_end` for the overlap check — covers strict overlap AND touching at endpoint.",
        "4. `max(current_end, new_end)` for the merge — handles contained intervals.",
        "5. Edge cases: empty, single, sorted/reversed input, contained intervals, all overlapping, all disjoint.",
    ],
    "tips": [
        "Don't mutate the input. Sort a copy.",
        "For very large inputs, use in-place mutation if allowed — saves O(n) extra space.",
        "Common follow-up: 'insert a new interval into a sorted list of merged intervals.' Binary-search the insertion point; merge locally.",
        "Common follow-up: 'overlap detection only (don't merge).' Same scan, just count or return any pair.",
        "Common follow-up: 'merge intervals with payload (e.g. priority).' Combine payloads on merge per a domain-specific rule.",
    ],
    "companies": ["Amazon", "Google", "Facebook", "Microsoft"],
    "topics": ["Sorting", "Array", "Greedy"],
    "time_complexity": "O(n log n)",
    "space_complexity": "O(n)",
}


def REFERENCE(intervals):
    if not intervals:
        return []
    intervals = sorted(intervals)
    out = [list(intervals[0])]
    for s, e in intervals[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


register(PAYLOAD, REFERENCE)
