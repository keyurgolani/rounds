"""EX-02: one account cannot read another account's result row.

Guarantee (closed by ROUNDS-00B-L01's account scope): a signed-in account
cannot read another account's execution result by id or find it under a
filter, and reading a foreign id answers exactly as reading one that
doesn't exist.

The fixture makes two synthetic accounts, has A create one result row,
and has B view it by id, list it under a filter naming its id, and view
an id that doesn't exist.
"""
from __future__ import annotations

from conformance.outcomes import Outcome
from corpus._base import inconclusive, result

# This fixture's spec; conformance/manifest.py reads it as a literal.
SPEC = {
    "routes": [
        "POST /api/collections/take_home_attempts/records",
        "GET /api/collections/take_home_attempts/records/:id",
        "GET /api/collections/take_home_attempts/records",
    ],
    "subcases": ["EX-02.result-read-denied", "EX-02.foreign-reads-as-missing"],
    "expected": {"ci": "contained", "compose": "contained", "k8s": "contained"},
    "languages": [],
    "control": ("selftest/test_negative_controls.py: another account's rows readable, and a foreign id answering "
                "unlike a missing one"),
    "setup": "two synthetic accounts; account A creates one result row",
    "teardown": "both accounts removed with the admin token",
    "destructive": False,
    "environment_sensitive": True,
}

READ, SAME = SPEC["subcases"]
COLLECTION = "take_home_attempts"
MISSING_ID = "zzzzzzzzzzzzzzz"


def _shape(resp) -> tuple[int, object]:
    return resp.status, resp.body


def run(ctx):
    ctx.ensure_content()
    a = ctx.new_account("ex02a")
    b = ctx.new_account("ex02b")
    created = ctx.pb.create(COLLECTION, a.token, {"user": a.user_id, "assignment": ctx.content["assignment"],
                                                  "status": "in-progress"})
    if created.status not in (200, 201) or not isinstance(created.body, dict):
        return inconclusive(READ, f"couldn't seed account A's result row (status {created.status})")
    row = created.body["id"]

    view = ctx.pb.view(COLLECTION, row, token=b.token)
    listing = ctx.pb.listing(COLLECTION, token=b.token, params={"filter": f"id='{row}'", "perPage": 50})
    missing = ctx.pb.view(COLLECTION, MISSING_ID, token=b.token)
    items = (listing.body or {}).get("items") or [] if isinstance(listing.body, dict) else []

    leaked = view.status == 200 or any(item.get("id") == row for item in items)
    same = _shape(view) == _shape(missing)
    evidence = {
        "answers": f"view {view.status}, listed {len(items)}, missing-id view {missing.status}",
    }
    subcases = {
        READ: Outcome.DETECTED.value if leaked else Outcome.CONTAINED.value,
        SAME: Outcome.CONTAINED.value if same and not leaked else Outcome.DETECTED.value,
    }
    if leaked:
        note = "account B read account A's result row"
    elif not same:
        note = "a foreign id answered differently from a missing one"
    else:
        note = f"account B couldn't read account A's result, and it read as missing (view {view.status})"
    return result(subcases, note, evidence=evidence)
