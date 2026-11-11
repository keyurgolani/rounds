"""The share resolver's lookup (ROUNDS-00B-L04).

#11's resolver (app/share_capabilities.py) decides the public share switch,
the gate, and the request's shape, then calls ``lookup`` once for each
well-formed bearer. In order:

  1. A bearer under another key id resolves nothing.
  2. Its digest, and the throttle's keys from the client's address
     pseudonym and that digest (app/share_secrets.py).
  3. One call to PocketBase's lookup route as share-resolver
     (app/share_resolver_client.py). The route counts first and reads the
     capability only when no counter is over its limit, so a 429 never
     depends on whether the bearer is live.
  4. The password step. Each submitted password gets exactly one verify
     (app/share_password.py): against the capability's verifier when it
     has a current one, and against the dummy otherwise, so an unknown
     bearer, an unprotected capability, and a wrong password cost the same.
     No password, no verify.

It answers the capability's markup or None, or raises Throttled, Refused
(``password_required`` or ``password_wrong``), or LookupUnavailable, which
#11's resolver answers as degraded. Nothing is cached: every call asks
PocketBase again, so a rotate or a revoke holds from the next request on.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import datetime, timedelta, timezone

from app import share_password, share_resolver_client, share_secrets
from app.share_capabilities import Found, LookupUnavailable, Refused, Throttled

# PocketBase 0.22's datetime text, "2006-01-02 15:04:05.000Z", or the same
# with a T.
_PB_DATETIME = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})[ T]([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,9}))?Z"
)

_client: share_resolver_client.ResolverClient | None = None
_client_for: tuple[bytes, int] | None = None


def resolver() -> share_resolver_client.ResolverClient:
    """The process's session as share-resolver, for the running loop and
    the current secret. Without a usable secret, LookupUnavailable."""
    global _client, _client_for
    secret = share_resolver_client.secret_from_env()
    if secret is None:
        raise LookupUnavailable("no usable resolver secret")
    key = (hashlib.sha256(secret.encode("ascii")).digest(), id(asyncio.get_running_loop()))
    if _client is None or _client_for != key:
        _client, _client_for = share_resolver_client.ResolverClient(secret), key
    return _client


def _expired(text: str, now: datetime) -> bool:
    match = _PB_DATETIME.fullmatch(text)
    if match is None:
        return True
    year, month, day, hour, minute, second, fraction = match.groups()
    try:
        at = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), tzinfo=timezone.utc)
    except ValueError:
        return True
    at += timedelta(microseconds=int((fraction or "0").ljust(6, "0")[:6]))
    return at <= now


def _live(capability: dict | None) -> bool:
    """An active capability that hasn't expired. #11's lookup answers only
    those; this checks again."""
    if capability is None or capability.get("status") != "active":
        return False
    return not _expired(capability.get("expires_at") or "", datetime.now(timezone.utc))


async def lookup(token: str, password: str | None, address: str | None) -> Found | None:
    """One resolve's lookup and password step."""
    if not share_secrets.current(token):
        if password is not None:
            await share_password.verify(password, None)
        return None
    try:
        bearer = share_secrets.digest(token)
        keys = share_secrets.throttle_keys(share_secrets.ip_pseudonym(address), bearer, password is not None)
    except share_secrets.Unavailable:
        raise LookupUnavailable("no digest key") from None
    try:
        answer = await resolver().lookup(bearer, keys)
    except share_resolver_client.Unavailable:
        raise LookupUnavailable("the lookup didn't answer") from None
    if answer.throttled:
        raise Throttled(answer.retry_after)

    capability = answer.capability if _live(answer.capability) else None
    verifier = capability["password_policy_ref"] if capability is not None else ""
    if password is not None:
        matched = await share_password.verify(password, verifier or None)
        if capability is None:
            return None
        if verifier and not matched:
            raise Refused("password_wrong")
    elif capability is None:
        return None
    elif verifier:
        raise Refused("password_required")
    return Found(capability["id"], capability["markup"])
