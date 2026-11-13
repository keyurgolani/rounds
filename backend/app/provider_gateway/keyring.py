"""The keyring (ROUNDS-14-L02 stage A).

Every key the runner derives from ``AI_KEY_SECRET`` comes from here.

Root version 1 is ``AI_KEY_SECRET`` as UTF-8 bytes, read exactly as the
share secrets, the signed receipts and the log pseudonyms read it before
this module existed, so every key they made still matches. ``derive(label)``
is HKDF-SHA256 over the root with the label as its info: 32 bytes, no salt.
Each label names one use:

  rounds/share-digest/v1           share link digests (ROUNDS-00B-L04)
  rounds/share-throttle/v1         the share resolver's throttle keys
  rounds/legacy-share-receipt/v1   signed legacy share receipts (ROUNDS-00B-L06)
  rounds/legacy-snapshot-scan/v1   signed snapshot scans (ROUNDS-00A-L04)
  rounds/obs/account-pseudonym/v1  account pseudonyms in log lines (ROUNDS-00A-L01)
  rounds/credential-wrap/v1        saved AI provider keys

A saved provider key is wrapped (``aad-v1``) with AES-256-GCM under the
credential-wrap key, a fresh 96-bit nonce, and associated data that names
its account, its provider, the key version, and the address it was entered
for, so it opens only for that account, that provider and that address.
Keys saved before this release keep their older wrap (``legacy-v0``: AES-GCM
under SHA-256 of the root, with no associated data) until their first good
use rewraps them.

The root is unusable when ``AI_KEY_SECRET`` is unset, or when it is the
development placeholder and ``ROUNDS_ALLOW_DEV_KEY`` isn't true, which only
the development compose files set. Then saved AI provider keys and share
links answer that they're unavailable, and everything else keeps working.
``init`` runs at startup: it logs one line about the root, never its value,
and stops the runner only on a setting that is set and malformed.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import os
import re
import secrets
from dataclasses import dataclass
from typing import Mapping

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app import canonical

SECRET_ENV = "AI_KEY_SECRET"
DEV_OPT_IN_ENV = "ROUNDS_ALLOW_DEV_KEY"
# The development compose files' placeholder. It is public, so it counts
# only where those files opt in.
DEV_SECRET = "rounds-dev-key-DO-NOT-USE-IN-PROD"
ROOT_VERSION = 1
# `openssl rand -hex 32` gives 64; a shorter root still loads, with a warning.
SHORT_ROOT_BYTES = 32

SHARE_DIGEST = b"rounds/share-digest/v1"
SHARE_THROTTLE = b"rounds/share-throttle/v1"
LEGACY_SHARE_RECEIPT = b"rounds/legacy-share-receipt/v1"
LEGACY_SNAPSHOT_SCAN = b"rounds/legacy-snapshot-scan/v1"
OBS_PSEUDONYM = b"rounds/obs/account-pseudonym/v1"
CREDENTIAL_WRAP = b"rounds/credential-wrap/v1"
LABELS = (SHARE_DIGEST, SHARE_THROTTLE, LEGACY_SHARE_RECEIPT, LEGACY_SNAPSHOT_SCAN, OBS_PSEUDONYM, CREDENTIAL_WRAP)

WRAP_AAD_V1 = "aad-v1"
WRAP_LEGACY_V0 = "legacy-v0"
WRAPS = (WRAP_AAD_V1, WRAP_LEGACY_V0)
AAD_SCHEMA = "rounds-aad/v1"
RECORD_TYPE = "ai_credentials"
NONCE_BYTES = 12
# An API key is well under this; a longer value isn't one.
MAX_KEY_BYTES = 4096

_TRUE = ("true", "1", "yes")
_FALSE = ("", "false", "0", "no")
_RECORD_ID = re.compile(r"[a-z0-9]{15}")
_HOST = re.compile(r"[a-z0-9._:-]{1,253}")

_log = logging.getLogger(__name__)


class Unavailable(Exception):
    """No usable root: ``AI_KEY_SECRET`` is unset, or it is the development
    placeholder without ``ROUNDS_ALLOW_DEV_KEY=true``."""


class Malformed(ValueError):
    """A setting that is set but can't be read. The runner doesn't start."""


class CredentialUnusable(Exception):
    """A saved key that doesn't open with its account, provider, and address,
    or whose stored form is damaged."""


def dev_opt_in(env: Mapping[str, str] | None = None) -> bool:
    """Whether ``ROUNDS_ALLOW_DEV_KEY`` lets the development placeholder count.
    Raises Malformed for a value that is neither true nor false."""
    env = os.environ if env is None else env
    raw = (env.get(DEV_OPT_IN_ENV) or "").strip().lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise Malformed(f"{DEV_OPT_IN_ENV} must be true or false")


def _read(env: Mapping[str, str]) -> tuple[bytes | None, str]:
    """The root's bytes, or None, and why: ``loaded``, ``unset``,
    ``development-placeholder`` or ``malformed``."""
    raw = env.get(SECRET_ENV, "")
    if not raw:
        return None, "unset"
    try:
        material = raw.encode("utf-8")
    except UnicodeEncodeError:
        return None, "malformed"
    if raw == DEV_SECRET:
        try:
            allowed = dev_opt_in(env)
        except Malformed:
            allowed = False
        if not allowed:
            return None, "development-placeholder"
    return material, "loaded"


def root(version: int = ROOT_VERSION, env: Mapping[str, str] | None = None) -> bytes:
    """The root key material. Raises Unavailable when there is no usable root."""
    if isinstance(version, bool) or version != ROOT_VERSION:
        raise Unavailable
    material, _ = _read(os.environ if env is None else env)
    if material is None:
        raise Unavailable
    return material


def hkdf(secret: bytes, label: bytes) -> bytes:
    """HKDF-SHA256 over ``secret`` with ``label`` as its info: 32 bytes, no salt."""
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=label).derive(secret)


def derive(label: bytes, version: int = ROOT_VERSION, env: Mapping[str, str] | None = None) -> bytes:
    """The key for one use. Raises Unavailable without a usable root."""
    if label not in LABELS:
        raise ValueError("not a keyring label")
    return hkdf(root(version, env), label)


# ---------------------------------------------------------------------------
# Saved provider keys
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Binding:
    """What a saved key belongs to: its account, its provider, and the
    address (host and port) it was entered for."""

    account_id: str
    provider_id: str
    host: str
    port: int

    def __post_init__(self) -> None:
        if not (isinstance(self.account_id, str) and _RECORD_ID.fullmatch(self.account_id)):
            raise ValueError("not an account id")
        if not (isinstance(self.provider_id, str) and _RECORD_ID.fullmatch(self.provider_id)):
            raise ValueError("not a provider id")
        if not (isinstance(self.host, str) and _HOST.fullmatch(self.host)):
            raise ValueError("not a host")
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise ValueError("not a port")


@dataclass(frozen=True)
class Wrapped:
    """A saved key as it is stored: the wrap, the root version, and base64
    ciphertext and nonce."""

    wrap: str
    key_version: int
    ciphertext: str
    nonce: str


def _aad(binding: Binding, key_version: int) -> bytes:
    return canonical.canonical(
        [AAD_SCHEMA, binding.account_id, RECORD_TYPE, binding.provider_id, key_version, binding.host, binding.port]
    )


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(text: object) -> bytes:
    if not isinstance(text, str) or not text:
        raise ValueError("not base64")
    return base64.b64decode(text, validate=True)


def wrap(plaintext: str, binding: Binding) -> Wrapped:
    """Wrap a key for its account, provider, and address. Raises Unavailable
    without a usable root, and ValueError for a value that isn't a key."""
    if not isinstance(plaintext, str):
        raise ValueError("not a key")
    data = plaintext.encode("utf-8")
    if not data or len(data) > MAX_KEY_BYTES:
        raise ValueError("not a key")
    key = derive(CREDENTIAL_WRAP, ROOT_VERSION)
    nonce = secrets.token_bytes(NONCE_BYTES)
    sealed = AESGCM(key).encrypt(nonce, data, _aad(binding, ROOT_VERSION))
    return Wrapped(wrap=WRAP_AAD_V1, key_version=ROOT_VERSION, ciphertext=_b64(sealed), nonce=_b64(nonce))


def unwrap(wrapped: Wrapped, binding: Binding) -> str:
    """The key, when it opens for this account, provider, and address.
    Raises CredentialUnusable when it doesn't, and Unavailable without a
    usable root."""
    # Both wraps were made under root version 1, the only one there is.
    if isinstance(wrapped.key_version, bool) or wrapped.key_version != ROOT_VERSION:
        raise CredentialUnusable
    if wrapped.wrap == WRAP_AAD_V1:
        key = derive(CREDENTIAL_WRAP, wrapped.key_version)
        aad: bytes | None = _aad(binding, wrapped.key_version)
    elif wrapped.wrap == WRAP_LEGACY_V0:
        key = hashlib.sha256(root(wrapped.key_version)).digest()
        aad = None
    else:
        raise CredentialUnusable
    try:
        sealed = _unb64(wrapped.ciphertext)
        nonce = _unb64(wrapped.nonce)
        if len(nonce) != NONCE_BYTES:
            raise ValueError("not a nonce")
        opened = AESGCM(key).decrypt(nonce, sealed, aad)
        text = opened.decode("utf-8")
    except (InvalidTag, ValueError, binascii.Error, UnicodeDecodeError):
        raise CredentialUnusable from None
    if not text:
        raise CredentialUnusable
    return text


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Status:
    """What the runner can do with the root. ``reason`` is ``loaded``,
    ``unset``, ``development-placeholder`` or ``malformed``."""

    usable: bool
    reason: str
    short: bool = False


def status(env: Mapping[str, str] | None = None) -> Status:
    material, reason = _read(os.environ if env is None else env)
    if material is None:
        return Status(False, reason)
    return Status(True, reason, short=len(material) < SHORT_ROOT_BYTES)


def init(env: Mapping[str, str] | None = None) -> Status:
    """Check the root settings once, at startup, and log one line. Raises
    Malformed for a setting that is set and can't be read; the line never
    shows the secret."""
    env = os.environ if env is None else env
    dev_opt_in(env)
    current = status(env)
    if current.reason == "malformed":
        raise Malformed(f"{SECRET_ENV} isn't valid UTF-8 text")
    if current.reason == "unset":
        _log.warning("keyring: %s is unset, so saved AI provider keys and share links are unavailable", SECRET_ENV)
    elif current.reason == "development-placeholder":
        _log.warning(
            "keyring: %s is the development placeholder, which counts only with %s=true, so saved AI provider keys "
            "and share links are unavailable",
            SECRET_ENV,
            DEV_OPT_IN_ENV,
        )
    elif current.short:
        _log.warning(
            "keyring: %s loaded as root version %d; it is shorter than %d bytes, so generate a longer one with "
            "`openssl rand -hex 32` when you next set it",
            SECRET_ENV,
            ROOT_VERSION,
            SHORT_ROOT_BYTES,
        )
    else:
        _log.info("keyring: %s loaded as root version %d", SECRET_ENV, ROOT_VERSION)
    return current
