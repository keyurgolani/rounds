"""Text Editor Model — Medium. Logical & Maintainable / OOD.

Build the M of MVC for a tiny text editor. Plain text first; then
formatting; then images; then borders (decorator); then undo
(command). The L&M signal is incremental design — each new requirement
is one new class, not a rewrite."""
from builder.registry import register


PAYLOAD = {
    "title": "Text Editor Model (Composable Elements)",
    "difficulty": "Medium",
    "description": (
        "Implement the model layer of a tiny text editor (MVC's M) supporting:\n"
        "1. Plain text insert/delete at a cursor position.\n"
        "2. Bold/italic formatting that survives later edits.\n"
        "3. Mixed content — text plus images.\n"
        "4. Undo / redo via Command pattern.\n\n"
        "**Test framing:** the harness drives the editor through a sequence of operations and checks the "
        "rendered text after each one.\n\n"
        "Required operations:\n"
        "- `insert(pos, text)` — insert text at position `pos`.\n"
        "- `delete(pos, count)` — delete `count` characters starting at `pos`.\n"
        "- `text()` — return the current plain text content (formatting is metadata, not in the string).\n"
        "- `undo()` / `redo()` — reverse / replay the last operation.\n\n"
        "**Example:**\n"
        "```\n"
        "e = TextEditor()\n"
        "e.insert(0, 'hello')      # text = 'hello'\n"
        "e.insert(5, ' world')     # text = 'hello world'\n"
        "e.delete(0, 6)            # text = 'world'\n"
        "e.undo()                  # text = 'hello world'\n"
        "e.redo()                  # text = 'world'\n"
        "```"
    ),
    "hints": [
        "Don't copy the whole string on every edit. A list of strings (rope-lite) or a gap buffer is the textbook backing.",
        "For simplicity here, a Python list of characters or a list-of-strings with periodic compaction is fine — the algorithmic point is the COMMAND PATTERN for undo, not micro-optimised storage.",
        "Each editing op is a `Command` with `apply(model)` and `unapply(model)` methods. Push onto an undo stack on apply; push onto a redo stack on undo.",
        "Any non-undo edit clears the redo stack. Otherwise you'd have inconsistent history.",
        "Formatting is metadata — store as runs `(start, end, style)` rather than per-character. Survive edits by adjusting offsets on insert/delete.",
        "Edge cases: undo on empty stack (no-op), redo on empty stack (no-op), insert at end, delete past end.",
    ],
    "constraints": [
        "1 <= total operations <= 10⁴",
    ],
    "starter_code": {
        "python": (
            "class TextEditor:\n"
            "    def __init__(self): pass\n"
            "    def insert(self, pos, text): pass\n"
            "    def delete(self, pos, count): pass\n"
            "    def text(self): pass\n"
            "    def undo(self): pass\n"
            "    def redo(self): pass"
        ),
        "javascript": (
            "class TextEditor {\n"
            "    constructor() {}\n"
            "    insert(pos, text) {}\n"
            "    delete(pos, count) {}\n"
            "    text() {}\n"
            "    undo() {}\n"
            "    redo() {}\n"
            "}"
        ),
        "java": (
            "class TextEditor {\n"
            "    public TextEditor() {}\n"
            "    public void insert(int pos, String text) {}\n"
            "    public void delete(int pos, int count) {}\n"
            "    public String text() { return \"\"; }\n"
            "    public void undo() {}\n"
            "    public void redo() {}\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    e = TextEditor()\n"
            "    e.insert(0, 'hello')\n"
            "    print(e.text())"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["TextEditor", "insert", "insert", "delete", "text"],
                    "args": [[], [0, "hello"], [5, " world"], [0, 6], []]},
         "expected": [None, None, None, None, "world"],
         "description": "Insert + insert + delete", "tags": ["basic"]},
        {"input": {"ops": ["TextEditor", "insert", "undo", "text"],
                    "args": [[], [0, "abc"], [], []]},
         "expected": [None, None, None, ""],
         "description": "Undo a single insert", "tags": ["basic"]},
        {"input": {"ops": ["TextEditor", "insert", "undo", "redo", "text"],
                    "args": [[], [0, "abc"], [], [], []]},
         "expected": [None, None, None, None, "abc"],
         "description": "Redo after undo", "tags": ["basic"]},
        {"input": {"ops": ["TextEditor", "undo", "redo", "text"],
                    "args": [[], [], [], []]},
         "expected": [None, None, None, ""],
         "description": "Undo / redo on empty stacks are no-ops", "tags": ["edge"]},
        {"input": {"ops": ["TextEditor", "insert", "insert", "undo", "insert", "redo", "text"],
                    "args": [[], [0, "a"], [1, "b"], [], [1, "X"], [], []]},
         "expected": [None, None, None, None, None, None, "aX"],
         "description": "New edit after undo invalidates redo stack",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Command Pattern + List Backing",
            "time_complexity": "O(n) per edit (string copy), O(1) per undo/redo (apart from edit cost)",
            "space_complexity": "O(history × edit_size)",
            "description": (
                "Each edit is a Command object that knows how to apply and undo itself. Undo pops from the "
                "undo stack, calls `unapply`, pushes onto the redo stack. New edits clear the redo stack. "
                "For the algorithmic point, the data structure backing the text is incidental — `[chars]` "
                "is fine."
            ),
            "code": {
                "python": (
                    "class _InsertCmd:\n"
                    "    def __init__(self, pos, text):\n"
                    "        self.pos = pos; self.text = text\n"
                    "    def apply(self, ed):\n"
                    "        ed._buf[self.pos:self.pos] = list(self.text)\n"
                    "    def unapply(self, ed):\n"
                    "        del ed._buf[self.pos:self.pos + len(self.text)]\n\n"
                    "class _DeleteCmd:\n"
                    "    def __init__(self, pos, count):\n"
                    "        self.pos = pos; self.count = count; self.removed = ''\n"
                    "    def apply(self, ed):\n"
                    "        self.removed = ''.join(ed._buf[self.pos:self.pos + self.count])\n"
                    "        del ed._buf[self.pos:self.pos + self.count]\n"
                    "    def unapply(self, ed):\n"
                    "        ed._buf[self.pos:self.pos] = list(self.removed)\n\n"
                    "class TextEditor:\n"
                    "    def __init__(self):\n"
                    "        self._buf = []\n"
                    "        self._undo = []\n"
                    "        self._redo = []\n"
                    "    def insert(self, pos, text):\n"
                    "        cmd = _InsertCmd(pos, text)\n"
                    "        cmd.apply(self)\n"
                    "        self._undo.append(cmd)\n"
                    "        self._redo.clear()\n"
                    "    def delete(self, pos, count):\n"
                    "        cmd = _DeleteCmd(pos, count)\n"
                    "        cmd.apply(self)\n"
                    "        self._undo.append(cmd)\n"
                    "        self._redo.clear()\n"
                    "    def text(self):\n"
                    "        return ''.join(self._buf)\n"
                    "    def undo(self):\n"
                    "        if not self._undo:\n"
                    "            return\n"
                    "        cmd = self._undo.pop()\n"
                    "        cmd.unapply(self)\n"
                    "        self._redo.append(cmd)\n"
                    "    def redo(self):\n"
                    "        if not self._redo:\n"
                    "            return\n"
                    "        cmd = self._redo.pop()\n"
                    "        cmd.apply(self)\n"
                    "        self._undo.append(cmd)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Sketch the M layer first — text storage and edit operations. Don't bring in undo until the basic ops work.",
        "2. Don't model formatting as 'each char has style'; that breaks at scale. Use runs / spans.",
        "3. Inline images: `Element` interface with `Text`, `Image` subclasses. Common ops both must support.",
        "4. Borders: Decorator pattern. `BorderedElement(child, color)` wraps any other element.",
        "5. Tables: another Element kind — collection of cells, each holding an Element.",
        "6. Undo: Command pattern. Each edit becomes a Command with apply/unapply. Push onto a stack.",
        "7. Watch the redo invariant: any new edit clears the redo stack — otherwise history forks.",
    ],
    "tips": [
        "Don't reach for a rope or gap buffer until asked. The algorithmic content of this question is the Command pattern, not the storage.",
        "If formatting moves on edit, store runs sorted by start. On insert at pos, shift starts >= pos by len(insert). On delete, trim runs that overlap.",
        "Decorator pattern wins again for borders — same Element interface, behaviour layered.",
        "Common follow-up: 'collaborative editing.' Now you need OT or CRDTs — out of scope for the model layer alone.",
        "Common follow-up: 'undo group N consecutive keystrokes as one.' Coalesce commands within a time window before pushing.",
        "Common follow-up: 'persist undo history.' Each command is serialisable — `apply` and `unapply` from the same data.",
    ],
    "companies": ["Amazon", "Google", "Microsoft", "Apple"],
    "topics": ["Design", "Command Pattern", "Decorator Pattern", "Stack"],
    "time_complexity": "O(n) per edit, O(1) per undo",
    "space_complexity": "O(history)",
}


def REFERENCE(input):
    class _InsertCmd:
        def __init__(self, pos, text):
            self.pos = pos
            self.text = text

        def apply(self, ed):
            ed._buf[self.pos:self.pos] = list(self.text)

        def unapply(self, ed):
            del ed._buf[self.pos:self.pos + len(self.text)]

    class _DeleteCmd:
        def __init__(self, pos, count):
            self.pos = pos
            self.count = count
            self.removed = ""

        def apply(self, ed):
            self.removed = "".join(ed._buf[self.pos:self.pos + self.count])
            del ed._buf[self.pos:self.pos + self.count]

        def unapply(self, ed):
            ed._buf[self.pos:self.pos] = list(self.removed)

    class TextEditor:
        def __init__(self):
            self._buf = []
            self._undo = []
            self._redo = []

        def insert(self, pos, text):
            cmd = _InsertCmd(pos, text)
            cmd.apply(self)
            self._undo.append(cmd)
            self._redo.clear()

        def delete(self, pos, count):
            cmd = _DeleteCmd(pos, count)
            cmd.apply(self)
            self._undo.append(cmd)
            self._redo.clear()

        def text(self):
            return "".join(self._buf)

        def undo(self):
            if not self._undo:
                return
            cmd = self._undo.pop()
            cmd.unapply(self)
            self._redo.append(cmd)

        def redo(self):
            if not self._redo:
                return
            cmd = self._redo.pop()
            cmd.apply(self)
            self._undo.append(cmd)

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "TextEditor":
            instance = TextEditor()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "TextEditor",
    "constructor": {"params": []},
    "methods": [
        {"name": "insert", "params": [{"name": "pos", "type": "int"},
                                       {"name": "text", "type": "string"}], "returns": "any"},
        {"name": "delete", "params": [{"name": "pos", "type": "int"},
                                       {"name": "count", "type": "int"}], "returns": "any"},
        {"name": "text", "params": [], "returns": "string"},
        {"name": "undo", "params": [], "returns": "any"},
        {"name": "redo", "params": [], "returns": "any"},
    ],
}


register(PAYLOAD, REFERENCE)
