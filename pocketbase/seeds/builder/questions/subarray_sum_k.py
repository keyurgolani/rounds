"""Subarray Sum Equals K — Medium. Prefix Sum + HashMap.

Classic prefix-sum-with-hashmap problem. The 'sliding window' instinct
fails because negatives are allowed — windows aren't monotone in their
sum. The right reframe: prefix[i] - prefix[j] = k means we want, for
each i, the count of earlier prefixes equal to prefix[i] - k. One pass,
one hashmap of prefix-sum frequencies.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Subarray Sum Equals K",
    "difficulty": "Medium",
    "description": (
        "Given an integer array `nums` and an integer `k`, return the **number of contiguous "
        "non-empty subarrays** whose sum equals `k`.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,1,1]`, `k = 2`\n"
        "- Output: `2`\n"
        "- Explanation: The subarrays `[1,1]` (indices 0..1) and `[1,1]` (indices 1..2) each sum to 2.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [1,2,3]`, `k = 3`\n"
        "- Output: `2`\n"
        "- Explanation: `[1,2]` and `[3]` each sum to 3."
    ),
    "hints": [
        "Brute force: every (i, j) pair, sum the slice → O(n³). Or precompute prefix sums and check every "
        "(i, j) → O(n²). State both; submit neither for n up to 2·10⁴.",
        "Define `prefix[i] = nums[0] + nums[1] + ... + nums[i-1]`, with `prefix[0] = 0`. Then the sum of "
        "subarray `nums[j..i-1]` equals `prefix[i] - prefix[j]`.",
        "We want to count `(j, i)` pairs with `j < i` and `prefix[i] - prefix[j] = k`, i.e. "
        "`prefix[j] = prefix[i] - k`. As you walk `i` left-to-right, look up how many earlier prefixes equal "
        "`prefix[i] - k`.",
        "Maintain a hashmap `count[s] = number of prefixes seen so far equal to s`. Seed it with "
        "`count[0] = 1` so a subarray starting at index 0 with sum k is counted.",
        "Negatives are allowed → sliding window does NOT work (the running sum isn't monotone in window size). "
        "Prefix-sum + hashmap is the right tool.",
    ],
    "constraints": [
        "1 <= nums.length <= 2·10⁴",
        "-1000 <= nums[i] <= 1000 (negatives allowed — no sliding window)",
        "-10⁷ <= k <= 10⁷",
    ],
    "starter_code": {
        "python": "def subarray_sum(nums, k):\n    # Your code here\n    pass",
        "javascript": "function subarraySum(nums, k) {\n    // Your code here\n}",
        "java": "public int subarraySum(int[] nums, int k) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([1,1,1], 2), ([1,2,3], 3), ([1,-1,1,-1], 0)]\n"
            "    for nums, k in cases:\n"
            "        print(f\"subarray_sum({nums}, {k}) = {subarray_sum(nums, k)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,1,1], 2], [[1,2,3], 3], [[1,-1,1,-1], 0]].forEach(([nums, k]) =>\n"
            "    console.log(`subarraySum =`, subarraySum(nums, k))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.subarraySum(new int[]{1,1,1}, 2));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 1, 1], "k": 2}, "expected": 2,
         "description": "Classic — two overlapping [1,1] windows", "tags": ["basic"]},
        {"input": {"nums": [1, 2, 3], "k": 3}, "expected": 2,
         "description": "Classic — [1,2] and [3]", "tags": ["basic"]},
        {"input": {"nums": [1, -1, 1, -1], "k": 0}, "expected": 4,
         "description": "Negatives → multiple zero-sum windows: [1,-1], [-1,1], [1,-1], [1,-1,1,-1]",
         "tags": ["tricky", "negatives"]},
        {"input": {"nums": [5], "k": 5}, "expected": 1,
         "description": "Single element matching k", "tags": ["edge"]},
        {"input": {"nums": [5], "k": 3}, "expected": 0,
         "description": "Single element not matching k", "tags": ["edge"]},
        {"input": {"nums": [0, 0, 0, 0], "k": 0}, "expected": 10,
         "description": "All zeros, k=0 → C(5,2) = 10 contiguous windows", "tags": ["tricky"]},
        {"input": {"nums": [0, 0, 0, 0], "k": 1}, "expected": 0,
         "description": "All zeros, k=1 → no subarray reaches 1", "tags": ["edge"]},
        {"input": {"nums": [1, 0, 0, 1], "k": 1}, "expected": 6,
         "description": "Zeros injected — six windows sum to 1: [1] at idx 0, [1,0], [1,0,0], "
                        "[0,0,1], [0,1], [1] at idx 3",
         "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 3], "k": 7}, "expected": 0,
         "description": "k=7 unreachable (max single-window sum is 6)", "tags": ["edge"]},
        {"input": {"nums": [1, 2, 3], "k": 0}, "expected": 0,
         "description": "k=0 with strictly positive nums → no zero-sum subarray", "tags": ["edge"]},
        {"input": {"nums": [-1, -1, 1], "k": 0}, "expected": 1,
         "description": "Negatives — only [-1,1] sums to 0", "tags": ["negatives"]},
        {"input": {"nums": [1, -1] * 1000, "k": 0}, "expected": 1000000,
         "description": "Large alternating ±1, k=0 — every prefix sum is 0 or 1; "
                        "1000 zero-prefixes × 999/2 + diagonal = 1,000,000 windows",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Prefix Sum + HashMap (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk left-to-right maintaining the running prefix sum `s`. For each index, the number of "
                "subarrays ending here with sum `k` equals the count of earlier prefixes equal to `s - k`. "
                "Keep a hashmap of prefix-sum frequencies; seed it with `{0: 1}` so subarrays starting at "
                "index 0 are counted. Add to the running answer, then increment `count[s]`."
            ),
            "code": {
                "python": (
                    "def subarray_sum(nums, k):\n"
                    "    count = {0: 1}\n"
                    "    s = 0\n"
                    "    answer = 0\n"
                    "    for x in nums:\n"
                    "        s += x\n"
                    "        answer += count.get(s - k, 0)\n"
                    "        count[s] = count.get(s, 0) + 1\n"
                    "    return answer"
                ),
                "javascript": (
                    "function subarraySum(nums, k) {\n"
                    "    const count = new Map([[0, 1]]);\n"
                    "    let s = 0, answer = 0;\n"
                    "    for (const x of nums) {\n"
                    "        s += x;\n"
                    "        answer += count.get(s - k) || 0;\n"
                    "        count.set(s, (count.get(s) || 0) + 1);\n"
                    "    }\n"
                    "    return answer;\n"
                    "}"
                ),
                "java": (
                    "public int subarraySum(int[] nums, int k) {\n"
                    "    java.util.Map<Integer, Integer> count = new java.util.HashMap<>();\n"
                    "    count.put(0, 1);\n"
                    "    int s = 0, answer = 0;\n"
                    "    for (int x : nums) {\n"
                    "        s += x;\n"
                    "        answer += count.getOrDefault(s - k, 0);\n"
                    "        count.merge(s, 1, Integer::sum);\n"
                    "    }\n"
                    "    return answer;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "For each start index `i`, accumulate the running sum and increment the answer whenever it "
                "hits `k`. Mention as the baseline; never submit for n up to 2·10⁴ in a tight time budget."
            ),
            "code": {
                "python": (
                    "def subarray_sum(nums, k):\n"
                    "    answer = 0\n"
                    "    for i in range(len(nums)):\n"
                    "        s = 0\n"
                    "        for j in range(i, len(nums)):\n"
                    "            s += nums[j]\n"
                    "            if s == k:\n"
                    "                answer += 1\n"
                    "    return answer"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force is O(n²) (or O(n³) without prefix sums). State the baseline.",
        "2. Reframe with prefix sums: subarray `nums[j..i-1]` has sum `prefix[i] - prefix[j]`. We want this "
        "to equal `k`, i.e. `prefix[j] = prefix[i] - k`.",
        "3. As we walk `i`, count earlier prefixes equal to `prefix[i] - k`. A hashmap of prefix-sum "
        "frequencies makes that O(1) per step.",
        "4. Seed the hashmap with `{0: 1}` so the empty prefix is a valid `j` — this captures subarrays "
        "starting at index 0.",
        "5. Critical ordering: add `count[s - k]` to the answer *before* incrementing `count[s]`. Otherwise, "
        "when k=0, the current index would match itself and inflate the count.",
        "6. Negatives kill the sliding-window approach (running sum isn't monotone in window length). "
        "Prefix-sum + hashmap handles them naturally.",
    ],
    "tips": [
        "The seed `count[0] = 1` is the most-forgotten line. Without it, you under-count by the number of "
        "subarrays starting at index 0.",
        "Order matters: read `count[s - k]` first, then write `count[s] += 1`. Reversing the order silently "
        "breaks the k=0 case.",
        "Sliding window is wrong here — say so out loud. With negatives, growing the window can decrease the "
        "sum and shrinking can increase it; there's no monotone invariant.",
        "All-zero arrays with k=0 are the spiciest test. The answer is C(n+1, 2) = n*(n+1)/2 — the number of "
        "contiguous non-empty subarrays. Easy to off-by-one.",
        "Common follow-ups: 'Continuous Subarray Sum' (LC 523) uses the same trick but stores `prefix mod k`; "
        "'Subarrays Divisible by K' (LC 974) is the count variant. Same hashmap, different key.",
        "If the interviewer asks for 'longest' instead of 'count', store the *first* index a prefix is seen, "
        "not its frequency. Same data structure, different bookkeeping.",
    ],
    "companies": ["Facebook", "Amazon", "Google", "Microsoft", "Bloomberg"],
    "topics": ["Array", "Hash Table", "Prefix Sum"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(nums, k):
    count = {0: 1}
    s = 0
    answer = 0
    for x in nums:
        s += x
        answer += count.get(s - k, 0)
        count[s] = count.get(s, 0) + 1
    return answer


register(PAYLOAD, REFERENCE)
