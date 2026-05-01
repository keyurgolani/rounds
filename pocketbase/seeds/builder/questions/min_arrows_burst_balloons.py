"""Minimum Number of Arrows to Burst Balloons — Medium. Greedy / Interval Scheduling.

The interval-scheduling cousin: instead of picking the maximum number of
non-overlapping intervals, we count the minimum number of *piercing
points* — equivalently, the number of disjoint groups in the maximum
mutually-overlapping decomposition. Sorting by end coordinate and
sweeping with a single 'current arrow position' nails it in O(n log n).
"""
from builder.registry import register


PAYLOAD = {
    "title": "Minimum Number of Arrows to Burst Balloons",
    "difficulty": "Medium",
    "description": (
        "There are spherical balloons taped onto a flat wall. The balloons are given as a 2D integer array "
        "`points` where `points[i] = [x_start, x_end]` denotes a balloon whose horizontal diameter stretches "
        "between `x_start` and `x_end`.\n\n"
        "Arrows can be shot up directly vertically from any point along the x-axis. A balloon with "
        "`x_start <= x <= x_end` is **burst** by an arrow shot at `x`. There is no limit to the number of "
        "arrows that can be shot. A shot arrow keeps traveling up infinitely, bursting any balloon in its path.\n\n"
        "Return the **minimum number of arrows** that must be shot to burst all balloons.\n\n"
        "**Example 1:**\n"
        "- Input: `points = [[10,16],[2,8],[1,6],[7,12]]`\n"
        "- Output: `2`\n"
        "- Explanation: Shoot one arrow at `x = 6` to burst `[1,6]` and `[2,8]`; shoot another at `x = 11` "
        "to burst `[10,16]` and `[7,12]`.\n\n"
        "**Example 2:**\n"
        "- Input: `points = [[1,2],[3,4],[5,6],[7,8]]`\n"
        "- Output: `4`\n"
        "- Explanation: All intervals are pairwise disjoint, so each balloon needs its own arrow."
    ),
    "hints": [
        "Touching counts as overlap — at `x = 2`, both `[1,2]` and `[2,3]` burst, so a single arrow suffices.",
        "Sort the balloons by their **end** coordinate. After sorting, the optimal greedy is to place an arrow at the *end* of the first balloon.",
        "Sweep through the sorted list. Whenever a balloon's `start` is greater than the current arrow's x-position, you must place a new arrow — at that balloon's end.",
        "This is the classic interval-piercing / minimum-clique-cover-on-an-interval-graph problem; greedy by end coordinate is provably optimal.",
        "Watch out for integer overflow when sorting by end in some languages — `Integer.MIN_VALUE` vs `MAX_VALUE` subtraction can overflow Java's `int`. Use `Integer.compare(a[1], b[1])`.",
    ],
    "constraints": [
        "1 <= points.length <= 10⁵",
        "points[i].length == 2",
        "-2³¹ <= x_start < x_end <= 2³¹ - 1 (mind 32-bit overflow when subtracting endpoints in comparators)",
    ],
    "starter_code": {
        "python": "def find_min_arrow_shots(points):\n    # Your code here\n    pass",
        "javascript": "function findMinArrowShots(points) {\n    // Your code here\n}",
        "java": "public int findMinArrowShots(int[][] points) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[[10,16],[2,8],[1,6],[7,12]], [[1,2],[3,4],[5,6],[7,8]], [[1,2],[2,3]]]\n"
            "    for points in cases:\n"
            "        print(f\"find_min_arrow_shots({points}) = {find_min_arrow_shots(points)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[10,16],[2,8],[1,6],[7,12]], [[1,2],[3,4],[5,6],[7,8]]].forEach(points =>\n"
            "    console.log(`findMinArrowShots =`, findMinArrowShots(points))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] pts = {{10,16},{2,8},{1,6},{7,12}};\n"
            "        System.out.println(s.findMinArrowShots(pts));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"points": [[10, 16], [2, 8], [1, 6], [7, 12]]}, "expected": 2,
         "description": "Classic LeetCode example — two overlapping clusters", "tags": ["basic"]},
        {"input": {"points": [[1, 2], [3, 4], [5, 6], [7, 8]]}, "expected": 4,
         "description": "All disjoint — one arrow per balloon", "tags": ["basic"]},
        {"input": {"points": [[1, 10], [2, 9], [3, 8], [4, 7], [5, 6]]}, "expected": 1,
         "description": "All mutually overlapping — single arrow at the common region", "tags": ["edge"]},
        {"input": {"points": [[5, 10]]}, "expected": 1,
         "description": "Single balloon — one arrow", "tags": ["edge"]},
        {"input": {"points": [[1, 2], [2, 3]]}, "expected": 1,
         "description": "Touching endpoints — at x=2 both burst", "tags": ["edge"]},
        {"input": {"points": []}, "expected": 0,
         "description": "Empty list — zero arrows", "tags": ["edge"]},
        {"input": {"points": [[9, 12], [1, 10], [4, 11], [8, 12], [3, 9], [6, 7], [10, 11]]}, "expected": 2,
         "description": "Reverse-sorted-ish input — sorting by end is essential", "tags": ["tricky"]},
        {"input": {"points": [[1, 6], [2, 8], [7, 12], [10, 16], [15, 18], [17, 20]]}, "expected": 3,
         "description": "Mixed pattern — three distinct overlap clusters", "tags": ["tricky"]},
        {"input": {"points": [[-2147483646, -2147483645], [2147483646, 2147483647]]}, "expected": 2,
         "description": "Extreme coordinates — comparator must avoid 32-bit subtraction overflow", "tags": ["large"]},
        {"input": {"points": [[1, 2], [4, 5], [1, 5]]}, "expected": 2,
         "description": "Wide balloon overlaps both narrow ones, but they don't overlap each other",
         "tags": ["tricky"]},
        {"input": {"points": [[i, i + 1] for i in range(0, 1000, 2)]}, "expected": 500,
         "description": "500 disjoint unit balloons — needs 500 arrows", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Greedy by End-Coordinate (Optimal)",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(1) auxiliary (or O(n) for the sort)",
            "description": (
                "Sort balloons by their end coordinate. Place the first arrow at the end of the first "
                "balloon — this is the rightmost x that still bursts it, maximising the chance of also "
                "bursting later balloons. Walk through the sorted list: if a balloon's start is strictly "
                "greater than the current arrow position, the previous arrow can't reach it, so place a new "
                "arrow at this balloon's end. Otherwise it's already burst — skip. The greedy is provably "
                "optimal because choosing any earlier arrow position would burst a strict subset of balloons."
            ),
            "code": {
                "python": (
                    "def find_min_arrow_shots(points):\n"
                    "    if not points:\n"
                    "        return 0\n"
                    "    points.sort(key=lambda p: p[1])\n"
                    "    arrows = 1\n"
                    "    arrow_x = points[0][1]\n"
                    "    for start, end in points[1:]:\n"
                    "        if start > arrow_x:\n"
                    "            arrows += 1\n"
                    "            arrow_x = end\n"
                    "    return arrows"
                ),
                "javascript": (
                    "function findMinArrowShots(points) {\n"
                    "    if (points.length === 0) return 0;\n"
                    "    points.sort((a, b) => a[1] - b[1]);\n"
                    "    let arrows = 1;\n"
                    "    let arrowX = points[0][1];\n"
                    "    for (let i = 1; i < points.length; i++) {\n"
                    "        const [start, end] = points[i];\n"
                    "        if (start > arrowX) {\n"
                    "            arrows++;\n"
                    "            arrowX = end;\n"
                    "        }\n"
                    "    }\n"
                    "    return arrows;\n"
                    "}"
                ),
                "java": (
                    "public int findMinArrowShots(int[][] points) {\n"
                    "    if (points.length == 0) return 0;\n"
                    "    // Use Integer.compare to avoid overflow when ends straddle Integer.MIN/MAX.\n"
                    "    Arrays.sort(points, (a, b) -> Integer.compare(a[1], b[1]));\n"
                    "    int arrows = 1;\n"
                    "    int arrowX = points[0][1];\n"
                    "    for (int i = 1; i < points.length; i++) {\n"
                    "        if (points[i][0] > arrowX) {\n"
                    "            arrows++;\n"
                    "            arrowX = points[i][1];\n"
                    "        }\n"
                    "    }\n"
                    "    return arrows;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Greedy by Start-Coordinate (Alternative)",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(1) auxiliary",
            "description": (
                "An equally valid framing: sort by `start`. Maintain the *minimum end* of the current "
                "overlapping group as the arrow's reach. When a balloon's start exceeds that minimum end, "
                "fire a new arrow and reset the group. Slightly subtler than sorting by end because you "
                "must keep tightening the reach with `min(reach, end)` while the group grows — but it's "
                "equivalent and useful when the input naturally arrives start-sorted."
            ),
            "code": {
                "python": (
                    "def find_min_arrow_shots(points):\n"
                    "    if not points:\n"
                    "        return 0\n"
                    "    points.sort(key=lambda p: p[0])\n"
                    "    arrows = 1\n"
                    "    reach = points[0][1]\n"
                    "    for start, end in points[1:]:\n"
                    "        if start > reach:\n"
                    "            arrows += 1\n"
                    "            reach = end\n"
                    "        else:\n"
                    "            reach = min(reach, end)\n"
                    "    return arrows"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: minimum number of x-coordinates that collectively pierce every interval. Classical interval-piercing problem.",
        "2. Brute force: try every distinct endpoint as a candidate arrow set — exponential. Useless for n up to 10⁵.",
        "3. Greedy intuition: if I sort by end, the first balloon's *end* is the latest possible arrow that still bursts it. Any later arrow misses it; any earlier arrow bursts a subset of what shooting at end would burst. So always shoot at end[0].",
        "4. Sweep: keep advancing through sorted balloons. Each one with start ≤ current_arrow is already pierced — skip. The first one with start > current_arrow forces a new arrow, placed at *its* end.",
        "5. Touching endpoints (`[1,2]` and `[2,3]`) overlap at x=2 — the comparison must be strict `>`, not `>=`.",
        "6. Edge cases: empty input → 0; single balloon → 1; identical balloons → 1.",
        "7. Overflow: in Java, sorting with `(a,b) -> a[1] - b[1]` overflows when `a[1] = MIN_VALUE` and `b[1] = MAX_VALUE`. Use `Integer.compare`.",
    ],
    "tips": [
        "Sort by `end`, not by `start`. Both work, but sort-by-end has a one-line greedy; sort-by-start needs you to also track `min(reach, end)`.",
        "The condition is `start > arrow_x` (strict). Touching counts as overlap because the problem allows `start <= x <= end`.",
        "In Java, `(a,b) -> a[1] - b[1]` is a classic bug at FAANG — it overflows on extreme inputs. Always reach for `Integer.compare` when sorting `int[][]`.",
        "Sibling problems: 'Non-overlapping Intervals' (435) → return n − arrows; 'Meeting Rooms II' (253) → max overlap depth, different greedy. Recognise the family.",
        "If the input is read-only / can't be sorted in place, copy first. The greedy is still O(n log n) overall.",
        "When asked to *return the arrow positions* (a follow-up), append `arrow_x` to a list each time you advance — same loop, one extra line.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Facebook", "Bloomberg"],
    "topics": ["Array", "Greedy", "Sorting", "Intervals"],
    "time_complexity": "O(n log n)",
    "space_complexity": "O(1)",
}


def REFERENCE(points):
    if not points:
        return 0
    pts = sorted(points, key=lambda p: p[1])
    arrows = 1
    arrow_x = pts[0][1]
    for start, end in pts[1:]:
        if start > arrow_x:
            arrows += 1
            arrow_x = end
    return arrows


register(PAYLOAD, REFERENCE)
