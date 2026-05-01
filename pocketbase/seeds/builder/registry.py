"""Registry collecting authored coding-question modules.

Each module under `builder/questions/` defines a top-level `QUESTION`
dict (the canonical PocketBase shape) and a top-level `REFERENCE`
callable (the Python solution invoked during validation). The build
script imports every module in `builder/questions/`, harvests both,
runs the reference solution against every test case via the actual
backend matchers, and emits the consolidated `more_coding.json`.

Test-case `expected` values follow the same conventions as the
existing seed (see `pocketbase/seeds/content.json`):

  - Bare value      → strict equality
  - {"$match":"..."} → tagged matcher (validator/unordered_deep/etc.)

The reference callable receives the test-case input dict expanded as
keyword arguments. For class-based problems (input shaped as
`{"ops": [...], "args": [...]}`) the reference receives the dict and
must replay the op sequence itself — this mirrors how
`backend/runner.py` dispatches the user's class.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


Matcher = Callable[[Any, Any, Any], tuple[bool, str | None]]


@dataclass
class Question:
    payload: dict[str, Any]
    reference_python: Callable[..., Any]
    # Optional: skip validation on specific test-case indices (e.g.
    # validators that only check structural invariants the reference
    # happens to satisfy by construction). Empty by default.
    skip_validation_indices: set[int] = field(default_factory=set)


# Module-level registry. Each question module appends to this list at
# import time via `register(...)`.
QUESTIONS: list[Question] = []


def register(payload: dict[str, Any], reference_python: Callable[..., Any], **kwargs: Any) -> None:
    QUESTIONS.append(Question(payload=payload, reference_python=reference_python, **kwargs))


# ---- Matcher helpers (build-time convenience constructors) -----------
# These produce the same JSON shapes the runtime matcher in
# `backend/matchers.py` understands, but are easier to author from
# Python than hand-written dicts.

def validator(description: str, code: str, examples: list[Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "$match": "validator",
        "description": description,
        "code": code,
    }
    if examples is not None:
        out["examples"] = examples
    return out


def unordered_deep(value: Any) -> dict[str, Any]:
    return {"$match": "unordered_deep", "value": value}


def unordered(value: Any) -> dict[str, Any]:
    return {"$match": "unordered", "value": value}


def any_of(values: list[Any]) -> dict[str, Any]:
    return {"$match": "any_of", "values": values}


def approx(value: Any, abs_tol: float = 0.0, rel_tol: float = 0.0) -> dict[str, Any]:
    return {"$match": "approx", "value": value, "abs_tol": abs_tol, "rel_tol": rel_tol}
