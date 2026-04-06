import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_root_redirect(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code in (200, 307)


class TestSecurity:
    def test_api_key_missing(self, client):
        resp = client.get("/v1/ingest/list")
        assert resp.status_code in (401, 403, 422)

    def test_api_key_invalid(self, client):
        headers = {"Authorization": "Bearer invalid-key"}
        resp = client.get("/v1/ingest/list", headers=headers)
        assert resp.status_code in (401, 403)

    def test_api_key_valid(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.get("/v1/ingest/list", headers=headers)
        assert resp.status_code == 200


class TestChunksEndpoint:
    def test_chunks_missing_auth(self, client):
        resp = client.post("/v1/chunks", json={"text": "test"})
        assert resp.status_code in (401, 403, 422)

    def test_chunks_missing_body(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.post("/v1/chunks", headers=headers)
        assert resp.status_code == 422

    def test_chunks_empty_text(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.post(
            "/v1/chunks",
            json={"text": "", "limit": 5},
            headers=headers,
        )
        assert resp.status_code in (200, 422)


class TestIngestList:
    def test_ingest_list_ok(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.get("/v1/ingest/list?limit=10", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data or "total" in data

    def test_ingest_list_filter_status(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.get(
            "/v1/ingest/list?status=indexed&limit=5", headers=headers
        )
        assert resp.status_code == 200


class TestWorkspaces:
    def test_workspaces_list(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.get("/workspaces", headers=headers)
        assert resp.status_code == 200

    def test_workspaces_create_missing_auth(self, client):
        resp = client.post(
            "/workspaces", json={"name": "test"}
        )
        assert resp.status_code in (401, 403, 422)

    def test_workspaces_create_and_delete(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.post(
            "/workspaces", json={"name": "pytest-tmp-workspace"}, headers=headers
        )
        assert resp.status_code == 200

        resp = client.delete(
            "/workspaces/pytest-tmp-workspace?force=true", headers=headers
        )
        assert resp.status_code in (200, 404)


class TestCollections:
    def test_collections_list(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.get("/collections", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
