"""JavaScript linked_list driver."""
from __future__ import annotations

import json

from drivers.javascript._node_codegen import emit_class, emit_inflate, emit_deflate


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

function _to_verbose(value, shape, template) {{
  if (shape === "linked_list_array") {{
    if (!value || value.length === 0) return {{nodes: [], entry: null}};
    const f = template.fields[0].name;
    const l = template.links[0].name;
    return {{
      nodes: value.map((v, i) => ({{
        id: i, fields: {{ [f]: v }},
        links: {{ [l]: (i + 1 < value.length) ? i + 1 : null }}
      }})),
      entry: 0
    }};
  }}
  throw new Error("shorthand shape not supported in linked_list runtime: " + shape);
}}

function _to_shape(verbose, outputShape, template) {{
  if (outputShape === "verbose") return verbose;
  if (outputShape === "linked_list_array") {{
    if (!verbose || verbose.entry == null) return [];
    const f = template.fields[0].name;
    const l = template.links[0].name;
    const byId = new Map(verbose.nodes.map(n => [n.id, n]));
    const out = [];
    const seen = new Set();
    let cur = verbose.entry;
    while (cur != null && !seen.has(cur)) {{
      seen.add(cur);
      const node = byId.get(cur);
      out.push(node.fields[f]);
      cur = node.links[l];
    }}
    return out;
  }}
  throw new Error("unsupported output shape in linked_list driver: " + outputShape);
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
    if (shape === "verbose") {{
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
