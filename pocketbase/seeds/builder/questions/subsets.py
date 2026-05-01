"""Subsets — Medium. Backtracking / Bit Manipulation.

The canonical 'enumerate the power set' problem. Three textbook
solutions all show up in interviews: backtracking (the recursion
tree pattern that also solves Combinations and Permutations),
iterative doubling (the cleanest code), and bit enumeration (the
'oh that's clever' answer that also generalises to subset-sum
DP). Worth being fluent in all three because the follow-ups
(Subsets II with duplicates, fixed-size Combinations, Permutations)
each pick a different base.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Subsets",
    "difficulty": "Medium",
    "description": (
        "Given an integer array `nums` of **distinct** elements, return *all possible subsets* "
        "(the power set).\n\n"
        "The solution set **must not contain duplicate subsets**. Return the solution in **any order**.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,2,3]`\n"
        "- Output: `[[],[1],[2],[1,2],[3],[1,3],[2,3],[1,2,3]]`\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [0]`\n"
        "- Output: `[[],[0]]`\n\n"
        "Note: there are exactly `2^n` subsets, where `n = len(nums)`. Both the outer ordering "
        "of subsets and the inner ordering of elements within each subset are unspecified — "
        "any permutation of any valid power set is accepted."
    ),
    "hints": [
        "There are exactly 2^n subsets. Any solution that runs faster than that is wrong — you can't enumerate 2^n things in less than 2^n work.",
        "Backtracking: at each index, choose to include or exclude `nums[i]`. The recursion tree has 2^n leaves; each leaf is a subset.",
        "Iterative: start with `[[]]`. For each new number, double the list by appending the number to every existing subset.",
        "Bit manipulation: enumerate `mask` from 0 to 2^n - 1. Bit `i` of `mask` decides whether `nums[i]` is in the subset.",
        "Don't forget the empty subset `[]` — it's always part of the answer.",
    ],
    "constraints": [
        "1 <= nums.length <= 10",
        "-10 <= nums[i] <= 10",
        "All the numbers of `nums` are unique.",
    ],
    "starter_code": {
        "python": "def subsets(nums):\n    # Your code here\n    pass",
        "javascript": "function subsets(nums) {\n    // Your code here\n}",
        "java": "public List<List<Integer>> subsets(int[] nums) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[1, 2, 3], [0], []]\n"
            "    for nums in cases:\n"
            "        print(f\"subsets({nums}) = {subsets(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1, 2, 3], [0], []].forEach(nums =>\n"
            "    console.log(`subsets(${JSON.stringify(nums)}) =`, JSON.stringify(subsets(nums)))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.subsets(new int[]{1, 2, 3}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 2, 3]},
         "expected": {"$match": "unordered_deep",
                      "value": [[], [1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]]},
         "description": "Three-element power set — 8 subsets", "tags": ["basic"]},
        {"input": {"nums": []},
         "expected": {"$match": "unordered_deep", "value": [[]]},
         "description": "Empty input — only the empty subset", "tags": ["edge"]},
        {"input": {"nums": [0]},
         "expected": {"$match": "unordered_deep", "value": [[], [0]]},
         "description": "Single element — empty plus singleton", "tags": ["edge"]},
        {"input": {"nums": [1, 2]},
         "expected": {"$match": "unordered_deep", "value": [[], [1], [2], [1, 2]]},
         "description": "Two elements — 4 subsets", "tags": ["basic"]},
        {"input": {"nums": [-1, 0, 1]},
         "expected": {"$match": "unordered_deep",
                      "value": [[], [-1], [0], [1], [-1, 0], [-1, 1], [0, 1], [-1, 0, 1]]},
         "description": "Mix of negative, zero, positive — distinctness still holds",
         "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 3, 4]},
         "expected": {"$match": "unordered_deep",
                      "value": [
                          [],
                          [1], [2], [3], [4],
                          [1, 2], [1, 3], [1, 4], [2, 3], [2, 4], [3, 4],
                          [1, 2, 3], [1, 2, 4], [1, 3, 4], [2, 3, 4],
                          [1, 2, 3, 4],
                      ]},
         "description": "Four elements — full 16-subset power set", "tags": ["tricky"]},
        {"input": {"nums": [5, 10]},
         "expected": {"$match": "unordered_deep",
                      "value": [[], [5], [10], [5, 10]]},
         "description": "Larger values — verifies we're not assuming small numbers",
         "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Backtracking (Include / Exclude)",
            "time_complexity": "O(n · 2^n)",
            "space_complexity": "O(n) recursion depth (output excluded)",
            "description": (
                "At each index, recurse twice — once with `nums[i]` included, once without. The "
                "recursion tree has 2^n leaves; each leaf records the current path as a subset. "
                "This is the prototype recursion-tree pattern that also solves Combinations and "
                "Permutations."
            ),
            "code": {
                "python": (
                    "def subsets(nums):\n"
                    "    result = []\n"
                    "    path = []\n"
                    "\n"
                    "    def backtrack(i):\n"
                    "        if i == len(nums):\n"
                    "            result.append(path[:])\n"
                    "            return\n"
                    "        # exclude nums[i]\n"
                    "        backtrack(i + 1)\n"
                    "        # include nums[i]\n"
                    "        path.append(nums[i])\n"
                    "        backtrack(i + 1)\n"
                    "        path.pop()\n"
                    "\n"
                    "    backtrack(0)\n"
                    "    return result"
                ),
                "javascript": (
                    "function subsets(nums) {\n"
                    "    const result = [];\n"
                    "    const path = [];\n"
                    "    const backtrack = (i) => {\n"
                    "        if (i === nums.length) {\n"
                    "            result.push([...path]);\n"
                    "            return;\n"
                    "        }\n"
                    "        backtrack(i + 1);\n"
                    "        path.push(nums[i]);\n"
                    "        backtrack(i + 1);\n"
                    "        path.pop();\n"
                    "    };\n"
                    "    backtrack(0);\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public List<List<Integer>> subsets(int[] nums) {\n"
                    "    List<List<Integer>> result = new ArrayList<>();\n"
                    "    backtrack(nums, 0, new ArrayList<>(), result);\n"
                    "    return result;\n"
                    "}\n"
                    "private void backtrack(int[] nums, int i, List<Integer> path, List<List<Integer>> result) {\n"
                    "    if (i == nums.length) {\n"
                    "        result.add(new ArrayList<>(path));\n"
                    "        return;\n"
                    "    }\n"
                    "    backtrack(nums, i + 1, path, result);\n"
                    "    path.add(nums[i]);\n"
                    "    backtrack(nums, i + 1, path, result);\n"
                    "    path.remove(path.size() - 1);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Iterative Doubling",
            "time_complexity": "O(n · 2^n)",
            "space_complexity": "O(n · 2^n) for output",
            "description": (
                "Start with `[[]]`. For each new number, append it to every existing subset and "
                "add those new subsets to the list. After n iterations the list has 2^n subsets. "
                "Often the cleanest code on a whiteboard — no recursion, no bitmasks."
            ),
            "code": {
                "python": (
                    "def subsets(nums):\n"
                    "    result = [[]]\n"
                    "    for x in nums:\n"
                    "        result += [sub + [x] for sub in result]\n"
                    "    return result"
                ),
                "javascript": (
                    "function subsets(nums) {\n"
                    "    let result = [[]];\n"
                    "    for (const x of nums) {\n"
                    "        const next = result.map(sub => [...sub, x]);\n"
                    "        result = result.concat(next);\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Bit Manipulation",
            "time_complexity": "O(n · 2^n)",
            "space_complexity": "O(n · 2^n) for output",
            "description": (
                "Each subset corresponds to an n-bit mask. Enumerate `mask` from 0 to 2^n - 1; "
                "for each mask, the i-th bit decides whether `nums[i]` is in that subset. "
                "Direct, no recursion, and the same trick generalises to subset-sum DP."
            ),
            "code": {
                "python": (
                    "def subsets(nums):\n"
                    "    n = len(nums)\n"
                    "    result = []\n"
                    "    for mask in range(1 << n):\n"
                    "        sub = [nums[i] for i in range(n) if mask & (1 << i)]\n"
                    "        result.append(sub)\n"
                    "    return result"
                ),
                "javascript": (
                    "function subsets(nums) {\n"
                    "    const n = nums.length;\n"
                    "    const result = [];\n"
                    "    for (let mask = 0; mask < (1 << n); mask++) {\n"
                    "        const sub = [];\n"
                    "        for (let i = 0; i < n; i++) {\n"
                    "            if (mask & (1 << i)) sub.push(nums[i]);\n"
                    "        }\n"
                    "        result.push(sub);\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Output size is 2^n. Any 'optimal' answer has to be at least 2^n work — clarify this with the interviewer up front so 'O(2^n)' isn't a surprise.",
        "2. The cleanest mental model is the binary decision tree: for each element, include or exclude. n levels, 2^n leaves, each leaf is a subset.",
        "3. Backtracking writes that tree directly — recurse twice at each level. Pop after the include branch to restore the path; standard backtracking discipline.",
        "4. Iterative doubling reframes the same idea: after processing k elements, you have 2^k subsets. Adding the (k+1)-th doubles the list — each old subset spawns one new subset that includes the new element.",
        "5. Bit manipulation collapses both into pure enumeration: each integer 0..2^n - 1 *is* a subset, with bit i = 'include nums[i]'. Cleanest code, but only practical for n ≤ ~20.",
        "6. Edge cases: empty input → `[[]]` (the empty subset is always present); single element → `[[], [x]]`. All three solutions handle these without special cases.",
    ],
    "tips": [
        "Subsets II (with duplicates): sort first, then in the backtracking tree skip the include-branch for any duplicate at the *same recursion level*. Same skeleton, one extra check.",
        "Combinations (n choose k): same recursion tree, but only record paths whose length is k. Equivalent to subsets filtered by `len(path) == k`.",
        "Permutations: different tree — at each level you pick *any unused* element, not 'include or not'. The branching factor changes from 2 to (n − depth).",
        "Don't append `path` directly to the result inside backtracking — append `path[:]` (a copy). Aliasing the same list will leave you with N copies of the final state.",
        "For very large n the 2^n output dominates. If the problem only needs the *count* (or sum) of subsets meeting a property, switch to subset-sum DP and skip enumeration entirely.",
    ],
    "companies": ["Amazon", "Facebook", "Bloomberg"],
    "topics": ["Array", "Backtracking", "Bit Manipulation"],
    "time_complexity": "O(n · 2^n)",
    "space_complexity": "O(n · 2^n)",
}


def REFERENCE(nums):
    result = [[]]
    for x in nums:
        result += [sub + [x] for sub in result]
    return result


register(PAYLOAD, REFERENCE)
