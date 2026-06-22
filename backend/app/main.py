from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.exception_handlers import validation_exception_handler
from app.middleware.request_context import RequestContextMiddleware
from app.routers import analyze, diagnostics, health, report

configure_logging()

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.3.0",
    description="Defensive phishing risk analysis API for the PhishLens browser extension.",
)

_extension_origins = settings.chrome_extension_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[*settings.allowed_origins, *_extension_origins],
    # Fall back to broad regex only when no specific IDs are configured (local dev).
    allow_origin_regex=(
        r"^chrome-extension://.*$"
        if settings.allow_chrome_extension_origins and not _extension_origins
        else None
    ),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID", "X-Diagnostics-Token"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestContextMiddleware)

app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(report.router)
app.include_router(diagnostics.router)
