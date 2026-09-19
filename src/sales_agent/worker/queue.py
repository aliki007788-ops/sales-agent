# ==========================================
# src/sales_agent/worker/queue.py
# Version: 1.0 — Phase 5
#
# Simple in-process async queue (no Redis required).
# Can be swapped for Redis/arq later.
# ==========================================
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

logger = logging.getLogger("sales_agent.queue")

JobHandler = Callable[["Job"], Awaitable[None]]


@dataclass(slots=True)
class Job:
    name: str
    payload: dict[str, Any]
    tenant_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    attempts: int = 0


class InMemoryQueue:
    """Bounded asyncio queue with a background worker."""

    def __init__(self, maxsize: int = 1000) -> None:
        self._queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=maxsize)
        self._handlers: dict[str, JobHandler] = {}
        self._worker_task: asyncio.Task | None = None
        self._running = False

    def register(self, name: str, handler: JobHandler) -> None:
        self._handlers[name] = handler

    async def enqueue(self, name: str, payload: dict[str, Any], *, tenant_id: str | None = None) -> None:
        job = Job(name=name, payload=payload, tenant_id=tenant_id)
        await self._queue.put(job)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._run(), name="asa-queue-worker")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    @property
    def depth(self) -> int:
        return self._queue.qsize()

    async def _run(self) -> None:
        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            handler = self._handlers.get(job.name)
            if handler is None:
                logger.warning("no handler for job %s", job.name)
                self._queue.task_done()
                continue
            try:
                job.attempts += 1
                await handler(job)
            except Exception:
                logger.exception("job %s failed (attempt %s)", job.name, job.attempts)
            finally:
                self._queue.task_done()


# Process-wide singleton (one worker per process)
_queue: InMemoryQueue | None = None


def get_queue() -> InMemoryQueue:
    global _queue
    if _queue is None:
        _queue = InMemoryQueue()
    return _queue
