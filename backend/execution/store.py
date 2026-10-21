"""The runner's client of the execution job store (ROUNDS-00A-L03).

The runner keeps no job state. ``pocketbase/pb_hooks/execution.js`` keeps
it in ``execution_jobs``, ``execution_attempts``, and
``execution_envelopes``, and this module calls its service routes under
``/api/rounds/execution/`` as the ``execution_service`` record
``execution-worker``, logged in with ``ROUNDS_EXECUTION_SECRET``. Only the
runner and PocketBase hold that secret, and candidate processes never get
it (app/sandbox.py's minimal environment).

1. ``claim`` reaps first, then leases the oldest queued job of an account
   with fewer than 2 active, under the hash of a fencing token this
   runner made and keeps.
2. ``heartbeat`` keeps the lease for 30 s on PocketBase's clock; the first
   one with a budget marks the candidate tree started. It answers whether
   a cancel was asked for.
3. ``complete`` writes the envelope and both terminal states together.
4. ``reap`` ends what lost its lease or ran past its budget.

A write for an attempt whose token lost its lease is ``Superseded``: the
store counted it as rejected and applied nothing. A transport error or an
answer outside the contract is ``Unavailable``; a 4xx the store answered
in the contract's shape is ``Refused``; the store gate off is
``StoreOff``.

TODO(ROUNDS-00A-L03): PR 2's job-backed routes add the caller's enqueue
and cancel, with the caller's bearer and the runner key.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import string
from dataclasses import dataclass
from typing import Any

import httpx

from app.pb_auth import POCKETBASE_URL

VERSION = "execution/v1"
BASE_PATH = "/api/rounds/execution"
LOGIN_PATH = "/api/collections/execution_service/auth-with-password"
WORKER_USERNAME = "execution-worker"
SECRET_ENV = "ROUNDS_EXECUTION_SECRET"
# pb_hooks/execution.js takes the same range; bcrypt reads at most 72 bytes.
SECRET_MIN_CHARS = 32
SECRET_MAX_CHARS = 72
TIMEOUT_S = 5
RECORD_ID = re.compile(r"[a-z0-9]{15}")
_TOKEN_ALPHABET = string.ascii_letters + string.digits
_TOKEN_CHARS = 43


class Unavailable(Exception):
    """The store didn't answer in the contract's shape."""


class Refused(Unavailable):
    """The store answered and applied nothing."""


class StoreOff(Refused):
    """ROUNDS_GATE_EXECUTION_STORE is off on PocketBase."""


class Superseded(Refused):
    """The attempt's token no longer holds its lease; the write was
    counted as rejected."""


class LoginRejected(Refused):
    """The worker secret didn't log in."""


def usable_secret(secret: str | None) -> bool:
    """32 to 72 printable ASCII characters, no spaces, as PocketBase's
    worker record takes."""
    return (
        isinstance(secret, str)
        and SECRET_MIN_CHARS <= len(secret) <= SECRET_MAX_CHARS
        and all(33 <= ord(ch) <= 126 for ch in secret)
    )


def secret_from_env() -> str | None:
    """The worker secret, or None when it's unset or unusable."""
    secret = os.environ.get(SECRET_ENV, "")
    return secret if usable_secret(secret) else None


def new_token() -> str:
    """A fencing token: 43 letters and digits, about 256 bits."""
    return "".join(secrets.choice(_TOKEN_ALPHABET) for _ in range(_TOKEN_CHARS))


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class Job:
    id: str
    account: str
    kind: str
    purpose: str
    definition: dict[str, Any]
    fingerprint: str
    source_checksum: str
    input_digest: str
    input: dict[str, Any]
    queued_at: int


@dataclass(frozen=True)
class Attempt:
    id: str
    attempt_number: int
    lease_expires_at: int


@dataclass(frozen=True)
class Claim:
    job: Job
    attempt: Attempt
    # The fencing token, which only this runner holds.
    token: str
    reaped: dict[str, int]


@dataclass(frozen=True)
class Beat:
    lease_expires_at: int
    cancel_requested: bool


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _record_id(value: Any) -> bool:
    return isinstance(value, str) and RECORD_ID.fullmatch(value) is not None


def _counts(body: Any) -> dict[str, int]:
    out = {}
    for key in ("requeued", "worker_lost", "over_budget"):
        value = body.get(key) if isinstance(body, dict) else None
        if not _int(value) or value < 0:
            raise Unavailable
        out[key] = value
    return out


def _job(raw: Any) -> Job:
    if not isinstance(raw, dict) or not _record_id(raw.get("id")) or not _record_id(raw.get("account")):
        raise Unavailable
    try:
        job = Job(
            id=raw["id"], account=raw["account"], kind=raw["kind"], purpose=raw["purpose"],
            definition=raw["definition"], fingerprint=raw["fingerprint"], source_checksum=raw["source_checksum"],
            input_digest=raw["input_digest"], input=raw["input"], queued_at=raw["queued_at"],
        )
    except KeyError:
        raise Unavailable from None
    if not isinstance(job.kind, str) or not isinstance(job.definition, dict) or not isinstance(job.input, dict):
        raise Unavailable
    if not _int(job.queued_at):
        raise Unavailable
    return job


class ServiceClient:
    """The worker's session with the store, as ``execution-worker``."""

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
        """Logs in as execution-worker. ``LoginRejected`` when the secret
        doesn't match the record's password."""
        try:
            resp = await self._http.post(LOGIN_PATH, json={"identity": WORKER_USERNAME, "password": self._secret})
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

    async def _post(self, action: str, payload: dict[str, Any]) -> tuple[int, Any]:
        for tries in range(2):
            if self._auth is None:
                await self.login()
            try:
                resp = await self._http.post(f"{BASE_PATH}/{action}", json=payload,
                                             headers={"Authorization": f"Bearer {self._auth}"})
            except httpx.HTTPError:
                raise Unavailable from None
            # An expired or revoked token logs in again, once.
            if resp.status_code in (401, 403) and tries == 0:
                self._auth = None
                continue
            break
        try:
            body = resp.json()
        except ValueError:
            body = None
        if resp.status_code == 503 and isinstance(body, dict) and body.get("error") == "store_off":
            raise StoreOff
        if resp.status_code in (401, 403):
            raise Refused
        return resp.status_code, body

    @staticmethod
    def _ours(body: Any) -> bool:
        return isinstance(body, dict) and body.get("v") == VERSION

    async def claim(self, worker: str) -> Claim | None:
        """The next job, leased under a new token, or None when nothing
        is queued for an account with room."""
        token = new_token()
        status, body = await self._post("claim", {"worker": worker, "token_hash": token_hash(token)})
        if status != 200 or not self._ours(body):
            raise Refused if 400 <= status < 500 and self._ours(body) else Unavailable
        reaped = _counts(body.get("reaped"))
        if body.get("job") is None:
            return None
        raw = body.get("attempt")
        if not isinstance(raw, dict) or not _record_id(raw.get("id")) or not _int(raw.get("attempt_number")):
            raise Unavailable
        if not _int(raw.get("lease_expires_at")):
            raise Unavailable
        return Claim(_job(body["job"]), Attempt(raw["id"], raw["attempt_number"], raw["lease_expires_at"]),
                     token, reaped)

    async def heartbeat(self, attempt_id: str, token: str, budget_s: int | None = None) -> Beat:
        """Keeps the lease. With ``budget_s``, marks the candidate tree
        started with that wall budget."""
        payload: dict[str, Any] = {"attempt_id": attempt_id, "token": token}
        if budget_s is not None:
            payload.update(started=True, budget_s=budget_s)
        status, body = await self._post("heartbeat", payload)
        if not self._ours(body):
            raise Unavailable
        if status == 200:
            expires, cancel = body.get("lease_expires_at"), body.get("cancel_requested")
            if not _int(expires) or not isinstance(cancel, bool):
                raise Unavailable
            return Beat(expires, cancel)
        if status in (404, 409) and body.get("error") in ("superseded", "not_found"):
            raise Superseded
        if 400 <= status < 500:
            raise Refused
        raise Unavailable

    async def complete(self, attempt_id: str, token: str, result: dict[str, Any]) -> str:
        """Writes the envelope; answers its id."""
        status, body = await self._post("complete", {"attempt_id": attempt_id, "token": token, "result": result})
        if not self._ours(body):
            raise Unavailable
        if status == 200 and _record_id(body.get("envelope_id")):
            return body["envelope_id"]
        if status in (404, 409) and body.get("error") in ("superseded", "not_found"):
            raise Superseded
        if 400 <= status < 500:
            raise Refused
        raise Unavailable

    async def reap(self) -> dict[str, int]:
        status, body = await self._post("reap", {})
        if status != 200 or not self._ours(body):
            raise Unavailable
        return _counts(body)
