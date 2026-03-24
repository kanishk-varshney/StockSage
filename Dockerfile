FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MALLOC_ARENA_MAX=2

WORKDIR /app

# Install project dependencies and app package.
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY main.py /app/main.py

RUN pip install --upgrade pip && pip install .

EXPOSE 8000

# Cloud platforms (Railway, Render, Koyeb) inject PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn src.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
