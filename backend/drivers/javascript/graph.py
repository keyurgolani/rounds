"""JavaScript graph driver."""
from __future__ import annotations

import json

from drivers.javascript._node_codegen import emit_class, emit_inflate, emit_deflate


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

function _to_verbose(adj, shape, template) {{
  if (shape === "graph_adjacency") {{
    const f = template.fields[0].name;
    const l = template.links[0].name;
    const keys = Object.keys(adj);
    const idForKey = {{}};
    keys.forEach((k, i) => {{ idForKey[k] = i; }});
    const nodes = keys.map((k, i) => {{
      const val = isNaN(parseInt(k)) ? k : parseInt(k);
      const neighborIds = adj[k]
        .filter(n => idForKey[String(n)] !== undefined)
        .map(n => idForKey[String(n)]);
      return {{id: i, fields: {{[f]: val}}, links: {{[l]: neighborIds}}}};
    }});
    return {{nodes, entry: nodes.length ? 0 : null}};
  }}
  throw new Error("unsupported graph shape: " + shape);
}}

function _to_shape(verbose, outputShape, template) {{
  if (outputShape === "verbose") return verbose;
  if (outputShape === "graph_adjacency") {{
    const f = template.fields[0].name;
    const l = template.links[0].name;
    const byId = new Map((verbose.nodes || []).map(n => [n.id, n]));
    const out = {{}};
    for (const node of (verbose.nodes || [])) {{
      const key = String(node.fields[f]);
      out[key] = (node.links[l] || [])
        .filter(id => byId.has(id))
        .map(id => byId.get(id).fields[f]);
    }}
    return out;
  }}
  throw new Error("unsupported output shape in graph driver: " + outputShape);
}}

function _drive(input) {{
  const fn = eval({json.dumps(name)});
  const kwargs = {{...input}};
  const nodeParams = {json.dumps(node_param_names)};
  const shape = {json.dumps(shape)};
  const template = {json.dumps(template)};
  const outputShape = {json.dumps(output_shape)};
  for (const p of nodeParams) {{
    const v = kwargs[p];
    if (v == null) continue;
     if (shape === "verbose" || (v && typeof v === "object" && "nodes" in v)) kwargs[p] = _inflate(v);
     else kwargs[p] = _inflate(_to_verbose(v, shape, template));
  }}
  const out = fn(...Object.values(kwargs));
  if (out instanceof {template["name"]} || out === null) {{
    return _to_shape(_deflate(out), outputShape, template);
  }}
  return out;
}}
"""
