"""Python graph driver — generic node primitive over general layout."""
from __future__ import annotations

from drivers.python._node_codegen import emit_class, emit_inflate, emit_deflate


_DEFAULT_TEMPLATE = {
    "name": "Node",
    "fields": [{"name": "val", "type": "int"}],
    "links": [{"name": "neighbors", "arity": "list"}],
}
_DEFAULT_SHAPE = "graph_adjacency"
_SUPPORTED_OUTPUT_SHAPES = {"verbose", "graph_adjacency"}


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
        return _to_shape(_deflate(out), _output_shape, _template)
    return out


def _to_verbose(adj, shape, template):
    if shape == "graph_adjacency":
        f_name = template["fields"][0]["name"]
        l_name = template["links"][0]["name"]
        keys = list(adj.keys())
        id_for_key = {{k: i for i, k in enumerate(keys)}}
        nodes = []
        for i, k in enumerate(keys):
            try:
                val = int(k)
            except (TypeError, ValueError):
                val = k
            neighbor_ids = [id_for_key[str(n)] for n in adj[k] if str(n) in id_for_key]
            nodes.append({{"id": i, "fields": {{f_name: val}}, "links": {{l_name: neighbor_ids}}}})
        return {{"nodes": nodes, "entry": 0 if nodes else None}}
    raise ValueError(f"unsupported graph shape: {{shape}}")


def _to_shape(verbose, output_shape, template):
    if output_shape == "verbose":
        return verbose
    if output_shape == "graph_adjacency":
        f_name = template["fields"][0]["name"]
        l_name = template["links"][0]["name"]
        by_id = {{n["id"]: n for n in verbose.get("nodes", [])}}
        out = {{}}
        for node in verbose.get("nodes", []):
            key = str(node["fields"][f_name])
            out[key] = [by_id[nid]["fields"][f_name] for nid in node["links"].get(l_name, []) if nid in by_id]
        return out
    raise ValueError(f"unsupported output shape in graph driver: {{output_shape}}")
"""
