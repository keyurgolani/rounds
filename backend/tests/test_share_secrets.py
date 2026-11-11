"""Share link secrets (ROUNDS-00B-L04, app/share_secrets.py): the bearer's
format, its keyed digest, the separation of the keys derived from
AI_KEY_SECRET, and the resolver throttle's keys."""
from __future__ import annotations

import base64
import hashlib
import hmac
import re

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app import obs, share_secrets

SECRET = "test-share-secret-placeholder-0123456789"


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("AI_KEY_SECRET", SECRET)
    obs.reset_pseudonym_key()
    yield
    obs.reset_pseudonym_key()


def _hkdf(info: bytes, root: str = SECRET) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(root.encode())


# ---- the bearer -------------------------------------------------------------


def test_a_new_bearer_is_sd1_and_128_random_bits():
    token = share_secrets.new_token()
    assert re.fullmatch(r"sd1_[A-Za-z0-9_-]{22}", token)
    raw = base64.urlsafe_b64decode(token[4:] + "==")
    assert len(raw) == 16
    assert share_secrets.well_formed(token) and share_secrets.current(token)


def test_bearers_never_repeat():
    tokens = {share_secrets.new_token() for _ in range(2000)}
    assert len(tokens) == 2000


@pytest.mark.parametrize(
    "value, well_formed, key_id",
    [
        ("sd1_" + "A" * 22, True, "sd1"),
        ("sd2_" + "A" * 22, True, "sd2"),
        ("sd999_" + "a-_9" * 5 + "Zz", True, "sd999"),
        ("sd1000_" + "A" * 22, False, None),
        ("sd_" + "A" * 22, False, None),
        ("sd1_" + "A" * 21, False, None),
        ("sd1_" + "A" * 23, False, None),
        ("sd1_" + "A" * 21 + "=", False, None),
        ("sd1_" + "A" * 21 + "+", False, None),
        ("SD1_" + "A" * 22, False, None),
        ("sd1-" + "A" * 22, False, None),
        ("A" * 22, False, None),
        (" sd1_" + "A" * 22, False, None),
        ("sd1_" + "A" * 22 + "\n", False, None),
        (None, False, None),
        (12345, False, None),
    ],
)
def test_the_well_formed_pattern_and_the_key_id(value, well_formed, key_id):
    assert share_secrets.well_formed(value) is well_formed
    assert share_secrets.key_id(value) == key_id
    assert share_secrets.current(value) is (key_id == "sd1")


# ---- the digest -------------------------------------------------------------


def test_the_digest_is_hmac_sha256_under_the_digest_label():
    token = share_secrets.new_token()
    expected = hmac.new(_hkdf(b"rounds/share-digest/v1"), token.encode(), hashlib.sha256).hexdigest()
    assert share_secrets.digest(token) == expected
    assert re.fullmatch(r"[0-9a-f]{64}", expected)


def test_the_digest_is_stable_and_differs_per_bearer_and_per_secret(monkeypatch):
    a, b = share_secrets.new_token(), share_secrets.new_token()
    assert share_secrets.digest(a) == share_secrets.digest(a)
    assert share_secrets.digest(a) != share_secrets.digest(b)
    before = share_secrets.digest(a)
    monkeypatch.setenv("AI_KEY_SECRET", SECRET + "-rotated")
    assert share_secrets.digest(a) != before


@pytest.mark.parametrize("value", ["sd2_" + "A" * 22, "sd1_" + "A" * 21, "", None])
def test_only_a_current_bearer_is_digested(value):
    with pytest.raises(ValueError):
        share_secrets.digest(value)


def test_the_digest_never_contains_the_bearer():
    token = share_secrets.new_token()
    assert token[4:] not in share_secrets.digest(token)


def test_digests_compare_in_constant_time_and_only_as_digests():
    d = share_secrets.digest(share_secrets.new_token())
    assert share_secrets.same_digest(d, d)
    assert not share_secrets.same_digest(d, "0" * 64)
    assert not share_secrets.same_digest(d, d.upper())
    assert not share_secrets.same_digest(d, None)
    assert not share_secrets.same_digest("é" * 64, "é" * 64)


def test_without_the_secret_nothing_is_derived(monkeypatch):
    monkeypatch.delenv("AI_KEY_SECRET")
    token = share_secrets.new_token()
    with pytest.raises(share_secrets.Unavailable):
        share_secrets.digest(token)
    with pytest.raises(share_secrets.Unavailable):
        share_secrets.ip_pseudonym("203.0.113.7")
    with pytest.raises(share_secrets.Unavailable):
        share_secrets.throttle_keys("a" * 32, "b" * 64, True)


def test_the_labels_and_key_versions_are_pinned():
    assert share_secrets.KEY_ID == "sd1" and share_secrets.DIGEST_KEY_VERSION == 1
    assert share_secrets.DIGEST_INFO == b"rounds/share-digest/v1"
    assert share_secrets.THROTTLE_INFO == b"rounds/share-throttle/v1"
    assert share_secrets.LEGACY_RECEIPT_INFO == b"rounds/legacy-share-receipt/v1"


def test_every_key_from_the_secret_is_separate():
    keys = {
        "digest": _hkdf(b"rounds/share-digest/v1"),
        "throttle": _hkdf(b"rounds/share-throttle/v1"),
        "receipt": _hkdf(b"rounds/legacy-share-receipt/v1"),
        "obs": _hkdf(b"rounds/obs/account-pseudonym/v1"),
        "scan": _hkdf(b"rounds/legacy-snapshot-scan/v1"),
        # app.crypto's AES key.
        "aes": hashlib.sha256(SECRET.encode()).digest(),
    }
    assert len(set(keys.values())) == len(keys)
    assert share_secrets._derive(share_secrets.DIGEST_INFO) == keys["digest"]
    assert share_secrets._derive(share_secrets.THROTTLE_INFO) == keys["throttle"]


# ---- the throttle -----------------------------------------------------------


def test_a_pseudonym_is_16_bytes_of_hmac_and_never_the_address():
    p = share_secrets.ip_pseudonym("203.0.113.7")
    expected = hmac.new(_hkdf(b"rounds/share-throttle/v1"), b"4:" + bytes([203, 0, 113, 7]), hashlib.sha256)
    assert p == expected.digest()[:16].hex()
    assert re.fullmatch(r"[0-9a-f]{32}", p)


def test_ipv4_counts_by_address_and_ipv6_by_its_64():
    assert share_secrets.ip_pseudonym("203.0.113.7") != share_secrets.ip_pseudonym("203.0.113.8")
    assert share_secrets.ip_pseudonym("2001:db8:1:2::1") == share_secrets.ip_pseudonym("2001:db8:1:2:ffff:ffff:ffff:ffff")
    assert share_secrets.ip_pseudonym("2001:db8:1:2::1") != share_secrets.ip_pseudonym("2001:db8:1:3::1")
    # An IPv4-mapped IPv6 address is the IPv4 client.
    assert share_secrets.ip_pseudonym("::ffff:203.0.113.7") == share_secrets.ip_pseudonym("203.0.113.7")
    # The /64 of an IPv6 address never collides with an IPv4 address.
    assert share_secrets.ip_pseudonym("cb00:7107::") != share_secrets.ip_pseudonym("203.0.113.7")


@pytest.mark.parametrize("value", [None, "", "not-an-address", "203.0.113.999"])
def test_an_unreadable_address_shares_one_pseudonym(value):
    assert share_secrets.ip_pseudonym(value) == share_secrets.ip_pseudonym(None)
    assert share_secrets.ip_pseudonym(value) != share_secrets.ip_pseudonym("203.0.113.7")


def test_the_throttle_keys_come_in_order_and_only_with_a_password_for_tries():
    p = share_secrets.ip_pseudonym("203.0.113.7")
    d = share_secrets.digest(share_secrets.new_token())
    with_password = share_secrets.throttle_keys(p, d, True)
    assert [scope for scope, _ in with_password] == ["ip_minute", "pw_15m", "digest_day"]
    without = share_secrets.throttle_keys(p, d, False)
    assert [scope for scope, _ in without] == ["ip_minute", "digest_day"]
    assert dict(without) == {k: v for k, v in with_password if k != "pw_15m"}
    for _, key in with_password:
        assert re.fullmatch(r"[0-9a-f]{64}", key)
        assert key not in (p, d) and p not in key and d not in key


def test_the_throttle_keys_separate_clients_and_bearers():
    p1, p2 = share_secrets.ip_pseudonym("203.0.113.7"), share_secrets.ip_pseudonym("198.51.100.4")
    d1, d2 = (share_secrets.digest(share_secrets.new_token()) for _ in range(2))
    k = lambda p, d: dict(share_secrets.throttle_keys(p, d, True))  # noqa: E731
    # The client's minute follows the client only; the bearer's day the bearer only.
    assert k(p1, d1)["ip_minute"] == k(p1, d2)["ip_minute"] != k(p2, d1)["ip_minute"]
    assert k(p1, d1)["digest_day"] == k(p2, d1)["digest_day"] != k(p1, d2)["digest_day"]
    # Password tries follow the pair.
    assert len({k(p, d)["pw_15m"] for p in (p1, p2) for d in (d1, d2)}) == 4


@pytest.mark.parametrize("pseudonym, bearer_digest", [("a" * 31, "b" * 64), ("a" * 32, "b" * 63), ("A" * 32, "b" * 64),
                                                     (None, "b" * 64), ("a" * 32, None)])
def test_the_throttle_keys_take_only_a_pseudonym_and_a_digest(pseudonym, bearer_digest):
    with pytest.raises(ValueError):
        share_secrets.throttle_keys(pseudonym, bearer_digest, False)
