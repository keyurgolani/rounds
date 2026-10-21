"""RD-07: the render proxy and its health check reveal no sidecar text.

Guarantee (closed by ROUNDS-00A-L01; the sidecar's own echo is a
white-box sub-case for ROUNDS-00A-L06): the ``/api/pdf/render`` proxy
answers a failed render with a typed status and fixed text, never the
sidecar's body or a ``URLError`` string, and ``/api/pdf/health`` answers
only its status. The contained answer is a typed envelope with no sidecar
text and a health body whose only key is ``status``; leaking the
sidecar's text or an extra field is a finding.

The fixture drives the proxy with the sidecar unreachable (the corpus
stack runs no renderer at stage 1) and reads a small, ordinary document
through it. It sends no document that probes the renderer; the render
sub-cases that need a live renderer are pending rows for ROUNDS-00A-L06.
"""
from __future__ import annotations

from corpus._base import Result, contained, detected, inconclusive

# Text that would betray the sidecar or the transport if it were echoed.
_LEAK_MARKERS = ("URLError", "ECONNREFUSED", "Connection refused", "pdf-renderer", "Traceback", "Errno")


def run(ctx) -> Result:
    acct = ctx.new_account("rd07")
    findings: list[str] = []

    with ctx.budget.spend():
        health = ctx.runner.request("GET", "/api/pdf/health", token=acct.token)
    if not isinstance(health.body, dict):
        return inconclusive(f"health did not answer JSON (status {health.status})")
    extra = sorted(set(health.body) - {"status"})
    if extra:
        findings.append(f"health leaked extra keys {extra}")

    with ctx.budget.spend():
        render = ctx.runner.request(
            "POST", "/api/pdf/render", token=acct.token, json_body={"html": "<p>x</p>", "margin_mm": 0}
        )
    code = render.body.get("code") if isinstance(render.body, dict) else None
    detail = render.body.get("detail", "") if isinstance(render.body, dict) else render.text
    if render.status == 200:
        findings.append("render unexpectedly succeeded with no renderer")
    elif code not in ("worker_unavailable", "render_timeout"):
        findings.append(f"render answered an untyped failure (status {render.status}, code {code})")
    leaked = [m for m in _LEAK_MARKERS if m in detail]
    if leaked:
        findings.append(f"render echoed sidecar or transport text: {leaked}")

    evidence = {
        "health_status": str(health.status),
        "health_keys": ",".join(sorted(health.body)),
        "render_status": str(render.status),
        "render_code": str(code),
    }
    if findings:
        return detected("; ".join(findings), evidence=evidence, canary_text=detail)
    return contained(
        "health answered only its status and the failed render was typed with no sidecar text",
        evidence=evidence,
        canary_text=detail,
    )
