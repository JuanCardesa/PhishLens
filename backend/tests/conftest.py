import pytest

from app.core.config import get_settings
from app.services.phishtank_service import clear_phishtank_cache
from app.services.tls_service import clear_tls_cache


@pytest.fixture(autouse=True)
def isolate_runtime_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PHISHLENS_MODEL_PATH", "ml/models/test-model-does-not-exist.joblib")
    monkeypatch.delenv("PHISHTANK_API_KEY", raising=False)
    clear_phishtank_cache()
    clear_tls_cache()
    get_settings.cache_clear()
    yield
    clear_phishtank_cache()
    clear_tls_cache()
    get_settings.cache_clear()
