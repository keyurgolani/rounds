"""Product of Array Except Self — Medium. Arrays / Prefix-suffix.

The signature 'no division allowed, O(n) time' problem. The trick is
two passes: a prefix-product sweep left-to-right, then a suffix sweep
right-to-left that multiplies into the same output array. The follow-
up about O(1) extra space is satisfied because the output array doesn't
count toward the space bound.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Product of Array Except Self",
    "difficulty": "Medium",
    "description": (
        "Given an integer array `nums`, return an array `answer` such that `answer[i]` is "
        "equal to the product of all the elements of `nums` except `nums[i]`.\n\n"
        "The product of any prefix or suffix of `nums` is guaranteed to fit in a 32-bit integer.\n\n"
        "You must write an algorithm that runs in **O(n)** time and **without using the division operation**.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,2,3,4]`\n"
        "- Output: `[24,12,8,6]`\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [-1,1,0,-3,3]`\n"
        "- Output: `[0,0,9,0,0]`\n\n"
        "**Follow-up:** Can you solve it in O(1) extra space (the output array does not count as extra space)?"
    ),
    "hints": [
        "If division were allowed: `total / nums[i]` — but that breaks for zeros and is explicitly disallowed.",
        "Decompose: `answer[i] = (product of nums[0..i-1]) * (product of nums[i+1..n-1])`. Two halves: prefix and suffix.",
        "Two passes, two arrays: build prefix products left-to-right, suffix products right-to-left, then multiply pairwise.",
        "Optimisation: skip the explicit prefix/suffix arrays. First pass writes prefix products into `answer`; second pass walks right-to-left maintaining a running suffix product and multiplies into `answer` in place.",
        "Edge cases that destroy a careless solution: a single zero (only its own slot is non-zero), two or more zeros (output is all zeros), negative values affecting sign.",
    ],
    "constraints": [
        "2 <= nums.length <= 10⁵",
        "-30 <= nums[i] <= 30",
        "The product of any prefix or suffix fits in a 32-bit signed integer",
    ],
    "starter_code": {
        "python": "def product_except_self(nums):\n    # Your code here\n    pass",
        "javascript": "function productExceptSelf(nums) {\n    // Your code here\n}",
        "java": "public int[] productExceptSelf(int[] nums) {\n    // Your code here\n    return new int[]{};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[1,2,3,4], [-1,1,0,-3,3], [2,3]]\n"
            "    for nums in cases:\n"
            "        print(f\"product_except_self({nums}) = {product_except_self(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,2,3,4], [-1,1,0,-3,3]].forEach(nums =>\n"
            "    console.log(`productExceptSelf =`, productExceptSelf(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(Arrays.toString(s.productExceptSelf(new int[]{1,2,3,4})));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 2, 3, 4]}, "expected": [24, 12, 8, 6],
         "description": "Standard example", "tags": ["basic"]},
        {"input": {"nums": [-1, 1, 0, -3, 3]}, "expected": [0, 0, 9, 0, 0],
         "description": "Single zero — only its own slot has a non-zero product", "tags": ["basic", "tricky"]},
        {"input": {"nums": [2, 3]}, "expected": [3, 2],
         "description": "Minimum-length input", "tags": ["edge"]},
        {"input": {"nums": [0, 0]}, "expected": [0, 0],
         "description": "Two zeros — every slot is zero", "tags": ["edge"]},
        {"input": {"nums": [1, 0, 0, 4]}, "expected": [0, 0, 0, 0],
         "description": "Multiple zeros — entire output is zero", "tags": ["tricky"]},
        {"input": {"nums": [-2, -3, -4, -5]}, "expected": [-60, -40, -30, -24],
         "description": "All negatives — sign tracking matters", "tags": ["tricky"]},
        {"input": {"nums": [1, 1, 1, 1, 1]}, "expected": [1, 1, 1, 1, 1],
         "description": "All ones — every slot is the product of n-1 ones", "tags": ["edge"]},
        {"input": {"nums": [-1, -1, -1, -1]}, "expected": [-1, -1, -1, -1],
         "description": "All negative ones — three negatives multiply to -1", "tags": ["tricky"]},
        {"input": {"nums": [10, 20, 30]}, "expected": [600, 300, 200],
         "description": "Three-element triple-digit case", "tags": ["basic"]},
        {"input": {"nums": [1] * 100}, "expected": [1] * 100,
         "description": "100 ones — output is all ones", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Two Pass, In-Place Output (Optimal — O(1) extra space)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1) extra (the output array doesn't count)",
            "description": (
                "Pass 1: walk left-to-right, writing the prefix product into `answer[i]`. After this pass, "
                "`answer[i]` holds the product of everything strictly to the left of i. Pass 2: walk right-to-left, "
                "maintain a running suffix product, multiply it into `answer[i]`. No division, no extra arrays."
            ),
            "code": {
                "python": (
                    "def product_except_self(nums):\n"
                    "    n = len(nums)\n"
                    "    answer = [1] * n\n"
                    "    # Pass 1: prefix products\n"
                    "    prefix = 1\n"
                    "    for i in range(n):\n"
                    "        answer[i] = prefix\n"
                    "        prefix *= nums[i]\n"
                    "    # Pass 2: suffix products, multiplied in place\n"
                    "    suffix = 1\n"
                    "    for i in range(n - 1, -1, -1):\n"
                    "        answer[i] *= suffix\n"
                    "        suffix *= nums[i]\n"
                    "    return answer"
                ),
                "javascript": (
                    "function productExceptSelf(nums) {\n"
                    "    const n = nums.length;\n"
                    "    const answer = new Array(n).fill(1);\n"
                    "    let prefix = 1;\n"
                    "    for (let i = 0; i < n; i++) {\n"
                    "        answer[i] = prefix;\n"
                    "        prefix *= nums[i];\n"
                    "    }\n"
                    "    let suffix = 1;\n"
                    "    for (let i = n - 1; i >= 0; i--) {\n"
                    "        answer[i] *= suffix;\n"
                    "        suffix *= nums[i];\n"
                    "    }\n"
                    "    return answer;\n"
                    "}"
                ),
                "java": (
                    "public int[] productExceptSelf(int[] nums) {\n"
                    "    int n = nums.length;\n"
                    "    int[] answer = new int[n];\n"
                    "    int prefix = 1;\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        answer[i] = prefix;\n"
                    "        prefix *= nums[i];\n"
                    "    }\n"
                    "    int suffix = 1;\n"
                    "    for (int i = n - 1; i >= 0; i--) {\n"
                    "        answer[i] *= suffix;\n"
                    "        suffix *= nums[i];\n"
                    "    }\n"
                    "    return answer;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Explicit Prefix + Suffix Arrays",
            "time_complexity": "O(n)",
            "space_complexity": "O(n) extra",
            "description": (
                "Build two auxiliary arrays — `prefix[i] = product of nums[0..i-1]` and `suffix[i] = product "
                "of nums[i+1..n-1]` — then `answer[i] = prefix[i] * suffix[i]`. Same time complexity as the "
                "in-place version but easier to walk through on a whiteboard."
            ),
            "code": {
                "python": (
                    "def product_except_self(nums):\n"
                    "    n = len(nums)\n"
                    "    prefix = [1] * n\n"
                    "    suffix = [1] * n\n"
                    "    for i in range(1, n):\n"
                    "        prefix[i] = prefix[i - 1] * nums[i - 1]\n"
                    "    for i in range(n - 2, -1, -1):\n"
                    "        suffix[i] = suffix[i + 1] * nums[i + 1]\n"
                    "    return [prefix[i] * suffix[i] for i in range(n)]"
                ),
            },
        },
        {
            "title": "Division Trick (Disallowed — Pedagogical Only)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "If division were allowed: total = product of all, then `answer[i] = total / nums[i]`. Breaks "
                "the moment any element is zero (and is explicitly forbidden by the problem). Worth mentioning "
                "only to acknowledge you've considered it and discarded it — never as your final answer."
            ),
            "code": {
                "python": (
                    "def product_except_self(nums):\n"
                    "    # NOTE: violates the no-division constraint; included only for discussion.\n"
                    "    zeros = nums.count(0)\n"
                    "    if zeros >= 2:\n"
                    "        return [0] * len(nums)\n"
                    "    if zeros == 1:\n"
                    "        prod = 1\n"
                    "        for n in nums:\n"
                    "            if n != 0:\n"
                    "                prod *= n\n"
                    "        return [prod if n == 0 else 0 for n in nums]\n"
                    "    total = 1\n"
                    "    for n in nums:\n"
                    "        total *= n\n"
                    "    return [total // n for n in nums]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. State the obvious: divide the total by each element. Then immediately disqualify it (no division allowed; breaks on zeros).",
        "2. Reframe: `answer[i]` is the product of everything strictly to the left of i, times everything strictly to the right.",
        "3. Two halves → two passes. Build prefix products in one direction, suffix products in the other, multiply pairwise.",
        "4. Optimise space: prefix products go directly into the output array on pass 1; pass 2 maintains a single running suffix variable and multiplies in place.",
        "5. Verify on the zero case: a single zero kills every slot except its own; multiple zeros kill everything. The two-pass approach handles both naturally because it never divides.",
        "6. Sign check on negatives: track an even/odd count mentally — three negatives multiply to negative, four to positive.",
    ],
    "tips": [
        "The 'output doesn't count' clause is what makes the O(1) extra-space follow-up tractable. Mention it explicitly.",
        "Don't conflate 'O(1) extra space' with 'O(1) total space' — the output is O(n) by definition.",
        "Pre-empt the question: 'why not just divide?' Answer: zeros + the explicit constraint.",
        "Common follow-up: 'What if integer overflow is a concern?' Track the prefix and suffix in 64-bit and downcast at the end (or normalise modulo a prime if asked for modular product).",
        "Common variant: 'Return the product of every element except the k smallest/largest.' Same prefix/suffix technique, but the indices to skip are computed first.",
    ],
    "companies": ["Amazon", "Facebook", "Google", "Microsoft", "Apple"],
    "topics": ["Array", "Prefix Sum"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1) extra",
}


def REFERENCE(nums):
    n = len(nums)
    answer = [1] * n
    prefix = 1
    for i in range(n):
        answer[i] = prefix
        prefix *= nums[i]
    suffix = 1
    for i in range(n - 1, -1, -1):
        answer[i] *= suffix
        suffix *= nums[i]
    return answer


register(PAYLOAD, REFERENCE)
