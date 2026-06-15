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


@lru_cache
def get_settings() -> Settings:
    return Settings()
