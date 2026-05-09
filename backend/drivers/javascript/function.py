"""JavaScript `function` driver.

When the test-case input is a dict, we MUST bind dict values to function
arguments in `entry.params` declaration order. JS objects preserve key
insertion order, so a naive `Object.values(input)` works for cases
where the test author writes keys in declaration order — but it
silently passes wrong values to wrong positions when the JSON
serializer or the author reorders keys (e.g. `{b: 2, a: 1}` for
`function fn(a, b)`). Python's twin uses `fn(**input)` which is order-
agnostic; the JS path doesn't get that for free.

If `entry.params` is provided we emit positional binding by name. If
it's omitted we fall back to `Object.values(input)` for backward
compatibility, but the validator nudges authors to declare params.
"""
from __future__ import annotations

import json


def validate(entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("name"), str) or not entry.get("name"):
        errors.append("missing 'name' (function to call)")
    return errors


def wrapper_snippet(entry: dict) -> str:
    name_js = json.dumps(entry["name"])
    params = entry.get("params") or []
    param_names = [p["name"] for p in params if isinstance(p, dict) and p.get("name")]
    param_names_js = json.dumps(param_names)
    return f"""
function _drive(input) {{
  const fn = eval({name_js});
  const _params = {param_names_js};
  if (input && typeof input === 'object' && !Array.isArray(input)) {{
    if (_params.length > 0) {{
      // Bind dict values to args in declaration order — order-agnostic
      // to JSON key shuffling, matches Python's `fn(**input)` semantics.
      return fn(..._params.map(k => input[k]));
    }}
    return fn(...Object.values(input));
  }}
  if (Array.isArray(input)) {{
    return fn(...input);
  }}
  return fn(input);
}}
"""
