"""The share resolver's PocketBase session (ROUNDS-00B-L04).

A recipient opening a share link has no account, so the runner resolves
the link as ``share-resolver``, the one record of the ``share_resolvers``
auth collection (D16, as ``execution_service`` does), logged in with
``ROUNDS_SHARE_RESOLVER_PASSWORD``. Only the runner and PocketBase hold
that secret, and candidate processes never get it (``app.sandbox``'s
minimal environment). PocketBase refuses that record everywhere except the
one lookup route (``pb_hooks/share_secrets.js``).

``lookup`` sends the submitted bearer's digest and the throttle's keys
(``app.share_secrets``), never the bearer or a client address, and reads
one answer: throttled with a wait, or the capability's lookup fields, or
none. A transport error, a refused login, or an answer outside that shape
is ``Unavailable``, which the resolver answers as the uniform not-found.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.pb_auth import POCKETBASE_URL

VERSION = "share-lookup/v1"
COLLECTION = "share_resolvers"
USERNAME = "share-resolver"
LOGIN_PATH = f"/api/collections/{COLLECTION}/auth-with-password"
LOOKUP_PATH = "/api/rounds/share/lookup"
SECRET_ENV = "ROUNDS_SHARE_RESOLVER_PASSWORD"
# pb_hooks/share_secrets.js takes the same range; bcrypt reads at most 72 bytes.
SECRET_MIN_CHARS = 32
SECRET_MAX_CHARS = 72
TIMEOUT_S = 5

RECORD_ID = re.compile(r"[a-z0-9]{15}")
HEX64 = re.compile(r"[0-9a-f]{64}")
SCOPES = ("ip_minute", "pw_15m", "digest_day")
# What the lookup answers for a capability that resolves: #11's
# lookup_capability fields.
LOOKUP_FIELDS = frozenset(
    {"id", "status", "expires_at", "capability_version", "snapshot", "password_policy_ref", "markup"}
)


class Unavailable(Exception):
    """The lookup didn't answer in the contract's shape."""


class LoginRejected(Unavailable):
    """The resolver secret didn't log in."""


def usable_secret(secret: object) -> bool:
    """32 to 72 printable ASCII characters, no spaces, as PocketBase's
    resolver record takes."""
    return (
        isinstance(secret, str)
        and SECRET_MIN_CHARS <= len(secret) <= SECRET_MAX_CHARS
        and all(33 <= ord(ch) <= 126 for ch in secret)
    )


def secret_from_env() -> str | None:
    """The resolver secret, or None when it's unset or unusable."""
    secret = os.environ.get(SECRET_ENV, "")
    return secret if usable_secret(secret) else None


@dataclass(frozen=True)
class Lookup:
    throttled: bool
    # Whole seconds to wait, while throttled.
    retry_after: int
    # The capability's lookup fields, or None when nothing resolves.
    capability: dict[str, Any] | None


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _capability(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != LOOKUP_FIELDS:
        raise Unavailable
    if not (isinstance(raw["id"], str) and RECORD_ID.fullmatch(raw["id"])):
        raise Unavailable
    if not (isinstance(raw["snapshot"], str) and RECORD_ID.fullmatch(raw["snapshot"])):
        raise Unavailable
    if not (_int(raw["capability_version"]) and raw["capability_version"] >= 1):
        raise Unavailable
    for name in ("status", "expires_at", "password_policy_ref", "markup"):
        if not isinstance(raw[name], str):
            raise Unavailable
    return dict(raw)


def read_answer(status: int, body: Any) -> Lookup:
    """The lookup route's answer, or ``Unavailable``."""
    if status != 200 or not isinstance(body, dict) or body.get("v") != VERSION:
        raise Unavailable
    throttled = body.get("throttled")
    if throttled is True:
        wait = body.get("retry_after")
        if set(body) != {"v", "throttled", "retry_after"} or not _int(wait) or wait < 1:
            raise Unavailable
        return Lookup(True, wait, None)
    if throttled is False and set(body) == {"v", "throttled", "capability"}:
        return Lookup(False, 0, _capability(body["capability"]))
    raise Unavailable


def lookup_request(bearer_digest: str, throttle: list[tuple[str, str]]) -> dict[str, Any]:
    """The lookup's body: the digest and the throttle's keys, nothing else."""
    if not isinstance(bearer_digest, str) or HEX64.fullmatch(bearer_digest) is None:
        raise ValueError("not a bearer digest")
    entries = []
    for scope, key in throttle:
        if scope not in SCOPES or not isinstance(key, str) or HEX64.fullmatch(key) is None:
            raise ValueError("not a throttle key")
        entries.append({"scope": scope, "key": key})
    return {"digest": bearer_digest, "throttle": entries}


class ResolverClient:
    """The resolver's session with PocketBase, as ``share-resolver``."""

    def __init__(self, secret: str, base_url: str | None = None, timeout: float = TIMEOUT_S,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._secret = secret
        self._http = httpx.AsyncClient(base_url=base_url or POCKETBASE_URL, timeout=timeout, transport=transport)
        self._auth: str | None = None

    async def aclose(self) -> None:
        await self._http.aclose()

    @property
    def logged_in(self) -> bool:
        return self._auth is not None

    async def login(self) -> None:
        """Logs in as share-resolver. ``LoginRejected`` when the secret
        doesn't match the record's password."""
        try:
            resp = await self._http.post(LOGIN_PATH, json={"identity": USERNAME, "password": self._secret})
        except httpx.HTTPError:
            raise Unavailable from None
        if resp.status_code == 400:
            self._auth = None
            raise LoginRejected
        try:
            body = resp.json()
        except ValueError:
            raise Unavailable from None
        token = body.get("token") if isinstance(body, dict) else None
        if resp.status_code != 200 or not isinstance(token, str) or not token:
            raise Unavailable
        self._auth = token

    async def lookup(self, bearer_digest: str, throttle: list[tuple[str, str]]) -> Lookup:
        """One throttled lookup. An expired or revoked session logs in
        again, once."""
        payload = lookup_request(bearer_digest, throttle)
        for tries in range(2):
            if self._auth is None:
                await self.login()
            try:
                resp = await self._http.post(LOOKUP_PATH, json=payload,
                                             headers={"Authorization": f"Bearer {self._auth}"})
            except httpx.HTTPError:
                raise Unavailable from None
            if resp.status_code in (401, 403) and tries == 0:
                self._auth = None
                continue
            break
        try:
            body = resp.json()
        except ValueError:
            raise Unavailable from None
        return read_answer(resp.status_code, body)
