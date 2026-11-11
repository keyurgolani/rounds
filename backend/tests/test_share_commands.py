"""CreateShare and RotateShareBearer at the runner (ROUNDS-00B-L04,
app/share_commands.py).

The guarantees checked here:

  * a share link's bearer is in the one response that issues it, and
    PocketBase gets only its digest and, for a password, a pw1 verifier;
  * a retry under the same Idempotency-Key answers the same capability with
    already-issued and no bearer, and makes nothing again;
  * the fingerprint sees whether a password was set, never the password;
  * the key is required whatever ENFORCE_IDEMPOTENCY says;
  * a bad body is a fixed 400 that repeats nothing, never FastAPI's 422;
  * the snapshot step is #4's command, admitted as snapshot_create under
    the key the command's row keeps, so a retry gets the same snapshot, and
    a source edited since is 409 snapshot_conflict;
  * #4's ineligible answers as it is, with no capability made;
  * a rotation shows the new bearer once and answers a stale version, a
    revoked or expired capability, and another account's as the contract
    says;
  * with the gate closed, POST /api/share is the create it was, and rotate
    is turned off;
  * no line holds a bearer or a password.

PocketBase's hook routes are a fake with their contract here; the hooks
themselves run under node (pocketbase/tests/test_share_secrets_hooks.py).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app import admission_state, gates, legacy_snapshots, obs, share_commands, share_password, share_secrets
from app.errors import DETAILS, TypedError
from conftest import TEST_ACCOUNT_ID, TEST_TOKEN

V = "share-secrets/v1"
GATE = "ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION"
SECRET = "share-commands-test-ai-key-secret-0123456789"
KEY = "0190f000-0000-7000-8000-00000000000a"
OTHER_KEY = "0190f000-0000-7000-8000-00000000000b"
RESUME = "resumeaaaaaaaa1"
VARIANT = "variantaaaaaaa1"
SNAPSHOT = "snapaaaaaaaaaa1"
OTHERS = "capbbbbbbbbbbb1"
PASSWORD = "correct horse battery"
UPDATED = "2026-11-10 10:00:00.000Z"
LATER = "2027-02-09 12:00:00.000Z"


class FakeShareHooks:
    """share_secrets.js's three command routes for the signed-in account,
    in memory: begin, create, and rotate, each one transaction that keeps
    nothing when it refuses. OTHERS is another account's capability."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.commands: dict[str, dict] = {}
        self.capabilities: dict[str, dict] = {OTHERS: {"owner": "u2", "status": "active", "version": 1,
                                                       "expires_at": LATER, "digest": "e" * 64}}
        self.answers: dict[str, tuple[int, object]] = {}
        self.made = 0

    async def __call__(self, path: str, token: str, payload: dict):
        self.calls.append((path, token, json.loads(json.dumps(payload))))
        kind = "begin" if path == share_commands.BEGIN_PATH else (
            "create" if path == share_commands.CAPABILITIES_PATH else "rotate")
        if kind in self.answers:
            return self.answers[kind]
        return getattr(self, kind)(path, payload)

    def paths(self) -> list[str]:
        return [path for path, _, _ in self.calls]

    def _begin(self, key: str, operation: str, fingerprint: str):
        command = self.commands.get(key)
        if command is None:
            command = self.commands[key] = {"operation": operation, "fingerprint": fingerprint,
                                            "state": "in_flight", "result": None, "snapshot": None}
            return "new", command
        if command["operation"] != operation or command["fingerprint"] != fingerprint:
            return "mismatch", None
        return ("replay" if command["state"] == "completed" else "retry"), command

    @staticmethod
    def _refuse(verdict: str, key: str, commands: dict, status: int, code: str):
        if verdict == "new":
            del commands[key]
        return status, {"v": V, "error": code}

    def begin(self, _path, p):
        verdict, command = self._begin(p["command_id"], p["operation"], p["fingerprint"])
        if verdict == "mismatch":
            return 409, {"v": V, "error": "idempotency_mismatch"}
        if verdict == "replay":
            return 200, {"v": V, "verdict": "replay", "result": command["result"]}
        if command["snapshot"] is None:
            command["snapshot"] = p["snapshot_command_id"]
        return 200, {"v": V, "verdict": verdict, "snapshot_command_id": command["snapshot"]}

    def create(self, _path, p):
        verdict, command = self._begin(p["command_id"], "share_create", p["fingerprint"])
        if verdict == "mismatch":
            return 409, {"v": V, "error": "idempotency_mismatch"}
        if verdict == "replay":
            return 200, {"v": V, "delivery": "already_issued", "result": command["result"]}
        if p["snapshot_id"] != SNAPSHOT:
            return self._refuse(verdict, p["command_id"], self.commands, 404, "not_found")
        self.made += 1
        cid = f"capnew{self.made:09d}"
        self.capabilities[cid] = {"owner": TEST_ACCOUNT_ID, "status": "active", "version": 1,
                                  "expires_at": p["expires_at"] or LATER, "digest": p["bearer_digest"],
                                  "verifier": p["password_policy_ref"]}
        result = {"status": 201, "body": {
            "capability_id": cid,
            "scope": {"target_kind": "legacy_artifact_snapshot", "resume_id": RESUME, "projection_version": 1},
            "state": "active", "expires_at": self.capabilities[cid]["expires_at"], "capability_version": 1}}
        command["state"], command["result"] = "completed", result
        return 201, {"v": V, "delivery": "issued", "result": result}

    def rotate(self, path, p):
        cid = path.split("/")[-2]
        verdict, command = self._begin(p["command_id"], "share_rotate", p["fingerprint"])
        if verdict == "mismatch":
            return 409, {"v": V, "error": "idempotency_mismatch"}
        if verdict == "replay":
            return 200, {"v": V, "delivery": "already_issued", "result": command["result"]}
        cap = self.capabilities.get(cid)
        if cap is None or cap["owner"] != TEST_ACCOUNT_ID:
            return self._refuse(verdict, p["command_id"], self.commands, 404, "not_found")
        if cap["status"] != "active":
            return self._refuse(verdict, p["command_id"], self.commands, 409, "capability_revoked")
        if cap["expires_at"] < "2026":
            return self._refuse(verdict, p["command_id"], self.commands, 409, "capability_expired")
        if cap["version"] != p["expected_capability_version"]:
            return self._refuse(verdict, p["command_id"], self.commands, 409, "capability_version_conflict")
        cap["digest"], cap["version"] = p["bearer_digest"], cap["version"] + 1
        result = {"status": 200, "body": {"capability_id": cid, "state": "active", "expires_at": cap["expires_at"],
                                          "capability_version": cap["version"]}}
        command["state"], command["result"] = "completed", result
        return 200, {"v": V, "delivery": "issued", "result": result}


class FakeSnapshots:
    """#4's snapshot hook as the runner's legacy_snapshots.create calls it."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict, str | None]] = []
        self.answer: tuple[int, dict] | TypedError = (201, {
            "status": "created", "snapshot_id": SNAPSHOT, "content_checksum": "sha256:" + "c" * 64})

    async def create(self, token, req, command_id):
        self.calls.append((token, req.model_dump(), command_id))
        if isinstance(self.answer, TypedError):
            raise self.answer
        return self.answer


class FakeSources:
    def __init__(self) -> None:
        self.updated = {RESUME: UPDATED, VARIANT: UPDATED}

    async def pb_get(self, token, path, params=None):
        source = path.rsplit("/", 1)[-1]
        if token != TEST_TOKEN or source not in self.updated:
            raise HTTPException(status_code=404, detail="The requested resource wasn't found.")
        return {"id": source, "updated": self.updated[source]}


@pytest.fixture
def world(monkeypatch, signed_in):
    monkeypatch.setenv("AI_KEY_SECRET", SECRET)
    monkeypatch.setenv(GATE, "enabled")
    monkeypatch.setattr(gates, "_snapshot", gates.load({"ROUNDS_GATE_LEGACY_SNAPSHOT_CREATE": "enabled"},
                                                       gates.RUNNER))
    hooks, snapshots, sources = FakeShareHooks(), FakeSnapshots(), FakeSources()
    monkeypatch.setattr(share_commands, "_hook", hooks)
    monkeypatch.setattr(legacy_snapshots, "create", snapshots.create)
    monkeypatch.setattr(share_commands, "pb_get", sources.pb_get)

    class World:
        pass

    w = World()
    w.hooks, w.snapshots, w.sources, w.headers = hooks, snapshots, sources, signed_in
    return w


def create(client, world, body=None, key: str | None = KEY, **kwargs):
    headers = dict(world.headers)
    if key is not None:
        headers["Idempotency-Key"] = key
    if "content" not in kwargs:
        kwargs["content"] = json.dumps({"resume_id": RESUME} if body is None else body)
        headers.setdefault("Content-Type", "application/json")
    headers.update(kwargs.pop("extra_headers", {}))
    return client.post("/api/share", headers=headers, **kwargs)


def rotate(client, world, cid, version=1, key: str | None = OTHER_KEY, body=None, **kwargs):
    headers = dict(world.headers, **{"Content-Type": "application/json"})
    if key is not None:
        headers["Idempotency-Key"] = key
    content = json.dumps({"expected_capability_version": version} if body is None else body)
    return client.post(f"/api/share/capabilities/{cid}/rotate", headers=headers, content=content, **kwargs)


def _typed(res) -> tuple[int, str]:
    return res.status_code, res.json().get("code")


def everything_sent(world, admission_store) -> str:
    return json.dumps([world.hooks.calls, world.snapshots.calls, admission_store.calls], default=str)


# ---- CreateShare: the bearer once -------------------------------------------------------------------------


def test_a_create_shows_the_bearer_once_and_sends_pocketbase_only_its_digest(client, world, admission_store):
    res = create(client, world)
    assert res.status_code == 201
    body = res.json()
    assert list(body) == ["capability_id", "scope", "state", "expires_at", "capability_version", "secret_delivery",
                          "token"]
    assert body["secret_delivery"] == "issued"
    assert body["scope"] == {"target_kind": "legacy_artifact_snapshot", "resume_id": RESUME, "projection_version": 1}
    token = body["token"]
    assert share_secrets.current(token)
    assert res.headers["cache-control"] == "no-store"
    made = [p for path, _, p in world.hooks.calls if path == share_commands.CAPABILITIES_PATH]
    assert made[0]["bearer_digest"] == share_secrets.digest(token)
    assert made[0]["password_policy_ref"] == "" and made[0]["digest_key_version"] == 1
    assert token not in everything_sent(world, admission_store)


def test_a_retry_with_the_same_key_is_already_issued_without_the_bearer(client, world):
    first = create(client, world).json()
    again = create(client, world)
    assert again.status_code == 200
    body = again.json()
    assert body.pop("secret_delivery") == "already-issued"
    assert "token" not in body
    assert body == {k: v for k, v in first.items() if k not in ("token", "secret_delivery")}
    # Nothing ran again: no snapshot, no capability.
    assert len(world.snapshots.calls) == 1
    assert world.hooks.paths().count(share_commands.CAPABILITIES_PATH) == 1
    assert first["token"] not in again.text


def test_a_create_that_lost_the_race_to_its_own_retry_is_already_issued(client, world):
    first = create(client, world).json()
    result = world.hooks.commands[KEY]["result"]
    world.hooks.commands.clear()
    world.hooks.answers["create"] = (200, {"v": V, "delivery": "already_issued", "result": result})
    res = create(client, world)
    assert res.status_code == 200 and res.json()["secret_delivery"] == "already-issued"
    assert res.json()["capability_id"] == first["capability_id"] and "token" not in res.json()


def test_a_password_reaches_pocketbase_only_as_a_pw1_verifier(client, world, admission_store, capsys):
    res = create(client, world, {"resume_id": RESUME, "password": PASSWORD})
    assert res.status_code == 201
    (made,) = [p for path, _, p in world.hooks.calls if path == share_commands.CAPABILITIES_PATH]
    assert share_password.is_current(made["password_policy_ref"])
    sent = everything_sent(world, admission_store)
    assert PASSWORD not in sent and PASSWORD not in capsys.readouterr().out


def test_the_fingerprint_sees_that_a_password_was_set_never_the_password(client, world):
    first = create(client, world, {"resume_id": RESUME, "password": PASSWORD})
    other_password = create(client, world, {"resume_id": RESUME, "password": "a different password"})
    no_password = create(client, world, {"resume_id": RESUME})
    assert first.status_code == 201
    # The same request but for the password's value: the same command.
    assert (other_password.status_code, other_password.json()["secret_delivery"]) == (200, "already-issued")
    # Without one, another request under the same key.
    assert _typed(no_password) == (409, "idempotency_mismatch")


def test_the_key_is_required_whatever_enforce_idempotency_says(client, world, monkeypatch):
    monkeypatch.setattr(gates, "_snapshot", gates.load({"ROUNDS_GATE_LEGACY_SNAPSHOT_CREATE": "enabled",
                                                        "ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "off"}, gates.RUNNER))
    res = create(client, world, key=None)
    assert _typed(res) == (400, "idempotency_key_required")
    assert world.hooks.calls == []


def test_no_bearer_is_401_before_anything(client, world):
    res = client.post("/api/share", content=json.dumps({"resume_id": RESUME}),
                      headers={"Content-Type": "application/json", "Idempotency-Key": KEY})
    assert _typed(res) == (401, "unauthenticated")
    assert world.hooks.calls == []


ECHO = "echo-me-if-you-can"
BAD_BODIES = {
    "unknown field": dict(body={"resume_id": RESUME, "note": ECHO}),
    "both targets": dict(body={"resume_id": RESUME, "variant_id": VARIANT}),
    "no target": dict(body={"purpose": ECHO}),
    "odd id": dict(body={"resume_id": ECHO}),
    "short password": dict(body={"resume_id": RESUME, "password": "short"}),
    "long password": dict(body={"resume_id": RESUME, "password": "p" * 129}),
    "number password": dict(body={"resume_id": RESUME, "password": 12345678}),
    "long purpose": dict(body={"resume_id": RESUME, "purpose": ECHO * 10}),
    "odd day": dict(body={"resume_id": RESUME, "expires_at": "2026-13-01"}),
    "past day": dict(body={"resume_id": RESUME, "expires_at": "2020-01-01"}),
    "not a day": dict(body={"resume_id": RESUME, "expires_at": ECHO}),
    "an array": dict(body=[RESUME, ECHO]),
    "not json": dict(content=b"{resume_id: " + ECHO.encode()),
    "text media": dict(content=json.dumps({"resume_id": RESUME}).encode(), extra_headers={"Content-Type": "text/plain"}),
    "over 4 KiB": dict(content=json.dumps({"resume_id": RESUME, "purpose": "x" * 5000}).encode()),
}


@pytest.mark.parametrize("case", list(BAD_BODIES))
def test_a_bad_body_is_a_fixed_400_that_repeats_nothing(client, world, case):
    res = create(client, world, **BAD_BODIES[case])
    assert res.status_code == 400
    assert {k: v for k, v in res.json().items() if k != "correlation_id"} == {
        "detail": DETAILS["invalid_request"], "code": "invalid_request"}
    assert ECHO not in res.text and "short" not in res.text
    assert world.hooks.calls == [] and world.snapshots.calls == []


def test_the_expiry_is_the_end_of_the_chosen_day_in_utc_within_the_most_allowed():
    now = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
    assert share_commands.expiry(None, now) is None
    assert share_commands.expiry("2026-12-01", now) == "2026-12-01 23:59:59.999Z"
    assert share_commands.expiry("2026-11-11", now) == "2026-11-11 23:59:59.999Z"
    latest = now + timedelta(days=365) - timedelta(seconds=60)
    assert share_commands.expiry("2027-11-11", now) == latest.strftime("%Y-%m-%d %H:%M:%S.000Z")
    for day in ("2026-11-10", "2026-02-30"):
        with pytest.raises(TypedError):
            share_commands.expiry(day, now)


# ---- CreateShare: the snapshot step ---------------------------------------------------------------------


def test_the_snapshot_runs_as_snapshot_create_under_the_key_the_row_keeps(client, world, admission_store):
    assert create(client, world).status_code == 201
    kept = world.hooks.commands[KEY]["snapshot"]
    assert admission_state.COMMAND_ID.fullmatch(kept) and kept != KEY
    (admit,) = admission_store.called("admit")
    req = legacy_snapshots.SnapshotRequest(source_kind="resume", source_id=RESUME, expected_updated=UPDATED)
    assert (admit["operation"], admit["key"], admit["mode"]) == ("snapshot_create", kept, "enforce")
    assert admit["fingerprint"] == admission_state.fingerprint("POST /api/pdf/snapshots", "snapshot_create", req)
    assert world.snapshots.calls == [(TEST_TOKEN, req.model_dump(), kept)]
    (finish,) = admission_store.called("finish")
    assert finish["outcome"] == "completed"


def test_a_retry_after_a_failed_write_reuses_the_first_snapshot(client, world):
    world.hooks.answers["create"] = (503, {"v": V, "error": "unavailable"})
    assert _typed(create(client, world)) == (503, "shares_unavailable")
    del world.hooks.answers["create"]
    res = create(client, world)
    assert res.status_code == 201
    # The snapshot command replayed; #4's hook ran once.
    assert len(world.snapshots.calls) == 1
    made = [p for path, _, p in world.hooks.calls if path == share_commands.CAPABILITIES_PATH]
    assert [p["snapshot_id"] for p in made] == [SNAPSHOT, SNAPSHOT]


def test_a_source_edited_since_the_first_attempt_is_a_snapshot_conflict(client, world):
    world.hooks.answers["create"] = (503, {"v": V, "error": "unavailable"})
    create(client, world)
    del world.hooks.answers["create"]
    world.sources.updated[RESUME] = "2026-11-11 09:00:00.000Z"
    res = create(client, world)
    assert _typed(res) == (409, "snapshot_conflict")
    assert world.hooks.paths().count(share_commands.CAPABILITIES_PATH) == 1


def test_an_ineligible_source_answers_as_it_is_and_makes_no_capability(client, world):
    world.snapshots.answer = (200, {"status": "ineligible", "snapshot_id": None, "content_checksum": None,
                                    "reason": "demo_account"})
    res = create(client, world)
    assert (res.status_code, res.json()) == (200, {"status": "ineligible", "reason": "demo_account"})
    assert share_commands.CAPABILITIES_PATH not in world.hooks.paths()


@pytest.mark.parametrize("code", ["snapshot_conflict", "materializer_unavailable", "snapshot_quota_exceeded"])
def test_the_snapshot_commands_refusals_pass_on_and_make_no_capability(client, world, code):
    world.snapshots.answer = TypedError(code)
    assert _typed(create(client, world))[1] == code
    assert share_commands.CAPABILITIES_PATH not in world.hooks.paths()


def test_a_missing_or_another_accounts_source_is_one_not_found(client, world):
    missing = create(client, world, {"resume_id": "resumemissing01"})
    assert _typed(missing) == (404, "not_found")
    assert world.snapshots.calls == []


def test_the_snapshot_gate_off_is_route_disabled(client, world, monkeypatch):
    monkeypatch.setattr(gates, "_snapshot", gates.load({}, gates.RUNNER))
    assert _typed(create(client, world)) == (503, "route_disabled")
    assert world.snapshots.calls == []


def test_no_digest_key_is_503_before_pocketbase_is_asked(client, world, monkeypatch):
    monkeypatch.delenv("AI_KEY_SECRET")
    assert _typed(create(client, world)) == (503, "shares_unavailable")
    assert world.hooks.calls == []


@pytest.mark.parametrize("answer, want", [
    ((404, {"v": V, "error": "not_found"}), (404, "not_found")),
    ((400, {"v": V, "error": "invalid_request"}), (400, "invalid_request")),
    ((409, {"v": V, "error": "idempotency_mismatch"}), (409, "idempotency_mismatch")),
    ((401, {"code": 401, "message": "PocketBase detail", "data": {}}), (401, "unauthenticated")),
    ((500, {"code": 500, "message": "PocketBase detail", "data": {}}), (503, "shares_unavailable")),
    ((201, {"v": V, "delivery": "issued", "result": {"status": 201, "body": {"capability_id": "short"}}}),
     (503, "shares_unavailable")),
    ((201, {"v": V, "delivery": "already_issued", "result": None}), (503, "shares_unavailable")),
])
def test_each_write_answer_maps_to_one_typed_answer_with_no_pocketbase_text(client, world, answer, want):
    world.hooks.answers["create"] = answer
    res = create(client, world)
    assert _typed(res) == want
    assert "PocketBase" not in res.text and "token" not in res.json()


def test_with_the_gate_closed_post_api_share_is_the_create_it_was(client, world, monkeypatch):
    from routers import share

    monkeypatch.setenv(GATE, "disabled")
    sent = {}

    async def current_user(_request):
        return {"id": TEST_ACCOUNT_ID, "token": TEST_TOKEN}

    async def pb_post(_token, _path, payload):
        sent.update(payload)
        return {"id": "lnk000000000001", **payload, "created": ""}

    monkeypatch.setattr(share, "current_user", current_user)
    monkeypatch.setattr(share, "pb_post", pb_post)
    res = client.post("/api/share", json={"resume_id": RESUME}, headers=world.headers)
    assert res.status_code == 200 and set(res.json()) == {"id", "token", "resume_id", "variant_id", "created"}
    assert world.hooks.calls == []
    # Its body checks are FastAPI's, as before.
    assert client.post("/api/share", json={"resume_id": 5}, headers=world.headers).status_code == 422


# ---- RotateShareBearer --------------------------------------------------------------------------------------


def _made(client, world) -> dict:
    body = create(client, world).json()
    return body


def test_rotate_shows_a_new_bearer_once_and_swaps_the_digest(client, world, admission_store):
    first = _made(client, world)
    cid = first["capability_id"]
    res = rotate(client, world, cid)
    assert res.status_code == 200
    body = res.json()
    assert list(body) == ["capability_id", "state", "expires_at", "capability_version", "secret_delivery", "token"]
    assert (body["capability_id"], body["capability_version"], body["secret_delivery"]) == (cid, 2, "issued")
    assert share_secrets.current(body["token"]) and body["token"] != first["token"]
    assert world.hooks.capabilities[cid]["digest"] == share_secrets.digest(body["token"])
    assert res.headers["cache-control"] == "no-store"
    assert body["token"] not in everything_sent(world, admission_store)


def test_a_duplicate_rotate_key_is_already_issued_without_a_bearer(client, world):
    cid = _made(client, world)["capability_id"]
    first = rotate(client, world, cid).json()
    again = rotate(client, world, cid)
    assert again.status_code == 200
    assert again.json() == {k: v for k, v in first.items() if k != "token"} | {"secret_delivery": "already-issued"}
    assert world.hooks.capabilities[cid]["version"] == 2


@pytest.mark.parametrize("setup, want", [
    (lambda caps, cid: None, None),
    (lambda caps, cid: caps[cid].update(version=2), (409, "capability_version_conflict")),
    (lambda caps, cid: caps[cid].update(status="revoked"), (409, "capability_revoked")),
    (lambda caps, cid: caps[cid].update(expires_at="2020-01-01 00:00:00.000Z"), (409, "capability_expired")),
])
def test_a_rotation_that_cannot_happen_answers_its_conflict(client, world, setup, want):
    cid = _made(client, world)["capability_id"]
    setup(world.hooks.capabilities, cid)
    res = rotate(client, world, cid)
    if want is None:
        assert res.status_code == 200
    else:
        assert _typed(res) == want and "token" not in res.json()


def test_another_accounts_capability_and_a_missing_one_are_one_404(client, world):
    foreign = rotate(client, world, OTHERS)
    missing = rotate(client, world, "capmissingaaaa1", key="0190f000-0000-7000-8000-00000000000c")
    malformed = rotate(client, world, "CAPAAAAAAAAAAA1", key="0190f000-0000-7000-8000-00000000000d")
    strip = lambda r: {k: v for k, v in r.json().items() if k != "correlation_id"}  # noqa: E731
    assert strip(foreign) == strip(missing) == strip(malformed) == {"detail": "Not found.", "code": "not_found"}
    # The malformed id never reached PocketBase.
    assert not any("CAPAAAAAAAAAAA1" in path for path in world.hooks.paths())


@pytest.mark.parametrize("body", [{}, {"expected_capability_version": 0}, {"expected_capability_version": "1"},
                                  {"expected_capability_version": True}, {"expected_capability_version": 1.5},
                                  {"expected_capability_version": 1, "token": "sd1_x"}])
def test_a_bad_rotate_body_is_a_fixed_400(client, world, body):
    res = rotate(client, world, "capaaaaaaaaaaa1", body=body)
    assert _typed(res) == (400, "invalid_request")
    assert world.hooks.calls == []


def test_rotate_needs_a_key(client, world):
    assert _typed(rotate(client, world, "capaaaaaaaaaaa1", key=None)) == (400, "idempotency_key_required")
    assert world.hooks.calls == []


def test_with_the_gate_closed_rotate_is_turned_off(client, world, monkeypatch):
    monkeypatch.setenv(GATE, "disabled")
    assert _typed(rotate(client, world, "capaaaaaaaaaaa1")) == (503, "route_disabled")
    assert world.hooks.calls == []


# ---- logs ---------------------------------------------------------------------------------------------------


def test_each_command_logs_a_coarse_code_by_pseudonym_and_never_a_bearer(client, world, capsys):
    capsys.readouterr()
    first = create(client, world, {"resume_id": RESUME, "password": PASSWORD}).json()
    create(client, world, {"resume_id": RESUME, "password": PASSWORD})
    turned = rotate(client, world, first["capability_id"]).json()
    rotate(client, world, OTHERS, key="0190f000-0000-7000-8000-00000000000e")
    out = capsys.readouterr().out
    lines = [json.loads(x) for x in out.splitlines() if x.startswith("{") and '"share.' in x and "resolve" not in x]
    assert [(line["event"], line["code"], line.get("record")) for line in lines] == [
        ("share.create", "issued", first["capability_id"]),
        ("share.create", "already_issued", first["capability_id"]),
        ("share.rotate", "issued", first["capability_id"]),
        ("share.rotate", "not_found", None),
    ]
    for line in lines:
        assert line["account"] == obs.account_pseudonym(TEST_ACCOUNT_ID)
        assert set(line) <= {"v", "event", "correlation_id", "account", "record", "code"}
    for secret in (first["token"], turned["token"], PASSWORD, TEST_TOKEN, f'"{TEST_ACCOUNT_ID}"'):
        assert secret not in out


def test_a_command_id_is_a_uuidv7():
    for _ in range(50):
        assert admission_state.COMMAND_ID.fullmatch(share_commands.new_command_id())
