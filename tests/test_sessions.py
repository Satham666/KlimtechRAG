import pytest
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


class TestSessionsCRUD:
    def test_create_session(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.post(
            "/v1/sessions",
            json={"title": "Test Session"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "title" in data
        assert data["title"] == "Test Session"

    def test_list_sessions(self, client, api_key):
        headers = _auth_headers(api_key)
        resp = client.get("/v1/sessions", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_get_session(self, client, api_key):
        headers = _auth_headers(api_key)
        create_resp = client.post(
            "/v1/sessions",
            json={"title": "Get Test"},
            headers=headers,
        )
        session_id = create_resp.json()["id"]

        resp = client.get(f"/v1/sessions/{session_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == session_id

    def test_patch_session(self, client, api_key):
        headers = _auth_headers(api_key)
        create_resp = client.post(
            "/v1/sessions",
            json={"title": "Original Title"},
            headers=headers,
        )
        session_id = create_resp.json()["id"]

        resp = client.patch(
            f"/v1/sessions/{session_id}",
            json={"title": "New Title"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New Title"

    def test_delete_session(self, client, api_key):
        headers = _auth_headers(api_key)
        create_resp = client.post(
            "/v1/sessions",
            json={"title": "To Delete"},
            headers=headers,
        )
        session_id = create_resp.json()["id"]

        resp = client.delete(f"/v1/sessions/{session_id}", headers=headers)
        assert resp.status_code == 204

        resp = client.get(f"/v1/sessions/{session_id}", headers=headers)
        assert resp.status_code == 404
