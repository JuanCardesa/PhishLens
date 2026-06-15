from app.core.config import get_settings


def test_default_cors_does_not_allow_all_chrome_extensions() -> None:
    settings = get_settings()

    assert settings.allowed_origins == ["http://localhost:5173"]
    assert settings.allow_chrome_extension_origins is False


def test_cors_can_allow_chrome_extensions_when_explicitly_configured(monkeypatch) -> None:
    monkeypatch.setenv("PHISHLENS_ALLOWED_ORIGINS", "http://localhost:5173,chrome-extension://*")
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.allowed_origins == ["http://localhost:5173"]
    assert settings.allow_chrome_extension_origins is True
