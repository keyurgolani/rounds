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
step turns a route off. A gate stop tests no account step, though, so
the fixture needs at least one route to answer the 401: when every route
answers its gate's stop, nothing was tested and the fixture is
inconclusive. Any other answer, a 2xx, a 422, or a different code, is a
finding: it means something other than the account step decided.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import code_of, result
from corpus._requests import bodies

# This fixture's spec; conformance/manifest.py reads it as a literal.
SPEC = {
    "routes": [
        "POST /api/run",
        "POST /api/evaluate",
        "POST /api/ai-coding/run-project",
        "POST /api/ai-coding/grade",
        "POST /api/take-home/run",
        "POST /api/take-home/submit",
        "POST /api/pdf/render",
    ],
    "subcases": ["EX-01.anonymous-denied"],
    "expected": {"ci": "contained", "compose": "contained", "k8s": "contained"},
    "languages": [],
    "control": "selftest/test_negative_controls.py: the account step off, and the body checked before the account",
    "setup": "none; the fixture sends no account",
    "teardown": "none",
    "destructive": False,
    "environment_sensitive": True,
}

SUBCASE = SPEC["subcases"][0]
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
    refused: list[str] = []
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
            refused.append(path)
        else:
            seen.append(f"{method} {path} -> {resp.status} {code}")
            findings.append(f"{path} -> {resp.status} {code}")
    evidence = {"answers": "\n".join(seen)}
    canary_text = "\n".join(texts)
    if findings:
        outcome, note = Outcome.DETECTED.value, "an anonymous request wasn't refused at the account step: " + "; ".join(findings)
    elif failed_to_answer:
        outcome, note = Outcome.INCONCLUSIVE.value, "no answer from " + ", ".join(failed_to_answer)
    elif not refused:
        # A gate stop runs nothing, but it doesn't reach the account step,
        # so a run in which every route was gated tested nothing.
        outcome = Outcome.INCONCLUSIVE.value
        note = "no route reached the account step; every one answered its gate's stop: " + ", ".join(gated)
    else:
        outcome = Outcome.CONTAINED.value
        note = f"{len(refused)} of {len(seen)} admitted routes refused the anonymous caller 401 unauthenticated"
        if gated:
            note += "; contained by their gates: " + ", ".join(gated)
    return result({SUBCASE: outcome}, note, evidence=evidence, canary_text=canary_text)
