"""Single Number — Easy. Bit Manipulation / Hash Set.

The XOR self-cancellation classic. Every duplicate cancels out, leaving
only the singleton. The hash-set / sum-trick variants are the natural
'I forgot the XOR property' fallbacks — worth knowing all three so the
interviewer can probe space-vs-clarity trade-offs.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Single Number",
    "difficulty": "Easy",
    "description": (
        "Given a **non-empty** array of integers `nums`, every element appears **twice** except for one. "
        "Find that single one.\n\n"
        "You must implement a solution with **linear runtime complexity** and use only **constant extra "
        "space**.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [2,2,1]`\n"
        "- Output: `1`\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [4,1,2,1,2]`\n"
        "- Output: `4`\n"
        "- Explanation: 1 and 2 each appear twice; 4 is the singleton."
    ),
    "hints": [
        "Brute force: nested loops checking whether each element has a partner — O(n²) time, O(1) space. "
        "States the problem; never the answer for the linear-time constraint.",
        "Hash set / counter: one pass to add (or toggle), one pass to find the element with count 1. "
        "O(n) time but O(n) extra space — fails the constant-space requirement.",
        "Math trick: `2 * sum(set(nums)) - sum(nums)` equals the singleton. Clean one-liner, but the "
        "intermediate `2 * sum(set(...))` can overflow fixed-width integer types and `set()` itself is O(n) space.",
        "XOR property: `x ^ x = 0` and `x ^ 0 = x`, and XOR is commutative + associative. So XOR-ing every "
        "element together cancels every pair, leaving the singleton alone. O(n) time, O(1) space, no overflow.",
        "Walk the array once accumulating `result ^= num`. Order doesn't matter — pairs cancel regardless "
        "of where they sit in the array.",
    ],
    "constraints": [
        "1 <= nums.length <= 3 * 10⁴",
        "-3 * 10⁴ <= nums[i] <= 3 * 10⁴",
        "Each element appears twice except for exactly one element which appears once.",
    ],
    "starter_code": {
        "python": "def single_number(nums):\n    # Your code here\n    pass",
        "javascript": "function singleNumber(nums) {\n    // Your code here\n}",
        "java": "public int singleNumber(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[2,2,1], [4,1,2,1,2], [1]]\n"
            "    for nums in cases:\n"
            "        print(f\"single_number({nums}) = {single_number(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[2,2,1], [4,1,2,1,2], [1]].forEach(nums =>\n"
            "    console.log(`singleNumber =`, singleNumber(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.singleNumber(new int[]{4,1,2,1,2}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [2, 2, 1]}, "expected": 1,
         "description": "Classic — singleton at the tail", "tags": ["basic"]},
        {"input": {"nums": [4, 1, 2, 1, 2]}, "expected": 4,
         "description": "LC canonical example — singleton at the head", "tags": ["basic"]},
        {"input": {"nums": [1]}, "expected": 1,
         "description": "Single element — only one value, it's the answer", "tags": ["edge"]},
        {"input": {"nums": [-1, -1, -2]}, "expected": -2,
         "description": "All negatives — XOR works on two's-complement representation", "tags": ["edge"]},
        {"input": {"nums": [-5, 3, 3, -5, 7]}, "expected": 7,
         "description": "Mixed positive and negative values", "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 1, 3, 2, 5, 3]}, "expected": 5,
         "description": "Pairs interleaved out of order — XOR doesn't care about position", "tags": ["tricky"]},
        {"input": {"nums": [10, 20, 30, 10, 30]}, "expected": 20,
         "description": "Singleton in the middle", "tags": ["basic"]},
        {"input": {"nums": [30000, -30000, 30000]}, "expected": -30000,
         "description": "Boundary values from the constraint range", "tags": ["edge"]},
        {"input": {"nums": [a for pair in zip(range(1, 5001), range(1, 5001)) for a in pair] + [99999]},
         "expected": 99999,
         "description": "10K duplicates + a single trailing singleton — stress test", "tags": ["large"]},
        {"input": {"nums": [1, 2, 3, 1, 2, 3, 1, 2, 3, 4, 1, 2, 3] if False else
                            [1, 2, 1, 2, 1, 2, 1, 2, 9, 3, 4, 3, 4]}, "expected": 9,
         "description": "Alternating duplicates — XOR cancels regardless of ordering", "tags": ["tricky"]},
        {"input": {"nums": [0, 0, 7]}, "expected": 7,
         "description": "Zero pairs cancel cleanly — `0 ^ 0 ^ 7 = 7`", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "XOR Accumulator (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "XOR every element into a running accumulator. By `x ^ x = 0` and `x ^ 0 = x`, every "
                "duplicate pair cancels and the singleton survives. One pass, one integer of state, "
                "no overflow concerns."
            ),
            "code": {
                "python": (
                    "def single_number(nums):\n"
                    "    result = 0\n"
                    "    for n in nums:\n"
                    "        result ^= n\n"
                    "    return result"
                ),
                "javascript": (
                    "function singleNumber(nums) {\n"
                    "    let result = 0;\n"
                    "    for (const n of nums) result ^= n;\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public int singleNumber(int[] nums) {\n"
                    "    int result = 0;\n"
                    "    for (int n : nums) result ^= n;\n"
                    "    return result;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Hash Set (Toggle)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk the array; add each value on first sight, remove on second sight. The set ends "
                "with exactly one element — the singleton. Linear time but O(n) space, so it fails "
                "the constant-space requirement; mention as the natural fallback if XOR doesn't come to mind."
            ),
            "code": {
                "python": (
                    "def single_number(nums):\n"
                    "    seen = set()\n"
                    "    for n in nums:\n"
                    "        if n in seen:\n"
                    "            seen.remove(n)\n"
                    "        else:\n"
                    "            seen.add(n)\n"
                    "    return seen.pop()"
                ),
                "javascript": (
                    "function singleNumber(nums) {\n"
                    "    const seen = new Set();\n"
                    "    for (const n of nums) {\n"
                    "        if (seen.has(n)) seen.delete(n);\n"
                    "        else seen.add(n);\n"
                    "    }\n"
                    "    return [...seen][0];\n"
                    "}"
                ),
                "java": (
                    "public int singleNumber(int[] nums) {\n"
                    "    java.util.Set<Integer> seen = new java.util.HashSet<>();\n"
                    "    for (int n : nums) {\n"
                    "        if (!seen.add(n)) seen.remove(n);\n"
                    "    }\n"
                    "    return seen.iterator().next();\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force: for each element, scan the rest for its partner — O(n²). State it as the baseline.",
        "2. Hash map / counter: one pass to count, one pass to find count == 1. O(n) time, O(n) space — "
        "violates the constant-space constraint but is the natural first improvement.",
        "3. Sum trick: `2 * sum(set(nums)) - sum(nums)`. Clever, but `set()` is O(n) and large sums can "
        "overflow fixed-width ints in C/Java without a wider accumulator.",
        "4. XOR insight: `a ^ a = 0`, `a ^ 0 = a`, XOR is commutative and associative. XOR-ing every "
        "element collapses each duplicate pair to 0; the singleton survives.",
        "5. Implementation is three lines: a running accumulator, one loop, return. No edge cases.",
        "6. Sanity-check edges: single element (XOR with 0 returns itself), negative values "
        "(two's-complement XOR is well-defined), zeros (cancel like any other pair).",
    ],
    "tips": [
        "Memorise the two XOR identities: `x ^ x = 0` and `x ^ 0 = x`. Half the bit-tricks in interviews "
        "fall out of these.",
        "When the problem says 'O(n) time and O(1) space' and involves duplicates, XOR is almost always "
        "the intended trick.",
        "Variant — Single Number II (each element appears 3 times except one): use bitwise counters mod 3, "
        "or two accumulator variables (`ones`, `twos`). XOR alone is insufficient.",
        "Variant — Single Number III (two singletons): XOR everything to get `a ^ b`, isolate any set bit "
        "to partition the array, then XOR each partition separately.",
        "Don't reach for `Counter` or `set()` if the interviewer asks for constant space — they'll "
        "specifically fail you on it. Lead with XOR.",
        "Order independence is a feature: if asked to handle a streaming input, the XOR accumulator "
        "still works without any modification.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Apple", "Bloomberg", "Palantir"],
    "topics": ["Array", "Bit Manipulation"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    result = 0
    for n in nums:
        result ^= n
    return result


register(PAYLOAD, REFERENCE)
