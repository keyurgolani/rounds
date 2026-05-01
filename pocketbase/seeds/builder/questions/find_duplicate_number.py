"""Find the Duplicate Number — Medium. Floyd's Cycle Detection / Binary Search.

The classic 'array as implicit linked list' trick. Each index points to
`nums[i]`, and because values are in `[1, n]` while indices are `[0, n]`,
following `i → nums[i]` always stays in-bounds. A duplicate value means
two indices point to the same cell — i.e., a cycle. Floyd's tortoise &
hare finds the cycle entry in O(n) time and O(1) space without mutating
the array. The binary-search-on-value variant is the secondary answer
worth knowing — same space bound, slightly worse time.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Find the Duplicate Number",
    "difficulty": "Medium",
    "description": (
        "Given an array of integers `nums` containing `n + 1` integers where each integer is in the "
        "range `[1, n]` inclusive, there is **only one repeated number** in `nums`. Return *this* "
        "repeated number.\n\n"
        "You must solve the problem **without modifying** the array `nums` and use only **constant** "
        "extra space.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,3,4,2,2]`\n"
        "- Output: `2`\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [3,1,3,4,2]`\n"
        "- Output: `3`\n\n"
        "**Example 3:**\n"
        "- Input: `nums = [1,1]`\n"
        "- Output: `1`"
    ),
    "hints": [
        "Treat the array as an implicit linked list: from index `i`, the 'next' pointer is `nums[i]`. "
        "Because values are in `[1, n]` and there are `n + 1` slots, two indices must point to the "
        "same value — that's a cycle. Use Floyd's tortoise & hare to find its entry.",
        "Binary search on the *value range* `[1, n]`: for a candidate `m`, count how many `nums[i] <= m`. "
        "If the count exceeds `m`, the duplicate is in `[1, m]`; otherwise it's in `[m + 1, n]`. "
        "O(n log n) time, O(1) space, never mutates the array.",
        "Sorting works in O(n log n) but mutates the array — explicitly disallowed by the constraints. "
        "Mention it only as a baseline.",
        "A hash set gives O(n) time but O(n) space — also disallowed. Worth stating to show you read the "
        "constraints carefully.",
        "Bit-counting at each position gives another O(n log n) / O(1) approach but is rarely the cleanest "
        "answer in interview — Floyd's is the expected solution.",
    ],
    "constraints": [
        "1 <= n <= 10⁵",
        "nums.length == n + 1",
        "1 <= nums[i] <= n; all integers in nums appear only once except for exactly one which appears two or more times",
    ],
    "starter_code": {
        "python": "def find_duplicate(nums):\n    # Your code here\n    pass",
        "javascript": "function findDuplicate(nums) {\n    // Your code here\n}",
        "java": "public int findDuplicate(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[1,3,4,2,2], [3,1,3,4,2], [1,1], [2,2,2,2,2]]\n"
            "    for nums in cases:\n"
            "        print(f\"find_duplicate({nums}) = {find_duplicate(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,3,4,2,2], [3,1,3,4,2], [1,1]].forEach(nums =>\n"
            "    console.log(`findDuplicate =`, findDuplicate(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.findDuplicate(new int[]{1,3,4,2,2}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 3, 4, 2, 2]}, "expected": 2,
         "description": "Classic LC example — duplicate is 2", "tags": ["basic"]},
        {"input": {"nums": [3, 1, 3, 4, 2]}, "expected": 3,
         "description": "Classic LC example — duplicate is 3", "tags": ["basic"]},
        {"input": {"nums": [1, 1]}, "expected": 1,
         "description": "Minimum size n=1 — both slots hold the only value", "tags": ["edge"]},
        {"input": {"nums": [2, 1, 2, 3, 4]}, "expected": 2,
         "description": "Duplicate appears at the very start", "tags": ["edge"]},
        {"input": {"nums": [1, 2, 3, 4, 4]}, "expected": 4,
         "description": "Duplicate appears at the very end", "tags": ["edge"]},
        {"input": {"nums": [2, 2, 2, 2, 2]}, "expected": 2,
         "description": "Many copies of the same duplicate — algorithm still pinpoints it", "tags": ["tricky"]},
        {"input": {"nums": [5, 5, 5, 5, 5, 5]}, "expected": 5,
         "description": "All entries identical, n=5", "tags": ["tricky"]},
        {"input": {"nums": [3, 1, 4, 6, 2, 5, 7, 8, 9, 10, 6]}, "expected": 6,
         "description": "n=10 — duplicate buried in the middle", "tags": ["basic"]},
        {"input": {"nums": [1, 4, 6, 6, 6, 6, 6, 3, 2, 5]}, "expected": 6,
         "description": "n=9 — duplicate appears 5 times in a run", "tags": ["tricky"]},
        {"input": {"nums": [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 5]}, "expected": 5,
         "description": "Reverse-sorted prefix with trailing duplicate", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Floyd's Cycle Detection (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Treat the array as a function `f(i) = nums[i]`. Because values live in `[1, n]` and there "
                "are `n + 1` slots, the iterated sequence starting from index 0 must eventually revisit a "
                "value — and the *only* way two indices map to the same cell is via the duplicate. So the "
                "implicit linked list contains a cycle whose entry point is the duplicate.\n\n"
                "Phase 1 — find a meeting point inside the cycle: advance `slow` by one step and `fast` by "
                "two until they collide.\n"
                "Phase 2 — find the cycle entry: reset one pointer to index 0, then advance both by one "
                "step. They meet at the duplicate (standard tortoise-and-hare proof: distance from start "
                "to entry equals distance from meeting point to entry).\n\n"
                "Pure index arithmetic — no mutation, no extra space, single pass-equivalent."
            ),
            "code": {
                "python": (
                    "def find_duplicate(nums):\n"
                    "    slow = fast = nums[0]\n"
                    "    while True:\n"
                    "        slow = nums[slow]\n"
                    "        fast = nums[nums[fast]]\n"
                    "        if slow == fast:\n"
                    "            break\n"
                    "    slow = nums[0]\n"
                    "    while slow != fast:\n"
                    "        slow = nums[slow]\n"
                    "        fast = nums[fast]\n"
                    "    return slow"
                ),
                "javascript": (
                    "function findDuplicate(nums) {\n"
                    "    let slow = nums[0], fast = nums[0];\n"
                    "    do {\n"
                    "        slow = nums[slow];\n"
                    "        fast = nums[nums[fast]];\n"
                    "    } while (slow !== fast);\n"
                    "    slow = nums[0];\n"
                    "    while (slow !== fast) {\n"
                    "        slow = nums[slow];\n"
                    "        fast = nums[fast];\n"
                    "    }\n"
                    "    return slow;\n"
                    "}"
                ),
                "java": (
                    "public int findDuplicate(int[] nums) {\n"
                    "    int slow = nums[0], fast = nums[0];\n"
                    "    do {\n"
                    "        slow = nums[slow];\n"
                    "        fast = nums[nums[fast]];\n"
                    "    } while (slow != fast);\n"
                    "    slow = nums[0];\n"
                    "    while (slow != fast) {\n"
                    "        slow = nums[slow];\n"
                    "        fast = nums[fast];\n"
                    "    }\n"
                    "    return slow;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Binary Search on Value Range",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(1)",
            "description": (
                "Binary search the answer over the value space `[1, n]`. For a midpoint `m`, count "
                "`c = #{i : nums[i] <= m}`. By pigeonhole, if `c > m` the duplicate lies in `[1, m]`; "
                "otherwise it lies in `[m + 1, n]`. Each iteration scans the array, so total work is "
                "`O(n log n)`. Doesn't mutate, uses two integers — fully satisfies the constraints. "
                "Worth knowing as a backup if Floyd's slips your mind under pressure."
            ),
            "code": {
                "python": (
                    "def find_duplicate(nums):\n"
                    "    lo, hi = 1, len(nums) - 1\n"
                    "    while lo < hi:\n"
                    "        mid = (lo + hi) // 2\n"
                    "        count = sum(1 for x in nums if x <= mid)\n"
                    "        if count > mid:\n"
                    "            hi = mid\n"
                    "        else:\n"
                    "            lo = mid + 1\n"
                    "    return lo"
                ),
                "javascript": (
                    "function findDuplicate(nums) {\n"
                    "    let lo = 1, hi = nums.length - 1;\n"
                    "    while (lo < hi) {\n"
                    "        const mid = (lo + hi) >> 1;\n"
                    "        let count = 0;\n"
                    "        for (const x of nums) if (x <= mid) count++;\n"
                    "        if (count > mid) hi = mid;\n"
                    "        else lo = mid + 1;\n"
                    "    }\n"
                    "    return lo;\n"
                    "}"
                ),
                "java": (
                    "public int findDuplicate(int[] nums) {\n"
                    "    int lo = 1, hi = nums.length - 1;\n"
                    "    while (lo < hi) {\n"
                    "        int mid = (lo + hi) >>> 1;\n"
                    "        int count = 0;\n"
                    "        for (int x : nums) if (x <= mid) count++;\n"
                    "        if (count > mid) hi = mid;\n"
                    "        else lo = mid + 1;\n"
                    "    }\n"
                    "    return lo;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Read the constraints carefully — *no mutation* and *O(1) space* kill sort, hash set, and "
        "in-place index-marking. State this out loud; it's the whole point of the problem.",
        "2. Reframe the array as a function `f(i) = nums[i]`. Indices `0..n`, values `1..n` — so the "
        "iteration `0 → nums[0] → nums[nums[0]] → ...` stays in-bounds forever and must eventually loop.",
        "3. Because the duplicate value is the only way two indices share a target, the cycle's entry "
        "point *is* the duplicate. Now it's literally LeetCode 142 (Linked List Cycle II) on an implicit "
        "list.",
        "4. Apply Floyd's: slow/fast collide somewhere inside the cycle, then reset slow to the head and "
        "advance both at speed 1; the next collision is the cycle entry, which is the duplicate.",
        "5. If Floyd's doesn't click, fall back to binary search on the value range — same space, slightly "
        "worse time, easier to derive on the spot.",
        "6. Sanity-check edge cases: `n=1` (`[1,1]` → 1), the duplicate at the start, the duplicate at "
        "the end, and the all-same case `[k,k,k,...,k]`.",
    ],
    "tips": [
        "The phrasing 'find without modifying nums and using O(1) extra space' is a *huge* hint pointing "
        "at Floyd's. If the interviewer relaxes either constraint, hash-set or sort becomes acceptable.",
        "Floyd's two-phase proof: if the cycle entry is `μ` steps from the start and the cycle length is "
        "`λ`, the meeting point is `μ` steps before the entry going forward. Resetting one pointer and "
        "stepping in lockstep meets exactly at `μ`.",
        "Why start `slow = fast = nums[0]` and not at index 0? Because index 0 may itself never be "
        "revisited — it's the 'tail' before the cycle. The cycle is in the *value space*, so we start "
        "at the first value.",
        "Binary-search variant generalises to 'find any number whose count exceeds its rank' — useful "
        "framing for k-th-smallest-in-sorted-matrix-style problems.",
        "Common follow-up — 'what if there can be multiple duplicates?' Floyd's still finds *one* of "
        "them; binary search finds the smallest. State this if asked.",
        "Common gotcha — candidates write `fast = nums[nums[fast]]` but forget the inner step is one "
        "advance, not two: it is `f(f(fast))`, two hops in a single statement. Don't accidentally write "
        "three.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Bloomberg", "Apple", "Adobe"],
    "topics": ["Array", "Two Pointers", "Binary Search", "Bit Manipulation"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    slow = fast = nums[0]
    while True:
        slow = nums[slow]
        fast = nums[nums[fast]]
        if slow == fast:
            break
    slow = nums[0]
    while slow != fast:
        slow = nums[slow]
        fast = nums[fast]
    return slow


register(PAYLOAD, REFERENCE)
