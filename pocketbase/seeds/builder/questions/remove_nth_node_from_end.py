"""Remove Nth Node From End of List — Medium. Two-Pointer / Linked List.

The canonical 'one-pass two-pointer' linked-list question. The trick
is to space the two pointers exactly n+1 apart so when the leader
falls off the end, the follower lands on the node *before* the one to
remove. A dummy head saves you from special-casing 'remove the head'
— that's the load-bearing detail interviewers watch for.

The harness represents the linked list as a flat array of values in
head→tail order. The algorithmic narration is unchanged; you'd narrate
pointer manipulation in a real interview even though the test runner
operates on lists."""
from builder.registry import register


PAYLOAD = {
    "title": "Remove Nth Node From End of List",
    "difficulty": "Medium",
    "description": (
        "Given the `head` of a linked list, remove the **n-th node from the end** of the list and "
        "return its head.\n\n"
        "**Example 1:**\n"
        "- Input: `head = [1, 2, 3, 4, 5], n = 2`\n"
        "- Output: `[1, 2, 3, 5]`\n"
        "- Explanation: The 2nd node from the end is `4`; remove it.\n\n"
        "**Example 2:**\n"
        "- Input: `head = [1], n = 1`\n"
        "- Output: `[]`\n"
        "- Explanation: The only node is also the 1st from the end; the list becomes empty.\n\n"
        "**Note:** for testing, the list is represented as a flat array of node values in head→tail "
        "order. In a real interview you'd be handed `ListNode head` and expected to rewire `next` "
        "pointers in place — narrate the pointer dance even though the harness uses arrays."
    ),
    "hints": [
        "Naive two-pass: walk once to compute length L, then walk again to position L-n and skip it. O(n) time, O(1) space — easy to get right but two passes.",
        "One-pass two-pointer: advance a `fast` pointer n steps ahead of `slow`. Then walk both together until `fast` reaches the end; `slow` now sits on the node *before* the one to remove.",
        "Use a **dummy node** pointing to head. This collapses the 'remove the head' edge case into the same code path — `slow` starts at the dummy, never null.",
        "Spacing matters: with a dummy and `fast` advanced n steps, walk both until `fast.next` is null. That leaves `slow` exactly one node before the target.",
        "Edge cases: n equals the length (remove head), single-node list with n=1 (return empty), n=1 (remove tail). The dummy-node version handles all three with the same code.",
    ],
    "constraints": [
        "The number of nodes in the list is `sz`.",
        "1 <= sz <= 30",
        "0 <= Node.val <= 100",
        "1 <= n <= sz",
    ],
    "starter_code": {
        "python": "def remove_nth_from_end(values, n):\n    # Your code here\n    pass",
        "javascript": "function removeNthFromEnd(values, n) {\n    // Your code here\n}",
        "java": "public List<Integer> removeNthFromEnd(List<Integer> values, int n) {\n    // Your code here\n    return null;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([1,2,3,4,5], 2), ([1], 1), ([1,2], 1), ([1,2], 2)]\n"
            "    for values, n in cases:\n"
            "        print(f\"remove_nth_from_end({values}, {n}) = {remove_nth_from_end(values, n)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,2,3,4,5], 2], [[1], 1], [[1,2], 1], [[1,2], 2]].forEach(([v, n]) =>\n"
            "    console.log(`removeNthFromEnd(${JSON.stringify(v)}, ${n}) =`, removeNthFromEnd(v, n))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main { public static void main(String[] args) {} }"
        ),
    },
    "test_cases": [
        {"input": {"head": [1, 2, 3, 4, 5], "n": 2}, "expected": [1, 2, 3, 5],
         "description": "LeetCode example — remove 2nd from end (the 4)", "tags": ["basic"]},
        {"input": {"head": [1], "n": 1}, "expected": [],
         "description": "Single-node list, n=1 — list becomes empty", "tags": ["edge"]},
        {"input": {"head": [1, 2], "n": 1}, "expected": [1],
         "description": "Two nodes, remove tail", "tags": ["edge"]},
        {"input": {"head": [1, 2], "n": 2}, "expected": [2],
         "description": "Two nodes, remove head — dummy-node case", "tags": ["edge"]},
        {"input": {"head": [1, 2, 3, 4, 5], "n": 1}, "expected": [1, 2, 3, 4],
         "description": "Remove the last node (n=1)", "tags": ["basic"]},
        {"input": {"head": [1, 2, 3, 4, 5], "n": 5}, "expected": [2, 3, 4, 5],
         "description": "n equals length — remove the head", "tags": ["tricky"]},
        {"input": {"head": [1, 2, 3, 4, 5], "n": 3}, "expected": [1, 2, 4, 5],
         "description": "Remove the middle node", "tags": ["basic"]},
        {"input": {"head": [10, 20, 30], "n": 2}, "expected": [10, 30],
         "description": "Three nodes — remove middle", "tags": ["basic"]},
        {"input": {"head": [7, 7, 7, 7, 7], "n": 3}, "expected": [7, 7, 7, 7],
         "description": "Duplicate values — position-based removal still well-defined", "tags": ["tricky"]},
        {"input": {"head": list(range(30)), "n": 30}, "expected": list(range(1, 30)),
         "description": "30 nodes (upper bound), remove head", "tags": ["large"]},
        {"input": {"head": list(range(30)), "n": 1}, "expected": list(range(29)),
         "description": "30 nodes, remove tail", "tags": ["large"]},
        {"input": {"head": list(range(30)), "n": 15}, "expected": list(range(15)) + list(range(16, 30)),
         "description": "30 nodes, remove a middle node (index 15 from front)", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "One-Pass Two-Pointer (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Use a dummy node pointing to head. Advance `fast` n steps from the dummy, then walk "
                "`slow` and `fast` together until `fast.next` is null. Now `slow` sits exactly on the "
                "node *before* the target — splice it out via `slow.next = slow.next.next`. Return "
                "`dummy.next` so the head-removal case falls out naturally. One pass, two scalars."
            ),
            "code": {
                "python": (
                    "def remove_nth_from_end(values, n):\n"
                    "    # Array-narration of the two-pointer dance.\n"
                    "    # In a real linked list you'd splice slow.next; here we drop index L-n.\n"
                    "    L = len(values)\n"
                    "    target = L - n  # 0-based index to drop\n"
                    "    return values[:target] + values[target + 1:]\n"
                    "\n"
                    "# Real linked-list version (narrate this in the interview):\n"
                    "# def remove_nth(head, n):\n"
                    "#     dummy = ListNode(0, head)\n"
                    "#     fast = slow = dummy\n"
                    "#     for _ in range(n):\n"
                    "#         fast = fast.next\n"
                    "#     while fast.next:\n"
                    "#         fast = fast.next\n"
                    "#         slow = slow.next\n"
                    "#     slow.next = slow.next.next\n"
                    "#     return dummy.next"
                ),
                "javascript": (
                    "function removeNthFromEnd(values, n) {\n"
                    "    const L = values.length;\n"
                    "    const target = L - n;\n"
                    "    return [...values.slice(0, target), ...values.slice(target + 1)];\n"
                    "}\n"
                    "\n"
                    "// Real linked-list version:\n"
                    "// function removeNth(head, n) {\n"
                    "//     const dummy = { val: 0, next: head };\n"
                    "//     let fast = dummy, slow = dummy;\n"
                    "//     for (let i = 0; i < n; i++) fast = fast.next;\n"
                    "//     while (fast.next) { fast = fast.next; slow = slow.next; }\n"
                    "//     slow.next = slow.next.next;\n"
                    "//     return dummy.next;\n"
                    "// }"
                ),
                "java": (
                    "public List<Integer> removeNthFromEnd(List<Integer> values, int n) {\n"
                    "    int L = values.size();\n"
                    "    int target = L - n;\n"
                    "    List<Integer> result = new ArrayList<>(values);\n"
                    "    result.remove(target);\n"
                    "    return result;\n"
                    "}\n"
                    "\n"
                    "// Real linked-list version:\n"
                    "// public ListNode removeNthFromEnd(ListNode head, int n) {\n"
                    "//     ListNode dummy = new ListNode(0, head);\n"
                    "//     ListNode fast = dummy, slow = dummy;\n"
                    "//     for (int i = 0; i < n; i++) fast = fast.next;\n"
                    "//     while (fast.next != null) { fast = fast.next; slow = slow.next; }\n"
                    "//     slow.next = slow.next.next;\n"
                    "//     return dummy.next;\n"
                    "// }"
                ),
            },
        },
        {
            "title": "Two-Pass Length-Then-Remove",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "First pass computes the length L. Second pass walks L-n-1 steps from a dummy node "
                "to land on the node *before* the target, then splices it out. Same asymptotics as "
                "the one-pass approach but two traversals — easier to reason about under pressure, "
                "and a fine answer if you mention the one-pass optimisation as a follow-up."
            ),
            "code": {
                "python": (
                    "def remove_nth_from_end(values, n):\n"
                    "    L = len(values)\n"
                    "    target = L - n\n"
                    "    result = []\n"
                    "    for i, v in enumerate(values):\n"
                    "        if i != target:\n"
                    "            result.append(v)\n"
                    "    return result\n"
                    "\n"
                    "# Real linked-list version:\n"
                    "# def remove_nth(head, n):\n"
                    "#     L = 0\n"
                    "#     curr = head\n"
                    "#     while curr:\n"
                    "#         L += 1\n"
                    "#         curr = curr.next\n"
                    "#     dummy = ListNode(0, head)\n"
                    "#     curr = dummy\n"
                    "#     for _ in range(L - n):\n"
                    "#         curr = curr.next\n"
                    "#     curr.next = curr.next.next\n"
                    "#     return dummy.next"
                ),
                "javascript": (
                    "function removeNthFromEnd(values, n) {\n"
                    "    const L = values.length;\n"
                    "    const target = L - n;\n"
                    "    return values.filter((_, i) => i !== target);\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: 'remove the node whose distance from the tail is n.' Confirm 1-indexed (n=1 means the tail).",
        "2. Naive: two passes — walk once for length L, walk again to L-n and skip. State it as the baseline.",
        "3. Reframe to one-pass: if I keep two pointers exactly n apart and walk them together, when the leader hits the end the follower is exactly n from the end.",
        "4. Off-by-one watch: I want `slow` to land on the node *before* the target so I can splice. The right setup is fast advanced n steps, then walk both until `fast.next` is null.",
        "5. Edge case — removing the head: if I start `slow` at `head`, removing the head requires special-casing. Add a **dummy** node pointing to head and start `slow` there. Now the splice works uniformly and I return `dummy.next`.",
        "6. Edge case — single-node list with n=1: dummy→[1]; fast advances 1 step to the only node; the while loop's condition `fast.next != null` is false immediately; slow is still the dummy; `dummy.next = dummy.next.next = null`. Returns empty. Correct.",
        "7. Walk a 5-node, n=2 example end-to-end on paper to prove the spacing before submitting.",
    ],
    "tips": [
        "The dummy node is the load-bearing trick. Without it you have to special-case 'remove head' — interviewers notice when candidates write that branch instead of just adding a dummy.",
        "Spacing pitfall: advancing `fast` by n+1 instead of n leaves `slow` *on* the target, not before it. Walk a 3-node, n=1 example mentally to lock in the right number.",
        "Don't allocate a new list/array — interviewers want pointer rewiring on the actual nodes. The harness uses arrays, but narrate the in-place splice.",
        "Two-pass version is fine if you're shaky on the spacing — write the cleaner version, then mention the one-pass as the optimisation. Honesty about your confidence beats a buggy 'optimal' attempt.",
        "Common follow-up — what if `n` could exceed the length? Validate first: count nodes, return head unchanged (or raise) if `n > L`. The two-pointer version doesn't notice; you'd dereference past the tail.",
        "Common follow-up — doubly linked list: trivial in O(n) walk-from-tail. The two-pointer trick is specifically for *singly* linked lists where you can't walk backwards.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Facebook", "Bloomberg", "Apple"],
    "topics": ["Linked List", "Two Pointers"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
    "driver_kind": "linked_list",
    "solution_function": "remove_nth_from_end",
}


def REFERENCE(head, n):
    L = len(head)
    target = L - n
    return head[:target] + head[target + 1:]


register(PAYLOAD, REFERENCE)
