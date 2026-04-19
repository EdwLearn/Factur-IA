FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libxml2-dev \
    libxslt-dev \
    libjpeg-dev \
    zlib1g-dev \
    poppler-utils \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# torch in its own layer — changes to requirements.txt won't invalidate this ~800 MB download
# --retries 5 handles flaky CDN (download.pytorch.org) on Railway / CI
RUN pip install --no-cache-dir --timeout 600 --retries 5 torch==2.1.2+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# All other dependencies
COPY apps/api/requirements_api.txt requirements.txt
RUN pip install --no-cache-dir --timeout 300 --retries 5 -r requirements.txt

# Alembic lives at project root — preserve the same layout so imports resolve
COPY alembic.ini .
COPY alembic/ alembic/

# App source (preserves apps/api/src structure that alembic/env.py imports)
COPY apps/api/ apps/api/

# PYTHONPATH lets both import styles work:
#   "src.api.main:app"                  (uvicorn, relative to apps/api/)
#   "apps.api.src.database.models"      (alembic env.py, relative to /app)
ENV PYTHONPATH=/app:/app/apps/api

RUN chmod +x apps/api/entrypoint.sh

EXPOSE 8000

CMD ["./apps/api/entrypoint.sh"]
