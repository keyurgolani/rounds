"""The owner's share capability routes at the runner (ROUNDS-00B-L03
stage 2).

The guarantees checked here:

  * the runner asks PocketBase's hook routes with the caller's own bearer,
    never the superuser's, and answers only the owner's fields;
  * revoking another account's capability, a missing one, and a malformed
    id get one 404, and a malformed id or a request body is refused before
    PocketBase is asked;
  * revoking again answers the same;
  * no PocketBase text reaches a response, and an answer of the wrong shape
    is a typed 503;
  * the revoke line names the account by pseudonym only.
"""
from __future__ import annotations

import json

import pytest

from app import errors, obs, share_capabilities
from conftest import TEST_ACCOUNT_ID, TEST_TOKEN

V = "share-capability/v1"
CAP = "capaaaaaaaaaaa1"
OTHER = "capbbbbbbbbbbb1"


def item(cid: str = CAP, **over) -> dict:
    row = {"id": cid, "status": "active", "revoked_reason": "", "purpose": "For recruiters",
           "expires_at": "2027-02-09 12:00:00.000Z", "created": "2026-11-11 12:00:00.000Z", "revoked_at": ""}
    row.update(over)
    return row


REVOKED = item(status="revoked", revoked_reason="owner", revoked_at="2026-11-12 09:00:00.000Z")


class FakeHooks:
    """PocketBase's two hook routes for one account: CAP is the caller's,
    OTHER is another account's, and anything else doesn't exist."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.list_answer: tuple[int, object] = (200, {"v": V, "items": [item(), item(OTHER)]})
        self.revoked = False
        self.revoke_answer: tuple[int, object] | None = None

    async def __call__(self, method: str, path: str, token: str):
        self.calls.append((method, path, token))
        if method == "GET":
            return self.list_answer
        if self.revoke_answer is not None:
            return self.revoke_answer
        if path == f"{share_capabilities.HOOK_PATH}/{CAP}/revoke":
            changed = not self.revoked
            self.revoked = True
            return 200, {"v": V, "capability": REVOKED, "changed": changed}
        return 404, {"v": V, "error": "not_found"}


@pytest.fixture
def hooks(monkeypatch, signed_in):
    fake = FakeHooks()
    monkeypatch.setattr(share_capabilities, "_hook", fake)
    return fake


def _body(res) -> dict:
    data = res.json()
    data.pop("correlation_id", None)
    return data


# ---- the list ----------------------------------------------------------------


def test_the_list_asks_with_the_callers_bearer_and_answers_only_the_owner_fields(client, hooks, signed_in):
    hooks.list_answer = (200, {"v": V, "items": [dict(item(), bearer_digest="d" * 64, snapshot="snapaaaaaaaaaa1",
                                                       user=TEST_ACCOUNT_ID, password_policy_ref="pw1$x")]})
    res = client.get("/api/share/capabilities", headers=signed_in)
    assert res.status_code == 200
    assert res.json() == [item()]
    assert hooks.calls == [("GET", share_capabilities.HOOK_PATH, TEST_TOKEN)]
    for leaked in ("d" * 64, "snapaaaaaaaaaa1", "pw1$x"):
        assert leaked not in res.text


def test_an_empty_list_is_empty(client, hooks, signed_in):
    hooks.list_answer = (200, {"v": V, "items": []})
    assert client.get("/api/share/capabilities", headers=signed_in).json() == []


@pytest.mark.parametrize("answer", [
    (200, {"v": V, "items": [item(id="short")]}),
    (200, {"v": V, "items": [item(status="paused")]}),
    (200, {"v": V, "items": [item(purpose=7)]}),
    (200, {"v": V, "items": "not a list"}),
    (200, {"v": "other/v9", "items": []}),
    (200, None),
    (500, {"code": 500, "message": "PocketBase secret detail", "data": {}}),
    (503, None),
])
def test_an_answer_of_any_other_shape_is_a_typed_503_with_no_pocketbase_text(client, hooks, signed_in, answer):
    hooks.list_answer = answer
    res = client.get("/api/share/capabilities", headers=signed_in)
    assert res.status_code == 503
    assert _body(res) == {"detail": errors.DETAILS["shares_unavailable"], "code": "shares_unavailable"}
    assert "PocketBase" not in res.text


def test_a_rejected_bearer_is_unauthenticated(client, hooks, signed_in):
    hooks.list_answer = (401, {"code": 401, "message": "The request requires valid record authorization token.", "data": {}})
    res = client.get("/api/share/capabilities", headers=signed_in)
    assert (res.status_code, res.json()["code"]) == (401, "unauthenticated")


def test_no_bearer_is_refused_before_pocketbase_is_asked(client, hooks):
    res = client.get("/api/share/capabilities")
    assert (res.status_code, res.json()["code"]) == (401, "unauthenticated")
    res = client.post(f"/api/share/capabilities/{CAP}/revoke")
    assert (res.status_code, res.json()["code"]) == (401, "unauthenticated")
    assert hooks.calls == []


# ---- revoke ------------------------------------------------------------------


def test_revoke_asks_with_the_callers_bearer_and_answers_the_owner_fields(client, hooks, signed_in):
    res = client.post(f"/api/share/capabilities/{CAP}/revoke", headers=signed_in)
    assert res.status_code == 200
    assert res.json() == REVOKED
    assert hooks.calls == [("POST", f"{share_capabilities.HOOK_PATH}/{CAP}/revoke", TEST_TOKEN)]


def test_revoking_again_answers_the_same(client, hooks, signed_in):
    first = client.post(f"/api/share/capabilities/{CAP}/revoke", headers=signed_in)
    again = client.post(f"/api/share/capabilities/{CAP}/revoke", headers=signed_in)
    assert (first.status_code, again.status_code) == (200, 200)
    assert first.json() == again.json()


def test_another_accounts_capability_answers_like_a_missing_one(client, hooks, signed_in):
    foreign = client.post(f"/api/share/capabilities/{OTHER}/revoke", headers=signed_in)
    missing = client.post("/api/share/capabilities/capmissingaaaa1/revoke", headers=signed_in)
    malformed = client.post("/api/share/capabilities/CAPAAAAAAAAAAA1/revoke", headers=signed_in)
    assert foreign.status_code == missing.status_code == malformed.status_code == 404
    assert _body(foreign) == _body(missing) == _body(malformed) == {"detail": "Not found.", "code": "not_found"}
    # The malformed id never reached PocketBase.
    assert [c[1] for c in hooks.calls] == [f"{share_capabilities.HOOK_PATH}/{OTHER}/revoke",
                                           f"{share_capabilities.HOOK_PATH}/capmissingaaaa1/revoke"]


@pytest.mark.parametrize("raw", [b'{"reason": "owner"}', b"[]", b"revoke"])
def test_a_revoke_with_a_body_is_refused_before_pocketbase_is_asked(client, hooks, signed_in, raw):
    res = client.post(f"/api/share/capabilities/{CAP}/revoke", content=raw,
                      headers={**signed_in, "Content-Type": "application/json"})
    assert (res.status_code, res.json()["code"]) == (400, "invalid_request")
    assert hooks.calls == []


@pytest.mark.parametrize("answer", [
    (200, {"v": V, "capability": item(OTHER), "changed": True}),
    (200, {"v": V, "capability": REVOKED}),
    (200, {"v": V, "capability": dict(REVOKED, status="gone"), "changed": True}),
    (404, {"code": 404, "message": "PocketBase secret detail", "data": {}}),
    (500, {"code": 500, "message": "PocketBase secret detail", "data": {}}),
])
def test_a_revoke_answer_of_any_other_shape_is_a_typed_503(client, hooks, signed_in, answer):
    hooks.revoke_answer = answer
    res = client.post(f"/api/share/capabilities/{CAP}/revoke", headers=signed_in)
    assert (res.status_code, res.json()["code"]) == (503, "shares_unavailable")
    assert "PocketBase" not in res.text


# ---- logs ----------------------------------------------------------------------


def test_the_revoke_line_names_the_account_by_pseudonym_only(client, hooks, signed_in, capsys):
    capsys.readouterr()
    client.post(f"/api/share/capabilities/{CAP}/revoke", headers=signed_in)
    client.post(f"/api/share/capabilities/{CAP}/revoke", headers=signed_in)
    client.post(f"/api/share/capabilities/{OTHER}/revoke", headers=signed_in)
    out = capsys.readouterr().out
    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{") and '"share.revoke"' in line]
    assert [(line["code"], line.get("record")) for line in lines] == [
        ("revoked", CAP), ("unchanged", CAP), ("not_found", None)]
    for line in lines:
        assert line["account"] == obs.account_pseudonym(TEST_ACCOUNT_ID)
        assert set(line) <= {"v", "event", "correlation_id", "account", "record", "code"}
    assert TEST_TOKEN not in out and f'"{TEST_ACCOUNT_ID}"' not in out
