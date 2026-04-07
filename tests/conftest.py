"""
Wspólne fixtures dla testów KlimtechRAG.
Używane przez test_health.py, test_chat.py, test_ingest.py, test_chunks.py itd.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    from backend_app.main import app as _app
    return _app


@pytest.fixture(scope="session")
def client(app):
    return TestClient(app)


@pytest.fixture(scope="session")
def api_key() -> str:
    return "test-key-sk-local"


@pytest.fixture(scope="session")
def auth_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


@pytest.fixture(scope="session")
def bad_headers() -> dict:
    return {"Authorization": "Bearer wrong-key"}
