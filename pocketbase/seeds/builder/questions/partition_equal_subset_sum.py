"""Partition Equal Subset Sum — Medium. 0/1 Knapsack / Subset Sum.

The canonical 'subset sum' reduction: split into two equal-sum halves iff
some subset hits `total/2`. Quick parity reject (odd total → impossible),
then a 1D bool DP walked high→low to preserve 0/1 semantics. The Python
bitset trick (treating an int as a bitset of reachable sums) is the
chef's-kiss optimisation worth showing once you've nailed the DP.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Partition Equal Subset Sum",
    "difficulty": "Medium",
    "description": (
        "Given an integer array `nums` containing only positive integers, return `true` if you can "
        "partition the array into two subsets such that the sum of the elements in both subsets is "
        "equal, otherwise return `false`.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,5,11,5]`\n"
        "- Output: `true`\n"
        "- Explanation: The array can be partitioned as `[1, 5, 5]` and `[11]`.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [1,2,3,5]`\n"
        "- Output: `false`\n"
        "- Explanation: The array cannot be partitioned into equal sum subsets."
    ),
    "hints": [
        "If `sum(nums)` is odd, no partition is possible — return False immediately. This kills half the inputs for free.",
        "Otherwise let `target = sum(nums) // 2`. The question reduces to: 'is there a subset of `nums` whose sum equals `target`?' That's classic subset-sum / 0-1 knapsack.",
        "DP state: `dp[s]` = True iff some subset of the numbers seen so far sums to `s`. Initialise `dp[0] = True`.",
        "For each `num`, update `dp[s] = dp[s] or dp[s - num]` for `s` from `target` down to `num`. The reverse walk is what enforces 0/1 (each number used at most once).",
        "Python flex: represent `dp` as a single integer bitset. `bits |= bits << num` updates all reachable sums at once. Check `(bits >> target) & 1`.",
    ],
    "constraints": [
        "1 <= nums.length <= 200",
        "1 <= nums[i] <= 100",
    ],
    "starter_code": {
        "python": "def can_partition(nums):\n    # Your code here\n    pass",
        "javascript": "function canPartition(nums) {\n    // Your code here\n}",
        "java": "public boolean canPartition(int[] nums) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[1,5,11,5], [1,2,3,5], [1,2,3,4,5,6,7]]\n"
            "    for nums in cases:\n"
            "        print(f\"can_partition({nums}) = {can_partition(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,5,11,5], [1,2,3,5]].forEach(nums =>\n"
            "    console.log(`canPartition =`, canPartition(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.canPartition(new int[]{1,5,11,5}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 5, 11, 5]}, "expected": True,
         "description": "Classic — [1,5,5] vs [11], both sum to 11", "tags": ["basic"]},
        {"input": {"nums": [1, 2, 3, 5]}, "expected": False,
         "description": "Sum = 11, odd → no partition possible", "tags": ["basic"]},
        {"input": {"nums": [1, 2, 3, 4, 5, 6, 7]}, "expected": True,
         "description": "Sum = 28, target = 14 (e.g. [7,6,1] vs [2,3,4,5])", "tags": ["basic"]},
        {"input": {"nums": [1]}, "expected": False,
         "description": "Single element — sum is odd, can't split", "tags": ["edge"]},
        {"input": {"nums": [2, 2, 2, 2]}, "expected": True,
         "description": "All equal evens — trivially splittable", "tags": ["edge"]},
        {"input": {"nums": [100]}, "expected": False,
         "description": "Single element with even value — but no second subset to balance it", "tags": ["edge"]},
        {"input": {"nums": [1, 1, 1, 1, 1, 1, 1, 1, 1]}, "expected": False,
         "description": "Nine ones — sum = 9, odd → False", "tags": ["edge"]},
        {"input": {"nums": [3, 3, 3, 4, 5]}, "expected": True,
         "description": "Sum = 18, target = 9 — [4,5] vs [3,3,3]", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "1D Bool DP, High→Low Walk (Optimal Standard)",
            "time_complexity": "O(n × target)",
            "space_complexity": "O(target)",
            "description": (
                "Reduce to subset-sum on `target = total / 2`. After parity reject, maintain `dp[s]` "
                "= 'is sum `s` reachable?'. For each number, update `s` from `target` down to `num` "
                "so that each element is used at most once. Early exit when `dp[target]` flips True."
            ),
            "code": {
                "python": (
                    "def can_partition(nums):\n"
                    "    total = sum(nums)\n"
                    "    if total % 2:\n"
                    "        return False\n"
                    "    target = total // 2\n"
                    "    dp = [False] * (target + 1)\n"
                    "    dp[0] = True\n"
                    "    for num in nums:\n"
                    "        if num > target:\n"
                    "            return False\n"
                    "        for s in range(target, num - 1, -1):\n"
                    "            if dp[s - num]:\n"
                    "                dp[s] = True\n"
                    "        if dp[target]:\n"
                    "            return True\n"
                    "    return dp[target]"
                ),
                "javascript": (
                    "function canPartition(nums) {\n"
                    "    const total = nums.reduce((a, b) => a + b, 0);\n"
                    "    if (total % 2) return false;\n"
                    "    const target = total / 2;\n"
                    "    const dp = new Array(target + 1).fill(false);\n"
                    "    dp[0] = true;\n"
                    "    for (const num of nums) {\n"
                    "        if (num > target) return false;\n"
                    "        for (let s = target; s >= num; s--) {\n"
                    "            if (dp[s - num]) dp[s] = true;\n"
                    "        }\n"
                    "        if (dp[target]) return true;\n"
                    "    }\n"
                    "    return dp[target];\n"
                    "}"
                ),
                "java": (
                    "public boolean canPartition(int[] nums) {\n"
                    "    int total = 0;\n"
                    "    for (int n : nums) total += n;\n"
                    "    if (total % 2 != 0) return false;\n"
                    "    int target = total / 2;\n"
                    "    boolean[] dp = new boolean[target + 1];\n"
                    "    dp[0] = true;\n"
                    "    for (int num : nums) {\n"
                    "        if (num > target) return false;\n"
                    "        for (int s = target; s >= num; s--) {\n"
                    "            if (dp[s - num]) dp[s] = true;\n"
                    "        }\n"
                    "        if (dp[target]) return true;\n"
                    "    }\n"
                    "    return dp[target];\n"
                    "}"
                ),
            },
        },
        {
            "title": "2D DP (Pedagogical)",
            "time_complexity": "O(n × target)",
            "space_complexity": "O(n × target)",
            "description": (
                "Classic textbook 0/1 knapsack table: `dp[i][s]` = 'can we form sum `s` using a subset "
                "of the first `i` numbers?'. Either skip `nums[i-1]` (use `dp[i-1][s]`) or take it "
                "(use `dp[i-1][s - nums[i-1]]`). Worth writing once before collapsing to 1D."
            ),
            "code": {
                "python": (
                    "def can_partition(nums):\n"
                    "    total = sum(nums)\n"
                    "    if total % 2:\n"
                    "        return False\n"
                    "    target = total // 2\n"
                    "    n = len(nums)\n"
                    "    dp = [[False] * (target + 1) for _ in range(n + 1)]\n"
                    "    for i in range(n + 1):\n"
                    "        dp[i][0] = True\n"
                    "    for i in range(1, n + 1):\n"
                    "        num = nums[i - 1]\n"
                    "        for s in range(1, target + 1):\n"
                    "            dp[i][s] = dp[i - 1][s]\n"
                    "            if s >= num:\n"
                    "                dp[i][s] = dp[i][s] or dp[i - 1][s - num]\n"
                    "    return dp[n][target]"
                ),
            },
        },
        {
            "title": "Bitset Trick (Pythonic Speed)",
            "time_complexity": "O(n × target / word_size)",
            "space_complexity": "O(target / word_size)",
            "description": (
                "Encode the entire `dp` array as a single Python big-integer where bit `s` is set iff "
                "sum `s` is reachable. Each iteration becomes `bits |= bits << num` — a single shift-"
                "and-or that updates every reachable sum simultaneously, riding on the CPU's word-level "
                "parallelism. ~64× faster in practice. The check is `(bits >> target) & 1`."
            ),
            "code": {
                "python": (
                    "def can_partition(nums):\n"
                    "    total = sum(nums)\n"
                    "    if total % 2:\n"
                    "        return False\n"
                    "    target = total // 2\n"
                    "    bits = 1  # bit 0 set: sum 0 is reachable\n"
                    "    for num in nums:\n"
                    "        bits |= bits << num\n"
                    "    return (bits >> target) & 1 == 1"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Both subsets must sum to `total / 2`. So if `total` is odd, return False up front — pure parity argument.",
        "2. Reframe: 'pick a subset summing to `target = total / 2`'. That's textbook subset-sum / 0-1 knapsack.",
        "3. State the 2D recurrence first: `dp[i][s] = dp[i-1][s] or dp[i-1][s - nums[i-1]]`. Two choices: skip or take.",
        "4. Collapse to 1D: only the previous row matters. Walk `s` from `target` down to `num` so the cell you read (`dp[s - num]`) reflects the *previous* row, enforcing 0/1 (each item used once).",
        "5. Add cheap pruning — if any single number exceeds `target`, return False; once `dp[target]` flips True, return immediately.",
        "6. Edge cases: single element (always False), odd sum (always False), `nums[i] > target` (always False).",
    ],
    "tips": [
        "Direction matters. Walking `s` low→high would let you pick the same element multiple times — that's the *unbounded* knapsack. For 0/1 you must walk high→low.",
        "The bitset trick is gold in Python interviews — `bits |= bits << num` does an entire DP row in a single CPU-friendly operation. Bring it up after explaining the bool DP.",
        "Common follow-up — Partition to K Equal Sum Subsets (LC 698): generalise to k buckets. The DP doesn't extend cleanly; you switch to backtracking with bitmask memoisation.",
        "Common follow-up — Target Sum (LC 494): assign +/- signs to reach a target. Reduces to subset-sum on `(total + target) / 2`. Same DP, different framing.",
        "Don't reach for recursion + memo unless you have to — the 1D bool DP is shorter, faster, and easier to reason about.",
    ],
    "companies": ["Amazon", "Goldman Sachs"],
    "topics": ["Array", "Dynamic Programming"],
    "time_complexity": "O(n × target) where target = sum(nums) / 2",
    "space_complexity": "O(target)",
}


def REFERENCE(nums):
    total = sum(nums)
    if total % 2:
        return False
    target = total // 2
    dp = [False] * (target + 1)
    dp[0] = True
    for num in nums:
        if num > target:
            return False
        for s in range(target, num - 1, -1):
            if dp[s - num]:
                dp[s] = True
        if dp[target]:
            return True
    return dp[target]


register(PAYLOAD, REFERENCE)
