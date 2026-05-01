"""K Closest Points to Origin — Medium. Heap / Quickselect.

The canonical 'top-k by a numeric key' problem. Three respectable approaches:
sort by distance² (O(n log n)), max-heap of size k (O(n log k)), Quickselect
on distance² (O(n) average). The trick worth remembering: never compute the
square root — comparing x²+y² preserves ordering and avoids the floating
point work entirely.
"""
from builder.registry import register


PAYLOAD = {
    "title": "K Closest Points to Origin",
    "difficulty": "Medium",
    "description": (
        "Given an array `points` where `points[i] = [xi, yi]` represents a point on the X-Y plane and an "
        "integer `k`, return the **k closest points** to the origin `(0, 0)`.\n\n"
        "The distance between two points on the X-Y plane is the Euclidean distance "
        "(i.e., `sqrt((x1 - x2)² + (y1 - y2)²)`).\n\n"
        "You may return the answer in **any order**. The answer is **guaranteed to be unique** "
        "(except for the order that it is in).\n\n"
        "**Example 1:**\n"
        "- Input: `points = [[1,3],[-2,2]], k = 1`\n"
        "- Output: `[[-2,2]]`\n"
        "- Explanation: The distance between `(1,3)` and the origin is `sqrt(10)`. "
        "The distance between `(-2,2)` and the origin is `sqrt(8)`. "
        "Since `sqrt(8) < sqrt(10)`, `(-2,2)` is closer. We only want the closest `k = 1` points "
        "from the origin, so the answer is `[[-2,2]]`.\n\n"
        "**Example 2:**\n"
        "- Input: `points = [[3,3],[5,-1],[-2,4]], k = 2`\n"
        "- Output: `[[3,3],[-2,4]]`\n"
        "- Explanation: The answer `[[-2,4],[3,3]]` would also be accepted."
    ),
    "hints": [
        "Sort the points by their squared distance `x² + y²` ascending and take the first k. O(n log n) — easy to write, easy to verify.",
        "Use a **max-heap of size k** keyed on squared distance. Push every point; if the heap exceeds k, pop the farthest. End with the k closest. O(n log k).",
        "**Quickselect** on squared distance partitions the array around a pivot until the k-th element is in place; the first k slots are then the answer (in some order). O(n) average, O(n²) worst.",
        "Never compute `sqrt`. Comparing `x² + y²` values preserves the ordering of distances and avoids floating-point drift entirely.",
        "Output order is unspecified — don't waste cycles sorting the final k points unless asked.",
    ],
    "constraints": [
        "1 <= k <= points.length <= 10⁴",
        "-10⁴ <= xi, yi <= 10⁴",
        "The answer is guaranteed to be unique up to order.",
    ],
    "starter_code": {
        "python": "def k_closest(points, k):\n    # Your code here\n    pass",
        "javascript": "function kClosest(points, k) {\n    // Your code here\n}",
        "java": "public int[][] kClosest(int[][] points, int k) {\n    // Your code here\n    return new int[0][0];\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([[1,3],[-2,2]], 1), ([[3,3],[5,-1],[-2,4]], 2)]\n"
            "    for points, k in cases:\n"
            "        print(f\"k_closest({points}, {k}) = {k_closest(points, k)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[[1,3],[-2,2]], 1], [[[3,3],[5,-1],[-2,4]], 2]].forEach(([points, k]) =>\n"
            "    console.log(`kClosest =`, kClosest(points, k))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(Arrays.deepToString(s.kClosest(new int[][]{{1,3},{-2,2}}, 1)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {
            "input": {"points": [[1, 3], [-2, 2]], "k": 1},
            "expected": {"$match": "unordered_deep", "value": [[-2, 2]]},
            "description": "Classic two-point case — closer wins",
            "tags": ["basic"],
        },
        {
            "input": {"points": [[3, 3], [5, -1], [-2, 4]], "k": 2},
            "expected": {"$match": "unordered_deep", "value": [[3, 3], [-2, 4]]},
            "description": "LeetCode example — pick the two closest in any order",
            "tags": ["basic"],
        },
        {
            "input": {"points": [[1, 1], [2, 2], [3, 3]], "k": 3},
            "expected": {"$match": "unordered_deep", "value": [[1, 1], [2, 2], [3, 3]]},
            "description": "k equals length — return every point",
            "tags": ["edge"],
        },
        {
            "input": {"points": [[0, 1]], "k": 1},
            "expected": {"$match": "unordered_deep", "value": [[0, 1]]},
            "description": "Single point with k=1",
            "tags": ["edge"],
        },
        {
            "input": {"points": [[5, 0], [0, 5], [-5, 0], [0, -5]], "k": 2},
            "expected": {
                "$match": "unordered_deep",
                "value": [[5, 0], [0, 5]],
            },
            "description": (
                "Four points all at distance 5 — any two are valid. Reference returns the first two; "
                "matcher accepts in any order. (Problem normally guarantees uniqueness; this stresses "
                "the unordered matcher when ties are allowed.)"
            ),
            "tags": ["tricky"],
        },
        {
            "input": {"points": [[3, 0], [0, 4], [-1, 0], [0, -2], [2, 2]], "k": 3},
            "expected": {"$match": "unordered_deep", "value": [[-1, 0], [0, -2], [2, 2]]},
            "description": "Mixed quadrants — closest three by squared distance (1, 4, 8)",
            "tags": ["basic"],
        },
        {
            "input": {"points": [[1, 0], [0, 1], [-1, 0], [0, -1], [2, 0], [0, 2]], "k": 4},
            "expected": {
                "$match": "unordered_deep",
                "value": [[1, 0], [0, 1], [-1, 0], [0, -1]],
            },
            "description": "Points on axes — four unit-distance points beat the two distance-2 points",
            "tags": ["tricky"],
        },
        {
            "input": {"points": [[10000, 10000], [-10000, -10000], [1, 1], [9999, 9999]], "k": 1},
            "expected": {"$match": "unordered_deep", "value": [[1, 1]]},
            "description": "Large coordinates near constraint bound — squared distance fits in 64-bit",
            "tags": ["edge"],
        },
        {
            "input": {"points": [[i, i] for i in range(1, 1001)], "k": 5},
            "expected": {
                "$match": "unordered_deep",
                "value": [[1, 1], [2, 2], [3, 3], [4, 4], [5, 5]],
            },
            "description": "1K points along the diagonal — closest five are the smallest indices",
            "tags": ["large"],
        },
        {
            "input": {"points": [[i, 0] for i in range(-500, 501) if i != 0], "k": 4},
            "expected": {
                "$match": "unordered_deep",
                "value": [[-1, 0], [1, 0], [-2, 0], [2, 0]],
            },
            "description": "1K points on x-axis with symmetric ties — both signs of the two smallest |x| win",
            "tags": ["large"],
        },
    ],
    "solutions": [
        {
            "title": "Max-Heap of Size k (Optimal in Practice)",
            "time_complexity": "O(n log k)",
            "space_complexity": "O(k)",
            "description": (
                "Walk the points; push squared distance into a max-heap (Python's heapq is min-heap, so "
                "negate the key). When the heap exceeds k, pop — that evicts the current farthest. After "
                "the pass the heap holds the k closest. Beats sort whenever k ≪ n and uses bounded memory."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "def k_closest(points, k):\n"
                    "    heap = []  # max-heap via negated key\n"
                    "    for x, y in points:\n"
                    "        d2 = x * x + y * y\n"
                    "        if len(heap) < k:\n"
                    "            heapq.heappush(heap, (-d2, [x, y]))\n"
                    "        elif -heap[0][0] > d2:\n"
                    "            heapq.heapreplace(heap, (-d2, [x, y]))\n"
                    "    return [p for _, p in heap]"
                ),
                "javascript": (
                    "// Max-heap implemented inline; key is squared distance.\n"
                    "function kClosest(points, k) {\n"
                    "    const heap = [];\n"
                    "    const swap = (i, j) => { [heap[i], heap[j]] = [heap[j], heap[i]]; };\n"
                    "    const up = (i) => {\n"
                    "        while (i > 0) {\n"
                    "            const p = (i - 1) >> 1;\n"
                    "            if (heap[p][0] >= heap[i][0]) break;\n"
                    "            swap(i, p); i = p;\n"
                    "        }\n"
                    "    };\n"
                    "    const down = (i) => {\n"
                    "        const n = heap.length;\n"
                    "        while (true) {\n"
                    "            const l = 2*i+1, r = 2*i+2; let s = i;\n"
                    "            if (l < n && heap[l][0] > heap[s][0]) s = l;\n"
                    "            if (r < n && heap[r][0] > heap[s][0]) s = r;\n"
                    "            if (s === i) break;\n"
                    "            swap(i, s); i = s;\n"
                    "        }\n"
                    "    };\n"
                    "    for (const [x, y] of points) {\n"
                    "        const d2 = x*x + y*y;\n"
                    "        if (heap.length < k) { heap.push([d2, [x, y]]); up(heap.length - 1); }\n"
                    "        else if (heap[0][0] > d2) { heap[0] = [d2, [x, y]]; down(0); }\n"
                    "    }\n"
                    "    return heap.map(([, p]) => p);\n"
                    "}"
                ),
                "java": (
                    "public int[][] kClosest(int[][] points, int k) {\n"
                    "    PriorityQueue<int[]> heap = new PriorityQueue<>(\n"
                    "        (a, b) -> Integer.compare(b[0]*b[0]+b[1]*b[1], a[0]*a[0]+a[1]*a[1]));\n"
                    "    for (int[] p : points) {\n"
                    "        heap.offer(p);\n"
                    "        if (heap.size() > k) heap.poll();\n"
                    "    }\n"
                    "    int[][] out = new int[k][2];\n"
                    "    for (int i = 0; i < k; i++) out[i] = heap.poll();\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Quickselect by Squared Distance (Optimal Average)",
            "time_complexity": "O(n) average, O(n²) worst",
            "space_complexity": "O(1) extra (in-place)",
            "description": (
                "Partition the array around a pivot's squared distance, Hoare/Lomuto-style. Recurse only "
                "into the side that contains the k-th index. After the recursion `points[:k]` are the "
                "closest k (in some order). Expected linear time but pivot-sensitive in the worst case — "
                "shuffle the array first or pick a random pivot."
            ),
            "code": {
                "python": (
                    "import random\n\n"
                    "def k_closest(points, k):\n"
                    "    def d2(p):\n"
                    "        return p[0]*p[0] + p[1]*p[1]\n\n"
                    "    def partition(lo, hi):\n"
                    "        pivot_idx = random.randint(lo, hi)\n"
                    "        points[pivot_idx], points[hi] = points[hi], points[pivot_idx]\n"
                    "        pivot = d2(points[hi])\n"
                    "        store = lo\n"
                    "        for i in range(lo, hi):\n"
                    "            if d2(points[i]) < pivot:\n"
                    "                points[store], points[i] = points[i], points[store]\n"
                    "                store += 1\n"
                    "        points[store], points[hi] = points[hi], points[store]\n"
                    "        return store\n\n"
                    "    lo, hi = 0, len(points) - 1\n"
                    "    while lo < hi:\n"
                    "        p = partition(lo, hi)\n"
                    "        if p == k:\n"
                    "            break\n"
                    "        if p < k:\n"
                    "            lo = p + 1\n"
                    "        else:\n"
                    "            hi = p - 1\n"
                    "    return points[:k]"
                ),
            },
        },
        {
            "title": "Sort by Squared Distance",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n) for the sort (or O(log n) in-place)",
            "description": (
                "Sort the array using `x² + y²` as the key, then slice the first k. Easiest to remember; "
                "fine for n up to 10⁴ but loses to the heap when k is small relative to n."
            ),
            "code": {
                "python": (
                    "def k_closest(points, k):\n"
                    "    return sorted(points, key=lambda p: p[0]*p[0] + p[1]*p[1])[:k]"
                ),
                "javascript": (
                    "function kClosest(points, k) {\n"
                    "    return points\n"
                    "        .slice()\n"
                    "        .sort((a, b) => (a[0]*a[0] + a[1]*a[1]) - (b[0]*b[0] + b[1]*b[1]))\n"
                    "        .slice(0, k);\n"
                    "}"
                ),
                "java": (
                    "public int[][] kClosest(int[][] points, int k) {\n"
                    "    Arrays.sort(points, (a, b) ->\n"
                    "        Integer.compare(a[0]*a[0]+a[1]*a[1], b[0]*b[0]+b[1]*b[1]));\n"
                    "    return Arrays.copyOfRange(points, 0, k);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. The shape: 'top-k by a numeric key'. The key here is Euclidean distance — but `sqrt` is monotone, so squared distance is the same ordering and integer-clean.",
        "2. Sort gives O(n log n). State it; it's correct and easy. Then ask: can we do better?",
        "3. Heap of size k cuts work to O(n log k) and bounded extra memory — strictly better when k ≪ n. The standard 'top-k' answer.",
        "4. Quickselect gives O(n) expected; it's the right answer if the interviewer pushes for sub-log-n time. Mention pivot-sensitivity and randomisation.",
        "5. Output order doesn't matter — don't sort the final k points.",
        "6. Edge cases: k = n (return everything), single point, ties on distance (any choice valid because the problem guarantees uniqueness 'up to order').",
    ],
    "tips": [
        "`sqrt` is the rookie trap. Compare `x² + y²` directly — simpler, faster, and avoids floating-point precision issues entirely.",
        "Python's `heapq` is a min-heap. For 'farthest of k closest' semantics you want a max-heap — negate the key, or store `(-d2, point)` tuples.",
        "Quickselect's worst case is O(n²) on adversarial inputs; randomising the pivot (or shuffling the array up front) makes the expected case dominate.",
        "Java's `PriorityQueue` is a min-heap by default — supply a reversed comparator for the max-heap variant.",
        "Streaming follow-up: 'points arrive one at a time, return current top-k anytime' → max-heap of size k, the same data structure.",
        "If the interviewer asks for 'k farthest' instead, flip the heap's comparator (or sort descending). Same algorithm.",
    ],
    "companies": ["Amazon", "Facebook", "Google", "Microsoft", "LinkedIn", "Uber"],
    "topics": ["Array", "Math", "Heap", "Quickselect", "Sorting", "Divide and Conquer"],
    "time_complexity": "O(n log k)",
    "space_complexity": "O(k)",
}


def REFERENCE(points, k):
    import heapq
    heap = []  # max-heap via negated key
    for x, y in points:
        d2 = x * x + y * y
        if len(heap) < k:
            heapq.heappush(heap, (-d2, [x, y]))
        elif -heap[0][0] > d2:
            heapq.heapreplace(heap, (-d2, [x, y]))
    return [p for _, p in heap]


register(PAYLOAD, REFERENCE)
