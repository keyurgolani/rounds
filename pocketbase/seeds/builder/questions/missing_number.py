"""Missing Number — Easy. Bit Manipulation / Math.

The 'one number is missing from a permutation' classic. Three canonical
solutions worth knowing: sum formula (cute, but watch overflow on the
intermediate sum in Java), XOR (the interview-favorite, no overflow,
single pass), and sort-and-scan (state it, never submit it). The XOR
trick is the same pairing identity that powers 'Single Number' and
'Single Number III' — pattern recognition pays off later.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Missing Number",
    "difficulty": "Easy",
    "description": (
        "Given an array `nums` containing `n` distinct numbers in the range `[0, n]`, return "
        "*the only number in the range that is missing from the array*.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [3,0,1]`\n"
        "- Output: `2`\n"
        "- Explanation: `n = 3` since there are 3 numbers, so all numbers are in the range `[0,3]`. "
        "`2` is the missing number.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [9,6,4,2,3,5,7,0,1]`\n"
        "- Output: `8`\n"
        "- Explanation: `n = 9` so all numbers are in the range `[0,9]`. `8` is the missing number."
    ),
    "hints": [
        "The expected sum of `[0..n]` is `n*(n+1)/2`. Subtract the actual sum and you have the missing number — O(n) time, O(1) space.",
        "Worried about integer overflow on the sum (Java/C++ with large n)? Accumulate `total += i - nums[i]` in one loop instead — same idea, no large intermediate.",
        "XOR trick: `0 ^ 1 ^ 2 ^ ... ^ n` XORed with every element of `nums` cancels every present number, leaving the missing one. No arithmetic, no overflow.",
        "Sort the array and scan for the first index `i` where `nums[i] != i`. O(n log n) — mention as a baseline; never submit it.",
        "Cyclic-sort placement (put each `nums[i]` at index `nums[i]`) also works and generalises to 'Find All Missing/Duplicate' variants — overkill here but worth recognising.",
    ],
    "constraints": [
        "n == nums.length",
        "1 <= n <= 10⁴",
        "0 <= nums[i] <= n, all values distinct",
    ],
    "starter_code": {
        "python": "def missing_number(nums):\n    # Your code here\n    pass",
        "javascript": "function missingNumber(nums) {\n    // Your code here\n}",
        "java": "public int missingNumber(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[3,0,1], [0,1], [9,6,4,2,3,5,7,0,1]]\n"
            "    for nums in cases:\n"
            "        print(f\"missing_number({nums}) = {missing_number(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[3,0,1], [0,1], [9,6,4,2,3,5,7,0,1]].forEach(nums =>\n"
            "    console.log(`missingNumber =`, missingNumber(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.missingNumber(new int[]{3,0,1}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [3, 0, 1]}, "expected": 2,
         "description": "Classic LC example — missing 2", "tags": ["basic"]},
        {"input": {"nums": [0, 1]}, "expected": 2,
         "description": "Missing the top of the range", "tags": ["basic"]},
        {"input": {"nums": [9, 6, 4, 2, 3, 5, 7, 0, 1]}, "expected": 8,
         "description": "Unsorted, n=9 — missing 8", "tags": ["basic"]},
        {"input": {"nums": [1, 2, 3]}, "expected": 0,
         "description": "Missing 0 (smallest)", "tags": ["edge"]},
        {"input": {"nums": [0, 1, 2]}, "expected": 3,
         "description": "Missing n (largest)", "tags": ["edge"]},
        {"input": {"nums": [0]}, "expected": 1,
         "description": "Single element, has 0 — missing 1", "tags": ["edge"]},
        {"input": {"nums": [1]}, "expected": 0,
         "description": "Single element, has 1 — missing 0", "tags": ["edge"]},
        {"input": {"nums": [2, 0, 3, 4, 1, 6]}, "expected": 5,
         "description": "Missing in the middle", "tags": ["tricky"]},
        {"input": {"nums": list(range(5000)) + list(range(5001, 10001))},
         "expected": 5000,
         "description": "10K elements, missing 5000 — large input", "tags": ["large"]},
        {"input": {"nums": list(range(1, 10001))}, "expected": 0,
         "description": "10K elements, missing 0 — sum-formula stress test", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Sum Formula (Gauss)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "The sum of `[0..n]` is `n*(n+1)/2` (Gauss). Subtract the actual sum of `nums` and "
                "what's left is the missing number. One pass, two scalars. In strongly-typed "
                "languages with bounded ints (Java), prefer accumulating `i - nums[i]` to avoid the "
                "intermediate sum overflowing for large n."
            ),
            "code": {
                "python": (
                    "def missing_number(nums):\n"
                    "    n = len(nums)\n"
                    "    expected = n * (n + 1) // 2\n"
                    "    return expected - sum(nums)"
                ),
                "javascript": (
                    "function missingNumber(nums) {\n"
                    "    const n = nums.length;\n"
                    "    const expected = (n * (n + 1)) / 2;\n"
                    "    let actual = 0;\n"
                    "    for (const x of nums) actual += x;\n"
                    "    return expected - actual;\n"
                    "}"
                ),
                "java": (
                    "public int missingNumber(int[] nums) {\n"
                    "    int n = nums.length;\n"
                    "    int total = n;  // start with n; loop covers indices 0..n-1\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        total += i - nums[i];\n"
                    "    }\n"
                    "    return total;\n"
                    "}"
                ),
            },
        },
        {
            "title": "XOR Cancellation",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "XOR is its own inverse: `x ^ x == 0`. XOR every index `0..n` with every value in "
                "`nums`. Every present value cancels its matching index, and the lone surviving "
                "term is the missing number. No arithmetic — no overflow risk — and this is the "
                "exact pattern used by 'Single Number'."
            ),
            "code": {
                "python": (
                    "def missing_number(nums):\n"
                    "    result = len(nums)\n"
                    "    for i, v in enumerate(nums):\n"
                    "        result ^= i ^ v\n"
                    "    return result"
                ),
                "javascript": (
                    "function missingNumber(nums) {\n"
                    "    let result = nums.length;\n"
                    "    for (let i = 0; i < nums.length; i++) {\n"
                    "        result ^= i ^ nums[i];\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public int missingNumber(int[] nums) {\n"
                    "    int result = nums.length;\n"
                    "    for (int i = 0; i < nums.length; i++) {\n"
                    "        result ^= i ^ nums[i];\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sort and Scan (Baseline)",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(1)",
            "description": (
                "Sort the array, then walk it. The first index where `nums[i] != i` is the missing "
                "number; if every index matches, the missing number is `n`. Mention as a baseline; "
                "never submit it when O(n) is on the table."
            ),
            "code": {
                "python": (
                    "def missing_number(nums):\n"
                    "    nums.sort()\n"
                    "    for i, v in enumerate(nums):\n"
                    "        if i != v:\n"
                    "            return i\n"
                    "    return len(nums)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force: for each k in [0..n], check if k in nums → O(n²). State it; don't submit it.",
        "2. Hash set: drop nums into a set, scan [0..n] for the missing key → O(n) time, O(n) space. Clean but uses memory.",
        "3. Sum formula: expected − actual. O(n) time, O(1) space. The cleanest one-liner.",
        "4. Watch overflow: in Java/C++, `n*(n+1)/2` can overflow for very large n. Accumulate `i - nums[i]` in a single pass to sidestep the issue.",
        "5. XOR variant: same complexity, no arithmetic, no overflow concern. Recognise the pattern — it's the same trick as 'Single Number'.",
        "6. Edge cases: missing 0 (smallest), missing n (largest), single-element arrays. All three solutions handle them with no special casing.",
    ],
    "tips": [
        "Mention all three approaches in the interview — sum, XOR, sort. Pick XOR or running-delta sum for the implementation.",
        "If asked about overflow, prefer the running-delta form `total += i - nums[i]` over computing the full Gauss sum first.",
        "Common follow-up — 'Find All Numbers Disappeared in an Array' (LC 448): same setup, multiple missing. Cyclic-sort or in-place negation.",
        "Common follow-up — 'Single Number' (LC 136): every element appears twice except one. Pure XOR — same identity.",
        "Common follow-up — 'Missing Number' with the constraint that you can only read each element once and use O(1) memory: XOR is the textbook answer.",
        "Don't sort just to find one missing number when O(n) works — interviewers will downgrade you to the sort-and-scan tier.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Bloomberg", "Apple"],
    "topics": ["Array", "Math", "Bit Manipulation", "Hash Table"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    result = len(nums)
    for i, v in enumerate(nums):
        result ^= i ^ v
    return result


register(PAYLOAD, REFERENCE)
