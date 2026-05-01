"""Combination Sum — Medium. Backtracking.

The canonical 'unbounded knapsack as combinations' question. The trick
that separates a clean solution from a duplicate-spewing mess is the
*start index*: each recursive call picks from `candidates[start:]`,
which forces non-decreasing picks and gives every combination exactly
one canonical path. Reuse is free — you recurse with the same index,
not `start + 1`. Mastering this template unlocks Combination Sum II,
Combination Sum III, Subsets, Subsets II, and Palindrome Partitioning.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Combination Sum",
    "difficulty": "Medium",
    "description": (
        "Given an array of **distinct** integers `candidates` and a target integer `target`, return a list "
        "of all **unique combinations** of `candidates` where the chosen numbers sum to `target`. You may "
        "return the combinations in any order.\n\n"
        "The **same number** may be chosen from `candidates` an **unlimited number of times**. Two "
        "combinations are unique if the frequency of at least one of the chosen numbers is different.\n\n"
        "It is guaranteed that the number of unique combinations that sum up to `target` is less than 150 "
        "for the given input.\n\n"
        "**Example 1:**\n"
        "- Input: `candidates = [2,3,6,7], target = 7`\n"
        "- Output: `[[2,2,3],[7]]`\n"
        "- Explanation: 2 + 2 + 3 = 7 (2 used twice). 7 = 7. These are the only two combinations.\n\n"
        "**Example 2:**\n"
        "- Input: `candidates = [2,3,5], target = 8`\n"
        "- Output: `[[2,2,2,2],[2,3,3],[3,5]]`\n\n"
        "**Example 3:**\n"
        "- Input: `candidates = [2], target = 1`\n"
        "- Output: `[]`"
    ),
    "hints": [
        "Backtracking: at each step decide 'take candidate[i] (and stay at i, since reuse is allowed)' or 'skip to i+1'.",
        "To avoid duplicate combinations like [2,3,2] vs [2,2,3], pass a `start` index so picks are non-decreasing in candidate order.",
        "Prune aggressively: if `target - candidate[i] < 0`, you can break (after sorting) — every later candidate will also overshoot.",
        "Sorting `candidates` first makes the prune cleaner but is not strictly required for correctness.",
        "Think of it as unbounded knapsack: the 'count' of each candidate is unbounded, the 'weight' is its value, and we want all subsets that hit the target exactly.",
    ],
    "constraints": [
        "1 <= candidates.length <= 30",
        "2 <= candidates[i] <= 40",
        "All elements of candidates are distinct.",
        "1 <= target <= 40",
    ],
    "starter_code": {
        "python": "def combination_sum(candidates, target):\n    # Your code here\n    pass",
        "javascript": "function combinationSum(candidates, target) {\n    // Your code here\n}",
        "java": "public List<List<Integer>> combinationSum(int[] candidates, int target) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([2,3,6,7], 7), ([2,3,5], 8), ([2], 1)]\n"
            "    for cands, t in cases:\n"
            "        print(f\"combination_sum({cands}, {t}) = {combination_sum(cands, t)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[2,3,6,7], 7], [[2,3,5], 8], [[2], 1]].forEach(([c, t]) =>\n"
            "    console.log(`combinationSum =`, combinationSum(c, t))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.combinationSum(new int[]{2,3,6,7}, 7));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"candidates": [2, 3, 6, 7], "target": 7},
         "expected": {"$match": "unordered_deep", "value": [[2, 2, 3], [7]]},
         "description": "Classic — 2+2+3 and the singleton 7", "tags": ["basic"]},
        {"input": {"candidates": [2, 3, 5], "target": 8},
         "expected": {"$match": "unordered_deep", "value": [[2, 2, 2, 2], [2, 3, 3], [3, 5]]},
         "description": "Three combinations including a four-element one", "tags": ["basic"]},
        {"input": {"candidates": [2], "target": 1},
         "expected": [],
         "description": "Target smaller than the only candidate — no combinations", "tags": ["edge"]},
        {"input": {"candidates": [1], "target": 1},
         "expected": {"$match": "unordered_deep", "value": [[1]]},
         "description": "Trivial single-element hit", "tags": ["edge"]},
        {"input": {"candidates": [1], "target": 2},
         "expected": {"$match": "unordered_deep", "value": [[1, 1]]},
         "description": "Reuse — only way is two 1s", "tags": ["edge"]},
        {"input": {"candidates": [8, 7, 4, 3], "target": 11},
         "expected": {"$match": "unordered_deep", "value": [[3, 4, 4], [3, 8], [4, 7]]},
         "description": "Unsorted input — output combinations still canonicalised internally", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Backtracking with Start Index (Optimal)",
            "time_complexity": "O(N^(T/M))",
            "space_complexity": "O(T/M)",
            "description": (
                "Recurse with a `start` index. At each call, iterate `i` from `start` to the end: append "
                "`candidates[i]`, recurse with the same `i` (because reuse is allowed) and the remaining "
                "target reduced by `candidates[i]`, then pop. The non-decreasing index guarantees every "
                "combination is generated exactly once in canonical (sorted-by-original-position) order. "
                "N is the number of candidates, T is the target, M is the smallest candidate."
            ),
            "code": {
                "python": (
                    "def combination_sum(candidates, target):\n"
                    "    candidates = sorted(candidates)\n"
                    "    result = []\n"
                    "    path = []\n"
                    "\n"
                    "    def backtrack(start, remaining):\n"
                    "        if remaining == 0:\n"
                    "            result.append(path[:])\n"
                    "            return\n"
                    "        for i in range(start, len(candidates)):\n"
                    "            if candidates[i] > remaining:\n"
                    "                break  # sorted — every later candidate overshoots too\n"
                    "            path.append(candidates[i])\n"
                    "            backtrack(i, remaining - candidates[i])  # reuse → stay at i\n"
                    "            path.pop()\n"
                    "\n"
                    "    backtrack(0, target)\n"
                    "    return result"
                ),
                "javascript": (
                    "function combinationSum(candidates, target) {\n"
                    "    candidates = [...candidates].sort((a, b) => a - b);\n"
                    "    const result = [], path = [];\n"
                    "    const backtrack = (start, remaining) => {\n"
                    "        if (remaining === 0) { result.push([...path]); return; }\n"
                    "        for (let i = start; i < candidates.length; i++) {\n"
                    "            if (candidates[i] > remaining) break;\n"
                    "            path.push(candidates[i]);\n"
                    "            backtrack(i, remaining - candidates[i]);\n"
                    "            path.pop();\n"
                    "        }\n"
                    "    };\n"
                    "    backtrack(0, target);\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public List<List<Integer>> combinationSum(int[] candidates, int target) {\n"
                    "    Arrays.sort(candidates);\n"
                    "    List<List<Integer>> result = new ArrayList<>();\n"
                    "    backtrack(candidates, target, 0, new ArrayList<>(), result);\n"
                    "    return result;\n"
                    "}\n"
                    "private void backtrack(int[] c, int remaining, int start, List<Integer> path, List<List<Integer>> result) {\n"
                    "    if (remaining == 0) { result.add(new ArrayList<>(path)); return; }\n"
                    "    for (int i = start; i < c.length; i++) {\n"
                    "        if (c[i] > remaining) break;\n"
                    "        path.add(c[i]);\n"
                    "        backtrack(c, remaining - c[i], i, path, result);\n"
                    "        path.remove(path.size() - 1);\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "DP — List of Combinations per Subtarget",
            "time_complexity": "O(N · T · K)",
            "space_complexity": "O(T · K)",
            "description": (
                "Build `dp[t]` = list of all unique combinations summing to `t`. Iterate `t` from 1 to "
                "`target`; for each candidate `c <= t`, extend every combination in `dp[t - c]` by appending "
                "`c` — but only if `c >= last element of that combination` (canonical sorted form, which "
                "dedupes). K is the average number of combinations per subtarget. Slower in practice than "
                "backtracking with the prune, but a useful framing if the interviewer steers DP."
            ),
            "code": {
                "python": (
                    "def combination_sum(candidates, target):\n"
                    "    candidates = sorted(candidates)\n"
                    "    dp = [[] for _ in range(target + 1)]\n"
                    "    dp[0] = [[]]\n"
                    "    for t in range(1, target + 1):\n"
                    "        for c in candidates:\n"
                    "            if c > t:\n"
                    "                break\n"
                    "            for prev in dp[t - c]:\n"
                    "                if not prev or prev[-1] <= c:  # canonical (non-decreasing) form\n"
                    "                    dp[t].append(prev + [c])\n"
                    "    return dp[target]"
                ),
            },
        },
        {
            "title": "DP — Count of Ways (Variant)",
            "time_complexity": "O(N · T)",
            "space_complexity": "O(T)",
            "description": (
                "If the interviewer only asks for the *number* of combinations (not the combinations "
                "themselves), this is the classic unbounded-knapsack count. Outer loop over candidates, "
                "inner loop over `t`: `dp[t] += dp[t - c]`. Listed for completeness — the actual problem "
                "asks for the lists, so this is a 'follow-up' framing."
            ),
            "code": {
                "python": (
                    "def combination_sum_count(candidates, target):\n"
                    "    dp = [0] * (target + 1)\n"
                    "    dp[0] = 1\n"
                    "    for c in candidates:           # outer over candidates → counts combinations, not permutations\n"
                    "        for t in range(c, target + 1):\n"
                    "            dp[t] += dp[t - c]\n"
                    "    return dp[target]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute force: generate every multiset of candidates up to size `target / min(candidates)`, sum each, keep those that hit the target. Exponential and full of duplicates — unworkable.",
        "2. The duplicate problem: a naive recursion that picks any candidate at each step will produce [2,2,3], [2,3,2], [3,2,2] — all the same combination. We need a *canonical* generation order.",
        "3. The start-index trick: pass an index `start`; the recursive call may only pick candidates at positions `>= start`. This forces every combination to be generated in non-decreasing-index order, so each multiset has exactly one path.",
        "4. Reuse is allowed: when we pick `candidates[i]`, we recurse with `start = i` (not `i + 1`). That lets us pick the same candidate again on the next level. Combination Sum II flips this to `i + 1`.",
        "5. Pruning: sort `candidates` first. Then in the loop, if `candidates[i] > remaining`, break — every later candidate is at least as large, so they all overshoot too. This prune is what makes the backtracking fast in practice.",
        "6. Edge cases: target 0 → one empty combination [[]]; target smaller than the smallest candidate → []; single candidate dividing target → one combination of repeats; single candidate not dividing target → [].",
    ],
    "tips": [
        "The start-index pattern is a *family*. Memorise the template — it powers Subsets, Subsets II, Combination Sum I/II/III, Palindrome Partitioning, and more.",
        "Combination Sum II (LC 40): each candidate may be used **at most once**, and the input may contain duplicates. Two changes: recurse with `i + 1` (no reuse), and `if i > start and c[i] == c[i-1]: continue` to skip duplicate *siblings* at the same depth.",
        "Combination Sum III (LC 216): use exactly **k** numbers from 1..9 summing to `target`. Same template, candidates fixed to `range(1, 10)`, recurse with `i + 1`, prune when `len(path) > k`.",
        "Combination Sum IV (LC 377) is a misnomer — it asks for the *count of permutations*, not combinations. The DP swaps loop order: outer over `t`, inner over candidates. Different problem entirely.",
        "If the interviewer asks for the *number* of combinations only, do not enumerate — use the count DP (O(N·T) time, O(T) space). Enumerating is exponential in output size.",
    ],
    "companies": ["Amazon", "Apple", "Bloomberg"],
    "topics": ["Array", "Backtracking"],
    "time_complexity": "O(N^(T/M))",
    "space_complexity": "O(T/M)",
}


def REFERENCE(candidates, target):
    candidates = sorted(candidates)
    result = []
    path = []

    def backtrack(start, remaining):
        if remaining == 0:
            result.append(path[:])
            return
        for i in range(start, len(candidates)):
            if candidates[i] > remaining:
                break
            path.append(candidates[i])
            backtrack(i, remaining - candidates[i])
            path.pop()

    backtrack(0, target)
    return result


register(PAYLOAD, REFERENCE)
