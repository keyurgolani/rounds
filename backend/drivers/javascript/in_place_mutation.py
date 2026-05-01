"""JavaScript in_place_mutation driver."""
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
    return f"""
function _drive(input) {{
  const fn = eval({name_js});
  if (!input || typeof input !== 'object' || Array.isArray(input)) {{
    throw new Error("in_place_mutation input must be an object of params");
  }}
  fn(...Object.values(input));
  return input[{mutates_js}];
}}
"""
