import sqlite3
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend_app.main import app

    return TestClient(app)


@pytest.fixture()
def api_key():
    return "test-key-sk-local"


def _auth_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


class TestAdminEndpoints:
    @pytest.fixture(autouse=True)
    def mock_auth(self):
        with patch("backend_app.utils.dependencies.require_api_key", return_value="test-key"):
            yield

    @pytest.fixture(autouse=True)
    def mock_db(self):
        in_memory = sqlite3.connect(":memory:")
        in_memory.row_factory = sqlite3.Row
        with patch("sqlite3.connect", return_value=in_memory):
            yield

    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_ingest_stats(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.get("/v1/ingest/stats", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_files" in data
        assert "indexed" in data
        assert "pending" in data
        assert "errors" in data

    def test_system_info(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.get("/v1/system/info", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "python_version" in data
        assert "base_path" in data

    def test_batch_stats(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.get("/v1/batch/stats", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "queue_size" in data

    def test_top_files(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.get("/v1/ingest/top-files?limit=10", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "files" in data
        assert isinstance(data["files"], list)
