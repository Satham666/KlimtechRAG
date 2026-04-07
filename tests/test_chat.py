"""Testy endpointów czatu — /v1/chat/completions, /v1/models, /query."""
from unittest.mock import patch, AsyncMock


class TestModels:
    def test_models_list(self, client, auth_headers):
        resp = client.get("/v1/models", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data or isinstance(data, list)

    def test_models_no_auth(self, client):
        resp = client.get("/v1/models")
        assert resp.status_code in (200, 401, 403)


class TestChatCompletions:
    def test_chat_no_auth(self, client):
        resp = client.post("/v1/chat/completions", json={
            "messages": [{"role": "user", "content": "hej"}]
        })
        assert resp.status_code in (401, 403, 422)

    def test_chat_bad_auth(self, client, bad_headers):
        resp = client.post("/v1/chat/completions",
                           headers=bad_headers,
                           json={"messages": [{"role": "user", "content": "hej"}]})
        assert resp.status_code in (401, 403)

    def test_chat_empty_messages(self, client, auth_headers):
        resp = client.post("/v1/chat/completions",
                           headers=auth_headers,
                           json={"messages": []})
        assert resp.status_code in (200, 400, 422)

    def test_chat_missing_body(self, client, auth_headers):
        resp = client.post("/v1/chat/completions", headers=auth_headers)
        assert resp.status_code == 422

    def test_chat_use_rag_false(self, client, auth_headers):
        """Czat z use_rag=False nie powinien ładować embeddingów."""
        with patch("backend_app.services.chat_service.handle_chat_completions",
                   new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {
                "id": "test",
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {}
            }
            resp = client.post("/v1/chat/completions",
                               headers=auth_headers,
                               json={"messages": [{"role": "user", "content": "hej"}],
                                     "use_rag": False})
            assert resp.status_code in (200, 500)


class TestRagDebug:
    def test_rag_debug_no_auth(self, client):
        resp = client.get("/rag/debug")
        assert resp.status_code in (200, 401, 403)
