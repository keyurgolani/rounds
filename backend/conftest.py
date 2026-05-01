import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    # The code-runner backend is stateless — no DB, no migrations, no
    # seed. Just instantiate the app.
    from main import app
    with TestClient(app) as test_client:
        yield test_client
