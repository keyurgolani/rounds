"""Python `class_ops` driver — sequence of operations on one class instance.

Test case input shape: {"ops": [...], "args": [...]} parallel arrays.
ops[0] is the class itself (treated as the constructor); subsequent
ops[i] are method names. args[i] is the positional argument list for
ops[i]. Returns a list of per-op results (None for the constructor)."""
from __future__ import annotations


def validate(entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("class"), str) or not entry.get("class"):
        errors.append("missing 'class' (class to instantiate)")
    return errors


def wrapper_snippet(entry: dict) -> str:
    class_name = entry["class"]
    return f"""
def _drive(input):
    if not (isinstance(input, dict) and "ops" in input and "args" in input):
        raise ValueError("class_ops input must be {{'ops': [...], 'args': [...]}}")
    ops = input["ops"]
    args_list = input["args"]
    if not ops or ops[0] != {class_name!r}:
        raise ValueError(
            f"class_ops: ops[0] must equal {class_name!r}, got {{ops[0]!r}}"
        )
    cls = globals()[{class_name!r}]
    instance = cls(*args_list[0])
    results = [None]
    for op, args in zip(ops[1:], args_list[1:]):
        method = getattr(instance, op)
        results.append(method(*args))
    return results
"""
