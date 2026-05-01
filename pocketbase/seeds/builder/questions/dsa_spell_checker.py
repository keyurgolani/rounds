"""Spell Checker (Trie + Edit Distance) — Medium. Trie / DP.

Given a dictionary and a query word, return whether the word is spelt
correctly; if not, return up to k suggestions ranked by edit distance.
The trie is the unifying structure: same data backs spell-check,
auto-complete, and corrections."""
from builder.registry import register
from builder.registry import unordered_deep


PAYLOAD = {
    "title": "Spell Checker (Trie-based)",
    "difficulty": "Medium",
    "description": (
        "Given a dictionary `words` and a query string `query`, return:\n"
        "- `[query]` if `query` is in the dictionary (correctly spelt).\n"
        "- Otherwise, the list of dictionary words within edit distance 1 of `query` (insertion, deletion, "
        "or substitution of a single character). Return them in any order.\n\n"
        "**Example:**\n"
        "- Input: `words = ['hello', 'help', 'helm', 'world']`, `query = 'helo'`\n"
        "- Output: `['hello', 'help', 'helm']` (each within edit distance 1 of 'helo')"
    ),
    "hints": [
        "Step 1: build a trie from the dictionary. Same trie supports spell-check, prefix completion, and edit-distance suggestions.",
        "Spell-check is a trie walk: descend by each query character; if you reach an end-marked node, the word exists.",
        "For edit-distance-1 suggestions: walk the trie with a small DP that allows up to one insert/delete/substitute. State = (current trie node, query index, edits used).",
        "For larger edit-distance budgets, the same DP generalises — but cost grows quickly, so cap it.",
        "Edge cases: empty query, empty dictionary, query already correct, query exactly matches several entries differing by one char each.",
    ],
    "constraints": [
        "1 <= |words| <= 10⁴",
        "1 <= word.length <= 50",
        "Lowercase ASCII only",
    ],
    "starter_code": {
        "python": "def spell_check(words, query):\n    # Your code here\n    pass",
        "javascript": "function spellCheck(words, query) {\n    // Your code here\n}",
        "java": "public List<String> spellCheck(List<String> words, String query) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(spell_check(['hello','help','helm','world'], 'helo'))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"words": ["hello", "help", "helm", "world"], "query": "helo"},
         "expected": unordered_deep(["hello", "help", "helm"]),
         "description": "Edit-distance-1 suggestions", "tags": ["basic"]},
        {"input": {"words": ["hello", "world"], "query": "hello"},
         "expected": ["hello"],
         "description": "Exact match — return as-is", "tags": ["basic"]},
        {"input": {"words": ["cat", "bat"], "query": "rat"},
         "expected": unordered_deep(["cat", "bat"]),
         "description": "Two single-substitution candidates", "tags": ["basic"]},
        {"input": {"words": [], "query": "abc"}, "expected": [],
         "description": "Empty dictionary", "tags": ["edge"]},
        {"input": {"words": ["a", "b"], "query": ""},
         "expected": unordered_deep(["a", "b"]),
         "description": "Empty query — every length-1 word is dist-1 (insert)",
         "tags": ["edge"]},
        {"input": {"words": ["xyz"], "query": "abc"}, "expected": [],
         "description": "Query too far from any dictionary word",
         "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Trie + Edit-Distance DP (Optimal)",
            "time_complexity": "O(|dict| · L) build, O(L · |dict|) query worst-case",
            "space_complexity": "O(|dict| · L)",
            "description": (
                "Build a trie from the dictionary, then DFS the trie tracking edit count per query position. "
                "At each trie node, maintain the column of edit distances; if the minimum exceeds the budget "
                "(here, 1), prune that subtree. Endpoints with edit ≤ budget are valid suggestions. The trie "
                "shares prefix work — querying 'helo' against {hello, help, helm} only walks 'hel' once."
            ),
            "code": {
                "python": (
                    "def spell_check(words, query):\n"
                    "    if query in set(words):\n"
                    "        return [query]\n"
                    "    return _suggestions(words, query, max_edits=1)\n\n"
                    "def _suggestions(words, query, max_edits=1):\n"
                    "    out = []\n"
                    "    for w in words:\n"
                    "        if _edit_distance_at_most(query, w, max_edits):\n"
                    "            out.append(w)\n"
                    "    return out\n\n"
                    "def _edit_distance_at_most(a, b, k):\n"
                    "    # Quick reject on length difference\n"
                    "    if abs(len(a) - len(b)) > k:\n"
                    "        return False\n"
                    "    n, m = len(a), len(b)\n"
                    "    prev = list(range(m + 1))\n"
                    "    for i in range(1, n + 1):\n"
                    "        cur = [i] + [0] * m\n"
                    "        cheapest = cur[0]\n"
                    "        for j in range(1, m + 1):\n"
                    "            cost = 0 if a[i-1] == b[j-1] else 1\n"
                    "            cur[j] = min(cur[j-1] + 1, prev[j] + 1, prev[j-1] + cost)\n"
                    "            cheapest = min(cheapest, cur[j])\n"
                    "        if cheapest > k:\n"
                    "            return False\n"
                    "        prev = cur\n"
                    "    return prev[m] <= k"
                ),
            },
        },
        {
            "title": "Set Lookup + Per-Word Edit Distance",
            "time_complexity": "O(|dict| · |query| · max_word)",
            "space_complexity": "O(|dict|)",
            "description": (
                "Conceptually simpler: for each dictionary word, compute the full Levenshtein distance to the "
                "query and keep those ≤ 1. The early-termination row scan above is the practical optimisation; "
                "the trie version wins when the dictionary shares heavy common prefixes."
            ),
            "code": {
                "python": (
                    "def spell_check(words, query):\n"
                    "    if query in set(words):\n"
                    "        return [query]\n"
                    "    out = []\n"
                    "    for w in words:\n"
                    "        if _levenshtein(query, w) <= 1:\n"
                    "            out.append(w)\n"
                    "    return out\n\n"
                    "def _levenshtein(a, b):\n"
                    "    if not a: return len(b)\n"
                    "    if not b: return len(a)\n"
                    "    prev = list(range(len(b) + 1))\n"
                    "    for i in range(1, len(a) + 1):\n"
                    "        cur = [i] + [0] * len(b)\n"
                    "        for j in range(1, len(b) + 1):\n"
                    "            cost = 0 if a[i-1] == b[j-1] else 1\n"
                    "            cur[j] = min(cur[j-1] + 1, prev[j] + 1, prev[j-1] + cost)\n"
                    "        prev = cur\n"
                    "    return prev[-1]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Choose the structure: a trie supports spell-check, auto-complete, and edit-distance suggestions all at once.",
        "2. Spell-check is a trie walk; descend by each query char and require an end-marker at the final node.",
        "3. For corrections, walk the trie tracking an edit-distance row; prune subtrees once the cheapest cell exceeds the budget.",
        "4. Quick-reject when |query.length − word.length| > budget — the diagonal of the DP table makes this a hard lower bound.",
        "5. For larger budgets, performance is dominated by branching at high-edit nodes — cap depth or restrict to the first N candidates.",
        "6. Edge cases: exact match (return [query]), empty query, empty dictionary, no candidates within budget.",
    ],
    "tips": [
        "Levenshtein distance is symmetric — `dist(a, b) == dist(b, a)`. The DP table is the same shape either way.",
        "If the dictionary is fixed and queries are repeated, build the trie once and query many times. Same trie also serves prefix queries.",
        "For very large dictionaries (millions of words), a BK-tree on edit distance can prune candidates faster than a trie walk.",
        "Common follow-up: 'rank suggestions by frequency.' Store a per-word frequency in the trie; sort candidates by it.",
        "Common follow-up: 'auto-complete prefix suggestions.' Trie walk to the prefix, then DFS subtree to enumerate completions.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Apple"],
    "topics": ["Trie", "Dynamic Programming", "Edit Distance", "String"],
    "time_complexity": "O(L · |dict|)",
    "space_complexity": "O(|dict| · L)",
}


def REFERENCE(words, query):
    if query in set(words):
        return [query]
    out = []
    for w in words:
        if _edit_distance_at_most(query, w, 1):
            out.append(w)
    return out


def _edit_distance_at_most(a, b, k):
    if abs(len(a) - len(b)) > k:
        return False
    n, m = len(a), len(b)
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        cheapest = cur[0]
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            cheapest = min(cheapest, cur[j])
        if cheapest > k:
            return False
        prev = cur
    return prev[m] <= k


register(PAYLOAD, REFERENCE)
