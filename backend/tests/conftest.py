import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def isolate_runtime_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PHISHLENS_MODEL_PATH", "ml/models/test-model-does-not-exist.joblib")
    monkeypatch.delenv("PHISHTANK_API_KEY", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
