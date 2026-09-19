# ==========================================
# tests/unit/test_breaker.py
# ==========================================
from __future__ import annotations

import pytest

from sales_agent.resilience.breaker import BreakerState, CircuitBreaker, reset_breakers


@pytest.fixture(autouse=True)
def _clean():
    reset_breakers()
    yield
    reset_breakers()


@pytest.mark.asyncio
async def test_opens_after_threshold() -> None:
    b = CircuitBreaker(name="t", fail_threshold=3, reset_timeout=60)

    async def fail():
        raise ValueError("boom")

    for _ in range(3):
        with pytest.raises(ValueError):
            await b.call(fail)

    assert b.state == BreakerState.OPEN
    with pytest.raises(RuntimeError, match="circuit open"):
        await b.call(fail)


@pytest.mark.asyncio
async def test_success_resets() -> None:
    b = CircuitBreaker(name="t2", fail_threshold=2)

    async def ok():
        return 42

    assert await b.call(ok) == 42
    assert b.state == BreakerState.CLOSED
