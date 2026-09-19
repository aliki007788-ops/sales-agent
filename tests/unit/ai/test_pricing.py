from sales_agent.ai.pricing import compute_cost_usd, count_tokens


def test_count_tokens():
    assert count_tokens("") == 0
    assert count_tokens("hello world") > 0


def test_compute_cost():
    c = compute_cost_usd("gpt-4o-mini", "x" * 100, "y" * 20)
    assert c.cost_usd >= 0
    assert c.input_tokens > 0
