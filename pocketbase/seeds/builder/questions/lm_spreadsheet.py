"""Spreadsheet — Hard. Logical & Maintainable / DAG.

Implement a tiny spreadsheet with cell references and formulas.
The senior bar: dependency graph for invalidation, cycle detection,
lazy vs eager recomputation."""
from builder.registry import register


PAYLOAD = {
    "title": "Spreadsheet (Cells, Formulas, Cycles)",
    "difficulty": "Hard",
    "description": (
        "Implement a `Spreadsheet` class supporting:\n"
        "- `set(cell, value)` — `value` is either an integer literal or a formula `'=A1+B2'` (sum of "
        "cells; only single-level addition for this problem).\n"
        "- `get(cell)` — return the current numeric value, recomputing dependencies as needed. Return "
        "`None` if there's a cycle anywhere in `cell`'s dependency chain or any referenced cell is "
        "unset.\n\n"
        "Cell ids are like `A1`, `B12` (one letter, then digits). Formulas reference other cell ids "
        "separated by `+`.\n\n"
        "**Example:**\n"
        "```\n"
        "s.set('A1', 5)\n"
        "s.set('A2', 2)\n"
        "s.set('A3', '=A1+A2')\n"
        "s.get('A3')     # 7\n"
        "s.set('A2', 4)\n"
        "s.get('A3')     # 9 (must reflect the update)\n"
        "s.set('C1', '=C2+3')   # invalid — '3' isn't a cell id\n"
        "                       # for this problem, formulas are pure cell sums\n"
        "s.set('B1', '=B2')\n"
        "s.set('B2', '=B1')     # cycle\n"
        "s.get('B1')     # None\n"
        "```"
    ),
    "hints": [
        "Store each cell as `(kind, payload)` — either a literal value or a list of referenced cell ids.",
        "On `get`: recursively compute dependencies. Memoise per-`get` to avoid repeated subtree work.",
        "Cycle detection: track 'currently being computed' cells. If a recursion hits a cell already in that set, return None.",
        "Don't compute on `set` — that misses the update propagation case (set A2 → A3 must reflect the new value when next read).",
        "Optionally maintain a reverse-dependency graph for eager invalidation; for the basic version, lazy recomputation is enough.",
        "Edge cases: cell never set, formula with one term, cell referencing itself, deep dependency chain.",
    ],
    "constraints": [
        "1 <= total operations <= 10⁴",
        "Formulas are sums of cell ids only (no constants)",
    ],
    "starter_code": {
        "python": (
            "class Spreadsheet:\n"
            "    def __init__(self): pass\n"
            "    def set(self, cell, value): pass\n"
            "    def get(self, cell): pass"
        ),
        "javascript": (
            "class Spreadsheet {\n"
            "    constructor() {}\n"
            "    set(cell, value) {}\n"
            "    get(cell) {}\n"
            "}"
        ),
        "java": (
            "class Spreadsheet {\n"
            "    public Spreadsheet() {}\n"
            "    public void set(String cell, Object value) {}\n"
            "    public Integer get(String cell) { return null; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    s = Spreadsheet()\n"
            "    s.set('A1', 5); s.set('A2', 2); s.set('A3', '=A1+A2')\n"
            "    print(s.get('A3'))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["Spreadsheet", "set", "set", "set", "get", "set", "get"],
                    "args": [[], ["A1", 5], ["A2", 2], ["A3", "=A1+A2"], ["A3"], ["A2", 4], ["A3"]]},
         "expected": [None, None, None, None, 7, None, 9],
         "description": "Update propagates through formula", "tags": ["basic"]},
        {"input": {"ops": ["Spreadsheet", "get"], "args": [[], ["A1"]]},
         "expected": [None, None],
         "description": "Get on never-set cell", "tags": ["edge"]},
        {"input": {"ops": ["Spreadsheet", "set", "set", "get"],
                    "args": [[], ["A1", "=A2"], ["A2", "=A1"], ["A1"]]},
         "expected": [None, None, None, None],
         "description": "Two-cell cycle", "tags": ["edge"]},
        {"input": {"ops": ["Spreadsheet", "set", "get"],
                    "args": [[], ["A1", "=A1"], ["A1"]]},
         "expected": [None, None, None],
         "description": "Self-referential cell", "tags": ["edge"]},
        {"input": {"ops": ["Spreadsheet", "set", "set", "set", "get"],
                    "args": [[], ["A1", 1], ["B1", "=A1"], ["C1", "=B1"], ["C1"]]},
         "expected": [None, None, None, None, 1],
         "description": "Three-deep dependency chain", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Lazy Recomputation with Cycle Detection (Optimal)",
            "time_complexity": "O(D) per get where D = transitive dependency count",
            "space_complexity": "O(C) cell store + O(D) recursion",
            "description": (
                "Cells store either an int literal or a list of referenced cell ids. `set` only writes the "
                "raw value/formula. `get` recursively resolves: literal → return; formula → sum the gets of "
                "each ref. Track an 'in progress' set across the recursion to detect cycles → return None. "
                "A per-`get` memo stops re-walking the same subtree."
            ),
            "code": {
                "python": (
                    "class Spreadsheet:\n"
                    "    def __init__(self):\n"
                    "        self._cells = {}\n"
                    "    def set(self, cell, value):\n"
                    "        if isinstance(value, str) and value.startswith('='):\n"
                    "            refs = value[1:].split('+')\n"
                    "            self._cells[cell] = ('formula', refs)\n"
                    "        else:\n"
                    "            self._cells[cell] = ('literal', value)\n"
                    "    def get(self, cell):\n"
                    "        return self._resolve(cell, set(), {})\n"
                    "    def _resolve(self, cell, in_progress, memo):\n"
                    "        if cell in memo:\n"
                    "            return memo[cell]\n"
                    "        if cell in in_progress:\n"
                    "            return None  # cycle\n"
                    "        if cell not in self._cells:\n"
                    "            return None\n"
                    "        kind, payload = self._cells[cell]\n"
                    "        if kind == 'literal':\n"
                    "            memo[cell] = payload\n"
                    "            return payload\n"
                    "        in_progress.add(cell)\n"
                    "        total = 0\n"
                    "        for ref in payload:\n"
                    "            v = self._resolve(ref, in_progress, memo)\n"
                    "            if v is None:\n"
                    "                in_progress.discard(cell)\n"
                    "                return None\n"
                    "            total += v\n"
                    "        in_progress.discard(cell)\n"
                    "        memo[cell] = total\n"
                    "        return total"
                ),
            },
        },
        {
            "title": "Eager Recomputation with Reverse-Dependency Graph",
            "time_complexity": "O(D_invalidate) per set, O(1) per get (after recompute)",
            "space_complexity": "O(C) + reverse-deps storage",
            "description": (
                "Maintain `cell → cells that depend on it`. On `set`, recompute the cell's value, then "
                "BFS through reverse-deps recomputing each in topological order. Cycles still need "
                "detection during recomputation. Wins when reads are much more frequent than writes."
            ),
            "code": {
                "python": (
                    "# Sketch — not implemented in full; complexity warning.\n"
                    "class Spreadsheet:\n"
                    "    def __init__(self):\n"
                    "        raise NotImplementedError(\n"
                    "            'Eager: maintain cell -> set of dependents. On set, recompute and walk reverse-deps.'\n"
                    "        )"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Decide eager vs lazy. Lazy is simpler to write correctly under interview pressure.",
        "2. Cell store: each cell is either a literal int or a parsed formula (list of refs).",
        "3. `set` is a pure write — never compute. That's the bug most candidates introduce in v1.",
        "4. `get` is a recursive resolve: literal → return; formula → sum of resolves of each ref.",
        "5. Cycle detection: track 'in progress' cells across the recursion. Hit one again → cycle → return None.",
        "6. Memoise per `get` call. Subtree results are stable for the duration of a single resolve.",
        "7. Edge cases: missing cell, self-referential, two-cycle, deep chain, broken chain (any unset cell along the way).",
    ],
    "tips": [
        "The 'compute on set' bug is the canonical L4 failure — set('A2', 4) doesn't update A3's stored value, so the next get('A3') returns the stale 7. Lazy fixes it.",
        "Memoisation per `get` is fine; memoisation across `get` calls is wrong unless you also invalidate on every `set`.",
        "Cycle detection isn't optional. The most common bug: infinite recursion until stack overflow.",
        "Common follow-up: 'support arbitrary expressions with precedence.' Now you need a real parser. Discuss Pratt parsing or recursive descent.",
        "Common follow-up: 'collaborative editing.' That's CRDT territory — operational transforms, last-write-wins per cell, version vectors.",
    ],
    "companies": ["Amazon", "Microsoft", "Google"],
    "topics": ["Graph", "Topological Sort", "DFS", "Design"],
    "time_complexity": "O(D) per get",
    "space_complexity": "O(C)",
}


def REFERENCE(input):
    class Spreadsheet:
        def __init__(self):
            self._cells = {}

        def set(self, cell, value):
            if isinstance(value, str) and value.startswith("="):
                refs = value[1:].split("+")
                self._cells[cell] = ("formula", refs)
            else:
                self._cells[cell] = ("literal", value)

        def get(self, cell):
            return self._resolve(cell, set(), {})

        def _resolve(self, cell, in_progress, memo):
            if cell in memo:
                return memo[cell]
            if cell in in_progress:
                return None
            if cell not in self._cells:
                return None
            kind, payload = self._cells[cell]
            if kind == "literal":
                memo[cell] = payload
                return payload
            in_progress.add(cell)
            total = 0
            for ref in payload:
                v = self._resolve(ref, in_progress, memo)
                if v is None:
                    in_progress.discard(cell)
                    return None
                total += v
            in_progress.discard(cell)
            memo[cell] = total
            return total

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "Spreadsheet":
            instance = Spreadsheet()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "Spreadsheet",
    "constructor": {"params": []},
    "methods": [
        {"name": "set", "params": [{"name": "cell", "type": "string"},
                                    {"name": "value", "type": "any"}], "returns": "any"},
        {"name": "get", "params": [{"name": "cell", "type": "string"}], "returns": "any"},
    ],
}


register(PAYLOAD, REFERENCE)
