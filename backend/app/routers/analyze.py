from fastapi import APIRouter

from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.scoring_service import analyze_url

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    return await analyze_url(request)
