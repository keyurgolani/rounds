"""Top 3-Page Sequence in Web Log — Medium. Hashing / Sliding Window.

The classic 'find the most common N-gram in a per-user activity stream'
problem. Demonstrates that you can't naively scan — you must group by
user first, then sliding-window over each user's sequence."""
from builder.registry import register


PAYLOAD = {
    "title": "Most Common 3-Page Sequence in Web Log",
    "difficulty": "Medium",
    "description": (
        "Given a log of website requests where each entry is `[time, customer_id, page]`, find the most "
        "common 3-page sequence visited by any single customer.\n\n"
        "**Important:** entries for the same customer are NOT necessarily contiguous in the log — you must "
        "group by customer first, sort each customer's pages by time, then count adjacent 3-page sequences.\n\n"
        "**Example:**\n"
        "```\n"
        "log = [[0,'C1','A'],[0,'C2','E'],[1,'C1','B'],[1,'C2','B'],\n"
        "       [2,'C1','C'],[2,'C2','C'],[3,'C1','D'],[3,'C2','D'],\n"
        "       [4,'C1','E'],[5,'C2','A']]\n"
        "C1: A→B→C→D→E   C2: E→B→C→D→A\n"
        "Common sequences:\n"
        "  A→B→C, B→C→D (×2), C→D→E, E→B→C, C→D→A\n"
        "Answer: ['B','C','D']\n"
        "```\n\n"
        "If multiple sequences tie for most common, returning any of them is acceptable."
    ),
    "hints": [
        "Don't assume the log is grouped by customer — group it yourself first.",
        "Once grouped, sort each customer's entries by time, then slide a 3-element window and count each tuple in a global map.",
        "Common mistake: counting (A,B,C) for a customer who visited only 2 pages — guard the window length.",
        "Tie-breaking is not specified; pick any of the maximum-count sequences. State this assumption explicitly.",
        "Scaling: for a log that doesn't fit in memory, this becomes a MapReduce job — map by customer, reduce by sequence.",
    ],
    "constraints": [
        "0 <= log.length <= 10⁵",
        "Each customer has at most 10³ entries",
        "Time values may be repeated; sort is stable on (time, original_index)",
    ],
    "starter_code": {
        "python": "def top_3_page_sequence(log):\n    # Your code here\n    pass",
        "javascript": "function top3PageSequence(log) {\n    // Your code here\n}",
        "java": "public List<String> top3PageSequence(List<List<Object>> log) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    log = [[0,'C1','A'],[0,'C2','E'],[1,'C1','B'],[1,'C2','B'],\n"
            "           [2,'C1','C'],[2,'C2','C'],[3,'C1','D'],[3,'C2','D'],\n"
            "           [4,'C1','E'],[5,'C2','A']]\n"
            "    print(top_3_page_sequence(log))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "console.log(top3PageSequence([[0,'C1','A'],[1,'C1','B'],[2,'C1','C']]));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main { public static void main(String[] args) {} }"
        ),
    },
    "test_cases": [
        {"input": {"log": [[0, 'C1', 'A'], [0, 'C2', 'E'], [1, 'C1', 'B'], [1, 'C2', 'B'],
                            [2, 'C1', 'C'], [2, 'C2', 'C'], [3, 'C1', 'D'], [3, 'C2', 'D'],
                            [4, 'C1', 'E'], [5, 'C2', 'A']]},
         "expected": ['B', 'C', 'D'],
         "description": "Canonical example from the problem statement", "tags": ["basic"]},
        {"input": {"log": [[0, 'X', 'A'], [1, 'X', 'B'], [2, 'X', 'C']]},
         "expected": ['A', 'B', 'C'],
         "description": "Single customer, single 3-sequence", "tags": ["edge"]},
        {"input": {"log": [[0, 'X', 'A'], [1, 'X', 'B']]},
         "expected": [],
         "description": "Customer never reaches 3 pages — no sequence", "tags": ["edge"]},
        {"input": {"log": []}, "expected": [],
         "description": "Empty log", "tags": ["edge"]},
        {"input": {"log": [[1, 'A', 'X'], [0, 'A', 'Y'], [2, 'A', 'Z']]},
         "expected": ['Y', 'X', 'Z'],
         "description": "Out-of-order log entries — must sort by time", "tags": ["tricky"]},
        {"input": {"log": [[i, 'C1', p] for i, p in enumerate(['A', 'B', 'C', 'A', 'B', 'C'])]},
         "expected": {"$match": "any_of", "values": [['A', 'B', 'C'], ['B', 'C', 'A'], ['C', 'A', 'B']]},
         "description": "Repeated pattern — multiple sequences tie",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Group + Slide + Count (Optimal)",
            "time_complexity": "O(N log k) where N = log size, k = avg per-user entries",
            "space_complexity": "O(N)",
            "description": (
                "Two phases. Phase 1: group entries by customer. Phase 2: for each customer, sort their "
                "entries by time, then slide a 3-element window and increment a counter for each tuple. "
                "Return the tuple with the highest count. The sort dominates within a customer; total work "
                "is N log k."
            ),
            "code": {
                "python": (
                    "from collections import defaultdict, Counter\n\n"
                    "def top_3_page_sequence(log):\n"
                    "    by_customer = defaultdict(list)\n"
                    "    for t, cid, page in log:\n"
                    "        by_customer[cid].append((t, page))\n"
                    "    counts = Counter()\n"
                    "    for entries in by_customer.values():\n"
                    "        entries.sort()  # by time\n"
                    "        pages = [p for _, p in entries]\n"
                    "        for i in range(len(pages) - 2):\n"
                    "            counts[(pages[i], pages[i+1], pages[i+2])] += 1\n"
                    "    if not counts:\n"
                    "        return []\n"
                    "    best = counts.most_common(1)[0][0]\n"
                    "    return list(best)"
                ),
                "javascript": (
                    "function top3PageSequence(log) {\n"
                    "    const byCustomer = new Map();\n"
                    "    for (const [t, cid, page] of log) {\n"
                    "        if (!byCustomer.has(cid)) byCustomer.set(cid, []);\n"
                    "        byCustomer.get(cid).push([t, page]);\n"
                    "    }\n"
                    "    const counts = new Map();\n"
                    "    for (const entries of byCustomer.values()) {\n"
                    "        entries.sort((a, b) => a[0] - b[0]);\n"
                    "        for (let i = 0; i < entries.length - 2; i++) {\n"
                    "            const k = `${entries[i][1]}|${entries[i+1][1]}|${entries[i+2][1]}`;\n"
                    "            counts.set(k, (counts.get(k) || 0) + 1);\n"
                    "        }\n"
                    "    }\n"
                    "    let best = null, bestN = 0;\n"
                    "    for (const [k, n] of counts) if (n > bestN) { best = k; bestN = n; }\n"
                    "    return best ? best.split('|') : [];\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Read carefully: log entries for the same customer are NOT contiguous — group first.",
        "2. Group by customer in a hash map → list of (time, page).",
        "3. Per customer: sort by time, then slide a 3-wide window over the resulting page sequence.",
        "4. Keep a global Counter of 3-tuples; return the most common.",
        "5. Tie-breaking is unspecified; pick any maximum and call it out.",
        "6. Scaling: if the log doesn't fit in memory, this becomes 'group by customer' (map step) then 'count tuples' (reduce step) — textbook MapReduce.",
        "7. Edge cases: empty log, customer with <3 entries (skip), out-of-order log entries.",
    ],
    "tips": [
        "Python tuples are hashable — use them directly as dict keys for the 3-page sequences.",
        "JS doesn't allow array keys — encode as a delimited string (`|` or any char that won't appear in page names).",
        "If you really care about ties, return all maxima or sort lexicographically; pin the rule down with the interviewer.",
        "Common follow-up: 'top N-page sequence' — generalise the window size from 3 to N.",
        "Common follow-up: 'top 10 sequences with counts' — `Counter.most_common(10)`.",
        "Common follow-up: 'sharded log files across servers' — MapReduce by customer for the group step, then aggregate the local counters.",
    ],
    "companies": ["Amazon", "Google", "Meta", "Bloomberg"],
    "topics": ["Hash Table", "Sliding Window", "Sorting", "Counting"],
    "time_complexity": "O(N log k)",
    "space_complexity": "O(N)",
}


def REFERENCE(log):
    from collections import defaultdict, Counter
    by_customer = defaultdict(list)
    for t, cid, page in log:
        by_customer[cid].append((t, page))
    counts = Counter()
    for entries in by_customer.values():
        entries.sort()
        pages = [p for _, p in entries]
        for i in range(len(pages) - 2):
            counts[(pages[i], pages[i + 1], pages[i + 2])] += 1
    if not counts:
        return []
    best = counts.most_common(1)[0][0]
    return list(best)


register(PAYLOAD, REFERENCE)
