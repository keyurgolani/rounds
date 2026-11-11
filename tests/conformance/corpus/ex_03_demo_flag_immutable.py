"""EX-03: a client cannot change its own demo or limit flags.

Guarantee (closed by ROUNDS-00A-L01; the demo lifecycle is owned by
ROUNDS-00B-L07): ``is_demo`` and the demo usage flags are server-owned. A
client write to them on its own ``users`` record is refused and leaves
them as they were, so a demo account can't reset its own limits. The
fixture makes an ordinary account, writes its own ``demo_run_used`` flag,
and reads the record back with the admin token.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import inconclusive, result

SUBCASE = "EX-03.demo-flags-server-owned"


def run(ctx):
    acct = ctx.new_account("ex03")
    write = ctx.pb.update("users", acct.user_id, {"demo_run_used": True}, token=acct.token)
    after = ctx.pb.view("users", acct.user_id, token=ctx.admin_token)
    if after.status != 200 or not isinstance(after.body, dict):
        return inconclusive(SUBCASE, f"couldn't read the account back (status {after.status})")
    changed = bool(after.body.get("demo_run_used"))
    refused = 400 <= write.status < 500
    evidence = {"answers": f"write {write.status}, demo_run_used after {changed}"}
    if changed:
        return result({SUBCASE: Outcome.DETECTED.value}, "a client write set its own demo_run_used flag",
                      evidence=evidence)
    if not refused:
        return result({SUBCASE: Outcome.DETECTED.value},
                      f"a client write to demo_run_used wasn't refused (status {write.status})", evidence=evidence)
    return result({SUBCASE: Outcome.CONTAINED.value},
                  f"the client write was refused ({write.status}) and the flag didn't change", evidence=evidence)
