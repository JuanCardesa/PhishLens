from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_name: str = "PhishLens API"
    service_name: str = "phishlens-api"
    phishtank_api_key: str | None = Field(default=None, validation_alias="PHISHTANK_API_KEY")
    phishtank_user_agent: str = Field(
        default="phishtank/phishlens-demo",
        validation_alias="PHISHTANK_USER_AGENT",
    )
    allowed_origins_raw: str = Field(
        default="http://localhost:5173",
        validation_alias="PHISHLENS_ALLOWED_ORIGINS",
    )
    enable_threat_intel: bool = Field(default=True, validation_alias="PHISHLENS_ENABLE_THREAT_INTEL")
    enable_tls_analysis: bool = Field(default=True, validation_alias="PHISHLENS_ENABLE_TLS_ANALYSIS")
    model_path: str = Field(default="ml/models/phishlens_model.joblib", validation_alias="PHISHLENS_MODEL_PATH")
    external_timeout_seconds: float = Field(default=4.0, validation_alias="PHISHLENS_EXTERNAL_TIMEOUT_SECONDS")
    enable_diagnostics: bool = Field(default=True, validation_alias="PHISHLENS_ENABLE_DIAGNOSTICS")
    enable_rate_limiting: bool = Field(default=True, validation_alias="PHISHLENS_ENABLE_RATE_LIMITING")
    analyze_rate_limit_per_minute: int = Field(default=60, ge=1, validation_alias="PHISHLENS_ANALYZE_RATE_LIMIT")
    report_rate_limit_per_minute: int = Field(default=20, ge=1, validation_alias="PHISHLENS_REPORT_RATE_LIMIT")
    rate_limit_window_seconds: int = Field(default=60, ge=1, validation_alias="PHISHLENS_RATE_LIMIT_WINDOW_SECONDS")
    enable_demo_threat_source: bool = Field(default=False, validation_alias="PHISHLENS_ENABLE_DEMO_THREAT_SOURCE")
    # Comma-separated Chrome extension IDs that are allowed to call the API.
    # When set, only these specific extension origins are accepted.
    # When empty, PHISHLENS_ALLOWED_ORIGINS may still opt into chrome-extension://*
    # for local development before the extension has a stable published ID.
    chrome_extension_ids: str = Field(default="", validation_alias="PHISHLENS_CHROME_EXTENSION_IDS")
    behind_proxy: bool = Field(default=False, validation_alias="PHISHLENS_BEHIND_PROXY")
    feedback_db_path: str = Field(default="feedback.db", validation_alias="PHISHLENS_FEEDBACK_DB_PATH")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins_raw.split(",")
            if origin.strip() and origin.strip() != "chrome-extension://*"
        ]

    @property
    def allow_chrome_extension_origins(self) -> bool:
        return "chrome-extension://*" in self.allowed_origins_raw

    @property
    def chrome_extension_origins(self) -> list[str]:
        """Specific extension origins derived from configured IDs, e.g. chrome-extension://<id>."""
        if not self.chrome_extension_ids.strip():
            return []
        return [
            f"chrome-extension://{ext_id.strip()}"
            for ext_id in self.chrome_extension_ids.split(",")
            if ext_id.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
