"""Unique Linked List — Easy. Hashing.

Walk a singly-linked list of strings, return True iff every value is
distinct. Surface the cycle and null-handling concerns explicitly —
that's where bar-raising answers diverge from baseline ones.

The linked list is represented here as a plain Python list (the values
in arrival order). The semantic question — uniqueness — is preserved;
the underlying datastructure is incidental for the algorithm."""
from builder.registry import register


PAYLOAD = {
    "title": "Unique Linked List Values",
    "difficulty": "Easy",
    "description": (
        "Given a linked list of strings, return `true` if every value is unique, otherwise `false`. The "
        "list may be empty.\n\n"
        "**Example 1:**\n"
        "- Input: `head = ['a', 'b', 'c']`\n"
        "- Output: `true`\n\n"
        "**Example 2:**\n"
        "- Input: `head = ['x', 'y', 'x']`\n"
        "- Output: `false`\n\n"
        "**Note:** for testing purposes the list is represented as a flat array of node values in order. "
        "Cycles aren't representable in this serialisation, but the interview discussion should still cover "
        "what would happen if the list cycled."
    ),
    "hints": [
        "Hash set: walk once, return false the moment a value is already in the set. O(n) time, O(n) space.",
        "Sort: copy, sort, scan adjacent. O(n log n) time, O(n) space if you must clone (you can't sort a singly linked list in place efficiently without merge sort).",
        "Brute force: for each node, scan the rest of the list. O(n²) time, O(1) space. State it as the baseline.",
        "Cycle gotcha: if the list cycles, naive walks loop forever. Use Floyd's tortoise/hare to detect cycles, or bound the walk by the set's size.",
        "Null gotcha: empty list is trivially unique (return true). Single null value is also unique.",
    ],
    "constraints": [
        "0 <= n <= 10⁴",
        "Values are arbitrary strings",
    ],
    "starter_code": {
        "python": "def is_unique_list(values):\n    # Your code here\n    pass",
        "javascript": "function isUniqueList(values) {\n    // Your code here\n}",
        "java": "public boolean isUniqueList(List<String> values) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for v in [['a','b','c'], ['x','y','x'], [], ['only']]:\n"
            "        print(f\"is_unique_list({v}) = {is_unique_list(v)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[['a','b','c'], ['x','y','x']].forEach(v =>\n"
            "    console.log(`isUniqueList(${JSON.stringify(v)}) =`, isUniqueList(v))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main { public static void main(String[] args) {} }"
        ),
    },
    "test_cases": [
        {"input": {"values": ["a", "b", "c"]}, "expected": True,
         "description": "All distinct strings", "tags": ["basic"]},
        {"input": {"values": ["x", "y", "x"]}, "expected": False,
         "description": "Single duplicate", "tags": ["basic"]},
        {"input": {"values": []}, "expected": True,
         "description": "Empty list — vacuously unique", "tags": ["edge"]},
        {"input": {"values": ["solo"]}, "expected": True,
         "description": "Single element", "tags": ["edge"]},
        {"input": {"values": ["", "", "x"]}, "expected": False,
         "description": "Empty-string duplicates count as duplicates", "tags": ["edge"]},
        {"input": {"values": ["A", "a"]}, "expected": True,
         "description": "Case-sensitive — uppercase and lowercase are distinct", "tags": ["edge"]},
        {"input": {"values": [str(i) for i in range(10000)]}, "expected": True,
         "description": "10K distinct strings", "tags": ["large"]},
        {"input": {"values": [str(i) for i in range(9999)] + ["42"]}, "expected": False,
         "description": "10K mostly-distinct with a late duplicate", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Hash Set (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk once. Maintain a set of seen strings. Return false the moment a value is already in "
                "the set; return true after the walk completes."
            ),
            "code": {
                "python": (
                    "def is_unique_list(values):\n"
                    "    seen = set()\n"
                    "    for v in values:\n"
                    "        if v in seen:\n"
                    "            return False\n"
                    "        seen.add(v)\n"
                    "    return True"
                ),
                "javascript": (
                    "function isUniqueList(values) {\n"
                    "    const seen = new Set();\n"
                    "    for (const v of values) {\n"
                    "        if (seen.has(v)) return false;\n"
                    "        seen.add(v);\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
                "java": (
                    "public boolean isUniqueList(List<String> values) {\n"
                    "    Set<String> seen = new HashSet<>();\n"
                    "    for (String v : values) {\n"
                    "        if (!seen.add(v)) return false;\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Sort + Adjacent Compare",
            "time_complexity": "O(n log n)",
            "space_complexity": "O(n)",
            "description": (
                "Clone, sort, scan adjacent. Wins when memory is genuinely tight (you trade time for "
                "space). For singly-linked lists, merge sort is the only in-place option."
            ),
            "code": {
                "python": (
                    "def is_unique_list(values):\n"
                    "    arr = sorted(values)\n"
                    "    for i in range(1, len(arr)):\n"
                    "        if arr[i] == arr[i - 1]:\n"
                    "            return False\n"
                    "    return True"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "For each node, scan the rest of the list for a matching value. Mention this as the baseline "
                "to demonstrate awareness; never submit it."
            ),
            "code": {
                "python": (
                    "def is_unique_list(values):\n"
                    "    for i in range(len(values)):\n"
                    "        for j in range(i + 1, len(values)):\n"
                    "            if values[i] == values[j]:\n"
                    "                return False\n"
                    "    return True"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: 'every value distinct → true; any duplicate → false.'",
        "2. State brute force (O(n²)). Then move to set-based O(n).",
        "3. Surface the trade-off: hashing is fastest but uses O(n) memory; sort is O(n log n) with O(1)-ish extra (merge-sort in place for linked lists).",
        "4. Bring up the cycle case unprompted: 'on a real linked list, a cycle would loop forever — I'd need Floyd's, or to bound by set size.' That's the bar-raising signal.",
        "5. Edge cases: empty list, single element, empty strings, case-sensitive duplicates, very large input.",
    ],
    "tips": [
        "Saying `len(set(values)) != len(values)` is correct but skips the data-structure narration the interviewer wants to hear.",
        "Don't forget the cycle discussion — the interviewer is listening for it specifically (it's the canonical follow-up).",
        "Java: `set.add(v)` returns false if the element was already present — one-liner the check.",
        "Common follow-up: 'O(1) extra memory required.' That kills the hash set; sort or two-pointer if values are bounded.",
        "Common follow-up: 'streaming list of strings.' Set-based works incrementally; sort-based doesn't.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg"],
    "topics": ["Linked List", "Hash Table"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(values):
    seen = set()
    for v in values:
        if v in seen:
            return False
        seen.add(v)
    return True


register(PAYLOAD, REFERENCE)
