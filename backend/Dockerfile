# ==============================================================================
# ClimateRiskFloodPrediction - Backend Container (FastAPI + ONNX Runtime CPU)
# Target Deployment: Amazon ECS Fargate / AWS App Runner / Local Docker
# Note: Explicitly CPU-based; Amazon SageMaker is NOT used.
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ml.txt requirements-geo.txt requirements-prod.txt /build/
RUN pip install --no-cache-dir --user -r requirements-prod.txt

# Final lean runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create non-root user for security compliance
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data /app/models_deployed && \
    chown -R appuser:appuser /app

# Copy application source code and deployed model configuration
COPY --chown=appuser:appuser app /app/app
COPY --chown=appuser:appuser models_deployed /app/models_deployed/

USER appuser

ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////app/data/flood_app.db \
    MODEL_DIR=/app/models_deployed \
    CORS_ORIGINS=*

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

