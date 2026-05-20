# Multi-stage: builder installs deps, runtime runs the Flask backend.
# IMPORTANT: build context must be repository root.
FROM python:3.14-slim AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
# fastembed → py-rust-stemmers: no py3.14 wheel yet; compile from source (needs cc).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade pip
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

FROM python:3.14-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app
RUN useradd --create-home --shell /bin/bash appuser
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Backend application code
COPY backend/app ./app
COPY backend/run.py ./run.py
COPY backend/docker-entrypoint.sh /app/docker-entrypoint.sh
COPY backend/migrations ./migrations

# OpenAPI inventory for /backend/openapi.yaml (path resolved from app/info/routes.py → /app/docs/api/)
COPY docs/api/openapi.yaml ./docs/api/openapi.yaml

# Shared runtime packages used by backend imports
COPY story_runtime_core ./story_runtime_core
COPY ai_stack ./ai_stack

# YAML narrative modules (session start, compiler). Matches packaged path in module_loader.
COPY content/modules /app/content/modules
COPY prompts /app/prompts

RUN mkdir -p /app/instance && chmod +x /app/docker-entrypoint.sh && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
# Default limit_request_field_size is 8190; large Cookie headers (e.g. many localhost dev cookies) trigger 431.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--limit-request-field_size", "32768", "--access-logfile", "-", "run:app"]
