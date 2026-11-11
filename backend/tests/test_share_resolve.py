"""The share capability resolver (ROUNDS-00B-L03 stage 2).

The guarantees checked here:

  * every request that doesn't resolve gets one 404 with the same bytes and
    headers: the public share switch, the closed gate, a body of any other
    shape, a token in any other format, a token that resolves nothing (no
    such capability, or one expired, revoked, or another account's), and
    the lookup failing;
  * the switch, the gate, and the request's shape are decided before any
    lookup, and every well-formed token makes exactly one;
  * a capability that resolves answers only its markup and the projection
    version, with the same headers;
  * nothing is cached: the next request asks again;
  * each request logs one line with a coarse outcome, and the capability id
    only when one resolves, never the token.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest

from app import share_capabilities

URL = "/api/share/resolve"
TOKEN = "sd1_AbCdEfGhIjKlMnOpQrStUv"
CAP_ID = "capaaaaaaaaaaa1"
MARKUP = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Resume</title></head><body><p>Ada é</p></body></html>'
GATE = "ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION"
SWITCH = "ROUNDS_GATE_PUBLIC_SHARES"
ALIAS = "ROUNDS_DISABLE_PUBLIC_SHARES"
OPEN = {GATE: "enabled"}
NOT_FOUND = b'{"detail":"Not found."}'


class FakeLookup:
    """Answers per token; a token it doesn't know resolves nothing. #12's
    lookup (app/share_resolver.py) also takes any password and the client's
    address; its own tests are test_share_resolver.py."""

    def __init__(self, answers: dict | None = None, fail: Exception | None = None) -> None:
        self.answers = dict(answers or {})
        self.fail = fail
        self.calls: list[str] = []

    async def __call__(self, token: str, password: str | None = None, address: str | None = None):
        self.calls.append(token)
        if self.fail is not None:
            raise self.fail
        return self.answers.get(token)


@pytest.fixture
def lookup(monkeypatch):
    fake = FakeLookup({TOKEN: share_capabilities.Found(CAP_ID, MARKUP)})
    monkeypatch.setattr(share_capabilities, "lookup", fake)
    for name in (GATE, SWITCH, ALIAS):
        monkeypatch.delenv(name, raising=False)
    return fake


def _post(client, monkeypatch, body=None, *, raw=None, media="application/json", env=None):
    # Each request sees only the env it names; the default is an open gate.
    for name in (GATE, SWITCH, ALIAS):
        monkeypatch.delenv(name, raising=False)
    for name, value in (env if env is not None else OPEN).items():
        monkeypatch.setenv(name, value)
    if raw is not None:
        return client.post(URL, content=raw, headers={"Content-Type": media})
    return client.post(URL, content=json.dumps(body if body is not None else {"token": TOKEN}),
                       headers={"Content-Type": media})


def _headers(res):
    keep = {k.lower() for k in share_capabilities.RESOLVER_HEADERS}
    return {k.lower(): v for k, v in res.headers.items() if k.lower() in keep}


WANT_HEADERS = {k.lower(): v for k, v in share_capabilities.RESOLVER_HEADERS.items()}


def _lines(capsys) -> list[dict]:
    out = capsys.readouterr().out
    return [json.loads(line) for line in out.splitlines() if line.startswith("{") and '"share.resolve"' in line]


# ---- what resolves ---------------------------------------------------------


def test_a_capability_that_resolves_answers_only_its_markup_and_the_projection_version(client, monkeypatch, lookup):
    res = _post(client, monkeypatch)
    assert res.status_code == 200
    assert res.json() == {"projection_version": 1, "markup": MARKUP}
    assert _headers(res) == WANT_HEADERS
    assert lookup.calls == [TOKEN]


def test_the_answer_names_no_capability_owner_snapshot_or_purpose(client, monkeypatch, lookup):
    text = _post(client, monkeypatch).text
    for value in (CAP_ID, TOKEN, "snapshot", "purpose", "user", "expires_at", "password"):
        assert value not in text, value


# ---- what doesn't --------------------------------------------------------


def _oversized() -> bytes:
    return ('{"token": "' + TOKEN + '"' + " " * 2100 + "}").encode()


FAILURES = {
    # The public share switch, as its alias and as the gate.
    "switch-alias": dict(env={**OPEN, ALIAS: "true"}),
    "switch-alias-garbage": dict(env={**OPEN, ALIAS: "on"}),
    "switch-gate": dict(env={**OPEN, SWITCH: "disabled"}),
    # Resolution closed: by default, or by a value outside the gate's list.
    "gate-default": dict(env={}),
    "gate-disabled": dict(env={GATE: "disabled"}),
    "gate-invalid": dict(env={GATE: "true"}),
    # Any other shape of request.
    "form-encoded": dict(raw=b"token=" + TOKEN.encode(), media="application/x-www-form-urlencoded"),
    "text-media": dict(raw=json.dumps({"token": TOKEN}).encode(), media="text/plain"),
    "not-json": dict(raw=b"{token:", media="application/json"),
    "not-utf8": dict(raw=b'{"token": "\xff"}', media="application/json"),
    "array": dict(body=[TOKEN]),
    "empty-object": dict(body={}),
    "extra-field": dict(body={"token": TOKEN, "purpose": "placeholder"}),
    "password-number": dict(body={"token": TOKEN, "password": 7}),
    "password-list": dict(body={"token": TOKEN, "password": ["placeholder"]}),
    "password-only": dict(body={"password": "placeholder"}),
    "number": dict(body={"token": 7}),
    "null": dict(body={"token": None}),
    "oversized": dict(raw=_oversized(), media="application/json"),
    # Any other token format.
    "short": dict(body={"token": "sd1_AbCd"}),
    "long": dict(body={"token": TOKEN + "x"}),
    "no-key-version": dict(body={"token": "AbCdEfGhIjKlMnOpQrStUv"}),
    "odd-key-version": dict(body={"token": "sdx_AbCdEfGhIjKlMnOpQrStUv"}),
    "odd-chars": dict(body={"token": "sd1_AbCdEfGhIjKlMnOp.rStUv"}),
    # Well-formed tokens that resolve nothing: none has the token, or its
    # capability expired, was revoked, or is another account's.
    "unknown": dict(body={"token": "sd1_UnknownUnknownUnknown0"}),
    "expired": dict(body={"token": "sd1_ExpiredExpiredExpired0"}),
    "revoked": dict(body={"token": "sd1_RevokedRevokedRevoked0"}),
    "cross-account": dict(body={"token": "sd1_ForeignForeignForeign0"}),
}


@pytest.fixture
def missing(client, monkeypatch, lookup):
    res = _post(client, monkeypatch, {"token": "sd1_UnknownUnknownUnknown0"})
    assert res.status_code == 404
    return res


@pytest.mark.parametrize("case", sorted(FAILURES))
def test_every_failure_is_byte_identical_to_an_unknown_token(client, monkeypatch, lookup, missing, case):
    res = _post(client, monkeypatch, **FAILURES[case])
    assert res.status_code == 404
    assert res.content == missing.content == NOT_FOUND
    assert _headers(res) == _headers(missing) == WANT_HEADERS


@pytest.mark.parametrize("fail", [share_capabilities.LookupUnavailable("store down"), httpx.ConnectError("refused"),
                                  RuntimeError("anything")])
def test_a_lookup_that_fails_gets_the_same_not_found(client, monkeypatch, lookup, fail):
    lookup.fail = fail
    res = _post(client, monkeypatch)
    assert (res.status_code, res.content, _headers(res)) == (404, NOT_FOUND, WANT_HEADERS)


def test_a_lookup_answer_without_markup_gets_the_same_not_found(client, monkeypatch, lookup):
    lookup.answers[TOKEN] = share_capabilities.Found(CAP_ID, "")
    res = _post(client, monkeypatch)
    assert (res.status_code, res.content) == (404, NOT_FOUND)


def test_the_shipped_lookup_is_the_share_resolvers():
    # ROUNDS-00B-L04's digest, throttle, and password step (app/share_resolver.py).
    assert share_capabilities.lookup is share_capabilities._resolver_lookup


# ---- the order: nothing is looked up before the request is decided ---------------------------------


BEFORE_ANY_LOOKUP = sorted(c for c in FAILURES if c not in ("unknown", "expired", "revoked", "cross-account"))


@pytest.mark.parametrize("case", BEFORE_ANY_LOOKUP)
def test_the_switch_the_gate_and_the_shape_come_before_any_lookup(client, monkeypatch, lookup, case):
    _post(client, monkeypatch, **FAILURES[case])
    assert lookup.calls == []


@pytest.mark.parametrize("case", ["unknown", "expired", "revoked", "cross-account"])
def test_each_well_formed_token_makes_exactly_one_lookup(client, monkeypatch, lookup, case):
    # A token that resolves nothing costs the same one lookup as one that
    # resolves, whatever stopped it.
    _post(client, monkeypatch, **FAILURES[case])
    assert lookup.calls == [FAILURES[case]["body"]["token"]]


# ---- no cache --------------------------------------------------------------


def test_nothing_is_cached_between_requests(client, monkeypatch, lookup):
    assert _post(client, monkeypatch).status_code == 200
    # The owner revokes; the very next request asks again and gets nothing.
    lookup.answers.pop(TOKEN)
    second = _post(client, monkeypatch)
    assert (second.status_code, second.content) == (404, NOT_FOUND)
    assert lookup.calls == [TOKEN, TOKEN]
    assert _post(client, monkeypatch, env={**OPEN, ALIAS: "true"}).status_code == 404
    assert lookup.calls == [TOKEN, TOKEN]


# ---- logs ---------------------------------------------------------------------


@pytest.mark.parametrize("case, code, record", [
    ("available", "available", CAP_ID),
    ("switch-alias", "kill_switch", None),
    ("gate-default", "gate_closed", None),
    ("extra-field", "not_found", None),
    ("unknown", "not_found", None),
    ("degraded", "degraded", None),
])
def test_each_request_logs_one_coarse_outcome_and_never_the_token(client, monkeypatch, lookup, capsys, caplog,
                                                                   case, code, record):
    capsys.readouterr()
    if case == "available":
        _post(client, monkeypatch)
    elif case == "degraded":
        lookup.fail = share_capabilities.LookupUnavailable("store down")
        _post(client, monkeypatch)
    else:
        _post(client, monkeypatch, **FAILURES[case])
    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.splitlines()
             if line.startswith("{") and '"share.resolve"' in line]
    (line,) = lines
    assert line["code"] == code
    assert line.get("record") == record
    assert set(line) <= {"v", "event", "correlation_id", "record", "code"}
    everything = captured.out + captured.err + caplog.text
    for secret in (TOKEN, "sd1_UnknownUnknownUnknown0", MARKUP, "placeholder"):
        assert secret not in everything


# ---- the deployment verifier checks the same answer ---------------------------------


def test_the_not_found_matches_what_the_deployment_verifier_checks(client, monkeypatch, missing):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))
    import verify_deployment as vd

    assert _headers(missing) == dict(vd.SHARE_HEADERS, **{"content-security-policy": vd.SHARE_READ_CSP})
    assert missing.content == vd.SHARE_NOT_FOUND
    malformed, unknown = (body["token"] for _label, body in vd.SHARE_RESOLVE_BODIES)
    assert share_capabilities.TOKEN_RE.fullmatch(malformed) is None
    assert share_capabilities.TOKEN_RE.fullmatch(unknown) is not None


def test_both_resolvers_answer_with_one_set_of_headers():
    from routers import share

    assert share.PUBLIC_HEADERS is share_capabilities.RESOLVER_HEADERS
    assert share.NOT_FOUND_BODY is share_capabilities.NOT_FOUND_BODY
