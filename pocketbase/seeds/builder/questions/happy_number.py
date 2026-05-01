"""Happy Number — Easy. Hash Set / Cycle Detection / Math.

The 'is this an iterated function eventually 1, or does it cycle?' problem.
The hidden insight: every unhappy number's trajectory eventually lands in
the cycle [4, 16, 37, 58, 89, 145, 42, 20] (and back to 4). So the question
reduces to classic cycle-detection — either remember everything you've seen
(hash set) or run Floyd's tortoise-and-hare on the squared-digit-sum
function. Same shape as Linked List Cycle, applied to integers.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Happy Number",
    "difficulty": "Easy",
    "description": (
        "Write an algorithm to determine if a number `n` is **happy**.\n\n"
        "A happy number is defined by the following process:\n"
        "- Starting with any positive integer, replace the number by the **sum of the squares of its digits**.\n"
        "- Repeat the process until the number equals `1` (where it stays), or it **loops endlessly in a cycle** "
        "that does not include `1`.\n"
        "- Numbers for which this process **ends in 1** are happy.\n\n"
        "Return `True` if `n` is a happy number, and `False` if it is not.\n\n"
        "**Example 1:**\n"
        "- Input: `n = 19`\n"
        "- Output: `True`\n"
        "- Explanation: 1² + 9² = 82 → 8² + 2² = 68 → 6² + 8² = 100 → 1² + 0² + 0² = 1.\n\n"
        "**Example 2:**\n"
        "- Input: `n = 2`\n"
        "- Output: `False`\n"
        "- Explanation: 2 → 4 → 16 → 37 → 58 → 89 → 145 → 42 → 20 → 4 (cycle, never reaches 1)."
    ),
    "hints": [
        "The process either reaches 1 (happy) or repeats a value forever (unhappy). There is no third option — "
        "for any starting `n`, the squared-digit-sum stays bounded (a 10-digit number maps to at most 810), so "
        "by pigeonhole the sequence must eventually revisit a value.",
        "Cycle detection is the framing. Option A: keep a `set` of values you've seen. If you ever produce a "
        "value already in the set, you're in a cycle → return False. If you produce 1, return True.",
        "Option B (O(1) space): Floyd's tortoise-and-hare. Treat `next = sum_of_squares(current)` as the 'next "
        "node' function. Advance `slow` by one step and `fast` by two steps until they meet or `fast` hits 1.",
        "Helper: `sum_of_squares(n)` — peel off digits with `n % 10`, square, accumulate, then `n //= 10`. "
        "Loop while `n > 0`.",
        "Trivia worth knowing: every unhappy number's trajectory eventually enters the fixed cycle "
        "`[4, 16, 37, 58, 89, 145, 42, 20]`. So a third (less elegant) option is to hard-code that cycle and "
        "return False the moment you hit any of those eight numbers. Clever in interviews, but the hash-set or "
        "Floyd's solutions are the expected answers.",
    ],
    "constraints": [
        "1 <= n <= 2³¹ - 1",
        "n fits in a 32-bit signed integer.",
        "The squared-digit-sum of any input is bounded (≤ 10 digits × 81 = 810), so the sequence is finite-state.",
    ],
    "starter_code": {
        "python": "def is_happy(n):\n    # Your code here\n    pass",
        "javascript": "function isHappy(n) {\n    // Your code here\n}",
        "java": "public boolean isHappy(int n) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for n in [19, 2, 1, 7]:\n"
            "        print(f\"is_happy({n}) = {is_happy(n)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[19, 2, 1, 7].forEach(n =>\n"
            "    console.log(`isHappy(${n}) =`, isHappy(n))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.isHappy(19));\n"
            "        System.out.println(s.isHappy(2));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"n": 19}, "expected": True,
         "description": "Classic happy number — 19 → 82 → 68 → 100 → 1", "tags": ["basic"]},
        {"input": {"n": 2}, "expected": False,
         "description": "Falls into the [4,16,37,58,89,145,42,20] cycle", "tags": ["basic"]},
        {"input": {"n": 1}, "expected": True,
         "description": "Already 1 — happy by definition", "tags": ["edge"]},
        {"input": {"n": 7}, "expected": True,
         "description": "Chains 7 → 49 → 97 → 130 → 10 → 1", "tags": ["tricky"]},
        {"input": {"n": 4}, "expected": False,
         "description": "Immediately enters the unhappy cycle (4 is in the cycle itself)", "tags": ["edge"]},
        {"input": {"n": 100}, "expected": True,
         "description": "100 → 1 in a single step (1² + 0² + 0² = 1)", "tags": ["edge"]},
        {"input": {"n": 23}, "expected": True,
         "description": "23 → 13 → 10 → 1", "tags": ["basic"]},
        {"input": {"n": 20}, "expected": False,
         "description": "20 is in the cycle — 20 → 4 → 16 → ... → 20", "tags": ["tricky"]},
        {"input": {"n": 1111111}, "expected": True,
         "description": "Seven ones → 7 → ... → 1 (large happy)", "tags": ["large"]},
        {"input": {"n": 1234567}, "expected": False,
         "description": "Large unhappy number — sums into the cycle", "tags": ["large"]},
        {"input": {"n": 1999999999}, "expected": False,
         "description": "Very large 10-digit input near INT_MAX — enters the cycle", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Hash Set Cycle Detection (Optimal)",
            "time_complexity": "O(log n)",
            "space_complexity": "O(log n)",
            "description": (
                "Iterate the squared-digit-sum function. Keep a `seen` set of every value produced. If we hit "
                "1, return True. If we hit a value already in `seen`, we're in a cycle → return False. The "
                "number of distinct values before a repeat is bounded by ~243 (the largest fixed point of the "
                "step for 3-digit-or-fewer inputs), so this is effectively O(log n) on the input size and "
                "constant for practical n."
            ),
            "code": {
                "python": (
                    "def is_happy(n):\n"
                    "    def step(x):\n"
                    "        total = 0\n"
                    "        while x > 0:\n"
                    "            x, d = divmod(x, 10)\n"
                    "            total += d * d\n"
                    "        return total\n"
                    "\n"
                    "    seen = set()\n"
                    "    while n != 1 and n not in seen:\n"
                    "        seen.add(n)\n"
                    "        n = step(n)\n"
                    "    return n == 1"
                ),
                "javascript": (
                    "function isHappy(n) {\n"
                    "    const step = (x) => {\n"
                    "        let total = 0;\n"
                    "        while (x > 0) {\n"
                    "            const d = x % 10;\n"
                    "            total += d * d;\n"
                    "            x = Math.floor(x / 10);\n"
                    "        }\n"
                    "        return total;\n"
                    "    };\n"
                    "    const seen = new Set();\n"
                    "    while (n !== 1 && !seen.has(n)) {\n"
                    "        seen.add(n);\n"
                    "        n = step(n);\n"
                    "    }\n"
                    "    return n === 1;\n"
                    "}"
                ),
                "java": (
                    "public boolean isHappy(int n) {\n"
                    "    java.util.Set<Integer> seen = new java.util.HashSet<>();\n"
                    "    while (n != 1 && !seen.contains(n)) {\n"
                    "        seen.add(n);\n"
                    "        n = step(n);\n"
                    "    }\n"
                    "    return n == 1;\n"
                    "}\n"
                    "\n"
                    "private int step(int x) {\n"
                    "    int total = 0;\n"
                    "    while (x > 0) {\n"
                    "        int d = x % 10;\n"
                    "        total += d * d;\n"
                    "        x /= 10;\n"
                    "    }\n"
                    "    return total;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Floyd's Tortoise and Hare (Constant Space)",
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
            "description": (
                "Treat `step(x)` as the 'next-pointer' of an implicit linked list of integers. Advance `slow` "
                "by one step per iteration and `fast` by two. If the sequence reaches 1, `fast` will hit 1 "
                "first — return True. Otherwise `fast` and `slow` collide inside the cycle — return False. "
                "Drops the auxiliary set entirely."
            ),
            "code": {
                "python": (
                    "def is_happy(n):\n"
                    "    def step(x):\n"
                    "        total = 0\n"
                    "        while x > 0:\n"
                    "            x, d = divmod(x, 10)\n"
                    "            total += d * d\n"
                    "        return total\n"
                    "\n"
                    "    slow, fast = n, step(n)\n"
                    "    while fast != 1 and slow != fast:\n"
                    "        slow = step(slow)\n"
                    "        fast = step(step(fast))\n"
                    "    return fast == 1"
                ),
                "javascript": (
                    "function isHappy(n) {\n"
                    "    const step = (x) => {\n"
                    "        let total = 0;\n"
                    "        while (x > 0) {\n"
                    "            const d = x % 10;\n"
                    "            total += d * d;\n"
                    "            x = Math.floor(x / 10);\n"
                    "        }\n"
                    "        return total;\n"
                    "    };\n"
                    "    let slow = n, fast = step(n);\n"
                    "    while (fast !== 1 && slow !== fast) {\n"
                    "        slow = step(slow);\n"
                    "        fast = step(step(fast));\n"
                    "    }\n"
                    "    return fast === 1;\n"
                    "}"
                ),
                "java": (
                    "public boolean isHappy(int n) {\n"
                    "    int slow = n, fast = step(n);\n"
                    "    while (fast != 1 && slow != fast) {\n"
                    "        slow = step(slow);\n"
                    "        fast = step(step(fast));\n"
                    "    }\n"
                    "    return fast == 1;\n"
                    "}\n"
                    "\n"
                    "private int step(int x) {\n"
                    "    int total = 0;\n"
                    "    while (x > 0) {\n"
                    "        int d = x % 10;\n"
                    "        total += d * d;\n"
                    "        x /= 10;\n"
                    "    }\n"
                    "    return total;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Read carefully: the process either lands on 1 or loops. Decide which case is happening — that's a "
        "termination problem.",
        "2. Why must one of those two happen? Squared-digit-sum is bounded (≤ 810 for any 10-digit input), so "
        "the sequence is confined to a finite set and must revisit a value.",
        "3. Detect the revisit: classic cycle detection. Either remember everything (hash set) or use Floyd's "
        "tortoise-and-hare (O(1) space).",
        "4. Implement `step(n)` once: extract digits with `n % 10` / `n //= 10`, square, accumulate.",
        "5. Edge case: `n == 1` should return True without entering the loop. Both solutions handle it because "
        "the loop guard checks `n != 1` (or `fast != 1`) up front.",
        "6. Small flex if asked for trivia: every unhappy number lands in the cycle "
        "`[4, 16, 37, 58, 89, 145, 42, 20]`. Don't lead with this — interviewer wants cycle detection.",
    ],
    "tips": [
        "Always have `step(x)` as a helper. Inlining digit extraction inside the main loop makes the cycle-"
        "detection logic harder to read and Floyd's variant nearly impossible.",
        "Use `divmod(x, 10)` in Python — it returns quotient and remainder in one call, which mirrors the "
        "natural 'peel a digit, shift right' operation.",
        "Floyd's variant is the right answer if asked for O(1) space. Mention it even if you implement the hash-"
        "set version first — interviewers often follow up with the space constraint.",
        "Don't bother with BigInteger / overflow checks. The squared-digit-sum of even INT_MAX is at most "
        "10 × 81 = 810, so all intermediate values fit easily in a 32-bit int.",
        "Common follow-up — Linked List Cycle (LC 141): same Floyd's algorithm applied to actual list nodes "
        "instead of integers. If you nailed Floyd's here, that one's a 30-second write.",
        "Common follow-up — what's the largest possible value after one step? 10 digits × 9² = 810. Knowing "
        "this bound is sometimes asked to justify why the algorithm terminates.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Apple", "Bloomberg", "Airbnb"],
    "topics": ["Hash Table", "Math", "Two Pointers"],
    "time_complexity": "O(log n)",
    "space_complexity": "O(log n)",
}


def REFERENCE(n):
    def step(x):
        total = 0
        while x > 0:
            x, d = divmod(x, 10)
            total += d * d
        return total

    seen = set()
    while n != 1 and n not in seen:
        seen.add(n)
        n = step(n)
    return n == 1


register(PAYLOAD, REFERENCE)
