"""Remove Duplicates from Sorted Array — Easy. Two Pointers / In-place.

The canonical 'write index vs read index' two-pointer pattern. Sorted
input is the gift — duplicates cluster, so a single comparison with the
previous *kept* element is enough to decide whether to write. Foundation
for Remove Duplicates II, Move Zeroes, and the partition step in Dutch
National Flag. Worth getting the index bookkeeping muscle memory right.
"""
import copy

from builder.registry import register


PAYLOAD = {
    "title": "Remove Duplicates from Sorted Array",
    "difficulty": "Easy",
    "description": (
        "Given an integer array `nums` sorted in **non-decreasing order**, remove the duplicates "
        "**in-place** such that each unique element appears only once. The relative order of the "
        "elements should be kept the same.\n\n"
        "Return `k` — the number of unique elements in `nums`. The first `k` slots of `nums` must "
        "hold the unique values (in their original sorted order); what you leave beyond index `k` "
        "does not matter.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,1,2]`\n"
        "- Output: `k = 2`, with `nums = [1,2,_]`\n"
        "- Explanation: Your function should return `k = 2`, and the first two elements of `nums` "
        "are `1` and `2`. It does not matter what you leave beyond the returned `k`.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [0,0,1,1,1,2,2,3,3,4]`\n"
        "- Output: `k = 5`, with `nums = [0,1,2,3,4,_,_,_,_,_]`\n"
        "- Explanation: The first five elements are `0, 1, 2, 3, 4`. The trailing slots are ignored."
    ),
    "hints": [
        "The array is sorted — duplicates always sit next to each other. You only ever need to compare "
        "the current element to the previous *kept* element.",
        "Two pointers: `k` is the **write index** (next slot to fill with a unique value), `i` is the "
        "**read index** that scans every element.",
        "Initialise `k = 1` and `i = 1` (the first element is always unique). Walk `i` from 1 to "
        "`len(nums) - 1`.",
        "On each step, only write when `nums[i] != nums[i - 1]`: do `nums[k] = nums[i]; k += 1`. "
        "Otherwise skip — it's a duplicate.",
        "Return `k` at the end. The first `k` slots hold the deduplicated prefix; the tail is "
        "garbage you don't need to clear.",
    ],
    "constraints": [
        "1 <= nums.length <= 3 * 10⁴ (problem-stated; treat empty array as a defensive edge case)",
        "-100 <= nums[i] <= 100",
        "`nums` is sorted in non-decreasing order.",
    ],
    "starter_code": {
        "python": "def remove_duplicates(nums):\n    # Modify nums in-place and return the new length k.\n    pass",
        "javascript": "function removeDuplicates(nums) {\n    // Modify nums in-place and return the new length k.\n}",
        "java": "public int removeDuplicates(int[] nums) {\n    // Modify nums in-place and return the new length k.\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[1,1,2], [0,0,1,1,1,2,2,3,3,4], [1]]\n"
            "    for nums in cases:\n"
            "        original = list(nums)\n"
            "        k = remove_duplicates(nums)\n"
            "        print(f\"remove_duplicates({original}) -> k={k}, prefix={nums[:k]}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,1,2], [0,0,1,1,1,2,2,3,3,4]].forEach(nums => {\n"
            "    const original = [...nums];\n"
            "    const k = removeDuplicates(nums);\n"
            "    console.log(`removeDuplicates(${JSON.stringify(original)}) -> k=${k}, prefix=${JSON.stringify(nums.slice(0, k))}`);\n"
            "});"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.Arrays;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[] nums = {0,0,1,1,1,2,2,3,3,4};\n"
            "        int k = s.removeDuplicates(nums);\n"
            "        System.out.println(\"k=\" + k + \", prefix=\" + Arrays.toString(Arrays.copyOf(nums, k)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 1, 2]}, "expected": [1, 2],
         "description": "Classic LC example — one duplicate run", "tags": ["basic"]},
        {"input": {"nums": [0, 0, 1, 1, 1, 2, 2, 3, 3, 4]}, "expected": [0, 1, 2, 3, 4],
         "description": "Classic LC example — multiple duplicate runs", "tags": ["basic"]},
        {"input": {"nums": []}, "expected": [],
         "description": "Empty array — defensive edge case", "tags": ["edge"]},
        {"input": {"nums": [1]}, "expected": [1],
         "description": "Single element — already unique", "tags": ["edge"]},
        {"input": {"nums": [1, 1, 1]}, "expected": [1],
         "description": "All duplicates — collapses to one", "tags": ["edge"]},
        {"input": {"nums": [1, 2, 3]}, "expected": [1, 2, 3],
         "description": "Strictly increasing — no duplicates to remove", "tags": ["edge"]},
        {"input": {"nums": [-3, -3, -2, -1, -1, 0, 1, 1]}, "expected": [-3, -2, -1, 0, 1],
         "description": "Negatives mixed with non-negatives", "tags": ["tricky"]},
        {"input": {"nums": [-100, -100, -100, 0, 0, 100, 100, 100]}, "expected": [-100, 0, 100],
         "description": "Three runs at the constraint extremes", "tags": ["tricky"]},
        {"input": {"nums": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]}, "expected": [1, 2, 3, 4, 5, 6],
         "description": "Every value appears exactly twice — long alternating runs", "tags": ["tricky"]},
        {"input": {"nums": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2]}, "expected": [0, 1, 2],
         "description": "Three large equal-size chunks", "tags": ["tricky"]},
        {"input": {"nums": [-1, -1, -1, -1, -1, -1, -1]}, "expected": [-1],
         "description": "Long run of one negative value", "tags": ["edge"]},
        {"input": {"nums": sorted([i // 3 for i in range(300)])}, "expected": list(range(100)),
         "description": "300-element sorted array with each value repeated 3× — large multi-run",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Two Pointers (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Maintain a write pointer `k` and a read pointer `i`. The first element is always "
                "unique, so start both at 1. For each `i`, compare `nums[i]` against `nums[i - 1]`: "
                "if they differ, the value at `i` is the start of a new run — write it to `nums[k]` "
                "and advance `k`. Otherwise it's a duplicate and we skip. One pass, in-place, "
                "constant extra space."
            ),
            "code": {
                "python": (
                    "def remove_duplicates(nums):\n"
                    "    if not nums:\n"
                    "        return 0\n"
                    "    k = 1\n"
                    "    for i in range(1, len(nums)):\n"
                    "        if nums[i] != nums[i - 1]:\n"
                    "            nums[k] = nums[i]\n"
                    "            k += 1\n"
                    "    return k"
                ),
                "javascript": (
                    "function removeDuplicates(nums) {\n"
                    "    if (nums.length === 0) return 0;\n"
                    "    let k = 1;\n"
                    "    for (let i = 1; i < nums.length; i++) {\n"
                    "        if (nums[i] !== nums[i - 1]) {\n"
                    "            nums[k] = nums[i];\n"
                    "            k++;\n"
                    "        }\n"
                    "    }\n"
                    "    return k;\n"
                    "}"
                ),
                "java": (
                    "public int removeDuplicates(int[] nums) {\n"
                    "    if (nums.length == 0) return 0;\n"
                    "    int k = 1;\n"
                    "    for (int i = 1; i < nums.length; i++) {\n"
                    "        if (nums[i] != nums[i - 1]) {\n"
                    "            nums[k] = nums[i];\n"
                    "            k++;\n"
                    "        }\n"
                    "    }\n"
                    "    return k;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Two Pointers — Compare Against Last Kept",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Equivalent variant that compares `nums[i]` against `nums[k - 1]` (the last *kept* "
                "value) rather than `nums[i - 1]`. Useful when the input is not strictly sorted but "
                "you still want to keep first occurrences only — the comparison key generalises."
            ),
            "code": {
                "python": (
                    "def remove_duplicates(nums):\n"
                    "    k = 0\n"
                    "    for x in nums:\n"
                    "        if k == 0 or x != nums[k - 1]:\n"
                    "            nums[k] = x\n"
                    "            k += 1\n"
                    "    return k"
                ),
                "javascript": (
                    "function removeDuplicates(nums) {\n"
                    "    let k = 0;\n"
                    "    for (const x of nums) {\n"
                    "        if (k === 0 || x !== nums[k - 1]) {\n"
                    "            nums[k] = x;\n"
                    "            k++;\n"
                    "        }\n"
                    "    }\n"
                    "    return k;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Re-read the problem: in-place, preserve order, return the new length. The tail beyond `k` does not matter.",
        "2. Notice the input is sorted — that's the only reason a single comparison against the previous element suffices to detect duplicates.",
        "3. Pick the two-pointer pattern: `k` (write) and `i` (read). Both start at 1 because index 0 is unique by definition.",
        "4. Walk `i` from 1 to n-1. If `nums[i] != nums[i - 1]`, copy to the write slot and bump `k`. Else skip.",
        "5. Return `k`. The first `k` slots are the deduplicated prefix; the rest is unspecified.",
        "6. Edge cases: empty array (return 0), single element (return 1), all duplicates (return 1), strictly increasing (return n).",
    ],
    "tips": [
        "Initialising both pointers at 1 lets you skip a redundant `nums[0] = nums[0]` self-write. Small thing, but interviewers notice.",
        "The tail of `nums` after index `k` is *not* required to be cleared — don't waste a second pass zeroing it.",
        "If you compare against `nums[k - 1]` instead of `nums[i - 1]`, the logic still works and generalises to unsorted-but-deduped-by-first-occurrence problems.",
        "Common follow-up — Remove Duplicates II: allow each value at most twice. Same skeleton, comparison becomes `nums[i] != nums[k - 2]`.",
        "Common follow-up — Move Zeroes: identical write-pointer pattern, the predicate is `x != 0`. Recognising the family saves implementation time under interview pressure.",
        "Don't reach for a `set` or a fresh list — that violates the in-place / O(1) extra space constraint, even if the test passes.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Bloomberg", "Apple", "Facebook"],
    "topics": ["Array", "Two Pointers"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    work = copy.deepcopy(nums)
    if not work:
        return []
    k = 1
    for i in range(1, len(work)):
        if work[i] != work[i - 1]:
            work[k] = work[i]
            k += 1
    return work[:k]


register(PAYLOAD, REFERENCE)
