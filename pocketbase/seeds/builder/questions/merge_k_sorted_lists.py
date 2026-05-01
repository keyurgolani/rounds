"""Merge k Sorted Lists — Hard. Heap / Divide and Conquer.

LeetCode 23. The k-way merge canonical. Two competing optimal
shapes: a min-heap of (value, list_index, position) where every pop
emits one element of the answer in O(log k); or pairwise divide-and-
conquer that reuses the LC 21 two-list merge in log k rounds. Both
hit O(N log k) total work where N is the sum of all list lengths.

Inputs are encoded as flat arrays per list (rather than ListNode
chains) — same algorithmic content, simpler harness. Two production
gotchas live in the tips: heap tie-breaking on the second tuple slot
(values aren't always comparable) and why naïve 'merge into one
running list' is O(Nk), not O(N log k).
"""
from builder.registry import register
import heapq


PAYLOAD = {
    "title": "Merge k Sorted Lists",
    "difficulty": "Hard",
    "description": (
        "You are given an array of `k` linked lists `lists`, where each linked list is sorted in "
        "ascending order. Merge all the linked lists into one sorted linked list and return its head.\n\n"
        "For this harness, each linked list is encoded as a flat array of values in ascending order; "
        "`lists` is therefore an array of arrays. Return the merged values as a single ascending array.\n\n"
        "**Example 1:**\n"
        "- Input: `lists = [[1,4,5],[1,3,4],[2,6]]`\n"
        "- Output: `[1,1,2,3,4,4,5,6]`\n"
        "- Explanation: The linked lists are `1 -> 4 -> 5`, `1 -> 3 -> 4`, `2 -> 6`. Merging them produces `1 -> 1 -> 2 -> 3 -> 4 -> 4 -> 5 -> 6`.\n\n"
        "**Example 2:**\n"
        "- Input: `lists = []`\n"
        "- Output: `[]`\n\n"
        "**Example 3:**\n"
        "- Input: `lists = [[]]`\n"
        "- Output: `[]`"
    ),
    "hints": [
        "Naïve: concatenate everything and sort. O(N log N) where N is total elements. Correct, but ignores the structure — and the interviewer's whole point.",
        "Min-heap of size k: push the head of every list, then repeatedly pop the smallest and push the *next* element from the same list. Each pop/push is O(log k); N total ops → O(N log k) time, O(k) heap space.",
        "Heap tie-break gotcha: store `(value, list_idx, elem_idx)` (or `(value, list_idx, node)`). The second slot breaks ties so Python's tuple compare never reaches a non-comparable third slot. Without it, `ListNode` comparison raises TypeError on duplicate values.",
        "Divide and conquer: pair up the k lists and merge them with the LC 21 two-list routine. After one round you have k/2 lists, after two rounds k/4, ... ⌈log k⌉ rounds. Each round touches every element once → O(N log k).",
        "Don't 'merge into one running list': merging a length-m list into a length-M accumulator is O(M+m), so total work is m₁ + (m₁+m₂) + (m₁+m₂+m₃) + ... = O(Nk). Same algorithm shape, much worse complexity.",
    ],
    "constraints": [
        "0 <= k <= 10^4",
        "0 <= |lists[i]| <= 500, total elements N <= 10^4",
        "-10^4 <= lists[i][j] <= 10^4 and each `lists[i]` is sorted in non-decreasing order",
    ],
    "starter_code": {
        "python": "def merge_k_sorted(lists):\n    # Your code here\n    pass",
        "javascript": "function mergeKSorted(lists) {\n    // Your code here\n}",
        "java": "public List<Integer> mergeKSorted(List<List<Integer>> lists) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[[1,4,5],[1,3,4],[2,6]], [], [[]]]\n"
            "    for lists in cases:\n"
            "        print(f\"merge_k_sorted({lists}) = {merge_k_sorted(lists)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,4,5],[1,3,4],[2,6]], [], [[]]].forEach(lists =>\n"
            "    console.log(`mergeKSorted =`, mergeKSorted(lists))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.mergeKSorted(List.of(\n"
            "            List.of(1,4,5), List.of(1,3,4), List.of(2,6)\n"
            "        )));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"lists": [[1, 4, 5], [1, 3, 4], [2, 6]]},
         "expected": [1, 1, 2, 3, 4, 4, 5, 6],
         "description": "LeetCode canonical example — three interleaved lists with ties at the head",
         "tags": ["basic"]},
        {"input": {"lists": []}, "expected": [],
         "description": "Zero lists — return empty", "tags": ["edge"]},
        {"input": {"lists": [[]]}, "expected": [],
         "description": "Single empty list — return empty", "tags": ["edge"]},
        {"input": {"lists": [[1, 2, 3, 4, 5]]}, "expected": [1, 2, 3, 4, 5],
         "description": "Single non-empty list — pass-through", "tags": ["edge"]},
        {"input": {"lists": [[], [], [], []]}, "expected": [],
         "description": "Many empty lists — return empty without false starts on the heap",
         "tags": ["edge"]},
        {"input": {"lists": [[5], [3], [1], [4], [2]]},
         "expected": [1, 2, 3, 4, 5],
         "description": "k singleton lists — heap reduces to a sort",
         "tags": ["tricky"]},
        {"input": {"lists": [[1, 1, 1], [1, 1], [1, 1, 1, 1]]},
         "expected": [1, 1, 1, 1, 1, 1, 1, 1, 1],
         "description": "All-same value across all lists — exercises tie-break ordering",
         "tags": ["tricky"]},
        {"input": {"lists": [[], [1, 2, 3], [], [4, 5], []]},
         "expected": [1, 2, 3, 4, 5],
         "description": "Mixed empty and non-empty lists — never push from empty",
         "tags": ["tricky"]},
        {"input": {"lists": [[-10, -5, 0], [-7, -1, 4], [-3, 2, 8]]},
         "expected": [-10, -7, -5, -3, -1, 0, 2, 4, 8],
         "description": "Mixed signs, fully interleaved across three lists",
         "tags": ["basic"]},
        {"input": {"lists": [list(range(0, 30, 3)), list(range(1, 30, 3)), list(range(2, 30, 3))]},
         "expected": list(range(30)),
         "description": "Three arithmetic-progression lists interleaving into 0..29",
         "tags": ["large"]},
        {"input": {"lists": [list(range(i, 1000, 10)) for i in range(10)]},
         "expected": list(range(1000)),
         "description": "k=10 lists totalling 1000 elements — stresses the log k factor",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Min-Heap of List Heads (Optimal)",
            "time_complexity": "O(N log k)",
            "space_complexity": "O(k)",
            "description": (
                "Maintain a min-heap of size at most k holding one (value, list_idx, elem_idx) tuple "
                "per still-non-empty list. Pop the smallest, append its value to the output, then push "
                "the next element from the *same* list (if any). Each of the N pop/push pairs is "
                "O(log k), so total work is O(N log k) and the heap never holds more than k entries.\n\n"
                "The `list_idx` slot in the tuple is load-bearing: it breaks ties so the comparator "
                "never tries to compare two non-comparable third slots (e.g. real `ListNode` objects). "
                "On the array form here, ints are comparable, but keep the slot anyway — it's a habit "
                "that survives the port to real linked lists."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "def merge_k_sorted(lists):\n"
                    "    heap = []\n"
                    "    # Seed with each list's head — skip empty lists so we never pop a phantom.\n"
                    "    for i, lst in enumerate(lists):\n"
                    "        if lst:\n"
                    "            heapq.heappush(heap, (lst[0], i, 0))\n"
                    "    out = []\n"
                    "    while heap:\n"
                    "        val, i, j = heapq.heappop(heap)\n"
                    "        out.append(val)\n"
                    "        if j + 1 < len(lists[i]):\n"
                    "            heapq.heappush(heap, (lists[i][j + 1], i, j + 1))\n"
                    "    return out"
                ),
                "javascript": (
                    "function mergeKSorted(lists) {\n"
                    "    // Tiny binary min-heap on [val, listIdx, elemIdx].\n"
                    "    const heap = [];\n"
                    "    const cmp = (a, b) => a[0] - b[0] || a[1] - b[1];\n"
                    "    const up = (i) => {\n"
                    "        while (i > 0) {\n"
                    "            const p = (i - 1) >> 1;\n"
                    "            if (cmp(heap[i], heap[p]) < 0) { [heap[i], heap[p]] = [heap[p], heap[i]]; i = p; }\n"
                    "            else break;\n"
                    "        }\n"
                    "    };\n"
                    "    const down = (i) => {\n"
                    "        const n = heap.length;\n"
                    "        while (true) {\n"
                    "            const l = 2 * i + 1, r = l + 1; let s = i;\n"
                    "            if (l < n && cmp(heap[l], heap[s]) < 0) s = l;\n"
                    "            if (r < n && cmp(heap[r], heap[s]) < 0) s = r;\n"
                    "            if (s === i) break;\n"
                    "            [heap[i], heap[s]] = [heap[s], heap[i]]; i = s;\n"
                    "        }\n"
                    "    };\n"
                    "    const push = (x) => { heap.push(x); up(heap.length - 1); };\n"
                    "    const pop = () => {\n"
                    "        const top = heap[0], last = heap.pop();\n"
                    "        if (heap.length) { heap[0] = last; down(0); }\n"
                    "        return top;\n"
                    "    };\n"
                    "    for (let i = 0; i < lists.length; i++) {\n"
                    "        if (lists[i].length) push([lists[i][0], i, 0]);\n"
                    "    }\n"
                    "    const out = [];\n"
                    "    while (heap.length) {\n"
                    "        const [val, i, j] = pop();\n"
                    "        out.push(val);\n"
                    "        if (j + 1 < lists[i].length) push([lists[i][j + 1], i, j + 1]);\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public List<Integer> mergeKSorted(List<List<Integer>> lists) {\n"
                    "    // (val, listIdx, elemIdx); list index breaks ties.\n"
                    "    PriorityQueue<int[]> pq = new PriorityQueue<>(\n"
                    "        (a, b) -> a[0] != b[0] ? a[0] - b[0] : a[1] - b[1]\n"
                    "    );\n"
                    "    for (int i = 0; i < lists.size(); i++) {\n"
                    "        if (!lists.get(i).isEmpty()) pq.offer(new int[]{lists.get(i).get(0), i, 0});\n"
                    "    }\n"
                    "    List<Integer> out = new ArrayList<>();\n"
                    "    while (!pq.isEmpty()) {\n"
                    "        int[] top = pq.poll();\n"
                    "        int val = top[0], i = top[1], j = top[2];\n"
                    "        out.add(val);\n"
                    "        if (j + 1 < lists.get(i).size()) pq.offer(new int[]{lists.get(i).get(j + 1), i, j + 1});\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Divide and Conquer (Pairwise Merge)",
            "time_complexity": "O(N log k)",
            "space_complexity": "O(log k) recursion stack (or O(1) iterative)",
            "description": (
                "Reuse the LC 21 two-list merge as a building block. Pair up the k lists and merge each "
                "pair, halving the count per round. After ⌈log k⌉ rounds you have one list. Each round "
                "touches every element exactly once — total work O(N log k), same as the heap, but with "
                "only O(log k) extra space (or O(1) iteratively) since the heap is gone.\n\n"
                "Why this beats the naïve 'fold left' merge into a single accumulator: that approach "
                "rescans the growing accumulator on every pair, costing O(Nk). Pairing up keeps each "
                "element at depth log k in the merge tree."
            ),
            "code": {
                "python": (
                    "def merge_k_sorted(lists):\n"
                    "    if not lists:\n"
                    "        return []\n\n"
                    "    def merge_two(a, b):\n"
                    "        out, i, j = [], 0, 0\n"
                    "        while i < len(a) and j < len(b):\n"
                    "            if a[i] <= b[j]:\n"
                    "                out.append(a[i]); i += 1\n"
                    "            else:\n"
                    "                out.append(b[j]); j += 1\n"
                    "        out.extend(a[i:])\n"
                    "        out.extend(b[j:])\n"
                    "        return out\n\n"
                    "    # Iterative pairing: stride 1, then 2, then 4, ... — log k rounds.\n"
                    "    step = 1\n"
                    "    n = len(lists)\n"
                    "    lists = [list(x) for x in lists]\n"
                    "    while step < n:\n"
                    "        for i in range(0, n - step, 2 * step):\n"
                    "            lists[i] = merge_two(lists[i], lists[i + step])\n"
                    "        step *= 2\n"
                    "    return lists[0]"
                ),
                "javascript": (
                    "function mergeKSorted(lists) {\n"
                    "    if (lists.length === 0) return [];\n"
                    "    const mergeTwo = (a, b) => {\n"
                    "        const out = []; let i = 0, j = 0;\n"
                    "        while (i < a.length && j < b.length) {\n"
                    "            if (a[i] <= b[j]) out.push(a[i++]); else out.push(b[j++]);\n"
                    "        }\n"
                    "        while (i < a.length) out.push(a[i++]);\n"
                    "        while (j < b.length) out.push(b[j++]);\n"
                    "        return out;\n"
                    "    };\n"
                    "    let step = 1, n = lists.length;\n"
                    "    lists = lists.map(l => l.slice());\n"
                    "    while (step < n) {\n"
                    "        for (let i = 0; i + step < n; i += 2 * step) {\n"
                    "            lists[i] = mergeTwo(lists[i], lists[i + step]);\n"
                    "        }\n"
                    "        step *= 2;\n"
                    "    }\n"
                    "    return lists[0];\n"
                    "}"
                ),
            },
        },
        {
            "title": "Concatenate-and-Sort (Baseline)",
            "time_complexity": "O(N log N)",
            "space_complexity": "O(N)",
            "description": (
                "Flatten everything and sort. Worth saying out loud — it shows you noticed the trivial "
                "answer — but it ignores the per-list sortedness. log N is bigger than log k whenever "
                "any list has more than one element on average, so the structure-aware solutions win."
            ),
            "code": {
                "python": (
                    "def merge_k_sorted(lists):\n"
                    "    out = []\n"
                    "    for lst in lists:\n"
                    "        out.extend(lst)\n"
                    "    out.sort()\n"
                    "    return out"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Start with the brute force: concatenate all lists and sort. O(N log N) where N is total elements. State it; it's the floor, not the answer.",
        "2. Notice you're throwing away the per-list sortedness. The next-smallest element of the merged answer is always one of the k current heads — so the question reduces to 'find min among k changing values', repeated N times.",
        "3. 'Min among k, supporting replace': that's a heap. Seed with one head per non-empty list. Each pop emits one answer element and pushes its successor. Heap size stays ≤ k. N ops × log k each → O(N log k).",
        "4. Tie-break the heap on `(value, list_idx, ...)` so two equal values never force the comparator to look at the third slot. On real linked lists this matters — `ListNode` isn't comparable; without `list_idx` you'd hit a TypeError exactly when two lists have a duplicate value.",
        "5. Divide-and-conquer is the same complexity, different shape: pair up lists, merge each pair via the LC 21 routine, halve. log k rounds, every element touched once per round, O(N log k) total. Less code than the heap if you already have `merge_two`. No heap → O(log k) or O(1) extra space.",
        "6. Edge cases line up cleanly: `lists=[]` → heap never seeded, return []. `lists=[[]]` → empty list filtered at seeding, same outcome. All-empty lists → never push a phantom. Singleton lists → heap reduces to a sort. All-same value → tie-break slot saves you.",
        "7. Watch the failure mode: 'merge into one running list' (fold-left). Each merge is O(M+m), totalling O(Nk). Right answer, wrong complexity — interviewers ask for it specifically.",
    ],
    "tips": [
        "Always tuple-tie-break heap entries on a unique secondary key. `(val, list_idx, ...)` works because list indices are unique. Skipping it bites you the moment two list heads tie *and* the third tuple slot isn't comparable.",
        "Skip empty lists at seed time. Pushing a sentinel like `(inf, i, 0)` 'works' but adds k log k of dead weight and a special case at pop time.",
        "Iterative pairwise merge beats recursive on Python for large k — recursion limit is real, and the iterative stride-doubling form is no harder to write.",
        "On real linked lists, both optimal solutions splice nodes in place: the heap holds `(val, idx, node)`, the divide-and-conquer rewires `next` pointers. O(1) extra beyond the heap/recursion.",
        "Direct prerequisite — Merge Two Sorted Lists (LC 21). The divide-and-conquer solution literally calls it as a subroutine; getting that one airtight pays for itself here.",
        "The heap and divide-and-conquer are both O(N log k). When does each win in practice? Heap when k is small and lists are wildly uneven (you do less work per pop). D&C when k is large and lists are balanced (cache-friendly contiguous merges, no heap overhead).",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Facebook", "Apple", "Bloomberg", "Uber"],
    "topics": ["Linked List", "Heap (Priority Queue)", "Divide and Conquer", "Merge Sort"],
    "time_complexity": "O(N log k)",
    "space_complexity": "O(k) for the heap, O(N) for the output",
}


def REFERENCE(lists):
    heap = []
    for i, lst in enumerate(lists):
        if lst:
            heapq.heappush(heap, (lst[0], i, 0))
    out = []
    while heap:
        val, i, j = heapq.heappop(heap)
        out.append(val)
        if j + 1 < len(lists[i]):
            heapq.heappush(heap, (lists[i][j + 1], i, j + 1))
    return out


register(PAYLOAD, REFERENCE)
