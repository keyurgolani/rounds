"""Add Two Numbers — Medium. Linked List / Math / Simulation.

LeetCode 2. Two non-empty linked lists hold non-negative integers with
their digits stored in *reverse* order (least significant digit first),
which is the gift the problem hands you — addition naturally flows
low-to-high, so a single forward walk with a running carry suffices.
No reversing, no length-matching prep work.

The harness inflates the test-case digit arrays into real `ListNode`
chains before invoking the user function and deflates the returned
chain back to a flat array of digits for matching. The user works
with `ListNode` end-to-end."""
from builder.registry import register


PAYLOAD = {
    "title": "Add Two Numbers",
    "difficulty": "Medium",
    "description": (
        "You are given two **non-empty** linked lists representing two non-negative integers. The digits "
        "are stored in **reverse order**, and each node contains a single digit. Add the two numbers and "
        "return the sum as a linked list, also in reverse order.\n\n"
        "You may assume the two numbers do not contain any leading zero, except the number 0 itself.\n\n"
        "You receive `l1` and `l2` as `ListNode` head pointers (or `None`/`null` for an empty list). "
        "Return a `ListNode` head pointer (or `None`/`null`).\n\n"
        "**Example 1:**\n"
        "- Input: `l1 = 2 -> 4 -> 3`, `l2 = 5 -> 6 -> 4`\n"
        "- Output: `7 -> 0 -> 8`\n"
        "- Explanation: 342 + 465 = 807. Digits are stored low-to-high, so 807 is encoded head-to-tail as 7,0,8.\n\n"
        "**Example 2:**\n"
        "- Input: `l1 = 9 -> 9 -> 9 -> 9 -> 9 -> 9 -> 9`, `l2 = 9 -> 9 -> 9 -> 9`\n"
        "- Output: `8 -> 9 -> 9 -> 9 -> 0 -> 0 -> 0 -> 1`\n"
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
        "Neither input has leading zeros (except the number 0 itself, which is encoded as a single-node list with value 0)",
    ],
    "starter_code": {
        "python": (
            "# class ListNode:\n"
            "#     def __init__(self, val=0, next=None):\n"
            "#         self.val = val\n"
            "#         self.next = next\n"
            "\n"
            "def add_two_numbers(l1, l2):\n"
            "    # l1, l2 are ListNode heads (or None for an empty list).\n"
            "    # Return a ListNode head (or None).\n"
            "    pass"
        ),
        "javascript": (
            "// class ListNode {\n"
            "//   constructor(val=0, next=null) { this.val = val; this.next = next; }\n"
            "// }\n"
            "\n"
            "function addTwoNumbers(l1, l2) {\n"
            "    // l1, l2 are ListNode heads (or null for an empty list).\n"
            "    // Return a ListNode head (or null).\n"
            "}"
        ),
        "java": (
            "// NOTE: Java is display-only in this harness — code is shown for\n"
            "// reference but is not executed. Run/Evaluate use Python or JavaScript.\n"
            "//\n"
            "// class ListNode {\n"
            "//     int val;\n"
            "//     ListNode next;\n"
            "//     ListNode(int x) { val = x; next = null; }\n"
            "// }\n"
            "\n"
            "public ListNode addTwoNumbers(ListNode l1, ListNode l2) {\n"
            "    // Your code here\n"
            "    return null;\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "def _build(values):\n"
            "    head = None\n"
            "    for v in reversed(values):\n"
            "        head = ListNode(v, head)\n"
            "    return head\n"
            "\n"
            "def _walk(node):\n"
            "    out = []\n"
            "    while node:\n"
            "        out.append(node.val); node = node.next\n"
            "    return out\n"
            "\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([2,4,3], [5,6,4]), ([0], [0]), ([9,9,9,9,9,9,9], [9,9,9,9])]\n"
            "    for v1, v2 in cases:\n"
            "        result = add_two_numbers(_build(v1), _build(v2))\n"
            "        print(f\"add_two_numbers({v1}, {v2}) = {_walk(result)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "function _build(values) {\n"
            "    let head = null;\n"
            "    for (let i = values.length - 1; i >= 0; i--) head = new ListNode(values[i], head);\n"
            "    return head;\n"
            "}\n"
            "function _walk(node) {\n"
            "    const out = [];\n"
            "    while (node) { out.push(node.val); node = node.next; }\n"
            "    return out;\n"
            "}\n"
            "[[[2,4,3],[5,6,4]], [[0],[0]], [[9,9,9,9,9,9,9],[9,9,9,9]]].forEach(([v1, v2]) =>\n"
            "    console.log(`addTwoNumbers =`, _walk(addTwoNumbers(_build(v1), _build(v2))))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        // Java is display-only in this harness.\n"
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
                "head-to-tail. Treat a shorter list's missing digits as zero, and after the loop, if `carry` "
                "is still 1, append it as a new tail node. A single loop guarded by `l1 or l2 or carry` "
                "handles all three termination conditions uniformly. Build the output behind a dummy-head "
                "sentinel so you don't special-case the first append."
            ),
            "code": {
                "python": (
                    "def add_two_numbers(l1, l2):\n"
                    "    dummy = ListNode()\n"
                    "    tail = dummy\n"
                    "    carry = 0\n"
                    "    while l1 or l2 or carry:\n"
                    "        d1 = l1.val if l1 else 0\n"
                    "        d2 = l2.val if l2 else 0\n"
                    "        total = d1 + d2 + carry\n"
                    "        tail.next = ListNode(total % 10)\n"
                    "        tail = tail.next\n"
                    "        carry = total // 10\n"
                    "        l1 = l1.next if l1 else None\n"
                    "        l2 = l2.next if l2 else None\n"
                    "    return dummy.next"
                ),
                "javascript": (
                    "function addTwoNumbers(l1, l2) {\n"
                    "    const dummy = new ListNode();\n"
                    "    let tail = dummy, carry = 0;\n"
                    "    while (l1 || l2 || carry) {\n"
                    "        const d1 = l1 ? l1.val : 0;\n"
                    "        const d2 = l2 ? l2.val : 0;\n"
                    "        const total = d1 + d2 + carry;\n"
                    "        tail.next = new ListNode(total % 10);\n"
                    "        tail = tail.next;\n"
                    "        carry = Math.floor(total / 10);\n"
                    "        l1 = l1 ? l1.next : null;\n"
                    "        l2 = l2 ? l2.next : null;\n"
                    "    }\n"
                    "    return dummy.next;\n"
                    "}"
                ),
                "java": (
                    "public ListNode addTwoNumbers(ListNode l1, ListNode l2) {\n"
                    "    ListNode dummy = new ListNode(0);\n"
                    "    ListNode tail = dummy;\n"
                    "    int carry = 0;\n"
                    "    while (l1 != null || l2 != null || carry > 0) {\n"
                    "        int d1 = (l1 != null) ? l1.val : 0;\n"
                    "        int d2 = (l2 != null) ? l2.val : 0;\n"
                    "        int total = d1 + d2 + carry;\n"
                    "        tail.next = new ListNode(total % 10);\n"
                    "        tail = tail.next;\n"
                    "        carry = total / 10;\n"
                    "        if (l1 != null) l1 = l1.next;\n"
                    "        if (l2 != null) l2 = l2.next;\n"
                    "    }\n"
                    "    return dummy.next;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Convert to Int + Add + Reconstruct (Anti-Pattern)",
            "time_complexity": "O(max(m, n))",
            "space_complexity": "O(max(m, n))",
            "description": (
                "Walk both lists to decode each into an integer, add them, then peel digits back off the sum to build a result chain. "
                "Tempting in Python where ints are arbitrary precision, but a trap in any language with fixed-width "
                "integers (Java `int` overflows at 10 digits, `long` at 19) — and the problem allows up to 100 digits, "
                "which exceeds `BigInteger`-free arithmetic anywhere. State this as the 'why we don't do it that way' "
                "baseline so the interviewer hears you considered and rejected it; never submit it in a typed language."
            ),
            "code": {
                "python": (
                    "def add_two_numbers(l1, l2):\n"
                    "    # Decode the chain into an int, then peel digits off the sum.\n"
                    "    def decode(node):\n"
                    "        n, place = 0, 1\n"
                    "        while node:\n"
                    "            n += node.val * place\n"
                    "            place *= 10\n"
                    "            node = node.next\n"
                    "        return n\n"
                    "    total = decode(l1) + decode(l2)\n"
                    "    if total == 0:\n"
                    "        return ListNode(0)\n"
                    "    dummy = ListNode()\n"
                    "    tail = dummy\n"
                    "    while total:\n"
                    "        tail.next = ListNode(total % 10)\n"
                    "        tail = tail.next\n"
                    "        total //= 10\n"
                    "    return dummy.next"
                ),
                "javascript": (
                    "function addTwoNumbers(l1, l2) {\n"
                    "    // BigInt because Number loses precision past 2^53.\n"
                    "    const decode = (node) => {\n"
                    "        let n = 0n, place = 1n;\n"
                    "        while (node) {\n"
                    "            n += BigInt(node.val) * place;\n"
                    "            place *= 10n;\n"
                    "            node = node.next;\n"
                    "        }\n"
                    "        return n;\n"
                    "    };\n"
                    "    let total = decode(l1) + decode(l2);\n"
                    "    if (total === 0n) return new ListNode(0);\n"
                    "    const dummy = new ListNode();\n"
                    "    let tail = dummy;\n"
                    "    while (total > 0n) {\n"
                    "        tail.next = new ListNode(Number(total % 10n));\n"
                    "        tail = tail.next;\n"
                    "        total /= 10n;\n"
                    "    }\n"
                    "    return dummy.next;\n"
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
                "returns the head of the result chain from this position onward. Elegant on paper. "
                "With up to 100 digits the stack depth is fine; for bigger variants prefer the iterative "
                "form to avoid stack-overflow risk."
            ),
            "code": {
                "python": (
                    "def add_two_numbers(l1, l2):\n"
                    "    def rec(a, b, carry):\n"
                    "        if a is None and b is None and carry == 0:\n"
                    "            return None\n"
                    "        d1 = a.val if a else 0\n"
                    "        d2 = b.val if b else 0\n"
                    "        total = d1 + d2 + carry\n"
                    "        node = ListNode(total % 10)\n"
                    "        node.next = rec(a.next if a else None, b.next if b else None, total // 10)\n"
                    "        return node\n"
                    "    return rec(l1, l2, 0)"
                ),
                "javascript": (
                    "function addTwoNumbers(l1, l2) {\n"
                    "    const rec = (a, b, carry) => {\n"
                    "        if (!a && !b && !carry) return null;\n"
                    "        const d1 = a ? a.val : 0;\n"
                    "        const d2 = b ? b.val : 0;\n"
                    "        const total = d1 + d2 + carry;\n"
                    "        const node = new ListNode(total % 10);\n"
                    "        node.next = rec(a ? a.next : null, b ? b.next : null, Math.floor(total / 10));\n"
                    "        return node;\n"
                    "    };\n"
                    "    return rec(l1, l2, 0);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Notice the gift: digits are stored *reverse* order. The head of each list is the ones place — exactly where addition starts. No reversing or right-aligning needed.",
        "2. Sketch the by-hand process: stack the numbers, add column by column, carry propagates from one column to the next. Walk both heads in lockstep with one running `carry`.",
        "3. Handle different lengths: when one list is shorter, treat its missing digit as 0. Don't stop when the shorter one ends — the longer one might still have carries flowing through.",
        "4. Don't forget the final carry. 99 + 1 = 100 — two two-digit inputs produce a three-digit result. The classic bug: exiting the loop the moment both lists are exhausted; you need `carry` in the loop guard too.",
        "5. Single unified loop: `while l1 or l2 or carry:`. This collapses three exit conditions into one and removes the 'now mop up the leftover' epilogue.",
        "6. Build the output behind a dummy-head sentinel; advance a `tail` pointer. `return dummy.next`. Removes the 'is the result empty yet?' branch on every append.",
        "7. Edge cases shake out: single-node `ListNode(0) + ListNode(0)` returns a single `ListNode(0)`. `ListNode(5) + ListNode(5)` returns `0 -> 1`. Different lengths: shorter pointer just keeps reading 0.",
    ],
    "tips": [
        "The unified-loop trick (`while l1 or l2 or carry:`) is worth committing to muscle memory — same shape as 'merge two sorted lists with leftovers' and 'add two binary strings'.",
        "Compute the digit *before* updating the carry: `digit = total % 10; carry = total // 10`. Order doesn't matter mathematically here, but stay consistent so you don't accidentally zero out `total` first.",
        "Build behind a `dummy = ListNode()` and advance a `tail` pointer. Same dummy-sentinel trick as Merge Two Sorted Lists. Return `dummy.next`.",
        "Direct follow-up — Add Two Numbers II (LC 445): same problem but digits are stored *most significant first*. Two clean approaches: reverse both inputs (then this exact algorithm), or push onto two stacks and pop in lockstep.",
        "Direct follow-up — Plus One (LC 66): increment a digit array by 1. Same carry-propagation pattern, simplified to one input and one initial carry.",
        "Don't try to cap the loop at `max(len(l1), len(l2))`. The final carry can extend past both — the `or carry` clause is the load-bearing piece.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Bloomberg", "Adobe", "Facebook"],
    "topics": ["Linked List", "Math", "Simulation"],
    "time_complexity": "O(max(m, n))",
    "space_complexity": "O(max(m, n)) for output",
    "entry": {
        "kind": "linked_list",
        "name": "add_two_numbers",
        "params": [
            {"name": "l1", "type": "node"},
            {"name": "l2", "type": "node"},
        ],
        "input_shape": "linked_list_array",
        "output_shape": "linked_list_array",
    },
}


def REFERENCE(l1, l2):
    # Build-time oracle: operates on the array form of the test-case
    # input. The user-visible runtime form (real ListNode chains) is
    # produced by the linked_list driver, which inflates these arrays
    # before invoking the user code and deflates the returned chain.
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
