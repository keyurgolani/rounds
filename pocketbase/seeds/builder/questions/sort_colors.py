"""Sort Colors — Medium. Two Pointers / Dutch National Flag.

The classic Dijkstra Dutch National Flag problem. Three values, sort
in-place, one pass, O(1) extra space. The 'three pointers low/mid/high'
partition pattern is worth burning into muscle memory — it generalises
to 'partition around a pivot' (quicksort) and 'segregate by category'
problems. Counting sort is the fallback when you forget the pointer
dance under pressure.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Sort Colors",
    "difficulty": "Medium",
    "description": (
        "Given an array `nums` with `n` objects colored red, white, or blue, sort them **in-place** so that "
        "objects of the same color are adjacent, with the colors in the order red, white, and blue.\n\n"
        "We use the integers `0`, `1`, and `2` to represent the color red, white, and blue, respectively.\n\n"
        "You must solve this problem **without using the library's sort function**.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [2,0,2,1,1,0]`\n"
        "- Output: `[0,0,1,1,2,2]`\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [2,0,1]`\n"
        "- Output: `[0,1,2]`"
    ),
    "hints": [
        "Two-pass counting sort: count occurrences of 0, 1, 2 → overwrite the array. O(n) time, O(1) extra space, but two passes.",
        "One-pass Dutch National Flag: maintain three pointers — `low` (next 0 position), `mid` (current scan), `high` (next 2 position). Invariants: `[0..low-1]` are 0s, `[low..mid-1]` are 1s, `[high+1..n-1]` are 2s.",
        "At `nums[mid]`: if 0 → swap with `low`, advance both. If 1 → just advance `mid`. If 2 → swap with `high`, decrement `high` (do NOT advance `mid` — the swapped-in value is unexamined).",
        "The classic bug: advancing `mid` after swapping with `high`. The value that came from `high` hasn't been classified yet.",
        "Library sort would be O(n log n) — the problem explicitly forbids it. The whole point is to recognise that with only 3 distinct keys, you can do better than comparison sort.",
    ],
    "constraints": [
        "n == nums.length",
        "1 <= n <= 300",
        "nums[i] is either 0, 1, or 2",
    ],
    "starter_code": {
        "python": "def sort_colors(nums):\n    # Sort nums in-place. Return the sorted list.\n    pass",
        "javascript": "function sortColors(nums) {\n    // Sort nums in-place. Return the sorted array.\n}",
        "java": "public int[] sortColors(int[] nums) {\n    // Sort nums in-place. Return the sorted array.\n    return nums;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[2,0,2,1,1,0], [2,0,1], [0], [1,2,0]]\n"
            "    for nums in cases:\n"
            "        arr = list(nums)\n"
            "        sort_colors(arr)\n"
            "        print(f\"sort_colors({nums}) = {arr}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[2,0,2,1,1,0], [2,0,1], [0]].forEach(nums => {\n"
            "    const arr = [...nums];\n"
            "    sortColors(arr);\n"
            "    console.log(`sortColors =`, arr);\n"
            "});"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.Arrays;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[] nums = {2,0,2,1,1,0};\n"
            "        s.sortColors(nums);\n"
            "        System.out.println(Arrays.toString(nums));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [2, 0, 2, 1, 1, 0]}, "expected": [0, 0, 1, 1, 2, 2],
         "description": "Classic mixed case from the prompt", "tags": ["basic"]},
        {"input": {"nums": [2, 0, 1]}, "expected": [0, 1, 2],
         "description": "One of each — minimal mixed case", "tags": ["basic"]},
        {"input": {"nums": [0, 1, 2]}, "expected": [0, 1, 2],
         "description": "Already sorted — should still produce the same output", "tags": ["edge"]},
        {"input": {"nums": [2, 1, 0]}, "expected": [0, 1, 2],
         "description": "Reverse sorted — every element moves", "tags": ["edge"]},
        {"input": {"nums": [0, 0, 0, 0]}, "expected": [0, 0, 0, 0],
         "description": "All zeros — no swaps needed", "tags": ["edge"]},
        {"input": {"nums": [1, 1, 1]}, "expected": [1, 1, 1],
         "description": "All ones — `mid` walks through, no swaps", "tags": ["edge"]},
        {"input": {"nums": [2, 2, 2, 2]}, "expected": [2, 2, 2, 2],
         "description": "All twos — every element swaps with `high` then settles", "tags": ["edge"]},
        {"input": {"nums": [1]}, "expected": [1],
         "description": "Single element — trivial", "tags": ["edge"]},
        {"input": {"nums": [0]}, "expected": [0],
         "description": "Single zero", "tags": ["edge"]},
        {"input": {"nums": [2]}, "expected": [2],
         "description": "Single two", "tags": ["edge"]},
        {"input": {"nums": [1, 0]}, "expected": [0, 1],
         "description": "Two-element swap — 1 then 0", "tags": ["edge"]},
        {"input": {"nums": [2, 0]}, "expected": [0, 2],
         "description": "Two-element swap — 2 then 0 (classic three-pointer trap)", "tags": ["tricky"]},
        {"input": {"nums": [0, 0, 1, 1, 2, 2, 0, 1, 2]}, "expected": [0, 0, 0, 1, 1, 1, 2, 2, 2],
         "description": "Mixed with repeats — exercises all three pointer moves", "tags": ["tricky"]},
        {"input": {"nums": [2, 2, 1, 1, 0, 0]}, "expected": [0, 0, 1, 1, 2, 2],
         "description": "Reverse-sorted blocks — twos and zeros swap across", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Dutch National Flag (One Pass, Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Three pointers partition the array into four regions: `[0..low-1] = 0`, `[low..mid-1] = 1`, "
                "`[mid..high]` unscanned, `[high+1..n-1] = 2`. At each step examine `nums[mid]`. If 0, swap "
                "with `low` and advance both (the value coming from `low` is guaranteed to be 1 or `low == mid`, "
                "so it's safe to advance `mid`). If 1, just advance `mid`. If 2, swap with `high` and decrement "
                "`high` — but do NOT advance `mid`, because the value swapped in from `high` is unclassified. "
                "Loop while `mid <= high`."
            ),
            "code": {
                "python": (
                    "def sort_colors(nums):\n"
                    "    low, mid, high = 0, 0, len(nums) - 1\n"
                    "    while mid <= high:\n"
                    "        if nums[mid] == 0:\n"
                    "            nums[low], nums[mid] = nums[mid], nums[low]\n"
                    "            low += 1\n"
                    "            mid += 1\n"
                    "        elif nums[mid] == 1:\n"
                    "            mid += 1\n"
                    "        else:  # nums[mid] == 2\n"
                    "            nums[mid], nums[high] = nums[high], nums[mid]\n"
                    "            high -= 1\n"
                    "    return nums"
                ),
                "javascript": (
                    "function sortColors(nums) {\n"
                    "    let low = 0, mid = 0, high = nums.length - 1;\n"
                    "    while (mid <= high) {\n"
                    "        if (nums[mid] === 0) {\n"
                    "            [nums[low], nums[mid]] = [nums[mid], nums[low]];\n"
                    "            low++; mid++;\n"
                    "        } else if (nums[mid] === 1) {\n"
                    "            mid++;\n"
                    "        } else {\n"
                    "            [nums[mid], nums[high]] = [nums[high], nums[mid]];\n"
                    "            high--;\n"
                    "        }\n"
                    "    }\n"
                    "    return nums;\n"
                    "}"
                ),
                "java": (
                    "public int[] sortColors(int[] nums) {\n"
                    "    int low = 0, mid = 0, high = nums.length - 1;\n"
                    "    while (mid <= high) {\n"
                    "        if (nums[mid] == 0) {\n"
                    "            int t = nums[low]; nums[low] = nums[mid]; nums[mid] = t;\n"
                    "            low++; mid++;\n"
                    "        } else if (nums[mid] == 1) {\n"
                    "            mid++;\n"
                    "        } else {\n"
                    "            int t = nums[mid]; nums[mid] = nums[high]; nums[high] = t;\n"
                    "            high--;\n"
                    "        }\n"
                    "    }\n"
                    "    return nums;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Counting Sort (Two-Pass)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "First pass: count the number of 0s, 1s, and 2s. Second pass: overwrite the array in order — "
                "first `count[0]` zeros, then `count[1]` ones, then `count[2]` twos. Two passes but conceptually "
                "trivial; useful as a fallback if you blank on the three-pointer dance. The counter array is "
                "fixed size 3, so extra space is O(1)."
            ),
            "code": {
                "python": (
                    "def sort_colors(nums):\n"
                    "    count = [0, 0, 0]\n"
                    "    for v in nums:\n"
                    "        count[v] += 1\n"
                    "    i = 0\n"
                    "    for color in range(3):\n"
                    "        for _ in range(count[color]):\n"
                    "            nums[i] = color\n"
                    "            i += 1\n"
                    "    return nums"
                ),
                "javascript": (
                    "function sortColors(nums) {\n"
                    "    const count = [0, 0, 0];\n"
                    "    for (const v of nums) count[v]++;\n"
                    "    let i = 0;\n"
                    "    for (let color = 0; color < 3; color++) {\n"
                    "        for (let k = 0; k < count[color]; k++) nums[i++] = color;\n"
                    "    }\n"
                    "    return nums;\n"
                    "}"
                ),
                "java": (
                    "public int[] sortColors(int[] nums) {\n"
                    "    int[] count = new int[3];\n"
                    "    for (int v : nums) count[v]++;\n"
                    "    int i = 0;\n"
                    "    for (int color = 0; color < 3; color++) {\n"
                    "        for (int k = 0; k < count[color]; k++) nums[i++] = color;\n"
                    "    }\n"
                    "    return nums;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Library sort works in O(n log n) but is explicitly forbidden — and we should be able to beat it because there are only 3 distinct keys.",
        "2. Counting sort is the obvious O(n) approach: tally each value, rewrite the array. Two passes, but trivial to get right.",
        "3. Can we do it in one pass with O(1) space? Yes — the Dutch National Flag partition.",
        "4. Maintain three regions via three pointers. `low` marks the boundary of the 0s, `high` marks the boundary of the 2s, `mid` is the scan cursor. The unscanned region is `[mid..high]`.",
        "5. Key invariant during the loop: everything left of `low` is 0, everything between `low` and `mid` is 1, everything right of `high` is 2.",
        "6. Trickiest case: when swapping a 2 to the back, the value pulled from `high` is unscanned — must NOT advance `mid` after that swap.",
        "7. Loop terminates when `mid > high`: the unscanned region is empty.",
    ],
    "tips": [
        "The 'don't advance mid after swapping with high' is THE bug. Practise tracing `[2, 0, 1]` by hand to lock it in.",
        "The 'do advance mid after swapping with low' is safe because `nums[low]` was already classified as 1 (or `low == mid`, in which case you're just swapping a 0 with itself).",
        "Loop condition is `mid <= high`, not `mid < high`. The middle pointer must examine the position equal to `high`.",
        "Generalises: 'Dutch National Flag' is the partition step in 3-way quicksort (handy for arrays with many duplicates of the pivot).",
        "Common follow-up: 'sort an array with k distinct values in-place'. Counting sort still works in O(n + k); the three-pointer trick does not generalise cleanly beyond k = 3.",
        "If asked 'what if we can't modify the array' — counting sort produces a new array of the same length; not useful here. The single-pass swap version inherently needs in-place mutation.",
    ],
    "companies": ["Amazon", "Microsoft", "Facebook", "Apple", "Bloomberg"],
    "topics": ["Array", "Two Pointers", "Sorting"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    import copy
    arr = copy.deepcopy(nums)
    low, mid, high = 0, 0, len(arr) - 1
    while mid <= high:
        if arr[mid] == 0:
            arr[low], arr[mid] = arr[mid], arr[low]
            low += 1
            mid += 1
        elif arr[mid] == 1:
            mid += 1
        else:
            arr[mid], arr[high] = arr[high], arr[mid]
            high -= 1
    return arr


register(PAYLOAD, REFERENCE)
