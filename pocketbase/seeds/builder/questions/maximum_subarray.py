"""Maximum Subarray — Medium. Kadane's Algorithm / DP.

The canonical 'running sum that resets when it goes negative' problem.
Often the first DP problem candidates encounter that doesn't *look*
like DP. The Kadane recurrence is one line, but the all-negative case
trips up everyone who initialises `best = 0`. Divide-and-conquer is
the textbook follow-up — slower, but it generalises to the parallel
and segment-tree variants.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Maximum Subarray",
    "difficulty": "Medium",
    "description": (
        "Given an integer array `nums`, find the **contiguous subarray** (containing at least one number) "
        "which has the largest sum and return its sum.\n\n"
        "A subarray is a **contiguous** non-empty sequence of elements within an array.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [-2,1,-3,4,-1,2,1,-5,4]`\n"
        "- Output: `6`\n"
        "- Explanation: The subarray `[4,-1,2,1]` has the largest sum `6`.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [1]`\n"
        "- Output: `1`\n\n"
        "**Example 3:**\n"
        "- Input: `nums = [5,4,-1,7,8]`\n"
        "- Output: `23`\n"
        "- Explanation: The whole array sums to `23`.\n\n"
        "**Follow-up:** If you have figured out the O(n) solution, try coding another solution using the "
        "**divide and conquer** approach, which is more subtle."
    ),
    "hints": [
        "Brute force: every (i, j) pair → O(n²) (or O(n³) if you re-sum each time). State it; never submit it for n up to 10⁵.",
        "Key Kadane insight: a negative running sum can never help a future subarray — drop it and start fresh from the next element.",
        "Maintain `current` (best sum ending *exactly here*) and `best` (best seen anywhere). At each step: `current = max(nums[i], current + nums[i])`, `best = max(best, current)`.",
        "Initialise `best` and `current` to `nums[0]`, not 0. Otherwise an all-negative array (e.g. `[-3,-1,-2]`) wrongly returns 0 instead of `-1`.",
        "Divide-and-conquer follow-up: split, recurse on each half, then handle the case where the answer crosses the midpoint by extending left and right from the middle. O(n log n).",
    ],
    "constraints": [
        "1 <= nums.length <= 10⁵",
        "-10⁴ <= nums[i] <= 10⁴",
    ],
    "starter_code": {
        "python": "def max_sub_array(nums):\n    # Your code here\n    pass",
        "javascript": "function maxSubArray(nums) {\n    // Your code here\n}",
        "java": "public int maxSubArray(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[-2,1,-3,4,-1,2,1,-5,4], [1], [5,4,-1,7,8], [-3,-1,-2]]\n"
            "    for nums in cases:\n"
            "        print(f\"max_sub_array({nums}) = {max_sub_array(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[-2,1,-3,4,-1,2,1,-5,4], [1], [5,4,-1,7,8]].forEach(nums =>\n"
            "    console.log(`maxSubArray =`, maxSubArray(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.maxSubArray(new int[]{-2,1,-3,4,-1,2,1,-5,4}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [-2, 1, -3, 4, -1, 2, 1, -5, 4]}, "expected": 6,
         "description": "Classic LeetCode example — best window is [4,-1,2,1]", "tags": ["basic"]},
        {"input": {"nums": [1]}, "expected": 1,
         "description": "Single positive element", "tags": ["edge"]},
        {"input": {"nums": [-1]}, "expected": -1,
         "description": "Single negative element — must return the element itself, not 0", "tags": ["edge"]},
        {"input": {"nums": [5, 4, -1, 7, 8]}, "expected": 23,
         "description": "Whole array is the best subarray", "tags": ["basic"]},
        {"input": {"nums": [-3, -1, -2]}, "expected": -1,
         "description": "All negative — must return the largest single element (the Kadane gotcha)",
         "tags": ["tricky"]},
        {"input": {"nums": [-5, -4, -3, -2, -1]}, "expected": -1,
         "description": "Monotonically increasing all-negative — answer is the last element", "tags": ["tricky"]},
        {"input": {"nums": [3, -2, 5, -1]}, "expected": 6,
         "description": "Reset would lose; carrying the negative dip pays off", "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 3, 4, 5]}, "expected": 15,
         "description": "All positive — sum the whole array", "tags": ["basic"]},
        {"input": {"nums": [0, 0, 0, 0]}, "expected": 0,
         "description": "All zeros — answer is 0", "tags": ["edge"]},
        {"input": {"nums": list(range(-100, 101))}, "expected": 5050,
         "description": "Symmetric -100..100 — best window is 0..100 summing to 5050", "tags": ["large"]},
        {"input": {"nums": [10000] * 10000}, "expected": 100000000,
         "description": "10K copies of 10⁴ — full-range sum", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Kadane's Algorithm (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk left-to-right maintaining `current` — the maximum-sum subarray ending exactly at this "
                "index. At each step, either extend the previous window (`current + nums[i]`) or start fresh "
                "from `nums[i]`, whichever is larger. The global answer is the running maximum of `current`. "
                "Initialise both `current` and `best` to `nums[0]` so an all-negative array correctly returns "
                "the largest element rather than 0."
            ),
            "code": {
                "python": (
                    "def max_sub_array(nums):\n"
                    "    current = best = nums[0]\n"
                    "    for x in nums[1:]:\n"
                    "        current = max(x, current + x)\n"
                    "        best = max(best, current)\n"
                    "    return best"
                ),
                "javascript": (
                    "function maxSubArray(nums) {\n"
                    "    let current = nums[0], best = nums[0];\n"
                    "    for (let i = 1; i < nums.length; i++) {\n"
                    "        current = Math.max(nums[i], current + nums[i]);\n"
                    "        best = Math.max(best, current);\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "public int maxSubArray(int[] nums) {\n"
                    "    int current = nums[0], best = nums[0];\n"
                    "    for (int i = 1; i < nums.length; i++) {\n"
                    "        current = Math.max(nums[i], current + nums[i]);\n"
                    "        best = Math.max(best, current);\n"
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
                "Try every starting index, extend rightward accumulating the running sum, and track the "
                "maximum. Mention as the baseline; never submit for n up to 10⁵."
            ),
            "code": {
                "python": (
                    "def max_sub_array(nums):\n"
                    "    best = nums[0]\n"
                    "    for i in range(len(nums)):\n"
                    "        s = 0\n"
                    "        for j in range(i, len(nums)):\n"
                    "            s += nums[j]\n"
                    "            if s > best:\n"
                    "                best = s\n"
                    "    return best"
                ),
            },
        },
        {
            "title": "Divide and Conquer",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(log n)",
            "description": (
                "Split the array in half. The best subarray is either entirely in the left half, entirely "
                "in the right half, or it crosses the midpoint. The crossing case is solved in O(n) by "
                "extending greedily from the middle outward in both directions. Recurrence T(n) = 2T(n/2) + "
                "O(n) → O(n log n). Slower than Kadane, but the textbook follow-up and the basis for the "
                "segment-tree solution that supports range-update queries."
            ),
            "code": {
                "python": (
                    "def max_sub_array(nums):\n"
                    "    def helper(lo, hi):\n"
                    "        if lo == hi:\n"
                    "            return nums[lo]\n"
                    "        mid = (lo + hi) // 2\n"
                    "        left_best = helper(lo, mid)\n"
                    "        right_best = helper(mid + 1, hi)\n"
                    "        # Best crossing subarray: extend left from mid, right from mid+1.\n"
                    "        s = 0\n"
                    "        left_cross = float('-inf')\n"
                    "        for i in range(mid, lo - 1, -1):\n"
                    "            s += nums[i]\n"
                    "            left_cross = max(left_cross, s)\n"
                    "        s = 0\n"
                    "        right_cross = float('-inf')\n"
                    "        for i in range(mid + 1, hi + 1):\n"
                    "            s += nums[i]\n"
                    "            right_cross = max(right_cross, s)\n"
                    "        return max(left_best, right_best, left_cross + right_cross)\n"
                    "    return helper(0, len(nums) - 1)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force is O(n²) (or O(n³) if you re-sum each window). State it as the baseline, then immediately propose better.",
        "2. Key observation: if the running sum of a prefix has gone *negative*, prepending it to any future subarray strictly hurts. Drop it and restart from the next element.",
        "3. Define `current[i]` = max-sum subarray ending exactly at index i. The recurrence is `current[i] = max(nums[i], current[i-1] + nums[i])` — either extend the previous window or restart fresh.",
        "4. The global answer is `max(current[i])` across all i. Track it with a running scalar; no array needed → O(1) space.",
        "5. Initialise both `current` and `best` to `nums[0]` (not 0). Then iterate from index 1. This handles the all-negative case correctly: the answer is the largest single element, which is negative.",
        "6. Walk an example like `[-2,1,-3,4,-1,2,1,-5,4]` by hand. `current` resets to 4 at index 3 (because `-1 + 1 = 0 < 4`), accumulates 4→3→5→6, then drops to 1 at index 7. `best = 6`.",
        "7. For the divide-and-conquer follow-up: split, recurse on each half, then handle the crossing case in O(n) by extending greedily from the midpoint. Recurrence is the same as merge sort → O(n log n).",
    ],
    "tips": [
        "The all-negative gotcha: initialise `best = nums[0]`, not `best = 0`. Half of all candidates miss this; explicitly call it out when you write the initialiser.",
        "Equivalent phrasing: `current = max(0, current) + nums[i]` works *only* if you've already special-cased the all-negative array. The `max(nums[i], current + nums[i])` form handles it uniformly — prefer it.",
        "Kadane is the prefix-sum problem in disguise: `max subarray sum = max(prefix[j]) - min(prefix[i]) for i < j`. Mention this if the interviewer asks where the algorithm comes from.",
        "Common follow-up: return the *indices* of the best subarray, not just the sum. Track `start` (last reset point) and `end` (where `best` was last updated) alongside the scalars.",
        "Common follow-up: divide-and-conquer for the segment-tree variant that supports point updates and range-max-subarray queries in O(log n) per op. Each node stores (best, prefix_max, suffix_max, total) — a classic interview escalation.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg", "Apple", "Google"],
    "topics": ["Array", "Dynamic Programming", "Divide and Conquer"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    current = best = nums[0]
    for x in nums[1:]:
        current = max(x, current + x)
        best = max(best, current)
    return best


register(PAYLOAD, REFERENCE)
