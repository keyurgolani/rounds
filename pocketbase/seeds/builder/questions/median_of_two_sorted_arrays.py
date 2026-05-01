"""Median of Two Sorted Arrays — Hard. Binary Search / Divide and Conquer.

The canonical 'log-of-the-min' interview problem. The merge-then-pick
solution is O(m+n) and trivial; the expected solution is the partition
binary search that runs in O(log(min(m, n))). The trick is to stop
thinking about indices into the merged array and start thinking about
*partitions*: pick a split of the shorter array, derive the matching
split of the longer one, and binary-search until the four boundary
elements satisfy the median invariant.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Median of Two Sorted Arrays",
    "difficulty": "Hard",
    "description": (
        "Given two sorted arrays `nums1` and `nums2` of size `m` and `n` respectively, return the **median** "
        "of the two sorted arrays.\n\n"
        "The overall run time complexity should be `O(log(min(m, n)))`.\n\n"
        "**Example 1:**\n"
        "- Input: `nums1 = [1,3]`, `nums2 = [2]`\n"
        "- Output: `2.0`\n"
        "- Explanation: Merged array = `[1,2,3]`, median is `2`.\n\n"
        "**Example 2:**\n"
        "- Input: `nums1 = [1,2]`, `nums2 = [3,4]`\n"
        "- Output: `2.5`\n"
        "- Explanation: Merged array = `[1,2,3,4]`, median is `(2 + 3) / 2 = 2.5`.\n\n"
        "**Example 3:**\n"
        "- Input: `nums1 = []`, `nums2 = [1]`\n"
        "- Output: `1.0`"
    ),
    "hints": [
        "The naïve approach is to merge both arrays and pick the middle — O(m+n) time, O(m+n) space. State it as the baseline; it does not meet the required complexity.",
        "Two-pointer merge to the k-th element trims space to O(1) but still costs O(m+n). Closer, but still not log time.",
        "For log time, stop thinking about indices into the *merged* array. Think about a **partition**: a cut that puts the smaller half on the left of both arrays and the larger half on the right.",
        "Binary-search the cut on the **shorter** array. The cut on the longer array is forced by `i + j = (m + n + 1) // 2`. That makes the search space `[0, m]` where m is the shorter length.",
        "The partition is correct when `left1 <= right2` and `left2 <= right1`. If `left1 > right2`, move the cut left in nums1; otherwise move it right.",
        "Edge cases: empty array (return median of the other directly), cut at 0 (treat `left` as -inf), cut at length (treat `right` as +inf).",
    ],
    "constraints": [
        "nums1.length == m",
        "nums2.length == n",
        "0 <= m <= 1000",
        "0 <= n <= 1000",
        "1 <= m + n <= 2000",
        "-10⁶ <= nums1[i], nums2[i] <= 10⁶",
    ],
    "starter_code": {
        "python": "def find_median_sorted_arrays(nums1, nums2):\n    # Your code here\n    pass",
        "javascript": "function findMedianSortedArrays(nums1, nums2) {\n    // Your code here\n}",
        "java": "public double findMedianSortedArrays(int[] nums1, int[] nums2) {\n    // Your code here\n    return 0.0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([1,3], [2]), ([1,2], [3,4]), ([], [1])]\n"
            "    for a, b in cases:\n"
            "        print(f\"find_median_sorted_arrays({a}, {b}) = {find_median_sorted_arrays(a, b)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,3],[2]], [[1,2],[3,4]], [[],[1]]].forEach(([a, b]) =>\n"
            "    console.log(`findMedianSortedArrays =`, findMedianSortedArrays(a, b))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.findMedianSortedArrays(new int[]{1,3}, new int[]{2}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums1": [1, 3], "nums2": [2]}, "expected": 2.0,
         "description": "Odd total length — single middle element", "tags": ["basic"]},
        {"input": {"nums1": [1, 2], "nums2": [3, 4]}, "expected": 2.5,
         "description": "Even total length — average of two middles", "tags": ["basic"]},
        {"input": {"nums1": [], "nums2": [1]}, "expected": 1.0,
         "description": "One array empty — median of singleton", "tags": ["edge"]},
        {"input": {"nums1": [], "nums2": [2, 3]}, "expected": 2.5,
         "description": "One array empty — median of even-length other", "tags": ["edge"]},
        {"input": {"nums1": [1, 2, 3, 4, 5], "nums2": []}, "expected": 3.0,
         "description": "Other array empty — odd length", "tags": ["edge"]},
        {"input": {"nums1": [1, 3, 5, 7], "nums2": [2, 4, 6, 8]}, "expected": 4.5,
         "description": "Interleaved equal-size arrays — partition lands mid-merge", "tags": ["tricky"]},
        {"input": {"nums1": [1], "nums2": [2, 3, 4, 5]}, "expected": 3.0,
         "description": "Highly unbalanced sizes — binary search on the shorter array", "tags": ["tricky"]},
        {"input": {"nums1": [-5, 3, 6, 12, 15], "nums2": [-12, -10, -6, -3, 4, 10]}, "expected": 3.0,
         "description": "Negatives and uneven sizes — odd total length", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Binary Search on Partition (Optimal)",
            "time_complexity": "O(log(min(m, n)))",
            "space_complexity": "O(1)",
            "description": (
                "Binary-search a partition `i` in the shorter array; the partition `j` in the longer array is "
                "forced by `i + j = (m + n + 1) // 2`. The cut is correct when `left1 <= right2` and "
                "`left2 <= right1`. For odd total length the median is `max(left1, left2)`; for even, the "
                "average of `max(left1, left2)` and `min(right1, right2)`. Use ±inf sentinels for cuts at the "
                "ends of either array."
            ),
            "code": {
                "python": (
                    "def find_median_sorted_arrays(nums1, nums2):\n"
                    "    # Always binary-search the shorter array.\n"
                    "    if len(nums1) > len(nums2):\n"
                    "        nums1, nums2 = nums2, nums1\n"
                    "    m, n = len(nums1), len(nums2)\n"
                    "    half = (m + n + 1) // 2\n"
                    "    lo, hi = 0, m\n"
                    "    while lo <= hi:\n"
                    "        i = (lo + hi) // 2\n"
                    "        j = half - i\n"
                    "        left1 = nums1[i - 1] if i > 0 else float('-inf')\n"
                    "        right1 = nums1[i] if i < m else float('inf')\n"
                    "        left2 = nums2[j - 1] if j > 0 else float('-inf')\n"
                    "        right2 = nums2[j] if j < n else float('inf')\n"
                    "        if left1 <= right2 and left2 <= right1:\n"
                    "            if (m + n) % 2:\n"
                    "                return float(max(left1, left2))\n"
                    "            return (max(left1, left2) + min(right1, right2)) / 2\n"
                    "        if left1 > right2:\n"
                    "            hi = i - 1\n"
                    "        else:\n"
                    "            lo = i + 1\n"
                    "    return 0.0"
                ),
                "javascript": (
                    "function findMedianSortedArrays(nums1, nums2) {\n"
                    "    if (nums1.length > nums2.length) [nums1, nums2] = [nums2, nums1];\n"
                    "    const m = nums1.length, n = nums2.length;\n"
                    "    const half = Math.floor((m + n + 1) / 2);\n"
                    "    let lo = 0, hi = m;\n"
                    "    while (lo <= hi) {\n"
                    "        const i = Math.floor((lo + hi) / 2);\n"
                    "        const j = half - i;\n"
                    "        const left1 = i > 0 ? nums1[i - 1] : -Infinity;\n"
                    "        const right1 = i < m ? nums1[i] : Infinity;\n"
                    "        const left2 = j > 0 ? nums2[j - 1] : -Infinity;\n"
                    "        const right2 = j < n ? nums2[j] : Infinity;\n"
                    "        if (left1 <= right2 && left2 <= right1) {\n"
                    "            if ((m + n) % 2) return Math.max(left1, left2);\n"
                    "            return (Math.max(left1, left2) + Math.min(right1, right2)) / 2;\n"
                    "        }\n"
                    "        if (left1 > right2) hi = i - 1;\n"
                    "        else lo = i + 1;\n"
                    "    }\n"
                    "    return 0.0;\n"
                    "}"
                ),
                "java": (
                    "public double findMedianSortedArrays(int[] nums1, int[] nums2) {\n"
                    "    if (nums1.length > nums2.length) { int[] t = nums1; nums1 = nums2; nums2 = t; }\n"
                    "    int m = nums1.length, n = nums2.length;\n"
                    "    int half = (m + n + 1) / 2;\n"
                    "    int lo = 0, hi = m;\n"
                    "    while (lo <= hi) {\n"
                    "        int i = (lo + hi) / 2;\n"
                    "        int j = half - i;\n"
                    "        int left1 = i > 0 ? nums1[i - 1] : Integer.MIN_VALUE;\n"
                    "        int right1 = i < m ? nums1[i] : Integer.MAX_VALUE;\n"
                    "        int left2 = j > 0 ? nums2[j - 1] : Integer.MIN_VALUE;\n"
                    "        int right2 = j < n ? nums2[j] : Integer.MAX_VALUE;\n"
                    "        if (left1 <= right2 && left2 <= right1) {\n"
                    "            if (((m + n) & 1) == 1) return Math.max(left1, left2);\n"
                    "            return (Math.max(left1, left2) + Math.min(right1, right2)) / 2.0;\n"
                    "        }\n"
                    "        if (left1 > right2) hi = i - 1;\n"
                    "        else lo = i + 1;\n"
                    "    }\n"
                    "    return 0.0;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Two-Pointer Merge to k-th Element (Baseline)",
            "time_complexity": "O(m + n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk two pointers through both arrays, advancing the smaller head, until you've stepped past "
                "the median index. Tracks only the previous and current values so space stays constant. "
                "Trivial to write under pressure and a good 'I'd ship this and then optimise' answer if you "
                "blank on the partition idea."
            ),
            "code": {
                "python": (
                    "def find_median_sorted_arrays(nums1, nums2):\n"
                    "    m, n = len(nums1), len(nums2)\n"
                    "    total = m + n\n"
                    "    i = j = 0\n"
                    "    prev = curr = 0\n"
                    "    for _ in range(total // 2 + 1):\n"
                    "        prev = curr\n"
                    "        if i < m and (j >= n or nums1[i] <= nums2[j]):\n"
                    "            curr = nums1[i]\n"
                    "            i += 1\n"
                    "        else:\n"
                    "            curr = nums2[j]\n"
                    "            j += 1\n"
                    "    if total % 2:\n"
                    "        return float(curr)\n"
                    "    return (prev + curr) / 2"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force: merge both arrays, return the middle (or average of the two middles). O(m+n) time, O(m+n) space. Always state this first.",
        "2. Trim the space: two-pointer walk to the k-th element keeps only `prev` and `curr`. Still O(m+n) — does not satisfy the required log bound.",
        "3. Reframe in terms of *partitions* rather than merged indices. A correct partition splits both arrays so that everything on the left is ≤ everything on the right, and the left side has exactly `(m+n+1)//2` elements.",
        "4. Pick the cut `i` in the shorter array (range `[0, m]`); the cut `j` in the longer array is forced: `j = (m+n+1)//2 - i`. That collapses two unknowns to one.",
        "5. Binary-search `i`. The partition is valid when `nums1[i-1] <= nums2[j]` and `nums2[j-1] <= nums1[i]`. If `nums1[i-1] > nums2[j]`, the cut in nums1 is too far right — move `hi` down. Otherwise move `lo` up.",
        "6. Read off the answer once valid: odd total → `max(left1, left2)`; even total → `(max(left1, left2) + min(right1, right2)) / 2`.",
        "7. Edge handling falls out of using ±inf sentinels at the boundaries: cut at 0 means 'no left element', cut at length means 'no right element'. Both cases collapse to a single max/min comparison.",
    ],
    "tips": [
        "Always binary-search the shorter array. That's what makes the bound `log(min(m, n))`, and it also guarantees `j = half - i` stays in `[0, n]`.",
        "Use `(m + n + 1) // 2` for the left-side size — the `+1` makes the same formula work for both odd and even totals; the median element on odd lengths ends up as `max(left1, left2)`.",
        "Generalises directly to 'k-th smallest element in two sorted arrays' — same partition idea with `half` replaced by `k`.",
        "For the analogous problem on **k sorted arrays**, the partition trick no longer collapses cleanly; switch to a min-heap for `O((m+n) log k)`, which is the standard follow-up.",
        "Implement with sentinels (±inf) rather than nested `if` branches at the boundaries — far fewer off-by-ones, and the code reads as a single comparison block.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Adobe"],
    "topics": ["Array", "Binary Search", "Divide and Conquer"],
    "time_complexity": "O(log(min(m, n)))",
    "space_complexity": "O(1)",
}


def REFERENCE(nums1, nums2):
    if len(nums1) > len(nums2):
        nums1, nums2 = nums2, nums1
    m, n = len(nums1), len(nums2)
    half = (m + n + 1) // 2
    lo, hi = 0, m
    while lo <= hi:
        i = (lo + hi) // 2
        j = half - i
        left1 = nums1[i - 1] if i > 0 else float('-inf')
        right1 = nums1[i] if i < m else float('inf')
        left2 = nums2[j - 1] if j > 0 else float('-inf')
        right2 = nums2[j] if j < n else float('inf')
        if left1 <= right2 and left2 <= right1:
            if (m + n) % 2:
                return float(max(left1, left2))
            return (max(left1, left2) + min(right1, right2)) / 2
        if left1 > right2:
            hi = i - 1
        else:
            lo = i + 1
    return 0.0


register(PAYLOAD, REFERENCE)
