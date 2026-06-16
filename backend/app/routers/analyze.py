import logging

from fastapi import APIRouter, Depends, Request

from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.diagnostics import DIAGNOSTICS
from app.services.rate_limiter import rate_limit_dependency
from app.services.scoring_service import analyze_url
from app.services.url_normalizer import hostname_from_url

router = APIRouter(tags=["analysis"])
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    payload: AnalysisRequest,
    request: Request,
    _: None = Depends(rate_limit_dependency("analyze")),
) -> AnalysisResponse:
    response = await analyze_url(payload)
    DIAGNOSTICS.record_analysis(response.label, response.sources)
    logger.info(
        "analysis_completed",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "url_host": hostname_from_url(payload.url),
            "risk_score": response.risk_score,
            "label": response.label,
            "sources": response.sources.model_dump(),
        },
    )
    return response
