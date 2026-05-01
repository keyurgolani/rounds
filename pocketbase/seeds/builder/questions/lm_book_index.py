"""Book Index Generator — Easy/Medium. Hashing / String.

Generate a book-style index from text content. Map each word to the
sorted list of pages it appears on. Real value: discuss stop-words,
case-folding, stemming."""
from builder.registry import register


PAYLOAD = {
    "title": "Book Index Generator",
    "difficulty": "Medium",
    "description": (
        "Generate a book index from a list of pages. Each page is a string of words. The output is a "
        "dict mapping each (case-folded, stop-word-filtered) word to a sorted list of page numbers (1-"
        "indexed) on which it appears. A word should appear at most once per page in the index.\n\n"
        "**Example:**\n"
        "```\n"
        "pages = [\n"
        "  'The quick brown fox',\n"
        "  'The lazy dog sleeps',\n"
        "  'The fox jumps over the dog'\n"
        "]\n"
        "stop_words = {'the', 'over'}\n"
        "build_index(pages, stop_words)\n"
        "→ {\n"
        "    'quick': [1],\n"
        "    'brown': [1],\n"
        "    'fox':   [1, 3],\n"
        "    'lazy':  [2],\n"
        "    'dog':   [2, 3],\n"
        "    'sleeps':[2],\n"
        "    'jumps': [3]\n"
        "  }\n"
        "```"
    ),
    "hints": [
        "Tokenise each page on whitespace (or use a regex for word boundaries to skip punctuation).",
        "Case-fold to canonicalise — 'Fox' and 'fox' index together.",
        "Use a set per page to dedupe within-page repetitions before appending the page number.",
        "Stop-word filter: skip words present in the stop_words set.",
        "Stemming / lemmatisation is the senior follow-up — 'jumps' / 'jumping' / 'jumped' should index together. Mention NLTK / spaCy.",
        "Edge cases: empty pages, page containing only stop words, mixed case, punctuation, unicode.",
    ],
    "constraints": [
        "0 <= |pages| <= 10⁴",
        "Each page is a string of at most 10⁴ characters",
    ],
    "starter_code": {
        "python": "def build_index(pages, stop_words):\n    # Your code here\n    pass",
        "javascript": "function buildIndex(pages, stopWords) {\n    // Your code here\n}",
        "java": "public Map<String, List<Integer>> buildIndex(List<String> pages, Set<String> stopWords) {\n    // Your code here\n    return new HashMap<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    pages = ['The quick brown fox', 'The lazy dog sleeps', 'The fox jumps over the dog']\n"
            "    print(build_index(pages, ['the', 'over']))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"pages": ["The quick brown fox", "The lazy dog sleeps",
                              "The fox jumps over the dog"],
                    "stop_words": ["the", "over"]},
         "expected": {"quick": [1], "brown": [1], "fox": [1, 3],
                       "lazy": [2], "dog": [2, 3], "sleeps": [2], "jumps": [3]},
         "description": "Standard 3-page example", "tags": ["basic"]},
        {"input": {"pages": [], "stop_words": []}, "expected": {},
         "description": "Empty book", "tags": ["edge"]},
        {"input": {"pages": ["the the the"], "stop_words": ["the"]},
         "expected": {},
         "description": "Page is all stop words", "tags": ["edge"]},
        {"input": {"pages": ["a a a", "a a a"], "stop_words": []},
         "expected": {"a": [1, 2]},
         "description": "Within-page duplicates collapse to single page entry",
         "tags": ["edge"]},
        {"input": {"pages": ["Fox FOX fox"], "stop_words": []},
         "expected": {"fox": [1]},
         "description": "Case folding", "tags": ["edge"]},
        {"input": {"pages": ["one two", "two three"], "stop_words": []},
         "expected": {"one": [1], "two": [1, 2], "three": [2]},
         "description": "Sorted page numbers per word", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Tokenise + Map + Sort (Optimal)",
            "time_complexity": "O(N · L · log P) where N = pages, L = avg words, P = pages per word",
            "space_complexity": "O(unique words × avg pages per word)",
            "description": (
                "For each page, lowercase + tokenise + dedupe via a set. For each surviving word, append "
                "the page number to its list in the index. Page numbers are appended in increasing order, "
                "so the lists are already sorted (no per-word sort needed)."
            ),
            "code": {
                "python": (
                    "def build_index(pages, stop_words):\n"
                    "    stop_set = set(s.lower() for s in stop_words)\n"
                    "    index = {}\n"
                    "    for i, page in enumerate(pages, 1):\n"
                    "        seen_on_page = set()\n"
                    "        for raw in page.split():\n"
                    "            w = raw.lower()\n"
                    "            if w in stop_set or w in seen_on_page:\n"
                    "                continue\n"
                    "            seen_on_page.add(w)\n"
                    "            index.setdefault(w, []).append(i)\n"
                    "    return index"
                ),
                "javascript": (
                    "function buildIndex(pages, stopWords) {\n"
                    "    const stop = new Set(stopWords.map(s => s.toLowerCase()));\n"
                    "    const index = {};\n"
                    "    pages.forEach((page, i) => {\n"
                    "        const seen = new Set();\n"
                    "        for (const raw of page.split(/\\s+/)) {\n"
                    "            const w = raw.toLowerCase();\n"
                    "            if (!w || stop.has(w) || seen.has(w)) continue;\n"
                    "            seen.add(w);\n"
                    "            (index[w] ||= []).push(i + 1);\n"
                    "        }\n"
                    "    });\n"
                    "    return index;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Tokenise each page; case-fold; filter stop words.",
        "2. Dedupe within page so the same word doesn't add the page twice.",
        "3. Append the page number to the word's list in the global index.",
        "4. Page numbers are 1-indexed and accumulate in order, so per-word lists are pre-sorted — no extra sort needed.",
        "5. Senior follow-ups: stemming, lemmatisation, n-gram index, frequency weighting (TF-IDF).",
        "6. Edge cases: empty pages, all-stop-word page, case differences, repeated words on a single page.",
    ],
    "tips": [
        "If you don't dedupe per page, the lists end up with duplicate page numbers — easy bug to miss.",
        "If you sort the per-word list after all pages are processed, that's O(P log P) per word — wasteful when in-order appending gives sorted-by-construction.",
        "For real books, strip punctuation before tokenising — `re.findall(r'[a-z]+', page.lower())` does it in one line.",
        "Common follow-up: 'add chapter info' — change page → (chapter, page); aggregate by chapter at output.",
        "Common follow-up: 'sub-second indexing for million-page documents.' Map-reduce: per-page tokenise = map, per-word merge = reduce.",
    ],
    "companies": ["Amazon", "Microsoft"],
    "topics": ["Hash Table", "String", "Inverted Index"],
    "time_complexity": "O(N · L)",
    "space_complexity": "O(unique words × pages)",
}


def REFERENCE(pages, stop_words):
    stop_set = set(s.lower() for s in stop_words)
    index = {}
    for i, page in enumerate(pages, 1):
        seen_on_page = set()
        for raw in page.split():
            w = raw.lower()
            if w in stop_set or w in seen_on_page:
                continue
            seen_on_page.add(w)
            index.setdefault(w, []).append(i)
    return index


register(PAYLOAD, REFERENCE)
