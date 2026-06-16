import pytest

from app.core.config import get_settings
from app.services.diagnostics import clear_diagnostics
from app.services.phishtank_service import clear_phishtank_cache
from app.services.rate_limiter import clear_rate_limiter
from app.services.tls_service import clear_tls_cache


@pytest.fixture(autouse=True)
def isolate_runtime_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PHISHLENS_MODEL_PATH", "ml/models/test-model-does-not-exist.joblib")
    monkeypatch.setenv("PHISHLENS_ENABLE_RATE_LIMITING", "true")
    monkeypatch.setenv("PHISHLENS_ENABLE_DIAGNOSTICS", "true")
    monkeypatch.delenv("PHISHLENS_ENABLE_DEMO_THREAT_SOURCE", raising=False)
    monkeypatch.delenv("PHISHTANK_API_KEY", raising=False)
    clear_diagnostics()
    clear_phishtank_cache()
    clear_rate_limiter()
    clear_tls_cache()
    get_settings.cache_clear()
    yield
    clear_diagnostics()
    clear_phishtank_cache()
    clear_rate_limiter()
    clear_tls_cache()
    get_settings.cache_clear()
