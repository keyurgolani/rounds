"""Burst Balloons — Hard. Interval DP.

The canonical 'think backwards' interval DP. The natural framing —
'which balloon do I burst FIRST?' — is wrong, because the first burst's
neighbours depend on later bursts. Flip it: in any subrange (i, j),
pick the LAST balloon to burst. That balloon's neighbours are exactly
nums[i] and nums[j] (the padded boundary), so the subproblems on
either side become independent. O(n^3) time, O(n^2) space.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Burst Balloons",
    "difficulty": "Hard",
    "description": (
        "You are given `n` balloons, indexed from `0` to `n - 1`. Each balloon is painted with a number on it "
        "represented by an array `nums`. You are asked to burst all the balloons.\n\n"
        "If you burst the i-th balloon, you will get `nums[left] * nums[i] * nums[right]` coins. After the "
        "burst, balloons `left` and `right` become adjacent.\n\n"
        "If `left` or `right` goes out of bounds of the array, treat it as if there is a balloon with a `1` "
        "painted on it.\n\n"
        "Return the **maximum coins** you can collect by bursting the balloons wisely.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [3,1,5,8]`\n"
        "- Output: `167`\n"
        "- Explanation: Optimal order is `[3,1,5,8] -> [3,5,8] -> [3,8] -> [8] -> []`.\n"
        "  Coins = `3*1*5 + 3*5*8 + 1*3*8 + 1*8*1 = 15 + 120 + 24 + 8 = 167`.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [1,5]`\n"
        "- Output: `10`\n"
        "- Explanation: Burst the `1` first: `1*1*5 = 5`. Then burst the `5`: `1*5*1 = 5`. Total = `10`."
    ),
    "hints": [
        "Brute force tries every burst order: n! permutations. State the cost; never submit.",
        "The greedy 'burst the smallest first' fails. Counter-example: `[3,1,5,8]` — the smallest is 1, but "
        "bursting it first locks in the wrong neighbours for everything that follows.",
        "Key insight — flip the question. Don't ask 'which balloon do I burst FIRST in this subrange?' Ask "
        "'which balloon do I burst LAST?' If `k` is last in subrange `(i, j)`, its neighbours at the moment "
        "of bursting are exactly `nums[i]` and `nums[j]` — the boundary balloons that haven't been touched.",
        "Pad `nums` with `1` on both ends: `arr = [1] + nums + [1]`. Then `dp[i][j]` = max coins from "
        "bursting all balloons strictly between indices `i` and `j` in `arr`. Final answer is `dp[0][n+1]`.",
        "Recurrence: `dp[i][j] = max over k in (i, j) of dp[i][k] + dp[k][j] + arr[i]*arr[k]*arr[j]`. "
        "Iterate by interval length so subproblems are solved before the intervals that need them.",
    ],
    "constraints": [
        "n == nums.length",
        "1 <= n <= 300",
        "0 <= nums[i] <= 100",
    ],
    "starter_code": {
        "python": "def max_coins(nums):\n    # Your code here\n    pass",
        "javascript": "function maxCoins(nums) {\n    // Your code here\n}",
        "java": "public int maxCoins(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[3,1,5,8], [1,5], [5], [3,4]]\n"
            "    for nums in cases:\n"
            "        print(f\"max_coins({nums}) = {max_coins(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[3,1,5,8], [1,5], [5], [3,4]].forEach(nums =>\n"
            "    console.log(`maxCoins =`, maxCoins(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.maxCoins(new int[]{3,1,5,8}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [3, 1, 5, 8]}, "expected": 167,
         "description": "Classic LeetCode example — optimal order yields 167", "tags": ["basic"]},
        {"input": {"nums": [1, 5]}, "expected": 10,
         "description": "LeetCode second example — order doesn't matter, total 10", "tags": ["basic"]},
        {"input": {"nums": [5]}, "expected": 5,
         "description": "Single balloon — coins = 1*5*1", "tags": ["edge"]},
        {"input": {"nums": [3, 4]}, "expected": 16,
         "description": "Two balloons — best order is burst 3 first (1*3*4=12) then burst 4 (1*4*1=4), total 16",
         "tags": ["edge"]},
        {"input": {"nums": [1, 2, 3, 4, 5]}, "expected": 110,
         "description": "Ascending — interval DP finds the optimum", "tags": ["tricky"]},
        {"input": {"nums": [5, 4, 3, 2, 1]}, "expected": 110,
         "description": "Descending — symmetric to ascending under interval DP", "tags": ["tricky"]},
        {"input": {"nums": [7, 9, 8, 0, 7, 1, 3, 5, 5, 2]}, "expected": 1582,
         "description": "Mixed values including a zero — zeros still appear in the recurrence as factors",
         "tags": ["tricky"]},
        {"input": {"nums": [9, 76, 64, 21, 97, 60]}, "expected": 1086136,
         "description": "Six-balloon stress — exercises full O(n^3) recurrence", "tags": ["large"]},
        {"input": {"nums": [8, 3, 4, 3, 5, 0, 5, 6, 6, 2, 8, 5, 6, 2, 3, 8, 3, 5, 1, 0, 2]}, "expected": 3394,
         "description": "Twenty-one balloons — large enough to expose any O(n!) attempts", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Interval DP (Bottom-Up, Optimal)",
            "time_complexity": "O(n^3)",
            "space_complexity": "O(n^2)",
            "description": (
                "Pad with 1s on both ends. `dp[i][j]` = max coins from bursting all balloons strictly between "
                "indices `i` and `j` in the padded array. For each interval `(i, j)` and each candidate "
                "last-burst `k` in `(i, j)`, `dp[i][j] = max(dp[i][j], dp[i][k] + dp[k][j] + arr[i]*arr[k]*arr[j])`. "
                "Because `k` is bursted *last* in the interval, its neighbours at burst time are exactly `arr[i]` "
                "and `arr[j]` — the untouched boundary balloons. Iterate by increasing interval length so "
                "subproblems are ready when needed."
            ),
            "code": {
                "python": (
                    "def max_coins(nums):\n"
                    "    arr = [1] + nums + [1]\n"
                    "    n = len(arr)\n"
                    "    dp = [[0] * n for _ in range(n)]\n"
                    "    for length in range(2, n):\n"
                    "        for i in range(n - length):\n"
                    "            j = i + length\n"
                    "            best = 0\n"
                    "            for k in range(i + 1, j):\n"
                    "                gain = arr[i] * arr[k] * arr[j] + dp[i][k] + dp[k][j]\n"
                    "                if gain > best:\n"
                    "                    best = gain\n"
                    "            dp[i][j] = best\n"
                    "    return dp[0][n - 1]"
                ),
                "javascript": (
                    "function maxCoins(nums) {\n"
                    "    const arr = [1, ...nums, 1];\n"
                    "    const n = arr.length;\n"
                    "    const dp = Array.from({length: n}, () => new Array(n).fill(0));\n"
                    "    for (let length = 2; length < n; length++) {\n"
                    "        for (let i = 0; i + length < n; i++) {\n"
                    "            const j = i + length;\n"
                    "            let best = 0;\n"
                    "            for (let k = i + 1; k < j; k++) {\n"
                    "                const gain = arr[i] * arr[k] * arr[j] + dp[i][k] + dp[k][j];\n"
                    "                if (gain > best) best = gain;\n"
                    "            }\n"
                    "            dp[i][j] = best;\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[0][n - 1];\n"
                    "}"
                ),
                "java": (
                    "public int maxCoins(int[] nums) {\n"
                    "    int n = nums.length + 2;\n"
                    "    int[] arr = new int[n];\n"
                    "    arr[0] = arr[n - 1] = 1;\n"
                    "    for (int i = 0; i < nums.length; i++) arr[i + 1] = nums[i];\n"
                    "    int[][] dp = new int[n][n];\n"
                    "    for (int length = 2; length < n; length++) {\n"
                    "        for (int i = 0; i + length < n; i++) {\n"
                    "            int j = i + length;\n"
                    "            int best = 0;\n"
                    "            for (int k = i + 1; k < j; k++) {\n"
                    "                int gain = arr[i] * arr[k] * arr[j] + dp[i][k] + dp[k][j];\n"
                    "                if (gain > best) best = gain;\n"
                    "            }\n"
                    "            dp[i][j] = best;\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[0][n - 1];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Memoized Recursion (Top-Down)",
            "time_complexity": "O(n^3)",
            "space_complexity": "O(n^2)",
            "description": (
                "Same recurrence written recursively. `solve(i, j)` returns the max coins from bursting "
                "balloons strictly between `i` and `j` in the padded array, memoizing on `(i, j)`. Same "
                "asymptotics as the bottom-up version, often easier to write under time pressure but with "
                "Python's recursion overhead."
            ),
            "code": {
                "python": (
                    "from functools import lru_cache\n\n"
                    "def max_coins(nums):\n"
                    "    arr = [1] + nums + [1]\n"
                    "    @lru_cache(maxsize=None)\n"
                    "    def solve(i, j):\n"
                    "        if j - i < 2:\n"
                    "            return 0\n"
                    "        best = 0\n"
                    "        for k in range(i + 1, j):\n"
                    "            gain = arr[i] * arr[k] * arr[j] + solve(i, k) + solve(k, j)\n"
                    "            if gain > best:\n"
                    "                best = gain\n"
                    "        return best\n"
                    "    return solve(0, len(arr) - 1)"
                ),
                "javascript": (
                    "function maxCoins(nums) {\n"
                    "    const arr = [1, ...nums, 1];\n"
                    "    const n = arr.length;\n"
                    "    const memo = Array.from({length: n}, () => new Array(n).fill(-1));\n"
                    "    function solve(i, j) {\n"
                    "        if (j - i < 2) return 0;\n"
                    "        if (memo[i][j] !== -1) return memo[i][j];\n"
                    "        let best = 0;\n"
                    "        for (let k = i + 1; k < j; k++) {\n"
                    "            const gain = arr[i] * arr[k] * arr[j] + solve(i, k) + solve(k, j);\n"
                    "            if (gain > best) best = gain;\n"
                    "        }\n"
                    "        memo[i][j] = best;\n"
                    "        return best;\n"
                    "    }\n"
                    "    return solve(0, n - 1);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force every burst order: n! permutations. State it as the baseline; for n up to 300 it's wildly impossible.",
        "2. The greedy 'burst smallest first' / 'burst largest first' both fail on `[3,1,5,8]`. Burst order is genuinely combinatorial.",
        "3. Try DP on subranges. Standard interval-DP attempt: 'pick the FIRST balloon to burst in (i, j)'. This fails because once you burst k first, the neighbours of every later burst depend on k, and the subproblems on left and right are no longer independent.",
        "4. Flip the question: 'pick the LAST balloon to burst in (i, j)'. If k bursts last, then by the time k bursts every other balloon in (i, j) is gone, so k's neighbours at burst time are the original boundary balloons at indices i and j. The subproblems on (i, k) and (k, j) are now genuinely independent.",
        "5. Pad with 1s on both ends so the boundary 'imaginary balloon = 1' is encoded uniformly. dp[i][j] = best coins from bursting the OPEN interval (i, j) in the padded array.",
        "6. Recurrence: dp[i][j] = max over k in (i, j) of dp[i][k] + dp[k][j] + arr[i]*arr[k]*arr[j]. Iterate by increasing interval length. Final answer dp[0][n+1].",
        "7. Complexity: O(n^3) time, O(n^2) space — tight for n up to 300 (~27M ops, fine in Python).",
    ],
    "tips": [
        "If you find yourself writing 'pick the first balloon to burst', stop. The first-burst framing has dependent subproblems and the DP doesn't close. Switch to last-burst.",
        "Always pad with 1s. Without padding you write a half-dozen edge cases for the boundary; with padding the recurrence is uniform.",
        "Indexing trap: dp[i][j] is the OPEN interval (i, j) — i and j themselves are not burst inside this subproblem. Be consistent or you'll off-by-one yourself into nonsense.",
        "Iteration order: by interval length, not by i or j alone. dp[i][j] depends on shorter intervals dp[i][k] and dp[k][j], so length must grow monotonically.",
        "Top-down memoization is faster to write under time pressure; bottom-up is slightly faster at runtime and avoids Python recursion limits. Pick based on language.",
        "Common follow-up — print the optimal burst order. Track the argmax k for each (i, j) and reconstruct recursively (in-order: left subrange, then k, then right subrange).",
    ],
    "companies": ["Google", "Amazon", "Microsoft", "Snapchat", "Bloomberg"],
    "topics": ["Array", "Dynamic Programming", "Interval DP"],
    "time_complexity": "O(n^3)",
    "space_complexity": "O(n^2)",
}


def REFERENCE(nums):
    arr = [1] + list(nums) + [1]
    n = len(arr)
    dp = [[0] * n for _ in range(n)]
    for length in range(2, n):
        for i in range(n - length):
            j = i + length
            best = 0
            for k in range(i + 1, j):
                gain = arr[i] * arr[k] * arr[j] + dp[i][k] + dp[k][j]
                if gain > best:
                    best = gain
            dp[i][j] = best
    return int(dp[0][n - 1])


register(PAYLOAD, REFERENCE)
