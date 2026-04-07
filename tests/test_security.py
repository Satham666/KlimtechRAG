import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend_app.main import app
    return TestClient(app)


@pytest.fixture()
def api_key():
    return "sk-local"


def _auth_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


class TestSecurityAuth:
    def test_missing_auth_returns_401_or_403(self, client):
        endpoints = [
            "/v1/sessions",
            "/v1/ingest/list",
            "/v1/batch/stats",
        ]
        for endpoint in endpoints:
            resp = client.get(endpoint)
            assert resp.status_code in (401, 403), f"{endpoint} should reject without auth"

    def test_invalid_auth_returns_401_or_403(self, client):
        headers = {"Authorization": "Bearer wrong-key"}
        endpoints = [
            "/v1/sessions",
            "/v1/ingest/list",
        ]
        for endpoint in endpoints:
            resp = client.get(endpoint, headers=headers)
            assert resp.status_code in (401, 403), f"{endpoint} should reject invalid key"

    def test_path_traversal_blocked(self, client, api_key):
        headers = _auth_headers(api_key)
        dangerous_paths = [
            "../../etc/passwd",
            "..%2F..%2Fetc%2Fpasswd",
            "....//....//....//etc/passwd",
        ]
        for dangerous in dangerous_paths:
            resp = client.get("/files/list?path=" + dangerous, headers=headers)
            assert resp.status_code in (400, 403, 404), f"Path traversal should be blocked: {dangerous}"
            if resp.status_code == 200:
                content = resp.text.lower()
                assert "root:" not in content and "bin/bash" not in content, "Should not leak system files"

    def test_health_public_no_auth(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_docs_swagger_public(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200
