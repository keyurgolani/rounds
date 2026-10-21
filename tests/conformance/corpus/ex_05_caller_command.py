"""EX-05: the caller cannot choose the shell command that runs.

Guarantee (closed by ROUNDS-00A-L01 and ROUNDS-00A-L02): with
server-owned definitions enforced, a request that carries a
caller-chosen ``test_command`` is refused 422 ``legacy_request_rejected``
before anything runs; what runs comes only from the resolved definition.
The contained answer is that typed refusal; accepting the field and
running it is a finding.

The request names a field the server no longer takes. It carries no shell
payload that could run, so it reveals no injection recipe. The negative
control is a runner that still honours the caller's command.
"""
from __future__ import annotations

from corpus._base import Result, contained, detected

_CODE = "code-placeholder"


def run(ctx) -> Result:
    acct = ctx.new_account("ex05")
    # A caller-chosen command field, which the enforced server rejects.
    body = {"test_command": "server-should-refuse-this", "code": _CODE, "input": {}}
    with ctx.budget.spend():
        resp = ctx.runner.request("POST", "/api/run", token=acct.token, json_body=body)
    code = (resp.body or {}).get("code") if isinstance(resp.body, dict) else None
    evidence = {"status": str(resp.status), "code": str(code)}
    if resp.status == 422 and code == "legacy_request_rejected":
        return contained(
            "a caller-supplied test_command was refused legacy_request_rejected",
            evidence=evidence,
        )
    if resp.status in (200, 201):
        return detected(
            f"a caller-supplied test_command was accepted (status {resp.status})",
            evidence=evidence,
            canary_text=resp.text,
        )
    return detected(
        f"a caller-supplied test_command was not refused as expected (status {resp.status}, code {code})",
        evidence=evidence,
    )
