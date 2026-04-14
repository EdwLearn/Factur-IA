# Multi-stage Docker build for FastAPI backend
# Optimized for production with minimal image size

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY apps/api/requirements.txt .
RUN pip install --user --no-cache-dir --no-warn-script-location -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies for OpenCV and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 facturia && \
    mkdir -p /app /tmp/ml_models && \
    chown -R facturia:facturia /app /tmp/ml_models

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder --chown=facturia:facturia /root/.local /home/facturia/.local

# Copy application code
COPY --chown=facturia:facturia apps/api/src ./src
COPY --chown=facturia:facturia apps/api/migrations ./migrations
COPY --chown=facturia:facturia apps/api/alembic.ini .

# Copy shared Python utilities if they exist
COPY --chown=facturia:facturia packages/python-utils ./packages/python-utils

# Set environment variables
ENV PATH=/home/facturia/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

# Switch to non-root user
USER facturia

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
