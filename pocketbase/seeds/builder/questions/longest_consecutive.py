"""Longest Consecutive Sequence — Medium. Hashing.

The 'sort would be too slow' classic. The trick: only start counting
from values that are the *start* of a run (i.e. value - 1 is not in
the set). That guarantees each value is visited at most twice across
the whole algorithm — overall O(n) despite the inner while-loop.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Longest Consecutive Sequence",
    "difficulty": "Medium",
    "description": (
        "Given an unsorted array of integers `nums`, return the length of the longest consecutive "
        "elements sequence.\n\n"
        "You must write an algorithm that runs in **O(n)** time.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [100,4,200,1,3,2]`\n"
        "- Output: `4`\n"
        "- Explanation: The longest consecutive elements sequence is `[1,2,3,4]`. Length = 4.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [0,3,7,2,5,8,4,6,0,1]`\n"
        "- Output: `9`"
    ),
    "hints": [
        "Sorting and walking gives O(n log n) — easy to write, but fails the O(n) requirement. Mention it as the baseline.",
        "Put every value into a hash set so you can ask 'is x in nums?' in O(1).",
        "For each value v, only attempt to extend a run if v is the *start* of one — i.e. `v - 1` is not in the set. This is what makes the algorithm O(n) overall: each value participates in exactly one walk.",
        "From a confirmed start v, walk v+1, v+2, … while they're in the set. The longest such walk is your answer.",
        "Edge case: empty input → 0. Single element → 1. Duplicates collapse for free thanks to the set.",
    ],
    "constraints": [
        "0 <= nums.length <= 10⁵",
        "-10⁹ <= nums[i] <= 10⁹",
    ],
    "starter_code": {
        "python": "def longest_consecutive(nums):\n    # Your code here\n    pass",
        "javascript": "function longestConsecutive(nums) {\n    // Your code here\n}",
        "java": "public int longestConsecutive(int[] nums) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[100,4,200,1,3,2], [0,3,7,2,5,8,4,6,0,1], []]\n"
            "    for nums in cases:\n"
            "        print(f\"longest_consecutive({nums}) = {longest_consecutive(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[100,4,200,1,3,2], [0,3,7,2,5,8,4,6,0,1]].forEach(nums =>\n"
            "    console.log(`longestConsecutive =`, longestConsecutive(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.longestConsecutive(new int[]{100,4,200,1,3,2}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [100, 4, 200, 1, 3, 2]}, "expected": 4,
         "description": "Standard — run is [1,2,3,4]", "tags": ["basic"]},
        {"input": {"nums": [0, 3, 7, 2, 5, 8, 4, 6, 0, 1]}, "expected": 9,
         "description": "Duplicates and a 9-long run", "tags": ["basic"]},
        {"input": {"nums": []}, "expected": 0,
         "description": "Empty input", "tags": ["edge"]},
        {"input": {"nums": [42]}, "expected": 1,
         "description": "Single element", "tags": ["edge"]},
        {"input": {"nums": [1, 2, 0, 1]}, "expected": 3,
         "description": "Duplicate inside the longest run", "tags": ["tricky"]},
        {"input": {"nums": [-3, -2, -1, 0, 1, 2]}, "expected": 6,
         "description": "Run crosses zero with negatives", "tags": ["tricky"]},
        {"input": {"nums": [10, 5, 12, 3, 55, 30, 4, 11, 2]}, "expected": 4,
         "description": "Two runs: [2,3,4,5] (len 4) and [10,11,12] (len 3)",
         "tags": ["tricky"]},
        {"input": {"nums": [5, 5, 5, 5]}, "expected": 1,
         "description": "All duplicates of the same value", "tags": ["edge"]},
        {"input": {"nums": list(range(10000))}, "expected": 10000,
         "description": "10K consecutive ascending — single run of length 10K", "tags": ["large"]},
        {"input": {"nums": list(range(0, 10000, 2)) + list(range(1, 10000, 2))}, "expected": 10000,
         "description": "Evens then odds — a run only forms after both halves are seeded",
         "tags": ["large", "tricky"]},
    ],
    "solutions": [
        {
            "title": "Hash Set + Run-Start Detection (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Put everything in a set. For each value, walk forward only if it's the start of a run "
                "(its predecessor isn't in the set). The walk visits each value at most once across the "
                "entire algorithm, so the total work is O(n) despite the nested loop."
            ),
            "code": {
                "python": (
                    "def longest_consecutive(nums):\n"
                    "    s = set(nums)\n"
                    "    best = 0\n"
                    "    for n in s:\n"
                    "        if n - 1 in s:\n"
                    "            continue  # not a run start; skip\n"
                    "        length = 1\n"
                    "        while n + length in s:\n"
                    "            length += 1\n"
                    "        if length > best:\n"
                    "            best = length\n"
                    "    return best"
                ),
                "javascript": (
                    "function longestConsecutive(nums) {\n"
                    "    const s = new Set(nums);\n"
                    "    let best = 0;\n"
                    "    for (const n of s) {\n"
                    "        if (s.has(n - 1)) continue;\n"
                    "        let length = 1;\n"
                    "        while (s.has(n + length)) length++;\n"
                    "        if (length > best) best = length;\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
                "java": (
                    "public int longestConsecutive(int[] nums) {\n"
                    "    Set<Integer> s = new HashSet<>();\n"
                    "    for (int n : nums) s.add(n);\n"
                    "    int best = 0;\n"
                    "    for (int n : s) {\n"
                    "        if (s.contains(n - 1)) continue;\n"
                    "        int length = 1;\n"
                    "        while (s.contains(n + length)) length++;\n"
                    "        if (length > best) best = length;\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sort + Linear Scan",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(1) extra (in-place sort)",
            "description": (
                "Sort, then walk once tracking the current run length. Easier to remember; fails the "
                "O(n) constraint. Use only as a fallback if you can't recall the hash-set trick."
            ),
            "code": {
                "python": (
                    "def longest_consecutive(nums):\n"
                    "    if not nums:\n"
                    "        return 0\n"
                    "    nums = sorted(set(nums))\n"
                    "    best = current = 1\n"
                    "    for i in range(1, len(nums)):\n"
                    "        if nums[i] == nums[i - 1] + 1:\n"
                    "            current += 1\n"
                    "            best = max(best, current)\n"
                    "        else:\n"
                    "            current = 1\n"
                    "    return best"
                ),
            },
        },
        {
            "title": "Union-Find by Adjacency",
            "time_complexity": "O(n α(n)) ≈ O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Insert each value into DSU. After inserting v, union it with v-1 and v+1 if they exist. "
                "The largest component is the answer. Beautiful but heavyweight for this problem — the "
                "hash-set approach has fewer moving parts and the same asymptotic cost."
            ),
            "code": {
                "python": (
                    "def longest_consecutive(nums):\n"
                    "    parent, size = {}, {}\n"
                    "    def find(x):\n"
                    "        while parent[x] != x:\n"
                    "            parent[x] = parent[parent[x]]\n"
                    "            x = parent[x]\n"
                    "        return x\n"
                    "    def union(a, b):\n"
                    "        ra, rb = find(a), find(b)\n"
                    "        if ra == rb:\n"
                    "            return\n"
                    "        if size[ra] < size[rb]:\n"
                    "            ra, rb = rb, ra\n"
                    "        parent[rb] = ra\n"
                    "        size[ra] += size[rb]\n"
                    "    for n in set(nums):\n"
                    "        parent[n] = n\n"
                    "        size[n] = 1\n"
                    "        if n - 1 in parent:\n"
                    "            union(n, n - 1)\n"
                    "        if n + 1 in parent:\n"
                    "            union(n, n + 1)\n"
                    "    return max(size.values()) if size else 0"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Notice the explicit O(n) constraint. Sort-based solutions are out.",
        "2. The query you need: 'is value v present in nums?' Hash set gives O(1). Insert all values.",
        "3. Naive walk from every value is O(n²) worst case. The fix: only start the walk from values that are *run starts*.",
        "4. Run-start test: v is a start iff `v - 1` is not in the set. Otherwise some smaller predecessor will already be doing the walk.",
        "5. Each value is touched once during set construction, once during the run-start check, and at most once during a forward walk → O(n) overall.",
        "6. Edge cases: empty (0), all duplicates (1), negatives, ranges crossing zero, duplicates inside a run.",
    ],
    "tips": [
        "If you blank on the run-start trick, fall back to sort and explicitly call out the complexity gap. Better than no answer.",
        "Don't iterate `nums` directly — iterate the *set*. Otherwise duplicates do redundant work (correctness is fine, complexity isn't).",
        "Common follow-up: 'Find the longest consecutive *increasing* subsequence (in array order, not value order).' Different problem — sliding window over indices.",
        "Common follow-up: 'Stream the values one at a time, query longest run after each insert.' Switch to Union-Find: O(α(n)) per insert, longest is `max(size.values())`.",
        "Don't forget: for `nums = []`, return 0 — many candidates only test on non-empty inputs and miss this.",
    ],
    "companies": ["Amazon", "Google", "Facebook", "Microsoft", "Bloomberg"],
    "topics": ["Array", "Hash Table", "Union Find"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(nums):
    s = set(nums)
    best = 0
    for n in s:
        if n - 1 in s:
            continue
        length = 1
        while n + length in s:
            length += 1
        if length > best:
            best = length
    return best


register(PAYLOAD, REFERENCE)
