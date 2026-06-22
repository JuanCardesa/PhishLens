# --- build stage: install runtime dependencies -----------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- runtime stage: lean image, no dev tooling -----------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PHISHLENS_FEEDBACK_DB_PATH=/data/feedback.db

# Non-root user so the process cannot write to arbitrary container paths.
RUN addgroup --system phishlens && adduser --system --ingroup phishlens phishlens

WORKDIR /app

# Copy only the installed site-packages from the builder stage.
COPY --from=builder /install /usr/local

# Copy application source.
COPY app ./app

# Writable directory for the feedback SQLite database (mounted as a volume).
RUN mkdir -p /data && chown phishlens:phishlens /data

USER phishlens

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
