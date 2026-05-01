"""Find Median from Data Stream — Hard. Two Heaps / Design.

The canonical 'two heaps' problem. Maintain a max-heap of the lower
half and a min-heap of the upper half, rebalanced after each insert
so their sizes differ by at most 1. Median is either the top of the
larger heap (odd count) or the average of both tops (even count).
Each `addNum` is O(log n); `findMedian` is O(1)."""
from builder.registry import register


PAYLOAD = {
    "title": "Find Median from Data Stream",
    "difficulty": "Hard",
    "description": (
        "The **median** is the middle value in an ordered integer list. If the size of the list is even, "
        "the median is the average of the two middle values.\n\n"
        "Implement the `MedianFinder` class:\n"
        "- `MedianFinder()` — initialize the data structure.\n"
        "- `addNum(num)` — add an integer `num` from the data stream to the structure.\n"
        "- `findMedian()` — return the median of all elements added so far (as a float).\n\n"
        "**Example 1:**\n"
        "```\n"
        "MedianFinder mf = new MedianFinder();\n"
        "mf.addNum(1);          // arr = [1]\n"
        "mf.addNum(2);          // arr = [1, 2]\n"
        "mf.findMedian();       // → 1.5\n"
        "mf.addNum(3);          // arr = [1, 2, 3]\n"
        "mf.findMedian();       // → 2.0\n"
        "```\n\n"
        "**Example 2:**\n"
        "```\n"
        "MedianFinder mf = new MedianFinder();\n"
        "mf.addNum(-1);         // arr = [-1]\n"
        "mf.findMedian();       // → -1.0\n"
        "mf.addNum(-2);         // arr = [-2, -1]\n"
        "mf.findMedian();       // → -1.5\n"
        "```"
    ),
    "hints": [
        "Keep two heaps: a **max-heap `lo`** for the lower half and a **min-heap `hi`** for the upper half. The median lies at one or both of their tops.",
        "Maintain the invariant `len(lo) == len(hi)` or `len(lo) == len(hi) + 1`. The larger heap (or either, if equal) holds the median candidate.",
        "On each `addNum`: push to `lo` (negating for max-heap behaviour in Python's `heapq`), pop its top and push to `hi`, then rebalance if `hi` has grown larger than `lo`.",
        "`findMedian` is O(1): if sizes are equal, return `(lo.top + hi.top) / 2`; otherwise return the top of the larger heap.",
        "Sorted-list insertion (`bisect.insort`) is conceptually simple but O(n) per add due to the shift — fails at scale. Two heaps is the textbook answer.",
    ],
    "constraints": [
        "-10⁵ <= num <= 10⁵",
        "There will be at least one element in the data structure before `findMedian` is called.",
        "At most 5 * 10⁴ calls to `addNum` and `findMedian`.",
    ],
    "starter_code": {
        "python": (
            "class MedianFinder:\n"
            "    def __init__(self):\n"
            "        pass\n"
            "    def addNum(self, num):\n"
            "        pass\n"
            "    def findMedian(self):\n"
            "        pass"
        ),
        "javascript": (
            "class MedianFinder {\n"
            "    constructor() { /* ... */ }\n"
            "    addNum(num) { /* ... */ }\n"
            "    findMedian() { /* ... */ }\n"
            "}"
        ),
        "java": (
            "class MedianFinder {\n"
            "    public MedianFinder() {}\n"
            "    public void addNum(int num) {}\n"
            "    public double findMedian() { return 0.0; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    mf = MedianFinder()\n"
            "    mf.addNum(1)\n"
            "    mf.addNum(2)\n"
            "    print(mf.findMedian())  # 1.5\n"
            "    mf.addNum(3)\n"
            "    print(mf.findMedian())  # 2.0"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["MedianFinder", "addNum", "addNum", "findMedian", "addNum", "findMedian"],
                   "args": [[], [1], [2], [], [3], []]},
         "expected": [None, None, None, 1.5, None, 2.0],
         "description": "Standard sequence — 1.5 then 2.0", "tags": ["basic"]},
        {"input": {"ops": ["MedianFinder", "addNum", "findMedian"],
                   "args": [[], [42], []]},
         "expected": [None, None, 42.0],
         "description": "Single element — median is itself", "tags": ["edge"]},
        {"input": {"ops": ["MedianFinder", "addNum", "addNum", "addNum", "addNum", "addNum", "findMedian"],
                   "args": [[], [1], [2], [3], [4], [5], []]},
         "expected": [None, None, None, None, None, None, 3.0],
         "description": "Ascending stream — median = 3", "tags": ["basic"]},
        {"input": {"ops": ["MedianFinder", "addNum", "addNum", "addNum", "addNum", "findMedian"],
                   "args": [[], [10], [8], [6], [4], []]},
         "expected": [None, None, None, None, None, 7.0],
         "description": "Descending stream — median = (6 + 8) / 2", "tags": ["basic"]},
        {"input": {"ops": ["MedianFinder", "addNum", "addNum", "addNum", "addNum", "findMedian", "addNum", "findMedian"],
                   "args": [[], [5], [5], [5], [5], [], [5], []]},
         "expected": [None, None, None, None, None, 5.0, None, 5.0],
         "description": "Duplicates — all 5s, median stays 5", "tags": ["edge"]},
        {"input": {"ops": ["MedianFinder", "addNum", "addNum", "addNum", "findMedian", "addNum", "findMedian"],
                   "args": [[], [-3], [-1], [-2], [], [-4], []]},
         "expected": [None, None, None, None, -2.0, None, -2.5],
         "description": "Negatives — sorted [-3,-2,-1] median -2; then [-4,-3,-2,-1] median -2.5", "tags": ["edge"]},
        {"input": {"ops": ["MedianFinder", "addNum", "addNum", "findMedian", "addNum", "addNum", "findMedian",
                            "addNum", "findMedian", "addNum", "findMedian"],
                   "args": [[], [6], [10], [], [2], [6], [], [5], [], [0], []]},
         "expected": [None, None, None, 8.0, None, None, 6.0, None, 6.0, None, 5.5],
         "description": "Many adds with periodic findMedian", "tags": ["tricky"]},
        {"input": {"ops": ["MedianFinder", "addNum", "addNum", "addNum", "addNum", "addNum", "addNum",
                            "findMedian", "addNum", "findMedian"],
                   "args": [[], [1], [100], [2], [99], [3], [98], [], [50], []]},
         "expected": [None, None, None, None, None, None, None, 50.5, None, 50.0],
         "description": "Mixed extremes — even then odd count", "tags": ["tricky"]},
        {"input": {"ops": ["MedianFinder", "addNum", "addNum", "findMedian"],
                   "args": [[], [-100000], [100000], []]},
         "expected": [None, None, None, 0.0],
         "description": "Min and max of range — median is 0", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Two Heaps (Optimal)",
            "time_complexity": "O(log n) per addNum, O(1) per findMedian",
            "space_complexity": "O(n)",
            "description": (
                "Maintain `lo` as a max-heap of the lower half and `hi` as a min-heap of the upper half. "
                "Invariant: `len(lo) == len(hi)` or `len(lo) == len(hi) + 1`. On `addNum`, push to `lo` "
                "first (negate for Python's min-heap), then move its top to `hi` to ensure `lo`'s max ≤ "
                "`hi`'s min. If `hi` has grown larger than `lo`, move its top back. Median is `lo`'s top "
                "(odd count) or the average of both tops (even count)."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "class MedianFinder:\n"
                    "    def __init__(self):\n"
                    "        self.lo = []  # max-heap (negated)\n"
                    "        self.hi = []  # min-heap\n"
                    "    def addNum(self, num):\n"
                    "        heapq.heappush(self.lo, -num)\n"
                    "        heapq.heappush(self.hi, -heapq.heappop(self.lo))\n"
                    "        if len(self.hi) > len(self.lo):\n"
                    "            heapq.heappush(self.lo, -heapq.heappop(self.hi))\n"
                    "    def findMedian(self):\n"
                    "        if len(self.lo) > len(self.hi):\n"
                    "            return float(-self.lo[0])\n"
                    "        return (-self.lo[0] + self.hi[0]) / 2.0"
                ),
                "javascript": (
                    "// Sketch: use two priority queues (max-heap lo, min-heap hi).\n"
                    "// JS lacks a native heap; bring a small MinHeap class and use negation for the max-heap.\n"
                    "class MedianFinder {\n"
                    "    constructor() { this.lo = new MaxHeap(); this.hi = new MinHeap(); }\n"
                    "    addNum(num) {\n"
                    "        this.lo.push(num);\n"
                    "        this.hi.push(this.lo.pop());\n"
                    "        if (this.hi.size() > this.lo.size()) this.lo.push(this.hi.pop());\n"
                    "    }\n"
                    "    findMedian() {\n"
                    "        if (this.lo.size() > this.hi.size()) return this.lo.peek();\n"
                    "        return (this.lo.peek() + this.hi.peek()) / 2;\n"
                    "    }\n"
                    "}"
                ),
                "java": (
                    "import java.util.PriorityQueue;\n\n"
                    "class MedianFinder {\n"
                    "    private final PriorityQueue<Integer> lo = new PriorityQueue<>((a, b) -> b - a);\n"
                    "    private final PriorityQueue<Integer> hi = new PriorityQueue<>();\n"
                    "    public void addNum(int num) {\n"
                    "        lo.offer(num);\n"
                    "        hi.offer(lo.poll());\n"
                    "        if (hi.size() > lo.size()) lo.offer(hi.poll());\n"
                    "    }\n"
                    "    public double findMedian() {\n"
                    "        if (lo.size() > hi.size()) return lo.peek();\n"
                    "        return (lo.peek() + hi.peek()) / 2.0;\n"
                    "    }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sorted Array via Insertion (Less Optimal)",
            "time_complexity": "O(n) per addNum (shift), O(1) per findMedian",
            "space_complexity": "O(n)",
            "description": (
                "Maintain a sorted list. Use `bisect.insort` to insert each new number in O(log n) for the "
                "search but O(n) for the shift. `findMedian` is O(1) by indexing the middle. Mention as a "
                "baseline; fails at n = 5*10⁴ calls in tight loops."
            ),
            "code": {
                "python": (
                    "from bisect import insort\n\n"
                    "class MedianFinder:\n"
                    "    def __init__(self):\n"
                    "        self.arr = []\n"
                    "    def addNum(self, num):\n"
                    "        insort(self.arr, num)\n"
                    "    def findMedian(self):\n"
                    "        n = len(self.arr)\n"
                    "        if n % 2:\n"
                    "            return float(self.arr[n // 2])\n"
                    "        return (self.arr[n // 2 - 1] + self.arr[n // 2]) / 2.0"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Naive: store all numbers, sort on each `findMedian` → O(n log n) per query. Too slow.",
        "2. Better: keep the array sorted on insert via `bisect.insort` → O(n) per add (shift). Better but still linear.",
        "3. Key insight: the median only depends on the **middle one or two elements**. We don't need the rest sorted — just partitioned.",
        "4. Two heaps: max-heap of lower half, min-heap of upper half. Tops give the median in O(1).",
        "5. Insertion: push to `lo`, immediately move its top to `hi` (this enforces `max(lo) <= min(hi)`), then rebalance sizes.",
        "6. Edge cases: single element (odd-count branch), duplicates (heaps handle naturally), negatives (no special case in heap ordering).",
    ],
    "tips": [
        "Python's `heapq` is a min-heap only. For the max-heap on `lo`, push the **negated** value and negate again on read.",
        "The 'push to lo, move top to hi, rebalance if hi too big' pattern is the cleanest — don't try to branch on which heap to push to based on the value; the move-and-rebalance always converges.",
        "Java: `PriorityQueue` defaults to a min-heap; use a comparator `(a, b) -> b - a` for the max-heap.",
        "When sizes are equal, return the **average** as a float (`(lo + hi) / 2.0`), not integer division.",
        "Common follow-up — '99% of numbers are in [0, 100]'. Use a bucket array of size 101 for the dense range plus two heaps for outliers.",
        "Common follow-up — 'support removal too'. Use a 'lazy deletion' hashmap: mark removed values, lazy-pop heap tops that match.",
    ],
    "companies": ["Amazon", "Google", "Facebook", "Bloomberg", "Microsoft", "Uber"],
    "topics": ["Heap", "Two Heaps", "Design", "Data Stream"],
    "time_complexity": "O(log n) per addNum, O(1) per findMedian",
    "space_complexity": "O(n)",
}


def REFERENCE(input):
    """Class-ops driver: replay the operation sequence using two heaps."""
    import heapq

    class MedianFinder:
        def __init__(self):
            self.lo = []  # max-heap (negated values)
            self.hi = []  # min-heap

        def addNum(self, num):
            heapq.heappush(self.lo, -num)
            heapq.heappush(self.hi, -heapq.heappop(self.lo))
            if len(self.hi) > len(self.lo):
                heapq.heappush(self.lo, -heapq.heappop(self.hi))

        def findMedian(self):
            if len(self.lo) > len(self.hi):
                return float(-self.lo[0])
            return (-self.lo[0] + self.hi[0]) / 2.0

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "MedianFinder":
            instance = MedianFinder()
            results.append(None)
        else:
            method = getattr(instance, op)
            ret = method(*a)
            results.append(ret)
    return results


# Add the entry field for class_ops dispatch
PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "MedianFinder",
    "constructor": {"params": []},
    "methods": [
        {"name": "addNum", "params": [{"name": "num", "type": "int"}], "returns": "any"},
        {"name": "findMedian", "params": [], "returns": "float"},
    ],
}


register(PAYLOAD, REFERENCE)
