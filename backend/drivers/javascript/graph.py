"""JavaScript graph driver — verbose-only inputs at runtime."""
from __future__ import annotations

import json

from drivers.javascript._node_codegen import emit_class, emit_inflate, emit_deflate


_DEFAULT_TEMPLATE = {
    "name": "Node",
    "fields": [{"name": "val", "type": "int"}],
    "links": [{"name": "neighbors", "arity": "list"}],
}
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
    input_shape = entry.get("input_shape", "verbose")
    if input_shape != "verbose":
        errors.append(
            f"unsupported input_shape {input_shape!r}; graph inputs must be authored as "
            f"verbose JSON (use builder._shorthand.adj_to_verbose at build time)"
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

function _to_shape(verbose, outputShape, template) {{
  if (outputShape === "verbose") return verbose;
  if (outputShape === "graph_adjacency") {{
    const f = template.fields[0].name;
    const ln = template.links[0].name;
    const nodes = (verbose && verbose.nodes) || [];
    const byId = new Map(nodes.map(n => [n.id, n]));
    const out = {{}};
    for (const node of nodes) {{
      const key = String(node.fields[f]);
      out[key] = (node.links[ln] || [])
        .filter(nid => byId.has(nid))
        .map(nid => byId.get(nid).fields[f]);
    }}
    return out;
  }}
  throw new Error("unsupported output shape in graph driver: " + outputShape);
}}

function _drive(input) {{
  const fn = eval({json.dumps(name)});
  const kwargs = {{...input}};
  const nodeParams = {json.dumps(node_param_names)};
  const template = {json.dumps(template)};
  const outputShape = {json.dumps(output_shape)};
  for (const p of nodeParams) {{
    const v = kwargs[p];
    if (v == null) continue;
    if (!(v && typeof v === "object" && "nodes" in v && "entry" in v)) {{
      throw new TypeError(
        "graph driver expected verbose JSON {{nodes: [...], entry: id}} for param " +
        JSON.stringify(p) + "; got " + (Array.isArray(v) ? "array" : typeof v)
      );
    }}
    kwargs[p] = _inflate(v);
  }}
  const out = fn(...Object.values(kwargs));
  if (out instanceof {template["name"]} || out === null) {{
    return _to_shape(_deflate(out), outputShape, template);
  }}
  return out;
}}
"""
