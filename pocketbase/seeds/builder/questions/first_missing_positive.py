"""First Missing Positive — Hard. Cyclic Sort / In-Place Hashing.

The canonical 'use the array as a hashmap' problem. The trick: in an
array of length n, the answer is always in [1, n+1]. So values outside
that range are noise — and inside it, you can place value k at index
k-1 in O(n) total swaps. The first index whose value disagrees is your
answer. The sign-marking variant is the same idea with bit-encoding
instead of swapping. Worth knowing both because interviewers occasionally
forbid mutation of the *values* (sign trick) or forbid swaps (cyclic).
"""
from builder.registry import register


PAYLOAD = {
    "title": "First Missing Positive",
    "difficulty": "Hard",
    "description": (
        "Given an unsorted integer array `nums`, return the smallest **positive integer** that is not "
        "present in `nums`.\n\n"
        "You must implement an algorithm that runs in **O(n)** time and uses **O(1)** auxiliary space "
        "(the input array itself may be modified).\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,2,0]`\n"
        "- Output: `3`\n"
        "- Explanation: The numbers 1 and 2 are present, so the smallest missing positive is 3.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [3,4,-1,1]`\n"
        "- Output: `2`\n"
        "- Explanation: 1 is present but 2 is missing — so the answer is 2."
    ),
    "hints": [
        "Key observation: for an array of length `n`, the answer must lie in the range `[1, n+1]`. Anything outside that range is irrelevant.",
        "Cyclic sort idea: place each value `k` (where `1 <= k <= n`) at index `k-1`. Use a while-loop to keep swapping until the slot you're standing on is either out of range or already correct.",
        "Ignore values that are `<= 0`, `> n`, or duplicates of what's already at the target index — they can't help you.",
        "After placement, scan left-to-right: the first index `i` where `nums[i] != i+1` gives the answer `i+1`. If every slot matches, the answer is `n+1`.",
        "Alternative: sign-marker. First sweep replaces non-positives with `n+1` (a sentinel out of range). Second sweep flips the sign of `nums[abs(v)-1]` for each in-range `v`. Third sweep returns the first index whose value is still positive, plus one.",
    ],
    "constraints": [
        "1 <= nums.length <= 10⁵",
        "-2³¹ <= nums[i] <= 2³¹ - 1",
        "Must run in O(n) time and use O(1) auxiliary space",
    ],
    "starter_code": {
        "python": "def first_missing_positive(nums):\n    # Your code here\n    pass",
        "javascript": "function firstMissingPositive(nums) {\n    // Your code here\n}",
        "java": "public int firstMissingPositive(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[1,2,0], [3,4,-1,1], [7,8,9,11,12]]\n"
            "    for nums in cases:\n"
            "        print(f\"first_missing_positive({nums}) = {first_missing_positive(nums[:])}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,2,0], [3,4,-1,1], [7,8,9,11,12]].forEach(nums =>\n"
            "    console.log(`firstMissingPositive =`, firstMissingPositive([...nums]))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.firstMissingPositive(new int[]{3,4,-1,1}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 2, 0]}, "expected": 3,
         "description": "Classic LC example — 1 and 2 present, 3 missing", "tags": ["basic"]},
        {"input": {"nums": [3, 4, -1, 1]}, "expected": 2,
         "description": "Classic LC example — 1 present, 2 missing", "tags": ["basic"]},
        {"input": {"nums": [7, 8, 9, 11, 12]}, "expected": 1,
         "description": "All values out of range [1,n] — answer is 1", "tags": ["basic"]},
        {"input": {"nums": [1, 2, 3, 4, 5]}, "expected": 6,
         "description": "All positives 1..n present — answer is n+1", "tags": ["edge"]},
        {"input": {"nums": [2, 3, 4]}, "expected": 1,
         "description": "Missing 1 — smallest possible answer", "tags": ["edge"]},
        {"input": {"nums": [-1, -2, -3]}, "expected": 1,
         "description": "All negative — answer is 1", "tags": ["edge"]},
        {"input": {"nums": [1]}, "expected": 2,
         "description": "Single element 1 — answer is 2", "tags": ["edge"]},
        {"input": {"nums": [2]}, "expected": 1,
         "description": "Single element 2 — answer is 1 (1 is missing)", "tags": ["edge"]},
        {"input": {"nums": [0]}, "expected": 1,
         "description": "Single zero — answer is 1", "tags": ["edge"]},
        {"input": {"nums": [0, 1, 2]}, "expected": 3,
         "description": "Zero is irrelevant; 1 and 2 present → 3", "tags": ["edge"]},
        {"input": {"nums": [1, 1]}, "expected": 2,
         "description": "Duplicate 1s — duplicates do not help", "tags": ["tricky"]},
        {"input": {"nums": [1, 1, 2, 2]}, "expected": 3,
         "description": "Multiple duplicates — answer is the first true gap", "tags": ["tricky"]},
        {"input": {"nums": [-1, 4, 2, 1, 9, 10]}, "expected": 3,
         "description": "Mixed signs and out-of-range — gap is 3", "tags": ["tricky"]},
        {"input": {"nums": list(range(1, 10001))}, "expected": 10001,
         "description": "10K consecutive positives — answer is n+1", "tags": ["large"]},
        {"input": {"nums": [-i for i in range(1, 10001)]}, "expected": 1,
         "description": "10K negatives — answer is 1", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Cyclic Sort In-Place (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "For each index `i`, while `nums[i]` is in range `[1, n]` and is not already at its "
                "correct slot (`nums[nums[i]-1] != nums[i]`), swap it into place. Each swap puts at "
                "least one element where it belongs, so the total work is O(n). After the pass, scan "
                "for the first index `i` with `nums[i] != i+1`; that's the answer. If every slot is "
                "correct, return `n+1`. Pure in-place — no extra memory."
            ),
            "code": {
                "python": (
                    "def first_missing_positive(nums):\n"
                    "    n = len(nums)\n"
                    "    i = 0\n"
                    "    while i < n:\n"
                    "        v = nums[i]\n"
                    "        if 1 <= v <= n and nums[v - 1] != v:\n"
                    "            nums[i], nums[v - 1] = nums[v - 1], nums[i]\n"
                    "        else:\n"
                    "            i += 1\n"
                    "    for i in range(n):\n"
                    "        if nums[i] != i + 1:\n"
                    "            return i + 1\n"
                    "    return n + 1"
                ),
                "javascript": (
                    "function firstMissingPositive(nums) {\n"
                    "    const n = nums.length;\n"
                    "    let i = 0;\n"
                    "    while (i < n) {\n"
                    "        const v = nums[i];\n"
                    "        if (v >= 1 && v <= n && nums[v - 1] !== v) {\n"
                    "            [nums[i], nums[v - 1]] = [nums[v - 1], nums[i]];\n"
                    "        } else {\n"
                    "            i++;\n"
                    "        }\n"
                    "    }\n"
                    "    for (let j = 0; j < n; j++) {\n"
                    "        if (nums[j] !== j + 1) return j + 1;\n"
                    "    }\n"
                    "    return n + 1;\n"
                    "}"
                ),
                "java": (
                    "public int firstMissingPositive(int[] nums) {\n"
                    "    int n = nums.length;\n"
                    "    int i = 0;\n"
                    "    while (i < n) {\n"
                    "        int v = nums[i];\n"
                    "        if (v >= 1 && v <= n && nums[v - 1] != v) {\n"
                    "            int tmp = nums[v - 1];\n"
                    "            nums[v - 1] = v;\n"
                    "            nums[i] = tmp;\n"
                    "        } else {\n"
                    "            i++;\n"
                    "        }\n"
                    "    }\n"
                    "    for (int j = 0; j < n; j++) {\n"
                    "        if (nums[j] != j + 1) return j + 1;\n"
                    "    }\n"
                    "    return n + 1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sign-Marking In-Place",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Three sweeps. Sweep 1: replace every non-positive with `n+1` (a sentinel guaranteed "
                "out of range). Sweep 2: for each `v = abs(nums[i])`, if `1 <= v <= n`, flip the sign "
                "of `nums[v-1]` to negative — this 'marks' that the value `v` was seen. Use abs() "
                "because earlier marks may have made it negative. Sweep 3: return the first index "
                "whose value is still positive, plus one; if none, return `n+1`. Same complexity as "
                "cyclic sort but encodes presence in the sign bit instead of position."
            ),
            "code": {
                "python": (
                    "def first_missing_positive(nums):\n"
                    "    n = len(nums)\n"
                    "    for i in range(n):\n"
                    "        if nums[i] <= 0:\n"
                    "            nums[i] = n + 1\n"
                    "    for i in range(n):\n"
                    "        v = abs(nums[i])\n"
                    "        if 1 <= v <= n and nums[v - 1] > 0:\n"
                    "            nums[v - 1] = -nums[v - 1]\n"
                    "    for i in range(n):\n"
                    "        if nums[i] > 0:\n"
                    "            return i + 1\n"
                    "    return n + 1"
                ),
                "javascript": (
                    "function firstMissingPositive(nums) {\n"
                    "    const n = nums.length;\n"
                    "    for (let i = 0; i < n; i++) {\n"
                    "        if (nums[i] <= 0) nums[i] = n + 1;\n"
                    "    }\n"
                    "    for (let i = 0; i < n; i++) {\n"
                    "        const v = Math.abs(nums[i]);\n"
                    "        if (v >= 1 && v <= n && nums[v - 1] > 0) {\n"
                    "            nums[v - 1] = -nums[v - 1];\n"
                    "        }\n"
                    "    }\n"
                    "    for (let i = 0; i < n; i++) {\n"
                    "        if (nums[i] > 0) return i + 1;\n"
                    "    }\n"
                    "    return n + 1;\n"
                    "}"
                ),
                "java": (
                    "public int firstMissingPositive(int[] nums) {\n"
                    "    int n = nums.length;\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        if (nums[i] <= 0) nums[i] = n + 1;\n"
                    "    }\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        int v = Math.abs(nums[i]);\n"
                    "        if (v >= 1 && v <= n && nums[v - 1] > 0) {\n"
                    "            nums[v - 1] = -nums[v - 1];\n"
                    "        }\n"
                    "    }\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        if (nums[i] > 0) return i + 1;\n"
                    "    }\n"
                    "    return n + 1;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Bound the answer: with n elements, the smallest missing positive is in [1, n+1]. So values outside [1, n] cannot be the answer and cannot help us deduce it.",
        "2. We need O(1) space, which rules out a hash set. The only memory we have is the array itself — so we must encode 'is value k present?' inside the array.",
        "3. Cyclic sort encoding: put value k at index k-1. Then 'is k present?' becomes 'is nums[k-1] == k?'. Sign-marking encoding: flip sign of nums[k-1] when k is seen.",
        "4. Cyclic sort loop: while the current slot holds an in-range value that doesn't match its target slot, swap. Increment only when the slot is settled. Each swap puts one element home → O(n) total swaps.",
        "5. After placement, the first mismatch `nums[i] != i+1` gives the answer `i+1`. If every slot matches, the array is exactly `[1..n]` and the answer is `n+1`.",
        "6. Edge cases: all negatives → no in-range values → first mismatch at index 0 → answer 1. Duplicates → second copy fails the `nums[v-1] != v` guard and is skipped (won't infinite-loop).",
    ],
    "tips": [
        "The duplicate guard `nums[v-1] != v` is what prevents infinite swaps. Forget it and you'll loop forever on inputs like `[1, 1]`.",
        "When you swap in cyclic sort, do *not* increment `i` — the new value at `nums[i]` may also need placement. Increment only when the slot is settled (out-of-range or already correct).",
        "Sign-marking requires `abs()` when reading, because a previous iteration may have flipped the value's sign. Forgetting `abs` is the #1 bug in this approach.",
        "Watch the integer overflow trap in Java: `-Integer.MIN_VALUE` overflows. The 'replace non-positives with n+1' sweep sidesteps it by clamping all problematic values out of range first.",
        "Common follow-up: 'find all duplicates in [1..n] in-place'. Same cyclic-sort skeleton — at the end, indices whose values disagree are the duplicates / missing.",
        "If the interviewer allows O(n) extra space, the boring solution is `set(nums)` then iterate `1, 2, 3, ...` until you find the gap. Mention it as a baseline before optimizing.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Facebook", "Apple", "Bloomberg", "Stripe"],
    "topics": ["Array", "Hash Table", "Cyclic Sort"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums):
    nums = list(nums)
    n = len(nums)
    i = 0
    while i < n:
        v = nums[i]
        if 1 <= v <= n and nums[v - 1] != v:
            nums[i], nums[v - 1] = nums[v - 1], nums[i]
        else:
            i += 1
    for i in range(n):
        if nums[i] != i + 1:
            return i + 1
    return n + 1


register(PAYLOAD, REFERENCE)
