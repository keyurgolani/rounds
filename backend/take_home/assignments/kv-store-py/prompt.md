# Tiny KV Store

You're building the routing layer of an internal HTTP-shaped service
and want to pull the dispatch logic out into a pure function so it's
trivially testable — no socket, no framework, just
`(method, path, body) → (status, body)`. The "service" itself is a
four-route key-value cache. Whoever picks this up next should be able
to add a fifth route without rewriting the whole switchboard, so the
shape of dispatch matters as much as the routes themselves.

Implement `handle(method: str, path: str, body: dict | None = None) -> tuple[int, dict]`
in `app.py`.

## Contract

| Method | Path           | Body                       | Response                                                        |
|--------|----------------|----------------------------|-----------------------------------------------------------------|
| POST   | `/set/<key>`   | `{"value": <any>}`         | `(200, {"ok": True})` — stores the value                        |
| GET    | `/get/<key>`   | (none)                     | `(200, {"value": <stored>})` or `(404, {"error": "not found"})` |
| DELETE | `/del/<key>`   | (none)                     | `(200, {"ok": True})` — idempotent on missing                   |
| GET    | `/list`        | (none)                     | `(200, {"keys": [<sorted list>]})`                              |

State persists across calls within the same process.

## What we're looking for

- Correctness on all four routes.
- Clean dispatch — avoid a giant if/elif chain on path strings. A
  small route table or regex-driven match is the kind of thing that
  pays off the moment a fifth route shows up.
- Clear error responses (consistent shape, useful when something
  unexpected hits the function).
- Standard library only — no external deps.

## Deliverables

- `app.py` with `handle(method, path, body)` implemented.
- `NOTES.md` — your dispatch approach in one paragraph (route table?
  regex? something else?), the trade-off you made, and what you'd
  change if a fifth route landed tomorrow.

## Time budget

~1 hour. The grading harness runs in seconds.
