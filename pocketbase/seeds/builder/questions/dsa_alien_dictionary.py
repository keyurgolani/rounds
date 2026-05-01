"""Alien Dictionary — Hard. Graph / Topological Sort.

Given a sorted list of words from an alien language, recover the
character ordering. Build a directed graph from adjacent-word
comparisons, then topological-sort. Edge cases (cycles, prefix
violations, isolated chars) are where most candidates lose points."""
from builder.registry import register
from builder.registry import any_of
from itertools import permutations as _perms


def _all_valid_orderings(words):
    """Enumerate every permutation of the alphabet that satisfies the pairwise constraints.
    Used at build time only — fine because the alphabet is tiny."""
    chars = sorted({c for w in words for c in w})
    # Prefix violation
    for w1, w2 in zip(words, words[1:]):
        if len(w1) > len(w2) and w1.startswith(w2):
            return [""]
    valid = []
    for perm in _perms(chars):
        s = "".join(perm)
        pos = {c: i for i, c in enumerate(s)}
        ok = True
        for w1, w2 in zip(words, words[1:]):
            for a, b in zip(w1, w2):
                if a != b:
                    if pos[a] >= pos[b]:
                        ok = False
                    break
            if not ok:
                break
        if ok:
            valid.append(s)
    return valid if valid else [""]


PAYLOAD = {
    "title": "Alien Dictionary",
    "difficulty": "Hard",
    "description": (
        "Given a list of `words` written in an unknown 'alien' language, sorted lexicographically by that "
        "language's rules, return a string describing a valid character ordering. If multiple valid orderings "
        "exist, returning any is acceptable. If no valid ordering exists (the input is contradictory), "
        "return an empty string.\n\n"
        "**Example 1:**\n"
        "- Input: `words = ['wrt','wrf','er','ett','rftt']`\n"
        "- Output: `'wertf'` (any topological ordering of the inferred graph)\n\n"
        "**Example 2:**\n"
        "- Input: `words = ['z','x','z']`\n"
        "- Output: `''` (cycle: z < x and x < z)\n\n"
        "**Example 3 (prefix violation):**\n"
        "- Input: `words = ['abc','ab']`\n"
        "- Output: `''` (a longer word can't precede its prefix)"
    ),
    "hints": [
        "Step 1: build a directed graph from adjacent-word comparisons. For each pair, find the first differing character — that gives you one edge.",
        "Step 2: topological sort the graph. BFS (Kahn's algorithm) or DFS — both work.",
        "Cycle detection: if you can't produce a complete ordering (BFS dequeues fewer than V nodes / DFS hits a back-edge), the input is contradictory → return empty.",
        "Prefix violation: if word_i is longer than word_{i+1} and word_{i+1} is a prefix of word_i, the ordering is impossible.",
        "Don't forget isolated characters — characters that appear in some word but never produce an edge still need to be in the output.",
    ],
    "constraints": [
        "1 <= |words| <= 100",
        "1 <= word.length <= 20",
        "Lowercase ASCII letters",
    ],
    "starter_code": {
        "python": "def alien_order(words):\n    # Your code here\n    pass",
        "javascript": "function alienOrder(words) {\n    // Your code here\n}",
        "java": "public String alienOrder(String[] words) {\n    // Your code here\n    return \"\";\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(alien_order(['wrt','wrf','er','ett','rftt']))\n"
            "    print(alien_order(['z','x','z']))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"words": ["wrt", "wrf", "er", "ett", "rftt"]},
         "expected": any_of(_all_valid_orderings(["wrt", "wrf", "er", "ett", "rftt"])),
         "description": "Standard 5-word example", "tags": ["basic"]},
        {"input": {"words": ["z", "x"]},
         "expected": any_of(_all_valid_orderings(["z", "x"])),
         "description": "Two words, two characters", "tags": ["basic"]},
        {"input": {"words": ["z", "x", "z"]}, "expected": "",
         "description": "Cycle: z < x and x < z", "tags": ["edge"]},
        {"input": {"words": ["abc", "ab"]}, "expected": "",
         "description": "Prefix violation — long word before its prefix",
         "tags": ["edge"]},
        {"input": {"words": ["abc"]},
         "expected": any_of(_all_valid_orderings(["abc"])),
         "description": "Single word — any permutation valid",
         "tags": ["edge"]},
        {"input": {"words": ["aa", "aa", "bb"]},
         "expected": any_of(_all_valid_orderings(["aa", "aa", "bb"])),
         "description": "Duplicate words — still must produce a < b",
         "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Kahn's Algorithm (Optimal)",
            "time_complexity": "O(C + N·L) where C = total chars, N = words, L = avg word length",
            "space_complexity": "O(C)",
            "description": (
                "Build adjacency list and indegree map from adjacent-word comparisons. Detect prefix "
                "violations early. BFS from indegree-0 nodes; append each dequeued node to the output. If "
                "the output length doesn't match the alphabet size, a cycle exists → return empty."
            ),
            "code": {
                "python": (
                    "def alien_order(words):\n"
                    "    from collections import defaultdict, deque\n"
                    "    chars = set(c for w in words for c in w)\n"
                    "    adj = defaultdict(set)\n"
                    "    indeg = {c: 0 for c in chars}\n"
                    "    for w1, w2 in zip(words, words[1:]):\n"
                    "        # Prefix violation check\n"
                    "        if len(w1) > len(w2) and w1.startswith(w2):\n"
                    "            return ''\n"
                    "        for a, b in zip(w1, w2):\n"
                    "            if a != b:\n"
                    "                if b not in adj[a]:\n"
                    "                    adj[a].add(b)\n"
                    "                    indeg[b] += 1\n"
                    "                break\n"
                    "    q = deque([c for c in chars if indeg[c] == 0])\n"
                    "    out = []\n"
                    "    while q:\n"
                    "        c = q.popleft()\n"
                    "        out.append(c)\n"
                    "        for nxt in adj[c]:\n"
                    "            indeg[nxt] -= 1\n"
                    "            if indeg[nxt] == 0:\n"
                    "                q.append(nxt)\n"
                    "    if len(out) != len(chars):\n"
                    "        return ''\n"
                    "    return ''.join(out)"
                ),
                "javascript": (
                    "function alienOrder(words) {\n"
                    "    const chars = new Set();\n"
                    "    for (const w of words) for (const c of w) chars.add(c);\n"
                    "    const adj = new Map();\n"
                    "    const indeg = new Map();\n"
                    "    for (const c of chars) { adj.set(c, new Set()); indeg.set(c, 0); }\n"
                    "    for (let i = 0; i < words.length - 1; i++) {\n"
                    "        const w1 = words[i], w2 = words[i+1];\n"
                    "        if (w1.length > w2.length && w1.startsWith(w2)) return '';\n"
                    "        const L = Math.min(w1.length, w2.length);\n"
                    "        for (let j = 0; j < L; j++) {\n"
                    "            const a = w1[j], b = w2[j];\n"
                    "            if (a !== b) {\n"
                    "                if (!adj.get(a).has(b)) { adj.get(a).add(b); indeg.set(b, indeg.get(b) + 1); }\n"
                    "                break;\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "    const q = [];\n"
                    "    for (const c of chars) if (indeg.get(c) === 0) q.push(c);\n"
                    "    const out = [];\n"
                    "    while (q.length) {\n"
                    "        const c = q.shift();\n"
                    "        out.push(c);\n"
                    "        for (const nxt of adj.get(c)) {\n"
                    "            indeg.set(nxt, indeg.get(nxt) - 1);\n"
                    "            if (indeg.get(nxt) === 0) q.push(nxt);\n"
                    "        }\n"
                    "    }\n"
                    "    return out.length === chars.size ? out.join('') : '';\n"
                    "}"
                ),
            },
        },
        {
            "title": "DFS with Cycle Detection",
            "time_complexity": "Same as Kahn's",
            "space_complexity": "Same",
            "description": (
                "DFS each node, marking colours: white (unvisited), grey (in progress), black (done). A "
                "back-edge (grey→grey) signals a cycle. Reverse-postorder gives a topological order."
            ),
            "code": {
                "python": (
                    "def alien_order(words):\n"
                    "    from collections import defaultdict\n"
                    "    chars = set(c for w in words for c in w)\n"
                    "    adj = defaultdict(set)\n"
                    "    for w1, w2 in zip(words, words[1:]):\n"
                    "        if len(w1) > len(w2) and w1.startswith(w2):\n"
                    "            return ''\n"
                    "        for a, b in zip(w1, w2):\n"
                    "            if a != b:\n"
                    "                adj[a].add(b)\n"
                    "                break\n"
                    "    WHITE, GREY, BLACK = 0, 1, 2\n"
                    "    color = {c: WHITE for c in chars}\n"
                    "    order = []\n"
                    "    cycle = [False]\n"
                    "    def dfs(c):\n"
                    "        if cycle[0]: return\n"
                    "        if color[c] == GREY:\n"
                    "            cycle[0] = True; return\n"
                    "        if color[c] == BLACK: return\n"
                    "        color[c] = GREY\n"
                    "        for nxt in adj[c]:\n"
                    "            dfs(nxt)\n"
                    "        color[c] = BLACK\n"
                    "        order.append(c)\n"
                    "    for c in chars:\n"
                    "        dfs(c)\n"
                    "        if cycle[0]: return ''\n"
                    "    return ''.join(reversed(order))"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Reframe: each adjacent pair tells you ONE ordering constraint between the first differing char pair.",
        "2. Build a directed graph from those constraints. All chars in the input alphabet are nodes, even if they have no edges.",
        "3. Toposort the graph. Kahn's BFS is the cleanest under interview pressure; DFS works too.",
        "4. Detect contradictions: cycle (toposort returns fewer nodes than V) OR prefix violation (long word before its prefix).",
        "5. Multiple valid orderings: any one is acceptable. Don't try to enumerate them unless asked.",
        "6. Edge cases: single word (any permutation OK), duplicate words, words sharing all common prefix, prefix violation.",
    ],
    "tips": [
        "The prefix violation check is easy to miss — a longer word followed by its prefix means no valid ordering exists, even with no other constraints.",
        "Use `set` for adjacency to avoid double-counting edges from repeated word pairs.",
        "If the alphabet is bounded (e.g. lowercase ASCII), use fixed-size arrays for indegree and adjacency — fast and tidy.",
        "Common follow-up: 'enumerate ALL valid orderings.' That's exponential — generate via backtracking with permutations of the indegree-0 set at each step.",
        "Common follow-up: 'is the input self-consistent?' Just return success/failure of the toposort without producing the ordering.",
    ],
    "companies": ["Amazon", "Facebook", "Google", "Airbnb"],
    "topics": ["Graph", "Topological Sort", "BFS", "DFS"],
    "time_complexity": "O(C + N·L)",
    "space_complexity": "O(C)",
}


def REFERENCE(words):
    from collections import defaultdict, deque
    chars = set(c for w in words for c in w)
    adj = defaultdict(set)
    indeg = {c: 0 for c in chars}
    for w1, w2 in zip(words, words[1:]):
        if len(w1) > len(w2) and w1.startswith(w2):
            return ""
        for a, b in zip(w1, w2):
            if a != b:
                if b not in adj[a]:
                    adj[a].add(b)
                    indeg[b] += 1
                break
    q = deque([c for c in chars if indeg[c] == 0])
    out = []
    while q:
        c = q.popleft()
        out.append(c)
        for nxt in adj[c]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                q.append(nxt)
    if len(out) != len(chars):
        return ""
    return "".join(out)


register(PAYLOAD, REFERENCE)
