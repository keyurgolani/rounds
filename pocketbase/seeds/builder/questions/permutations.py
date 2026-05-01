"""Permutations — Medium. Backtracking.

The canonical 'generate all arrangements' problem. The interview value
is in *how* you avoid reusing elements: the `used[]` boolean array is
the cleanest framing, and it generalises straight to Permutations II
(with duplicates) by adding a single skip-on-prev-equal check. The
in-place swap variant is more space-efficient but trickier to get right
under pressure.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Permutations",
    "difficulty": "Medium",
    "description": (
        "Given an array `nums` of **distinct** integers, return all the possible permutations. "
        "You can return the answer in **any order**.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,2,3]`\n"
        "- Output: `[[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]]`\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [0,1]`\n"
        "- Output: `[[0,1],[1,0]]`\n\n"
        "**Example 3:**\n"
        "- Input: `nums = [1]`\n"
        "- Output: `[[1]]`"
    ),
    "hints": [
        "There are exactly n! permutations. State the size up front so the recursion depth and output count aren't a surprise.",
        "Backtracking template: maintain a current path and a `used[]` boolean array. At each level, try every index that isn't used yet.",
        "When the path length equals `n`, copy it into the result. Copy — not append-by-reference — because you'll be mutating the path on the way back up.",
        "Alternative: in-place swap. For position `i`, swap each `j ≥ i` into slot `i`, recurse for `i+1`, then swap back. No extra `used[]` array.",
        "All permutations share the same multiset, so a quick sanity check on any returned list is `sorted(perm) == sorted(nums)`.",
    ],
    "constraints": [
        "1 <= nums.length <= 6",
        "-10 <= nums[i] <= 10",
        "All the integers of nums are unique.",
    ],
    "starter_code": {
        "python": "def permute(nums):\n    # Your code here\n    pass",
        "javascript": "function permute(nums) {\n    // Your code here\n}",
        "java": "public List<List<Integer>> permute(int[] nums) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for nums in [[1,2,3], [0,1], [1]]:\n"
            "        print(f\"permute({nums}) = {permute(nums)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,2,3], [0,1], [1]].forEach(nums =>\n"
            "    console.log(`permute =`, permute(nums))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.permute(new int[]{1,2,3}));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [1, 2, 3]},
         "expected": {"$match": "unordered_deep",
                      "value": [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]},
         "description": "Three distinct elements — 6 permutations", "tags": ["basic"]},
        {"input": {"nums": [0, 1]},
         "expected": {"$match": "unordered_deep",
                      "value": [[0, 1], [1, 0]]},
         "description": "Two elements — 2 permutations", "tags": ["basic"]},
        {"input": {"nums": [1]},
         "expected": {"$match": "unordered_deep",
                      "value": [[1]]},
         "description": "Single element — one permutation", "tags": ["edge"]},
        {"input": {"nums": []},
         "expected": {"$match": "unordered_deep",
                      "value": [[]]},
         "description": "Empty input — the empty permutation", "tags": ["edge"]},
        {"input": {"nums": [-1, 0, 1]},
         "expected": {"$match": "unordered_deep",
                      "value": [[-1, 0, 1], [-1, 1, 0], [0, -1, 1], [0, 1, -1], [1, -1, 0], [1, 0, -1]]},
         "description": "Negative values mixed in — 6 permutations", "tags": ["tricky"]},
        {"input": {"nums": [1, 2, 3, 4]},
         "expected": {"$match": "validator",
                      "description": "All 24 permutations",
                      "code": "lambda inp, out: (isinstance(out, list) and len(out) == 24 and len({tuple(p) for p in out}) == 24 and all(sorted(p) == sorted(inp['nums']) for p in out))"},
         "description": "Four elements — 24 permutations validated by uniqueness + multiset", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Backtracking with used[] (Canonical)",
            "time_complexity": "O(n · n!)",
            "space_complexity": "O(n) recursion + O(n · n!) output",
            "description": (
                "Classic backtracking template. Maintain a `path` list and a `used[]` boolean array. At each "
                "recursion level, try every index that isn't yet used: mark it, append it, recurse, then "
                "un-mark and pop. When `len(path) == n`, snapshot it into the result. Generalises directly to "
                "Permutations II — sort the input and skip `i` when `nums[i] == nums[i-1]` and `used[i-1]` is False."
            ),
            "code": {
                "python": (
                    "def permute(nums):\n"
                    "    n = len(nums)\n"
                    "    result, path, used = [], [], [False] * n\n"
                    "\n"
                    "    def backtrack():\n"
                    "        if len(path) == n:\n"
                    "            result.append(path[:])\n"
                    "            return\n"
                    "        for i in range(n):\n"
                    "            if used[i]:\n"
                    "                continue\n"
                    "            used[i] = True\n"
                    "            path.append(nums[i])\n"
                    "            backtrack()\n"
                    "            path.pop()\n"
                    "            used[i] = False\n"
                    "\n"
                    "    backtrack()\n"
                    "    return result"
                ),
                "javascript": (
                    "function permute(nums) {\n"
                    "    const n = nums.length, result = [], path = [], used = Array(n).fill(false);\n"
                    "    const backtrack = () => {\n"
                    "        if (path.length === n) { result.push([...path]); return; }\n"
                    "        for (let i = 0; i < n; i++) {\n"
                    "            if (used[i]) continue;\n"
                    "            used[i] = true;\n"
                    "            path.push(nums[i]);\n"
                    "            backtrack();\n"
                    "            path.pop();\n"
                    "            used[i] = false;\n"
                    "        }\n"
                    "    };\n"
                    "    backtrack();\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public List<List<Integer>> permute(int[] nums) {\n"
                    "    List<List<Integer>> result = new ArrayList<>();\n"
                    "    boolean[] used = new boolean[nums.length];\n"
                    "    backtrack(nums, new ArrayList<>(), used, result);\n"
                    "    return result;\n"
                    "}\n"
                    "\n"
                    "private void backtrack(int[] nums, List<Integer> path, boolean[] used, List<List<Integer>> result) {\n"
                    "    if (path.size() == nums.length) { result.add(new ArrayList<>(path)); return; }\n"
                    "    for (int i = 0; i < nums.length; i++) {\n"
                    "        if (used[i]) continue;\n"
                    "        used[i] = true;\n"
                    "        path.add(nums[i]);\n"
                    "        backtrack(nums, path, used, result);\n"
                    "        path.remove(path.size() - 1);\n"
                    "        used[i] = false;\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Backtracking by In-Place Swap",
            "time_complexity": "O(n · n!)",
            "space_complexity": "O(n) recursion (output excluded)",
            "description": (
                "Avoid the `used[]` array by mutating `nums` itself. For position `start`, swap each `i ≥ start` "
                "into `nums[start]`, recurse for `start + 1`, then swap back. When `start == n`, snapshot the "
                "current arrangement into the result. More space-efficient but easier to get the swap-back wrong."
            ),
            "code": {
                "python": (
                    "def permute(nums):\n"
                    "    nums = nums[:]\n"
                    "    n = len(nums)\n"
                    "    result = []\n"
                    "\n"
                    "    def backtrack(start):\n"
                    "        if start == n:\n"
                    "            result.append(nums[:])\n"
                    "            return\n"
                    "        for i in range(start, n):\n"
                    "            nums[start], nums[i] = nums[i], nums[start]\n"
                    "            backtrack(start + 1)\n"
                    "            nums[start], nums[i] = nums[i], nums[start]\n"
                    "\n"
                    "    backtrack(0)\n"
                    "    return result"
                ),
            },
        },
        {
            "title": "Iterative Builder",
            "time_complexity": "O(n · n!)",
            "space_complexity": "O(n · n!)",
            "description": (
                "Build the answer bottom-up. Start with `[[]]`. For each new number, take every existing "
                "permutation and insert the number at every possible position to produce the next generation. "
                "After consuming all n numbers, the list holds n! permutations. Useful when you don't want "
                "recursion at all (e.g., very deep stacks)."
            ),
            "code": {
                "python": (
                    "def permute(nums):\n"
                    "    result = [[]]\n"
                    "    for x in nums:\n"
                    "        next_gen = []\n"
                    "        for p in result:\n"
                    "            for i in range(len(p) + 1):\n"
                    "                next_gen.append(p[:i] + [x] + p[i:])\n"
                    "        result = next_gen\n"
                    "    return result"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Output size is n! — state it. The algorithm can't be sub-n! because you must emit every permutation.",
        "2. Frame as backtracking: at each level pick an unused element, recurse, then undo.",
        "3. Decide the 'unused' bookkeeping: a `used[]` boolean array (clear, O(n) extra) or in-place swap (no extra array, trickier).",
        "4. Snapshot the path on the leaf — you must copy because the same `path` list is mutated as recursion unwinds.",
        "5. Confirm complexity: O(n · n!) — n! leaves, each costing O(n) to copy out.",
        "6. Edge cases: empty input → `[[]]` (the empty permutation), single element → `[[x]]`. Both fall out of the template naturally.",
    ],
    "tips": [
        "Forgetting to copy the path on the leaf is the #1 bug. `result.append(path)` (by reference) leaves you with n! pointers to the same list, which ends up empty.",
        "In the swap variant, swap-back is required even though it 'looks redundant' on the last `i` — without it the array is permuted on the way out and the next sibling call sees the wrong state.",
        "Permutations II (LC 47): inputs may contain duplicates. Sort first, then in the loop skip `i` when `i > 0 and nums[i] == nums[i-1] and not used[i-1]`. Same scaffolding.",
        "Next Permutation (LC 31): an entirely different problem despite the name — it computes the *one* lexicographically next permutation in place. Don't conflate with this one.",
        "If the interviewer asks for a generator (lazy iteration), the backtracking template `yield`s the path naturally and avoids materialising all n! results in memory.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Facebook"],
    "topics": ["Array", "Backtracking"],
    "time_complexity": "O(n · n!)",
    "space_complexity": "O(n · n!)",
}


def REFERENCE(nums):
    n = len(nums)
    result, path, used = [], [], [False] * n

    def backtrack():
        if len(path) == n:
            result.append(path[:])
            return
        for i in range(n):
            if used[i]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack()
            path.pop()
            used[i] = False

    backtrack()
    return result


register(PAYLOAD, REFERENCE)
