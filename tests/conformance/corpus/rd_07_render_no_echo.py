"""RD-07: the render proxy and its health check repeat no renderer text.

Guarantee (closed by ROUNDS-00A-L01; the renderer's own echo is a
white-box pending row for ROUNDS-00A-L06): ``/api/pdf/health`` answers
only its status, ``ok`` with 200 or ``unavailable`` with 503, and a render
the renderer can't finish answers its typed status with that code's fixed
sentence, never the renderer's body or a transport error. The fixture
compares the answer with exactly those, so any other text is a finding,
whatever it says. The corpus stack runs no renderer at stage 1, so the
fixture's ordinary render request always fails at the renderer.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import code_of, result
from corpus._requests import bodies

HEALTH = "RD-07.health-status-only"
RENDER = "RD-07.render-failure-typed"
# What health may answer, and the HTTP status each comes with
# (backend/routers/pdf.py).
HEALTH_STATUSES = {"ok": 200, "unavailable": 503}
# The typed failures a render may answer: the HTTP status and the fixed
# sentence of each (backend/routers/pdf.py RENDER_FAILED, and
# backend/app/errors.py for render_timeout, which the proxy sends with its
# registered sentence).
RENDER_FAILURES = {
    "worker_unavailable": (503, "The PDF renderer couldn't finish this document. Try again shortly."),
    "render_timeout": (422, "This document took too long to render. Simplify it and try again."),
}
ENVELOPE = {"detail", "code", "correlation_id"}


def _health(resp) -> tuple[str, str]:
    if resp.error or not isinstance(resp.body, dict):
        return Outcome.INCONCLUSIVE.value, f"health didn't answer JSON ({resp.status or resp.error})"
    if set(resp.body) != {"status"}:
        return Outcome.DETECTED.value, "health answered more than its status"
    status = resp.body["status"]
    if not isinstance(status, str) or status not in HEALTH_STATUSES:
        return Outcome.DETECTED.value, "health's status isn't one of its own values"
    if resp.status != HEALTH_STATUSES[status]:
        return Outcome.DETECTED.value, f"health answered {status} with {resp.status}, not {HEALTH_STATUSES[status]}"
    return Outcome.CONTAINED.value, ""


def _render(resp) -> tuple[str, str]:
    if resp.error:
        return Outcome.INCONCLUSIVE.value, f"render didn't answer ({resp.error})"
    if resp.status == 200:
        return Outcome.INCONCLUSIVE.value, "a render succeeded, so this stack has a renderer and the check can't run"
    body = resp.body
    code = code_of(body)
    expected = RENDER_FAILURES.get(code) if isinstance(code, str) else None
    if (not isinstance(body, dict) or set(body) != ENVELOPE or expected is None
            or (resp.status, body.get("detail")) != expected):
        return (Outcome.DETECTED.value,
                f"the failed render wasn't the typed envelope with its fixed sentence ({resp.status} {code})")
    return Outcome.CONTAINED.value, ""


def run(ctx):
    acct = ctx.new_account("rd07")
    health = ctx.runner.request("GET", "/api/pdf/health", token=acct.token)
    render = ctx.runner.request("POST", "/api/pdf/render", token=acct.token,
                                json_body=bodies()[("POST", "/api/pdf/render")])
    subcases: dict[str, str] = {}
    notes: list[str] = []
    for subcase, (outcome, why) in ((HEALTH, _health(health)), (RENDER, _render(render))):
        subcases[subcase] = outcome
        if why:
            notes.append(why)

    keys = sorted(health.body) if isinstance(health.body, dict) else None
    evidence = {"answers": f"health {health.status} keys {keys}; render {render.status} {code_of(render.body)}"}
    note = "; ".join(notes) or "health answered only its status and the failed render was typed with fixed text"
    # Both answers are scanned whole, whatever their shape.
    return result(subcases, note, evidence=evidence, canary_text=health.text + "\n" + render.text)
