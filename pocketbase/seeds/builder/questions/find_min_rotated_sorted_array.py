"""Find Minimum in Rotated Sorted Array — Medium. Binary Search.

The canonical 'modified binary search' problem. The trick is to compare
nums[mid] with nums[hi] (not nums[lo]) — that comparison alone tells you
which half holds the minimum, regardless of whether the array is rotated
or not. Master this and the rotated-search family (LC 33, 81, 154) all
fall into place.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Find Minimum in Rotated Sorted Array",
    "difficulty": "Medium",
    "description": (
        "Suppose an array of length `n` sorted in ascending order is **rotated** between 1 and n times. "
        "For example, `[0,1,2,4,5,6,7]` might become `[4,5,6,7,0,1,2]` (rotated 4 times) or `[0,1,2,4,5,6,7]` "
        "(rotated 7 times — back to itself).\n\n"
        "Given the sorted rotated array `nums` of **unique** elements, return *the minimum element of this "
        "array*.\n\n"
        "You must write an algorithm that runs in **O(log n) time**.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [3,4,5,1,2]`\n"
        "- Output: `1`\n"
        "- Explanation: The original array was `[1,2,3,4,5]`, rotated 3 times.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [4,5,6,7,0,1,2]`\n"
        "- Output: `0`\n"
        "- Explanation: The original array was `[0,1,2,4,5,6,7]`, rotated 4 times.\n\n"
        "**Example 3:**\n"
        "- Input: `nums = [11,13,15,17]`\n"
        "- Output: `11`\n"
        "- Explanation: The original array was `[11,13,15,17]`, rotated 4 times (back to itself)."
    ),
    "hints": [
        "Linear scan is O(n) — state it as a baseline, then beat it. The interviewer wants O(log n).",
        "Binary search, but on what predicate? You can't compare to a fixed target — there isn't one. Compare `nums[mid]` to a *boundary* of the current window instead.",
        "Compare `nums[mid]` with `nums[hi]`. If `nums[mid] > nums[hi]`, the rotation pivot (and therefore the minimum) is strictly to the *right* of `mid` — so `lo = mid + 1`.",
        "Otherwise (`nums[mid] <= nums[hi]`), the right half from `mid` to `hi` is sorted, so the minimum is at `mid` or to its left — so `hi = mid` (don't exclude `mid`, it might *be* the answer).",
        "Loop while `lo < hi`. When they meet, `nums[lo]` is the minimum. Comparing with `nums[lo]` instead of `nums[hi]` is the classic bug — it breaks on already-sorted inputs.",
    ],
    "constraints": [
        "n == nums.length",
        "1 <= n <= 5000",
        "-5000 <= nums[i] <= 5000",
        "All the integers of `nums` are unique.",
        "`nums` is sorted and rotated between 1 and n times.",
    ],
    "starter_code": {
        "python": "def find_min(nums):\n    # Your code here\n    pass",
        "javascript": "function findMin(nums) {\n    // Your code here\n}",
        "java": "public int findMin(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[3,4,5,1,2], [4,5,6,7,0,1,2], [11,13,15,17], [1]]\n"
            "    for nums in cases:\n"
            "        print(f\"find_min({nums}) = {find_min(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[3,4,5,1,2], [4,5,6,7,0,1,2], [11,13,15,17]].forEach(nums =>\n"
            "    console.log(`findMin =`, findMin(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.findMin(new int[]{3,4,5,1,2}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [3, 4, 5, 1, 2]}, "expected": 1,
         "description": "Standard rotation — min in second half", "tags": ["basic"]},
        {"input": {"nums": [4, 5, 6, 7, 0, 1, 2]}, "expected": 0,
         "description": "Larger rotation — pivot near middle", "tags": ["basic"]},
        {"input": {"nums": [11, 13, 15, 17]}, "expected": 11,
         "description": "No rotation (or rotated by n) — min is the first element", "tags": ["edge"]},
        {"input": {"nums": [2, 1]}, "expected": 1,
         "description": "Two-element rotation", "tags": ["edge"]},
        {"input": {"nums": [1]}, "expected": 1,
         "description": "Single element", "tags": ["edge"]},
        {"input": {"nums": [5, 1, 2, 3, 4]}, "expected": 1,
         "description": "Min at index 1 — pivot near the front", "tags": ["tricky"]},
        {"input": {"nums": [3, 1]}, "expected": 1,
         "description": "Two-element where mid==lo — exercises the comparison-with-hi insight", "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}, "expected": 1,
         "description": "Larger no-rotation — confirms the algorithm doesn't drift right", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Binary Search (Optimal)",
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
            "description": (
                "Two pointers `lo` and `hi`. At each step compare `nums[mid]` to `nums[hi]`. "
                "If `nums[mid] > nums[hi]`, the array is 'still rotated' on the right side, so the minimum "
                "lies strictly to the right of `mid` — move `lo = mid + 1`. Otherwise the right half is sorted "
                "and the minimum is at `mid` or somewhere to its left — move `hi = mid` (keep `mid` as a "
                "candidate). When `lo == hi` the minimum is `nums[lo]`."
            ),
            "code": {
                "python": (
                    "def find_min(nums):\n"
                    "    lo, hi = 0, len(nums) - 1\n"
                    "    while lo < hi:\n"
                    "        mid = (lo + hi) // 2\n"
                    "        if nums[mid] > nums[hi]:\n"
                    "            lo = mid + 1\n"
                    "        else:\n"
                    "            hi = mid\n"
                    "    return nums[lo]"
                ),
                "javascript": (
                    "function findMin(nums) {\n"
                    "    let lo = 0, hi = nums.length - 1;\n"
                    "    while (lo < hi) {\n"
                    "        const mid = (lo + hi) >> 1;\n"
                    "        if (nums[mid] > nums[hi]) lo = mid + 1;\n"
                    "        else hi = mid;\n"
                    "    }\n"
                    "    return nums[lo];\n"
                    "}"
                ),
                "java": (
                    "public int findMin(int[] nums) {\n"
                    "    int lo = 0, hi = nums.length - 1;\n"
                    "    while (lo < hi) {\n"
                    "        int mid = (lo + hi) >>> 1;\n"
                    "        if (nums[mid] > nums[hi]) lo = mid + 1;\n"
                    "        else hi = mid;\n"
                    "    }\n"
                    "    return nums[lo];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Linear Scan (Baseline)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk the array and track the running minimum. Mention as the baseline; the problem explicitly "
                "asks for O(log n), so submit the binary-search version."
            ),
            "code": {
                "python": (
                    "def find_min(nums):\n"
                    "    best = nums[0]\n"
                    "    for x in nums:\n"
                    "        if x < best:\n"
                    "            best = x\n"
                    "    return best"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Linear scan is O(n) — state it as the baseline, then beat it. The problem explicitly demands O(log n).",
        "2. Binary search needs a *predicate* that splits the search space. There's no fixed target here, so compare `nums[mid]` against a window boundary instead.",
        "3. Why compare with `nums[hi]` and not `nums[lo]`? Because if you compare with `nums[lo]`, an unrotated array (e.g. `[1,2,3,4,5]`) looks identical to a rotated one and you can't decide which half to discard. Comparing with `nums[hi]` resolves both cases uniformly.",
        "4. Case A — `nums[mid] > nums[hi]`: the segment `mid..hi` is *not* sorted, so it must contain the rotation pivot. The minimum is the pivot, which is strictly to the right of `mid` → `lo = mid + 1`.",
        "5. Case B — `nums[mid] <= nums[hi]`: the segment `mid..hi` *is* sorted, so its minimum is `nums[mid]`. The overall minimum is at `mid` or in the left half → `hi = mid` (do NOT do `hi = mid - 1`; you'd skip the candidate).",
        "6. Loop while `lo < hi`. The invariant is 'minimum is somewhere in `[lo, hi]`'. When the window collapses, `nums[lo]` is the answer. The loop runs ⌈log₂ n⌉ times.",
    ],
    "tips": [
        "The asymmetry — `lo = mid + 1` vs `hi = mid` — is intentional. `mid` can be the answer when the right half is sorted, so you must keep it as a candidate.",
        "Comparing with `nums[lo]` instead of `nums[hi]` is the classic bug. Try `[1,2,3]`: `nums[mid]=2 > nums[lo]=1`, you'd move `lo` and miss the true minimum at index 0.",
        "If the interviewer asks 'what if the array isn't rotated at all?', point out that it's just the rotated-by-n case and the algorithm naturally returns `nums[0]` because every comparison falls into the `hi = mid` branch.",
        "Follow-up — LC 154 'Find Minimum in Rotated Sorted Array II': allows duplicates. The trick: when `nums[mid] == nums[hi]` you can't tell which side the pivot is on, so do `hi -= 1` and shrink linearly. Worst-case O(n) — for example, `[1,1,1,1,0,1,1]`.",
        "Related — LC 33 'Search in Rotated Sorted Array': finds a target instead of the minimum. Same skeleton; pick the sorted half each iteration and decide whether the target lies in it.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg"],
    "topics": ["Array", "Binary Search"],
    "time_complexity": "O(log n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] > nums[hi]:
            lo = mid + 1
        else:
            hi = mid
    return nums[lo]


register(PAYLOAD, REFERENCE)
