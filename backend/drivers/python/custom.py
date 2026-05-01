"""Python custom driver — driver code authored per problem.

The entry's drivers["python"] string must define `_drive(input)` and is
trusted (it comes from our seed data, not from user input). It runs in
the same subprocess as user code, with full access to user globals."""
from __future__ import annotations


def validate(entry: dict) -> list[str]:
    drivers = entry.get("drivers")
    if not isinstance(drivers, dict):
        return ["missing 'drivers' map — need a 'python' key"]
    code = drivers.get("python")
    if not isinstance(code, str) or not code.strip():
        return ["missing 'drivers.python' (must be a non-empty string)"]
    return []


def wrapper_snippet(entry: dict) -> str:
    return entry["drivers"]["python"]
