"""Merge Two Sorted Lists — Easy. Linked List / Two Pointers.

LeetCode 21. The canonical 'merge two sorted sequences' problem,
phrased on linked lists. Two pointers walk both inputs and splice
nodes onto a dummy-head sentinel to dodge the empty-output edge case.
The same shape underlies merge sort's combine step, the k-way merge
(LC 23), and the merge-sorted-arrays family.

Inputs are encoded here as flat Python lists of values rather than
ListNode objects — keeps the harness clean while preserving the
algorithmic content. A 'real linked list' implementation note lives
in the tips for splicing nodes in O(1) extra space.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Merge Two Sorted Lists",
    "difficulty": "Easy",
    "description": (
        "You are given the heads of two sorted linked lists `l1` and `l2`. Merge the two lists into a "
        "single sorted list by splicing together the nodes of the first two lists. Return the merged "
        "list.\n\n"
        "For this harness, the lists are encoded as flat arrays of values in ascending order; you should "
        "return the merged values as a single ascending array.\n\n"
        "**Example 1:**\n"
        "- Input: `l1 = [1,2,4]`, `l2 = [1,3,4]`\n"
        "- Output: `[1,1,2,3,4,4]`\n\n"
        "**Example 2:**\n"
        "- Input: `l1 = []`, `l2 = []`\n"
        "- Output: `[]`\n\n"
        "**Example 3:**\n"
        "- Input: `l1 = []`, `l2 = [0]`\n"
        "- Output: `[0]`"
    ),
    "hints": [
        "Two pointers, one per list. Advance whichever head is smaller; tie goes to either side (the result is still sorted).",
        "Use a dummy-head sentinel: build the result behind `dummy.next` so you don't special-case 'is the output empty yet?' on every append.",
        "When one input runs out, the *other* tail is already sorted — link/extend it wholesale instead of looping one node at a time.",
        "Don't sort the concatenation. That's O((n+m) log(n+m)) and ignores the structure you were handed.",
        "On real linked lists you can splice nodes in place: O(1) extra space (the merged 'list' is just a re-pointed chain of the original nodes).",
    ],
    "constraints": [
        "0 <= |l1|, |l2| <= 50",
        "-100 <= node value <= 100",
        "both `l1` and `l2` are sorted in non-decreasing order",
    ],
    "starter_code": {
        "python": "def merge_two_sorted(l1, l2):\n    # Your code here\n    pass",
        "javascript": "function mergeTwoSorted(l1, l2) {\n    // Your code here\n}",
        "java": "public List<Integer> mergeTwoSorted(List<Integer> l1, List<Integer> l2) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([1,2,4], [1,3,4]), ([], []), ([], [0])]\n"
            "    for l1, l2 in cases:\n"
            "        print(f\"merge_two_sorted({l1}, {l2}) = {merge_two_sorted(l1, l2)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,2,4],[1,3,4]], [[],[]], [[],[0]]].forEach(([l1, l2]) =>\n"
            "    console.log(`mergeTwoSorted =`, mergeTwoSorted(l1, l2))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.mergeTwoSorted(List.of(1,2,4), List.of(1,3,4)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"l1": [1, 2, 4], "l2": [1, 3, 4]},
         "expected": [1, 1, 2, 3, 4, 4],
         "description": "LeetCode canonical example — interleaved with a tied head",
         "tags": ["basic"]},
        {"input": {"l1": [], "l2": []}, "expected": [],
         "description": "Both empty — return empty", "tags": ["edge"]},
        {"input": {"l1": [], "l2": [0]}, "expected": [0],
         "description": "First empty — return the other unchanged", "tags": ["edge"]},
        {"input": {"l1": [0], "l2": []}, "expected": [0],
         "description": "Second empty — return the other unchanged", "tags": ["edge"]},
        {"input": {"l1": [1, 2, 3], "l2": [4, 5, 6]},
         "expected": [1, 2, 3, 4, 5, 6],
         "description": "Disjoint ranges — l1 fully precedes l2", "tags": ["tricky"]},
        {"input": {"l1": [4, 5, 6], "l2": [1, 2, 3]},
         "expected": [1, 2, 3, 4, 5, 6],
         "description": "Disjoint ranges — l2 fully precedes l1", "tags": ["tricky"]},
        {"input": {"l1": [1, 1, 1], "l2": [1, 1]},
         "expected": [1, 1, 1, 1, 1],
         "description": "All duplicates across both lists", "tags": ["tricky"]},
        {"input": {"l1": [-10, -5, 0, 5], "l2": [-7, -1, 2, 8]},
         "expected": [-10, -7, -5, -1, 0, 2, 5, 8],
         "description": "Mixed signs, fully interleaved", "tags": ["basic"]},
        {"input": {"l1": list(range(0, 50, 2)), "l2": list(range(1, 50, 2))},
         "expected": list(range(50)),
         "description": "Even-vs-odd interleave at the constraint upper bound",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Iterative with Dummy Head (Optimal)",
            "time_complexity": "O(n + m)",
            "space_complexity": "O(1) extra (excluding the O(n+m) output)",
            "description": (
                "Two pointers, `i` into `l1` and `j` into `l2`. A dummy-head sentinel removes the "
                "'is the output empty?' branch on every append — you always have a `tail` to attach to. "
                "Advance whichever pointer points to the smaller value; on a tie either side is correct "
                "(the merged sequence is still sorted). When one input is exhausted, append the rest of "
                "the other in one shot. On real linked lists this rewires nodes in place; here we copy "
                "values into an output array, but the output itself is unavoidable O(n+m) — the "
                "*algorithmic* extra space is O(1)."
            ),
            "code": {
                "python": (
                    "def merge_two_sorted(l1, l2):\n"
                    "    # Dummy head sentinel: the 'real' result starts at out[1:].\n"
                    "    # Equivalent to dummy.next on a real linked list.\n"
                    "    out = []\n"
                    "    i = j = 0\n"
                    "    while i < len(l1) and j < len(l2):\n"
                    "        if l1[i] <= l2[j]:\n"
                    "            out.append(l1[i]); i += 1\n"
                    "        else:\n"
                    "            out.append(l2[j]); j += 1\n"
                    "    # Drain the non-empty tail wholesale.\n"
                    "    out.extend(l1[i:])\n"
                    "    out.extend(l2[j:])\n"
                    "    return out"
                ),
                "javascript": (
                    "function mergeTwoSorted(l1, l2) {\n"
                    "    const out = [];\n"
                    "    let i = 0, j = 0;\n"
                    "    while (i < l1.length && j < l2.length) {\n"
                    "        if (l1[i] <= l2[j]) out.push(l1[i++]);\n"
                    "        else out.push(l2[j++]);\n"
                    "    }\n"
                    "    while (i < l1.length) out.push(l1[i++]);\n"
                    "    while (j < l2.length) out.push(l2[j++]);\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public List<Integer> mergeTwoSorted(List<Integer> l1, List<Integer> l2) {\n"
                    "    List<Integer> out = new ArrayList<>(l1.size() + l2.size());\n"
                    "    int i = 0, j = 0;\n"
                    "    while (i < l1.size() && j < l2.size()) {\n"
                    "        if (l1.get(i) <= l2.get(j)) out.add(l1.get(i++));\n"
                    "        else out.add(l2.get(j++));\n"
                    "    }\n"
                    "    while (i < l1.size()) out.add(l1.get(i++));\n"
                    "    while (j < l2.size()) out.add(l2.get(j++));\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Recursive",
            "time_complexity": "O(n + m)",
            "space_complexity": "O(n + m) call stack",
            "description": (
                "Pick the smaller head, then recurse on the rest. Elegant and matches the natural "
                "linked-list framing — the recursion mirrors how you'd splice nodes by hand. Watch the "
                "stack depth: with n+m up to ~10^4 it can blow Python's default recursion limit, so on "
                "production-sized inputs prefer the iterative form."
            ),
            "code": {
                "python": (
                    "def merge_two_sorted(l1, l2):\n"
                    "    if not l1: return list(l2)\n"
                    "    if not l2: return list(l1)\n"
                    "    if l1[0] <= l2[0]:\n"
                    "        return [l1[0]] + merge_two_sorted(l1[1:], l2)\n"
                    "    return [l2[0]] + merge_two_sorted(l1, l2[1:])"
                ),
                "javascript": (
                    "function mergeTwoSorted(l1, l2) {\n"
                    "    if (l1.length === 0) return [...l2];\n"
                    "    if (l2.length === 0) return [...l1];\n"
                    "    if (l1[0] <= l2[0]) return [l1[0], ...mergeTwoSorted(l1.slice(1), l2)];\n"
                    "    return [l2[0], ...mergeTwoSorted(l1, l2.slice(1))];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Concatenate-and-Sort (Baseline)",
            "time_complexity": "O((n + m) log(n + m))",
            "space_complexity": "O(n + m)",
            "description": (
                "Throw both lists into one buffer and sort. Worth mentioning so the interviewer hears "
                "you noticed it; never submit it — it ignores the sortedness you were given."
            ),
            "code": {
                "python": (
                    "def merge_two_sorted(l1, l2):\n"
                    "    return sorted(l1 + l2)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Two sorted inputs → reach for two-pointer merge, not sort. The sort baseline is O((n+m) log(n+m)); the merge is O(n+m).",
        "2. Set up a dummy-head sentinel. On a real linked list this is `dummy = ListNode(0); tail = dummy`; on the array form here, the empty `out` array plays the same role. The point is: you always have something to append to, so no `if result is None` branch on every step.",
        "3. Walk both pointers. While both are in range, append the smaller head and advance that pointer. Use `<=` (ties to `l1`) for stability if you ever care which list a tied value came from — for plain integers it doesn't matter.",
        "4. When the inner loop exits, exactly one list still has unconsumed elements. That tail is already sorted *and* already past every element you've emitted, so splice/extend it wholesale instead of looping one element at a time.",
        "5. Edge cases fall out: empty + empty → loop never runs, both extends do nothing, return empty. Empty + non-empty → loop never runs, one extend dumps the whole survivor. Disjoint ranges → loop fully drains the smaller side, then the extend handles the rest. Total dups → either branch fires; output length = n + m.",
        "6. On a real linked list, return `dummy.next`. The trick is purely about avoiding a special-case for the very first node — every other 'append' is just `tail = tail.next`.",
    ],
    "tips": [
        "Dummy head removes a whole class of off-by-one mistakes. Always reach for it on linked-list construction problems.",
        "On real linked lists, splice nodes in place — set `tail.next = whichever_head` and advance `tail`. That's O(1) extra space; you're rewiring, not allocating.",
        "Don't write `out = out + [x]` inside the loop. That's O(n²). Use `append` (Python) / `push` (JS) — amortised O(1).",
        "When draining the tail, `extend(l1[i:])` is one shot. Avoid a per-element `while` if the language gives you a slice/extend.",
        "Direct follow-up — Merge K Sorted Lists (LC 23, see merging_data_streams): heap of k heads, pop-and-replace. O(N log k) total. Or pairwise-merge with the k=2 routine in log k rounds — same complexity, simpler code.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Bloomberg", "LinkedIn"],
    "topics": ["Linked List", "Two Pointers", "Merge"],
    "time_complexity": "O(n + m)",
    "space_complexity": "O(1) extra (O(n + m) for the output)",
}


def REFERENCE(l1, l2):
    out = []
    i = j = 0
    while i < len(l1) and j < len(l2):
        if l1[i] <= l2[j]:
            out.append(l1[i])
            i += 1
        else:
            out.append(l2[j])
            j += 1
    out.extend(l1[i:])
    out.extend(l2[j:])
    return out


register(PAYLOAD, REFERENCE)
