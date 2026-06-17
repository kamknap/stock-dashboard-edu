# Stock Dashboard API container image.
# Works unchanged on Render (free) and Cloud Run: both inject the listening
# port via the $PORT environment variable.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY app ./app

# Local default; the hosting platform overrides PORT at runtime.
ENV PORT=8080
EXPOSE 8080

# Shell form so ${PORT} is expanded at runtime.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
