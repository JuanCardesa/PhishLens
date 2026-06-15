import logging

from fastapi import APIRouter

from app.schemas.analysis import ReportRequest, ReportResponse

router = APIRouter(tags=["reports"])
logger = logging.getLogger(__name__)


@router.post("/report", response_model=ReportResponse)
def report_feedback(request: ReportRequest) -> ReportResponse:
    logger.info(
        "phishlens_feedback",
        extra={
            "url": request.url,
            "observed_label": request.observed_label,
            "expected_label": request.expected_label,
            "notes_present": bool(request.notes),
        },
    )
    return ReportResponse(status="received", message="Feedback recorded for review.")
