FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy and install backend requirements first (lighter dependencies)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# Install PyTorch CPU-only version FIRST (much smaller than CUDA version)
# This reduces image size significantly (~200MB vs ~900MB for torch alone)
# CPU-only version is sufficient for sentence-transformers
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Copy ingestion module
COPY ingestion /app/ingestion

# Install ingestion dependencies (sentence-transformers will use already-installed torch)
# Exclude pydantic from ingestion requirements to avoid conflict with backend's pydantic v1
COPY ingestion/requirements.txt /app/ingestion/requirements.txt
RUN grep -v "^pydantic" /app/ingestion/requirements.txt > /tmp/ingestion_reqs.txt && \
    pip install -r /tmp/ingestion_reqs.txt && \
    pip install sentence-transformers>=2.2.0 numpy>=1.24.0

# Copy application code
COPY app /app/app
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations

# Add ingestion directory to Python path
ENV PYTHONPATH=/app/ingestion:$PYTHONPATH

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health', timeout=5)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
