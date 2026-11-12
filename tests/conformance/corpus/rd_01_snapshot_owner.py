"""RD-01: one account cannot render another account's snapshot.

Guarantee (closed by ROUNDS-00A-L04; the anonymous render is EX-01's): a
render names one Legacy Artifact Snapshot by id and checksum, and only the
account that owns it gets a render of it. Another account naming it, with
its own checksum, gets exactly the answer it gets for a snapshot that
doesn't exist, and nothing renders.

The fixture makes two synthetic accounts and seeds a snapshot account A
owns (corpus/_snapshots.py). Account B renders it, then renders an id
that doesn't exist. A's own render of the same snapshot is the control: it
passes every check before the renderer and ends there, at the renderer's
typed failure, since the corpus stack runs no renderer, or with a PDF on a
stack that does.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import code_of, result
from corpus._requests import NO_SNAPSHOT, render_body
from corpus._snapshots import owned_snapshot

# This fixture's spec; conformance/manifest.py reads it as a literal.
SPEC = {
    "routes": ["POST /api/pdf/render"],
    "subcases": ["RD-01.foreign-snapshot-not-rendered", "RD-01.foreign-reads-as-missing"],
    "expected": {"ci": "contained", "compose": "contained", "k8s": "contained"},
    "languages": [],
    "control": "selftest/test_negative_controls.py: the render route without the snapshot owner check",
    "setup": ("two synthetic accounts and a snapshot the first owns, seeded with the admin token over its own "
              "resume"),
    "teardown": "both accounts removed with the admin token, their resumes and snapshots with them",
    "destructive": False,
    "environment_sensitive": True,
}

SUBCASES = tuple(SPEC["subcases"])
NOT_RENDERED, SAME = SUBCASES
# What a render that got past every snapshot check answers: a PDF, or the
# renderer's own typed failure (backend/routers/pdf.py).
REACHED_RENDERER = {(503, "worker_unavailable"), (422, "render_timeout")}


def _reached_renderer(resp) -> bool:
    return resp.status == 200 or (resp.status, code_of(resp.body)) in REACHED_RENDERER


def _answer(resp) -> tuple:
    body = resp.body if isinstance(resp.body, dict) else {}
    return resp.status, body.get("code"), body.get("detail")


def _render(ctx, acct, snapshot_id, checksum):
    return ctx.runner.request("POST", "/api/pdf/render", token=acct.token,
                              json_body=render_body(snapshot_id, checksum))


def run(ctx):
    a = ctx.new_account("rd01a")
    b = ctx.new_account("rd01b")
    snapshot_id, checksum = owned_snapshot(ctx, a)
    own = _render(ctx, a, snapshot_id, checksum)
    foreign = _render(ctx, b, snapshot_id, checksum)
    missing = _render(ctx, b, NO_SNAPSHOT, checksum)
    evidence = {"answers": f"owner {own.status} {code_of(own.body)}; other account {foreign.status} "
                           f"{code_of(foreign.body)}; missing id {missing.status} {code_of(missing.body)}"}
    texts = "\n".join(r.text for r in (own, foreign, missing))

    if not _reached_renderer(own):
        # The owner's own render didn't get past the snapshot checks, so
        # this run can't tell a refusal by owner from any other.
        subcases = {s: Outcome.INCONCLUSIVE.value for s in SUBCASES}
        return result(subcases, "the owner's own render didn't reach the renderer", evidence=evidence,
                      canary_text=texts)

    leaked = _reached_renderer(foreign)
    same = _answer(foreign) == _answer(missing) and (foreign.status, code_of(foreign.body)) == (404, "not_found")
    subcases = {
        NOT_RENDERED: Outcome.DETECTED.value if leaked else Outcome.CONTAINED.value,
        SAME: Outcome.CONTAINED.value if same and not leaked else Outcome.DETECTED.value,
    }
    if leaked:
        note = "account B's render of account A's snapshot got past the snapshot checks"
    elif not same:
        note = "another account's snapshot answered differently from a missing one"
    else:
        note = "account B's render of account A's snapshot read as a missing snapshot and nothing rendered"
    return result(subcases, note, evidence=evidence, canary_text=texts)
