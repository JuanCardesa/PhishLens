import logging

from fastapi import APIRouter

from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.scoring_service import analyze_url
from app.services.url_normalizer import hostname_from_url

router = APIRouter(tags=["analysis"])
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    response = await analyze_url(request)
    logger.info(
        "analysis_completed",
        extra={
            "url_host": hostname_from_url(request.url),
            "risk_score": response.risk_score,
            "label": response.label,
            "sources": response.sources.model_dump(),
        },
    )
    return response
