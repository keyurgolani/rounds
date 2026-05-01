"""Search in Rotated Sorted Array — Medium. Modified Binary Search.

The classic 'binary search with a twist'. The array is sorted, then
rotated at an unknown pivot — so it's no longer globally monotonic,
but at any midpoint *one half is still sorted*. Identifying which
half is sorted (and whether the target lies inside it) is the whole
trick. Asked everywhere; the natural follow-up is LeetCode 81 where
duplicates break the strict comparison and force a worst-case O(n).
"""
from builder.registry import register


PAYLOAD = {
    "title": "Search in Rotated Sorted Array",
    "difficulty": "Medium",
    "description": (
        "There is an integer array `nums` sorted in ascending order (with **distinct** values).\n\n"
        "Prior to being passed to your function, `nums` is **possibly rotated** at an unknown pivot index "
        "`k` (`0 <= k < nums.length`) such that the resulting array is "
        "`[nums[k], nums[k+1], ..., nums[n-1], nums[0], nums[1], ..., nums[k-1]]` (0-indexed). For example, "
        "`[0,1,2,4,5,6,7]` might be rotated at pivot index `3` and become `[4,5,6,7,0,1,2]`.\n\n"
        "Given the array `nums` after the possible rotation and an integer `target`, return the index of "
        "`target` if it is in `nums`, or `-1` if it is not in `nums`.\n\n"
        "You must write an algorithm with **O(log n)** runtime complexity.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [4,5,6,7,0,1,2]`, `target = 0`\n"
        "- Output: `4`\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [4,5,6,7,0,1,2]`, `target = 3`\n"
        "- Output: `-1`\n\n"
        "**Example 3:**\n"
        "- Input: `nums = [1]`, `target = 0`\n"
        "- Output: `-1`"
    ),
    "hints": [
        "O(n) linear scan trivially works — state it, then beat it. The interviewer wants O(log n).",
        "Plain binary search fails because `nums` isn't globally monotonic. But at any midpoint, *one half* (left of mid or right of mid) is still strictly sorted.",
        "Compare `nums[lo]` with `nums[mid]`. If `nums[lo] <= nums[mid]`, the left half is sorted. Otherwise the right half is sorted.",
        "Once you know which half is sorted, check whether `target` lies inside its known range. If it does, recurse there; otherwise recurse the other half.",
        "Two-pass alternative: first find the pivot (smallest element) with binary search, then plain-binary-search the correct half. Same O(log n), more code.",
    ],
    "constraints": [
        "1 <= nums.length <= 5000",
        "-10⁴ <= nums[i] <= 10⁴",
        "All values of nums are unique.",
        "nums is an ascending array that is possibly rotated.",
        "-10⁴ <= target <= 10⁴",
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
            "    cases = [([4,5,6,7,0,1,2], 0), ([4,5,6,7,0,1,2], 3), ([1], 0)]\n"
            "    for nums, target in cases:\n"
            "        print(f\"search({nums}, {target}) = {search(nums, target)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[4,5,6,7,0,1,2], 0], [[4,5,6,7,0,1,2], 3], [[1], 0]].forEach(([nums, target]) =>\n"
            "    console.log(`search =`, search(nums, target))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.search(new int[]{4,5,6,7,0,1,2}, 0));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [4, 5, 6, 7, 0, 1, 2], "target": 0}, "expected": 4,
         "description": "Target lives in the rotated (right) half", "tags": ["basic"]},
        {"input": {"nums": [4, 5, 6, 7, 0, 1, 2], "target": 3}, "expected": -1,
         "description": "Target falls in the gap created by rotation — not present", "tags": ["basic"]},
        {"input": {"nums": [1], "target": 0}, "expected": -1,
         "description": "Single element, miss", "tags": ["edge"]},
        {"input": {"nums": [1], "target": 1}, "expected": 0,
         "description": "Single element, hit", "tags": ["edge"]},
        {"input": {"nums": [3, 1], "target": 1}, "expected": 1,
         "description": "Two-element rotation — the small-array boundary case binary search trips on",
         "tags": ["edge"]},
        {"input": {"nums": [5, 1, 3], "target": 3}, "expected": 2,
         "description": "Three-element rotation; target on the sorted-right side",
         "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 3, 4, 5], "target": 4}, "expected": 3,
         "description": "Zero rotation — degenerates to plain binary search", "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 3, 4, 5], "target": 6}, "expected": -1,
         "description": "Zero rotation, target beyond max — plain miss", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "One-Pass Modified Binary Search (Optimal)",
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
            "description": (
                "Standard binary search loop with one extra decision. At each midpoint, compare `nums[lo]` "
                "to `nums[mid]` to determine which half is sorted. Then check whether `target` falls inside "
                "that sorted half's known range — if so, narrow into it; otherwise narrow into the other half. "
                "Each iteration halves the search space, so O(log n)."
            ),
            "code": {
                "python": (
                    "def search(nums, target):\n"
                    "    lo, hi = 0, len(nums) - 1\n"
                    "    while lo <= hi:\n"
                    "        mid = (lo + hi) // 2\n"
                    "        if nums[mid] == target:\n"
                    "            return mid\n"
                    "        if nums[lo] <= nums[mid]:\n"
                    "            # Left half [lo..mid] is sorted\n"
                    "            if nums[lo] <= target < nums[mid]:\n"
                    "                hi = mid - 1\n"
                    "            else:\n"
                    "                lo = mid + 1\n"
                    "        else:\n"
                    "            # Right half [mid..hi] is sorted\n"
                    "            if nums[mid] < target <= nums[hi]:\n"
                    "                lo = mid + 1\n"
                    "            else:\n"
                    "                hi = mid - 1\n"
                    "    return -1"
                ),
                "javascript": (
                    "function search(nums, target) {\n"
                    "    let lo = 0, hi = nums.length - 1;\n"
                    "    while (lo <= hi) {\n"
                    "        const mid = (lo + hi) >> 1;\n"
                    "        if (nums[mid] === target) return mid;\n"
                    "        if (nums[lo] <= nums[mid]) {\n"
                    "            if (nums[lo] <= target && target < nums[mid]) hi = mid - 1;\n"
                    "            else lo = mid + 1;\n"
                    "        } else {\n"
                    "            if (nums[mid] < target && target <= nums[hi]) lo = mid + 1;\n"
                    "            else hi = mid - 1;\n"
                    "        }\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
                "java": (
                    "public int search(int[] nums, int target) {\n"
                    "    int lo = 0, hi = nums.length - 1;\n"
                    "    while (lo <= hi) {\n"
                    "        int mid = (lo + hi) >>> 1;\n"
                    "        if (nums[mid] == target) return mid;\n"
                    "        if (nums[lo] <= nums[mid]) {\n"
                    "            if (nums[lo] <= target && target < nums[mid]) hi = mid - 1;\n"
                    "            else lo = mid + 1;\n"
                    "        } else {\n"
                    "            if (nums[mid] < target && target <= nums[hi]) lo = mid + 1;\n"
                    "            else hi = mid - 1;\n"
                    "        }\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Linear Scan (Baseline)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk the array and return the first matching index. Mention as the baseline only — it "
                "ignores both the sortedness and the O(log n) requirement."
            ),
            "code": {
                "python": (
                    "def search(nums, target):\n"
                    "    for i, x in enumerate(nums):\n"
                    "        if x == target:\n"
                    "            return i\n"
                    "    return -1"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Sorted + O(log n) screams binary search. But the array is rotated, so `nums[mid] < target` no longer reliably tells you which side to recurse on. Don't give up on binary search — adapt it.",
        "2. Key observation: when you split the array at any `mid`, *at least one* of the two halves [lo..mid] or [mid..hi] is still strictly sorted. Rotation creates exactly one 'break' point, and any split puts that break on one side only.",
        "3. Detect which half is sorted with a single compare: if `nums[lo] <= nums[mid]`, the left half is sorted; otherwise the right half is sorted.",
        "4. Once you know which half is sorted, you can check whether `target` lies inside its known min/max range in O(1). If yes, narrow there; if no, narrow into the other (unsorted-looking) half — and the recursion repeats.",
        "5. Worked example: `nums = [4,5,6,7,0,1,2]`, `target = 0`. lo=0, hi=6, mid=3, nums[mid]=7. nums[lo]=4 <= 7, so left half [4,5,6,7] is sorted. Is 0 in [4, 7)? No. → Search right: lo=4, hi=6, mid=5, nums[mid]=1. nums[lo]=0 <= 1, left half [0,1] is sorted. Is 0 in [0, 1)? Yes. → hi=4. lo=4, hi=4, mid=4, nums[mid]=0 == target → return 4.",
        "6. Edge case to be careful about: `nums[lo] <= nums[mid]` (note the `<=`). When lo == mid, the 'left half' is a single element and is trivially sorted; the `<=` keeps the invariant correct.",
        "7. Termination: `while lo <= hi`, and each branch strictly moves a pointer past `mid`, so the window shrinks every iteration → O(log n).",
    ],
    "tips": [
        "The `<=` in `nums[lo] <= nums[mid]` (not `<`) matters. Without it, the lo == mid case mis-classifies the trivially-sorted single-element half.",
        "The range checks use asymmetric bounds — `nums[lo] <= target < nums[mid]` and `nums[mid] < target <= nums[hi]` — because `nums[mid]` itself was already handled by the equality check above.",
        "Two-step alternative: binary-search the pivot (index of the minimum), then plain-binary-search the correct half. Same complexity, more lines, easier to explain — useful if the one-pass conditions confuse you under pressure.",
        "Follow-up — LeetCode 81: same problem with **duplicates** allowed. The single compare `nums[lo] <= nums[mid]` becomes ambiguous when they're equal (e.g., `[1,1,1,3,1]`). Standard fix: when `nums[lo] == nums[mid] == nums[hi]`, increment `lo` and decrement `hi` and retry. Worst case degrades to O(n).",
        "Follow-up — find the rotation pivot itself (LeetCode 153, 'Find Minimum in Rotated Sorted Array'). Same machinery; you're searching for the discontinuity instead of a value.",
    ],
    "companies": ["Amazon", "Microsoft", "Facebook", "Apple", "Bloomberg"],
    "topics": ["Array", "Binary Search"],
    "time_complexity": "O(log n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1


register(PAYLOAD, REFERENCE)
