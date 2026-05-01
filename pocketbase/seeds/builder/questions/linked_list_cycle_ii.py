"""Linked List Cycle II — Medium. Two-Pointer / Hash Set.

The follow-up to LC 141 'Linked List Cycle'. Instead of a yes/no on
whether a cycle exists, return the *node where the cycle begins*.
Floyd's tortoise-and-hare still applies — there's a beautiful little
algebraic argument: after slow and fast meet inside the cycle, reset
one pointer to head and walk both at speed 1; they collide exactly
at the cycle entry. The proof drops out of `2·slow_dist = fast_dist`
(mod cycle length).

Driver note: same as LC 141 — JSON can't encode a cyclic structure,
so the harness passes `(nodes, pos)` and rebuilds the list. The
REFERENCE returns the *index* of the cycle start (which is just
`pos`), or -1 for no cycle. The candidate's job is to return the
actual node pointer; the harness compares by index.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Linked List Cycle II",
    "difficulty": "Medium",
    "description": (
        "Given the `head` of a linked list, return *the node where the cycle begins*. If there is no "
        "cycle, return `null`.\n\n"
        "There is a cycle in a linked list if there is some node in the list that can be reached again "
        "by continuously following the `next` pointer. Internally, `pos` is used to denote the index of "
        "the node that the tail's `next` pointer is connected to (0-indexed). Note that `pos = -1` means "
        "there is no cycle. **`pos` is not passed as a parameter** — it's only described to clarify the "
        "shape of the input.\n\n"
        "Do not modify the linked list.\n\n"
        "**Example 1:**\n"
        "- Input: `head = [3, 2, 0, -4]`, `pos = 1`\n"
        "- Output: returns the node at index 1 (value 2)\n"
        "- Explanation: There is a cycle in the linked list, where the tail connects to the 1st node.\n\n"
        "**Example 2:**\n"
        "- Input: `head = [1, 2]`, `pos = 0`\n"
        "- Output: returns the node at index 0 (value 1)\n"
        "- Explanation: There is a cycle, where the tail connects to the 0th node.\n\n"
        "**Example 3:**\n"
        "- Input: `head = [1]`, `pos = -1`\n"
        "- Output: `null`\n"
        "- Explanation: No cycle.\n\n"
        "**Note:** real linked lists with cycles can't be encoded as JSON, so the test harness passes "
        "`(nodes, pos)` — a flat array of values and the index the tail's `next` should point to "
        "(-1 means no cycle). The harness builds the list, calls your function with the resulting "
        "`head`, and compares by index — return the node itself (or `None`/`null` for no cycle), and "
        "the harness will check it against `pos`."
    ),
    "hints": [
        "Hash set baseline: walk the list, store every node *reference* in a set. The first node you revisit is the cycle start. O(n) time, O(n) space — easy to reason about, expensive on memory.",
        "Floyd's, phase 1: tortoise-and-hare to detect a cycle. Slow moves one step, fast moves two. If fast hits None there's no cycle — return null. Otherwise, they meet inside the loop.",
        "Floyd's, phase 2: reset one pointer (say `slow`) to `head`. Now move both `slow` and `fast` one step at a time. They will collide *exactly at the cycle entry*. That node is your answer.",
        "Why does phase 2 work? Let `L` = distance from head to cycle start, `C` = cycle length, `k` = distance from cycle start to the meeting point. When they meet, slow has walked `L + k` and fast has walked `2(L + k) = L + k + n·C` for some n ≥ 1. So `L + k = n·C`, i.e. `L = n·C − k`. Walking `L` more from the meeting point lands on the cycle entry, and walking `L` from `head` also lands there — so they meet at the entry.",
        "Edge cases that fall out naturally: empty list → return null (loop never enters). Single node, no cycle → null. Single node self-loop → phase 1 meets immediately at that node, phase 2 trivially returns it. Cycle starting at head → `L = 0`, both pointers already at head when phase 2 starts.",
    ],
    "constraints": [
        "0 <= n <= 10⁴, where n is the number of nodes",
        "-10⁵ <= Node.val <= 10⁵",
        "`pos` is -1 or a valid index into the list (0 <= pos < n)",
    ],
    "starter_code": {
        "python": "def detect_cycle(head):\n    # Your code here. `head` is a ListNode (or None).\n    # Return the node where the cycle begins, or None if no cycle.\n    pass",
        "javascript": "function detectCycle(head) {\n    // Your code here. `head` is a ListNode (or null).\n    // Return the node where the cycle begins, or null if no cycle.\n}",
        "java": "public ListNode detectCycle(ListNode head) {\n    // Your code here.\n    return null;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only). Builds a linked list with optional cycle\n"
            "# from (nodes, pos), then calls detect_cycle(head). The harness\n"
            "# compares the returned node to the expected index by walking from head.\n"
            "class ListNode:\n"
            "    def __init__(self, val=0, nxt=None):\n"
            "        self.val = val\n"
            "        self.next = nxt\n"
            "\n"
            "def _build(nodes, pos):\n"
            "    if not nodes:\n"
            "        return None\n"
            "    built = [ListNode(v) for v in nodes]\n"
            "    for i in range(len(built) - 1):\n"
            "        built[i].next = built[i + 1]\n"
            "    if pos != -1:\n"
            "        built[-1].next = built[pos]\n"
            "    return built[0], built\n"
            "\n"
            "def _index_of(node, built):\n"
            "    if node is None:\n"
            "        return -1\n"
            "    for i, n in enumerate(built):\n"
            "        if n is node:\n"
            "            return i\n"
            "    return -2  # not in the list — bug in solution\n"
            "\n"
            "if __name__ == \"__main__\":\n"
            "    for nodes, pos in [([3, 2, 0, -4], 1), ([1, 2], 0), ([1], -1), ([], -1)]:\n"
            "        if not nodes:\n"
            "            print(f\"detect_cycle({nodes}, pos={pos}) = -1\")\n"
            "            continue\n"
            "        head, built = _build(nodes, pos)\n"
            "        result = detect_cycle(head)\n"
            "        print(f\"detect_cycle({nodes}, pos={pos}) = {_index_of(result, built)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "class ListNode { constructor(val, next = null) { this.val = val; this.next = next; } }\n"
            "function _build(nodes, pos) {\n"
            "    if (!nodes.length) return [null, []];\n"
            "    const built = nodes.map(v => new ListNode(v));\n"
            "    for (let i = 0; i < built.length - 1; i++) built[i].next = built[i + 1];\n"
            "    if (pos !== -1) built[built.length - 1].next = built[pos];\n"
            "    return [built[0], built];\n"
            "}\n"
            "function _indexOf(node, built) {\n"
            "    if (node === null || node === undefined) return -1;\n"
            "    for (let i = 0; i < built.length; i++) if (built[i] === node) return i;\n"
            "    return -2;\n"
            "}\n"
            "[[[3,2,0,-4],1], [[1,2],0], [[1],-1], [[],-1]].forEach(([nodes, pos]) => {\n"
            "    const [head, built] = _build(nodes, pos);\n"
            "    const r = detectCycle(head);\n"
            "    console.log(`detectCycle(${JSON.stringify(nodes)}, pos=${pos}) =`, _indexOf(r, built));\n"
            "});"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main { public static void main(String[] args) {} }"
        ),
    },
    "test_cases": [
        {"input": {"nodes": [], "pos": -1}, "expected": -1,
         "description": "Empty list — no cycle", "tags": ["edge"]},
        {"input": {"nodes": [1], "pos": -1}, "expected": -1,
         "description": "Single node, no cycle — return null", "tags": ["edge"]},
        {"input": {"nodes": [1], "pos": 0}, "expected": 0,
         "description": "Single node looping to itself — entry is the node itself", "tags": ["edge"]},
        {"input": {"nodes": [1, 2], "pos": 0}, "expected": 0,
         "description": "Two nodes, tail loops to head — entry at index 0", "tags": ["basic"]},
        {"input": {"nodes": [1, 2], "pos": -1}, "expected": -1,
         "description": "Two nodes, no cycle", "tags": ["basic"]},
        {"input": {"nodes": [3, 2, 0, -4], "pos": 1}, "expected": 1,
         "description": "LeetCode example — cycle entry at index 1", "tags": ["basic"]},
        {"input": {"nodes": [1, 2, 3, 4, 5], "pos": -1}, "expected": -1,
         "description": "Five-node list, no cycle", "tags": ["basic"]},
        {"input": {"nodes": [1, 2, 3, 4, 5], "pos": 0}, "expected": 0,
         "description": "Cycle covers entire list — entry is head (L = 0 case)", "tags": ["tricky"]},
        {"input": {"nodes": [1, 2, 3, 4, 5, 6, 7], "pos": 3}, "expected": 3,
         "description": "Cycle entry in the middle — phase 2 must walk forward L=3 steps", "tags": ["tricky"]},
        {"input": {"nodes": [1, 2, 3, 4, 5, 6, 7], "pos": 6}, "expected": 6,
         "description": "Tail loops to itself — cycle of length 1 at the last node", "tags": ["tricky"]},
        {"input": {"nodes": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "pos": 7}, "expected": 7,
         "description": "Long tail before short cycle — entry deep in the list", "tags": ["tricky"]},
        {"input": {"nodes": list(range(1000)), "pos": -1}, "expected": -1,
         "description": "1K nodes, no cycle — stress the linear walk", "tags": ["large"]},
        {"input": {"nodes": list(range(1000)), "pos": 500}, "expected": 500,
         "description": "1K nodes with cycle — phase 2 walks 500 steps to the entry", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Floyd's Two-Pointer (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Two phases. Phase 1 (detection): standard tortoise-and-hare — slow steps once, fast "
                "twice. If fast hits None, return null. Otherwise they meet inside the cycle. Phase 2 "
                "(localisation): reset slow to head; walk slow and fast one step at a time. When they "
                "collide, they're at the cycle entry. The math: at meeting time slow has walked `L + k`, "
                "fast has walked `2(L + k) = L + k + n·C`, so `L = n·C − k`. Walking `L` more from the "
                "meeting point lands on the entry, and walking `L` from head also lands there."
            ),
            "code": {
                "python": (
                    "def detect_cycle(head):\n"
                    "    slow = fast = head\n"
                    "    # Phase 1: detect a cycle.\n"
                    "    while fast and fast.next:\n"
                    "        slow = slow.next\n"
                    "        fast = fast.next.next\n"
                    "        if slow is fast:\n"
                    "            break\n"
                    "    else:\n"
                    "        return None\n"
                    "    if fast is None or fast.next is None:\n"
                    "        return None\n"
                    "    # Phase 2: locate the entry.\n"
                    "    slow = head\n"
                    "    while slow is not fast:\n"
                    "        slow = slow.next\n"
                    "        fast = fast.next\n"
                    "    return slow"
                ),
                "javascript": (
                    "function detectCycle(head) {\n"
                    "    let slow = head, fast = head;\n"
                    "    // Phase 1: detect.\n"
                    "    while (fast && fast.next) {\n"
                    "        slow = slow.next;\n"
                    "        fast = fast.next.next;\n"
                    "        if (slow === fast) break;\n"
                    "    }\n"
                    "    if (!fast || !fast.next || slow !== fast) return null;\n"
                    "    // Phase 2: locate.\n"
                    "    slow = head;\n"
                    "    while (slow !== fast) {\n"
                    "        slow = slow.next;\n"
                    "        fast = fast.next;\n"
                    "    }\n"
                    "    return slow;\n"
                    "}"
                ),
                "java": (
                    "public ListNode detectCycle(ListNode head) {\n"
                    "    ListNode slow = head, fast = head;\n"
                    "    // Phase 1: detect.\n"
                    "    while (fast != null && fast.next != null) {\n"
                    "        slow = slow.next;\n"
                    "        fast = fast.next.next;\n"
                    "        if (slow == fast) break;\n"
                    "    }\n"
                    "    if (fast == null || fast.next == null || slow != fast) return null;\n"
                    "    // Phase 2: locate.\n"
                    "    slow = head;\n"
                    "    while (slow != fast) {\n"
                    "        slow = slow.next;\n"
                    "        fast = fast.next;\n"
                    "    }\n"
                    "    return slow;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Hash Set (Identity-Based)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk the list, storing every node reference in a hash set. The first node you encounter "
                "that's already in the set *is* the cycle entry — by definition, it's the first node "
                "reachable both from before the cycle and from inside the cycle. Trivial to write but "
                "uses O(n) memory you don't need. Mention as the obvious first thought, then upgrade to "
                "Floyd's for the O(1)-space win."
            ),
            "code": {
                "python": (
                    "def detect_cycle(head):\n"
                    "    seen = set()\n"
                    "    curr = head\n"
                    "    while curr:\n"
                    "        if id(curr) in seen:\n"
                    "            return curr\n"
                    "        seen.add(id(curr))\n"
                    "        curr = curr.next\n"
                    "    return None"
                ),
                "javascript": (
                    "function detectCycle(head) {\n"
                    "    const seen = new Set();\n"
                    "    let curr = head;\n"
                    "    while (curr) {\n"
                    "        if (seen.has(curr)) return curr;\n"
                    "        seen.add(curr);\n"
                    "        curr = curr.next;\n"
                    "    }\n"
                    "    return null;\n"
                    "}"
                ),
                "java": (
                    "public ListNode detectCycle(ListNode head) {\n"
                    "    Set<ListNode> seen = new HashSet<>();\n"
                    "    ListNode curr = head;\n"
                    "    while (curr != null) {\n"
                    "        if (!seen.add(curr)) return curr;\n"
                    "        curr = curr.next;\n"
                    "    }\n"
                    "    return null;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: not just 'is there a cycle?' but 'where does it start?'. The entry is the first node reachable from both the linear prefix and the cycle.",
        "2. Obvious first thought — hash set: walk the list storing node references; the first revisit *is* the entry. O(n) time and space. State it as the baseline.",
        "3. Optimization — Floyd's two-phase: phase 1 detects (same as LC 141), phase 2 localises (reset one pointer to head, walk both at speed 1, collision is the entry). O(n) time, O(1) space.",
        "4. Prove phase 2: let L = head→entry, C = cycle length, k = entry→meeting-point. Slow walked L + k; fast walked 2(L + k) = L + k + n·C. So L + k = n·C, i.e. L ≡ −k (mod C). Walking L steps from the meeting point therefore lands on the entry; walking L from head lands there too — they collide at the entry.",
        "5. Termination check for phase 1: `while fast and fast.next` — both must exist before stepping fast forward by two. If either is None, no cycle.",
        "6. Edge cases: empty (return null), single no-next (null), single self-loop (slow=fast=head, immediate meet, phase 2 trivially returns head), cycle-from-head (L=0, slow already at fast when phase 2 starts → return head). All natural.",
        "7. State the trade-off: hash set is two lines of obvious code at O(n) space; Floyd's is the same time complexity at O(1) space but requires the algebraic argument. Production code: usually Floyd's; whiteboard: lead with hash set, then upgrade.",
    ],
    "tips": [
        "Identity, not equality: when using a hash set, store node references (or `id(node)` in Python). Two distinct nodes can share a value — using values would trigger false positives and return the wrong node.",
        "The two phases are independent — write them as two separate `while` loops, not one combined loop. Conflating them is the #1 source of bugs on this problem.",
        "After phase 1, double-check that `slow is fast` before entering phase 2 — otherwise you exited because `fast` or `fast.next` was None, and there's no cycle to localise.",
        "The 1:2 speed ratio is load-bearing for phase 2. Other ratios (e.g. 1:3) detect a cycle but don't give you the entry from this exact reset-and-walk trick. Worth saying out loud if asked 'why two and not three?'.",
        "Cycle-starts-at-head edge case (L = 0): when phase 2 begins, `slow = head` and `fast` is already at the meeting point. The condition `while slow is not fast` may exit immediately if and only if the meeting point happens to be head — which it does when L = 0. Trace through it once to convince yourself.",
        "Common follow-up — cycle length: once slow and fast meet in phase 1, freeze one and walk the other until it returns. Step count = cycle length. Different question; same Floyd's setup.",
        "Don't modify the list (e.g., setting visited flags on nodes). It mutates input, breaks if values are read-only, and Floyd's gives you O(1) auxiliary space without it.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Bloomberg", "Facebook", "Google"],
    "topics": ["Linked List", "Two Pointers", "Hash Table"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nodes, pos):
    # The harness passes (nodes, pos); the cycle entry's index is
    # exactly `pos` when a cycle exists, and -1 when it doesn't.
    # Empty lists trivially have no cycle.
    if not nodes:
        return -1
    return pos


register(PAYLOAD, REFERENCE)
