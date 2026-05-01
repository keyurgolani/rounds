"""JavaScript class_ops driver."""
from __future__ import annotations

import json


def validate(entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("class"), str) or not entry.get("class"):
        errors.append("missing 'class' (class to instantiate)")
    return errors


def wrapper_snippet(entry: dict) -> str:
    class_name = entry["class"]
    name_js = json.dumps(class_name)
    return f"""
function _drive(input) {{
  if (!input || typeof input !== 'object' || !Array.isArray(input.ops) || !Array.isArray(input.args)) {{
    throw new Error("class_ops input must be {{ops: [...], args: [...]}}");
  }}
  const ops = input.ops;
  const args = input.args;
  if (ops.length === 0 || ops[0] !== {name_js}) {{
    throw new Error("class_ops: ops[0] must equal " + {name_js} + ", got " + JSON.stringify(ops[0]));
  }}
  const Cls = eval({name_js});
  const inst = new Cls(...args[0]);
  const results = [null];
  for (let i = 1; i < ops.length; i++) {{
    const out = inst[ops[i]](...args[i]);
    results.push(out === undefined ? null : out);
  }}
  return results;
}}
"""
