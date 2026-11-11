"""The share resolver's lookup (ROUNDS-00B-L04, app/share_resolver.py), as
#11's resolver answers with it.

The guarantees checked here:

  * a throttled client gets 429 with Retry-After and the resolver headers,
    the same for a live bearer and an unknown one, and no password is
    verified for it;
  * a submitted password costs one verify, never more or fewer: an unknown
    bearer, an unprotected capability, another profile, and a wrong password
    each run one, and no password runs none;
  * a missing or wrong password, a revoked or expired answer, another key
    id, and an unset key all answer the bytes an unknown bearer gets;
  * PocketBase gets the bearer's digest and the throttle's keys, never the
    bearer, the password, or the client's address;
  * the throttle counts by X-Real-IP only from a trusted proxy;
  * nothing is cached, so a rotated bearer stops resolving at once;
  * no line holds the bearer or the password.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest
from starlette.requests import Request

from app import share_capabilities, share_password, share_resolver, share_resolver_client, share_secrets

URL = "/api/share/resolve"
GATE = "ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION"
SECRET = "share-resolver-test-ai-key-secret-0123456789"
TOKEN = "sd1_AbCdEfGhIjKlMnOpQrStUv"
OTHER = "sd1_ZyXwVuTsRqPoNmLkJiHgFe"
UNKNOWN = "sd1_UnknownUnknownUnknown0"
CAP_ID = "capaaaaaaaaaaa1"
MARKUP = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Resume</title></head><body><p>Ada</p></body></html>'
PASSWORD = "correct horse battery"
WRONG = "not the password at all"
VERIFIER = asyncio.run(share_password.hash_password(PASSWORD))
NOT_FOUND = b'{"detail":"Not found."}'
WANT_HEADERS = {k.lower(): v for k, v in share_capabilities.RESOLVER_HEADERS.items()}


def _later(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S.000Z")


def capability(verifier: str = "", **over) -> dict:
    fields = {"id": CAP_ID, "status": "active", "expires_at": _later(), "capability_version": 1,
              "snapshot": "snapaaaaaaaaaa1", "password_policy_ref": verifier, "markup": MARKUP}
    fields.update(over)
    return fields


class FakeResolver:
    """PocketBase's lookup route as share-resolver: capabilities by digest,
    and a throttle that's over its limit for every key or none."""

    def __init__(self) -> None:
        self.by_digest: dict[str, dict] = {}
        self.throttled = False
        self.calls: list[tuple[str, list[tuple[str, str]]]] = []
        self.fail: Exception | None = None

    def share(self, token: str, fields: dict) -> None:
        self.by_digest[share_secrets.digest(token)] = fields

    async def lookup(self, bearer_digest, throttle):
        self.calls.append((bearer_digest, list(throttle)))
        if self.fail is not None:
            raise self.fail
        if self.throttled:
            return share_resolver_client.Lookup(True, 120, None)
        return share_resolver_client.Lookup(False, 0, self.by_digest.get(bearer_digest))


@pytest.fixture
def resolver(monkeypatch):
    monkeypatch.setenv("AI_KEY_SECRET", SECRET)
    monkeypatch.setenv(GATE, "enabled")
    for name in ("ROUNDS_GATE_PUBLIC_SHARES", "ROUNDS_DISABLE_PUBLIC_SHARES"):
        monkeypatch.delenv(name, raising=False)
    fake = FakeResolver()
    monkeypatch.setattr(share_resolver, "resolver", lambda: fake)
    return fake


@pytest.fixture
def verifies(monkeypatch):
    """Counts the Argon2id verifies, after the dummy exists, as at start."""
    share_password._dummy_verifier()
    calls: list[str] = []

    class Counting:
        def __init__(self, inner):
            self.inner = inner

        def hash(self, password):
            return self.inner.hash(password)

        def verify(self, hash_, password):
            calls.append(hash_)
            return self.inner.verify(hash_, password)

    monkeypatch.setattr(share_password, "_hasher", Counting(share_password._hasher))
    return calls


def _post(client, token=TOKEN, password=None, **extra):
    body = {"token": token, **({"password": password} if password is not None else {}), **extra}
    return client.post(URL, content=json.dumps(body), headers={"Content-Type": "application/json"})


def _headers(res) -> dict:
    return {k.lower(): v for k, v in res.headers.items() if k.lower() in WANT_HEADERS}


# ---- resolving -------------------------------------------------------------------------------------------


def test_an_unprotected_capability_resolves_without_a_password(client, resolver, verifies):
    resolver.share(TOKEN, capability())
    res = _post(client)
    assert res.status_code == 200
    assert res.json() == {"projection_version": 1, "markup": MARKUP}
    assert len(resolver.calls) == 1 and verifies == []


def test_a_protected_capability_resolves_only_with_its_password(client, resolver):
    resolver.share(TOKEN, capability(VERIFIER))
    unknown = _post(client, UNKNOWN)
    assert unknown.content == NOT_FOUND
    without, wrong, right = _post(client), _post(client, password=WRONG), _post(client, password=PASSWORD)
    assert (without.status_code, without.content, _headers(without)) == (404, NOT_FOUND, WANT_HEADERS)
    assert (wrong.status_code, wrong.content, _headers(wrong)) == (404, NOT_FOUND, WANT_HEADERS)
    assert right.status_code == 200 and right.json()["markup"] == MARKUP


CASES = {
    # case: (what the token's digest finds, the password sent, the status, the verifies)
    "unknown, no password": (None, None, 404, 0),
    "unknown, a password": (None, WRONG, 404, 1),
    "unprotected, no password": (capability(), None, 200, 0),
    "unprotected, a password": (capability(), WRONG, 200, 1),
    "another profile, no password": (capability("pw2" + VERIFIER[3:]), None, 404, 0),
    "another profile, its password": (capability("pw2" + VERIFIER[3:]), PASSWORD, 404, 1),
    "protected, no password": (capability(VERIFIER), None, 404, 0),
    "protected, a wrong password": (capability(VERIFIER), WRONG, 404, 1),
    "protected, a password that could never match": (capability(VERIFIER), "x" * 300, 404, 1),
    "protected, the password": (capability(VERIFIER), PASSWORD, 200, 1),
}


@pytest.mark.parametrize("case", list(CASES))
def test_every_password_sent_costs_one_verify_and_no_password_costs_none(client, resolver, verifies, case):
    found, password, status, count = CASES[case]
    if found is not None:
        resolver.share(TOKEN, found)
    res = _post(client, password=password)
    assert res.status_code == status
    if status == 404:
        assert res.content == NOT_FOUND
    assert len(verifies) == count
    # Against the capability's own verifier only when it's a current one.
    if count and found is not None and share_password.is_current(found["password_policy_ref"]):
        assert verifies == [found["password_policy_ref"][3:]]
    elif count:
        assert verifies == [share_password._dummy_verifier()[3:]]


@pytest.mark.parametrize("over", [{"status": "revoked"}, {"expires_at": "2020-01-01 00:00:00.000Z"},
                                  {"expires_at": "soon"}])
def test_a_revoked_or_expired_answer_is_the_same_not_found(client, resolver, over):
    resolver.share(TOKEN, capability(**over))
    res = _post(client)
    assert (res.status_code, res.content, _headers(res)) == (404, NOT_FOUND, WANT_HEADERS)


def test_another_key_id_resolves_nothing_and_asks_nothing(client, resolver, verifies):
    res = _post(client, "sd2_AbCdEfGhIjKlMnOpQrStUv", password=WRONG)
    assert (res.status_code, res.content) == (404, NOT_FOUND)
    assert resolver.calls == []
    # Its password still costs one verify.
    assert len(verifies) == 1


def test_an_unset_digest_key_is_the_same_not_found(client, resolver, monkeypatch):
    resolver.share(TOKEN, capability())
    monkeypatch.delenv("AI_KEY_SECRET")
    res = _post(client)
    assert (res.status_code, res.content, _headers(res)) == (404, NOT_FOUND, WANT_HEADERS)
    assert resolver.calls == []


@pytest.mark.parametrize("fail", [share_resolver_client.Unavailable(), share_resolver_client.LoginRejected()])
def test_a_lookup_that_cant_answer_is_the_same_not_found(client, resolver, fail):
    resolver.fail = fail
    res = _post(client)
    assert (res.status_code, res.content, _headers(res)) == (404, NOT_FOUND, WANT_HEADERS)


def test_no_resolver_secret_is_the_same_not_found(client, monkeypatch):
    monkeypatch.setenv("AI_KEY_SECRET", SECRET)
    monkeypatch.setenv(GATE, "enabled")
    monkeypatch.delenv(share_resolver_client.SECRET_ENV, raising=False)
    res = _post(client)
    assert (res.status_code, res.content) == (404, NOT_FOUND)


# ---- the throttle ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("password", [None, PASSWORD])
def test_a_throttled_client_gets_429_whether_or_not_its_bearer_is_live(client, resolver, verifies, password):
    resolver.share(TOKEN, capability(VERIFIER))
    resolver.throttled = True
    live, unknown = _post(client, password=password), _post(client, UNKNOWN, password=password)
    for res in (live, unknown):
        assert res.status_code == 429
        assert res.headers["retry-after"] == "120"
        assert res.json() == {"detail": "Too many attempts."}
        assert _headers(res) == WANT_HEADERS
    assert live.content == unknown.content
    assert verifies == []


def test_the_lookup_sends_the_digest_and_the_throttle_keys_only(client, resolver):
    resolver.share(TOKEN, capability(VERIFIER))
    _post(client)
    _post(client, password=PASSWORD)
    (digest, plain), (_, with_password) = resolver.calls
    assert digest == share_secrets.digest(TOKEN)
    assert [scope for scope, _ in plain] == ["ip_minute", "digest_day"]
    assert [scope for scope, _ in with_password] == ["ip_minute", "pw_15m", "digest_day"]
    sent = json.dumps(resolver.calls)
    for secret in (TOKEN, PASSWORD, "testclient"):
        assert secret not in sent


def _request(peer: str, *headers: tuple[bytes, bytes]) -> Request:
    return Request({"type": "http", "method": "POST", "path": URL, "headers": list(headers),
                    "client": (peer, 40000)})


def test_the_throttle_counts_x_real_ip_only_from_a_trusted_proxy(monkeypatch):
    monkeypatch.delenv("ROUNDS_TRUSTED_PROXY_CIDRS", raising=False)
    spoof = (b"x-real-ip", b"203.0.113.9")
    assert share_capabilities._address(_request("10.0.0.5", spoof)) == "203.0.113.9"
    assert share_capabilities._address(_request("198.51.100.7", spoof)) == "198.51.100.7"
    assert share_capabilities._address(_request("198.51.100.7")) == "198.51.100.7"


# ---- no cache ---------------------------------------------------------------------------------------------


def test_a_rotated_bearer_stops_resolving_on_the_next_request(client, resolver):
    resolver.share(TOKEN, capability())
    assert _post(client).status_code == 200
    # RotateShareBearer swaps the digest; the old bearer finds nothing.
    resolver.by_digest = {}
    resolver.share(OTHER, capability(capability_version=2))
    old, new = _post(client), _post(client, OTHER)
    assert (old.status_code, old.content) == (404, NOT_FOUND)
    assert new.status_code == 200
    assert len(resolver.calls) == 3


# ---- logs ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("case, code", [
    ("wrong password", "password_wrong"),
    ("no password", "password_required"),
    ("throttled", "throttled"),
    ("right password", "available"),
])
def test_each_resolve_logs_a_coarse_code_and_never_the_bearer_or_password(client, resolver, capsys, caplog,
                                                                          case, code):
    resolver.share(TOKEN, capability(VERIFIER))
    resolver.throttled = case == "throttled"
    capsys.readouterr()
    _post(client, password={"wrong password": WRONG, "no password": None}.get(case, PASSWORD))
    captured = capsys.readouterr()
    (line,) = [json.loads(x) for x in captured.out.splitlines() if x.startswith("{") and '"share.resolve"' in x]
    assert line["code"] == code
    assert line.get("record") == (CAP_ID if code == "available" else None)
    everything = captured.out + captured.err + caplog.text
    for secret in (TOKEN, PASSWORD, WRONG, share_secrets.digest(TOKEN), VERIFIER):
        assert secret not in everything


# ---- the session ------------------------------------------------------------------------------------------


def test_the_session_is_kept_per_secret(monkeypatch):
    first_secret, second_secret = "s" * 40, "t" * 40

    async def sessions():
        monkeypatch.setenv(share_resolver_client.SECRET_ENV, first_secret)
        a, b = share_resolver.resolver(), share_resolver.resolver()
        monkeypatch.setenv(share_resolver_client.SECRET_ENV, second_secret)
        c = share_resolver.resolver()
        return a, b, c

    monkeypatch.setattr(share_resolver, "_client", None)
    monkeypatch.setattr(share_resolver, "_client_for", None)
    a, b, c = asyncio.run(sessions())
    assert a is b and c is not a


@pytest.mark.parametrize("secret", ["", "short", "x" * 73, "has space" + "x" * 30])
def test_no_usable_resolver_secret_makes_no_session(monkeypatch, secret):
    monkeypatch.setenv(share_resolver_client.SECRET_ENV, secret)

    async def session():
        return share_resolver.resolver()

    with pytest.raises(share_capabilities.LookupUnavailable):
        asyncio.run(session())
