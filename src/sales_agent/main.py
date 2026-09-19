# ==========================================
# src/sales_agent/main.py
# Version: 1.1 — Phase 5 (queue lifecycle)
# ==========================================
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sales_agent import __version__
from sales_agent.api import health
from sales_agent.api.v1 import router as v1_router
from sales_agent.config import get_settings
from sales_agent.db.session import dispose_engine, get_engine
from sales_agent.worker.queue import get_queue
from sales_agent.middleware.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_engine()
    q = get_queue()
    await q.start()
    yield
    await q.stop()
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        RateLimitMiddleware,
        max_requests=getattr(settings, "rate_limit_max", 120),
        window_seconds=getattr(settings, "rate_limit_window_seconds", 60.0),
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health.router)
    app.include_router(v1_router)
    return app


app = create_app()
