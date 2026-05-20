# Multi-stage: builder compiles Rust-backed wheels; runtime stays slim.
# IMPORTANT: build context must be repository root.
FROM python:3.14-slim AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
# fastembed → py-rust-stemmers: no py3.14 wheel yet; compile from source (needs cc).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade pip
COPY world-engine/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.14-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY world-engine/app ./app

# Shared runtime packages used by world-engine imports
COPY story_runtime_core ./story_runtime_core
COPY ai_stack ./ai_stack

# Content modules (god_of_carnage, etc.) - required for Scene Director and canonical rules
COPY content ./content
COPY prompts ./prompts

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
