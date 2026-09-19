# ==========================================
# src/sales_agent/resilience/breaker.py
# Version: 1.0 — per-host circuit breaker
# ==========================================
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Simple in-process circuit breaker (per service/host)."""

    name: str
    fail_threshold: int = 5
    reset_timeout: float = 60.0
    half_open_max: int = 1
    _failures: int = 0
    _state: BreakerState = BreakerState.CLOSED
    _opened_at: float = 0.0
    _half_open_calls: int = 0

    @property
    def state(self) -> BreakerState:
        if self._state == BreakerState.OPEN:
            if time.monotonic() - self._opened_at >= self.reset_timeout:
                self._state = BreakerState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    async def call(self, fn: Callable[[], Awaitable[Any]]) -> Any:
        st = self.state
        if st == BreakerState.OPEN:
            raise RuntimeError(f"circuit open: {self.name}")
        if st == BreakerState.HALF_OPEN and self._half_open_calls >= self.half_open_max:
            raise RuntimeError(f"circuit half-open limit: {self.name}")

        if st == BreakerState.HALF_OPEN:
            self._half_open_calls += 1

        try:
            result = await fn()
        except Exception:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result

    def _on_success(self) -> None:
        self._failures = 0
        self._state = BreakerState.CLOSED
        self._half_open_calls = 0

    def _on_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.fail_threshold:
            self._state = BreakerState.OPEN
            self._opened_at = time.monotonic()


_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str, **kwargs: Any) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name, **kwargs)
    return _breakers[name]


def reset_breakers() -> None:
    _breakers.clear()
