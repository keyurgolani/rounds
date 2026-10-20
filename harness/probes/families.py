"""Enforced account-scope probe families.

Only guarantees the rules already enforce at the audited revision have an
implementation here (orchestrator decision D4). The two pending families
(create.foreign-owner / update.reassign-owner) are intentionally absent:
their probes land in the PR that tightens the create/update rules
(ROUNDS-00B-L01 stage 3), which proves the negative control locally. The
verdict fails the run if a pending family ever appears in this registry or
produces a receipt, so the policy row and the probe flip together.

A probe states the guarantee it checks (for example a foreign-owner read
returns not-found); it is a regression check, not an attack recipe, and it
records only statuses, never record contents.
"""
from __future__ import annotations

import secrets
from typing import Callable

from factory import Account
from pbclient import PBClient
from receipts import Receipt


def _ids_in(body) -> set[str]:
    if not isinstance(body, dict):
        return set()
    return {it.get("id") for it in (body.get("items") or []) if isinstance(it, dict)}


def list_cross_account_isolated(
    pb: PBClient, collection: str, a: Account, b: Account
) -> Receipt:
    """Account B's own list never contains account A's row."""
    a_id = a.ids[collection]
    b_id = b.ids[collection]
    resp = pb.listing(collection, token=b.token)
    returned = _ids_in(resp.body)
    ok = resp.status == 200 and a_id not in returned and b_id in returned
    detail = "" if ok else f"a_absent={a_id not in returned} b_present={b_id in returned}"
    return Receipt(
        probe_id="account-scope.list.cross-account.isolated",
        collection=collection,
        operation="list",
        actor="authenticated-other",
        expected_status=200,
        observed_status=resp.status,
        passed=ok,
        request_time_ms=resp.elapsed_ms,
        detail=detail,
    )


def list_anonymous_isolated(
    pb: PBClient, collection: str, a: Account, b: Account
) -> Receipt:
    """An anonymous list returns neither account's rows."""
    resp = pb.listing(collection, token=None)
    returned = _ids_in(resp.body)
    ok = resp.status == 200 and a.ids[collection] not in returned and b.ids[collection] not in returned
    return Receipt(
        probe_id="account-scope.list.anonymous.isolated",
        collection=collection,
        operation="list",
        actor="anonymous",
        expected_status=200,
        observed_status=resp.status,
        passed=ok,
        request_time_ms=resp.elapsed_ms,
        detail="" if ok else "foreign rows present in anonymous list",
    )


def view_cross_account_denied(
    pb: PBClient, collection: str, a: Account, b: Account
) -> Receipt:
    """Account B cannot read account A's record by id."""
    resp = pb.view(collection, a.ids[collection], token=b.token)
    ok = resp.status == 404
    return Receipt(
        probe_id="account-scope.view.cross-account.denied",
        collection=collection,
        operation="view",
        actor="authenticated-other",
        expected_status=404,
        observed_status=resp.status,
        passed=ok,
        request_time_ms=resp.elapsed_ms,
    )


def view_anonymous_denied(
    pb: PBClient, collection: str, a: Account, b: Account
) -> Receipt:
    """An anonymous caller cannot read account A's record by id."""
    resp = pb.view(collection, a.ids[collection], token=None)
    ok = resp.status == 404
    return Receipt(
        probe_id="account-scope.view.anonymous.denied",
        collection=collection,
        operation="view",
        actor="anonymous",
        expected_status=404,
        observed_status=resp.status,
        passed=ok,
        request_time_ms=resp.elapsed_ms,
    )


def delete_cross_account_denied(
    pb: PBClient, collection: str, a: Account, b: Account
) -> Receipt:
    """Account B cannot delete account A's record; A's row survives."""
    resp = pb.delete(collection, a.ids[collection], token=b.token)
    still = pb.view(collection, a.ids[collection], token=a.token)
    ok = resp.status == 404 and still.status == 200
    detail = "" if ok else f"delete={resp.status} owner_view={still.status}"
    return Receipt(
        probe_id="account-scope.delete.cross-account.denied",
        collection=collection,
        operation="delete",
        actor="authenticated-other",
        expected_status=404,
        observed_status=resp.status,
        passed=ok,
        request_time_ms=resp.elapsed_ms,
        detail=detail,
    )


def signup_disabled_denied(pb: PBClient, collection: str, a, b) -> Receipt:
    """With signups disabled, a signup request is rejected by the hook."""
    email = f"blocked-{secrets.token_hex(6)}@harness.invalid"
    password = "Hx" + secrets.token_hex(16) + "!9"
    resp = pb.signup(email, password)
    ok = resp.status == 400
    return Receipt(
        probe_id="account-scope.signup.disabled.denied",
        collection="users",
        operation="create",
        actor="anonymous",
        expected_status=400,
        observed_status=resp.status,
        passed=ok,
        request_time_ms=resp.elapsed_ms,
    )


# Registry of IMPLEMENTED families. Pending families are deliberately absent.
# phase: "main" runs against each applicable collection with two live
# accounts; "hook" runs once after PocketBase restarts with signups disabled.
MAIN_FAMILIES: dict[str, Callable[[PBClient, str, Account, Account], Receipt]] = {
    "account-scope.list.cross-account.isolated": list_cross_account_isolated,
    "account-scope.list.anonymous.isolated": list_anonymous_isolated,
    "account-scope.view.cross-account.denied": view_cross_account_denied,
    "account-scope.view.anonymous.denied": view_anonymous_denied,
    "account-scope.delete.cross-account.denied": delete_cross_account_denied,
}

HOOK_FAMILIES: dict[str, Callable[[PBClient, str, Account, Account], Receipt]] = {
    "account-scope.signup.disabled.denied": signup_disabled_denied,
}

# Every family this harness knows how to run. The verdict cross-checks this
# against the policy: a family the policy marks "pending" must not be here.
IMPLEMENTED_FAMILIES = set(MAIN_FAMILIES) | set(HOOK_FAMILIES)
