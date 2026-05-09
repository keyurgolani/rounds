"""Build-time shorthand → verbose helpers for authoring node-shaped fixtures.

The runtime drivers (backend/drivers/{python,javascript}/{tree,linked_list,
graph}.py) accept ONLY the canonical verbose form
    {"nodes": [{"id": int, "fields": {...}, "links": {...}}], "entry": id|None}
A test case authored as a level-order array, flat list, or adjacency dict is
a *build-time* convenience: the helpers here translate it into verbose JSON
which the seed file ultimately stores. Anything that escapes this layer with
a legacy shape will be rejected by the runtime drivers and surface as a
build failure, which is what we want.

Importable as `from builder._shorthand import to_verbose, inflate_tree, ...`
from any module under pocketbase/seeds/builder/."""
from __future__ import annotations

from typing import Any


# Default templates per kind — match the backend driver defaults so that
# question authors usually don't need to think about them.
TREE_TEMPLATE = {
    "name": "TreeNode",
    "fields": [{"name": "val", "type": "int"}],
    "links": [
        {"name": "left", "arity": "single"},
        {"name": "right", "arity": "single"},
    ],
}
LINKED_LIST_TEMPLATE = {
    "name": "ListNode",
    "fields": [{"name": "val", "type": "int"}],
    "links": [{"name": "next", "arity": "single"}],
}
GRAPH_TEMPLATE = {
    "name": "Node",
    "fields": [{"name": "val", "type": "int"}],
    "links": [{"name": "neighbors", "arity": "list"}],
}


# ---- shorthand → verbose -------------------------------------------------

def to_verbose(value: Any, *, shape: str, template: dict | None = None) -> dict:
    if shape == "verbose":
        return value
    fn = _SHAPES.get(shape)
    if fn is None:
        raise ValueError(f"Unknown input_shape: {shape!r}")
    return fn(value, template or _DEFAULT_TEMPLATE_FOR_SHAPE[shape])


def level_order_to_verbose(values: list, template: dict | None = None) -> dict:
    """Author a tree as a LeetCode-style level-order list with None for missing children."""
    return _tree_level_order(values, template or TREE_TEMPLATE)


def linked_list_to_verbose(values: list, template: dict | None = None) -> dict:
    """Author a singly-linked chain as a flat list of values."""
    return _linked_list_array(values, template or LINKED_LIST_TEMPLATE)


def adj_to_verbose(adj: dict, template: dict | None = None) -> dict:
    """Author a graph as an adjacency dict keyed by stringified node values."""
    return _graph_adjacency(adj, template or GRAPH_TEMPLATE)


def _linked_list_array(values: list, template: dict) -> dict:
    if not values:
        return {"nodes": [], "entry": None}
    field_name = template["fields"][0]["name"]
    link_name = template["links"][0]["name"]
    nodes = []
    for i, v in enumerate(values):
        next_id = i + 1 if i + 1 < len(values) else None
        nodes.append({"id": i, "fields": {field_name: v}, "links": {link_name: next_id}})
    return {"nodes": nodes, "entry": 0}


def _tree_level_order(values: list, template: dict) -> dict:
    if not values:
        return {"nodes": [], "entry": None}
    field_name = template["fields"][0]["name"]
    link_names = [link["name"] for link in template["links"]]
    if len(link_names) != 2:
        raise ValueError("tree_level_order requires exactly 2 links (e.g. left, right)")

    nodes = []
    id_for_pos = {}
    for pos, v in enumerate(values):
        if v is None:
            continue
        id_for_pos[pos] = len(nodes)
        nodes.append({
            "id": len(nodes),
            "fields": {field_name: v},
            "links": {link_names[0]: None, link_names[1]: None},
        })

    if 0 not in id_for_pos:
        return {"nodes": [], "entry": None}
    queue = [(0, id_for_pos[0])]
    cursor = 1
    while queue and cursor < len(values):
        _, parent_id = queue.pop(0)
        for link_name in link_names:
            if cursor >= len(values):
                break
            child_pos = cursor
            cursor += 1
            if values[child_pos] is None:
                continue
            child_id = id_for_pos[child_pos]
            nodes[parent_id]["links"][link_name] = child_id
            queue.append((child_pos, child_id))
    return {"nodes": nodes, "entry": 0}


def _graph_adjacency(adj: dict, template: dict) -> dict:
    field_name = template["fields"][0]["name"]
    link_name = template["links"][0]["name"]
    keys = list(adj.keys())
    id_for_key = {k: i for i, k in enumerate(keys)}
    nodes = []
    for i, k in enumerate(keys):
        try:
            val = int(k)
        except (TypeError, ValueError):
            val = k
        neighbor_ids = [id_for_key[str(n)] for n in adj[k] if str(n) in id_for_key]
        nodes.append({
            "id": i,
            "fields": {field_name: val},
            "links": {link_name: neighbor_ids},
        })
    return {"nodes": nodes, "entry": 0 if nodes else None}


_SHAPES = {
    "linked_list_array": _linked_list_array,
    "tree_level_order": _tree_level_order,
    "graph_adjacency": _graph_adjacency,
}
_DEFAULT_TEMPLATE_FOR_SHAPE = {
    "linked_list_array": LINKED_LIST_TEMPLATE,
    "tree_level_order": TREE_TEMPLATE,
    "graph_adjacency": GRAPH_TEMPLATE,
}


# ---- verbose → ergonomic node for REFERENCE bodies ---------------------
#
# REFERENCE solutions receive the verbose dict via build.py's
# `_invoke_reference(reference, deepcopy(input))`. To keep authoring
# concise, `inflate_tree` (and friends) hands back a node that supports
# BOTH attribute access (`n.left`) and item access (`n["left"]`) — some
# existing algorithms reach in via attributes, some via subscripts, and
# we don't want the migration to force a stylistic rewrite of every
# REFERENCE body.

class _DictNode(dict):
    """A dict whose top-level keys are also attribute-accessible."""

    __slots__ = ()

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError as e:
            raise AttributeError(name) from e


def inflate_tree(verbose: dict, *, field: str = "val", left: str = "left", right: str = "right"):
    """Verbose tree → recursive _DictNode (or None) supporting attr+item access."""
    if not verbose or verbose.get("entry") is None:
        return None
    by_id = {n["id"]: n for n in verbose["nodes"]}

    def build(nid):
        if nid is None:
            return None
        n = by_id[nid]
        return _DictNode({
            field: n["fields"].get(field),
            left: build(n["links"].get(left)),
            right: build(n["links"].get(right)),
        })

    return build(verbose["entry"])


def inflate_list(verbose: dict, *, field: str = "val", link: str = "next") -> list:
    """Verbose chain → flat list of node-field values, in chain order."""
    if not verbose or verbose.get("entry") is None:
        return []
    by_id = {n["id"]: n for n in verbose["nodes"]}
    out = []
    cur = verbose["entry"]
    seen = set()
    while cur is not None and cur not in seen:
        seen.add(cur)
        node = by_id[cur]
        out.append(node["fields"].get(field))
        cur = node["links"].get(link)
    return out


def inflate_graph(verbose: dict, *, field: str = "val", link: str = "neighbors") -> dict:
    """Verbose graph → adjacency dict {val_str: [neighbor_vals...]} mirroring authoring form."""
    if not verbose or verbose.get("entry") is None:
        return {}
    by_id = {n["id"]: n for n in verbose["nodes"]}
    out: dict[str, list] = {}
    for node in verbose["nodes"]:
        key = str(node["fields"].get(field))
        out[key] = [by_id[nid]["fields"].get(field) for nid in node["links"].get(link, [])]
    return out
