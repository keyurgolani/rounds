"""AI provider custody in pb_hooks/ai_custody.js (ROUNDS-14-L02 stage A).

The routes' decisions under node, on an in-memory store with the
PocketBase store's contract (ai_custody_runner.cjs): the request checks,
one 404 for a missing or another account's provider, a saved key that
works only with the address it was entered for, the model list, the read
that carries a key's ciphertext, the rewrap of a key saved before this
release, a demo account's writes, and nothing written on any refusal.
Then the route registration and the proxies' refusals. The harness runs
the same functions on a real PocketBase.
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
HOOKS = HERE.parent / "pb_hooks"
RUNNER = HERE / "ai_custody_runner.cjs"

A = {"id": "acct00000000001", "demo": False}
B = {"id": "acct00000000002", "demo": False}
DEMO = {"id": "acct00000000003", "demo": True}
P_A = "prova0000000001"
P_B = "provb0000000001"
P_NEW = "provnew00000001"
CT = base64.b64encode(b"wrapped-key-bytes-for-tests-0123456789abcdef").decode()
CT2 = base64.b64encode(b"another-wrapped-key-for-tests-0123456789abc").decode()
NONCE = base64.b64encode(b"\x01" * 12).decode()
NONCE2 = base64.b64encode(b"\x02" * 12).decode()
HERE_AT = {"host": "llm.example.test", "port": 443}
ELSEWHERE = {"host": "llm.other.test", "port": 443}


def run(steps: list[dict], state: dict | None = None) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run(
        [node, str(RUNNER), str(HOOKS)],
        input=json.dumps({"state": base_state() if state is None else state, "steps": steps}),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def credential(ct=CT, nonce=NONCE, at=HERE_AT) -> dict:
    return {"wrap": "aad-v1", "key_version": 1, "ciphertext": ct, "nonce": nonce, **at}


def stored(ct=CT, nonce=NONCE, at=HERE_AT, user=A["id"], provider=P_A, wrap="aad-v1", status="active") -> dict:
    registered = at if wrap == "aad-v1" else {"host": "", "port": 0}
    return {"user": user, "provider": provider, "wrap": wrap, "key_version": 1, "ciphertext": ct, "nonce": nonce,
            "registered_host": registered["host"], "registered_port": registered["port"], "status": status,
            "legacy_ciphertext": ct if wrap == "legacy-v0" else "", "legacy_nonce": nonce if wrap == "legacy-v0" else ""}


def base_state() -> dict:
    return {
        "providers": {
            P_A: {"user": A["id"], "kind": "openai-compatible", "label": "Mine", "base_url": "https://llm.example.test/v1",
                  "models_cached_at": "2026-11-01T00:00:00.000Z", "created": "2026-11-01 00:00:00.000Z"},
            P_B: {"user": B["id"], "kind": "openai", "label": "Theirs", "base_url": "",
                  "models_cached_at": "", "created": "2026-11-01 00:00:01.000Z"},
        },
        "credentials": {
            P_A: stored(),
            P_B: stored(user=B["id"], provider=P_B, at={"host": "api.openai.com", "port": 443}),
        },
        "models": {
            P_A: [{"user": A["id"], "model": "local-large", "verification": "user-declared"},
                  {"user": A["id"], "model": "local-small", "verification": "registry"}],
        },
    }


def update(account=A, provider=P_A, kind="openai-compatible", label="Mine", base_url="https://llm.example.test/v1",
           endpoint=HERE_AT, key="keep") -> dict:
    return {"op": "update", "account": account, "data": {"provider": provider, "kind": kind, "label": label,
                                                         "base_url": base_url, "endpoint": endpoint, "key": key}}


def error(out: dict) -> tuple[int, str | None]:
    return out["status"], out["body"].get("error")


# ---- list and read ------------------------------------------------------------


def test_a_list_holds_only_the_callers_providers_and_no_ciphertext():
    out = run([{"op": "list", "account": A, "data": {}}])
    (res,) = out["results"]
    assert res["status"] == 200 and res["body"]["v"] == "ai-custody/v1"
    (provider,) = res["body"]["providers"]
    assert provider["id"] == P_A and provider["has_key"] is True
    assert provider["key"] == {"wrap": "aad-v1", "status": "active", "registered_host": "llm.example.test",
                               "registered_port": 443}
    assert [m["model"] for m in provider["models"]] == ["local-large", "local-small"]
    assert CT not in json.dumps(res)


def test_a_key_that_also_sits_under_another_account_counts_as_no_key():
    state = base_state()
    state["credentials"][P_A]["status"] = "suspect-planted"
    (res,) = run([{"op": "list", "account": A, "data": {}}], state)["results"]
    assert res["body"]["providers"][0]["has_key"] is False


@pytest.mark.parametrize("data", [{"provider": "SHORT"}, {"provider": None}, {"x": 1}, []])
def test_list_takes_only_a_provider_id(data):
    (res,) = run([{"op": "list", "account": A, "data": data}])["results"]
    assert error(res) == (400, "invalid_request")


def test_a_list_of_one_holds_the_callers_provider_or_nothing():
    mine, theirs, missing = run([{"op": "list", "account": A, "data": {"provider": P_A}},
                                 {"op": "list", "account": A, "data": {"provider": P_B}},
                                 {"op": "list", "account": A, "data": {"provider": "provnone0000001"}}])["results"]
    assert [p["id"] for p in mine["body"]["providers"]] == [P_A]
    assert theirs == missing == {"status": 200, "body": {"v": "ai-custody/v1", "providers": []}}


def test_a_read_carries_the_callers_ciphertext_only():
    out = run([{"op": "read", "account": A, "data": {"provider": P_A}},
               {"op": "read", "account": A, "data": {"provider": P_B}},
               {"op": "read", "account": A, "data": {"provider": "provnone0000001"}}])
    mine, theirs, missing = out["results"]
    assert mine["status"] == 200 and mine["body"]["credential"]["ciphertext"] == CT
    assert mine["body"]["provider"] == {"id": P_A, "kind": "openai-compatible", "label": "Mine",
                                        "base_url": "https://llm.example.test/v1"}
    assert "legacy_ciphertext" not in mine["body"]["credential"]
    # Another account's provider and a missing one get the same answer.
    assert theirs == missing == {"status": 404, "body": {"v": "ai-custody/v1", "error": "not_found"}}


# ---- create -------------------------------------------------------------------


def create(account=A, pid=P_NEW, kind="openai-compatible", label="New", base_url="https://llm.example.test/v1",
           cred=None) -> dict:
    data = {"id": pid, "kind": kind, "label": label, "base_url": base_url}
    if cred is not None:
        data["credential"] = cred
    return {"op": "create", "account": account, "data": data}


def test_a_create_saves_the_provider_and_its_key_for_the_caller():
    out = run([create(cred=credential())])
    (res,) = out["results"]
    assert res["status"] == 200
    assert res["body"]["provider"]["id"] == P_NEW and res["body"]["provider"]["has_key"] is True
    row = out["state"]["providers"][P_NEW]
    assert (row["user"], row["kind"], row["label"], row["base_url"]) == (A["id"], "openai-compatible", "New",
                                                                         "https://llm.example.test/v1")
    saved = out["state"]["credentials"][P_NEW]
    assert saved == {**stored(provider=P_NEW), "legacy_ciphertext": "", "legacy_nonce": ""}


def test_a_create_without_a_key_saves_no_key():
    out = run([create(kind="anthropic", base_url="")])
    assert out["results"][0]["body"]["provider"]["has_key"] is False
    assert P_NEW not in out["state"]["credentials"]


@pytest.mark.parametrize(
    "step",
    [
        create(pid="SHORT"),
        create(pid="provnew0000000_"),
        create(kind="other"),
        create(label=""),
        create(label="   "),
        create(label="x" * 201),
        create(label="tab\there"),
        # A first-party kind keeps no base URL.
        create(kind="openai", base_url="https://llm.example.test/v1"),
        create(base_url="x" * 2049),
        # A key needs an address to be bound to.
        create(base_url="", cred=credential()),
        create(cred={**credential(), "wrap": "legacy-v0"}),
        create(cred={**credential(), "key_version": 2}),
        create(cred={**credential(), "nonce": "short"}),
        create(cred={**credential(), "ciphertext": "not base64!"}),
        create(cred={**credential(), "host": "UPPER.example.test"}),
        create(cred={**credential(), "port": 0}),
        create(cred={**credential(), "extra": True}),
    ],
)
def test_a_create_refuses_what_isnt_a_provider_and_writes_nothing(step):
    out = run([step])
    assert error(out["results"][0]) == (400, "invalid_request")
    assert out["state"] == base_state()


def test_a_create_refuses_an_id_already_taken_whoever_holds_it():
    out = run([create(pid=P_B)])
    assert error(out["results"][0]) == (409, "conflict")
    assert out["state"]["providers"][P_B]["user"] == B["id"]


def test_a_demo_account_writes_nothing():
    out = run([create(account=DEMO), update(account=DEMO),
               {"op": "models", "account": DEMO, "data": {"provider": P_A, "models": [], "verification": "registry",
                                                          "replace": True}}])
    assert [error(r) for r in out["results"]] == [(403, "demo_not_permitted")] * 3


# ---- update: a saved key works only with the address it was entered for ------------------------------------------


def test_a_label_change_keeps_the_saved_key():
    out = run([update(label="Renamed")])
    assert out["results"][0]["status"] == 200
    assert out["state"]["providers"][P_A]["label"] == "Renamed"
    assert out["state"]["credentials"][P_A] == stored()
    # Same kind and address, so the model list stays.
    assert len(out["state"]["models"][P_A]) == 2


@pytest.mark.parametrize(
    "change",
    [
        {"base_url": "https://llm.other.test/v1", "endpoint": ELSEWHERE},
        {"base_url": "https://llm.example.test:8443/v1", "endpoint": {"host": "llm.example.test", "port": 8443}},
        {"base_url": "", "endpoint": None},
    ],
    ids=["another host", "another port", "no address"],
)
def test_changing_the_address_asks_for_the_key_again(change):
    out = run([update(**change)])
    assert error(out["results"][0]) == (400, "credential_required")
    assert out["state"] == base_state()


def test_the_same_address_under_another_path_or_kind_keeps_the_key():
    out = run([update(kind="anthropic-compatible", base_url="https://llm.example.test/v2")])
    assert out["results"][0]["status"] == 200
    assert out["state"]["credentials"][P_A] == stored()
    # A model list belongs to the kind and address it came from.
    assert out["state"]["models"][P_A] == []
    assert out["state"]["providers"][P_A]["models_cached_at"] == ""


def test_a_new_address_with_a_new_key_saves_both():
    out = run([update(base_url="https://llm.other.test/v1", endpoint=ELSEWHERE,
                      key=credential(CT2, NONCE2, ELSEWHERE))])
    assert out["results"][0]["status"] == 200
    assert out["state"]["providers"][P_A]["base_url"] == "https://llm.other.test/v1"
    assert out["state"]["credentials"][P_A] == stored(CT2, NONCE2, ELSEWHERE)


def test_a_new_key_must_be_wrapped_for_the_address_the_update_sets():
    out = run([update(base_url="https://llm.other.test/v1", endpoint=ELSEWHERE, key=credential(CT2, NONCE2))])
    assert error(out["results"][0]) == (400, "invalid_request")
    assert out["state"] == base_state()


def test_clearing_the_key_removes_it():
    out = run([update(base_url="", endpoint=None, key="clear")])
    assert out["results"][0]["status"] == 200
    assert P_A not in out["state"]["credentials"]
    assert out["results"][0]["body"]["provider"]["has_key"] is False


def legacy_state() -> dict:
    state = base_state()
    state["credentials"][P_A] = stored(wrap="legacy-v0")
    return state


def test_a_key_saved_before_this_release_keeps_its_provider_as_it_was():
    state = legacy_state()
    out = run([update(label="Renamed"),
               update(kind="anthropic-compatible"),
               update(base_url="https://llm.example.test/v2")], state)
    assert [r["status"] for r in out["results"]] == [200, 400, 400]
    assert [error(r)[1] for r in out["results"][1:]] == ["credential_required", "credential_required"]
    assert out["state"]["credentials"][P_A] == stored(wrap="legacy-v0")


def test_another_accounts_provider_and_a_missing_one_answer_alike():
    out = run([update(provider=P_B, kind="openai", base_url="", endpoint={"host": "api.openai.com", "port": 443}),
               update(provider="provnone0000001")])
    assert out["results"][0] == out["results"][1] == {"status": 404,
                                                      "body": {"v": "ai-custody/v1", "error": "not_found"}}
    assert out["state"] == base_state()


@pytest.mark.parametrize(
    "data",
    [
        {"provider": P_A, "kind": "openai-compatible", "label": "x", "base_url": "", "endpoint": None},
        {"provider": P_A, "kind": "openai-compatible", "label": "x", "base_url": "", "endpoint": None, "key": "drop"},
        {"provider": P_A, "kind": "openai-compatible", "label": "x", "base_url": "", "key": "keep"},
        {"provider": P_A, "kind": "openai", "label": "x", "base_url": "https://x.example.test", "endpoint": None,
         "key": "keep"},
        {"provider": P_A, "kind": "openai-compatible", "label": "x", "base_url": "", "endpoint": {"host": "x"},
         "key": "keep"},
    ],
)
def test_an_update_refuses_what_it_cant_read(data):
    (res,) = run([{"op": "update", "account": A, "data": data}])["results"]
    assert error(res) == (400, "invalid_request")


# ---- models -------------------------------------------------------------------


def models(models_, verification="registry", replace=True, provider=P_A, account=A) -> dict:
    return {"op": "models", "account": account,
            "data": {"provider": provider, "models": models_, "verification": verification, "replace": replace}}


def test_a_refresh_replaces_the_providers_own_list_and_keeps_what_the_owner_named():
    out = run([models(["local-small", "local-medium", "local-medium"])])
    assert out["results"][0]["status"] == 200
    assert sorted((m["model"], m["verification"]) for m in out["state"]["models"][P_A]) == [
        ("local-large", "user-declared"), ("local-medium", "registry"), ("local-small", "registry")]
    assert out["state"]["providers"][P_A]["models_cached_at"] == "2026-11-13T00:00:00.000Z"


def test_a_named_model_is_added_once():
    out = run([models(["my-model", "local-small"], "user-declared", False)])
    assert sorted((m["model"], m["verification"]) for m in out["state"]["models"][P_A]) == [
        ("local-large", "user-declared"), ("local-small", "registry"), ("my-model", "user-declared")]
    # Naming a model isn't a refresh.
    assert out["state"]["providers"][P_A]["models_cached_at"] == "2026-11-01T00:00:00.000Z"


@pytest.mark.parametrize(
    "step",
    [
        models(["x" * 257]),
        models(["bad\nname"]),
        models([""]),
        models([1]),
        models(["m%d" % i for i in range(1001)]),
        models(["a"], verification="guessed"),
        {"op": "models", "account": A, "data": {"provider": P_A, "models": ["a"], "verification": "registry"}},
    ],
)
def test_a_model_list_takes_only_model_names(step):
    out = run([step])
    assert error(out["results"][0]) == (400, "invalid_request")
    assert out["state"] == base_state()


def test_a_model_list_stays_within_its_cap():
    state = base_state()
    state["models"][P_A] = [{"user": A["id"], "model": "u%04d" % i, "verification": "user-declared"} for i in range(999)]
    out = run([models(["one", "two"], "user-declared", False)], state)
    assert error(out["results"][0]) == (400, "invalid_request")


def test_another_accounts_model_list_is_not_found():
    out = run([models(["a"], provider=P_B)])
    assert error(out["results"][0]) == (404, "not_found")


# ---- convert --------------------------------------------------------------------


def from_digest(ct=CT, nonce=NONCE) -> str:
    return run([{"op": "sha256", "text": f"{ct}:{nonce}"}], {})["results"][0]


def convert(cred, frm, provider=P_A, account=A) -> dict:
    return {"op": "convert", "account": account, "data": {"provider": provider, "from": frm, "credential": cred}}


def test_a_key_saved_before_this_release_rewraps_once_and_keeps_the_moved_pair():
    out = run([convert(credential(CT2, NONCE2), from_digest())], legacy_state())
    assert out["results"][0] == {"status": 200, "body": {"v": "ai-custody/v1", "converted": True}}
    saved = out["state"]["credentials"][P_A]
    assert saved == {**stored(CT2, NONCE2), "legacy_ciphertext": CT, "legacy_nonce": NONCE}


@pytest.mark.parametrize(
    "state_change, frm",
    [
        (lambda s: None, "0" * 64),
        # Already rewrapped, or the key was entered again since.
        (lambda s: s["credentials"].__setitem__(P_A, stored()), None),
        (lambda s: s["credentials"][P_A].__setitem__("status", "suspect-planted"), None),
        (lambda s: s["credentials"].pop(P_A), None),
    ],
    ids=["another pair", "already current", "suspect", "no key"],
)
def test_a_rewrap_that_lost_a_race_changes_nothing(state_change, frm):
    state = legacy_state()
    state_change(state)
    out = run([convert(credential(CT2, NONCE2), frm or from_digest())], state)
    assert error(out["results"][0]) == (409, "conflict")
    assert out["state"] == state


def test_another_accounts_key_never_rewraps():
    state = legacy_state()
    state["credentials"][P_B] = stored(user=B["id"], provider=P_B, wrap="legacy-v0")
    out = run([convert(credential(CT2, NONCE2), from_digest(), provider=P_B)], state)
    assert error(out["results"][0]) == (404, "not_found")


# ---- routes and proxies ---------------------------------------------------------

ROUTES = {
    "/api/rounds/ai/providers/list": "list",
    "/api/rounds/ai/providers/create": "create",
    "/api/rounds/ai/providers/update": "update",
    "/api/rounds/ai/providers/models": "models",
    "/api/rounds/ai/credentials/read": "read",
    "/api/rounds/ai/credentials/convert": "convert",
}


def test_every_route_needs_a_signed_in_caller_and_names_its_action():
    src = (HOOKS / "ai_custody.pb.js").read_text()
    found = re.findall(
        r'routerAdd\(\s*"POST",\s*"([^"]+)",\s*\(c\) => require\(`\$\{__hooks\}/ai_custody\.js`\)\.handle\(c, "([a-z]+)"\),'
        r'\s*\$apis\.requireRecordAuth\("users"\),\s*\);',
        src,
    )
    assert dict(found) == ROUTES and src.count("routerAdd(") == len(ROUTES)


def test_every_route_checks_the_runner_key_before_it_reads_the_body():
    src = (HOOKS / "ai_custody.js").read_text()
    body = src[src.index("function handle(c, action)"):]
    assert body.index("runnerKeyError(") < body.index("run(pbStore(")
    assert "runInTransaction(" in body


def test_the_proxies_refuse_the_ai_routes():
    nginx = (ROOT / "frontend" / "nginx.conf").read_text()
    assert "location ~* ^/api/rounds/ai(/|$) { return 404; }" in nginx
    dev = (ROOT / "frontend" / "devProxy.ts").read_text()
    assert "/^\\/api\\/rounds\\/ai(\\/|$)/i," in dev
