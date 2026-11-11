"""The share resolver's PocketBase session (ROUNDS-00B-L04,
app/share_resolver_client.py): its login as share-resolver, the one
lookup call with only a digest and throttle keys in it, and every answer
outside the contract read as unavailable."""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app import share_resolver_client as client

SECRET = "test-resolver-secret-placeholder-0123456789"
DIGEST = "d" * 64
KEYS = [("ip_minute", "1" * 64), ("pw_15m", "2" * 64), ("digest_day", "3" * 64)]
CAPABILITY = {
    "id": "cap000000000001",
    "status": "active",
    "expires_at": "2027-01-01 00:00:00.000Z",
    "capability_version": 2,
    "snapshot": "snp000000000001",
    "password_policy_ref": "",
    "markup": "<article>Resume</article>",
}


class FakePocketBase:
    def __init__(self, answers=None, login_status=200):
        self.requests: list[httpx.Request] = []
        self.answers = list(answers or [])
        self.login_status = login_status
        self.logins = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == client.LOGIN_PATH:
            self.logins += 1
            if self.login_status != 200:
                return httpx.Response(self.login_status, json={"code": self.login_status})
            return httpx.Response(200, json={"token": f"session-{self.logins}", "record": {"id": "res000000000001"}})
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        status, body = answer
        return httpx.Response(status, content=body if isinstance(body, bytes) else json.dumps(body).encode())


def _client(fake: FakePocketBase) -> client.ResolverClient:
    return client.ResolverClient(SECRET, base_url="http://pocketbase.test", transport=httpx.MockTransport(fake))


def _lookup(fake: FakePocketBase, throttle=KEYS):
    async def go():
        c = _client(fake)
        try:
            return await c.lookup(DIGEST, throttle)
        finally:
            await c.aclose()

    return asyncio.run(go())


def ok(capability):
    return 200, {"v": client.VERSION, "throttled": False, "capability": capability}


# ---- the secret -------------------------------------------------------------


@pytest.mark.parametrize(
    "secret, usable",
    [("x" * 32, True), ("x" * 72, True), ("x" * 31, False), ("x" * 73, False), ("", False), (None, False),
     ("x" * 31 + " ", False), ("x" * 31 + "é", False), ("x" * 31 + "\n", False)],
)
def test_the_secret_is_32_to_72_printable_ascii(secret, usable):
    assert client.usable_secret(secret) is usable


def test_the_secret_comes_from_its_own_variable(monkeypatch):
    monkeypatch.setenv("ROUNDS_SHARE_RESOLVER_PASSWORD", SECRET)
    assert client.secret_from_env() == SECRET
    monkeypatch.setenv("ROUNDS_SHARE_RESOLVER_PASSWORD", "short")
    assert client.secret_from_env() is None
    monkeypatch.delenv("ROUNDS_SHARE_RESOLVER_PASSWORD")
    assert client.secret_from_env() is None


# ---- the calls --------------------------------------------------------------


def test_it_logs_in_as_share_resolver_and_sends_only_the_digest_and_throttle_keys():
    fake = FakePocketBase([ok(CAPABILITY)])
    out = _lookup(fake)
    assert out == client.Lookup(False, 0, CAPABILITY)
    login, call = fake.requests
    assert login.url.path == "/api/collections/share_resolvers/auth-with-password"
    assert json.loads(login.content) == {"identity": "share-resolver", "password": SECRET}
    assert call.url.path == "/api/rounds/share/lookup" and call.method == "POST"
    assert call.headers["authorization"] == "Bearer session-1"
    assert json.loads(call.content) == {
        "digest": DIGEST,
        "throttle": [{"scope": s, "key": k} for s, k in KEYS],
    }
    # Nothing that names the caller travels with it.
    for name in ("x-real-ip", "x-forwarded-for", "forwarded", "cookie"):
        assert name not in call.headers


def test_a_session_is_reused_and_logs_in_again_once_when_refused():
    fake = FakePocketBase([ok(None), (401, {}), ok(None)])

    async def go():
        c = _client(fake)
        try:
            first = await c.lookup(DIGEST, KEYS)
            second = await c.lookup(DIGEST, KEYS)
        finally:
            await c.aclose()
        return first, second

    first, second = asyncio.run(go())
    assert first == second == client.Lookup(False, 0, None)
    assert fake.logins == 2
    paths = [r.url.path for r in fake.requests]
    assert paths == [client.LOGIN_PATH, client.LOOKUP_PATH, client.LOOKUP_PATH, client.LOGIN_PATH, client.LOOKUP_PATH]


def test_refused_twice_is_unavailable():
    fake = FakePocketBase([(403, {}), (403, {})])
    with pytest.raises(client.Unavailable):
        _lookup(fake)
    assert fake.logins == 2


def test_a_rejected_login_is_unavailable_and_sends_no_lookup():
    fake = FakePocketBase([], login_status=400)
    with pytest.raises(client.LoginRejected):
        _lookup(fake)
    assert [r.url.path for r in fake.requests] == [client.LOGIN_PATH]


def test_throttled_answers_its_wait():
    fake = FakePocketBase([(200, {"v": client.VERSION, "throttled": True, "retry_after": 42})])
    assert _lookup(fake) == client.Lookup(True, 42, None)


@pytest.mark.parametrize(
    "answer",
    [
        (500, {"v": client.VERSION, "throttled": False, "capability": None}),
        (404, {"v": client.VERSION, "throttled": False, "capability": None}),
        (200, {"throttled": False, "capability": None}),
        (200, {"v": "share-lookup/v2", "throttled": False, "capability": None}),
        (200, {"v": client.VERSION, "throttled": True}),
        (200, {"v": client.VERSION, "throttled": True, "retry_after": 0}),
        (200, {"v": client.VERSION, "throttled": True, "retry_after": "5"}),
        (200, {"v": client.VERSION, "throttled": True, "retry_after": 5, "capability": None}),
        (200, {"v": client.VERSION, "throttled": False}),
        (200, {"v": client.VERSION, "throttled": "no", "capability": None}),
        (200, {"v": client.VERSION, "throttled": False, "capability": dict(CAPABILITY, extra="x")}),
        (200, {"v": client.VERSION, "throttled": False, "capability": {k: v for k, v in CAPABILITY.items() if k != "markup"}}),
        (200, {"v": client.VERSION, "throttled": False, "capability": dict(CAPABILITY, id="../x")}),
        (200, {"v": client.VERSION, "throttled": False, "capability": dict(CAPABILITY, snapshot=None)}),
        (200, {"v": client.VERSION, "throttled": False, "capability": dict(CAPABILITY, capability_version=0)}),
        (200, {"v": client.VERSION, "throttled": False, "capability": dict(CAPABILITY, capability_version=True)}),
        (200, {"v": client.VERSION, "throttled": False, "capability": dict(CAPABILITY, markup=None)}),
        (200, {"v": client.VERSION, "throttled": False, "capability": []}),
        (200, b"not json"),
        (200, ["a list"]),
    ],
)
def test_any_answer_outside_the_contract_is_unavailable(answer):
    fake = FakePocketBase([answer])
    with pytest.raises(client.Unavailable):
        _lookup(fake)


def test_a_transport_error_is_unavailable():
    fake = FakePocketBase([httpx.ConnectError("down")])
    with pytest.raises(client.Unavailable):
        _lookup(fake)


@pytest.mark.parametrize(
    "bearer_digest, throttle",
    [
        ("D" * 64, KEYS),
        ("d" * 63, KEYS),
        (DIGEST, [("ip_hour", "1" * 64)]),
        (DIGEST, [("ip_minute", "1" * 63)]),
        (DIGEST, [("ip_minute", None)]),
    ],
)
def test_only_a_digest_and_throttle_keys_can_be_sent(bearer_digest, throttle):
    with pytest.raises(ValueError):
        client.lookup_request(bearer_digest, throttle)
