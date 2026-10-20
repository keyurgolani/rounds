"""Account-scope probe families.

Every enforced (collection, operation, actor) write cell has a probe here, so
a loosened rule plus an edited current_rules row cannot pass silently, and the
owner's own update is proven to still succeed. This is the PR that tightens the
create and update rules (ROUNDS-00B-L01 stage 3), so the foreign-owner and
reassign deny families land here together with the rule migration (orchestrator
decision D4: a gap's probes land in the PR that closes it); the PR proves the
negative control locally, that they fail on the pre-migration rules.

Expected statuses come from the policy's deny_contract, never hard-coded, so
changing the contract changes what the probes require.

A probe states the guarantee it checks (for example a foreign-owner create is
rejected); it is a regression check, not an attack recipe, and it records only
statuses and an owner-unchanged read-back, never record contents.
"""
from __future__ import annotations

import secrets
from typing import Callable

from factory import Account
from pbclient import PBClient
from receipts import Receipt


def _ids_in(body) -> set:
    if not isinstance(body, dict):
        return set()
    return {it.get("id") for it in (body.get("items") or []) if isinstance(it, dict)}


def list_cross_account_isolated(pb, collection, a, b, expected) -> Receipt:
    resp = pb.listing(collection, token=b.token)
    returned = _ids_in(resp.body)
    ok = resp.status == expected and a.ids[collection] not in returned and b.ids[collection] in returned
    detail = "" if ok else f"a_absent={a.ids[collection] not in returned} b_present={b.ids[collection] in returned}"
    return Receipt("account-scope.list.cross-account.isolated", collection, "list", "authenticated-other",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


def list_anonymous_isolated(pb, collection, a, b, expected) -> Receipt:
    resp = pb.listing(collection, token=None)
    returned = _ids_in(resp.body)
    ok = resp.status == expected and a.ids[collection] not in returned and b.ids[collection] not in returned
    return Receipt("account-scope.list.anonymous.isolated", collection, "list", "anonymous",
                   expected, resp.status, ok, resp.elapsed_ms, "" if ok else "foreign rows present in anonymous list")


def view_cross_account_denied(pb, collection, a, b, expected) -> Receipt:
    resp = pb.view(collection, a.ids[collection], token=b.token)
    return Receipt("account-scope.view.cross-account.denied", collection, "view", "authenticated-other",
                   expected, resp.status, resp.status == expected, resp.elapsed_ms)


def view_anonymous_denied(pb, collection, a, b, expected) -> Receipt:
    resp = pb.view(collection, a.ids[collection], token=None)
    return Receipt("account-scope.view.anonymous.denied", collection, "view", "anonymous",
                   expected, resp.status, resp.status == expected, resp.elapsed_ms)


def _owner_snapshot(pb, collection, a):
    """The owner's view of its own record: status and the whole record body."""
    resp = pb.view(collection, a.ids[collection], token=a.token)
    return resp.status, (resp.body if isinstance(resp.body, dict) else None)


def _denied_unchanged(pb, collection, a, attempt, expected):
    """Run a write attempt on `a`'s record and check it was denied and left the
    record exactly as it was (every field, `updated` included)."""
    before = _owner_snapshot(pb, collection, a)
    resp = attempt()
    after = _owner_snapshot(pb, collection, a)
    unchanged = before[0] == 200 and after == before
    ok = resp.status == expected and unchanged
    detail = "" if ok else f"status={resp.status} unchanged={unchanged} owner_view={after[0]}"
    return resp, ok, detail


def update_cross_account_denied(pb, collection, a, b, expected) -> Receipt:
    resp, ok, detail = _denied_unchanged(
        pb, collection, a, lambda: pb.update(collection, a.ids[collection], {}, token=b.token), expected)
    return Receipt("account-scope.update.cross-account.denied", collection, "update", "authenticated-other",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


def update_anonymous_denied(pb, collection, a, b, expected) -> Receipt:
    resp, ok, detail = _denied_unchanged(
        pb, collection, a, lambda: pb.update(collection, a.ids[collection], {}, token=None), expected)
    return Receipt("account-scope.update.anonymous.denied", collection, "update", "anonymous",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


def delete_cross_account_denied(pb, collection, a, b, expected) -> Receipt:
    resp, ok, detail = _denied_unchanged(
        pb, collection, a, lambda: pb.delete(collection, a.ids[collection], token=b.token), expected)
    return Receipt("account-scope.delete.cross-account.denied", collection, "delete", "authenticated-other",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


def delete_anonymous_denied(pb, collection, a, b, expected) -> Receipt:
    resp, ok, detail = _denied_unchanged(
        pb, collection, a, lambda: pb.delete(collection, a.ids[collection], token=None), expected)
    return Receipt("account-scope.delete.anonymous.denied", collection, "delete", "anonymous",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


def create_anonymous_denied(pb, collection, payload, admin_token, owner_id, expected) -> Receipt:
    # An anonymous create with a complete, valid, non-colliding body (built by
    # factory.fresh_payload). Because field, relation, and uniqueness
    # validation all pass, the only thing left to stop the write is the
    # createRule. A rule denial returns the deny-contract status with an empty
    # `data`; a field or uniqueness failure returns the same status with a
    # populated `data`, so we require `data` to be empty to prove the rule ran.
    # The superuser then confirms no row was left under the named owner.
    resp = pb.create(collection, None, payload)
    data = resp.body.get("data") if isinstance(resp.body, dict) else None
    leaked, listing_status = _admin_owner_count(pb, collection, admin_token, owner_id)
    ok = resp.status == expected and data == {} and leaked == 0
    detail = "" if ok else (
        f"status={resp.status} data={list((data or {}).keys())} {_owner_count_detail(leaked, listing_status)}"
    )
    return Receipt("account-scope.create.anonymous.denied", collection, "create", "anonymous",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


def oversized_input_rejected(pb, collection, token, payload, field, expected) -> Receipt:
    # An owner create whose body is valid except that one JSON field exceeds
    # its maxSize. PocketBase rejects it with a per-field size error.
    resp = pb.create(collection, token, payload)
    field_err = ""
    if isinstance(resp.body, dict):
        field_err = ((resp.body.get("data") or {}).get(field) or {}).get("code", "")
    ok = resp.status == expected and field_err == "validation_json_size_limit"
    return Receipt("account-scope.oversized-input.rejected", collection, "create", "authenticated-owner",
                   expected, resp.status, ok, resp.elapsed_ms, "" if ok else f"status={resp.status} field_code={field_err!r}")


def oversized_filler(max_bytes: int) -> list:
    return ["z" * (int(max_bytes) + 4096)]


def _admin_owner_count(pb, collection, admin_token, owner_id) -> tuple[int | None, int]:
    """How many rows the superuser sees owned by ``owner_id``, and the listing's status.

    A denied create must leave no row behind, not just return an error status.
    The owner used for this check is a no-rows account, so a clean deny leaves
    the count at zero. The count is None when the superuser listing fails or
    doesn't return a page, so a probe that needs it fails instead of passing on
    a check it never made.
    """
    resp = pb.listing(collection, token=admin_token, params={"filter": f'user = "{owner_id}"'})
    if resp.status != 200 or not isinstance(resp.body, dict):
        return None, resp.status
    total = resp.body.get("totalItems")
    if isinstance(total, int):
        return total, resp.status
    items = resp.body.get("items")
    return (len(items) if isinstance(items, list) else None), resp.status


def _owner_count_detail(count, listing_status) -> str:
    if count is None:
        return f"rows_under_owner=unknown (listing status={listing_status})"
    return f"rows_under_owner={count}"


def create_foreign_owner_denied(pb, collection, caller_token, payload, admin_token, owner_id, expected) -> Receipt:
    # An authenticated account tries to create a row owned by someone else. The
    # body is complete and valid (factory.fresh_payload) and names a different,
    # no-rows account as `user`, so field, relation, and uniqueness validation
    # all pass and only the createRule can stop the write. A rule denial is the
    # deny-contract status with empty `data` (a validation failure populates
    # `data`); the superuser then confirms no row was planted under that owner.
    resp = pb.create(collection, caller_token, payload)
    data = resp.body.get("data") if isinstance(resp.body, dict) else None
    leaked, listing_status = _admin_owner_count(pb, collection, admin_token, owner_id)
    ok = resp.status == expected and data == {} and leaked == 0
    detail = "" if ok else (
        f"status={resp.status} data={list((data or {}).keys())} {_owner_count_detail(leaked, listing_status)}"
    )
    return Receipt("account-scope.create.foreign-owner.denied", collection, "create", "authenticated-other",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


def update_reassign_denied(pb, collection, record_id, new_owner_id, owner_token, admin_token, original_owner_id, expected) -> Receipt:
    # The owner tries to move its own row to another account by resending
    # `user`. The owner rule matches the row, but the second clause rejects the
    # changed `user`, so the write is not found and the row keeps its owner.
    # The superuser reads the record before and after: the owner did not change,
    # and neither did anything else.
    before = pb.view(collection, record_id, token=admin_token)
    resp = pb.update(collection, record_id, {"user": new_owner_id}, token=owner_token)
    after = pb.view(collection, record_id, token=admin_token)
    owner_after = after.body.get("user") if isinstance(after.body, dict) else None
    unchanged = before.status == 200 and after.status == 200 and before.body == after.body
    ok = resp.status == expected and owner_after == original_owner_id and unchanged
    detail = "" if ok else f"status={resp.status} owner_after={owner_after!r} unchanged={unchanged}"
    return Receipt("account-scope.update.reassign-owner.denied", collection, "update", "authenticated-owner",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


def update_own_accepted(pb, collection, record_id, owner_id, owner_token, expected) -> Receipt:
    # The owner updates its own row in both client shapes the SPA uses: a
    # partial body that omits `user`, and a body that resends the owner's own
    # id. Both must still succeed under the tightened update rule.
    partial = pb.update(collection, record_id, {}, token=owner_token)
    resend = pb.update(collection, record_id, {"user": owner_id}, token=owner_token)
    ok = partial.status == expected and resend.status == expected
    detail = "" if ok else f"partial={partial.status} resend={resend.status}"
    return Receipt("account-scope.update.own.accepted", collection, "update", "authenticated-owner",
                   expected, partial.status, ok, partial.elapsed_ms, detail)


def create_server_only_denied(pb, collection, caller_token, payload, admin_token, owner_id, expected) -> Receipt:
    # A server-only collection (create rule null) rejects an authenticated
    # client create outright. An authenticated caller is the hardest to deny,
    # so denying it proves the rule admits no client; the superuser then
    # confirms no row was planted under the named owner.
    resp = pb.create(collection, caller_token, payload)
    leaked, listing_status = _admin_owner_count(pb, collection, admin_token, owner_id)
    ok = resp.status == expected and leaked == 0
    detail = "" if ok else f"status={resp.status} {_owner_count_detail(leaked, listing_status)}"
    return Receipt("account-scope.create.server-only.denied", collection, "create", "authenticated-other",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


def update_server_only_denied(pb, collection, record_id, owner_token, expected) -> Receipt:
    # A server-only collection (update rule null) rejects even the owner's own
    # update; the owner reads the row before and after, proving the deny is the
    # rule and not a missing record, and that the row is exactly as it was.
    before = pb.view(collection, record_id, token=owner_token)
    resp = pb.update(collection, record_id, {}, token=owner_token)
    still = pb.view(collection, record_id, token=owner_token)
    unchanged = before.status == 200 and still.status == 200 and before.body == still.body
    ok = resp.status == expected and unchanged
    detail = "" if ok else f"update={resp.status} owner_view={still.status} unchanged={unchanged}"
    return Receipt("account-scope.update.server-only.denied", collection, "update", "authenticated-owner",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


def create_superuser_accepted(pb, collection, admin_token, payload, expected) -> Receipt:
    # The superuser view-tracking insert still works after create becomes null.
    # The row names the same owner as the share link it points at, so it is not
    # a cross-owner relation and the clean scan stays empty.
    resp = pb.create(collection, admin_token, payload)
    ok = resp.status in (200, 201)
    detail = "" if ok else f"status={resp.status}"
    return Receipt("account-scope.create.superuser.accepted", collection, "create", "superuser",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


# --------------------------------------------------------------------------
# enumeration, inference, and replay (stage 4)
# --------------------------------------------------------------------------

_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def missing_record_id() -> str:
    """A well-formed PocketBase record id (15 lowercase alphanumerics) that no
    record has: random per call, so it can't collide with a seeded one."""
    return "".join(secrets.choice(_ID_ALPHABET) for _ in range(15))


def list_filter_isolated(pb, collection, a, b, expected) -> Receipt:
    # B lists with a filter naming A's record id and, where the collection has
    # an owner field, one naming A's account. The list rule still applies under
    # any filter, so both come back empty.
    filters = [f'id = "{a.ids[collection]}"']
    if collection != "users":
        filters.append(f'user = "{a.user_id}"')
    problems, last = [], None
    for flt in filters:
        last = pb.listing(collection, token=b.token, params={"filter": flt})
        items = last.body.get("items") if isinstance(last.body, dict) else None
        if last.status != expected or items != []:
            problems.append(f"status={last.status} rows={None if items is None else len(items)}")
    return Receipt("account-scope.list.filter.isolated", collection, "list", "authenticated-other",
                   expected, last.status, not problems, last.elapsed_ms, "; ".join(problems))


def _foreign_or_missing(op, pb, collection, a, b, expected) -> Receipt:
    # B tries the same operation on A's record and on an id no record has. Both
    # must answer the deny contract with byte-for-byte the same body, so the
    # answer says nothing about whether the record exists. A's record must come
    # out unchanged.
    missing = missing_record_id()
    call = {
        "view": lambda rid: pb.view(collection, rid, token=b.token),
        "update": lambda rid: pb.update(collection, rid, {}, token=b.token),
        "delete": lambda rid: pb.delete(collection, rid, token=b.token),
    }[op]
    before = _owner_snapshot(pb, collection, a)
    foreign = call(a.ids[collection])
    after = _owner_snapshot(pb, collection, a)
    absent = call(missing)
    same = foreign.status == absent.status and foreign.body == absent.body
    unchanged = before[0] == 200 and after == before
    ok = foreign.status == expected and same and unchanged
    detail = "" if ok else (f"foreign={foreign.status} missing={absent.status} "
                            f"same_body={foreign.body == absent.body} unchanged={unchanged}")
    return Receipt(f"account-scope.{op}.foreign-or-missing.indistinguishable", collection, op,
                   "authenticated-other", expected, foreign.status, ok, foreign.elapsed_ms, detail)


def view_foreign_or_missing(pb, collection, a, b, expected) -> Receipt:
    return _foreign_or_missing("view", pb, collection, a, b, expected)


def update_foreign_or_missing(pb, collection, a, b, expected) -> Receipt:
    return _foreign_or_missing("update", pb, collection, a, b, expected)


def delete_foreign_or_missing(pb, collection, a, b, expected) -> Receipt:
    return _foreign_or_missing("delete", pb, collection, a, b, expected)


def create_replayed_denied(pb, collection, caller_token, payload, admin_token, owner_id, expected, times=3) -> Receipt:
    # The same denied foreign-owner create, sent again unchanged. Nothing about
    # an earlier denial may let a later copy through: every copy is rejected by
    # the create rule (empty `data`) and no row is left under the named owner.
    statuses, rule_denials, last = [], 0, None
    for _ in range(times):
        last = pb.create(collection, caller_token, payload)
        statuses.append(last.status)
        if isinstance(last.body, dict) and last.body.get("data") == {}:
            rule_denials += 1
    leaked, listing_status = _admin_owner_count(pb, collection, admin_token, owner_id)
    ok = all(s == expected for s in statuses) and rule_denials == times and leaked == 0
    detail = "" if ok else f"statuses={statuses} rule_denials={rule_denials} {_owner_count_detail(leaked, listing_status)}"
    return Receipt("account-scope.create.replayed-denied.denied", collection, "create", "authenticated-other",
                   expected, last.status, ok, last.elapsed_ms, detail)


def create_nonexistent_owner_denied(pb, collection, caller_token, payload, admin_token, owner_id, expected) -> Receipt:
    # A create naming an owner id that no account has. It is denied with the
    # same status as one naming another account, and no row is left. Only the
    # status is compared: PocketBase checks that the named user exists before
    # the create rule runs, and the error body is an open exception for #13
    # (policy open_exceptions, owner-id-create-shape).
    resp = pb.create(collection, caller_token, payload)
    leaked, listing_status = _admin_owner_count(pb, collection, admin_token, owner_id)
    ok = resp.status == expected and leaked == 0
    detail = "" if ok else f"status={resp.status} {_owner_count_detail(leaked, listing_status)}"
    return Receipt("account-scope.create.nonexistent-owner.denied", collection, "create", "authenticated-other",
                   expected, resp.status, ok, resp.elapsed_ms, detail)


def runner_fails_closed_without_pocketbase(frontend: PBClient, collection, expected) -> Receipt:
    # PocketBase is stopped; the runner and the nginx frontend are up. A
    # take-home submit (a runner write) through nginx must fail closed: the
    # runner can't verify the bearer, so admission answers 503 auth_unavailable
    # before the route body runs, and nothing is written. The bearer is a
    # placeholder, since no token can be verified with PocketBase down.
    resp = frontend.post(
        "/api/take-home/submit",
        {"assignment_slug": "harness-fixture", "files": {"main.py": "x = 1"}},
        token="harness-degraded-placeholder",
    )
    code = resp.body.get("code") if isinstance(resp.body, dict) else None
    ok = resp.status == expected and code == "auth_unavailable"
    return Receipt("account-scope.runner.pocketbase-unreachable.fails-closed", collection, "create", "unverified",
                   expected, resp.status, ok, resp.elapsed_ms, "" if ok else f"status={resp.status} code={code!r}")


def signup_disabled_denied(pb, expected) -> Receipt:
    email = f"blocked-{secrets.token_hex(6)}@harness.invalid"
    password = "Hx" + secrets.token_hex(16) + "!9"
    resp = pb.signup(email, password)
    return Receipt("account-scope.signup.disabled.denied", "users", "create", "anonymous",
                   expected, resp.status, resp.status == expected, resp.elapsed_ms)


# Registry of IMPLEMENTED families. Pending families are deliberately absent.
# The uniform ones take (pb, collection, a, b, expected); create-anonymous,
# oversized, and the signup hook need extra inputs and are dispatched
# separately by run.py.
MAIN_FAMILIES: dict[str, Callable] = {
    "account-scope.list.cross-account.isolated": list_cross_account_isolated,
    "account-scope.list.anonymous.isolated": list_anonymous_isolated,
    "account-scope.view.cross-account.denied": view_cross_account_denied,
    "account-scope.view.anonymous.denied": view_anonymous_denied,
    "account-scope.update.cross-account.denied": update_cross_account_denied,
    "account-scope.update.anonymous.denied": update_anonymous_denied,
    "account-scope.delete.cross-account.denied": delete_cross_account_denied,
    "account-scope.delete.anonymous.denied": delete_anonymous_denied,
    "account-scope.list.filter.isolated": list_filter_isolated,
    "account-scope.view.foreign-or-missing.indistinguishable": view_foreign_or_missing,
    "account-scope.update.foreign-or-missing.indistinguishable": update_foreign_or_missing,
    "account-scope.delete.foreign-or-missing.indistinguishable": delete_foreign_or_missing,
}

CREATE_ANON_FAMILY = "account-scope.create.anonymous.denied"
OVERSIZED_FAMILY = "account-scope.oversized-input.rejected"
# Families this PR lands with the rule migration. Each needs an extra input
# (a specific caller token, the superuser token, a claimed owner, or a seeded
# record id), so run.py dispatches them directly rather than through
# MAIN_FAMILIES' (pb, collection, a, b, expected) shape.
FOREIGN_OWNER_FAMILY = "account-scope.create.foreign-owner.denied"
REASSIGN_FAMILY = "account-scope.update.reassign-owner.denied"
UPDATE_OWN_FAMILY = "account-scope.update.own.accepted"
SERVER_ONLY_CREATE_FAMILY = "account-scope.create.server-only.denied"
SERVER_ONLY_UPDATE_FAMILY = "account-scope.update.server-only.denied"
SUPERUSER_CREATE_FAMILY = "account-scope.create.superuser.accepted"
# Stage 4 creates, dispatched by run.py with a caller token, the superuser
# token, and the claimed owner.
REPLAY_FAMILY = "account-scope.create.replayed-denied.denied"
NONEXISTENT_OWNER_FAMILY = "account-scope.create.nonexistent-owner.denied"
HOOK_FAMILIES: dict[str, Callable] = {
    "account-scope.signup.disabled.denied": signup_disabled_denied,
}
# Run in the degraded phase, with PocketBase stopped and the runner and nginx
# frontend up.
DEGRADED_FAMILIES: dict[str, Callable] = {
    "account-scope.runner.pocketbase-unreachable.fails-closed": runner_fails_closed_without_pocketbase,
}

# Every family this harness knows how to run. The verdict cross-checks this
# against the policy: a family the policy marks "pending" must not be here.
IMPLEMENTED_FAMILIES = (
    set(MAIN_FAMILIES)
    | {CREATE_ANON_FAMILY, OVERSIZED_FAMILY}
    | {
        FOREIGN_OWNER_FAMILY,
        REASSIGN_FAMILY,
        UPDATE_OWN_FAMILY,
        SERVER_ONLY_CREATE_FAMILY,
        SERVER_ONLY_UPDATE_FAMILY,
        SUPERUSER_CREATE_FAMILY,
        REPLAY_FAMILY,
        NONEXISTENT_OWNER_FAMILY,
    }
    | set(HOOK_FAMILIES)
    | set(DEGRADED_FAMILIES)
)
