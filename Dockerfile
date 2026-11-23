# RAGOps image: ONE image for the API Deployment, the ingestion Job/CronJob and the evaluation Job.
# Build context: the repository root.   docker build -t ragops:v1 .
# It contains A2's code unchanged (api/app, indexer/pipeline) plus the RAGOps layer (ragops/), the
# configuration defaults (config/) and the evaluation data (eval/, experiments/). Nothing secret and no
# corpus is baked in: documents arrive on the data volume, thresholds arrive from a ConfigMap.
FROM python:3.12.11-slim-bookworm AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=10
RUN python -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
# the cache mount keeps downloaded wheels outside the image, so a retry after a network timeout resumes
RUN --mount=type=cache,target=/root/.cache/pip /opt/venv/bin/pip install -r /tmp/requirements.txt

FROM python:3.12.11-slim-bookworm
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app RAGOPS_ROOT=/app RAGOPS_DATA_DIR=/data HOME=/tmp
# OCR needs system packages: tesseract for recognition, poppler to render PDF pages.
# No 'apt-get upgrade': on the slow network used for this assignment it re-downloaded every base package.
# The base image tag is pinned instead; bump it to pick up Debian security fixes.
RUN apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY api/app /app/app
COPY indexer/pipeline /app/pipeline
COPY ragops /app/ragops
COPY config /app/config
COPY eval /app/eval
COPY experiments /app/experiments
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin rahbar \
    && mkdir -p /data && chown 10001:10001 /data
USER 10001
EXPOSE 8000
# Default command = the API. Jobs override it (python -m ragops.ingestion ... / ragops.evaluation.suite ...).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
