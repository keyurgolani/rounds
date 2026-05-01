"""Maximum Product Subarray — Medium. Array / Dynamic Programming.

Kadane's cousin, but with a twist: multiplication isn't monotone under
sign. A negative number flips the role of 'best' and 'worst', so the
running max can become the running min in one step. The trick is to
track *both* extremes at every index. Zeros are a natural reset.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Maximum Product Subarray",
    "difficulty": "Medium",
    "description": (
        "Given an integer array `nums`, find a **contiguous non-empty subarray** within the array that has "
        "the largest product, and return that product.\n\n"
        "The test cases are generated so that the answer fits in a 32-bit integer.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [2,3,-2,4]`\n"
        "- Output: `6`\n"
        "- Explanation: `[2,3]` has the largest product `6`.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [-2,0,-1]`\n"
        "- Output: `0`\n"
        "- Explanation: The result cannot be `2` because `[-2,-1]` is not contiguous."
    ),
    "hints": [
        "Brute force: every (i, j) pair, multiply through → O(n²) or O(n³). Mention it; never submit it.",
        "Why Kadane doesn't directly work: a large negative product is *valuable* — the next negative number flips it into the new max.",
        "Track *both* `cur_max` and `cur_min` at each index. New values: `cur_max = max(num, num*prev_max, num*prev_min)`; `cur_min = min(num, num*prev_max, num*prev_min)`.",
        "Zeros reset both running products. The `max(num, ...)` form handles this for free — when `num = 0`, both extremes become 0.",
        "Logarithm trick (`log(prod) = sum(log)`) reduces to Maximum Subarray — but only works for strictly positive inputs. Mention as a contrast, don't submit.",
    ],
    "constraints": [
        "1 <= nums.length <= 2 * 10⁴",
        "-10 <= nums[i] <= 10",
        "The product of any prefix or suffix of nums is guaranteed to fit in a 32-bit integer.",
    ],
    "starter_code": {
        "python": "def max_product(nums):\n    # Your code here\n    pass",
        "javascript": "function maxProduct(nums) {\n    // Your code here\n}",
        "java": "public int maxProduct(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[2,3,-2,4], [-2,0,-1], [-2,3,-4], [2,-5,-2,-4,3]]\n"
            "    for nums in cases:\n"
            "        print(f\"max_product({nums}) = {max_product(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[2,3,-2,4], [-2,0,-1], [-2,3,-4]].forEach(nums =>\n"
            "    console.log(`maxProduct =`, maxProduct(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.maxProduct(new int[]{2,3,-2,4}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [2, 3, -2, 4]}, "expected": 6,
         "description": "Best window is [2,3] — the -2 would flip the sign", "tags": ["basic"]},
        {"input": {"nums": [-2, 0, -1]}, "expected": 0,
         "description": "Zero in the middle — best non-empty product is 0", "tags": ["basic"]},
        {"input": {"nums": [-2, 3, -4]}, "expected": 24,
         "description": "Two negatives flank a positive — full-array product wins", "tags": ["tricky"]},
        {"input": {"nums": [0, 2]}, "expected": 2,
         "description": "Leading zero — best is the singleton 2", "tags": ["edge"]},
        {"input": {"nums": [-1]}, "expected": -1,
         "description": "Single negative — must return that element (subarray is non-empty)", "tags": ["edge"]},
        {"input": {"nums": [-2]}, "expected": -2,
         "description": "Single negative, larger magnitude — same rule", "tags": ["edge"]},
        {"input": {"nums": [2, -5, -2, -4, 3]}, "expected": 24,
         "description": "Three negatives — best is to skip one to keep the sign positive ([-5,-2,-4,3] is negative; [-5,-2] gives 10; [2,-5,-2] gives 20; [-2,-4,3] gives 24)",
         "tags": ["tricky"]},
        {"input": {"nums": [0, -1, 4, -4, 5, -2, -1, -1, -2, -3]}, "expected": 960,
         "description": "Zero resets, then a long negative-rich tail — track both extremes to catch the best signed window",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Track Max and Min (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk left-to-right. At each index, the new `cur_max` is the largest of three candidates: "
                "`num` alone (start fresh here), `num * prev_max`, or `num * prev_min` (a negative times a "
                "negative). Mirror the logic for `cur_min`. Update the global answer with `cur_max`. "
                "Capture `prev_max` before overwriting it — `cur_min` still needs the *old* value."
            ),
            "code": {
                "python": (
                    "def max_product(nums):\n"
                    "    cur_max = cur_min = best = nums[0]\n"
                    "    for num in nums[1:]:\n"
                    "        if num < 0:\n"
                    "            cur_max, cur_min = cur_min, cur_max\n"
                    "        cur_max = max(num, num * cur_max)\n"
                    "        cur_min = min(num, num * cur_min)\n"
                    "        best = max(best, cur_max)\n"
                    "    return best"
                ),
                "javascript": (
                    "function maxProduct(nums) {\n"
                    "    let curMax = nums[0], curMin = nums[0], best = nums[0];\n"
                    "    for (let i = 1; i < nums.length; i++) {\n"
                    "        const num = nums[i];\n"
                    "        if (num < 0) [curMax, curMin] = [curMin, curMax];\n"
                    "        curMax = Math.max(num, num * curMax);\n"
                    "        curMin = Math.min(num, num * curMin);\n"
                    "        best = Math.max(best, curMax);\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "public int maxProduct(int[] nums) {\n"
                    "    int curMax = nums[0], curMin = nums[0], best = nums[0];\n"
                    "    for (int i = 1; i < nums.length; i++) {\n"
                    "        int num = nums[i];\n"
                    "        if (num < 0) {\n"
                    "            int tmp = curMax; curMax = curMin; curMin = tmp;\n"
                    "        }\n"
                    "        curMax = Math.max(num, num * curMax);\n"
                    "        curMin = Math.min(num, num * curMin);\n"
                    "        best = Math.max(best, curMax);\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force on Prefix Products (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "For each starting index, multiply forward and track the running product, updating the global "
                "best each step. Reset when a zero is hit (any subarray crossing it has product 0). Mention "
                "as the n² baseline; never submit for n up to 2·10⁴."
            ),
            "code": {
                "python": (
                    "def max_product(nums):\n"
                    "    best = nums[0]\n"
                    "    for i in range(len(nums)):\n"
                    "        prod = 1\n"
                    "        for j in range(i, len(nums)):\n"
                    "            prod *= nums[j]\n"
                    "            if prod > best:\n"
                    "                best = prod\n"
                    "            if nums[j] == 0:\n"
                    "                break\n"
                    "    return best"
                ),
            },
        },
        {
            "title": "Logarithm Reduction (Doesn't Work for Negatives)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "If every input were strictly positive, `log(a*b) = log(a) + log(b)` would let you reduce this "
                "problem to Maximum Subarray (Kadane on `log(nums[i])`). Mention only as a contrast — the "
                "moment a single negative or zero appears, logs are undefined and the reduction collapses. "
                "Useful framing to *recognise* but not to submit."
            ),
            "code": {
                "python": (
                    "# Conceptual only — fails on negative numbers and zeros.\n"
                    "import math\n"
                    "def max_product_positive_only(nums):\n"
                    "    # Assumes all nums[i] > 0 — otherwise math.log is invalid.\n"
                    "    best = current = math.log(nums[0])\n"
                    "    for x in nums[1:]:\n"
                    "        current = max(math.log(x), current + math.log(x))\n"
                    "        best = max(best, current)\n"
                    "    return round(math.exp(best))"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force: every (i, j) → O(n²). State it as the baseline; ruled out for n up to 2·10⁴.",
        "2. Try Kadane directly: `current = max(num, num * current)`. Fails on `[-2, 3, -4]` — Kadane discards `-2` because `3 * -2 < 3`, missing that `-2 * 3 * -4 = 24`.",
        "3. The fix: *negative numbers flip max and min*. A large-negative running product becomes the next iteration's best when multiplied by another negative.",
        "4. Track BOTH `cur_max` and `cur_min`. New values: each is the max/min of three candidates — `num` alone, `num * prev_max`, `num * prev_min`. Use `prev_max` before you overwrite it.",
        "5. Zeros: `max(num, ...)` with `num = 0` collapses both extremes to 0 — a clean, automatic reset. No special case needed.",
        "6. Edges: single element (return it; subarray must be non-empty), all-negative (the answer may be a *single* negative if the array length is odd and all are negative).",
    ],
    "tips": [
        "The negative-flip trick is the whole interview signal. If you can articulate *why* Kadane breaks here and how tracking the min repairs it, you've shown the insight.",
        "Zero handling: nothing special required. `cur_max = max(num, num * cur_max)` with `num = 0` gives `cur_max = 0`. Same for min. Both extremes reset; the global best is preserved.",
        "Connection to Maximum Subarray (Kadane): same one-pass DP shape, but the recurrence has *two* states instead of one because multiplication isn't sign-monotone.",
        "Watch the update order: if you write `cur_max = max(num, num*cur_max)` first, then compute `cur_min` using the *new* `cur_max`, you'll get a subtle wrong answer on negatives. Snapshot before overwriting, or do the swap-on-negative trick.",
        "Initialise `best`, `cur_max`, `cur_min` to `nums[0]` and start the loop at index 1 — cleaner than seeding with `1` and 0 (which silently breaks on all-negative inputs of odd length).",
    ],
    "companies": ["Amazon", "LinkedIn"],
    "topics": ["Array", "Dynamic Programming"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    cur_max = cur_min = best = nums[0]
    for num in nums[1:]:
        if num < 0:
            cur_max, cur_min = cur_min, cur_max
        cur_max = max(num, num * cur_max)
        cur_min = min(num, num * cur_min)
        best = max(best, cur_max)
    return best


register(PAYLOAD, REFERENCE)
