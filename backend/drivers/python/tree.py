"""Python tree driver — generic node primitive over tree layout.

Inputs MUST arrive in canonical verbose form
    {"nodes": [{"id": int, "fields": {...}, "links": {...}}], "entry": id|None}
Legacy shapes such as `tree_level_order` are a build-time authoring
convenience (see `pocketbase/seeds/builder/_shorthand.py`) and are
rejected at runtime so violations surface during seed build.

Output is the user's TreeNode return value, deflated to verbose and then
optionally reshaped per `output_shape`."""
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
    input_shape = entry.get("input_shape", "verbose")
    if input_shape != "verbose":
        errors.append(
            f"unsupported input_shape {input_shape!r}; tree inputs must be authored as "
            f"verbose JSON (use builder._shorthand.level_order_to_verbose at build time)"
        )
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
    _template = {template!r}
    _output_shape = {output_shape!r}
    for _name in _node_params:
        v = kwargs.get(_name)
        if v is None:
            continue
        if not (isinstance(v, dict) and 'nodes' in v and 'entry' in v):
            raise TypeError(
                "tree driver expected verbose JSON {{'nodes': [...], 'entry': id}} for "
                "param " + repr(_name) + "; got " + type(v).__name__
            )
        kwargs[_name] = _inflate(v)
    out = fn(**kwargs)
    if isinstance(out, {template["name"]}) or out is None:
        return _to_shape(_deflate(out), _output_shape, _template)
    return out


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
