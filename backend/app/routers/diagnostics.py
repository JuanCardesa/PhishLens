from hmac import compare_digest

from fastapi import APIRouter, Header, HTTPException

from app.core.config import get_settings
from app.services.diagnostics import DIAGNOSTICS
from app.services.ml_service import is_model_available


router = APIRouter(tags=["diagnostics"])


@router.get("/diagnostics")
def diagnostics(x_diagnostics_token: str = Header(default="")) -> dict[str, object]:
    settings = get_settings()
    if not settings.enable_diagnostics:
        raise HTTPException(status_code=404, detail="Diagnostics are disabled.")
    if settings.diagnostics_token and not compare_digest(x_diagnostics_token, settings.diagnostics_token):
        raise HTTPException(status_code=401, detail="Invalid or missing diagnostics token.")

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
