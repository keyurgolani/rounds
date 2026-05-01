"""Min Stack — Easy. Stack / Design.

Design a stack that supports push, pop, top, and retrieving the minimum
element, all in O(1) time. The trick is to maintain auxiliary state
(parallel min-stack or per-entry min) so getMin doesn't have to scan."""
from builder.registry import register


PAYLOAD = {
    "title": "Min Stack",
    "difficulty": "Easy",
    "description": (
        "Design a stack that supports the following operations, **all in O(1) time**:\n"
        "- `push(val)` — push integer `val` onto the stack.\n"
        "- `pop()` — remove the element on top of the stack.\n"
        "- `top()` — return the element on top of the stack.\n"
        "- `get_min()` — return the minimum element currently in the stack.\n\n"
        "**Example sequence:**\n"
        "```\n"
        "s = MinStack()\n"
        "s.push(-2)\n"
        "s.push(0)\n"
        "s.push(-3)\n"
        "s.get_min()   # → -3\n"
        "s.pop()\n"
        "s.top()       # → 0\n"
        "s.get_min()   # → -2\n"
        "```\n"
        "You may assume `pop`, `top`, and `get_min` are only called on a non-empty stack "
        "(LeetCode 155 guarantees this in test inputs)."
    ),
    "hints": [
        "Computing min on each `get_min` call by scanning is O(n) — too slow. You need to *cache* the min as the stack mutates.",
        "Push the running minimum alongside each element (or on a parallel stack). Pop both together.",
        "Trick: a single stack of `(val, current_min)` tuples is the simplest mental model.",
        "Memory optimization: store deltas vs the current min instead of full mins (advanced).",
        "Edge cases to think through: duplicates of the current minimum, strictly increasing pushes, strictly decreasing pushes.",
    ],
    "constraints": [
        "-2³¹ <= val <= 2³¹ - 1",
        "At most 3 * 10⁴ calls total to push/pop/top/get_min",
        "pop, top, and get_min are only called on a non-empty stack",
    ],
    "starter_code": {
        "python": (
            "class MinStack:\n"
            "    def __init__(self):\n"
            "        pass\n"
            "    def push(self, val):\n"
            "        pass\n"
            "    def pop(self):\n"
            "        pass\n"
            "    def top(self):\n"
            "        pass\n"
            "    def get_min(self):\n"
            "        pass"
        ),
        "javascript": (
            "class MinStack {\n"
            "    constructor() { /* ... */ }\n"
            "    push(val) { /* ... */ }\n"
            "    pop() { /* ... */ }\n"
            "    top() { /* ... */ }\n"
            "    getMin() { /* ... */ }\n"
            "}"
        ),
        "java": (
            "class MinStack {\n"
            "    public MinStack() {}\n"
            "    public void push(int val) {}\n"
            "    public void pop() {}\n"
            "    public int top() { return 0; }\n"
            "    public int getMin() { return 0; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    s = MinStack()\n"
            "    s.push(-2); s.push(0); s.push(-3)\n"
            "    print(s.get_min())  # -3\n"
            "    s.pop()\n"
            "    print(s.top())      # 0\n"
            "    print(s.get_min())  # -2"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["MinStack", "push", "push", "push", "get_min", "pop", "top", "get_min"],
                    "args": [[], [-2], [0], [-3], [], [], [], []]},
         "expected": [None, None, None, None, -3, None, 0, -2],
         "description": "Standard LeetCode example sequence", "tags": ["basic"]},
        {"input": {"ops": ["MinStack", "push", "get_min", "top"],
                    "args": [[], [42], [], []]},
         "expected": [None, None, 42, 42],
         "description": "Single element — top equals get_min", "tags": ["edge"]},
        {"input": {"ops": ["MinStack", "push", "push", "push", "get_min", "pop", "get_min", "pop", "get_min"],
                    "args": [[], [5], [5], [5], [], [], [], [], []]},
         "expected": [None, None, None, None, 5, None, 5, None, 5],
         "description": "Repeating min values — all duplicates must each preserve the min on pop",
         "tags": ["edge", "duplicates"]},
        {"input": {"ops": ["MinStack", "push", "push", "push", "push", "get_min", "pop", "get_min", "pop", "get_min"],
                    "args": [[], [1], [2], [3], [4], [], [], [], [], []]},
         "expected": [None, None, None, None, None, 1, None, 1, None, 1],
         "description": "Strictly increasing pushes — min stays at the bottom", "tags": ["basic"]},
        {"input": {"ops": ["MinStack", "push", "push", "push", "push", "get_min", "pop", "get_min", "pop", "get_min", "pop", "get_min"],
                    "args": [[], [4], [3], [2], [1], [], [], [], [], [], [], []]},
         "expected": [None, None, None, None, None, 1, None, 2, None, 3, None, 4],
         "description": "Strictly decreasing pushes — every pop reveals a new min",
         "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Two Stacks (Canonical)",
            "time_complexity": "O(1) for all operations",
            "space_complexity": "O(n)",
            "description": (
                "Maintain a primary stack of values and a parallel `min_stack`. On every `push(val)`, also push "
                "`min(val, min_stack[-1])` (or `val` itself if the min stack is empty) onto `min_stack`. On `pop`, "
                "pop both stacks. `get_min` is just `min_stack[-1]`. Worst case the min stack is the same size as "
                "the value stack, but every operation is genuinely O(1)."
            ),
            "code": {
                "python": (
                    "class MinStack:\n"
                    "    def __init__(self):\n"
                    "        self._stack = []\n"
                    "        self._min = []\n"
                    "    def push(self, val):\n"
                    "        self._stack.append(val)\n"
                    "        self._min.append(val if not self._min else min(val, self._min[-1]))\n"
                    "    def pop(self):\n"
                    "        self._stack.pop()\n"
                    "        self._min.pop()\n"
                    "    def top(self):\n"
                    "        return self._stack[-1]\n"
                    "    def get_min(self):\n"
                    "        return self._min[-1]"
                ),
                "javascript": (
                    "class MinStack {\n"
                    "    constructor() { this.stack = []; this.minStack = []; }\n"
                    "    push(val) {\n"
                    "        this.stack.push(val);\n"
                    "        const m = this.minStack.length === 0 ? val : Math.min(val, this.minStack[this.minStack.length - 1]);\n"
                    "        this.minStack.push(m);\n"
                    "    }\n"
                    "    pop() { this.stack.pop(); this.minStack.pop(); }\n"
                    "    top() { return this.stack[this.stack.length - 1]; }\n"
                    "    getMin() { return this.minStack[this.minStack.length - 1]; }\n"
                    "}"
                ),
                "java": (
                    "class MinStack {\n"
                    "    private final Deque<Integer> stack = new ArrayDeque<>();\n"
                    "    private final Deque<Integer> minStack = new ArrayDeque<>();\n"
                    "    public void push(int val) {\n"
                    "        stack.push(val);\n"
                    "        minStack.push(minStack.isEmpty() ? val : Math.min(val, minStack.peek()));\n"
                    "    }\n"
                    "    public void pop() { stack.pop(); minStack.pop(); }\n"
                    "    public int top() { return stack.peek(); }\n"
                    "    public int getMin() { return minStack.peek(); }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Single Stack of (val, current_min) Tuples",
            "time_complexity": "O(1) for all operations",
            "space_complexity": "O(n)",
            "description": (
                "Same idea as two stacks, but baked into a single stack of `(val, running_min)` tuples. "
                "Cleaner if you prefer one data structure; identical asymptotic behavior. Useful when an "
                "interviewer asks you to 'use a single stack' as a constraint."
            ),
            "code": {
                "python": (
                    "class MinStack:\n"
                    "    def __init__(self):\n"
                    "        self._stack = []  # list of (val, running_min)\n"
                    "    def push(self, val):\n"
                    "        m = val if not self._stack else min(val, self._stack[-1][1])\n"
                    "        self._stack.append((val, m))\n"
                    "    def pop(self):\n"
                    "        self._stack.pop()\n"
                    "    def top(self):\n"
                    "        return self._stack[-1][0]\n"
                    "    def get_min(self):\n"
                    "        return self._stack[-1][1]"
                ),
                "javascript": (
                    "class MinStack {\n"
                    "    constructor() { this.stack = []; }\n"
                    "    push(val) {\n"
                    "        const m = this.stack.length === 0 ? val : Math.min(val, this.stack[this.stack.length - 1][1]);\n"
                    "        this.stack.push([val, m]);\n"
                    "    }\n"
                    "    pop() { this.stack.pop(); }\n"
                    "    top() { return this.stack[this.stack.length - 1][0]; }\n"
                    "    getMin() { return this.stack[this.stack.length - 1][1]; }\n"
                    "}"
                ),
            },
        },
        {
            "title": "Single Stack with Delta Encoding (Memory-Optimal)",
            "time_complexity": "O(1) for all operations",
            "space_complexity": "O(n) — single stack, ~half the memory of the two-stack approach",
            "description": (
                "Store `val - current_min` (a delta) instead of `val`. Maintain `current_min` as a single field. "
                "When pushing, if `val < current_min`, store the delta `val - current_min` (negative) and update "
                "`current_min = val`. On `pop`, if the top delta is negative, the min before this push was "
                "`current_min - delta`; restore it. This is the classic 'clever trick' answer — interviewers love "
                "it but the two-stack solution is what they expect first."
            ),
            "code": {
                "python": (
                    "class MinStack:\n"
                    "    def __init__(self):\n"
                    "        self._stack = []  # stores deltas (val - min_at_time_of_push)\n"
                    "        self._min = 0\n"
                    "    def push(self, val):\n"
                    "        if not self._stack:\n"
                    "            self._stack.append(0)\n"
                    "            self._min = val\n"
                    "        else:\n"
                    "            self._stack.append(val - self._min)\n"
                    "            if val < self._min:\n"
                    "                self._min = val\n"
                    "    def pop(self):\n"
                    "        delta = self._stack.pop()\n"
                    "        if delta < 0:\n"
                    "            # popped value was the min; restore previous min\n"
                    "            self._min = self._min - delta\n"
                    "    def top(self):\n"
                    "        delta = self._stack[-1]\n"
                    "        return self._min if delta < 0 else self._min + delta\n"
                    "    def get_min(self):\n"
                    "        return self._min"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Read the constraint carefully: ALL ops must be O(1), including `get_min`. That rules out 'scan the stack on get_min' (O(n)).",
        "2. Recognize this is a 'cache the answer' problem — we must update the min as the stack mutates, not when it's queried.",
        "3. First idea: store the running min alongside each element. Then `get_min` is just reading the top.",
        "4. Pick a layout: two parallel stacks (clearest), single stack of tuples (one structure), or delta encoding (memory win).",
        "5. Walk through duplicates: if you push the current min N times, you must pop N times before the min changes. The 'push min on every push' trick handles this naturally — DO NOT try to push the min only on strict-less-than, that breaks pop.",
        "6. Sanity-check both monotonic patterns: strictly increasing pushes → min stays at the bottom; strictly decreasing pushes → every pop reveals the previous min.",
    ],
    "tips": [
        "Duplicates trap: a tempting but wrong optimization is 'only push to min_stack when val < current_min.' This breaks: if you push the same min value 3 times then pop once, you'd lose track of how many copies remain. Always push *some* min marker on every push (full min, or a count, or a delta).",
        "Why two stacks beats 'compute min on get_min': O(1) vs O(n) per call. With 3·10⁴ calls, a scan-based solution is 9·10⁸ ops worst case — TLE. The auxiliary structure pays its O(n) memory cost to win on time.",
        "Interviewer follow-up: 'Can you do it with O(1) extra space?' — that's a hard problem (true O(1) auxiliary). The delta-encoding solution above is O(n) total but uses a single stack; mention it as a memory optimization, not as O(1) space.",
        "Java specific: prefer `ArrayDeque` over `Stack`. `Stack` extends `Vector` and is synchronized — slow and discouraged.",
        "Naming gotcha: LeetCode uses `getMin()` (camelCase), Python convention is `get_min()`. Match whatever the harness expects — here it's `get_min`.",
    ],
    "companies": ["Amazon", "Bloomberg", "Microsoft"],
    "topics": ["Stack", "Design"],
    "time_complexity": "O(1)",
    "space_complexity": "O(n)",
}


def REFERENCE(input):
    """Class-ops driver: replay the operation sequence."""

    class MinStack:
        def __init__(self):
            self._stack = []
            self._min = []

        def push(self, val):
            self._stack.append(val)
            self._min.append(val if not self._min else min(val, self._min[-1]))

        def pop(self):
            self._stack.pop()
            self._min.pop()

        def top(self):
            return self._stack[-1]

        def get_min(self):
            return self._min[-1]

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "MinStack":
            instance = MinStack()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


# Add the entry field for class_ops dispatch
PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "MinStack",
    "constructor": {"params": []},
    "methods": [
        {"name": "push", "params": [{"name": "val", "type": "int"}], "returns": "any"},
        {"name": "pop", "params": [], "returns": "any"},
        {"name": "top", "params": [], "returns": "int"},
        {"name": "get_min", "params": [], "returns": "int"},
    ],
}


register(PAYLOAD, REFERENCE)
