"""Share link passwords (ROUNDS-00B-L04): the ``pw1`` verifier.

``pw1`` is Argon2id with 19456 KiB of memory, 2 passes, 1 lane, a 16-byte
salt, and a 32-byte hash, stored as ``pw1`` followed by the PHC string. A
password is 8 to 128 characters and is set only when a share is made, so a
later profile applies to new shares and an existing share keeps its own. A
verifier under any other profile never resolves.

Hashing and verifying run in a worker thread, at most two at a time in each
process, since every one holds its 19 MiB until it ends. A submitted
password costs one verify, never more or fewer: the share's verifier when it
has a current one, and otherwise a dummy ``pw1`` verifier the process makes
once. So an unknown link, an unprotected one, and one under another profile
cost what a wrong password costs. No password, no verify.
"""
from __future__ import annotations

import asyncio
import re
import secrets
import threading
from typing import Any, Callable

import anyio
import argon2
from argon2.exceptions import InvalidHashError, VerificationError

PROFILE = "pw1"
TIME_COST = 2
MEMORY_COST_KIB = 19456
PARALLELISM = 1
SALT_BYTES = 16
HASH_BYTES = 32
MIN_CHARS = 8
MAX_CHARS = 128
# Verifies and hashes in flight at once in one process.
CONCURRENCY = 2

_PHC_PREFIX = f"$argon2id$v=19$m={MEMORY_COST_KIB},t={TIME_COST},p={PARALLELISM}$"
# pw1, then the PHC string: unpadded base64 of the 16-byte salt (22
# characters) and of the 32-byte hash (43).
VERIFIER = re.compile(re.escape(PROFILE + _PHC_PREFIX) + r"[A-Za-z0-9+/]{22}\$[A-Za-z0-9+/]{43}")

_hasher = argon2.PasswordHasher(
    time_cost=TIME_COST,
    memory_cost=MEMORY_COST_KIB,
    parallelism=PARALLELISM,
    hash_len=HASH_BYTES,
    salt_len=SALT_BYTES,
    type=argon2.Type.ID,
)


def valid_password(value: object) -> bool:
    """8 to 128 characters that encode as UTF-8."""
    if not isinstance(value, str) or not MIN_CHARS <= len(value) <= MAX_CHARS:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def is_current(verifier: object) -> bool:
    """A verifier under the ``pw1`` profile, exactly."""
    return isinstance(verifier, str) and VERIFIER.fullmatch(verifier) is not None


# ---------------------------------------------------------------------------
# The slots
# ---------------------------------------------------------------------------

_slots: asyncio.Semaphore | None = None
_slots_loop: asyncio.AbstractEventLoop | None = None


def _semaphore() -> asyncio.Semaphore:
    """The process's slots, made for the running loop (a test may run
    several loops in turn; the runner runs one)."""
    global _slots, _slots_loop
    loop = asyncio.get_running_loop()
    if _slots is None or _slots_loop is not loop:
        _slots, _slots_loop = asyncio.Semaphore(CONCURRENCY), loop
    return _slots


async def _in_slot(fn: Callable[..., Any], *args: Any) -> Any:
    async with _semaphore():
        return await anyio.to_thread.run_sync(fn, *args)


# ---------------------------------------------------------------------------
# The dummy verifier
# ---------------------------------------------------------------------------

_dummy: str | None = None
_dummy_lock = threading.Lock()


def _dummy_verifier() -> str:
    """A ``pw1`` verifier of a random password nobody holds, made once."""
    global _dummy
    with _dummy_lock:
        if _dummy is None:
            _dummy = PROFILE + _hasher.hash(secrets.token_urlsafe(32))
        return _dummy


async def warm() -> None:
    """Makes the dummy verifier now, so no resolve pays for it."""
    await _in_slot(_dummy_verifier)


# ---------------------------------------------------------------------------
# Hash and verify
# ---------------------------------------------------------------------------


def _hash(password: str) -> str:
    return PROFILE + _hasher.hash(password)


async def hash_password(password: str) -> str:
    """The ``pw1`` verifier for a new share's password. ValueError for a
    password outside the bounds, before any work."""
    if not valid_password(password):
        raise ValueError("password outside the bounds")
    return await _in_slot(_hash, password)


def _verify(password: object, verifier: object) -> bool:
    real = is_current(verifier)
    target = verifier if real else _dummy_verifier()
    # Bytes as they came: a value that isn't UTF-8 can't match a verifier
    # made from a valid password, and still costs one verify.
    secret = password.encode("utf-8", errors="surrogatepass") if isinstance(password, str) else b""
    try:
        _hasher.verify(target[len(PROFILE):], secret)  # type: ignore[index]
    except (VerificationError, InvalidHashError):
        return False
    return real


async def verify(password: object, verifier: object) -> bool:
    """One verify of ``password``. True only when ``verifier`` is a current
    ``pw1`` verifier and the password matches it."""
    return await _in_slot(_verify, password, verifier)
