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

``Caller`` (PR 2) is a job-backed route's session for one account: it
calls ``enqueue``, ``cancel``, and ``status`` with the caller's bearer,
which names the account, and the runner key (``ROUNDS_ADMISSION_SECRET``),
as admission's routes take them. Another account's job is the same
not-found as an unknown one.
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

from app import admission_state
from app.pb_auth import POCKETBASE_URL
from execution import kinds

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


@dataclass(frozen=True)
class Completed:
    envelope_id: str
    # How the store ended the job: what the runner reported, except where
    # the store couldn't keep that result (PR 3's graded row).
    state: str | None
    outcome_class: str | None


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

    async def complete(self, attempt_id: str, token: str, result: dict[str, Any],
                       graded: dict[str, Any] | None = None) -> "Completed":
        """Writes the envelope, and for an authoritative grading result its
        graded row (``graded``, PR 3), in one transaction; answers the
        envelope's id and how the store ended the job."""
        payload: dict[str, Any] = {"attempt_id": attempt_id, "token": token, "result": result}
        if graded is not None:
            payload["graded"] = graded
        status, body = await self._post("complete", payload)
        if not self._ours(body):
            raise Unavailable
        if status == 200 and _record_id(body.get("envelope_id")):
            job = body.get("job")
            state = job.get("state") if isinstance(job, dict) else None
            outcome_class = job.get("outcome_class") if isinstance(job, dict) else None
            return Completed(body["envelope_id"], state if state in kinds.STATES else None,
                             outcome_class if outcome_class in kinds.OUTCOME_CLASSES else None)
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


# ---------------------------------------------------------------------------
# The caller's routes (PR 2)
# ---------------------------------------------------------------------------


class Mismatch(Refused):
    """The key was admitted for another request, or enqueued another job."""


class NotAdmitted(Refused):
    """No admitted command in flight under the key."""


@dataclass(frozen=True)
class JobView:
    """A job as its account sees it."""

    id: str
    kind: str
    state: str
    outcome_class: str | None
    attempts: int
    attempts_started: int
    cancel_requested: bool
    cleanup: str | None
    queued_at: int
    finished_at: int | None


@dataclass(frozen=True)
class JobStatus:
    job: JobView
    # Whether a same-key retry would run the job again.
    retryable: bool
    # The user view of the envelope it ended with, when it has one.
    envelope: dict[str, Any] | None


def _view(raw: Any) -> JobView:
    if not isinstance(raw, dict) or not _record_id(raw.get("id")):
        raise Unavailable
    kind, state = raw.get("kind"), raw.get("state")
    outcome_class, cleanup = raw.get("outcome_class"), raw.get("cleanup")
    if kind not in kinds.KINDS or state not in kinds.STATES:
        raise Unavailable
    if outcome_class is not None and outcome_class not in kinds.OUTCOME_CLASSES:
        raise Unavailable
    if cleanup is not None and cleanup not in kinds.CLEANUP:
        raise Unavailable
    counts = (raw.get("attempts"), raw.get("attempts_started"), raw.get("queued_at"))
    if not all(_int(v) and v >= 0 for v in counts) or not isinstance(raw.get("cancel_requested"), bool):
        raise Unavailable
    finished = raw.get("finished_at")
    if finished is not None and not (_int(finished) and finished >= 0):
        raise Unavailable
    return JobView(raw["id"], kind, state, outcome_class, raw["attempts"], raw["attempts_started"],
                   raw["cancel_requested"], cleanup, raw["queued_at"], finished)


class Caller:
    """One account's calls to the store's caller routes: the caller's
    bearer and the runner key, over one connection for the whole request
    (a long-poll asks many times)."""

    def __init__(self, token: str, base_url: str | None = None, timeout: float = TIMEOUT_S,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._token = token
        self._http = httpx.AsyncClient(base_url=base_url or POCKETBASE_URL, timeout=timeout, transport=transport)

    async def __aenter__(self) -> "Caller":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self._http.aclose()

    async def _post(self, action: str, payload: dict[str, Any]) -> tuple[int, Any]:
        try:
            key = admission_state.runner_key()
        except admission_state.Unconfigured:
            raise Refused from None
        try:
            resp = await self._http.post(
                f"{BASE_PATH}/{action}", json=payload,
                headers={"Authorization": f"Bearer {self._token}", admission_state.RUNNER_KEY_HEADER: key},
            )
        except httpx.HTTPError:
            raise Unavailable from None
        try:
            body = resp.json()
        except ValueError:
            body = None
        if resp.status_code == 503 and isinstance(body, dict) and body.get("error") == "store_off":
            raise StoreOff
        if resp.status_code in (401, 403):
            raise Refused
        if not ServiceClient._ours(body):
            raise Unavailable
        return resp.status_code, body

    async def enqueue(self, payload: dict[str, Any]) -> tuple[JobView, bool, bool]:
        """The job for an admitted command, with whether it was there
        already and whether this re-queued it."""
        status, body = await self._post("enqueue", payload)
        if status == 200:
            duplicate, requeued = body.get("duplicate"), body.get("requeued")
            if not isinstance(duplicate, bool) or not isinstance(requeued, bool):
                raise Unavailable
            return _view(body.get("job")), duplicate, requeued
        if status == 409 and body.get("error") == "mismatch":
            raise Mismatch
        if status in (404, 409) and body.get("error") == "not_admitted":
            raise NotAdmitted
        raise Refused if 400 <= status < 500 else Unavailable

    async def status(self, job_id: str) -> JobStatus | None:
        """The account's job, or None for another account's or an unknown
        one."""
        status, body = await self._post("status", {"job_id": job_id})
        if status == 404 and body.get("error") == "not_found":
            return None
        if status != 200 or not isinstance(body.get("retryable"), bool):
            raise Refused if 400 <= status < 500 else Unavailable
        envelope = body.get("envelope")
        if envelope is not None and not isinstance(envelope, dict):
            raise Unavailable
        return JobStatus(_view(body.get("job")), body["retryable"], envelope)

    async def cancel(self, job_id: str) -> JobView | None:
        """Asks the account's job to stop: a queued one ends at once, a
        running one at its next heartbeat. None for another account's or an
        unknown one."""
        status, body = await self._post("cancel", {"job_id": job_id})
        if status == 404 and body.get("error") == "not_found":
            return None
        if status != 200:
            raise Refused if 400 <= status < 500 else Unavailable
        return _view(body.get("job"))

    async def review_start(self, job_id: str, source_checksum: str, command_id: str, lease_hash: str,
                           quota: str) -> ReviewStarted | None:
        """Marks the job's result's rubric requested, with its own
        admission charge, before any provider call (PR 3); or answers how
        far its review already got. None for another account's or an
        unknown job."""
        payload = {"job_id": job_id, "source_checksum": source_checksum, "command_id": command_id,
                   "lease_hash": lease_hash, "quota": quota}
        status, body = await self._post("review_start", payload)
        if status == 404 and body.get("error") == "not_found":
            return None
        if status == 200 and body.get("state") in REVIEW_STATES:
            material = body.get("material")
            if body["state"] == "requested" and not _material(material):
                raise Unavailable
            return ReviewStarted(body["state"], material if body["state"] == "requested" else None)
        if status == 409 and body.get("error") in REVIEW_REFUSALS:
            raise ReviewRefused(body["error"])
        if status == 429 and body.get("error") == "quota" and body.get("quota") in ("exceeded", "demo_limit"):
            retry_after = body.get("retry_after")
            raise ReviewOverQuota(body["quota"], retry_after if _int(retry_after) and retry_after >= 0 else 0)
        raise Refused if 400 <= status < 500 else Unavailable

    async def review_finish(self, job_id: str, lease: str, review: dict[str, Any]) -> str:
        """Writes the review into the graded row and completes the rubric,
        while the review's lease is live; answers the rubric's state. A
        finish that came too late is ``Superseded``."""
        status, body = await self._post("review_finish", {"job_id": job_id, "lease": lease, "review": review})
        if status == 200 and body.get("state") == "completed":
            return "completed"
        if status in (404, 409) and body.get("error") in ("superseded", "not_found"):
            raise Superseded
        raise Refused if 400 <= status < 500 else Unavailable


# ---------------------------------------------------------------------------
# The review's answers (PR 3)
# ---------------------------------------------------------------------------

# requested: this call marked it and may call the provider; completed and
# lost: as it already is.
REVIEW_STATES = ("requested", "completed", "lost")
REVIEW_REFUSALS = ("not_reviewable", "files_changed", "in_flight", "mismatch")


class ReviewRefused(Refused):
    """The store won't start this review: ``code`` says why."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ReviewOverQuota(Refused):
    """The review's own charge doesn't fit the hour."""

    def __init__(self, quota: str, retry_after: int) -> None:
        super().__init__(quota)
        self.quota = quota
        self.retry_after = retry_after


@dataclass(frozen=True)
class ReviewStarted:
    state: str
    # With ``requested``: the job's kind and definition, and the graded
    # row's results and chats, which the prompt is made of.
    material: dict[str, Any] | None


def _material(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("kind") in ("grade", "take_home_submit")
        and isinstance(value.get("definition"), dict)
        and isinstance(value.get("results"), (list, dict))
        and isinstance(value.get("ai_chats"), list)
    )
