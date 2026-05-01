"""Driver registry — maps (language, kind) to a driver module.

A driver module exports two functions:
  validate(entry: dict) -> list[str]
      Returns schema errors for the entry declaration. Empty = OK.
  wrapper_snippet(entry: dict) -> str
      Returns language-specific source code that defines a `_drive(input)`
      function. The orchestrator concatenates: user code + this snippet +
      invocation boilerplate.
"""
from __future__ import annotations

from importlib import import_module
from types import ModuleType

LANGUAGES = ("python", "javascript")
KINDS = (
    "function",
    "class_ops",
    "in_place_mutation",
    "custom",
    "linked_list",
    "tree",
    "graph",
)


def get_driver(language: str, kind: str) -> ModuleType:
    if language not in LANGUAGES:
        raise KeyError(f"Unknown language: {language!r}")
    if kind not in KINDS:
        raise KeyError(f"Unknown kind: {kind!r}")
    return import_module(f"drivers.{language}.{kind}")
