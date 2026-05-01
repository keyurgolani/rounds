"""Smallest K Numbers — Easy/Medium. Heap / Quickselect / Sorting.

Three respectable approaches with different complexity profiles. The
best candidates discuss all three, then pick a max-heap of size k for
the streaming case (it works incrementally and uses bounded memory)."""
from builder.registry import register
from builder.registry import unordered_deep


PAYLOAD = {
    "title": "Smallest K Numbers",
    "difficulty": "Medium",
    "description": (
        "Given an integer array `arr` and an integer `k`, return the **k smallest values** from the array, "
        "in any order.\n\n"
        "**Example 1:**\n"
        "- Input: `arr = [3,2,1,5,6,4], k = 2`\n"
        "- Output: `[1,2]`\n\n"
        "**Example 2:**\n"
        "- Input: `arr = [7,10,4,3,20,15], k = 3`\n"
        "- Output: `[3,4,7]`\n\n"
        "**Follow-up:** What if `arr` were a stream that didn't fit in memory?"
    ),
    "hints": [
        "Naive: sort, take the first k. O(n log n) time, O(1) extra (or O(n) if you must clone). Always state this baseline.",
        "Max-heap of size k: walk once, push each element, pop when size > k. O(n log k) — wins for k << n and works as a streaming algorithm.",
        "Quickselect: partition to find the k-th smallest, then everything to its left is your answer. Expected O(n), worst O(n²) — mention the random-pivot fix.",
        "If memory is tight and k is small, the heap is the canonical pick: bounded memory, easy to reason about under pressure.",
        "Edge cases: k = 0 (empty), k >= n (return everything), duplicates in the input.",
    ],
    "constraints": [
        "0 <= k <= arr.length <= 10⁴",
        "-10⁴ <= arr[i] <= 10⁴",
    ],
    "starter_code": {
        "python": "def smallest_k(arr, k):\n    # Your code here\n    pass",
        "javascript": "function smallestK(arr, k) {\n    // Your code here\n}",
        "java": "public int[] smallestK(int[] arr, int k) {\n    // Your code here\n    return new int[]{};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([3,2,1,5,6,4], 2), ([7,10,4,3,20,15], 3), ([], 0)]\n"
            "    for arr, k in cases:\n"
            "        print(f\"smallest_k({arr}, {k}) = {smallest_k(arr, k)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[3,2,1,5,6,4], 2], [[7,10,4,3,20,15], 3]].forEach(([arr, k]) =>\n"
            "    console.log(`smallestK =`, smallestK(arr, k))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(Arrays.toString(s.smallestK(new int[]{3,2,1,5,6,4}, 2)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"arr": [3, 2, 1, 5, 6, 4], "k": 2},
         "expected": unordered_deep([1, 2]),
         "description": "Two smallest from a small unsorted list", "tags": ["basic"]},
        {"input": {"arr": [7, 10, 4, 3, 20, 15], "k": 3},
         "expected": unordered_deep([3, 4, 7]),
         "description": "Three smallest", "tags": ["basic"]},
        {"input": {"arr": [], "k": 0}, "expected": [],
         "description": "Empty input, k=0", "tags": ["edge"]},
        {"input": {"arr": [5, 5, 5], "k": 2},
         "expected": unordered_deep([5, 5]),
         "description": "All equal — k duplicates returned", "tags": ["edge"]},
        {"input": {"arr": [1, 2, 3], "k": 5},
         "expected": unordered_deep([1, 2, 3]),
         "description": "k > n — return everything", "tags": ["edge"]},
        {"input": {"arr": [-3, -1, -7, 0, 5], "k": 2},
         "expected": unordered_deep([-7, -3]),
         "description": "Negative numbers", "tags": ["edge"]},
        {"input": {"arr": [1], "k": 1}, "expected": [1],
         "description": "Single element", "tags": ["edge"]},
        {"input": {"arr": list(range(10000, 0, -1)), "k": 5},
         "expected": unordered_deep([1, 2, 3, 4, 5]),
         "description": "10K descending — top 5 smallest at the end", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Max-Heap of Size k (Optimal for k << n)",
            "time_complexity": "O(n log k)",
            "space_complexity": "O(k)",
            "description": (
                "Walk once, pushing every element into a max-heap of size k (in Python use negation since "
                "`heapq` is a min-heap). When the heap exceeds size k, pop the largest. At the end the heap "
                "holds the k smallest. Wins for k << n and is the streaming-friendly choice."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "def smallest_k(arr, k):\n"
                    "    if k <= 0:\n"
                    "        return []\n"
                    "    heap = []  # max-heap via negation\n"
                    "    for x in arr:\n"
                    "        heapq.heappush(heap, -x)\n"
                    "        if len(heap) > k:\n"
                    "            heapq.heappop(heap)\n"
                    "    return [-v for v in heap]"
                ),
                "javascript": (
                    "function smallestK(arr, k) {\n"
                    "    if (k <= 0) return [];\n"
                    "    // Sort fallback — JS lacks a built-in heap; for the k << n case implement one inline.\n"
                    "    const sorted = [...arr].sort((a, b) => a - b);\n"
                    "    return sorted.slice(0, Math.min(k, arr.length));\n"
                    "}"
                ),
                "java": (
                    "public int[] smallestK(int[] arr, int k) {\n"
                    "    if (k <= 0) return new int[0];\n"
                    "    PriorityQueue<Integer> heap = new PriorityQueue<>(Comparator.reverseOrder());\n"
                    "    for (int x : arr) {\n"
                    "        heap.offer(x);\n"
                    "        if (heap.size() > k) heap.poll();\n"
                    "    }\n"
                    "    int[] out = new int[heap.size()];\n"
                    "    int i = 0;\n"
                    "    for (int v : heap) out[i++] = v;\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sort and Slice",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n) (or O(1) if mutating in place)",
            "description": (
                "Easiest to remember. Sort the array, take the first k. Loses to the heap when k << n but is "
                "the right answer when k is comparable to n."
            ),
            "code": {
                "python": (
                    "def smallest_k(arr, k):\n"
                    "    return sorted(arr)[:k]"
                ),
                "javascript": (
                    "function smallestK(arr, k) {\n"
                    "    return [...arr].sort((a, b) => a - b).slice(0, k);\n"
                    "}"
                ),
                "java": (
                    "public int[] smallestK(int[] arr, int k) {\n"
                    "    int[] copy = arr.clone();\n"
                    "    Arrays.sort(copy);\n"
                    "    return Arrays.copyOf(copy, Math.min(k, arr.length));\n"
                    "}"
                ),
            },
        },
        {
            "title": "Quickselect (Expected O(n))",
            "time_complexity": "O(n) expected, O(n²) worst",
            "space_complexity": "O(1) extra (in-place)",
            "description": (
                "Partition around a pivot until the k-th smallest sits at index k-1; everything to its left "
                "is your answer. Beats both alternatives in the average case but is harder to implement "
                "correctly under interview pressure. Use a random pivot to avoid the O(n²) worst case."
            ),
            "code": {
                "python": (
                    "import random\n\n"
                    "def smallest_k(arr, k):\n"
                    "    if k <= 0:\n"
                    "        return []\n"
                    "    if k >= len(arr):\n"
                    "        return list(arr)\n"
                    "    a = list(arr)\n"
                    "    def partition(lo, hi):\n"
                    "        p = random.randint(lo, hi)\n"
                    "        a[p], a[hi] = a[hi], a[p]\n"
                    "        pivot = a[hi]\n"
                    "        store = lo\n"
                    "        for i in range(lo, hi):\n"
                    "            if a[i] < pivot:\n"
                    "                a[i], a[store] = a[store], a[i]\n"
                    "                store += 1\n"
                    "        a[store], a[hi] = a[hi], a[store]\n"
                    "        return store\n"
                    "    lo, hi = 0, len(a) - 1\n"
                    "    while lo < hi:\n"
                    "        p = partition(lo, hi)\n"
                    "        if p == k:\n"
                    "            break\n"
                    "        if p < k:\n"
                    "            lo = p + 1\n"
                    "        else:\n"
                    "            hi = p - 1\n"
                    "    return a[:k]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Always state the sort baseline first: O(n log n), trivially correct.",
        "2. Notice that we don't need a full sort — we only need the k smallest. That's where the heap and quickselect come in.",
        "3. For k << n, max-heap of size k is the textbook answer: O(n log k), bounded memory, streaming-friendly.",
        "4. For k ≈ n, sort wins because heap doesn't help when log k ≈ log n.",
        "5. For best expected time, quickselect is O(n). Worth mentioning even if you don't implement it — it shows depth.",
        "6. Discuss the streaming variant explicitly: 'if `arr` were a stream, only the heap approach generalises.'",
        "7. Edge cases: k = 0 (empty), k >= n (everything), duplicates, negatives.",
    ],
    "tips": [
        "Python: `heapq.nsmallest(k, arr)` is O(n log k). State it after writing the explicit heap so the interviewer sees you know the algorithm.",
        "Java: `PriorityQueue` is a min-heap by default; pass `Comparator.reverseOrder()` to make it max-heap.",
        "JS lacks a built-in heap; either roll your own (4 short methods) or fall back to sort.",
        "Streaming: only the heap approach extends. Sort needs the whole array; quickselect needs random access.",
        "Common follow-up: 'k smallest distinct'. Run a Counter first, then the heap on unique values.",
    ],
    "companies": ["Amazon", "Bloomberg", "Facebook", "Microsoft", "Apple"],
    "topics": ["Array", "Heap", "Quickselect", "Sorting"],
    "time_complexity": "O(n log k)",
    "space_complexity": "O(k)",
}


def REFERENCE(arr, k):
    if k <= 0:
        return []
    return sorted(arr)[:k]


register(PAYLOAD, REFERENCE)
