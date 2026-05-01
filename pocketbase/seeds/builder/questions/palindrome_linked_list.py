"""Palindrome Linked List — Easy. Two-pointer / Reverse half / Recursion.

The classic 'O(1) space on a linked list' problem. The naive solution
(copy values into an array and two-pointer compare) is fine to mention
but the expected answer is: walk to the middle with slow/fast, reverse
the second half in place, walk the two halves in lockstep comparing
values. That's the trick the question is built around — recognizing
that the absence of prev pointers forces you to either pay O(n) memory
or rewire pointers.

The harness represents the list as a flat array of node values in
head→tail order. The semantic question — palindrome by value sequence
— is preserved; the underlying data structure is incidental for the
algorithmic narration."""
from builder.registry import register


PAYLOAD = {
    "title": "Palindrome Linked List",
    "difficulty": "Easy",
    "description": (
        "Given the `head` of a singly linked list, return `True` if it is a palindrome — i.e. the "
        "sequence of node values reads the same forward and backward — and `False` otherwise.\n\n"
        "**Example 1:**\n"
        "- Input: `head = [1, 2, 2, 1]`\n"
        "- Output: `True`\n"
        "- Explanation: Forward and reversed sequences are both `[1, 2, 2, 1]`.\n\n"
        "**Example 2:**\n"
        "- Input: `head = [1, 2]`\n"
        "- Output: `False`\n"
        "- Explanation: Reversed it would be `[2, 1]` — not the same as `[1, 2]`.\n\n"
        "**Note:** for testing purposes the list is represented as a flat array of node values in "
        "head→tail order. In a real interview you'd be handed `ListNode head` and the follow-up is "
        "always 'can you do it in O(1) extra space?' — narrate the find-middle-and-reverse-second-half "
        "approach explicitly even though the harness uses arrays."
    ),
    "hints": [
        "Easy O(n)/O(n) version: copy every value into an array, then check `arr == arr[::-1]` (or two-pointer compare from both ends). This is the warm-up — interviewers expect better.",
        "Optimal O(n)/O(1): walk to the middle with slow/fast pointers, reverse the second half in place, then walk the first half and the reversed second half in lockstep comparing values.",
        "Stack approach O(n)/O(n): push the first half onto a stack while finding the middle, then pop and compare with the second half as you walk.",
        "Recursive O(n)/O(n) trick: a recursive function carries a shared 'front' pointer that advances forward as the recursion unwinds backward — comparing front with the recursive return at each frame.",
        "Edge cases that fall out of the math: empty list (vacuously palindrome — True), single node (palindrome — True), two equal nodes (True), two different nodes (False).",
    ],
    "constraints": [
        "0 <= n <= 100000",
        "-10^9 <= Node.val <= 10^9",
        "Follow-up: can you solve it in O(n) time and O(1) extra space?",
    ],
    "starter_code": {
        "python": "def is_palindrome(head):\n    # Your code here\n    pass",
        "javascript": "function isPalindrome(head) {\n    // Your code here\n}",
        "java": "public boolean isPalindrome(List<Integer> head) {\n    // Your code here\n    return false;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    for v in [[1,2,2,1], [1,2,3], [1], [], [1,2,3,2,1]]:\n"
            "        print(f\"is_palindrome({v}) = {is_palindrome(v)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[1,2,2,1], [1,2,3], [1], [], [1,2,3,2,1]].forEach(v =>\n"
            "    console.log(`isPalindrome(${JSON.stringify(v)}) =`, isPalindrome(v))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main { public static void main(String[] args) {} }"
        ),
    },
    "test_cases": [
        {"input": {"head": [1, 2, 2, 1]}, "expected": True,
         "description": "Classic even-length palindrome", "tags": ["basic"]},
        {"input": {"head": [1, 2, 3]}, "expected": False,
         "description": "Three-node non-palindrome", "tags": ["basic"]},
        {"input": {"head": [1]}, "expected": True,
         "description": "Single node — vacuously a palindrome", "tags": ["edge"]},
        {"input": {"head": []}, "expected": True,
         "description": "Empty list — vacuously a palindrome", "tags": ["edge"]},
        {"input": {"head": [7, 7]}, "expected": True,
         "description": "Two equal nodes — palindrome", "tags": ["edge"]},
        {"input": {"head": [1, 2]}, "expected": False,
         "description": "Two different nodes — not a palindrome", "tags": ["edge"]},
        {"input": {"head": [1, 2, 3, 2, 1]}, "expected": True,
         "description": "Odd-length palindrome — middle node ignored in compare", "tags": ["basic"]},
        {"input": {"head": [1, 2, 3, 4, 3, 2, 1]}, "expected": True,
         "description": "Longer odd-length palindrome", "tags": ["basic"]},
        {"input": {"head": [1, 2, 3, 4, 5, 6, 7]}, "expected": False,
         "description": "Longer non-palindrome (strictly ascending)", "tags": ["basic"]},
        {"input": {"head": [-1, 0, 1, 0, -1]}, "expected": True,
         "description": "Negatives and zero — palindrome with mixed signs", "tags": ["tricky"]},
        {"input": {"head": [1, 2, 2, 2, 1]}, "expected": True,
         "description": "Repeated middle values — still a palindrome", "tags": ["tricky"]},
        {"input": {"head": list(range(500)) + list(range(499, -1, -1))}, "expected": True,
         "description": "1000-node palindrome — stress on slow/fast walk", "tags": ["large"]},
        {"input": {"head": list(range(1000))}, "expected": False,
         "description": "1000 ascending — not a palindrome", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Find Middle + Reverse Second Half (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk to the middle with slow/fast (fast moves twice as fast — when fast hits the end, "
                "slow is at the midpoint). Reverse the second half in place using the standard "
                "three-pointer pattern. Then walk the first half and the reversed second half in "
                "lockstep comparing values; if any pair differs, return False. This is the canonical "
                "O(n)/O(1) answer the interviewer is fishing for. The harness uses arrays so the code "
                "below mirrors the *logic* (compare head to tail moving inward) — but narrate the "
                "pointer-rewiring version explicitly."
            ),
            "code": {
                "python": (
                    "def is_palindrome(head):\n"
                    "    # Array mirror of the linked-list two-pointer compare.\n"
                    "    # The real linked-list version: slow/fast to find mid, reverse second half,\n"
                    "    # walk both halves in lockstep. Same number of comparisons, O(1) extra space.\n"
                    "    i, j = 0, len(head) - 1\n"
                    "    while i < j:\n"
                    "        if head[i] != head[j]:\n"
                    "            return False\n"
                    "        i += 1\n"
                    "        j -= 1\n"
                    "    return True\n"
                    "\n"
                    "# Real linked-list version (narrate this in the interview):\n"
                    "# def is_palindrome(head):\n"
                    "#     # 1. Find middle with slow/fast.\n"
                    "#     slow = fast = head\n"
                    "#     while fast and fast.next:\n"
                    "#         slow = slow.next\n"
                    "#         fast = fast.next.next\n"
                    "#     # 2. Reverse second half starting at slow.\n"
                    "#     prev = None\n"
                    "#     while slow:\n"
                    "#         nxt = slow.next\n"
                    "#         slow.next = prev\n"
                    "#         prev = slow\n"
                    "#         slow = nxt\n"
                    "#     # 3. Walk both halves in lockstep.\n"
                    "#     left, right = head, prev\n"
                    "#     while right:\n"
                    "#         if left.val != right.val:\n"
                    "#             return False\n"
                    "#         left, right = left.next, right.next\n"
                    "#     return True"
                ),
                "javascript": (
                    "function isPalindrome(head) {\n"
                    "    let i = 0, j = head.length - 1;\n"
                    "    while (i < j) {\n"
                    "        if (head[i] !== head[j]) return false;\n"
                    "        i++; j--;\n"
                    "    }\n"
                    "    return true;\n"
                    "}\n"
                    "\n"
                    "// Real linked-list version:\n"
                    "// function isPalindrome(head) {\n"
                    "//     let slow = head, fast = head;\n"
                    "//     while (fast && fast.next) { slow = slow.next; fast = fast.next.next; }\n"
                    "//     let prev = null;\n"
                    "//     while (slow) {\n"
                    "//         const nxt = slow.next;\n"
                    "//         slow.next = prev;\n"
                    "//         prev = slow;\n"
                    "//         slow = nxt;\n"
                    "//     }\n"
                    "//     let left = head, right = prev;\n"
                    "//     while (right) {\n"
                    "//         if (left.val !== right.val) return false;\n"
                    "//         left = left.next; right = right.next;\n"
                    "//     }\n"
                    "//     return true;\n"
                    "// }"
                ),
                "java": (
                    "public boolean isPalindrome(List<Integer> head) {\n"
                    "    int i = 0, j = head.size() - 1;\n"
                    "    while (i < j) {\n"
                    "        if (!head.get(i).equals(head.get(j))) return false;\n"
                    "        i++; j--;\n"
                    "    }\n"
                    "    return true;\n"
                    "}\n"
                    "\n"
                    "// Real linked-list version:\n"
                    "// public boolean isPalindrome(ListNode head) {\n"
                    "//     ListNode slow = head, fast = head;\n"
                    "//     while (fast != null && fast.next != null) { slow = slow.next; fast = fast.next.next; }\n"
                    "//     ListNode prev = null;\n"
                    "//     while (slow != null) {\n"
                    "//         ListNode nxt = slow.next;\n"
                    "//         slow.next = prev;\n"
                    "//         prev = slow;\n"
                    "//         slow = nxt;\n"
                    "//     }\n"
                    "//     ListNode left = head, right = prev;\n"
                    "//     while (right != null) {\n"
                    "//         if (!left.val.equals(right.val)) return false;\n"
                    "//         left = left.next; right = right.next;\n"
                    "//     }\n"
                    "//     return true;\n"
                    "// }"
                ),
            },
        },
        {
            "title": "Convert to List + Two-Pointer Compare",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk the list once copying values into an array, then two-pointer compare from both "
                "ends inward. Trivial to write and bug-free — but spends O(n) extra memory you "
                "technically don't need. Mention as the warm-up before the O(1)-space answer; "
                "interviewers like to see you state the easy solution, then upgrade."
            ),
            "code": {
                "python": (
                    "def is_palindrome(head):\n"
                    "    values = list(head)  # in real linked-list code: walk and append node.val\n"
                    "    return values == values[::-1]\n"
                    "\n"
                    "# Equivalent two-pointer version (avoids building a reversed copy):\n"
                    "# def is_palindrome(head):\n"
                    "#     values = list(head)\n"
                    "#     i, j = 0, len(values) - 1\n"
                    "#     while i < j:\n"
                    "#         if values[i] != values[j]: return False\n"
                    "#         i += 1; j -= 1\n"
                    "#     return True"
                ),
                "javascript": (
                    "function isPalindrome(head) {\n"
                    "    const values = [...head];\n"
                    "    let i = 0, j = values.length - 1;\n"
                    "    while (i < j) {\n"
                    "        if (values[i] !== values[j]) return false;\n"
                    "        i++; j--;\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
                "java": (
                    "public boolean isPalindrome(List<Integer> head) {\n"
                    "    int i = 0, j = head.size() - 1;\n"
                    "    while (i < j) {\n"
                    "        if (!head.get(i).equals(head.get(j))) return false;\n"
                    "        i++; j--;\n"
                    "    }\n"
                    "    return true;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate: 'is the value sequence the same forward and backward?' Clarify it's singly linked — no prev pointers — which is what makes the O(1)-space answer non-trivial.",
        "2. State the warm-up: copy values to an array, two-pointer compare. O(n) time, O(n) space. Acknowledge it works but the interviewer will push for better.",
        "3. State the goal: O(n) time, O(1) extra space. The trick: find the middle, reverse the second half, walk both halves comparing values.",
        "4. Find-middle with slow/fast: when fast (moving 2 steps) reaches the end, slow (moving 1 step) is at the midpoint. For odd length, slow lands on the middle node; for even, slow lands on the start of the second half. Either way, reversing 'from slow to end' gives the right comparison.",
        "5. Reverse the second half using the standard three-pointer dance (Reverse Linked List primitive composed inline). After reversal, `prev` is the head of the reversed second half.",
        "6. Walk left from `head` and right from `prev` in lockstep; the right walk terminates first (or at the same time for even length), which automatically handles the odd-length 'skip the middle' case.",
        "7. Edge cases: empty list (True — vacuously), single node (True — slow/fast loop doesn't run, comparison loop doesn't run). Both fall out without special casing.",
        "8. (Optional polish) Restore the second half by reversing it again — only matters if the interviewer cares about not mutating input. State it but don't write it unless asked.",
    ],
    "tips": [
        "The follow-up 'can you do it in O(1) space?' is asked every single time. Don't wait to be asked — volunteer the find-middle-and-reverse approach upfront and save a round-trip.",
        "Slow/fast pointer for the middle: the standard `while fast and fast.next` loop. For odd length, slow is on the middle; for even, slow is on the start of the second half. Both work — you compare until the right pointer hits None, which terminates correctly in both cases.",
        "If the interviewer cares about input integrity, restore the second half by reversing it again at the end. Most don't ask, but mentioning it shows you noticed the mutation.",
        "Don't confuse this with 'palindrome string' or 'palindrome number' — those are array/integer two-pointer problems. The linked-list version's whole point is the O(1)-space twist.",
        "Recursive solution is elegant but uses O(n) stack — for the constraint n up to 1e5, you'll blow Python's default recursion limit. Mention as a curiosity, don't lead with it.",
        "Common bug: comparing pointers instead of values. In the array mirror this doesn't bite, but in real linked-list code make sure you compare `left.val` to `right.val`, not `left` to `right`.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Facebook", "Bloomberg", "Adobe"],
    "topics": ["Linked List", "Two Pointers", "Stack", "Recursion"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(head):
    values = list(head)
    return values == values[::-1]


register(PAYLOAD, REFERENCE)
