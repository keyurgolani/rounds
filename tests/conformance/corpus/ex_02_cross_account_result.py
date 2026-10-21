"""EX-02: one account cannot read another account's result row.

Guarantee (the applicable part is closed by ROUNDS-00B-L01's account
scope; the job and quota sub-cases close with ROUNDS-00A-L03): a signed-in
account cannot read another account's execution result by id, and a
foreign id reads the same as one that does not exist. The contained
answer is 404 for the foreign row and no leak in a filtered list; a 200
that returns the other account's row is a finding.

The fixture makes two synthetic accounts, has A create one result row,
and has B try to read it by id and to list it under a filter naming A's
id. It touches only result ownership; the in-flight quota sub-cases are a
pending row for ROUNDS-00A-L03.
"""
from __future__ import annotations

from corpus._base import Result, contained, detected, inconclusive

_COLLECTION = "take_home_attempts"


def run(ctx) -> Result:
    ctx.ensure_content()
    a = ctx.new_account("ex02a")
    b = ctx.new_account("ex02b")
    with ctx.budget.spend():
        created = ctx.pb.create(
            _COLLECTION,
            a.token,
            {"user": a.user_id, "assignment": ctx.content["assignment"], "status": "in-progress"},
        )
    if created.status not in (200, 201) or not isinstance(created.body, dict):
        return inconclusive(f"could not seed account A's result row (status {created.status})")
    a_row = created.body["id"]

    with ctx.budget.spend():
        view = ctx.pb.view(_COLLECTION, a_row, token=b.token)
    with ctx.budget.spend():
        listing = ctx.pb.listing(
            _COLLECTION, token=b.token, params={"filter": f"id='{a_row}'", "perPage": 50}
        )
    items = (listing.body or {}).get("items") or [] if isinstance(listing.body, dict) else []
    leaked = view.status == 200 or any(it.get("id") == a_row for it in items)
    evidence = {"view_status": str(view.status), "list_items": str(len(items))}
    if leaked:
        return detected("account B read account A's result row", evidence=evidence)
    return contained(
        f"account B could not read account A's result (view {view.status}, {len(items)} listed)",
        evidence=evidence,
    )
