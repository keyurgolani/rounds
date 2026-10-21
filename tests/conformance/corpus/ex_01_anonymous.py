"""EX-01: an anonymous caller cannot start execution or rendering.

Guarantee (closed by ROUNDS-00A-L01): every admitted execution and render
route refuses a request that carries no account, at the account step,
before it starts a subprocess, a render, or any scoring. The fixture
sends each route a well-formed request in the current shape, so nothing
but the account step can refuse it, and requires exactly the typed 401
``unauthenticated``.

A route an operator turned off answers its gate's typed 503 before the
account step (``route_disabled``, or ``definitions_disabled`` for the
execution routes), which runs nothing for anyone: that route is
contained by its gate and recorded as such, as the README's quarantine
step turns a route off. Any other answer, a 2xx, a 422, or a different
code, is a finding: it means something other than the account step
decided.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import code_of, result
from corpus._requests import bodies

SUBCASE = "EX-01.anonymous-denied"
# A gate's stop, before the account step (backend/app/admission.py).
GATE_STOPS = frozenset({"route_disabled", "definitions_disabled"})


def _stopped_by_gate(status: int, body) -> bool:
    return status == 503 and code_of(body) in GATE_STOPS


def run(ctx):
    seen: list[str] = []
    texts: list[str] = []
    findings: list[str] = []
    failed_to_answer: list[str] = []
    gated: list[str] = []
    for (method, path), body in bodies().items():
        resp = ctx.runner.request(method, path, json_body=body)
        code = code_of(resp.body)
        texts.append(resp.text)
        if resp.error:
            seen.append(f"{method} {path} -> no answer ({resp.error})")
            failed_to_answer.append(f"{path} ({resp.error})")
        elif _stopped_by_gate(resp.status, resp.body):
            seen.append(f"{method} {path} -> {resp.status} {code} (contained by its gate)")
            gated.append(f"{path} ({code})")
        elif (resp.status, code) == (401, "unauthenticated"):
            seen.append(f"{method} {path} -> {resp.status} {code}")
        else:
            seen.append(f"{method} {path} -> {resp.status} {code}")
            findings.append(f"{path} -> {resp.status} {code}")
    evidence = {"answers": "\n".join(seen)}
    canary_text = "\n".join(texts)
    if findings:
        outcome, note = Outcome.DETECTED.value, "an anonymous request wasn't refused at the account step: " + "; ".join(findings)
    elif failed_to_answer:
        outcome, note = Outcome.INCONCLUSIVE.value, "no answer from " + ", ".join(failed_to_answer)
    else:
        outcome = Outcome.CONTAINED.value
        refused = len(seen) - len(gated)
        note = f"{refused} of {len(seen)} admitted routes refused the anonymous caller 401 unauthenticated"
        if gated:
            note += "; contained by their gates: " + ", ".join(gated)
    return result({SUBCASE: outcome}, note, evidence=evidence, canary_text=canary_text)
