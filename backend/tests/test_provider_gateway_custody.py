"""Saved AI provider keys through PocketBase's AI routes (ROUNDS-14-L02
stage A, app/provider_gateway/custody.py and the provider routes).

PocketBase's hook routes are a fake here, over the same HTTP calls the
runner makes, that keeps ai_custody.js's rules (pocketbase/tests has the
hook's own tests): a saved key works only with the address it was entered
for, and changing the address asks for the key again. The checks before a
key opens, in order, the rewrap of a key saved before this release, the
typed answers for each refusal, and the routes on top."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets as pysecrets

import httpx
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app import admission_state, destinations
from app.errors import TypedError
from app.provider_gateway import custody, keyring

SECRET = "test-custody-secret-placeholder-0123456789"
RUNNER_KEY = "test-runner-key-placeholder-0123456789"
USER = {"id": "acct00000000001", "token": "bearer-a", "record": {"id": "acct00000000001", "is_demo": False}}
OTHER = {"id": "acct00000000002", "token": "bearer-b", "record": {"id": "acct00000000002", "is_demo": False}}
PID = "prov00000000001"
HERE = "https://llm.example.test/v1"
THERE = "https://llm.other.test/v1"
PUBLIC = "93.184.216.34"


class Hooks:
    """PocketBase's AI routes, over its state: providers, saved keys, and
    model lists, with the hook's rules."""

    def __init__(self) -> None:
        self.providers: dict[str, dict] = {}
        self.credentials: dict[str, dict] = {}
        self.models: dict[str, list[dict]] = {}
        self.calls: list[tuple[str, dict]] = []
        self.answer: dict[str, httpx.Response] = {}
        self.converts = 0

    def add(self, pid, user=USER, kind="openai-compatible", base_url=HERE, models=("local-model",)):
        self.providers[pid] = {"id": pid, "user": user["id"], "kind": kind, "label": "Mine", "base_url": base_url,
                               "created": "2026-11-13 00:00:00.000Z", "models_cached_at": ""}
        self.models[pid] = [{"model": m, "verification": "registry"} for m in models]

    def view(self, pid):
        row = self.providers[pid]
        cred = self.credentials.get(pid)
        return {**{k: row[k] for k in ("id", "kind", "label", "base_url", "created", "models_cached_at")},
                "has_key": bool(cred and cred["status"] == "active"),
                "key": None if cred is None else {"wrap": cred["wrap"], "status": cred["status"],
                                                 "registered_host": cred["registered_host"],
                                                 "registered_port": cred["registered_port"]},
                "models": sorted(self.models.get(pid, []), key=lambda m: m["model"])}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        body = json.loads(request.content or b"{}")
        self.calls.append((path, body))
        if path in self.answer:
            return self.answer[path]
        if request.headers.get(admission_state.RUNNER_KEY_HEADER) != RUNNER_KEY:
            return httpx.Response(403, json={"v": "ai-custody/v1", "error": "forbidden"})
        account = {"bearer-a": USER["id"], "bearer-b": OTHER["id"]}[request.headers["authorization"].split()[1]]
        ok = lambda **kw: httpx.Response(200, json={"v": "ai-custody/v1", **kw})  # noqa: E731
        err = lambda status, code: httpx.Response(status, json={"v": "ai-custody/v1", "error": code})  # noqa: E731
        owned = lambda pid: pid in self.providers and self.providers[pid]["user"] == account  # noqa: E731
        action = path.rsplit("/", 1)[-1]
        if action == "list":
            if body.get("provider"):
                return ok(providers=[self.view(body["provider"])] if owned(body["provider"]) else [])
            return ok(providers=[self.view(p) for p, r in self.providers.items() if r["user"] == account])
        if action == "create":
            if body["id"] in self.providers:
                return err(409, "conflict")
            self.providers[body["id"]] = {"id": body["id"], "user": account, "kind": body["kind"], "label": body["label"],
                                          "base_url": body["base_url"], "created": "now", "models_cached_at": ""}
            if body.get("credential"):
                self._save(body["id"], account, body["credential"])
            return ok(provider=self.view(body["id"]))
        if not owned(body["provider"]):
            return err(404, "not_found")
        pid = body["provider"]
        row, cred = self.providers[pid], self.credentials.get(pid)
        if action == "update":
            if body["key"] == "keep" and cred is not None:
                if cred["registered_host"]:
                    stays = body["endpoint"] == {"host": cred["registered_host"], "port": cred["registered_port"]}
                else:
                    stays = (body["kind"], body["base_url"]) == (row["kind"], row["base_url"])
                if not stays:
                    return err(400, "credential_required")
            row.update(kind=body["kind"], label=body["label"], base_url=body["base_url"])
            if body["key"] == "clear":
                self.credentials.pop(pid, None)
            elif isinstance(body["key"], dict):
                self._save(pid, account, body["key"])
            return ok(provider=self.view(pid))
        if action == "models":
            keep = [m for m in self.models.get(pid, []) if not body["replace"] or m["verification"] != body["verification"]]
            have = {m["model"] for m in keep}
            self.models[pid] = keep + [{"model": m, "verification": body["verification"]} for m in body["models"]
                                       if m not in have]
            return ok(provider=self.view(pid))
        if action == "read":
            return ok(provider={k: row[k] for k in ("id", "kind", "label", "base_url")},
                      credential=None if cred is None else {k: cred[k] for k in (
                          "wrap", "key_version", "ciphertext", "nonce", "registered_host", "registered_port", "status")},
                      models=self.models.get(pid, []))
        if action == "convert":
            digest = hashlib.sha256(f"{cred['ciphertext']}:{cred['nonce']}".encode()).hexdigest() if cred else ""
            if cred is None or cred["wrap"] != "legacy-v0" or digest != body["from"]:
                return err(409, "conflict")
            self.converts += 1
            self._save(pid, account, body["credential"])
            return ok(converted=True)
        raise AssertionError(path)

    def _save(self, pid, account, c):
        self.credentials[pid] = {"user": account, "wrap": c["wrap"], "key_version": c["key_version"],
                                 "ciphertext": c["ciphertext"], "nonce": c["nonce"], "registered_host": c["host"],
                                 "registered_port": c["port"], "status": "active"}


@pytest.fixture
def hooks(monkeypatch):
    monkeypatch.setenv("AI_KEY_SECRET", SECRET)
    monkeypatch.delenv("ROUNDS_ALLOW_DEV_KEY", raising=False)
    monkeypatch.setenv(admission_state.RUNNER_KEY_ENV, RUNNER_KEY)
    fake = Hooks()
    real = httpx.AsyncClient

    def client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(fake)
        return real(*args, **kwargs)

    monkeypatch.setattr(custody.httpx, "AsyncClient", client)

    async def resolve(host, port):
        return [PUBLIC]

    monkeypatch.setattr(destinations, "resolve", resolve)
    return fake


def run(coro):
    return asyncio.run(coro)


def saved_key(hooks, key="test-provider-key-placeholder", pid=PID, at=("llm.example.test", 443), user=USER):
    w = keyring.wrap(key, keyring.Binding(user["id"], pid, *at))
    hooks._save(pid, user["id"], {"wrap": w.wrap, "key_version": w.key_version, "ciphertext": w.ciphertext,
                                  "nonce": w.nonce, "host": at[0], "port": at[1]})


def legacy_key(hooks, key="test-provider-key-placeholder", pid=PID):
    nonce = pysecrets.token_bytes(12)
    sealed = AESGCM(hashlib.sha256(SECRET.encode()).digest()).encrypt(nonce, key.encode(), None)
    hooks.credentials[pid] = {"user": USER["id"], "wrap": "legacy-v0", "key_version": 1,
                              "ciphertext": base64.b64encode(sealed).decode(), "nonce": base64.b64encode(nonce).decode(),
                              "registered_host": "", "registered_port": 0, "status": "active"}


def code(exc_info) -> str:
    return exc_info.value.code


# ---- addresses -------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind, base_url, want",
    [
        ("openai", "", ("api.openai.com", 443)),
        ("anthropic", "", ("api.anthropic.com", 443)),
        ("openai-compatible", "", None),
        ("openai-compatible", "https://LLM.Example.test/v1", ("llm.example.test", 443)),
        ("anthropic-compatible", "http://llm.example.test:8080", ("llm.example.test", 8080)),
        ("openai-compatible", "https://bücher.example.test/v1", ("xn--bcher-kva.example.test", 443)),
    ],
)
def test_a_providers_address_is_its_base_urls_or_its_kinds_own(kind, base_url, want):
    assert custody.endpoint(kind, base_url) == want


@pytest.mark.parametrize("base_url", ["ftp://llm.example.test", "not a url", "https://"])
def test_a_base_url_that_names_no_address_is_denied(base_url):
    with pytest.raises(TypedError) as err:
        custody.endpoint("openai-compatible", base_url)
    assert code(err) == "destination_denied"


# ---- R1: a saved key works only with the address it was entered for ------------------------------------


def test_changing_a_providers_address_without_its_key_asks_for_the_key_again(client, hooks, monkeypatch, signed_in_user):
    hooks.add(PID)
    saved_key(hooks)
    res = client.patch(f"/api/ai/providers/{PID}",
                       json={"kind": "openai-compatible", "label": "Mine", "base_url": THERE, "key": ""})
    assert res.status_code == 400 and res.json()["code"] == "credential_required"
    assert hooks.providers[PID]["base_url"] == HERE


def test_a_label_change_keeps_the_saved_key(client, hooks, signed_in_user):
    hooks.add(PID)
    saved_key(hooks)
    res = client.patch(f"/api/ai/providers/{PID}",
                       json={"kind": "openai-compatible", "label": "Renamed", "base_url": HERE, "key": ""})
    assert res.status_code == 200, res.text
    assert res.json()["has_key"] is True and hooks.providers[PID]["label"] == "Renamed"


def test_a_new_address_with_its_key_saves_a_key_for_that_address_only(client, hooks, signed_in_user):
    hooks.add(PID)
    saved_key(hooks)
    res = client.patch(f"/api/ai/providers/{PID}",
                       json={"kind": "openai-compatible", "label": "Mine", "base_url": THERE, "key": "the-new-key"})
    assert res.status_code == 200, res.text
    cred = hooks.credentials[PID]
    assert (cred["registered_host"], cred["registered_port"]) == ("llm.other.test", 443)
    stored = keyring.Wrapped(cred["wrap"], cred["key_version"], cred["ciphertext"], cred["nonce"])
    assert keyring.unwrap(stored, keyring.Binding(USER["id"], PID, "llm.other.test", 443)) == "the-new-key"
    with pytest.raises(keyring.CredentialUnusable):
        keyring.unwrap(stored, keyring.Binding(USER["id"], PID, "llm.example.test", 443))


def test_opening_a_key_checks_the_address_it_was_entered_for(hooks):
    hooks.add(PID)
    saved_key(hooks, at=("llm.other.test", 443))
    with pytest.raises(TypedError) as err:
        run(custody.key_for(USER, PID, "local-model"))
    assert code(err) == "credential_required"


# ---- R6: the checks before a key opens, in order -------------------------------------------------------


@pytest.fixture
def no_open(monkeypatch):
    def refuse(*_a, **_k):
        raise AssertionError("a key was opened")

    monkeypatch.setattr(keyring, "unwrap", refuse)


def test_the_model_must_be_on_the_providers_list_before_any_key_opens(hooks, no_open, monkeypatch):
    from routers import ai

    hooks.add(PID)
    saved_key(hooks)

    async def settings(_user):
        return {"text_provider": PID, "text_model": "not-listed"}

    monkeypatch.setattr(ai, "_load_settings", settings)
    with pytest.raises(TypedError) as err:
        run(ai._active_text_config(USER))
    assert code(err) == "model_unregistered"


@pytest.mark.parametrize(
    "setup, want",
    [
        (lambda h: None, "credential_missing"),
        (lambda h: (saved_key(h), h.credentials[PID].update(status="suspect-planted")), "credential_missing"),
        (lambda h: (saved_key(h), h.providers[PID].update(base_url="")), "credential_required"),
    ],
    ids=["no key", "suspect key", "no address"],
)
def test_no_usable_key_or_address_opens_nothing(hooks, no_open, setup, want):
    hooks.add(PID)
    setup(hooks)
    with pytest.raises(TypedError) as err:
        run(custody.key_for(USER, PID, "local-model"))
    assert code(err) == want


@pytest.mark.parametrize("secret", [None, keyring.DEV_SECRET])
def test_without_a_usable_root_no_key_opens(hooks, no_open, monkeypatch, secret):
    hooks.add(PID)
    saved_key(hooks)
    if secret is None:
        monkeypatch.delenv("AI_KEY_SECRET")
    else:
        monkeypatch.setenv("AI_KEY_SECRET", secret)
    with pytest.raises(TypedError) as err:
        run(custody.key_for(USER, PID, "local-model"))
    assert code(err) == "keyring_unavailable"


def test_a_saved_key_opens_for_its_provider_and_address(hooks):
    hooks.add(PID)
    saved_key(hooks)
    opened = run(custody.key_for(USER, PID, "local-model"))
    assert (opened.api_key, opened.kind, opened.base_url) == ("test-provider-key-placeholder", "openai-compatible", HERE)
    assert hooks.converts == 0


def test_a_key_that_doesnt_open_is_missing(hooks):
    hooks.add(PID)
    saved_key(hooks)
    hooks.credentials[PID]["ciphertext"] = base64.b64encode(b"\0" * 40).decode()
    with pytest.raises(TypedError) as err:
        run(custody.key_for(USER, PID, "local-model"))
    assert code(err) == "credential_missing"


# ---- a key saved before this release ------------------------------------------------------------------------


def test_a_key_saved_before_this_release_opens_and_is_rewrapped_for_its_address(hooks):
    hooks.add(PID)
    legacy_key(hooks)
    assert run(custody.key_for(USER, PID, "local-model")).api_key == "test-provider-key-placeholder"
    assert hooks.converts == 1
    cred = hooks.credentials[PID]
    assert (cred["wrap"], cred["registered_host"], cred["registered_port"]) == ("aad-v1", "llm.example.test", 443)
    stored = keyring.Wrapped(cred["wrap"], cred["key_version"], cred["ciphertext"], cred["nonce"])
    assert keyring.unwrap(stored, keyring.Binding(USER["id"], PID, "llm.example.test", 443)) == "test-provider-key-placeholder"
    # The next use opens the rewrapped key and rewraps nothing.
    run(custody.key_for(USER, PID, "local-model"))
    assert hooks.converts == 1


def test_a_rewrap_that_loses_a_race_still_lets_the_call_go_ahead(hooks):
    hooks.add(PID)
    legacy_key(hooks)
    hooks.answer["/api/rounds/ai/credentials/convert"] = httpx.Response(409, json={"v": "ai-custody/v1",
                                                                                  "error": "conflict"})
    assert run(custody.key_for(USER, PID, "local-model")).api_key == "test-provider-key-placeholder"
    assert hooks.credentials[PID]["wrap"] == "legacy-v0"


# ---- the routes' answers ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "response, want",
    [
        (httpx.Response(404, json={"v": "ai-custody/v1", "error": "not_found"}), "provider_unavailable"),
        (httpx.Response(403, json={"v": "ai-custody/v1", "error": "demo_not_permitted"}), "demo_not_permitted"),
        (httpx.Response(400, json={"v": "ai-custody/v1", "error": "invalid_request"}), "invalid_request"),
        (httpx.Response(401, json={"code": 401, "message": "PocketBase's text"}), "unauthenticated"),
        (httpx.Response(503, json={"v": "ai-custody/v1", "error": "unconfigured"}), "providers_unavailable"),
        (httpx.Response(403, json={"v": "ai-custody/v1", "error": "forbidden"}), "providers_unavailable"),
        (httpx.Response(500, text="PocketBase's own text"), "providers_unavailable"),
        (httpx.Response(200, json={"v": "other/v1"}), "providers_unavailable"),
    ],
)
def test_each_answer_maps_to_a_typed_error_without_pocketbases_text(hooks, response, want):
    hooks.answer["/api/rounds/ai/providers/list"] = response
    with pytest.raises(TypedError) as err:
        run(custody.list_providers(USER))
    assert code(err) == want and "PocketBase" not in err.value.detail


def test_without_the_runner_key_nothing_is_asked(hooks, monkeypatch):
    monkeypatch.delenv(admission_state.RUNNER_KEY_ENV)
    with pytest.raises(TypedError) as err:
        run(custody.list_providers(USER))
    assert code(err) == "providers_unavailable" and hooks.calls == []


def test_another_accounts_provider_and_a_missing_one_answer_alike(hooks):
    hooks.add(PID, user=OTHER)
    answers = []
    for pid in (PID, "provnone0000001"):
        with pytest.raises(TypedError) as err:
            run(custody.load(USER, pid))
        answers.append((err.value.status_code, err.value.code, err.value.detail))
    assert answers[0] == answers[1] == (404, "provider_unavailable", "This AI provider isn't available.")


# ---- create ------------------------------------------------------------------------------------


def test_a_create_binds_the_key_to_the_id_it_mints_and_the_kinds_address(hooks):
    made = run(custody.create(USER, "openai", "Mine", "https://ignored.example.test/v1", "sk-test-placeholder"))
    pid = made["id"]
    assert len(pid) == 15 and made["base_url"] == "" and made["has_key"] is True
    cred = hooks.credentials[pid]
    assert (cred["registered_host"], cred["registered_port"]) == ("api.openai.com", 443)
    stored = keyring.Wrapped(cred["wrap"], cred["key_version"], cred["ciphertext"], cred["nonce"])
    assert keyring.unwrap(stored, keyring.Binding(USER["id"], pid, "api.openai.com", 443)) == "sk-test-placeholder"
    (path, body), = [c for c in hooks.calls if c[0].endswith("/create")]
    assert "user" not in body and "sk-test-placeholder" not in json.dumps(body)


def test_a_create_whose_id_is_taken_tries_a_new_one(hooks, monkeypatch):
    hooks.add("takenid00000001")
    ids = iter(["takenid00000001", "freshid00000001"])
    monkeypatch.setattr(custody, "new_provider_id", lambda: next(ids))
    made = run(custody.create(USER, "anthropic", "Mine", "", "sk-test-placeholder"))
    assert made["id"] == "freshid00000001"
    cred = hooks.credentials["freshid00000001"]
    stored = keyring.Wrapped(cred["wrap"], cred["key_version"], cred["ciphertext"], cred["nonce"])
    assert keyring.unwrap(stored, keyring.Binding(USER["id"], "freshid00000001", "api.anthropic.com", 443))


def test_a_compatible_key_needs_its_base_url(hooks):
    with pytest.raises(TypedError) as err:
        run(custody.create(USER, "openai-compatible", "Mine", "", "sk-test-placeholder"))
    assert code(err) == "invalid_request" and hooks.calls == []


def test_without_a_usable_root_no_key_is_saved(hooks, monkeypatch):
    monkeypatch.setenv("AI_KEY_SECRET", keyring.DEV_SECRET)
    with pytest.raises(TypedError) as err:
        run(custody.create(USER, "anthropic", "Mine", "", "sk-test-placeholder"))
    assert code(err) == "keyring_unavailable" and hooks.calls == []


@pytest.mark.parametrize("key, want", [(None, "clear"), ("", "keep"), ("   ", "keep")])
def test_an_update_keeps_or_clears_the_key_as_asked(hooks, key, want):
    hooks.add(PID)
    saved_key(hooks)
    run(custody.update(USER, PID, "openai-compatible", "Mine", HERE, key))
    (_path, body), = [c for c in hooks.calls if c[0].endswith("/update")]
    assert body["key"] == want and body["endpoint"] == {"host": "llm.example.test", "port": 443}


# ---- the provider routes ----------------------------------------------------------------------------------


@pytest.fixture
def signed_in_user(monkeypatch):
    from routers import ai, ai_coding

    async def user(_request):
        return USER

    monkeypatch.setattr(ai, "current_user", user)
    monkeypatch.setattr(ai_coding, "current_user", user)
    return USER


def test_the_provider_list_shows_each_key_as_saved_or_not_and_the_model_list(client, hooks, signed_in_user):
    hooks.add(PID)
    saved_key(hooks)
    hooks.add("prov00000000002", models=())
    res = client.get("/api/ai/providers")
    assert res.status_code == 200
    assert res.json() == [
        {"id": PID, "kind": "openai-compatible", "label": "Mine", "base_url": HERE, "has_key": True,
         "models": ["local-model"], "models_cached_at": ""},
        {"id": "prov00000000002", "kind": "openai-compatible", "label": "Mine", "base_url": HERE, "has_key": False,
         "models": [], "models_cached_at": ""},
    ]


def test_choosing_a_model_names_it_on_a_compatible_providers_list(client, hooks, signed_in_user, monkeypatch):
    from routers import ai

    hooks.add(PID)

    async def no_row(_user):
        return None

    async def save(_token, _path, payload):
        return {"id": "set000000000001", **payload}

    monkeypatch.setattr(ai, "_load_settings", no_row)
    monkeypatch.setattr(ai, "pb_post", save)
    res = client.put("/api/ai/settings", json={"text_provider_id": PID, "text_model": "typed-model"})
    assert res.status_code == 200, res.text
    assert {"model": "typed-model", "verification": "user-declared"} in hooks.models[PID]


def test_choosing_a_model_a_first_party_provider_doesnt_list_is_refused(client, hooks, signed_in_user, monkeypatch):
    from routers import ai

    hooks.add(PID, kind="openai", base_url="", models=("gpt-listed",))

    async def no_row(_user):
        return None

    async def save(*_a):
        pytest.fail("the settings were saved")

    monkeypatch.setattr(ai, "_load_settings", no_row)
    monkeypatch.setattr(ai, "pb_post", save)
    res = client.put("/api/ai/settings", json={"text_provider_id": PID, "text_model": "gpt-unlisted"})
    assert res.status_code == 400 and res.json()["code"] == "model_unregistered"


def test_the_coding_model_list_holds_each_listed_model_of_each_provider_with_a_key(client, hooks, signed_in_user):
    hooks.add(PID, models=("b-model", "a-model"))
    saved_key(hooks)
    hooks.add("prov00000000002", models=("no-key-model",))
    res = client.get("/api/ai-coding/models")
    assert res.status_code == 200
    assert res.json() == [
        {"provider_id": PID, "provider_label": "Mine", "kind": "openai-compatible", "model": "a-model"},
        {"provider_id": PID, "provider_label": "Mine", "kind": "openai-compatible", "model": "b-model"},
    ]


def test_refreshing_a_providers_models_replaces_its_list(client, hooks, signed_in_user, monkeypatch):
    from routers import ai

    hooks.add(PID, kind="openai", base_url="", models=("gpt-old",))
    saved_key(hooks, at=("api.openai.com", 443))
    seen = {}

    async def fetch(kind, api_key, base_url, destination=None):
        seen.update(kind=kind, api_key=api_key, base_url=base_url)
        return ["gpt-a", "gpt-b"]

    monkeypatch.setattr(ai, "_fetch_models", fetch)
    res = client.post(f"/api/ai/providers/{PID}/refresh-models")
    assert res.status_code == 200, res.text
    assert res.json()["models"] == ["gpt-a", "gpt-b"]
    assert seen == {"kind": "openai", "api_key": "test-provider-key-placeholder", "base_url": ""}
    assert sorted(m["model"] for m in hooks.models[PID]) == ["gpt-a", "gpt-b"]


def test_the_runner_writes_no_provider_row_through_rest(client, hooks, signed_in_user, monkeypatch):
    from app import pb_auth
    from routers import ai

    def no_rest(*_a, **_k):
        pytest.fail("a provider row was written through REST")

    for name in ("pb_post", "pb_patch"):
        monkeypatch.setattr(ai, name, no_rest, raising=False)
        monkeypatch.setattr(pb_auth, name, no_rest)
    assert client.post("/api/ai/providers", json={"kind": "anthropic", "label": "New", "key": "k"}).status_code == 200
    (pid,) = hooks.providers
    assert client.patch(f"/api/ai/providers/{pid}", json={"kind": "anthropic", "label": "Re", "key": ""}).status_code == 200
    for path, body in hooks.calls:
        assert "user" not in body, path
