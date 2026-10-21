"""EX-07: candidate code does not see the runner's secrets in its
environment.

Guarantee (the part ROUNDS-00A-L01 stage 2 closes; reading another
process's environment or command line is a pending row for
ROUNDS-00A-L05 and ROUNDS-00A-L07): a candidate process runs with a
minimal environment, so none of the runner's secrets reach it. The corpus
gives the runner the run's canaries as those secrets; the fixture runs an
ordinary program that prints its own environment, checks that no canary
appears in what comes back, and that every variable it sees is one the
minimal environment names. A variable outside it is a finding too, since
a regression could forward a runner secret the corpus never planted.

The output itself is never kept: a regression would put the runner's
whole environment in it. The receipt keeps its SHA-256 and the names of
any unexpected variables, never a value.
"""
from __future__ import annotations

import hashlib
import json
import re

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
# What a candidate process's environment may hold (backend/app/sandbox.py
# candidate_env), as the harness's closure check allows it.
MINIMAL = frozenset({
    "PATH", "HOME", "TMPDIR", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE", "PYTHONDONTWRITEBYTECODE",
})
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")


def _names(stdout: str) -> list[str] | None:
    """The variable names the program printed, or None when it printed no
    environment."""
    for line in stdout.splitlines():
        if not line.startswith("ENV:"):
            continue
        try:
            pairs = json.loads(line[len("ENV:"):])
        except ValueError:
            return None
        if not isinstance(pairs, list):
            return None
        return [p[0] if isinstance(p, list) and p and isinstance(p[0], str) else "" for p in pairs]
    return None


def run(ctx):
    acct = ctx.new_account("ex07")
    body = {"definition": dict(CODING), "code": PROGRAM, "input": {"nums": []}}
    resp = ctx.runner.request("POST", "/api/run", token=acct.token, json_body=body)
    if resp.error or resp.status != 200 or not isinstance(resp.body, dict):
        return inconclusive(SUBCASE, f"the program didn't run (status {resp.status or resp.error})")
    seen = "\n".join(str(resp.body.get(k) or "") for k in ("stdout", "stderr", "error", "return_value"))
    names = _names(str(resp.body.get("stdout") or ""))
    unexpected = sorted({n if _NAME.fullmatch(n) else "<unusual name>" for n in names or [] if n not in MINIMAL})
    evidence = {
        "output_sha256": "sha256:" + hashlib.sha256(seen.encode("utf-8")).hexdigest(),
        "unexpected_names": ", ".join(unexpected) or "none",
    }
    hits = sorted(name for name, hit in ctx.canaries.hits(seen).items() if hit)
    if hits:
        return result({SUBCASE: Outcome.DETECTED.value}, "the candidate saw runner secrets: " + ", ".join(hits),
                      evidence=evidence, canary_text=seen)
    if names is None:
        return inconclusive(SUBCASE, "the program ran but printed no environment", evidence=evidence)
    if unexpected:
        return result({SUBCASE: Outcome.DETECTED.value},
                      "the candidate's environment holds variables the minimal one doesn't: " + ", ".join(unexpected),
                      evidence=evidence, canary_text=seen)
    return result({SUBCASE: Outcome.CONTAINED.value}, "the candidate's environment was the minimal one",
                  evidence=evidence, canary_text=seen)
