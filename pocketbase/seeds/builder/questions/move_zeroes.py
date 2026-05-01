"""Move Zeroes — Easy. Two Pointers / In-Place Array.

The canonical 'partition without preserving the zero block' problem.
Two clean idioms — swap-based and overwrite-then-fill — and both are
worth knowing because they generalise to 'remove element', 'partition
by predicate', and 'sort colors'. Stable for the non-zero side, which
is the constraint that rules out a naive two-end swap.
"""
from copy import deepcopy

from builder.registry import register


PAYLOAD = {
    "title": "Move Zeroes",
    "difficulty": "Easy",
    "description": (
        "Given an integer array `nums`, move all `0`'s to the end of it while maintaining the **relative "
        "order** of the non-zero elements.\n\n"
        "You must do this **in-place** without making a copy of the array. Return the resulting array "
        "(for testing).\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [0,1,0,3,12]`\n"
        "- Output: `[1,3,12,0,0]`\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [0]`\n"
        "- Output: `[0]`"
    ),
    "hints": [
        "Two pointers. One scans (`read`); the other tracks the position where the next non-zero element should land (`write`).",
        "When `nums[read]` is non-zero, place it at `write` and advance `write`. Zeros are skipped — they get overwritten or swapped later.",
        "Variant A — swap: `swap(nums[read], nums[write])` whenever `nums[read] != 0`, then advance `write`. Maintains stability of non-zeros and pushes zeros rightward in one pass.",
        "Variant B — overwrite-then-fill: copy non-zeros forward in pass 1, then fill positions `[write..n-1]` with `0` in pass 2. Slightly more writes when the array is mostly zeros' worth thinking about.",
        "Stability matters: a naive 'swap zero with the last element' two-end approach reorders the non-zeros and is wrong here. Don't propose it.",
    ],
    "constraints": [
        "1 <= nums.length <= 10⁴",
        "-2³¹ <= nums[i] <= 2³¹ - 1",
        "Must operate in-place with O(1) extra space.",
    ],
    "starter_code": {
        "python": "def move_zeroes(nums):\n    # Modify nums in-place; return nums for testing\n    pass",
        "javascript": "function moveZeroes(nums) {\n    // Modify nums in-place; return nums for testing\n}",
        "java": "public int[] moveZeroes(int[] nums) {\n    // Modify nums in-place; return nums for testing\n    return nums;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[0,1,0,3,12], [0], [1,2,3], [0,0,0]]\n"
            "    for nums in cases:\n"
            "        print(f\"move_zeroes({nums}) = {move_zeroes(nums[:])}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[0,1,0,3,12], [0], [1,2,3], [0,0,0]].forEach(nums =>\n"
            "    console.log(`moveZeroes =`, moveZeroes([...nums]))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.Arrays;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(Arrays.toString(s.moveZeroes(new int[]{0,1,0,3,12})));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [0, 1, 0, 3, 12]}, "expected": [1, 3, 12, 0, 0],
         "description": "Classic LeetCode example", "tags": ["basic"]},
        {"input": {"nums": [0, 0, 0, 0]}, "expected": [0, 0, 0, 0],
         "description": "All zeros — array unchanged", "tags": ["edge"]},
        {"input": {"nums": [1, 2, 3, 4, 5]}, "expected": [1, 2, 3, 4, 5],
         "description": "No zeros — array unchanged", "tags": ["edge"]},
        {"input": {"nums": [0]}, "expected": [0],
         "description": "Single zero element", "tags": ["edge"]},
        {"input": {"nums": [7]}, "expected": [7],
         "description": "Single non-zero element", "tags": ["edge"]},
        {"input": {"nums": [0, 1, 0, 1, 0, 1]}, "expected": [1, 1, 1, 0, 0, 0],
         "description": "Alternating zeros and non-zeros", "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 3, 0, 0, 0]}, "expected": [1, 2, 3, 0, 0, 0],
         "description": "Trailing zeros only — already partitioned", "tags": ["tricky"]},
        {"input": {"nums": [0, 0, 0, 1, 2, 3]}, "expected": [1, 2, 3, 0, 0, 0],
         "description": "Leading zeros only — full shift", "tags": ["tricky"]},
        {"input": {"nums": [-1, 0, -2, 0, 3]}, "expected": [-1, -2, 3, 0, 0],
         "description": "Negative non-zeros are preserved like any other non-zero", "tags": ["tricky"]},
        {"input": {"nums": [4, 2, 4, 0, 0, 3, 0, 5, 1, 0]}, "expected": [4, 2, 4, 3, 5, 1, 0, 0, 0, 0],
         "description": "Mixed, requires stability of non-zeros", "tags": ["tricky"]},
        {"input": {"nums": [0] * 5000 + [1] * 5000}, "expected": [1] * 5000 + [0] * 5000,
         "description": "10K elements — half zeros leading, half ones trailing", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Two-Pointer Swap (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Maintain `write` — the index where the next non-zero should land. Scan with `read`. "
                "Whenever `nums[read]` is non-zero, swap it with `nums[write]` and advance `write`. "
                "Zeros are left to be overwritten by later non-zeros (or swapped to the tail). One pass; "
                "stability of the non-zero subsequence is preserved by construction."
            ),
            "code": {
                "python": (
                    "def move_zeroes(nums):\n"
                    "    write = 0\n"
                    "    for read in range(len(nums)):\n"
                    "        if nums[read] != 0:\n"
                    "            nums[write], nums[read] = nums[read], nums[write]\n"
                    "            write += 1\n"
                    "    return nums"
                ),
                "javascript": (
                    "function moveZeroes(nums) {\n"
                    "    let write = 0;\n"
                    "    for (let read = 0; read < nums.length; read++) {\n"
                    "        if (nums[read] !== 0) {\n"
                    "            [nums[write], nums[read]] = [nums[read], nums[write]];\n"
                    "            write++;\n"
                    "        }\n"
                    "    }\n"
                    "    return nums;\n"
                    "}"
                ),
                "java": (
                    "public int[] moveZeroes(int[] nums) {\n"
                    "    int write = 0;\n"
                    "    for (int read = 0; read < nums.length; read++) {\n"
                    "        if (nums[read] != 0) {\n"
                    "            int tmp = nums[write];\n"
                    "            nums[write] = nums[read];\n"
                    "            nums[read] = tmp;\n"
                    "            write++;\n"
                    "        }\n"
                    "    }\n"
                    "    return nums;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Two-Pointer Overwrite-Then-Fill",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Pass 1: copy every non-zero forward into position `write`, advancing `write`. Pass 2: "
                "from `write` to end, set every slot to `0`. Same asymptotics as swap; the swap version "
                "does fewer writes when there are many zeros (each non-zero costs one swap = two writes "
                "vs. one copy + one zero-fill = two writes — equivalent), but avoids the temporary on "
                "every iteration."
            ),
            "code": {
                "python": (
                    "def move_zeroes(nums):\n"
                    "    write = 0\n"
                    "    for read in range(len(nums)):\n"
                    "        if nums[read] != 0:\n"
                    "            nums[write] = nums[read]\n"
                    "            write += 1\n"
                    "    for i in range(write, len(nums)):\n"
                    "        nums[i] = 0\n"
                    "    return nums"
                ),
                "javascript": (
                    "function moveZeroes(nums) {\n"
                    "    let write = 0;\n"
                    "    for (let read = 0; read < nums.length; read++) {\n"
                    "        if (nums[read] !== 0) {\n"
                    "            nums[write++] = nums[read];\n"
                    "        }\n"
                    "    }\n"
                    "    for (let i = write; i < nums.length; i++) nums[i] = 0;\n"
                    "    return nums;\n"
                    "}"
                ),
                "java": (
                    "public int[] moveZeroes(int[] nums) {\n"
                    "    int write = 0;\n"
                    "    for (int read = 0; read < nums.length; read++) {\n"
                    "        if (nums[read] != 0) nums[write++] = nums[read];\n"
                    "    }\n"
                    "    for (int i = write; i < nums.length; i++) nums[i] = 0;\n"
                    "    return nums;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate the constraint: in-place, O(1) extra space, preserve relative order of non-zeros.",
        "2. Reject the naive 'two-end swap' (left index from start, right from end, swap when left is zero) — it does not preserve non-zero order. Easy interviewer trap.",
        "3. Reframe as a partition: imagine writing the non-zeros into a fresh array left-to-right. The next slot is `write`. That index is your second pointer.",
        "4. Variant A (swap): when you see a non-zero at `read`, swap it into `nums[write]`. Zero values get pushed right naturally. Single pass, stable.",
        "5. Variant B (overwrite-then-fill): copy non-zeros forward; zero out the tail. Two passes, but each iteration is simpler (no swap branch).",
        "6. Edge cases: all zeros (write stays at 0; nothing moves), no zeros (every element swaps with itself), single element (loop body is degenerate).",
    ],
    "tips": [
        "When `read == write`, the swap is a no-op (same index). It's safe — don't add a special-case branch for it.",
        "If the interviewer asks you to *minimize writes*, the swap version wins when zeros are sparse (one swap per non-zero). The overwrite-then-fill version wins when non-zeros are sparse (one copy per non-zero, then one bulk-fill).",
        "Generalises to 'Remove Element' (LC 27): replace `nums[read] != 0` with `nums[read] != val`. Same skeleton.",
        "Generalises to 'Partition by predicate'. Anything of the form 'keep these, push those to the end' is the same two-pointer idiom.",
        "Don't return a *new* array. The function modifies in-place; returning `nums` is purely for the test harness — the LeetCode submission is `void`.",
    ],
    "companies": ["Facebook", "Bloomberg", "Amazon", "Apple", "Microsoft"],
    "topics": ["Array", "Two Pointers"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    nums = deepcopy(nums)
    write = 0
    for read in range(len(nums)):
        if nums[read] != 0:
            nums[write], nums[read] = nums[read], nums[write]
            write += 1
    return nums


register(PAYLOAD, REFERENCE)
