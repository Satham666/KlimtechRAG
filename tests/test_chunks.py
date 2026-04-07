"""Testy endpointu /v1/chunks — low-level retrieval bez LLM."""


class TestChunks:
    def test_chunks_no_auth(self, client):
        resp = client.post("/v1/chunks", json={"text": "test"})
        assert resp.status_code in (401, 403, 422)

    def test_chunks_bad_auth(self, client, bad_headers):
        resp = client.post("/v1/chunks",
                           headers=bad_headers,
                           json={"text": "test"})
        assert resp.status_code in (401, 403)

    def test_chunks_missing_body(self, client, auth_headers):
        resp = client.post("/v1/chunks", headers=auth_headers)
        assert resp.status_code == 422

    def test_chunks_empty_text(self, client, auth_headers):
        resp = client.post("/v1/chunks",
                           headers=auth_headers,
                           json={"text": "", "limit": 5})
        assert resp.status_code in (200, 400, 422)

    def test_chunks_valid_request(self, client, auth_headers):
        """Poprawne zapytanie — odpowiedź 200 z listą chunków (może być pusta)."""
        resp = client.post("/v1/chunks",
                           headers=auth_headers,
                           json={"text": "test query", "limit": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_chunks_with_context_filter(self, client, auth_headers):
        resp = client.post("/v1/chunks",
                           headers=auth_headers,
                           json={"text": "test",
                                 "limit": 5,
                                 "context_filter": {"source": "nieistniejacy.pdf"}})
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] == []

    def test_chunks_limit_respected(self, client, auth_headers):
        resp = client.post("/v1/chunks",
                           headers=auth_headers,
                           json={"text": "test", "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) <= 2
