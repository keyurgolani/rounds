"""Python in_place_mutation driver — calls user fn (which mutates one
arg in place), returns that arg as the result so existing matchers grade it."""
from __future__ import annotations


def validate(entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("name"), str) or not entry.get("name"):
        errors.append("missing 'name' (function to call)")
    if not isinstance(entry.get("mutates"), str) or not entry.get("mutates"):
        errors.append("missing 'mutates' (param name that is mutated in place)")
    return errors


def wrapper_snippet(entry: dict) -> str:
    name = entry["name"]
    mutates = entry["mutates"]
    return f"""
def _drive(input):
    fn = globals()[{name!r}]
    if not isinstance(input, dict):
        raise ValueError("in_place_mutation input must be a dict of params")
    fn(**input)
    return input[{mutates!r}]
"""
