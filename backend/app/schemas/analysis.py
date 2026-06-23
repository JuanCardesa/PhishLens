from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.services.url_normalizer import URLNormalizationError, normalize_url


RiskLabel = Literal["safe", "suspicious", "dangerous"]
RiskCategory = Literal["url", "dom", "threat_intel", "tls", "domain_age", "ml"]


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
        try:
            return normalize_url(value)
        except URLNormalizationError as exc:
            raise ValueError("url must be an absolute http or https URL") from exc


class AnalysisSources(BaseModel):
    heuristics: bool
    ml: bool
    phishtank: bool
    tls: bool
    domain_age: bool = False
    demo: bool = False


class RiskBreakdownItem(BaseModel):
    category: RiskCategory
    score: int = Field(ge=-10, le=100)
    min_score: int = Field(default=0, ge=-10, le=100)
    max_score: int = Field(ge=0, le=100)
    reasons: list[str]
    source: str


class AnalysisResponse(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    label: RiskLabel
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
    sources: AnalysisSources
    risk_breakdown: list[RiskBreakdownItem] = Field(default_factory=list)


class ReportRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    observed_label: RiskLabel
    expected_label: RiskLabel
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, value: str) -> str:
        try:
            return normalize_url(value)
        except URLNormalizationError as exc:
            raise ValueError("url must be an absolute http or https URL") from exc


class ReportResponse(BaseModel):
    status: Literal["received"]
    message: str
