"""Linked List Cycle — Easy. Two-Pointer / Hash Set.

The canonical Floyd's tortoise-and-hare question. The trick is the
elegant O(1)-space proof: if there's a cycle, a fast pointer moving
two steps will eventually lap a slow pointer moving one step *inside*
the cycle. If there's no cycle, fast falls off the end. Worth knowing
the hash-set version too because (a) it's the obvious first thought
and (b) it generalises naturally to LC 142 ('return the node where
the cycle begins') even though Floyd's also handles that with extra
care.

Driver note: real linked lists with cycles can't survive a JSON
round-trip, so the test harness passes `(nodes, pos)` — a flat array
of values plus the index the tail loops back to (-1 for no cycle).
The REFERENCE simply checks `pos != -1`; the candidate's job is to
narrate Floyd's against an actual `head` pointer. Description spells
this out so the candidate isn't confused by the calling convention.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Linked List Cycle",
    "difficulty": "Easy",
    "description": (
        "Given the `head` of a linked list, determine if the linked list contains a cycle.\n\n"
        "There is a cycle in a linked list if there is some node in the list that can be reached again "
        "by continuously following the `next` pointer. Return `True` if there is a cycle in the linked "
        "list. Otherwise, return `False`.\n\n"
        "**Example 1:**\n"
        "- Input: `head = [3, 2, 0, -4]`, `pos = 1`\n"
        "- Output: `True`\n"
        "- Explanation: There is a cycle in the linked list, where the tail connects to the 1st node "
        "(0-indexed).\n\n"
        "**Example 2:**\n"
        "- Input: `head = [1, 2]`, `pos = 0`\n"
        "- Output: `True`\n"
        "- Explanation: There is a cycle, where the tail connects to the 0th node.\n\n"
        "**Example 3:**\n"
        "- Input: `head = [1]`, `pos = -1`\n"
        "- Output: `False`\n"
        "- Explanation: No cycle.\n\n"
        "**Note:** real linked lists with cycles can't be encoded as JSON, so the test harness passes "
        "`(nodes, pos)` — a flat array of values and the index the tail's `next` should point to "
        "(-1 means no cycle). In a real interview you'd be handed `ListNode head` directly and would "
        "narrate Floyd's tortoise-and-hare on the actual node pointers."
    ),
    "hints": [
        "Hash set: walk the list, store every node reference (not value — references) in a set. If you ever revisit a node, there's a cycle. O(n) time, O(n) space.",
        "Floyd's tortoise-and-hare: two pointers, slow moves one step, fast moves two. If there's a cycle, fast eventually meets slow *inside* it. If no cycle, fast hits None. O(n) time, O(1) space — the optimal answer.",
        "Why does Floyd's terminate inside a cycle? Once both pointers are inside, fast gains one position on slow per step. The gap closes monotonically modulo cycle length, so they meet within `cycle_length` steps.",
        "Edge cases: empty list → no cycle; single node with `next = None` → no cycle; single node pointing to itself → cycle. The Floyd's loop handles all of these without special casing if you check `fast and fast.next` before stepping.",
        "Don't store *values* in the hash set — duplicates would trigger false positives. Store node identity (the reference itself) so two distinct nodes with the same value remain distinct.",
    ],
    "constraints": [
        "0 <= n <= 10⁴, where n is the number of nodes",
        "-10⁵ <= Node.val <= 10⁵",
        "`pos` is -1 or a valid index into the list (0 <= pos < n)",
    ],
    "starter_code": {
        "python": "def has_cycle(head):\n    # Your code here. `head` is a ListNode (or None).\n    # In the harness, the test runner constructs the linked list\n    # from (nodes, pos) and hands you the resulting head pointer.\n    pass",
        "javascript": "function hasCycle(head) {\n    // Your code here. `head` is a ListNode (or null).\n}",
        "java": "public boolean hasCycle(ListNode head) {\n    // Your code here.\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only). Builds a linked list with optional cycle\n"
            "# from (nodes, pos), then calls has_cycle(head).\n"
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
            "    return built[0]\n"
            "\n"
            "if __name__ == \"__main__\":\n"
            "    for nodes, pos in [([3, 2, 0, -4], 1), ([1, 2], 0), ([1], -1), ([], -1)]:\n"
            "        print(f\"has_cycle({nodes}, pos={pos}) = {has_cycle(_build(nodes, pos))}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "class ListNode { constructor(val, next = null) { this.val = val; this.next = next; } }\n"
            "function _build(nodes, pos) {\n"
            "    if (!nodes.length) return null;\n"
            "    const built = nodes.map(v => new ListNode(v));\n"
            "    for (let i = 0; i < built.length - 1; i++) built[i].next = built[i + 1];\n"
            "    if (pos !== -1) built[built.length - 1].next = built[pos];\n"
            "    return built[0];\n"
            "}\n"
            "[[[3,2,0,-4],1], [[1,2],0], [[1],-1], [[],-1]].forEach(([nodes, pos]) =>\n"
            "    console.log(`hasCycle(${JSON.stringify(nodes)}, pos=${pos}) =`, hasCycle(_build(nodes, pos)))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main { public static void main(String[] args) {} }"
        ),
    },
    "test_cases": [
        {"input": {"nodes": [], "pos": -1}, "expected": False,
         "description": "Empty list — no cycle", "tags": ["edge"]},
        {"input": {"nodes": [1], "pos": -1}, "expected": False,
         "description": "Single node, no cycle", "tags": ["edge"]},
        {"input": {"nodes": [1], "pos": 0}, "expected": True,
         "description": "Single node looping to itself — cycle of length 1", "tags": ["edge"]},
        {"input": {"nodes": [1, 2], "pos": -1}, "expected": False,
         "description": "Two nodes, no cycle", "tags": ["basic"]},
        {"input": {"nodes": [1, 2], "pos": 0}, "expected": True,
         "description": "Two nodes, tail loops to head — cycle of length 2", "tags": ["basic"]},
        {"input": {"nodes": [3, 2, 0, -4], "pos": 1}, "expected": True,
         "description": "LeetCode example — tail connects to index 1", "tags": ["basic"]},
        {"input": {"nodes": [1, 2, 3, 4, 5], "pos": -1}, "expected": False,
         "description": "Five-node list, no cycle — fast pointer falls off end", "tags": ["basic"]},
        {"input": {"nodes": [1, 2, 3, 4, 5], "pos": 0}, "expected": True,
         "description": "Cycle at the head — entire list is the loop", "tags": ["tricky"]},
        {"input": {"nodes": [1, 2, 3, 4, 5, 6, 7], "pos": 3}, "expected": True,
         "description": "Cycle in the middle — tail loops to index 3", "tags": ["tricky"]},
        {"input": {"nodes": [1, 2, 3, 4, 5, 6, 7], "pos": 6}, "expected": True,
         "description": "Self-loop at the tail — cycle of length 1 at end", "tags": ["tricky"]},
        {"input": {"nodes": list(range(1000)), "pos": -1}, "expected": False,
         "description": "1K nodes, no cycle — stress the linear walk", "tags": ["large"]},
        {"input": {"nodes": list(range(1000)), "pos": 500}, "expected": True,
         "description": "1K nodes with cycle — fast pointer must lap slow inside the loop", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Floyd's Tortoise and Hare (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Two pointers: `slow` advances one step, `fast` advances two. If `fast` (or `fast.next`) "
                "becomes None, there's no cycle. Otherwise, the gap between `fast` and `slow` closes by "
                "one each iteration *modulo* cycle length, so they collide within `cycle_length` steps "
                "of both being inside the cycle. O(n) time, O(1) space — the answer interviewers want."
            ),
            "code": {
                "python": (
                    "def has_cycle(head):\n"
                    "    slow = fast = head\n"
                    "    while fast and fast.next:\n"
                    "        slow = slow.next\n"
                    "        fast = fast.next.next\n"
                    "        if slow is fast:\n"
                    "            return True\n"
                    "    return False"
                ),
                "javascript": (
                    "function hasCycle(head) {\n"
                    "    let slow = head, fast = head;\n"
                    "    while (fast && fast.next) {\n"
                    "        slow = slow.next;\n"
                    "        fast = fast.next.next;\n"
                    "        if (slow === fast) return true;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
                "java": (
                    "public boolean hasCycle(ListNode head) {\n"
                    "    ListNode slow = head, fast = head;\n"
                    "    while (fast != null && fast.next != null) {\n"
                    "        slow = slow.next;\n"
                    "        fast = fast.next.next;\n"
                    "        if (slow == fast) return true;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Hash Set (Identity-Based)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk the list, storing every node reference (not value!) in a set. If you ever revisit "
                "a node, there's a cycle. If you fall off the end, there isn't. Trivial to write but "
                "wastes O(n) memory you don't need — mention as the obvious first thought, then upgrade "
                "to Floyd's for the O(1)-space win."
            ),
            "code": {
                "python": (
                    "def has_cycle(head):\n"
                    "    seen = set()\n"
                    "    curr = head\n"
                    "    while curr:\n"
                    "        if id(curr) in seen:\n"
                    "            return True\n"
                    "        seen.add(id(curr))\n"
                    "        curr = curr.next\n"
                    "    return False"
                ),
                "javascript": (
                    "function hasCycle(head) {\n"
                    "    const seen = new Set();\n"
                    "    let curr = head;\n"
                    "    while (curr) {\n"
                    "        if (seen.has(curr)) return true;\n"
                    "        seen.add(curr);\n"
                    "        curr = curr.next;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
                "java": (
                    "public boolean hasCycle(ListNode head) {\n"
                    "    Set<ListNode> seen = new HashSet<>();\n"
                    "    ListNode curr = head;\n"
                    "    while (curr != null) {\n"
                    "        if (!seen.add(curr)) return true;\n"
                    "        curr = curr.next;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: 'does following `.next` from head ever revisit a node, or does it terminate at None?' Confirm singly-linked.",
        "2. Obvious first thought — hash set: track every node reference; revisiting one means cycle. O(n) time and space. State it as the baseline.",
        "3. Optimization — Floyd's: two pointers at different speeds. If there's a cycle, they must meet inside it; if not, the fast one falls off the end. O(n) time, O(1) space.",
        "4. Prove termination: once both pointers are inside the cycle, fast gains one position on slow each iteration. The gap is bounded by cycle length, so they meet within `cycle_length` iterations.",
        "5. Termination check: `while fast and fast.next` — both must exist before stepping fast forward by two, otherwise you'll dereference None.",
        "6. Edge cases: empty (loop never runs, return False), single node no-next (same), single node self-loop (slow = fast = head, then both step and meet — returns True). All fall out naturally.",
        "7. Mention the follow-up — LC 142 'Linked List Cycle II' — find the *start* of the cycle. Same Floyd's setup, then reset one pointer to head and walk both at speed 1; they meet at the cycle entry.",
    ],
    "tips": [
        "Identity, not equality: when using a hash set, store node references (or `id(node)` in Python). Two distinct nodes can share a value — using values would trigger false positives.",
        "The `while fast and fast.next` guard is load-bearing: if you only check `fast`, you'll deref None on `fast.next.next` when fast is at the last node. Get this exactly right.",
        "Common follow-up — LC 142 'Linked List Cycle II': find the node where the cycle begins. After Floyd's meet, reset one pointer to head; walk both at speed 1; they collide at the cycle entry. Comes from a clean math argument on cycle distances.",
        "Common follow-up — 'find cycle length': once slow and fast meet, freeze one and walk the other until it returns. The number of steps is the cycle length.",
        "Don't modify the list (e.g., setting visited flags on nodes). It mutates input, breaks if values are read-only, and Floyd's gives you O(1) space without it.",
        "If asked 'why 1 and 2 — would 1 and 3 work?': yes, any (a, b) with a < b works for *detection*; the gap-closing argument generalises. (1, 2) is just the cleanest. For finding the cycle start (LC 142), the math relies specifically on the 1:2 ratio.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Bloomberg", "Yahoo"],
    "topics": ["Linked List", "Two Pointers", "Hash Table"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(nodes, pos):
    # The harness passes (nodes, pos); a cycle exists iff the tail
    # is wired to a valid index. Empty lists trivially have no cycle.
    if not nodes:
        return False
    return pos != -1


register(PAYLOAD, REFERENCE)
