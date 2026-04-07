"""Smoke testy health / docs / root."""


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json().get("status") == "ok"

    def test_health_has_version(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "status" in data

    def test_docs_accessible(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["info"]["title"] == "KlimtechRAG API"

    def test_root_responds(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code in (200, 307, 302)
