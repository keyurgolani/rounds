"""EX-01: an anonymous caller cannot start execution or rendering.

Guarantee (closed by ROUNDS-00A-L01): every admitted execution and
render route refuses a request that carries no account, before it starts
a subprocess, a render, or CPU-bound scoring. The contained answer is a
typed denial; a 2xx from any route is a finding.

This probes the deny path only: it sends no code and no payload that
would run, so it reveals no bypass. The negative control removes the
account step in a fault profile and the fixture then detects.
"""
from __future__ import annotations

from conformance.outcomes import classify_denial
from corpus._base import Result, contained, detected

# Admitted routes that start work and must refuse an anonymous caller.
_ROUTES = [
    ("POST", "/api/run"),
    ("POST", "/api/evaluate"),
    ("POST", "/api/ai-coding/run-project"),
    ("POST", "/api/ai-coding/grade"),
    ("POST", "/api/take-home/run"),
    ("POST", "/api/take-home/submit"),
    ("POST", "/api/pdf/render"),
]


def run(ctx) -> Result:
    allowed: list[str] = []
    seen: list[str] = []
    bodies: list[str] = []
    for method, path in _ROUTES:
        with ctx.budget.spend():
            resp = ctx.runner.request(method, path, json_body={})
        seen.append(f"{path} -> {resp.status}")
        bodies.append(resp.text)
        if not classify_denial(resp.status):
            allowed.append(f"{path} -> {resp.status}")
    evidence = {"statuses": "\n".join(seen)}
    canary_text = "\n".join(bodies)
    if allowed:
        return detected(
            "an admitted route answered an anonymous caller: " + "; ".join(allowed),
            evidence=evidence,
            canary_text=canary_text,
        )
    return contained(
        f"every admitted route refused the anonymous caller ({len(_ROUTES)} routes)",
        evidence=evidence,
        canary_text=canary_text,
    )
