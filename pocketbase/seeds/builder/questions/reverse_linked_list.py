"""Reverse Linked List — Easy. Pointer manipulation / Recursion.

The canonical pointer-rewiring question. Iterative version is three
lines of pointer dance that every interviewer expects you to write
flawlessly; recursive version is the elegant counterpart that costs
O(n) stack. Worth knowing both because the follow-ups (reverse in
groups of k, reverse between m and n) compose directly on top.

The linked list is represented here as a plain Python list (the values
in head→tail order). The semantic question — order reversal — is
preserved; the underlying datastructure is incidental for the
algorithmic narration."""
from builder.registry import register


PAYLOAD = {
    "title": "Reverse Linked List",
    "difficulty": "Easy",
    "description": (
        "Given the `head` of a singly linked list, reverse the list and return the reversed list.\n\n"
        "**Example 1:**\n"
        "- Input: `head = [1, 2, 3, 4, 5]`\n"
        "- Output: `[5, 4, 3, 2, 1]`\n\n"
        "**Example 2:**\n"
        "- Input: `head = [1, 2]`\n"
        "- Output: `[2, 1]`\n\n"
        "**Example 3:**\n"
        "- Input: `head = []`\n"
        "- Output: `[]`\n\n"
        "**Note:** for testing purposes the list is represented as a flat array of node values in "
        "head→tail order. In a real interview you'd be handed `ListNode head` and expected to rewire "
        "the `next` pointers in place — narrate that explicitly even though the harness uses arrays."
    ),
    "hints": [
        "Iterative: walk once with three pointers — `prev`, `curr`, `next`. At each step, save `curr.next`, point `curr.next` at `prev`, advance `prev` and `curr`. O(n) time, O(1) space.",
        "Recursive: recurse to the tail, then on the way back up flip `head.next.next = head; head.next = None`. O(n) time, O(n) stack.",
        "Edge cases: empty list (return None / empty), single node (return as-is). Both fall out of the iterative loop without special casing.",
        "Don't lose the reference to `curr.next` *before* you overwrite it — that's the classic bug. Save it first.",
        "Think of `prev` as 'the new head so far'. When the walk ends, `prev` is the new head of the reversed list.",
    ],
    "constraints": [
        "0 <= n <= 5000",
        "-5000 <= Node.val <= 5000",
    ],
    "starter_code": {
        "python": "def reverse_linked_list(values):\n    # Your code here\n    pass",
        "javascript": "function reverseLinkedList(values) {\n    // Your code here\n}",
        "java": "public List<Integer> reverseLinkedList(List<Integer> values) {\n    // Your code here\n    return null;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for v in [[1,2,3,4,5], [1,2], [], [42]]:\n"
            "        print(f\"reverse_linked_list({v}) = {reverse_linked_list(v)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,2,3,4,5], [1,2], [], [42]].forEach(v =>\n"
            "    console.log(`reverseLinkedList(${JSON.stringify(v)}) =`, reverseLinkedList(v))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main { public static void main(String[] args) {} }"
        ),
    },
    "test_cases": [
        {"input": {"values": [1, 2, 3, 4, 5]}, "expected": [5, 4, 3, 2, 1],
         "description": "LeetCode example — five-node list", "tags": ["basic"]},
        {"input": {"values": [1, 2]}, "expected": [2, 1],
         "description": "Two-node list — swap", "tags": ["basic"]},
        {"input": {"values": []}, "expected": [],
         "description": "Empty list — return empty", "tags": ["edge"]},
        {"input": {"values": [42]}, "expected": [42],
         "description": "Single node — reversed list is identical", "tags": ["edge"]},
        {"input": {"values": [-1, 0, 1]}, "expected": [1, 0, -1],
         "description": "Negative, zero, positive — sign agnostic", "tags": ["edge"]},
        {"input": {"values": [7, 7, 7, 7]}, "expected": [7, 7, 7, 7],
         "description": "All-equal values — order reversal still applies (output identical)", "tags": ["tricky"]},
        {"input": {"values": list(range(100))}, "expected": list(range(99, -1, -1)),
         "description": "100 ascending → 100 descending", "tags": ["large"]},
        {"input": {"values": list(range(5000))}, "expected": list(range(4999, -1, -1)),
         "description": "5K nodes — upper constraint bound", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Iterative Three-Pointer (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk once with `prev`, `curr`, `next`. At each step: stash `curr.next` into `next`, "
                "point `curr.next` at `prev`, advance `prev = curr` and `curr = next`. When `curr` "
                "is None the walk is done; `prev` is the new head. The harness uses arrays, so the "
                "code below builds a reversed list — but in a real interview you'd be rewiring "
                "`ListNode` pointers in place, which is the actual O(1)-space win."
            ),
            "code": {
                "python": (
                    "def reverse_linked_list(values):\n"
                    "    # Pointer-style narration on an array: prev grows from the tail backwards.\n"
                    "    result = []\n"
                    "    for v in values:\n"
                    "        result.insert(0, v)  # in real linked-list code this is the O(1) prev rewire\n"
                    "    return result\n"
                    "\n"
                    "# Real linked-list version (narrate this in the interview):\n"
                    "# def reverse(head):\n"
                    "#     prev, curr = None, head\n"
                    "#     while curr:\n"
                    "#         nxt = curr.next\n"
                    "#         curr.next = prev\n"
                    "#         prev = curr\n"
                    "#         curr = nxt\n"
                    "#     return prev"
                ),
                "javascript": (
                    "function reverseLinkedList(values) {\n"
                    "    const result = [];\n"
                    "    for (const v of values) result.unshift(v);\n"
                    "    return result;\n"
                    "}\n"
                    "\n"
                    "// Real linked-list version:\n"
                    "// function reverse(head) {\n"
                    "//     let prev = null, curr = head;\n"
                    "//     while (curr) {\n"
                    "//         const nxt = curr.next;\n"
                    "//         curr.next = prev;\n"
                    "//         prev = curr;\n"
                    "//         curr = nxt;\n"
                    "//     }\n"
                    "//     return prev;\n"
                    "// }"
                ),
                "java": (
                    "public List<Integer> reverseLinkedList(List<Integer> values) {\n"
                    "    List<Integer> result = new ArrayList<>();\n"
                    "    for (int i = values.size() - 1; i >= 0; i--) {\n"
                    "        result.add(values.get(i));\n"
                    "    }\n"
                    "    return result;\n"
                    "}\n"
                    "\n"
                    "// Real linked-list version:\n"
                    "// public ListNode reverseList(ListNode head) {\n"
                    "//     ListNode prev = null, curr = head;\n"
                    "//     while (curr != null) {\n"
                    "//         ListNode nxt = curr.next;\n"
                    "//         curr.next = prev;\n"
                    "//         prev = curr;\n"
                    "//         curr = nxt;\n"
                    "//     }\n"
                    "//     return prev;\n"
                    "// }"
                ),
            },
        },
        {
            "title": "Recursive",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Recurse to the tail. The base case returns the last node — which becomes the new head. "
                "On the way back up, flip the pointer: `head.next.next = head; head.next = None`. Elegant "
                "but costs O(n) stack frames, so for n up to 5000 you risk a stack overflow on some "
                "platforms — call it out as the trade-off."
            ),
            "code": {
                "python": (
                    "def reverse_linked_list(values):\n"
                    "    def rec(i):\n"
                    "        if i >= len(values):\n"
                    "            return []\n"
                    "        return rec(i + 1) + [values[i]]\n"
                    "    return rec(0)\n"
                    "\n"
                    "# Real linked-list version:\n"
                    "# def reverse(head):\n"
                    "#     if head is None or head.next is None:\n"
                    "#         return head\n"
                    "#     new_head = reverse(head.next)\n"
                    "#     head.next.next = head\n"
                    "#     head.next = None\n"
                    "#     return new_head"
                ),
                "javascript": (
                    "function reverseLinkedList(values) {\n"
                    "    const rec = (i) => i >= values.length ? [] : [...rec(i + 1), values[i]];\n"
                    "    return rec(0);\n"
                    "}"
                ),
            },
        },
        {
            "title": "Stack (Auxiliary Space)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Push every value onto a stack, then pop them off into the result. Trivial to write but "
                "wastes O(n) memory you don't need. Mention only as a baseline — the iterative pointer "
                "version dominates it on every axis except 'first thing that comes to mind'."
            ),
            "code": {
                "python": (
                    "def reverse_linked_list(values):\n"
                    "    stack = []\n"
                    "    for v in values:\n"
                    "        stack.append(v)\n"
                    "    result = []\n"
                    "    while stack:\n"
                    "        result.append(stack.pop())\n"
                    "    return result"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: 'rewire pointers so the head becomes the tail.' Clarify it's a singly-linked list (no prev pointers — that's why the three-pointer dance is needed).",
        "2. Sketch the invariant: at each step, everything to the left of `curr` has been reversed; `prev` is the new head of that reversed prefix.",
        "3. Walk through the pointer dance on paper: `nxt = curr.next; curr.next = prev; prev = curr; curr = nxt`. Get the order right — saving `nxt` *first* is the load-bearing line.",
        "4. State the recursive alternative for completeness: recurse to the tail, flip on the way back. Call out the O(n) stack cost as the trade-off.",
        "5. Edge cases: empty list (loop never runs, `prev` stays None — correct), single node (loop runs once, `prev` becomes that node — correct). No special-casing needed.",
        "6. Walk a 3-node example end-to-end (1→2→3 becomes 3→2→1) to prove the code works before submitting.",
        "7. Mention follow-ups proactively: 'reverse in groups of k' (LC 25) and 'reverse between positions m and n' (LC 92) — both compose on top of this primitive.",
    ],
    "tips": [
        "Recursion-stack tradeoff: recursive solution is O(n) stack. For very long lists (Python's default recursion limit is 1000), iterative is the safe choice — say so explicitly.",
        "Common follow-up — Reverse Nodes in k-Group (LC 25): reverse the first k nodes, recurse on the rest, splice. Iterative version uses the same three-pointer pattern bounded by k.",
        "Common follow-up — Reverse Linked List II (LC 92): reverse only between positions m and n. Walk to position m-1, do the standard reverse for n-m+1 steps, then re-splice the head and tail of the reversed segment.",
        "Don't build a new list with values copied — interviewers want pointer rewiring on the actual nodes. The harness uses arrays, but narrate the in-place version.",
        "The classic bug: writing `curr.next = prev` *before* saving `curr.next` into `nxt`. You lose the rest of the list. Always stash `nxt` first.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Bloomberg", "Facebook"],
    "topics": ["Linked List", "Recursion"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(values):
    result = []
    for v in values:
        result.insert(0, v)
    return result


register(PAYLOAD, REFERENCE)
