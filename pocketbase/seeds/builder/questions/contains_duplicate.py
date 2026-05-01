"""Contains Duplicate — Easy. Arrays / Hashing.

The canonical first-day arrays/hashing problem. Its real value as an
interview question is the explicit memory-vs-time trade-off it forces:
brute force is O(1) extra space, sort is O(1) + O(n log n), hash set
is O(n) + O(n). Demonstrate awareness of all three.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Contains Duplicate",
    "difficulty": "Easy",
    "description": (
        "Given an integer array `nums`, return `true` if any value appears at least "
        "twice in the array, and return `false` if every element is distinct.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,2,3,1]`\n"
        "- Output: `true`\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [1,2,3,4]`\n"
        "- Output: `false`\n\n"
        "**Example 3:**\n"
        "- Input: `nums = [1,1,1,3,3,4,3,2,4,2]`\n"
        "- Output: `true`"
    ),
    "hints": [
        "Brute force: compare every pair — O(n²) time, O(1) space. Mention it; it's the baseline you're going to beat.",
        "Sort first, then duplicates become adjacent — O(n log n) time, O(1) extra space if you're allowed to mutate the input.",
        "Hash set: walk once. If a value is already in the set, return true. O(n) time, O(n) space.",
        "Pythonic shortcut: `len(set(nums)) != len(nums)` — same complexity as the explicit set, but say what's happening out loud; interviewers want to hear the data-structure choice.",
        "Edge: arrays of length 1 can never have a duplicate, so handle that early or rely on the loop to no-op.",
    ],
    "constraints": [
        "1 <= nums.length <= 10⁵",
        "-10⁹ <= nums[i] <= 10⁹",
    ],
    "starter_code": {
        "python": "def contains_duplicate(nums):\n    # Your code here\n    pass",
        "javascript": "function containsDuplicate(nums) {\n    // Your code here\n}",
        "java": "public boolean containsDuplicate(int[] nums) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    test_cases = [\n"
            "        [1, 2, 3, 1],\n"
            "        [1, 2, 3, 4],\n"
            "        [1, 1, 1, 3, 3, 4, 3, 2, 4, 2],\n"
            "    ]\n"
            "    for nums in test_cases:\n"
            "        print(f\"contains_duplicate({nums}) = {contains_duplicate(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "const testCases = [[1,2,3,1], [1,2,3,4], [1,1,1,3,3,4,3,2,4,2]];\n"
            "testCases.forEach((nums) =>\n"
            "    console.log(`containsDuplicate(${JSON.stringify(nums)}) =`, containsDuplicate(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] tests = {{1,2,3,1}, {1,2,3,4}, {1,1,1,3,3,4,3,2,4,2}};\n"
            "        for (int[] t : tests) System.out.println(s.containsDuplicate(t));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 2, 3, 1]}, "expected": True,
         "description": "Single duplicate near the end", "tags": ["basic"]},
        {"input": {"nums": [1, 2, 3, 4]}, "expected": False,
         "description": "All distinct", "tags": ["basic"]},
        {"input": {"nums": [1, 1, 1, 3, 3, 4, 3, 2, 4, 2]}, "expected": True,
         "description": "Multiple duplicates", "tags": ["basic"]},
        {"input": {"nums": [7]}, "expected": False,
         "description": "Single element — distinct by definition", "tags": ["edge"]},
        {"input": {"nums": [-1, -1]}, "expected": True,
         "description": "Negative-value duplicate", "tags": ["edge"]},
        {"input": {"nums": [0, 0]}, "expected": True,
         "description": "Zero duplicate", "tags": ["edge"]},
        {"input": {"nums": [1000000000, -1000000000, 1000000000]}, "expected": True,
         "description": "Constraint-boundary values, duplicate at the edge", "tags": ["edge"]},
        {"input": {"nums": [1] * 1000}, "expected": True,
         "description": "All identical — duplicate found at index 1", "tags": ["edge", "tricky"]},
        {"input": {"nums": list(range(10000))}, "expected": False,
         "description": "10K distinct ascending — worst case for the hash-set miss path", "tags": ["large"]},
        {"input": {"nums": list(range(9999)) + [42]}, "expected": True,
         "description": "10K mostly-distinct with one late duplicate", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Hash Set (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk the array once. Maintain a set of values you've already seen. "
                "The moment you encounter a value already in the set, return true. "
                "If the walk completes, every value was distinct."
            ),
            "code": {
                "python": (
                    "def contains_duplicate(nums):\n"
                    "    seen = set()\n"
                    "    for n in nums:\n"
                    "        if n in seen:\n"
                    "            return True\n"
                    "        seen.add(n)\n"
                    "    return False"
                ),
                "javascript": (
                    "function containsDuplicate(nums) {\n"
                    "    const seen = new Set();\n"
                    "    for (const n of nums) {\n"
                    "        if (seen.has(n)) return true;\n"
                    "        seen.add(n);\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
                "java": (
                    "public boolean containsDuplicate(int[] nums) {\n"
                    "    Set<Integer> seen = new HashSet<>();\n"
                    "    for (int n : nums) {\n"
                    "        if (!seen.add(n)) return true;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sort + Adjacent Compare",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(1) extra (in-place sort) or O(n) if you must clone",
            "description": (
                "Sort the array, then walk it once and check each element against its "
                "predecessor. Wins when memory is tight; loses on wall-clock time. "
                "Mutates the caller's array — clone first if the input must be preserved."
            ),
            "code": {
                "python": (
                    "def contains_duplicate(nums):\n"
                    "    arr = sorted(nums)\n"
                    "    for i in range(1, len(arr)):\n"
                    "        if arr[i] == arr[i - 1]:\n"
                    "            return True\n"
                    "    return False"
                ),
                "javascript": (
                    "function containsDuplicate(nums) {\n"
                    "    const arr = [...nums].sort((a, b) => a - b);\n"
                    "    for (let i = 1; i < arr.length; i++) {\n"
                    "        if (arr[i] === arr[i - 1]) return true;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
                "java": (
                    "public boolean containsDuplicate(int[] nums) {\n"
                    "    int[] arr = nums.clone();\n"
                    "    Arrays.sort(arr);\n"
                    "    for (int i = 1; i < arr.length; i++) {\n"
                    "        if (arr[i] == arr[i - 1]) return true;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "Check every pair. Mention it to anchor the conversation; never submit "
                "it as your final answer for n up to 10⁵."
            ),
            "code": {
                "python": (
                    "def contains_duplicate(nums):\n"
                    "    for i in range(len(nums)):\n"
                    "        for j in range(i + 1, len(nums)):\n"
                    "            if nums[i] == nums[j]:\n"
                    "                return True\n"
                    "    return False"
                ),
            },
        },
    ],
    "thought_process": [
        "1. State the brute force first: 'I could check every pair in O(n²).' Interviewers want to hear that you considered the obvious approach.",
        "2. Reframe the operation: 'For each new value, I need to know if I've seen it before.' That's a set-membership query.",
        "3. Pick the data structure: hash set gives O(1) average insert + lookup → overall O(n) time.",
        "4. Surface the trade-off out loud: hashing is fastest but uses O(n) memory; sorting is slower but uses O(1) extra space.",
        "5. Cover the edge cases: single-element arrays (always distinct), arrays where every element is identical (return at i=1), negatives, zeros, constraint-boundary values.",
    ],
    "tips": [
        "If asked about memory pressure, reach for the sort-based approach — same correctness, no auxiliary structure.",
        "Don't write `len(set(nums)) != len(nums)` without saying 'hash set, O(n)' — the interviewer wants to hear the data-structure choice, not just see the trick.",
        "Common follow-up: 'What if duplicates only count when within k positions of each other?' → Sliding hash set of the last k values.",
        "Common follow-up: 'What if values are floats within ε?' → Bucket by ε and check the current bucket plus its two neighbors.",
        "Java gotcha: `Arrays.sort(int[])` is dual-pivot quicksort and runs in-place — but it mutates the input. Clone if the caller cares.",
    ],
    "companies": ["Google", "Amazon", "Microsoft", "Apple", "Meta"],
    "topics": ["Array", "Hash Table", "Sorting"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(nums):
    seen = set()
    for n in nums:
        if n in seen:
            return True
        seen.add(n)
    return False


register(PAYLOAD, REFERENCE)
