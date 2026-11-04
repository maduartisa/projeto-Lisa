FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

COPY alembic.ini ./
COPY migrations ./migrations

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health/live', timeout=2).read()"

CMD ["uvicorn", "commercial_platform.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
