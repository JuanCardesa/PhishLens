from hmac import compare_digest

from fastapi import APIRouter, HTTPException, Request

from app.core.config import get_settings
from app.services.diagnostics import DIAGNOSTICS
from app.services.ml_service import is_model_available


router = APIRouter(tags=["diagnostics"])


@router.get("/diagnostics")
def diagnostics(request: Request) -> dict[str, object]:
    settings = get_settings()
    if not settings.enable_diagnostics:
        raise HTTPException(status_code=404, detail="Diagnostics are disabled.")

    if settings.diagnostics_token:
        provided = request.headers.get("X-Diagnostics-Token", "")
        if not compare_digest(provided, settings.diagnostics_token):
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
            "domain_age_lookup_enabled": settings.enable_domain_age_lookup,
            "ml_model_available": is_model_available(settings),
            "demo_threat_source_enabled": settings.enable_demo_threat_source,
        },
        **snapshot,
    }
