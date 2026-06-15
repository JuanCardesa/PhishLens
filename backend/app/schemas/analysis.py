from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


RiskLabel = Literal["safe", "suspicious", "dangerous"]


class DOMFeatures(BaseModel):
    has_password_field: bool = False
    num_forms: int = Field(default=0, ge=0, le=100)
    external_form_action: bool = False
    num_iframes: int = Field(default=0, ge=0, le=200)
    external_links_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    has_hidden_inputs: bool = False


class AnalysisRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    dom_features: DOMFeatures = Field(default_factory=DOMFeatures)

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("url must be an absolute http or https URL")
        return value


class AnalysisSources(BaseModel):
    heuristics: bool
    ml: bool
    phishtank: bool
    tls: bool


class AnalysisResponse(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    label: RiskLabel
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
    sources: AnalysisSources


class ReportRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    observed_label: RiskLabel
    expected_label: RiskLabel
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("url must be an absolute http or https URL")
        return value


class ReportResponse(BaseModel):
    status: Literal["received"]
    message: str
