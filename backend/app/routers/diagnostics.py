from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.services.diagnostics import DIAGNOSTICS
from app.services.ml_service import is_model_available


router = APIRouter(tags=["diagnostics"])


@router.get("/diagnostics")
def diagnostics() -> dict[str, object]:
    settings = get_settings()
    if not settings.enable_diagnostics:
        raise HTTPException(status_code=404, detail="Diagnostics are disabled.")

    snapshot = DIAGNOSTICS.snapshot()
    return {
        "status": "ok",
        "service": settings.service_name,
        "privacy": "No URLs, page content, form values, credentials, cookies, or HTML are exposed.",
        "capabilities": {
            "diagnostics_enabled": settings.enable_diagnostics,
            "rate_limiting_enabled": settings.enable_rate_limiting,
            "threat_intel_enabled": settings.enable_threat_intel,
            "tls_analysis_enabled": settings.enable_tls_analysis,
            "ml_model_available": is_model_available(settings),
            "demo_threat_source_enabled": settings.enable_demo_threat_source,
        },
        **snapshot,
    }
