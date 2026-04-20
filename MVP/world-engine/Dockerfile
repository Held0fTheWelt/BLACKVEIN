FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# IMPORTANT: build context must be repository root.
COPY world-engine/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY world-engine/app ./app

# Shared runtime packages used by world-engine imports
COPY story_runtime_core ./story_runtime_core
COPY ai_stack ./ai_stack

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
