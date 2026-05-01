"""Merging K Sorted Data Streams — Medium. Heap / Streaming.

Process orders streaming in from K fulfillment-center sources, sorted
by promised delivery date. Max-priority output is the next-due across
all streams. Heap of stream heads + lazy refill is the canonical
streaming K-way merge."""
from builder.registry import register


PAYLOAD = {
    "title": "Merging K Sorted Data Streams (Streaming)",
    "difficulty": "Medium",
    "description": (
        "An Amazon fulfillment center receives a constant influx of orders from K different sources. Each "
        "source emits orders **already sorted** by promised delivery date (earlier = higher priority). "
        "Process the combined stream in priority order — earliest delivery first — without buffering all "
        "orders.\n\n"
        "**Test framing:** for offline testing, K input arrays are given. Return the merged sequence. The "
        "real-world constraint is that each input may be much larger than memory and arrives over time; "
        "your algorithm must consume each source lazily and never hold more than K items in memory at "
        "once.\n\n"
        "**Example:**\n"
        "- Input: `streams = [[1, 4, 7], [2, 5, 8], [3, 6, 9]]`\n"
        "- Output: `[1, 2, 3, 4, 5, 6, 7, 8, 9]`"
    ),
    "hints": [
        "Same algorithm as K-way merge: min-heap of (current value, source index, position).",
        "Streaming-friendly: at any moment the heap holds at most K items — one per active source. Memory is bounded by K, not the total volume.",
        "On pop, refill from the same source. If that source is exhausted, simply don't push.",
        "If sources arrive over time and may emit slowly, you might need a 'wait for any source' primitive — that's outside pure data-structure territory and into concurrency.",
        "Edge cases: empty stream list, all empty streams, single stream, very uneven stream lengths.",
    ],
    "constraints": [
        "0 <= K <= 10⁴",
        "Total orders across all streams: 0 to 10⁵",
    ],
    "starter_code": {
        "python": "def merge_streams(streams):\n    # Your code here\n    pass",
        "javascript": "function mergeStreams(streams) {\n    // Your code here\n}",
        "java": "public int[] mergeStreams(int[][] streams) {\n    // Your code here\n    return new int[]{};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(merge_streams([[1,4,7],[2,5,8],[3,6,9]]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"streams": [[1, 4, 7], [2, 5, 8], [3, 6, 9]]},
         "expected": [1, 2, 3, 4, 5, 6, 7, 8, 9],
         "description": "Three round-robin streams", "tags": ["basic"]},
        {"input": {"streams": [[]]}, "expected": [],
         "description": "Single empty stream", "tags": ["edge"]},
        {"input": {"streams": []}, "expected": [],
         "description": "No streams at all", "tags": ["edge"]},
        {"input": {"streams": [[1, 2, 3], [], [4, 5]]},
         "expected": [1, 2, 3, 4, 5],
         "description": "Mixed empty and non-empty streams", "tags": ["edge"]},
        {"input": {"streams": [[1], [1], [1]]}, "expected": [1, 1, 1],
         "description": "All-equal heads", "tags": ["edge"]},
        {"input": {"streams": [[i * 3 for i in range(10)],
                                [i * 3 + 1 for i in range(10)],
                                [i * 3 + 2 for i in range(10)]]},
         "expected": list(range(30)),
         "description": "Three interleaved streams of 10 each", "tags": ["large"]},
        {"input": {"streams": [list(range(100))]}, "expected": list(range(100)),
         "description": "Single stream — reduces to identity", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Streaming K-Way Merge with Min-Heap (Optimal)",
            "time_complexity": "O(N log K) where N is total elements",
            "space_complexity": "O(K)",
            "description": (
                "Initialise a min-heap with the head of each non-empty stream as `(value, source, "
                "next_index)`. Pop the smallest, append to output, push the next from the same source if "
                "any. Memory is bounded by K — works for streams that don't fit in memory."
            ),
            "code": {
                "python": (
                    "import heapq\n\n"
                    "def merge_streams(streams):\n"
                    "    heap = []\n"
                    "    for i, st in enumerate(streams):\n"
                    "        if st:\n"
                    "            heapq.heappush(heap, (st[0], i, 0))\n"
                    "    out = []\n"
                    "    while heap:\n"
                    "        val, src, idx = heapq.heappop(heap)\n"
                    "        out.append(val)\n"
                    "        if idx + 1 < len(streams[src]):\n"
                    "            heapq.heappush(heap, (streams[src][idx + 1], src, idx + 1))\n"
                    "    return out"
                ),
                "javascript": (
                    "function mergeStreams(streams) {\n"
                    "    const heap = [];\n"
                    "    const swap = (i, j) => { [heap[i], heap[j]] = [heap[j], heap[i]]; };\n"
                    "    const up = i => { while (i > 0) { const p = (i-1)>>1; if (heap[p][0] <= heap[i][0]) break; swap(i, p); i = p; } };\n"
                    "    const down = i => { const n = heap.length; while (true) { const l = 2*i+1, r = 2*i+2; let s = i; if (l < n && heap[l][0] < heap[s][0]) s = l; if (r < n && heap[r][0] < heap[s][0]) s = r; if (s === i) break; swap(i, s); i = s; } };\n"
                    "    for (let i = 0; i < streams.length; i++) if (streams[i].length) { heap.push([streams[i][0], i, 0]); up(heap.length - 1); }\n"
                    "    const out = [];\n"
                    "    while (heap.length) {\n"
                    "        const [v, s, j] = heap[0];\n"
                    "        out.push(v);\n"
                    "        if (j + 1 < streams[s].length) { heap[0] = [streams[s][j+1], s, j+1]; down(0); }\n"
                    "        else { swap(0, heap.length - 1); heap.pop(); down(0); }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Reframe: 'K sorted sources, want a single sorted output, in bounded memory.' Heap of stream heads, K-way merge.",
        "2. Memory bound is K — independent of total stream size. That's the streaming property.",
        "3. Pop the smallest, refill from the same source. Streams that run dry just stop contributing.",
        "4. If sources are truly streaming (not pre-materialised arrays), the same heap algorithm applies — replace `streams[src][idx + 1]` with `next(stream_iterator[src])`.",
        "5. Discuss back-pressure: if one source is much faster than others, you may need to throttle on the slower ones.",
        "6. Edge cases: zero streams, all-empty, single stream, very uneven sizes, all-equal heads.",
    ],
    "tips": [
        "Don't preload every element into the heap — that defeats the purpose. Preload only one head per stream.",
        "Tuple comparison breaks ties cleanly: (value, source_index, _) — equal values fall back to source order, which is deterministic.",
        "If you can't extract the head without consuming it (true streams), use a queue-of-iterators and maintain a parallel 'current head' array.",
        "Common follow-up: 'streams emit at different rates / can fail.' Add a timeout per source; mark sources as exhausted on persistent failure.",
        "Common follow-up: 'merge sorted log files from disk.' This IS the inner loop of external merge sort.",
    ],
    "companies": ["Amazon", "Google", "LinkedIn", "Bloomberg"],
    "topics": ["Heap", "Merge", "Streaming", "K-way Merge"],
    "time_complexity": "O(N log K)",
    "space_complexity": "O(K)",
}


def REFERENCE(streams):
    import heapq
    heap = []
    for i, st in enumerate(streams):
        if st:
            heapq.heappush(heap, (st[0], i, 0))
    out = []
    while heap:
        val, src, idx = heapq.heappop(heap)
        out.append(val)
        if idx + 1 < len(streams[src]):
            heapq.heappush(heap, (streams[src][idx + 1], src, idx + 1))
    return out


register(PAYLOAD, REFERENCE)
