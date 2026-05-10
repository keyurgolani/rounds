"""Tiny KV Store — implement handle()."""
from __future__ import annotations


def handle(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    """Dispatch (method, path) to the appropriate operation.

    See prompt.md for the route contract.
    """
    return 501, {"error": "not implemented"}
