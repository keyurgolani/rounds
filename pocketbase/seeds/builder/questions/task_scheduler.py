"""Task Scheduler — Medium. Greedy / Counting / Heap.

The 'frame construction' classic. Two clean approaches: a one-line math
formula (count the most-frequent task, build the frame, fill the gaps),
and a max-heap simulation that mirrors the real CPU schedule. The
formula is the optimal answer; the heap is the explanation when the
interviewer asks 'why does that work?'.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Task Scheduler",
    "difficulty": "Medium",
    "description": (
        "You are given an array of CPU `tasks`, each represented by a character, and a non-negative integer "
        "`n`. Each task takes one CPU interval. For each interval, the CPU can either complete one task or "
        "stay idle.\n\n"
        "However, there is a constraint: identical tasks must be separated by **at least `n` intervals** of "
        "other tasks or idle time. Return the **minimum number of CPU intervals** required to finish all "
        "tasks.\n\n"
        "**Example 1:**\n"
        "- Input: `tasks = [\"A\",\"A\",\"A\",\"B\",\"B\",\"B\"]`, `n = 2`\n"
        "- Output: `8`\n"
        "- Explanation: A valid schedule is `A B idle A B idle A B`. Two `A`s must be separated by 2 "
        "intervals; the same for `B`. Total intervals = 8.\n\n"
        "**Example 2:**\n"
        "- Input: `tasks = [\"A\",\"A\",\"A\",\"B\",\"B\",\"B\"]`, `n = 0`\n"
        "- Output: `6`\n"
        "- Explanation: With no cooldown, just run them back to back: `A A A B B B`.\n\n"
        "**Example 3:**\n"
        "- Input: `tasks = [\"A\",\"A\",\"A\",\"A\",\"A\",\"A\",\"B\",\"C\",\"D\",\"E\",\"F\",\"G\"]`, `n = 2`\n"
        "- Output: `16`\n"
        "- Explanation: One valid schedule is `A B C A D E A F G A idle idle A idle idle A`. The six `A`s "
        "drive the answer: 5 gaps of size 3 between `A`s, plus the final `A`."
    ),
    "hints": [
        "Only the **frequencies** of tasks matter — not which letters they are. Reduce the input to a count of 26 buckets.",
        "Picture a 'frame' built around the most frequent task. If it appears `maxFreq` times, you have `maxFreq - 1` gaps, each of size `n + 1` (the task itself plus `n` slots after it), then a final occurrence.",
        "Frame length = `(maxFreq - 1) * (n + 1) + countOfMaxFreq`, where `countOfMaxFreq` is how many distinct tasks tie for the maximum frequency (they each fill the trailing slot of every gap, and one trailing slot at the end).",
        "If `len(tasks)` already exceeds the frame, there are no idle slots: the answer is just `len(tasks)`. Final formula: `max(frame_length, len(tasks))`.",
        "Alternative: simulate with a max-heap of frequencies. Each round, pop up to `n + 1` tasks, decrement and re-push the non-zero ones. Total intervals = sum of round lengths.",
    ],
    "constraints": [
        "1 <= tasks.length <= 10⁴",
        "tasks[i] is an uppercase English letter",
        "0 <= n <= 100",
    ],
    "starter_code": {
        "python": "def least_interval(tasks, n):\n    # Your code here\n    pass",
        "javascript": "function leastInterval(tasks, n) {\n    // Your code here\n}",
        "java": "public int leastInterval(char[] tasks, int n) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        ([\"A\",\"A\",\"A\",\"B\",\"B\",\"B\"], 2),\n"
            "        ([\"A\",\"A\",\"A\",\"B\",\"B\",\"B\"], 0),\n"
            "        ([\"A\",\"A\",\"A\",\"A\",\"A\",\"A\",\"B\",\"C\",\"D\",\"E\",\"F\",\"G\"], 2),\n"
            "    ]\n"
            "    for tasks, n in cases:\n"
            "        print(f\"least_interval({tasks}, {n}) = {least_interval(tasks, n)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\n"
            "    [[\"A\",\"A\",\"A\",\"B\",\"B\",\"B\"], 2],\n"
            "    [[\"A\",\"A\",\"A\",\"B\",\"B\",\"B\"], 0],\n"
            "].forEach(([tasks, n]) =>\n"
            "    console.log(`leastInterval =`, leastInterval(tasks, n))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.leastInterval(new char[]{'A','A','A','B','B','B'}, 2));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"tasks": ["A", "A", "A", "B", "B", "B"], "n": 2}, "expected": 8,
         "description": "Classic example: two cooldown slots, two tied max-freq tasks", "tags": ["basic"]},
        {"input": {"tasks": ["A", "A", "A", "B", "B", "B"], "n": 0}, "expected": 6,
         "description": "No cooldown — answer is just len(tasks)", "tags": ["basic"]},
        {"input": {"tasks": ["A"], "n": 5}, "expected": 1,
         "description": "Single task — cooldown is irrelevant", "tags": ["edge"]},
        {"input": {"tasks": ["A", "A", "A", "A"], "n": 3}, "expected": 13,
         "description": "All same task: 3 gaps of size 4, plus the last A → (4-1)*(3+1) + 1 = 13",
         "tags": ["edge"]},
        {"input": {"tasks": ["A", "B", "C", "D", "E", "F"], "n": 2}, "expected": 6,
         "description": "Many distinct tasks, small cooldown — len(tasks) dominates",
         "tags": ["tricky"]},
        {"input": {"tasks": ["A", "A", "A", "A", "A", "A", "B", "C", "D", "E", "F", "G"], "n": 2},
         "expected": 16,
         "description": "LeetCode example: one max-freq task forces idles",
         "tags": ["basic"]},
        {"input": {"tasks": ["A", "A", "A", "B", "B", "B", "C", "C", "C"], "n": 2}, "expected": 9,
         "description": "Three tied max-freq — frame fills perfectly, no idles",
         "tags": ["tricky"]},
        {"input": {"tasks": ["A", "A", "B", "B"], "n": 100}, "expected": 103,
         "description": "n much larger than distinct tasks — long idle stretches: (2-1)*101 + 2 = 103",
         "tags": ["edge"]},
        {"input": {"tasks": ["A", "A", "A", "B", "B", "C", "C"], "n": 2}, "expected": 7,
         "description": "len(tasks) ties the frame length — answer = 7",
         "tags": ["tricky"]},
        {"input": {"tasks": ["A", "B"], "n": 0}, "expected": 2,
         "description": "Two distinct tasks, no cooldown", "tags": ["edge"]},
        {"input": {"tasks": ["A"] * 1000 + ["B"] * 999, "n": 2}, "expected": 2998,
         "description": "Large input — frame (999*3 + 1 = 2998) just edges out len(tasks)=1999",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Counting / Math Formula (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Count task frequencies. Let `maxFreq` be the highest, and `tied` be how many tasks share "
                "that frequency. Build a frame: `(maxFreq - 1)` rows of width `n + 1`, plus a final row of "
                "`tied` slots. The frame length is `(maxFreq - 1) * (n + 1) + tied`. If the actual number "
                "of tasks already exceeds that frame, there are no idle slots and the answer is "
                "`len(tasks)`. Take the max of the two."
            ),
            "code": {
                "python": (
                    "from collections import Counter\n\n"
                    "def least_interval(tasks, n):\n"
                    "    counts = Counter(tasks)\n"
                    "    max_freq = max(counts.values())\n"
                    "    tied = sum(1 for c in counts.values() if c == max_freq)\n"
                    "    frame = (max_freq - 1) * (n + 1) + tied\n"
                    "    return max(frame, len(tasks))"
                ),
                "javascript": (
                    "function leastInterval(tasks, n) {\n"
                    "    const counts = new Map();\n"
                    "    for (const t of tasks) counts.set(t, (counts.get(t) || 0) + 1);\n"
                    "    let maxFreq = 0;\n"
                    "    for (const c of counts.values()) if (c > maxFreq) maxFreq = c;\n"
                    "    let tied = 0;\n"
                    "    for (const c of counts.values()) if (c === maxFreq) tied++;\n"
                    "    const frame = (maxFreq - 1) * (n + 1) + tied;\n"
                    "    return Math.max(frame, tasks.length);\n"
                    "}"
                ),
                "java": (
                    "public int leastInterval(char[] tasks, int n) {\n"
                    "    int[] counts = new int[26];\n"
                    "    for (char t : tasks) counts[t - 'A']++;\n"
                    "    int maxFreq = 0;\n"
                    "    for (int c : counts) if (c > maxFreq) maxFreq = c;\n"
                    "    int tied = 0;\n"
                    "    for (int c : counts) if (c == maxFreq) tied++;\n"
                    "    int frame = (maxFreq - 1) * (n + 1) + tied;\n"
                    "    return Math.max(frame, tasks.length);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Greedy Max-Heap Simulation",
            "time_complexity": "O(n log 26) ≈ O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Push every non-zero frequency into a max-heap. Each round, pop up to `n + 1` of the "
                "largest-remaining tasks (so no two of the same task can collide), decrement them, and "
                "re-push any that still have remaining count. If the heap empties before the round is "
                "full *and* tasks still remain, those leftover slots are idle. Sum the round lengths."
            ),
            "code": {
                "python": (
                    "import heapq\n"
                    "from collections import Counter\n\n"
                    "def least_interval(tasks, n):\n"
                    "    heap = [-c for c in Counter(tasks).values()]\n"
                    "    heapq.heapify(heap)\n"
                    "    intervals = 0\n"
                    "    while heap:\n"
                    "        used = []\n"
                    "        for _ in range(n + 1):\n"
                    "            if heap:\n"
                    "                used.append(heapq.heappop(heap) + 1)  # one fewer (negatives)\n"
                    "        for u in used:\n"
                    "            if u < 0:\n"
                    "                heapq.heappush(heap, u)\n"
                    "        intervals += (n + 1) if heap else len(used)\n"
                    "    return intervals"
                ),
                "javascript": (
                    "// Sketch — JS lacks a built-in heap; sort each round.\n"
                    "function leastInterval(tasks, n) {\n"
                    "    const counts = new Map();\n"
                    "    for (const t of tasks) counts.set(t, (counts.get(t) || 0) + 1);\n"
                    "    let freqs = [...counts.values()];\n"
                    "    let intervals = 0;\n"
                    "    while (freqs.length) {\n"
                    "        freqs.sort((a, b) => b - a);\n"
                    "        const take = Math.min(n + 1, freqs.length);\n"
                    "        for (let i = 0; i < take; i++) freqs[i]--;\n"
                    "        freqs = freqs.filter(x => x > 0);\n"
                    "        intervals += freqs.length ? n + 1 : take;\n"
                    "    }\n"
                    "    return intervals;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Brute-force search over schedules is exponential — don't go there.",
        "2. Realise only frequencies matter: which letters they are is irrelevant. Reduce to a frequency multiset.",
        "3. The bottleneck is the most frequent task. If `A` appears `k` times with cooldown `n`, you need at least `(k - 1) * (n + 1) + 1` intervals just for the `A`s.",
        "4. Generalise: if multiple tasks tie at frequency `k`, each adds one to the trailing row → `(k - 1) * (n + 1) + tied`.",
        "5. Idle slots only appear when the frame is wider than `len(tasks)`. Otherwise the schedule packs perfectly: answer is `len(tasks)`.",
        "6. Final formula: `max((maxFreq - 1) * (n + 1) + tied, len(tasks))`.",
        "7. To explain *why* the formula is achievable, describe the heap simulation: pop the largest each round and re-push, which constructs an explicit valid schedule.",
    ],
    "tips": [
        "Don't be intimidated by 'scheduling' problems. This one boils down to a 26-bucket histogram — counts, not characters.",
        "When you draw the frame on a whiteboard, the formula is obvious. Always sketch a 6-A-3-B example before reaching for code.",
        "The `tied` term (`countOfMaxFreq`) is the part candidates miss. If you forget it, you'll fail the `[\"A\",\"A\",\"B\",\"B\"], n=2` style cases.",
        "The `max(frame, len(tasks))` clamp handles the 'so many distinct tasks the cooldown never triggers' case. Don't omit it.",
        "Be ready for the follow-up 'reorder tasks freely?' (this problem) vs 'preserve order?' (Task Scheduler II). Different problem entirely — the second one needs a hashmap of next-allowed times.",
        "Heap solution is O(n log 26) — i.e. O(n). Don't claim O(n log n) unless the alphabet is unbounded.",
    ],
    "companies": ["Facebook", "Amazon", "Microsoft", "Google", "LinkedIn", "Bloomberg"],
    "topics": ["Array", "Hash Table", "Greedy", "Heap (Priority Queue)", "Counting"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(tasks, n):
    from collections import Counter
    counts = Counter(tasks)
    max_freq = max(counts.values())
    tied = sum(1 for c in counts.values() if c == max_freq)
    frame = (max_freq - 1) * (n + 1) + tied
    return max(frame, len(tasks))


register(PAYLOAD, REFERENCE)
