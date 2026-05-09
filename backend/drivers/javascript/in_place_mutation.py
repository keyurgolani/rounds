"""JavaScript in_place_mutation driver.

Same dict-arg-ordering caveat as the `function` driver: when params
are declared, bind by name in declaration order; otherwise fall back
to `Object.values(input)`. The Python twin uses `fn(**input)` and is
already order-agnostic.
"""
from __future__ import annotations

import json


def validate(entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("name"), str) or not entry.get("name"):
        errors.append("missing 'name' (function to call)")
    if not isinstance(entry.get("mutates"), str) or not entry.get("mutates"):
        errors.append("missing 'mutates' (param name that is mutated in place)")
    return errors


def wrapper_snippet(entry: dict) -> str:
    name_js = json.dumps(entry["name"])
    mutates_js = json.dumps(entry["mutates"])
    params = entry.get("params") or []
    param_names = [p["name"] for p in params if isinstance(p, dict) and p.get("name")]
    param_names_js = json.dumps(param_names)
    return f"""
function _drive(input) {{
  const fn = eval({name_js});
  const _params = {param_names_js};
  if (!input || typeof input !== 'object' || Array.isArray(input)) {{
    throw new Error("in_place_mutation input must be an object of params");
  }}
  if (_params.length > 0) {{
    fn(..._params.map(k => input[k]));
  }} else {{
    fn(...Object.values(input));
  }}
  return input[{mutates_js}];
}}
"""
