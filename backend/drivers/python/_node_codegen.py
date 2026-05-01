"""Python source-code generator for node templates.

Three emit functions, called by the per-kind drivers (linked_list,
tree, graph) when they build their wrapper snippets.

  emit_class(template)   -> the user-facing Node class declaration.
  emit_inflate(template) -> a `_inflate(verbose) -> root_node` helper.
  emit_deflate(template) -> a `_deflate(node) -> verbose` helper.

The generated functions reference the template's field/link names; the
arity ('single' vs 'list') controls how links are walked."""
from __future__ import annotations


def emit_class(template: dict) -> str:
    name = template["name"]
    fields = template.get("fields", [])
    links = template.get("links", [])

    args = []
    body = []
    for f in fields:
        args.append(f"{f['name']}=0")
        body.append(f"        self.{f['name']} = {f['name']}")
    for link in links:
        if link["arity"] == "single":
            args.append(f"{link['name']}=None")
            body.append(f"        self.{link['name']} = {link['name']}")
        elif link["arity"] == "list":
            args.append(f"{link['name']}=None")
            body.append(
                f"        self.{link['name']} = "
                f"{link['name']} if {link['name']} is not None else []"
            )
        else:
            raise ValueError(f"unknown link arity: {link['arity']!r}")

    args_str = ", ".join(args) if args else ""
    body_str = "\n".join(body) if body else "        pass"
    return f"""
class {name}:
    def __init__(self, {args_str}):
{body_str}
"""


def emit_inflate(template: dict) -> str:
    name = template["name"]
    fields = template.get("fields", [])
    links = template.get("links", [])

    field_assigns = []
    for f in fields:
        field_assigns.append(f"            {f['name']}=_n.get('fields', {{}}).get({f['name']!r})")

    return f"""
def _inflate(verbose):
    if not verbose or verbose.get('entry') is None:
        return None
    by_id = {{}}
    for _n in verbose['nodes']:
        by_id[_n['id']] = {name}(
{','.join(field_assigns) if field_assigns else ''}
        )
    for _n in verbose['nodes']:
        _inst = by_id[_n['id']]
        _links = _n.get('links') or {{}}
{_emit_inflate_link_assigns(links)}
    return by_id[verbose['entry']]
"""


def _emit_inflate_link_assigns(links: list) -> str:
    out = []
    for link in links:
        if link["arity"] == "single":
            out.append(
                f"        _ref = _links.get({link['name']!r})\n"
                f"        _inst.{link['name']} = by_id.get(_ref) if _ref is not None else None"
            )
        elif link["arity"] == "list":
            out.append(
                f"        _refs = _links.get({link['name']!r}) or []\n"
                f"        _inst.{link['name']} = [by_id.get(_r) for _r in _refs if _r is not None]"
            )
    return "\n".join(out)


def emit_deflate(template: dict) -> str:
    fields = template.get("fields", [])
    links = template.get("links", [])
    field_names = [f["name"] for f in fields]
    return f"""
def _deflate(root):
    if root is None:
        return {{'nodes': [], 'entry': None}}
    id_of = {{}}
    order = []
    def _walk(n):
        if id(n) in id_of or n is None:
            return
        id_of[id(n)] = len(order)
        order.append(n)
{_emit_deflate_walk_links(links)}
    _walk(root)
    out = []
    for i, n in enumerate(order):
        out.append({{
            'id': i,
            'fields': {{ {", ".join(f"{f!r}: getattr(n, {f!r}, None)" for f in field_names)} }},
            'links': {{
{_emit_deflate_link_serializers(links)}
            }},
        }})
    return {{'nodes': out, 'entry': 0}}
"""


def _emit_deflate_walk_links(links: list) -> str:
    out = []
    for link in links:
        if link["arity"] == "single":
            out.append(f"        _walk(getattr(n, {link['name']!r}, None))")
        elif link["arity"] == "list":
            out.append(
                f"        for _c in getattr(n, {link['name']!r}, None) or []:\n"
                f"            _walk(_c)"
            )
    return "\n".join(out)


def _emit_deflate_link_serializers(links: list) -> str:
    parts = []
    for link in links:
        if link["arity"] == "single":
            parts.append(
                f"                {link['name']!r}: id_of.get(id(getattr(n, {link['name']!r}, None))) "
                f"if getattr(n, {link['name']!r}, None) is not None else None,"
            )
        elif link["arity"] == "list":
            parts.append(
                f"                {link['name']!r}: [id_of[id(_c)] for _c in "
                f"(getattr(n, {link['name']!r}, None) or [])],"
            )
    return "\n".join(parts)
