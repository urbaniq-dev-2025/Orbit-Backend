FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch FIRST (before requirements.txt)
# This prevents sentence-transformers from pulling CUDA version
# CPU-only PyTorch is ~200MB vs ~900MB+ for CUDA version
RUN pip install --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install Python dependencies
# Filter out torch-related packages to avoid conflicts
# Ensure sentence-transformers uses the CPU-only torch we installed
COPY requirements.txt /app/requirements.txt
RUN grep -v "^torch" /app/requirements.txt > /tmp/requirements_filtered.txt && \
    pip install --no-cache-dir -r /tmp/requirements_filtered.txt && \
    pip install --no-cache-dir sentence-transformers>=2.2.0 numpy>=1.24.0

# Copy application code
COPY clarivo_ingestion /app/clarivo_ingestion

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/healthz', timeout=5)" || exit 1

CMD ["uvicorn", "clarivo_ingestion.main:app", "--host", "0.0.0.0", "--port", "8000"]

