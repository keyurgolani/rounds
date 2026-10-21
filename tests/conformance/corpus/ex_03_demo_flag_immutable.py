"""EX-03: a client cannot change its own demo or limit flags.

Guarantee (closed by ROUNDS-00A-L01; the demo lifecycle is owned by
ROUNDS-00B-L07): the ``is_demo`` flag and the demo usage flags are
server-derived; a client write to them on its own ``users`` record is
refused, so a demo actor cannot reset its own limits. The contained
answer is that the flag never changes; a write that sticks is a finding.

The fixture makes a normal account and tries to set its own
``demo_run_used`` flag, then reads the record back with the admin token
to confirm it did not change.
"""
from __future__ import annotations

from corpus._base import Result, contained, detected, inconclusive


def run(ctx) -> Result:
    acct = ctx.new_account("ex03")
    with ctx.budget.spend():
        resp = ctx.pb.update("users", acct.user_id, {"demo_run_used": True}, token=acct.token)
    with ctx.budget.spend():
        after = ctx.pb.view("users", acct.user_id, token=ctx.admin_token)
    if after.status != 200 or not isinstance(after.body, dict):
        return inconclusive(f"could not read the account back (status {after.status})")
    flag = bool(after.body.get("demo_run_used"))
    evidence = {"write_status": str(resp.status), "demo_run_used_after": str(flag)}
    if flag:
        return detected("a client write set its own demo_run_used flag", evidence=evidence)
    return contained(
        f"a client write to demo_run_used was refused (status {resp.status}) and the flag did not change",
        evidence=evidence,
    )
