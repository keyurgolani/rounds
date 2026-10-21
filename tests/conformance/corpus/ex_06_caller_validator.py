"""EX-06: the caller cannot supply the validators or a custom driver.

Guarantee (closed by ROUNDS-00A-L01 for caller validators and the
``custom`` driver, and ROUNDS-00A-L02 for keeping evaluation out of the
API): with server-owned definitions enforced, a request that carries
caller ``validators`` or a caller ``entry`` is refused 422
``legacy_request_rejected`` before anything runs; validators come only
from the definition's pinned revision and run in the validator process,
never in the API. The contained answer is that typed refusal.

The request names fields the server no longer takes and carries no
validator or driver body that could execute, so it reveals no escape
recipe. The negative control evaluates a caller-supplied validator.
"""
from __future__ import annotations

from corpus._base import Result, contained, detected

_CODE = "code-placeholder"


def run(ctx) -> Result:
    acct = ctx.new_account("ex06")
    findings: list[str] = []
    statuses: list[str] = []
    # Each request names one field the enforced server refuses: caller
    # validators, and a caller-supplied entry (the path a custom driver
    # would have taken).
    for field, body in (
        ("validators", {"validators": [], "code": _CODE, "case_ids": []}),
        ("entry", {"entry": {"kind": "custom"}, "code": _CODE, "input": {}}),
    ):
        route = "/api/evaluate" if field == "validators" else "/api/run"
        with ctx.budget.spend():
            resp = ctx.runner.request("POST", route, token=acct.token, json_body=body)
        code = (resp.body or {}).get("code") if isinstance(resp.body, dict) else None
        statuses.append(f"{field} -> {resp.status}/{code}")
        if not (resp.status == 422 and code == "legacy_request_rejected"):
            findings.append(f"{field}: status {resp.status}, code {code}")
    evidence = {"attempts": "\n".join(statuses)}
    if findings:
        return detected(
            "a caller-supplied validator or driver field was not refused: " + "; ".join(findings),
            evidence=evidence,
        )
    return contained(
        "caller validators and a caller-supplied driver were both refused legacy_request_rejected",
        evidence=evidence,
    )
