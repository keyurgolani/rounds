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

function _to_verbose(values, shape, template) {{
  if (shape === "tree_level_order") {{
    if (!values || values.length === 0) return {{nodes: [], entry: null}};
    const f = template.fields[0].name;
    const links = template.links.map(l => l.name);
    const nodes = [];
    const idForPos = {{}};
    for (let pos = 0; pos < values.length; pos++) {{
      if (values[pos] === null) continue;
      idForPos[pos] = nodes.length;
      const linkInit = {{}};
      for (const ln of links) linkInit[ln] = null;
      nodes.push({{id: nodes.length, fields: {{[f]: values[pos]}}, links: linkInit}});
    }}
    if (idForPos[0] === undefined) return {{nodes: [], entry: null}};
    const queue = [[0, idForPos[0]]];
    let cursor = 1;
    while (queue.length && cursor < values.length) {{
      const [, parentId] = queue.shift();
      for (const ln of links) {{
        if (cursor >= values.length) break;
        const childPos = cursor++;
        if (values[childPos] === null) continue;
        const childId = idForPos[childPos];
        nodes[parentId].links[ln] = childId;
        queue.push([childPos, childId]);
      }}
    }}
    return {{nodes, entry: 0}};
  }}
  throw new Error("unsupported tree shape: " + shape);
}}

function _drive(input) {{
  const fn = eval({json.dumps(name)});
  const kwargs = {{...input}};
  const nodeParams = {json.dumps(node_param_names)};
  const shape = {json.dumps(shape)};
  const template = {json.dumps(template)};
  for (const p of nodeParams) {{
    const v = kwargs[p];
    if (v == null) continue;
    if (shape === "verbose") kwargs[p] = _inflate(v);
    else kwargs[p] = _inflate(_to_verbose(v, shape, template));
  }}
  const out = fn(...Object.values(kwargs));
  if (out instanceof {template["name"]} || out === null) return _deflate(out);
  return out;
}}
"""
