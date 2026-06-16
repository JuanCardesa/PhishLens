from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.services.diagnostics import DIAGNOSTICS


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
        **snapshot,
    }
