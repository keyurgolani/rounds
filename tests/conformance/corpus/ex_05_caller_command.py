"""EX-05: the caller cannot choose the command that runs.

Guarantee (closed by ROUNDS-00A-L01 and ROUNDS-00A-L02): with
server-owned definitions enforced, a well-formed request that also names
its own ``test_command`` is refused 422 ``legacy_request_rejected``
before anything runs; what runs comes only from the resolved definition.
Every route the manifest lists gets the check. Accepting the field, or
refusing it for any other reason, is a finding.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import code_of, result
from corpus._requests import bodies

SUBCASE = "EX-05.caller-command-refused"
ROUTES = (("POST", "/api/run"), ("POST", "/api/ai-coding/run-project"))


def run(ctx):
    acct = ctx.new_account("ex05")
    all_bodies = bodies()
    answers: list[str] = []
    outcomes: list[str] = []
    for method, path in ROUTES:
        body = dict(all_bodies[(method, path)])
        body["test_command"] = "a caller-chosen command the server must refuse"
        resp = ctx.runner.request(method, path, token=acct.token, json_body=body)
        code = code_of(resp.body)
        answers.append(f"{path} -> {resp.status or resp.error} {code}")
        if resp.error:
            outcomes.append(Outcome.INCONCLUSIVE.value)
        elif (resp.status, code) == (422, "legacy_request_rejected"):
            outcomes.append(Outcome.CONTAINED.value)
        else:
            outcomes.append(Outcome.DETECTED.value)
    if Outcome.DETECTED.value in outcomes:
        outcome, note = Outcome.DETECTED.value, "a caller-supplied test_command wasn't refused by name"
    elif Outcome.INCONCLUSIVE.value in outcomes:
        outcome, note = Outcome.INCONCLUSIVE.value, "a route didn't answer"
    else:
        outcome, note = Outcome.CONTAINED.value, f"both routes refused a caller-supplied test_command by name"
    return result({SUBCASE: outcome}, note, evidence={"answers": "\n".join(answers)})
