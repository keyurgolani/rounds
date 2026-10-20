import re

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    # The code-runner backend is stateless — no DB, no migrations, no
    # seed. Just instantiate the app.
    from main import app
    with TestClient(app) as test_client:
        yield test_client


# ---- admission (ROUNDS-00A-L01) --------------------------------------------

TEST_TOKEN = "test-token-placeholder"
TEST_ACCOUNT_ID = "u1"


@pytest.fixture
def signed_in(monkeypatch):
    """Admits requests that carry ``Authorization: Bearer <TEST_TOKEN>``
    as account ``u1`` without asking PocketBase. Any other bearer is 401.
    Returns the headers to send."""
    from app import admission
    from app.errors import TypedError

    async def authenticate(token: str) -> dict:
        if token != TEST_TOKEN:
            raise TypedError("unauthenticated")
        return {"id": TEST_ACCOUNT_ID, "token": token, "record": {"id": TEST_ACCOUNT_ID, "is_demo": False}}

    monkeypatch.setattr(admission, "authenticate", authenticate)
    return {"Authorization": f"Bearer {TEST_TOKEN}"}


class FakePocketBase:
    """The record reads the runner makes with a caller's token: a list
    filtered by slug, or one record by id. A hidden record answers 404,
    the way PocketBase answers for another account's record."""

    _PATH = re.compile(r"/api/collections/([a-z_]+)/records(?:/([a-z0-9]+))?")
    _FILTER = re.compile(r"slug='([a-z0-9-]+)'")

    def __init__(self) -> None:
        self.records: dict[str, dict[str, dict]] = {}
        self.hidden: set[tuple[str, str]] = set()
        self.calls: list[tuple[str, str, dict | None]] = []

    def add(self, collection: str, *, hidden: bool = False, **fields) -> dict:
        rows = self.records.setdefault(collection, {})
        record = {"id": f"r{sum(map(len, self.records.values())):014d}", **fields}
        rows[record["id"]] = record
        if hidden:
            self.hidden.add((collection, record["id"]))
        return record

    def view(self, collection: str) -> "CollectionView":
        return CollectionView(self, collection)

    async def pb_get(self, token, path, params=None):
        self.calls.append((token, path, params))
        match = self._PATH.fullmatch(path)
        assert match, path
        collection, record_id = match.groups()
        rows = self.records.get(collection, {})
        if record_id is not None:
            record = rows.get(record_id)
            if record is None or (collection, record_id) in self.hidden:
                raise HTTPException(status_code=404, detail="The requested resource wasn't found.")
            return record
        slug = self._FILTER.fullmatch((params or {}).get("filter", ""))
        items = [
            r for r in rows.values()
            if slug and r.get("slug") == slug.group(1) and (collection, r["id"]) not in self.hidden
        ]
        return {"items": items[:1], "totalItems": len(items)}


class CollectionView:
    def __init__(self, pocketbase: FakePocketBase, collection: str) -> None:
        self.pocketbase = pocketbase
        self.collection = collection

    def add(self, **fields) -> dict:
        return self.pocketbase.add(self.collection, **fields)

    @property
    def calls(self) -> list:
        prefix = f"/api/collections/{self.collection}/"
        return [c for c in self.pocketbase.calls if c[1].startswith(prefix)]


class FakeAdmissionStore:
    """``pb_hooks/admission.js`` behind ``admission.store``, in memory.

    Commands key on (bearer, command id), as the hook keys on (account,
    command id). Every request is in quota unless a test sets ``quota``,
    and ``down`` makes every call fail the way an unreachable store does.
    The hook's own decisions are tested under node and in the harness."""

    def __init__(self) -> None:
        from app import admission_state

        self.Unavailable = admission_state.Unavailable
        self._decision = admission_state.Decision
        self.commands: dict[tuple[str, str], dict] = {}
        self.leases: dict[str, dict] = {}
        self.calls: list[tuple[str, dict]] = []
        self.quota = "ok"
        self.retry_after = 0
        self.down = False
        self._leases = 0

    def _call(self, name: str, **args) -> None:
        self.calls.append((name, args))
        if self.down:
            raise self.Unavailable

    def called(self, name: str) -> list[dict]:
        return [args for call, args in self.calls if call == name]

    async def admit(self, token, operation, wall_seconds, key, fingerprint, mode):
        self._call("admit", token=token, operation=operation, wall_seconds=wall_seconds, key=key,
                   fingerprint=fingerprint, mode=mode)
        verdict, existing = "none", None
        if key is not None:
            existing = self.commands.get((token, key))
            if existing is None:
                verdict = "new"
            elif existing["fingerprint"] != fingerprint or existing["operation"] != operation:
                verdict = "mismatch"
            elif existing["state"] == "completed":
                verdict = "replay"
            elif existing["state"] == "in_flight":
                verdict = "in_flight"
            else:
                verdict = "retry"
        refused = verdict in ("replay", "mismatch", "in_flight")
        if refused and mode == "enforce":
            return self._decision(verdict, "skipped", 0, None, existing["result"] if verdict == "replay" else None)
        if self.quota != "ok":
            return self._decision(verdict, self.quota, self.retry_after, None, None)
        self._leases += 1
        lease = f"lease{self._leases:038d}"
        if key is not None and not refused:
            self.commands[(token, key)] = {"fingerprint": fingerprint, "operation": operation,
                                           "state": "in_flight", "result": None, "wall_seconds": wall_seconds}
        self.leases[lease] = {"token": token, "key": None if refused else key, "wall_seconds": wall_seconds}
        return self._decision(verdict, "ok", 0, lease, None)

    async def settle(self, token, lease, wall_seconds):
        self._call("settle", token=token, lease=lease, wall_seconds=wall_seconds)
        self.leases[lease]["wall_seconds"] = wall_seconds

    async def finish(self, token, lease, outcome, result=None):
        self._call("finish", token=token, lease=lease, outcome=outcome, result=result)
        entry = self.leases.pop(lease, None)
        if entry is None:
            return False
        if entry["key"] is not None:
            command = self.commands[(token, entry["key"])]
            command["state"] = {"completed": "completed", "denied": "retryable"}.get(outcome, "failed_infrastructure")
            command["result"] = result if outcome == "completed" else None
        return True


@pytest.fixture(autouse=True)
def admission_store(monkeypatch):
    """Every test talks to an in-memory admission store, never PocketBase."""
    from app import admission

    fake = FakeAdmissionStore()
    monkeypatch.setattr(admission, "store", fake)
    return fake


@pytest.fixture
def pocketbase(monkeypatch):
    """One fake PocketBase behind every admitted router's ``pb_get``."""
    from routers import ai_coding, runner, take_home

    fake = FakePocketBase()
    for module in (runner, ai_coding, take_home):
        monkeypatch.setattr(module, "pb_get", fake.pb_get)
    return fake


@pytest.fixture
def questions(pocketbase):
    """The fake ``coding_questions`` collection."""
    return pocketbase.view("coding_questions")
