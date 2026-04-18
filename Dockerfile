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

RUN groupadd --system --gid 1001 stocksage \
    && useradd --system --uid 1001 --gid stocksage --home-dir /app stocksage \
    && chown -R stocksage:stocksage /app

USER stocksage

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/').status==200 else 1)" || exit 1

CMD ["sh", "-c", "uvicorn src.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
