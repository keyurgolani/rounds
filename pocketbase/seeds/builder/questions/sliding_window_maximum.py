"""Sliding Window Maximum — Hard. Monotonic Deque.

The canonical monotonic-deque problem. Brute force is O(n·k); a heap with
lazy deletion gets you O(n log n); the deque trick gets you the optimal
O(n) by maintaining indices of a decreasing sequence and evicting from the
front when they slide out of the window. Worth knowing cold — the deque
pattern recurs in 'Shortest Subarray with Sum at Least K', 'Constrained
Subsequence Sum', and many DP-on-window optimisations.
"""
from collections import deque

from builder.registry import register


PAYLOAD = {
    "title": "Sliding Window Maximum",
    "difficulty": "Hard",
    "description": (
        "You are given an array of integers `nums` and an integer `k`. There is a sliding window of size `k` "
        "that moves from the very left of the array to the very right. You can only see the `k` numbers in "
        "the window. Each time the sliding window moves right by one position.\n\n"
        "Return *the max sliding window* — an array containing the maximum value in each window, in window "
        "order (left to right).\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,3,-1,-3,5,3,6,7]`, `k = 3`\n"
        "- Output: `[3,3,5,5,6,7]`\n"
        "- Explanation: Windows are `[1,3,-1]`, `[3,-1,-3]`, `[-1,-3,5]`, `[-3,5,3]`, `[5,3,6]`, `[3,6,7]` "
        "with maxes `3, 3, 5, 5, 6, 7`.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [1]`, `k = 1`\n"
        "- Output: `[1]`\n"
        "- Explanation: Single element, single window."
    ),
    "hints": [
        "Brute force: scan each of the n−k+1 windows in O(k) → O(n·k). Fine to state, will TLE for n up to 10⁵.",
        "Key insight: maintain a **monotonic deque of indices** whose corresponding values are strictly (or non-strictly) decreasing front-to-back. The front index always holds the current window's maximum.",
        "When a new index `i` arrives, **pop from the back** while `nums[back] <= nums[i]` — those values can never again be the max while `nums[i]` is in the window, so they're dead weight.",
        "**Pop from the front** when `front <= i - k`, i.e. the front index has slid out of the window. Use indices, not values, so this check is trivial.",
        "Once `i >= k - 1`, you've formed a full window; append `nums[deque[0]]` to the answer. Each index is pushed and popped at most once, so the total work is O(n).",
        "Alternative: a max-heap of `(-value, index)` with **lazy deletion** — pop the top while its index is out of window. O(n log n), simpler to code under pressure if the deque pattern slips.",
    ],
    "constraints": [
        "1 <= nums.length <= 10⁵",
        "-10⁴ <= nums[i] <= 10⁴",
        "1 <= k <= nums.length",
    ],
    "starter_code": {
        "python": "def max_sliding_window(nums, k):\n    # Your code here\n    pass",
        "javascript": "function maxSlidingWindow(nums, k) {\n    // Your code here\n}",
        "java": "public int[] maxSlidingWindow(int[] nums, int k) {\n    // Your code here\n    return new int[0];\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([1,3,-1,-3,5,3,6,7], 3), ([1], 1), ([9,11], 2)]\n"
            "    for nums, k in cases:\n"
            "        print(f\"max_sliding_window({nums}, {k}) = {max_sliding_window(nums, k)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,3,-1,-3,5,3,6,7], 3], [[1], 1]].forEach(([nums, k]) =>\n"
            "    console.log(`maxSlidingWindow =`, maxSlidingWindow(nums, k))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.Arrays;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(Arrays.toString(s.maxSlidingWindow(new int[]{1,3,-1,-3,5,3,6,7}, 3)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 3, -1, -3, 5, 3, 6, 7], "k": 3}, "expected": [3, 3, 5, 5, 6, 7],
         "description": "Classic LeetCode example", "tags": ["basic"]},
        {"input": {"nums": [1, 3, -1, -3, 5, 3, 6, 7], "k": 1}, "expected": [1, 3, -1, -3, 5, 3, 6, 7],
         "description": "k=1 — every element is its own window", "tags": ["edge"]},
        {"input": {"nums": [1, 3, -1, -3, 5, 3, 6, 7], "k": 8}, "expected": [7],
         "description": "k=n — single window over entire array", "tags": ["edge"]},
        {"input": {"nums": [1, 2, 3, 4, 5, 6], "k": 3}, "expected": [3, 4, 5, 6],
         "description": "Strictly ascending — window max is always the right edge", "tags": ["tricky"]},
        {"input": {"nums": [6, 5, 4, 3, 2, 1], "k": 3}, "expected": [6, 5, 4, 3],
         "description": "Strictly descending — window max is always the left edge (front of deque)",
         "tags": ["tricky"]},
        {"input": {"nums": [4, 4, 4, 4, 4], "k": 2}, "expected": [4, 4, 4, 4],
         "description": "All equal — duplicates handled by ≤ pop rule", "tags": ["edge"]},
        {"input": {"nums": [2, 1, 2, 1, 2, 1], "k": 2}, "expected": [2, 2, 2, 2, 2],
         "description": "k=2 alternating — same max repeats", "tags": ["tricky"]},
        {"input": {"nums": [-7, -8, -1, -3, -2], "k": 3}, "expected": [-1, -1, -1],
         "description": "All-negative values — sign handling", "tags": ["edge"]},
        {"input": {"nums": [1, 3, 1, 2, 0, 5], "k": 3}, "expected": [3, 3, 2, 5],
         "description": "Mixed — peak slides out then a new one appears", "tags": ["basic"]},
        {"input": {"nums": [9, 11], "k": 2}, "expected": [11],
         "description": "Two-element array, k=n=2", "tags": ["edge"]},
        {"input": {"nums": [5], "k": 1}, "expected": [5],
         "description": "Single element, k=1", "tags": ["edge"]},
        {"input": {"nums": [10, 9, 8, 7, 6, 5, 4, 3, 2, 1], "k": 4}, "expected": [10, 9, 8, 7, 6, 5, 4],
         "description": "Long descending — front of deque keeps falling off", "tags": ["tricky"]},
        {"input": {"nums": list(range(1000)), "k": 100}, "expected": list(range(99, 1000)),
         "description": "1K ascending, k=100 — stress for O(n·k) brute force", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Monotonic Deque (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(k)",
            "description": (
                "Maintain a deque of **indices** whose values form a non-increasing sequence front-to-back. "
                "For each new index `i`: (1) pop from the front while it's out of window (`front <= i - k`); "
                "(2) pop from the back while `nums[back] <= nums[i]`; (3) push `i`. Once `i >= k - 1`, append "
                "`nums[deque[0]]` to the result. Each index enters and leaves the deque at most once → O(n)."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "def max_sliding_window(nums, k):\n"
                    "    dq = deque()  # holds indices, values nums[dq[0]] >= nums[dq[1]] >= ...\n"
                    "    out = []\n"
                    "    for i, x in enumerate(nums):\n"
                    "        # 1. drop indices that fell out of the window\n"
                    "        if dq and dq[0] <= i - k:\n"
                    "            dq.popleft()\n"
                    "        # 2. drop tail values dominated by x\n"
                    "        while dq and nums[dq[-1]] <= x:\n"
                    "            dq.pop()\n"
                    "        dq.append(i)\n"
                    "        # 3. emit once a full window is formed\n"
                    "        if i >= k - 1:\n"
                    "            out.append(nums[dq[0]])\n"
                    "    return out"
                ),
                "javascript": (
                    "function maxSlidingWindow(nums, k) {\n"
                    "    const dq = [];  // indices\n"
                    "    const out = [];\n"
                    "    for (let i = 0; i < nums.length; i++) {\n"
                    "        if (dq.length && dq[0] <= i - k) dq.shift();\n"
                    "        while (dq.length && nums[dq[dq.length - 1]] <= nums[i]) dq.pop();\n"
                    "        dq.push(i);\n"
                    "        if (i >= k - 1) out.push(nums[dq[0]]);\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public int[] maxSlidingWindow(int[] nums, int k) {\n"
                    "    int n = nums.length;\n"
                    "    int[] out = new int[n - k + 1];\n"
                    "    java.util.Deque<Integer> dq = new java.util.ArrayDeque<>();\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        if (!dq.isEmpty() && dq.peekFirst() <= i - k) dq.pollFirst();\n"
                    "        while (!dq.isEmpty() && nums[dq.peekLast()] <= nums[i]) dq.pollLast();\n"
                    "        dq.offerLast(i);\n"
                    "        if (i >= k - 1) out[i - k + 1] = nums[dq.peekFirst()];\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Max-Heap with Lazy Deletion",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "Push `(-value, index)` for every element. Before reading the max, pop any heap-top whose "
                "index is out of the current window (lazy deletion). Simpler to code than a deque if you're "
                "shaky on the monotonic invariant; the log factor is acceptable for n up to ~10⁵ but loses "
                "to the deque on tighter limits."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "def max_sliding_window(nums, k):\n"
                    "    heap = []\n"
                    "    out = []\n"
                    "    for i, x in enumerate(nums):\n"
                    "        heapq.heappush(heap, (-x, i))\n"
                    "        if i >= k - 1:\n"
                    "            while heap[0][1] <= i - k:\n"
                    "                heapq.heappop(heap)\n"
                    "            out.append(-heap[0][0])\n"
                    "    return out"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(n·k)",
            "space_complexity": "O(1)",
            "description": (
                "For each of the n−k+1 windows, take `max(nums[i:i+k])`. State as the baseline only — TLEs "
                "at n = 10⁵."
            ),
            "code": {
                "python": (
                    "def max_sliding_window(nums, k):\n"
                    "    return [max(nums[i:i + k]) for i in range(len(nums) - k + 1)]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force: scan each window. O(n·k). Will TLE — state and move on.",
        "2. Ask: across consecutive windows, what changes? One element leaves on the left, one enters on the right. We want a structure that supports both ends.",
        "3. Observation: if `nums[j] <= nums[i]` for `j < i`, then `nums[j]` is *dominated* — it can never be the max of any window that contains `nums[i]`. So we should evict it.",
        "4. That leads directly to a monotonic (non-increasing) deque. Store indices, not values, so the 'sliding out' check is `front <= i - k`.",
        "5. Each index is pushed once and popped at most once → amortised O(1) per step → O(n) total.",
        "6. If the deque pattern feels brittle, fall back to a max-heap with lazy deletion — O(n log n), still passes most limits, easier to keep correct under interview pressure.",
        "7. Edge cases: k=1 (output equals input), k=n (single max), all-equal (deque rule must use `<=`, not `<`, to keep length bounded), all-negative (no special handling needed if you avoid 0-sentinels).",
    ],
    "tips": [
        "Store **indices** in the deque, not values. The window-eviction check then becomes `dq[0] <= i - k`, no extra bookkeeping.",
        "Use `<=` (not `<`) when popping from the back. With `<`, equal-value duplicates linger and the deque can grow to O(n); with `<=`, length stays bounded by k.",
        "The deque is monotonic *non-increasing*, so the front is always the answer for the current window. Don't search the deque — `dq[0]` is O(1).",
        "In Python use `collections.deque`; lists give you O(n) `pop(0)` and silently turn the algorithm into O(n²). In JS, plain arrays with `shift()` have the same trap — for tight constraints, implement a ring buffer or use a head pointer.",
        "Common follow-up: 'Sliding Window Minimum' — same code, flip the comparison. 'Shortest Subarray with Sum at Least K' — monotonic deque on prefix sums. Recognise the pattern.",
        "Heap solution gotcha: don't pop on every push, only before *reading* the top — otherwise you waste O(log n) work on indices that may yet become the max.",
    ],
    "companies": ["Amazon", "Google", "Facebook", "Microsoft", "Bloomberg", "Uber"],
    "topics": ["Array", "Sliding Window", "Monotonic Deque", "Heap"],
    "time_complexity": "O(n)",
    "space_complexity": "O(k)",
}


def REFERENCE(nums, k):
    dq = deque()
    out = []
    for i, x in enumerate(nums):
        if dq and dq[0] <= i - k:
            dq.popleft()
        while dq and nums[dq[-1]] <= x:
            dq.pop()
        dq.append(i)
        if i >= k - 1:
            out.append(nums[dq[0]])
    return out


register(PAYLOAD, REFERENCE)
