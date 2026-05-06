"""AES-GCM encryption for stored AI provider keys.

The master secret comes from the ``AI_KEY_SECRET`` env var. We derive
a 32-byte key from it via SHA-256 so users can paste anything (a hex
string, a passphrase, etc.) and we still get a valid AES-256 key.

If the env var is missing we fall back to a deterministic dev secret —
that's fine for local development but emits a warning so it's obvious
the deployment forgot to set the variable.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_logger = logging.getLogger(__name__)

_DEV_SECRET = "rounds-dev-key-DO-NOT-USE-IN-PROD"


def _master_key() -> bytes:
    raw = os.environ.get("AI_KEY_SECRET")
    if not raw:
        if not getattr(_master_key, "_warned", False):
            _logger.warning(
                "AI_KEY_SECRET not set — using a dev-only fallback. Stored AI "
                "keys will NOT be portable across environments."
            )
            _master_key._warned = True  # type: ignore[attr-defined]
        raw = _DEV_SECRET
    return hashlib.sha256(raw.encode("utf-8")).digest()


@dataclass
class Encrypted:
    ciphertext_b64: str
    iv_b64: str


def encrypt(plaintext: str) -> Encrypted:
    if not plaintext:
        return Encrypted(ciphertext_b64="", iv_b64="")
    key = _master_key()
    aes = AESGCM(key)
    iv = secrets.token_bytes(12)
    ct = aes.encrypt(iv, plaintext.encode("utf-8"), associated_data=None)
    return Encrypted(
        ciphertext_b64=base64.b64encode(ct).decode("ascii"),
        iv_b64=base64.b64encode(iv).decode("ascii"),
    )


def decrypt(ciphertext_b64: str, iv_b64: str) -> str:
    if not ciphertext_b64 or not iv_b64:
        return ""
    key = _master_key()
    aes = AESGCM(key)
    ct = base64.b64decode(ciphertext_b64)
    iv = base64.b64decode(iv_b64)
    return aes.decrypt(iv, ct, associated_data=None).decode("utf-8")
