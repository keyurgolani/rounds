"""Python graph driver — generic node primitive over general layout."""
from __future__ import annotations

from drivers.python._node_codegen import emit_class, emit_inflate, emit_deflate


_DEFAULT_TEMPLATE = {
    "name": "Node",
    "fields": [{"name": "val", "type": "int"}],
    "links": [{"name": "neighbors", "arity": "list"}],
}
_DEFAULT_SHAPE = "graph_adjacency"


def validate(entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("name"), str) or not entry.get("name"):
        errors.append("missing 'name'")
    if not isinstance(entry.get("params"), list):
        errors.append("missing 'params'")
    return errors


def wrapper_snippet(entry: dict) -> str:
    name = entry["name"]
    params = entry["params"]
    template = entry.get("node_template", _DEFAULT_TEMPLATE)
    shape = entry.get("input_shape", _DEFAULT_SHAPE)

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
"""
