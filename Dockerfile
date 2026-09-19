FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY scripts ./scripts

RUN pip install --upgrade pip \
    && pip install \
      "fastapi==0.115.0" \
      "uvicorn[standard]==0.32.0" \
      "pydantic==2.9.2" \
      "pydantic-settings==2.5.2" \
      "sqlalchemy[asyncio]==2.0.35" \
      "asyncpg==0.29.0" \
      "alembic==1.13.3" \
      "bcrypt==4.2.0" \
      "cryptography==43.0.1" \
      "httpx==0.27.2" \
      "structlog==24.4.0" \
      "python-jose[cryptography]==3.3.0"

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "sales_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
