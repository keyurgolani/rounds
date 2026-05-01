"""Falling Water (Trap Rain Water) — Hard. Two Pointers / DP.

Classic 'trapping rain water' problem. Two-pointer is the elegant
O(n) / O(1) solution; DP with prefix max arrays is the easier-to-derive
O(n) / O(n) solution."""
from builder.registry import register


PAYLOAD = {
    "title": "Falling Water (Trapping Rain Water)",
    "difficulty": "Hard",
    "description": (
        "Given an array of non-negative integers `heights` representing a 2D landscape elevation profile "
        "(each entry is one horizontal inch wide), return the **total volume** of water trapped after "
        "infinite rainfall.\n\n"
        "Water cannot escape past either edge — segments beyond both ends have infinite depth.\n\n"
        "**Example:**\n"
        "- Input: `heights = [1, 2, 3, 2, 1, 2, 3, 5, 4, 3, 4, 3]`\n"
        "- Output: `5`\n\n"
        "More canonical:\n"
        "- Input: `[0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]`\n"
        "- Output: `6`"
    ),
    "hints": [
        "At each index `i`, the water above it is `min(left_max, right_max) - heights[i]` (clamped at 0).",
        "DP: precompute `left_max[i]` and `right_max[i]` arrays. Sum the formula. O(n) time, O(n) space.",
        "Two-pointer: maintain `left`, `right`, `left_max`, `right_max`. Always process the smaller side because the constraint comes from there. O(n) time, O(1) space.",
        "Stack-based: monotonic decreasing stack of bar heights. On a higher bar, pop and add the rectangle of water that just got bounded.",
        "Edge cases: empty / single bar (no water), monotonic, plateau, single trough.",
    ],
    "constraints": [
        "0 <= |heights| <= 10⁵",
        "0 <= heights[i] <= 10⁴",
    ],
    "starter_code": {
        "python": "def trap(heights):\n    # Your code here\n    pass",
        "javascript": "function trap(heights) {\n    // Your code here\n}",
        "java": "public int trap(int[] heights) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(trap([0,1,0,2,1,0,1,3,2,1,2,1]))   # 6"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"heights": [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]}, "expected": 6,
         "description": "Standard canonical example", "tags": ["basic"]},
        {"input": {"heights": []}, "expected": 0,
         "description": "Empty", "tags": ["edge"]},
        {"input": {"heights": [3]}, "expected": 0,
         "description": "Single bar — no water possible", "tags": ["edge"]},
        {"input": {"heights": [1, 2, 3, 4]}, "expected": 0,
         "description": "Monotonic ascending — water flows off the right", "tags": ["edge"]},
        {"input": {"heights": [4, 3, 2, 1]}, "expected": 0,
         "description": "Monotonic descending — water flows off the left", "tags": ["edge"]},
        {"input": {"heights": [2, 0, 2]}, "expected": 2,
         "description": "Single trough", "tags": ["basic"]},
        {"input": {"heights": [3, 3, 3]}, "expected": 0,
         "description": "Flat plateau — no trapping", "tags": ["edge"]},
        {"input": {"heights": [4, 2, 0, 3, 2, 5]}, "expected": 9,
         "description": "Tricky asymmetric profile", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Two-Pointer (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Two pointers `l = 0`, `r = n-1`. Maintain `left_max` and `right_max`. Each step, advance "
                "the pointer on the smaller-bar side (its max bounds the water). When the current bar is "
                "below its side's max, the difference is trapped; otherwise update the side's max."
            ),
            "code": {
                "python": (
                    "def trap(heights):\n"
                    "    if not heights:\n"
                    "        return 0\n"
                    "    l, r = 0, len(heights) - 1\n"
                    "    lmax = rmax = 0\n"
                    "    total = 0\n"
                    "    while l < r:\n"
                    "        if heights[l] < heights[r]:\n"
                    "            if heights[l] >= lmax:\n"
                    "                lmax = heights[l]\n"
                    "            else:\n"
                    "                total += lmax - heights[l]\n"
                    "            l += 1\n"
                    "        else:\n"
                    "            if heights[r] >= rmax:\n"
                    "                rmax = heights[r]\n"
                    "            else:\n"
                    "                total += rmax - heights[r]\n"
                    "            r -= 1\n"
                    "    return total"
                ),
                "javascript": (
                    "function trap(heights) {\n"
                    "    if (!heights.length) return 0;\n"
                    "    let l = 0, r = heights.length - 1;\n"
                    "    let lmax = 0, rmax = 0, total = 0;\n"
                    "    while (l < r) {\n"
                    "        if (heights[l] < heights[r]) {\n"
                    "            if (heights[l] >= lmax) lmax = heights[l];\n"
                    "            else total += lmax - heights[l];\n"
                    "            l++;\n"
                    "        } else {\n"
                    "            if (heights[r] >= rmax) rmax = heights[r];\n"
                    "            else total += rmax - heights[r];\n"
                    "            r--;\n"
                    "        }\n"
                    "    }\n"
                    "    return total;\n"
                    "}"
                ),
            },
        },
        {
            "title": "DP with Prefix-Max Arrays",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Precompute `left_max[i]` (max of heights[0..i]) and `right_max[i]` (max of heights[i..n-1]). "
                "Water at i is `min(left_max[i], right_max[i]) - heights[i]`. Sum. Easier to derive than "
                "two-pointer; loses the O(1) space."
            ),
            "code": {
                "python": (
                    "def trap(heights):\n"
                    "    n = len(heights)\n"
                    "    if n == 0:\n"
                    "        return 0\n"
                    "    lmax = [0] * n; rmax = [0] * n\n"
                    "    lmax[0] = heights[0]\n"
                    "    for i in range(1, n):\n"
                    "        lmax[i] = max(lmax[i - 1], heights[i])\n"
                    "    rmax[n - 1] = heights[n - 1]\n"
                    "    for i in range(n - 2, -1, -1):\n"
                    "        rmax[i] = max(rmax[i + 1], heights[i])\n"
                    "    total = 0\n"
                    "    for i in range(n):\n"
                    "        total += min(lmax[i], rmax[i]) - heights[i]\n"
                    "    return total"
                ),
            },
        },
        {
            "title": "Monotonic Stack",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Stack of indices with decreasing heights. On a bar higher than the top, pop the top "
                "(it's a valley bottom). Width = current_index - new_top - 1. Bounded height = "
                "min(new_top_height, current_height) - popped_height. Add the rectangle."
            ),
            "code": {
                "python": (
                    "def trap(heights):\n"
                    "    stack = []\n"
                    "    total = 0\n"
                    "    for i, h in enumerate(heights):\n"
                    "        while stack and heights[stack[-1]] < h:\n"
                    "            top = stack.pop()\n"
                    "            if not stack:\n"
                    "                break\n"
                    "            width = i - stack[-1] - 1\n"
                    "            bounded = min(heights[stack[-1]], h) - heights[top]\n"
                    "            total += width * bounded\n"
                    "        stack.append(i)\n"
                    "    return total"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Per-index reasoning: the water above index i is `min(max_to_left, max_to_right) - h[i]` (clamped at 0).",
        "2. Brute force computes both maxes per index → O(n²). Reject.",
        "3. DP precomputes both maxes in O(n) and O(n) space — easy to derive, easy to explain.",
        "4. Two-pointer optimisation: 'always advance the smaller side because that's where the constraint binds.' O(n) / O(1).",
        "5. Stack variant: monotonic decreasing stack. Different framing; same complexity.",
        "6. Edge cases: empty, single bar, monotonic, plateaus, asymmetric profiles.",
    ],
    "tips": [
        "Two-pointer is the canonical answer in interviews — but it takes a moment to prove correct. Have the proof ready.",
        "DP with prefix-max is easier to write under stress. Submit it if you're shaky on the two-pointer.",
        "Stack is overkill for this problem but generalises to histogram / largest-rectangle.",
        "Common follow-up: '2D version (trapping rain water II).' Min-heap of border cells; expand inwards updating water level.",
        "Common follow-up: 'rainfall amount instead of infinite.' Same DP but cap each contribution at the rainfall.",
    ],
    "companies": ["Amazon", "Apple", "Bloomberg", "Google"],
    "topics": ["Two Pointers", "Dynamic Programming", "Stack", "Array"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(heights):
    if not heights:
        return 0
    l, r = 0, len(heights) - 1
    lmax = rmax = 0
    total = 0
    while l < r:
        if heights[l] < heights[r]:
            if heights[l] >= lmax:
                lmax = heights[l]
            else:
                total += lmax - heights[l]
            l += 1
        else:
            if heights[r] >= rmax:
                rmax = heights[r]
            else:
                total += rmax - heights[r]
            r -= 1
    return total


register(PAYLOAD, REFERENCE)
