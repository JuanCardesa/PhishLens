import logging

from fastapi import APIRouter, Depends, Request

from app.schemas.analysis import ReportRequest, ReportResponse
from app.services.diagnostics import DIAGNOSTICS
from app.services.rate_limiter import rate_limit_dependency
from app.services.url_normalizer import hostname_from_url

router = APIRouter(tags=["reports"])
logger = logging.getLogger(__name__)


@router.post("/report", response_model=ReportResponse)
def report_feedback(
    payload: ReportRequest,
    request: Request,
    _: None = Depends(rate_limit_dependency("report")),
) -> ReportResponse:
    DIAGNOSTICS.record_report()
    logger.info(
        "phishlens_feedback",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "url_host": hostname_from_url(payload.url),
            "observed_label": payload.observed_label,
            "expected_label": payload.expected_label,
            "notes_present": bool(payload.notes),
        },
    )
    return ReportResponse(status="received", message="Feedback recorded for review.")
