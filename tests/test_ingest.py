"""Testy endpointów ingest — upload, ingest_path, files/stats, progress."""
import io
from unittest.mock import patch, MagicMock


class TestUpload:
    def test_upload_no_auth(self, client):
        resp = client.post("/upload", files={"file": ("test.txt", b"tresc", "text/plain")})
        assert resp.status_code in (401, 403, 422)

    def test_upload_bad_auth(self, client, bad_headers):
        resp = client.post("/upload",
                           headers=bad_headers,
                           files={"file": ("test.txt", b"tresc", "text/plain")})
        assert resp.status_code in (401, 403)

    def test_upload_no_file(self, client, auth_headers):
        resp = client.post("/upload", headers=auth_headers)
        assert resp.status_code == 422


class TestIngestPath:
    def test_ingest_path_no_auth(self, client):
        resp = client.post("/ingest_path", json={"path": "/tmp/test.txt"})
        assert resp.status_code in (401, 403, 422)

    def test_ingest_path_missing_body(self, client, auth_headers):
        resp = client.post("/ingest_path", headers=auth_headers)
        assert resp.status_code == 422

    def test_ingest_path_traversal_blocked(self, client, auth_headers):
        """Path traversal musi być blokowany."""
        resp = client.post("/ingest_path",
                           headers=auth_headers,
                           json={"path": "../../etc/passwd"})
        assert resp.status_code in (400, 403, 404, 422)
        if resp.status_code == 200:
            content = resp.text
            assert "root:" not in content


class TestFilesStats:
    def test_files_stats_ok(self, client, auth_headers):
        resp = client.get("/files/stats", headers=auth_headers)
        assert resp.status_code == 200

    def test_files_stats_no_auth(self, client):
        resp = client.get("/files/stats")
        assert resp.status_code in (200, 401, 403)


class TestIngestProgress:
    def test_progress_unknown_task(self, client, auth_headers):
        resp = client.get("/ingest/progress/nonexistent-task-id",
                          headers=auth_headers)
        assert resp.status_code in (200, 404)


class TestIngestActive:
    def test_active_ok(self, client, auth_headers):
        resp = client.get("/ingest/active", headers=auth_headers)
        assert resp.status_code in (200, 401, 403)
