"""EX-04: an oversized request is refused before it is read, and the
caller can't choose its own limits.

Guarantee (closed by ROUNDS-00A-L01, with ROUNDS-00A-L02):

- a body larger than a route's byte cap answers 413 ``payload_too_large``
  from its declared length alone, before authentication, so an outsized
  payload never reaches a parser, a lookup, or a subprocess. The fixture
  declares one byte over the cap and sends only the headers, as the
  harness's verifier does, so nothing large crosses the network. An
  answer that doesn't come from the declared length (no answer while the
  runner waits for the body, or any other status) is a finding; a failed
  connection is inconclusive;
- a well-formed request that also names its own time limit is refused
  422 ``legacy_request_rejected`` before anything runs.

Both routes the manifest lists get both checks.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import code_of, result
from corpus._requests import bodies

CAP = "EX-04.body-cap"
LIMITS = "EX-04.caller-limits-refused"
# The /api/run and /api/evaluate admission cap (backend/app/admission.py).
CAP_BYTES = 512 * 1024
ROUTES = (("POST", "/api/run"), ("POST", "/api/evaluate"))


def _worst(outcomes: list[str]) -> str:
    for outcome in (Outcome.DETECTED.value, Outcome.INCONCLUSIVE.value):
        if outcome in outcomes:
            return outcome
    return Outcome.CONTAINED.value


def run(ctx):
    answers: list[str] = []
    cap_outcomes: list[str] = []
    for method, path in ROUTES:
        resp = ctx.runner.declare(method, path, CAP_BYTES + 1)
        code = code_of(resp.body)
        answers.append(f"declared {CAP_BYTES + 1} bytes to {path} -> {resp.status or resp.error} {code}")
        if resp.error == "timeout":
            cap_outcomes.append(Outcome.DETECTED.value)
        elif resp.error:
            cap_outcomes.append(Outcome.INCONCLUSIVE.value)
        elif (resp.status, code) == (413, "payload_too_large"):
            cap_outcomes.append(Outcome.CONTAINED.value)
        else:
            cap_outcomes.append(Outcome.DETECTED.value)

    acct = ctx.new_account("ex04")
    limit_outcomes: list[str] = []
    all_bodies = bodies()
    for method, path in ROUTES:
        body = dict(all_bodies[(method, path)])
        body["timeout_s"] = 30
        resp = ctx.runner.request(method, path, token=acct.token, json_body=body)
        code = code_of(resp.body)
        answers.append(f"{path} with a caller time limit -> {resp.status or resp.error} {code}")
        if resp.error:
            limit_outcomes.append(Outcome.INCONCLUSIVE.value)
        elif (resp.status, code) == (422, "legacy_request_rejected"):
            limit_outcomes.append(Outcome.CONTAINED.value)
        else:
            limit_outcomes.append(Outcome.DETECTED.value)

    subcases = {CAP: _worst(cap_outcomes), LIMITS: _worst(limit_outcomes)}
    problems = [s for s, o in subcases.items() if o != Outcome.CONTAINED.value]
    note = ("oversized bodies were refused from their declared length and caller limits were refused"
            if not problems else "not contained: " + ", ".join(problems))
    return result(subcases, note, evidence={"answers": "\n".join(answers)})
