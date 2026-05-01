"""JavaScript `function` driver."""
from __future__ import annotations

import json


def validate(entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("name"), str) or not entry.get("name"):
        errors.append("missing 'name' (function to call)")
    return errors


def wrapper_snippet(entry: dict) -> str:
    name = entry["name"]
    name_js = json.dumps(name)
    return f"""
function _drive(input) {{
  const fn = eval({name_js});
  if (input && typeof input === 'object' && !Array.isArray(input)) {{
    return fn(...Object.values(input));
  }}
  if (Array.isArray(input)) {{
    return fn(...input);
  }}
  return fn(input);
}}
"""
