"""EX-07: candidate code does not see the runner's secrets in its
environment.

Guarantee (the part ROUNDS-00A-L01 stage 2 closes; reading another
process's environment or command line is a pending row for
ROUNDS-00A-L05 and ROUNDS-00A-L07): a candidate process runs with a
minimal environment, so none of the runner's secrets reach it. The corpus
gives the runner the run's canaries as those secrets; the fixture runs an
ordinary program that prints its own environment and checks that no
canary appears in what comes back.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import inconclusive, result
from corpus._requests import CODING

SUBCASE = "EX-07.candidate-env-minimal"
PROGRAM = (
    "import json, os\n"
    "print('ENV:' + json.dumps(sorted(os.environ.items())))\n"
    "def three_sum(nums):\n"
    "    return []\n"
)


def run(ctx):
    acct = ctx.new_account("ex07")
    body = {"definition": dict(CODING), "code": PROGRAM, "input": {"nums": []}}
    resp = ctx.runner.request("POST", "/api/run", token=acct.token, json_body=body)
    if resp.error or resp.status != 200 or not isinstance(resp.body, dict):
        return inconclusive(SUBCASE, f"the program didn't run (status {resp.status or resp.error})")
    seen = "\n".join(str(resp.body.get(k) or "") for k in ("stdout", "stderr", "error", "return_value"))
    hits = sorted(name for name, hit in ctx.canaries.hits(seen).items() if hit)
    evidence = {"output": seen}
    if hits:
        # The plugin redacts the canary values from the kept evidence.
        return result({SUBCASE: Outcome.DETECTED.value}, "the candidate saw runner secrets: " + ", ".join(hits),
                      evidence=evidence, canary_text=seen)
    if "ENV:" not in seen:
        return inconclusive(SUBCASE, "the program ran but printed no environment")
    return result({SUBCASE: Outcome.CONTAINED.value}, "no runner secret reached the candidate's environment",
                  evidence=evidence, canary_text=seen)
