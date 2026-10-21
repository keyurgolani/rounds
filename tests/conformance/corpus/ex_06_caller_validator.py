"""EX-06: the caller cannot supply the validators or a driver.

Guarantee (closed by ROUNDS-00A-L01 for caller validators and drivers,
and ROUNDS-00A-L02 for keeping evaluation out of the API; running a
definition's validators inside the worker is a pending row for
ROUNDS-00A-L05): with server-owned definitions enforced, a well-formed
request that also carries its own ``validators`` or ``entry`` is refused
422 ``legacy_request_rejected`` before anything runs. Validators come
only from the definition's pinned revision and run in the validator
process, never in the API.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import code_of, result
from corpus._requests import bodies

VALIDATORS = "EX-06.caller-validators-refused"
DRIVER = "EX-06.caller-driver-refused"
CHECKS = (
    (VALIDATORS, ("POST", "/api/evaluate"), "validators", []),
    (DRIVER, ("POST", "/api/run"), "entry", {"kind": "custom"}),
)


def run(ctx):
    acct = ctx.new_account("ex06")
    all_bodies = bodies()
    answers: list[str] = []
    subcases: dict[str, str] = {}
    for subcase, (method, path), field, value in CHECKS:
        body = dict(all_bodies[(method, path)])
        body[field] = value
        resp = ctx.runner.request(method, path, token=acct.token, json_body=body)
        code = code_of(resp.body)
        answers.append(f"{field} on {path} -> {resp.status or resp.error} {code}")
        if resp.error:
            subcases[subcase] = Outcome.INCONCLUSIVE.value
        elif (resp.status, code) == (422, "legacy_request_rejected"):
            subcases[subcase] = Outcome.CONTAINED.value
        else:
            subcases[subcase] = Outcome.DETECTED.value
    open_ = [s for s, o in subcases.items() if o != Outcome.CONTAINED.value]
    note = ("caller validators and a caller driver were both refused by name" if not open_
            else "not contained: " + ", ".join(open_))
    return result(subcases, note, evidence={"answers": "\n".join(answers)})
