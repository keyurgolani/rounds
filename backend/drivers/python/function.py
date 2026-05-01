"""Python `function` driver — plain function call.

Input shapes accepted:
  dict -> kwargs:    fn(**input)
  list -> positional: fn(*input)
  scalar -> single arg: fn(input)
"""
from __future__ import annotations


def validate(entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("name"), str) or not entry.get("name"):
        errors.append("missing 'name' (function to call)")
    return errors


def wrapper_snippet(entry: dict) -> str:
    name = entry["name"]
    return f"""
def _drive(input):
    fn = globals()[{name!r}]
    if isinstance(input, dict):
        return fn(**input)
    if isinstance(input, list):
        return fn(*input)
    return fn(input)
"""
