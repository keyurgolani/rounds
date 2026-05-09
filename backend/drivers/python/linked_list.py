"""Python linked_list driver — generic node primitive over chain layout.

Inputs MUST arrive in canonical verbose form. Legacy `linked_list_array`
shorthand is a build-time authoring convenience (see
pocketbase/seeds/builder/_shorthand.py) and is rejected at runtime."""
from __future__ import annotations

from drivers.python._node_codegen import emit_class, emit_inflate, emit_deflate


_DEFAULT_TEMPLATE = {
    "name": "ListNode",
    "fields": [{"name": "val", "type": "int"}],
    "links": [{"name": "next", "arity": "single"}],
}
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
    input_shape = entry.get("input_shape", "verbose")
    if input_shape != "verbose":
        errors.append(
            f"unsupported input_shape {input_shape!r}; linked_list inputs must be authored "
            f"as verbose JSON (use builder._shorthand.linked_list_to_verbose at build time)"
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
    _template = {template!r}
    _output_shape = {output_shape!r}
    for _name in _node_params:
        v = kwargs.get(_name)
        if v is None:
            continue
        if not (isinstance(v, dict) and 'nodes' in v and 'entry' in v):
            raise TypeError(
                "linked_list driver expected verbose JSON {{'nodes': [...], 'entry': id}} "
                "for param " + repr(_name) + "; got " + type(v).__name__
            )
        kwargs[_name] = _inflate(v)
    out = fn(**kwargs)
    if isinstance(out, {template["name"]}) or out is None:
        verbose = _deflate(out)
        return _to_shape(verbose, _output_shape, _template)
    return out


def _to_shape(verbose, output_shape, template):
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
