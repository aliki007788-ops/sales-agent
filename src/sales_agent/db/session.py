# ==========================================
# src/sales_agent/db/session.py
# Version: 1.1 — Postgres-safe guards
# ==========================================
from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sales_agent.config import get_settings


def _is_postgres(url: str | None = None) -> bool:
    u = (url or get_settings().database_url).lower()
    return "postgres" in u or "postgresql" in u


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    settings = get_settings()
    connect_args: dict[str, Any] = {}
    if not _is_postgres(settings.database_url):
        connect_args["check_same_thread"] = False

    kwargs: dict[str, Any] = {
        "echo": settings.db_echo,
        "future": True,
        "connect_args": connect_args,
    }
    if _is_postgres(settings.database_url):
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
        kwargs["pool_pre_ping"] = True

    return create_async_engine(settings.database_url, **kwargs)


@lru_cache(maxsize=1)
def session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """RLS tenant context — no-op on SQLite."""
    if not _is_postgres():
        return
    await session.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": tenant_id or ""},
    )


async def clear_tenant_context(session: AsyncSession) -> None:
    await set_tenant_context(session, "")


async def check_connection() -> dict[str, Any]:
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "database": "ok",
            "dialect": "postgresql" if _is_postgres() else "sqlite",
        }
    except Exception as exc:
        return {"database": "error", "detail": str(exc)}


async def dispose_engine() -> None:
    engine = get_engine()
    await engine.dispose()
    get_engine.cache_clear()
    session_factory.cache_clear()
