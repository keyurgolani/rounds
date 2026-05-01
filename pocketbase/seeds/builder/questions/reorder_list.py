"""Reorder List — Medium. Linked list / Two pointers / Reversal.

A three-stage pipeline question: find the middle (slow/fast pointers),
reverse the second half (in-place pointer rewire), then merge the two
halves by alternating. Each stage is a primitive every interviewer
expects you to know cold; the interesting bit is composing them
cleanly without losing pointers between phases. The naive O(n) extra
space version (deque or array indexing) is fine to mention but the
in-place O(1) version is what the question is really probing.

The harness represents the linked list as a flat Python list of node
values in head→tail order. The semantic question — alternate-from-ends
weave — is preserved; the underlying datastructure is incidental.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Reorder List",
    "difficulty": "Medium",
    "description": (
        "Given the head of a singly linked list `L: L0 → L1 → … → Ln-1 → Ln`, reorder it to:\n\n"
        "`L0 → Ln → L1 → Ln-1 → L2 → Ln-2 → …`\n\n"
        "You may not modify the values in the list's nodes — only the nodes themselves may be changed. "
        "Reorder the list **in place**.\n\n"
        "**Example 1:**\n"
        "- Input: `head = [1, 2, 3, 4]`\n"
        "- Output: `[1, 4, 2, 3]`\n\n"
        "**Example 2:**\n"
        "- Input: `head = [1, 2, 3, 4, 5]`\n"
        "- Output: `[1, 5, 2, 4, 3]`\n\n"
        "**Note:** for testing purposes the list is represented as a flat array of node values in "
        "head→tail order. In a real interview you'd be handed `ListNode head` and expected to rewire "
        "the `next` pointers in place — narrate that explicitly even though the harness uses arrays."
    ),
    "hints": [
        "Three stages: (1) find the middle of the list, (2) reverse the second half, (3) merge the two halves by alternating nodes.",
        "Stage 1 — find the middle with slow/fast pointers. When fast reaches the end, slow is at the middle. For odd-length lists slow lands on the exact middle; the second half is one shorter.",
        "Stage 2 — reverse in place using the standard three-pointer dance (`prev`, `curr`, `nxt`). The reversed second half ends with what was originally the tail.",
        "Stage 3 — merge by alternating: take one from the first half, one from the reversed second half, repeat until both are exhausted. Save `next` pointers before rewiring.",
        "Cleanest split: after finding the middle, sever the link between the two halves (`slow.next = None`) so each half is a self-contained list. Avoids edge-case bugs when the halves are unequal lengths.",
    ],
    "constraints": [
        "1 <= n <= 5 * 10⁴",
        "-1000 <= Node.val <= 1000",
    ],
    "starter_code": {
        "python": "def reorder_list(head):\n    # Your code here\n    pass",
        "javascript": "function reorderList(head) {\n    // Your code here\n}",
        "java": "public List<Integer> reorderList(List<Integer> head) {\n    // Your code here\n    return null;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for v in [[1,2,3,4], [1,2,3,4,5], [1], [1,2]]:\n"
            "        print(f\"reorder_list({v}) = {reorder_list(v)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,2,3,4], [1,2,3,4,5], [1], [1,2]].forEach(v =>\n"
            "    console.log(`reorderList(${JSON.stringify(v)}) =`, reorderList(v))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main { public static void main(String[] args) {} }"
        ),
    },
    "test_cases": [
        {"input": {"head": [1, 2, 3, 4]}, "expected": [1, 4, 2, 3],
         "description": "LeetCode example — even-length 4-node list", "tags": ["basic"]},
        {"input": {"head": [1, 2, 3, 4, 5]}, "expected": [1, 5, 2, 4, 3],
         "description": "LeetCode example — odd-length 5-node list", "tags": ["basic"]},
        {"input": {"head": [1]}, "expected": [1],
         "description": "Single node — already reordered", "tags": ["edge"]},
        {"input": {"head": [1, 2]}, "expected": [1, 2],
         "description": "Two-node list — output identical (L0 → L1)", "tags": ["edge"]},
        {"input": {"head": [1, 2, 3]}, "expected": [1, 3, 2],
         "description": "Three-node list — odd length minimum non-trivial", "tags": ["edge"]},
        {"input": {"head": [1, 2, 3, 4, 5, 6]}, "expected": [1, 6, 2, 5, 3, 4],
         "description": "Six-node even — full alternation, both halves equal length", "tags": ["basic"]},
        {"input": {"head": [1, 2, 3, 4, 5, 6, 7]}, "expected": [1, 7, 2, 6, 3, 5, 4],
         "description": "Seven-node odd — middle node lands last", "tags": ["basic"]},
        {"input": {"head": [-5, -4, -3, -2, -1]}, "expected": [-5, -1, -4, -2, -3],
         "description": "All-negative values — sign agnostic", "tags": ["edge"]},
        {"input": {"head": [7, 7, 7, 7]}, "expected": [7, 7, 7, 7],
         "description": "All-equal values — output identical regardless of weave", "tags": ["tricky"]},
        {"input": {"head": [0, 1, 0, 1, 0, 1]}, "expected": [0, 1, 1, 0, 0, 1],
         "description": "Alternating pattern — weave produces non-obvious order", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Find Middle + Reverse Second Half + Merge (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Three-stage pipeline. Stage 1: slow/fast pointers find the middle in one pass. Stage 2: "
                "reverse the second half in place using the three-pointer dance. Stage 3: merge the two "
                "halves by alternating, advancing one pointer from each at every step. Each stage is O(n) "
                "and uses O(1) auxiliary space — three passes total but still O(n) overall. This is the "
                "canonical interview answer; mention it by name."
            ),
            "code": {
                "python": (
                    "def reorder_list(values):\n"
                    "    n = len(values)\n"
                    "    if n <= 2:\n"
                    "        return values[:]\n"
                    "\n"
                    "    # Stage 1: split at the middle (slow/fast in real linked-list terms).\n"
                    "    mid = (n + 1) // 2  # first half gets the extra node when n is odd\n"
                    "    first, second = values[:mid], values[mid:]\n"
                    "\n"
                    "    # Stage 2: reverse the second half in place.\n"
                    "    second.reverse()\n"
                    "\n"
                    "    # Stage 3: merge by alternating one from each.\n"
                    "    result = []\n"
                    "    i = 0\n"
                    "    while i < len(second):\n"
                    "        result.append(first[i])\n"
                    "        result.append(second[i])\n"
                    "        i += 1\n"
                    "    if len(first) > len(second):\n"
                    "        result.append(first[-1])  # odd-length leftover from first half\n"
                    "    return result\n"
                    "\n"
                    "# Real linked-list version (narrate this in the interview):\n"
                    "# def reorder(head):\n"
                    "#     if not head or not head.next: return\n"
                    "#     # 1. find middle\n"
                    "#     slow, fast = head, head\n"
                    "#     while fast.next and fast.next.next:\n"
                    "#         slow, fast = slow.next, fast.next.next\n"
                    "#     # 2. reverse second half\n"
                    "#     prev, curr = None, slow.next\n"
                    "#     slow.next = None  # sever\n"
                    "#     while curr:\n"
                    "#         nxt = curr.next; curr.next = prev; prev = curr; curr = nxt\n"
                    "#     # 3. merge\n"
                    "#     a, b = head, prev\n"
                    "#     while b:\n"
                    "#         a_nxt, b_nxt = a.next, b.next\n"
                    "#         a.next = b; b.next = a_nxt\n"
                    "#         a, b = a_nxt, b_nxt"
                ),
                "javascript": (
                    "function reorderList(values) {\n"
                    "    const n = values.length;\n"
                    "    if (n <= 2) return values.slice();\n"
                    "    const mid = Math.ceil(n / 2);\n"
                    "    const first = values.slice(0, mid);\n"
                    "    const second = values.slice(mid).reverse();\n"
                    "    const result = [];\n"
                    "    for (let i = 0; i < second.length; i++) {\n"
                    "        result.push(first[i]);\n"
                    "        result.push(second[i]);\n"
                    "    }\n"
                    "    if (first.length > second.length) result.push(first[first.length - 1]);\n"
                    "    return result;\n"
                    "}\n"
                    "\n"
                    "// Real linked-list version:\n"
                    "// function reorder(head) {\n"
                    "//     if (!head || !head.next) return;\n"
                    "//     let slow = head, fast = head;\n"
                    "//     while (fast.next && fast.next.next) { slow = slow.next; fast = fast.next.next; }\n"
                    "//     let prev = null, curr = slow.next; slow.next = null;\n"
                    "//     while (curr) { const nxt = curr.next; curr.next = prev; prev = curr; curr = nxt; }\n"
                    "//     let a = head, b = prev;\n"
                    "//     while (b) {\n"
                    "//         const aNxt = a.next, bNxt = b.next;\n"
                    "//         a.next = b; b.next = aNxt;\n"
                    "//         a = aNxt; b = bNxt;\n"
                    "//     }\n"
                    "// }"
                ),
                "java": (
                    "public List<Integer> reorderList(List<Integer> values) {\n"
                    "    int n = values.size();\n"
                    "    List<Integer> result = new ArrayList<>();\n"
                    "    if (n <= 2) { result.addAll(values); return result; }\n"
                    "    int mid = (n + 1) / 2;\n"
                    "    List<Integer> first = new ArrayList<>(values.subList(0, mid));\n"
                    "    List<Integer> second = new ArrayList<>(values.subList(mid, n));\n"
                    "    Collections.reverse(second);\n"
                    "    for (int i = 0; i < second.size(); i++) {\n"
                    "        result.add(first.get(i));\n"
                    "        result.add(second.get(i));\n"
                    "    }\n"
                    "    if (first.size() > second.size()) result.add(first.get(first.size() - 1));\n"
                    "    return result;\n"
                    "}\n"
                    "\n"
                    "// Real linked-list version:\n"
                    "// public void reorderList(ListNode head) {\n"
                    "//     if (head == null || head.next == null) return;\n"
                    "//     ListNode slow = head, fast = head;\n"
                    "//     while (fast.next != null && fast.next.next != null) {\n"
                    "//         slow = slow.next; fast = fast.next.next;\n"
                    "//     }\n"
                    "//     ListNode prev = null, curr = slow.next; slow.next = null;\n"
                    "//     while (curr != null) {\n"
                    "//         ListNode nxt = curr.next; curr.next = prev; prev = curr; curr = nxt;\n"
                    "//     }\n"
                    "//     ListNode a = head, b = prev;\n"
                    "//     while (b != null) {\n"
                    "//         ListNode aNxt = a.next, bNxt = b.next;\n"
                    "//         a.next = b; b.next = aNxt;\n"
                    "//         a = aNxt; b = bNxt;\n"
                    "//     }\n"
                    "// }"
                ),
            },
        },
        {
            "title": "Deque / Two-Pointer Index (Auxiliary Space)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Push every node onto a deque (or just index the array from both ends with two pointers). "
                "Alternate `popleft` and `pop` to weave the result. Trivial to write but spends O(n) extra "
                "memory you don't strictly need. Perfectly fine for arrays; for the actual linked list, "
                "interviewers expect the in-place version so call this out as the warm-up."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "\n"
                    "def reorder_list(values):\n"
                    "    dq = deque(values)\n"
                    "    result = []\n"
                    "    take_left = True\n"
                    "    while dq:\n"
                    "        result.append(dq.popleft() if take_left else dq.pop())\n"
                    "        take_left = not take_left\n"
                    "    return result"
                ),
                "javascript": (
                    "function reorderList(values) {\n"
                    "    const arr = values.slice();\n"
                    "    const result = [];\n"
                    "    let left = 0, right = arr.length - 1, takeLeft = true;\n"
                    "    while (left <= right) {\n"
                    "        if (takeLeft) result.push(arr[left++]);\n"
                    "        else result.push(arr[right--]);\n"
                    "        takeLeft = !takeLeft;\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
                "java": (
                    "public List<Integer> reorderList(List<Integer> values) {\n"
                    "    List<Integer> result = new ArrayList<>();\n"
                    "    int left = 0, right = values.size() - 1;\n"
                    "    boolean takeLeft = true;\n"
                    "    while (left <= right) {\n"
                    "        if (takeLeft) result.add(values.get(left++));\n"
                    "        else result.add(values.get(right--));\n"
                    "        takeLeft = !takeLeft;\n"
                    "    }\n"
                    "    return result;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: 'weave the list by alternating one from the front, one from the back, until both meet in the middle.' Confirm it's in-place — node values stay put, pointers move.",
        "2. Recognise the three primitives: find middle (slow/fast), reverse a list (three-pointer dance), merge two lists by alternation. Each is a standalone interview question — composing them is the trick here.",
        "3. Stage 1 — slow/fast: when fast reaches the end, slow is at the middle. Decide which side gets the extra node when n is odd; convention is 'first half gets it' so the merge runs out cleanly.",
        "4. Stage 2 — reverse second half: standard `prev/curr/nxt` walk. Critical: sever `slow.next = None` *before* reversing so the first half terminates properly — otherwise you'll create a cycle.",
        "5. Stage 3 — merge: keep two pointers `a` and `b` (heads of the two halves). At each step, save `a.next` and `b.next`, then rewire `a.next = b; b.next = a_next`. Advance both. Watch for the unequal-length termination.",
        "6. Edge cases: 1 node (no-op), 2 nodes (no-op — `L0 → L1` is already the answer), 3 nodes (the smallest case where the algorithm actually does work).",
        "7. Walk a 5-node example end-to-end on the whiteboard before submitting. The merge step is where pointer bugs hide; tracing it once catches them.",
    ],
    "tips": [
        "The 'severing' step (`slow.next = None`) is what most candidates forget. Without it, the first half still points into the (now-reversed) second half — you get a corrupted list or a cycle.",
        "When n is odd, the middle node is the *last* element in the output. Make sure your merge logic handles unequal-length halves gracefully (the longer half contributes its trailing node at the end).",
        "Common follow-up — palindrome linked list (LC 234): exact same pipeline (find middle + reverse second half), but instead of merging you compare the two halves node-by-node.",
        "Don't try to do all three stages in a single pass — it tangles into a mess of pointer state. Three clean passes is O(n) total and far easier to reason about.",
        "If the interviewer pushes on space: 'O(1) auxiliary, three passes, in-place via the find-middle / reverse / merge pipeline.' That's the answer they want to hear verbatim.",
        "Don't use recursion for the reverse step here — for n up to 5×10⁴ you'll blow Python's default 1000-frame stack. Iterative all the way.",
    ],
    "companies": ["Amazon", "Microsoft", "Facebook", "Apple", "Bloomberg", "Adobe"],
    "topics": ["Linked List", "Two Pointers", "Stack"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(head):
    n = len(head)
    if n <= 2:
        return head[:]
    mid = (n + 1) // 2
    first = head[:mid]
    second = head[mid:]
    second.reverse()
    result = []
    i = 0
    while i < len(second):
        result.append(first[i])
        result.append(second[i])
        i += 1
    if len(first) > len(second):
        result.append(first[-1])
    return result


register(PAYLOAD, REFERENCE)
