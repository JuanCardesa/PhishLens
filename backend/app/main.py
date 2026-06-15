from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import analyze, health, report


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Defensive phishing risk analysis API for the PhishLens browser extension.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=r"^chrome-extension://.*$" if settings.allow_chrome_extension_origins else None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(report.router)
