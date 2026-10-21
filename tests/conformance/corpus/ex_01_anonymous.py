"""EX-01: an anonymous caller cannot start execution or rendering.

Guarantee (closed by ROUNDS-00A-L01): every admitted execution and render
route refuses a request that carries no account, at the account step,
before it starts a subprocess, a render, or any scoring. The fixture
sends each route a well-formed request in the current shape, so nothing
but the account step can refuse it, and requires exactly the typed 401
``unauthenticated``. Any other answer, a 2xx, a 422, or a different
code, is a finding: it means something other than the account step
decided.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import code_of, result
from corpus._requests import bodies

SUBCASE = "EX-01.anonymous-denied"


def run(ctx):
    seen: list[str] = []
    texts: list[str] = []
    findings: list[str] = []
    failed_to_answer: list[str] = []
    for (method, path), body in bodies().items():
        resp = ctx.runner.request(method, path, json_body=body)
        code = code_of(resp.body)
        seen.append(f"{method} {path} -> {resp.status} {code}")
        texts.append(resp.text)
        if resp.error:
            failed_to_answer.append(f"{path} ({resp.error})")
        elif (resp.status, code) != (401, "unauthenticated"):
            findings.append(f"{path} -> {resp.status} {code}")
    evidence = {"answers": "\n".join(seen)}
    canary_text = "\n".join(texts)
    if findings:
        outcome, note = Outcome.DETECTED.value, "an anonymous request wasn't refused at the account step: " + "; ".join(findings)
    elif failed_to_answer:
        outcome, note = Outcome.INCONCLUSIVE.value, "no answer from " + ", ".join(failed_to_answer)
    else:
        outcome, note = Outcome.CONTAINED.value, f"all {len(seen)} admitted routes refused the anonymous caller 401 unauthenticated"
    return result({SUBCASE: outcome}, note, evidence=evidence, canary_text=canary_text)
