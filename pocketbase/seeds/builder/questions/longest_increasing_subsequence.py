"""Longest Increasing Subsequence — Medium. DP / Patience Sort + Binary Search.

The canonical 'two solutions' problem: O(n²) DP is the obvious one and
gets you most of the way there in an interview, but the O(n log n)
patience-sort variant is the kind of trick you either know or you don't.
Worth knowing both because the O(n²) version naturally extends to
reconstruction (parent pointers) and the bisect variant collapses the
'maintain a sorted structure of best tails' insight to four lines.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Longest Increasing Subsequence",
    "difficulty": "Medium",
    "description": (
        "Given an integer array `nums`, return the length of the longest **strictly increasing** "
        "subsequence.\n\n"
        "A *subsequence* is a sequence derived from the array by deleting some or no elements without "
        "changing the order of the remaining elements.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [10,9,2,5,3,7,101,18]`\n"
        "- Output: `4`\n"
        "- Explanation: One LIS is `[2,3,7,101]` (length 4). Another valid LIS is `[2,3,7,18]`.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [0,1,0,3,2,3]`\n"
        "- Output: `4`\n\n"
        "**Example 3:**\n"
        "- Input: `nums = [7,7,7,7,7]`\n"
        "- Output: `1`\n"
        "- Explanation: 'Strictly' increasing — duplicates do not extend the run."
    ),
    "hints": [
        "O(n²) DP: `dp[i]` = length of the LIS ending at index `i`. Transition: `dp[i] = 1 + max(dp[j] for j < i if nums[j] < nums[i])`.",
        "The answer is `max(dp)`, not `dp[-1]` — the LIS does not need to end at the last element.",
        "O(n log n): maintain a `tails` array where `tails[k]` = smallest possible tail of any increasing subsequence of length `k+1` seen so far.",
        "For each `x` in `nums`, binary-search the leftmost position in `tails` whose value is `>= x` and overwrite it. If `x` is bigger than every tail, append. The answer is `len(tails)`.",
        "Strict vs non-strict matters: strict → `bisect_left`; non-decreasing → `bisect_right`. One character change.",
    ],
    "constraints": [
        "1 <= nums.length <= 2500  (typical LC bound; the O(n log n) version handles 10⁵ comfortably)",
        "-10⁴ <= nums[i] <= 10⁴",
    ],
    "starter_code": {
        "python": "def length_of_lis(nums):\n    # Your code here\n    pass",
        "javascript": "function lengthOfLIS(nums) {\n    // Your code here\n}",
        "java": "public int lengthOfLIS(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[10,9,2,5,3,7,101,18], [0,1,0,3,2,3], [7,7,7,7,7]]\n"
            "    for nums in cases:\n"
            "        print(f\"length_of_lis({nums}) = {length_of_lis(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[10,9,2,5,3,7,101,18], [0,1,0,3,2,3], [7,7,7,7,7]].forEach(nums =>\n"
            "    console.log(`lengthOfLIS =`, lengthOfLIS(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.lengthOfLIS(new int[]{10,9,2,5,3,7,101,18}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [10, 9, 2, 5, 3, 7, 101, 18]}, "expected": 4,
         "description": "Classic example — [2,3,7,18] or [2,3,7,101]", "tags": ["basic"]},
        {"input": {"nums": [0, 1, 0, 3, 2, 3]}, "expected": 4,
         "description": "Duplicates and dips — LIS is [0,1,2,3]", "tags": ["basic"]},
        {"input": {"nums": [7, 7, 7, 7, 7]}, "expected": 1,
         "description": "Strict means equal does not extend — answer is 1",
         "tags": ["edge"]},
        {"input": {"nums": []}, "expected": 0,
         "description": "Empty array — no subsequence", "tags": ["edge"]},
        {"input": {"nums": [1]}, "expected": 1,
         "description": "Single element — LIS is itself", "tags": ["edge"]},
        {"input": {"nums": [1, 2, 3, 4, 5]}, "expected": 5,
         "description": "Already sorted — LIS is the whole array", "tags": ["tricky"]},
        {"input": {"nums": [5, 4, 3, 2, 1]}, "expected": 1,
         "description": "Strictly decreasing — best LIS is any single element", "tags": ["tricky"]},
        {"input": {"nums": [3, 1, 8, 2, 5]}, "expected": 3,
         "description": "Non-trivial — best LIS is [1,2,5] (or [3,8,*] cannot reach 3)",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Patience Sort + Binary Search (Optimal)",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "Maintain `tails`, where `tails[k]` is the smallest possible tail of any strictly "
                "increasing subsequence of length `k+1` we've seen so far. For each new element `x`:\n"
                "- Binary-search for the leftmost index `i` with `tails[i] >= x` (use `bisect_left`).\n"
                "- If `i == len(tails)`, append `x` (we found a longer LIS).\n"
                "- Otherwise overwrite `tails[i] = x` (we found a smaller tail for a length-(i+1) LIS).\n"
                "`len(tails)` at the end is the LIS length. Note: `tails` is not necessarily an actual LIS "
                "of `nums`, but its length is correct."
            ),
            "code": {
                "python": (
                    "from bisect import bisect_left\n"
                    "\n"
                    "def length_of_lis(nums):\n"
                    "    tails = []\n"
                    "    for x in nums:\n"
                    "        i = bisect_left(tails, x)\n"
                    "        if i == len(tails):\n"
                    "            tails.append(x)\n"
                    "        else:\n"
                    "            tails[i] = x\n"
                    "    return len(tails)"
                ),
                "javascript": (
                    "function lengthOfLIS(nums) {\n"
                    "    const tails = [];\n"
                    "    for (const x of nums) {\n"
                    "        let lo = 0, hi = tails.length;\n"
                    "        while (lo < hi) {\n"
                    "            const mid = (lo + hi) >> 1;\n"
                    "            if (tails[mid] < x) lo = mid + 1;\n"
                    "            else hi = mid;\n"
                    "        }\n"
                    "        if (lo === tails.length) tails.push(x);\n"
                    "        else tails[lo] = x;\n"
                    "    }\n"
                    "    return tails.length;\n"
                    "}"
                ),
                "java": (
                    "public int lengthOfLIS(int[] nums) {\n"
                    "    int[] tails = new int[nums.length];\n"
                    "    int size = 0;\n"
                    "    for (int x : nums) {\n"
                    "        int lo = 0, hi = size;\n"
                    "        while (lo < hi) {\n"
                    "            int mid = (lo + hi) >>> 1;\n"
                    "            if (tails[mid] < x) lo = mid + 1;\n"
                    "            else hi = mid;\n"
                    "        }\n"
                    "        tails[lo] = x;\n"
                    "        if (lo == size) size++;\n"
                    "    }\n"
                    "    return size;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Dynamic Programming (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(n)",
            "description": (
                "`dp[i]` = length of the LIS ending exactly at index `i`. For each `i`, look back at every "
                "`j < i` with `nums[j] < nums[i]` and take `dp[i] = 1 + max(dp[j])`. The answer is the "
                "global max of `dp`. Easy to write, easy to extend to reconstruction (track parent indices)."
            ),
            "code": {
                "python": (
                    "def length_of_lis(nums):\n"
                    "    if not nums:\n"
                    "        return 0\n"
                    "    n = len(nums)\n"
                    "    dp = [1] * n\n"
                    "    for i in range(1, n):\n"
                    "        for j in range(i):\n"
                    "            if nums[j] < nums[i]:\n"
                    "                dp[i] = max(dp[i], dp[j] + 1)\n"
                    "    return max(dp)"
                ),
            },
        },
        {
            "title": "Patience Sort with Subsequence Reconstruction",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "Same patience-sort skeleton, but we also record, for each position `i` in the original "
                "array, which length-bucket it landed in (`length_at[i]`) and the index of the element that "
                "preceded it in its LIS (`parent[i]`). After the scan, walk back from the index that ended "
                "up in the highest bucket to reconstruct one valid LIS."
            ),
            "code": {
                "python": (
                    "from bisect import bisect_left\n"
                    "\n"
                    "def longest_increasing_subsequence(nums):\n"
                    "    if not nums:\n"
                    "        return []\n"
                    "    n = len(nums)\n"
                    "    tails_vals = []   # tails[k] = best tail value for length k+1\n"
                    "    tails_idx = []    # index in nums of that tail\n"
                    "    parent = [-1] * n\n"
                    "    for i, x in enumerate(nums):\n"
                    "        k = bisect_left(tails_vals, x)\n"
                    "        if k > 0:\n"
                    "            parent[i] = tails_idx[k - 1]\n"
                    "        if k == len(tails_vals):\n"
                    "            tails_vals.append(x)\n"
                    "            tails_idx.append(i)\n"
                    "        else:\n"
                    "            tails_vals[k] = x\n"
                    "            tails_idx[k] = i\n"
                    "    # Walk parent pointers from the tail of the longest run.\n"
                    "    out = []\n"
                    "    cur = tails_idx[-1]\n"
                    "    while cur != -1:\n"
                    "        out.append(nums[cur])\n"
                    "        cur = parent[cur]\n"
                    "    return out[::-1]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force is 2ⁿ (every subsequence). Useless beyond n≈20. State it, move on.",
        "2. DP framing: define `dp[i]` = length of the LIS *ending at index i*. The 'ending at' constraint is what makes the recurrence clean.",
        "3. Transition: `dp[i] = 1 + max(dp[j] for j < i if nums[j] < nums[i])`, with `dp[i] = 1` if no such `j` exists. Answer = `max(dp)`.",
        "4. That's O(n²). For n up to ~2500 it's fine; for 10⁵ you need better.",
        "5. Key insight for O(n log n): we don't actually care about the *full* LIS — only the smallest possible tail for each achievable length. Maintain `tails[]` where `tails[k]` = smallest tail of any length-(k+1) increasing subsequence seen so far.",
        "6. `tails[]` is monotonically increasing by construction → binary search to find where each new element belongs (`bisect_left` for strict). Either extend (append) or improve (overwrite).",
        "7. Edge cases: empty input → 0; single element → 1; all duplicates → 1 (because *strictly* increasing).",
    ],
    "tips": [
        "Strictly vs non-strictly increasing is a one-character change: `bisect_left` for strict, `bisect_right` for non-decreasing. Confirm which the interviewer wants before coding.",
        "If asked to *reconstruct* an actual LIS (not just its length), the O(n²) DP is easier to extend — track a `parent[i]` index alongside `dp[i]`, then walk back from the argmax. The patience-sort version can do it too but the bookkeeping is fiddlier.",
        "`tails[]` is *not* a valid LIS of the array — its length is right but its contents may interleave elements that never coexisted in any single subsequence. Don't print it as the answer.",
        "The 'longest non-decreasing subsequence' variant (allow equal) shows up often. `bisect_right` instead of `bisect_left`. Double-check by hand on `[7,7,7,7,7]` — strict gives 1, non-decreasing gives 5.",
        "Common follow-ups: count the number of LIS (LC 673 — augment the O(n²) DP with a count array), Russian Doll Envelopes (LC 354 — sort cleverly then reduce to LIS), Longest Common Subsequence (different problem, different DP).",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Bloomberg"],
    "topics": ["Array", "Binary Search", "Dynamic Programming"],
    "time_complexity": "O(n log n)",
    "space_complexity": "O(n)",
}


def REFERENCE(nums):
    from bisect import bisect_left
    tails = []
    for x in nums:
        i = bisect_left(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return len(tails)


register(PAYLOAD, REFERENCE)
