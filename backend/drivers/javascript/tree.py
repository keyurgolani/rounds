"""JavaScript tree driver."""
from __future__ import annotations

import json

from drivers.javascript._node_codegen import emit_class, emit_inflate, emit_deflate


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

function _to_verbose(values, shape, template) {{
  if (shape === "tree_level_order") {{
    if (!values || values.length === 0) return {{nodes: [], entry: null}};
    const f = template.fields[0].name;
    const lNames = template.links.map(l => l.name);
    const nodes = [];
    const idForPos = {{}};
    for (let pos = 0; pos < values.length; pos++) {{
      const v = values[pos];
      if (v === null || v === undefined) continue;
      idForPos[pos] = nodes.length;
      const linkInit = {{}};
      for (const ln of lNames) linkInit[ln] = null;
      nodes.push({{ id: nodes.length, fields: {{ [f]: v }}, links: linkInit }});
    }}
    if (!(0 in idForPos)) return {{nodes: [], entry: null}};
    const queue = [[0, idForPos[0]]];
    let cursor = 1;
    while (queue.length && cursor < values.length) {{
      const [, parentId] = queue.shift();
      for (const ln of lNames) {{
        if (cursor >= values.length) break;
        const childPos = cursor++;
        if (values[childPos] === null || values[childPos] === undefined) continue;
        const childId = idForPos[childPos];
        nodes[parentId].links[ln] = childId;
        queue.push([childPos, childId]);
      }}
    }}
    return {{ nodes, entry: 0 }};
  }}
  throw new Error("unsupported tree shape: " + shape);
}}

function _to_shape(verbose, outputShape, template) {{
  if (outputShape === "verbose") return verbose;
  if (outputShape === "tree_level_order") {{
    if (!verbose || verbose.entry == null) return [];
    const f = template.fields[0].name;
    const lNames = template.links.map(l => l.name);
    const byId = new Map(verbose.nodes.map(n => [n.id, n]));
    const out = [];
    const q = [verbose.entry];
    while (q.length) {{
      const cur = q.shift();
      if (cur == null) {{ out.push(null); continue; }}
      const node = byId.get(cur);
      out.push(node.fields[f]);
      for (const ln of lNames) {{
        const child = node.links[ln];
        q.push(child);
      }}
    }}
    while (out.length && out[out.length - 1] === null) out.pop();
    return out;
  }}
  throw new Error("unsupported output shape in tree driver: " + outputShape);
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
     if (shape === "verbose" || (v && typeof v === "object" && "nodes" in v)) {{
       kwargs[p] = _inflate(v);
     }} else {{
       kwargs[p] = _inflate(_to_verbose(v, shape, template));
     }}
  }}
  const out = fn(...Object.values(kwargs));
  if (out instanceof {template["name"]} || out === null) {{
    return _to_shape(_deflate(out), outputShape, template);
  }}
  return out;
}}
"""
