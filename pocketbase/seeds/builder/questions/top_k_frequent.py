"""Top K Frequent Elements — Medium. Heap / Hashing / Bucket sort.

Three respectable solutions, each with a different complexity profile.
The best candidates discuss all three: sort by count (O(n log n)), heap
of size k (O(n log k)), bucket sort indexed by frequency (O(n)). The
last one is the surprise — it exploits that frequencies are bounded by
the array length.
"""
from builder.registry import register


_TOPK_VALIDATOR = (
    # Output must be a list of k ints, all distinct, drawn from `nums`,
    # whose frequencies in `nums` are >= every other element's frequency.
    "lambda inp, out: ("
    "isinstance(out, list) and len(out) == inp['k'] and "
    "len(set(out)) == inp['k'] and "
    "all(x in set(inp['nums']) for x in out) and "
    "(lambda freqs, threshold: all(freqs[x] >= threshold for x in out))("
    "{x: sum(1 for v in inp['nums'] if v == x) for x in set(inp['nums'])}, "
    "sorted([sum(1 for v in inp['nums'] if v == x) for x in set(inp['nums'])], reverse=True)[inp['k']-1]"
    ")"
    ")"
)


PAYLOAD = {
    "title": "Top K Frequent Elements",
    "difficulty": "Medium",
    "description": (
        "Given an integer array `nums` and an integer `k`, return the **k most frequent elements**. "
        "You may return the answer in **any order**.\n\n"
        "**Example 1:**\n"
        "- Input: `nums = [1,1,1,2,2,3], k = 2`\n"
        "- Output: `[1,2]`\n\n"
        "**Example 2:**\n"
        "- Input: `nums = [1], k = 1`\n"
        "- Output: `[1]`\n\n"
        "**Follow-up:** Your algorithm's time complexity must be better than O(n log n), where n is the array's size."
    ),
    "hints": [
        "Step 1 in every approach: count frequencies. `Counter(nums)` or a manual hash map.",
        "Naive: sort all unique elements by frequency, take the first k. O(n log n) — fails the follow-up.",
        "Heap: maintain a min-heap of size k while walking the frequency map. O(n log k) — beats the bound.",
        "Bucket sort: frequencies are bounded by `len(nums)`. Index a list of buckets by frequency, then walk from highest to lowest until you've collected k elements. O(n).",
        "Quickselect on (-count, value) gives expected O(n) too, but it's harder to implement under interview time pressure than bucket sort.",
    ],
    "constraints": [
        "1 <= nums.length <= 10⁵",
        "-10⁴ <= nums[i] <= 10⁴",
        "k is in the range [1, number of distinct elements in nums]",
        "The answer is guaranteed to be unique (the k-th and (k+1)-th most frequent elements have different counts)",
    ],
    "starter_code": {
        "python": "def top_k_frequent(nums, k):\n    # Your code here\n    pass",
        "javascript": "function topKFrequent(nums, k) {\n    // Your code here\n}",
        "java": "public int[] topKFrequent(int[] nums, int k) {\n    // Your code here\n    return new int[]{};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([1,1,1,2,2,3], 2), ([1], 1), ([4,4,4,5,5,6,6,6,6], 2)]\n"
            "    for nums, k in cases:\n"
            "        print(f\"top_k_frequent({nums}, {k}) = {top_k_frequent(nums, k)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,1,1,2,2,3], 2], [[1], 1]].forEach(([nums, k]) =>\n"
            "    console.log(`topKFrequent =`, topKFrequent(nums, k))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(Arrays.toString(s.topKFrequent(new int[]{1,1,1,2,2,3}, 2)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {
            "input": {"nums": [1, 1, 1, 2, 2, 3], "k": 2},
            "expected": {
                "$match": "validator",
                "description": "k most frequent elements (any order)",
                "code": _TOPK_VALIDATOR,
                "examples": [[1, 2], [2, 1]],
            },
            "description": "Standard from the problem statement",
            "tags": ["basic"],
        },
        {
            "input": {"nums": [1], "k": 1},
            "expected": [1],
            "description": "Single element", "tags": ["edge"],
        },
        {
            "input": {"nums": [4, 4, 4, 5, 5, 6, 6, 6, 6], "k": 2},
            "expected": {
                "$match": "validator",
                "description": "Top 2 by frequency: 6 (×4), 4 (×3)",
                "code": _TOPK_VALIDATOR,
                "examples": [[6, 4], [4, 6]],
            },
            "description": "Multi-frequency, distinct counts", "tags": ["basic"],
        },
        {
            "input": {"nums": [1, 2, 3, 4, 5], "k": 3},
            "expected": {
                "$match": "validator",
                "description": "All elements equally frequent — any 3 distinct elements are valid",
                "code": _TOPK_VALIDATOR,
                "examples": [[1, 2, 3], [3, 5, 1]],
            },
            "description": "All counts are 1, k=3", "tags": ["tricky"],
        },
        {
            "input": {"nums": [-1, -1, -1, 0, 0, 1], "k": 1},
            "expected": [-1],
            "description": "Negative values and zero — only one valid answer",
            "tags": ["edge"],
        },
        {
            "input": {"nums": [7, 7, 7, 7, 7, 7], "k": 1},
            "expected": [7],
            "description": "Single distinct value", "tags": ["edge"],
        },
        {
            "input": {"nums": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5], "k": 5},
            "expected": {
                "$match": "validator",
                "description": "k equals the number of distinct elements — return all of them",
                "code": _TOPK_VALIDATOR,
                "examples": [[1, 2, 3, 4, 5]],
            },
            "description": "k = number of distinct elements", "tags": ["tricky"],
        },
        {
            "input": {"nums": [10000, 10000, -10000, -10000, -10000, 0], "k": 2},
            "expected": {
                "$match": "validator",
                "description": "Constraint-edge values; -10000 (×3) and 10000 (×2) are top 2",
                "code": _TOPK_VALIDATOR,
                "examples": [[-10000, 10000], [10000, -10000]],
            },
            "description": "Constraint-boundary values", "tags": ["edge"],
        },
        {
            "input": {"nums": ([1] * 5000 + [2] * 3000 + [3] * 2000 + list(range(100, 200))), "k": 3},
            "expected": {
                "$match": "validator",
                "description": "10K+ elements; top 3 are 1, 2, 3 by clear margin",
                "code": _TOPK_VALIDATOR,
                "examples": [[1, 2, 3]],
            },
            "description": "10K+ elements, clear top-3", "tags": ["large"],
        },
        {
            "input": {"nums": list(range(1000)) * 10 + [0] * 50, "k": 1},
            "expected": [0],
            "description": "10050 elements; 0 wins by 50 vs 10 for everything else",
            "tags": ["large"],
        },
    ],
    "solutions": [
        {
            "title": "Bucket Sort by Frequency (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Frequencies are bounded by `len(nums)`. Build a `freq → [values]` bucket array of length "
                "n+1, then iterate from the highest bucket down, collecting values until you have k. "
                "Beats the O(n log n) bound."
            ),
            "code": {
                "python": (
                    "from collections import Counter\n\n"
                    "def top_k_frequent(nums, k):\n"
                    "    counts = Counter(nums)\n"
                    "    buckets = [[] for _ in range(len(nums) + 1)]\n"
                    "    for val, freq in counts.items():\n"
                    "        buckets[freq].append(val)\n"
                    "    out = []\n"
                    "    for freq in range(len(buckets) - 1, 0, -1):\n"
                    "        for val in buckets[freq]:\n"
                    "            out.append(val)\n"
                    "            if len(out) == k:\n"
                    "                return out\n"
                    "    return out"
                ),
                "javascript": (
                    "function topKFrequent(nums, k) {\n"
                    "    const counts = new Map();\n"
                    "    for (const n of nums) counts.set(n, (counts.get(n) || 0) + 1);\n"
                    "    const buckets = Array.from({ length: nums.length + 1 }, () => []);\n"
                    "    for (const [val, freq] of counts) buckets[freq].push(val);\n"
                    "    const out = [];\n"
                    "    for (let f = buckets.length - 1; f > 0 && out.length < k; f--) {\n"
                    "        for (const v of buckets[f]) {\n"
                    "            out.push(v);\n"
                    "            if (out.length === k) return out;\n"
                    "        }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public int[] topKFrequent(int[] nums, int k) {\n"
                    "    Map<Integer, Integer> counts = new HashMap<>();\n"
                    "    for (int n : nums) counts.merge(n, 1, Integer::sum);\n"
                    "    List<List<Integer>> buckets = new ArrayList<>();\n"
                    "    for (int i = 0; i <= nums.length; i++) buckets.add(new ArrayList<>());\n"
                    "    for (var e : counts.entrySet()) buckets.get(e.getValue()).add(e.getKey());\n"
                    "    int[] out = new int[k];\n"
                    "    int idx = 0;\n"
                    "    for (int f = buckets.size() - 1; f > 0 && idx < k; f--) {\n"
                    "        for (int v : buckets.get(f)) {\n"
                    "            if (idx == k) break;\n"
                    "            out[idx++] = v;\n"
                    "        }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Min-Heap of Size k",
            "time_complexity": "O(n log k)",
            "space_complexity": "O(n + k)",
            "description": (
                "Count frequencies, then push (count, value) pairs into a min-heap, evicting the smallest "
                "whenever the heap exceeds size k. At the end the heap holds the top-k by frequency. "
                "Strictly worse than bucket sort but easier to recall under stress."
            ),
            "code": {
                "python": (
                    "import heapq\n"
                    "from collections import Counter\n\n"
                    "def top_k_frequent(nums, k):\n"
                    "    counts = Counter(nums)\n"
                    "    heap = []\n"
                    "    for val, freq in counts.items():\n"
                    "        heapq.heappush(heap, (freq, val))\n"
                    "        if len(heap) > k:\n"
                    "            heapq.heappop(heap)\n"
                    "    return [val for _, val in heap]"
                ),
                "javascript": (
                    "// Min-heap implemented inline to avoid dependencies.\n"
                    "function topKFrequent(nums, k) {\n"
                    "    const counts = new Map();\n"
                    "    for (const n of nums) counts.set(n, (counts.get(n) || 0) + 1);\n"
                    "    const heap = [];\n"
                    "    const swap = (i, j) => { [heap[i], heap[j]] = [heap[j], heap[i]]; };\n"
                    "    const up = (i) => {\n"
                    "        while (i > 0) {\n"
                    "            const p = (i - 1) >> 1;\n"
                    "            if (heap[p][0] <= heap[i][0]) break;\n"
                    "            swap(i, p); i = p;\n"
                    "        }\n"
                    "    };\n"
                    "    const down = (i) => {\n"
                    "        const n = heap.length;\n"
                    "        while (true) {\n"
                    "            const l = 2*i+1, r = 2*i+2;\n"
                    "            let s = i;\n"
                    "            if (l < n && heap[l][0] < heap[s][0]) s = l;\n"
                    "            if (r < n && heap[r][0] < heap[s][0]) s = r;\n"
                    "            if (s === i) break;\n"
                    "            swap(i, s); i = s;\n"
                    "        }\n"
                    "    };\n"
                    "    for (const [val, freq] of counts) {\n"
                    "        heap.push([freq, val]); up(heap.length - 1);\n"
                    "        if (heap.length > k) { swap(0, heap.length - 1); heap.pop(); down(0); }\n"
                    "    }\n"
                    "    return heap.map(([_, v]) => v);\n"
                    "}"
                ),
                "java": (
                    "public int[] topKFrequent(int[] nums, int k) {\n"
                    "    Map<Integer, Integer> counts = new HashMap<>();\n"
                    "    for (int n : nums) counts.merge(n, 1, Integer::sum);\n"
                    "    PriorityQueue<int[]> heap = new PriorityQueue<>((a, b) -> a[0] - b[0]);\n"
                    "    for (var e : counts.entrySet()) {\n"
                    "        heap.offer(new int[]{e.getValue(), e.getKey()});\n"
                    "        if (heap.size() > k) heap.poll();\n"
                    "    }\n"
                    "    int[] out = new int[k];\n"
                    "    for (int i = 0; i < k; i++) out[i] = heap.poll()[1];\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sort Frequencies",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "Count, sort the unique values by frequency descending, take the first k. Easiest to remember "
                "but fails the follow-up's complexity bound."
            ),
            "code": {
                "python": (
                    "from collections import Counter\n\n"
                    "def top_k_frequent(nums, k):\n"
                    "    counts = Counter(nums)\n"
                    "    return [val for val, _ in counts.most_common(k)]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. The shape: 'top k by frequency'. Step 0 is always 'count frequencies' — every approach starts there.",
        "2. Sort gives O(n log n). State it, then notice the follow-up wants better.",
        "3. To beat O(n log n), exploit a constraint. Frequencies are bounded by `len(nums)` — that's the bucket-sort opening.",
        "4. Heap of size k is the standard middle-ground answer: O(n log k). Worth knowing because it generalises to streaming inputs.",
        "5. Bucket sort iteration goes high → low. Stop the moment you've collected k values.",
        "6. Edge cases: k = 1 (just the mode), k = number of distinct values (return everything), all elements unique (any k of them).",
    ],
    "tips": [
        "If asked 'what if nums could be a stream?' the bucket sort no longer works — frequencies aren't known up front. Switch to the heap (top-k streaming is a heap classic).",
        "Quickselect on (-count, value) gives expected O(n) too. Mention it; you don't need to implement it unless asked.",
        "`Counter.most_common(k)` is the cheat-code Python answer. Don't lead with it — interviewers want to see the algorithm.",
        "If counts are guaranteed to fit in a small range (e.g. 32-bit), even radix sort buys you O(n) without the bucket-array memory hit.",
        "The 'answer is unique' constraint matters: it lets you ignore tie-breaking. If it weren't there, you'd need a deterministic tiebreaker (e.g. value ascending).",
    ],
    "companies": ["Amazon", "Facebook", "Google", "Microsoft", "Yelp"],
    "topics": ["Array", "Hash Table", "Heap", "Bucket Sort", "Quickselect"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(nums, k):
    from collections import Counter
    counts = Counter(nums)
    buckets = [[] for _ in range(len(nums) + 1)]
    for val, freq in counts.items():
        buckets[freq].append(val)
    out = []
    for freq in range(len(buckets) - 1, 0, -1):
        for val in buckets[freq]:
            out.append(val)
            if len(out) == k:
                return out
    return out


register(PAYLOAD, REFERENCE)
