"""Jump Game II — Medium. Greedy / BFS-like.

The 'BFS-by-layers without a queue' classic. Each index `i` holds the
maximum jump length from there; you want the minimum number of jumps
to reach the last index. The naive DP is O(n²); the greedy 'farthest
reach within current layer' trick collapses it to O(n) with two
pointers and a counter. Worth recognising the BFS framing — the layers
are exactly the jump count.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Jump Game II",
    "difficulty": "Medium",
    "description": (
        "You are given a 0-indexed array of non-negative integers `nums` of length `n`. You are initially "
        "positioned at `nums[0]`.\n\n"
        "Each element `nums[i]` represents the maximum length of a forward jump from index `i`. In other "
        "words, if you are at `nums[i]`, you can jump to any `nums[i + j]` where `0 <= j <= nums[i]` and "
        "`i + j < n`.\n\n"
        "Return the **minimum number of jumps** to reach `nums[n - 1]`. The test cases are generated such "
        "that you can always reach `nums[n - 1]`.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [2,3,1,1,4]`\n"
        "- Output: `2`\n"
        "- Explanation: Jump 1 step from index 0 to 1, then 3 steps to the last index.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [2,3,0,1,4]`\n"
        "- Output: `2`\n"
        "- Explanation: Jump 1 step from index 0 to 1, then 3 steps to the last index."
    ),
    "hints": [
        "Brute / DP: `dp[i] = min jumps to reach i`. For each `i`, try every reachable `j` from a previous index. O(n²) time, O(n) space — works but slow for n up to 10⁴.",
        "Reframe as BFS: index 0 is layer 0, everything reachable in one jump is layer 1, etc. The answer is the layer number containing `n - 1`. You don't need a queue — the layers are contiguous index ranges.",
        "Greedy (optimal): track three things — `jumps` (count so far), `currentEnd` (rightmost index of the current layer), `farthestReach` (farthest index reachable from anything in the current layer).",
        "Walk `i` from 0 to n - 2. Update `farthestReach = max(farthestReach, i + nums[i])`. When `i == currentEnd`, you've finished the current layer: increment `jumps` and set `currentEnd = farthestReach`.",
        "Loop bound is `n - 1`, not `n` — you don't need to 'jump from' the last index; arriving counts as done. Off-by-one here is the most common bug.",
    ],
    "constraints": [
        "1 <= nums.length <= 10⁴",
        "0 <= nums[i] <= 1000",
        "It's guaranteed you can reach `nums[n - 1]`.",
    ],
    "starter_code": {
        "python": "def jump(nums):\n    # Your code here\n    pass",
        "javascript": "function jump(nums) {\n    // Your code here\n}",
        "java": "public int jump(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[2,3,1,1,4], [2,3,0,1,4], [1,1,1,1], [5,1,1,1,1]]\n"
            "    for nums in cases:\n"
            "        print(f\"jump({nums}) = {jump(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[2,3,1,1,4], [2,3,0,1,4], [1,1,1,1]].forEach(nums =>\n"
            "    console.log(`jump =`, jump(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.jump(new int[]{2,3,1,1,4}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [2, 3, 1, 1, 4]}, "expected": 2,
         "description": "Classic — 0 → 1 → 4", "tags": ["basic"]},
        {"input": {"nums": [2, 3, 0, 1, 4]}, "expected": 2,
         "description": "Zero in the middle but layer 1 already reaches the end", "tags": ["basic"]},
        {"input": {"nums": [0]}, "expected": 0,
         "description": "Single element — already at the end, no jumps needed", "tags": ["edge"]},
        {"input": {"nums": [1, 2]}, "expected": 1,
         "description": "Two elements — one jump suffices", "tags": ["edge"]},
        {"input": {"nums": [2, 1]}, "expected": 1,
         "description": "Two elements, oversized first jump — still one jump", "tags": ["edge"]},
        {"input": {"nums": [10, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]}, "expected": 1,
         "description": "Huge jump at start covers everything — one jump", "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 1, 1, 1]}, "expected": 3,
         "description": "Greedy takes 0 → 1 → 3 → 4", "tags": ["tricky"]},
        {"input": {"nums": [2, 1, 1, 1, 4]}, "expected": 3,
         "description": "Alternating small jumps — 0 → 1 → 2 → 4 (or 0 → 2 → 3 → 4)", "tags": ["tricky"]},
        {"input": {"nums": [1] * 100}, "expected": 99,
         "description": "All ones — must jump n - 1 times", "tags": ["large"]},
        {"input": {"nums": [1] * 1000}, "expected": 999,
         "description": "All ones, longer — n - 1 jumps", "tags": ["large"]},
        {"input": {"nums": [5, 9, 3, 2, 1, 0, 2, 3, 3, 1, 0, 0]}, "expected": 3,
         "description": "Long array with zeros mid-way — greedy still optimal", "tags": ["large"]},
        {"input": {"nums": [1000] + [1] * 999}, "expected": 1,
         "description": "Massive first jump covers all 1000 indices in one hop", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "BFS-style Greedy (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Treat the array as a BFS: layer k = the set of indices reachable in exactly k jumps. "
                "Track `currentEnd` (rightmost index in the current layer) and `farthestReach` (rightmost "
                "index reachable from anything in the current layer). Walk `i` from 0 to n - 2. Whenever "
                "`i` hits `currentEnd`, the current layer is exhausted: bump `jumps`, advance "
                "`currentEnd = farthestReach`. Loop bound is `n - 1` because arriving at the last index "
                "is the goal — you don't jump *from* it."
            ),
            "code": {
                "python": (
                    "def jump(nums):\n"
                    "    jumps = 0\n"
                    "    current_end = 0\n"
                    "    farthest = 0\n"
                    "    for i in range(len(nums) - 1):\n"
                    "        if i + nums[i] > farthest:\n"
                    "            farthest = i + nums[i]\n"
                    "        if i == current_end:\n"
                    "            jumps += 1\n"
                    "            current_end = farthest\n"
                    "    return jumps"
                ),
                "javascript": (
                    "function jump(nums) {\n"
                    "    let jumps = 0, currentEnd = 0, farthest = 0;\n"
                    "    for (let i = 0; i < nums.length - 1; i++) {\n"
                    "        if (i + nums[i] > farthest) farthest = i + nums[i];\n"
                    "        if (i === currentEnd) {\n"
                    "            jumps++;\n"
                    "            currentEnd = farthest;\n"
                    "        }\n"
                    "    }\n"
                    "    return jumps;\n"
                    "}"
                ),
                "java": (
                    "public int jump(int[] nums) {\n"
                    "    int jumps = 0, currentEnd = 0, farthest = 0;\n"
                    "    for (int i = 0; i < nums.length - 1; i++) {\n"
                    "        if (i + nums[i] > farthest) farthest = i + nums[i];\n"
                    "        if (i == currentEnd) {\n"
                    "            jumps++;\n"
                    "            currentEnd = farthest;\n"
                    "        }\n"
                    "    }\n"
                    "    return jumps;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Bottom-Up DP (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(n)",
            "description": (
                "Define `dp[i]` = minimum jumps to reach index `i`. Initialise `dp[0] = 0`, the rest to "
                "infinity. For each `i`, scan `j` from `i + 1` to `min(i + nums[i], n - 1)` and relax "
                "`dp[j] = min(dp[j], dp[i] + 1)`. Return `dp[n - 1]`. Correct but quadratic — for n up to "
                "10⁴ it borders on TLE; mention as the natural baseline before showing the greedy."
            ),
            "code": {
                "python": (
                    "def jump(nums):\n"
                    "    n = len(nums)\n"
                    "    dp = [float('inf')] * n\n"
                    "    dp[0] = 0\n"
                    "    for i in range(n):\n"
                    "        for j in range(i + 1, min(i + nums[i] + 1, n)):\n"
                    "            if dp[i] + 1 < dp[j]:\n"
                    "                dp[j] = dp[i] + 1\n"
                    "    return dp[n - 1]"
                ),
                "javascript": (
                    "function jump(nums) {\n"
                    "    const n = nums.length;\n"
                    "    const dp = new Array(n).fill(Infinity);\n"
                    "    dp[0] = 0;\n"
                    "    for (let i = 0; i < n; i++) {\n"
                    "        for (let j = i + 1; j < Math.min(i + nums[i] + 1, n); j++) {\n"
                    "            if (dp[i] + 1 < dp[j]) dp[j] = dp[i] + 1;\n"
                    "        }\n"
                    "    }\n"
                    "    return dp[n - 1];\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: we want the *minimum* number of jumps to reach the last index. Reachability is guaranteed.",
        "2. Brute DP: `dp[i] = min(dp[j] + 1)` over all `j` that can reach `i`. O(n²). State it as the baseline.",
        "3. Reframe as BFS: jumps = layer index. Layer 0 = {0}; layer 1 = everything index 0 can reach; layer 2 = everything any layer-1 index can reach; etc.",
        "4. Crucial observation: each layer is a *contiguous range* of indices `[currentEnd_prev + 1, currentEnd_new]`. So a queue is overkill — two pointers suffice.",
        "5. Maintain `farthestReach = max(farthestReach, i + nums[i])` while walking through the current layer. When `i` hits `currentEnd`, the layer is exhausted: bump `jumps` and set `currentEnd = farthestReach`.",
        "6. Stop the loop at `n - 2`. Arriving at the last index counts; you never jump *from* it. Looping to `n - 1` would over-count by 1.",
        "7. Edge case: `n == 1` → answer is 0 (loop never runs). The code handles it naturally.",
    ],
    "tips": [
        "Loop to `n - 1` exclusive (i.e., last `i` is `n - 2`). Looping to `n` inclusive over-counts by one jump every time.",
        "The greedy isn't 'always jump as far as possible from index 0' — that's wrong. It's 'within the current layer, find the farthest reach, *then* take one jump to that boundary.'",
        "BFS framing makes it click: every time you finish a layer, you've used one jump. The number of layers crossed before reaching `n - 1` is the answer.",
        "Don't track the actual path. The problem only asks for the count, and tracking paths balloons memory without changing the answer.",
        "Common follow-up — Jump Game I: 'can you reach the end at all?' Same scan, but track only `farthestReach` and bail if `i > farthestReach`.",
        "Common follow-up — Jump Game III/IV/V/VI: each adds a twist (allowed-direction set, equal-value teleports, sliding window of jumps). The BFS framing here is the foundation for all of them.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Meta", "Bloomberg"],
    "topics": ["Array", "Greedy", "Dynamic Programming"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    jumps = 0
    current_end = 0
    farthest = 0
    for i in range(len(nums) - 1):
        if i + nums[i] > farthest:
            farthest = i + nums[i]
        if i == current_end:
            jumps += 1
            current_end = farthest
    return jumps


register(PAYLOAD, REFERENCE)
