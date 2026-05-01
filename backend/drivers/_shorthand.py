"""Shorthand -> verbose JSON conversion for node-shaped inputs.

Verbose form is canonical: {"nodes": [{"id": int, "fields": {...},
"links": {<link_name>: <id|null|[ids]>}}], "entry": <id|null>}.

Each shape is a thin transformation; the per-language driver receives
verbose JSON and walks it to construct Node instances."""
from __future__ import annotations

from typing import Any


def to_verbose(value: Any, *, shape: str, template: dict) -> dict:
    if shape == "verbose":
        return value
    fn = _SHAPES.get(shape)
    if fn is None:
        raise ValueError(f"Unknown input_shape: {shape!r}")
    return fn(value, template)


def _linked_list_array(values: list, template: dict) -> dict:
    if not values:
        return {"nodes": [], "entry": None}
    field_name = template["fields"][0]["name"]
    link_name = template["links"][0]["name"]  # singly-linked: one link
    nodes = []
    for i, v in enumerate(values):
        next_id = i + 1 if i + 1 < len(values) else None
        nodes.append({"id": i, "fields": {field_name: v}, "links": {link_name: next_id}})
    return {"nodes": nodes, "entry": 0}


def _tree_level_order(values: list, template: dict) -> dict:
    if not values:
        return {"nodes": [], "entry": None}
    field_name = template["fields"][0]["name"]
    link_names = [link["name"] for link in template["links"]]  # e.g. ["left", "right"]
    if len(link_names) != 2:
        raise ValueError("tree_level_order requires exactly 2 links (e.g. left, right)")

    # Build only the non-None positions as actual nodes; track parent chain.
    nodes = []
    id_for_pos = {}  # position-in-input -> node id
    for pos, v in enumerate(values):
        if v is None:
            continue
        id_for_pos[pos] = len(nodes)
        nodes.append({"id": len(nodes), "fields": {field_name: v},
                      "links": {link_names[0]: None, link_names[1]: None}})

    # Walk with a queue: each non-None node consumes the next two
    # positions in the input (its children, possibly None).
    if 0 not in id_for_pos:
        return {"nodes": [], "entry": None}
    queue = [(0, id_for_pos[0])]  # (input_position, node_id)
    cursor = 1
    while queue and cursor < len(values):
        _, parent_id = queue.pop(0)
        for slot, link_name in enumerate(link_names):
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
        # Try to coerce key to int (json shorthand uses string keys).
        try:
            val = int(k)
        except (TypeError, ValueError):
            val = k
        neighbor_ids = []
        for n in adj[k]:
            n_key = str(n)
            if n_key in id_for_key:
                neighbor_ids.append(id_for_key[n_key])
        nodes.append({"id": i, "fields": {field_name: val},
                      "links": {link_name: neighbor_ids}})
    return {"nodes": nodes, "entry": 0 if nodes else None}


_SHAPES = {
    "linked_list_array": _linked_list_array,
    "tree_level_order": _tree_level_order,
    "graph_adjacency": _graph_adjacency,
}
