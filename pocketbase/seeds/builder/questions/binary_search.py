"""Binary Search — Easy. Binary Search.

The canonical binary search. Looks trivial; almost everyone gets it
subtly wrong on a whiteboard. The interesting part is *which*
invariant you commit to (half-open `[lo, hi)` vs closed `[lo, hi]`)
and then *holding* that invariant through every line — the loop
condition, the `mid` update, and the recursion on miss.

Worth practicing both the half-open and closed variants because the
follow-ups (find first/last occurrence, lower_bound, search-in-rotated)
all reduce to a binary search with a tweaked invariant.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Binary Search",
    "difficulty": "Easy",
    "description": (
        "Given an array of integers `nums` which is sorted in **ascending order**, and an integer `target`, "
        "write a function to search `target` in `nums`. If `target` exists, then return its index. "
        "Otherwise, return `-1`.\n\n"
        "You must write an algorithm with **O(log n)** runtime complexity.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [-1,0,3,5,9,12], target = 9`\n"
        "- Output: `4`\n"
        "- Explanation: 9 exists in nums and its index is 4.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [-1,0,3,5,9,12], target = 2`\n"
        "- Output: `-1`\n"
        "- Explanation: 2 does not exist in nums so return -1."
    ),
    "hints": [
        "Sorted + O(log n) = binary search. The tricky part is not the idea — it's holding the loop invariant cleanly.",
        "Pick *one* convention and stick with it: half-open `[lo, hi)` (where `hi = len(nums)`) or closed `[lo, hi]` (where `hi = len(nums) - 1`). The loop condition and `hi` update differ between the two.",
        "Always compute `mid = lo + (hi - lo) // 2`. In Python it doesn't matter, but in Java/C++ `(lo + hi) // 2` overflows for large arrays. Habit-form it.",
        "After comparing `nums[mid]` to `target`, you eliminate *one half* of the search window. If your bounds don't shrink every iteration, you'll loop forever — that's the classic binary-search bug.",
        "Empty array, single element, target smaller than min, target larger than max — walk through each on paper. They all collapse cleanly if your invariant is right.",
    ],
    "constraints": [
        "1 <= nums.length <= 10⁴ (we additionally test the empty-array case).",
        "-10⁴ < nums[i], target < 10⁴",
        "All integers in `nums` are **unique**.",
        "`nums` is sorted in ascending order.",
    ],
    "starter_code": {
        "python": "def search(nums, target):\n    # Your code here\n    pass",
        "javascript": "function search(nums, target) {\n    // Your code here\n}",
        "java": "public int search(int[] nums, int target) {\n    // Your code here\n    return -1;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([-1,0,3,5,9,12], 9), ([-1,0,3,5,9,12], 2), ([], 1)]\n"
            "    for nums, target in cases:\n"
            "        print(f\"search({nums}, {target}) = {search(nums, target)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[-1,0,3,5,9,12], 9], [[-1,0,3,5,9,12], 2]].forEach(([nums, target]) =>\n"
            "    console.log(`search =`, search(nums, target))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.search(new int[]{-1,0,3,5,9,12}, 9));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [-1, 0, 3, 5, 9, 12], "target": 9}, "expected": 4,
         "description": "Target present in middle-right of array", "tags": ["basic"]},
        {"input": {"nums": [-1, 0, 3, 5, 9, 12], "target": 2}, "expected": -1,
         "description": "Target absent, would sort between existing elements", "tags": ["basic"]},
        {"input": {"nums": [5], "target": 5}, "expected": 0,
         "description": "Single-element array — target matches", "tags": ["edge"]},
        {"input": {"nums": [5], "target": 4}, "expected": -1,
         "description": "Single-element array — target absent", "tags": ["edge"]},
        {"input": {"nums": [], "target": 1}, "expected": -1,
         "description": "Empty array — must not index into nums[0]", "tags": ["edge"]},
        {"input": {"nums": [1, 2, 3, 4, 5], "target": 1}, "expected": 0,
         "description": "Target at the leftmost boundary", "tags": ["edge"]},
        {"input": {"nums": [1, 2, 3, 4, 5], "target": 5}, "expected": 4,
         "description": "Target at the rightmost boundary", "tags": ["edge"]},
        {"input": {"nums": [1, 2, 3, 4, 5], "target": 6}, "expected": -1,
         "description": "Target larger than every element", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Iterative — Half-Open Interval [lo, hi) (Canonical)",
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
            "description": (
                "The half-open variant. `hi` starts at `len(nums)` and is *exclusive*. The loop runs while "
                "`lo < hi`. On a miss-low we set `lo = mid + 1`; on a miss-high we set `hi = mid` (not "
                "`mid - 1`, because `hi` is exclusive). This convention generalises cleanly to "
                "`bisect_left` / lower_bound problems."
            ),
            "code": {
                "python": (
                    "def search(nums, target):\n"
                    "    lo, hi = 0, len(nums)\n"
                    "    while lo < hi:\n"
                    "        mid = lo + (hi - lo) // 2\n"
                    "        if nums[mid] == target:\n"
                    "            return mid\n"
                    "        elif nums[mid] < target:\n"
                    "            lo = mid + 1\n"
                    "        else:\n"
                    "            hi = mid\n"
                    "    return -1"
                ),
                "javascript": (
                    "function search(nums, target) {\n"
                    "    let lo = 0, hi = nums.length;\n"
                    "    while (lo < hi) {\n"
                    "        const mid = lo + ((hi - lo) >> 1);\n"
                    "        if (nums[mid] === target) return mid;\n"
                    "        else if (nums[mid] < target) lo = mid + 1;\n"
                    "        else hi = mid;\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
                "java": (
                    "public int search(int[] nums, int target) {\n"
                    "    int lo = 0, hi = nums.length;\n"
                    "    while (lo < hi) {\n"
                    "        int mid = lo + (hi - lo) / 2;\n"
                    "        if (nums[mid] == target) return mid;\n"
                    "        else if (nums[mid] < target) lo = mid + 1;\n"
                    "        else hi = mid;\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative — Closed Interval [lo, hi]",
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
            "description": (
                "The closed variant. `hi` starts at `len(nums) - 1` and is *inclusive*. The loop runs while "
                "`lo <= hi`. On a miss-high we set `hi = mid - 1`. Equivalent in correctness; some find this "
                "easier to reason about because both ends are 'real' indices."
            ),
            "code": {
                "python": (
                    "def search(nums, target):\n"
                    "    lo, hi = 0, len(nums) - 1\n"
                    "    while lo <= hi:\n"
                    "        mid = lo + (hi - lo) // 2\n"
                    "        if nums[mid] == target:\n"
                    "            return mid\n"
                    "        elif nums[mid] < target:\n"
                    "            lo = mid + 1\n"
                    "        else:\n"
                    "            hi = mid - 1\n"
                    "    return -1"
                ),
                "javascript": (
                    "function search(nums, target) {\n"
                    "    let lo = 0, hi = nums.length - 1;\n"
                    "    while (lo <= hi) {\n"
                    "        const mid = lo + ((hi - lo) >> 1);\n"
                    "        if (nums[mid] === target) return mid;\n"
                    "        else if (nums[mid] < target) lo = mid + 1;\n"
                    "        else hi = mid - 1;\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Recursive",
            "time_complexity": "O(log n)",
            "space_complexity": "O(log n) — recursion stack",
            "description": (
                "Same logic, expressed as recursion on a closed interval. Conceptually cleaner; the iterative "
                "version is preferred in interviews because it avoids the O(log n) stack and removes the "
                "tail-call dependency."
            ),
            "code": {
                "python": (
                    "def search(nums, target):\n"
                    "    def helper(lo, hi):\n"
                    "        if lo > hi:\n"
                    "            return -1\n"
                    "        mid = lo + (hi - lo) // 2\n"
                    "        if nums[mid] == target:\n"
                    "            return mid\n"
                    "        elif nums[mid] < target:\n"
                    "            return helper(mid + 1, hi)\n"
                    "        else:\n"
                    "            return helper(lo, mid - 1)\n"
                    "    return helper(0, len(nums) - 1)"
                ),
            },
        },
        {
            "title": "Built-in bisect_left + Membership Check",
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
            "description": (
                "`bisect.bisect_left` returns the insertion point for `target` to keep `nums` sorted. If that "
                "index is in range and the element there equals `target`, return it; otherwise -1. Worth "
                "knowing because most binary-search interview problems are 'lower_bound with a twist', and "
                "`bisect` is the right primitive — but in an interview, write the loop yourself unless told "
                "otherwise."
            ),
            "code": {
                "python": (
                    "from bisect import bisect_left\n"
                    "\n"
                    "def search(nums, target):\n"
                    "    i = bisect_left(nums, target)\n"
                    "    if i < len(nums) and nums[i] == target:\n"
                    "        return i\n"
                    "    return -1"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Sorted + O(log n) is the dead giveaway: binary search. State the invariant before writing code.",
        "2. Pick a convention. Half-open `[lo, hi)` with `hi = len(nums)` and loop `while lo < hi`, OR closed `[lo, hi]` with `hi = len(nums) - 1` and loop `while lo <= hi`. Mixing them is the #1 source of off-by-one bugs.",
        "3. Compute `mid = lo + (hi - lo) // 2`. Avoids overflow in fixed-width languages and is a free habit to form even in Python.",
        "4. On `nums[mid] < target`, the answer (if any) is strictly to the right → `lo = mid + 1`. On `nums[mid] > target`, the answer is strictly to the left → `hi = mid` (half-open) or `hi = mid - 1` (closed). The `+1` / `-1` *must* match your convention.",
        "5. Termination: each iteration shrinks the window by at least one element. The loop ends when `lo == hi` (half-open) or `lo > hi` (closed). At that point the target is absent → return -1.",
        "6. Edge cases: empty array (loop body never runs), single element (one iteration), target outside the range (one or two iterations until the window collapses). All handled correctly by the invariant — no special cases needed.",
    ],
    "tips": [
        "Always use `mid = lo + (hi - lo) // 2`. In Java/C++/Go, `(lo + hi) / 2` overflows when both are near `INT_MAX`. Even in Python, get the muscle memory.",
        "Half-open `[lo, hi)` vs closed `[lo, hi]` — pick one and *stick to it across the whole interview*. The bug pattern is to accidentally switch mid-problem.",
        "Variant — find the *first* occurrence (lower_bound): on equality, don't return; instead set `hi = mid` and keep searching left. Final answer is `lo` if `nums[lo] == target`.",
        "Variant — find the *last* occurrence (upper_bound - 1): on equality, set `lo = mid + 1` and keep searching right. Final answer is `lo - 1` if it points to `target`.",
        "If the array is sorted but rotated (LC 33), you binary-search on which half is sorted at each step. Same skeleton, more interesting comparison logic.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Bloomberg"],
    "topics": ["Array", "Binary Search"],
    "time_complexity": "O(log n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums, target):
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return -1


register(PAYLOAD, REFERENCE)
