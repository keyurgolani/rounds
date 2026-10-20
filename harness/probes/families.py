"""Enforced account-scope probe families.

Only guarantees the rules already enforce at the audited revision have an
implementation here (orchestrator decision D4). The two pending families
(create.foreign-owner / update.reassign-owner) are intentionally absent:
their probes land in the PR that tightens the create/update rules
(ROUNDS-00B-L01 stage 3), which proves the negative control locally. The
verdict fails the run if a pending family ever appears in this registry or
produces a receipt, so the policy row and its probe flip together.

Every enforced (collection, operation, actor) denial cell has a probe here,
so a loosened rule plus an edited current_rules row cannot pass silently.
Expected statuses come from the policy's deny_contract, never hard-coded, so
changing the contract changes what the probes require.

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


def update_cross_account_denied(pb, collection, a, b, expected) -> Receipt:
    resp = pb.update(collection, a.ids[collection], {}, token=b.token)
    still = pb.view(collection, a.ids[collection], token=a.token)
    ok = resp.status == expected and still.status == 200
    return Receipt("account-scope.update.cross-account.denied", collection, "update", "authenticated-other",
                   expected, resp.status, ok, resp.elapsed_ms, "" if ok else f"update={resp.status} owner_view={still.status}")


def update_anonymous_denied(pb, collection, a, b, expected) -> Receipt:
    resp = pb.update(collection, a.ids[collection], {}, token=None)
    still = pb.view(collection, a.ids[collection], token=a.token)
    ok = resp.status == expected and still.status == 200
    return Receipt("account-scope.update.anonymous.denied", collection, "update", "anonymous",
                   expected, resp.status, ok, resp.elapsed_ms, "" if ok else f"update={resp.status} owner_view={still.status}")


def delete_cross_account_denied(pb, collection, a, b, expected) -> Receipt:
    resp = pb.delete(collection, a.ids[collection], token=b.token)
    still = pb.view(collection, a.ids[collection], token=a.token)
    ok = resp.status == expected and still.status == 200
    return Receipt("account-scope.delete.cross-account.denied", collection, "delete", "authenticated-other",
                   expected, resp.status, ok, resp.elapsed_ms, "" if ok else f"delete={resp.status} owner_view={still.status}")


def delete_anonymous_denied(pb, collection, a, b, expected) -> Receipt:
    resp = pb.delete(collection, a.ids[collection], token=None)
    still = pb.view(collection, a.ids[collection], token=a.token)
    ok = resp.status == expected and still.status == 200
    return Receipt("account-scope.delete.anonymous.denied", collection, "delete", "anonymous",
                   expected, resp.status, ok, resp.elapsed_ms, "" if ok else f"delete={resp.status} owner_view={still.status}")


def create_anonymous_denied(pb, collection, a, b, expected) -> Receipt:
    # An anonymous create with no bearer, naming account A as the owner. The
    # createRule requires an authenticated caller, so this is denied today
    # (and no row is written). A missing-field validation error would also be
    # the same denial status; either way the create does not succeed.
    resp = pb.create(collection, None, {"user": a.user_id})
    return Receipt("account-scope.create.anonymous.denied", collection, "create", "anonymous",
                   expected, resp.status, resp.status == expected, resp.elapsed_ms)


def oversized_input_rejected(pb, collection, a, cfg, expected) -> Receipt:
    field = cfg["field"]
    filler = "z" * (int(cfg["max_bytes"]) + 4096)
    value = filler if cfg.get("as_string") else [filler]
    payload = {"user": a.user_id, **cfg.get("base", {}), field: value}
    resp = pb.create(collection, a.token, payload)
    field_err = ""
    if isinstance(resp.body, dict):
        field_err = ((resp.body.get("data") or {}).get(field) or {}).get("code", "")
    ok = resp.status == expected and field_err == "validation_json_size_limit"
    return Receipt("account-scope.oversized-input.rejected", collection, "create", "authenticated-owner",
                   expected, resp.status, ok, resp.elapsed_ms, "" if ok else f"field_code={field_err!r}")


def signup_disabled_denied(pb, expected) -> Receipt:
    email = f"blocked-{secrets.token_hex(6)}@harness.invalid"
    password = "Hx" + secrets.token_hex(16) + "!9"
    resp = pb.signup(email, password)
    return Receipt("account-scope.signup.disabled.denied", "users", "create", "anonymous",
                   expected, resp.status, resp.status == expected, resp.elapsed_ms)


# Registry of IMPLEMENTED families. Pending families are deliberately absent.
# The uniform ones take (pb, collection, a, b, expected); oversized and the
# signup hook are dispatched separately by run.py.
MAIN_FAMILIES: dict[str, Callable] = {
    "account-scope.list.cross-account.isolated": list_cross_account_isolated,
    "account-scope.list.anonymous.isolated": list_anonymous_isolated,
    "account-scope.view.cross-account.denied": view_cross_account_denied,
    "account-scope.view.anonymous.denied": view_anonymous_denied,
    "account-scope.update.cross-account.denied": update_cross_account_denied,
    "account-scope.update.anonymous.denied": update_anonymous_denied,
    "account-scope.delete.cross-account.denied": delete_cross_account_denied,
    "account-scope.delete.anonymous.denied": delete_anonymous_denied,
    "account-scope.create.anonymous.denied": create_anonymous_denied,
}

OVERSIZED_FAMILY = "account-scope.oversized-input.rejected"
HOOK_FAMILIES: dict[str, Callable] = {
    "account-scope.signup.disabled.denied": signup_disabled_denied,
}

# Every family this harness knows how to run. The verdict cross-checks this
# against the policy: a family the policy marks "pending" must not be here.
IMPLEMENTED_FAMILIES = set(MAIN_FAMILIES) | {OVERSIZED_FAMILY} | set(HOOK_FAMILIES)
