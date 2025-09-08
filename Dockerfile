# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (optional: tzdata for correct time)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-web.txt ./
RUN pip install -r requirements-web.txt

COPY . .

EXPOSE 8080
# Yandex Cloud typically sets PORT; fallback to 8080
ENV PORT=8080
CMD ["gunicorn", "web:create_app()", "--bind", "0.0.0.0:${PORT}", "--workers", "2", "--threads", "4", "--timeout", "120"]
