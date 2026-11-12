"""A Legacy Artifact Snapshot an account owns, for the render fixtures
(ROUNDS-00A-L04).

Only a PocketBase hook writes snapshots in a deployment, and the corpus
stack runs no materializer, so a fixture seeds one with the admin token
over the account's own resume, the way #9's harness factory seeds its
fixture snapshot, with the factory's fixed markup document. The account's
teardown removes the resume and the snapshot with it.
"""
from __future__ import annotations

import secrets


def owned_snapshot(ctx, acct) -> tuple[str, str]:
    """(snapshot id, content checksum) of a new snapshot ``acct`` owns."""
    import factory  # harness/probes

    resume = ctx.pb.create("resumes", acct.token, {"user": acct.user_id, "name": "corpus resume",
                                                   "slug": "corpus-" + secrets.token_hex(4)})
    if resume.status != 200 or not isinstance(resume.body, dict):
        raise RuntimeError(f"the account's resume create answered {resume.status}")
    made = ctx.pb.create_with_file(
        "legacy_artifact_snapshots",
        ctx.admin_token,
        {"user": acct.user_id, **factory.snapshot_fields(resume.body["id"])},
        "markup",
        "snapshot.html",
        factory.SNAPSHOT_MARKUP,
        "text/html",
    )
    if made.status != 200 or not isinstance(made.body, dict):
        raise RuntimeError(f"the snapshot seed answered {made.status}")
    return made.body["id"], made.body["content_checksum"]
