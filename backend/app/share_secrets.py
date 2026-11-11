"""Share link secrets (ROUNDS-00B-L04): the bearer, its keyed digest, and
the resolver throttle's keys.

A share link's secret is an ``sd1`` bearer: ``sd1_`` and the unpadded
base64url of 16 random bytes, where ``sd1`` names the key its digest is made
under. Rounds stores only that digest, hex HMAC-SHA256 under a key HKDF-SHA256
derives from ``AI_KEY_SECRET``. The bearer itself lives in runner memory and
in the one response that issues it.

Three labels share that secret, each apart from ``app.crypto``'s AES key and
``app.obs``'s pseudonym key:

  rounds/share-digest/v1          the bearer digest, key version 1
  rounds/share-throttle/v1        the resolver throttle's keys
  rounds/legacy-share-receipt/v1  reserved for ROUNDS-00B-L06

The resolver throttle counts by keys made under the second label from a
client address pseudonym and the submitted bearer's digest. So a throttle
row holds neither an address nor a digest, and the throttle can count before
any lookup, whether or not the bearer is live.

Only the runner holds these keys. With ``AI_KEY_SECRET`` unset, every
derivation raises ``Unavailable``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import logging
import os
import re
import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_log = logging.getLogger(__name__)

SECRET_ENV = "AI_KEY_SECRET"
# app.crypto's development placeholder: accepted with a warning, as there.
_DEV_SECRET = "rounds-dev-key-DO-NOT-USE-IN-PROD"

# The current key id, and the key version its digests are stored under.
KEY_ID = "sd1"
DIGEST_KEY_VERSION = 1
TOKEN_BYTES = 16
# Any key id the format allows. Only KEY_ID resolves; a bearer under another
# key id answers as an unknown one.
WELL_FORMED = re.compile(r"sd[0-9]{1,3}_[A-Za-z0-9_-]{22}")
DIGEST = re.compile(r"[0-9a-f]{64}")

DIGEST_INFO = b"rounds/share-digest/v1"
THROTTLE_INFO = b"rounds/share-throttle/v1"
# Reserved for ROUNDS-00B-L06's receipts; nothing here derives it.
LEGACY_RECEIPT_INFO = b"rounds/legacy-share-receipt/v1"

# The throttle's scopes, in the order the resolver counts them: resolves a
# minute per client, password tries per 15 minutes per client and bearer,
# and resolves a day per bearer.
IP_MINUTE = "ip_minute"
PASSWORD_15M = "pw_15m"
DIGEST_DAY = "digest_day"
SCOPES = (IP_MINUTE, PASSWORD_15M, DIGEST_DAY)
PSEUDONYM_BYTES = 16
PSEUDONYM = re.compile(r"[0-9a-f]{32}")
# An IPv6 client counts by its /64, the smallest block one is usually given.
IPV6_PREFIX_BYTES = 8


class Unavailable(Exception):
    """``AI_KEY_SECRET`` is unset, so no share key can be derived."""


# ---------------------------------------------------------------------------
# The bearer
# ---------------------------------------------------------------------------


def new_token() -> str:
    """A fresh bearer under the current key id: 128 random bits."""
    raw = base64.urlsafe_b64encode(secrets.token_bytes(TOKEN_BYTES)).rstrip(b"=").decode("ascii")
    return f"{KEY_ID}_{raw}"


def well_formed(value: object) -> bool:
    return isinstance(value, str) and WELL_FORMED.fullmatch(value) is not None


def key_id(value: object) -> str | None:
    """The key id of a well-formed bearer, else None."""
    return value.split("_", 1)[0] if well_formed(value) else None  # type: ignore[union-attr]


def current(value: object) -> bool:
    """Well formed and under the current key id."""
    return key_id(value) == KEY_ID


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------

_warned = False


def _root() -> bytes:
    global _warned
    raw = os.environ.get(SECRET_ENV, "")
    if not raw:
        raise Unavailable
    if raw == _DEV_SECRET and not _warned:
        _log.warning("%s is the development placeholder, so share links made here work only with it.", SECRET_ENV)
        _warned = True
    return raw.encode("utf-8")


def _derive(info: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(_root())


def digest(token: str) -> str:
    """The stored digest of a current bearer: 64 hex characters."""
    if not current(token):
        raise ValueError("not a current share bearer")
    return hmac.new(_derive(DIGEST_INFO), token.encode("ascii"), hashlib.sha256).hexdigest()


def same_digest(a: object, b: object) -> bool:
    """Whether two digests are equal, compared in constant time."""
    if not (isinstance(a, str) and isinstance(b, str) and DIGEST.fullmatch(a) and DIGEST.fullmatch(b)):
        return False
    return hmac.compare_digest(a, b)


# ---------------------------------------------------------------------------
# The resolver throttle
# ---------------------------------------------------------------------------


def _address_input(address: str | None) -> bytes:
    """What a client address counts as: an IPv4 address (an IPv4-mapped IPv6
    one included), or an IPv6 address's /64. Anything unreadable counts as
    one shared client."""
    if address is None:
        return b"none"
    try:
        ip = ipaddress.ip_address(address.strip())
    except ValueError:
        return b"none"
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if isinstance(ip, ipaddress.IPv4Address):
        return b"4:" + ip.packed
    return b"6:" + ip.packed[:IPV6_PREFIX_BYTES]


def ip_pseudonym(address: str | None) -> str:
    """The throttle's handle for a client address: HMAC-SHA256 under the
    throttle key, cut to 16 bytes, as 32 hex characters. The address itself
    is never stored."""
    mac = hmac.new(_derive(THROTTLE_INFO), _address_input(address), hashlib.sha256).digest()
    return mac[:PSEUDONYM_BYTES].hex()


def throttle_keys(pseudonym: str, bearer_digest: str, password: bool) -> list[tuple[str, str]]:
    """The counters one resolve bumps, in order, as (scope, key): the
    client's minute, the client's password tries on this bearer when a
    password came with it, and the bearer's day. Each key is HMAC-SHA256
    under the throttle key, so none holds the pseudonym or the digest."""
    if not isinstance(pseudonym, str) or PSEUDONYM.fullmatch(pseudonym) is None:
        raise ValueError("not a client pseudonym")
    if not isinstance(bearer_digest, str) or DIGEST.fullmatch(bearer_digest) is None:
        raise ValueError("not a bearer digest")
    key = _derive(THROTTLE_INFO)

    def counter(*parts: str) -> str:
        return hmac.new(key, "|".join(parts).encode("ascii"), hashlib.sha256).hexdigest()

    out = [(IP_MINUTE, counter(IP_MINUTE, pseudonym))]
    if password:
        out.append((PASSWORD_15M, counter(PASSWORD_15M, pseudonym, bearer_digest)))
    out.append((DIGEST_DAY, counter(DIGEST_DAY, bearer_digest)))
    return out
