"""Insert Interval — Medium. Arrays / Sweep.

The 'sorted-list insert with local merge' classic. Three phases: copy
intervals strictly before the new one, absorb the overlap window into a
single merged interval, then copy the rest. O(n) without sorting because
the input is already sorted. The throwaway alternative — append and call
merge-intervals — works but costs the sort."""
from builder.registry import register


PAYLOAD = {
    "title": "Insert Interval",
    "difficulty": "Medium",
    "description": (
        "You are given a list of `intervals` sorted by start time and **non-overlapping**, plus a "
        "`newInterval = [start, end]`. Insert `newInterval` into `intervals` such that the result is "
        "still sorted by start and has no overlapping intervals (merging if necessary). Return the "
        "resulting list.\n\n"
        "**Example 1:**\n"
        "- Input: `intervals = [[1,3],[6,9]]`, `newInterval = [2,5]`\n"
        "- Output: `[[1,5],[6,9]]`\n"
        "- Explanation: `[2,5]` overlaps `[1,3]` → merge into `[1,5]`. `[6,9]` is untouched.\n\n"
        "**Example 2:**\n"
        "- Input: `intervals = [[1,2],[3,5],[6,7],[8,10],[12,16]]`, `newInterval = [4,8]`\n"
        "- Output: `[[1,2],[3,10],[12,16]]`\n"
        "- Explanation: `[4,8]` overlaps `[3,5]`, `[6,7]`, and `[8,10]` (touching at 8). Merge them all into `[3,10]`."
    ),
    "hints": [
        "Three phases: (a) copy every interval that ends *strictly before* `newInterval.start` — they're disjoint and to the left. (b) Merge the run of overlapping intervals (anything whose start is `<= newInterval.end`) into a single interval, expanding `newInterval` as you go. (c) Copy the remaining intervals — they're all to the right.",
        "Overlap check: `intervals[i].start <= new.end AND intervals[i].end >= new.start`. Touching at endpoints counts as overlap (problem semantics).",
        "While merging in phase (b): `new.start = min(new.start, intervals[i].start)`; `new.end = max(new.end, intervals[i].end)`. Push `new` to output once the run ends.",
        "Edge cases worth rehearsing: insert at front (no overlap), insert at end (no overlap), insert into empty list, insert that swallows the entire list, single-element input.",
        "Optional optimisation: binary-search for the first interval whose end >= new.start (start of overlap region) and the last interval whose start <= new.end. Phase (a) and phase (c) become slice copies. Same O(n) (because the copy still costs n) but elegant.",
    ],
    "constraints": [
        "0 <= intervals.length <= 10⁴",
        "intervals[i].length == 2 and 0 <= start_i <= end_i <= 10⁵",
        "intervals is sorted by start_i in ascending order with no overlaps; newInterval is well-formed.",
    ],
    "starter_code": {
        "python": "def insert_interval(intervals, newInterval):\n    # Your code here\n    pass",
        "javascript": "function insertInterval(intervals, newInterval) {\n    // Your code here\n}",
        "java": "public int[][] insertInterval(int[][] intervals, int[] newInterval) {\n    // Your code here\n    return new int[][]{};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(insert_interval([[1,3],[6,9]], [2,5]))\n"
            "    print(insert_interval([[1,2],[3,5],[6,7],[8,10],[12,16]], [4,8]))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "console.log(insertInterval([[1,3],[6,9]], [2,5]));\n"
            "console.log(insertInterval([[1,2],[3,5],[6,7],[8,10],[12,16]], [4,8]));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] r = s.insertInterval(new int[][]{{1,3},{6,9}}, new int[]{2,5});\n"
            "        for (int[] iv : r) System.out.println(iv[0] + \",\" + iv[1]);\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"intervals": [[1, 3], [6, 9]], "newInterval": [2, 5]},
         "expected": [[1, 5], [6, 9]],
         "description": "Classic LC example — overlap with the first only", "tags": ["basic"]},
        {"input": {"intervals": [[1, 2], [3, 5], [6, 7], [8, 10], [12, 16]], "newInterval": [4, 8]},
         "expected": [[1, 2], [3, 10], [12, 16]],
         "description": "Classic LC example — merge a run of three (touching at 8)", "tags": ["basic"]},
        {"input": {"intervals": [[3, 5], [7, 9]], "newInterval": [1, 2]},
         "expected": [[1, 2], [3, 5], [7, 9]],
         "description": "Insert at front, no overlap", "tags": ["edge"]},
        {"input": {"intervals": [[1, 3], [5, 7]], "newInterval": [9, 12]},
         "expected": [[1, 3], [5, 7], [9, 12]],
         "description": "Insert at end, no overlap", "tags": ["edge"]},
        {"input": {"intervals": [[1, 2], [3, 4], [5, 6]], "newInterval": [0, 10]},
         "expected": [[0, 10]],
         "description": "New interval swallows everything", "tags": ["tricky"]},
        {"input": {"intervals": [], "newInterval": [4, 7]},
         "expected": [[4, 7]],
         "description": "Insert into empty list", "tags": ["edge"]},
        {"input": {"intervals": [[1, 3], [4, 6], [9, 11]], "newInterval": [2, 5]},
         "expected": [[1, 6], [9, 11]],
         "description": "Merges first two only", "tags": ["basic"]},
        {"input": {"intervals": [[1, 5]], "newInterval": [2, 3]},
         "expected": [[1, 5]],
         "description": "Single-interval list, new interval fully contained", "tags": ["edge"]},
        {"input": {"intervals": [[1, 5]], "newInterval": [6, 8]},
         "expected": [[1, 5], [6, 8]],
         "description": "Single-interval list, no overlap (touches by one)", "tags": ["edge"]},
        {"input": {"intervals": [[1, 3], [6, 9]], "newInterval": [3, 6]},
         "expected": [[1, 9]],
         "description": "Touching exactly on both sides — merge all", "tags": ["tricky"]},
        {"input": {"intervals": [[3, 5]], "newInterval": [5, 7]},
         "expected": [[3, 7]],
         "description": "Single interval touching exactly at endpoint", "tags": ["tricky"]},
        {"input": {"intervals": [[2, 5]], "newInterval": [1, 10]},
         "expected": [[1, 10]],
         "description": "Single interval list, new interval fully contains it", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Three-Phase Linear Scan (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n) for the output",
            "description": (
                "Walk the input once with three phases. (1) Copy every interval ending strictly before "
                "`newInterval.start`. (2) While the current interval overlaps `newInterval` (start <= "
                "newInterval.end), absorb it by expanding `newInterval` to "
                "`[min(start), max(end)]`. Push the merged `newInterval`. (3) Copy the rest. No sort "
                "needed because the input is already sorted."
            ),
            "code": {
                "python": (
                    "def insert_interval(intervals, newInterval):\n"
                    "    out = []\n"
                    "    i, n = 0, len(intervals)\n"
                    "    new = list(newInterval)\n"
                    "    # Phase 1: strictly-before intervals\n"
                    "    while i < n and intervals[i][1] < new[0]:\n"
                    "        out.append(list(intervals[i]))\n"
                    "        i += 1\n"
                    "    # Phase 2: merge the overlap run\n"
                    "    while i < n and intervals[i][0] <= new[1]:\n"
                    "        new[0] = min(new[0], intervals[i][0])\n"
                    "        new[1] = max(new[1], intervals[i][1])\n"
                    "        i += 1\n"
                    "    out.append(new)\n"
                    "    # Phase 3: strictly-after intervals\n"
                    "    while i < n:\n"
                    "        out.append(list(intervals[i]))\n"
                    "        i += 1\n"
                    "    return out"
                ),
                "javascript": (
                    "function insertInterval(intervals, newInterval) {\n"
                    "    const out = [];\n"
                    "    let i = 0;\n"
                    "    const n = intervals.length;\n"
                    "    const nw = [newInterval[0], newInterval[1]];\n"
                    "    while (i < n && intervals[i][1] < nw[0]) {\n"
                    "        out.push(intervals[i].slice());\n"
                    "        i++;\n"
                    "    }\n"
                    "    while (i < n && intervals[i][0] <= nw[1]) {\n"
                    "        nw[0] = Math.min(nw[0], intervals[i][0]);\n"
                    "        nw[1] = Math.max(nw[1], intervals[i][1]);\n"
                    "        i++;\n"
                    "    }\n"
                    "    out.push(nw);\n"
                    "    while (i < n) {\n"
                    "        out.push(intervals[i].slice());\n"
                    "        i++;\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public int[][] insertInterval(int[][] intervals, int[] newInterval) {\n"
                    "    java.util.List<int[]> out = new java.util.ArrayList<>();\n"
                    "    int i = 0, n = intervals.length;\n"
                    "    int[] nw = new int[]{newInterval[0], newInterval[1]};\n"
                    "    while (i < n && intervals[i][1] < nw[0]) out.add(intervals[i++]);\n"
                    "    while (i < n && intervals[i][0] <= nw[1]) {\n"
                    "        nw[0] = Math.min(nw[0], intervals[i][0]);\n"
                    "        nw[1] = Math.max(nw[1], intervals[i][1]);\n"
                    "        i++;\n"
                    "    }\n"
                    "    out.add(nw);\n"
                    "    while (i < n) out.add(intervals[i++]);\n"
                    "    return out.toArray(new int[out.size()][]);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Append-and-Merge (Throwaway)",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "Append `newInterval` to the input and reuse the standard 'merge intervals' routine: sort "
                "by start, walk once, merge overlaps. Easy to write under pressure when you don't trust "
                "your three-phase boundary conditions, but you forfeit the linear-time advantage that the "
                "already-sorted input gives you."
            ),
            "code": {
                "python": (
                    "def insert_interval(intervals, newInterval):\n"
                    "    arr = list(intervals) + [list(newInterval)]\n"
                    "    arr.sort()\n"
                    "    out = [list(arr[0])]\n"
                    "    for s, e in arr[1:]:\n"
                    "        if s <= out[-1][1]:\n"
                    "            out[-1][1] = max(out[-1][1], e)\n"
                    "        else:\n"
                    "            out.append([s, e])\n"
                    "    return out"
                ),
                "javascript": (
                    "function insertInterval(intervals, newInterval) {\n"
                    "    const arr = [...intervals.map(x => x.slice()), newInterval.slice()];\n"
                    "    arr.sort((a, b) => a[0] - b[0]);\n"
                    "    const out = [arr[0].slice()];\n"
                    "    for (let i = 1; i < arr.length; i++) {\n"
                    "        const [s, e] = arr[i];\n"
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
        "1. Don't sort. The input is already sorted and non-overlapping; sorting throws away that information.",
        "2. Three phases. Strictly-before, overlap-merge, strictly-after. Each interval visits exactly one phase.",
        "3. Phase boundaries are pure numeric comparisons against `newInterval.start` and `newInterval.end`. No off-by-one if you write `intervals[i][1] < new.start` for phase 1 and `intervals[i][0] <= new.end` for phase 2.",
        "4. Touching at endpoints (e.g., [1,3] and [3,5]) — the problem treats this as overlap. Use `<=` not `<` in the phase-2 check.",
        "5. Phase 2 expands the running `new` interval — both ends — because earlier intervals may extend it leftward, later ones rightward.",
        "6. Edge cases: empty input → just `[newInterval]`. New before all → no phase 2, no phase 3. New after all → no phase 2.",
        "7. Optional binary search: find first overlap index and last overlap index; copy slices around. Same asymptotic, lower constant if overlap region is small.",
    ],
    "tips": [
        "Copy `newInterval` before mutating it. Otherwise you've corrupted the caller's argument.",
        "Phase-1 condition is `end < new.start` (strict). Phase-2 condition is `start <= new.end` (non-strict). Mixing these up is the #1 bug.",
        "Always push `new` to the output exactly once — between phase 2 and phase 3. Easy to forget when phase 2 is empty.",
        "Common follow-up: 'insert and then *also* return the indices that were merged.' Track the index range during phase 2.",
        "Common follow-up: 'streaming inserts.' Maintain a balanced BST or sorted container keyed by start; per-insert O(log n + k) where k is the merge length.",
        "Common follow-up: 'remove an interval' (LC 1272). Same three-phase shape, but phase 2 produces 0, 1, or 2 intervals instead of merging.",
    ],
    "companies": ["Google", "Facebook", "Amazon", "LinkedIn", "Microsoft", "Bloomberg"],
    "topics": ["Array", "Greedy", "Sorting"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(intervals, newInterval):
    out = []
    i, n = 0, len(intervals)
    new = list(newInterval)
    while i < n and intervals[i][1] < new[0]:
        out.append(list(intervals[i]))
        i += 1
    while i < n and intervals[i][0] <= new[1]:
        new[0] = min(new[0], intervals[i][0])
        new[1] = max(new[1], intervals[i][1])
        i += 1
    out.append(new)
    while i < n:
        out.append(list(intervals[i]))
        i += 1
    return out


register(PAYLOAD, REFERENCE)
