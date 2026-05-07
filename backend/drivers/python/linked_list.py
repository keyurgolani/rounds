"""Python linked_list driver — generic node primitive over chain layout.

Default node_template: {val} + {next}. Default input_shape: linked_list_array.
For variants (doubly-linked, random pointer), declare node_template + input_shape
on the entry."""
from __future__ import annotations

from drivers.python._node_codegen import emit_class, emit_inflate, emit_deflate


_DEFAULT_TEMPLATE = {
    "name": "ListNode",
    "fields": [{"name": "val", "type": "int"}],
    "links": [{"name": "next", "arity": "single"}],
}
_DEFAULT_SHAPE = "linked_list_array"
_SUPPORTED_OUTPUT_SHAPES = {"verbose", "linked_list_array"}


def validate(entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("name"), str) or not entry.get("name"):
        errors.append("missing 'name' (function to call)")
    if not isinstance(entry.get("params"), list):
        errors.append("missing 'params' (list of {name, type})")
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

    inflate_code = emit_inflate(template)
    deflate_code = emit_deflate(template)
    cls_code = emit_class(template)

    node_param_names = [p["name"] for p in params if p.get("type") == "node"]

    return f"""
{cls_code}
{inflate_code}
{deflate_code}

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
        if _shape == "verbose" or isinstance(v, dict) and 'nodes' in v:
            kwargs[_name] = _inflate(v)
        else:
            kwargs[_name] = _inflate(_to_verbose(v, _shape, _template))
    out = fn(**kwargs)
    if isinstance(out, {template["name"]}) or out is None:
        verbose = _deflate(out)
        return _to_shape(verbose, _output_shape, _template)
    return out


def _to_verbose(value, shape, template):
    # Inline shorthand interpreter — the wrapper subprocess doesn't
    # have drivers/_shorthand.py on its path, so we inline just the
    # shape this kind cares about. Variants beyond this default ship
    # input_shape='verbose' and pass verbose JSON directly.
    if shape == "linked_list_array":
        if not value: return {{"nodes": [], "entry": None}}
        f_name = template["fields"][0]["name"]
        l_name = template["links"][0]["name"]
        return {{
            "nodes": [
                {{"id": i, "fields": {{f_name: v}},
                  "links": {{l_name: i + 1 if i + 1 < len(value) else None}}}}
                for i, v in enumerate(value)
            ],
            "entry": 0,
        }}
    raise ValueError(f"shorthand shape not supported in linked_list driver runtime: {{shape}}")


def _to_shape(verbose, output_shape, template):
    # Forward transform: deflated verbose form -> requested output shape.
    # 'verbose' is the backward-compatible pass-through.
    if output_shape == "verbose":
        return verbose
    if output_shape == "linked_list_array":
        if not verbose or verbose.get("entry") is None:
            return []
        f_name = template["fields"][0]["name"]
        l_name = template["links"][0]["name"]
        by_id = {{n["id"]: n for n in verbose["nodes"]}}
        out = []
        cur = verbose["entry"]
        seen = set()
        while cur is not None and cur not in seen:
            seen.add(cur)
            node = by_id[cur]
            out.append(node["fields"][f_name])
            cur = node["links"].get(l_name)
        return out
    raise ValueError(f"unsupported output shape in linked_list driver: {{output_shape}}")
"""
