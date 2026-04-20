import os
import pytest
from fastapi.testclient import TestClient

# Use an in-memory DB for tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def client():
    # Import after env override so database.py picks up the URL.
    # database.py currently hard-codes the URL, so monkeypatch here.
    # SQLite in-memory databases are per-connection; use StaticPool so that
    # every session/connection reuses the same in-memory DB.
    import database
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    # Patch the database module so all code using database.engine /
    # database.SessionLocal operates on the in-memory DB.
    database.engine = test_engine
    database.SessionLocal = test_session_local

    # seed_data.py captures SessionLocal at module import time; patch there too.
    import seed_data
    seed_data.SessionLocal = test_session_local

    # Register all ORM classes and create schema on the in-memory engine.
    from database import Base
    import models  # noqa: F401

    Base.metadata.create_all(bind=test_engine)

    # Override FastAPI's get_db dependency so request handlers also use our DB.
    def override_get_db():
        db = test_session_local()
        try:
            yield db
        finally:
            db.close()

    from main import app

    app.dependency_overrides[database.get_db] = override_get_db

    # Use context manager so the startup event (seed_if_empty) fires before
    # any test requests are made.
    with TestClient(app) as test_client:
        yield test_client
