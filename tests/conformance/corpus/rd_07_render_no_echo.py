"""RD-07: the render proxy and its health check repeat no renderer text.

Guarantee (closed by ROUNDS-00A-L01; the renderer's own echo is a
white-box pending row for ROUNDS-00A-L06): ``/api/pdf/health`` answers
only its status, and a render the renderer can't finish answers a typed
status with fixed text, never the renderer's body or a transport error.
The corpus stack runs no renderer at stage 1, so the fixture's ordinary
render request always fails at the renderer.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import code_of, result
from corpus._requests import bodies

HEALTH = "RD-07.health-status-only"
RENDER = "RD-07.render-failure-typed"
# Text that would come from the renderer or the transport, not the proxy.
FOREIGN_TEXT = ("URLError", "ECONNREFUSED", "Connection refused", "pdf-renderer", "Traceback", "Errno")
ENVELOPE = {"detail", "code", "correlation_id"}


def run(ctx):
    acct = ctx.new_account("rd07")
    subcases: dict[str, str] = {}
    notes: list[str] = []

    health = ctx.runner.request("GET", "/api/pdf/health", token=acct.token)
    if health.error or not isinstance(health.body, dict):
        subcases[HEALTH] = Outcome.INCONCLUSIVE.value
        notes.append(f"health didn't answer JSON ({health.status or health.error})")
    elif set(health.body) != {"status"}:
        subcases[HEALTH] = Outcome.DETECTED.value
        notes.append("health answered more than its status")
    else:
        subcases[HEALTH] = Outcome.CONTAINED.value

    render = ctx.runner.request("POST", "/api/pdf/render", token=acct.token,
                                json_body=bodies()[("POST", "/api/pdf/render")])
    code = code_of(render.body)
    detail = render.body.get("detail", "") if isinstance(render.body, dict) else render.text
    if render.error:
        subcases[RENDER] = Outcome.INCONCLUSIVE.value
        notes.append(f"render didn't answer ({render.error})")
    elif render.status == 200:
        subcases[RENDER] = Outcome.INCONCLUSIVE.value
        notes.append("a render succeeded, so this stack has a renderer and the check can't run")
    elif (code not in ("worker_unavailable", "render_timeout")
          or not isinstance(render.body, dict) or set(render.body) != ENVELOPE
          or any(text in detail for text in FOREIGN_TEXT)):
        subcases[RENDER] = Outcome.DETECTED.value
        notes.append(f"the failed render wasn't the typed envelope with fixed text ({render.status} {code})")
    else:
        subcases[RENDER] = Outcome.CONTAINED.value

    evidence = {
        "answers": f"health {health.status} keys {sorted(health.body) if isinstance(health.body, dict) else None}; "
                   f"render {render.status} {code}",
    }
    note = "; ".join(notes) or "health answered only its status and the failed render was typed with fixed text"
    return result(subcases, note, evidence=evidence, canary_text=detail)
