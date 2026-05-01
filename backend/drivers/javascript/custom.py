"""JavaScript custom driver."""
from __future__ import annotations


def validate(entry: dict) -> list[str]:
    drivers = entry.get("drivers")
    if not isinstance(drivers, dict):
        return ["missing 'drivers' map"]
    code = drivers.get("javascript")
    if not isinstance(code, str) or not code.strip():
        return ["missing 'drivers.javascript' (must be a non-empty string)"]
    return []


def wrapper_snippet(entry: dict) -> str:
    return entry["drivers"]["javascript"]
