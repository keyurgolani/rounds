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
    return errors


def wrapper_snippet(entry: dict) -> str:
    name = entry["name"]
    params = entry["params"]
    template = entry.get("node_template", _DEFAULT_TEMPLATE)
    shape = entry.get("input_shape", _DEFAULT_SHAPE)

    inflate_code = emit_inflate(template)
    deflate_code = emit_deflate(template)
    cls_code = emit_class(template)

    node_param_names = [p["name"] for p in params if p.get("type") == "node"]
    # Python-literal repr for embedding into Python source — JSON's
    # true/false/null aren't valid Python tokens.
    template_repr = repr(template)
    shape_repr = repr(shape)

    return f"""
{cls_code}
{inflate_code}
{deflate_code}

def _drive(input):
    fn = globals()[{name!r}]
    kwargs = dict(input)
    _node_params = {node_param_names!r}
    _shape = {shape_repr}
    _template = {template_repr}
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
        return _deflate(out)
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
"""
