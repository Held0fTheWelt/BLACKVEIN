# Multi-stage: builder installs deps, runtime runs the Flask backend.
# IMPORTANT: build context must be repository root.
FROM python:3.13-slim AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
RUN pip install --no-cache-dir --upgrade pip
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

FROM python:3.13-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app
RUN useradd --create-home --shell /bin/bash appuser
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Backend application code
COPY backend/app ./app
COPY backend/run.py ./run.py
COPY backend/migrations ./migrations

# Shared runtime packages used by backend imports
COPY story_runtime_core ./story_runtime_core
COPY ai_stack ./ai_stack

RUN mkdir -p /app/instance && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "run:app"]
