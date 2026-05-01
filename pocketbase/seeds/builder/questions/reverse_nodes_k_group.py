"""Reverse Nodes in k-Group — Hard. Linked List / Recursion / Pointer dance.

The natural follow-up to Reverse Linked List. Instead of reversing
the whole list, you reverse contiguous chunks of size k and leave any
trailing remainder of length < k untouched. The trick is the
bookkeeping: count k forward to confirm the chunk exists, reverse it
in place, then splice the freshly reversed chunk's tail to the head
of whatever comes back from recursing on the rest.

The harness drives the function with a flat array of values (the list
in head→tail order) plus the integer k; the REFERENCE returns the
reordered array. In a real interview you'd be rewiring `ListNode`
pointers, so narrate that explicitly even though the test harness
uses arrays.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Reverse Nodes in k-Group",
    "difficulty": "Hard",
    "description": (
        "Given the `head` of a linked list, reverse the nodes of the list `k` at a time and return the "
        "modified list.\n\n"
        "`k` is a positive integer and is less than or equal to the length of the linked list. If the "
        "number of nodes is not a multiple of `k`, then the **left-out nodes at the end** should remain as "
        "they are.\n\n"
        "You may not alter the values in the list's nodes — only the nodes themselves may be changed.\n\n"
        "**Example 1:**\n"
        "- Input: `head = [1, 2, 3, 4, 5]`, `k = 2`\n"
        "- Output: `[2, 1, 4, 3, 5]`\n"
        "- Explanation: Reverse the first two nodes (1, 2) → (2, 1). Reverse the next two nodes (3, 4) → "
        "(4, 3). The trailing single node (5) has fewer than k=2 nodes left, so it stays put.\n\n"
        "**Example 2:**\n"
        "- Input: `head = [1, 2, 3, 4, 5]`, `k = 3`\n"
        "- Output: `[3, 2, 1, 4, 5]`\n"
        "- Explanation: Reverse the first three nodes (1, 2, 3) → (3, 2, 1). The remaining (4, 5) is "
        "fewer than k=3 nodes, so it stays untouched.\n\n"
        "**Note:** the harness represents the linked list as a flat array of node values in head→tail "
        "order. The semantic question — group-wise reversal with a leftover tail — is preserved; the "
        "underlying pointer rewiring is incidental for the harness but expected of you in interview."
    ),
    "hints": [
        "Before reversing anything, count `k` nodes forward from the current group's start. If you can't reach k (i.e. you hit None first), the rest is the leftover tail — return it as is.",
        "Once you've confirmed a full chunk of k exists, reverse those k nodes using the standard three-pointer dance — but bound the loop by k iterations, not by `curr is None`.",
        "Use a **dummy node** before the head to make splicing trivial: every group's predecessor points to a `prev_group_tail`, which after the reverse becomes `prev_group_tail.next = new_chunk_head`.",
        "After reversing a chunk, the **old head of the chunk** is now the chunk's tail — that's what you re-link to either the next reversed chunk or the leftover tail. Keep a pointer to it before you reverse.",
        "Recursive framing: reverse the first k nodes (or return head unchanged if fewer than k exist), then recursively process the rest and splice. Cleaner code, but pays O(n/k) stack frames.",
    ],
    "constraints": [
        "The number of nodes in the list is in the range [1, 5000].",
        "0 <= Node.val <= 1000",
        "1 <= k <= number of nodes in the list",
    ],
    "starter_code": {
        "python": "def reverse_k_group(head, k):\n    # Your code here\n    pass",
        "javascript": "function reverseKGroup(head, k) {\n    // Your code here\n}",
        "java": "public List<Integer> reverseKGroup(List<Integer> head, int k) {\n    // Your code here\n    return null;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [([1,2,3,4,5], 2), ([1,2,3,4,5], 3), ([1,2,3,4,5], 1), ([1,2,3,4,5], 5)]\n"
            "    for head, k in cases:\n"
            "        print(f\"reverse_k_group({head}, {k}) = {reverse_k_group(head, k)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[[1,2,3,4,5], 2], [[1,2,3,4,5], 3], [[1,2,3,4,5], 1]].forEach(([h, k]) =>\n"
            "    console.log(`reverseKGroup(${JSON.stringify(h)}, ${k}) =`, reverseKGroup(h, k))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(s.reverseKGroup(java.util.Arrays.asList(1,2,3,4,5), 2));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"head": [1, 2, 3, 4, 5], "k": 2}, "expected": [2, 1, 4, 3, 5],
         "description": "Classic LeetCode example — k=2, one leftover node", "tags": ["basic"]},
        {"input": {"head": [1, 2, 3, 4, 5], "k": 3}, "expected": [3, 2, 1, 4, 5],
         "description": "Classic LeetCode example — k=3, two leftover nodes", "tags": ["basic"]},
        {"input": {"head": [1, 2, 3, 4, 5], "k": 1}, "expected": [1, 2, 3, 4, 5],
         "description": "k=1 — every group is a single node, list is unchanged", "tags": ["edge"]},
        {"input": {"head": [1, 2, 3, 4, 5], "k": 5}, "expected": [5, 4, 3, 2, 1],
         "description": "k equals list length — full reverse, no leftover", "tags": ["edge"]},
        {"input": {"head": [1, 2, 3], "k": 5}, "expected": [1, 2, 3],
         "description": "k > list length — no full chunk exists, list untouched", "tags": ["edge"]},
        {"input": {"head": [42], "k": 1}, "expected": [42],
         "description": "Single-node list with k=1 — trivially unchanged", "tags": ["edge"]},
        {"input": {"head": [1, 2, 3, 4, 5, 6, 7, 8], "k": 2}, "expected": [2, 1, 4, 3, 6, 5, 8, 7],
         "description": "Even-length list, k=2 — pure pairwise swap, no leftover", "tags": ["tricky"]},
        {"input": {"head": [1, 2, 3, 4, 5, 6, 7, 8], "k": 3}, "expected": [3, 2, 1, 6, 5, 4, 7, 8],
         "description": "k=3 with leftover — two full chunks reversed, two trailing nodes preserved",
         "tags": ["tricky"]},
        {"input": {"head": [1, 2, 3, 4, 5, 6], "k": 3}, "expected": [3, 2, 1, 6, 5, 4],
         "description": "Length is exact multiple of k — every node is reversed", "tags": ["tricky"]},
        {"input": {"head": list(range(1, 21)), "k": 4},
         "expected": [4, 3, 2, 1, 8, 7, 6, 5, 12, 11, 10, 9, 16, 15, 14, 13, 20, 19, 18, 17],
         "description": "20 nodes, k=4 — five clean chunks, no leftover", "tags": ["large"]},
        {"input": {"head": list(range(1, 11)), "k": 3},
         "expected": [3, 2, 1, 6, 5, 4, 9, 8, 7, 10],
         "description": "10 nodes, k=3 — three chunks of three plus one leftover", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Iterative with Dummy Node (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Anchor the list to a dummy node so the very first chunk has a uniform 'previous tail' to "
                "splice into. Loop: peek k nodes ahead — if you can't reach k, you're at the leftover, "
                "stop. Otherwise reverse exactly k nodes using the three-pointer dance bounded by k, then "
                "splice: the dummy's `next` (old chunk head, now the chunk's tail) becomes the new prev "
                "tail; its `next` points at whatever comes after the reversed chunk. O(n) time because "
                "every node is touched a constant number of times; O(1) extra space — only a few pointers."
            ),
            "code": {
                "python": (
                    "def reverse_k_group(head, k):\n"
                    "    # Array-based narration of the in-place pointer algorithm.\n"
                    "    n = len(head)\n"
                    "    result = []\n"
                    "    i = 0\n"
                    "    while i + k <= n:\n"
                    "        # Reverse the chunk [i, i+k) and append.\n"
                    "        for j in range(i + k - 1, i - 1, -1):\n"
                    "            result.append(head[j])\n"
                    "        i += k\n"
                    "    # Leftover tail — append in original order.\n"
                    "    while i < n:\n"
                    "        result.append(head[i])\n"
                    "        i += 1\n"
                    "    return result\n"
                    "\n"
                    "# Real linked-list version (narrate this in the interview):\n"
                    "# def reverse_k_group(head, k):\n"
                    "#     dummy = ListNode(0, head)\n"
                    "#     group_prev = dummy\n"
                    "#     while True:\n"
                    "#         kth = group_prev\n"
                    "#         for _ in range(k):\n"
                    "#             kth = kth.next\n"
                    "#             if kth is None:\n"
                    "#                 return dummy.next  # leftover tail; leave as is\n"
                    "#         group_next = kth.next\n"
                    "#         # Reverse the chunk between group_prev.next and kth (inclusive).\n"
                    "#         prev, curr = group_next, group_prev.next\n"
                    "#         while curr is not group_next:\n"
                    "#             nxt = curr.next\n"
                    "#             curr.next = prev\n"
                    "#             prev = curr\n"
                    "#             curr = nxt\n"
                    "#         tmp = group_prev.next  # old head, now this chunk's tail\n"
                    "#         group_prev.next = kth  # splice: prev group → new chunk head\n"
                    "#         group_prev = tmp        # advance to this chunk's tail\n"
                    "#     return dummy.next"
                ),
                "javascript": (
                    "function reverseKGroup(head, k) {\n"
                    "    const n = head.length;\n"
                    "    const result = [];\n"
                    "    let i = 0;\n"
                    "    while (i + k <= n) {\n"
                    "        for (let j = i + k - 1; j >= i; j--) result.push(head[j]);\n"
                    "        i += k;\n"
                    "    }\n"
                    "    while (i < n) result.push(head[i++]);\n"
                    "    return result;\n"
                    "}\n"
                    "\n"
                    "// Real linked-list version:\n"
                    "// function reverseKGroup(head, k) {\n"
                    "//     const dummy = { next: head };\n"
                    "//     let groupPrev = dummy;\n"
                    "//     while (true) {\n"
                    "//         let kth = groupPrev;\n"
                    "//         for (let i = 0; i < k && kth; i++) kth = kth.next;\n"
                    "//         if (!kth) return dummy.next;\n"
                    "//         const groupNext = kth.next;\n"
                    "//         let prev = groupNext, curr = groupPrev.next;\n"
                    "//         while (curr !== groupNext) {\n"
                    "//             const nxt = curr.next;\n"
                    "//             curr.next = prev;\n"
                    "//             prev = curr;\n"
                    "//             curr = nxt;\n"
                    "//         }\n"
                    "//         const tmp = groupPrev.next;\n"
                    "//         groupPrev.next = kth;\n"
                    "//         groupPrev = tmp;\n"
                    "//     }\n"
                    "// }"
                ),
                "java": (
                    "public List<Integer> reverseKGroup(List<Integer> head, int k) {\n"
                    "    int n = head.size();\n"
                    "    List<Integer> result = new ArrayList<>();\n"
                    "    int i = 0;\n"
                    "    while (i + k <= n) {\n"
                    "        for (int j = i + k - 1; j >= i; j--) result.add(head.get(j));\n"
                    "        i += k;\n"
                    "    }\n"
                    "    while (i < n) result.add(head.get(i++));\n"
                    "    return result;\n"
                    "}\n"
                    "\n"
                    "// Real linked-list version:\n"
                    "// public ListNode reverseKGroup(ListNode head, int k) {\n"
                    "//     ListNode dummy = new ListNode(0, head);\n"
                    "//     ListNode groupPrev = dummy;\n"
                    "//     while (true) {\n"
                    "//         ListNode kth = groupPrev;\n"
                    "//         for (int i = 0; i < k && kth != null; i++) kth = kth.next;\n"
                    "//         if (kth == null) return dummy.next;\n"
                    "//         ListNode groupNext = kth.next;\n"
                    "//         ListNode prev = groupNext, curr = groupPrev.next;\n"
                    "//         while (curr != groupNext) {\n"
                    "//             ListNode nxt = curr.next;\n"
                    "//             curr.next = prev;\n"
                    "//             prev = curr;\n"
                    "//             curr = nxt;\n"
                    "//         }\n"
                    "//         ListNode tmp = groupPrev.next;\n"
                    "//         groupPrev.next = kth;\n"
                    "//         groupPrev = tmp;\n"
                    "//     }\n"
                    "// }"
                ),
            },
        },
        {
            "title": "Recursive",
            "time_complexity": "O(n)",
            "space_complexity": "O(n / k)",
            "description": (
                "Reverse the first k nodes — but first, walk forward to confirm k nodes exist; if not, "
                "return the head unchanged (leftover tail). Once confirmed, reverse those k nodes (bounded "
                "loop), recursively process the remainder, and splice the original head's `next` (now the "
                "chunk's tail) onto the recursive result. Stack depth is `n / k` — fine for n ≤ 5000 and "
                "moderate k, but worth flagging the trade-off versus iterative."
            ),
            "code": {
                "python": (
                    "def reverse_k_group(head, k):\n"
                    "    # Array-based narration of the recursive in-place algorithm.\n"
                    "    if len(head) < k:\n"
                    "        return head[:]\n"
                    "    return head[k - 1::-1][:k] + reverse_k_group(head[k:], k)\n"
                    "\n"
                    "# Real linked-list version:\n"
                    "# def reverse_k_group(head, k):\n"
                    "#     # Walk k forward to verify a full chunk exists.\n"
                    "#     curr = head\n"
                    "#     for _ in range(k):\n"
                    "#         if curr is None:\n"
                    "#             return head  # leftover, leave intact\n"
                    "#         curr = curr.next\n"
                    "#     # Reverse exactly k nodes.\n"
                    "#     prev, curr = None, head\n"
                    "#     for _ in range(k):\n"
                    "#         nxt = curr.next\n"
                    "#         curr.next = prev\n"
                    "#         prev = curr\n"
                    "#         curr = nxt\n"
                    "#     # `head` is now the tail of the reversed chunk; splice.\n"
                    "#     head.next = reverse_k_group(curr, k)\n"
                    "#     return prev"
                ),
                "javascript": (
                    "function reverseKGroup(head, k) {\n"
                    "    if (head.length < k) return head.slice();\n"
                    "    const chunk = head.slice(0, k).reverse();\n"
                    "    return chunk.concat(reverseKGroup(head.slice(k), k));\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: 'reverse contiguous groups of k nodes; leave any trailing remainder of length < k untouched.' Confirm with the interviewer that the leftover stays in original order — it's the most-asked clarification.",
        "2. Decompose: there are two primitives — (a) check whether k nodes exist ahead, (b) reverse exactly k nodes. Get both right in isolation, then compose.",
        "3. Counting forward: walk a temp pointer k steps. If it falls off the end before reaching k, the rest is leftover — splice as-is.",
        "4. Bounded reverse: the standard three-pointer dance, but the loop runs exactly k times instead of 'until None'. After the loop, `prev` is the new chunk head, the *old* head is the chunk's tail.",
        "5. Splicing: a dummy node before the original head makes this uniform — every chunk has a `group_prev` pointing at it. After reversing, `group_prev.next = new_chunk_head`, `group_prev = old_chunk_head`.",
        "6. Edge cases: k=1 (every chunk is a single node, list unchanged); k = list length (single full reverse); k > list length (no chunks reverse, leftover is the whole list); single node (any k ≥ 2 → unchanged).",
        "7. Walk a 5-node example with k=2 end-to-end: (1,2) reverses to (2,1), (3,4) reverses to (4,3), (5) is leftover → [2,1,4,3,5]. Mention the same list with k=3 → [3,2,1,4,5] to show the leftover behaviour.",
        "8. Complexity: every node is touched O(1) times across the count-forward pass and the reverse pass, so O(n) total time. Iterative version is O(1) space; recursive is O(n/k) stack. State both.",
    ],
    "tips": [
        "Always count forward *first*. If you start reversing optimistically and run out of nodes mid-chunk, you've corrupted the list and now have to un-reverse — which is messy and a real interview failure mode.",
        "Use a dummy/sentinel node. It eliminates the special case for the very first chunk (no 'previous' to splice into) and shrinks the code by half a dozen lines.",
        "After reversing a chunk in place, the *original head* of the chunk becomes its tail — keep a pointer to it before reversing, because that's what you splice into the next group.",
        "Bound the reverse loop by k, not by `curr is None`. Forgetting this is the classic bug — you'll happily reverse past the end of the chunk and clobber the rest of the list.",
        "Common follow-ups — Reverse Linked List II (LC 92, 'reverse between m and n') is the same primitive without grouping; Swap Pairs (LC 24) is exactly this problem hard-coded with k=2 and admits a cleaner recursive form.",
    ],
    "companies": ["Microsoft", "Amazon", "Facebook", "Google", "Bloomberg"],
    "topics": ["Linked List", "Recursion"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(head, k):
    n = len(head)
    result = []
    i = 0
    while i + k <= n:
        for j in range(i + k - 1, i - 1, -1):
            result.append(head[j])
        i += k
    while i < n:
        result.append(head[i])
        i += 1
    return result


register(PAYLOAD, REFERENCE)
