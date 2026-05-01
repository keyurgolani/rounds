"""Sorting Iterators (K-way Merge) — Medium. Heap.

Given k sorted iterators, produce a single sorted iterator across all
of them. The textbook k-way merge — same machinery as merging k sorted
lists or k sorted streams from external storage."""
from builder.registry import register


PAYLOAD = {
    "title": "Sorting Iterators (K-way Merge)",
    "difficulty": "Medium",
    "description": (
        "Given a list of `k` sorted lists (each in ascending order), return a single list containing every "
        "element across all of them in **ascending order**.\n\n"
        "The interviewer's framing is iterator-based: build a `SortingIterator` that exposes `next()` and "
        "`hasNext()` over `k` input iterators. Conceptually it's the same problem — at any moment you need "
        "the smallest unconsumed value across all `k` sources.\n\n"
        "**Example:**\n"
        "- Input: `lists = [[1,7,10],[2,3,11],[4,5,9]]`\n"
        "- Output: `[1,2,3,4,5,7,9,10,11]`\n\n"
        "**Follow-up:** What if the inputs are infinite streams?"
    ),
    "hints": [
        "Brute force: concatenate everything, sort. O(N log N) where N is the total element count. Throws away the per-list ordering.",
        "Pairwise merge: merge two lists at a time. O(N · k) — slow for large k.",
        "Min-heap of (value, list_index, element_index): pop the smallest, push the next from the same list. O(N log k). This is the canonical answer.",
        "For infinite streams, the heap approach still works — initialise with one element per stream, refill on pop.",
        "Edge cases: empty list of lists, some inner lists empty, duplicate values across lists, k = 1.",
    ],
    "constraints": [
        "0 <= k <= 10⁴",
        "0 <= total elements <= 10⁵",
        "Each inner list is sorted ascending",
    ],
    "starter_code": {
        "python": "def merge_k_sorted(lists):\n    # Your code here\n    pass",
        "javascript": "function mergeKSorted(lists) {\n    // Your code here\n}",
        "java": "public int[] mergeKSorted(int[][] lists) {\n    // Your code here\n    return new int[]{};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        [[1,7,10],[2,3,11],[4,5,9]],\n"
            "        [[],[1,2],[]],\n"
            "        [],\n"
            "    ]\n"
            "    for c in cases:\n"
            "        print(f\"merge_k_sorted({c}) = {merge_k_sorted(c)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,7,10],[2,3,11]], [[],[1]]].forEach(c =>\n"
            "    console.log(`mergeKSorted =`, mergeKSorted(c))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] in = {{1,7,10},{2,3,11},{4,5,9}};\n"
            "        System.out.println(Arrays.toString(s.mergeKSorted(in)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"lists": [[1, 7, 10], [2, 3, 11], [4, 5, 9]]},
         "expected": [1, 2, 3, 4, 5, 7, 9, 10, 11],
         "description": "Three lists, fully interleaved", "tags": ["basic"]},
        {"input": {"lists": [[], [1, 2], []]}, "expected": [1, 2],
         "description": "Mostly empty inputs", "tags": ["edge"]},
        {"input": {"lists": []}, "expected": [],
         "description": "No lists at all", "tags": ["edge"]},
        {"input": {"lists": [[1, 1, 1], [1, 1]]}, "expected": [1, 1, 1, 1, 1],
         "description": "All duplicates across lists", "tags": ["edge"]},
        {"input": {"lists": [[5]]}, "expected": [5],
         "description": "Single list, single element", "tags": ["edge"]},
        {"input": {"lists": [[-3, 0, 4], [-5, 2]]}, "expected": [-5, -3, 0, 2, 4],
         "description": "Negative values across lists", "tags": ["basic"]},
        {"input": {"lists": [list(range(0, 1000, 2)), list(range(1, 1000, 2))]},
         "expected": list(range(1000)),
         "description": "Two large interleaved lists (evens + odds)", "tags": ["large"]},
        {"input": {"lists": [[i] for i in range(100)]}, "expected": list(range(100)),
         "description": "100 single-element lists — k = 100", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Min-Heap K-way Merge (Optimal)",
            "time_complexity": "O(N log k)",
            "space_complexity": "O(k)",
            "description": (
                "Initialise a min-heap with the first element of each non-empty list as `(value, list_idx, "
                "elem_idx)`. Pop the smallest, append it, and push the next element from the same list. "
                "Repeat until the heap is empty. Memory is bounded by k regardless of total size — works for "
                "infinite streams too."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "def merge_k_sorted(lists):\n"
                    "    heap = []\n"
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
                    "// Minimal min-heap inlined to avoid dependencies.\n"
                    "function mergeKSorted(lists) {\n"
                    "    const heap = [];\n"
                    "    const swap = (i, j) => { [heap[i], heap[j]] = [heap[j], heap[i]]; };\n"
                    "    const up = i => { while (i > 0) { const p = (i-1)>>1; if (heap[p][0] <= heap[i][0]) break; swap(i, p); i = p; } };\n"
                    "    const down = i => { const n = heap.length; while (true) { const l = 2*i+1, r = 2*i+2; let s = i; if (l < n && heap[l][0] < heap[s][0]) s = l; if (r < n && heap[r][0] < heap[s][0]) s = r; if (s === i) break; swap(i, s); i = s; } };\n"
                    "    for (let i = 0; i < lists.length; i++) if (lists[i].length) { heap.push([lists[i][0], i, 0]); up(heap.length - 1); }\n"
                    "    const out = [];\n"
                    "    while (heap.length) {\n"
                    "        const [val, i, j] = heap[0];\n"
                    "        out.push(val);\n"
                    "        if (j + 1 < lists[i].length) { heap[0] = [lists[i][j+1], i, j+1]; down(0); }\n"
                    "        else { swap(0, heap.length - 1); heap.pop(); down(0); }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public int[] mergeKSorted(int[][] lists) {\n"
                    "    PriorityQueue<int[]> heap = new PriorityQueue<>((a, b) -> a[0] - b[0]);\n"
                    "    int total = 0;\n"
                    "    for (int i = 0; i < lists.length; i++) {\n"
                    "        total += lists[i].length;\n"
                    "        if (lists[i].length > 0) heap.offer(new int[]{lists[i][0], i, 0});\n"
                    "    }\n"
                    "    int[] out = new int[total]; int o = 0;\n"
                    "    while (!heap.isEmpty()) {\n"
                    "        int[] t = heap.poll();\n"
                    "        out[o++] = t[0];\n"
                    "        int i = t[1], j = t[2];\n"
                    "        if (j + 1 < lists[i].length) heap.offer(new int[]{lists[i][j+1], i, j+1});\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Pairwise Merge (Tournament)",
            "time_complexity": "O(N log k)",
            "space_complexity": "O(N)",
            "description": (
                "Repeatedly merge pairs of lists in a tournament bracket. Same big-O as the heap, but "
                "allocates intermediate arrays. Worth knowing because it's how external-merge-sort merges "
                "runs from disk."
            ),
            "code": {
                "python": (
                    "def merge_k_sorted(lists):\n"
                    "    if not lists:\n"
                    "        return []\n"
                    "    def merge_two(a, b):\n"
                    "        out = []\n"
                    "        i = j = 0\n"
                    "        while i < len(a) and j < len(b):\n"
                    "            if a[i] <= b[j]:\n"
                    "                out.append(a[i]); i += 1\n"
                    "            else:\n"
                    "                out.append(b[j]); j += 1\n"
                    "        out.extend(a[i:]); out.extend(b[j:])\n"
                    "        return out\n"
                    "    while len(lists) > 1:\n"
                    "        nxt = []\n"
                    "        for i in range(0, len(lists), 2):\n"
                    "            if i + 1 < len(lists):\n"
                    "                nxt.append(merge_two(lists[i], lists[i + 1]))\n"
                    "            else:\n"
                    "                nxt.append(lists[i])\n"
                    "        lists = nxt\n"
                    "    return lists[0]"
                ),
            },
        },
        {
            "title": "Concatenate and Sort (Baseline)",
            "time_complexity": "O(N log N)",
            "space_complexity": "O(N)",
            "description": (
                "Flatten every list into one and sort. Throws away the per-list order. State as the baseline; "
                "use the heap for production."
            ),
            "code": {
                "python": (
                    "def merge_k_sorted(lists):\n"
                    "    return sorted(x for lst in lists for x in lst)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the shape: 'k sources, each sorted, want a single sorted output.' That's k-way merge.",
        "2. State the brute force baseline (concat + sort) and explain why it's wasteful — you're throwing away the per-list ordering.",
        "3. Reach for the heap: 'I always need the smallest unconsumed value across all k sources. That's a min-heap.'",
        "4. Walk through heap state: initial fill = one element per non-empty list, pop = take smallest + refill from same source.",
        "5. Complexity: each push/pop is log k, N total ops → O(N log k). Space O(k).",
        "6. Mention that the iterator framing is identical — `next()` pops the heap, `hasNext()` is `not heap.empty()`.",
        "7. Edge cases: empty outer list, empty inner lists, single list, duplicate values, k = 1.",
    ],
    "tips": [
        "Python tuple comparison is lexicographic — (value, list_idx, elem_idx) breaks ties cleanly without extra logic.",
        "Java tuple equivalent: `int[]{value, list_idx, elem_idx}` with a comparator on the first element.",
        "If your language's heap doesn't support tuples, store an object with a `compareTo` on the value field.",
        "Common follow-up: 'streaming inputs that don't all fit in memory.' Same algorithm — heap holds k current heads, you read on demand.",
        "Common follow-up: 'I want descending order.' Negate values into a max-heap, or invert the comparator.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "LinkedIn", "Bloomberg"],
    "topics": ["Heap", "Merge", "Divide and Conquer", "Iterator"],
    "time_complexity": "O(N log k)",
    "space_complexity": "O(k)",
}


def REFERENCE(lists):
    import heapq
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
