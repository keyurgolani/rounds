"""Two Sum II - Input Array is Sorted — Medium. Two Pointers.

The 'sorted-input twist' on Two Sum. Because the array is sorted,
the hash-map trick is overkill — you can shrink the search window
from both ends in O(1) extra space. Indices returned are 1-based
because LeetCode wrote it that way; mind the off-by-one. The
constant-space requirement is what makes the two-pointer approach
the canonical answer.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Two Sum II - Input Array is Sorted",
    "difficulty": "Medium",
    "description": (
        "Given a **1-indexed** array of integers `numbers` that is already sorted in non-decreasing order, "
        "find two numbers such that they add up to a specific `target` number.\n\n"
        "Let these two numbers be `numbers[index1]` and `numbers[index2]` where "
        "`1 <= index1 < index2 <= numbers.length`.\n\n"
        "Return the indices of the two numbers, `index1` and `index2`, **added by one** as an integer array "
        "`[index1, index2]` of length 2.\n\n"
        "The tests are generated such that there is **exactly one solution**. You may not use the same "
        "element twice. Your solution must use only constant extra space.\n\n"
        "**Example 1:**\n"
        "- Input: `numbers = [2,7,11,15]`, `target = 9`\n"
        "- Output: `[1,2]`\n"
        "- Explanation: The sum of 2 and 7 is 9. Therefore, `index1 = 1`, `index2 = 2`. We return `[1, 2]`.\n\n"
        "**Example 2:**\n"
        "- Input: `numbers = [2,3,4]`, `target = 6`\n"
        "- Output: `[1,3]`\n"
        "- Explanation: The sum of 2 and 4 is 6. Therefore `index1 = 1`, `index2 = 3`. We return `[1, 3]`."
    ),
    "hints": [
        "The array is **sorted** — that's the whole point of this variant. A plain hash-map two-sum works but ignores the sortedness and violates the O(1) space constraint.",
        "Place two pointers: `left = 0`, `right = n - 1`. Compute `numbers[left] + numbers[right]`.",
        "If the sum is **less than** target, the only way to grow it is to move `left` right (the left value increases, since the array is sorted ascending).",
        "If the sum is **greater than** target, shrink it by moving `right` left.",
        "Alternative — for each `i`, binary-search the complement `target - numbers[i]` in the suffix `numbers[i+1:]`. O(n log n) but still O(1) space; useful framing if asked to avoid two pointers.",
        "Don't forget to convert the final 0-based pointers to **1-based** indices before returning.",
    ],
    "constraints": [
        "2 <= numbers.length <= 3 * 10⁴",
        "-1000 <= numbers[i] <= 1000",
        "numbers is sorted in non-decreasing order",
        "-1000 <= target <= 1000",
        "The tests are generated such that there is exactly one solution",
    ],
    "starter_code": {
        "python": "def two_sum(numbers, target):\n    # Your code here\n    pass",
        "javascript": "function twoSum(numbers, target) {\n    // Your code here\n}",
        "java": "public int[] twoSum(int[] numbers, int target) {\n    // Your code here\n    return new int[]{0, 0};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([2,7,11,15], 9), ([2,3,4], 6), ([-1,0], -1)]\n"
            "    for numbers, target in cases:\n"
            "        print(f\"two_sum({numbers}, {target}) = {two_sum(numbers, target)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[2,7,11,15], 9], [[2,3,4], 6], [[-1,0], -1]].forEach(([numbers, target]) =>\n"
            "    console.log(`twoSum =`, twoSum(numbers, target))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[] r = s.twoSum(new int[]{2,7,11,15}, 9);\n"
            "        System.out.println(r[0] + \",\" + r[1]);\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"numbers": [2, 7, 11, 15], "target": 9}, "expected": [1, 2],
         "description": "Classic LeetCode example — first two elements sum to target", "tags": ["basic"]},
        {"input": {"numbers": [2, 3, 4], "target": 6}, "expected": [1, 3],
         "description": "First and last — pair spans the whole array", "tags": ["basic"]},
        {"input": {"numbers": [-1, 0], "target": -1}, "expected": [1, 2],
         "description": "Negatives — two-element array, the only possible pair", "tags": ["edge"]},
        {"input": {"numbers": [1, 1, 2], "target": 2}, "expected": [1, 2],
         "description": "Duplicates — two pointers naturally pick the leftmost+rightmost valid pair (1+1=2)",
         "tags": ["tricky"]},
        {"input": {"numbers": [1, 2, 3, 4, 4, 9, 56, 90], "target": 8}, "expected": [4, 5],
         "description": "Duplicates inside the array — pair is the two 4s", "tags": ["tricky"]},
        {"input": {"numbers": [-3, -1, 0, 2, 5], "target": 4}, "expected": [2, 5],
         "description": "Mixed signs — -1 + 5 = 4", "tags": ["tricky"]},
        {"input": {"numbers": [5, 25, 75], "target": 100}, "expected": [2, 3],
         "description": "Last two elements form the pair", "tags": ["edge"]},
        {"input": {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "target": 11}, "expected": [1, 10],
         "description": "Consecutive integers — pair is first + last", "tags": ["basic"]},
        {"input": {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "target": 9}, "expected": [1, 8],
         "description": "Consecutive integers — outer pair found by two-pointer (1+8)", "tags": ["tricky"]},
        {"input": {"numbers": [-1000, -500, 0, 500, 1000], "target": 0}, "expected": [1, 5],
         "description": "Symmetric around zero — extremes cancel", "tags": ["edge"]},
        {"input": {"numbers": list(range(1, 10001)), "target": 19999}, "expected": [9999, 10000],
         "description": "Large array, pair is the last two — exercises right-pointer locality",
         "tags": ["large"]},
        {"input": {"numbers": list(range(1, 10001)), "target": 3}, "expected": [1, 2],
         "description": "Large array, pair is the first two — exercises left-pointer locality",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Two Pointers (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Place `left` at index 0 and `right` at index n-1. Compute the sum. If it equals target, "
                "return the 1-based indices. If the sum is too small, advance `left` (the array is sorted "
                "ascending, so the left value can only grow). If the sum is too large, retreat `right`. "
                "Each iteration eliminates one index from consideration, so the loop runs at most n times. "
                "Constant extra space — the two pointers are scalars."
            ),
            "code": {
                "python": (
                    "def two_sum(numbers, target):\n"
                    "    left, right = 0, len(numbers) - 1\n"
                    "    while left < right:\n"
                    "        s = numbers[left] + numbers[right]\n"
                    "        if s == target:\n"
                    "            return [left + 1, right + 1]\n"
                    "        if s < target:\n"
                    "            left += 1\n"
                    "        else:\n"
                    "            right -= 1\n"
                    "    return []  # problem guarantees a solution"
                ),
                "javascript": (
                    "function twoSum(numbers, target) {\n"
                    "    let left = 0, right = numbers.length - 1;\n"
                    "    while (left < right) {\n"
                    "        const s = numbers[left] + numbers[right];\n"
                    "        if (s === target) return [left + 1, right + 1];\n"
                    "        if (s < target) left++;\n"
                    "        else right--;\n"
                    "    }\n"
                    "    return [];\n"
                    "}"
                ),
                "java": (
                    "public int[] twoSum(int[] numbers, int target) {\n"
                    "    int left = 0, right = numbers.length - 1;\n"
                    "    while (left < right) {\n"
                    "        int s = numbers[left] + numbers[right];\n"
                    "        if (s == target) return new int[]{left + 1, right + 1};\n"
                    "        if (s < target) left++;\n"
                    "        else right--;\n"
                    "    }\n"
                    "    return new int[]{};\n"
                    "}"
                ),
            },
        },
        {
            "title": "Binary Search for Complement",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(1)",
            "description": (
                "For each index `i`, binary-search for `target - numbers[i]` in the suffix "
                "`numbers[i+1:]`. Slower than two pointers but still satisfies the O(1) space constraint, "
                "and it's worth knowing because it generalises to problems where the two-pointer invariant "
                "doesn't hold (e.g. unsorted data with a precomputed sorted index)."
            ),
            "code": {
                "python": (
                    "def two_sum(numbers, target):\n"
                    "    n = len(numbers)\n"
                    "    for i in range(n - 1):\n"
                    "        complement = target - numbers[i]\n"
                    "        lo, hi = i + 1, n - 1\n"
                    "        while lo <= hi:\n"
                    "            mid = (lo + hi) // 2\n"
                    "            if numbers[mid] == complement:\n"
                    "                return [i + 1, mid + 1]\n"
                    "            if numbers[mid] < complement:\n"
                    "                lo = mid + 1\n"
                    "            else:\n"
                    "                hi = mid - 1\n"
                    "    return []"
                ),
                "javascript": (
                    "function twoSum(numbers, target) {\n"
                    "    const n = numbers.length;\n"
                    "    for (let i = 0; i < n - 1; i++) {\n"
                    "        const complement = target - numbers[i];\n"
                    "        let lo = i + 1, hi = n - 1;\n"
                    "        while (lo <= hi) {\n"
                    "            const mid = (lo + hi) >> 1;\n"
                    "            if (numbers[mid] === complement) return [i + 1, mid + 1];\n"
                    "            if (numbers[mid] < complement) lo = mid + 1;\n"
                    "            else hi = mid - 1;\n"
                    "        }\n"
                    "    }\n"
                    "    return [];\n"
                    "}"
                ),
                "java": (
                    "public int[] twoSum(int[] numbers, int target) {\n"
                    "    int n = numbers.length;\n"
                    "    for (int i = 0; i < n - 1; i++) {\n"
                    "        int complement = target - numbers[i];\n"
                    "        int lo = i + 1, hi = n - 1;\n"
                    "        while (lo <= hi) {\n"
                    "            int mid = (lo + hi) >>> 1;\n"
                    "            if (numbers[mid] == complement) return new int[]{i + 1, mid + 1};\n"
                    "            if (numbers[mid] < complement) lo = mid + 1;\n"
                    "            else hi = mid - 1;\n"
                    "        }\n"
                    "    }\n"
                    "    return new int[]{};\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Note the sorted input — the regular Two Sum hash-map approach works but ignores it and uses O(n) space.",
        "2. Constant-space requirement steers you to two pointers: `left = 0`, `right = n - 1`.",
        "3. Compare `numbers[left] + numbers[right]` with target. Sorted order guarantees moving `left` rightward only increases the sum, and moving `right` leftward only decreases it.",
        "4. Each step eliminates exactly one candidate index. Loop terminates in ≤ n iterations.",
        "5. Convert to 1-based indices on return — easy place to drop a +1.",
        "6. If two-pointer feels off-limits (e.g. interviewer asks for a different approach), fall back to binary-searching the complement at each index — O(n log n), still O(1) space.",
    ],
    "tips": [
        "The sorted-array invariant is the whole point — say it out loud. If your solution would still work on an unsorted array, you're not exploiting the input.",
        "Don't return 0-based indices. The problem is 1-indexed; that's a one-line +1 fix that is always missed in interviews.",
        "Two pointers correctness sketch: the pair (left, right) you skip past is provably not the answer (sum too small → no smaller-index partner can fix it; symmetric for the other direction). Be ready to argue this.",
        "If the interviewer changes 'exactly one solution' to 'all pairs', the two-pointer template still works — after a hit, advance both pointers and skip duplicates.",
        "Common follow-up — Three Sum: outer loop fixes one index, then run this same two-pointer scan on the rest.",
        "Watch the sum overflow on large `int` arrays in Java/C++ — `numbers[left] + numbers[right]` can exceed `INT_MAX`. Within this problem's bounds it's fine, but flag it as something you'd guard in production.",
    ],
    "companies": ["Amazon", "Google", "Apple", "Microsoft", "Bloomberg", "Facebook"],
    "topics": ["Array", "Two Pointers", "Binary Search"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(numbers, target):
    left, right = 0, len(numbers) - 1
    while left < right:
        s = numbers[left] + numbers[right]
        if s == target:
            return [left + 1, right + 1]
        if s < target:
            left += 1
        else:
            right -= 1
    return []


register(PAYLOAD, REFERENCE)
