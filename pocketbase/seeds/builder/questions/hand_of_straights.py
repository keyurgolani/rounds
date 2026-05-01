"""Hand of Straights — Medium. Greedy / Hash Map / Heap.

Given a multiset of cards, can you partition into runs of `groupSize`
consecutive integers? The greedy insight: the smallest remaining card
*must* be the start of some run (nothing smaller exists to extend down
into it). So peel off `groupSize` consecutive starting there, repeat.
A min-heap or a sorted Counter walk implements that cleanly in
O(n log n).
"""
from builder.registry import register


PAYLOAD = {
    "title": "Hand of Straights",
    "difficulty": "Medium",
    "description": (
        "Alice has a `hand` of cards, given as an array of integers. She wants to rearrange the cards "
        "into groups so that **each group is of size `groupSize`**, and **consists of `groupSize` "
        "consecutive cards**.\n\n"
        "Given an integer array `hand` and an integer `groupSize`, return `true` if she can rearrange "
        "the cards, or `false` otherwise.\n\n"
        "**Example 1:**\n"
        "- Input: `hand = [1,2,3,6,2,3,4,7,8]`, `groupSize = 3`\n"
        "- Output: `true`\n"
        "- Explanation: Alice's hand can be rearranged as `[1,2,3]`, `[2,3,4]`, `[6,7,8]`.\n\n"
        "**Example 2:**\n"
        "- Input: `hand = [1,2,3,4,5]`, `groupSize = 4`\n"
        "- Output: `false`\n"
        "- Explanation: Alice's hand cannot be rearranged into groups of `4`."
    ),
    "hints": [
        "Quick reject: if `len(hand) % groupSize != 0` it is impossible — return `false` immediately.",
        "Count the occurrences of every card value with a hash map / `Counter`.",
        "Greedy lemma: the **smallest** remaining card must be the start of a run. Nothing smaller exists to "
        "extend into it, so it cannot be the 2nd, 3rd, … card of any group.",
        "From that smallest value `v`, peel off one copy of `v, v+1, …, v+groupSize-1`. If any count is "
        "missing, return `false`. Otherwise decrement and repeat.",
        "Use a **min-heap** (or sorted keys + counter) so 'find the smallest remaining card' is O(log n) "
        "per group rather than O(n).",
    ],
    "constraints": [
        "1 <= hand.length <= 10⁴",
        "0 <= hand[i] <= 10⁹",
        "1 <= groupSize <= hand.length; if `hand.length % groupSize != 0`, the answer is `false`.",
    ],
    "starter_code": {
        "python": (
            "def is_n_straight_hand(hand, groupSize):\n"
            "    # Your code here\n"
            "    pass"
        ),
        "javascript": (
            "function isNStraightHand(hand, groupSize) {\n"
            "    // Your code here\n"
            "}"
        ),
        "java": (
            "public boolean isNStraightHand(int[] hand, int groupSize) {\n"
            "    // Your code here\n"
            "    return false;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([1,2,3,6,2,3,4,7,8], 3), ([1,2,3,4,5], 4), ([1,1,2,2,3,3], 2)]\n"
            "    for hand, gs in cases:\n"
            "        print(f\"is_n_straight_hand({hand}, {gs}) = {is_n_straight_hand(hand, gs)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,2,3,6,2,3,4,7,8], 3], [[1,2,3,4,5], 4]].forEach(([hand, gs]) =>\n"
            "    console.log(`isNStraightHand =`, isNStraightHand(hand, gs))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.isNStraightHand(new int[]{1,2,3,6,2,3,4,7,8}, 3));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"hand": [1, 2, 3, 6, 2, 3, 4, 7, 8], "groupSize": 3}, "expected": True,
         "description": "Classic: [1,2,3], [2,3,4], [6,7,8]", "tags": ["basic"]},
        {"input": {"hand": [1, 2, 3, 4, 5], "groupSize": 4}, "expected": False,
         "description": "Length 5 is not divisible by groupSize 4", "tags": ["basic"]},
        {"input": {"hand": [1, 2, 3, 4, 5], "groupSize": 1}, "expected": True,
         "description": "groupSize 1 — every singleton is a valid 'run'", "tags": ["edge"]},
        {"input": {"hand": [1, 2, 3, 4, 5], "groupSize": 5}, "expected": True,
         "description": "groupSize equals length, values are consecutive — single run", "tags": ["edge"]},
        {"input": {"hand": [1, 2, 3, 4, 6], "groupSize": 5}, "expected": False,
         "description": "groupSize equals length but values are not consecutive (5 missing)", "tags": ["edge"]},
        {"input": {"hand": [1, 1, 2, 2, 3, 3], "groupSize": 3}, "expected": True,
         "description": "Duplicates that align — two copies of [1,2,3]", "tags": ["tricky"]},
        {"input": {"hand": [1, 1, 2, 2, 3, 4], "groupSize": 3}, "expected": False,
         "description": "Duplicates that misalign — [1,2,3] leaves orphan 1, missing 5",
         "tags": ["tricky"]},
        {"input": {"hand": [8, 10, 12], "groupSize": 3}, "expected": False,
         "description": "Spaced by 2 — not consecutive", "tags": ["tricky"]},
        {"input": {"hand": [3, 2, 1], "groupSize": 3}, "expected": True,
         "description": "Single group, unsorted input", "tags": ["basic"]},
        {"input": {"hand": [1, 2, 3, 4, 5, 6], "groupSize": 2}, "expected": True,
         "description": "Multiple groups of 2: [1,2], [3,4], [5,6]", "tags": ["basic"]},
        {"input": {"hand": [1, 2, 3, 4, 5, 6], "groupSize": 3}, "expected": True,
         "description": "Multiple groups of 3: [1,2,3], [4,5,6]", "tags": ["basic"]},
        {"input": {"hand": [0, 0], "groupSize": 2}, "expected": False,
         "description": "Two identical zeros cannot form a run of 2 (need 0,1)", "tags": ["edge"]},
        {"input": {"hand": [1000000000, 999999999, 999999998], "groupSize": 3}, "expected": True,
         "description": "Large values, single consecutive run", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Min-Heap (Optimal)",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "Count card frequencies with a hash map. Push every distinct value into a min-heap. "
                "Repeatedly pop the smallest value `v`: it must start the next group. For each of "
                "`v, v+1, …, v+groupSize-1`, decrement the count; if any value is missing or its count "
                "drops below zero, return `false`. Lazy-pop the heap top when its count hits 0. "
                "Each card is touched O(log n) times for heap ops → O(n log n) overall."
            ),
            "code": {
                "python": (
                    "import heapq\n"
                    "from collections import Counter\n"
                    "\n"
                    "def is_n_straight_hand(hand, groupSize):\n"
                    "    if len(hand) % groupSize != 0:\n"
                    "        return False\n"
                    "    count = Counter(hand)\n"
                    "    heap = list(count.keys())\n"
                    "    heapq.heapify(heap)\n"
                    "    while heap:\n"
                    "        start = heap[0]\n"
                    "        for v in range(start, start + groupSize):\n"
                    "            if count[v] == 0:\n"
                    "                return False\n"
                    "            count[v] -= 1\n"
                    "            if count[v] == 0:\n"
                    "                if v != heap[0]:\n"
                    "                    return False\n"
                    "                heapq.heappop(heap)\n"
                    "    return True"
                ),
                "javascript": (
                    "function isNStraightHand(hand, groupSize) {\n"
                    "    if (hand.length % groupSize !== 0) return false;\n"
                    "    const count = new Map();\n"
                    "    for (const c of hand) count.set(c, (count.get(c) || 0) + 1);\n"
                    "    const keys = [...count.keys()].sort((a, b) => a - b);\n"
                    "    let i = 0;\n"
                    "    while (i < keys.length) {\n"
                    "        while (i < keys.length && count.get(keys[i]) === 0) i++;\n"
                    "        if (i === keys.length) break;\n"
                    "        const start = keys[i];\n"
                    "        for (let v = start; v < start + groupSize; v++) {\n"
                    "            const c = count.get(v) || 0;\n"
                    "            if (c === 0) return false;\n"
                    "            count.set(v, c - 1);\n"
                    "        }\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
                "java": (
                    "import java.util.*;\n"
                    "\n"
                    "public boolean isNStraightHand(int[] hand, int groupSize) {\n"
                    "    if (hand.length % groupSize != 0) return false;\n"
                    "    TreeMap<Integer, Integer> count = new TreeMap<>();\n"
                    "    for (int c : hand) count.merge(c, 1, Integer::sum);\n"
                    "    while (!count.isEmpty()) {\n"
                    "        int start = count.firstKey();\n"
                    "        for (int v = start; v < start + groupSize; v++) {\n"
                    "            Integer c = count.get(v);\n"
                    "            if (c == null) return false;\n"
                    "            if (c == 1) count.remove(v);\n"
                    "            else count.put(v, c - 1);\n"
                    "        }\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sorted Keys + Counter",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "Same greedy idea, but instead of a heap we sort the **distinct** keys once and walk "
                "them left-to-right. For each key whose remaining count is positive, treat it as the "
                "start of a group and decrement `count[v], count[v+1], …, count[v+groupSize-1]`. "
                "Any missing/zero count along the way is an immediate `false`. Conceptually identical "
                "to the heap version; trades a heap for a single sort."
            ),
            "code": {
                "python": (
                    "from collections import Counter\n"
                    "\n"
                    "def is_n_straight_hand(hand, groupSize):\n"
                    "    if len(hand) % groupSize != 0:\n"
                    "        return False\n"
                    "    count = Counter(hand)\n"
                    "    for v in sorted(count):\n"
                    "        c = count[v]\n"
                    "        if c == 0:\n"
                    "            continue\n"
                    "        for k in range(1, groupSize):\n"
                    "            if count[v + k] < c:\n"
                    "                return False\n"
                    "            count[v + k] -= c\n"
                    "        count[v] = 0\n"
                    "    return True"
                ),
                "javascript": (
                    "function isNStraightHand(hand, groupSize) {\n"
                    "    if (hand.length % groupSize !== 0) return false;\n"
                    "    const count = new Map();\n"
                    "    for (const c of hand) count.set(c, (count.get(c) || 0) + 1);\n"
                    "    const keys = [...count.keys()].sort((a, b) => a - b);\n"
                    "    for (const v of keys) {\n"
                    "        const c = count.get(v);\n"
                    "        if (c === 0) continue;\n"
                    "        for (let k = 1; k < groupSize; k++) {\n"
                    "            const next = count.get(v + k) || 0;\n"
                    "            if (next < c) return false;\n"
                    "            count.set(v + k, next - c);\n"
                    "        }\n"
                    "        count.set(v, 0);\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Quick reject on `len(hand) % groupSize != 0` — it's impossible to partition.",
        "2. Greedy lemma: the smallest remaining card *has* to start a group. Nothing smaller can extend "
        "into it, so it can't be the 2nd, 3rd, … element of any run.",
        "3. Build a frequency map. Repeatedly find the smallest value with positive count; peel off "
        "`groupSize` consecutive values starting there. Missing count → `false`.",
        "4. Implement 'find the smallest remaining' with a min-heap (lazy-pop zeros) or by sorting the "
        "distinct keys once and walking them.",
        "5. Watch for duplicates: e.g. `[1,1,2,2,3,4]` with groupSize 3 — the first run consumes "
        "[1,2,3] but 1 still has count 1 with no 2 left to pair, so we correctly return `false`.",
    ],
    "tips": [
        "The 'smallest must start a run' argument is the entire problem. Lead with it in the interview.",
        "Always state the divisibility quick reject — it's a free correctness and perf win.",
        "Python `Counter` makes the sorted-keys version a one-screener. In Java, `TreeMap` gives you "
        "`firstKey()` for free and is cleaner than a `PriorityQueue`.",
        "Don't forget to *fully decrement* counts and skip exhausted keys — missing this loops forever or "
        "double-counts.",
        "Same algorithm applies to LeetCode 1296 'Divide Array in Sets of K Consecutive Numbers' — "
        "literally the same problem, different wording. Recognise it.",
        "Bucket-sort variant: if values are bounded (e.g. ≤ 10⁴) you can index a fixed array instead of "
        "a hash map and drop the `log n`. Mention it as a follow-up for huge inputs with small range.",
    ],
    "companies": ["Google", "Amazon", "Microsoft", "Bloomberg", "DoorDash"],
    "topics": ["Array", "Hash Table", "Greedy", "Heap (Priority Queue)", "Sorting"],
    "time_complexity": "O(n log n)",
    "space_complexity": "O(n)",
}


def REFERENCE(hand, groupSize):
    if len(hand) % groupSize != 0:
        return False
    from collections import Counter
    count = Counter(hand)
    for v in sorted(count):
        c = count[v]
        if c == 0:
            continue
        for k in range(1, groupSize):
            if count[v + k] < c:
                return False
            count[v + k] -= c
        count[v] = 0
    return True


register(PAYLOAD, REFERENCE)
