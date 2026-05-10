# Tiny KV Store

Implement a small in-memory key-value store as a pure dispatch function.

## Contract

Your job is to fill in `handle(method: str, path: str, body: dict | None = None) -> tuple[int, dict]` in `app.py`.

The function must support these routes:

| Method | Path           | Body                       | Response                                         |
|--------|----------------|----------------------------|--------------------------------------------------|
| POST   | `/set/<key>`   | `{"value": <any>}`         | `(200, {"ok": True})` — stores the value         |
| GET    | `/get/<key>`   | (none)                     | `(200, {"value": <stored>})` or `(404, {"error": "not found"})` |
| DELETE | `/del/<key>`   | (none)                     | `(200, {"ok": True})` — idempotent on missing    |
| GET    | `/list`        | (none)                     | `(200, {"keys": [<sorted list>]})`               |

State persists across calls within the same process.

## Deliverables

- A working `app.py` with `handle(method, path, body)` implemented.
- Optional: a short note in `NOTES.md` explaining your dispatch approach (e.g., regex routes, or a tiny route table) and any trade-offs.

## What we're looking for

- Correctness on all four routes.
- Clean dispatch (avoid a giant if/elif chain on path strings).
- Clear error responses.
- The candidate uses Python's standard library only — no external deps.

## Time budget

Roughly 1 hour. The grading harness runs in a few seconds.
