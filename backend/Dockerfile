# syntax=docker/dockerfile:1
FROM python:3.11.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MDE_DATA_DIR=/app/data

WORKDIR /app

COPY requirements.lock .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-deps --retries 10 --timeout 600 -r requirements.lock

COPY api ./api
COPY mde ./mde

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
