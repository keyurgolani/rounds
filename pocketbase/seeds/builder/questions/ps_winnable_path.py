"""Winnable Path — Easy. Greedy / Reachability.

Given a board with jump distances per cell, determine whether you can
reach the end starting from index 0. Same shape as Jump Game (LeetCode
55) — greedy reach tracking is O(n) / O(1)."""
from builder.registry import register


PAYLOAD = {
    "title": "Winnable Path",
    "difficulty": "Easy",
    "description": (
        "Given an array `nums` where each entry represents the **maximum jump distance** from that "
        "position, return `True` if you can reach the LAST index starting from index 0.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [2, 3, 1, 1, 4]`\n"
        "- Output: `True` (one path: index 0 → 1 → 4)\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [3, 2, 1, 0, 4]`\n"
        "- Output: `False` (every path stalls at index 3)"
    ),
    "hints": [
        "Greedy: track `furthest` reachable index. For each position i ≤ furthest, update `furthest = max(furthest, i + nums[i])`. Return `furthest >= len(nums) - 1`.",
        "If at any i, `i > furthest`, you can't even reach i — early exit with False.",
        "DP / BFS works too but is overkill — greedy is O(n) / O(1).",
        "Edge cases: single-element array (already at end, True), zero at index 0 with len > 1 (False), all zeros (only the first index is reachable), strictly decreasing.",
    ],
    "constraints": [
        "1 <= |nums| <= 10⁴",
        "0 <= nums[i] <= 10⁵",
    ],
    "starter_code": {
        "python": "def can_reach_end(nums):\n    # Your code here\n    pass",
        "javascript": "function canReachEnd(nums) {\n    // Your code here\n}",
        "java": "public boolean canReachEnd(int[] nums) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(can_reach_end([2, 3, 1, 1, 4]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"nums": [2, 3, 1, 1, 4]}, "expected": True,
         "description": "Multi-path winnable", "tags": ["basic"]},
        {"input": {"nums": [3, 2, 1, 0, 4]}, "expected": False,
         "description": "Stalls at index 3 with 0 jump", "tags": ["basic"]},
        {"input": {"nums": [0]}, "expected": True,
         "description": "Single element — already at end", "tags": ["edge"]},
        {"input": {"nums": [0, 1]}, "expected": False,
         "description": "Stuck at index 0 with len 2", "tags": ["edge"]},
        {"input": {"nums": [1, 0, 0]}, "expected": False,
         "description": "Reaches index 1 but can't proceed", "tags": ["edge"]},
        {"input": {"nums": [10, 0, 0, 0, 0]}, "expected": True,
         "description": "First jump covers everything", "tags": ["basic"]},
        {"input": {"nums": [2, 0, 2, 0, 1]}, "expected": True,
         "description": "Skip the zeros", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Greedy Reach Tracking (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Track `furthest` = farthest index reachable so far. Walk i; if `i > furthest` you can't "
                "even arrive at i — bail with False. Otherwise update `furthest = max(furthest, i + "
                "nums[i])`. After the walk, return whether furthest reached the last index."
            ),
            "code": {
                "python": (
                    "def can_reach_end(nums):\n"
                    "    furthest = 0\n"
                    "    n = len(nums)\n"
                    "    for i in range(n):\n"
                    "        if i > furthest:\n"
                    "            return False\n"
                    "        furthest = max(furthest, i + nums[i])\n"
                    "        if furthest >= n - 1:\n"
                    "            return True\n"
                    "    return True"
                ),
                "javascript": (
                    "function canReachEnd(nums) {\n"
                    "    let furthest = 0;\n"
                    "    for (let i = 0; i < nums.length; i++) {\n"
                    "        if (i > furthest) return false;\n"
                    "        furthest = Math.max(furthest, i + nums[i]);\n"
                    "        if (furthest >= nums.length - 1) return true;\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
                "java": (
                    "public boolean canReachEnd(int[] nums) {\n"
                    "    int furthest = 0;\n"
                    "    for (int i = 0; i < nums.length; i++) {\n"
                    "        if (i > furthest) return false;\n"
                    "        furthest = Math.max(furthest, i + nums[i]);\n"
                    "        if (furthest >= nums.length - 1) return true;\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
        {
            "title": "DP from the End",
            "time_complexity": "O(n²) worst case",
            "space_complexity": "O(n)",
            "description": (
                "`dp[i] = True` iff position i can reach the end. Walk right to left; for each i with "
                "nums[i] >= 1, check if any reachable j ∈ [i+1, i+nums[i]] has dp[j]=True. Less efficient "
                "than greedy."
            ),
            "code": {
                "python": (
                    "def can_reach_end(nums):\n"
                    "    n = len(nums)\n"
                    "    dp = [False] * n\n"
                    "    dp[-1] = True\n"
                    "    for i in range(n - 2, -1, -1):\n"
                    "        max_reach = min(n - 1, i + nums[i])\n"
                    "        for j in range(i + 1, max_reach + 1):\n"
                    "            if dp[j]:\n"
                    "                dp[i] = True\n"
                    "                break\n"
                    "    return dp[0]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Reframe: 'reach last index' = furthest reachable >= last index after the walk.",
        "2. Greedy: at each i ≤ furthest, update furthest with i + nums[i].",
        "3. If you reach an i > furthest, you've stalled — can't reach further.",
        "4. Early exit on furthest >= n-1.",
        "5. Edge cases: single element (true), zero at start with len > 1 (false), zeros after a high jump.",
    ],
    "tips": [
        "Don't reach for DP first; the greedy approach is strictly faster and easier to write.",
        "The `i > furthest` check is the bail condition — without it the loop would continue past unreachable indices.",
        "Common follow-up: 'minimum number of jumps' (Jump Game II). BFS-flavoured greedy: track current reach + next reach, count jumps when reach exhausts.",
        "Common follow-up: 'find one valid path.' Track parents during the greedy walk and reconstruct.",
        "Common follow-up: 'cyclic / 2D grid version.' BFS with visited set.",
    ],
    "companies": ["Amazon", "Google", "Microsoft"],
    "topics": ["Greedy", "Array"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    furthest = 0
    n = len(nums)
    for i in range(n):
        if i > furthest:
            return False
        furthest = max(furthest, i + nums[i])
        if furthest >= n - 1:
            return True
    return True


register(PAYLOAD, REFERENCE)
