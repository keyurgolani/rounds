"""Python tree driver — generic node primitive over tree layout.

Default node_template: {val} + {left, right}. Default input_shape:
tree_level_order. For n-ary trees, override links to {children: list}
and input_shape to nary_tree_level_order (or use verbose)."""
from __future__ import annotations

from drivers.python._node_codegen import emit_class, emit_inflate, emit_deflate


_DEFAULT_TEMPLATE = {
    "name": "TreeNode",
    "fields": [{"name": "val", "type": "int"}],
    "links": [
        {"name": "left", "arity": "single"},
        {"name": "right", "arity": "single"},
    ],
}
_DEFAULT_SHAPE = "tree_level_order"
_SUPPORTED_OUTPUT_SHAPES = {"verbose", "tree_level_order"}


def validate(entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("name"), str) or not entry.get("name"):
        errors.append("missing 'name'")
    if not isinstance(entry.get("params"), list):
        errors.append("missing 'params'")
    template = entry.get("node_template", _DEFAULT_TEMPLATE)
    if not isinstance(template.get("fields"), list) or not template.get("fields"):
        errors.append("node_template must declare at least one field")
    if not isinstance(template.get("links"), list) or not template.get("links"):
        errors.append("node_template must declare at least one link")
    output_shape = entry.get("output_shape", "verbose")
    if output_shape not in _SUPPORTED_OUTPUT_SHAPES:
        errors.append(
            f"unsupported output_shape {output_shape!r}; "
            f"must be one of {sorted(_SUPPORTED_OUTPUT_SHAPES)}"
        )
    return errors


def wrapper_snippet(entry: dict) -> str:
    name = entry["name"]
    params = entry["params"]
    template = entry.get("node_template", _DEFAULT_TEMPLATE)
    shape = entry.get("input_shape", _DEFAULT_SHAPE)
    output_shape = entry.get("output_shape", "verbose")

    cls_code = emit_class(template)
    inflate_code = emit_inflate(template)
    deflate_code = emit_deflate(template)

    node_param_names = [p["name"] for p in params if p.get("type") == "node"]

    return f"""
{cls_code}
{inflate_code}
{deflate_code}

from collections import deque

def _drive(input):
    fn = globals()[{name!r}]
    kwargs = dict(input)
    _node_params = {node_param_names!r}
    _shape = {shape!r}
    _template = {template!r}
    _output_shape = {output_shape!r}
    for _name in _node_params:
        v = kwargs.get(_name)
        if v is None:
            continue
        if _shape == "verbose":
            kwargs[_name] = _inflate(v)
        else:
            kwargs[_name] = _inflate(_to_verbose(v, _shape, _template))
    out = fn(**kwargs)
    if isinstance(out, {template["name"]}) or out is None:
        return _to_shape(_deflate(out), _output_shape, _template)
    return out


def _to_verbose(values, shape, template):
    if shape == "tree_level_order":
        if not values: return {{"nodes": [], "entry": None}}
        f_name = template["fields"][0]["name"]
        l_names = [link["name"] for link in template["links"]]
        nodes = []
        id_for_pos = {{}}
        for pos, v in enumerate(values):
            if v is None: continue
            id_for_pos[pos] = len(nodes)
            link_init = {{ln: None for ln in l_names}}
            nodes.append({{"id": len(nodes), "fields": {{f_name: v}}, "links": link_init}})
        if 0 not in id_for_pos:
            return {{"nodes": [], "entry": None}}
        queue = [(0, id_for_pos[0])]
        cursor = 1
        while queue and cursor < len(values):
            _, parent_id = queue.pop(0)
            for ln in l_names:
                if cursor >= len(values): break
                child_pos = cursor
                cursor += 1
                if values[child_pos] is None: continue
                child_id = id_for_pos[child_pos]
                nodes[parent_id]["links"][ln] = child_id
                queue.append((child_pos, child_id))
        return {{"nodes": nodes, "entry": 0}}
    raise ValueError(f"unsupported tree shape: {{shape}}")


def _to_shape(verbose, output_shape, template):
    if output_shape == "verbose":
        return verbose
    if output_shape == "tree_level_order":
        if not verbose or verbose.get("entry") is None:
            return []
        f_name = template["fields"][0]["name"]
        l_names = [link["name"] for link in template["links"]]
        by_id = {{n["id"]: n for n in verbose["nodes"]}}
        out = []
        q = deque([verbose["entry"]])
        while q:
            cur = q.popleft()
            if cur is None:
                out.append(None)
                continue
            node = by_id[cur]
            out.append(node["fields"][f_name])
            for ln in l_names:
                child = node["links"].get(ln)
                q.append(child)
        # LeetCode convention: trim trailing nulls.
        while out and out[-1] is None:
            out.pop()
        return out
    raise ValueError(f"unsupported output shape in tree driver: {{output_shape}}")
"""
