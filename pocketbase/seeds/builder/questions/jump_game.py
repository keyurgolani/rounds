"""Jump Game (LeetCode 55) — Medium. Greedy / DP.

Canonical LC framing. Greedy reach-tracking is O(n) / O(1); top-down
memoised DP is O(n²) / O(n) but worth presenting as the natural first
recursive instinct before collapsing it to the greedy invariant.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Jump Game",
    "difficulty": "Medium",
    "description": (
        "You are given an integer array `nums`. You are initially positioned at the array's **first index**, "
        "and each element in the array represents your **maximum jump length** at that position.\n\n"
        "Return `True` if you can reach the last index, or `False` otherwise.\n\n"
        "Implement the function `can_jump(nums)`.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [2, 3, 1, 1, 4]`\n"
        "- Output: `True`\n"
        "- Explanation: Jump 1 step from index 0 to 1, then 3 steps to the last index.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [3, 2, 1, 0, 4]`\n"
        "- Output: `False`\n"
        "- Explanation: You will always arrive at index 3 with a max jump length of 0, which makes it "
        "impossible to reach the last index."
    ),
    "hints": [
        "Think backwards: from each index, what's the *farthest* index you can possibly reach? Maintain that as a running maximum.",
        "Greedy invariant: walk i = 0 .. n-1. If `i > max_reach`, you've stalled — bail with False. Otherwise update `max_reach = max(max_reach, i + nums[i])`.",
        "Early-exit when `max_reach >= n - 1` — no need to scan the rest.",
        "Top-down DP / memoisation works (O(n²) / O(n)) but is strictly dominated by the greedy. Mention it to show you saw the recursion before collapsing it.",
        "Edge cases worth verbalising: single-element array (already at end → True), `nums[0] = 0` with len > 1 (False), all zeros after a sufficiently large first element (True).",
    ],
    "constraints": [
        "1 <= nums.length <= 10⁴",
        "0 <= nums[i] <= 10⁵",
    ],
    "starter_code": {
        "python": "def can_jump(nums):\n    # Your code here\n    pass",
        "javascript": "function can_jump(nums) {\n    // Your code here\n}",
        "java": "public boolean can_jump(int[] nums) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[2, 3, 1, 1, 4], [3, 2, 1, 0, 4], [0]]\n"
            "    for nums in cases:\n"
            "        print(f\"can_jump({nums}) = {can_jump(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[2, 3, 1, 1, 4], [3, 2, 1, 0, 4]].forEach(nums =>\n"
            "    console.log(`can_jump =`, can_jump(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.can_jump(new int[]{2, 3, 1, 1, 4}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [2, 3, 1, 1, 4]}, "expected": True,
         "description": "LC example 1 — winnable", "tags": ["basic"]},
        {"input": {"nums": [3, 2, 1, 0, 4]}, "expected": False,
         "description": "LC example 2 — stalls on the zero", "tags": ["basic"]},
        {"input": {"nums": [1]}, "expected": True,
         "description": "Single element with non-zero — already at end", "tags": ["edge"]},
        {"input": {"nums": [2, 0, 0]}, "expected": True,
         "description": "First jump exactly reaches end across two zeros", "tags": ["edge"]},
        {"input": {"nums": [1, 1, 1, 1, 1]}, "expected": True,
         "description": "All ones — exactly enough to walk to the end", "tags": ["tricky"]},
        {"input": {"nums": [4, 0, 0, 0, 1, 0]}, "expected": True,
         "description": "First jump lands on index 4; nums[4]=1 reaches the last index", "tags": ["tricky"]},
        {"input": {"nums": [5, 9, 3, 2, 1, 0, 2, 3, 3, 1, 0, 0]}, "expected": True,
         "description": "Length 12 — index 1's jump of 9 covers everything past the 0-zone", "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 0, 1, 0, 1, 0]}, "expected": False,
         "description": "Length 7 — stalls at index 4 (max_reach = 4, but nums[4]=0)", "tags": ["tricky"]},
        {"input": {"nums": [2, 5, 0, 0, 0, 0, 0, 0, 0, 1]}, "expected": False,
         "description": "Length 10 — best reach is idx 6, can't bridge the zero plateau to idx 9", "tags": ["tricky"]},
        {"input": {"nums": [1] * 5000 + [0]}, "expected": True,
         "description": "5001-length array of all 1s ending in 0 — last index reached exactly", "tags": ["large"]},
        {"input": {"nums": [10000] + [0] * 9999}, "expected": True,
         "description": "10K-length — first jump covers entire array", "tags": ["large"]},
        {"input": {"nums": [1, 0] + [1] * 9998}, "expected": False,
         "description": "10K-length — stalls at index 1 immediately", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Greedy Reach Tracking (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk left-to-right. Track `max_reach` = farthest index reachable so far. At each i, if "
                "`i > max_reach` you've stalled — return False. Otherwise update `max_reach = max(max_reach, "
                "i + nums[i])`. Early-exit when `max_reach >= n - 1`. After the walk, return True."
            ),
            "code": {
                "python": (
                    "def can_jump(nums):\n"
                    "    max_reach = 0\n"
                    "    n = len(nums)\n"
                    "    for i in range(n):\n"
                    "        if i > max_reach:\n"
                    "            return False\n"
                    "        if i + nums[i] > max_reach:\n"
                    "            max_reach = i + nums[i]\n"
                    "        if max_reach >= n - 1:\n"
                    "            return True\n"
                    "    return True"
                ),
                "javascript": (
                    "function can_jump(nums) {\n"
                    "    let maxReach = 0;\n"
                    "    const n = nums.length;\n"
                    "    for (let i = 0; i < n; i++) {\n"
                    "        if (i > maxReach) return false;\n"
                    "        if (i + nums[i] > maxReach) maxReach = i + nums[i];\n"
                    "        if (maxReach >= n - 1) return true;\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
                "java": (
                    "public boolean can_jump(int[] nums) {\n"
                    "    int maxReach = 0;\n"
                    "    int n = nums.length;\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        if (i > maxReach) return false;\n"
                    "        if (i + nums[i] > maxReach) maxReach = i + nums[i];\n"
                    "        if (maxReach >= n - 1) return true;\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Top-Down DP with Memoisation",
            "time_complexity": "O(n²)",
            "space_complexity": "O(n)",
            "description": (
                "`solve(i)` = True iff index i can reach the last index. Recurse over every reachable "
                "j ∈ [i+1, i + nums[i]] and return True if any does. Memoise by index. Strictly dominated "
                "by greedy but it's the natural first recursive instinct — present it to show the "
                "subproblem structure before collapsing to the O(n) greedy invariant."
            ),
            "code": {
                "python": (
                    "def can_jump(nums):\n"
                    "    n = len(nums)\n"
                    "    memo = {}\n"
                    "\n"
                    "    def solve(i):\n"
                    "        if i >= n - 1:\n"
                    "            return True\n"
                    "        if i in memo:\n"
                    "            return memo[i]\n"
                    "        furthest = min(i + nums[i], n - 1)\n"
                    "        for j in range(i + 1, furthest + 1):\n"
                    "            if solve(j):\n"
                    "                memo[i] = True\n"
                    "                return True\n"
                    "        memo[i] = False\n"
                    "        return False\n"
                    "\n"
                    "    return solve(0)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force / pure recursion: from each index, try every jump length up to nums[i]. Exponential without memoisation.",
        "2. Memoise by index — `solve(i)` only depends on i. That's O(n²) time, O(n) space.",
        "3. Reframe greedily: I never need to know *which* path; I only need to know the *furthest index reachable so far*.",
        "4. Walk i = 0 .. n-1. If `i > max_reach`, the prefix can't even arrive at i — bail with False.",
        "5. Otherwise update `max_reach = max(max_reach, i + nums[i])`. Early-exit when `max_reach >= n - 1`.",
        "6. Edge cases: single element (True), `nums[0] = 0` with len > 1 (False), large first element trivially covers everything.",
    ],
    "tips": [
        "Don't write the DP first — interviewers usually want the greedy. Mention DP as the recursive baseline you saw and dismissed.",
        "The bail condition `i > max_reach` is the part candidates forget. Without it, the loop happily marches past unreachable indices and produces wrong answers.",
        "Don't confuse Jump Game (LC 55) with Jump Game II (LC 45). II asks for the *minimum number of jumps* — same greedy shape but with two pointers (current_end, next_reach).",
        "Common follow-up — Jump Game III (LC 1306): jumps are `i ± nums[i]` and you must reach an index whose value is 0. BFS/DFS, not greedy.",
        "Common follow-up — Jump Game IV / V / VI: each adds a twist (same-value teleport, max-jump-K, sliding window max). Different algorithms; don't pattern-match blindly.",
        "Initialising `max_reach = 0` is correct because index 0 is trivially reachable. Don't initialise to `nums[0]`; that double-counts.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Apple", "Bloomberg"],
    "topics": ["Array", "Greedy", "Dynamic Programming"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    max_reach = 0
    n = len(nums)
    for i in range(n):
        if i > max_reach:
            return False
        if i + nums[i] > max_reach:
            max_reach = i + nums[i]
        if max_reach >= n - 1:
            return True
    return True


register(PAYLOAD, REFERENCE)
