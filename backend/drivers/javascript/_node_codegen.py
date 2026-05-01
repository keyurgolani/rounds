"""JavaScript source-code generator for node templates."""
from __future__ import annotations

import json


def emit_class(template: dict) -> str:
    name = template["name"]
    fields = template.get("fields", [])
    links = template.get("links", [])

    init_args = []
    init_body = []
    for f in fields:
        init_args.append(f"{f['name']} = 0")
        init_body.append(f"    this.{f['name']} = {f['name']};")
    for link in links:
        if link["arity"] == "single":
            init_args.append(f"{link['name']} = null")
            init_body.append(f"    this.{link['name']} = {link['name']};")
        elif link["arity"] == "list":
            init_args.append(f"{link['name']} = null")
            init_body.append(
                f"    this.{link['name']} = {link['name']} || [];"
            )
        else:
            raise ValueError(f"unknown link arity: {link['arity']!r}")

    return f"""
class {name} {{
  constructor({', '.join(init_args)}) {{
{chr(10).join(init_body)}
  }}
}}
"""


def emit_inflate(template: dict) -> str:
    name = template["name"]
    fields = template.get("fields", [])
    links = template.get("links", [])
    field_lookups = ", ".join(
        f"(_n.fields && _n.fields[{json.dumps(f['name'])}]) ?? 0" for f in fields
    )
    link_assigns = []
    for link in links:
        ln = json.dumps(link["name"])
        if link["arity"] == "single":
            link_assigns.append(
                f"      {{\n"
                f"        const _ref = _n.links && _n.links[{ln}];\n"
                f"        _inst[{ln}] = (_ref != null) ? byId.get(_ref) : null;\n"
                f"      }}"
            )
        elif link["arity"] == "list":
            link_assigns.append(
                f"      {{\n"
                f"        const _refs = (_n.links && _n.links[{ln}]) || [];\n"
                f"        _inst[{ln}] = _refs.filter(r => r != null).map(r => byId.get(r));\n"
                f"      }}"
            )

    return f"""
function _inflate(verbose) {{
  if (!verbose || verbose.entry == null) return null;
  const byId = new Map();
  for (const _n of verbose.nodes) {{
    byId.set(_n.id, new {name}({field_lookups}));
  }}
  for (const _n of verbose.nodes) {{
    const _inst = byId.get(_n.id);
{chr(10).join(link_assigns)}
  }}
  return byId.get(verbose.entry);
}}
"""


def emit_deflate(template: dict) -> str:
    fields = template.get("fields", [])
    links = template.get("links", [])
    field_serializers = ", ".join(
        f"{json.dumps(f['name'])}: n[{json.dumps(f['name'])}]" for f in fields
    )
    link_walks = []
    link_serializers = []
    for link in links:
        ln = json.dumps(link["name"])
        if link["arity"] == "single":
            link_walks.append(f"    _walk(n[{ln}]);")
            link_serializers.append(
                f"      {ln}: (n[{ln}] != null) ? idOf.get(n[{ln}]) : null,"
            )
        elif link["arity"] == "list":
            link_walks.append(f"    for (const _c of (n[{ln}] || [])) _walk(_c);")
            link_serializers.append(
                f"      {ln}: ((n[{ln}] || []).map(_c => idOf.get(_c))),"
            )

    return f"""
function _deflate(root) {{
  if (root == null) return {{nodes: [], entry: null}};
  const idOf = new Map();
  const order = [];
  function _walk(n) {{
    if (n == null || idOf.has(n)) return;
    idOf.set(n, order.length);
    order.push(n);
{chr(10).join(link_walks)}
  }}
  _walk(root);
  const nodes = order.map((n, i) => ({{
    id: i,
    fields: {{ {field_serializers} }},
    links: {{
{chr(10).join(link_serializers)}
    }},
  }}));
  return {{nodes, entry: 0}};
}}
"""
