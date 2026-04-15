FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1 \
    MALLOC_ARENA_MAX=2

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.5.0"

COPY pyproject.toml uv.lock README.md main.py /app/
COPY src /app/src

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
