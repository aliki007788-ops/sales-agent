import pytest
from sales_agent.ai.llm import LLMClient


@pytest.mark.asyncio
async def test_mock_complete():
    c = LLMClient()
    r = await c.complete("sys", "hello")
    assert r.text
    assert r.cost_usd >= 0
    await c.aclose()
