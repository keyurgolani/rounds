"""Stack from Scratch — Easy. Logical & Maintainable / Design.

Build a generic Stack with push, pop, peek, size. Surface the
implementation choice (linked list vs dynamic array) and the empty-pop
contract explicitly — that's the L&M signal."""
from builder.registry import register


PAYLOAD = {
    "title": "Stack from Scratch",
    "difficulty": "Easy",
    "description": (
        "Implement a generic stack data structure with the following operations:\n"
        "- `push(value)` — append to the top.\n"
        "- `pop()` — remove and return the top. Return `null` (Python: `None`) when empty.\n"
        "- `peek()` — return the top without removing. Return `null` when empty.\n"
        "- `size()` — number of elements.\n"
        "- `is_empty()` — boolean.\n\n"
        "All operations must be **O(1) amortised**.\n\n"
        "**Test framing:** the harness drives a sequence of operations and inspects every return value, "
        "including the `null` returns from popping or peeking an empty stack."
    ),
    "hints": [
        "Two natural backings: dynamic array (Python list / Java ArrayList) — push/pop at the END are amortised O(1) — or singly-linked list with a head pointer — push/pop at the head are O(1).",
        "Pop on empty: throw vs return None. Both are defensible; pick one and document. The Python idiom is to throw IndexError; the API specified here returns None.",
        "Generics: write the data type-agnostically. Don't hardcode `int` if the question says 'generic'.",
        "Concurrency follow-up: `push` and `pop` are write ops; either lock the whole stack (`synchronized` in Java, `threading.Lock` in Python) or use a lock-free deque.",
        "Memory follow-up: dynamic array has occasional O(n) resize amortised to O(1); linked list has a per-node allocation that fragments memory.",
    ],
    "constraints": [
        "1 <= total operations <= 10⁵",
    ],
    "starter_code": {
        "python": (
            "class Stack:\n"
            "    def __init__(self): pass\n"
            "    def push(self, v): pass\n"
            "    def pop(self): pass\n"
            "    def peek(self): pass\n"
            "    def size(self): pass\n"
            "    def is_empty(self): pass"
        ),
        "javascript": (
            "class Stack {\n"
            "    constructor() {}\n"
            "    push(v) {}\n"
            "    pop() {}\n"
            "    peek() {}\n"
            "    size() {}\n"
            "    isEmpty() {}\n"
            "}"
        ),
        "java": (
            "class Stack<T> {\n"
            "    public Stack() {}\n"
            "    public void push(T v) {}\n"
            "    public T pop() { return null; }\n"
            "    public T peek() { return null; }\n"
            "    public int size() { return 0; }\n"
            "    public boolean isEmpty() { return true; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    s = Stack()\n"
            "    s.push(1); s.push(2)\n"
            "    print(s.pop(), s.pop(), s.pop())  # 2, 1, None"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["Stack", "push", "push", "pop", "pop", "pop"],
                    "args": [[], [1], [2], [], [], []]},
         "expected": [None, None, None, 2, 1, None],
         "description": "Push, pop, pop on empty returns None", "tags": ["basic"]},
        {"input": {"ops": ["Stack", "is_empty", "push", "is_empty", "pop", "is_empty"],
                    "args": [[], [], ["x"], [], [], []]},
         "expected": [None, True, None, False, "x", True],
         "description": "is_empty across the stack lifecycle", "tags": ["basic"]},
        {"input": {"ops": ["Stack", "push", "peek", "size", "peek"],
                    "args": [[], [42], [], [], []]},
         "expected": [None, None, 42, 1, 42],
         "description": "Peek doesn't pop", "tags": ["basic"]},
        {"input": {"ops": ["Stack", "peek", "pop", "size"],
                    "args": [[], [], [], []]},
         "expected": [None, None, None, 0],
         "description": "Empty stack returns None / 0", "tags": ["edge"]},
        {"input": {"ops": ["Stack"] + ["push"] * 5 + ["pop"] * 5,
                    "args": [[], [1], [2], [3], [4], [5], [], [], [], [], []]},
         "expected": [None, None, None, None, None, None, 5, 4, 3, 2, 1],
         "description": "LIFO ordering", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Dynamic Array Backing",
            "time_complexity": "O(1) amortised per op",
            "space_complexity": "O(n)",
            "description": (
                "Back with a list / dynamic array. Push appends; pop removes the last. Both are O(1) "
                "amortised — the language runtime handles resizing. Cache-friendly because elements live "
                "contiguously."
            ),
            "code": {
                "python": (
                    "class Stack:\n"
                    "    def __init__(self):\n"
                    "        self._data = []\n"
                    "    def push(self, v):\n"
                    "        self._data.append(v)\n"
                    "    def pop(self):\n"
                    "        return self._data.pop() if self._data else None\n"
                    "    def peek(self):\n"
                    "        return self._data[-1] if self._data else None\n"
                    "    def size(self):\n"
                    "        return len(self._data)\n"
                    "    def is_empty(self):\n"
                    "        return not self._data"
                ),
                "javascript": (
                    "class Stack {\n"
                    "    constructor() { this.data = []; }\n"
                    "    push(v) { this.data.push(v); }\n"
                    "    pop() { return this.data.length ? this.data.pop() : null; }\n"
                    "    peek() { return this.data.length ? this.data[this.data.length - 1] : null; }\n"
                    "    size() { return this.data.length; }\n"
                    "    isEmpty() { return this.data.length === 0; }\n"
                    "}"
                ),
                "java": (
                    "class Stack<T> {\n"
                    "    private final ArrayList<T> data = new ArrayList<>();\n"
                    "    public void push(T v) { data.add(v); }\n"
                    "    public T pop() { return data.isEmpty() ? null : data.remove(data.size() - 1); }\n"
                    "    public T peek() { return data.isEmpty() ? null : data.get(data.size() - 1); }\n"
                    "    public int size() { return data.size(); }\n"
                    "    public boolean isEmpty() { return data.isEmpty(); }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Linked List Backing",
            "time_complexity": "O(1) per op (true, not amortised)",
            "space_complexity": "O(n) + per-node overhead",
            "description": (
                "Back with a singly linked list, push/pop at the head. True O(1) — no occasional resize "
                "cost. Worse cache behaviour than array. Useful when the stack is large enough that resize "
                "events would matter, or when you can't afford the allocation pause."
            ),
            "code": {
                "python": (
                    "class _Node:\n"
                    "    __slots__ = ('val', 'next')\n"
                    "    def __init__(self, val, nxt=None):\n"
                    "        self.val = val; self.next = nxt\n\n"
                    "class Stack:\n"
                    "    def __init__(self):\n"
                    "        self._head = None\n"
                    "        self._size = 0\n"
                    "    def push(self, v):\n"
                    "        self._head = _Node(v, self._head); self._size += 1\n"
                    "    def pop(self):\n"
                    "        if self._head is None:\n"
                    "            return None\n"
                    "        v = self._head.val; self._head = self._head.next; self._size -= 1\n"
                    "        return v\n"
                    "    def peek(self):\n"
                    "        return self._head.val if self._head else None\n"
                    "    def size(self):\n"
                    "        return self._size\n"
                    "    def is_empty(self):\n"
                    "        return self._head is None"
                ),
            },
        },
    ],
    "thought_score": "1. State the contract first: what does pop on empty do? Throw, return None, sentinel? Pick one and document.",
    "thought_process": [
        "1. State the contract first: pop/peek on empty returns None (per the spec here). Document.",
        "2. Decide backing: dynamic array (cache-friendly, amortised) or linked list (true O(1), poor cache).",
        "3. Generic types: write data-type-agnostic code. Don't hardcode int.",
        "4. Hide internals — `_data` / `_head` is private; only the methods are public.",
        "5. `size` should be O(1) — store a counter, don't traverse the list every call.",
        "6. Edge cases: pop on empty, peek on empty, repeated push/pop, single-element stack.",
        "7. Concurrency: lock the whole stack for thread-safety; consider stripe locks for high contention.",
    ],
    "tips": [
        "If the only test for size is 'is it 0 or not', use is_empty() — `len > 0` works but is_empty is more readable.",
        "Don't size() = sum of pushes minus pops manually — store a counter directly.",
        "JavaScript's Array.push/pop ARE the textbook stack operations — they're already amortised O(1).",
        "Common follow-up: 'add getMin() in O(1).' Maintain a parallel min-stack: push min(currentMin, newValue); pop both.",
        "Common follow-up: 'implement a queue using two stacks.' Push to in-stack; pop from out-stack, refilling from in-stack when out-stack empties. Amortised O(1).",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg"],
    "topics": ["Stack", "Design", "Linked List"],
    "time_complexity": "O(1) amortised",
    "space_complexity": "O(n)",
}


def REFERENCE(input):
    class Stack:
        def __init__(self):
            self._data = []

        def push(self, v):
            self._data.append(v)

        def pop(self):
            return self._data.pop() if self._data else None

        def peek(self):
            return self._data[-1] if self._data else None

        def size(self):
            return len(self._data)

        def is_empty(self):
            return not self._data

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "Stack":
            instance = Stack()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "Stack",
    "constructor": {"params": []},
    "methods": [
        {"name": "push", "params": [{"name": "v", "type": "any"}], "returns": "any"},
        {"name": "pop", "params": [], "returns": "any"},
        {"name": "peek", "params": [], "returns": "any"},
        {"name": "size", "params": [], "returns": "int"},
        {"name": "is_empty", "params": [], "returns": "bool"},
    ],
}


register(PAYLOAD, REFERENCE)
