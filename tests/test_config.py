import pytest


@pytest.fixture(scope="module")
def settings():
    from backend_app.config import Settings

    return Settings()


class TestConfigDefaults:
    def test_qdrant_collection(self, settings):
        assert settings.qdrant_collection == "klimtech_docs"

    def test_qdrant_url(self, settings):
        assert "localhost" in str(settings.qdrant_url)

    def test_api_key_default_none(self, settings):
        assert settings.api_key is None

    def test_allowed_extensions(self, settings):
        assert ".pdf" in settings.allowed_extensions_docs
        assert ".docx" in settings.allowed_extensions_docs
        assert ".py" in settings.allowed_extensions_docs

    def test_bm25_weight(self, settings):
        assert 0.0 <= settings.bm25_weight <= 1.0

    def test_max_file_size(self, settings):
        assert settings.max_file_size_bytes > 0

    def test_log_level(self, settings):
        assert settings.log_level in ("DEBUG", "INFO", "WARNING", "ERROR")


class TestConfigWithEnv:
    @pytest.mark.parametrize("env_key,env_val,field", [
        ("KLIMTECH_BM25_WEIGHT", "0.5", "bm25_weight"),
        ("KLIMTECH_QDRANT_COLLECTION", "test_coll", "qdrant_collection"),
    ])
    def test_env_override(self, monkeypatch, settings, env_key, env_val, field):
        monkeypatch.setenv(env_key, env_val)
        s = Settings()
        assert getattr(s, field) in (float(env_val) if "weight" in field else env_val)
