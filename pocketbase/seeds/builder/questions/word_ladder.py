"""Word Ladder — Hard. BFS shortest path on an implicit graph.

The classic 'words as nodes, one-letter edits as edges' problem. The
trick that separates a TLE from an accepted solution is the *pattern
map*: instead of comparing every pair of words (O(N²·M)), bucket
words by wildcard patterns like `h*t` so each word's neighbours can
be discovered in O(M²) work. Bidirectional BFS then halves the
explored frontier in practice.
"""
from collections import defaultdict, deque

from builder.registry import register


PAYLOAD = {
    "title": "Word Ladder",
    "difficulty": "Hard",
    "description": (
        "A **transformation sequence** from word `beginWord` to word `endWord` using a dictionary "
        "`wordList` is a sequence of words `beginWord -> s_1 -> s_2 -> ... -> s_k = endWord` such that:\n\n"
        "- Every adjacent pair of words differs by exactly **one letter**.\n"
        "- Every `s_i` for `1 <= i <= k` is in `wordList`. Note that `beginWord` does **not** need to be "
        "in `wordList`.\n"
        "- `s_k == endWord`.\n\n"
        "Given two words `beginWord` and `endWord`, and a dictionary `wordList`, return the **number of "
        "words** in the shortest transformation sequence from `beginWord` to `endWord`, or `0` if no such "
        "sequence exists. The length includes both endpoints.\n\n"
        "**Example 1:**\n"
        "- Input: `beginWord = \"hit\"`, `endWord = \"cog\"`, `wordList = [\"hot\",\"dot\",\"dog\",\"lot\",\"log\",\"cog\"]`\n"
        "- Output: `5`\n"
        "- Explanation: One shortest transformation is `\"hit\" -> \"hot\" -> \"dot\" -> \"dog\" -> \"cog\"`, "
        "which has length `5`.\n\n"
        "**Example 2:**\n"
        "- Input: `beginWord = \"hit\"`, `endWord = \"cog\"`, `wordList = [\"hot\",\"dot\",\"dog\",\"lot\",\"log\"]`\n"
        "- Output: `0`\n"
        "- Explanation: `endWord = \"cog\"` is not in `wordList`, so no valid transformation sequence exists."
    ),
    "hints": [
        "Shortest transformation = shortest path on an unweighted graph. That's BFS — not DFS, not Dijkstra.",
        "Don't build the graph by comparing every word pair (O(N²·M)). Build a **pattern map**: for each word, "
        "generate all `M` wildcard patterns like `h*t`, `*it`, `hi*`, and bucket words under each pattern. "
        "Two words are neighbours iff they share a pattern.",
        "Mark words as visited the moment you enqueue them, not when you dequeue. Otherwise BFS revisits the "
        "same nodes through the queue and degenerates.",
        "If `endWord` isn't in `wordList`, return `0` immediately — no sequence can end at it.",
        "Bidirectional BFS: search from both `beginWord` and `endWord`, alternating the smaller frontier each "
        "iteration. When the frontiers intersect, you have the shortest path. Cuts the explored space from "
        "`b^d` to roughly `2·b^(d/2)`.",
    ],
    "constraints": [
        "1 <= beginWord.length <= 10",
        "endWord.length == beginWord.length and all wordList[i].length are equal",
        "1 <= wordList.length <= 5000; all words consist of lowercase English letters",
    ],
    "starter_code": {
        "python": "def ladder_length(beginWord, endWord, wordList):\n    # Your code here\n    pass",
        "javascript": "function ladderLength(beginWord, endWord, wordList) {\n    // Your code here\n}",
        "java": "public int ladderLength(String beginWord, String endWord, List<String> wordList) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [\n"
            "        (\"hit\", \"cog\", [\"hot\",\"dot\",\"dog\",\"lot\",\"log\",\"cog\"]),\n"
            "        (\"hit\", \"cog\", [\"hot\",\"dot\",\"dog\",\"lot\",\"log\"]),\n"
            "    ]\n"
            "    for begin, end, words in cases:\n"
            "        print(f\"ladder_length({begin!r}, {end!r}, {words}) = {ladder_length(begin, end, words)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[\n"
            "    [\"hit\", \"cog\", [\"hot\",\"dot\",\"dog\",\"lot\",\"log\",\"cog\"]],\n"
            "    [\"hit\", \"cog\", [\"hot\",\"dot\",\"dog\",\"lot\",\"log\"]],\n"
            "].forEach(([b, e, w]) =>\n"
            "    console.log(`ladderLength =`, ladderLength(b, e, w))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "import java.util.*;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.ladderLength(\"hit\", \"cog\",\n"
            "            Arrays.asList(\"hot\",\"dot\",\"dog\",\"lot\",\"log\",\"cog\")));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"beginWord": "hit", "endWord": "cog",
                   "wordList": ["hot", "dot", "dog", "lot", "log", "cog"]},
         "expected": 5,
         "description": "Classic LC example — hit → hot → dot → dog → cog",
         "tags": ["basic"]},
        {"input": {"beginWord": "hit", "endWord": "cog",
                   "wordList": ["hot", "dot", "dog", "lot", "log"]},
         "expected": 0,
         "description": "endWord not in wordList — impossible",
         "tags": ["edge"]},
        {"input": {"beginWord": "a", "endWord": "c", "wordList": ["a", "b", "c"]},
         "expected": 2,
         "description": "Length-1 words; a → c is one edit, length 2",
         "tags": ["edge"]},
        {"input": {"beginWord": "hot", "endWord": "dog", "wordList": ["hot", "dog"]},
         "expected": 0,
         "description": "Two words but they differ in two letters with no bridge — impossible",
         "tags": ["tricky"]},
        {"input": {"beginWord": "hot", "endWord": "dog", "wordList": ["hot", "dog", "dot"]},
         "expected": 3,
         "description": "Bridge word 'dot' connects them — chain of 3",
         "tags": ["basic"]},
        {"input": {"beginWord": "cat", "endWord": "dog",
                   "wordList": ["cat", "bat", "bot", "bog", "dog"]},
         "expected": 5,
         "description": "Chain of 5: cat → bat → bot → bog → dog",
         "tags": ["tricky"]},
        {"input": {"beginWord": "hit", "endWord": "cog",
                   "wordList": ["hot", "dot", "dog", "lot", "log", "cog",
                                "abc", "abd", "abe", "xyz", "xyy"]},
         "expected": 5,
         "description": "Many disconnected words — answer ignores the unreachable cluster",
         "tags": ["tricky"]},
        {"input": {"beginWord": "ab", "endWord": "ac", "wordList": ["ac"]},
         "expected": 2,
         "description": "Single-element wordList — direct one-edit step",
         "tags": ["edge"]},
        {"input": {"beginWord": "lost", "endWord": "miss",
                   "wordList": ["most", "mist", "miss", "lost", "fist", "fish"]},
         "expected": 4,
         "description": "Long ladder: lost → most → mist → miss",
         "tags": ["tricky"]},
        {"input": {"beginWord": "leet", "endWord": "code",
                   "wordList": ["lest", "leet", "lose", "code", "lode", "robe", "lost"]},
         "expected": 6,
         "description": "Long ladder: leet → lest → lost → lose → lode → code",
         "tags": ["tricky"]},
        {"input": {"beginWord": "abc", "endWord": "xyz",
                   "wordList": ["abd", "abe", "xyy", "xyx"]},
         "expected": 0,
         "description": "endWord not in wordList — impossible despite many words",
         "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "BFS with Pattern Map (Optimal)",
            "time_complexity": "O(M² · N)",
            "space_complexity": "O(M² · N)",
            "description": (
                "Pre-compute a map from wildcard pattern (e.g. `h*t`) to the list of words matching it. "
                "Then BFS from `beginWord`, expanding each word by iterating its `M` wildcard patterns and "
                "visiting every other word bucketed under the same pattern. M = word length, N = wordList "
                "size. Mark words visited on enqueue to keep BFS linear."
            ),
            "code": {
                "python": (
                    "from collections import defaultdict, deque\n"
                    "\n"
                    "def ladder_length(beginWord, endWord, wordList):\n"
                    "    word_set = set(wordList)\n"
                    "    if endWord not in word_set:\n"
                    "        return 0\n"
                    "    M = len(beginWord)\n"
                    "    pattern_map = defaultdict(list)\n"
                    "    for word in word_set:\n"
                    "        for i in range(M):\n"
                    "            pattern_map[word[:i] + '*' + word[i+1:]].append(word)\n"
                    "\n"
                    "    queue = deque([(beginWord, 1)])\n"
                    "    visited = {beginWord}\n"
                    "    while queue:\n"
                    "        word, steps = queue.popleft()\n"
                    "        for i in range(M):\n"
                    "            pattern = word[:i] + '*' + word[i+1:]\n"
                    "            for nxt in pattern_map[pattern]:\n"
                    "                if nxt == endWord:\n"
                    "                    return steps + 1\n"
                    "                if nxt not in visited:\n"
                    "                    visited.add(nxt)\n"
                    "                    queue.append((nxt, steps + 1))\n"
                    "            pattern_map[pattern] = []  # prune: avoid re-scanning\n"
                    "    return 0"
                ),
                "javascript": (
                    "function ladderLength(beginWord, endWord, wordList) {\n"
                    "    const wordSet = new Set(wordList);\n"
                    "    if (!wordSet.has(endWord)) return 0;\n"
                    "    const M = beginWord.length;\n"
                    "    const patternMap = new Map();\n"
                    "    for (const word of wordSet) {\n"
                    "        for (let i = 0; i < M; i++) {\n"
                    "            const p = word.slice(0, i) + '*' + word.slice(i + 1);\n"
                    "            if (!patternMap.has(p)) patternMap.set(p, []);\n"
                    "            patternMap.get(p).push(word);\n"
                    "        }\n"
                    "    }\n"
                    "    const queue = [[beginWord, 1]];\n"
                    "    const visited = new Set([beginWord]);\n"
                    "    while (queue.length) {\n"
                    "        const [word, steps] = queue.shift();\n"
                    "        for (let i = 0; i < M; i++) {\n"
                    "            const p = word.slice(0, i) + '*' + word.slice(i + 1);\n"
                    "            for (const nxt of (patternMap.get(p) || [])) {\n"
                    "                if (nxt === endWord) return steps + 1;\n"
                    "                if (!visited.has(nxt)) {\n"
                    "                    visited.add(nxt);\n"
                    "                    queue.push([nxt, steps + 1]);\n"
                    "                }\n"
                    "            }\n"
                    "            patternMap.set(p, []);\n"
                    "        }\n"
                    "    }\n"
                    "    return 0;\n"
                    "}"
                ),
                "java": (
                    "public int ladderLength(String beginWord, String endWord, List<String> wordList) {\n"
                    "    Set<String> wordSet = new HashSet<>(wordList);\n"
                    "    if (!wordSet.contains(endWord)) return 0;\n"
                    "    int M = beginWord.length();\n"
                    "    Map<String, List<String>> patternMap = new HashMap<>();\n"
                    "    for (String word : wordSet) {\n"
                    "        for (int i = 0; i < M; i++) {\n"
                    "            String p = word.substring(0, i) + '*' + word.substring(i + 1);\n"
                    "            patternMap.computeIfAbsent(p, k -> new ArrayList<>()).add(word);\n"
                    "        }\n"
                    "    }\n"
                    "    Deque<String[]> queue = new ArrayDeque<>();\n"
                    "    queue.offer(new String[]{beginWord, \"1\"});\n"
                    "    Set<String> visited = new HashSet<>();\n"
                    "    visited.add(beginWord);\n"
                    "    while (!queue.isEmpty()) {\n"
                    "        String[] cur = queue.poll();\n"
                    "        String word = cur[0];\n"
                    "        int steps = Integer.parseInt(cur[1]);\n"
                    "        for (int i = 0; i < M; i++) {\n"
                    "            String p = word.substring(0, i) + '*' + word.substring(i + 1);\n"
                    "            for (String nxt : patternMap.getOrDefault(p, Collections.emptyList())) {\n"
                    "                if (nxt.equals(endWord)) return steps + 1;\n"
                    "                if (!visited.contains(nxt)) {\n"
                    "                    visited.add(nxt);\n"
                    "                    queue.offer(new String[]{nxt, String.valueOf(steps + 1)});\n"
                    "                }\n"
                    "            }\n"
                    "            patternMap.put(p, new ArrayList<>());\n"
                    "        }\n"
                    "    }\n"
                    "    return 0;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Bidirectional BFS",
            "time_complexity": "O(M² · N)",
            "space_complexity": "O(M² · N)",
            "description": (
                "Run BFS from both ends simultaneously, expanding the smaller frontier each iteration. "
                "Stop when the two frontiers intersect. Same big-O, but in practice prunes the search "
                "tree dramatically — the explored set goes from `b^d` to roughly `2·b^(d/2)` where `b` is "
                "the branching factor and `d` the path length."
            ),
            "code": {
                "python": (
                    "from collections import defaultdict\n"
                    "\n"
                    "def ladder_length(beginWord, endWord, wordList):\n"
                    "    word_set = set(wordList)\n"
                    "    if endWord not in word_set:\n"
                    "        return 0\n"
                    "    M = len(beginWord)\n"
                    "    pattern_map = defaultdict(list)\n"
                    "    for word in word_set:\n"
                    "        for i in range(M):\n"
                    "            pattern_map[word[:i] + '*' + word[i+1:]].append(word)\n"
                    "\n"
                    "    front = {beginWord}\n"
                    "    back = {endWord}\n"
                    "    visited = {beginWord, endWord}\n"
                    "    steps = 1\n"
                    "    while front and back:\n"
                    "        if len(front) > len(back):\n"
                    "            front, back = back, front\n"
                    "        next_front = set()\n"
                    "        for word in front:\n"
                    "            for i in range(M):\n"
                    "                p = word[:i] + '*' + word[i+1:]\n"
                    "                for nxt in pattern_map[p]:\n"
                    "                    if nxt in back:\n"
                    "                        return steps + 1\n"
                    "                    if nxt not in visited:\n"
                    "                        visited.add(nxt)\n"
                    "                        next_front.add(nxt)\n"
                    "        front = next_front\n"
                    "        steps += 1\n"
                    "    return 0"
                ),
            },
        },
    ],
    "thought_process": [
        "1. 'Shortest transformation sequence' on an unweighted implicit graph → BFS. DFS would explore exponentially.",
        "2. Naive neighbour discovery compares each word to every other (O(N²·M)). Too slow at N = 5000.",
        "3. Pattern-map trick: bucket words by wildcard pattern. Each word generates M patterns; lookup is O(1). Neighbour discovery becomes O(M²) per word.",
        "4. Edge case: if `endWord` not in `wordList`, return 0 immediately. The problem statement requires every intermediate (including the last) to be in the list.",
        "5. Mark visited on enqueue, not on dequeue — otherwise the same node enters the queue many times and BFS becomes quadratic.",
        "6. Bidirectional BFS for hard instances: expand the smaller frontier. Stop when frontiers meet.",
        "7. Length convention: LeetCode counts both endpoints. So `hit → hot → ... → cog` of 5 nodes returns 5, not 4.",
    ],
    "tips": [
        "Always check `endWord in wordList` first. Saves an entire BFS for the impossible case.",
        "After processing a pattern bucket, clear it (`pattern_map[p] = []`). Same words won't be visited again, so re-scanning the bucket is wasted work.",
        "Don't build a full adjacency list — the pattern map *is* the adjacency, just lazily evaluated.",
        "If begin == end, LC convention is to return 0 unless a *non-trivial* one-edit transformation forms a cycle. In practice the standard implementation returns 0 because BFS treats `beginWord` as visited from the start.",
        "Word Ladder II (return all shortest sequences) builds on this: same BFS, but record predecessors layer-by-layer, then DFS-reconstruct paths from `endWord`.",
        "For very large alphabets (not just 26 lowercase letters), the pattern-map approach still wins because patterns depend on word length, not alphabet size.",
    ],
    "companies": ["Amazon", "Facebook", "Google", "Microsoft", "LinkedIn", "Bloomberg"],
    "topics": ["Breadth-First Search", "Hash Table", "String", "Graph"],
    "time_complexity": "O(M² · N)",
    "space_complexity": "O(M² · N)",
}


def REFERENCE(beginWord, endWord, wordList):
    word_set = set(wordList)
    if endWord not in word_set:
        return 0
    M = len(beginWord)
    pattern_map = defaultdict(list)
    for word in word_set:
        for i in range(M):
            pattern_map[word[:i] + '*' + word[i + 1:]].append(word)

    queue = deque([(beginWord, 1)])
    visited = {beginWord}
    while queue:
        word, steps = queue.popleft()
        for i in range(M):
            pattern = word[:i] + '*' + word[i + 1:]
            for nxt in pattern_map[pattern]:
                if nxt == endWord:
                    return steps + 1
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, steps + 1))
            pattern_map[pattern] = []
    return 0


register(PAYLOAD, REFERENCE)
