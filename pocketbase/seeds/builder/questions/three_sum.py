"""3Sum — Medium. Two Pointers / Sorting.

The canonical 'sort + two pointers' problem and the standard place
candidates lose points to duplicate handling. A passing answer
emits the right triplets; a strong answer never even *visits* a
duplicate triplet, by skipping equal anchors and equal pointer
moves at every level.
"""
from builder.registry import register


# Validator: output must be a list of triplets that (a) sum to zero,
# (b) draw all values from `nums`, (c) match the canonical de-duplicated
# set of zero-sum triplets, with order-within-triplet and order-of-
# triplets both free.
_THREE_SUM_VALIDATOR = (
    "lambda inp, out: ("
    "isinstance(out, list) and "
    "all(isinstance(t, list) and len(t) == 3 and sum(t) == 0 for t in out) and "
    "sorted(tuple(sorted(t)) for t in out) == sorted("
    "set("
    "tuple(sorted([inp['nums'][i], inp['nums'][j], inp['nums'][k]])) "
    "for i in range(len(inp['nums'])) "
    "for j in range(i+1, len(inp['nums'])) "
    "for k in range(j+1, len(inp['nums'])) "
    "if inp['nums'][i] + inp['nums'][j] + inp['nums'][k] == 0"
    ")"
    ")"
    ")"
)


PAYLOAD = {
    "title": "3Sum",
    "difficulty": "Medium",
    "description": (
        "Given an integer array `nums`, return all the triplets `[nums[i], nums[j], nums[k]]` such "
        "that `i != j`, `i != k`, and `j != k`, and `nums[i] + nums[j] + nums[k] == 0`.\n\n"
        "Notice that the solution set must **not** contain duplicate triplets.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [-1,0,1,2,-1,-4]`\n"
        "- Output: `[[-1,-1,2],[-1,0,1]]`\n"
        "- Explanation: The two distinct triplets that sum to 0.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [0,1,1]`\n"
        "- Output: `[]`\n\n"
        "**Example 3:**\n"
        "- Input: `nums = [0,0,0]`\n"
        "- Output: `[[0,0,0]]`"
    ),
    "hints": [
        "Brute force: triple loop, O(n³). State it; never submit it for n up to 3000.",
        "Reframe as 'for each anchor a, find pairs (b, c) with b + c = -a' — that's 2Sum, which is two pointers on a sorted array.",
        "Sort first. Now the outer loop picks the anchor; an inner two-pointer pass over the suffix finds matching pairs in O(n).",
        "Duplicate elimination is the entire trap. Skip the anchor when `nums[i] == nums[i-1]`. Skip the left pointer after a hit when `nums[left] == nums[left-1]`. (Symmetric on the right pointer if you also want sub-linear duplicate skipping.)",
        "Early exit: once `nums[i] > 0`, no triplet starting at i can sum to 0 — the suffix is all non-negative.",
    ],
    "constraints": [
        "3 <= nums.length <= 3000",
        "-10⁵ <= nums[i] <= 10⁵",
    ],
    "starter_code": {
        "python": "def three_sum(nums):\n    # Your code here\n    pass",
        "javascript": "function threeSum(nums) {\n    // Your code here\n}",
        "java": "public List<List<Integer>> threeSum(int[] nums) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[-1,0,1,2,-1,-4], [0,1,1], [0,0,0]]\n"
            "    for nums in cases:\n"
            "        print(f\"three_sum({nums}) = {three_sum(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[-1,0,1,2,-1,-4], [0,1,1], [0,0,0]].forEach(nums =>\n"
            "    console.log(`threeSum =`, threeSum(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.threeSum(new int[]{-1,0,1,2,-1,-4}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {
            "input": {"nums": [-1, 0, 1, 2, -1, -4]},
            "expected": {
                "$match": "validator",
                "description": "all distinct zero-sum triplets, in any order",
                "code": _THREE_SUM_VALIDATOR,
                "examples": [[[-1, -1, 2], [-1, 0, 1]]],
            },
            "description": "Standard from problem statement", "tags": ["basic"],
        },
        {
            "input": {"nums": [0, 1, 1]},
            "expected": [],
            "description": "No triplets sum to zero", "tags": ["basic"],
        },
        {
            "input": {"nums": [0, 0, 0]},
            "expected": [[0, 0, 0]],
            "description": "Single triplet of zeros", "tags": ["edge"],
        },
        {
            "input": {"nums": [0, 0, 0, 0]},
            "expected": [[0, 0, 0]],
            "description": "Four zeros — one unique triplet", "tags": ["edge", "tricky"],
        },
        {
            "input": {"nums": [-2, 0, 1, 1, 2]},
            "expected": {
                "$match": "validator",
                "description": "two distinct triplets",
                "code": _THREE_SUM_VALIDATOR,
                "examples": [[[-2, 0, 2], [-2, 1, 1]]],
            },
            "description": "Two triplets, one with a duplicate value",
            "tags": ["tricky"],
        },
        {
            "input": {"nums": [1, 2, 3]},
            "expected": [],
            "description": "All positive — no zero sum possible", "tags": ["edge"],
        },
        {
            "input": {"nums": [-1, -1, -1, 2, 2]},
            "expected": [[-1, -1, 2]],
            "description": "Heavy duplicates — single dedup triplet", "tags": ["tricky"],
        },
        {
            "input": {"nums": [-4, -2, -2, -2, 0, 1, 2, 2, 2, 3, 3, 4, 4, 6, 6]},
            "expected": {
                "$match": "validator",
                "description": "many candidates with overlapping duplicates",
                "code": _THREE_SUM_VALIDATOR,
                "examples": [[[-4, 0, 4], [-4, 1, 3], [-4, 2, 2], [-2, -2, 4], [-2, 0, 2]]],
            },
            "description": "Heavy duplication exercises both skip rules",
            "tags": ["tricky", "basic"],
        },
        {
            "input": {"nums": list(range(-50, 51))},
            "expected": {
                "$match": "validator",
                "description": "101 elements; many balanced triplets through zero",
                "code": _THREE_SUM_VALIDATOR,
                "examples": [[]],
            },
            "description": "Symmetric range -50..50 — many triplets",
            "tags": ["large"],
        },
        {
            "input": {"nums": [3] * 1000 + [-3] * 1000 + [0]},
            "expected": [[-3, 0, 3]],
            "description": "2001 elements, only one canonical triplet — dedup must handle 1000s of (3, -3, 0)",
            "tags": ["large", "tricky"],
        },
    ],
    "solutions": [
        {
            "title": "Sort + Two Pointers (Optimal)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1) extra (sorting in place; output not counted)",
            "description": (
                "Sort. For each anchor `i`, run two pointers `left = i+1`, `right = n-1`. Sum the trio; "
                "if it's zero, record and shrink both pointers; if too small, advance left; if too big, "
                "retreat right. Skip duplicate anchors and duplicate post-hit pointer moves to keep the "
                "result set canonical."
            ),
            "code": {
                "python": (
                    "def three_sum(nums):\n"
                    "    nums = sorted(nums)\n"
                    "    out = []\n"
                    "    n = len(nums)\n"
                    "    for i in range(n - 2):\n"
                    "        if nums[i] > 0:\n"
                    "            break  # remaining values all positive\n"
                    "        if i > 0 and nums[i] == nums[i - 1]:\n"
                    "            continue  # skip duplicate anchor\n"
                    "        left, right = i + 1, n - 1\n"
                    "        while left < right:\n"
                    "            s = nums[i] + nums[left] + nums[right]\n"
                    "            if s == 0:\n"
                    "                out.append([nums[i], nums[left], nums[right]])\n"
                    "                left += 1\n"
                    "                right -= 1\n"
                    "                while left < right and nums[left] == nums[left - 1]:\n"
                    "                    left += 1\n"
                    "                while left < right and nums[right] == nums[right + 1]:\n"
                    "                    right -= 1\n"
                    "            elif s < 0:\n"
                    "                left += 1\n"
                    "            else:\n"
                    "                right -= 1\n"
                    "    return out"
                ),
                "javascript": (
                    "function threeSum(nums) {\n"
                    "    nums = [...nums].sort((a, b) => a - b);\n"
                    "    const out = [];\n"
                    "    const n = nums.length;\n"
                    "    for (let i = 0; i < n - 2; i++) {\n"
                    "        if (nums[i] > 0) break;\n"
                    "        if (i > 0 && nums[i] === nums[i - 1]) continue;\n"
                    "        let left = i + 1, right = n - 1;\n"
                    "        while (left < right) {\n"
                    "            const s = nums[i] + nums[left] + nums[right];\n"
                    "            if (s === 0) {\n"
                    "                out.push([nums[i], nums[left], nums[right]]);\n"
                    "                left++; right--;\n"
                    "                while (left < right && nums[left] === nums[left - 1]) left++;\n"
                    "                while (left < right && nums[right] === nums[right + 1]) right--;\n"
                    "            } else if (s < 0) left++;\n"
                    "            else right--;\n"
                    "        }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public List<List<Integer>> threeSum(int[] nums) {\n"
                    "    int[] arr = nums.clone();\n"
                    "    Arrays.sort(arr);\n"
                    "    List<List<Integer>> out = new ArrayList<>();\n"
                    "    for (int i = 0; i < arr.length - 2; i++) {\n"
                    "        if (arr[i] > 0) break;\n"
                    "        if (i > 0 && arr[i] == arr[i - 1]) continue;\n"
                    "        int left = i + 1, right = arr.length - 1;\n"
                    "        while (left < right) {\n"
                    "            int s = arr[i] + arr[left] + arr[right];\n"
                    "            if (s == 0) {\n"
                    "                out.add(Arrays.asList(arr[i], arr[left], arr[right]));\n"
                    "                left++; right--;\n"
                    "                while (left < right && arr[left] == arr[left - 1]) left++;\n"
                    "                while (left < right && arr[right] == arr[right + 1]) right--;\n"
                    "            } else if (s < 0) left++;\n"
                    "            else right--;\n"
                    "        }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Hash Set per Anchor",
            "time_complexity": "O(n²)",
            "space_complexity": "O(n)",
            "description": (
                "Same outer loop, but the inner pass uses a hash set (2Sum-via-set) instead of two pointers. "
                "Same asymptotic complexity but uses extra memory and is slightly trickier to dedupe — pointer "
                "version is the cleaner write-up under interview pressure."
            ),
            "code": {
                "python": (
                    "def three_sum(nums):\n"
                    "    nums = sorted(nums)\n"
                    "    out = set()\n"
                    "    for i in range(len(nums) - 2):\n"
                    "        if i > 0 and nums[i] == nums[i - 1]:\n"
                    "            continue\n"
                    "        seen = set()\n"
                    "        for j in range(i + 1, len(nums)):\n"
                    "            need = -nums[i] - nums[j]\n"
                    "            if need in seen:\n"
                    "                out.add((nums[i], need, nums[j]))\n"
                    "            seen.add(nums[j])\n"
                    "    return [list(t) for t in out]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force triple loop = O(n³). State it; that's your baseline.",
        "2. Reframe: pick an anchor, then it's 2Sum on the rest with target `-anchor`. 2Sum is O(n) via two pointers on a sorted array → outer is O(n) → total O(n²).",
        "3. Sort. Now both 'find pair' and 'dedupe' lean on adjacency.",
        "4. Outer loop: skip duplicate anchors (`nums[i] == nums[i-1]`).",
        "5. Inner two-pointer loop: on a hit, advance both pointers, then skip duplicates of the *just-emitted* values.",
        "6. Early exit: once `nums[i] > 0`, the rest of the array is non-negative; no triplet can sum to 0.",
        "7. Edge cases: fewer than 3 elements (impossible per constraint, but worth checking), all zeros (single triplet), all positives or all negatives (no triplets).",
    ],
    "tips": [
        "Dedup via sorting is *cheaper* than dedup via a result set — sorting groups duplicates together so a single equality check skips them.",
        "Don't forget the `nums[i] > 0` early break — it's a real speed-up for skewed inputs.",
        "Common follow-up: 4Sum. Same trick: outer pair + inner two pointers → O(n³). Watch the same dedup rules at every level.",
        "Common follow-up: 3Sum Closest. No dedup needed; track the running closest sum across all anchors.",
        "Common follow-up: 'Triplets that sum to a target T' (not zero). Same code; replace `-nums[i]` with `T - nums[i]`.",
    ],
    "companies": ["Facebook", "Amazon", "Apple", "Microsoft", "Adobe"],
    "topics": ["Array", "Two Pointers", "Sorting"],
    "time_complexity": "O(n²)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    nums = sorted(nums)
    out = []
    n = len(nums)
    for i in range(n - 2):
        if nums[i] > 0:
            break
        if i > 0 and nums[i] == nums[i - 1]:
            continue
        left, right = i + 1, n - 1
        while left < right:
            s = nums[i] + nums[left] + nums[right]
            if s == 0:
                out.append([nums[i], nums[left], nums[right]])
                left += 1
                right -= 1
                while left < right and nums[left] == nums[left - 1]:
                    left += 1
                while left < right and nums[right] == nums[right + 1]:
                    right -= 1
            elif s < 0:
                left += 1
            else:
                right -= 1
    return out


register(PAYLOAD, REFERENCE)
