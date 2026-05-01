"""Look-and-Say Sequence Membership — Easy/Medium. Simulation.

Determine whether two integers belong to the same look-and-say
sequence. Generate the sequence forward from each candidate's seed."""
from builder.registry import register


PAYLOAD = {
    "title": "Look-and-Say Sequence Membership",
    "difficulty": "Medium",
    "description": (
        "The look-and-say sequence is built by 'reading aloud' the previous term: `1`, `11` (one one), "
        "`21` (two ones), `1211` (one two, one one), `111221` (one one, one two, two ones), `312211`, …\n\n"
        "Given two strings of digits `a` and `b`, return `True` if there exists a starting term `s` such "
        "that both `a` and `b` appear in the look-and-say sequence beginning with `s`. Equivalently: "
        "does iteratively applying the look-and-say transform from one of them eventually produce the "
        "other?\n\n"
        "**Example:**\n"
        "- `is_same_chain('1211', '111221')` → `True` ('1211' → '111221' is one step)\n"
        "- `is_same_chain('1', '111221')` → `True` ('1' → '11' → '21' → '1211' → '111221')\n"
        "- `is_same_chain('21', '12')` → `False` (these aren't in the same forward chain)"
    ),
    "hints": [
        "Generate forward from each candidate; if the chain from `a` ever produces `b`, true. Likewise from `b`.",
        "Cap iterations to avoid infinite loops on bad input.",
        "The look-and-say transform: walk the digits, count runs of equal digit, emit `<count><digit>`.",
        "Two terms are in the same chain iff one is a forward descendant of the other.",
        "Edge cases: `a == b` (true), one term shorter than the other, uniform-digit input that cycles.",
    ],
    "constraints": [
        "1 <= |a|, |b| <= 100",
        "Both are non-empty digit strings",
    ],
    "starter_code": {
        "python": "def is_same_chain(a, b):\n    # Your code here\n    pass",
        "javascript": "function isSameChain(a, b) {\n    // Your code here\n}",
        "java": "public boolean isSameChain(String a, String b) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(is_same_chain('1211', '111221'))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"a": "1211", "b": "111221"}, "expected": True,
         "description": "One step apart in canonical sequence", "tags": ["basic"]},
        {"input": {"a": "1", "b": "111221"}, "expected": True,
         "description": "4 steps apart in canonical sequence", "tags": ["basic"]},
        {"input": {"a": "21", "b": "12"}, "expected": False,
         "description": "Not in the same forward chain", "tags": ["basic"]},
        {"input": {"a": "5", "b": "5"}, "expected": True,
         "description": "Same string — trivially true", "tags": ["edge"]},
        {"input": {"a": "1", "b": "11"}, "expected": True,
         "description": "Adjacent in canonical sequence", "tags": ["basic"]},
        {"input": {"a": "111221", "b": "1"}, "expected": True,
         "description": "Reverse direction also true", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Forward Iteration with Cap (Optimal)",
            "time_complexity": "O(L · K) where K = max iterations, L = average term length",
            "space_complexity": "O(L)",
            "description": (
                "From `a`, iteratively apply the look-and-say transform. At each step, compare against `b`; "
                "stop on match or after a fixed cap. Repeat from `b`. Return true on either match."
            ),
            "code": {
                "python": (
                    "def is_same_chain(a, b):\n"
                    "    if a == b:\n"
                    "        return True\n"
                    "    return _reaches(a, b) or _reaches(b, a)\n\n"
                    "def _reaches(start, target, cap=30):\n"
                    "    cur = start\n"
                    "    for _ in range(cap):\n"
                    "        cur = _step(cur)\n"
                    "        if cur == target:\n"
                    "            return True\n"
                    "        if len(cur) > len(target) * 4:\n"
                    "            return False\n"
                    "    return False\n\n"
                    "def _step(s):\n"
                    "    if not s:\n"
                    "        return ''\n"
                    "    out = []\n"
                    "    i = 0\n"
                    "    while i < len(s):\n"
                    "        j = i\n"
                    "        while j < len(s) and s[j] == s[i]:\n"
                    "            j += 1\n"
                    "        out.append(str(j - i))\n"
                    "        out.append(s[i])\n"
                    "        i = j\n"
                    "    return ''.join(out)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. The look-and-say transform: count consecutive equal digits, emit `<count><digit>`.",
        "2. Forward chain: each term uniquely determines the next.",
        "3. To check if `a` and `b` are in the same chain, generate forward from each and check whether the other appears.",
        "4. Cap iterations (terms grow quickly — Conway's Cosmological Theorem says length growth ratio approaches Conway's constant ~1.303).",
        "5. Equality check at each step; bail early on `len(cur) > len(target)`.",
        "6. Edge cases: equal inputs, single-digit inputs, very long inputs.",
    ],
    "tips": [
        "Conway's constant: terms grow ~1.303× per step. Cap iterations to ~30 for safety.",
        "Don't recompute the transform — cache the chain and binary search by length if many queries.",
        "Common follow-up: 'find the n-th term.' Iterate n times from '1'.",
        "Common follow-up: 'is X in the canonical chain starting at 1?' Generate forward from '1'; bounded by Conway's constant.",
        "Common follow-up: 'why is 22 the only fixed point of the transform?' '22' transforms to '22' — proof is short and impressive in interview.",
    ],
    "companies": ["Amazon", "Microsoft"],
    "topics": ["String", "Simulation", "Math"],
    "time_complexity": "O(L · K)",
    "space_complexity": "O(L)",
}


def _step(s):
    if not s:
        return ""
    out = []
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out.append(str(j - i))
        out.append(s[i])
        i = j
    return "".join(out)


def _reaches(start, target, cap=30):
    cur = start
    for _ in range(cap):
        cur = _step(cur)
        if cur == target:
            return True
        if len(cur) > max(len(target), 4) * 4:
            return False
    return False


def REFERENCE(a, b):
    if a == b:
        return True
    return _reaches(a, b) or _reaches(b, a)


register(PAYLOAD, REFERENCE)
