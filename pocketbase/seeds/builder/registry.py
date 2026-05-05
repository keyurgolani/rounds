"""Registry collecting authored coding-question modules.

Each module under `builder/questions/` defines a top-level `QUESTION`
dict (the canonical PocketBase shape) and a top-level `REFERENCE`
callable (the Python solution invoked during validation). The build
script imports every module in `builder/questions/`, harvests both,
runs the reference solution against every test case via the actual
backend matchers, and emits the consolidated `more_coding.json`.

Test-case `expected` values follow the same conventions as the
existing seed (see `pocketbase/seeds/content.json`):

  - Bare value      → strict equality
  - {"$match":"..."} → tagged matcher (validator/unordered_deep/etc.)

The reference callable receives the test-case input dict expanded as
keyword arguments. For class-based problems (input shaped as
`{"ops": [...], "args": [...]}`) the reference receives the dict and
must replay the op sequence itself — this mirrors how
`backend/runner.py` dispatches the user's class.


# ---- The `entry` contract ------------------------------------------------
#
# Each PAYLOAD dict must include an `entry` key that tells the runtime
# which driver to use and how to wrap the user's submitted code.
#
# FIELDS
# ------
# kind (required)
#   One of: "function", "class_ops", "linked_list", "tree", "graph",
#   "in_place_mutation", "custom".
#   Selects the driver module under backend/drivers/{python,javascript}/.
#
# name (required for all non-"custom" kinds)
#   The user-visible function (or method) name that the harness will call.
#   Must exactly match the function the user defines in the editor.
#   Example: "add_two_numbers", "invertTree", "cloneGraph".
#
# params (required for kinds that take arguments)
#   List of {"name": str, "type": str} dicts describing the function
#   parameters in declaration order.
#   For node-aware kinds ("linked_list", "tree", "graph"), any param
#   whose "type" is "node" is automatically inflated from the input
#   shorthand into a real node object before the user function is called,
#   and the returned node is deflated back to verbose form for matching.
#   Example: [{"name": "l1", "type": "node"}, {"name": "l2", "type": "node"}]
#
# input_shape (optional; kind-specific default)
#   Controls how each test-case `input` value is decoded before being
#   passed to the driver.
#   - "linked_list_array"  (default for "linked_list"): flat digit/value
#     array, e.g. [2, 4, 3] builds a 3-node chain 2→4→3.
#   - "tree_level_order"   (default for "tree"): BFS-level array,
#     e.g. [1, 2, 3, None, None, 4] follows LeetCode level-order encoding.
#   - "graph_adjacency"    (default for "graph"): adjacency dict keyed by
#     string node values, e.g. {"1": [2, 3], "2": [1], "3": [1]}.
#   - "verbose": the test-case input is already in the canonical
#     {"nodes": [...], "entry": id} form — no transformation is applied.
#   For "function" / "class_ops" kinds this field is not used.
#
# output_shape (optional; default "verbose")
#   Controls how the user's returned node (or chain) is reshaped before
#   being fed to the matcher.
#   - "verbose"            → raw {"nodes", "entry"} dict (always available).
#   - "linked_list_array"  → flat value array, e.g. [7, 0, 8].
#   - "tree_level_order"   → BFS-level array, trailing nulls stripped.
#   Per-kind supported output shapes:
#     linked_list: {"verbose", "linked_list_array"}
#     tree:        {"verbose", "tree_level_order"}
#     graph:       {"verbose", "graph_adjacency"}
#
# node_template (optional; kind-specific default)
#   Customizes the generated Node class injected into the user's sandbox.
#   Keys:
#     "name"   (str)  — class name, e.g. "ListNode", "TreeNode", "Node".
#     "fields" (list) — list of {"name": str, "type": str} value fields.
#     "links"  (list) — list of {"name": str, "arity": "single"|"list"}
#                       pointer fields.
#   Defaults:
#     linked_list → ListNode  {fields: [val], links: [next (single)]}
#     tree        → TreeNode  {fields: [val], links: [left, right (single)]}
#     graph       → Node      {fields: [val], links: [neighbors (list)]}
#
# NOTE ON TEST CASES
# ------------------
# The test-case `input` and `expected` values stay in the readable
# shorthand form (e.g. flat arrays for linked lists, level-order arrays
# for trees). The driver round-trips through verbose internally; problem
# authors never need to write verbose JSON by hand.
#
# WORKED EXAMPLE — add_two_numbers
# ---------------------------------
# "entry": {
#     "kind": "linked_list",
#     "name": "add_two_numbers",
#     "params": [
#         {"name": "l1", "type": "node"},
#         {"name": "l2", "type": "node"},
#     ],
#     "input_shape": "linked_list_array",
#     "output_shape": "linked_list_array",
# }
#
# The runtime inflates l1=[2,4,3] and l2=[5,6,4] into real ListNode
# chains, calls add_two_numbers(l1, l2), deflates the returned chain,
# and reshapes to a flat array [7,0,8] before matching against expected.
# --------------------------------------------------------------------------
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


Matcher = Callable[[Any, Any, Any], tuple[bool, str | None]]


@dataclass
class Question:
    payload: dict[str, Any]
    reference_python: Callable[..., Any]
    # Optional: skip validation on specific test-case indices (e.g.
    # validators that only check structural invariants the reference
    # happens to satisfy by construction). Empty by default.
    skip_validation_indices: set[int] = field(default_factory=set)


# Module-level registry. Each question module appends to this list at
# import time via `register(...)`.
QUESTIONS: list[Question] = []


def register(payload: dict[str, Any], reference_python: Callable[..., Any], **kwargs: Any) -> None:
    QUESTIONS.append(Question(payload=payload, reference_python=reference_python, **kwargs))


# ---- Matcher helpers (build-time convenience constructors) -----------
# These produce the same JSON shapes the runtime matcher in
# `backend/matchers.py` understands, but are easier to author from
# Python than hand-written dicts.

def validator(description: str, code: str, examples: list[Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "$match": "validator",
        "description": description,
        "code": code,
    }
    if examples is not None:
        out["examples"] = examples
    return out


def unordered_deep(value: Any) -> dict[str, Any]:
    return {"$match": "unordered_deep", "value": value}


def unordered(value: Any) -> dict[str, Any]:
    return {"$match": "unordered", "value": value}


def any_of(values: list[Any]) -> dict[str, Any]:
    return {"$match": "any_of", "values": values}


def approx(value: Any, abs_tol: float = 0.0, rel_tol: float = 0.0) -> dict[str, Any]:
    return {"$match": "approx", "value": value, "abs_tol": abs_tol, "rel_tol": rel_tol}
