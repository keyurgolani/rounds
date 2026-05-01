"""Container With Most Water — Medium. Two Pointers / Greedy.

The proof of correctness is the whole interview. Why is it safe to
move the *shorter* side inward? Because moving the taller side can
never increase the area: width strictly decreases, and the height is
already capped by the shorter side. Articulate this and the rest of
the solution writes itself.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Container With Most Water",
    "difficulty": "Medium",
    "description": (
        "You are given an integer array `height` of length `n`. There are `n` vertical lines drawn such "
        "that the two endpoints of the i-th line are `(i, 0)` and `(i, height[i])`.\n\n"
        "Find two lines that together with the x-axis form a container, such that the container contains "
        "the most water.\n\n"
        "Return the **maximum amount of water** a container can store.\n\n"
        "*Notice that you may not slant the container.*\n\n"
        "**Example 1:**\n"
        "- Input: `height = [1,8,6,2,5,4,8,3,7]`\n"
        "- Output: `49`\n"
        "- Explanation: The vertical lines at index 1 (height 8) and index 8 (height 7) form the largest container with area = `min(8, 7) * (8 - 1) = 49`.\n\n"
        "**Example 2:**\n"
        "- Input: `height = [1,1]`\n"
        "- Output: `1`"
    ),
    "hints": [
        "Brute force: every pair → O(n²). State it as the baseline.",
        "Two pointers from both ends. Compute the area; remember the max.",
        "Decision rule: move the *shorter* side inward. The taller side already caps the area, so moving it can only shrink width without raising height.",
        "Why this is safe: any pair involving the shorter side and a value to its right would have width ≤ current width and height ≤ current shorter side. Discarding the shorter side never discards a better pair.",
        "Stop when the pointers meet. Track the running maximum across the walk.",
    ],
    "constraints": [
        "n == height.length",
        "2 <= n <= 10⁵",
        "0 <= height[i] <= 10⁴",
    ],
    "starter_code": {
        "python": "def max_area(height):\n    # Your code here\n    pass",
        "javascript": "function maxArea(height) {\n    // Your code here\n}",
        "java": "public int maxArea(int[] height) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[1,8,6,2,5,4,8,3,7], [1,1], [4,3,2,1,4]]\n"
            "    for h in cases:\n"
            "        print(f\"max_area({h}) = {max_area(h)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,8,6,2,5,4,8,3,7], [1,1], [4,3,2,1,4]].forEach(h =>\n"
            "    console.log(`maxArea =`, maxArea(h))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.maxArea(new int[]{1,8,6,2,5,4,8,3,7}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"height": [1, 8, 6, 2, 5, 4, 8, 3, 7]}, "expected": 49,
         "description": "Standard from problem statement", "tags": ["basic"]},
        {"input": {"height": [1, 1]}, "expected": 1,
         "description": "Minimum-length container", "tags": ["edge"]},
        {"input": {"height": [4, 3, 2, 1, 4]}, "expected": 16,
         "description": "Equal endpoints — best is the full width", "tags": ["tricky"]},
        {"input": {"height": [1, 2, 1]}, "expected": 2,
         "description": "Three lines, peak in middle is irrelevant — best is the outer pair",
         "tags": ["tricky"]},
        {"input": {"height": [2, 3, 4, 5, 18, 17, 6]}, "expected": 17,
         "description": "Tall pair late in the array — moving the shorter side matters",
         "tags": ["basic"]},
        {"input": {"height": [0, 0, 0, 0]}, "expected": 0,
         "description": "All zero — area is always zero", "tags": ["edge"]},
        {"input": {"height": [0, 5, 0, 5, 0]}, "expected": 10,
         "description": "Two non-zero pillars separated by zeros", "tags": ["tricky"]},
        {"input": {"height": [10000, 0, 0, 0, 10000]}, "expected": 40000,
         "description": "Maximum-height endpoints", "tags": ["edge"]},
        {"input": {"height": list(range(10000))}, "expected": 24995000,
         "description": "10K monotonically increasing — the area i*(9999-i) peaks at i≈5000 → 5000*4999 = 24,995,000",
         "tags": ["large"]},
        {"input": {"height": [10000] * 10000}, "expected": 99990000,
         "description": "10K equal heights — best is the outermost pair",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Two Pointers (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Pointers from both ends. Compute area, update max, then advance the pointer at the "
                "*shorter* side. Each step strictly reduces width, so we'd only stay competitive by "
                "raising the bottleneck — which only the shorter side can do. Stops in n − 1 steps."
            ),
            "code": {
                "python": (
                    "def max_area(height):\n"
                    "    left, right = 0, len(height) - 1\n"
                    "    best = 0\n"
                    "    while left < right:\n"
                    "        h = min(height[left], height[right])\n"
                    "        area = h * (right - left)\n"
                    "        if area > best:\n"
                    "            best = area\n"
                    "        if height[left] < height[right]:\n"
                    "            left += 1\n"
                    "        else:\n"
                    "            right -= 1\n"
                    "    return best"
                ),
                "javascript": (
                    "function maxArea(height) {\n"
                    "    let left = 0, right = height.length - 1, best = 0;\n"
                    "    while (left < right) {\n"
                    "        const h = Math.min(height[left], height[right]);\n"
                    "        const area = h * (right - left);\n"
                    "        if (area > best) best = area;\n"
                    "        if (height[left] < height[right]) left++;\n"
                    "        else right--;\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "public int maxArea(int[] height) {\n"
                    "    int left = 0, right = height.length - 1, best = 0;\n"
                    "    while (left < right) {\n"
                    "        int h = Math.min(height[left], height[right]);\n"
                    "        int area = h * (right - left);\n"
                    "        if (area > best) best = area;\n"
                    "        if (height[left] < height[right]) left++;\n"
                    "        else right--;\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "Try every pair. Mention it as the baseline; never submit it for n up to 10⁵."
            ),
            "code": {
                "python": (
                    "def max_area(height):\n"
                    "    best = 0\n"
                    "    for i in range(len(height)):\n"
                    "        for j in range(i + 1, len(height)):\n"
                    "            area = min(height[i], height[j]) * (j - i)\n"
                    "            if area > best:\n"
                    "                best = area\n"
                    "    return best"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Area = min(height[i], height[j]) * (j - i). Width and height fight each other.",
        "2. Brute force is n² — try to do better with structure.",
        "3. Two pointers from both ends maximises width up front. The question is which to move.",
        "4. Move the shorter side. Justification: if you move the taller side instead, width strictly drops and the bottleneck (shorter side) is unchanged → area can only decrease. So discarding the shorter side is safe.",
        "5. Track the running max as you go. Loop terminates when pointers cross — n-1 iterations.",
        "6. Edge cases: equal heights (move either; doesn't matter), all zeros (always 0), monotonic input (the answer is always the pair where the minimum is highest).",
    ],
    "tips": [
        "Be ready to *prove* the two-pointer rule on the spot. Saying 'it works' isn't enough — interviewers want the optimality argument.",
        "If both heights are equal, move either pointer (or both). Doesn't matter which — the proof still holds.",
        "Common follow-up: 'Trapping Rain Water'. Same shape, different question — total water trapped *between* the bars. Different two-pointer invariant; don't conflate them.",
        "Common follow-up: 'Max area for k slats' (k > 2). Different problem entirely; greedy two-pointer no longer applies.",
        "Don't forget that index distance is `right - left`, not `right - left + 1` — width counts gaps, not lines.",
    ],
    "companies": ["Amazon", "Apple", "Bloomberg", "Facebook", "Google"],
    "topics": ["Array", "Two Pointers", "Greedy"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(height):
    left, right = 0, len(height) - 1
    best = 0
    while left < right:
        h = min(height[left], height[right])
        area = h * (right - left)
        if area > best:
            best = area
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    return best


register(PAYLOAD, REFERENCE)
