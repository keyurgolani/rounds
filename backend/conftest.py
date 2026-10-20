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
