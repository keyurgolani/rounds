"""Kth Largest Element in an Array — Medium. Heap / Quickselect.

The canonical 'kth order statistic' problem. Three respectable answers
that map onto a complexity ladder: full sort (O(n log n)), min-heap of
size k (O(n log k)), Quickselect (expected O(n)). Quickselect is the
optimal expected-time answer; bring it up even if you implement the
heap, because that's what interviewers want to hear.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Kth Largest Element in an Array",
    "difficulty": "Medium",
    "description": (
        "Given an integer array `nums` and an integer `k`, return the **k-th largest element** in the array.\n\n"
        "Note that it is the k-th largest element in the **sorted order**, not the k-th distinct element.\n\n"
        "Can you solve it without sorting?\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [3,2,1,5,6,4], k = 2`\n"
        "- Output: `5`\n"
        "- Explanation: Sorted descending → `[6,5,4,3,2,1]`. The 2nd element is `5`.\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [3,2,3,1,2,4,5,5,6], k = 4`\n"
        "- Output: `4`\n"
        "- Explanation: Sorted descending → `[6,5,5,4,3,3,2,2,1]`. The 4th element is `4`. "
        "Notice duplicates count: the two `5`s occupy ranks 2 and 3."
    ),
    "hints": [
        "Sort the array descending and return `nums[k-1]`. O(n log n) — works, but interviewers will push for better.",
        "You don't need the full sort — only the top-k. Maintain a **min-heap of size k**: push everything, pop when size exceeds k. The root at the end is the answer. O(n log k).",
        "Quickselect — partition around a pivot, recurse only into the side that contains the k-th element. Expected O(n), worst-case O(n²). Randomise the pivot to make the worst case astronomically unlikely.",
        "Translate the problem: 'k-th largest' = 'find the index `len(nums) - k` in ascending order'. Easier to reason about partitions in ascending order.",
        "Duplicates count toward rank. `[5,5,5]` with k=2 returns `5`. The k-th largest is a positional concept, not a distinct-value concept.",
    ],
    "constraints": [
        "1 <= k <= nums.length <= 10⁵",
        "-10⁴ <= nums[i] <= 10⁴",
    ],
    "starter_code": {
        "python": "def find_kth_largest(nums, k):\n    # Your code here\n    pass",
        "javascript": "function findKthLargest(nums, k) {\n    // Your code here\n}",
        "java": "public int findKthLargest(int[] nums, int k) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([3,2,1,5,6,4], 2), ([3,2,3,1,2,4,5,5,6], 4), ([1], 1)]\n"
            "    for nums, k in cases:\n"
            "        print(f\"find_kth_largest({nums}, {k}) = {find_kth_largest(nums, k)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[3,2,1,5,6,4], 2], [[3,2,3,1,2,4,5,5,6], 4]].forEach(([nums, k]) =>\n"
            "    console.log(`findKthLargest =`, findKthLargest(nums, k))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.findKthLargest(new int[]{3,2,1,5,6,4}, 2));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"nums": [3, 2, 1, 5, 6, 4], "k": 2}, "expected": 5,
         "description": "Standard from the problem statement", "tags": ["basic"]},
        {"input": {"nums": [3, 2, 3, 1, 2, 4, 5, 5, 6], "k": 4}, "expected": 4,
         "description": "Duplicates count toward rank — two 5s occupy ranks 2 and 3", "tags": ["basic"]},
        {"input": {"nums": [7, 3, 9, 1, 5], "k": 1}, "expected": 9,
         "description": "k=1 → maximum element", "tags": ["edge"]},
        {"input": {"nums": [7, 3, 9, 1, 5], "k": 5}, "expected": 1,
         "description": "k=n → minimum element", "tags": ["edge"]},
        {"input": {"nums": [42], "k": 1}, "expected": 42,
         "description": "Single element, k=1", "tags": ["edge"]},
        {"input": {"nums": [4, 4, 4, 4, 4], "k": 3}, "expected": 4,
         "description": "All-same array — answer equals the only value", "tags": ["edge"]},
        {"input": {"nums": [1, 2, 3, 4, 5, 6, 7, 8], "k": 3}, "expected": 6,
         "description": "Sorted ascending — k-th from the end", "tags": ["tricky"]},
        {"input": {"nums": [8, 7, 6, 5, 4, 3, 2, 1], "k": 3}, "expected": 6,
         "description": "Sorted descending — directly index k-1", "tags": ["tricky"]},
        {"input": {"nums": [5, 5, 5, 4, 4, 3], "k": 2}, "expected": 5,
         "description": "Duplicates of the max — k=2 still returns 5", "tags": ["tricky"]},
        {"input": {"nums": [-1, -5, -3, -2, -4], "k": 2}, "expected": -2,
         "description": "All negatives — 2nd largest is -2", "tags": ["edge"]},
        {"input": {"nums": [3, 1, 2, 4] * 2500, "k": 5000}, "expected": 3,
         "description": "10K elements with periodic structure — middle rank", "tags": ["large"]},
        {"input": {"nums": list(range(10000)), "k": 1}, "expected": 9999,
         "description": "10K ascending, k=1 → max", "tags": ["large"]},
        {"input": {"nums": list(range(10000, 0, -1)), "k": 10000}, "expected": 1,
         "description": "10K descending, k=n → min", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Quickselect (Optimal Expected)",
            "time_complexity": "O(n) average, O(n²) worst",
            "space_complexity": "O(1) extra (in-place)",
            "description": (
                "Hoare/Lomuto partition around a randomised pivot. After partitioning, the pivot sits at "
                "its final sorted position — if that index equals `len(nums) - k`, the pivot is the answer. "
                "Otherwise recurse into the side that contains the target index. Randomising the pivot makes "
                "the O(n²) worst case astronomically unlikely on adversarial inputs."
            ),
            "code": {
                "python": (
                    "import random\n\n"
                    "def find_kth_largest(nums, k):\n"
                    "    target = len(nums) - k  # k-th largest = index `n-k` in ascending order\n"
                    "    lo, hi = 0, len(nums) - 1\n"
                    "    while lo <= hi:\n"
                    "        pivot_idx = random.randint(lo, hi)\n"
                    "        nums[pivot_idx], nums[hi] = nums[hi], nums[pivot_idx]\n"
                    "        pivot = nums[hi]\n"
                    "        store = lo\n"
                    "        for i in range(lo, hi):\n"
                    "            if nums[i] < pivot:\n"
                    "                nums[i], nums[store] = nums[store], nums[i]\n"
                    "                store += 1\n"
                    "        nums[store], nums[hi] = nums[hi], nums[store]\n"
                    "        if store == target:\n"
                    "            return nums[store]\n"
                    "        elif store < target:\n"
                    "            lo = store + 1\n"
                    "        else:\n"
                    "            hi = store - 1\n"
                    "    return -1  # unreachable for valid input"
                ),
                "javascript": (
                    "function findKthLargest(nums, k) {\n"
                    "    const target = nums.length - k;\n"
                    "    let lo = 0, hi = nums.length - 1;\n"
                    "    const swap = (i, j) => { [nums[i], nums[j]] = [nums[j], nums[i]]; };\n"
                    "    while (lo <= hi) {\n"
                    "        const pivotIdx = lo + Math.floor(Math.random() * (hi - lo + 1));\n"
                    "        swap(pivotIdx, hi);\n"
                    "        const pivot = nums[hi];\n"
                    "        let store = lo;\n"
                    "        for (let i = lo; i < hi; i++) {\n"
                    "            if (nums[i] < pivot) { swap(i, store); store++; }\n"
                    "        }\n"
                    "        swap(store, hi);\n"
                    "        if (store === target) return nums[store];\n"
                    "        else if (store < target) lo = store + 1;\n"
                    "        else hi = store - 1;\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
                "java": (
                    "public int findKthLargest(int[] nums, int k) {\n"
                    "    int target = nums.length - k;\n"
                    "    int lo = 0, hi = nums.length - 1;\n"
                    "    java.util.Random rng = new java.util.Random();\n"
                    "    while (lo <= hi) {\n"
                    "        int pivotIdx = lo + rng.nextInt(hi - lo + 1);\n"
                    "        int tmp = nums[pivotIdx]; nums[pivotIdx] = nums[hi]; nums[hi] = tmp;\n"
                    "        int pivot = nums[hi], store = lo;\n"
                    "        for (int i = lo; i < hi; i++) {\n"
                    "            if (nums[i] < pivot) {\n"
                    "                int t = nums[i]; nums[i] = nums[store]; nums[store] = t;\n"
                    "                store++;\n"
                    "            }\n"
                    "        }\n"
                    "        int t = nums[store]; nums[store] = nums[hi]; nums[hi] = t;\n"
                    "        if (store == target) return nums[store];\n"
                    "        else if (store < target) lo = store + 1;\n"
                    "        else hi = store - 1;\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Min-Heap of Size k",
            "time_complexity": "O(n log k)",
            "space_complexity": "O(k)",
            "description": (
                "Maintain a min-heap of size k. Push every element; whenever the heap exceeds k, pop the "
                "smallest. After processing all elements, the heap holds the k largest values, and the root "
                "(its minimum) is the k-th largest. Easier to recall under interview pressure than Quickselect."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "def find_kth_largest(nums, k):\n"
                    "    heap = []\n"
                    "    for x in nums:\n"
                    "        heapq.heappush(heap, x)\n"
                    "        if len(heap) > k:\n"
                    "            heapq.heappop(heap)\n"
                    "    return heap[0]"
                ),
                "javascript": (
                    "// Min-heap implemented inline.\n"
                    "function findKthLargest(nums, k) {\n"
                    "    const heap = [];\n"
                    "    const swap = (i, j) => { [heap[i], heap[j]] = [heap[j], heap[i]]; };\n"
                    "    const up = (i) => {\n"
                    "        while (i > 0) {\n"
                    "            const p = (i - 1) >> 1;\n"
                    "            if (heap[p] <= heap[i]) break;\n"
                    "            swap(i, p); i = p;\n"
                    "        }\n"
                    "    };\n"
                    "    const down = (i) => {\n"
                    "        const n = heap.length;\n"
                    "        while (true) {\n"
                    "            const l = 2*i+1, r = 2*i+2;\n"
                    "            let s = i;\n"
                    "            if (l < n && heap[l] < heap[s]) s = l;\n"
                    "            if (r < n && heap[r] < heap[s]) s = r;\n"
                    "            if (s === i) break;\n"
                    "            swap(i, s); i = s;\n"
                    "        }\n"
                    "    };\n"
                    "    for (const x of nums) {\n"
                    "        heap.push(x); up(heap.length - 1);\n"
                    "        if (heap.length > k) { swap(0, heap.length - 1); heap.pop(); down(0); }\n"
                    "    }\n"
                    "    return heap[0];\n"
                    "}"
                ),
                "java": (
                    "public int findKthLargest(int[] nums, int k) {\n"
                    "    PriorityQueue<Integer> heap = new PriorityQueue<>();\n"
                    "    for (int x : nums) {\n"
                    "        heap.offer(x);\n"
                    "        if (heap.size() > k) heap.poll();\n"
                    "    }\n"
                    "    return heap.peek();\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sort (Baseline)",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(1) or O(n) depending on sort",
            "description": (
                "Sort the array and index. Easiest to remember; the slowest of the three. State it first, then "
                "improve."
            ),
            "code": {
                "python": (
                    "def find_kth_largest(nums, k):\n"
                    "    nums.sort()\n"
                    "    return nums[-k]"
                ),
                "javascript": (
                    "function findKthLargest(nums, k) {\n"
                    "    nums.sort((a, b) => a - b);\n"
                    "    return nums[nums.length - k];\n"
                    "}"
                ),
                "java": (
                    "public int findKthLargest(int[] nums, int k) {\n"
                    "    Arrays.sort(nums);\n"
                    "    return nums[nums.length - k];\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate carefully: 'k-th largest in sorted order' — duplicates count. `[5,5,5]` k=2 returns 5.",
        "2. Sort + index is the baseline. O(n log n). State it; the interviewer will likely ask for better.",
        "3. Observation: we don't need full sort, only the top k. A min-heap of size k captures exactly that, in O(n log k).",
        "4. To beat O(n log k) on average, use Quickselect. Partition around a pivot; recurse only into the side containing the target index. Expected O(n).",
        "5. Convert 'k-th largest' to 'index n−k in ascending order' before partitioning — easier to reason about.",
        "6. Randomise the pivot. Without randomisation, sorted/adversarial inputs hit O(n²). With it, the expected linear bound holds in practice.",
        "7. Edge cases: k=1 (max), k=n (min), all-same array, single element, all negatives.",
    ],
    "tips": [
        "Lead with the heap if you're nervous. It's correct, it beats the sort, and it's easier to bug-free under stress than Quickselect.",
        "If you go for Quickselect, *randomise the pivot*. Median-of-three is a defensible alternative; deterministic first/last element invites the O(n²) trap.",
        "`heapq` in Python is a min-heap. For 'k largest', that's exactly what you want (size-k min-heap, root is the answer). For 'k smallest', either negate values or use a size-k max-heap (`heapq._heapify_max` or negate).",
        "There's a `heapq.nlargest(k, nums)[-1]` one-liner. It runs O(n log k) under the hood. Don't lead with it — interviewers want the algorithm, not the library call.",
        "Common follow-up: 'k-th smallest' — same algorithm, flip the comparator. 'k-th largest in a stream' — heap is mandatory; Quickselect doesn't apply because you can't repartition unbounded data.",
        "Counting-sort variant: when values are bounded (e.g., scores 0..100), bucket by value and walk down. O(n + V) where V is the value range.",
    ],
    "companies": ["Amazon", "Facebook", "Google", "Microsoft", "LinkedIn", "Apple"],
    "topics": ["Array", "Heap", "Quickselect", "Divide and Conquer", "Sorting"],
    "time_complexity": "O(n) average (Quickselect)",
    "space_complexity": "O(1)",
}


def REFERENCE(nums, k):
    # Sort baseline — simplest correct reference.
    return sorted(nums)[-k]


register(PAYLOAD, REFERENCE)
