"""EX-05: the caller cannot choose the command that runs.

Guarantee (closed by ROUNDS-00A-L01 and ROUNDS-00A-L02): with
server-owned definitions enforced, a well-formed request that also names
its own ``test_command`` is refused 422 ``legacy_request_rejected``
before anything runs; what runs comes only from the resolved definition.
Every route the spec lists gets the check. Accepting the field, or
refusing it for any other reason, is a finding.

On the take-home run route the fixture also sends the same body without
the field, which must run the definition it names: the corpus stack's
active take-home definition (conformance/overlay.py), so the live run
shows the runner resolves it. The answer has to name that definition as
the one that ran; any other answer leaves the route's check
inconclusive, since its refusal was then never checked against an
active definition.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import code_of, result
from corpus._requests import TAKE_HOME, bodies

# This fixture's spec; conformance/manifest.py reads it as a literal.
SPEC = {
    "routes": ["POST /api/run", "POST /api/ai-coding/run-project", "POST /api/take-home/run"],
    "subcases": ["EX-05.caller-command-refused"],
    "expected": {"ci": "contained", "compose": "contained", "k8s": "contained"},
    "languages": ["python", "javascript", "typescript"],
    "control": "selftest/test_negative_controls.py: caller fields accepted",
    "setup": ("one synthetic account; the enforced execution-definitions gate; the corpus stack's take-home "
              "definition (conformance/overlay.py), which the take-home run must run when the body carries no "
              "caller field"),
    "teardown": "the account removed with the admin token",
    "destructive": False,
    "environment_sensitive": False,
}

SUBCASE = SPEC["subcases"][0]
TAKE_HOME_RUN = ("POST", "/api/take-home/run")
ROUTES = (("POST", "/api/run"), ("POST", "/api/ai-coding/run-project"), TAKE_HOME_RUN)


def _ran_named_definition(resp, named: dict) -> bool:
    """The answer is a completed run of the definition the body named."""
    ran = resp.body.get("definition") if isinstance(resp.body, dict) else None
    return (not resp.error and resp.status == 200 and isinstance(ran, dict)
            and (ran.get("track"), ran.get("slug"), ran.get("variant"), ran.get("content_version"))
            == (named["track"], named["slug"], named["variant"], named["version"]))


def run(ctx):
    acct = ctx.new_account("ex05")
    all_bodies = bodies()
    answers: list[str] = []
    texts: list[str] = []
    outcomes: list[str] = []
    problems: list[str] = []
    for method, path in ROUTES:
        body = dict(all_bodies[(method, path)])
        if (method, path) == TAKE_HOME_RUN:
            plain = ctx.runner.request(method, path, token=acct.token, json_body=body)
            texts.append(plain.text)
            answers.append(f"{path} without the field -> {plain.status or plain.error} {code_of(plain.body)}")
            if not _ran_named_definition(plain, TAKE_HOME):
                outcomes.append(Outcome.INCONCLUSIVE.value)
                problems.append("the corpus take-home definition didn't run")
        body["test_command"] = "a caller-chosen command the server must refuse"
        resp = ctx.runner.request(method, path, token=acct.token, json_body=body)
        code = code_of(resp.body)
        texts.append(resp.text)
        answers.append(f"{path} -> {resp.status or resp.error} {code}")
        if resp.error:
            outcomes.append(Outcome.INCONCLUSIVE.value)
            problems.append(f"{path} didn't answer")
        elif (resp.status, code) == (422, "legacy_request_rejected"):
            outcomes.append(Outcome.CONTAINED.value)
        else:
            outcomes.append(Outcome.DETECTED.value)
    if Outcome.DETECTED.value in outcomes:
        outcome, note = Outcome.DETECTED.value, "a caller-supplied test_command wasn't refused by name"
    elif Outcome.INCONCLUSIVE.value in outcomes:
        outcome, note = Outcome.INCONCLUSIVE.value, "; ".join(problems)
    else:
        outcome = Outcome.CONTAINED.value
        note = (f"all {len(ROUTES)} routes refused a caller-supplied test_command by name, "
                "and the take-home run without it ran the corpus take-home definition")
    return result({SUBCASE: outcome}, note, evidence={"answers": "\n".join(answers)}, canary_text="\n".join(texts))
