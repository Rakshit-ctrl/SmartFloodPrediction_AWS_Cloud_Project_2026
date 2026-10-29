from app.config import settings


def test_cors_origins_parsing(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test ,")
    assert settings.cors_origins == ["http://a.test", "http://b.test"]


def test_upload_limit_default_and_invalid(monkeypatch):
    monkeypatch.setenv("UPLOAD_MAX_MB", "2")
    assert settings.upload_max_bytes == 2 * 1024 * 1024
    monkeypatch.setenv("UPLOAD_MAX_MB", "not-a-number")
    assert settings.upload_max_bytes == 8 * 1024 * 1024
