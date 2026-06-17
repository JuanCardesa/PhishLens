from fastapi import APIRouter, Response

from app.core.config import get_settings
from app.services.feedback_store import FEEDBACK_STORE
from app.services.ml_service import is_model_available

router = APIRouter(tags=["health"])


@router.get("/health")
def health(response: Response) -> dict[str, object]:
    settings = get_settings()

    db_ok = True
    try:
        FEEDBACK_STORE.count()
    except Exception:
        db_ok = False

    if not db_ok:
        response.status_code = 503

    return {
        "status": "ok" if db_ok else "degraded",
        "service": settings.service_name,
        "checks": {
            "feedback_store": db_ok,
            "ml_model": is_model_available(settings),
        },
    }
