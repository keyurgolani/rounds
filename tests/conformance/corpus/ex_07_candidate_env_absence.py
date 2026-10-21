"""EX-07: candidate code does not see the runner's secrets in its env.

Guarantee (the part closed by ROUNDS-00A-L01 stage 2; the ``/proc`` and
other-uid reads close with ROUNDS-00A-L05 and ROUNDS-00A-L07): a
candidate process runs with a minimal environment, so the runner's
secrets (the provider-key secret, the admin credentials, the admission
secret) are not in the environment the candidate can read. The contained
answer is that none of the run's canary values appear in the candidate's
output; a canary in the output is a finding.

The fixture runs an ordinary program that prints its own environment and
scans the output for the run's canaries. The runner is given those
canaries as its environment, so a regression that forwarded the runner's
environment would surface them here. Reading ``/proc`` or another job's
memory is a pending row (ROUNDS-00A-L05, ROUNDS-00A-L07), not this one.
"""
from __future__ import annotations

from corpus._base import Result, contained, detected, inconclusive

# An ordinary program: it prints its environment (so the fixture can scan
# it) and defines the function the coding definition calls, so the run
# completes. It reads nothing it should not and exploits nothing.
_CODE = (
    "import os, json\n"
    "print('ENVDUMP:' + json.dumps(dict(os.environ)))\n"
    "def three_sum(nums):\n"
    "    return []\n"
)

_DEFINITION = {"track": "coding", "slug": "3sum", "variant": "python", "version": 1}


def run(ctx) -> Result:
    acct = ctx.new_account("ex07")
    body = {"definition": _DEFINITION, "code": _CODE, "input": {"nums": []}}
    with ctx.budget.spend():
        resp = ctx.runner.request("POST", "/api/run", token=acct.token, json_body=body)
    if resp.status != 200 or not isinstance(resp.body, dict):
        return inconclusive(
            f"the probe program did not run (status {resp.status}); cannot judge env absence"
        )
    observed = "\n".join(
        str(resp.body.get(k) or "") for k in ("stdout", "stderr", "error", "return_value")
    )
    hits = [name for name, hit in ctx.canaries.hits(observed).items() if hit]
    evidence = {"stdout_len": str(len(str(resp.body.get("stdout") or "")))}
    if hits:
        # The canary values themselves are redacted from the retained
        # artifact; only the names of the canaries that leaked are kept.
        return detected(
            "candidate output held runner canaries: " + ", ".join(hits),
            evidence=evidence,
            canary_text=observed,
        )
    return contained(
        "no runner canary appeared in the candidate's environment output",
        evidence=evidence,
        canary_text=observed,
    )
