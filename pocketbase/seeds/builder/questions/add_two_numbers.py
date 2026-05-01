"""Add Two Numbers — Medium. Linked List / Math / Simulation.

LeetCode 2. Two non-empty linked lists hold non-negative integers with
their digits stored in *reverse* order (least significant digit first),
which is the gift the problem hands you — addition naturally flows
low-to-high, so a single forward walk with a running carry suffices.
No reversing, no length-matching prep work.

Two-list inputs, so we use `driver_kind: "function"` (the linked_list
driver only carries one head). Inputs are encoded as flat Python lists
of digits; the function returns a list of digits in the same reverse
order. The carry-propagation pattern shows up again in big-integer
addition, multi-precision arithmetic, and 'plus one' style problems.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Add Two Numbers",
    "difficulty": "Medium",
    "description": (
        "You are given two **non-empty** linked lists representing two non-negative integers. The digits "
        "are stored in **reverse order**, and each node contains a single digit. Add the two numbers and "
        "return the sum as a linked list, also in reverse order.\n\n"
        "You may assume the two numbers do not contain any leading zero, except the number 0 itself.\n\n"
        "For this harness, each linked list is encoded as a flat array of digits in least-significant-first "
        "order; return the resulting digits as an array in the same order.\n\n"
        "**Example 1:**\n"
        "- Input: `l1 = [2,4,3]`, `l2 = [5,6,4]`\n"
        "- Output: `[7,0,8]`\n"
        "- Explanation: 342 + 465 = 807. Digits are stored low-to-high, so 807 → `[7,0,8]`.\n\n"
        "**Example 2:**\n"
        "- Input: `l1 = [9,9,9,9,9,9,9]`, `l2 = [9,9,9,9]`\n"
        "- Output: `[8,9,9,9,0,0,0,1]`\n"
        "- Explanation: 9999999 + 9999 = 10009998. Note the final carry produces a new most-significant digit."
    ),
    "hints": [
        "Digits are stored *least significant first* — that's the gift. Addition propagates carry from low to high, so you walk both lists head-to-tail in lockstep, exactly the direction the data is laid out in.",
        "Maintain a running `carry` (0 or 1). At each step `total = d1 + d2 + carry`; the new digit is `total % 10` and the new carry is `total // 10`.",
        "The lists can have different lengths. Treat the missing digit as 0 once one list runs out — keep walking until *both* are exhausted.",
        "Don't forget the **final carry**. After both lists are consumed, if `carry == 1` you still need to append one more digit (e.g. 99 + 1 = 100 — three digits from two two-digit inputs).",
        "Use a dummy-head sentinel for the output. It removes the 'is the result empty yet?' branch on every iteration — same trick as in Merge Two Sorted Lists.",
    ],
    "constraints": [
        "1 <= |l1|, |l2| <= 100",
        "0 <= node value <= 9",
        "Neither input has leading zeros (except the number 0 itself, encoded as `[0]`)",
    ],
    "starter_code": {
        "python": "def add_two_numbers(l1, l2):\n    # Your code here\n    pass",
        "javascript": "function addTwoNumbers(l1, l2) {\n    // Your code here\n}",
        "java": "public List<Integer> addTwoNumbers(List<Integer> l1, List<Integer> l2) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([2,4,3], [5,6,4]), ([0], [0]), ([9,9,9,9,9,9,9], [9,9,9,9])]\n"
            "    for l1, l2 in cases:\n"
            "        print(f\"add_two_numbers({l1}, {l2}) = {add_two_numbers(l1, l2)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[2,4,3],[5,6,4]], [[0],[0]], [[9,9,9,9,9,9,9],[9,9,9,9]]].forEach(([l1, l2]) =>\n"
            "    console.log(`addTwoNumbers =`, addTwoNumbers(l1, l2))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.addTwoNumbers(List.of(2,4,3), List.of(5,6,4)));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"l1": [2, 4, 3], "l2": [5, 6, 4]},
         "expected": [7, 0, 8],
         "description": "LeetCode canonical — 342 + 465 = 807",
         "tags": ["basic"]},
        {"input": {"l1": [0], "l2": [0]},
         "expected": [0],
         "description": "Both zero — single-digit result",
         "tags": ["edge"]},
        {"input": {"l1": [9, 9, 9, 9, 9, 9, 9], "l2": [9, 9, 9, 9]},
         "expected": [8, 9, 9, 9, 0, 0, 0, 1],
         "description": "Different lengths + cascading carry — 9999999 + 9999 = 10009998",
         "tags": ["tricky"]},
        {"input": {"l1": [1, 8], "l2": [0]},
         "expected": [1, 8],
         "description": "Adding zero — result equals the non-zero operand",
         "tags": ["edge"]},
        {"input": {"l1": [5], "l2": [5]},
         "expected": [0, 1],
         "description": "Single-digit final carry — 5 + 5 = 10",
         "tags": ["edge"]},
        {"input": {"l1": [1], "l2": [9, 9, 9]},
         "expected": [0, 0, 0, 1],
         "description": "Tiny + huge with cascading carry — 1 + 999 = 1000",
         "tags": ["tricky"]},
        {"input": {"l1": [2, 4], "l2": [5, 6, 4]},
         "expected": [7, 0, 5],
         "description": "Different lengths, no final carry — 42 + 465 = 507",
         "tags": ["basic"]},
        {"input": {"l1": [0, 0, 1], "l2": [0, 0, 1]},
         "expected": [0, 0, 2],
         "description": "Interior zeros preserved — 100 + 100 = 200",
         "tags": ["tricky"]},
        {"input": {"l1": [9], "l2": [1, 9, 9, 9, 9, 9, 9, 9, 9, 9]},
         "expected": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
         "description": "Single digit triggers carry through 10 nines — adds a new MSB",
         "tags": ["large"]},
        {"input": {"l1": [1] + [0] * 99, "l2": [9] + [0] * 99},
         "expected": [0, 1] + [0] * 98,
         "description": "Constraint upper bound — 100 digits each, single carry at index 0",
         "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Elementary School Addition with Carry (Optimal)",
            "time_complexity": "O(max(m, n))",
            "space_complexity": "O(max(m, n)) for the output (O(1) extra)",
            "description": (
                "Walk both lists in lockstep with a running `carry`. At each position, sum `d1 + d2 + carry`; "
                "emit `total % 10` and update `carry = total // 10`. The reverse-order encoding aligns the "
                "digits exactly the way you'd add them by hand — least significant first, carry propagates "
                "rightward (in array index terms). Treat a shorter list's missing digits as zero, and after "
                "the loop, if `carry` is still 1, append it as the new most-significant digit. A single loop "
                "guarded by `i < len(l1) or j < len(l2) or carry` handles all three termination conditions "
                "uniformly — that's the classic elegance trick."
            ),
            "code": {
                "python": (
                    "def add_two_numbers(l1, l2):\n"
                    "    out = []\n"
                    "    i = j = 0\n"
                    "    carry = 0\n"
                    "    # Loop while either list has digits left OR there's a pending carry.\n"
                    "    while i < len(l1) or j < len(l2) or carry:\n"
                    "        d1 = l1[i] if i < len(l1) else 0\n"
                    "        d2 = l2[j] if j < len(l2) else 0\n"
                    "        total = d1 + d2 + carry\n"
                    "        out.append(total % 10)\n"
                    "        carry = total // 10\n"
                    "        i += 1\n"
                    "        j += 1\n"
                    "    return out"
                ),
                "javascript": (
                    "function addTwoNumbers(l1, l2) {\n"
                    "    const out = [];\n"
                    "    let i = 0, j = 0, carry = 0;\n"
                    "    while (i < l1.length || j < l2.length || carry) {\n"
                    "        const d1 = i < l1.length ? l1[i] : 0;\n"
                    "        const d2 = j < l2.length ? l2[j] : 0;\n"
                    "        const total = d1 + d2 + carry;\n"
                    "        out.push(total % 10);\n"
                    "        carry = Math.floor(total / 10);\n"
                    "        i++; j++;\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
                "java": (
                    "public List<Integer> addTwoNumbers(List<Integer> l1, List<Integer> l2) {\n"
                    "    List<Integer> out = new ArrayList<>();\n"
                    "    int i = 0, j = 0, carry = 0;\n"
                    "    while (i < l1.size() || j < l2.size() || carry > 0) {\n"
                    "        int d1 = i < l1.size() ? l1.get(i) : 0;\n"
                    "        int d2 = j < l2.size() ? l2.get(j) : 0;\n"
                    "        int total = d1 + d2 + carry;\n"
                    "        out.add(total % 10);\n"
                    "        carry = total / 10;\n"
                    "        i++; j++;\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Convert to Int + Add + Reconstruct (Anti-Pattern)",
            "time_complexity": "O(max(m, n))",
            "space_complexity": "O(max(m, n))",
            "description": (
                "Decode each list into an integer, add them, then peel digits back off the sum. "
                "Tempting in Python where ints are arbitrary precision, but a trap in any language with "
                "fixed-width integers (Java `int` overflows at 10 digits, `long` at 19) — and the problem "
                "allows up to 100 digits, which exceeds `BigInteger`-free arithmetic anywhere. State this "
                "as the 'why we don't do it that way' baseline so the interviewer hears you considered and "
                "rejected it; never submit it in a typed language."
            ),
            "code": {
                "python": (
                    "def add_two_numbers(l1, l2):\n"
                    "    # Decode reverse-order digits into an int.\n"
                    "    n1 = sum(d * 10 ** i for i, d in enumerate(l1))\n"
                    "    n2 = sum(d * 10 ** i for i, d in enumerate(l2))\n"
                    "    total = n1 + n2\n"
                    "    if total == 0:\n"
                    "        return [0]\n"
                    "    out = []\n"
                    "    while total:\n"
                    "        out.append(total % 10)\n"
                    "        total //= 10\n"
                    "    return out"
                ),
                "javascript": (
                    "function addTwoNumbers(l1, l2) {\n"
                    "    // BigInt because Number loses precision past 2^53.\n"
                    "    const decode = (l) => l.reduce((acc, d, i) => acc + BigInt(d) * 10n ** BigInt(i), 0n);\n"
                    "    let total = decode(l1) + decode(l2);\n"
                    "    if (total === 0n) return [0];\n"
                    "    const out = [];\n"
                    "    while (total > 0n) { out.push(Number(total % 10n)); total /= 10n; }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Recursive Carry Propagation",
            "time_complexity": "O(max(m, n))",
            "space_complexity": "O(max(m, n)) call stack",
            "description": (
                "Same recurrence as the iterative form, but expressed recursively: `add(l1, l2, carry)` "
                "returns the digits from this position onward. Elegant on paper, but with up to 100 digits "
                "the stack depth is fine — note however the iterative form is preferred in interview "
                "answers because it generalises better and avoids stack-overflow concerns on bigger variants."
            ),
            "code": {
                "python": (
                    "def add_two_numbers(l1, l2):\n"
                    "    def rec(i, j, carry):\n"
                    "        if i >= len(l1) and j >= len(l2) and carry == 0:\n"
                    "            return []\n"
                    "        d1 = l1[i] if i < len(l1) else 0\n"
                    "        d2 = l2[j] if j < len(l2) else 0\n"
                    "        total = d1 + d2 + carry\n"
                    "        return [total % 10] + rec(i + 1, j + 1, total // 10)\n"
                    "    return rec(0, 0, 0)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Notice the gift: digits are stored *reverse* order. That means the head of each list is the ones place — exactly where addition starts. No reversing or right-aligning needed.",
        "2. Sketch the by-hand process: stack the numbers, add column by column, carry propagates rightward (toward the more-significant end, which here is the *tail* of the list). One pointer per list, one running `carry`.",
        "3. Handle different lengths: when one list is shorter, treat its missing digit as 0. Don't stop when the shorter one ends — the longer one might still have carries flowing through.",
        "4. Don't forget the final carry. 99 + 1 = 100 — two two-digit inputs produce a three-digit result. The classic bug here is exiting the loop the moment both lists are exhausted; you need `carry` in the loop guard too.",
        "5. Single unified loop: `while i < len(l1) or j < len(l2) or carry:`. This collapses three exit conditions into one and removes the 'now mop up the leftover' epilogue.",
        "6. Edge cases shake out: `[0] + [0] = [0]` (one iteration, total 0, no carry, append 0, exit). `[5] + [5] = [0, 1]` (one iteration emits 0 with carry=1, second iteration runs purely for the carry, emits 1, exits). Different lengths: shorter pointer just keeps reading 0.",
        "7. Mention the int-conversion approach — and reject it. In Python it works, but the interviewer is testing whether you can manage *digit-level* arithmetic. In Java/JS it fails outright at ~10–18 digits, and the problem allows up to 100.",
    ],
    "tips": [
        "The unified-loop trick (`while i < ... or j < ... or carry:`) is worth committing to muscle memory — same shape as 'merge two sorted lists with leftovers' and 'add two binary strings'.",
        "Compute the digit *before* updating the carry: `digit = total % 10; carry = total // 10`. Order doesn't matter mathematically here, but stay consistent so you don't accidentally zero out `total` first.",
        "On real linked lists, build the output by appending to a `tail` pointer behind a `dummy` head — same dummy-sentinel trick as Merge Two Sorted Lists. The harness uses an array, but narrate the in-place version.",
        "Direct follow-up — Add Two Numbers II (LC 445): same problem but digits are stored *most significant first*. Two clean approaches: reverse both inputs (then this exact algorithm), or push onto two stacks and pop in lockstep.",
        "Direct follow-up — Plus One (LC 66): increment a digit array by 1. Same carry-propagation pattern, simplified to one input and one initial carry.",
        "Don't try to cap the loop at `max(len(l1), len(l2))`. The final carry can extend past both — the `or carry` clause is the load-bearing piece.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Bloomberg", "Adobe", "Facebook"],
    "topics": ["Linked List", "Math", "Simulation"],
    "time_complexity": "O(max(m, n))",
    "space_complexity": "O(max(m, n)) for output",
}


def REFERENCE(l1, l2):
    out = []
    i = j = 0
    carry = 0
    while i < len(l1) or j < len(l2) or carry:
        d1 = l1[i] if i < len(l1) else 0
        d2 = l2[j] if j < len(l2) else 0
        total = d1 + d2 + carry
        out.append(total % 10)
        carry = total // 10
        i += 1
        j += 1
    return out


register(PAYLOAD, REFERENCE)
