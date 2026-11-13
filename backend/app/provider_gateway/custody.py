"""Saved AI provider keys and model lists (ROUNDS-14-L02 stage A).

The runner's client for PocketBase's AI hook routes
(pocketbase/pb_hooks/ai_custody.js), which hold the caller's bearer and
the runner key, ROUNDS_ADMISSION_SECRET, and are the only writers of
ai_credentials, ai_provider_models, and ai_providers' creates and
updates. A route's own text never reaches a caller: each answer maps to
a typed error.

The keyring wraps a key here, before PocketBase sees it, for its account,
its provider, and the address it was entered for; so a create mints the
provider's id first. ``key_for`` is the one place that opens a saved key,
after checking, in order, that the model is on the provider's list
(model_unregistered), that a usable key is saved (credential_missing),
that the provider's address is the one the key was entered for
(credential_required), and that the keyring has its root
(keyring_unavailable). A key saved before this release opens once as it
was stored, and is then rewrapped for its address; a rewrap that loses a
race to a change of the key is dropped.
"""
from __future__ import annotations

import hashlib
import logging
import re
import secrets
import string
from dataclasses import dataclass
from typing import Any

import anyio
import httpx

from app import admission_state, destinations
from app.errors import TypedError
from app.pb_auth import POCKETBASE_URL
from app.provider_gateway import keyring

_log = logging.getLogger(__name__)

HOOK_PREFIX = "/api/rounds/ai"
VERSION = "ai-custody/v1"
TIMEOUT_S = 10
KINDS = ("anthropic", "openai", "openai-compatible", "anthropic-compatible")
# A first-party kind calls its provider's own address and keeps no base URL.
FIRST_PARTY = {"anthropic": ("api.anthropic.com", 443), "openai": ("api.openai.com", 443)}
_ID_ALPHABET = string.ascii_lowercase + string.digits
_ERROR = re.compile(r"[a-z_]{1,40}")

# A hook route's refusal -> the typed error the caller gets.
_REFUSALS = {
    (400, "invalid_request"): "invalid_request",
    (400, "credential_required"): "credential_required",
    (401, None): "unauthenticated",
    (403, "demo_not_permitted"): "demo_not_permitted",
    (404, "not_found"): "provider_unavailable",
}


class Conflict(Exception):
    """A create whose id was taken, or a rewrap that lost a race."""


@dataclass(frozen=True)
class Opened:
    """A saved key, opened for one call, and where the call goes."""

    provider_id: str
    kind: str
    base_url: str
    api_key: str


def new_provider_id() -> str:
    """A PocketBase record id: 15 lowercase letters and digits."""
    return "".join(secrets.choice(_ID_ALPHABET) for _ in range(15))


def is_first_party(kind: str) -> bool:
    return kind in FIRST_PARTY


def endpoint(kind: str, base_url: str) -> tuple[str, int] | None:
    """The address a provider's calls go to, as host and port: its base
    URL's, or a first-party kind's own. None for a compatible kind with no
    base URL. Raises destination_denied for a base URL that isn't one."""
    url = (base_url or "").strip()
    if url:
        host, port = destinations._host_and_port(url)
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError:
            raise TypedError("destination_denied") from None
        return host, port
    return FIRST_PARTY.get(kind)


def _binding(user: dict, provider_id: str, at: tuple[str, int]) -> keyring.Binding:
    try:
        return keyring.Binding(user["id"], provider_id, at[0], at[1])
    except ValueError:
        raise TypedError("destination_denied") from None


def _wrap(user: dict, provider_id: str, key: str, at: tuple[str, int]) -> dict[str, Any]:
    try:
        wrapped = keyring.wrap(key, _binding(user, provider_id, at))
    except keyring.Unavailable:
        _log.warning("custody: %s isn't usable here, so no provider key can be saved", keyring.SECRET_ENV)
        raise TypedError("keyring_unavailable") from None
    except ValueError:
        raise TypedError("invalid_request", "The API key isn't one a provider issues.") from None
    return {
        "wrap": wrapped.wrap,
        "key_version": wrapped.key_version,
        "ciphertext": wrapped.ciphertext,
        "nonce": wrapped.nonce,
        "host": at[0],
        "port": at[1],
    }


async def _call(user: dict, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """One hook route, with the caller's bearer and the runner key."""
    try:
        key = admission_state.runner_key()
    except admission_state.Unconfigured:
        _log.warning("custody: the runner has no usable %s", admission_state.RUNNER_KEY_ENV)
        raise TypedError("providers_unavailable") from None
    headers = {"Authorization": f"Bearer {user['token']}", admission_state.RUNNER_KEY_HEADER: key}
    try:
        with anyio.fail_after(TIMEOUT_S):
            async with httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=TIMEOUT_S) as client:
                resp = await client.post(HOOK_PREFIX + path, json=payload, headers=headers)
    except (httpx.HTTPError, TimeoutError) as err:
        _log.warning("custody: no answer from PocketBase (%s)", type(err).__name__)
        raise TypedError("providers_unavailable") from None
    try:
        body = resp.json()
    except ValueError:
        body = None
    status = resp.status_code
    error = body.get("error") if isinstance(body, dict) else None
    if status == 200 and isinstance(body, dict) and body.get("v") == VERSION:
        return body
    if status == 409 and error == "conflict":
        raise Conflict
    code = _REFUSALS.get((status, error)) or _REFUSALS.get((status, None))
    if code:
        raise TypedError(code)
    named = error if isinstance(error, str) and _ERROR.fullmatch(error) else "none"
    _log.warning("custody: PocketBase answered %s (%s)", status, named)
    raise TypedError("providers_unavailable")


def _view(provider: dict[str, Any]) -> dict[str, Any]:
    """A provider as the routes show it: never its key."""
    return {
        "id": provider.get("id") or "",
        "kind": provider.get("kind") or "",
        "label": provider.get("label") or "",
        "base_url": provider.get("base_url") or "",
        "has_key": bool(provider.get("has_key")),
        "models": sorted(m["model"] for m in provider.get("models") or [] if isinstance(m, dict) and m.get("model")),
        "models_cached_at": provider.get("models_cached_at") or "",
    }


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


async def list_providers(user: dict) -> list[dict[str, Any]]:
    """The caller's providers, oldest first, at most 50."""
    body = await _call(user, "/providers/list", {})
    return [_view(p) for p in body.get("providers") or [] if isinstance(p, dict)]


async def load(user: dict, provider_id: str) -> dict[str, Any]:
    """One of the caller's providers. provider_unavailable for one that is
    missing or another account's, with one answer for both."""
    body = await _call(user, "/providers/list", {"provider": provider_id})
    for provider in body.get("providers") or []:
        if isinstance(provider, dict) and provider.get("id") == provider_id:
            return _view(provider)
    raise TypedError("provider_unavailable")


def _fields(kind: str, label: str, base_url: str) -> tuple[str, str, str]:
    if kind not in KINDS:
        raise TypedError("invalid_request", "That provider kind isn't one Rounds knows.")
    # The settings screen shows a base URL only for a compatible kind, so a
    # first-party kind's is dropped.
    url = "" if is_first_party(kind) else (base_url or "").strip()
    return kind, (label or "").strip(), url


async def create(user: dict, kind: str, label: str, base_url: str, key: str | None) -> dict[str, Any]:
    """A provider for the caller, with its key when one comes."""
    kind, label, url = _fields(kind, label, base_url)
    await destinations.check(url)
    for _attempt in range(2):
        provider_id = new_provider_id()
        payload: dict[str, Any] = {"id": provider_id, "kind": kind, "label": label, "base_url": url}
        if key is not None and key.strip():
            at = endpoint(kind, url)
            if at is None:
                raise TypedError("invalid_request", "A compatible provider needs its base URL before its key.")
            payload["credential"] = _wrap(user, provider_id, key.strip(), at)
        try:
            body = await _call(user, "/providers/create", payload)
        except Conflict:
            continue
        return _view(body["provider"])
    raise TypedError("providers_unavailable")


async def update(user: dict, provider_id: str, kind: str, label: str, base_url: str, key: str | None) -> dict[str, Any]:
    """Change a provider. ``key`` None clears the saved key, blank keeps it,
    and anything else replaces it. A saved key works only with the address
    it was entered for, so changing the address asks for the key again
    (credential_required) unless one comes with the change."""
    kind, label, url = _fields(kind, label, base_url)
    await destinations.check(url)
    at = endpoint(kind, url)
    if key is None:
        given: Any = "clear"
    elif key.strip():
        if at is None:
            raise TypedError("invalid_request", "A compatible provider needs its base URL before its key.")
        given = _wrap(user, provider_id, key.strip(), at)
    else:
        given = "keep"
    payload = {
        "provider": provider_id,
        "kind": kind,
        "label": label,
        "base_url": url,
        "endpoint": None if at is None else {"host": at[0], "port": at[1]},
        "key": given,
    }
    try:
        body = await _call(user, "/providers/update", payload)
    except Conflict:
        raise TypedError("providers_unavailable") from None
    return _view(body["provider"])


async def put_models(user: dict, provider_id: str, models: list[str], verification: str, replace: bool) -> dict[str, Any]:
    """Replace a provider's own model list (``registry``, replace=True), or
    add the models its owner named (``user-declared``)."""
    body = await _call(
        user,
        "/providers/models",
        {"provider": provider_id, "models": list(models), "verification": verification, "replace": replace},
    )
    return _view(body["provider"])


# ---------------------------------------------------------------------------
# Opening a saved key
# ---------------------------------------------------------------------------


def _pair_digest(credential: dict[str, Any]) -> str:
    return hashlib.sha256(f"{credential['ciphertext']}:{credential['nonce']}".encode("utf-8")).hexdigest()


async def key_for(user: dict, provider_id: str, model: str | None) -> Opened:
    """The caller's saved key for one call to ``model`` on this provider.
    ``model`` None is the model list's own call, which names no model."""
    body = await _call(user, "/credentials/read", {"provider": provider_id})
    provider = body.get("provider") or {}
    credential = body.get("credential")
    names = {m.get("model") for m in body.get("models") or [] if isinstance(m, dict)}
    if model is not None and model not in names:
        raise TypedError("model_unregistered")
    if not isinstance(credential, dict) or credential.get("status") != "active":
        raise TypedError("credential_missing")
    kind = provider.get("kind") or ""
    base_url = provider.get("base_url") or ""
    at = endpoint(kind, base_url)
    if at is None:
        raise TypedError("credential_required")
    if credential.get("wrap") == keyring.WRAP_AAD_V1 and (
        credential.get("registered_host"), credential.get("registered_port")
    ) != at:
        raise TypedError("credential_required")
    if not keyring.status().usable:
        raise TypedError("keyring_unavailable")
    binding = _binding(user, provider_id, at)
    stored = keyring.Wrapped(
        wrap=credential.get("wrap") or "",
        key_version=credential.get("key_version"),
        ciphertext=credential.get("ciphertext") or "",
        nonce=credential.get("nonce") or "",
    )
    try:
        api_key = keyring.unwrap(stored, binding)
    except keyring.Unavailable:
        raise TypedError("keyring_unavailable") from None
    except keyring.CredentialUnusable:
        _log.warning("custody: a saved provider key didn't open (credential_unusable)")
        raise TypedError("credential_missing") from None
    if stored.wrap == keyring.WRAP_LEGACY_V0:
        await _rewrap(user, provider_id, credential, api_key, at)
    return Opened(provider_id=provider_id, kind=kind, base_url=base_url, api_key=api_key)


async def _rewrap(user: dict, provider_id: str, credential: dict[str, Any], api_key: str, at: tuple[str, int]) -> None:
    """Rewrap a key saved before this release for its address. Its call goes
    ahead whatever happens here, and a failed rewrap is tried again on the
    next use."""
    try:
        wrapped = _wrap(user, provider_id, api_key, at)
        await _call(
            user,
            "/credentials/convert",
            {"provider": provider_id, "from": _pair_digest(credential), "credential": wrapped},
        )
    except Conflict:
        _log.info("custody: a saved provider key changed before its rewrap; the change stays")
    except TypedError as err:
        _log.warning("custody: a saved provider key wasn't rewrapped (%s)", err.code)
