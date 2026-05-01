"""Largest Rectangle in Histogram — Hard. Monotonic Stack.

The canonical 'monotonic increasing stack' problem. Every bar is pushed
once and popped once, giving a clean O(n) one-pass. Worth knowing cold
because it's the inner loop of Maximal Rectangle (LC 85) — you reduce
that 2D problem to n calls of this one. Candidates almost always reach
for brute force first; the trick is realising that when a shorter bar
arrives, every taller bar still on the stack has just learned its right
boundary.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Largest Rectangle in Histogram",
    "difficulty": "Hard",
    "description": (
        "Given an array of integers `heights` representing the histogram's bar heights "
        "where the width of each bar is `1`, return *the area of the largest rectangle* "
        "that can be formed within the histogram.\n\n"
        "**Example 1:**\n"
        "- Input: `heights = [2,1,5,6,2,3]`\n"
        "- Output: `10`\n"
        "- Explanation: The largest rectangle spans bars `[5,6]` at height `5`, area = `5 * 2 = 10`.\n\n"
        "**Example 2:**\n"
        "- Input: `heights = [2,4]`\n"
        "- Output: `4`\n"
        "- Explanation: Either the full strip at height 2 (area 4) or the second bar alone (area 4)."
    ),
    "hints": [
        "Brute force: for each pair (i, j), find the minimum height in `heights[i..j]` and multiply by `j - i + 1`. O(n²) with the right inner-loop trick, O(n³) naively.",
        "Reframe: for each bar `i`, what's the largest rectangle in which `heights[i]` is the *shortest* bar? That's `heights[i] * (right_smaller[i] - left_smaller[i] - 1)`.",
        "Both `left_smaller` (nearest smaller to the left) and `right_smaller` (nearest smaller to the right) are textbook monotonic stack queries — each is O(n).",
        "You can fuse both passes into one: maintain a stack of indices in increasing-height order. When the current bar is shorter than the top, you've just found the *right* boundary for every popped bar.",
        "Append a sentinel `0` at the end (or treat `i == len(heights)` as height `0`) to flush the stack at the end without a special case.",
    ],
    "constraints": [
        "1 <= heights.length <= 10⁵",
        "0 <= heights[i] <= 10⁴",
    ],
    "starter_code": {
        "python": "def largest_rectangle_area(heights):\n    # Your code here\n    pass",
        "javascript": "function largestRectangleArea(heights) {\n    // Your code here\n}",
        "java": "public int largestRectangleArea(int[] heights) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[2,1,5,6,2,3], [2,4], [6,2,5,4,5,1,6]]\n"
            "    for heights in cases:\n"
            "        print(f\"largest_rectangle_area({heights}) = {largest_rectangle_area(heights)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[2,1,5,6,2,3], [2,4], [6,2,5,4,5,1,6]].forEach(heights =>\n"
            "    console.log(`largestRectangleArea =`, largestRectangleArea(heights))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.largestRectangleArea(new int[]{2,1,5,6,2,3}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"heights": [2, 1, 5, 6, 2, 3]}, "expected": 10,
         "description": "Canonical case — bars [5,6] at height 5 give area 10", "tags": ["basic"]},
        {"input": {"heights": [2, 4]}, "expected": 4,
         "description": "Two bars — either the full strip at height 2 or the lone 4", "tags": ["basic"]},
        {"input": {"heights": []}, "expected": 0,
         "description": "Empty histogram — no rectangle possible", "tags": ["edge"]},
        {"input": {"heights": [5]}, "expected": 5,
         "description": "Single bar — area equals its height", "tags": ["edge"]},
        {"input": {"heights": [1, 1, 1]}, "expected": 3,
         "description": "Flat histogram — full width at height 1", "tags": ["edge"]},
        {"input": {"heights": [6, 2, 5, 4, 5, 1, 6]}, "expected": 12,
         "description": "Best rectangle is bars [5,4,5] at height 4, width 3 — area 12", "tags": ["tricky"]},
        {"input": {"heights": [0, 0, 0]}, "expected": 0,
         "description": "All zeros — no positive area", "tags": ["edge"]},
        {"input": {"heights": [5, 4, 3, 2, 1]}, "expected": 9,
         "description": "Strictly decreasing — best is height 3 over width 3 (or 2x4, 1x5); 9 wins", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Monotonic Increasing Stack (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk left-to-right. Maintain a stack of bar *indices* whose heights are strictly increasing. "
                "When the current bar is shorter than the bar on top, pop: the popped bar's rectangle extends "
                "from one past the new top (its left smaller) to one before the current index (its right smaller). "
                "Each bar is pushed and popped once → O(n) total. Append a sentinel `0` at the end to flush."
            ),
            "code": {
                "python": (
                    "def largest_rectangle_area(heights):\n"
                    "    stack = []  # indices, heights strictly increasing\n"
                    "    best = 0\n"
                    "    extended = heights + [0]  # sentinel flushes the stack\n"
                    "    for i, h in enumerate(extended):\n"
                    "        while stack and extended[stack[-1]] > h:\n"
                    "            top = stack.pop()\n"
                    "            left = stack[-1] if stack else -1\n"
                    "            width = i - left - 1\n"
                    "            best = max(best, extended[top] * width)\n"
                    "        stack.append(i)\n"
                    "    return best"
                ),
                "javascript": (
                    "function largestRectangleArea(heights) {\n"
                    "    const stack = [];\n"
                    "    let best = 0;\n"
                    "    const ext = [...heights, 0];\n"
                    "    for (let i = 0; i < ext.length; i++) {\n"
                    "        while (stack.length && ext[stack[stack.length - 1]] > ext[i]) {\n"
                    "            const top = stack.pop();\n"
                    "            const left = stack.length ? stack[stack.length - 1] : -1;\n"
                    "            best = Math.max(best, ext[top] * (i - left - 1));\n"
                    "        }\n"
                    "        stack.push(i);\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "public int largestRectangleArea(int[] heights) {\n"
                    "    int n = heights.length;\n"
                    "    java.util.Deque<Integer> stack = new java.util.ArrayDeque<>();\n"
                    "    int best = 0;\n"
                    "    for (int i = 0; i <= n; i++) {\n"
                    "        int h = (i == n) ? 0 : heights[i];\n"
                    "        while (!stack.isEmpty() && heights[stack.peek()] > h) {\n"
                    "            int top = stack.pop();\n"
                    "            int left = stack.isEmpty() ? -1 : stack.peek();\n"
                    "            best = Math.max(best, heights[top] * (i - left - 1));\n"
                    "        }\n"
                    "        if (i < n) stack.push(i);\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Divide and Conquer",
            "time_complexity": "O(n log n) average, O(n²) worst",
            "space_complexity": "O(n) recursion",
            "description": (
                "The largest rectangle either (a) uses the global minimum bar across the full width, "
                "(b) lies entirely to the left of that minimum, or (c) entirely to the right. Recurse "
                "on the two halves. Balanced when minima split evenly; degenerates to O(n²) on sorted "
                "input. Pair with a sparse table or segment tree for guaranteed O(n log n)."
            ),
            "code": {
                "python": (
                    "def largest_rectangle_area(heights):\n"
                    "    def solve(lo, hi):\n"
                    "        if lo > hi:\n"
                    "            return 0\n"
                    "        min_idx = lo\n"
                    "        for k in range(lo, hi + 1):\n"
                    "            if heights[k] < heights[min_idx]:\n"
                    "                min_idx = k\n"
                    "        full = heights[min_idx] * (hi - lo + 1)\n"
                    "        return max(full, solve(lo, min_idx - 1), solve(min_idx + 1, hi))\n"
                    "    return solve(0, len(heights) - 1)"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "For each starting index `i`, walk right and track the running minimum height in `heights[i..j]`. "
                "Multiply by width `(j - i + 1)`. Mention as the baseline; never submit for n up to 10⁵."
            ),
            "code": {
                "python": (
                    "def largest_rectangle_area(heights):\n"
                    "    best = 0\n"
                    "    for i in range(len(heights)):\n"
                    "        run_min = heights[i]\n"
                    "        for j in range(i, len(heights)):\n"
                    "            run_min = min(run_min, heights[j])\n"
                    "            best = max(best, run_min * (j - i + 1))\n"
                    "    return best"
                ),
            },
        },
    ],
    "thought_process": [
        "1. State the brute force first: for each pair (i, j), the rectangle height is `min(heights[i..j])`, area is `min * (j - i + 1)`. O(n²) with running-min, O(n³) naive.",
        "2. Flip the perspective: instead of fixing endpoints, fix the *shortest bar*. For each bar `i`, find the widest interval where `heights[i]` is the minimum — that's `(right_smaller[i] - left_smaller[i] - 1)` wide.",
        "3. Computing 'nearest smaller element on each side' for every index is the textbook monotonic stack pattern. Two passes, each O(n).",
        "4. Fuse the two passes. Maintain a single stack of indices with strictly increasing heights as you sweep left-to-right. When `heights[i]` drops below the top, you've just learned the right boundary for that top.",
        "5. Worked example on `[2,1,5,6,2,3]`: push 2 (idx 0); see 1 < 2, pop 2 with width `1-(-1)-1=1`, area 2; push 1, push 5, push 6; see 2 < 6, pop 6 (area `6*1=6`), pop 5 (area `5*2=10` ← winner), push 2, push 3; flush with sentinel 0 → pop 3 (area 3), pop 2 (area `2*4=8`), pop 1 (area `1*6=6`). Answer 10.",
        "6. Sentinel trick: append `0` (or treat `i == len(heights)` as height 0) so the final flush happens inside the main loop — no separate cleanup branch.",
        "7. Edge cases: empty array → 0; single bar → its own height; all-equal → `h * n`; strictly decreasing → first pop on the sentinel finds the largest.",
    ],
    "tips": [
        "The stack stores *indices*, not heights — you need the index to compute width. Storing pairs `(idx, height)` works too but wastes space.",
        "`left_smaller` for a popped bar is the new top of the stack, *not* the bar you just popped. Off-by-one here is the most common bug.",
        "This problem is the inner loop of **Maximal Rectangle (LC 85)**: for each row of a 0/1 matrix, build a histogram of column heights and call this function. n calls × O(cols) = O(rows × cols) total.",
        "Segment tree / sparse table variant: precompute range-min queries in O(n log n), then run divide-and-conquer in worst-case O(n log n). Mention if asked about alternatives — the stack approach is still simpler and faster in practice.",
        "Watch out for integer overflow in Java/C++ when heights and widths are both near 10⁴ × 10⁵ — `long` for the running max is the safe call, even though the final answer fits in `int` for the LeetCode constraints.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg", "Goldman Sachs"],
    "topics": ["Array", "Stack", "Monotonic Stack", "Divide and Conquer"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(heights):
    stack = []  # indices, heights strictly increasing
    best = 0
    extended = list(heights) + [0]
    for i, h in enumerate(extended):
        while stack and extended[stack[-1]] > h:
            top = stack.pop()
            left = stack[-1] if stack else -1
            width = i - left - 1
            area = extended[top] * width
            if area > best:
                best = area
        stack.append(i)
    return best


register(PAYLOAD, REFERENCE)
