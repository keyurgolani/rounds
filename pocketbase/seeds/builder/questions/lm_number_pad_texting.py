"""Number Pad Texting — Medium. Trie / Backtracking.

Translate a digit sequence (T9-style) into all valid dictionary words.
Trie of the dictionary makes prefix lookups O(L); without it, you'd
brute-force the cartesian product."""
from builder.registry import register
from builder.registry import unordered_deep


_T9 = {
    "2": "abc", "3": "def", "4": "ghi", "5": "jkl",
    "6": "mno", "7": "pqrs", "8": "tuv", "9": "wxyz",
}


PAYLOAD = {
    "title": "Number Pad Texting (T9 Word Lookup)",
    "difficulty": "Medium",
    "description": (
        "On an old mobile keypad, each digit 2-9 maps to 3-4 letters (`2 → abc`, `3 → def`, …). Given a "
        "digit string and a dictionary, return all valid dictionary words whose letters match the digits "
        "in order. The output must contain ONLY whole-word matches; predictive-text matches are a follow-up.\n\n"
        "**Example:**\n"
        "- Input: `digits = '227'`, `dict = ['cap','bar','car','cab','app','book']`\n"
        "- Output: `['cap','bar','car','cab']` (each is a 3-letter word matching 2,2,7)\n\n"
        "Words shorter than the digit string don't match. Words longer than it don't match either (this is "
        "the strict whole-word version)."
    ),
    "hints": [
        "Brute force: enumerate the cartesian product of letter choices, intersect with dict. 3^L candidates per query.",
        "Filter the dict by length first, then membership test against the cartesian product (or, equivalently, walk the dict and check digit-letter compatibility).",
        "Best: build a trie of the dict once; for each digit in turn, descend along every letter assigned to that digit. Reach a terminal node at exactly position L → emit.",
        "Predictive text follow-up: instead of stopping at terminals matching the digit length, traverse the entire subtree below each matching node and emit all its terminals.",
        "Edge cases: empty digit string, no matches, dictionary with words of mixed lengths, digit string with characters outside 2-9.",
    ],
    "constraints": [
        "0 <= |digits| <= 20",
        "0 <= |dict| <= 10⁴",
        "Lowercase ASCII",
    ],
    "starter_code": {
        "python": "def t9_lookup(digits, dictionary):\n    # Your code here\n    pass",
        "javascript": "function t9Lookup(digits, dictionary) {\n    // Your code here\n}",
        "java": "public List<String> t9Lookup(String digits, List<String> dictionary) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(t9_lookup('227', ['cap','bar','car','cab','app','book']))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"digits": "227", "dictionary": ["cap", "bar", "car", "cab", "app", "book"]},
         "expected": unordered_deep(["cap", "bar", "car"]),
         "description": "227 → 3-letter matches ending in p/q/r/s (not b)",
         "tags": ["basic"]},
        {"input": {"digits": "43556", "dictionary": ["hello", "world"]},
         "expected": ["hello"],
         "description": "Single match", "tags": ["basic"]},
        {"input": {"digits": "", "dictionary": ["a", "b"]}, "expected": [],
         "description": "Empty digits — no whole-word match", "tags": ["edge"]},
        {"input": {"digits": "2", "dictionary": ["a", "b", "c", "z"]},
         "expected": unordered_deep(["a", "b", "c"]),
         "description": "Single digit, all letters mapping", "tags": ["edge"]},
        {"input": {"digits": "999", "dictionary": ["zzz"]}, "expected": ["zzz"],
         "description": "All-z match", "tags": ["edge"]},
        {"input": {"digits": "23", "dictionary": []}, "expected": [],
         "description": "Empty dictionary", "tags": ["edge"]},
        {"input": {"digits": "227", "dictionary": ["bar", "BARBELL"]},
         "expected": ["bar"],
         "description": "Wrong-length word excluded", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Filter Dict by Digit Compatibility (Practical)",
            "time_complexity": "O(D · L) where D = dict size, L = digit string length",
            "space_complexity": "O(1) extra",
            "description": (
                "Walk the dictionary once. For each word of the right length, check that every letter "
                "maps to its corresponding digit. Cleanest to write under interview pressure; trie wins "
                "at very large dictionaries with repeated queries."
            ),
            "code": {
                "python": (
                    "def t9_lookup(digits, dictionary):\n"
                    "    if not digits:\n"
                    "        return []\n"
                    "    LETTER_TO_DIGIT = {}\n"
                    "    for d, letters in {\n"
                    "        '2':'abc','3':'def','4':'ghi','5':'jkl',\n"
                    "        '6':'mno','7':'pqrs','8':'tuv','9':'wxyz'\n"
                    "    }.items():\n"
                    "        for c in letters:\n"
                    "            LETTER_TO_DIGIT[c] = d\n"
                    "    out = []\n"
                    "    L = len(digits)\n"
                    "    for w in dictionary:\n"
                    "        if len(w) != L:\n"
                    "            continue\n"
                    "        if all(LETTER_TO_DIGIT.get(c) == digits[i] for i, c in enumerate(w)):\n"
                    "            out.append(w)\n"
                    "    return out"
                ),
                "javascript": (
                    "function t9Lookup(digits, dictionary) {\n"
                    "    if (!digits) return [];\n"
                    "    const map = {};\n"
                    "    const D = {2:'abc',3:'def',4:'ghi',5:'jkl',6:'mno',7:'pqrs',8:'tuv',9:'wxyz'};\n"
                    "    for (const [d, letters] of Object.entries(D)) for (const c of letters) map[c] = d;\n"
                    "    const out = [];\n"
                    "    for (const w of dictionary) {\n"
                    "        if (w.length !== digits.length) continue;\n"
                    "        let ok = true;\n"
                    "        for (let i = 0; i < w.length; i++) if (map[w[i]] !== digits[i]) { ok = false; break; }\n"
                    "        if (ok) out.push(w);\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Trie Walk (Best for Repeated Queries)",
            "time_complexity": "O(D · L) build, O(L · 4^L) query worst-case",
            "space_complexity": "O(D · L)",
            "description": (
                "Build a trie of the dictionary. For each digit, descend along every letter mapped to that "
                "digit (maintaining a frontier of trie nodes). At exactly position L, emit all terminal "
                "nodes in the frontier."
            ),
            "code": {
                "python": (
                    "def t9_lookup(digits, dictionary):\n"
                    "    if not digits:\n"
                    "        return []\n"
                    "    DMAP = {\n"
                    "        '2':'abc','3':'def','4':'ghi','5':'jkl',\n"
                    "        '6':'mno','7':'pqrs','8':'tuv','9':'wxyz'\n"
                    "    }\n"
                    "    # Build trie keyed on letters; track terminals.\n"
                    "    root = {}\n"
                    "    for w in dictionary:\n"
                    "        node = root\n"
                    "        for c in w:\n"
                    "            node = node.setdefault(c, {})\n"
                    "        node['$'] = w\n"
                    "    frontier = [(root, '')]\n"
                    "    for d in digits:\n"
                    "        nxt = []\n"
                    "        for node, path in frontier:\n"
                    "            for c in DMAP.get(d, ''):\n"
                    "                if c in node:\n"
                    "                    nxt.append((node[c], path + c))\n"
                    "        frontier = nxt\n"
                    "    return [path for node, path in frontier if '$' in node]"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Map letters → digit; check each candidate word's letters against the digit string.",
        "2. Filter by length first — saves a lot of compute on dicts with mixed-length entries.",
        "3. For very large dicts and repeated queries, build a trie. Walk a frontier: at each digit, every node in the frontier branches to up to 4 children, one per assigned letter.",
        "4. Predictive text variant: don't stop at length L; continue traversing and emit every terminal in the subtree.",
        "5. Edge cases: empty digit string, empty dict, digits with no letter map (1, 0), word containing chars outside 2-9 mapping.",
    ],
    "tips": [
        "Precompute the letter-to-digit map; rebuilding it on every word is wasteful.",
        "If the dictionary is fixed and queries are many, the trie pays for itself.",
        "Predictive text follow-up shares the trie — that's the design win.",
        "Common follow-up: 'rank suggestions by frequency.' Store count per word in the trie; sort the output.",
        "Common follow-up: 'fuzzy matches one digit off.' Add a budget to the trie walk that allows one wrong digit.",
    ],
    "companies": ["Amazon", "Microsoft", "Nokia"],
    "topics": ["Trie", "String", "Hash Table"],
    "time_complexity": "O(D · L)",
    "space_complexity": "O(D · L)",
}


def REFERENCE(digits, dictionary):
    if not digits:
        return []
    LETTER_TO_DIGIT = {}
    for d, letters in _T9.items():
        for c in letters:
            LETTER_TO_DIGIT[c] = d
    out = []
    L = len(digits)
    for w in dictionary:
        if len(w) != L:
            continue
        if all(LETTER_TO_DIGIT.get(c) == digits[i] for i, c in enumerate(w)):
            out.append(w)
    return out


register(PAYLOAD, REFERENCE)
